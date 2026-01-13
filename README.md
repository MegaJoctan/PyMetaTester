<img width="1024" height="226" alt="1bba69da-cb6c-44ec-bea7-3b5d33981cd3" src="https://github.com/user-attachments/assets/f6b385db-f057-4042-9120-4b92352ce10e" />

## About the Project

A Python module for testing trading robots made using [https://www.mql5.com/en/docs/python_metatrader5](metatrader5) in Python.

## Getting started

Ensure you have the MetaTrader 5 desktop application then proceeed to install the dependencies used in this project in your Python virtual environment

```bash
pip install -r requirements.txt
```

# Running your First Robot in The Strategy Tester

### Step 1: Initialize the desired MetaTrader 5 terminal right after importing its module, alongside other useful Python modules for this project.

```python
import MetaTrader5 as mt5
from tester import Tester
from Trade.Trade import CTrade
import json
import os
import config

if not mt5.initialize(): # Initialize MetaTrader5 instance
    print(f"Failed to Initialize MetaTrader5. Error = {mt5.last_error()}")
    mt5.shutdown()
    quit()
```

### Step 2: Load configurations from a JSON file. *In this case configs/tester.json file*.

```python
try:
    with open(os.path.join(config.CONFIGS_DIR,'tester.json'), 'r', encoding='utf-8') as file: # reading a JSON file
        # Deserialize the file data into a Python object
        tester_configs = json.load(file)
except Exception as e:
    raise RuntimeError(e)
```

### Step 3: Initialize the Tester class, giving it configurations and an initialized MetaTrader 5 instance.

```python
tester = Tester(tester_config=tester_configs["tester"], mt5_instance=mt5) # very important
```

### Optionally, instantiate the CTrade class to make life much easier.
```python
m_trade = CTrade(simulator=tester, magic_number=magic_number, filling_type_symbol=symbol, deviation_points=slippage)
```

### Step 4: Write some trading strategy 

```python
# ---------------------- inputs ----------------------------

symbol = "EURUSD"
timeframe = "PERIOD_H1"
magic_number = 10012026
slippage = 100
sl = 1000
tp = 100

# ---------------------------------------------------------

symbol_info = tester.symbol_info(symbol=symbol) # symbol information

def pos_exists(magic: int, type: int) -> bool:

    for position in tester.positions_get():
        if position.type == type and position.magic == magic:
            return True
    
    return False

def on_tick():
    
    tick_info = tester.symbol_info_tick(symbol=symbol)
    
    ask = tick_info.ask
    bid = tick_info.bid
    
    pts = symbol_info.point
    
    if not pos_exists(magic=magic_number, type=mt5.POSITION_TYPE_BUY): # If a position of such kind doesn't exist
        m_trade.buy(volume=0.1, symbol=symbol, price=ask, sl=ask-sl*pts, tp=ask+tp*pts, comment="Tester buy") # we open a buy position
    
    if not pos_exists(magic=magic_number, type=mt5.POSITION_TYPE_SELL): # If a position of such kind doesn't exist
        m_trade.sell(volume=0.1, symbol=symbol, price=bid, sl=bid+sl*pts, tp=bid-tp*pts, comment="Tester sell") # we open a sell position
```

### Step 5: Call the main trading function into action on every tick, similarly to the [OnTick function in MQL5](https://www.mql5.com/en/docs/event_handlers/ontick)

```python
tester.OnTick(ontick_func=on_tick) # very important!
```

## More information about the project

- [https://www.mql5.com/en/articles/18971](https://www.mql5.com/en/articles/18971)
- [https://www.mql5.com/en/articles/20455](https://www.mql5.com/en/articles/20455)
- [https://www.mql5.com/en/articles/20782](https://www.mql5.com/en/articles/20782)
- [https://www.mql5.com/en/articles/20917](https://www.mql5.com/en/articles/20917)