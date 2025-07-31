import MetaTrader5 as mt5
from datetime import datetime

class CPositionInfo:
    def __init__(self):
        self._position = None
    
    def select_position(self, position) -> bool:
        
        if position is None:
            return False
        else:
            self._position = position
            return True
    
    """
    def select_by_ticket(self, ticket: int) -> bool:
        
        positions = mt5.positions_get(ticket=ticket)
        if positions:
            self._position = positions[0]
            return True
        return False

    def select_by_magic(self, magic: int, symbol: str = None) -> bool:
        
        positions = mt5.positions_get()
        if positions is None:
            return False
        for pos in positions:
            if pos.magic == magic and (symbol is None or pos.symbol == symbol):
                self._position = pos
                return True
        return False

    def select_by_index(self, index: int) -> bool:
        
        positions = mt5.positions_get()
        if positions and 0 <= index < len(positions):
            self._position = positions[index]
            return True
        return False
    """

    def ticket(self) -> int:
        return self._position.ticket if self._position else -1

    def magic(self) -> int:
        return self._position.magic if self._position else -1

    def time(self) -> datetime:
        return datetime.fromtimestamp(self._position.time) if self._position else None

    def time_msc(self) -> int:
        return self._position.time_msc if self._position else None
    
    def time_update(self) -> datetime:
        return datetime.fromtimestamp(self._position.time_update) if self._position else None

    def time_update_msc(self) -> int:
        return self._position.time_update_msc if self._position else None
    
    def position_type(self) -> int:
        return self._position.type if self._position else -1

    def position_type_description(self) -> int:
        
        pos_type_map = {
            mt5.POSITION_TYPE_BUY: "Buy",
            mt5.POSITION_TYPE_SELL: "Sell"
        }
        
        return pos_type_map.get(self.position_type(), "Unknown position type")
    
    def volume(self) -> float:
        return self._position.volume if self._position else 0.0

    def price_open(self) -> float:
        return self._position.price_open if self._position else 0.0

    def symbol(self) -> str:
        return self._position.symbol if self._position else ""

    def profit(self) -> float:
        return self._position.profit if self._position else 0.0

    def swap(self) -> float:
        return self._position.swap if self._position else 0.0

    # def commission(self) -> float:
    #     return self._position.commission if self._position else 0.0

    def comment(self) -> str:
        return self._position.comment if self._position else ""
    
    def stop_loss(self) -> float:
        return self._position.sl if self._position else 0.0

    def take_profit(self) -> float:
        return self._position.tp if self._position else 0.0

    def price_current(self) -> float:
        if not self._position:
            return 0.0
        tick = mt5.symbol_info_tick(self._position.symbol)
        if not tick:
            return 0.0
        return tick.bid if self._position.type == mt5.POSITION_TYPE_BUY else tick.ask
