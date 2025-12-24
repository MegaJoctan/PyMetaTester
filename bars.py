import MetaTrader5 as mt5
from datetime import datetime, timezone, timedelta
import os
import utils
import config
import pandas as pd
import polars as pl

def bars_to_polars(bars):
    
    return pl.DataFrame({
        "time": bars["time"],
        "open": bars["open"],
        "high": bars["high"],
        "low": bars["low"],
        "close": bars["close"],
        "tick_volume": bars["tick_volume"],
        "spread": bars["spread"],
        "real_volume": bars["real_volume"],
    })
    
def fetch_historical_bars(symbol: str, 
                          timeframe: int,
                          start_datetime: datetime,
                          end_datetime: datetime):
    """
    Fetch historical bar data for a given symbol and timeframe, forward in time.
    Saves data to a single Parquet file in append mode.
    """
    if not utils.ensure_symbol(symbol=symbol):
        print(f"Symbol {symbol} not available")
        return
    
    current = start_datetime.replace(day=1, hour=0, minute=0, second=0)

    while True:
        month_start, month_end = utils.month_bounds(current)

        # Cap last month to end_date
        if (
            month_start.year == end_datetime.year and
            month_start.month == end_datetime.month
        ):
            month_end = end_datetime

        # Stop condition
        if month_start > end_datetime:
            break

        print(f"Processing {month_start:%Y-%m-%d} -> {month_end:%Y-%m-%d}")

        # --- fetch data here ---
        rates = mt5.copy_rates_range(
            symbol,
            timeframe,
            month_start,
            month_end
        )

        if rates is not None and len(rates) > 0:
            
            df = bars_to_polars(rates)

            df = df.with_columns([
                pl.from_epoch("time", time_unit="s").dt.replace_time_zone("utc").alias("time")
            ])

            df = df.with_columns([
                pl.col("time").dt.year().alias("year"),
                pl.col("time").dt.month().alias("month"),
            ])
            
            tf_name = utils.TIMEFRAMES_REV[timeframe]
            df.write_parquet(
                os.path.join(config.BARS_HISTORY_DIR, symbol, tf_name),
                partition_by=["year", "month"],
                mkdir=True
            )

            print(df.head(-10))
            
        # Advance to next month safely
        current = (month_start + timedelta(days=32)).replace(day=1)

        

if __name__ == "__main__":
    
    if not mt5.initialize():
        print(f"Failed to Initialize MetaTrader5. Error = {mt5.last_error()}")
        mt5.shutdown()
        quit()
    
    start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
    end_date = datetime(2025, 1, 10, tzinfo=timezone.utc)
    
    # fetch_historical_bars("XAUUSD", mt5.TIMEFRAME_M1, start_date, end_date)
    # fetch_historical_bars("EURUSD", mt5.TIMEFRAME_M5, start_date, end_date)
    # fetch_historical_bars("GBPUSD", mt5.TIMEFRAME_M5, start_date, end_date)
    
    # read polaris dataframe and print the head for both symbols

    symbol = "GBPUSD"
    timeframe = utils.TIMEFRAMES_REV[mt5.TIMEFRAME_M5]
    
    path = os.path.join(config.BARS_HISTORY_DIR, symbol, timeframe)
    
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
