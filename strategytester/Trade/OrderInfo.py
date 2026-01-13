import MetaTrader5 as mt5
from datetime import datetime

class COrderInfo:
    def __init__(self):
        self._order = None
    
    def select_order(self, order) -> bool:
        
        if order is None:
            return False
        
        self._order = order
        return True
        
    """
    def select_by_ticket(self, ticket: int) -> bool:
        orders = mt5.orders_get(ticket=ticket)
        if orders:
            self._order = orders[0]
            return True
        return False

    def select_by_index(self, index: int) -> bool:
        orders = mt5.orders_get()
        if orders and 0 <= index < len(orders):
            self._order = orders[index]
            return True
        return False
    """

    def ticket(self) -> int:
        return self._order.ticket if self._order else -1

    def time_setup(self) -> datetime:
        return datetime.fromtimestamp(self._order.time_setup) if self._order else None

    def time_setup_msc(self) -> int:
        return self._order.time_setup_msc if self._order else 0

    def time_done(self) -> datetime:
        return datetime.fromtimestamp(self._order.time_done) if self._order else None

    def time_done_msc(self) -> int:
        return self._order.time_done_msc if self._order else 0

    def order_type(self) -> int:
        return self._order.type if self._order else -1
    
    def order_type_description(self) -> str:

        order_type_map = {
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

        return order_type_map.get(self.order_type(), "Unknown order type")
    
    def state(self) -> int:
        return self._order.state if self._order else -1
    
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
        
        return state_map.get(self.state(), "Unknown order state")

    def time_expiration(self) -> datetime:
        
        if self._order.time_expiration == 0:
            return None
        try:
            # Convert milliseconds to seconds by dividing by 1000
            return datetime.fromtimestamp(self._order.time_expiration / 1000)
        
        except (ValueError, OSError) as e:
            print(f"Error converting expiration time: {e}")
            return None

    def type_filling(self) -> int:
        return self._order.type_filling if self._order else -1
    
    def type_filling_description(self) -> str:
        
        filling_map = {
            1: "FOK (Fill or Kill)",
            2: "IOC (Immediate or Cancel)",
            4: "BOC (Book or Cancel)",
            8: "RETURN"
        }
        
        return filling_map.get(self.type_filling())

    def type_time(self) -> int:
        return self._order.type_time if self._order else -1

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
        
    def magic(self) -> int:
        return self._order.magic if self._order else -1

    def position_id(self) -> int:
        return self._order.position_id if self._order else -1

    # def position_by_id(self) -> int:
    #     return self._order.position_by_id if self._order else -1

    def volume_initial(self) -> float:
        return self._order.volume_initial if self._order else 0.0

    def volume_current(self) -> float:
        return self._order.volume_current if self._order else 0.0

    def price_open(self) -> float:
        return self._order.price_open if self._order else 0.0

    def stop_loss(self) -> float:
        return self._order.sl if self._order else 0.0

    def take_profit(self) -> float:
        return self._order.tp if self._order else 0.0

    def price_current(self) -> float:
        if not self._order:
            return 0.0
        tick = mt5.symbol_info_tick(self._order.symbol)
        if not tick:
            return 0.0
        return tick.bid if self._order.type in [mt5.ORDER_TYPE_BUY, mt5.ORDER_TYPE_BUY_LIMIT, mt5.ORDER_TYPE_BUY_STOP] else tick.ask

    def price_stop_limit(self) -> float:
        return self._order.price_stoplimit if self._order else 0.0

    def symbol(self) -> str:
        return self._order.symbol if self._order else ""

    def comment(self) -> str:
        return self._order.comment if self._order else ""

    def external_id(self) -> str:
        return self._order.external_id if self._order else ""

