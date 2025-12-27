from Trade.SymbolInfo import CSymbolInfo
import numpy as np

class TradeValidators:
    def __init__(self, symbol_info: CSymbolInfo, ticks_info: any, logger: any):
        
        self.symbol_info = symbol_info
        self.ticks_info = ticks_info
        self.logger = logger
        
    def is_valid_lotsize(self, lotsize: float) -> bool:
        
        # Validate lotsize
        
        if lotsize < self.symbol_info.lots_min(): # check if the received lotsize is smaller than minimum accepted lot of a symbol
            self.logger.info(f"Trade validation failed: lotsize ({lotsize}) is less than minimum allowed ({self.symbol_info.lots_min()})")
            return False
        if lotsize > self.symbol_info.lots_max(): # check if the received lotsize is greater than the maximum accepted lot
            self.logger.info(f"Trade validation failed: lotsize ({lotsize}) is greater than maximum allowed ({self.symbol_info.lots_max()})")
            return False
        
        step_count = lotsize / self.symbol_info.lots_step() 
        
        if abs(step_count - round(step_count)) > 1e-7: # check if the stoploss is a multiple of the step size
            self.logger.info(f"Trade validation failed: lotsize ({lotsize}) must be a multiple of step size ({self.symbol_info.lots_step()})")
            return False

        return True
    
    def __is_valid_freezenstopslevel(self, symbol: str, entry: float, stop_price: float, pos_type: int) -> bool:

        self.symbol_info.name(symbol)

        if not self.symbol_info.select():
            self.logger.info(f"Trade validation failed: Symbol {symbol} not selectable")
            return False

        point = self.symbol_info.point()
        stop_level   = self.symbol_info.stops_level() * point
        freeze_level = self.symbol_info.freeze_level() * point

        min_distance = max(stop_level, freeze_level)

        if pos_type == 0:  # BUY
            if stop_price > entry - min_distance:
                self.logger.info(
                    f"Trade validation failed: stop price too close for BUY "
                    f"(min distance {min_distance})"
                )
                return False

        elif pos_type == 1:  # SELL
            if stop_price < entry + min_distance:
                self.logger.info(
                    f"Trade validation failed: stop price too close for SELL "
                    f"(min distance {min_distance})"
                )
                return False
        else:
            self.logger.error("Unknown MetaTrader 5 position type")
            return False

        return True
    
    
    def is_valid_sl(self, symbol: str, entry: float, sl: float, pos_type: int) -> bool:
        
        if not self.__is_valid_freezenstopslevel(symbol, entry, sl, pos_type): # check for stops and freeze levels
            return False
            
        if sl > 0:
            if pos_type == 0: # buy position
                
                if sl >= entry:
                    self.logger.info(f"Trade validation failed: Buy stop loss ({sl}) must be below order opening price ({entry})")
                    return False
                
            elif pos_type == 1: # sell position
                
                if sl <= entry:
                    self.logger.info(f"Trade validation failed: Sell stop loss ({sl}) must be above order opening price ({entry})")
                    return False
            
            else:
                self.logger.error("Unknown MetaTrader 5 position type")
                return False
        
        return True

    def is_valid_tp(self, symbol: str, entry: float, tp: float, pos_type: int) -> bool:
        
        if not self.__is_valid_freezenstopslevel(symbol, entry, tp, pos_type): # check for stops and freeze levels
            return False
        
        if pos_type == 0: # buy position
            if tp <= entry:
                self.logger.info(f"Trade validation failed: Buy take profit ({tp}) must be above order opening price ({entry})")
                return False
        elif pos_type == 1: # sell position
            if tp >= entry:
                self.logger.info(f"Trade validation failed: Sell take profit ({tp}) must be below order opening price ({entry})")
                return False
        else:
            self.logger.error("Unknown MetaTrader 5 position type")
            return False
        
        return True
    
    def _price_equal(self, a: float, b: float, eps: float = 1e-8) -> bool:
        return abs(a - b) <= eps

    def is_valid_entry(self, price: float, pos_type: int) -> bool:

        if pos_type == 0:  # BUY
            if not self._price_equal(price, self.ticks_info.ask):
                self.logger.info(
                    f"Trade validation failed: Buy price {price} != ask {self.ticks_info.ask}"
                )
                return False

        elif pos_type == 1:  # SELL
            if not self._price_equal(price, self.ticks_info.bid):
                self.logger.info(
                    f"Trade validation failed: Sell price {price} != bid {self.ticks_info.bid}"
                )
                return False
        else:
            self.logger.error("Unknown MetaTrader 5 position type")
            return False

        return True
    
    def is_there_enough_money(self, margin_required: float, free_margin: float) -> bool:
        
        if margin_required < 0:
            self.logger.info("Trade validation failed: Cannot calculate margin requirements")
            return False
        
        # Check free margin
        if margin_required > free_margin:
            self.logger.info(f'Trade validation failed: Not enough money to open trade. '
                f'Required: {margin_required:.2f}, '
                f'Free margin: {free_margin:.2f}')
            
            return False

        return True
    
    def all_validators(
        self,
        symbol: str,
        lotsize: float,
        entry: float,
        sl: float,
        tp: float,
        pos_type: int,
        margin_required: float,
        free_margin: float,
    ) -> bool:
        """
        Run all trade validations.

        Returns:
            bool: True if all checks pass, otherwise False.
        """

        validators = [
            lambda: self.is_valid_lotsize(lotsize),
            lambda: self.is_valid_entry(entry, pos_type),
            lambda: self.is_there_enough_money(margin_required, free_margin),
        ]

        # SL / TP are optional in MT5
        if sl > 0:
            validators.append(lambda: self.is_valid_sl(symbol, entry, sl, pos_type))

        if tp > 0:
            validators.append(lambda: self.is_valid_tp(symbol, entry, tp, pos_type))

        for validate in validators:
            if not validate():
                return False

        return True
