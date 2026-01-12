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
    
def make_tick_from_tuple(data: tuple) -> Tick:
    """
    Convert a tuple-based tick into a Tick namedtuple.
    Extra fields at the end of the tuple are ignored.
    """

    if len(data) < 8:
        raise ValueError("Tick tuple must contain at least 8 elements")

    (
        time,
        bid,
        ask,
        last,
        volume,
        time_msc,
        flags,
        volume_real,
        *_
    ) = data

    # --- time handling ---
    if isinstance(time, (int, float)):
        time = datetime.fromtimestamp(time, tz=timezone.utc)
    elif isinstance(time, datetime):
        time = ensure_utc(time)
    else:
        raise ValueError("Invalid time field in tick tuple")

    return make_tick(
        time=time,
        bid=bid,
        ask=ask,
        last=last,
        volume=volume,
        time_msc=time_msc,
        flags=flags,
        volume_real=volume_real,
    )


DEAL_TYPE_MAP = {
    mt5.DEAL_TYPE_BUY: "BUY",
    mt5.DEAL_TYPE_SELL: "SELL",
    mt5.DEAL_TYPE_BALANCE: "BALANCE",
    mt5.DEAL_TYPE_CREDIT: "CREDIT",
    mt5.DEAL_TYPE_CHARGE: "CHARGE",
    mt5.DEAL_TYPE_CORRECTION: "CORRECTION",
    mt5.DEAL_TYPE_BONUS: "BONUS",
    mt5.DEAL_TYPE_COMMISSION: "COMMISSION",
    mt5.DEAL_TYPE_COMMISSION_DAILY: "COMMISSION DAILY",
    mt5.DEAL_TYPE_COMMISSION_MONTHLY: "COMMISSION MONTHLY",
    mt5.DEAL_TYPE_COMMISSION_AGENT_DAILY: "AGENT COMMISSION DAILY",
    mt5.DEAL_TYPE_COMMISSION_AGENT_MONTHLY: "AGENT COMMISSION MONTHLY",
    mt5.DEAL_TYPE_INTEREST: "INTEREST",
    mt5.DEAL_TYPE_BUY_CANCELED: "BUY CANCELED",
    mt5.DEAL_TYPE_SELL_CANCELED: "SELL CANCELED"
}


DEAL_ENTRY_MAP = {
    mt5.DEAL_ENTRY_IN: "IN",
    mt5.DEAL_ENTRY_OUT: "OUT",
    mt5.DEAL_ENTRY_INOUT: "INOUT"
}

ORDER_TYPE_MAP = {
    mt5.ORDER_TYPE_BUY: "Market Buy order",
    mt5.ORDER_TYPE_SELL: "Market Sell order",
    mt5.ORDER_TYPE_BUY_LIMIT: "Buy Limit pending order",
    mt5.ORDER_TYPE_SELL_LIMIT: "Sell Limit pending order",
    mt5.ORDER_TYPE_BUY_STOP: "Buy Stop pending order",
    mt5.ORDER_TYPE_SELL_STOP: "Sell Stop pending order",
    mt5.ORDER_TYPE_BUY_STOP_LIMIT: "Upon reaching the order price, a pending Buy Limit order is placed at the StopLimit price",
    mt5.ORDER_TYPE_SELL_STOP_LIMIT: "Upon reaching the order price, a pending Sell Limit order is placed at the StopLimit price",
    mt5.ORDER_TYPE_CLOSE_BY: "Order to close a position by an opposite one"
}


ORDER_STATE_MAP = {            
    mt5.ORDER_STATE_STARTED: "Order checked, but not yet accepted by broker",
    mt5.ORDER_STATE_PLACED: "Order accepted",
    mt5.ORDER_STATE_CANCELED: "Order canceled by client",
    mt5.ORDER_STATE_PARTIAL: "Order partially executed",
    mt5.ORDER_STATE_FILLED: "Order fully executed",
    mt5.ORDER_STATE_REJECTED: "Order rejected",
    mt5.ORDER_STATE_EXPIRED: "Order expired",
    mt5.ORDER_STATE_REQUEST_ADD: "Order is being registered (placing to the trading system)",
    mt5.ORDER_STATE_REQUEST_MODIFY: "Order is being modified (changing its parameters)",
    mt5.ORDER_STATE_REQUEST_CANCEL: "Order is being deleted (deleting from the trading system)"
}