import MetaTrader5 as mt5
from datetime import datetime

class CHistoryOrderInfo:
    def __init__(self):
        """CHistoryOrderInfo class provides easy access to the history order properties.

           For more information visit: https://www.mql5.com/en/docs/standardlibrary/tradeclasses/chistoryorderinfo
        """ 
        
        self._ticket = None
        self._order = None
        self._symbol = ""

    # --- Selection 

    def select_order(self, order):
        if order is None:
            return False
        
        self._order = order
        self._ticket = order.ticket
        return True

    def ticket(self):
        return self._ticket

    # ---  integer properties
    
    def time_setup(self):
        return datetime.fromtimestamp(self._order.time_setup) if self._order else None

    def time_setup_msc(self):
        return self._order.time_setup_msc if self._order else None

    def time_done(self):
        return datetime.fromtimestamp(self._order.time_done) if self._order else None

    def time_done_msc(self):
        return self._order.time_done_msc if self._order else None

    def order_type(self):
        return self._order.type if self._order else None

    def type_description(self) -> str:
        
        order_map = {
            mt5.ORDER_TYPE_BUY: "Market Buy order",
            mt5.ORDER_TYPE_SELL: "Market Sell order",
            mt5.ORDER_TYPE_BUY_LIMIT: "Buy Limit pending order",
            mt5.ORDER_TYPE_SELL_LIMIT: "Sell Limit pending order",
            mt5.ORDER_TYPE_BUY_STOP: "Buy Stop pending order",
            mt5.ORDER_TYPE_SELL_STOP: "Sell Stop pending order",
            mt5.ORDER_TYPE_BUY_STOP_LIMIT: "Buy Stop Limit (triggers a Buy Limit at StopLimit price)",
            mt5.ORDER_TYPE_SELL_STOP_LIMIT: "Sell Stop Limit (triggers a Sell Limit at StopLimit price)",
            mt5.ORDER_TYPE_CLOSE_BY: "Close By order (closes position with opposite one)"
        }

        return order_map.get(self.order_type(), f"Unknown Order Type")

    def state(self):
        return self._order.state if self._order else None

    def state_description(self) -> str:
        state_map = {
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

        return state_map.get(self.state(), f"Unknown Order State")
    
    def time_expiration(self) -> datetime: 
        
        if self._order.time_expiration == 0:
            return None
        try:
            # Convert milliseconds to seconds by dividing by 1000
            return datetime.fromtimestamp(self._order.time_expiration / 1000)
        
        except (ValueError, OSError) as e:
            print(f"Error converting expiration time: {e}")
            return None

    def type_filling(self):
        
        symbol_info = mt5.symbol_info(self.symbol())
        if symbol_info is None:
            print(f"Failed to get symbol info for {self.symbol()}")
        
        filling_map = {
            1: mt5.ORDER_FILLING_FOK,
            2: mt5.ORDER_FILLING_IOC,
            4: mt5.ORDER_FILLING_BOC,
            8: mt5.ORDER_FILLING_RETURN
        }
        
        return filling_map.get(symbol_info.filling_mode, f"Unknown Filling type")
    
    def type_filling_description(self):
        
        filling_map = {
            1: "FOK (Fill or Kill)",
            2: "IOC (Immediate or Cancel)",
            4: "BOC (Book or Cancel)",
            8: "RETURN"
        }
        
        return filling_map.get(self.type_filling())
        
    def type_time(self):
        return self._order.type_time if self._order else None

    def type_time_description(self):
        
        type_time = self._order.type_time
        
        if  type_time == mt5.ORDER_TIME_SPECIFIED:
            return "ORDER_TIME_SPECIFIED"
        elif type_time == mt5.ORDER_TIME_SPECIFIED_DAY:
            return "ORDER_TIME_SPECIFIED_DAY"
        elif type_time == mt5.ORDER_TIME_DAY:
            return "ORDER_TIME_DAY"
        elif type_time == mt5.ORDER_TIME_GTC:
            return "ORDER_TIME_GTC"
        else:
            return "unknown"

    def magic(self):
        return self._order.magic if self._order else None

    def position_id(self):
        return self._order.position_id if self._order else None

    def position_by_id(self):
        return self._order.position_by_id if self._order else None

    # ---  double properties
    
    def volume_initial(self):
        return self._order.volume_initial if self._order else None

    def volume_current(self):
        return self._order.volume_current if self._order else None

    def price_open(self):
        return self._order.price_open if self._order else None

    def stop_loss(self):
        return self._order.sl if self._order else None

    def take_profit(self):
        return self._order.tp if self._order else None

    def price_current(self):
        return self._order.price_current if self._order else None

    def price_stop_limit(self):
        return self._order.price_stoplimit if self._order else None

    # --- string properties
    
    def symbol(self):
        return self._order.symbol if self._order else None

    def comment(self):
        return self._order.comment if self._order else None

    def external_id(self):
        return self._order.external_id if self._order else None
