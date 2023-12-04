import os
import json
import configparser
import pandas as pd
from pandas_ta import rsi as RSI
import numpy as np
import time
from scipy.signal import find_peaks
from scipy.stats import gaussian_kde
import matplotlib.pyplot as plt

from bacaci.data import Data
from bacaci.database import Database
import bacaci.indicators as ind
from bacaci.memory import Memory

from bacaci.indicators import HeikinAshi

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

    selected_df_10s = dfs[0][ dfs[0]['timestamp'] % 10 == (int(time.time())%10) ]

    temp_df1 = dfs[1]
    temp_df1.loc[len(dfs[1].index)] = { 'close': selected_df_10s['close'].iloc[-1] }
    temp_df2 = dfs[2]
    temp_df2.loc[len(dfs[2].index)] = { 'close': selected_df_10s['close'].iloc[-1] }

    #print(temp_df)

    rsi = [
        selected_df_10s.join(RSI(selected_df_10s['close'], length=14, sma=14)),
        dfs[1].join(RSI(temp_df1['close'], length=14, sma=14)),
        dfs[2].join(RSI(temp_df2['close'], length=14, sma=14))
        #ind.rsi(df) for df in dfs
    ]

    return rsi

dfs = read_data()
print(dfs[2])