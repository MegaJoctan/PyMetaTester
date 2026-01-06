import MetaTrader5 as mt5
from Trade.Trade import CTrade
from datetime import datetime, timedelta
import time
import pytz
from simulator import Simulator, CTrade

if not mt5.initialize(): # Initialize MetaTrader5 instance
    print(f"Failed to Initialize MetaTrader5. Error = {mt5.last_error()}")
    mt5.shutdown()
    quit()

sim = Simulator(simulator_name="MySimulator", mt5_instance=mt5, deposit=1078.30, leverage="1:500")

symbol = "EURUSD"
timeframe = mt5.TIMEFRAME_H1

m_trade = CTrade(simulator=sim, magic_number=112233, filling_type_symbol=symbol, deviation_points=100)


mt5_ticks = mt5.symbol_info_tick(symbol) # tick source
sim.TickUpdate(symbol=symbol, tick=mt5_ticks) # very important

tick_from_sim = sim.symbol_info_tick(symbol=symbol) # we get ticks back from a class

ask = tick_from_sim.ask
bid = tick_from_sim.bid

symbol_info = sim.symbol_info(symbol=symbol)
lotsize = symbol_info.volume_min

"""
m_trade.buy(
    volume=lotsize,
    symbol=symbol,
    price=ask,
    sl=ask - 100 * symbol_info.point,
    tp=ask + 150 * symbol_info.point,
    comment="Market Buy"
)

m_trade.sell(
    volume=lotsize,
    symbol=symbol,
    price=bid,
    sl=bid + 100 * symbol_info.point,
    tp=bid - 150 * symbol_info.point,
    comment="Market Sell"
)

buy_limit_price = ask - 200 * symbol_info.point

m_trade.buy_limit(
    volume=lotsize,
    symbol=symbol,
    price=buy_limit_price,
    sl=buy_limit_price - 100 * symbol_info.point,
    tp=buy_limit_price + 200 * symbol_info.point,
    comment="Buy Limit"
)

sell_limit_price = bid + 200 * symbol_info.point

m_trade.sell_limit(
    volume=lotsize,
    symbol=symbol,
    price=sell_limit_price,
    sl=sell_limit_price + 100 * symbol_info.point,
    tp=sell_limit_price - 200 * symbol_info.point,
    comment="Sell Limit"
)

buy_stop_price = ask + 150 * symbol_info.point

m_trade.buy_stop(
    volume=lotsize,
    symbol=symbol,
    price=buy_stop_price,
    sl=buy_stop_price - 100 * symbol_info.point,
    tp=buy_stop_price + 300 * symbol_info.point,
    comment="Buy Stop"
)

sell_stop_price = bid - 150 * symbol_info.point

m_trade.sell_stop(
    volume=lotsize,
    symbol=symbol,
    price=sell_stop_price,
    sl=sell_stop_price + 100 * symbol_info.point,
    tp=sell_stop_price - 300 * symbol_info.point,
    comment="Sell Stop"
)
"""


# print(f"positions in a simulator = {sim.positions_total()}:\n",sim.positions_get())
# print(f"orders in a simulator = {sim.orders_total()}:\n", sim.orders_get())
"""

m_trade.buy(volume=lotsize, symbol=symbol, price=ask, comment="buy pos")
m_trade.sell(volume=lotsize, symbol=symbol, price=bid, comment="sell pos")

print(f"positions in a simulator = {sim.positions_total()}:\n",sim.positions_get())

positions = sim.positions_get()
for pos in positions:
    # if pos.symbol == symbol and pos.type == sim.mt5_instance.POSITION_TYPE_BUY: # close a buy position
    #     m_trade.position_close(ticket=pos.ticket, deviation=10) 
        
    if pos.sl == 0:
        if pos.type == sim.mt5_instance.POSITION_TYPE_BUY:
            m_trade.position_modify(ticket=pos.ticket, sl=pos.price_open - 100 * symbol_info.point, tp=pos.tp) 
        if pos.type == sim.mt5_instance.POSITION_TYPE_SELL:
            m_trade.position_modify(ticket=pos.ticket, sl=pos.price_open + 100 * symbol_info.point, tp=pos.tp) 
        
print("positions after modification\n: ", sim.positions_get())
"""

m_trade.buy_stop(symbol=symbol, volume=symbol_info.volume_min, price=ask+500*symbol_info.point)

for order in sim.orders_get():
    
    print("order curr price: ", order.price_open)
    
    m_trade.order_modify(ticket=order.ticket, price=order.price_open+10*symbol_info.point, sl=order.sl, tp=order.tp)
    
    print("order moved 10 points upward", order.price_open)
    if m_trade.order_delete(ticket=order.ticket) is None:
        continue
    
    print("orders remaining: ", sim.orders_total())

# for pos in sim.positions_get():
#     m_trade.position_close(ticket=pos.ticket)

# print("After close positions total in simulator: ", sim.positions_total())

# now = datetime.fromtimestamp(mt5_ticks.time)
# print("deals:\n",sim.history_deals_get(date_from=now-timedelta(days=1), date_to=now))

"""
sim.Start(IS_TESTER=False) # start the simulator in real-time trading

m_trade.buy(volume=0.01, symbol=symbol, price=ask)

print("positions total in MT5: ", sim.positions_total())

for pos in sim.positions_get(symbol=symbol):
    m_trade.position_close(ticket=pos.ticket)

print("after close positions total in MT5: ", sim.positions_total())
"""