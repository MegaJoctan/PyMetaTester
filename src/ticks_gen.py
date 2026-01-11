import numpy as np
import datetime
import polars as pl
import os
import config

class TicksGen:
    def __init__(self):
        pass
    
    @staticmethod
    def interpolate_prices(start, end, steps):
        if steps <= 1:
            return [end]
        return np.linspace(start, end, steps).tolist()
    
    @staticmethod
    def __tick__(time: datetime, 
             bid: float,
             ask: float,
             time_msc: int=0,
             last: float=0,
             volume: int=0,
             volume_real: int=0,
             flags: int=-1) -> dict:
        
        if time_msc == 0:
            if isinstance(time, datetime):
                time_msc = time.timestamp()
        
        return {
                    "time": time,
                    "bid": bid,
                    "ask": ask,
                    "last": bid if last==0 else last,
                    "volume": volume,
                    "time_msc": time_msc,
                    "flags": flags,
                    "volume_real": volume_real,
                }
    
    def build_support_points(bar: dict) -> list:
        o, h, l, c = bar["open"], bar["high"], bar["low"], bar["close"]

        if c >= o:  # bullish
            return [o, l, h, c]
        else:       # bearish
            return [o, h, l, c]
    
    @staticmethod    
    def __resolve_tick_count(bar: dict) -> int:
        # MT5 internally limits complexity
        return max(1, min(bar["tick_volume"], 20))
    
    @staticmethod
    def generate_ticks_from_bar(bar: dict, symbol_point: float):
        tick_count = TicksGen.__resolve_tick_count(bar)
        spread = bar["spread"]

        base_msc = int(bar["time"].timestamp() * 1000)
        step = max(1, 1000 // tick_count)

        ticks = []

        # ---- 1 tick -----
        if tick_count == 1:
            price = bar["close"]
            return [
                TicksGen.__tick__(
                    bar["time"],
                    price,
                    price + spread * symbol_point,
                    base_msc
                )
            ]

        # ----- 2 ticks ----
        if tick_count == 2:
            return [
                TicksGen.__tick__(bar["time"], bar["open"], bar["open"] + spread * symbol_point, base_msc),
                TicksGen.__tick__(bar["time"], bar["close"], bar["close"] + spread * symbol_point, base_msc + step),
            ]

        # ---- Support points ----
        support_points = TicksGen.build_support_points(bar)
        segments = len(support_points) - 1
        ticks_per_segment = tick_count // segments
        remainder = tick_count % segments

        t_index = 0
        for i in range(segments):
            start = support_points[i]
            end = support_points[i + 1]
            steps = ticks_per_segment + (1 if i < remainder else 0)

            prices = TicksGen.interpolate_prices(start, end, steps)
            for price in prices:
                ticks.append(
                    TicksGen.__tick__(
                        bar["time"],
                        float(price),
                        float(price + spread * symbol_point),
                        base_msc + t_index * step
                    )
                )
                t_index += 1

        return ticks[:tick_count]

    @staticmethod
    def generate_ticks_from_bars(
        bars: pl.DataFrame,
        symbol: str,
        symbol_point: float,
        out_dir: str,
        return_df: bool = False,
    ) -> pl.DataFrame:

        dfs: list[pl.DataFrame] = []

        # Ensure sorted (important!)
        bars = bars.sort("time")

        # Add year/month once
        bars = bars.with_columns([
            pl.col("time").dt.year().alias("year"),
            pl.col("time").dt.month().alias("month"),
        ])

        for (year, month), bars_chunk in bars.group_by(["year", "month"], maintain_order=True):

            if config.tester_logger is None:
                print(f"Generating ticks for {symbol}: {year}-{month:02d}")
            else:
                config.tester_logger.info(f"Generating ticks for {symbol}: {year}-{month:02d}")

            tick_rows = []

            for bar in bars_chunk.iter_rows(named=True):
                ticks = TicksGen.generate_ticks_from_bar(bar, symbol_point)
                if ticks:
                    tick_rows.extend(ticks)

            if not tick_rows:
                continue

            df = (
                pl.DataFrame(
                    tick_rows,
                    schema={
                        "time": pl.Datetime("us", time_zone="UTC"),
                        "bid": pl.Float64,
                        "ask": pl.Float64,
                        "last": pl.Float64,
                        "volume": pl.UInt64,
                        "time_msc": pl.Int64,
                        "flags": pl.Int8,
                        "volume_real": pl.UInt64,
                    },
                )
                .with_columns([
                    pl.col("time").dt.year().alias("year"),
                    pl.col("time").dt.month().alias("month"),
                ])
            )

            # Write monthly partition
            df.write_parquet(
                os.path.join(out_dir, symbol),
                partition_by=["year", "month"],
                mkdir=True,
            )

            if return_df:
                dfs.append(df)

        if return_df and dfs:
            return pl.concat(dfs, how="vertical")

        return pl.DataFrame()


