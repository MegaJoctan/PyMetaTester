import MetaTrader5 as mt5
from Trade.SymbolInfo import CSymbolInfo
from datetime import datetime, timedelta, timezone
import pytz
import sqlite3
import os
import numpy as np
from types import SimpleNamespace
import polars as pl
import utils
import config
from toolbox_gui import SimToolboxGUI

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
        
        self.leverage = int(leverage.split(":")[1])

        self.account_info = {
            "balance" : deposit,
            "equity": deposit,
            "profit": 0,
            "margin": 0,
            "free_margin": 0,
            "margin_level": 0,
            "leverage": self.leverage
        }
        
        # Position's information
        
        self.position_info = {
            "time": None,
            "id" : 0,
            "magic": 0,
            "symbol": None,
            "type": None,
            "volume": 0.0,
            "open_price": 0.0,
            "price": 0.0,
            "sl": 0.0,
            "tp": 0.0,
            "commission": 0.0,
            "margin_required": 0.0,
            "fee": 0.0,
            "swap": 0.0,
            "profit": 0,
            "comment": 0
        }
        
        # Order's information
        
        self.order_info = self.position_info.copy()
        self.order_info["expiry_date"] = datetime
        self.order_info["expiration_mode"] = ""
        
        # Deal's information

        self.deal_info = self.position_info.copy()
        
        self.deal_info["reason"] = None # This is used to store the reason why the trade was closed, e.g. "Take Profit", "Stop Loss", etc.
        self.deal_info["direction"] = None # The only difference btn an open trade and a closed one is that the closed one has a direction showing if at that instance it was opened or closed in history
        
        
        # Containers for positions, orders, and deals
                
        self.positions_container = [] # a list for storing all opened trades
        self.deals_container = [] # a list for storing all deals 
        self.orders_container = []
        
        # Database for trade history
        
        self.sim_folder = "Simulations"
        
        os.makedirs(self.sim_folder, exist_ok=True)  # Ensure the simulations path exists
        
        # Create the database file name
        
        self.history_db_name = os.path.join(self.sim_folder, self.simulator_name+".db")
        self._create_deals_db(self.history_db_name)

        self.toolbox_gui = SimToolboxGUI()  # Initialize the GUI

        self.IS_RUNNING = True # is the simulator running or stopped
        self.IS_TESTER = True # are we on the strategy tester mode or live trading 
        
        self.symbol_info_cache: dict[str, object] = {}
        self.tick = None
        
    def Start(self, IS_TESTER: bool) -> bool: # simulator start
        
        self.IS_TESTER = IS_TESTER
    
    def Stop(self): # simulator stopped
        self.IS_RUNNING = False
        pass
    
    def symbol_info(self, symbol: str) -> dict:    
        
        if symbol not in self.symbol_info_cache:
            info = self.mt5_instance.symbol_info(symbol)
            if info is None:
                return None
            
            self.symbol_info_cache[symbol] = info
        
        return self.symbol_info_cache[symbol]

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
    
    def TickUpdate(self, tick: dict):
        self.tick = tick
    
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
        
        if self.tick is None or self.tick.time is None:
            self.__GetLogger().critical("Time information not found in the ticker, call the function 'TickUpdate' giving it the latest tick information")
            now = datetime.now(tz=timezone.utc)
        else:
            now = self.tick.time
        
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
        if flags == mt5.COPY_TICKS_ALL:
            return (
                mt5.TICK_FLAG_BID
                | mt5.TICK_FLAG_ASK
                | mt5.TICK_FLAG_LAST
                | mt5.TICK_FLAG_VOLUME
                | mt5.TICK_FLAG_BUY
                | mt5.TICK_FLAG_SELL
            )

        mask = 0
        if flags & mt5.COPY_TICKS_INFO:
            mask |= mt5.TICK_FLAG_BID | mt5.TICK_FLAG_ASK
        if flags & mt5.COPY_TICKS_TRADE:
            mask |= mt5.TICK_FLAG_LAST | mt5.TICK_FLAG_VOLUME

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
                    ]) # return only what's required 
                    .collect(engine="streaming") # the streming engine, doesn't store data in memory
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

    def run_toolbox_gui(self):
        
        """
        Runs the simulator toolbox GUI.
        """
        
        self.toolbox_gui.update(self.account_info, self.positions_container, self.orders_container)
    
    def get_positions(self) -> list:

        return [pos for pos in self.positions_container]
    
    def get_orders(self) -> list:

        return [order for order in self.orders_container]

    def get_deals(self, start_time: datetime = None, end_time: datetime = None, from_db: bool = False) -> list:
        
        if start_time is None or end_time is None:
            raise ValueError("Both start_time and end_time must be provided")
        
        # Auto-swap if dates are in the wrong order
        if start_time > end_time:
            print("Swapping start_time and end_time for correct comparison.")
            start_time, end_time = end_time, start_time

        if from_db:
            conn = sqlite3.connect(self.history_db_name)
            cursor = conn.cursor()

            # Ensure ISO format for datetime strings
            start_str = start_time.isoformat()
            end_str = end_time.isoformat()

            cursor.execute('''
                SELECT * FROM closed_deals
                WHERE time BETWEEN ? AND ?
            ''', (start_str, end_str))

            columns = [col[0] for col in cursor.description]
            results = cursor.fetchall()
            conn.close()

            # Convert result rows into dicts
            return [dict(zip(columns, row)) for row in results]

        else:
            return [
                deal for deal in self.deals_container
                if start_time <= deal["time"] <= end_time
            ]

    def _create_deals_db(self, db_name: str):
        
        """
        Creates a SQLite database to store trade history and account information.
        
        Args:
            db_name (str): The name of the database file.
        """
        
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        # Create tables if they do not exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS closed_deals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time TEXT,
                magic INTEGER,
                symbol TEXT,
                type TEXT,
                direction TEXT,
                volume REAL,
                price REAL,
                sl REAL,
                tp REAL,
                commission REAL,
                margin_required REAL,
                fee REAL,
                swap REAL,
                profit REAL,
                comment TEXT,
                reason TEXT
            )
        ''')
        
        conn.commit() 
        conn.close()

    def _save_deal(self, deal: dict, db_name: str):
        """
            Saves a closed deal to the SQLite database.
        """
        
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO closed_deals (
                time, magic, symbol, type, direction, volume, price, sl, tp,
                commission, margin_required, fee, swap, profit, comment, reason
            ) VALUES (
                :time, :magic, :symbol, :type, :direction, :volume, :price, :sl, :tp,
                :commission, :margin_required, :fee, :swap, :profit, :comment, :reason
            );
        """, deal)

        conn.commit()
        conn.close()
    
    def set_magicnumber(self, magic_number: int):
        
        self.magic_number = magic_number
        
    def set_deviation_in_points(self, deviation_points: int):
        
        self.deviation_points = deviation_points
        
    """
    def set_filling_type_by_symbol(self, symbol: int):
        
        self.filling_type = self._get_type_filling(symbol)
        
        if self.filling_type == -1:
            print(f"Failed to set filling type for '{symbol}'")
    """
        
    def _calculate_profit(self, action: str, symbol: str, entry_price: float, exit_price: float, lotsize: float) -> float:
        
        """
        Calculate profit based on entry and exit prices, lot size, tick size, and tick value.
        
        Args:
            action (str): The action taken, either 'buy' or 'sell'.
            entry_price (float): The price at which the position was opened.
            exit_price (float): The price at which the position was closed.
            lotsize (float): The size of the lot in terms of contract units.
        """

        if action != "buy" and action != "sell":
            print(f"Unknown order type, It can be either 'buy' or 'sell'. Received '{action}' instead.")
            return 0
        
        order_type = self.mt5_instance.ORDER_TYPE_BUY if action == "buy" else self.mt5_instance.ORDER_TYPE_SELL
        
        profit = self.mt5_instance.order_calc_profit(
            order_type,
            symbol,
            lotsize,
            entry_price,
            exit_price
        )
        
        return profit
        
    def market_update(self, ask: float, bid: float, time: datetime):
        """
        self.ask = ask
        self.bid = bid
        self.time = time
        """
    
    def monitor_account(self, verbose: bool):
        
        """Recalculates all account metrics based on current positions"""
        
        # 1. Calculate unrealized P/L
        unrealized_pl = sum(pos['profit'] or 0 for pos in self.positions_container)
        
        self.account_info["profit"] = unrealized_pl
        
        # 2. Update Equity (Balance + Floating P/L)
        self.account_info['equity'] = self.account_info['balance'] + unrealized_pl
        
        # 3. Calculate Used Margin
        self.account_info['margin'] = sum(pos['margin_required'] or 0 for pos in self.positions_container)
        
        # 4. Calculate Free Margin (Equity - Used Margin)
        self.account_info['free_margin'] = self.account_info['equity'] - self.account_info['margin']
        
        # 5. Calculate Margin Level (Equity / Margin * 100)
        self.account_info['margin_level'] = (self.account_info['equity'] / self.account_info['margin']) * 100 \
            if self.account_info['margin'] > 0 else 0.0
        
        if verbose:
            
            print(f"Balance: {self.account_info['balance']:.2f} | Equity: {self.account_info['equity']:.2f} | Profit: {self.account_info['profit']:.2f} | Margin: {self.account_info['margin']:.2f} | Free margin: {self.account_info['free_margin']} | Margin level: {self.account_info['margin_level']:.2f}%")
        
        
    def monitor_positions(self, verbose: bool):
        
        # monitoring all open trades
        
        for pos in self.positions_container:
                
            self.m_symbol.name(pos["symbol"])
            self.m_symbol.refresh_rates()
            
            # Get ticks information for every symbol
            
            ask = self.m_symbol.ask()
            bid = self.m_symbol.bid()
            
            # update price information on all positions
            
            pos["price"] = ask if pos["type"] == "buy" else bid
            
            # Monitor and calculate the profit of a position
            
            pos["profit"] = self._calculate_profit(action=pos["type"], symbol=pos["symbol"], lotsize=pos["volume"], entry_price=pos["open_price"], 
                                                    exit_price=(ask if pos["type"]=="buy" else bid))
            
            
            # Monitor the stoploss and takeprofit situation of positions
            
            if pos["tp"] > 0 and ((pos["type"] == "buy" and bid >= pos["tp"]) or (pos["type"] == "sell" and ask <= pos["tp"])): # Take profit hit    
    
                self.position_close(pos_id=pos) # close such position
                
            if pos["sl"] > 0 and ((pos["type"] == "buy" and bid <= pos["sl"]) or (pos["type"] == "sell" and ask >= pos["sl"])): # Stop loss hit
                
                self.position_close(pos_id=pos) # close such position


            # Print the information about all trades (positions and orders (if any))            
            
            if verbose:
                print(f'sim -> ticket | {pos["id"]} | symbol {pos["symbol"]} | time {pos["time"]} | type {pos["type"]} | volume {pos["volume"]} | sl {pos["sl"]} | tp {pos["tp"]} | profit {pos["profit"]:.2f}')


    def _position_validation(self,
                       volume: float,
                       symbol: str,
                       pos_type: str,
                       open_price: float, 
                       sl: float = 0.0, 
                       tp: float = 0.0) -> bool:
        """
        Validates trade parameters similar to MQL5's OrderCheck()
        
        Returns:
            bool: True if validation passes, False with error message if fails
        """
        
        self.m_symbol.name(symbol) # Assign the current symbol to the CSymbolInfo class for accessing its properties    
            
        # Get symbol properties
        symbol_info = self.m_symbol.get_info() # Get the information about the current symbol
        if symbol_info is None:
            print(f"Trade validation failed. MetaTrader5 error = {self.mt5_instance.last_error()}")
            return False
            
        # Validate volume
        
        if volume < self.m_symbol.lots_min(): # check if the received lotsize is smaller than minimum accepted lot of a symbol
            print(f"Trade validation failed: Volume ({volume}) is less than minimum allowed ({self.m_symbol.lots_min()})")
            return False
        if volume > self.m_symbol.lots_max(): # check if the received lotsize is greater than the maximum accepted lot
            print(f"Trade validation failed: Volume ({volume}) is greater than maximum allowed ({self.m_symbol.lots_max()})")
            return False
        
        step_count = volume / self.m_symbol.lots_step() 
        
        if abs(step_count - round(step_count)) > 1e-7: # check if the stoploss is a multiple of the step size
            print(f"Trade validation failed: Volume ({volume}) must be a multiple of step size ({self.m_symbol.lots_step()})")
            return False
            
        # Validate the opening price
        
        self.m_symbol.refresh_rates() # Get recent ticks information
        
        ask = self.m_symbol.ask()
        bid = self.m_symbol.bid()
        
        if ask is None or bid is None or ask==0 or bid==0:
            print("Trade Validate: Failed to Get Ask and Bid prices, Call the function market_update() to update the simulator with newly simulated price values")
            return False
        
        # Slippage check
        
        actual_price = ask if pos_type == "buy" else bid
        point = self.m_symbol.point()

        # Allowable slippage range (in absolute price)
        
        max_deviation = self.deviation_points * point
        lower_bound = actual_price - max_deviation
        upper_bound = actual_price + max_deviation

        # Check if requested price is within allowed slippage
        
        if not (lower_bound <= open_price <= upper_bound):
            print(f"Trade validation failed: {pos_type.capitalize()} price ({open_price}) is out of slippage range: {lower_bound:.5f} - {upper_bound:.5f}")
            return False
            
        # Validate stop loss and take profit levels
        
        if sl > 0:
            if pos_type == "buy" and sl >= open_price:
                print(f"Trade validation failed: Buy stop loss ({sl}) must be below order opening price ({open_price})")
                return False
            if pos_type == "sell" and sl <= open_price:
                print(f"Trade validation failed: Sell stop loss ({sl}) must be above order opening price ({open_price})")
                return False
            if not self._check_stops_level(symbol, open_price, sl, pos_type):
                return False
                
        if tp > 0:
            if pos_type == "buy" and tp <= open_price:
                print(f"Trade validation failed: Buy take profit ({tp}) must be above order opening price ({open_price})")
                return False
            if pos_type == "sell" and tp >= open_price:
                print(f"Trade validation failed: Sell take profit ({tp}) must be below order opening price ({open_price})")
                return False
            if not self._check_stops_level(symbol, open_price, tp, pos_type):
                return False
            
        # Validate margin requirements
        
        margin_required = self._calculate_margin(symbol=symbol, volume=volume, open_price=open_price) #TODO:
                
        if margin_required is None:
            print("Trade validation failed: Cannot calculate margin requirements")
            return False
        
        # Check free margin
        if margin_required > self.account_info["free_margin"]:
            print(f'Trade validation failed: Not enough money to open trade. '
                f'Required: {margin_required:.2f}, '
                f'Free margin: {self.account_info["free_margin"]:.2f}')
            
            return False

        # Check margin level (if positions exist)
        if self.account_info["margin_level"] is not None and self.account_info["margin_level"] > 0:
            if (self.account_info["equity"] / self.account_info["margin"]) * 100 < self.account_info["margin_level"]:
                print(f'Trade validation failed: Margin level too low. '
                        f'Current: {(self.account_info["equity"] / self.account_info["margin"]) * 100:.2f}%, '
                        f'Required: {self.account_info["margin_level"]:.2f}%')
                
                return False

            
        # All validations passed
        return True
    
    
    def position_close(self, selected_pos: dict) -> bool:

        # Update deal info
        
        deal_info = selected_pos.copy()
        deal_info["direction"] = "closed"
        
        # check if the reason wa SL or TP according to recent tick/price information
        
        self.m_symbol.name(selected_pos["symbol"])
        self.m_symbol.refresh_rates()
        
        ask = self.m_symbol.ask()
        bid = self.m_symbol.bid()
        digits = self.m_symbol.digits()
        
        deal_info["reason"] = "Unknown" # Unkown deal reason if the stoploss or takeprofit wasn't hit
        
        if selected_pos["type"] == "buy":
            if np.isclose(selected_pos["tp"], bid, digits): # check if the current bid price is almost equal to the takeprofit
                deal_info["reason"] = "Take profit"           
                
            elif np.isclose(selected_pos["sl"], bid, digits): # check if the current bid price is almost equal to the stoploss
                deal_info["reason"] = "Stop loss"           
        
        
        if selected_pos["type"] == "sell":
            if np.isclose(selected_pos["tp"], ask, digits): # check if the current ask price is almost equal to the takeprofit
                deal_info["reason"] = "Take profit"           
                
            elif np.isclose(selected_pos["sl"], ask, digits): # check if the current ask price is almost equal to the stoploss
                deal_info["reason"] = "Stop loss"               
        
        
        self.deals_container.append(deal_info.copy()) # add the deal to the deals container
        
        print("Trade closed successfully: ", deal_info)
        
        # Save closed deal to database
        self._save_deal(deal_info, self.history_db_name)
        
        # Remove trade from open positions
        
        if selected_pos in self.positions_container:
                
            # update the account balance
            self.account_info["balance"] += selected_pos["profit"]
            
            self.positions_container.remove(selected_pos)
        else:
            print(f"Warning: Position with ID {selected_pos['id']} not found!")

        return True

    
    def _calculate_margin(self, symbol: str, volume: float, open_price: float, margin_rate=1.0) -> float:
        
        """
        Calculates margin requirement similar to MetaTrader5 based on the margin mode.
        """
        self.m_symbol.name(symbol)

        if not self.m_symbol.select():
            print(f"Margin calculation failed: MetaTrader5 error = {self.mt5_instance.last_error()}")
            return 0.0

        contract_size = self.m_symbol.contract_size()
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

        
    def _check_stops_level(self, symbol: str, open_price: float, stop_price: float, pos_type: str) -> bool:
        
        """Check if stop levels comply with broker requirements"""
        
        self.m_symbol.name(symbol)
        
        # Validate symbol
        if not self.m_symbol.select():
            print(f"Failed to check stop level: Symbol {symbol}. MetaTrader5 error = {self.mt5_instance.last_error()}")
            return False
        
        # Check for stops level 
        stop_level = self.m_symbol.stops_level()
        
        if pos_type == "buy":
            if stop_price > open_price - stop_level * self.m_symbol.point():
                print(f"Trade validation failed: Stop level too close. Must be at least {stop_level} points away")
                return False
        else:  # sell
            if stop_price < open_price + stop_level * self.m_symbol.point():
                print(f"Trade validation failed: Stop level too close. Must be at least {stop_level} points away")
                return False
            
        
        # Check for freeze level
        
        freeze_level = self.m_symbol.freeze_level()
        
        if pos_type == "buy":
            if stop_price > open_price - freeze_level * self.m_symbol.point():
                print(f"Trade validation failed: Stop level too close. Must be at least {freeze_level} points away")
                return False
        else:  # sell
            if stop_price < open_price + freeze_level * self.m_symbol.point():
                print(f"Trade validation failed: Stop level too close. Must be at least {freeze_level} points away")
                return False
            
        return True

    def _open_position(self, 
                       pos_type: str,
                       volume: float,
                       symbol: str,
                       open_price: float,
                       sl: float = 0.0,
                       tp: float = 0.0,
                       comment: str = "", 
                       magic_number: int=-1) -> bool:

        position_info = self.position_info.copy()

        self.m_symbol.name(symbol)
        self.m_symbol.refresh_rates() # Get recent ticks information

        if not self._position_validation(volume=volume, symbol=symbol, pos_type=pos_type, open_price=open_price, sl=sl, tp=tp):
            return False

        self.id += 1  # Increment trade ID

        position_info["time"] = self.m_symbol.time(timezone=pytz.UTC)
        position_info["id"] = self.id
        position_info["magic"] = magic_number
        position_info["symbol"] = symbol
        position_info["type"] = pos_type
        position_info["volume"] = volume
        position_info["open_price"] = open_price
        position_info["sl"] = sl
        position_info["tp"] = tp
        position_info["commission"] = 0.0
        position_info["fee"] = 0.0
        position_info["swap"] = 0.0
        position_info["profit"] = 0.0
        position_info["comment"] = comment
        position_info["margin_required"] = self._calculate_margin(symbol=symbol, volume=volume, open_price=open_price)

        # Update account margin
        self.account_info["margin"] += position_info["margin_required"]

        # Append to open trades
        self.positions_container.append(position_info)
        print("Trade opened successfully: ", position_info)

        # Track deal
        self.deal_info.update(position_info)
        self.deal_info["direction"] = "opened"
        self.deal_info["reason"] = "Expert"
        self.deals_container.append(self.deal_info.copy())

        # Log to database
        self._save_deal(self.deal_info, self.history_db_name)

        return True

    def buy(self, volume: float, symbol: str, open_price: float, sl: float = 0.0, tp: float = 0.0, comment: str = "") -> bool:
        return self._open_position("buy", volume, symbol, open_price, sl, tp, comment)

    def sell(self, volume: float, symbol: str, open_price: float, sl: float = 0.0, tp: float = 0.0, comment: str = "") -> bool:
        return self._open_position("sell", volume, symbol, open_price, sl, tp, comment)
    
    # Position modifications
    
    def position_modify(self, pos: dict, new_sl: float, new_tp) -> bool:
        
        new_position = pos.copy()
        
        if pos["type"] == "buy":
            if new_sl >= pos["price"]: 
                print("Failed to modify sl, new_sl >= current price")
                return False
        
        if pos["type"] == "sell":
            if new_sl <= pos["price"]: 
                print("Failed to modify sl, new_sl <= current price")
                return False
        
        if not self._check_stops_level(symbol=pos["symbol"], open_price=pos["open_price"], stop_price=new_sl, pos_type=pos["type"]):
            print("Failed to Modify the Stoploss")
            
        if not self._check_stops_level(symbol=pos["symbol"], open_price=pos["open_price"], stop_price=new_tp, pos_type=pos["type"]):
            print("Failed to Modify the Takeprofit")
        
        # new sl and tp values 
        
        new_position["sl"] = new_sl
        new_position["tp"] = new_tp
        
        # Update the container
        
        for i, p in enumerate(self.positions_container):
            if p["id"] == pos["id"]:
                self.positions_container[i] = new_position
                print(f"Position with id=[{pos['id']}] modified! new_sl={new_sl} new_tp={new_tp}")
                return True

        print("Failed to modify position: ID not found")

        return True
    
    
    # dealing with pending orders
    
    def _place_a_pending_order(self, 
                               order_type: str,
                               volume: float,
                               symbol: str,
                               open_price: float,
                               sl: float = 0.0,
                               tp: float = 0.0,
                               comment: str = "",
                               expiry_date: datetime = None,
                               expiration_mode: str="gtc",
                               magic_number: int=-1
                               ):
        
        order_types = ["buy limit", "buy stop", "sell limit", "sell stop"]
        
        if order_type not in order_types:
            raise ValueError(f"Invalid pending order type, available order types include: {order_types}")
        
        expiration_modes = ["gtc", "daily", "daily_excluding_stops"]
        if expiration_mode not in expiration_modes:
            raise ValueError(f"Invalid Expiration mode, available modes include: {expiration_modes}")
        
        # Get market info
        
        self.m_symbol.name(symbol_name=symbol) # assign symbol's name
        self.m_symbol.refresh_rates() # get recent ticks from the market using the current selected symbol
        
        if order_type in ("buy limit", "buy stop"):
            
            if abs(open_price - self.m_symbol.bid()) < self.m_symbol.stops_level() * self.m_symbol.point():
                print(f"Failed to open a pending order, a '{order_type}' order is too close to the market")
        
        if order_type in ("sell limit", "sell stop"):
            
            if abs(open_price - self.m_symbol.ask()) < self.m_symbol.stops_level() * self.m_symbol.point():
                print(f"Failed to open a pending order, a '{order_type}' order is too close to the market")
        
        
        # check if the order has a valid expiry date
        
        if expiry_date is not None:
            if expiry_date <= self.m_symbol.time(timezone=pytz.UTC):
                print(f"Failed to place a pending order {order_type}, Invalid datetime")
                return
        
        
        order_info = self.order_info.copy()
        
        self.id += 1
        
        order_info["id"] = self.id
        order_info["time"] = self.m_symbol.time(timezone=pytz.UTC)
        order_info["type"] = order_type
        order_info["volume"] = volume
        order_info["symbol"] = symbol
        order_info["open_price"] = open_price
        order_info["sl"] = sl
        order_info["tp"] = tp
        order_info["comment"] = comment
        order_info["magic"] = magic_number
        order_info["margin_required"] = self._calculate_margin(symbol=symbol, volume=volume, open_price=open_price)
        
        order_info["expiry_date"] = expiry_date
        order_info["expiration_mode"] = expiration_mode
        
        self.orders_container.append(order_info) # add a valid order to it's container
        
        
    def buy_stop(self, volume: float, symbol: str, open_price: float, sl: float = 0.0, tp: float = 0.0, comment: str = "", expiry_date: datetime = None,expiration_mode: str="gtc"):
        
        # validate an order according to it's type
        
        self.m_symbol.name(symbol_name=symbol)
        self.m_symbol.refresh_rates()
        
        if self.m_symbol.bid() >= open_price:
            print("Failed to place a buy stop order, open price <= the bid price")    
            return
        
        self._place_a_pending_order("buy stop", volume, symbol, open_price, sl, tp, comment, expiry_date, expiration_mode)    

    def buy_limit(self, volume: float, symbol: str, open_price: float, sl: float = 0.0, tp: float = 0.0, comment: str = "", expiry_date: datetime = None, expiration_mode: str="gtc"):
        
        self.m_symbol.name(symbol_name=symbol)
        self.m_symbol.refresh_rates()
        
        if self.m_symbol.bid() <= open_price:
            print("Failed to place a buy limit order, open price >= current bid price")
            return

        self._place_a_pending_order("buy limit", volume, symbol, open_price, sl, tp, comment, expiry_date, expiration_mode)

    def sell_stop(self, volume: float, symbol: str, open_price: float, sl: float = 0.0, tp: float = 0.0, comment: str = "", expiry_date: datetime = None, expiration_mode: str="gtc"):
        
        self.m_symbol.name(symbol_name=symbol)
        self.m_symbol.refresh_rates()

        if self.m_symbol.ask() <= open_price:
            print("Failed to place a sell stop order, open price >= current ask price")
            return

        self._place_a_pending_order("sell stop", volume, symbol, open_price, sl, tp, comment, expiry_date, expiration_mode)

    def sell_limit(self, volume: float, symbol: str, open_price: float, sl: float = 0.0, tp: float = 0.0, comment: str = "", expiry_date: datetime = None, expiration_mode: str="gtc"):
        
        self.m_symbol.name(symbol_name=symbol)
        self.m_symbol.refresh_rates()

        if self.m_symbol.ask() >= open_price:
            print("Failed to place a sell limit order, open price <= current ask price")
            return

        self._place_a_pending_order("sell limit", volume, symbol, open_price, sl, tp, comment, expiry_date, expiration_mode)
                
                
    def order_modify(self, order: dict, new_open_price: float, new_sl: float, new_tp: float, new_expiry: datetime = None, new_expiration_mode: str = None):
        """
        Modify an existing pending order's open price, SL/TP, and optionally its expiration settings.
        """
        new_order = order.copy()

        # Validate order type
        valid_types = ["buy limit", "buy stop", "sell limit", "sell stop"]
        if order["type"] not in valid_types:
            print(f"Invalid order type for modification: {order['type']}")
            return False

        self.m_symbol.name(order["symbol"])
        self.m_symbol.refresh_rates()

        # Ensure open price is placed logically according to type
        ask = self.m_symbol.ask()
        bid = self.m_symbol.bid()

        if order["type"] == "buy stop" and bid >= new_open_price:
            print("Failed to modify Buy Stop: new open price <= current bid price")
            return False
        if order["type"] == "buy limit" and bid <= new_open_price:
            print("Failed to modify Buy Limit: new open price >= current bid price")
            return False
        if order["type"] == "sell stop" and ask <= new_open_price:
            print("Failed to modify Sell Stop: new open price >= current ask price")
            return False
        if order["type"] == "sell limit" and ask >= new_open_price:
            print("Failed to modify Sell Limit: new open price <= current ask price")
            return False

        
        # ensure the order ins't close to the market
        
        order_type = order["type"]
        if order_type in ("buy limit", "buy stop"):
            
            if abs(new_open_price - self.m_symbol.bid()) < self.m_symbol.stops_level() * self.m_symbol.point():
                print(f"Failed to open a pending order, a '{order_type}' order is too close to the market")
                return False
        
        if order_type in ("sell limit", "sell stop"):
            
            if abs(new_open_price - self.m_symbol.ask()) < self.m_symbol.stops_level() * self.m_symbol.point():
                print(f"Failed to open a pending order, a '{order_type}' order is too close to the market")
                return False
        
        if new_expiry and new_expiry <= self.m_symbol.time(timezone=pytz.UTC):
            print("Invalid Expiry date, new expiry date must be a value in the future")
        
        # Update order values
        new_order["open_price"] = new_open_price
        new_order["sl"] = new_sl
        new_order["tp"] = new_tp

        if new_expiry:
            new_order["expiry_date"] = new_expiry
        if new_expiration_mode:
            new_order["expiration_mode"] = new_expiration_mode

        # Update the order in the container
        for i, o in enumerate(self.orders_container):
            if o["id"] == order["id"]:
                self.orders_container[i] = new_order
                print(f"Order with id=[{order['id']}] modified successfully.")
                return True

        print("Failed to modify order: ID not found")
        return False


    def order_delete(self, selected_order: dict) -> bool:
        
        # delete a pending order from the orders container
        
        if selected_order in self.orders_container:
            
            self.orders_container.remove(selected_order)
            return True
        
        else:
            print(f"Warning: An Order with ID {selected_order['id']} not found!")
            return False

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

