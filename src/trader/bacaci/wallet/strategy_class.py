import os
import pandas as pd
import time
import asyncio
import configparser
import json

from ..database import Database
from .wallet import Wallet
from ..data import Data
from ..enums import Parameters
from ..indicators import rsi as RSI, HeikinAshi

class StrategyGeneric:

    def __init__(self, api, symbol, test_mode=False):
        
        self.API = api
        self.SYMBOL = symbol
        self.TEST_MODE = test_mode
        self.qty = Parameters.QUANTITY.value

        self.wallet = Wallet(
            api=self.API,
            symbol=self.SYMBOL,
            test_mode=self.TEST_MODE
            )
        
        if self.TEST_MODE:
            print("Proceeding to Backtest...")
            time.sleep(1)
        else:
            print("Strategy created")
            time.sleep(1)

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
        #intervals = ['1s', '1m', '5m', '15m']

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
                RSI(df) for df in dfs
            ]

        # other check functions
        # write to excel
        self.write_to_excel(rsi)

        return rsi

    def read_memory(self):

        with open(f"memory_{self.SYMBOL}.json", "r") as memory:
            data = json.load(memory)
        
        return data

    async def check_conditions(self, cond):
        
        await asyncio.sleep(10)

        if cond:
            return True
        else:
            return False

    async def trade(self):
        pass

    def backtest(self):
        self.database = Database(
            db_name=Parameters.DATABASE.value
            )
        self.database.connect_db()
        
        test_15min = 90 * 24 * 4 + 10
        test_5min = 1 * (90 * 24 * 12) + 10
        test_1min = 90 * 24 * 60 + 10

        #df0 = pd.read_csv('NQZ2 Index-1min-t.csv')
        #df1 = pd.read_csv('NQZ2 Index-5min-t.csv')
        #rsi0 = RSI(df0)
        #rsi1 = RSI(df1)
        #res = self.backtest_4_1min_5min_stabil_rsi_DEV(df=[rsi0,rsi1])

        res = self.backtest_4_1min_5min_borders_coef_2_DEV(df=self.read_data(test_1min))
        #res = self.backtest_dummy(df=self.read_data(1000))

        self.write_to_excel(res)