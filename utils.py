import sys
import MetaTrader5 as mt5
from calendar import monthrange
from datetime import datetime, timezone

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