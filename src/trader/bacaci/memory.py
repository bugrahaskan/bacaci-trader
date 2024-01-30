import json
import time
import asyncio
import pandas as pd
from sklearn.preprocessing import StandardScaler, MinMaxScaler
import numpy as np
from pandas_ta import rsi as RSI

from .database import Database
from .data import Data
from .enums import Parameters
#import indicators as ind
#from .indicators import rsi as RSI

class Memory:

    def __init__(self, api, symbol):

        self.API = api
        self.SYMBOL = symbol
        self.INTERVAL = "1m"

        self.database = Database(
            db_name=Parameters.DATABASE.value
            )
        self.database.connect_db()

        self.table_name = Data.table_name(self.SYMBOL, self.INTERVAL, self.API)

        self.lock = asyncio.Lock()

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

        #loop = asyncio.new_event_loop()
        #loop.run_until_complete(self.mem())

    async def mem(self):

        # await asyncio.sleep(10) # wait before functioning

        while True:

            self.CURRENT_TIMESTAMP = int(time.time())

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
                    "5m": {},
                    "15m": {}
                },
                "current_state": {
                    "isGreen": None,
                    "isRed": None,
                    "isExtremum": None,
                    "isMax": None,
                    "isMin": None,
                    "rsi-1m": None,
                    "rsi-5m": None,
                    "rsi-15m": None,
                    "percent": None
                }
            }

            intervals = ['1s', '1m', '5m', '15m']
            #intervals = ['1s', '1m', '5m']

            async with self.lock:
                rows = [
                    self.database.fetch_rows(
                        Data.table_name(self.SYMBOL, intervals[0], self.API),
                        limit=600
                    ),
                    self.database.fetch_rows(
                        Data.table_name(self.SYMBOL, intervals[1], self.API),
                        limit=100
                    ),
                    self.database.fetch_rows(
                        Data.table_name(self.SYMBOL, intervals[2], self.API),
                        limit=50
                    ),
                    self.database.fetch_rows(
                        Data.table_name(self.SYMBOL, intervals[3], self.API),
                        limit=16
                    )
                ]

            dfs = [
                pd.DataFrame(
                    rows[0], columns=["timestamp","date","price"]
                ),
                pd.DataFrame(
                    # Data.generate_df(row)
                    rows[1], columns=["timestamp","date","open","high","low","close","volume"]
                ),
                pd.DataFrame(
                    # Data.generate_df(row)
                    rows[2], columns=["timestamp","date","open","high","low","close","volume"]
                ),
                pd.DataFrame(
                    # Data.generate_df(row)
                    rows[3], columns=["timestamp","date","open","high","low","close","volume"]
                )
            ]

            # to reconsider:

            '''# each 10 sec:
            #dfs[0] = dfs[0][ dfs[0]['timestamp'] % 10 == 0 ] # 10lu saniyelerin verileri
            #dfs[0] = dfs[0].loc[ dfs[0]['timestamp'] % 10 == (self.CURRENT_TIMESTAMP % 10) ] # son 10 saniyelerin verileri

            # each 10 sec back to 60 sec:
            selected_df_10s = dfs[0][ dfs[0]['timestamp'] % 10 == (self.CURRENT_TIMESTAMP%10) ]
            selected_df_back_10s = selected_df_10s.loc[ selected_df_10s['timestamp'] % 12 == (self.CURRENT_TIMESTAMP%12) ]

            # each 10 sec back to 60 sec:
            selected_df_1m = dfs[0][ dfs[0]['timestamp'] % 10 == (self.CURRENT_TIMESTAMP%10) ]
            selected_df_back_1m = selected_df_1m.loc[ selected_df_1m['timestamp'] % 60 == (self.CURRENT_TIMESTAMP%60) ]

            # each 10 sec back to 5*60 sec:
            selected_df_5m = dfs[0][ dfs[0]['timestamp'] % 10 == (self.CURRENT_TIMESTAMP%10) ]
            selected_df_back_5m = selected_df_5m.loc[ selected_df_5m['timestamp'] % 300 == (self.CURRENT_TIMESTAMP%300) ]

            # sum up volumes from 1s:
            grouped_sums_1m = []; num_rows_1m = len(dfs[0]); num_groups_1m = num_rows_1m // 60
            grouped_sums_5m = []; num_rows_5m = len(dfs[0]); num_groups_5m = num_rows_5m // 300

            for i in range(num_groups_1m):
                start = i * 60
                end = start + 60
                group = dfs[0]['volume'].iloc[start:end]
                group_sum = group.sum()
                grouped_sums_1m.append(group_sum)
                #np.append(grouped_sums_1m, group_sum)
            
            for i in range(num_groups_5m):
                start = i * 300
                end = start + 300
                group = dfs[0]['volume'].iloc[start:end]
                group_sum = group.sum()
                grouped_sums_5m.append(group_sum)
                #np.append(grouped_sums_5m, group_sum)
            
            grouped_sums_1m_array = np.array(grouped_sums_1m)
            grouped_sums_5m_array = np.array([None] * 80 + grouped_sums_5m) # astuce'''

            # real-time(intrabar) RSI with pandas_ta:
            '''rsi = [
                selected_df_10s.join(RSI(selected_df_10s['price'], length=14, sma=14)),
                selected_df_back_1m.join(RSI(selected_df_back_1m['close'], length=14, sma=14)),
                selected_df_back_5m.join(RSI(selected_df_back_5m['close'], length=14, sma=14))
            ]'''

            temp_df0 = dfs[0].copy()
            temp_df1 = dfs[1].copy()
            temp_df1.loc[len(dfs[1].index)] = { 'close': dfs[0]['price'].iloc[-1] }
            temp_df2 = dfs[2].copy()
            temp_df2.loc[len(dfs[2].index)] = { 'close': dfs[0]['price'].iloc[-1] }
            temp_df3 = dfs[3].copy()
            temp_df3.loc[len(dfs[3].index)] = { 'close': dfs[0]['price'].iloc[-1] }

            # bar RSI with pandas_ta:
            rsi = [
                temp_df0.join(RSI(dfs[0]['price'], length=14, sma=14)),
                temp_df1.join(RSI(temp_df1['close'], length=14, sma=14)),
                temp_df2.join(RSI(temp_df2['close'], length=14, sma=14)),
                temp_df3.join(RSI(temp_df3['close'], length=14, sma=14))
            ]

            '''rsi = [
                r.reset_index(drop=True) for r in rsi
            ]'''

            normalized_data = [
                pd.DataFrame(),
                pd.DataFrame(Memory.normalize_data(rsi[1]["volume"].values[:-1]), columns=['normalized_volume']),
                pd.DataFrame(Memory.normalize_data(rsi[2]["volume"].values[:-1]), columns=['normalized_volume']),
                pd.DataFrame(Memory.normalize_data(rsi[3]["volume"].values[:-1]), columns=['normalized_volume'])
            ]

            scaled_data = [
                pd.DataFrame(),
                Memory.scale_data(rsi[1]["volume"].iloc[:-1], name="volume"),
                Memory.scale_data(rsi[2]["volume"].iloc[:-1], name="volume"),
                Memory.scale_data(rsi[3]["volume"].iloc[:-1], name="volume")
            ]

            minmaxed_data = [
                pd.DataFrame(),
                pd.DataFrame(Memory.minmax_data(rsi[1]["volume"].iloc[:-1].values), columns=['minmax_volume']),
                pd.DataFrame(Memory.minmax_data(rsi[2]["volume"].iloc[:-1].values), columns=['minmax_volume']),
                pd.DataFrame(Memory.minmax_data(rsi[3]["volume"].iloc[:-1].values), columns=['minmax_volume'])
            ]

            data = []
            for i in range(len(rsi)):
                data.append(rsi[i].join(normalized_data[i]).join(scaled_data[i]).join(minmaxed_data[i]))

            '''writer = pd.ExcelWriter("coef.xlsx")

            test = pd.DataFrame(
                {
                    "date": data[1]["date"],
                    "rsi": data[1]["RSI_14"],
                    "minmax_volume": data[1]["minmax_volume"],
                    "coef": np.abs(data[1]["RSI_14"] - 50) * data[1]["minmax_volume"]
                }
            )

            test.to_excel(writer)
            writer.close()
            exit(0)'''

            # ekstremum modülü
            
            self.memory["current_date"] = int(time.time())

            self.memory["current_state"]["rsi-1m"] = data[1]["RSI_14"].iloc[-1]
            self.memory["current_state"]["rsi-5m"] = data[2]["RSI_14"].iloc[-1]
            self.memory["current_state"]["rsi-15m"] = data[3]["RSI_14"].iloc[-1]

            # add 1s.
            for i, row in data[0].iterrows():
                #if row[0] % 10 == 0: # remove if necessary
                self.memory["historical_prices"]["1s"][int(row.iloc[0])] = {
                    "t": int(row.iloc[0]),
                    "p": row.iloc[2],
                    "rsi": row.iloc[3],
                    "v": None # continuous kline where 'x': false
                }
            print("fetched 1s data")

            for i, row in data[1].iloc[:-1].iterrows():
                self.memory["historical_prices"]["1m"][int(row.iloc[0])] = {
                    "t": int(row.iloc[0]),
                    "o": row.iloc[2],
                    "h": row.iloc[3],
                    "l": row.iloc[4],
                    "c": row.iloc[5],
                    "v": row.iloc[6],
                    "rolling_v": None,
                    "rsi": row.iloc[7],
                    #"rsiUP": bool((normalized[0]['RSI_14'].iloc[i] - normalized[0]['RSI_14'].iloc[i-10]) > 0),
                    #"rsiUP": Memory.isRSIup_draft(normalized[0], row[0], 10),
                    "normalized_volume": row.iloc[8],
                    "scaled_volume": row.iloc[9],
                    "minmax_volume": row.iloc[10],
                    "coef": abs(row.iloc[7] - 50) * row.iloc[8],
                    "isMinLocal": None,
                    "isMaxLocal": None
                }
            
            

            for i, row in data[1].iloc[1:-2].iterrows():

                '''price_low_0, price_low_1, price_low_2 = 0, 0, 0
                price_high_0, price_high_1, price_high_2 = 0, 0, 0

                if Memory.isGreen(int(row.iloc[0]), Data.table_name(self.SYMBOL, intervals[1], self.API)):
                    price_low_1 = row.iloc[2]
                    price_high_1 = row.iloc[5]
                elif Memory.isRed(int(row.iloc[0]), Data.table_name(self.SYMBOL, intervals[1], self.API)):
                    price_low_1 = row.iloc[5]
                    price_high_1 = row.iloc[2]

                if Memory.isGreen(int(data[1].iloc[i-1,0]), Data.table_name(self.SYMBOL, intervals[1], self.API)):
                    price_low_0 = data[1].iloc[i-1,2]
                    price_high_0 = data[1].iloc[i-1,5]
                elif Memory.isRed(int(data[1].iloc[i-1,0]), Data.table_name(self.SYMBOL, intervals[1], self.API)):
                    price_low_0 = data[1].iloc[i-1,5]
                    price_high_0 = data[1].iloc[i-1,2]

                if Memory.isGreen(int(data[1].iloc[i+1,0]), Data.table_name(self.SYMBOL, intervals[1], self.API)):
                    price_low_2 = data[1].iloc[i+1,2]
                    price_high_2 = data[1].iloc[i+1,5]
                elif Memory.isRed(int(data[1].iloc[i+1,0]), Data.table_name(self.SYMBOL, intervals[1], self.API)):
                    price_low_2 = data[1].iloc[i+1,5]
                    price_high_2 = data[1].iloc[i+1,2]

                if price_low_1 <= price_low_0 and price_low_1 <= price_low_2:
                    self.memory["historical_prices"]["1m"][int(row.iloc[0])]["isMinLocal"] = True
                else:
                    self.memory["historical_prices"]["1m"][int(row.iloc[0])]["isMinLocal"] = False

                if price_high_1 >= price_high_0 and price_high_1 >= price_high_2:
                    self.memory["historical_prices"]["1m"][int(row.iloc[0])]["isMaxLocal"] = True
                else:
                    self.memory["historical_prices"]["1m"][int(row.iloc[0])]["isMaxLocal"] = False'''

                if row.iloc[4] <= data[1].iloc[i-1,4] and row.iloc[4] <= data[1].iloc[i+1,4]:
                    self.memory["historical_prices"]["1m"][int(row.iloc[0])]["isMinLocal"] = True
                else:
                    self.memory["historical_prices"]["1m"][int(row.iloc[0])]["isMinLocal"] = False

                if row.iloc[3] >= data[1].iloc[i-1,3] and row.iloc[3] >= data[1].iloc[i+1,3]:
                    self.memory["historical_prices"]["1m"][int(row.iloc[0])]["isMaxLocal"] = True
                else:
                    self.memory["historical_prices"]["1m"][int(row.iloc[0])]["isMaxLocal"] = False
            print("fetched 1m data")

            for i, row in data[2].iloc[:-1].iterrows():
                self.memory["historical_prices"]["5m"][int(row.iloc[0])] = {
                    "t": int(row.iloc[0]),
                    "o": row.iloc[2],
                    "h": row.iloc[3],
                    "l": row.iloc[4],
                    "c": row.iloc[5],
                    "v": row.iloc[6],
                    "rolling_v": None,
                    "rsi": row.iloc[7],
                    #"rsiUP": bool((normalized[1]['RSI_14'].iloc[i] - normalized[1]['RSI_14'].iloc[i-1]) > 0),
                    #"rsiUP": Memory.isRSIup_draft(normalized[1], row[0], 60),
                    "normalized_volume": row.iloc[8],
                    "scaled_volume": row.iloc[9],
                    "minmax_volume": row.iloc[10],
                    "coef": abs(row.iloc[7] - 50) * row.iloc[8],
                    "isMinLocal": None,
                    "isMaxLocal": None
                }
            
            for i, row in data[2].iloc[1:-2].iterrows():

                price_low_0, price_low_1, price_low_2 = 0, 0, 0
                price_high_0, price_high_1, price_high_2 = 0, 0, 0

                if Memory.isGreen(int(row.iloc[0]), Data.table_name(self.SYMBOL, intervals[2], self.API)):
                    price_low_1 = row.iloc[2]
                    price_high_1 = row.iloc[5]
                elif Memory.isRed(int(row.iloc[0]), Data.table_name(self.SYMBOL, intervals[2], self.API)):
                    price_low_1 = row.iloc[5]
                    price_high_1 = row.iloc[2]

                if Memory.isGreen(int(data[2].iloc[i-1,0]), Data.table_name(self.SYMBOL, intervals[2], self.API)):
                    price_low_0 = data[2].iloc[i-1,2]
                    price_high_0 = data[2].iloc[i-1,5]
                elif Memory.isRed(int(data[2].iloc[i-1,0]), Data.table_name(self.SYMBOL, intervals[2], self.API)):
                    price_low_0 = data[2].iloc[i-1,5]
                    price_high_0 = data[2].iloc[i-1,2]

                if Memory.isGreen(int(data[2].iloc[i+1,0]), Data.table_name(self.SYMBOL, intervals[2], self.API)):
                    price_low_2 = data[2].iloc[i+1,2]
                    price_high_2 = data[2].iloc[i+1,5]
                elif Memory.isRed(int(data[2].iloc[i+1,0]), Data.table_name(self.SYMBOL, intervals[2], self.API)):
                    price_low_2 = data[2].iloc[i+1,5]
                    price_high_2 = data[2].iloc[i+1,2]

                if price_low_1 <= price_low_0 and price_low_1 <= price_low_2:
                    self.memory["historical_prices"]["5m"][int(row.iloc[0])]["isMinLocal"] = True
                else:
                    self.memory["historical_prices"]["5m"][int(row.iloc[0])]["isMinLocal"] = False

                if price_high_1 >= price_high_0 and price_high_1 >= price_high_2:
                    self.memory["historical_prices"]["5m"][int(row.iloc[0])]["isMaxLocal"] = True
                else:
                    self.memory["historical_prices"]["5m"][int(row.iloc[0])]["isMaxLocal"] = False

                '''if row.iloc[5] <= data[2].iloc[i-1,5] and row.iloc[5] <= data[2].iloc[i+1,5]:
                    self.memory["historical_prices"]["5m"][int(row.iloc[0])]["isMinLocal"] = True
                else:
                    self.memory["historical_prices"]["5m"][int(row.iloc[0])]["isMinLocal"] = False'''
            print("fetched 5m data")
            # ...

            for i, row in data[3].iloc[:-1].iterrows():
                self.memory["historical_prices"]["15m"][int(row.iloc[0])] = {
                    "t": int(row.iloc[0]),
                    "o": row.iloc[2],
                    "h": row.iloc[3],
                    "l": row.iloc[4],
                    "c": row.iloc[5],
                    "v": row.iloc[6],
                    "rolling_v": None,
                    "rsi": row.iloc[7],
                    #"rsiUP": bool((normalized[1]['RSI_14'].iloc[i] - normalized[1]['RSI_14'].iloc[i-1]) > 0),
                    #"rsiUP": Memory.isRSIup_draft(normalized[1], row[0], 60),
                    "normalized_volume": None,
                    "scaled_volume": None,
                    "minmax_volume": None,
                    "coef": None,
                    "isMinLocal": None,
                    "isMaxLocal": None
                }
            print("fetched 15m data")

            async with self.lock:

                with open(f"memory_{self.SYMBOL}.json", "w") as memory:
                    memory.write(json.dumps(self.memory))
                    print("Memory written to file")

            await asyncio.sleep(1)

    async def mem_for_backtest(self):

        __gen = self.generate_data("1m", 1704632640, 1704643260)

        pass

    @staticmethod
    def isGreen(timestamp, table_name, database_name=Parameters.DATABASE.value):
        database = Database(database_name)
        row = database.fetch_rows(table_name, timestamp)

        if row[0][5] > row[0][2]:
            return True
        return False
    
    @staticmethod
    def isRed(timestamp, table_name, database_name=Parameters.DATABASE.value):
        database = Database(database_name)
        row = database.fetch_rows(table_name, timestamp)

        if row[0][5] <= row[0][2]:
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
    def minmax_data(data: np.array):
        # Create a MinMax Scaler
        scaler = MinMaxScaler()

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