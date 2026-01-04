import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone

is_debug = True

HISTORY_DIR = "History"  # Folder name for storing history data

BARS_HISTORY_DIR = os.path.join(HISTORY_DIR, "Bars")
TICKS_HISTORY_DIR = os.path.join(HISTORY_DIR, "Ticks")

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

TESTER_LOGS_DIR = os.path.join(LOGS_DIR, "Tester")
os.makedirs(TESTER_LOGS_DIR, exist_ok=True)
tester_logger = get_logger("tester", logfile=os.path.join(TESTER_LOGS_DIR, f"{LOG_DATE}.log"), level=logging_level)

SIMULATOR_LOGS_DIR = os.path.join(LOGS_DIR, "Simulator")
os.makedirs(SIMULATOR_LOGS_DIR, exist_ok=True)
simulator_logger = get_logger("simulator", logfile=os.path.join(SIMULATOR_LOGS_DIR, f"{LOG_DATE}.log"), level=logging_level)
