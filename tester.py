import MetaTrader5 as mt5
import error_description
from datetime import datetime, timedelta, timezone
import secrets
import time
import pytz
import os
import numpy as np
import fnmatch
from typing import Optional, Tuple
from collections import namedtuple
import polars as pl
import utils
import config
from validators import TradeValidators, TesterConfigValidators
import sys
import ticks
import bars
import json
from tqdm import tqdm

if config.is_debug:
    np.set_printoptions(
        suppress=True,     # disable scientific notation
    )

class Tester:
    def __init__(self, tester_config: dict, mt5_instance: mt5):
        """MetaTrader 5-Like Strategy tester for the MetaTrader5-Python module.

        Args:
            configs_json (dict): a dictonary containing tester configurations
        Raises:
            RuntimeError: When one of the operation fails
        """
        
        # ---------------- validate all configs from a dictionary -----------------
        
        self.tester_config = TesterConfigValidators.parse_tester_configs(tester_config)
        
        # -------------------- initialize the Loggers ----------------------------
        
        self.mt5_instance = mt5_instance
        self.simulator_name = self.tester_config["bot_name"]
        
        config.mt5_logger = config.get_logger(self.simulator_name+".mt5", 
                                                 logfile=os.path.join(config.MT5_LOGS_DIR, f"{config.LOG_DATE}.log"), level=config.logging_level)
        
        config.tester_logger = config.get_logger(self.simulator_name+".tester", 
                                                    logfile=os.path.join(config.TESTER_LOGS_DIR, f"{config.LOG_DATE}.log"), level=config.logging_level)

        # -------------- Check if we are not on the tester mode ------------------
        
        self.IS_TESTER = not any(arg.startswith("--mt5") for arg in sys.argv) # are we on the strategy tester mode or live trading
        
        if not self.IS_TESTER:
            self.__GetLogger().debug("MT5 mode")
            
        # --------------- initialize ticks or bars data ----------------------------
        
        self.__GetLogger().info("Tester Initializing")
        
        self.TESTER_ALL_TICKS_INFO = []
        self.TESTER_ALL_BARS_INFO = []
        
        start_dt = self.tester_config["start_date"]
        end_dt = self.tester_config["end_date"]
        
        for symbol in self.tester_config["symbols"]:
            
            modelling = self.tester_config["modelling"]
            if modelling == "real_ticks":
                    
                ticks_obtained = ticks.fetch_historical_ticks(start_datetime=start_dt, end_datetime=end_dt, symbol=symbol)
                
                ticks_info = {
                    "symbol": symbol,
                    "ticks": ticks_obtained,
                    "size": ticks_obtained.height,
                    "counter": 0
                }
                
                self.TESTER_ALL_TICKS_INFO.append(ticks_info)
            
            elif modelling == "new_bar":
                
                bars_obtained = bars.fetch_historical_bars(symbol=symbol, 
                                                           timeframe=utils.TIMEFRAMES[self.tester_config["timeframe"]],
                                                           start_datetime=start_dt,
                                                           end_datetime=end_dt)
                
                bars_info = {
                    "symbol": symbol,
                    "bars": bars_obtained,
                    "size": bars_obtained.height,
                    "counter": 0
                }
                
                print("symbol: ",symbol, " bars received: ",bars_obtained.height)
                
                self.TESTER_ALL_BARS_INFO.append(bars_info)
                
        self.__GetLogger().info("Initialized")
        
        # ----------------- TradeOrder --------------------------
        
        self.TradeOrder = namedtuple(
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
        
        self.__orders_container__ = []
        self.__orders_history_container__ = []
        
        # ----------------- TradePosition -----------------
        
        self.TradePosition = namedtuple(
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
        
        self.__positions_container__ = []
        
        # ----------------- TradeDeal -----------------
        
        self.TradeDeal = namedtuple(
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
            ]
        )
        self.__deals_history_container__ = []

        # ----------------- AccountInfo -----------------

        self.AccountInfo = namedtuple(
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
        
        mt5_acc_info = mt5_instance.account_info()

        if mt5_acc_info is None:
            raise RuntimeError("Failed to obtain MT5 account info")

        deposit = self.tester_config["deposit"]
        
        self.__account_state_update(
            account_info=self.AccountInfo(
                # ---- identity / broker-controlled ----
                login=11223344,
                trade_mode=mt5_acc_info.trade_mode,
                leverage=int(self.tester_config["leverage"]),
                limit_orders=mt5_acc_info.limit_orders,
                margin_so_mode=mt5_acc_info.margin_so_mode,
                trade_allowed=mt5_acc_info.trade_allowed,
                trade_expert=mt5_acc_info.trade_expert,
                margin_mode=mt5_acc_info.margin_mode,
                currency_digits=mt5_acc_info.currency_digits,
                fifo_close=mt5_acc_info.fifo_close,

                # ---- simulator-controlled financials ----
                balance=deposit,                # simulator starting balance
                credit=mt5_acc_info.credit,
                profit=0.0,
                equity=deposit,
                margin=0.0,
                margin_free=deposit,
                margin_level=0.0,

                # ---- risk thresholds (copied from broker) ----
                margin_so_call=mt5_acc_info.margin_so_call,
                margin_so_so=mt5_acc_info.margin_so_so,
                margin_initial=mt5_acc_info.margin_initial,
                margin_maintenance=mt5_acc_info.margin_maintenance,

                # ---- rarely used but keep parity ----
                assets=mt5_acc_info.assets,
                liabilities=mt5_acc_info.liabilities,
                commission_blocked=mt5_acc_info.commission_blocked,

                # ---- descriptive ----
                name="John Doe",
                server="MetaTrader5-Simulator",
                currency=mt5_acc_info.currency,
                company=mt5_acc_info.company,
            )
        )
        
        self.symbol_info_cache: dict[str, namedtuple] = {}
        self.tick_cache: dict[str, namedtuple] = {}
        
        self.ORDER_TYPES = [
            self.mt5_instance.ORDER_TYPE_BUY,
            self.mt5_instance.ORDER_TYPE_SELL,
            self.mt5_instance.ORDER_TYPE_BUY_LIMIT,
            self.mt5_instance.ORDER_TYPE_SELL_LIMIT,
            self.mt5_instance.ORDER_TYPE_BUY_STOP,
            self.mt5_instance.ORDER_TYPE_SELL_STOP,
            self.mt5_instance.ORDER_TYPE_BUY_STOP_LIMIT,
            self.mt5_instance.ORDER_TYPE_SELL_STOP_LIMIT,
            self.mt5_instance.ORDER_TYPE_CLOSE_BY
            ]
        
        self.BUY_ACTIONS = {
            # self.mt5_instance.POSITION_TYPE_BUY,
            self.mt5_instance.ORDER_TYPE_BUY,
            self.mt5_instance.ORDER_TYPE_BUY_LIMIT,
            self.mt5_instance.ORDER_TYPE_BUY_STOP,
            self.mt5_instance.ORDER_TYPE_BUY_STOP_LIMIT,
        }

        self.SELL_ACTIONS = {
            # self.mt5_instance.POSITION_TYPE_SELL,
            self.mt5_instance.ORDER_TYPE_SELL,
            self.mt5_instance.ORDER_TYPE_SELL_LIMIT,
            self.mt5_instance.ORDER_TYPE_SELL_STOP,
            self.mt5_instance.ORDER_TYPE_SELL_STOP_LIMIT,
        }
    
    def __account_state_update(self, account_info: namedtuple):
        
        self.AccountInfo = account_info
        
    def account_info(self) -> namedtuple:
        
        """Gets info on the current trading account."""
        
        if self.IS_TESTER:
            return self.AccountInfo
        
        mt5_ac_info = self.mt5_instance.account_info()
        if  mt5_ac_info is None:
            self.__GetLogger().warning(f"Failed to obtain MT5 account info, MT5 Error = {self.mt5_instance.last_error()}")
            return
            
        return mt5_ac_info
    
    def symbol_info(self, symbol: str) -> namedtuple:    
        
        """Gets data on the specified financial instrument."""
        
        if symbol not in self.symbol_info_cache:
            info = self.mt5_instance.symbol_info(symbol)
            if info is None:
                return None
            
            self.symbol_info_cache[symbol] = info
        
        return self.symbol_info_cache[symbol]

    def symbol_info_tick(self, symbol: str) -> namedtuple:
        """Get the last tick for the specified financial instrument.

        Returns:
            namedtuple: 
        """
        
        if self.IS_TESTER:
            return self.tick_cache[symbol] 
        
        try:
            tick = self.mt5_instance.symbol_info_tick(symbol)
        except Exception as e:
            self.__GetLogger().warning(f"Failed. MT5 Error = {self.mt5_instance.last_error()}")
            
        return tick
    
    def TickUpdate(self, symbol: str, tick: namedtuple):
        self.tick_cache[symbol] = tick
    
    def __mt5_data_to_dicts(self, rates) -> list[dict]:
        
        if rates is None or len(rates) == 0:
            return []

        # structured numpy array from MT5
        if rates.dtype.names is not None:
            return [
                {name: r[name].item() if hasattr(r[name], "item") else r[name]
                for name in rates.dtype.names}
                for r in rates
            ]

        raise TypeError(f"Unsupported rates format: {type(rates)}, dtype={rates.dtype}")

    def copy_rates_from(self, symbol: str, timeframe: int, date_from: datetime, count: int) -> np.array:
        
        """Get bars from the MetaTrader 5 terminal starting from the specified date.

        Args:
            symbol: Financial instrument name, for example, "EURUSD". Required unnamed parameter.
            timeframe: Timeframe the bars are requested for. Set by a value from the TIMEFRAME enumeration. Required unnamed parameter.
            date_from: Date of opening of the first bar from the requested sample. Set by the 'datetime' object or as a number of seconds elapsed since 1970.01.01. Required unnamed parameter.

            count: Number of bars to receive. Required unnamed parameter.

        Returns:
            Returns bars as the numpy array with the named time, open, high, low, close, tick_volume, spread and real_volume columns. Return None in case of an error. The info on the error can be obtained using last_error().
        """
        
        date_from = utils.ensure_utc(date_from)
        
        if self.IS_TESTER:    
            
            # instead of getting data from MetaTrader 5, get data stored in our custom directories
            
            path = os.path.join(config.BARS_HISTORY_DIR, symbol, utils.TIMEFRAMES_REV[timeframe])
            lf = pl.scan_parquet(path)

            try:
                rates = (
                    lf
                    .filter(pl.col("time") <= date_from) # get data starting at the given date
                    .sort("time", descending=True) 
                    .limit(count) # limit the request to some bars
                    .select([
                        pl.col("time").dt.epoch("s").cast(pl.Int64).alias("time"),

                        pl.col("open"),
                        pl.col("high"),
                        pl.col("low"),
                        pl.col("close"),
                        pl.col("tick_volume"),
                        pl.col("spread"),
                        pl.col("real_volume"),
                    ]) # return only what's required 
                    .collect(engine="streaming") # the streming engine, doesn't store data in memory
                ).to_dicts()

                rates = np.array(rates)[::-1] # reverse an array so it becomes oldest -> newest
            
            except Exception as e:
                self.__GetLogger().warning(f"Failed to copy rates {e}")
                return np.array(dict())
        else:
            
            rates = self.mt5_instance.copy_rates_from(symbol, timeframe, date_from, count)
            rates = np.array(self.__mt5_data_to_dicts(rates))
            
            if rates is None:
                self.__GetLogger().warning(f"Failed to copy rates. MetaTrader 5 error = {self.mt5_instance.last_error()}")
                return np.array(dict())
            
        return rates
    
    def __GetLogger(self):
        if self.IS_TESTER:
            return config.tester_logger
        
        return config.mt5_logger
    
    def copy_rates_from_pos(self, symbol: str, timeframe: int, start_pos: int, count: int) -> np.array:
        
        """
        Get bars from the MetaTrader 5 terminal starting from the specified index.
        
        Parameters:
            symbol (str): Financial instrument name, for example, "EURUSD". Required unnamed parameter.
            timeframe (int): MT5 timeframe the bars are requested for.
            start_pos (int): Initial index of the bar the data are requested from. The numbering of bars goes from present to past. Thus, the zero bar means the current one. Required unnamed parameter.
            count (int): Number of bars to receive. Required unnamed parameter.

        Returns:
            Returns bars as the numpy array with the named time, open, high, low, close, tick_volume, spread and real_volume columns. Returns None in case of an error. The info on the error can be obtained using last_error().
        """
        
        tick = self.tick_cache[symbol]
        
        if tick is None or tick.time is None:
            self.__GetLogger().critical("Time information not found in the ticker, call the function 'TickUpdate' giving it the latest tick information")
            now = datetime.now(tz=timezone.utc)
        else:
            now = tick.time
        
        if self.IS_TESTER:    
            rates = self.copy_rates_from(symbol=symbol, 
                                        timeframe=timeframe,
                                        date_from=now+timedelta(seconds=utils.PeriodSeconds(timeframe)*start_pos),
                                        count=count)
        
        else:
            
            rates = self.mt5_instance.copy_rates_from_pos(symbol, timeframe, start_pos, count)
            rates = np.array(self.__mt5_data_to_dicts(rates))
            
            if rates is None:
                self.__GetLogger().warning(f"Failed to copy rates. MetaTrader 5 error = {self.mt5_instance.last_error()}")
                return np.array(dict())
            
        return rates
    
    def copy_rates_range(self, symbol: str, timeframe: int, date_from: datetime, date_to: datetime):
        """Get bars in the specified date range from the MetaTrader 5 terminal.

        Args:
            symbol (str): Financial instrument name, for example, "EURUSD". Required unnamed parameter.
            timeframe (int): Timeframe the bars are requested for. Set by a value from the TIMEFRAME enumeration. Required unnamed parameter.
            date_from (datetime): Date the bars are requested from. Set by the 'datetime' object or as a number of seconds elapsed since 1970.01.01. Bars with the open time >= date_from are returned. Required unnamed parameter.
            date_to (datetime): Date, up to which the bars are requested. Set by the 'datetime' object or as a number of seconds elapsed since 1970.01.01. Bars with the open time <= date_to are returned. Required unnamed parameter.
            
            Returns:
                Returns bars as the numpy array with the named time, open, high, low, close, tick_volume, spread and real_volume columns. Returns None in case of an error. The info on the error can be obtained using MetaTrader5.last_error().
        """
        
        date_from = utils.ensure_utc(date_from)
        date_to = utils.ensure_utc(date_to)
        
        if self.IS_TESTER:    
            
            # instead of getting data from MetaTrader 5, get data stored in our custom directories
            
            path = os.path.join(config.BARS_HISTORY_DIR, symbol, utils.TIMEFRAMES_REV[timeframe])
            lf = pl.scan_parquet(path)

            try:
                rates = (
                    lf
                    .filter(
                            (pl.col("time") >= pl.lit(date_from)) &
                            (pl.col("time") <= pl.lit(date_to))
                        ) # get bars between date_from and date_to
                    .sort("time", descending=True) 
                    .select([
                        pl.col("time").dt.epoch("s").cast(pl.Int64).alias("time"),

                        pl.col("open"),
                        pl.col("high"),
                        pl.col("low"),
                        pl.col("close"),
                        pl.col("tick_volume"),
                        pl.col("spread"),
                        pl.col("real_volume"),
                    ]) # return only what's required 
                    .collect(engine="streaming") # the streming engine, doesn't store data in memory
                ).to_dicts()

                rates = np.array(rates)[::-1] # reverse an array so it becomes oldest -> newest
            
            except Exception as e:
                self.__GetLogger().warning(f"Failed to copy rates {e}")
                return np.array(dict())
        else:
            
            rates = self.mt5_instance.copy_rates_range(symbol, timeframe, date_from, date_to)
            rates = np.array(self.__mt5_data_to_dicts(rates))
            
            if rates is None:
                self.__GetLogger().warning(f"Failed to copy rates. MetaTrader 5 error = {self.mt5_instance.last_error()}")
                return np.array(dict())
            
        return rates

    def __tick_flag_mask(self, flags: int) -> int:
        if flags == self.mt5_instance.COPY_TICKS_ALL:
            return (
                self.mt5_instance.TICK_FLAG_BID
                | self.mt5_instance.TICK_FLAG_ASK
                | self.mt5_instance.TICK_FLAG_LAST
                | self.mt5_instance.TICK_FLAG_VOLUME
                | self.mt5_instance.TICK_FLAG_BUY
                | self.mt5_instance.TICK_FLAG_SELL
            )

        mask = 0
        if flags & self.mt5_instance.COPY_TICKS_INFO:
            mask |= self.mt5_instance.TICK_FLAG_BID | self.mt5_instance.TICK_FLAG_ASK
        if flags & self.mt5_instance.COPY_TICKS_TRADE:
            mask |= self.mt5_instance.TICK_FLAG_LAST | self.mt5_instance.TICK_FLAG_VOLUME

        return mask

    def copy_ticks_from(self, symbol: str, date_from: datetime, count: int, flags: int=mt5.COPY_TICKS_ALL) -> np.array:
        
        """Get ticks from the MetaTrader 5 terminal starting from the specified date.

        Args:
            symbol(str): Financial instrument name, for example, "EURUSD". Required unnamed parameter.
            date_from(datetime): Date of opening of the first bar from the requested sample. Set by the 'datetime' object or as a number of seconds elapsed since 1970.01.01. Required unnamed parameter.

            count(int): Number of ticks to receive. Required unnamed parameter.
            flags(int): A flag to define the type of the requested ticks. COPY_TICKS_INFO – ticks with Bid and/or Ask changes, COPY_TICKS_TRADE – ticks with changes in Last and Volume, COPY_TICKS_ALL – all ticks. Flag values are described in the COPY_TICKS enumeration. Required unnamed parameter.

        Returns:
            Returns ticks as the numpy array with the named time, bid, ask, last and flags columns. The 'flags' value can be a combination of flags from the TICK_FLAG enumeration. Return None in case of an error. The info on the error can be obtained using last_error().
        """
        
        date_from = utils.ensure_utc(date_from)
        flag_mask = self.__tick_flag_mask(flags)

        if self.IS_TESTER:    
            
            path = os.path.join(config.TICKS_HISTORY_DIR, symbol)
            lf = pl.scan_parquet(path)

            try:
                ticks = (
                    lf
                    .filter(pl.col("time") >= pl.lit(date_from)) # get data starting at the given date
                    .filter((pl.col("flags") & flag_mask) != 0)
                    .sort(
                        ["time", "time_msc"],
                        descending=[False, False]
                    )
                    .limit(count) # limit the request to a specified number of ticks
                    .select([
                        pl.col("time").dt.epoch("s").cast(pl.Int64).alias("time"),

                        pl.col("bid"),
                        pl.col("ask"),
                        pl.col("last"),
                        pl.col("volume"),
                        pl.col("time_msc"),
                        pl.col("flags"),
                        pl.col("volume_real"),
                    ]) 
                    .collect(engine="streaming") # the streaming engine, doesn't store data in memory
                ).to_dicts()

                ticks = np.array(ticks)
            
            except Exception as e:
                self.__GetLogger().warning(f"Failed to copy ticks {e}")
                return np.array(dict())
        else:
            
            ticks = self.mt5_instance.copy_ticks_from(symbol, date_from, count, flags)
            ticks = np.array(self.__mt5_data_to_dicts(ticks))
            
            if ticks is None:
                self.__GetLogger().warning(f"Failed to copy ticks. MetaTrader 5 error = {self.mt5_instance.last_error()}")
                return np.array(dict())
            
        return ticks
    
    
    def copy_ticks_range(self, symbol: str, date_from: datetime, date_to: datetime, flags: int=mt5.COPY_TICKS_ALL) -> np.array:
        
        """Get ticks for the specified date range from the MetaTrader 5 terminal.

        Args:
            symbol(str): Financial instrument name, for example, "EURUSD". Required unnamed parameter.
            date_from(datetime): Date of opening of the first bar from the requested sample. Set by the 'datetime' object or as a number of seconds elapsed since 1970.01.01. Required unnamed parameter.

            date_to(datetime): Date, up to which the ticks are requested. Set by the 'datetime' object or as a number of seconds elapsed since 1970.01.01. Required unnamed parameter.
            flags(int): A flag to define the type of the requested ticks. COPY_TICKS_INFO – ticks with Bid and/or Ask changes, COPY_TICKS_TRADE – ticks with changes in Last and Volume, COPY_TICKS_ALL – all ticks. Flag values are described in the COPY_TICKS enumeration. Required unnamed parameter.

        Returns:
            Returns ticks as the numpy array with the named time, bid, ask, last and flags columns. The 'flags' value can be a combination of flags from the TICK_FLAG enumeration. Return None in case of an error. The info on the error can be obtained using last_error().
        """
        
        date_from = utils.ensure_utc(date_from)
        date_to = utils.ensure_utc(date_to)
        
        flag_mask = self.__tick_flag_mask(flags)

        if self.IS_TESTER:    
            
            path = os.path.join(config.TICKS_HISTORY_DIR, symbol)
            lf = pl.scan_parquet(path)

            try:
                ticks = (
                    lf
                    .filter(
                            (pl.col("time") >= pl.lit(date_from)) &
                            (pl.col("time") <= pl.lit(date_to))
                        ) # get ticks between date_from and date_to
                    .filter((pl.col("flags") & flag_mask) != 0)
                    .sort(
                        ["time", "time_msc"],
                        descending=[False, False]
                    )
                    .select([
                        pl.col("time").dt.epoch("s").cast(pl.Int64).alias("time"),

                        pl.col("bid"),
                        pl.col("ask"),
                        pl.col("last"),
                        pl.col("volume"),
                        pl.col("time_msc"),
                        pl.col("flags"),
                        pl.col("volume_real"),
                    ]) 
                    .collect(engine="streaming") # the streaming engine, doesn't store data in memory
                ).to_dicts()

                ticks = np.array(ticks)
            
            except Exception as e:
                self.__GetLogger().warning(f"Failed to copy ticks {e}")
                return np.array(dict())
        else:
            
            ticks = self.mt5_instance.copy_ticks_range(symbol, date_from, date_to, flags)
            ticks = np.array(self.__mt5_data_to_dicts(ticks))
            
            if ticks is None:
                self.__GetLogger().warning(f"Failed to copy ticks. MetaTrader 5 error = {self.mt5_instance.last_error()}")
                return np.array(dict())
            
        return ticks
    

    def orders_total(self) -> int:
        
        """Get the number of active orders.
        
        Returns (int): The number of active orders in either a simulator or MetaTrader 5
        """
        
        if self.IS_TESTER:
            return len(self.__orders_container__)
        try:
            total = self.mt5_instance.orders_total()
        except Exception as e:
            self.__GetLogger().error(f"MetaTrader5 error = {e}")
            return -1
        
        return total
    
    def orders_get(self, symbol: Optional[str] = None, group: Optional[str] = None, ticket: Optional[int] = None) -> namedtuple:
                
        """Get active orders with the ability to filter by symbol or ticket. There are three call options.

        Args:
            symbol (str | optional): Symbol name. If a symbol is specified, the ticket parameter is ignored.
            group (str | optional): The filter for arranging a group of necessary symbols. If the group is specified, the function returns only active orders meeting a specified criteria for a symbol name.
            
            ticket (int | optional): Order ticket (ORDER_TICKET).
        
        Returns:
        
            list: Returns info in the form of a named tuple structure (namedtuple). Return None in case of an error. The info on the error can be obtained using last_error().
        """
        
        if self.IS_TESTER:
            
            orders = self.__orders_container__

            # no filters → return all orders
            if symbol is None and group is None and ticket is None:
                return tuple(orders)

            # symbol filter (highest priority)
            if symbol is not None:
                return tuple(o for o in orders if o.symbol == symbol)

            # group filter
            if group is not None:
                return tuple(o for o in orders if fnmatch.fnmatch(o.symbol, group))

            # ticket filter
            if ticket is not None:
                return tuple(o for o in orders if o.ticket == ticket)

            return tuple()
        
        try:
            if symbol is not None:
                return self.mt5_instance.orders_get(symbol=symbol)

            if group is not None:
                return self.mt5_instance.orders_get(group=group)

            if ticket is not None:
                return self.mt5_instance.orders_get(ticket=ticket)

            return self.mt5_instance.orders_get()

        except Exception as e:
            self.__GetLogger().error(f"MetaTrader5 error = {e}")
            return None

    def positions_total(self) -> int:
        """Get the number of open positions in MetaTrader 5 client.

        Returns:
            int: number of positions
        """
        
        if self.IS_TESTER:
            return len(self.__positions_container__)        
        try:
            total = self.mt5_instance.positions_total()
        except Exception as e:
            self.__GetLogger().error(f"MetaTrader5 error = {e}")
            return -1
        
        return total

    def positions_get(self, symbol: Optional[str] = None, group: Optional[str] = None, ticket: Optional[int] = None) -> namedtuple:
        
        """Get open positions with the ability to filter by symbol or ticket. There are three call options.

        Args:
            symbol (str | optional): Symbol name. If a symbol is specified, the ticket parameter is ignored.
            group (str | optional): The filter for arranging a group of necessary symbols. Optional named parameter. If the group is specified, the function returns only positions meeting a specified criteria for a symbol name.
            
            ticket (int | optional): Position ticket -> https://www.mql5.com/en/docs/constants/tradingconstants/positionproperties#enum_position_property_integer
        
        Returns:
        
            list: Returns info in the form of a named tuple structure (namedtuple). Return None in case of an error. The info on the error can be obtained using last_error().
        """
        
        if self.IS_TESTER:
            
            positions = self.__positions_container__

            # no filters → return all positions
            if symbol is None and group is None and ticket is None:
                return tuple(positions)

            # symbol filter (highest priority)
            if symbol is not None:
                return tuple(o for o in positions if o.symbol == symbol)

            # group filter
            if group is not None:
                return tuple(o for o in positions if fnmatch.fnmatch(o.symbol, group))

            # ticket filter
            if ticket is not None:
                return tuple(o for o in positions if o.ticket == ticket)

            return tuple()
        
        try:
            if symbol is not None:
                return self.mt5_instance.positions_get(symbol=symbol)

            if group is not None:
                return self.mt5_instance.positions_get(group=group)

            if ticket is not None:
                return self.mt5_instance.positions_get(ticket=ticket)

            return self.mt5_instance.positions_get()

        except Exception as e:
            self.__GetLogger().error(f"MetaTrader5 error = {e}")
            return None

    def history_orders_total(self, date_from: datetime, date_to: datetime) -> int:
        
        # date range is a requirement
        
        if date_from is None or date_to is None:
            self.__GetLogger().error("date_from and date_to must be specified")
            return None
            
        date_from = utils.ensure_utc(date_from)
        date_to = utils.ensure_utc(date_to)
        
        if self.IS_TESTER:
        
            date_from_ts = int(date_from.timestamp())
            date_to_ts   = int(date_to.timestamp())
            
            return sum(
                        1
                        for o in self.__orders_history_container__
                        if date_from_ts <= o.time_setup <= date_to_ts
                    )

        try:
            total = self.mt5_instance.history_orders_total(date_from, date_to)
        except Exception as e:
            self.__GetLogger().error(f"MetaTrader5 error = {e}")
            return -1
        
        return total
    
    def history_orders_get(self, 
                           date_from: datetime,
                           date_to: datetime,
                           group: Optional[str] = None,
                           ticket: Optional[int] = None,
                           position: Optional[int] = None
                           ) -> namedtuple:
        
        if self.IS_TESTER:

            orders = self.__orders_history_container__

            # ticket filter (highest priority)
            if ticket is not None:
                return tuple(o for o in orders if o.ticket == ticket)

            # position filter
            if position is not None:
                return tuple(o for o in orders if o.position_id == position)

            # date range is a requirement  
            if date_from is None or date_to is None:
                self.__GetLogger().error("date_from and date_to must be specified")
                return None

            date_from_ts = int(utils.ensure_utc(date_from).timestamp())
            date_to_ts   = int(utils.ensure_utc(date_to).timestamp())

            filtered = (
                o for o in orders
                if date_from_ts <= o.time_setup <= date_to_ts
            ) # obtain orders that fall within this time range

            # optional group filter
            if group is not None:
                filtered = (
                    o for o in filtered
                    if fnmatch.fnmatch(o.symbol, group)
                )

            return tuple(filtered)
    
        try: # we are not on the strategy tester simulation
            
            if ticket is not None:
                return self.mt5_instance.history_orders_get(date_from, date_to, ticket=ticket)

            if position is not None:
                return self.mt5_instance.history_orders_get(date_from, date_to, position=position)

            if date_from is None or date_to is None:
                raise ValueError("date_from and date_to are required")

            date_from = utils.ensure_utc(date_from)
            date_to   = utils.ensure_utc(date_to)

            if group is not None:
                return self.mt5_instance.history_orders_get(
                    date_from, date_to, group=group
                )

            return self.mt5_instance.history_orders_get(date_from, date_to)

        except Exception as e:
            self.__GetLogger().error(f"MetaTrader5 error = {e}")
            return None
    
    def history_deals_total(self, date_from: datetime, date_to: datetime) -> int:
        """
        Get the number of deals in history within the specified date range.

        Args:
            date_from (datetime): Date the orders are requested from. Set by the 'datetime' object or as a number of seconds elapsed since 1970.01.01. 
            
            date_to (datetime, required): Date, up to which the orders are requested. Set by the 'datetime' object or as a number of seconds elapsed since 1970.01.01.
        
        Returns:
            An integer value.
        """

        if date_from is None or date_to is None:
            self.__GetLogger().error("date_from and date_to must be specified")
            return -1

        date_from = utils.ensure_utc(date_from)
        date_to   = utils.ensure_utc(date_to)

        if self.IS_TESTER:

            date_from_ts = int(date_from.timestamp())
            date_to_ts   = int(date_to.timestamp())

            return sum(
                1
                for d in self.__deals_history_container__
                if date_from_ts <= d.time <= date_to_ts
            )

        try:
            return self.mt5_instance.history_deals_total(date_from, date_to)

        except Exception as e:
            self.__GetLogger().error(f"MetaTrader5 error = {e}")
            return -1
    
    def history_deals_get(self,
                          date_from: datetime,
                          date_to: datetime,
                          group: Optional[str] = None,
                          ticket: Optional[int] = None,
                          position: Optional[int] = None
                        ) -> namedtuple:
        """Gets deals from trading history within the specified interval with the ability to filter by ticket or position.

        Args:
            date_from (datetime): Date the orders are requested from. Set by the 'datetime' object or as a number of seconds elapsed since 1970.01.01. 
            
            date_to (datetime, required): Date, up to which the orders are requested. Set by the 'datetime' object or as a number of seconds elapsed since 1970.01.01.
            
            group (str, optional):  The filter for arranging a group of necessary symbols. Optional named parameter. If the group is specified, the function returns only deals meeting a specified criteria for a symbol name.
            
            ticket (int, optional): Ticket of an order (stored in DEAL_ORDER) all deals should be received for. If not specified, the filter is not applied.
            
            position (int, optional): Ticket of a position (stored in DEAL_POSITION_ID) all deals should be received for. If not specified, the filter is not applied.

        Raises:
            ValueError: MetaTrader5 error

        Returns:
            namedtuple: information about deals
        """
                
        if self.IS_TESTER:

            deals = self.__deals_history_container__

            # ticket filter (highest priority)
            if ticket is not None:
                return tuple(d for d in deals if d.ticket == ticket)

            # position filter
            if position is not None:
                return tuple(d for d in deals if d.position_id == position)

            # date range is a requirement  
            if date_from is None or date_to is None:
                self.__GetLogger().error("date_from and date_to must be specified")
                return None

            date_from_ts = int(utils.ensure_utc(date_from).timestamp())
            date_to_ts   = int(utils.ensure_utc(date_to).timestamp())

            filtered = (
                d for d in deals
                if date_from_ts <= d.time <= date_to_ts
            ) # obtain orders that fall within this time range

            # optional group filter
            if group is not None:
                filtered = (
                    d for d in filtered
                    if fnmatch.fnmatch(d.symbol, group)
                )

            return tuple(filtered)
    
        try: # we are not on the strategy tester simulation
            
            if ticket is not None:
                return self.mt5_instance.history_deals_get(date_from, date_to, ticket=ticket)

            if position is not None:
                return self.mt5_instance.history_deals_get(date_from, date_to, position=position)

            if date_from is None or date_to is None:
                raise ValueError("date_from and date_to are required")

            date_from = utils.ensure_utc(date_from)
            date_to   = utils.ensure_utc(date_to)

            if group is not None:
                return self.mt5_instance.history_deals_get(
                    date_from, date_to, group=group
                )

            return self.mt5_instance.history_deals_get(date_from, date_to)

        except Exception as e:
            self.__GetLogger().error(f"MetaTrader5 error = {e}")
            return None
    
    def __generate_deal_ticket(self) -> int:
        return len(self.__deals_history_container__)+1
    
    def __generate_order_ticket(self) -> int:
        ts = int(time.time_ns())
        rand = secrets.randbits(6)
        return (ts << 6) | rand

    def __generate_position_ticket(self) -> int:
        ts = int(time.time_ns())
        rand = secrets.randbits(6)
        return (ts << 6) | rand

    def __calc_commission(self) -> float:
        """
        MT5-style commission calculation.
        """

        return -0.2
        
    def order_send(self, request: dict):
        """
        Sends a request to perform a trading operation from the terminal to the trade server. The function is similar to OrderSend in MQL5.
        """

        # -----------------------------------------------------
        
        if not self.IS_TESTER:
            result = self.mt5_instance.order_send(request)
            if result is None or result.retcode != self.mt5_instance.TRADE_RETCODE_DONE:
                self.__GetLogger().warning(f"MT5 failed: {error_description.error_description(self.mt5_instance.last_error()[0])}")
                return None
            return result
        
        # -------------------- Extract request -----------------------------
        
        action     = request.get("action")
        order_type = request.get("type", None)
        symbol     = request.get("symbol")
        volume     = float(request.get("volume", 0))
        price      = float(request.get("price", 0))
        sl         = float(request.get("sl", 0))
        tp         = float(request.get("tp", 0))
        ticket     = int(request.get("ticket", -1))
        
        # try:
        
        ticks_info = self.symbol_info_tick(symbol)
        symbol_info = self.symbol_info(symbol)
        ac_info = self.account_info()
        
        # except Exception as e:
        #     self.__GetLogger().critical(f"Failed to obtain necessary ticks, symbol, or account info: {e}")
        #     return None
        
        now = ticks_info.time
        ts  = int(now)
        msc = int(now * 1000)
        
        
        if order_type is not None:
            if order_type not in self.ORDER_TYPES:
                self.__GetLogger().critical("Invalid order type")
                return None 
    
        trade_validators = TradeValidators(symbol_info=symbol_info, 
                                           ticks_info=ticks_info, 
                                           logger=self.__GetLogger(), 
                                           mt5_instance=self.mt5_instance)

        # ------------------ MARKET DEAL (open or close) ------------------
        
        if action == self.mt5_instance.TRADE_ACTION_DEAL:
            
            def deal_reason_gen() -> int:
                eps = pow(10, -symbol_info.digits)
                if TradeValidators.price_equal(a=price, b=sl, eps=eps):
                    return self.mt5_instance.DEAL_REASON_SL
                
                if TradeValidators.price_equal(a=price, b=tp, eps=eps):
                    return self.mt5_instance.DEAL_REASON_TP
                
                return self.mt5_instance.DEAL_REASON_EXPERT
                
            # ---------- CLOSE POSITION ----------
            
            ticket = request.get("position", -1)
            if ticket != -1:
                pos = next(
                    (p for p in self.__positions_container__ if p.ticket == ticket),
                    None,
                )
                
                if not pos:
                    return {"retcode": self.mt5_instance.TRADE_RETCODE_INVALID}

                # validate position close request
                
                if pos.type == order_type:
                    self.__GetLogger().critical("Failed to close an order. Order type must be the opposite")
                    return None
                
                if order_type == self.mt5_instance.ORDER_TYPE_BUY: # For a sell order/position
                    
                    if not TradeValidators.price_equal(a=price, b=ticks_info.ask, eps=pow(10, -symbol_info.digits)):
                        self.__GetLogger().critical(f"Failed to close ORDER_TYPE_SELL. Price {price} is not equal to bid {ticks_info.bid}")
                        return None
                        
                elif order_type == self.mt5_instance.ORDER_TYPE_SELL: # For a buy order/position
                    if not TradeValidators.price_equal(a=price, b=ticks_info.bid, eps=pow(10, -symbol_info.digits)):
                        self.__GetLogger().critical(f"Failed to close ORDER_TYPE_BUY. Price {price} is not equal to bid {ticks_info.bid}")
                        return None
                        
                    
                self.__positions_container__.remove(pos)
                
                deal_ticket = self.__generate_deal_ticket()
                self.__deals_history_container__.append(
                    self.TradeDeal(
                        ticket=deal_ticket,
                        order=0,
                        time=ts,
                        time_msc=msc,
                        type=order_type,
                        entry=self.mt5_instance.DEAL_ENTRY_OUT,
                        magic=request.get("magic", 0),
                        position_id=pos.ticket,
                        reason=deal_reason_gen(),
                        volume=volume,
                        price=price,
                        commission=self.__calc_commission(),
                        swap=0,
                        profit=0,
                        fee=0,
                        symbol=symbol,
                        comment=request.get("comment", ""),
                        external_id="",
                    )
                )

                return {
                    "retcode": self.mt5_instance.TRADE_RETCODE_DONE,
                    "deal": deal_ticket,
                }
                
            # ---------- OPEN POSITION ----------
            
            # validate new stops 
            
            if not trade_validators.is_valid_sl(entry=price, sl=sl, order_type=order_type):
                return None
            if not trade_validators.is_valid_tp(entry=price, tp=tp, order_type=order_type):
                return None
            
            # validate the lotsize
            
            if not trade_validators.is_valid_lotsize(lotsize=volume):
                return None
            
            total_volume = sum([pos.volume for pos in self.__positions_container__]) + sum([order.volume_current for order in self.__orders_container__])
            if trade_validators.is_symbol_volume_reached(symbol_volume=total_volume, volume_limit=symbol_info.volume_limit):
                return None
            
            
            if not trade_validators.is_there_enough_money(margin_required=self.order_calc_margin(order_type=order_type, 
                                                                                                 symbol=symbol,
                                                                                                 volume=volume,
                                                                                                 price=price), 
                                                          free_margin=ac_info.margin_free):
                return None
            
            position_ticket = self.__generate_position_ticket()
            order_ticket    = self.__generate_order_ticket()
            deal_ticket     = self.__generate_deal_ticket()

            position = self.TradePosition(
                ticket=position_ticket,
                time=ts,
                time_msc=msc,
                time_update=ts,
                time_update_msc=msc,
                type=order_type,
                magic=request.get("magic", 0),
                identifier=position_ticket,
                reason=self.mt5_instance.DEAL_REASON_EXPERT,
                volume=volume,
                price_open=price,
                sl=sl,
                tp=tp,
                price_current=price,
                swap=0,
                profit=0,
                symbol=symbol,
                comment=request.get("comment", ""),
                external_id="",
            )
            
            self.__positions_container__.append(position)

            self.__deals_history_container__.append(
                self.TradeDeal(
                    ticket=deal_ticket,
                    order=order_ticket,
                    time=ts,
                    time_msc=msc,
                    type=order_type,
                    entry=self.mt5_instance.DEAL_ENTRY_IN,
                    magic=request.get("magic", 0),
                    position_id=position_ticket,
                    reason=deal_reason_gen(),
                    volume=volume,
                    price=price,
                    commission=self.__calc_commission(),
                    swap=0,
                    profit=0,
                    fee=0,
                    symbol=symbol,
                    comment=request.get("comment", ""),
                    external_id="",
                )
            )
            
            return {
                "retcode": self.mt5_instance.TRADE_RETCODE_DONE,
                "deal": deal_ticket,
                "order": order_ticket,
                "position": position_ticket,
            }
            
        # --------------------- PENDING order --------------------------
        
        elif action == self.mt5_instance.TRADE_ACTION_PENDING:
            
            if trade_validators.is_max_orders_reached(open_orders=len(self.__orders_container__), 
                                                      ac_limit_orders=ac_info.limit_orders):
                return None
            
            if not trade_validators.is_valid_sl(entry=price, sl=sl, order_type=order_type) or not trade_validators.is_valid_tp(entry=price, tp=tp, order_type=order_type):
                return None
            
            total_volume = sum([pos.volume for pos in self.__positions_container__]) + sum([order.volume_current for order in self.__orders_container__])
            if trade_validators.is_symbol_volume_reached(symbol_volume=total_volume, volume_limit=symbol_info.volume_limit):
                return None
            
            order_ticket = self.__generate_order_ticket()

            order = self.TradeOrder(
                    ticket=order_ticket,
                    time_setup=ts,
                    time_setup_msc=msc,
                    time_done=0,
                    time_done_msc=0,
                    time_expiration=request.get("expiration", 0),
                    type=order_type,
                    type_time=request.get("type_time", 0),
                    type_filling=request.get("type_filling", 0),
                    state=self.mt5_instance.ORDER_STATE_PLACED,
                    magic=request.get("magic", 0),
                    position_id=0,
                    position_by_id=0,
                    reason=self.mt5_instance.DEAL_REASON_EXPERT,
                    volume_initial=volume,
                    volume_current=volume,
                    price_open=price,
                    sl=sl,
                    tp=tp,
                    price_current=price,
                    price_stoplimit=request.get("price_stoplimit", 0),
                    symbol=symbol,
                    comment=request.get("comment", ""),
                    external_id="",
                )
                
            self.__orders_container__.append(order) 
            self.__orders_history_container__.append(order)
            
            return {
                "retcode": self.mt5_instance.TRADE_RETCODE_DONE,
                "order": order_ticket,
            }
            
        elif action == self.mt5_instance.TRADE_ACTION_SLTP:
            
            ticket = request.get("position", -1)

            pos = next((p for p in self.__positions_container__ if p.ticket == ticket), None)
            if not pos:
                return {"retcode": self.mt5_instance.TRADE_RETCODE_INVALID}

            # --- Correct reference prices ---
            entry_price = pos.price_open
            market_price = ticks_info.bid if pos.type == self.mt5_instance.POSITION_TYPE_BUY else ticks_info.ask

            # --- Validate SL / TP relative to ENTRY ---
            if sl > 0:
                if not trade_validators.is_valid_sl(entry=entry_price, sl=sl, order_type=pos.type):
                    return None

            if tp > 0:
                if not trade_validators.is_valid_tp(entry=entry_price, tp=tp, order_type=pos.type):
                    return None

            # --- Validate freeze level against MARKET ---
            if sl > 0:
                if not trade_validators.is_valid_freeze_level(entry=market_price, stop_price=sl, order_type=pos.type):
                    return None

            if tp > 0:
                if not trade_validators.is_valid_freeze_level(entry=market_price, stop_price=tp, order_type=pos.type):
                    return None

            # --- APPLY MODIFICATION ---
            idx = self.__positions_container__.index(pos)

            updated_pos = pos._replace(
                sl=sl,
                tp=tp,
                time_update=ts,
                time_update_msc=msc
            )

            self.__positions_container__[idx] = updated_pos

            return {"retcode": self.mt5_instance.TRADE_RETCODE_DONE}
        
            
        # -------------------- REMOVE pending order ------------------------
        
        elif action == self.mt5_instance.TRADE_ACTION_MODIFY: # Modifying pending orders

            ticket = request.get("order", -1)

            order = next(
                (o for o in self.__orders_container__ if o.ticket == ticket),
                None,
            )

            if not order:
                return {"retcode": self.mt5_instance.TRADE_RETCODE_INVALID}

            # validate new stops 
            
            if not trade_validators.is_valid_freeze_level(entry=price, stop_price=sl, order_type=order_type):
                return None
            if not trade_validators.is_valid_freeze_level(entry=price, stop_price=tp, order_type=order_type):
                return None
                
            # Modify ONLY allowed fields
            
            idx = self.__orders_container__.index(order)

            updated_order = order._replace(
                price_open=price,
                sl=sl,
                tp=tp,
                time_expiration = request.get("expiration", order.time_expiration),
                price_stoplimit = request.get("price_stoplimit", order.price_stoplimit)
            )

            self.__orders_container__[idx] = updated_order
            
            return {"retcode": self.mt5_instance.TRADE_RETCODE_DONE}
        
        elif action == self.mt5_instance.TRADE_ACTION_REMOVE:
            
            ticket = request.get("order", -1)
            
            self.__orders_container__ = [
                o for o in self.__orders_container__ if o.ticket != ticket
            ]
            
            return {"retcode": self.mt5_instance.TRADE_RETCODE_DONE}

        return {
            "retcode": self.mt5_instance.TRADE_RETCODE_INVALID,
            "comment": "Unsupported trade action",
        }
    
    def order_calc_profit(self, 
                        order_type: int,
                        symbol: str,
                        volume: float,
                        price_open: float,
                        price_close: float) -> float:
        """
        Return profit in the account currency for a specified trading operation.
        
        Args:
            order_type (int): The type of position taken, either 0 (buy) or 1 (sell).
            symbol (str): Financial instrument name. 
            volume (float):   Trading operation volume.
            price_open (float): Open Price.
            price_close (float): Close Price.
        """
        
        sym = self.symbol_info(symbol)
        
        if self.IS_TESTER:
            
            contract_size = sym.trade_contract_size
            
            BUY_ACTIONS = {
                self.mt5_instance.ORDER_TYPE_BUY,
                self.mt5_instance.ORDER_TYPE_BUY_LIMIT,
                self.mt5_instance.ORDER_TYPE_BUY_STOP,
                self.mt5_instance.ORDER_TYPE_BUY_STOP_LIMIT,
            }

            SELL_ACTIONS = {
                self.mt5_instance.ORDER_TYPE_SELL,
                self.mt5_instance.ORDER_TYPE_SELL_LIMIT,
                self.mt5_instance.ORDER_TYPE_SELL_STOP,
                self.mt5_instance.ORDER_TYPE_SELL_STOP_LIMIT,
            }
            
            # --- Determine direction ---
            if order_type in BUY_ACTIONS: #TODO: 
                direction = 1
            elif order_type in SELL_ACTIONS:
                direction = -1

            # --- Core profit calculation ---

            calc_mode = sym.trade_calc_mode
            price_delta = (price_close - price_open) * direction

            try:
                # ------------------ FOREX / CFD / STOCKS -----------------------
                if calc_mode in (
                    self.mt5_instance.SYMBOL_CALC_MODE_FOREX,
                    self.mt5_instance.SYMBOL_CALC_MODE_FOREX_NO_LEVERAGE,
                    self.mt5_instance.SYMBOL_CALC_MODE_CFD,
                    self.mt5_instance.SYMBOL_CALC_MODE_CFDINDEX,
                    self.mt5_instance.SYMBOL_CALC_MODE_CFDLEVERAGE,
                    self.mt5_instance.SYMBOL_CALC_MODE_EXCH_STOCKS,
                    self.mt5_instance.SYMBOL_CALC_MODE_EXCH_STOCKS_MOEX,
                ):
                    profit = price_delta * contract_size * volume

                # ---------------- FUTURES --------------------
                elif calc_mode in (
                    self.mt5_instance.SYMBOL_CALC_MODE_FUTURES,
                    self.mt5_instance.SYMBOL_CALC_MODE_EXCH_FUTURES,
                    # self.mt5_instance.SYMBOL_CALC_MODE_EXCH_FUTURES_FORTS,
                ):
                    tick_value = sym.trade_tick_value
                    tick_size = sym.trade_tick_size

                    if tick_size <= 0:
                        self.__GetLogger().critical("Invalid tick size")
                        return 0.0

                    profit = price_delta * volume * (tick_value / tick_size)

                # ---------- BONDS -------------------
                
                elif calc_mode in (
                    self.mt5_instance.SYMBOL_CALC_MODE_EXCH_BONDS,
                    self.mt5_instance.SYMBOL_CALC_MODE_EXCH_BONDS_MOEX,
                ):
                    face_value = sym.trade_face_value
                    accrued_interest = sym.trade_accrued_interest

                    profit = (
                        volume
                        * contract_size
                        * (price_close * face_value + accrued_interest)
                        - volume
                        * contract_size
                        * (price_open * face_value)
                    )

                # ------ COLLATERAL -------
                elif calc_mode == self.mt5_instance.SYMBOL_CALC_MODE_SERV_COLLATERAL:
                    liquidity_rate = sym.trade_liquidity_rate
                    market_price = (
                        self.tick_cache[symbol].ask if order_type == self.mt5_instance.ORDER_TYPE_BUY else self.tick_cache[symbol].bid
                    )

                    profit = (
                        volume
                        * contract_size
                        * market_price
                        * liquidity_rate
                    )

                else:
                    self.__GetLogger().critical(
                        f"Unsupported trade calc mode: {calc_mode}"
                    )
                    return 0.0

                return round(profit, 2)
                
            except Exception as e:
                self.__GetLogger().critical(f"Failed: {e}")
                return 0.0
            
        # if we are not on the strategy tester
            
        try:
            profit = self.mt5_instance.order_calc_profit(
                order_type,
                symbol,
                volume,
                price_open,
                price_close
            )
        
        except Exception as e:
            self.__GetLogger().critical(f"Failed to calculate profit of a position, MT5 error = {self.mt5_instance.last_error()}")
            return np.nan
        
        return profit
    
    def order_calc_margin(self, order_type: int, symbol: str, volume: float, price: float) -> float:
        """
        Return margin in the account currency to perform a specified trading operation.
        
        """

        if volume <= 0 or price <= 0:
            self.__GetLogger().error("order_calc_margin failed: invalid volume or price")
            return 0.0

        if not self.IS_TESTER:
            try:
                return round(self.mt5_instance.order_calc_margin(order_type, symbol, volume, price), 2)
            except Exception:
                self.__GetLogger().warning(f"Failed: MT5 Error = {self.mt5_instance.last_error()}")
                return 0.0

        # IS_TESTER = True
        sym = self.symbol_info(symbol)

        contract_size = sym.trade_contract_size
        leverage = max(self.account_info().leverage, 1)

        margin_rate = (
            sym.margin_initial
            if sym.margin_initial > 0
            else sym.margin_maintenance
        )
        
        if margin_rate <= 0: # if margin rate is zero set it to 1
            margin_rate = 1.0

        mode = sym.trade_calc_mode

        if mode == self.mt5_instance.SYMBOL_CALC_MODE_FOREX:
            margin = (volume * contract_size * price) / leverage

        elif mode == self.mt5_instance.SYMBOL_CALC_MODE_FOREX_NO_LEVERAGE:
            margin = volume * contract_size * price

        elif mode in (
            self.mt5_instance.SYMBOL_CALC_MODE_CFD,
            self.mt5_instance.SYMBOL_CALC_MODE_CFDINDEX,
            self.mt5_instance.SYMBOL_CALC_MODE_EXCH_STOCKS,
            self.mt5_instance.SYMBOL_CALC_MODE_EXCH_STOCKS_MOEX,
        ):
            margin = volume * contract_size * price * margin_rate

        elif mode == self.mt5_instance.SYMBOL_CALC_MODE_CFDLEVERAGE:
            margin = (volume * contract_size * price * margin_rate) / leverage

        elif mode in (
            self.mt5_instance.SYMBOL_CALC_MODE_FUTURES,
            self.mt5_instance.SYMBOL_CALC_MODE_EXCH_FUTURES,
            # self.mt5_instance.SYMBOL_CALC_MODE_EXCH_FUTURES_FORTS,
        ):
            margin = volume * sym.margin_initial

        elif mode in (
            self.mt5_instance.SYMBOL_CALC_MODE_EXCH_BONDS,
            self.mt5_instance.SYMBOL_CALC_MODE_EXCH_BONDS_MOEX,
        ):
            margin = (
                volume
                * contract_size
                * sym.trade_face_value
                * price
                / 100
            )

        elif mode == self.mt5_instance.SYMBOL_CALC_MODE_SERV_COLLATERAL:
            margin = 0.0

        else:
            self.__GetLogger().warning(f"Unknown calc mode {mode}, fallback margin formula used")
            margin = (volume * contract_size * price) / leverage

        return round(margin, 2)

        
    def __account_monitoring(self):
        
        unrealized_pl = 0
        total_margin = 0
        
        for pos in self.__positions_container__:
            
            unrealized_pl += pos.profit
            total_margin += self.order_calc_margin(order_type=pos.type, 
                                                   symbol=pos.symbol,
                                                   volume=pos.volume,
                                                   price=pos.price)
            
        self.AccountInfo._replace(
            profit=unrealized_pl,
            equity=self.AccountInfo.balance + unrealized_pl,
            margin=total_margin
        )
        
        self.AccountInfo._replace(
            margin_free=self.AccountInfo.equity - self.AccountInfo.margin,
            margin_level=self.AccountInfo.equity / self.AccountInfo.margin * 100 if self.AccountInfo.margin > 0 else 0
        )
    
    def __positions_monitoring(self):
        """
        Monitors all open positions:
        - updates profit
        - checks SL / TP
        - closes positions when hit
        """

        for pos in list(self.__positions_container__):

            tick = self.tick_cache[pos.symbol]

            # --- Determine close price and opposite order type ---
            if pos.type == self.mt5_instance.POSITION_TYPE_BUY:
                price = tick.bid
                close_type = self.mt5_instance.ORDER_TYPE_SELL
            elif pos.type == self.mt5_instance.POSITION_TYPE_SELL:
                price = tick.ask
                close_type = self.mt5_instance.ORDER_TYPE_BUY
            else:
                self.__GetLogger().warning("Unknown position type")
                continue

            # --- Update floating profit ---
            pos.profit = self.order_calc_profit(
                order_type=pos.type,
                symbol=pos.symbol,
                volume=pos.volume,
                price_open=pos.price_open,
                price_close=price
            )

            # --- Check SL / TP ---
            hit_tp = False
            hit_sl = False

            if pos.tp > 0:
                hit_tp = (
                    price >= pos.tp if pos.type == self.mt5_instance.POSITION_TYPE_BUY
                    else price <= pos.tp
                )

            if pos.sl > 0:
                hit_sl = (
                    price <= pos.sl if pos.type == self.mt5_instance.POSITION_TYPE_BUY
                    else price >= pos.sl
                )

            if not (hit_tp or hit_sl):
                continue

            # --- Close position ---
            request = {
                "action": self.mt5_instance.TRADE_ACTION_DEAL,
                "type": close_type,
                "symbol": pos.symbol,
                "price": price,
                "volume": pos.volume,
                "position": pos.ticket,
                "comment": "TP hit" if hit_tp else "SL hit",
            }

            self.order_send(request)

    def __pending_orders_monitoring(self):
        
        """
        Monitors pending orders:
        - handles expiration
        - triggers STOP / LIMIT orders correctly
        - converts them into market positions
        """

        for order in list(self.__orders_container__):

            symbol = order.symbol
            tick = self.tick_cache[symbol]

            # --- Expiration handling ---
            if order.time_expiration > 0 and tick.time >= order.time_expiration:
                self.__orders_container__.remove(order)
                continue

            triggered = False
            deal_type = None
            deal_price = None

            # -------- BUY ORDERS --------
            if order.type == self.mt5_instance.ORDER_TYPE_BUY_LIMIT:
                if tick.ask <= order.price:
                    triggered = True
                    deal_type = self.mt5_instance.ORDER_TYPE_BUY
                    deal_price = order.price

            elif order.type == self.mt5_instance.ORDER_TYPE_BUY_STOP:
                if tick.ask >= order.price:
                    triggered = True
                    deal_type = self.mt5_instance.ORDER_TYPE_BUY
                    deal_price = tick.ask

            elif order.type == self.mt5_instance.ORDER_TYPE_BUY_STOP_LIMIT:
                if tick.ask >= order.price:
                    # Convert to BUY LIMIT at stoplimit price
                    order.type = self.mt5_instance.ORDER_TYPE_BUY_LIMIT
                    order.price = order.price_stoplimit
                continue

            # -------- SELL ORDERS --------
            elif order.type == self.mt5_instance.ORDER_TYPE_SELL_LIMIT:
                if tick.bid >= order.price:
                    triggered = True
                    deal_type = self.mt5_instance.ORDER_TYPE_SELL
                    deal_price = order.price

            elif order.type == self.mt5_instance.ORDER_TYPE_SELL_STOP:
                if tick.bid <= order.price:
                    triggered = True
                    deal_type = self.mt5_instance.ORDER_TYPE_SELL
                    deal_price = tick.bid

            elif order.type == self.mt5_instance.ORDER_TYPE_SELL_STOP_LIMIT:
                if tick.bid <= order.price:
                    order.type = self.mt5_instance.ORDER_TYPE_SELL_LIMIT
                    order.price = order.price_stoplimit
                continue

            if not triggered:
                continue

            # ----- Execute pending order -----
            request = {
                "action": self.mt5_instance.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "type": deal_type,
                "price": deal_price,
                "sl": order.sl,
                "tp": order.tp,
                "volume": order.volume_current,
                "magic": order.magic,
                "comment": order.comment,
            }

            result = self.order_send(request)

            # ----- Remove pending order after successful execution -----
            if result and result.get("retcode") == self.mt5_instance.TRADE_RETCODE_DONE:
                self.__orders_container__.remove(order)
    
    def _bar_to_tick(self, symbol, bar):
        """
            Creates a synthetic tick from a bar (MT5-style).
            Uses OPEN price.
        """

        price = bar["open"] if isinstance(bar, dict) else bar[1]

        return {
            "time": bar["time"] if isinstance(bar, dict) else bar[0],
            "bid": price,
            "ask": price + self.symbol_info(symbol).spread,
            "last": price,
            "volume": 0,
            "flags": 0,
        }

    def OnTick(self, ontick_func):
        """Calls the assigned function upon the receival of new tick(s)

        Args:
            ontick_func (_type_): A function to be called on every tick
        """
        
        if not self.IS_TESTER:
            return

        modelling = self.tester_config["modelling"]
        if modelling == "real_ticks":
            
            total_ticks = sum(ticks_info["size"] for ticks_info in self.TESTER_ALL_TICKS_INFO)

            self.__GetLogger().debug(f"total number of ticks: {total_ticks}")

            with tqdm(total=total_ticks, desc="Tester Progress", unit="tick") as pbar:
                while True:
                    
                    self.__account_monitoring()
                    self.__positions_monitoring()
                    self.__pending_orders_monitoring()
                    
                    any_tick_processed = False

                    for ticks_info in self.TESTER_ALL_TICKS_INFO:

                        symbol = ticks_info["symbol"]
                        size = ticks_info["size"]
                        counter = ticks_info["counter"]

                        if counter >= size:
                            continue

                        current_tick = ticks_info["ticks"].row(counter)

                        self.TickUpdate(symbol=symbol, tick=current_tick)
                        ontick_func()

                        ticks_info["counter"] = counter + 1
                        any_tick_processed = True

                        pbar.update(1)

                    if not any_tick_processed:
                        break
                    
        elif modelling == "new_bar":
            
            bars_ = [bars_info["size"] for bars_info in self.TESTER_ALL_BARS_INFO]
            total_bars = sum(bars_)
            
            self.__GetLogger().debug(f"total number of bars: {total_bars}")

            with tqdm(total=total_bars, desc="Tester Progress", unit="bar") as pbar:
                while True:
                    
                    self.__account_monitoring()
                    self.__positions_monitoring()
                    self.__pending_orders_monitoring()
                    
                    any_bar_processed = False

                    for bars_info in self.TESTER_ALL_BARS_INFO:

                        symbol = bars_info["symbol"]
                        size = bars_info["size"]
                        counter = bars_info["counter"]

                        if counter >= size:
                            continue

                        current_tick = self._bar_to_tick(symbol=symbol, bar=bars_info["bars"].row(counter))
                        
                        # how can I get tick at the current bar???
                        
                        self.TickUpdate(symbol=symbol, tick=current_tick)
                        ontick_func()

                        bars_info["counter"] = counter + 1
                        any_bar_processed = True

                        pbar.update(1)

                    if not any_bar_processed:
                        break
            
                        
# The ontick function will be called afterwards by the user without them having to worry about updating ticks to the simulator

if __name__ == "__main__":
    
    mt5.initialize()
    
    try:
        with open(os.path.join('configs/tester.json'), 'r', encoding='utf-8') as file:
            # Deserialize the file data into a Python object
            data = json.load(file)
    except Exception as e:
        raise RuntimeError(e)

    sim = Tester(tester_config=data["tester"], mt5_instance=mt5)

    def ontick_function():
        pass
        # print("some trading actions")
        # exit()

    sim.OnTick(ontick_function)