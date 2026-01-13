__version__ = '1.0.0'
__author__  = 'Omega Joctan Msigwa.'

from collections import namedtuple
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone
import MetaTrader5

IS_DEBUG = True

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

TradeOrder = namedtuple(
    "TradeOrder",
    [
        "ticket",
        "time_setup",
        "time_setup_msc",
        "time_done",
        "time_done_msc",
        "time_expiration",
        "type",
        "type_time",
        "type_filling",
        "state",
        "magic",
        "position_id",
        "position_by_id",
        "reason",
        "volume_initial",
        "volume_current",
        "price_open",
        "sl",
        "tp",
        "price_current",
        "price_stoplimit",
        "symbol",
        "comment",
        "external_id",
    ]
)


TradePosition = namedtuple(
    "TradePosition",
    [
        "ticket",
        "time",
        "time_msc",
        "time_update",
        "time_update_msc",
        "type",
        "magic",
        "identifier",
        "reason",
        "volume",
        "price_open",
        "sl",
        "tp",
        "price_current",
        "swap",
        "profit",
        "symbol",
        "comment",
        "external_id",
    ]
)


TradeDeal = namedtuple(
    "TradeDeal",
    [
        "ticket",        # DEAL_TICKET
        "order",         # DEAL_ORDER
        "time",          # DEAL_TIME (seconds)
        "time_msc",      # DEAL_TIME_MSC
        "type",          # DEAL_TYPE
        "entry",         # DEAL_ENTRY
        "magic",         # DEAL_MAGIC
        "position_id",   # DEAL_POSITION_ID
        "reason",        # DEAL_REASON
        "volume",        # DEAL_VOLUME
        "price",         # DEAL_PRICE
        "commission",    # DEAL_COMMISSION
        "swap",          # DEAL_SWAP
        "profit",        # DEAL_PROFIT
        "fee",           # DEAL_FEE
        "symbol",        # DEAL_SYMBOL
        "comment",       # DEAL_COMMENT
        "external_id",   # DEAL_EXTERNAL_ID
        "balance",       # Account balance
    ]
)


AccountInfo = namedtuple(
    "AccountInfo",
    [
        "login",
        "trade_mode",
        "leverage",
        "limit_orders",
        "margin_so_mode",
        "trade_allowed",
        "trade_expert",
        "margin_mode",
        "currency_digits",
        "fifo_close",
        "balance",
        "credit",
        "profit",
        "equity",
        "margin",
        "margin_free",
        "margin_level",
        "margin_so_call",
        "margin_so_so",
        "margin_initial",
        "margin_maintenance",
        "assets",
        "liabilities",
        "commission_blocked",
        "name",
        "server",
        "currency",
        "company",
    ]
)

SUPPORTED_TESTER_MODELLING = {
                "every_tick",
                "real_ticks",
                "new_bar",
                "1-minute-ohlc"
                }

REQUIRED_TESTER_CONFIG_KEYS = {
            "bot_name",
            "symbols",
            "timeframe",
            "start_date",
            "end_date",
            "modelling",
            "deposit",
            "leverage",
        }

DEAL_TYPE_MAP = {
    MetaTrader5.DEAL_TYPE_BUY: "BUY",
    MetaTrader5.DEAL_TYPE_SELL: "SELL",
    MetaTrader5.DEAL_TYPE_BALANCE: "BALANCE",
    MetaTrader5.DEAL_TYPE_CREDIT: "CREDIT",
    MetaTrader5.DEAL_TYPE_CHARGE: "CHARGE",
    MetaTrader5.DEAL_TYPE_CORRECTION: "CORRECTION",
    MetaTrader5.DEAL_TYPE_BONUS: "BONUS",
    MetaTrader5.DEAL_TYPE_COMMISSION: "COMMISSION",
    MetaTrader5.DEAL_TYPE_COMMISSION_DAILY: "COMMISSION DAILY",
    MetaTrader5.DEAL_TYPE_COMMISSION_MONTHLY: "COMMISSION MONTHLY",
    MetaTrader5.DEAL_TYPE_COMMISSION_AGENT_DAILY: "AGENT COMMISSION DAILY",
    MetaTrader5.DEAL_TYPE_COMMISSION_AGENT_MONTHLY: "AGENT COMMISSION MONTHLY",
    MetaTrader5.DEAL_TYPE_INTEREST: "INTEREST",
    MetaTrader5.DEAL_TYPE_BUY_CANCELED: "BUY CANCELED",
    MetaTrader5.DEAL_TYPE_SELL_CANCELED: "SELL CANCELED"
}


DEAL_ENTRY_MAP = {
    MetaTrader5.DEAL_ENTRY_IN: "IN",
    MetaTrader5.DEAL_ENTRY_OUT: "OUT",
    MetaTrader5.DEAL_ENTRY_INOUT: "INOUT"
}

ORDER_TYPE_MAP = {
    MetaTrader5.ORDER_TYPE_BUY: "Market Buy order",
    MetaTrader5.ORDER_TYPE_SELL: "Market Sell order",
    MetaTrader5.ORDER_TYPE_BUY_LIMIT: "Buy Limit pending order",
    MetaTrader5.ORDER_TYPE_SELL_LIMIT: "Sell Limit pending order",
    MetaTrader5.ORDER_TYPE_BUY_STOP: "Buy Stop pending order",
    MetaTrader5.ORDER_TYPE_SELL_STOP: "Sell Stop pending order",
    MetaTrader5.ORDER_TYPE_BUY_STOP_LIMIT: "Upon reaching the order price, a pending Buy Limit order is placed at the StopLimit price",
    MetaTrader5.ORDER_TYPE_SELL_STOP_LIMIT: "Upon reaching the order price, a pending Sell Limit order is placed at the StopLimit price",
    MetaTrader5.ORDER_TYPE_CLOSE_BY: "Order to close a position by an opposite one"
}


ORDER_STATE_MAP = {            
    MetaTrader5.ORDER_STATE_STARTED: "Order checked, but not yet accepted by broker",
    MetaTrader5.ORDER_STATE_PLACED: "Order accepted",
    MetaTrader5.ORDER_STATE_CANCELED: "Order canceled by client",
    MetaTrader5.ORDER_STATE_PARTIAL: "Order partially executed",
    MetaTrader5.ORDER_STATE_FILLED: "Order fully executed",
    MetaTrader5.ORDER_STATE_REJECTED: "Order rejected",
    MetaTrader5.ORDER_STATE_EXPIRED: "Order expired",
    MetaTrader5.ORDER_STATE_REQUEST_ADD: "Order is being registered (placing to the trading system)",
    MetaTrader5.ORDER_STATE_REQUEST_MODIFY: "Order is being modified (changing its parameters)",
    MetaTrader5.ORDER_STATE_REQUEST_CANCEL: "Order is being deleted (deleting from the trading system)"
}

        
BUY_ACTIONS = {
    MetaTrader5.ORDER_TYPE_BUY,
    MetaTrader5.ORDER_TYPE_BUY_LIMIT,
    MetaTrader5.ORDER_TYPE_BUY_STOP,
    MetaTrader5.ORDER_TYPE_BUY_STOP_LIMIT,
}

SELL_ACTIONS = {
    MetaTrader5.ORDER_TYPE_SELL,
    MetaTrader5.ORDER_TYPE_SELL_LIMIT,
    MetaTrader5.ORDER_TYPE_SELL_STOP,
    MetaTrader5.ORDER_TYPE_SELL_STOP_LIMIT,
}

TIMEFRAMES_MAP = {
    "M1": MetaTrader5.TIMEFRAME_M1,
    "M2": MetaTrader5.TIMEFRAME_M2,
    "M3": MetaTrader5.TIMEFRAME_M3,
    "M4": MetaTrader5.TIMEFRAME_M4,
    "M5": MetaTrader5.TIMEFRAME_M5,
    "M6": MetaTrader5.TIMEFRAME_M6,
    "M10": MetaTrader5.TIMEFRAME_M10,
    "M12": MetaTrader5.TIMEFRAME_M12,
    "M15": MetaTrader5.TIMEFRAME_M15,
    "M20": MetaTrader5.TIMEFRAME_M20,
    "M30": MetaTrader5.TIMEFRAME_M30,
    "H1": MetaTrader5.TIMEFRAME_H1,
    "H2": MetaTrader5.TIMEFRAME_H2,
    "H3": MetaTrader5.TIMEFRAME_H3,
    "H4": MetaTrader5.TIMEFRAME_H4,
    "H6": MetaTrader5.TIMEFRAME_H6,
    "H8": MetaTrader5.TIMEFRAME_H8,
    "H12": MetaTrader5.TIMEFRAME_H12,
    "D1": MetaTrader5.TIMEFRAME_D1,
    "W1": MetaTrader5.TIMEFRAME_W1,
    "MN1": MetaTrader5.TIMEFRAME_MN1,
}

# Reverse map
TIMEFRAMES_MAP_REVERSE = {v: k for k, v in TIMEFRAMES_MAP.items()}

def log_date_suffix():
    return datetime.now(timezone.utc).strftime("%Y%m%d")

LOG_DATE = log_date_suffix()

def get_logger(task_name: str, logfile: str, level=logging.INFO):
    """
        Returns a logger
    """
    logger_name = f"{task_name}"
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)

    if logger.handlers:
        return logger  # already configured

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | [%(filename)s:%(lineno)s - %(funcName)10s() ] => %(message)s"
    )

    file_handler = RotatingFileHandler(
        logfile,
        maxBytes=20 * 1024 * 1024,  # 20 MB
        backupCount=5,
        encoding="utf-8",
    )
    
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.propagate = False
    return logger

# Assigning loggers

logging_level = logging.DEBUG if IS_DEBUG else logging.INFO

CURVES_PLOT_INTERVAL_MINS = 1