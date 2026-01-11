import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone

is_debug = True

HISTORY_DIR = "History"  # Folder name for storing history data

BARS_HISTORY_DIR = os.path.join(HISTORY_DIR, "Bars")
TICKS_HISTORY_DIR = os.path.join(HISTORY_DIR, "Ticks")

SIMULATED_TICKS_DIR = os.path.join(HISTORY_DIR, "Simulated", "Ticks")

# logger configurations

LOGS_DIR = "Logs"
os.makedirs(LOGS_DIR, exist_ok=True)

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

logging_level = logging.DEBUG if is_debug else logging.INFO

MT5_LOGS_DIR = os.path.join(LOGS_DIR, "MT5")
os.makedirs(MT5_LOGS_DIR, exist_ok=True)
mt5_logger = None

TESTER_LOGS_DIR = os.path.join(LOGS_DIR, "Tester")
os.makedirs(TESTER_LOGS_DIR, exist_ok=True)
tester_logger = None

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