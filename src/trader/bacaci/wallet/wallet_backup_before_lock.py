import os
import json
from datetime import datetime, timedelta

from ..accounts.binance import Binance
#from ..accounts.alpaca import Alpaca
from ..accounts.interactiveBrokers import InteractiveBrokers
from ..accounts.bloomberg import Bloomberg
from ..database import Database
from ..data import Data
#from ..memory import Memory
from ..enums import Parameters

class Wallet:

    def __init__(self, api, symbol, test_mode=False, lock=False):
        
        self.API = api
        self.SYMBOL = symbol
        self.TEST_MODE = test_mode
        #self.qty = Parameters.QUANTITY.value

        if self.TEST_MODE:
            print("Proceeding in Test Mode")
            pass

        elif self.API == Parameters.BINANCE.value:
            self.binance = Binance()

        #elif self.API == Parameters.ALPACA.value:
        #    self.alpaca = Alpaca()

        elif self.API == Parameters.IB.value:
            self.interactive_brokers = InteractiveBrokers()
        
        # save orders to a symbol_file.json
        self.orders = {}
        self.INDEX = 0
        self.orders[self.INDEX] = {
            'Symbol': self.SYMBOL,
            'Side': None,
            'Open': 0,
            'DateOpen': None,
            'Quantity': 0,
            'Commission_open': float(Parameters.COMMISSION.value), # adjust it
            'Commission_close': float(Parameters.COMMISSION.value), # adjust it
            'Close': 0,
            'DateClose': None,
            'Profit': 0,
            'Balance': int(Parameters.CAPITAL.value),
            'Duration': None,
            'IsOpen': False
        }

        if self.is_open():
            self.close_wallet()
        
        '''for file in os.listdir(os.getcwd()):
            if file.startswith("wallet"):
                file_path = os.path.join(os.getcwd(), file)
                os.remove(file_path)
        print("All open wallets have been closed.")'''

    '''more than 1 lock'''
    def open_wallet(self):
        if not os.path.exists(os.getcwd()+f"/wallet_{self.SYMBOL}.lock"):
            with open(os.getcwd()+f"/wallet_{self.SYMBOL}.lock", "w") as wallet:
                wallet.write("")

    def close_wallet(self):
        if os.path.exists(os.getcwd()+f"/wallet_{self.SYMBOL}.lock"):
            os.remove(os.getcwd()+f"/wallet_{self.SYMBOL}.lock")

    def is_open(self):
        if os.path.exists(os.getcwd()+f"/wallet_{self.SYMBOL}.lock"):
            return True
        else:
            return False
    '''

    def open_wallet(self):
        _flag = {
            "IsOpen": True
        }

        with open(f"wallet_{self.SYMBOL}.lock", "w") as wallet:
            wallet.write(json.dumps(_flag))

    def close_wallet(self):
        _flag = {
            "IsOpen": False
        }

        with open(f"wallet_{self.SYMBOL}.lock", "w") as wallet:
            wallet.write(json.dumps(_flag))

    def is_open(self):
        if os.path.exists(f"wallet_{self.SYMBOL}.lock"):
            with open(f"wallet_{self.SYMBOL}.lock", "r") as wallet:
                _flag = json.load(wallet)
                if _flag["IsOpen"] is True:
                    return True
                else:
                    return False
        else:
            return False
        
    '''        
    def save_orders_to_json(self):
        with open(f"orders_{self.SYMBOL}.json", "w") as wallet:
            wallet.write(json.dumps(self.orders))

    def open_position(self, side, quantity, price, date):

        # check if wallet is open, if not open it
        if not self.is_open():
            self.open_wallet()

        self.INDEX += 1

        # process
        if self.TEST_MODE:
            pass

        else:
            if self.API == Parameters.BINANCE.value:
                self.binance.futures_open_position(self.SYMBOL, side, quantity)

            elif self.API == Parameters.ALPACA.value:
                self.alpaca.open_position(self.SYMBOL, side, quantity)

            elif self.API == Parameters.IB.value:
                pass

        self.orders[self.INDEX] = {
            'Symbol': self.SYMBOL,
            'Side': side,
            'Open': price,
            'DateOpen': date,
            'Quantity': quantity,
            'Commission_open': Parameters.COMMISSION.value,
            'Commission_close': Parameters.COMMISSION.value,
            'Close': None,
            'DateClose': None,
            'Profit': None,
            'Balance': self.orders[self.INDEX - 1]['Balance'], # calculate balance
            'Duration': None,
            'IsOpen': True
        }

        # save orders to json
        #self.save_orders_to_json()

        return self.orders

    def close_position(self, side, quantity, price, date):

        # process
        if self.TEST_MODE:
            pass

        else:
            if self.API == Parameters.BINANCE.value:
                self.binance.futures_close_position(self.SYMBOL, side, quantity)

            elif self.API == Parameters.ALPACA.value:
                self.alpaca.close_position(self.SYMBOL, side, quantity)

            elif self.API == Parameters.IB.value:
                pass

        self.orders[self.INDEX]['Close'] = price
        self.orders[self.INDEX]['DateClose'] = date
        self.orders[self.INDEX]['IsOpen'] = False
        #self.orders[self.INDEX]['Duration'] = str(int((datetime.strptime(date, '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.orders[self.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'

        if self.orders[self.INDEX]['Side'] == Parameters.TYPE_LONG.value:
            self.orders[self.INDEX]['Profit'] = (self.orders[self.INDEX]['Close'] - self.orders[self.INDEX]['Open']) * float(self.orders[self.INDEX]['Quantity']) * int(Parameters.INDEX_POINT.value) - 2 * float(Parameters.COMMISSION.value)
        elif self.orders[self.INDEX]['Side'] == Parameters.TYPE_SHORT.value:
            self.orders[self.INDEX]['Profit'] = (self.orders[self.INDEX]['Open'] - self.orders[self.INDEX]['Close']) * float(self.orders[self.INDEX]['Quantity']) * int(Parameters.INDEX_POINT.value) - 2 * float(Parameters.COMMISSION.value)

        self.orders[self.INDEX]['Balance'] = self.orders[self.INDEX - 1]['Balance'] + self.orders[self.INDEX]['Profit']

        # save orders to json
        #self.save_orders_to_json()

        # close the Wallet
        self.close_wallet()

        # return "orders"
        return self.orders
    
    def stop_loss(self, df, i, percentage):
        # abs() < eps ile yakınsama?

        if self.orders[self.INDEX]["Side"] == Parameters.TYPE_LONG.value:
            if df["close"].iloc[i] < (100 - percentage) * 0.01 * self.orders[self.INDEX]['Open']:
                return True
            else:
                return False

        elif self.orders[self.INDEX]["Side"] == Parameters.TYPE_SHORT.value:
            if df["close"].iloc[i] > (100 + percentage) * 0.01 * self.orders[self.INDEX]['Open']:
                return True
            else:
                return False
        
        else:
            return False
        
    def stop_loss_2(self, close, percentage):

        if self.orders[self.INDEX]["Side"] == Parameters.TYPE_LONG.value:
            if close < (100 - percentage) * 0.01 * self.orders[self.INDEX]['Open']:
                return True
            else:
                return False

        elif self.orders[self.INDEX]["Side"] == Parameters.TYPE_SHORT.value:
            if close > (100 + percentage) * 0.01 * self.orders[self.INDEX]['Open']:
                return True
            else:
                return False

        else:
            return False
    
    def take_profit(self, df, i, percentage):
        # abs() < eps ile yakınsama?

        if self.orders[self.INDEX]["Side"] == Parameters.TYPE_LONG.value:
            if df["close"].iloc[i] > (100 + percentage) * self.orders[self.INDEX]['Open']:
                return True
            else:
                return False

        elif self.orders[self.INDEX]["Side"] == Parameters.TYPE_SHORT.value:
            if df["close"].iloc[i] < (100 - percentage) * self.orders[self.INDEX]['Open']:
                return True
            else:
                return False
        
        else:
            return False

    def dummy_trailing_stop(self, df, i):
        # to correct...

        if df["close"].iloc[i-1] - df["close"].iloc[i] > 1.:
            return True
        
        else:
            return False
    
    def trailing_stop(self, df, i):
        # to develop...

        if self.orders[self.INDEX]["Side"] == Parameters.TYPE_LONG.value:
            if df["close"].iloc[i-1] - df["close"].iloc[i] > 5.:
                return True
            else:
                return False
        
        elif self.orders[self.INDEX]["Side"] == Parameters.TYPE_SHORT.value:
            if df["close"].iloc[i] - df["close"].iloc[i-1] > 5.:
                return True
            else:
                return False
        
        else:
            return False