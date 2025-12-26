import MetaTrader5 as mt5
from Trade.SymbolInfo import CSymbolInfo
from Trade.Trade import CTrade
from datetime import datetime, timedelta
import time
import pytz
from simulator import Simulator


if not mt5.initialize(): # Initialize MetaTrader5 instance
    print(f"Failed to Initialize MetaTrader5. Error = {mt5.last_error()}")
    mt5.shutdown()
    quit()


sim = Simulator(simulator_name="MySimulator", mt5_instance=mt5, deposit=1078.30, leverage="1:500")

start = datetime(2025, 1, 1)
end = datetime(2025, 1, 5)

bars = 10
symbol = "EURUSD"
timeframe = mt5.TIMEFRAME_H1

sim.Start(IS_TESTER=True)
# rates = sim.copy_rates_from(symbol=symbol, timeframe=mt5.TIMEFRAME_H1, date_from=start, count=bars)
# rates = sim.copy_rates_from_pos(symbol=symbol, timeframe=timeframe, start_pos=0, count=bars)
# rates = sim.copy_rates_range(symbol=symbol, timeframe=timeframe, date_from=start, date_to=end)
# print("is_tester=true\n", rates)

ticks = sim.copy_ticks_from(symbol=symbol, date_from=start.replace(month=12, hour=0, minute=0), count=bars)
print("is_tester=true\n", ticks)

sim.Start(IS_TESTER=False) # start the simulator in real-time trading

# rates = sim.copy_rates_from_pos(symbol=symbol, timeframe=timeframe, start_pos=0, count=bars)
# rates = sim.copy_rates_from(symbol=symbol, timeframe=timeframe, date_from=start, count=bars)
# rates = sim.copy_rates_range(symbol=symbol, timeframe=timeframe, date_from=start, date_to=end)
# print("is_tester=false\n",rates)

ticks = sim.copy_ticks_from(symbol=symbol, date_from=start.replace(month=12, hour=0, minute=0), count=bars)
print("is_tester=false\n", ticks)

"""    
magic_number = 123456
slippage = 10

sim.set_magicnumber(magic_number=magic_number) #sets the magic number of a simulator
sim.set_deviation_in_points(deviation_points=slippage) # sets slippage of the simulator

symbol = symbol
m_symbol = CSymbolInfo(mt5_instance=mt5)
m_symbol.name(symbol_name=symbol) # sets the symbol name for the class CSymbolInfo


def is_position_exists(type: str) -> bool:
    
    for pos in sim.get_positions():
        if pos["magic"] == magic_number and pos["symbol"] == symbol and pos["type"] == type:
            return True # position exists
        
    return False
    
def close_positions(type: str):
    
    for pos in sim.get_positions():
        if pos["magic"] == magic_number and pos["symbol"] == symbol and pos["type"] == type:
            sim.position_close(pos)

while True:
    
    sim.monitor_pending_orders()
    sim.monitor_positions(verbose=False)
    sim.monitor_account(verbose=False)
    
    sim.run_toolbox_gui()  # Run the simulator toolbox GUI
    
    if m_symbol.refresh_rates() is None: # Get recent ticks data from MetaTrader5
        # print("failed to get recent ticks data")
        continue
        
    if not is_position_exists("buy"): # open a buy trade in a simulator if it doesn't exist
        sim.buy(volume=0.1, symbol=symbol, open_price=m_symbol.ask())
    
    close_positions("buy") # close all buy positions
    
    if not is_position_exists("sell"): # open a sell trade in a simulator if it doesn't exist
        sim.sell(volume=0.1, symbol=symbol, open_price=m_symbol.bid())
    
    time.sleep(1) # sleep for one second    

# Market Orders

sim.buy(volume=0.1, symbol=symbol, open_price=m_symbol.ask())
sim.sell(volume=0.1, symbol=symbol, open_price=m_symbol.bid())

m_trade.buy(volume=0.1, symbol=symbol, price=m_symbol.ask())
m_trade.sell(volume=0.1, symbol=symbol, price=m_symbol.bid())


# Pending Orders

expiry = datetime.now(tz=pytz.UTC) + timedelta(days=1)
price_gap = 0.0005

# Buy Stop: place above current ask
sim.buy_stop(volume=0.1, symbol=symbol, open_price=m_symbol.ask() + price_gap, sl=0.0, tp=0.0,
             comment="Buy Stop Example", expiry_date=expiry, expiration_mode="daily")

m_trade.buy_stop(volume=0.1, symbol=symbol, price=m_symbol.ask() + price_gap)

# Buy Limit: place below current bid
sim.buy_limit(volume=0.1, symbol=symbol, open_price=m_symbol.bid() - price_gap, sl=0.0, tp=0.0,
              comment="Buy Limit Example", expiry_date=expiry, expiration_mode="daily_excluding_stops")

m_trade.buy_limit(volume=0.1, symbol=symbol, price=m_symbol.bid() - price_gap)

# Sell Stop: place below current bid

sim.sell_stop(volume=0.1, symbol=symbol, open_price=m_symbol.bid() - price_gap, sl=0.0, tp=0.0,
              comment="Sell Stop Example", expiry_date=expiry, expiration_mode="gtc")

m_trade.sell_stop(volume=0.1, symbol=symbol, price=m_symbol.ask() - price_gap)

# Sell Limit: place above current ask
sim.sell_limit(volume=0.1, symbol=symbol, open_price=m_symbol.ask() + price_gap, sl=0.0, tp=0.0,
               comment="Sell Limit Example", expiry_date=expiry, expiration_mode="gtc")

m_trade.sell_limit(volume=0.1, symbol=symbol, price=m_symbol.bid() + price_gap)

while True: # constantly monitor trades and account metrics
    
    sim.monitor_pending_orders()
    sim.monitor_positions(verbose=False)
    sim.monitor_account(verbose=False)
    
    # sim.run_toolbox_gui()  # Run the simulator toolbox GUI
    
    time.sleep(1) # sleep for one second
"""