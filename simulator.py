import MetaTrader5 as mt5
from Trade.SymbolInfo import CSymbolInfo
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
from validators import TradeValidators
from Trade.Trade import CTrade

if config.is_debug:
    np.set_printoptions(
        suppress=True,     # disable scientific notation
    )

class Simulator:
    def __init__(self, simulator_name: str, mt5_instance: mt5, deposit: float, leverage: str="1:100"):
        
        self.mt5_instance = mt5_instance
        self.simulator_name = simulator_name
        
        self.deviation_points = None
        self.filling_type = None
        self.id = 0
        self.m_symbol = CSymbolInfo(self.mt5_instance)
        
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

        self.__account_state_update(
            account_info=self.AccountInfo(
                # ---- identity / broker-controlled ----
                login=11223344,
                trade_mode=mt5_acc_info.trade_mode,
                leverage=int(leverage.split(":")[1]),
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

        self.IS_RUNNING = True # is the simulator running or stopped
        self.IS_TESTER = True # are we on the strategy tester mode or live trading 
        
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
        
    def Start(self, IS_TESTER: bool) -> bool: # simulator start
        
        self.IS_TESTER = IS_TESTER
    
    def Stop(self): # simulator stopped
        
        self.IS_RUNNING  = False
        pass #TODO:
    
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
        
        return config.simulator_logger
    
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
    

    def run_toolbox_gui(self):
        
        """
        Runs the simulator toolbox GUI.
        """
        
        self.toolbox_gui.update(self.account_info, self.positions_container, self.orders_container)
    
    def orders_total(self) -> int:
        
        """Get the number of active orders.
        
        Returns (int): The number of active orders in either a simulator or MetaTrader 5
        """
        
        if self.IS_TESTER:
            return len(self.orders_container)
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
                self.__GetLogger().warning(f"MT5 failed: {self.mt5_instance.last_error()}")
                return None
            return result

        # -------------------- Extract request -----------------------------
        
        action     = request.get("action")
        order_type = request.get("type")
        symbol     = request.get("symbol")
        volume     = float(request.get("volume", 0))
        price      = float(request.get("price", 0))
        sl         = float(request.get("sl", 0))
        tp         = float(request.get("tp", 0))
        ticket     = int(request.get("ticket", -1))
        
        ticks_info = self.tick_cache[symbol]
        symbol_info = self.symbol_info(symbol)
        ac_info = self.account_info()
        
        now = ticks_info.time
        ts  = int(now)
        msc = int(now * 1000)
        
        if order_type not in self.ORDER_TYPES:
            return {"retcode": self.mt5_instance.TRADE_RETCODE_INVALID}
        
        
        trade_validators = TradeValidators(symbol_info=symbol_info, 
                                           ticks_info=ticks_info, 
                                           logger=self.__GetLogger(), 
                                           mt5_instance=self.mt5_instance)
        
        # -------------------- REMOVE pending order ------------------------
        
        if action == self.mt5_instance.TRADE_ACTION_REMOVE:
            
            ticket = request.get("order", -1)
            
            self.__orders_container__ = [
                o for o in self.__orders_container__ if o.ticket != ticket
            ]
            
            return {"retcode": self.mt5_instance.TRADE_RETCODE_DONE}

        # --------------------- PENDING order --------------------------
        
        if action == self.mt5_instance.TRADE_ACTION_PENDING:
            
            if trade_validators.is_max_orders_reached(open_orders=len(self.__orders_container__), 
                                                      ac_limit_orders=ac_info.limit_orders):
                return None
            
            if not trade_validators.is_valid_sl(entry=price, sl=sl, order_type=order_type) or not trade_validators.is_valid_tp(entry=price, tp=tp, order_type=order_type):
                return None
            
            total_volume = sum([pos.volume for pos in self.__positions_container__]) + sum([order.volume for order in self.__orders_container__])
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
            
            total_volume = sum([pos.volume for pos in self.__positions_container__]) + sum([order.volume for order in self.__orders_container__])
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
            order.price_open      = price
            order.sl              = sl
            order.tp              = tp
            order.time_expiration = request.get("expiration", order.time_expiration)
            order.price_stoplimit = request.get("price_stoplimit", order.price_stoplimit)

            return {"retcode": self.mt5_instance.TRADE_RETCODE_DONE}
            
        elif action == self.mt5_instance.TRADE_ACTION_SLTP: # Modifying an open position
            
            ticket = request.get("position", -1)

            pos = next(
                (p for p in self.__positions_container__ if p.ticket == ticket),
                None,
            )

            if not pos:
                return {"retcode": self.mt5_instance.TRADE_RETCODE_INVALID}

            # Check for valid stoplosses and TPs ensuring they are not too close to the market
            
            if pos.type == self.mt5_instance.ORDER_TYPE_BUY:
                if not trade_validators.is_valid_sl(entry=ticks_info.bid, sl=sl, order_type=order_type) or not trade_validators.is_valid_tp(entry=ticks_info.bid, tp=tp, order_type=order_type):
                    return None
                
            elif pos.type == self.mt5_instance.ORDER_TYPE_SELL:
                if not trade_validators.is_valid_sl(entry=ticks_info.ask, sl=sl, order_type=order_type) or not trade_validators.is_valid_tp(entry=ticks_info.ask, tp=tp, order_type=order_type):
                    return None
            
            if not trade_validators.is_valid_freeze_level(entry=price, stop_price=sl, order_type=order_type):
                return None
            if not trade_validators.is_valid_freeze_level(entry=price, stop_price=sl, order_type=order_type):
                return None
            
            pos.sl = sl
            pos.tp = tp
            pos.time_update = ts
            pos.time_update_msc = msc

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
            
        self.AccountInfo(
            profit=unrealized_pl,
            equity=self.AccountInfo.balance + unrealized_pl,
            margin=total_margin
        )
        
        self.AccountInfo(
            margin_free=self.AccountInfo.equity - self.AccountInfo.margin,
            margin_level=self.AccountInfo.equity / self.AccountInfo.margin * 100 if self.AccountInfo.margin > 0 else 0
        )
        
        
    def __positions_monitoring(self, verbose: bool):
        
        # monitoring all open trades
        
        for pos in self.__positions_container__:
            
            # update price information on all positions
            
            tick = self.tick_cache[pos.symbol]
            price = tick.ask if pos.type == 0 else tick.bid
            
            # Monitor and calculate the profit of a position
            
            profit = self.order_calc_profit(order_type=pos.type,
                                            symbol=pos.symbol,
                                            volume=pos.volume,
                                            price_open=pos.price_open,
                                            price_close= (tick.ask if pos.type==0 else tick.bid))
            
            # Monitor the stoploss and takeprofit situation of positions
            
            if pos.tp == 0 and pos.sl == 0:
                continue
            
            if pos.type == self.mt5_instance.POSITION_TYPE_BUY:
                if price >= pos.tp: # Takeprofit is hit
                    # self.order_send
                    pass
                if price <= pos.sl:
                    pass
            elif pos.type == self.mt5_instance.POSITION_TYPE_SELL:
                if price <= pos.tp: # Takeprofit is hit
                    # self.order_send
                    pass
                if price >= pos.sl:
                    pass
            else:
                self.__GetLogger().warning(f"Unknown order type, It can be either 'buy' or 'sell'.")
                
    
    def __calculate_margin(self, symbol: str, volume: float, open_price: float, margin_rate=1.0) -> float:
        
        """
        Calculates margin requirement similar to MetaTrader5 based on the margin mode.
        """
        self.m_symbol.name(symbol)

        if not self.m_symbol.select():
            print(f"Margin calculation failed: MetaTrader5 error = {self.mt5_instance.last_error()}")
            return 0.0

        contract_size = self.m_symbol.trade_contract_size()
        leverage = self.leverage
        margin_mode = self.m_symbol.trade_calc_mode()

        print("Margin calculation mode: ",self.m_symbol.trade_calc_mode_description())
        
        tick_size = self.m_symbol.tick_size() or 0.0001
        tick_value = self.m_symbol.tick_value() or 0.0
        initial_margin = self.m_symbol.margin_initial() or 0.0
        face_value = self.m_symbol.trade_face_value() 
        
            
        if margin_mode == self.mt5_instance.SYMBOL_CALC_MODE_FOREX:
            margin = (volume * contract_size * margin_rate) / leverage

        elif margin_mode == self.mt5_instance.SYMBOL_CALC_MODE_FOREX_NO_LEVERAGE:
            margin = volume * contract_size * margin_rate

        elif margin_mode == self.mt5_instance.SYMBOL_CALC_MODE_CFD:
            margin = volume * contract_size * open_price * margin_rate

        elif margin_mode == self.mt5_instance.SYMBOL_CALC_MODE_CFDLEVERAGE:
            margin = (volume * contract_size * open_price * margin_rate) / leverage

        elif margin_mode == self.mt5_instance.SYMBOL_CALC_MODE_CFDINDEX:
            margin = volume * contract_size * open_price * tick_value / tick_size * margin_rate

        elif margin_mode in [self.mt5_instance.SYMBOL_CALC_MODE_EXCH_STOCKS, self.mt5_instance.SYMBOL_CALC_MODE_EXCH_STOCKS_MOEX]:
            margin = volume * contract_size * open_price * margin_rate

        elif margin_mode in [self.mt5_instance.SYMBOL_CALC_MODE_FUTURES, 
                             self.mt5_instance.SYMBOL_CALC_MODE_EXCH_FUTURES]:
            
            margin = volume * initial_margin * margin_rate

        elif margin_mode in [self.mt5_instance.SYMBOL_CALC_MODE_EXCH_BONDS, self.mt5_instance.SYMBOL_CALC_MODE_EXCH_BONDS_MOEX]:
            margin = volume * contract_size * face_value * open_price / 100

        elif margin_mode == self.mt5_instance.SYMBOL_CALC_MODE_SERV_COLLATERAL:
            margin = 0.0

        else:
            print(f"Unknown margin mode: {margin_mode}, falling back to default margin calc.")
            margin = (volume * contract_size * open_price) / leverage

        return margin

    def monitor_pending_orders(self):
        
        now = datetime.now(tz=pytz.UTC)
        
        expired_orders = []
        triggered_orders = []

        for order in self.orders_container: # loop through all orders
            
            expiration_mode = order.get("expiration_mode", "gtc")
            expiry_date = order.get("expiry_date")

            # Check for expiration based on mode
            if expiration_mode == "daily" or expiration_mode == "daily_excluding_stops":
                if expiry_date and now >= expiry_date:
                    
                    expired_orders.append(order)
                    continue  # Skip to next order

            self.m_symbol.name(symbol_name=order["symbol"])
            
            if not self.m_symbol.refresh_rates():
                continue

            ask = self.m_symbol.ask()
            bid = self.m_symbol.bid()
            open_price = order["open_price"]
            order_type = order["type"].lower()
            
            if order_type in ("buy limit", "buy stop"):
                order["price"] = self.m_symbol.ask()

            if order_type in ("sell limit", "sell stop"):
                order["price"] = self.m_symbol.bid()
                
            triggered = False # store the triggered condition of an order
            
            if order_type == "buy limit" and ask <= open_price:
                triggered = self.buy(order["volume"], order["symbol"], ask, order["sl"], order["tp"], order["comment"]) # open a buy position with credentials taken from an order

            elif order_type == "buy stop" and ask >= open_price:
                triggered = self.buy(order["volume"], order["symbol"], ask, order["sl"], order["tp"], order["comment"]) # open a buy position

            elif order_type == "sell limit" and bid >= open_price:
                triggered = self.sell(order["volume"], order["symbol"], bid, order["sl"], order["tp"], order["comment"]) # open a sell position

            elif order_type == "sell stop" and bid <= open_price:
                triggered = self.sell(order["volume"], order["symbol"], bid, order["sl"], order["tp"], order["comment"]) # open a sell position

            if triggered:
                triggered_orders.append(order) # add a triggerd order to the list 

        # Clean up expired and triggered orders
        for order in expired_orders + triggered_orders:
            
            if order in self.orders_container:
                self.orders_container.remove(order)

