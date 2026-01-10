
from typing import Dict
from datetime import datetime
import utils

def _validate_keys(raw_config):
    required_keys = {
        "bot_name",
        "symbols",
        "timeframe",
        "start_date",
        "end_date",
        "modelling",
        "deposit",
        "leverage",
    }

    provided_keys = set(raw_config.keys())

    missing = required_keys - provided_keys
    if missing:
        raise RuntimeError(f"Missing tester config keys: {missing}")

    extra = provided_keys - required_keys
    if extra:
        raise RuntimeError(f"Unknown tester config keys: {extra}")

def parse_tester_config(raw_config: Dict) -> Dict:
    cfg = raw_config

    # --- BOT NAME ---
    cfg.bot_name = str(cfg["bot_name"])

    # --- SYMBOLS ---
    if not isinstance(cfg["symbols"], list) or not cfg["symbols"]:
        raise RuntimeError("symbols must be a non-empty list")

    cfg.symbols = cfg["symbols"]

    # --- TIMEFRAME ---
    timeframe = cfg["timeframe"].upper()
    if timeframe not in utils.TIMEFRAMES.keys():
        raise RuntimeError(f"Invalid timeframe: {timeframe}")

    cfg.timeframe = timeframe

    # --- MODELLING ---
    
    modelling = cfg["modelling"].lower()

    VALID_MODELLING = {"ticks", "new_bar"}
    if modelling not in VALID_MODELLING:
        raise RuntimeError(f"Invalid modelling mode: {modelling}")

    cfg.modelling = modelling  # "ticks" | "new_bar"

    # --- DATE PARSING ---
    try:
        cfg.start_date = datetime.strptime(cfg["start_date"], "%d.%m.%Y %H:%M")
        cfg.end_date   = datetime.strptime(cfg["end_date"], "%d.%m.%Y %H:%M")
    except ValueError:
        raise RuntimeError("Date format must be: DD.MM.YYYY HH:MM")

    if cfg.start_date >= cfg.end_date:
        raise RuntimeError("start_date must be earlier than end_date")

    # --- DEPOSIT ---
    cfg.deposit = float(cfg["deposit"])
    if cfg.deposit <= 0:
        raise RuntimeError("deposit must be > 0")

    # --- LEVERAGE ---
    cfg.leverage = cfg._parse_leverage(cfg["leverage"])

def _parse_leverage(self, leverage: str) -> int:
    """
    Converts '1:100' -> 100
    """
    try:
        left, right = leverage.split(":")
        if left != "1":
            raise ValueError
        value = int(right)
        if value <= 0:
            raise ValueError
        return value
    except Exception:
        raise RuntimeError(f"Invalid leverage format: {leverage}")
