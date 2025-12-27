from Trade.SymbolInfo import CSymbolInfo

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
        
        """Check if stop levels comply with broker requirements (stops levels and freeze levels) 
        """
        
        self.symbol_info.name(symbol)
        
        # Validate symbol
        if not self.symbol_info.select():
            self.logger.info(f"Failed to check stop level: Symbol {symbol}. MetaTrader5 error = {self.mt5_instance.last_error()}")
            return False
        
        # Check for stops level 
        stop_level = self.symbol_info.stops_level()
        
        if pos_type == 0: # buy position
            if stop_price > entry - stop_level * self.symbol_info.point():
                self.logger.info(f"Trade validation failed: Stop level too close. Must be at least {stop_level} points away")
                return False
        elif pos_type == 1:  # sell position type
            if stop_price < entry + stop_level * self.symbol_info.point():
                self.logger.info(f"Trade validation failed: Stop level too close. Must be at least {stop_level} points away")
                return False
        else:
            
            self.logger.error(f"Unknown MetaTrader 5 position type")
            return False
        
        # Check for freeze level
        
        freeze_level = self.symbol_info.freeze_level()
        
        if pos_type == "buy":
            if stop_price > entry - freeze_level * self.symbol_info.point():
                self.logger.info(f"Trade validation failed: Stop level too close. Must be at least {freeze_level} points away")
                return False
        else:  # sell
            if stop_price < entry + freeze_level * self.symbol_info.point():
                self.logger.info(f"Trade validation failed: Stop level too close. Must be at least {freeze_level} points away")
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
        
        if tp > 0:
            if pos_type == "buy" and tp <= entry:
                print(f"Trade validation failed: Buy take profit ({tp}) must be above order opening price ({entry})")
                return False
            if pos_type == "sell" and tp >= entry:
                print(f"Trade validation failed: Sell take profit ({tp}) must be below order opening price ({entry})")
                return False
        
        return True
            
    def is_valid_entry(self, price: float, pos_type: int) -> bool