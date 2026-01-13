import MetaTrader5 as mt5
from Trade.Trade import CTrade
from datetime import datetime, timedelta
import time
import pytz
from tester import Tester
from Trade.Trade import CTrade

if not mt5.initialize(): # Initialize MetaTrader5 instance
    print(f"Failed to Initialize MetaTrader5. Error = {mt5.last_error()}")
    mt5.shutdown()
    quit()