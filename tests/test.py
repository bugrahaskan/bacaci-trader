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

# Example usage
initial_stop_price = df[0]['close'].iloc[0]  # Set an initial stop-loss price
trailing_percent = 2.0  # Set the trailing stop percentage

trailing_stop = TrailingStop(trailing_percent, initial_stop_price)

'''SLOPE DEV'''
def tan(x1, y1, x2, y2):

    m = (y2 - y1) / (x2 - x1)

    return m

m = tan(
    df[0]['timestamp'].iloc[0],
    df[0]['volume'].iloc[0],
    df[0]['timestamp'].iloc[2],
    df[0]['volume'].iloc[2]
)

'''GENERATE COEFF'''
def generate_coef(df, i):

    return abs(df['RSI_14'].iloc[i] - 50) * df['volume'].iloc[i]

def variation_rate(old_value, new_value):

    return ((new_value - old_value) / old_value) * 100

date = []
coef = []
taux = [None]

for i, row in df[0].iterrows():
    print(row['date'], generate_coef(df[0], i))
    date.append(row['date'])
    coef.append(generate_coef(df[0], i))

for i, row in df[0].iloc[1:].iterrows():
    taux.append(variation_rate(coef[i-1], coef[i]))

res = pd.DataFrame(
    {
        'date': date,
        'coef': coef,
        'taux': taux
    }
)

#w = pd.ExcelWriter("res.xlsx")
#res.to_excel(w)
#w.close()

print(res.loc[ res['coef'] > 55000 ])