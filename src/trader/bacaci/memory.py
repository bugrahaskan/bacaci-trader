import json
import time
import asyncio
import pandas as pd
from sklearn.preprocessing import StandardScaler, MinMaxScaler
import numpy as np

from .database import Database
from .data import Data
from .enums import Parameters
#import indicators as ind
from .indicators import rsi as RSI

class Memory:

    def __init__(self, api, symbol):

        self.API = api
        self.SYMBOL = symbol
        self.INTERVAL = "1m"
        self.CURRENT_TIMESTAMP = int(time.time()) - 1

        self.database = Database(
            db_name=Parameters.DATABASE.value
            )
        self.database.connect_db()

        self.table_name = Data.table_name(self.SYMBOL, self.INTERVAL, self.API)

        # Create JSON
        '''self.memory = {
            "meta": {
                "api": self.API,
                "symbol": self.SYMBOL,
                "interval": self.INTERVAL # ?
            },
            "current_date": self.CURRENT_TIMESTAMP,
            "historical_prices": {
                "1s": {}, # correct
                "1m": {},
                "5m": {}
            },
            "current_state": {
                "isGreen": None,
                "isRed": None,
                "isExtremum": None,
                "isMax": None,
                "isMin": None
            }
        }'''

        loop = asyncio.new_event_loop()
        loop.run_until_complete(self.test())

    async def test(self):

        # await asyncio.sleep(10) # wait before functioning

        while True:

            self.memory = {
                "meta": {
                    "api": self.API,
                    "symbol": self.SYMBOL,
                    "interval": self.INTERVAL # ?
                },
                "current_date": self.CURRENT_TIMESTAMP,
                "historical_prices": {
                    "1s": {}, # correct
                    "1m": {},
                    "5m": {}
                },
                "current_state": {
                    "isGreen": None,
                    "isRed": None,
                    "isExtremum": None,
                    "isMax": None,
                    "isMin": None
                }
            }

            #intervals = ['1s', '1m', '5m']
            intervals = ['1m', '5m']

            rows = [
                #self.database.fetch_rows(
                #    Data.table_name(self.SYMBOL, intervals[0], self.API),
                #    limit=6000
                #    #limit=1000
                #),
                self.database.fetch_rows(
                    Data.table_name(self.SYMBOL, intervals[0], self.API),
                    limit=100
                ),
                self.database.fetch_rows(
                    Data.table_name(self.SYMBOL, intervals[1], self.API),
                    limit=100
                )
            ]

            dfs = [
                pd.DataFrame(
                    # Data.generate_df(row)
                    row, columns=["timestamp","date","open","high","low","close","volume"]
                ) for row in rows
            ]

            # each 10 sec:
            #dfs[0] = dfs[0][ dfs[0]['timestamp'] % 10 == 0 ] # 10lu saniyelerin verileri
            #dfs[0] = dfs[0].loc[ dfs[0]['timestamp'] % 10 == (self.CURRENT_TIMESTAMP % 10) ] # son 10 saniyelerin verileri

            # each 10 sec back to 60 sec:
            #selected_df_10s = dfs[0][ dfs[0]['timestamp'] % 10 == (self.CURRENT_TIMESTAMP%10) ]
            #selected_df_back_10s = selected_df_10s.loc[ selected_df_10s['timestamp'] % 12 == (self.CURRENT_TIMESTAMP%12) ]

            rsi = [
                #RSI(dfs[0], periods=14*6, ema=True),
                #RSI(selected_df_back_10s, ema=True),
                RSI(dfs[0], ema=True),
                RSI(dfs[1], ema=True)
            ]
            
            normalized_data = [
                #Memory.normalize_data(rsi[0]["volume"], name="volume"),
                pd.DataFrame(Memory.normalize_data(rsi[0]["volume"].values)),
                pd.DataFrame(Memory.normalize_data(rsi[1]["volume"].values))
            ]

            scaled_data = [
                #Memory.scale_data(rsi[0]["volume"], name="volume"),
                Memory.scale_data(rsi[0]["volume"], name="volume"),
                Memory.scale_data(rsi[1]["volume"], name="volume")
            ]

            data = []
            for i in range(len(rsi)):
                data.append(rsi[i].join(normalized_data[i]).join(scaled_data[i]))
            
            # ekstremum modülü
            
            self.memory["current_date"] = int(time.time())

            # add 1s.
            '''for i, row in data[0].iterrows():
                #if row[0] % 10 == 0: # remove if necessary
                self.memory["historical_prices"]["1s"][row.iloc[0]] = {
                    "t": row.iloc[0],
                    "o": row.iloc[2],
                    "h": row.iloc[3],
                    "l": row.iloc[4],
                    "c": row.iloc[5],
                    "v": row.iloc[6],
                    "rolling_v": None,
                    "rsi": row.iloc[7],
                    #"rsiUP": bool((normalized[0]['RSI_14'].iloc[i] - normalized[0]['RSI_14'].iloc[i-10]) > 0),
                    #"rsiUP": Memory.isRSIup_draft(normalized[0], row[0], 10),
                    "normalized_volume": row.iloc[8]
                    #"scaled_volume": row.iloc[9]
                }
            print("fetched 1s data")'''

            for i, row in data[0].iterrows():
                self.memory["historical_prices"]["1m"][row.iloc[0]] = {
                    "t": row.iloc[0],
                    "o": row.iloc[2],
                    "h": row.iloc[3],
                    "l": row.iloc[4],
                    "c": row.iloc[5],
                    "v": row.iloc[6],
                    "rolling_v": None,
                    "rsi": row.iloc[7],
                    #"rsiUP": bool((normalized[0]['RSI_14'].iloc[i] - normalized[0]['RSI_14'].iloc[i-10]) > 0),
                    #"rsiUP": Memory.isRSIup_draft(normalized[0], row[0], 10),
                    "normalized_volume": row.iloc[8]
                    #"scaled_volume": row.iloc[9]
                }
            print("fetched 1m data")

            for i, row in data[1].iterrows():
                self.memory["historical_prices"]["5m"][row.iloc[0]] = {
                    "t": row.iloc[0],
                    "o": row.iloc[2],
                    "h": row.iloc[3],
                    "l": row.iloc[4],
                    "c": row.iloc[5],
                    "v": row.iloc[6],
                    "rolling_v": None,
                    "rsi": row.iloc[7],
                    #"rsiUP": bool((normalized[1]['RSI_14'].iloc[i] - normalized[1]['RSI_14'].iloc[i-1]) > 0),
                    #"rsiUP": Memory.isRSIup_draft(normalized[1], row[0], 60),
                    "normalized_volume": row.iloc[8]
                    #"scaled_volume": row.iloc[9]
                }
            print("fetched 5m data")
            # ...

            with open(f"memory_{self.SYMBOL}.json", "w") as memory:
                memory.write(json.dumps(self.memory))
                print("Memory written to file")

            await asyncio.sleep(10)

    @staticmethod
    def isGreen(timestamp, table_name, database_name=Parameters.DATABASE.value):
        database = Database(database_name)
        row = database.fetch_rows(table_name, timestamp)

        if row[5] > row[2]:
            return True
        return False
    
    @staticmethod
    def isRed(timestamp, table_name, database_name=Parameters.DATABASE.value):
        database = Database(database_name)
        row = database.fetch_rows(table_name, timestamp)

        if row[5] <= row[2]:
            return True
        return False

    @staticmethod
    def isRSIup(df, timestamp, offset):
        try:

            timestamp = float(timestamp)

            if isinstance(df.loc[ df["timestamp"] == (timestamp - offset)]["RSI_14"].values[0], float):
                current_rsi = df.loc[ df["timestamp"] == timestamp ]["RSI_14"].values[0]
                past_rsi = df.loc[ df["timestamp"] == (timestamp - offset) ]["RSI_14"].values[0]

                if current_rsi > past_rsi:
                    return True

                elif past_rsi > current_rsi:
                    return False
                
                else:
                    return 1

            #else:
            #    return 1
        except IndexError:
            return 2
    
    @staticmethod
    def isRSIup_draft(df, timestamp, offset):
    
        if df.isin(df.loc[ df["timestamp"] == (timestamp - offset) ]).all(axis=1).any():
        
            if isinstance(df.loc[ df["timestamp"] == (timestamp - offset)]["RSI_14"].values[0], float):
                current_rsi = df.loc[ df["timestamp"] == timestamp ]["RSI_14"].values[0]
                past_rsi = df.loc[ df["timestamp"] == (timestamp - offset) ]["RSI_14"].values[0]

                if current_rsi > past_rsi:
                    return True

                elif past_rsi > current_rsi:
                    return False

                else:
                    return 1
            
            else:
                return 2
        
        else:
            return 3

    @staticmethod
    def normalize_data_old(data: pd.Series, name):
        normalized_data = pd.Series(100 * ((data - data.min()) / (data.max() - data.min())), name=f"normalized_{name}")

        return normalized_data
    
    @staticmethod
    def normalize_data(data: np.array):
        # Create a StandardScaler
        scaler = StandardScaler()

        return scaler.fit_transform(data.reshape(-1,1))
    
    @staticmethod
    def scale_data(data, name):

        # Scale values over target_total value
        target_total = 100.0

        # Given data as Series of values, transform it to a List
        current_total = sum(data.to_list())

        # Calculate the scaling factor
        scaling_factor = target_total / current_total

        # Scale the volumes
        scaled_data = pd.Series([volume * scaling_factor for volume in data.to_list()], name=f"scaled_{name}")

        # Verify that the scaled volumes sum up to the target total (approximately 100)
        #scaled_total = sum(scaled_volumes)

        return scaled_data

    # if necessary
    @staticmethod
    def isVolumeSufficient(value):
        
        if value > 20:
            return True
        
        else:
            return False
    
    @staticmethod
    def slope():
        pass