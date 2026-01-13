import MetaTrader5 as mt5
from datetime import datetime

class CDealInfo:
    def __init__(self):
        self._deal = None
        self._ticket = 0

    def _deal_type_description(self):
        if not self._deal:
            return "N/A"
        deal_type_map = {
            mt5.DEAL_TYPE_BUY: "BUY",
            mt5.DEAL_TYPE_SELL: "SELL",
            mt5.DEAL_TYPE_BALANCE: "BALANCE",
            mt5.DEAL_TYPE_CREDIT: "CREDIT",
            mt5.DEAL_TYPE_CHARGE: "CHARGE",
            mt5.DEAL_TYPE_CORRECTION: "CORRECTION",
            mt5.DEAL_TYPE_BONUS: "BONUS",
            mt5.DEAL_TYPE_COMMISSION: "COMMISSION",
            mt5.DEAL_TYPE_COMMISSION_DAILY: "COMMISSION DAILY",
            mt5.DEAL_TYPE_COMMISSION_MONTHLY: "COMMISSION MONTHLY",
            mt5.DEAL_TYPE_COMMISSION_AGENT_DAILY: "AGENT COMMISSION DAILY",
            mt5.DEAL_TYPE_COMMISSION_AGENT_MONTHLY: "AGENT COMMISSION MONTHLY",
            mt5.DEAL_TYPE_INTEREST: "INTEREST",
            mt5.DEAL_TYPE_BUY_CANCELED: "BUY CANCELED",
            mt5.DEAL_TYPE_SELL_CANCELED: "SELL CANCELED"
        }
        return deal_type_map.get(self._deal.type, f"UNKNOWN({self._deal.type})")

    # --- selection

    def select_deal(self, deal) -> bool:
        
        if deal is None:
            return False
    
        self._deal = deal
        return True
    
    # --- Integer, datetime & string properties
    
    def ticket(self):
        return self._ticket

    def order(self):
        return self._deal.order if self._deal else None

    def time(self):
        return datetime.fromtimestamp(self._deal.time) if self._deal else None

    def time_msc(self):
        return self._deal.time_msc if self._deal else None

    def deal_type(self):
        return self._deal.type if self._deal else None

    def type_description(self):
        return self._deal_type_description() if self._deal else "N/A"

    def entry(self):
        return self._deal.entry if self._deal else None

    def entry_description(self):
        if not self._deal:
            return "N/A"
        entry_map = {
            mt5.DEAL_ENTRY_IN: "IN",
            mt5.DEAL_ENTRY_OUT: "OUT",
            mt5.DEAL_ENTRY_INOUT: "INOUT"
        }
        return entry_map.get(self._deal.entry, "UNKNOWN")

    def magic(self):
        return self._deal.magic if self._deal else None

    def position_id(self):
        return self._deal.position_id if self._deal else None

    # --- Double properties
    
    def volume(self):
        return self._deal.volume if self._deal else None

    def price(self):
        return self._deal.price if self._deal else None

    def commission(self):
        return self._deal.commission if self._deal else None

    def swap(self):
        return self._deal.swap if self._deal else None

    def profit(self):
        return self._deal.profit if self._deal else None

    # --- Text properties
    
    def symbol(self):
        return self._deal.symbol if self._deal else None

    def comment(self):
        return self._deal.comment if self._deal else None

    def external_id(self):
        return self._deal.external_id if self._deal else None
