import MetaTrader5 as mt5
from datetime import datetime

class CSymbolInfo:
    def __init__(self, mt5_instance: mt5):
        
        """This class provides access to the symbol properties.
        
           read more: https://www.mql5.com/en/docs/standardlibrary/tradeclasses/csymbolinfo
        """ 
        
        self.symbol = ""
        self.info = None
        self.mt5_instance = mt5_instance
        
        self.ticks_info = {
                'time': None,
                'ask': 0,
                'bid': 0,
                'last': 0,
                'volume': 0,
                'time_msc': 0,
                'volume_real': 0
        }

    def name(self, symbol_name: str):
        
        self.symbol = symbol_name
    
    # --- controlling
    
    def symbol_info_check(method):
        def wrapper(self, *args, **kwargs):
            if not self.info: # if symbolinfo == none 
                if not self.refresh(): # forces to get symbolinfo
                    raise Exception(f"Failed to get symbol info for {self.symbol}. MetaTrader5 Error = {self.mt5_instance.last_error()}")
            return method(self, *args, **kwargs)
        return wrapper
    
    def refresh(self) -> bool:
        
        info = self.mt5_instance.symbol_info(self.symbol)
        
        if not info:
            return False
        
        self.info = info
        return True

    @symbol_info_check
    def get_info(self):
        
        self.refresh()
        return self.info
    
    def refresh_rates(self):

        """
        Safely refreshes market rates using symbol_info_tick()
        Returns True if successful, False otherwise
        """
        
        try:
            # Get fresh tick data
            new_ticks = self.mt5_instance.symbol_info_tick(self.symbol)
            if new_ticks is None:
                print(f"Refresh failed: {self.mt5_instance.last_error()}")
                return False    
        
            self.ticks_info['time'] = new_ticks.time
            self.ticks_info['ask'] = new_ticks.ask
            self.ticks_info['bid'] = new_ticks.bid
            self.ticks_info['last'] = new_ticks.last
            self.ticks_info['volume'] = new_ticks.volume
            self.ticks_info['time_msc'] = new_ticks.time_msc
            self.ticks_info['volume_real'] = new_ticks.volume_real
        
            return True
            
        except AttributeError as e:
            print(f"Refresh error: {str(e)}")
            return False


    # --- properties
    
    @symbol_info_check
    def get_name(self):
        return self.info.name
    
    def select(self, select=True):
        
        return self.mt5_instance.symbol_select(self.symbol, select)

    # --- volumes
    
    def volume(self):
        return self.ticks_info['volume']
    
    def volume_real(self):
        return self.ticks_info['volume_real']
    
    
    @symbol_info_check
    def volume_high(self):
        return self.info.volumehigh
    
    @symbol_info_check
    def volume_low(self):
        return self.info.volumelow
    
    # --- Miscillaneous
    
    def time(self, timezone):
        return datetime.fromtimestamp(self.ticks_info['time'], tz=timezone)
    
    def time_msc(self):
        return self.ticks_info["time_msc"]

    @symbol_info_check
    def spread(self):
        return self.info.spread

    @symbol_info_check
    def spread_float(self):
        return self.info.spread_float
    
    @symbol_info_check
    def ticks_book_depth(self):
        return self.info.ticks_bookdepth
    
    # --- Trade levels
    
    @symbol_info_check
    def stops_level(self):
        return self.info.trade_stops_level

    @symbol_info_check
    def freeze_level(self):
        return self.info.trade_freeze_level
    
    # --- bid parameters
    
    def bid(self):
        return self.ticks_info['bid']
        
    def bid_high(self):
        return self.info.bidhigh

    def bid_low(self):
        return self.info.bidlow
    
    # --- ask parameters
    
    def ask(self):
        return self.ticks_info['ask']
    
    @symbol_info_check
    def ask_high(self):
        return self.info.askhigh

    @symbol_info_check
    def ask_low(self):
        return self.info.asklow
    
    # --- Last parameters
    
    @symbol_info_check
    def is_synchronized(self):
        return self.info.select

    def last(self):
        return self.ticks_info['last']

    @symbol_info_check
    def last_high(self):
        return self.info.lasthigh

    @symbol_info_check
    def last_low(self):
        return self.info.lastlow

    # --- terms and calculation of trades 
    
    @symbol_info_check
    def trade_calc_mode(self):
        return self.info.trade_calc_mode
    
    def trade_calc_mode_description(self) -> str:
        
        calc_mode_map = {
            self.mt5_instance.SYMBOL_CALC_MODE_FOREX: "Calculation of profit and margin for Forex",
            self.mt5_instance.SYMBOL_CALC_MODE_FUTURES: "Calculation of margin and profit for futures",
            self.mt5_instance.SYMBOL_CALC_MODE_CFD: "Calculation of margin and profit for CFD",
            self.mt5_instance.SYMBOL_CALC_MODE_CFDINDEX: "Calculation of margin and profit for CFD by indexes",
            self.mt5_instance.SYMBOL_CALC_MODE_CFDLEVERAGE: "Calculation of margin and profit for CFD at leverage trading",
            self.mt5_instance.SYMBOL_CALC_MODE_FOREX_NO_LEVERAGE: "Calculation of profit and margin for Forex symbols without taking into account the leverage",
            self.mt5_instance.SYMBOL_CALC_MODE_EXCH_STOCKS: "Calculation of margin and profit for trading securities on a stock exchange",
            self.mt5_instance.SYMBOL_CALC_MODE_EXCH_FUTURES: "Calculation of margin and profit for trading futures contracts on a stock exchange",
            self.mt5_instance.SYMBOL_CALC_MODE_EXCH_BONDS: "Calculation of margin and profit for trading bonds on a stock exchange",
            self.mt5_instance.SYMBOL_CALC_MODE_EXCH_STOCKS_MOEX: "Calculation of margin and profit for trading securities on MOEX",
            self.mt5_instance.SYMBOL_CALC_MODE_EXCH_BONDS_MOEX: "Calculation of margin and profit for trading bonds on MOEX",
            self.mt5_instance.SYMBOL_CALC_MODE_SERV_COLLATERAL: "Collateral mode - a symbol is used as a non-tradable asset on a trading account"
        }

        return calc_mode_map.get(self.trade_calc_mode(), "Unknown trade calculation mode")
    
    @symbol_info_check
    def trade_mode(self):
        return self.info.trade_mode

    def trade_mode_description(self) -> str:
        
        trade_mode_map = {
            self.mt5_instance.SYMBOL_TRADE_MODE_DISABLED: "Trade is disabled for the symbol",
            self.mt5_instance.SYMBOL_TRADE_MODE_LONGONLY: "Allowed only long positions",
            self.mt5_instance.SYMBOL_TRADE_MODE_SHORTONLY: "Allowed only short positions",
            self.mt5_instance.SYMBOL_TRADE_MODE_CLOSEONLY: "Allowed only position close operations",
            self.mt5_instance.SYMBOL_TRADE_MODE_FULL: "No trade restrictions"
        }

        return trade_mode_map.get(self.trade_mode(), "Unknown trade mode")
    
    
    @symbol_info_check
    def trade_execution(self):
        return self.info.trade_exemode

    def trade_execution_description(self) -> str:
        
        exec_mode_map = {
            
            self.mt5_instance.SYMBOL_TRADE_EXECUTION_REQUEST: "Execution by request",
            self.mt5_instance.SYMBOL_TRADE_EXECUTION_INSTANT: "Instant execution",
            self.mt5_instance.SYMBOL_TRADE_EXECUTION_MARKET: "Market execution",
            self.mt5_instance.SYMBOL_TRADE_EXECUTION_EXCHANGE: "Exchange execution"
        }

        return exec_mode_map.get(self.trade_execution(), "Unkown trade execution mode")
        
    @symbol_info_check
    def order_mode(self):
        return self.info.order_mode

    # --- swaps
    
    @symbol_info_check
    def swap_mode(self):
        return self.info.swap_mode

    def swap_mode_description(self) -> str:
        
        swap_mode_map = {
            self.mt5_instance.SYMBOL_SWAP_MODE_DISABLED: "No swaps",
            self.mt5_instance.SYMBOL_SWAP_MODE_POINTS: "Swaps are calculated in points",
            self.mt5_instance.SYMBOL_SWAP_MODE_CURRENCY_SYMBOL: "Swaps are calculated in base currency",
            self.mt5_instance.SYMBOL_SWAP_MODE_CURRENCY_MARGIN: "Swaps are calculated in margin currency",
            self.mt5_instance.SYMBOL_SWAP_MODE_CURRENCY_DEPOSIT: "Swaps are calculated in deposit currency",
            self.mt5_instance.SYMBOL_SWAP_MODE_INTEREST_CURRENT: "Swaps are calculated as annual interest using the current price",
            self.mt5_instance.SYMBOL_SWAP_MODE_INTEREST_OPEN: "Swaps are calculated as annual interest using the open price",
            self.mt5_instance.SYMBOL_SWAP_MODE_REOPEN_CURRENT: "Swaps are charged by reopening positions at the close price",
            self.mt5_instance.SYMBOL_SWAP_MODE_REOPEN_BID: "Swaps are charged by reopening positions at the Bid price"
        }
    
        return swap_mode_map.get(self.swap_mode(), "Unkown swap mode")

    @symbol_info_check
    def swap_rollover_3days(self):
        return self.info.swap_rollover3days

    def swap_rollover_3days_description(self):
        
        swap_rollover_map = {
            0: "Sunday",
            1: "Monday",
            2: "Tuesday",
            3: "Wednesday",
            4: "Thursday",
            5: "Friday",
            6: "Saturday",
        }

        return swap_rollover_map.get(self.swap_rollover_3days(), "Unkown swap rollover 3 days")
        
    @symbol_info_check
    def filling_mode(self):
        return self.info.filling_mode
    
    # --- dates for futures

    @symbol_info_check
    def expiration_time(self):
        return self.info.expiration_time

    @symbol_info_check
    def start_time(self):
        return self.info.start_time
    
    # --- margin parameters
    
    @symbol_info_check
    def margin_initial(self):
        return self.info.margin_initial

    @symbol_info_check
    def margin_maintenance(self):
        return self.info.margin_maintenance

    @symbol_info_check
    def margin_hedged(self):
        return self.info.margin_hedged

    @symbol_info_check
    def margin_hedged_use_leg(self):
        return self.info.margin_hedged_use_leg
    
    # --- tick parameters

    @symbol_info_check
    def digits(self):
        return self.info.digits

    @symbol_info_check
    def point(self):
        return self.info.point
    
    @symbol_info_check
    def tick_value(self):
        return self.info.trade_tick_value

    @symbol_info_check
    def tick_value_profit(self):
        return self.info.trade_tick_value_profit

    @symbol_info_check
    def tick_value_loss(self):
        return self.info.trade_tick_value_loss

    @symbol_info_check
    def tick_size(self):
        return self.info.trade_tick_size

    @symbol_info_check
    def swap_long(self):
        return self.info.swap_long

    @symbol_info_check
    def swap_short(self):
        return self.info.swap_short
    
    # --- Lots parameters
    
    @symbol_info_check
    def contract_size(self):
        return self.info.trade_contract_size
    
    @symbol_info_check
    def lots_min(self):
        return self.info.volume_min

    @symbol_info_check
    def lots_max(self):
        return self.info.volume_max

    @symbol_info_check
    def lots_step(self):
        return self.info.volume_step

    @symbol_info_check
    def lots_limit(self):
        return self.info.volume_limit

    # --- Currency 
    
    @symbol_info_check
    def currency_base(self):
        return self.info.currency_base

    @symbol_info_check
    def currency_profit(self):
        return self.info.currency_profit

    @symbol_info_check
    def currency_margin(self):
        return self.info.currency_margin

    @symbol_info_check
    def bank(self):
        return self.info.bank
    
    @symbol_info_check
    def description(self):
        return self.info.description    
    
    @symbol_info_check
    def path(self):
        return self.info.path
    
    @symbol_info_check
    def page(self):
        return self.info.page
    
    # --- Sessions

    @symbol_info_check
    def session_deals(self):
        return self.info.session_deals

    @symbol_info_check
    def session_buy_orders(self):
        return self.info.session_buy_orders

    @symbol_info_check
    def session_sell_orders(self):
        return self.info.session_sell_orders

    @symbol_info_check
    def session_turnover(self):
        return self.info.session_turnover

    @symbol_info_check
    def session_interest(self):
        return self.info.session_interest

    @symbol_info_check
    def session_buy_orders_volume(self):
        return self.info.session_buy_orders_volume

    @symbol_info_check
    def session_sell_orders_volume(self):
        return self.info.session_sell_orders_volume

    @symbol_info_check
    def session_open(self):
        return self.info.session_open

    @symbol_info_check
    def session_close(self):
        return self.info.session_close

    @symbol_info_check
    def session_aw(self):
        return self.info.session_aw

    @symbol_info_check
    def session_price_settlement(self):
        return self.info.session_price_settlement

    @symbol_info_check
    def session_price_limit_min(self):
        return self.info.session_price_limit_min

    @symbol_info_check
    def session_price_limit_max(self):
        return self.info.session_price_limit_max
    
    @symbol_info_check
    def trade_face_value(self):
        return self.info.trade_face_value
