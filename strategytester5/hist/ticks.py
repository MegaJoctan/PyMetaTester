import MetaTrader5 as mt5
from datetime import datetime, timezone, timedelta
import os
import polars as pl
from strategytester5 import *

def ticks_to_polars(ticks):
    return pl.DataFrame({
        "time": ticks["time"],
        "bid": ticks["bid"],
        "ask": ticks["ask"],
        "last": ticks["last"],
        "volume": ticks["volume"],
        "time_msc": ticks["time_msc"],
        "flags": ticks["flags"],
        "volume_real": ticks["volume_real"],
    })
    
def fetch_historical_ticks(start_datetime: datetime, 
                        end_datetime: datetime,
                        symbol: str) -> pl.DataFrame:
    """
    if not ensure_symbol(symbol=symbol):
        if LOGGER is None:
            print(f"Symbol {symbol} not available")
        else:
            LOGGER.warning(f"Symbol {symbol} not available")
        return pl.DataFrame()
    """

    start_datetime = ensure_utc(start_datetime)
    end_datetime   = ensure_utc(end_datetime)

    current = start_datetime.replace(day=1, hour=0, minute=0, second=0)

    dfs: list[pl.DataFrame] = []

    while True:
        month_start, month_end = month_bounds(current)

        if (
            month_start.year == end_datetime.year and
            month_start.month == end_datetime.month
        ):
            month_end = end_datetime

        if month_start > end_datetime:
            break
        
        if LOGGER is None:
            print(f"Processing ticks for {symbol}: {month_start:%Y-%m-%d} -> {month_end:%Y-%m-%d}")
        else:
            LOGGER.info(f"Processing ticks for {symbol}: {month_start:%Y-%m-%d} -> {month_end:%Y-%m-%d}")

        ticks = mt5.copy_ticks_range(
            symbol,
            month_start,
            month_end,
            mt5.COPY_TICKS_ALL
        )

        if ticks is None or len(ticks) == 0:
            
            if LOGGER is None:
                print(f"No ticks for {symbol} {month_start:%Y-%m}")
            else:
                LOGGER.warning(f"No ticks for {symbol} {month_start:%Y-%m}")
                
            current = (month_start + timedelta(days=32)).replace(day=1)
            continue

        df = ticks_to_polars(ticks)

        df = df.with_columns(
            pl.from_epoch("time", time_unit="s")
                .dt.replace_time_zone("utc")
                .alias("time")
        )

        df = df.with_columns([
            pl.col("time").dt.year().alias("year"),
            pl.col("time").dt.month().alias("month"),
        ])

        # Save monthly partitions
        df.write_parquet(
            os.path.join("Ticks", symbol),
            partition_by=["year", "month"],
            mkdir=True
        )

        # if config.is_debug: 
        #     print(df.head(-10))
            
        dfs.append(df)

        current = (month_start + timedelta(days=32)).replace(day=1)

    if not dfs:
        return pl.DataFrame()

    return pl.concat(dfs, how="vertical")
    
"""
if __name__ == "__main__":
    
    if not mt5.initialize():
        print(f"Failed to Initialize MetaTrader5. Error = {mt5.last_error()}")
        mt5.shutdown()
        quit()
    
    symbol = "EURUSD"
    start_dt = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    end_dt = datetime(2025, 12, 1, 1, 0, tzinfo=timezone.utc)
    
    fetch_historical_ticks(start_datetime=start_dt, end_datetime=end_dt, symbol=symbol)
    fetch_historical_ticks(start_datetime=start_dt, end_datetime=end_dt, symbol= "GBPUSD")
    
    path = os.path.join(config.TICKS_HISTORY_DIR, symbol)
    lf = pl.scan_parquet(path)

    jan_2024 = (
        lf
        .filter(
            (pl.col("year") == 2024) &
            (pl.col("month") == 1)
        )
        .collect(engine="streaming")
    )

    print("January 2024:\n", jan_2024.head(-10))
    print(
        jan_2024.select([
            pl.col("time").min().alias("time_min"),
            pl.col("time").max().alias("time_max")
        ])
    )
    
    mt5.shutdown()
"""