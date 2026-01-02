from collections import namedtuple
import MetaTrader5 as mt5

class TradeValidators:
    def __init__(self, 
                 symbol_info: namedtuple, 
                 ticks_info: any, 
                 logger: any,
                 mt5_instance: mt5=mt5):
        
        self.symbol_info = symbol_info
        self.ticks_info = ticks_info
        self.logger = logger
        self.mt5_instance = mt5_instance
        
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
        
    def is_valid_lotsize(self, lotsize: float) -> bool:
        
        # Validate lotsize
        
        if lotsize < self.symbol_info.volume_min: # check if the received lotsize is smaller than minimum accepted lot of a symbol
            self.logger.info(f"Trade validation failed: lotsize ({lotsize}) is less than minimum allowed ({self.symbol_info.volume_min})")
            return False
        
        if lotsize > self.symbol_info.volume_max: # check if the received lotsize is greater than the maximum accepted lot
            self.logger.info(f"Trade validation failed: lotsize ({lotsize}) is greater than maximum allowed ({self.symbol_info.volume_max})")
            return False
        
        step_count = lotsize / self.symbol_info.volume_step 
        
        if abs(step_count - round(step_count)) > 1e-7: # check if the stoploss is a multiple of the step size
            self.logger.info(f"Trade validation failed: lotsize ({lotsize}) must be a multiple of step size ({self.symbol_info.volume_step})")
            return False

        return True
    
    def is_valid_freeze_level(self, entry: float, stop_price: float, order_type: int) -> bool:
        """
        Check SYMBOL_TRADE_FREEZE_LEVEL for pending orders and open positions.
        Logs detailed reasons when modification is not allowed.
        """

        freeze_level = self.symbol_info.trade_freeze_level
        if freeze_level <= 0:
            return True  # No freeze restriction

        point = self.symbol_info.point
        freeze_distance = freeze_level * point

        bid = self.ticks_info.bid
        ask = self.ticks_info.ask

        def log_fail(msg: str, dist: float):
            self.logger.info(
                f"{msg} | distance={dist/point:.1f} pts < "
                f"freeze_level={freeze_level} pts"
            )

        # ---------------- Pending Orders ----------------

        if order_type == self.mt5_instance.ORDER_TYPE_BUY_LIMIT:
            dist = ask - entry
            if dist < freeze_distance:
                log_fail("BuyLimit cannot be modified: Ask - OpenPrice", dist)
                return False
            return True

        if order_type == self.mt5_instance.ORDER_TYPE_SELL_LIMIT:
            dist = entry - bid
            if dist < freeze_distance:
                log_fail("SellLimit cannot be modified: OpenPrice - Bid", dist)
                return False
            return True

        if order_type == self.mt5_instance.ORDER_TYPE_BUY_STOP:
            dist = entry - ask
            if dist < freeze_distance:
                log_fail("BuyStop cannot be modified: OpenPrice - Ask", dist)
                return False
            return True

        if order_type == self.mt5_instance.ORDER_TYPE_SELL_STOP:
            dist = bid - entry
            if dist < freeze_distance:
                log_fail("SellStop cannot be modified: Bid - OpenPrice", dist)
                return False
            return True

        # ---------------- Open Positions (SL / TP modification) ----------------

        # Buy position
        if order_type == self.mt5_instance.ORDER_TYPE_BUY:
            if stop_price <= 0:
                return True

            if stop_price < entry:  # StopLoss
                dist = bid - stop_price
                if dist < freeze_distance:
                    log_fail("Buy position SL cannot be modified: Bid - SL", dist)
                    return False
            else:  # TakeProfit
                dist = stop_price - bid
                if dist < freeze_distance:
                    log_fail("Buy position TP cannot be modified: TP - Bid", dist)
                    return False

            return True

        # Sell position
        if order_type == self.mt5_instance.ORDER_TYPE_SELL:
            if stop_price <= 0:
                return True

            if stop_price > entry:  # StopLoss
                dist = stop_price - ask
                if dist < freeze_distance:
                    log_fail("Sell position SL cannot be modified: SL - Ask", dist)
                    return False
            else:  # TakeProfit
                dist = ask - stop_price
                if dist < freeze_distance:
                    log_fail("Sell position TP cannot be modified: Ask - TP", dist)
                    return False

            return True

        self.logger.error("Unknown MetaTrader 5 order type")
        return False
    
    def is_valid_stops_level(self, entry: float, stop_price: float, order_type: int) -> bool:
        
        point = self.symbol_info.point
        stop_level   = self.symbol_info.trade_stops_level * point
        
        if order_type in self.BUY_ACTIONS:  # BUY
            if stop_price > entry - stop_level:
                self.logger.info(f"Either SL or TP is too close to the market for a Buy-based order. Min allowed distance = {stop_level}")
                return False

        if order_type in self.SELL_ACTIONS:  # SELL
            if stop_price < entry + stop_level:
                self.logger.info(f"Either SL or TP is too close to the market for a Sell-based order. Min allowed distance = {stop_level}")
                return False
        else:
            self.logger.error("Unknown MetaTrader 5 order type")
            return False

        return True
    
    def is_max_orders_reached(self, open_orders: int, ac_limit_orders: int) -> bool:
        
        if open_orders >= ac_limit_orders:
            self.logger.critical(f"Pending Orders limit of {ac_limit_orders} is reached!")
            return True
        
        return False
    
    def is_symbol_volume_reached(self, symbol_volume: float, volume_limit: float) -> bool:
    
        if symbol_volume >= volume_limit and volume_limit > 0:
            self.logger.critical(f"Symbol Volume limit of {volume_limit} is reached!")
            return True
        
        return False
    
    def is_valid_sl(self, entry: float, sl: float, order_type: int) -> bool:
        
        if not self.is_valid_stops_level(entry, sl, order_type): # check for stops and freeze levels
            return False
            
        if sl > 0:
            if order_type in self.BUY_ACTIONS: # buy action
                
                if sl >= entry:
                    self.logger.info(f"Trade validation failed: Buy-based order's stop loss ({sl}) must be below order opening price ({entry})")
                    return False
                
            elif order_type in self.SELL_ACTIONS: # sell action
                
                if sl <= entry:
                    self.logger.info(f"Trade validation failed: Sell-based order's stop loss ({sl}) must be above order opening price ({entry})")
                    return False
            
            else:
                self.logger.error("Unknown MetaTrader 5 order type")
                return False
        
        return True

    def is_valid_tp(self, entry: float, tp: float, order_type: int) -> bool:
        
        if not self.is_valid_stops_level(entry, tp, order_type): # check for stops and freeze levels
            return False
        
        if order_type in self.BUY_ACTIONS: # buy position
            if tp <= entry:
                self.logger.info(f"Trade validation failed: Buy-based order's take profit ({tp}) must be above order opening price ({entry})")
                return False
        elif order_type in self.SELL_ACTIONS: # sell position
            if tp >= entry:
                self.logger.info(f"Trade validation failed: Sell-based order's take profit ({tp}) must be below order opening price ({entry})")
                return False
        else:
            self.logger.error("Unknown MetaTrader 5 order type")
            return False
        
        return True
    
    @staticmethod    
    def price_equal(a: float, b: float, eps: float = 1e-8) -> bool:
        return abs(a - b) <= eps

    def is_valid_entry(self, price: float, order_type: int) -> bool:
        
        eps = pow(10, -self.symbol_info.digits)
        if order_type == self.mt5_instance.ORDER_TYPE_BUY:  # BUY
            if not self.price_equal(a=price, b=self.ticks_info.ask, eps=eps):
                self.logger.info(f"Trade validation failed: Buy price {price} != ask {self.ticks_info.ask}")
                return False

        elif order_type == self.mt5_instance.ORDER_TYPE_SELL:  # SELL
            if not self.price_equal(a=price, b=self.ticks_info.bid, eps=eps):
                self.logger.info(f"Trade validation failed: Sell price {price} != bid {self.ticks_info.bid}")
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
        lotsize: float,
        entry: float,
        sl: float,
        tp: float,
        order_type: int,
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
            lambda: self.is_valid_entry(entry, order_type),
            lambda: True if order_type not in (self.mt5_instance.ORDER_TYPE_BUY, self.mt5_instance.ORDER_TYPE_SELL) else self.is_there_enough_money(margin_required, free_margin), # We don't validate this for pending orders
        ]

        # SL / TP are optional in MT5
        if sl > 0:
            validators.append(lambda: self.is_valid_sl(entry, sl, order_type))

        if tp > 0:
            validators.append(lambda: self.is_valid_tp(entry, tp, order_type))

        for validate in validators:
            if not validate():
                return False

        return True
