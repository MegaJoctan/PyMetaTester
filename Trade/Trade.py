import MetaTrader5 as mt5
import error_description
from Trade.SymbolInfo import CSymbolInfo
from datetime import datetime, timezone

class CTrade:
    
    def __init__(self):
        
        self.magic_number = None
        self.deviation_points = None
        self.filling_type = None
        
    def set_magicnumber(self, magic_number: int):
        
        self.magic_number = magic_number
        
    def set_deviation_in_points(self, deviation_points: int):
        
        self.deviation_points = deviation_points
    
    def set_filling_type_by_symbol(self, symbol: int):
        
        self.filling_type = self._get_type_filling(symbol)
        
        if self.filling_type == -1:
            print(f"Failed to set filling type for '{symbol}'")
        
    def _get_type_filling(self, symbol):
        
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            print(f"Failed to get symbol info for {symbol}")
        
        filling_map = {
            1: mt5.ORDER_FILLING_FOK,
            2: mt5.ORDER_FILLING_IOC,
            4: mt5.ORDER_FILLING_BOC,
            8: mt5.ORDER_FILLING_RETURN
        }
        
        return filling_map.get(symbol_info.filling_mode, f"Unknown Filling type")
    
    
    def position_open(self, symbol: str, volume: float, order_type: int, price: float, sl: float=0.0, tp: float=0.0, comment: str="") -> bool:
        
        """
        Open a market position (instant execution).
        
        Executes either a buy or sell order at the current market price. This is for immediate
        position opening, not pending orders.
        
        Args:
            symbol: Trading symbol (e.g., "EURUSD", "GBPUSD")
            volume: Trade volume in lots (e.g., 0.1 for micro lot)
            order_type: Trade direction (either ORDER_TYPE_BUY or ORDER_TYPE_SELL)
            price: Execution price. For market orders, this should be the current:
                - Ask price for BUY orders
                - Bid price for SELL orders
            sl: Stop loss price (set to 0.0 to disable)
            tp: Take profit price (set to 0.0 to disable)
            comment: Optional order comment (max 31 characters, will be truncated automatically)
        
        Returns:
            bool: True if position was opened successfully, False otherwise
        """
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": self.deviation_points,
            "magic": self.magic_number,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling":  self.filling_type,
        }
        
        # send a trading request
        result = mt5.order_send(request)
        
        if result is None:
            print(f"order_send() failed, error: {mt5.last_error()}")
            return False
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"Position send failed retcode: {result.retcode} description: {error_description.trade_server_return_code_description(result.retcode)}")
            return False
        
        print(f"Position Opened successfully!")
        return True
    
    
    def order_open(self, symbol: str, volume: float, order_type: int, price: float, sl: float = 0.0, tp: float = 0.0, type_time: int = mt5.ORDER_TIME_GTC, expiration: datetime = None, comment: str = "") -> bool:
        
        """
        Opens a pending order with full control over order parameters.
        
        Args:
            symbol: Trading symbol (e.g., "EURUSD")
            volume: Order volume in lots
            order_type: Order type (ORDER_TYPE_BUY_LIMIT, ORDER_TYPE_SELL_STOP, etc.)
            price: Activation price for pending order
            sl: Stop loss price (0 to disable)
            tp: Take profit price (0 to disable)
            type_time: Order expiration type (default: ORDER_TIME_GTC). Possible values:
                    - ORDER_TIME_GTC (Good-Til-Canceled)
                    - ORDER_TIME_DAY (Good for current day)
                    - ORDER_TIME_SPECIFIED (expires at specific datetime)
                    - ORDER_TIME_SPECIFIED_DAY (expires at end of specified day)
            expiration: Expiration datetime (required for ORDER_TIME_SPECIFIED types)
            comment: Optional order comment (max 31 characters)
        
        Returns:
            bool: True if order was placed successfully, False otherwise
        """
        
        # Check symbol info
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            print(f"Symbol {symbol} not found")
            return False

        if not symbol_info.visible:
            if not mt5.symbol_select(symbol, True):
                print(f"Failed to select symbol {symbol}")
                return False
        
        # Validate expiration for time-specific orders
        if type_time in (mt5.ORDER_TIME_SPECIFIED, mt5.ORDER_TIME_SPECIFIED_DAY) and expiration is None:
            print(f"Expiration required for order type {type_time}")
            return False
        
        request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": self.deviation_points,
            "magic": self.magic_number,
            "comment": comment[:31],  # MT5 comment max length is 31 chars
            "type_time": type_time,
            "type_filling": self.filling_type,
        }
        
        # Add expiration if required
        if type_time in (mt5.ORDER_TIME_SPECIFIED, mt5.ORDER_TIME_SPECIFIED_DAY) and expiration is not None:
            
            # Convert to broker's expected format (UTC timestamp in milliseconds)
            
            expiration_utc = expiration.astimezone(timezone.utc) if expiration.tzinfo else expiration.replace(tzinfo=timezone.utc)
            request["expiration"] = int(expiration_utc.timestamp() * 1000)
            
            
        # Send order
        result = mt5.order_send(request)

        if result is None:
            print(f"order_send() failed, error: {mt5.last_error()}")
            return False

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"order_send() failed retcode: {result.retcode} description: {error_description.trade_server_return_code_description(result.retcode)}")
            return False
        
        print(f"Order #{result.order} opened successfully!")
        return True
    
    
    def buy(self, volume: float, symbol: str, price: float, sl: float=0.0, tp: float=0.0, comment: str="") -> bool:
        
        """
        Opens a buy (market) position.
        
        Args:
            volume: Trade volume (lot size)
            symbol: Trading symbol (e.g., "EURUSD")
            price: Execution price
            sl: Stop loss price (optional, default=0.0)
            tp: Take profit price (optional, default=0.0)
            comment: Position comment (optional, default="")
        
        Returns:
            bool: True if order was sent successfully, False otherwise
        """
    
        return self.position_open(symbol=symbol, volume=volume, order_type=mt5.ORDER_TYPE_BUY, price=price, sl=sl, tp=tp, comment=comment)

    def sell(self, volume: float, symbol: str, price: float, sl: float=0.0, tp: float=0.0, comment: str="") -> bool:
        
        """
        Opens a sell (market) position.
        
        Args:
            volume: Trade volume (lot size)
            symbol: Trading symbol (e.g., "EURUSD")
            price: Execution price
            sl: Stop loss price (optional, default=0.0)
            tp: Take profit price (optional, default=0.0)
            comment: Position comment (optional, default="")
        
        Returns:
            bool: True if order was sent successfully, False otherwise
        """
        
        return self.position_open(symbol=symbol, volume=volume, order_type=mt5.ORDER_TYPE_SELL, price=price, sl=sl, tp=tp, comment=comment)
    
    def buy_limit(self, volume: float, price: float, symbol: str, sl: float=0.0, tp: float=0.0, type_time: float=mt5.ORDER_TIME_GTC, expiration: datetime=None, comment: str="") -> bool:
        
        """
        Places a buy limit pending order.
        
        Args:
            volume: Trade volume (lot size)
            price: Execution price
            symbol: Trading symbol (e.g., "EURUSD")
            sl: Stop loss price (optional, default=0.0)
            tp: Take profit price (optional, default=0.0)
            type_time: Order expiration type (default: ORDER_TIME_GTC). Possible values:
                  - ORDER_TIME_GTC (Good-Til-Canceled)
                  - ORDER_TIME_DAY (Good for current day)
                  - ORDER_TIME_SPECIFIED (expires at specific datetime)
                  - ORDER_TIME_SPECIFIED_DAY (expires at end of specified day)
            expiration: Expiration datetime (required for ORDER_TIME_SPECIFIED types)
            comment: Order comment (optional, default="")
        
        Returns:
            bool: True if order was placed successfully, False otherwise
        """
        
        return self.order_open(symbol=symbol, volume=volume, order_type=mt5.ORDER_TYPE_BUY_LIMIT, price=price, sl=sl, tp=tp, type_time=type_time, expiration=expiration, comment=comment)
        
    def sell_limit(self, volume: float, price: float, symbol: str, sl: float=0.0, tp: float=0.0, type_time: float=mt5.ORDER_TIME_GTC, expiration: datetime=None, comment: str="") -> bool:
            
        """
        Places a sell limit pending order.
        
        Args:
            volume: Trade volume (lot size)
            price: Execution price
            symbol: Trading symbol (e.g., "EURUSD")
            sl: Stop loss price (optional, default=0.0)
            tp: Take profit price (optional, default=0.0)
            type_time: Order expiration type (default: ORDER_TIME_GTC). Possible values:
                  - ORDER_TIME_GTC (Good-Til-Canceled)
                  - ORDER_TIME_DAY (Good for current day)
                  - ORDER_TIME_SPECIFIED (expires at specific datetime)
                  - ORDER_TIME_SPECIFIED_DAY (expires at end of specified day)
            expiration: Expiration datetime (required for ORDER_TIME_SPECIFIED types)
            comment: Order comment (optional, default="")
        
        Returns:
            bool: True if order was placed successfully, False otherwise
        """

        return self.order_open(symbol=symbol, volume=volume, order_type=mt5.ORDER_TYPE_SELL_LIMIT, price=price, sl=sl, tp=tp, type_time=type_time, expiration=expiration, comment=comment)
        
    def buy_stop(self, volume: float, price: float, symbol: str, sl: float=0.0, tp: float=0.0, type_time: float=mt5.ORDER_TIME_GTC, expiration: datetime=None, comment: str="") -> bool:

        """
        Places a buy stop pending order.
        
        Args:
            volume: Trade volume (lot size)
            price: Execution price
            symbol: Trading symbol (e.g., "EURUSD")
            sl: Stop loss price (optional, default=0.0)
            tp: Take profit price (optional, default=0.0)
            type_time: Order expiration type (default: ORDER_TIME_GTC). Possible values:
                  - ORDER_TIME_GTC (Good-Til-Canceled)
                  - ORDER_TIME_DAY (Good for current day)
                  - ORDER_TIME_SPECIFIED (expires at specific datetime)
                  - ORDER_TIME_SPECIFIED_DAY (expires at end of specified day)
            expiration: Expiration datetime (required for ORDER_TIME_SPECIFIED types)
            comment: Order comment (optional, default="")
        
        Returns:
            bool: True if order was placed successfully, False otherwise
        """
        
        return self.order_open(symbol=symbol, volume=volume, order_type=mt5.ORDER_TYPE_BUY_STOP, price=price, sl=sl, tp=tp, type_time=type_time, expiration=expiration, comment=comment)
        
    def sell_stop(self, volume: float, price: float, symbol: str, sl: float=0.0, tp: float=0.0, type_time: float=mt5.ORDER_TIME_GTC, expiration: datetime=None, comment: str="") -> bool:
        
        """
        Places a sell stop pending order.
        
        Args:
            volume: Trade volume (lot size)
            price: Execution price
            symbol: Trading symbol (e.g., "EURUSD")
            sl: Stop loss price (optional, default=0.0)
            tp: Take profit price (optional, default=0.0)
            type_time: Order expiration type (default: ORDER_TIME_GTC). Possible values:
                  - ORDER_TIME_GTC (Good-Til-Canceled)
                  - ORDER_TIME_DAY (Good for current day)
                  - ORDER_TIME_SPECIFIED (expires at specific datetime)
                  - ORDER_TIME_SPECIFIED_DAY (expires at end of specified day)
            expiration: Expiration datetime (required for ORDER_TIME_SPECIFIED types)
            comment: Order comment (optional, default="")
        
        Returns:
            bool: True if order was placed successfully, False otherwise
        """
        
        return self.order_open(symbol=symbol, volume=volume, order_type=mt5.ORDER_TYPE_SELL_STOP, price=price, sl=sl, tp=tp, type_time=type_time, expiration=expiration, comment=comment)
        
    def buy_stop_limit(self, volume: float, price: float, symbol: str, sl: float=0.0, tp: float=0.0, type_time: float=mt5.ORDER_TIME_GTC, expiration: datetime=None, comment: str="") -> bool:
        
        """
        Places a buy stop limit pending order.
        
        Args:
            volume: Trade volume (lot size)
            price: Execution price
            symbol: Trading symbol (e.g., "EURUSD")
            sl: Stop loss price (optional, default=0.0)
            tp: Take profit price (optional, default=0.0)
            type_time: Order expiration type (default: ORDER_TIME_GTC). Possible values:
                  - ORDER_TIME_GTC (Good-Til-Canceled)
                  - ORDER_TIME_DAY (Good for current day)
                  - ORDER_TIME_SPECIFIED (expires at specific datetime)
                  - ORDER_TIME_SPECIFIED_DAY (expires at end of specified day)
            expiration: Expiration datetime (required for ORDER_TIME_SPECIFIED types)
            comment: Order comment (optional, default="")
        
        Returns:
            bool: True if order was placed successfully, False otherwise
        """
        
        return self.order_open(symbol=symbol, volume=volume, order_type=mt5.ORDER_TYPE_BUY_STOP_LIMIT, price=price, sl=sl, tp=tp, type_time=type_time, expiration=expiration, comment=comment)
        
    def sell_stop_limit(self, volume: float, price: float, symbol: str, sl: float=0.0, tp: float=0.0, type_time: float=mt5.ORDER_TIME_GTC, expiration: datetime=None, comment: str="") -> bool:
        
        """
        Places a sell stop limit pending order.
        
        Args:
            volume: Trade volume (lot size)
            price: Execution price
            symbol: Trading symbol (e.g., "EURUSD")
            sl: Stop loss price (optional, default=0.0)
            tp: Take profit price (optional, default=0.0)
            type_time: Order expiration type (default: ORDER_TIME_GTC). Possible values:
                  - ORDER_TIME_GTC (Good-Til-Canceled)
                  - ORDER_TIME_DAY (Good for current day)
                  - ORDER_TIME_SPECIFIED (expires at specific datetime)
                  - ORDER_TIME_SPECIFIED_DAY (expires at end of specified day)
            expiration: Expiration datetime (required for ORDER_TIME_SPECIFIED types)
            comment: Order comment (optional, default="")
        
        Returns:
            bool: True if order was placed successfully, False otherwise
        """
        
        return self.order_open(symbol=symbol, volume=volume, order_type=mt5.ORDER_TYPE_SELL_STOP_LIMIT, price=price, sl=sl, tp=tp, type_time=type_time, expiration=expiration, comment=comment)


    def position_close(self, ticket: int, deviation: float=float("nan")) -> bool:
        
        """
        Closes an open position by ticket number.
        
        Args:
            ticket: Position ticket number
            deviation: Maximum price deviation in points (optional)
        
        Returns:
            bool: True if position was closed successfully, False otherwise
        
        Raises:
            Prints error message if position not found or close fails
        """
            
        # Select position by ticket
        if not mt5.positions_get(ticket=ticket):
            print(f"Position with ticket {ticket} not found.")
            return False

        position = mt5.positions_get(ticket=ticket)[0]
        symbol = position.symbol
        volume = position.volume
        position_type = position.type  # 0=BUY, 1=SELL

        # Get close price (BID for buy, ASK for sell)
        price = mt5.symbol_info_tick(symbol).bid if position_type == mt5.POSITION_TYPE_BUY else mt5.symbol_info_tick(symbol).ask

        # Set close order type
        order_type = mt5.ORDER_TYPE_SELL if position_type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": ticket,
            "symbol": symbol,
            "volume": volume,
            "magic": self.magic_number,
            "type": order_type,
            "price": price,
            "deviation": deviation if not isinstance(deviation, float) or not str(deviation) == 'nan' else self.deviation_points, 
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": self.filling_type,
        }

        # Send the close request
        result = mt5.order_send(request)

        # Check result
        if result is None:
            print(f"order_send() failed, error: {mt5.last_error()}")
            return False

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"Close failed. retcode: {result.retcode} description: {error_description.trade_server_return_code_description(result.retcode)}")
            return False

        print(f"Position {ticket} closed successfully!")
        return True
    
    def order_delete(self, ticket: int) -> bool:
        
        """
        Deletes a pending order by ticket number.
        
        Args:
            ticket: Order ticket number
        
        Returns:
            bool: True if order was deleted successfully, False otherwise
        
        Raises:
            Prints error message if deletion fails
        """
    
        request = {
            "action": mt5.TRADE_ACTION_REMOVE,
            "order": ticket,
            "magic": self.magic_number
        }

        # Send the delete request
        result = mt5.order_send(request)

        # Check result
        if result is None:
            print(f"order_delete() failed, error: {mt5.last_error()}")
            return False

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"Failed to delete an order with ticket = {ticket}, retcode: {result.retcode} description: {error_description.trade_server_return_code_description(result.retcode)}")
            return False

        print(f"Order {ticket} deleted successfully!")
        return True
            

    def position_modify(self, ticket: int, sl: float, tp: float) -> bool:
        
        """
        Modifies stop loss and take profit of an open position.
        
        Args:
            ticket: Position ticket number
            sl: New stop loss price
            tp: New take profit price
        
        Returns:
            bool: True if modification was successful, False otherwise
        
        Raises:
            Prints error message if position not found or modification fails
        """
        
        # Select position by ticket
        if not mt5.positions_get(ticket=ticket):
            print(f"Position with ticket {ticket} not found.")
            return False

        position = mt5.positions_get(ticket=ticket)[0]
        symbol = position.symbol
        
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "magic": self.magic_number,
            "symbol": symbol,
            "sl": sl,
            "tp": tp
        }
        
        # send a trading request
        result = mt5.order_send(request)
        
        if result is None:
            print(f"order_modify() failed, error: {mt5.last_error()}")
            return False
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"Position modify failed retcode: {result.retcode} description: {error_description.trade_server_return_code_description(result.retcode)}")
            return False
        
        print(f"Position {ticket} modified successfully!")
        return True
    
    def order_modify(self, ticket: int, price: float, sl: float, tp: float, type_time: int = mt5.ORDER_TIME_GTC, expiration: datetime = None, stoplimit: float = 0.0) -> bool:
        
        """
        Modify parameters of a pending order with full control similar to MQL5's OrderModify.
        
        Args:
            ticket: Order ticket number
            price: New activation price for the pending order
            sl: New stop loss price (0 to remove)
            tp: New take profit price (0 to remove)
            type_time: Order expiration type (ORDER_TIME_GTC, ORDER_TIME_DAY, etc.)
            expiration: Order expiration time (required for ORDER_TIME_SPECIFIED)
            stoplimit: StopLimit price for STOP_LIMIT orders
        
        Returns:
            bool: True if order was modified successfully, False otherwise
        
        Raises:
            Prints error message if modification fails
        """
        
        # Get the order by ticket
        order = mt5.orders_get(ticket=ticket)
        if not order:
            print(f"Order with ticket {ticket} not found")
            return False
        
        order = order[0]  # Get the first (and only) order
        
        request = {
            "action": mt5.TRADE_ACTION_MODIFY,
            "order": ticket,
            "price": price,
            "sl": sl,
            "tp": tp,
            "symbol": order.symbol,
            "type": order.type,
            "magic": self.magic_number,
            "type_time": type_time,
            "type_filling": self.filling_type,
        }
        
        # Add expiration if specified (for ORDER_TIME_SPECIFIED)
        if type_time == mt5.ORDER_TIME_SPECIFIED:
            if expiration is None:
                print("Error: expiration must be specified for ORDER_TIME_SPECIFIED")
                return False
            
            request["expiration"] = expiration
        
        # Add stoplimit for STOP_LIMIT orders
        if order.type in (mt5.ORDER_TYPE_BUY_STOP_LIMIT, mt5.ORDER_TYPE_SELL_STOP_LIMIT):
            request["stoplimit"] = stoplimit

        # Send the modification request
        result = mt5.order_send(request)

        # Check result
        if result is None:
            print(f"order_modify() failed, error: {mt5.last_error()}")
            return False

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"Failed to modify order {ticket}, retcode: {result.retcode} description: {error_description.trade_server_return_code_description(result.retcode)}")
            return False

        print(f"Order {ticket} modified successfully!")
        return True