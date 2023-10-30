import os
import json
import configparser
import pandas as pd
import pandas_ta as ta

from bacaci.data import Data
from bacaci.database import Database
import bacaci.indicators as ind
from bacaci.memory import Memory

class TrailingStop:

    def __init__(self, trailing_percent, initial_stop):
        self.trailing_percent = trailing_percent  # Trailing stop percentage
        self.initial_stop = initial_stop  # Initial stop-loss price
        self.current_stop = initial_stop  # Current stop-loss price

    def update_stop(self, current_price):
        # Calculate the new stop-loss price based on the trailing percent
        trailing_distance = (current_price - self.initial_stop) * (self.trailing_percent / 100)
        new_stop = current_price - trailing_distance

        # Update the stop-loss if the new price is higher (for long positions)
        if new_stop > self.current_stop:
            self.current_stop = new_stop

        return self.current_stop
    
def read_data():
    database = Database(
        db_name="data.db"
        )
    database.connect_db()

    config = configparser.ConfigParser()
    config.read('config.ini')
    int_list = [value for key, value in config['Intervals'].items()]

    rows = [
        database.fetch_rows(
            Data.table_name("ETHUSDT", i, "Binance"),
            limit=10000
        ) for i in int_list
    ]

    dfs = [
        pd.DataFrame(
            # Data.generate_df(row)
            row, columns=["timestamp","date","open","high","low","close","volume"]
        ) for row in rows
    ]

    rsi = [
        ind.rsi(df) for df in dfs
    ]

    return rsi

df = read_data()
print(df)

Memory.normalize_data()