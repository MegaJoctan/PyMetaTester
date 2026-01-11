import sys
import MetaTrader5 as mt5
from calendar import monthrange
from datetime import datetime, timezone
from collections import namedtuple

def ensure_symbol(symbol: str) -> bool:
    info = mt5.symbol_info(symbol)
    if info is None:
        print(f"Symbol {symbol} not found")
        return False

    if not info.visible:
        if not mt5.symbol_select(symbol, True):
            print(f"Failed to select symbol {symbol}")
            return False
    return True

def bytestoMB(size_in_bytes):
    """Convert bytes to megabytes."""
    return size_in_bytes / (1024 * 1024)

def PeriodSeconds(period: int) -> int:
    """
    Convert MT5 timeframe to seconds.
    Correctly decodes MetaTrader 5 bit flags.
    """

    # Months (0xC000)
    if (period & 0xC000) == 0xC000:
        value = period & 0x3FFF
        return value * 30 * 24 * 3600

    # Weeks (0x8000)
    if (period & 0x8000) == 0x8000:
        value = period & 0x7FFF
        return value * 7 * 24 * 3600

    # Hours / Days (0x4000)
    if (period & 0x4000) == 0x4000:
        value = period & 0x3FFF
        return value * 3600

    # Minutes
    return period * 60

# timeframes map
TIMEFRAMES = {
    "M1": mt5.TIMEFRAME_M1,
    "M2": mt5.TIMEFRAME_M2,
    "M3": mt5.TIMEFRAME_M3,
    "M4": mt5.TIMEFRAME_M4,
    "M5": mt5.TIMEFRAME_M5,
    "M6": mt5.TIMEFRAME_M6,
    "M10": mt5.TIMEFRAME_M10,
    "M12": mt5.TIMEFRAME_M12,
    "M15": mt5.TIMEFRAME_M15,
    "M20": mt5.TIMEFRAME_M20,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H2": mt5.TIMEFRAME_H2,
    "H3": mt5.TIMEFRAME_H3,
    "H4": mt5.TIMEFRAME_H4,
    "H6": mt5.TIMEFRAME_H6,
    "H8": mt5.TIMEFRAME_H8,
    "H12": mt5.TIMEFRAME_H12,
    "D1": mt5.TIMEFRAME_D1,
    "W1": mt5.TIMEFRAME_W1,
    "MN1": mt5.TIMEFRAME_MN1,
}

# Reverse map
TIMEFRAMES_REV = {v: k for k, v in TIMEFRAMES.items()}

def month_bounds(dt: datetime):
    
    """Return (month_start, month_end) in UTC."""
    
    year, month = dt.year, dt.month
    start = datetime(year, month, 1, tzinfo=timezone.utc)

    last_day = monthrange(year, month)[1]
    end = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)

    return start, end

def ensure_utc(dt: datetime) -> datetime:
    """
    Ensure datetime is timezone-aware and in UTC.
    - Naive datetimes are assumed to be UTC
    - Aware datetimes are converted to UTC
    """
    if dt.tzinfo is None:
        # Naive → assume UTC
        return dt.replace(tzinfo=timezone.utc)

    # Aware → convert to UTC if needed
    return dt.astimezone(timezone.utc)

Tick = namedtuple(
    "Tick",
    [
        "time",
        "bid",
        "ask",
        "last",
        "volume",
        "time_msc",
        "flags",
        "volume_real",
    ]
)

def make_tick(
    time: datetime,
    bid: float,
    ask: float,
    last: float = 0.0,
    volume: int = 0,
    time_msc: int = 0,
    flags: int = -1,
    volume_real: float = 0.0,
    ) -> Tick:

    # MT5 semantics
    time  = ensure_utc(time)

    if time_msc == 0:
        if isinstance(time, datetime):
            time_msc = time.timestamp()
                
    time_sec = int(time.timestamp())
    time_msc = int(time.timestamp() * 1000)

    return Tick(
        time=time_sec,
        bid=float(bid),
        ask=float(ask),
        last=float(bid if last==0 else last),
        volume=int(volume),
        time_msc=time_msc,
        flags=int(flags),
        volume_real=int(volume_real),
    )

def make_tick_from_dict(data: dict) -> Tick:
    """
    Convert a dict into a Tick namedtuple.
    Accepts MT5-like, Polars, or JSON tick dictionaries.
    """

    # --- time handling ---
    time = data.get("time")

    if isinstance(time, (int, float)):
        # epoch seconds
        time = datetime.fromtimestamp(time, tz=timezone.utc)

    elif isinstance(time, datetime):
        time = ensure_utc(time)

    else:
        raise ValueError("Tick dictionary must contain a valid 'time' field")

    return make_tick(
        time=time,
        bid=data.get("bid", 0.0),
        ask=data.get("ask", 0.0),
        last=data.get("last", 0.0),
        volume=data.get("volume", 0),
        time_msc=data.get("time_msc", 0),
        flags=data.get("flags", -1),
        volume_real=data.get("volume_real", 0.0),
    )
