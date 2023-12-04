import pandas as pd
import os
import time
import configparser
from datetime import datetime, timedelta
import numpy as np
from pandas_ta import rsi as RSI

from .wallet.wallet import Wallet
from .database import Database
from .data import Data
from .enums import Parameters
from .memory import Memory
#import indicators as ind
#from .indicators import rsi as RSI, HeikinAshi

from .wallet.wallet import TrailingStop, StopLoss, MyTrailingStop, TakeProfit

class Backtest:

    def __init__(self, api, symbol):

        print("Proceeding to Backtest...")
        time.sleep(1)

        self.API = api
        self.SYMBOL = symbol
        self.qty = Parameters.QUANTITY.value

        self.wallet = Wallet(
            api=self.API,
            symbol=self.SYMBOL,
            test_mode=True
            )

        self.database = Database(
            db_name=Parameters.DATABASE.value
            )
        self.database.connect_db()
        
        test_15min = 90 * 24 * 4 + 10
        test_5min = 1 * (90 * 24 * 12) + 10
        test_1min = 3 * 24 * 60 + 10

        #df0 = pd.read_csv('NQZ2 Index-1min-t.csv')
        #df1 = pd.read_csv('NQZ2 Index-5min-t.csv')
        #rsi0 = RSI(df0)
        #rsi1 = RSI(df1)
        #res = self.backtest_4_1min_5min_stabil_rsi_DEV(df=[rsi0,rsi1])

        res = self.backtest_dummy(df=self.read_data(test_1min))
        #res = self.backtest_dummy(df=self.read_data(1000))

        self.write_to_excel(res)

    def write_to_excel(self, dfs):
        '''
        dfs: a list of different dataframes
        '''

        self.OUTPUT_FILE = f"/output/data_{self.API}_{self.SYMBOL}.xlsx"
        self.WRITER = pd.ExcelWriter(os.getcwd()+self.OUTPUT_FILE)

        for index, item in enumerate(dfs):
            item.to_excel(self.WRITER, sheet_name=f'data_{self.SYMBOL}_{index}', index=False)

        df_orders = pd.DataFrame.from_dict(self.wallet.orders, orient='index')
        df_orders.to_excel(self.WRITER, sheet_name='orders', index=False)

        self.WRITER.close()

    def read_data(self, limit):
        config = configparser.ConfigParser()
        config.read('config.ini')
        int_list = [value for key, value in config['Intervals'].items()]
        #Or
        #intervals = ['1s', '1m', '5m']

        rows = [
                self.database.fetch_rows(
                    Data.table_name(self.SYMBOL, i, self.API),
                    limit=limit
                ) for i in int_list
            ]
        
        dfs = [
                pd.DataFrame(
                    # Data.generate_df(row)
                    row, columns=["timestamp","date","open","high","low","close","volume"]
                ) for row in rows
            ]
        
        rsi = [
                df.join(RSI(df['close'], length=14, sma=14)) for df in dfs
                #RSI(df) for df in dfs
            ]

        # other check functions
        # write to excel
        self.write_to_excel(rsi)

        return rsi
    
    def backtest_dummy(self, df):

        for i, row in df[1].iloc[100:-1].iterrows():

            if not self.wallet.is_open():
                # check start conditions
                #print(Memory.normalize_data(df[1]['volume'].iloc[i-100:i], name="volume").iloc[-1])
                
                print(i, df[1]['date'].iloc[i], df[1]['volume'].iloc[i])
                print(Memory.scale_data(df[1]["volume"].iloc[i-99:i+1], name="volume"))
                print(Memory.scale_data(df[1]['volume'].iloc[i-99:i+1], name="volume").iloc[-1])
                print("\n")
            
            elif self.wallet.is_open():
                # check stop conditions
                print(i)

        return [ df[0], df[1] ]
    
    def backtest_1(self, df):

        # find bars where RSI >= 70
        filtered_70_df = df[0][df[0]['RSI_14'] >= (70 - 3)]
        filtered_70_index = filtered_70_df.index.tolist()

        # find bars where RSI <= 30
        filtered_30_df = df[0][df[0]['RSI_14'] <= (30 + 3)]
        filtered_30_index = filtered_30_df.index.tolist()

        param_j = -1

        for i, row in df[0].iloc[9:].iterrows():

            if not self.wallet.is_open():

                if row.name in filtered_70_index and i > param_j:

                    #abs(df[1]['RSI_14'][ df[1]['timestamp'] <= df[0]['timestamp'].iloc[i] ].iloc[-1] - 70) <= 3.

                    if Memory.normalize_data(df[0]['volume'].iloc[i-9:i+1], name="volume").iloc[-1] >= 75 and df[0]['volume'].iloc[i-9:i+1].sum() >= 10*3000:
                    #if Memory.scale_data(df[0]['volume'].iloc[i-9:i+1], name="volume").iloc[-1] >= 25:

                        for j, row_j in df[0].iloc[i+1:].iterrows():

                            if row_j['RSI_14'] - df[0]['RSI_14'].iloc[j-1] < 0:
                                # close[i]'den al, open[j]'den sat
                                print("Conditions satisfied, proceeding...")

                                param_i = i
                                param_j = j

                                break
                        
                        self.wallet.open_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )
                        print(self.wallet.orders)

                elif row.name in filtered_30_index and i > param_j:

                    if Memory.normalize_data(df[0]['volume'].iloc[i-9:i+1], name="volume").iloc[-1] >= 75 and df[0]['volume'].iloc[i-9:i+1].sum() >= 10*3000:
                    #if Memory.scale_data(df[0]['volume'].iloc[i-9:i+1], name="volume").iloc[-1] >= 25:

                        for j, row_j in df[0].iloc[i+1:-1].iterrows():

                            if df[0]['RSI_14'].iloc[j-1] - row_j['RSI_14'] < 0:
                                # close[i]'den al, open[j]'den sat
                                print("Conditions satisfied, proceeding...")

                                param_i = i
                                param_j = j

                                break
                        
                        self.wallet.open_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1], # we have 1min lag
                            date=df[0]['date'].iloc[i+1]
                        )
                        print(self.wallet.orders)

                else:
                    print("...")

            elif self.wallet.is_open():
                
                print("waiting for close conditions")

                if self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_SHORT.value:

                    if df[0]['date'].iloc[param_i] > self.wallet.orders[self.wallet.INDEX]["DateOpen"] and self.wallet.stop_loss(df[0], i, 0.01):

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[param_i+1],
                            date=df[0]['date'].iloc[param_i+1]
                        )
                        
                    else:

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[param_j+1],
                            date=df[0]['date'].iloc[param_j+1]
                        )

                elif self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_LONG.value:

                    if df[0]['date'].iloc[param_i] > self.wallet.orders[self.wallet.INDEX]["DateOpen"] and self.wallet.stop_loss(df[0], i, 0.01):
                        
                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[param_i+1],
                            date=df[0]['date'].iloc[param_i+1]
                        )

                    else:

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[param_j+1],
                            date=df[0]['date'].iloc[param_j+1]
                        )

        return [ df[0], df[1] ]
    
    def backtest_1_rsi_stop_loss(self, df):

        # find bars where RSI >= 70
        filtered_70_df = df[0][df[0]['RSI_14'] >= (70 - 3)]
        filtered_70_index = filtered_70_df.index.tolist()

        # find bars where RSI <= 30
        filtered_30_df = df[0][df[0]['RSI_14'] <= (30 + 3)]
        filtered_30_index = filtered_30_df.index.tolist()

        for i, row in df[0].iloc[9:-1].iterrows():

            if not self.wallet.is_open():

                if row.name in filtered_70_index:

                    #if Memory.normalize_data(df[0]['volume'].iloc[i-9:i+1], name="volume").iloc[-1] >= 75 and df[0]['volume'].iloc[i-9:i+1].sum() >= 10*3000:
                    #if Memory.scale_data(df[0]['volume'].iloc[i-99:i+1], name="volume").iloc[-1] >= 10:
                    if Memory.normalize_data(df[0]['volume'].iloc[i-9:i+1].values)[-1][0] > 2 and df[0]['volume'].iloc[i-9:i+1].sum() >= 10*3000:

                        self.wallet.open_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        # stop loss:
                        stop_loss = StopLoss(df[0]['low'].iloc[i-5:i+1].min())

                        print(self.wallet.orders)

                elif row.name in filtered_30_index:

                    #if Memory.normalize_data(df[0]['volume'].iloc[i-9:i+1], name="volume").iloc[-1] >= 75 and df[0]['volume'].iloc[i-9:i+1].sum() >= 10*3000:
                    #if Memory.scale_data(df[0]['volume'].iloc[i-99:i+1], name="volume").iloc[-1] >= 10:
                    if Memory.normalize_data(df[0]['volume'].iloc[i-9:i+1].values)[-1][0] > 2 and df[0]['volume'].iloc[i-9:i+1].sum() >= 10*3000:

                        self.wallet.open_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        # stop loss:
                        stop_loss = StopLoss(df[0]['high'].iloc[i-5:i+1].max())

                        print(self.wallet.orders)

                else:
                    print("...")

            elif self.wallet.is_open():
                
                print("waiting for close conditions")

                if self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_SHORT.value:

                    # extra condition:
                    if df[0]['RSI_14'].iloc[i] >= df[0]['RSI_14'].iloc[i-3:i+1].min():

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )
                    
                    elif stop_loss.check_trigger(row['close'], Parameters.TYPE_SHORT.value):

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                elif self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_LONG.value:

                    # extra condition:
                    if df[0]['RSI_14'].iloc[i] <= df[0]['RSI_14'].iloc[i-3:i+1].max():

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )
                    
                    elif stop_loss.check_trigger(row['close'], Parameters.TYPE_LONG.value):
                        
                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

        return [ df[0], df[1] ]
    
    def test(self, df):

        # find bars where RSI >= 70
        filtered_70_df = df[1][ (df[1]['RSI_14'] >= (70 - 3)) & (df[1]['RSI_14'] <= (70 + 1)) ] # +/-4
        filtered_70_index = filtered_70_df.index.tolist()

        # find bars where RSI <= 30
        filtered_30_df = df[1][ (df[1]['RSI_14'] <= (30 + 3)) & (df[1]['RSI_14'] >= (30 - 1)) ] # +/-4
        filtered_30_index = filtered_30_df.index.tolist()

        #for i, row in df[1][ df[1]['timestamp'] >= 1688634300 ].iterrows():
        for i, row in df[1].iloc[9:-1].iterrows():
            
            if not self.wallet.is_open():

                if row.name in filtered_70_index and Memory.normalize_data(df[1]['volume'].iloc[i-9:i+1].values)[-1][0] < 0 and df[0]['volume'].iloc[i-9:i+1].sum() <= 10*2000:
                    
                    print("Conditions satisfied, proceeding...")

                    self.wallet.open_position(
                        side="SELL",
                        quantity=self.qty,
                        price=df[1]['open'].iloc[i+1],
                        date=df[1]['date'].iloc[i+1]
                    )

                    # trailing stop:
                    trailing_stop = MyTrailingStop(row['close'] + 3.)
                    #trailing_stop = MyTrailingStop(df[1]['high'].iloc[i-9:i].max())

                    # stop loss:
                    stop_loss = StopLoss(df[1]['high'].iloc[i-9:i].max() * (1. - .3)) # * (1. + .3)
                    #stop_loss = StopLoss(df[1]['close'].iloc[i] + 2.)

                    print(self.wallet.orders)
                    print(f"SHORT position {df[1]['date'].iloc[i+1]} at {df[1]['open'].iloc[i+1]}")
                    #time.sleep(1)
                
                elif row.name in filtered_30_index and Memory.normalize_data(df[1]['volume'].iloc[i-9:i+1].values)[-1][0] < 0 and df[0]['volume'].iloc[i-9:i+1].sum() <= 10*2000:

                    print("Conditions satisfied, proceeding...")

                    self.wallet.open_position(
                        side="BUY",
                        quantity=self.qty,
                        price=df[1]['open'].iloc[i+1],
                        date=df[1]['date'].iloc[i+1]
                    )

                    # trailing stop
                    trailing_stop = MyTrailingStop(row['close'] - 3.)
                    #trailing_stop = MyTrailingStop(df[1]['low'].iloc[i-9:i].min())

                    # stop loss:
                    stop_loss = StopLoss(df[1]['low'].iloc[i-9:i].min() * (1. + .3)) # * (1. - .3)
                    #stop_loss = StopLoss(df[1]['close'].iloc[i] - 2.)

                    print(self.wallet.orders)
                    print(f"LONG position {df[1]['date'].iloc[i+1]} at {df[1]['open'].iloc[i+1]}")
                    #time.sleep(1)

                else:
                    print("...")

            elif self.wallet.is_open():

                print("waiting for close conditions")
                
                if self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_LONG.value:

                    trailing_stop.update_stop(row['close'], Parameters.TYPE_LONG.value)

                    if self.wallet.orders[self.wallet.INDEX]["Open"] + 2. < row['close'] and trailing_stop.check_trigger(row['close'], Parameters.TYPE_LONG.value):

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[1]["open"].iloc[i+1],
                            date=df[1]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "trailing stop"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[1]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'

                    elif self.wallet.orders[self.wallet.INDEX]["Open"] > row['close'] and stop_loss.check_trigger(row['close'], Parameters.TYPE_LONG.value):

                        self.wallet.close_position(
                                side="SELL",
                                quantity=self.qty,
                                price=df[1]["open"].iloc[i+1],
                                date=df[1]['date'].iloc[i+1]
                            )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "stop loss"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[1]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'

                elif self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_SHORT.value:

                    trailing_stop.update_stop(row['close'], Parameters.TYPE_SHORT.value)

                    if self.wallet.orders[self.wallet.INDEX]["Open"] - 2. > row['close'] and trailing_stop.check_trigger(row['close'], Parameters.TYPE_SHORT.value):

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[1]["open"].iloc[i+1],
                            date=df[1]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "trailing stop"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[1]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'                 

                    elif self.wallet.orders[self.wallet.INDEX]["Open"] < row['close'] and stop_loss.check_trigger(row['close'], Parameters.TYPE_SHORT.value):

                        self.wallet.close_position(
                                side="BUY",
                                quantity=self.qty,
                                price=df[1]["open"].iloc[i+1],
                                date=df[1]['date'].iloc[i+1]
                            )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "stop loss"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[1]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'

        return [ df[0], df[1] ]

    def test_stop_loss(self, df):

        # find bars where RSI >= 70
        filtered_70_df = df[1][df[1]['RSI_14'] >= (70 - 0)] # +/-4
        filtered_70_index = filtered_70_df.index.tolist()

        # find bars where RSI <= 30
        filtered_30_df = df[1][df[1]['RSI_14'] <= (30 + 0)] # +/-4
        filtered_30_index = filtered_30_df.index.tolist()

        #for i, row in df[1][ df[1]['timestamp'] >= 1688634300 ].iterrows():
        for i, row in df[1].iloc[9:-1].iterrows():

            if not self.wallet.is_open():
                
                if row.name in filtered_70_index and Memory.normalize_data(df[1]['volume'].iloc[i-9:i+1].values)[-1][0] < 0 and df[0]['volume'].iloc[i-9:i+1].sum() <= 10*2000:
                    
                    print("Conditions satisfied, proceeding...")

                    self.wallet.open_position(
                        side="SELL",
                        quantity=self.qty,
                        price=df[1]['open'].iloc[i+1],
                        date=df[1]['date'].iloc[i+1]
                    )

                    # stop loss:
                    #stop_loss = StopLoss(df[1]['high'].iloc[i-9:i].max() * (1. + .3)) # * 1.1
                    stop_loss = StopLoss(df[1]['close'].iloc[i] + 5.)

                    print(self.wallet.orders)
                    print(f"SHORT position {df[1]['date'].iloc[i+1]} at {df[1]['open'].iloc[i+1]}")
                    #time.sleep(1)

                elif row.name in filtered_30_index and Memory.normalize_data(df[1]['volume'].iloc[i-9:i+1].values)[-1][0] < 0 and df[0]['volume'].iloc[i-9:i+1].sum() <= 10*2000:

                    print("Conditions satisfied, proceeding...")

                    self.wallet.open_position(
                        side="BUY",
                        quantity=self.qty,
                        price=df[1]['open'].iloc[i+1],
                        date=df[1]['date'].iloc[i+1]
                    )

                    # stop loss:
                    #stop_loss = StopLoss(df[1]['low'].iloc[i-9:i].min() * (1. - .3)) # * 1.1
                    stop_loss = StopLoss(df[1]['close'].iloc[i] - 5.)

                    print(self.wallet.orders)
                    print(f"LONG position {df[1]['date'].iloc[i+1]} at {df[1]['open'].iloc[i+1]}")
                    #time.sleep(1)

            elif self.wallet.is_open():

                print("waiting for close conditions")
                
                if self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_LONG.value:
                    
                    if stop_loss.check_trigger(row['close'], Parameters.TYPE_LONG.value):

                        self.wallet.close_position(
                                side="SELL",
                                quantity=self.qty,
                                price=df[1]["open"].iloc[i+1],
                                date=df[1]['date'].iloc[i+1]
                            )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "stop loss"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[1]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'

                elif self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_SHORT.value:
                    
                    if stop_loss.check_trigger(row['close'], Parameters.TYPE_SHORT.value):

                        self.wallet.close_position(
                                side="BUY",
                                quantity=self.qty,
                                price=df[1]["open"].iloc[i+1],
                                date=df[1]['date'].iloc[i+1]
                            )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "stop loss"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[1]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'

        return [ df[0], df[1] ]

    def test_trailing(self, df):

        # find bars where RSI >= 70
        filtered_70_df = df[1][df[1]['RSI_14'] >= (70 - 0)] # +/-4
        filtered_70_index = filtered_70_df.index.tolist()

        # find bars where RSI <= 30
        filtered_30_df = df[1][df[1]['RSI_14'] <= (30 + 0)] # +/-4
        filtered_30_index = filtered_30_df.index.tolist()

        #for i, row in df[1][ df[1]['timestamp'] >= 1688634300 ].iterrows():
        for i, row in df[1].iloc[9:-1].iterrows():

            if not self.wallet.is_open():

                if row.name in filtered_70_index and Memory.normalize_data(df[1]['volume'].iloc[i-9:i+1].values)[-1][0] < 0 and df[0]['volume'].iloc[i-9:i+1].sum() <= 10*2000:
                    
                    print("Conditions satisfied, proceeding...")

                    self.wallet.open_position(
                        side="SELL",
                        quantity=self.qty,
                        price=df[1]['open'].iloc[i+1],
                        date=df[1]['date'].iloc[i+1]
                    )

                    # trailing stop:
                    trailing_stop = MyTrailingStop(row['close'] + 3.)
                    #trailing_stop = MyTrailingStop(df[1]['high'].iloc[i-9:i].max())

                    print(self.wallet.orders)
                    print(f"SHORT position {df[1]['date'].iloc[i+1]} at {df[1]['open'].iloc[i+1]}")
                    #time.sleep(1)
                
                elif row.name in filtered_30_index and Memory.normalize_data(df[1]['volume'].iloc[i-9:i+1].values)[-1][0] < 0 and df[0]['volume'].iloc[i-9:i+1].sum() <= 10*2000:

                    print("Conditions satisfied, proceeding...")

                    self.wallet.open_position(
                        side="BUY",
                        quantity=self.qty,
                        price=df[1]['open'].iloc[i+1],
                        date=df[1]['date'].iloc[i+1]
                    )

                    # trailing stop
                    trailing_stop = MyTrailingStop(row['close'] - 3.)
                    #trailing_stop = MyTrailingStop(df[1]['low'].iloc[i-9:i].min())

                    print(self.wallet.orders)
                    print(f"LONG position {df[1]['date'].iloc[i+1]} at {df[1]['open'].iloc[i+1]}")
                    #time.sleep(1)

                else:
                    print("...")

            elif self.wallet.is_open():

                print("waiting for close conditions")
                
                if self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_LONG.value:

                    trailing_stop.update_stop(row['close'], Parameters.TYPE_LONG.value)

                    #if self.wallet.orders[self.wallet.INDEX]["Open"] < row['close'] and trailing_stop.check_trigger(row['close'], Parameters.TYPE_LONG.value):
                    if trailing_stop.check_trigger(row['close'], Parameters.TYPE_LONG.value):

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[1]["open"].iloc[i+1],
                            date=df[1]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "trailing stop"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[1]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'

                elif self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_SHORT.value:

                    trailing_stop.update_stop(row['close'], Parameters.TYPE_SHORT.value)

                    #if self.wallet.orders[self.wallet.INDEX]["Open"] > row['close'] and trailing_stop.check_trigger(row['close'], Parameters.TYPE_SHORT.value):
                    if trailing_stop.check_trigger(row['close'], Parameters.TYPE_SHORT.value):

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[1]["open"].iloc[i+1],
                            date=df[1]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "trailing stop"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[1]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'

        return [ df[0], df[1] ]

    def backtest_1_trailing_stop_loss(self, df):

        # find bars where RSI >= 70
        filtered_70_df = df[0][df[0]['RSI_14'] >= (70 - 0)]
        filtered_70_index = filtered_70_df.index.tolist()

        # find bars where RSI <= 30
        filtered_30_df = df[0][df[0]['RSI_14'] <= (30 + 0)]
        filtered_30_index = filtered_30_df.index.tolist()

        for i, row in df[0].iloc[9:-1].iterrows():

            if not self.wallet.is_open():

                if row.name in filtered_70_index:

                    #if Memory.normalize_data(df[0]['volume'].iloc[i-9:i+1], name="volume").iloc[-1] >= 45 and df[0]['volume'].iloc[i-9:i+1].sum() >= 10*3000:
                    #if Memory.scale_data(df[0]['volume'].iloc[i-99:i+1], name="volume").iloc[-1] >= 10:
                    if Memory.normalize_data(df[0]['volume'].iloc[i-9:i+1].values)[-1][0] > 0 and df[0]['volume'].iloc[i-9:i+1].sum() >= 10*3000:

                        self.wallet.open_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        # trailing stop:
                        trailing_stop = TrailingStop(100., row['close'] + 3.)

                        # stop loss:
                        stop_loss = StopLoss(df[1]['low'].iloc[i-9:i].min() * 1.3) # * 1.1
                        #stop_loss = StopLoss(df[1]['close'].iloc[i] - 5.)

                        print(self.wallet.orders)
                        print(f"LONG position {df[0]['date'].iloc[i+1]} at {df[0]['open'].iloc[i+1]}")

                elif row.name in filtered_30_index:

                    #if Memory.normalize_data(df[0]['volume'].iloc[i-9:i+1], name="volume").iloc[-1] >= 45 and df[0]['volume'].iloc[i-9:i+1].sum() >= 10*3000:
                    #if Memory.scale_data(df[0]['volume'].iloc[i-99:i+1], name="volume").iloc[-1] >= 10:
                    if Memory.normalize_data(df[0]['volume'].iloc[i-9:i+1].values)[-1][0] > 0 and df[0]['volume'].iloc[i-9:i+1].sum() >= 10*3000:

                        self.wallet.open_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        # trailing stop:
                        trailing_stop = TrailingStop(100., row['close'] - 3.)

                        # stop loss:
                        stop_loss = StopLoss(df[1]['high'].iloc[i-9:i].max() * 1.3) # * 1.1
                        #stop_loss = StopLoss(df[1]['close'].iloc[i] + 5.)

                        print(self.wallet.orders)
                        print(f"SHORT position {df[0]['date'].iloc[i+1]} at {df[0]['open'].iloc[i+1]}")

                else:
                    print("...")

            elif self.wallet.is_open():
                
                print("waiting for close conditions")

                if self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_SHORT.value:

                    if self.wallet.orders[self.wallet.INDEX]["Open"] < row['close'] and row['close'] >= trailing_stop.update_stop(df[0]['close'].iloc[i], Parameters.TYPE_SHORT.value):

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        print(self.wallet.orders)
                        print(f"closed SHORT at {df[0]['date'].iloc[i+1]}")
                        print(f"Current price: {row['close']}, Current stop: {trailing_stop.update_stop(row['close'], Parameters.TYPE_SHORT.value)}")

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "trailing stop"

                    elif self.wallet.orders[self.wallet.INDEX]["Open"] <= row['close'] and stop_loss.check_trigger(row['close'], Parameters.TYPE_SHORT.value):

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        print(self.wallet.orders)
                        print("stop loss")

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "stop loss"

                elif self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_LONG.value:

                    if self.wallet.orders[self.wallet.INDEX]["Open"] < row['close'] and row['close'] <= trailing_stop.update_stop(df[0]['close'].iloc[i], Parameters.TYPE_LONG.value):

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        print(self.wallet.orders)
                        print(f"closed LONG at {df[0]['date'].iloc[i+1]}")
                        print(f"Current price: {row['close']}, Current stop: {trailing_stop.update_stop(row['close'], Parameters.TYPE_LONG.value)}")
                    
                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "trailing stop"

                    elif self.wallet.orders[self.wallet.INDEX]["Open"] >= row['close'] and stop_loss.check_trigger(row['close'], Parameters.TYPE_LONG.value):

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        print(self.wallet.orders)
                        print("stop loss")

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "stop loss"

        return [ df[0], df[1] ]
    
    def backtest_1_trailing_stop_loss_DEV(self, df):

        # find bars where RSI >= 70
        filtered_70_df = df[0][df[0]['RSI_14'] >= (70 - 0)]
        filtered_70_index = filtered_70_df.index.tolist()

        # find bars where RSI <= 30
        filtered_30_df = df[0][df[0]['RSI_14'] <= (30 + 0)]
        filtered_30_index = filtered_30_df.index.tolist()

        for i, row in df[0].iloc[9:-1].iterrows():
        #for i, row in df[0][ (df[0]['timestamp'] >= 1692219600) & (df[0]['timestamp'] <= 1692392400) ].iterrows():

            if not self.wallet.is_open():

                if row.name in filtered_70_index:

                    #if Memory.normalize_data(df[0]['volume'].iloc[i-9:i+1], name="volume").iloc[-1] >= 45 and df[0]['volume'].iloc[i-9:i+1].sum() >= 10*3000:
                    #if Memory.scale_data(df[0]['volume'].iloc[i-99:i+1], name="volume").iloc[-1] >= 10:
                    if Memory.normalize_data(df[0]['volume'].iloc[i-9:i+1].values)[-1][0] > 0 and df[0]['volume'].iloc[i-9:i+1].sum() >= 10*3000:

                        self.wallet.open_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        # trailing stop
                        trailing_stop = MyTrailingStop(row['close'] - 3.)

                        # stop loss:
                        #stop_loss = StopLoss(df[0]['low'].iloc[i-9:i].min() * 1.3) # * 1.1
                        stop_loss = StopLoss(df[0]['close'].iloc[i] - 3.)

                        print(self.wallet.orders)
                        print(f"LONG position {df[0]['date'].iloc[i+1]} at {df[0]['open'].iloc[i+1]}")

                elif row.name in filtered_30_index:

                    #if Memory.normalize_data(df[0]['volume'].iloc[i-9:i+1], name="volume").iloc[-1] >= 45 and df[0]['volume'].iloc[i-9:i+1].sum() >= 10*3000:
                    #if Memory.scale_data(df[0]['volume'].iloc[i-99:i+1], name="volume").iloc[-1] >= 10:
                    if Memory.normalize_data(df[0]['volume'].iloc[i-9:i+1].values)[-1][0] > 0 and df[0]['volume'].iloc[i-9:i+1].sum() >= 10*3000:

                        self.wallet.open_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        # trailing stop:
                        trailing_stop = MyTrailingStop(row['close'] + 3.)

                        # stop loss:
                        #stop_loss = StopLoss(df[0]['high'].iloc[i-9:i].max() * 1.3) # * 1.1
                        stop_loss = StopLoss(df[0]['close'].iloc[i] + 3.)

                        print(self.wallet.orders)
                        print(f"SHORT position {df[0]['date'].iloc[i+1]} at {df[0]['open'].iloc[i+1]}")

                else:
                    print("...")

            elif self.wallet.is_open():
                
                print("waiting for close conditions")

                if self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_SHORT.value:

                    trailing_stop.update_stop(row['close'], Parameters.TYPE_SHORT.value)

                    #if self.wallet.orders[self.wallet.INDEX]["Open"] < row['close'] and row['close'] >= trailing_stop.update_stop(df[0]['close'].iloc[i], Parameters.TYPE_SHORT.value):
                    if trailing_stop.check_trigger(row['close'], Parameters.TYPE_SHORT.value):

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        print(self.wallet.orders)
                        print(f"closed SHORT at {df[0]['date'].iloc[i+1]}")
                        print(f"Current price: {row['close']}, Current stop: {trailing_stop.update_stop(row['close'], Parameters.TYPE_SHORT.value)}")

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "trailing stop"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'

                    elif self.wallet.orders[self.wallet.INDEX]["Open"] <= row['close'] and stop_loss.check_trigger(row['close'], Parameters.TYPE_SHORT.value):

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        print(self.wallet.orders)
                        print("stop loss")

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "stop loss"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'

                elif self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_LONG.value:

                    trailing_stop.update_stop(row['close'], Parameters.TYPE_LONG.value)

                    #if self.wallet.orders[self.wallet.INDEX]["Open"] < row['close'] and row['close'] <= trailing_stop.update_stop(df[0]['close'].iloc[i], Parameters.TYPE_LONG.value):
                    if trailing_stop.check_trigger(row['close'], Parameters.TYPE_LONG.value):

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        print(self.wallet.orders)
                        print(f"closed LONG at {df[0]['date'].iloc[i+1]}")
                        print(f"Current price: {row['close']}, Current stop: {trailing_stop.update_stop(row['close'], Parameters.TYPE_LONG.value)}")
                    
                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "trailing stop"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'

                    elif self.wallet.orders[self.wallet.INDEX]["Open"] >= row['close'] and stop_loss.check_trigger(row['close'], Parameters.TYPE_LONG.value):

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        print(self.wallet.orders)
                        print("stop loss")

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "stop loss"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'

        return [ df[0], df[1] ]
    
    def backtest_1_trailing_stop_loss_DEV_2(self, df):

        # find bars where RSI >= 70
        filtered_70_df = df[1][df[1]['RSI_14'] >= (70 - 0)]
        filtered_70_index = filtered_70_df.index.tolist()

        # find bars where RSI <= 30
        filtered_30_df = df[1][df[1]['RSI_14'] <= (30 + 0)]
        filtered_30_index = filtered_30_df.index.tolist()

        for i, row in df[1].iloc[9:-1].iterrows():

            if not self.wallet.is_open():

                if row.name in filtered_70_index:

                    #if Memory.normalize_data(df[1]['volume'].iloc[i-9:i+1], name="volume").iloc[-1] >= 45 and df[1]['volume'].iloc[i-9:i+1].sum() >= 10*3000:
                    #if Memory.scale_data(df[1]['volume'].iloc[i-99:i+1], name="volume").iloc[-1] >= 10:
                    if Memory.normalize_data(df[1]['volume'].iloc[i-9:i+1].values)[-1][0] > 0 and df[1]['volume'].iloc[i-9:i+1].sum() >= 10*3000:

                        self.wallet.open_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[1]['open'].iloc[i+1],
                            date=df[1]['date'].iloc[i+1]
                        )

                        # trailing stop
                        trailing_stop = MyTrailingStop(row['close'] - 3.)

                        # stop loss:
                        #stop_loss = StopLoss(df[1]['low'].iloc[i-9:i].min() * 1.3) # * 1.1
                        stop_loss = StopLoss(df[1]['close'].iloc[i] - 2.)

                        print(self.wallet.orders)
                        print(f"LONG position {df[1]['date'].iloc[i+1]} at {df[1]['open'].iloc[i+1]}")

                elif row.name in filtered_30_index:

                    #if Memory.normalize_data(df[1]['volume'].iloc[i-9:i+1], name="volume").iloc[-1] >= 45 and df[1]['volume'].iloc[i-9:i+1].sum() >= 10*3000:
                    #if Memory.scale_data(df[1]['volume'].iloc[i-99:i+1], name="volume").iloc[-1] >= 10:
                    if Memory.normalize_data(df[1]['volume'].iloc[i-9:i+1].values)[-1][0] > 0 and df[1]['volume'].iloc[i-9:i+1].sum() >= 10*3000:

                        self.wallet.open_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[1]['open'].iloc[i+1],
                            date=df[1]['date'].iloc[i+1]
                        )

                        # trailing stop:
                        trailing_stop = MyTrailingStop(row['close'] + 3.)

                        # stop loss:
                        #stop_loss = StopLoss(df[1]['high'].iloc[i-9:i].max() * 1.3) # * 1.1
                        stop_loss = StopLoss(df[1]['close'].iloc[i] + 2.)

                        print(self.wallet.orders)
                        print(f"SHORT position {df[1]['date'].iloc[i+1]} at {df[1]['open'].iloc[i+1]}")

                else:
                    print("...")

            elif self.wallet.is_open():
                
                print("waiting for close conditions")

                if self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_SHORT.value:

                    trailing_stop.update_stop(row['close'], Parameters.TYPE_SHORT.value)

                    #if self.wallet.orders[self.wallet.INDEX]["Open"] < row['close'] and row['close'] >= trailing_stop.update_stop(df[1]['close'].iloc[i], Parameters.TYPE_SHORT.value):
                    if trailing_stop.check_trigger(row['close'], Parameters.TYPE_SHORT.value):

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[1]['open'].iloc[i+1],
                            date=df[1]['date'].iloc[i+1]
                        )

                        print(self.wallet.orders)
                        print(f"closed SHORT at {df[1]['date'].iloc[i+1]}")
                        print(f"Current price: {row['close']}, Current stop: {trailing_stop.update_stop(row['close'], Parameters.TYPE_SHORT.value)}")

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "trailing stop"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[1]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'

                    elif self.wallet.orders[self.wallet.INDEX]["Open"] <= row['close'] and stop_loss.check_trigger(row['close'], Parameters.TYPE_SHORT.value):

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[1]['open'].iloc[i+1],
                            date=df[1]['date'].iloc[i+1]
                        )

                        print(self.wallet.orders)
                        print("stop loss")

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "stop loss"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[1]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'

                elif self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_LONG.value:

                    trailing_stop.update_stop(row['close'], Parameters.TYPE_LONG.value)

                    #if self.wallet.orders[self.wallet.INDEX]["Open"] < row['close'] and row['close'] <= trailing_stop.update_stop(df[1]['close'].iloc[i], Parameters.TYPE_LONG.value):
                    if trailing_stop.check_trigger(row['close'], Parameters.TYPE_LONG.value):

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[1]['open'].iloc[i+1],
                            date=df[1]['date'].iloc[i+1]
                        )

                        print(self.wallet.orders)
                        print(f"closed LONG at {df[1]['date'].iloc[i+1]}")
                        print(f"Current price: {row['close']}, Current stop: {trailing_stop.update_stop(row['close'], Parameters.TYPE_LONG.value)}")
                    
                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "trailing stop"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[1]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'

                    elif self.wallet.orders[self.wallet.INDEX]["Open"] >= row['close'] and stop_loss.check_trigger(row['close'], Parameters.TYPE_LONG.value):

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[1]['open'].iloc[i+1],
                            date=df[1]['date'].iloc[i+1]
                        )

                        print(self.wallet.orders)
                        print("stop loss")

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "stop loss"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[1]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'

        return [ df[0], df[1] ]

    def backtest_2_5min_stop_loss(self, df):

        # find bars where RSI >= 70
        filtered_70_df = df[1][df[1]['RSI_14'] >= (70 - 0)]
        filtered_70_index = filtered_70_df.index.tolist()

        # find bars where RSI <= 30
        filtered_30_df = df[1][df[1]['RSI_14'] <= (30 + 0)]
        filtered_30_index = filtered_30_df.index.tolist()

        for i, row in df[1].iloc[-25920:-1].iterrows():

            if not self.wallet.is_open():

                #if row.name in filtered_70_index and Memory.normalize_data(df[1]['volume'].iloc[i-9:i+1], name="volume").iloc[-1] < 15:
                #if row.name in filtered_70_index and Memory.normalize_data(df[1]['volume'].iloc[i-9:i+1].values)[-1][0] < 0:
                if row.name in filtered_70_index and Memory.normalize_data(df[1]['volume'].iloc[i-9:i+1].values)[-1][0] < 0 and df[1]['volume'].iloc[i-9:i+1].sum() <= 10*2000:

                    if not df[0]['RSI_14'][ df[0]['timestamp'] == df[1]['timestamp'].iloc[i] ].values[0] >= (70 - 0):

                        print("Conditions satisfied, proceeding...")

                        self.wallet.open_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[1]['open'].iloc[i+1],
                            date=df[1]['date'].iloc[i+1]
                        )

                        # stop loss:
                        #stop_loss = StopLoss(df[1]['high'].iloc[i-9:i].max() * 1.2)
                        stop_loss = StopLoss(df[1]['close'].iloc[i] + 5.)

                        print(self.wallet.orders)
                
                #elif row.name in filtered_30_index and Memory.normalize_data(df[1]['volume'].iloc[i-9:i+1], name="volume").iloc[-1] < 15:
                #elif row.name in filtered_30_index and Memory.normalize_data(df[1]['volume'].iloc[i-9:i+1].values)[-1][0] < 0:
                elif row.name in filtered_30_index and Memory.normalize_data(df[1]['volume'].iloc[i-9:i+1].values)[-1][0] < 0 and df[1]['volume'].iloc[i-9:i+1].sum() <= 10*2000:

                    if not df[0]['RSI_14'][ df[0]['timestamp'] == df[1]['timestamp'].iloc[i] ].values[0] <= (30 - 0):

                        print("Conditions satisfied, proceeding...")

                        self.wallet.open_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[1]['open'].iloc[i+1],
                            date=df[1]['date'].iloc[i+1]
                        )

                        # stop loss:
                        #stop_loss = StopLoss(df[1]['low'].iloc[i-9:i].min() * 1.2)
                        stop_loss = StopLoss(df[1]['close'].iloc[i] - 5.)

                        print(self.wallet.orders)

                else:
                    print("...")

            elif self.wallet.is_open():

                print("waiting for close conditions")

                if self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_SHORT.value:

                    if self.wallet.orders[self.wallet.INDEX]["Open"] <= row['close'] and stop_loss.check_trigger(row['close'], Parameters.TYPE_SHORT.value):
                        
                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[1]["open"].iloc[i+1],
                            date=df[1]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "stop loss"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[1]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'

                    #elif abs(df[1]['RSI_14'].iloc[i] - 30) <= 3:
                    elif df[1]['RSI_14'].iloc[i] <= (30 + 3): #abs()?
                        
                        self.wallet.close_position(
                                side="BUY",
                                quantity=self.qty,
                                price=df[1]["open"].iloc[i+1],
                                date=df[1]['date'].iloc[i+1]
                            )
                        
                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "rsi"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[1]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'
                        
                elif self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_LONG.value:

                    if self.wallet.orders[self.wallet.INDEX]["Open"] >= row['close'] and stop_loss.check_trigger(row['close'], Parameters.TYPE_LONG.value):

                        self.wallet.close_position(
                                side="SELL",
                                quantity=self.qty,
                                price=df[1]["open"].iloc[i+1],
                                date=df[1]['date'].iloc[i+1]
                            )
                        
                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "stop loss"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[1]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'
                        
                    #elif abs(df[1]['RSI_14'].iloc[i] - 70) <= 3:
                    elif df[1]['RSI_14'].iloc[i] >= (70 - 3): #abs()?
                        
                        self.wallet.close_position(
                                side="SELL",
                                quantity=self.qty,
                                price=df[1]["open"].iloc[i+1],
                                date=df[1]['date'].iloc[i+1]
                            )
                        
                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "rsi"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[1]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'
        
        return [ df[0], df[1] ]
    
    def backtest_2_5min_simple(self, df):

        # find bars where RSI >= 70
        filtered_70_df = df[1][df[1]['RSI_14'] >= (70 - 3)]
        filtered_70_index = filtered_70_df.index.tolist()

        # find bars where RSI <= 30
        filtered_30_df = df[1][df[1]['RSI_14'] <= (30 + 3)]
        filtered_30_index = filtered_30_df.index.tolist()

        for i, row in df[1].iloc[9:-2].iterrows():

            if not self.wallet.is_open():

                #if row.name in filtered_70_index and Memory.normalize_data(df[1]['volume'].iloc[i-9:i+1], name="volume").iloc[-1] <= 25:
                #if row.name in filtered_70_index and Memory.scale_data(df[1]["volume"].iloc[i-100:i], name="volume").iloc[-1] <= 5:
                if row.name in filtered_70_index and Memory.normalize_data(df[1]['volume'].iloc[i-9:i+1].values)[-1][0] < 0:

                    print("Conditions satisfied, proceeding...")

                    self.wallet.open_position(
                        side="SELL",
                        quantity=self.qty,
                        price=df[1]['close'].iloc[i+1],
                        date=df[1]['date'].iloc[i+1]
                    )
                    print(self.wallet.orders)
                
                #elif row.name in filtered_30_index and Memory.normalize_data(df[1]['volume'].iloc[i-9:i+1], name="volume").iloc[-1] <= 25:
                #elif row.name in filtered_30_index and Memory.scale_data(df[1]["volume"].iloc[i-100:i], name="volume").iloc[-1] <= 5:
                elif row.name in filtered_30_index and Memory.normalize_data(df[1]['volume'].iloc[i-9:i+1].values)[-1][0] < 0:

                    print("Conditions satisfied, proceeding...")

                    self.wallet.open_position(
                        side="BUY",
                        quantity=self.qty,
                        price=df[1]['close'].iloc[i+1],
                        date=df[1]['date'].iloc[i+1]
                    )
                    print(self.wallet.orders)

                else:
                    print("...")

            elif self.wallet.is_open():

                print("waiting for close conditions")

                if self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_SHORT.value:
                    
                    if row['RSI_14'] <= (30 + 3):
                    #if abs(row['RSI_14'] - 30) <= 3.:

                        self.wallet.close_position(
                                side="BUY",
                                quantity=self.qty,
                                price=df[1]["open"].iloc[i+1],
                                date=df[1]["date"].iloc[i+1]
                            )
                        
                elif self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_LONG.value:

                    if row['RSI_14'] >= (70 - 3):
                    #if abs(row['RSI_14'] - 70) <= 3.:
                        
                        self.wallet.close_position(
                                side="SELL",
                                quantity=self.qty,
                                price=df[1]["open"].iloc[i+1],
                                date=df[1]["date"].iloc[i+1]
                            )
        
        return [ df[0], df[1] ]

    def backtest_2_5min_trailing(self, df):

        # find bars where RSI >= 70
        filtered_70_df = df[1][df[1]['RSI_14'] >= (70 - 0)] # +/-4
        filtered_70_index = filtered_70_df.index.tolist()

        # find bars where RSI <= 30
        filtered_30_df = df[1][df[1]['RSI_14'] <= (30 + 0)] # +/-4
        filtered_30_index = filtered_30_df.index.tolist()

        #for i, row in df[1].iloc[9:-1].iterrows():
        for i, row in df[1][ df[1]['timestamp'] >= 1692035400 ].iterrows():

            if not self.wallet.is_open():

                #if row.name in filtered_70_index and Memory.normalize_data(df[1]['volume'].iloc[i-9:i+1], name="volume").iloc[-1] < 15 and df[0]['volume'].iloc[i-9:i+1].sum() <= 10*2000:
                if row.name in filtered_70_index and Memory.normalize_data(df[1]['volume'].iloc[i-9:i+1].values)[-1][0] < 0 and df[0]['volume'].iloc[i-9:i+1].sum() <= 10*2000:

                    print("Conditions satisfied, proceeding...")

                    self.wallet.open_position(
                        side="SELL",
                        quantity=self.qty,
                        price=df[1]['open'].iloc[i+1],
                        date=df[1]['date'].iloc[i+1]
                    )

                    # trailing stop:
                    trailing_stop = TrailingStop(100., row['close'] - 1.) # - 3.

                    # stop loss:
                    #stop_loss = StopLoss(df[1]['high'].iloc[i-9:i].max() * (1. + .3)) # * 1.1
                    stop_loss = StopLoss(df[1]['close'].iloc[i] + 5.)

                    print(self.wallet.orders)
                    print(f"SHORT position {df[1]['date'].iloc[i+1]} at {df[1]['open'].iloc[i+1]}")
                    print("initial trailing stop:", df[1]['close'].iloc[i])
                
                #elif row.name in filtered_30_index and Memory.normalize_data(df[1]['volume'].iloc[i-9:i+1], name="volume").iloc[-1] < 15 and df[0]['volume'].iloc[i-9:i+1].sum() <= 10*2000:
                elif row.name in filtered_30_index and Memory.normalize_data(df[1]['volume'].iloc[i-9:i+1].values)[-1][0] < 0 and df[0]['volume'].iloc[i-9:i+1].sum() <= 10*2000:

                    print("Conditions satisfied, proceeding...")

                    self.wallet.open_position(
                        side="BUY",
                        quantity=self.qty,
                        price=df[1]['open'].iloc[i+1],
                        date=df[1]['date'].iloc[i+1]
                    )

                    # trailing stop:
                    trailing_stop = TrailingStop(100., row['close'] + 1.) # + 3.

                    # stop loss:
                    #stop_loss = StopLoss(df[1]['low'].iloc[i-9:i].min() * (1. - .3)) # * 1.1
                    stop_loss = StopLoss(df[1]['close'].iloc[i] - 5.)

                    print(self.wallet.orders)
                    print(f"LONG position {df[1]['date'].iloc[i+1]} at {df[1]['open'].iloc[i+1]}")
                    print("initial trailing stop:", df[1]['close'].iloc[i])

                else:
                    print("...")

            elif self.wallet.is_open():

                print("waiting for close conditions")

                print(f"Current price: {row['close']}")
                print("actual stop:", trailing_stop.actual_stop())

                if self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_SHORT.value:

                    print("Actual Profit:", self.wallet.orders[self.wallet.INDEX]["Open"] - row['close'])
                    #time.sleep(1)

                    if self.wallet.orders[self.wallet.INDEX]["Open"] - 3. >= row['close'] and row['close'] <= trailing_stop.update_stop(df[1]['close'].iloc[i], Parameters.TYPE_SHORT.value):
                        # +3 spread may be unnecessary

                        self.wallet.close_position(
                                side="BUY",
                                quantity=self.qty,
                                price=df[1]["open"].iloc[i+1],
                                date=df[1]['date'].iloc[i+1]
                            )
                        
                        print("trailing stop")
                        print(f"closed SHORT at {df[1]['date'].iloc[i+1]}")
                        print(f"Current price: {row['close']}, Current stop: {trailing_stop.update_stop(row['close'], Parameters.TYPE_SHORT.value)} at {df[1]['date'].iloc[i]}")
                        print("Profit:", self.wallet.orders[self.wallet.INDEX]["Open"] - row['close'])
                        #time.sleep(1)

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "trailing stop"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[1]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'
                    
                    elif self.wallet.orders[self.wallet.INDEX]["Open"] < row['close'] and stop_loss.check_trigger(row['close'], Parameters.TYPE_SHORT.value):

                        self.wallet.close_position(
                                side="BUY",
                                quantity=self.qty,
                                price=df[1]["open"].iloc[i+1],
                                date=df[1]['date'].iloc[i+1]
                            )
                        
                        print("stop loss")
                        print(f"closed SHORT at {df[1]['date'].iloc[i+1]}")
                        print("Loss:", self.wallet.orders[self.wallet.INDEX]["Open"] - row['close'])
                        #time.sleep(1)

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "stop loss"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[1]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'
                        
                elif self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_LONG.value:

                    print("Actual Profit:", row['close'] - self.wallet.orders[self.wallet.INDEX]["Open"])
                    #time.sleep(1)

                    if self.wallet.orders[self.wallet.INDEX]["Open"] <= 3. + row['close'] and row['close'] >= trailing_stop.update_stop(df[1]['close'].iloc[i], Parameters.TYPE_LONG.value):
                        # +3 spread may be unnecessary

                        self.wallet.close_position(
                                side="SELL",
                                quantity=self.qty,
                                price=df[1]["open"].iloc[i+1],
                                date=df[1]['date'].iloc[i+1]
                            )
                        
                        print("trailing stop")
                        print(f"closed LONG at {df[1]['date'].iloc[i+1]}")
                        print(f"Current price: {row['close']}, Current stop: {trailing_stop.update_stop(row['close'], Parameters.TYPE_LONG.value)} at {df[1]['date'].iloc[i]}")
                        print("Profit:", row['close'] - self.wallet.orders[self.wallet.INDEX]["Open"])
                        #time.sleep(1)
                    
                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "trailing stop"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[1]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'

                    
                    elif self.wallet.orders[self.wallet.INDEX]["Open"] > row['close'] and stop_loss.check_trigger(row['close'], Parameters.TYPE_LONG.value):

                        self.wallet.close_position(
                                side="SELL",
                                quantity=self.qty,
                                price=df[1]["open"].iloc[i+1],
                                date=df[1]['date'].iloc[i+1]
                            )
                        
                        print("stop loss")
                        print(f"closed LONG at {df[1]['date'].iloc[i+1]}")
                        print("Loss:", row['close'] - self.wallet.orders[self.wallet.INDEX]["Open"])
                        #time.sleep(1)

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "stop loss"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[1]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'
        
        return [ df[0], df[1] ]
    
    def backtest_3_1min_5min_DEV(self, df):

        # find bars where RSI >= 70 for 1min data
        filtered_70_df = df[0][df[0]['RSI_14'] >= (70 - 0)]
        filtered_70_index = filtered_70_df.index.tolist()

        # find bars where RSI <= 30 for 1min data
        filtered_30_df = df[0][df[0]['RSI_14'] <= (30 + 0)]
        filtered_30_index = filtered_30_df.index.tolist()

        for i, row in df[0].iloc[9:].iterrows(): #check

            if not self.wallet.is_open():

                if row.name in filtered_70_index:

                    if Backtest.is_multiple_of_5_minutes(row['timestamp']):

                        if df[1]['RSI_14'].iloc[i] >= (70 - 0):
                            print("Conditions satisfied, proceeding...")

                            self.wallet.open_position(
                                side="BUY",
                                quantity=self.qty,
                                price=df[0]['open'].iloc[i+1],
                                date=df[0]['date'].iloc[i+1]
                            )

                            # trailing stop
                            trailing_stop = MyTrailingStop(row['close'] - 3.)

                            print(self.wallet.orders)
                
                elif row.name in filtered_30_index:

                    if Backtest.is_multiple_of_5_minutes(row['timestamp']):

                        if df[1]['RSI_14'].iloc[i] <= (30 + 0):
                            print("Conditions satisfied, proceeding...")

                            self.wallet.open_position(
                                side="SELL",
                                quantity=self.qty,
                                price=df[0]['open'].iloc[i+1],
                                date=df[0]['date'].iloc[i+1]
                            )

                            # trailing stop:
                            trailing_stop = MyTrailingStop(row['close'] + 3.)

                            print(self.wallet.orders)

                else:
                    print("...")

            elif self.wallet.is_open():
                
                print("waiting for close conditions")

                if self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_SHORT.value:

                    trailing_stop.update_stop(row['close'], Parameters.TYPE_SHORT.value)

                    if trailing_stop.check_trigger(row['close'], Parameters.TYPE_SHORT.value):
                        
                        self.wallet.close_position(
                                side="BUY",
                                quantity=self.qty,
                                price=df[0]['open'].iloc[i+1],
                                date=df[0]['date'].iloc[i+1]
                        )

                elif self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_LONG.value:

                    trailing_stop.update_stop(row['close'], Parameters.TYPE_LONG.value)
                        
                    if trailing_stop.check_trigger(row['close'], Parameters.TYPE_LONG.value):
                        
                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )
        
        return [ df[0], df[1] ]
    
    @staticmethod
    def is_multiple_of_5_minutes(time):
        
        if type(time) == np.int64 or type(time) == int:
            # Convert the integer to timestamp type
            timestamp = datetime.utcfromtimestamp(time)

            # Calculate the number of minutes
            total_minutes = timestamp.minute + timestamp.hour * 60

            # Check if the total minutes is a multiple of 5
            return total_minutes % 5 == 0
        
        if type(time) == str:
            # Convert the string format date to datetime type
            date = datetime.strptime(time, '%Y-%m-%d %H:%M:%S')

            timestamp = datetime.utcfromtimestamp(int(date.timestamp()))

            # Calculate the number of minutes
            total_minutes = timestamp.minute + timestamp.hour * 60

            # Check if the total minutes is a multiple of 5
            return total_minutes % 5 == 0
    
    @staticmethod
    def modulo_5_minutes(time):

        if type(time) == np.int64 or type(time) == int:
            # Convert the integer to timestamp type
            timestamp = datetime.utcfromtimestamp(time)

            # Calculate the number of minutes
            total_minutes = timestamp.minute + timestamp.hour * 60

            return total_minutes % 5
        
        if type(time) == str:
            # Convert the string format date to datetime type
            date = datetime.strptime(time, '%Y-%m-%d %H:%M:%S')

            timestamp = datetime.utcfromtimestamp(int(date.timestamp()))

            # Calculate the number of minutes
            total_minutes = timestamp.minute + timestamp.hour * 60

            return total_minutes % 5
    
    def backtest_4_1min_5min_stabil_rsi(self, df):

        df[0] = df[1]
        df[1] = df[2]

        # find bars where RSI >= 70 for 1min data
        filtered_70_df = df[0][ df[0]['RSI_14'] >= (70 - 0) ]
        filtered_70_index = filtered_70_df.index.tolist()

        # find bars where RSI <= 30 for 1min data
        filtered_30_df = df[0][ df[0]['RSI_14'] <= (30 + 0) ]
        filtered_30_index = filtered_30_df.index.tolist()

        for i, row in df[0].iloc[9:-1].iterrows(): #check

            if not self.wallet.is_open():

                if not row.name in filtered_70_index and Memory.normalize_data(df[0]['volume'].iloc[i-9:i+1].values)[-1][0] <= 0: # and df[0]['volume'].iloc[i-9:i+1].sum() <= 10*2000:

                    t = row['timestamp'] - Backtest.modulo_5_minutes(row['timestamp']) * 60 - 5 * 60
                    #t = datetime.strptime(row['date'], '%Y-%m-%d %H:%M:%S') - timedelta(minutes=Backtest.modulo_5_minutes(row['date'])) - timedelta(minutes=5)
                    #t = int(t.timestamp())
                    
                    #if abs(df[1]['RSI_14'].loc[ df[1]['timestamp'] == t ].values[0] - 70.) <= 4.:# and Memory.normalize_data(df[1]['volume'].loc[ df[1]['timestamp'] <= t ].iloc[i-9:i+1].values)[-1][0] < 0:
                    if df[1]['RSI_14'].loc[ df[1]['timestamp'] == t ].values[0] > (70 - 4.):
                        print("Conditions satisfied, proceeding...")

                        self.wallet.open_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        # stop loss:
                        #stop_loss = StopLoss(df[1]['high'].iloc[i-9:i].max() * 1.2)
                        #stop_loss = StopLoss(df[0]['close'].iloc[i] + 5.)
                        stop_loss = StopLoss(max(df[0]['open'].iloc[i], df[0]['close'].iloc[i]) + 2.5)

                        take_profit = TakeProfit(df[0]['open'].iloc[i+1] - 10.)

                        print(self.wallet.orders)

                elif not row.name in filtered_30_index and Memory.normalize_data(df[0]['volume'].iloc[i-9:i+1].values)[-1][0] <= 0: # and df[0]['volume'].iloc[i-9:i+1].sum() <= 10*2000:

                    t = row['timestamp'] - Backtest.modulo_5_minutes(row['timestamp']) * 60 - 5 * 60
                    #t = datetime.strptime(row['date'], '%Y-%m-%d %H:%M:%S') - timedelta(minutes=Backtest.modulo_5_minutes(row['date'])) - timedelta(minutes=5)
                    #t = int(t.timestamp())

                    #if abs(df[1]['RSI_14'].loc[ df[1]['timestamp'] == t ].values[0] - 30.) <= 4.:# and Memory.normalize_data(df[1]['volume'].loc[ df[1]['timestamp'] <= t ].iloc[i-9:i+1].values)[-1][0] < 0:
                    if df[1]['RSI_14'].loc[ df[1]['timestamp'] == t ].values[0] < (30 + 4.):
                        print("Conditions satisfied, proceeding...")

                        self.wallet.open_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        # stop loss:
                        #stop_loss = StopLoss(df[1]['low'].iloc[i-9:i].min() * 1.2)
                        #stop_loss = StopLoss(df[0]['close'].iloc[i] - 5.)
                        stop_loss = StopLoss(min(df[0]['open'].iloc[i], df[0]['close'].iloc[i]) - 2.5)

                        take_profit = TakeProfit(df[0]['open'].iloc[i+1] + 10.)

                        print(self.wallet.orders)

                else:
                    print("...")

            elif self.wallet.is_open():

                print("waiting for close conditions")

                if self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_SHORT.value:

                    t = row['timestamp'] - Backtest.modulo_5_minutes(row['timestamp']) * 60 - 5 * 60
                    #t = datetime.strptime(row['date'], '%Y-%m-%d %H:%M:%S') - timedelta(minutes=Backtest.modulo_5_minutes(row['date'])) - timedelta(minutes=5)
                    #t = int(t.timestamp())

                    if self.wallet.orders[self.wallet.INDEX]["Open"] <= row['close'] and stop_loss.check_trigger(row['close'], Parameters.TYPE_SHORT.value):
                        
                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[0]["open"].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "stop loss"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'

                    # strict comparison needed.
                    #elif abs(df[1]['RSI_14'].loc[ df[1]['timestamp'] == t ].values[0] - 30.) <= 5.:
                    '''elif df[1]['RSI_14'].loc[ df[1]['timestamp'] == t ].values[0] <= (30 + 3):

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[0]["open"].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "rsi"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'
                    '''
                    if row['RSI_14'] <= (30 + 3.) or take_profit.check_trigger(row['close'], Parameters.TYPE_SHORT.value):

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[0]["open"].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "rsi or take_profit"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'

                elif self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_LONG.value:

                    t = row['timestamp'] - Backtest.modulo_5_minutes(row['timestamp']) * 60 - 5 * 60
                    #t = datetime.strptime(row['date'], '%Y-%m-%d %H:%M:%S') - timedelta(minutes=Backtest.modulo_5_minutes(row['date'])) - timedelta(minutes=5)
                    #t = int(t.timestamp())

                    if self.wallet.orders[self.wallet.INDEX]["Open"] >= row['close'] and stop_loss.check_trigger(row['close'], Parameters.TYPE_LONG.value):

                        self.wallet.close_position(
                                side="SELL",
                                quantity=self.qty,
                                price=df[0]["open"].iloc[i+1],
                                date=df[0]['date'].iloc[i+1]
                            )
                        
                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "stop loss"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'
                    
                    # strict comparison needed.
                    #elif abs(df[1]['RSI_14'].loc[ df[1]['timestamp'] == t ].values[0] - 70.) <= 5.:
                    '''elif df[1]['RSI_14'].loc[ df[1]['timestamp'] == t ].values[0] >= (70 - 3):

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[0]["open"].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "rsi"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'
                    '''
                    if row['RSI_14'] >= (70 - 3.) or take_profit.check_trigger(row['close'], Parameters.TYPE_LONG.value):

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[0]["open"].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "rsi or take_profit"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'

        return [ df[0], df[1] ]
    
    def backtest_4_1min_5min_stabil_trailing(self, df):

        # find bars where RSI >= 70 for 1min data
        filtered_70_df = df[0][ df[0]['RSI_14'] >= (70 - 3) ]
        filtered_70_index = filtered_70_df.index.tolist()

        # find bars where RSI <= 30 for 1min data
        filtered_30_df = df[0][ df[0]['RSI_14'] <= (30 + 3) ]
        filtered_30_index = filtered_30_df.index.tolist()

        for i, row in df[0].iloc[9:-1].iterrows(): #check

            if not self.wallet.is_open():

                if not row.name in filtered_70_index and Memory.normalize_data(df[0]['volume'].iloc[i-9:i+1].values)[-1][0] < 0: # and df[0]['volume'].iloc[i-9:i+1].sum() <= 10*2000:

                    t = row['timestamp'] - Backtest.modulo_5_minutes(row['timestamp']) * 60 - 5 * 60
                    #t = datetime.strptime(row['date'], '%Y-%m-%d %H:%M:%S') - timedelta(minutes=Backtest.modulo_5_minutes(row['date'])) - timedelta(minutes=5)
                    #t = int(t.timestamp())
                    
                    if abs(df[1]['RSI_14'].loc[ df[1]['timestamp'] == t ].values[0] - 70.) <= 3. and Memory.normalize_data(df[1]['volume'].loc[ df[1]['timestamp'] <= t ].iloc[i-9:i+1].values)[-1][0] < 0:
                        print("Conditions satisfied, proceeding...")

                        self.wallet.open_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        # trailing stop:
                        trailing_stop = MyTrailingStop(row['close'] + 3.)

                        # stop loss:
                        #stop_loss = StopLoss(df[1]['high'].iloc[i-9:i].max() * 1.2)
                        stop_loss = StopLoss(df[0]['close'].iloc[i] + 5.)

                        print(self.wallet.orders)

                elif not row.name in filtered_30_index and Memory.normalize_data(df[0]['volume'].iloc[i-9:i+1].values)[-1][0] < 0: # and df[0]['volume'].iloc[i-9:i+1].sum() <= 10*2000:

                    t = row['timestamp'] - Backtest.modulo_5_minutes(row['timestamp']) * 60 - 5 * 60
                    #t = datetime.strptime(row['date'], '%Y-%m-%d %H:%M:%S') - timedelta(minutes=Backtest.modulo_5_minutes(row['date'])) - timedelta(minutes=5)
                    #t = int(t.timestamp())

                    if abs(df[1]['RSI_14'].loc[ df[1]['timestamp'] == t ].values[0] - 30.) <= 3. and Memory.normalize_data(df[1]['volume'].loc[ df[1]['timestamp'] <= t ].iloc[i-9:i+1].values)[-1][0] < 0:
                        print("Conditions satisfied, proceeding...")

                        self.wallet.open_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        # trailing stop
                        trailing_stop = MyTrailingStop(row['close'] - 3.)

                        # stop loss:
                        #stop_loss = StopLoss(df[1]['low'].iloc[i-9:i].min() * 1.2)
                        stop_loss = StopLoss(df[0]['close'].iloc[i] - 5.)

                        print(self.wallet.orders)

                else:
                    print("...")

            elif self.wallet.is_open():

                print("waiting for close conditions")

                if self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_SHORT.value:

                    trailing_stop.update_stop(row['close'], Parameters.TYPE_SHORT.value)

                    t = row['timestamp'] - Backtest.modulo_5_minutes(row['timestamp']) * 60 - 5 * 60
                    #t = datetime.strptime(row['date'], '%Y-%m-%d %H:%M:%S') - timedelta(minutes=Backtest.modulo_5_minutes(row['date'])) - timedelta(minutes=5)
                    #t = int(t.timestamp())
                    
                    if self.wallet.orders[self.wallet.INDEX]["Open"] <= row['close'] and stop_loss.check_trigger(row['close'], Parameters.TYPE_SHORT.value):
                        
                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[0]["open"].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "stop loss"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'

                    elif self.wallet.orders[self.wallet.INDEX]["Open"] - 2. > row['close'] and trailing_stop.check_trigger(row['close'], Parameters.TYPE_SHORT.value):

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[0]["open"].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "trailing stop"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'

                elif self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_LONG.value:

                    trailing_stop.update_stop(row['close'], Parameters.TYPE_LONG.value)

                    t = row['timestamp'] - Backtest.modulo_5_minutes(row['timestamp']) * 60 - 5 * 60
                    #t = datetime.strptime(row['date'], '%Y-%m-%d %H:%M:%S') - timedelta(minutes=Backtest.modulo_5_minutes(row['date'])) - timedelta(minutes=5)
                    #t = int(t.timestamp())

                    if self.wallet.orders[self.wallet.INDEX]["Open"] >= row['close'] and stop_loss.check_trigger(row['close'], Parameters.TYPE_LONG.value):

                        self.wallet.close_position(
                                side="SELL",
                                quantity=self.qty,
                                price=df[0]["open"].iloc[i+1],
                                date=df[0]['date'].iloc[i+1]
                            )
                        
                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "stop loss"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'
                    
                    elif self.wallet.orders[self.wallet.INDEX]["Open"] + 2. < row['close'] and trailing_stop.check_trigger(row['close'], Parameters.TYPE_LONG.value):

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[0]["open"].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "trailing stop"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'

        return [ df[0], df[1] ]
    
    def backtest_4_1min_5min_borders_1_DEV(self, df):

        '''df_ind = [
            ind.HeikinAshi(df[0]),
            ind.HeikinAshi(df[1])
        ]

        df = [
            df_ind[0],
            df_ind[1]
        ]'''

        # find bars where RSI >= 70 for 1min data
        filtered_70_df = df[0][df[0]['RSI_14'] >= (70 - 1)]
        filtered_70_index = filtered_70_df.index.tolist()

        # find bars where RSI <= 30 for 1min data
        filtered_30_df = df[0][df[0]['RSI_14'] <= (30 + 1)]
        filtered_30_index = filtered_30_df.index.tolist()

        for i, row in df[0].iloc[9:-1].iterrows():
        #for i, row in df[0][ (df[0]['timestamp'] >= 1692219600) & (df[0]['timestamp'] <= 1692392400) ].iterrows():

            if not self.wallet.is_open():

                t = row['timestamp'] - Backtest.modulo_5_minutes(row['timestamp']) * 60 - 5 * 60
                
                #if abs(df[1]['RSI_14'].loc[ df[1]['timestamp'] == t ].values[0] - 70.) <= 3. and Memory.normalize_data(df[1]['volume'].loc[ df[1]['timestamp'] <= t ].iloc[i-9:i+1].values)[-1][0] > 0:
                if df[1]['RSI_14'].loc[ df[1]['timestamp'] == t ].values[0] >= (70 - 4):# and Memory.normalize_data(df[1]['volume'].loc[ df[1]['timestamp'] <= t ].iloc[i-9:i+1].values)[-1][0] > 0:
                    
                    # is 5min RSI up?
                    #if df[1]['RSI_14'].loc[ df[1]['timestamp'] <= t ].values[-1] - df[1]['RSI_14'].loc[ df[1]['timestamp'] <= t ].values[-3] > 0:

                    #if row.name in filtered_70_index and Memory.normalize_data(df[0]['volume'].iloc[i-100:i], name="volume").iloc[-1] >= 25:
                    if row.name in filtered_70_index and Memory.normalize_data(df[0]['volume'].iloc[i-9:i+1].values)[-1][0] > 0:

                        print("Conditions satisfied, proceeding...")

                        self.wallet.open_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        # trailing stop
                        trailing_stop = MyTrailingStop(row['close'] - 5.)

                        # take profit
                        take_profit = TakeProfit(max(df[0]['open'].iloc[i], df[0]['close'].iloc[i]) + 5.)

                        # stop loss:
                        #stop_loss = StopLoss(df[1]['low'].iloc[i-9:i].min() * 1.2)
                        #stop_loss = StopLoss(df[0]['low'].iloc[i] - 2.)
                        stop_loss = StopLoss(min(df[0]['open'].iloc[i], df[0]['close'].iloc[i]) - 2.)

                        print(self.wallet.orders)

                #if abs(df[1]['RSI_14'].loc[ df[1]['timestamp'] == t ].values[0] - 30.) <= 3. and Memory.normalize_data(df[1]['volume'].loc[ df[1]['timestamp'] <= t ].iloc[i-9:i+1].values)[-1][0] > 0:
                elif df[1]['RSI_14'].loc[ df[1]['timestamp'] == t ].values[0] <= (30 + 4):# and Memory.normalize_data(df[1]['volume'].loc[ df[1]['timestamp'] <= t ].iloc[i-9:i+1].values)[-1][0] > 0:

                    # is 5min RSI up?
                    #if df[1]['RSI_14'].loc[ df[1]['timestamp'] <= t ].values[-1] - df[1]['RSI_14'].loc[ df[1]['timestamp'] <= t ].values[-3] > 0:

                    #elif row.name in filtered_30_index and Memory.normalize_data(df[0]['volume'].iloc[i-100:i], name="volume").iloc[-1] >= 25:
                    if row.name in filtered_30_index and Memory.normalize_data(df[0]['volume'].iloc[i-9:i+1].values)[-1][0] > 0:

                        print("Conditions satisfied, proceeding...")

                        self.wallet.open_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        # trailing stop:
                        trailing_stop = MyTrailingStop(row['close'] + 5.)

                        # take profit
                        take_profit = TakeProfit(min(df[0]['open'].iloc[i], df[0]['close'].iloc[i]) - 5.)

                        # stop loss:
                        #stop_loss = StopLoss(df[1]['high'].iloc[i-9:i].max() * 1.2)
                        #stop_loss = StopLoss(df[0]['high'].iloc[i] + 2.)
                        stop_loss = StopLoss(max(df[0]['open'].iloc[i], df[0]['close'].iloc[i]) + 2.)

                        print(self.wallet.orders)
                
                else:
                    print("...")

            elif self.wallet.is_open():
                
                print("waiting for close conditions")

                if self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_SHORT.value:

                    trailing_stop.update_stop(row['close'], Parameters.TYPE_SHORT.value)

                    t = row['timestamp'] - Backtest.modulo_5_minutes(row['timestamp']) * 60 - 5 * 60
                    
                    if stop_loss.check_trigger(row['close'], Parameters.TYPE_SHORT.value):

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "stop loss"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'
                    
                    '''if take_profit.check_trigger(row['close'], Parameters.TYPE_SHORT.value):

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "take profit"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'
                    '''
                    #if self.wallet.orders[self.wallet.INDEX]["Open"] - 2. > row['close'] and trailing_stop.check_trigger(row['close'], Parameters.TYPE_SHORT.value):
                    if trailing_stop.check_trigger(row['close'], Parameters.TYPE_SHORT.value):

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[0]["open"].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "trailing stop"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'
                    
                elif self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_LONG.value:

                    trailing_stop.update_stop(row['close'], Parameters.TYPE_LONG.value)

                    t = row['timestamp'] - Backtest.modulo_5_minutes(row['timestamp']) * 60 - 5 * 60
                    
                    #if self.wallet.orders[self.wallet.INDEX]["Open"] + 2. >= row['close'] and stop_loss.check_trigger(row['close'], Parameters.TYPE_LONG.value):
                    if stop_loss.check_trigger(row['close'], Parameters.TYPE_LONG.value):

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "stop loss"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'

                    '''if take_profit.check_trigger(row['close'], Parameters.TYPE_LONG.value):

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "take profit"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'
                    '''
                    #if self.wallet.orders[self.wallet.INDEX]["Open"] + 2. < row['close'] and trailing_stop.check_trigger(row['close'], Parameters.TYPE_LONG.value):
                    if trailing_stop.check_trigger(row['close'], Parameters.TYPE_LONG.value):

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[0]["open"].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "trailing stop"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'
                    
        return [ df[0], df[1] ]
    
    def backtest_4_1min_5min_borders_2_DEV(self, df):

        # isRSIup?

        # find bars where RSI >= 70 for 1min data
        filtered_70_df = df[0][df[0]['RSI_14'] >= (70 - 1)]
        filtered_70_index = filtered_70_df.index.tolist()

        # find bars where RSI <= 30 for 1min data
        filtered_30_df = df[0][df[0]['RSI_14'] <= (30 + 1)]
        filtered_30_index = filtered_30_df.index.tolist()

        param_i = 0

        for i, row in df[0].iloc[9:-1].iterrows(): #check

            if not self.wallet.is_open():

                #if row.name in filtered_70_index and Memory.normalize_data(df[0]['volume'].iloc[i-100:i], name="volume").iloc[-1] >= 25:
                if row.name in filtered_70_index and Memory.normalize_data(df[0]['volume'].iloc[i-9:i+1].values)[-1][0] > 1:

                    t = row['timestamp'] - Backtest.modulo_5_minutes(row['timestamp']) * 60 - 5 * 60
                    
                    if abs(df[1]['RSI_14'].loc[ df[1]['timestamp'] == t ].values[0] - 70.) <= 4.:
                        print("Conditions satisfied, proceeding...")

                        param_i = i

                        self.wallet.open_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        # stop loss:
                        stop_loss = StopLoss(min(df[0]['open'].iloc[i], df[0]['close'].iloc[i]) - 2.)

                        print(self.wallet.orders)

                #elif row.name in filtered_30_index and Memory.normalize_data(df[0]['volume'].iloc[i-100:i], name="volume").iloc[-1] >= 25:
                elif row.name in filtered_30_index and Memory.normalize_data(df[0]['volume'].iloc[i-9:i+1].values)[-1][0] > 1:

                    t = row['timestamp'] - Backtest.modulo_5_minutes(row['timestamp']) * 60 - 5 * 60

                    if abs(df[1]['RSI_14'].loc[ df[1]['timestamp'] == t ].values[0] - 30.) <= 4.:
                        print("Conditions satisfied, proceeding...")

                        param_i = i

                        self.wallet.open_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        # stop loss:
                        stop_loss = StopLoss(max(df[0]['open'].iloc[i], df[0]['close'].iloc[i]) + 2.)

                        print(self.wallet.orders)
                
                else:
                    print("...")

            elif self.wallet.is_open():
                
                print("waiting for close conditions")

                t = row['timestamp'] - Backtest.modulo_5_minutes(row['timestamp']) * 60 - 5 * 60

                if self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_SHORT.value:
                    
                    #if row['volume'] < df[0]['volume'].iloc[:i].tail(50).mean():
                    if row['RSI_14'] > min(df[0]['RSI_14'].iloc[param_i:i]):
                    #if df[1]['RSI_14'].loc[ df[1]['timestamp'] == t ].values[0] > min(df[1]['RSI_14'].loc[ df[1]['timestamp'] <= t ].values[-4:-1]):

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "rsi"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'
                    
                    '''if df[1]['RSI_14'].loc[ df[1]['timestamp'] == t ].values[0] < 35.:

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "rsi"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'
                    '''
                    if stop_loss.check_trigger(row['close'], Parameters.TYPE_SHORT.value):

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "stop loss"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'
                    
                elif self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_LONG.value:
                    
                    #if row['volume'] < df[0]['volume'].iloc[:i].tail(50).mean():
                    if row['RSI_14'] < max(df[0]['RSI_14'].iloc[param_i:i]):
                    #if df[1]['RSI_14'].loc[ df[1]['timestamp'] == t ].values[0] < max(df[1]['RSI_14'].loc[ df[1]['timestamp'] <= t ].values[-4:-1]):

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "rsi"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'
                    
                    '''if df[1]['RSI_14'].loc[ df[1]['timestamp'] == t ].values[0] > 65.:

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "rsi"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'
                    '''
                    if stop_loss.check_trigger(row['close'], Parameters.TYPE_LONG.value):

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "stop loss"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'
                    
        return [ df[0], df[1] ]
    
    def backtest_4_1min_5min_borders_3_DEV(self, df):

        # find bars where RSI >= 70 for 1min data
        filtered_70_df = df[0][df[0]['RSI_14'] >= (70 - 3)]
        filtered_70_index = filtered_70_df.index.tolist()

        # find bars where RSI <= 30 for 1min data
        filtered_30_df = df[0][df[0]['RSI_14'] <= (30 + 3)]
        filtered_30_index = filtered_30_df.index.tolist()

        param_i = 0

        for i, row in df[0].iloc[9:-1].iterrows():

            t = row['timestamp'] - Backtest.modulo_5_minutes(row['timestamp']) * 60 - 5 * 60

            if not self.wallet.is_open():

                if abs(row['RSI_14'] - 70.) <= 3. and Memory.normalize_data(df[0]['volume'].iloc[i-9:i+1].values)[-1][0] > 1:
                #if abs(df[1]['RSI_14'].loc[ df[1]['timestamp'] == t ].values[0] - 70.) <= 3. and Memory.normalize_data(df[1]['volume'].loc[ df[1]['timestamp'] <= t ].iloc[i-9:i+1].values)[-1][0] > 1:
                    print("Conditions satisfied, proceeding...")

                    param_i = i

                    self.wallet.open_position(
                        side="BUY",
                        quantity=self.qty,
                        price=df[0]['open'].iloc[i+1],
                        date=df[0]['date'].iloc[i+1]
                    )

                    # stop loss:
                    stop_loss = StopLoss(min(df[0]['open'].iloc[i], df[0]['close'].iloc[i]) - 5.)

                    print(self.wallet.orders)

                if abs(row['RSI_14'] - 30.) <= 3. and  Memory.normalize_data(df[0]['volume'].iloc[i-9:i+1].values)[-1][0] > 1:
                #if abs(df[1]['RSI_14'].loc[ df[1]['timestamp'] == t ].values[0] - 30.) <= 3. and Memory.normalize_data(df[1]['volume'].loc[ df[1]['timestamp'] <= t ].iloc[i-9:i+1].values)[-1][0] > 1:
                    print("Conditions satisfied, proceeding...")

                    param_i = i

                    self.wallet.open_position(
                        side="SELL",
                        quantity=self.qty,
                        price=df[0]['open'].iloc[i+1],
                        date=df[0]['date'].iloc[i+1]
                    )

                    # stop loss:
                    stop_loss = StopLoss(max(df[0]['open'].iloc[i], df[0]['close'].iloc[i]) + 5.)

                    print(self.wallet.orders)

                else:
                    print("...")
        
            elif self.wallet.is_open():
                
                print("waiting for close conditions")

                t = row['timestamp'] - Backtest.modulo_5_minutes(row['timestamp']) * 60 - 5 * 60

                if self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_SHORT.value:
                    
                    if row['RSI_14'] > min(df[0]['RSI_14'].iloc[param_i:i]):

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "rsi"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'

                elif self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_LONG.value:
                    
                    if row['RSI_14'] < max(df[0]['RSI_14'].iloc[param_i:i]):

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "rsi"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'
        
        return [ df[0], df[1] ]
    
    '''GENERATE COEFF'''
    @staticmethod
    def generate_coef(df, i):

        return abs(df['RSI_14'].iloc[i] - 50) * df['volume'].iloc[i]

    @staticmethod
    def generate_norm_coef(df, i):

        return abs(df['RSI_14'].iloc[i] - 50) * Memory.normalize_data(df['volume'].iloc[i-9:i+1].values)[-1][0]
    
    @staticmethod
    def generate_minmax_coef(df, i):

        return abs(df['RSI_14'].iloc[i] - 50) * Memory.minmax_data(df['volume'].iloc[i-9:i+1].values)[-1][0]

    @staticmethod
    def variation_rate(old_value, new_value):

        return ((new_value - old_value) / old_value) * 100
    
    def backtest_4_1min_5min_borders_coef_DEV(self, df):

        # find bars where RSI >= 70 for 1min data
        filtered_70_df = df[0][df[0]['RSI_14'] >= (70 - 3)]
        filtered_70_index = filtered_70_df.index.tolist()

        # find bars where RSI <= 30 for 1min data
        filtered_30_df = df[0][df[0]['RSI_14'] <= (30 + 3)]
        filtered_30_index = filtered_30_df.index.tolist()

        '''>>>>>>>>>>>>>>>>>>>>>>>'''
        date = []
        coef = []
        n_coef = []
        taux = [None]

        for i, row in df[0].iterrows():
            #print(row['date'], Backtest.generate_coef(df[0], i))
            date.append(row['date'])
            coef.append(Backtest.generate_coef(df[0], i))
        
        for i, row in df[0].iloc[9:-1].iterrows():
            n_coef.append(Backtest.generate_norm_coef(df[0], i))

        for i, row in df[0].iloc[1:].iterrows():
            taux.append(Backtest.variation_rate(coef[i-1], coef[i]))
        '''>>>>>>>>>>>>>>>>>>>>>>>'''

        for i, row in df[0].iloc[9:-1].iterrows():

            if not self.wallet.is_open():

                #if Backtest.generate_coef(df[0], i) > 55000:
                if Backtest.generate_norm_coef(df[0], i) > 10:

                    if row['RSI_14'] > 50:

                        self.wallet.open_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        # trailing stop
                        trailing_stop = MyTrailingStop(row['close'] - 5.)

                        # stop loss:
                        stop_loss = StopLoss(min(df[0]['open'].iloc[i], df[0]['close'].iloc[i]) - 3.)

                        # take profit
                        take_profit = TakeProfit(max(df[0]['open'].iloc[i], df[0]['close'].iloc[i]) + 5.)

                        print(self.wallet.orders)

                    elif row['RSI_14'] < 50:

                        self.wallet.open_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        # trailing stop
                        trailing_stop = MyTrailingStop(row['close'] + 5.)

                        # stop loss:
                        stop_loss = StopLoss(min(df[0]['open'].iloc[i], df[0]['close'].iloc[i]) + 3.)

                        # take profit
                        take_profit = TakeProfit(max(df[0]['open'].iloc[i], df[0]['close'].iloc[i]) - 5.)

                        print(self.wallet.orders)

                    else:
                        print("...")
            
            elif self.wallet.is_open():
                
                print("waiting for close conditions")

                if self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_SHORT.value:

                    trailing_stop.update_stop(row['close'], Parameters.TYPE_SHORT.value)

                    '''if take_profit.check_trigger(row['close'], Parameters.TYPE_SHORT.value):

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "take profit"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'
                    '''
                    if self.wallet.orders[self.wallet.INDEX]["Open"] > row['close'] and trailing_stop.check_trigger(row['close'], Parameters.TYPE_SHORT.value):

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[0]["open"].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "trailing stop"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'
                    
                    if stop_loss.check_trigger(row['close'], Parameters.TYPE_SHORT.value):

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "stop loss"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'

                elif self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_LONG.value:

                    trailing_stop.update_stop(row['close'], Parameters.TYPE_LONG.value)
                    
                    '''if take_profit.check_trigger(row['close'], Parameters.TYPE_LONG.value):

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "take profit"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'
                    '''
                    if self.wallet.orders[self.wallet.INDEX]["Open"] < row['close'] and trailing_stop.check_trigger(row['close'], Parameters.TYPE_LONG.value):

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[0]["open"].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "trailing stop"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'

                    if stop_loss.check_trigger(row['close'], Parameters.TYPE_LONG.value):

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "stop loss"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'
        
        return [ df[0], df[1] ]
    
    def backtest_4_1min_5min_borders_coef_2_DEV(self, df):

        # find bars where RSI >= 70 for 1min data
        filtered_70_df = df[0][df[0]['RSI_14'] >= (70 - 3)]
        filtered_70_index = filtered_70_df.index.tolist()

        # find bars where RSI <= 30 for 1min data
        filtered_30_df = df[0][df[0]['RSI_14'] <= (30 + 3)]
        filtered_30_index = filtered_30_df.index.tolist()

        '''>>>>>>>>>>>>>>>>>>>>>>>'''
        date = []
        coef = []
        n_coef = []
        m_coef = []
        taux = [None]

        for i, row in df[0].iterrows():
            #print(row['date'], Backtest.generate_coef(df[0], i))
            date.append(row['date'])
            coef.append(Backtest.generate_coef(df[0], i))

        for i, row in df[0].iloc[9:-1].iterrows():
            n_coef.append(Backtest.generate_norm_coef(df[0], i))
            m_coef.append(Backtest.generate_minmax_coef(df[0], i))

        for i, row in df[0].iloc[1:].iterrows():
            taux.append(Backtest.variation_rate(coef[i-1], coef[i]))
        '''>>>>>>>>>>>>>>>>>>>>>>>'''

        for i, row in df[0].iloc[9:-1].iterrows():

            if not self.wallet.is_open():

                #if Backtest.generate_coef(df[0], i) > 55000 and Backtest.generate_coef(df[0], i) < 155000:
                #if Backtest.variation_rate(Backtest.generate_coef(df[0], i-1), Backtest.generate_coef(df[0], i)) > 200:
                #if Backtest.generate_norm_coef(df[0], i) > 10:
                if Backtest.generate_minmax_coef(df[0], i) > 10:

                    #if row['RSI_14'] - df[0]['RSI_14'].iloc[i-3] > 0:
                    if row['RSI_14'] > df[0]['RSI_14'].iloc[i-5:i].mean():
                    #if row['RSI_14'] > 50:

                        self.wallet.open_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        # trailing stop
                        trailing_stop = MyTrailingStop(row['close'] - 2.)

                        # stop loss:
                        stop_loss = StopLoss(min(df[0]['open'].iloc[i], df[0]['close'].iloc[i]) - 3.)

                        # take profit
                        take_profit = TakeProfit(max(df[0]['open'].iloc[i], df[0]['close'].iloc[i]) + 5.)

                        print(self.wallet.orders)

                    #elif row['RSI_14'] - df[0]['RSI_14'].iloc[i-3] < 0:
                    elif row['RSI_14'] < df[0]['RSI_14'].iloc[i-5:i].mean():
                    #elif row['RSI_14'] < 50:

                        self.wallet.open_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        # trailing stop
                        trailing_stop = MyTrailingStop(row['close'] + 2.)

                        # stop loss:
                        stop_loss = StopLoss(max(df[0]['open'].iloc[i], df[0]['close'].iloc[i]) + 3.)

                        # take profit
                        take_profit = TakeProfit(min(df[0]['open'].iloc[i], df[0]['close'].iloc[i]) - 5.)

                        print(self.wallet.orders)

                else:
                    print("...")
            
            elif self.wallet.is_open():
                
                print("waiting for close conditions")

                if self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_SHORT.value:

                    trailing_stop.update_stop(row['close'], Parameters.TYPE_SHORT.value)

                    '''if take_profit.check_trigger(row['close'], Parameters.TYPE_SHORT.value):

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "take profit"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'
                    '''

                    if self.wallet.orders[self.wallet.INDEX]["Open"] > row['close'] and trailing_stop.check_trigger(row['close'], Parameters.TYPE_SHORT.value):

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[0]["open"].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "trailing stop"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'
                    
                    elif stop_loss.check_trigger(row['close'], Parameters.TYPE_SHORT.value):

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "stop loss"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'

                elif self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_LONG.value:

                    trailing_stop.update_stop(row['close'], Parameters.TYPE_LONG.value)
                    
                    '''if take_profit.check_trigger(row['close'], Parameters.TYPE_LONG.value):

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "take profit"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'
                    '''

                    if self.wallet.orders[self.wallet.INDEX]["Open"] < row['close'] and trailing_stop.check_trigger(row['close'], Parameters.TYPE_LONG.value):

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[0]["open"].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "trailing stop"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'

                    elif stop_loss.check_trigger(row['close'], Parameters.TYPE_LONG.value):

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "stop loss"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'
        
        return [ df[0], df[1] ]
    
    def test_coef(self, df):
        # with 1sec Data...
        
        actual_coef = 0.

        for i, row in df[0].iloc[9:-1].iterrows():

            #with open("coef_output.csv", "a") as r:
            #    d = "{},{:.{}f}\n".format(i, Backtest.generate_minmax_coef(df[0], i), 2)
            #    r.write(d)
        
            if not self.wallet.is_open():

                if Backtest.generate_minmax_coef(df[0], i) > 10:

                    actual_coef = Backtest.generate_minmax_coef(df[0], i)

                    if row['RSI_14'] > 50 and row['RSI_14'] > df[0]['RSI_14'].iloc[i-5:i].mean():

                        self.wallet.open_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        # trailing stop
                        trailing_stop = MyTrailingStop(row['close'] - 2.)

                        # stop loss:
                        stop_loss = StopLoss(min(df[0]['open'].iloc[i], df[0]['close'].iloc[i]) - 2.)

                        # take profit
                        take_profit = TakeProfit(max(df[0]['open'].iloc[i], df[0]['close'].iloc[i]) + 5.)

                        print(self.wallet.orders)

                    elif row['RSI_14'] < 50 and row['RSI_14'] < df[0]['RSI_14'].iloc[i-5:i].mean():

                        self.wallet.open_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        # trailing stop
                        trailing_stop = MyTrailingStop(row['close'] + 2.)

                        # stop loss:
                        stop_loss = StopLoss(max(df[0]['open'].iloc[i], df[0]['close'].iloc[i]) + 2.)

                        # take profit
                        take_profit = TakeProfit(min(df[0]['open'].iloc[i], df[0]['close'].iloc[i]) - 5.)

                        print(self.wallet.orders)

                else:
                    print("...")

            elif self.wallet.is_open():

                print("waiting for close conditions")

                if self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_SHORT.value:

                    trailing_stop.update_stop(row['close'], Parameters.TYPE_SHORT.value)
                    '''
                    if self.wallet.orders[self.wallet.INDEX]["Open"] > row['close'] and trailing_stop.check_trigger(row['close'], Parameters.TYPE_SHORT.value):

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[0]["open"].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "trailing stop"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'
                    '''
                    if Backtest.generate_minmax_coef(df[0], i) > actual_coef:

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "coef comparison"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'
                    
                    elif stop_loss.check_trigger(row['close'], Parameters.TYPE_SHORT.value):

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "stop loss"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'

                elif self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_LONG.value:

                    trailing_stop.update_stop(row['close'], Parameters.TYPE_LONG.value)
                    
                    '''
                    if self.wallet.orders[self.wallet.INDEX]["Open"] < row['close'] and trailing_stop.check_trigger(row['close'], Parameters.TYPE_LONG.value):

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[0]["open"].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "trailing stop"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'
                    '''
                    if Backtest.generate_minmax_coef(df[0], i) > actual_coef:

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "coef comparison"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'
                    
                    elif stop_loss.check_trigger(row['close'], Parameters.TYPE_LONG.value):

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=df[0]['open'].iloc[i+1],
                            date=df[0]['date'].iloc[i+1]
                        )

                        self.wallet.orders[self.wallet.INDEX]["NOT"] = "stop loss"
                        self.wallet.orders[self.wallet.INDEX]['Duration'] = str(int((datetime.strptime(df[0]['date'].iloc[i+1], '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.wallet.orders[self.wallet.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'

        return [ df[0], df[1], df[2] ]
    
    