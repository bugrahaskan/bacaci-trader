import os
import json
from datetime import datetime, timedelta
from binance.client import Client

from ..accounts.binance import Binance
#from ..accounts.alpaca import Alpaca
from ..accounts.interactiveBrokers import InteractiveBrokers
from ..accounts.bloomberg import Bloomberg
from ..database import Database
from ..data import Data
#from ..memory import Memory
from ..enums import Parameters

class Wallet:

    def __init__(self, api, symbol, test_mode=False):
        
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
            'Percent': 0,
            'Balance': int(Parameters.CAPITAL.value),
            'Duration': None,
            'IsOpen': False,
            'NOT': None,
            'IdOpen': None,
            'IdClose': None
        }
        
        for file in os.listdir(os.getcwd()):
            if file.startswith("wallet_"):
                file_path = os.path.join(os.getcwd(), file)
                os.remove(file_path)

        if self.is_open():
            self.close_wallet()

        print("All open wallets have been removed.")

    '''more than 1 lock'''
    def open_wallet(self, key=None):
        _flag = {
            "IsOpen": True
        }

        if not key is None:
            with open(os.getcwd()+f"/wallet_{self.SYMBOL}_{key}.lock", "w") as wallet:
                wallet.write(json.dumps(_flag))
        else:
            with open(os.getcwd()+f"/wallet_{self.SYMBOL}.lock", "w") as wallet:
                wallet.write(json.dumps(_flag))

    def close_wallet(self, key=None):
        _flag = {
            "IsOpen": False
        }

        if not key is None:
            with open(os.getcwd()+f"/wallet_{self.SYMBOL}_{key}.lock", "w") as wallet:
                wallet.write(json.dumps(_flag))
        else:
            with open(os.getcwd()+f"/wallet_{self.SYMBOL}.lock", "w") as wallet:
                wallet.write(json.dumps(_flag))

    def is_open(self, key=None):
        if not key is None:
            if os.path.exists(os.getcwd()+f"/wallet_{self.SYMBOL}_{key}.lock"):
                with open(os.getcwd()+f"/wallet_{self.SYMBOL}_{key}.lock", "r") as wallet:
                    _flag = json.load(wallet)
                    if _flag["IsOpen"] is True:
                        return True
                    else:
                        return False
            else:
                return False
        else:
            if os.path.exists(os.getcwd()+f"/wallet_{self.SYMBOL}.lock"):
                with open(os.getcwd()+f"/wallet_{self.SYMBOL}.lock", "r") as wallet:
                    _flag = json.load(wallet)
                    if _flag["IsOpen"] is True:
                        return True
                    else:
                        return False
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

    def open_position(self, side, quantity, price, date, type=Client.FUTURE_ORDER_TYPE_MARKET, key=None):

        # check if wallet is open, if not open it
        if not key is None:
            if not self.is_open(key):
                self.open_wallet(key)
        else:
            if not self.is_open():
                self.open_wallet()

        self.INDEX += 1

        # process
        if self.TEST_MODE:
            pass

        else:
            if self.API == Parameters.BINANCE.value:
                if type == Client.FUTURE_ORDER_TYPE_MARKET:
                    ord = self.binance.futures_open_position(self.SYMBOL, side, quantity)
                elif type == Client.FUTURE_ORDER_TYPE_LIMIT:
                    ord = self.binance.futures_open_position(self.SYMBOL, side, quantity, price=price, type=type)

            elif self.API == Parameters.ALPACA.value:
                self.alpaca.open_position(self.SYMBOL, side, quantity)

            elif self.API == Parameters.IB.value:
                pass


        if self.TEST_MODE:
            self.orders[self.INDEX] = {
                'Symbol': self.SYMBOL,
                'Side': side,
                'Open': price,
                'DateOpen': date,
                'Quantity': quantity, # kaldıraçlı işlem hacmi
                'Commission_open': None,
                'Commission_close': None,
                'Close': None,
                'DateClose': None,
                'Profit': None,
                'Percent': None,
                'Balance': self.orders[self.INDEX - 1]['Balance'], # calculate balance
                'Duration': None,
                'IsOpen': True,
                'NOT': None,
                'IdOpen': None, # in trade mode only
                'IdClose': None
            }

        else:
            #self.binance.client.futures_get_order(symbol=ord['Symbol'], orderId=ord['OrderID'])

            self.orders[self.INDEX] = {
                'Symbol': self.SYMBOL,
                'Side': side,
                'Open': price,
                'DateOpen': date,
                'Quantity': quantity, # kaldıraçlı işlem hacmi
                'Commission_open': None,
                'Commission_close': None,
                'Close': None,
                'DateClose': None,
                'Profit': None,
                'Percent': None,
                'Balance': self.orders[self.INDEX - 1]['Balance'], # calculate balance
                'Duration': None,
                'IsOpen': True,
                'NOT': None,
                'IdOpen': ord['OrderID'], # in trade mode only
                'IdClose': None
            }

        if self.API == Parameters.BINANCE.value:
            self.orders[self.INDEX]['Commission_open'] = self.orders[self.INDEX]['Open'] * float(self.orders[self.INDEX]['Quantity']) * float(Parameters.COMMISSION.value) / 100

        elif self.API == Parameters.IB.value:
            self.orders[self.INDEX]['Commission_open'] = Parameters.COMMISSION.value

        self.orders[self.INDEX]['Balance'] = self.orders[self.INDEX - 1]['Balance'] - self.orders[self.INDEX]['Commission_open']

        # save orders to json
        #self.save_orders_to_json()

        return self.orders

    def close_position(self, side, quantity, price, date, type=Client.FUTURE_ORDER_TYPE_MARKET, key=None):

        # process
        if self.TEST_MODE:
            pass

        else:
            if self.API == Parameters.BINANCE.value:
                if type == Client.FUTURE_ORDER_TYPE_MARKET:
                    ord = self.binance.futures_close_position(self.SYMBOL, side, quantity)
                elif type == Client.FUTURE_ORDER_TYPE_LIMIT:
                    ord = self.binance.futures_close_position(self.SYMBOL, side, quantity, price=price, type=type)

            elif self.API == Parameters.ALPACA.value:
                self.alpaca.close_position(self.SYMBOL, side, quantity)

            elif self.API == Parameters.IB.value:
                pass

        self.orders[self.INDEX]['Close'] = price
        self.orders[self.INDEX]['DateClose'] = date
        self.orders[self.INDEX]['IsOpen'] = False
        #self.orders[self.INDEX]['Duration'] = str(int((datetime.strptime(date, '%Y-%m-%d %H:%M:%S') - datetime.strptime(self.orders[self.INDEX]['DateOpen'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60))+'min'
        
        if self.TEST_MODE:
            self.orders[self.INDEX]['IdClose'] = None
        else:
            self.orders[self.INDEX]['IdClose'] = ord['OrderID']

        if self.API == Parameters.BINANCE.value:
            self.orders[self.INDEX]['Commission_close'] = self.orders[self.INDEX]['Close'] * float(self.orders[self.INDEX]['Quantity']) * float(Parameters.COMMISSION.value) / 100

        elif self.API == Parameters.IB.value:
            self.orders[self.INDEX]['Commission_close'] = Parameters.COMMISSION.value

        if self.orders[self.INDEX]['Side'] == Parameters.TYPE_LONG.value:
            self.orders[self.INDEX]['Profit'] = (self.orders[self.INDEX]['Close'] - self.orders[self.INDEX]['Open']) * float(self.orders[self.INDEX]['Quantity'])

        elif self.orders[self.INDEX]['Side'] == Parameters.TYPE_SHORT.value:
            self.orders[self.INDEX]['Profit'] = (self.orders[self.INDEX]['Open'] - self.orders[self.INDEX]['Close']) * float(self.orders[self.INDEX]['Quantity'])

        self.orders[self.INDEX]['Percent'] = self.orders[self.INDEX]['Profit'] / (float(self.orders[self.INDEX]['Quantity']) * self.orders[self.INDEX]['Close'])
        self.orders[self.INDEX]['Balance'] = self.orders[self.INDEX - 1]['Balance'] + self.orders[self.INDEX]['Profit'] - (self.orders[self.INDEX]['Commission_open'] + self.orders[self.INDEX]['Commission_close'])

        # save orders to json
        #self.save_orders_to_json()

        if not key is None:
            self.INDEX += 1

        # close the Wallet
        if not key is None:
            self.close_wallet(key)
        else:
            self.close_wallet()

        # return "orders"
        return self.orders
    
    # perimated
    '''def stop_loss(self, df, i, percentage):
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
            return False'''
        
    # perimated
    '''def stop_loss_2(self, close, percentage):

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
            return False'''
    
    # perimated
    '''def take_profit(self, df, i, percentage):
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
            return False'''

    # perimated
    '''def dummy_trailing_stop(self, df, i):
        # to correct...

        if df["close"].iloc[i-1] - df["close"].iloc[i] > 1.:
            return True
        
        else:
            return False'''
    
    # perimated
    '''def trailing_stop(self, df, i):
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
            return False'''


class TrailingStop:

    def __init__(self, trailing_percent, initial_stop):
        self.trailing_percent = trailing_percent  # Trailing stop percentage
        self.initial_stop = initial_stop  # Initial stop-loss price
        self.current_stop = initial_stop  # Current stop-loss price

    def actual_stop(self):

        return self.current_stop
  
    def update_stop(self, current_price, side):

        if side == Parameters.TYPE_LONG.value:
            # Calculate the new stop-loss price based on the trailing percent
            trailing_distance = (current_price - self.initial_stop) * (self.trailing_percent / 100)
            new_stop = current_price - trailing_distance

            # Update the stop-loss if the new price is higher (for long positions)
            if new_stop > self.current_stop:
                self.current_stop = new_stop

            return self.current_stop

        elif side == Parameters.TYPE_SHORT.value:
            # Calculate the new stop-loss price based on the trailing percent
            trailing_distance = (self.initial_stop - current_price) * (self.trailing_percent / 100)
            new_stop = current_price + trailing_distance

            # Update the stop-loss if the new price is higher (for long positions)
            if new_stop < self.current_stop:
                self.current_stop = new_stop

            return self.current_stop


class MyTrailingStop:

    def __init__(self, initial_stop):
        self.initial_stop = initial_stop
        self.current_stop = initial_stop
        self.stop_loss = StopLoss(self.initial_stop)

    def actual_stop(self):

        return self.current_stop
        
    def update_stop(self, current_price, side):

        if side == Parameters.TYPE_LONG.value:
            trailing_distance = (current_price - self.current_stop) * (50 / 100)
            new_stop = current_price - trailing_distance
            
            #new_stop = current_price - 3.
            
            if new_stop > self.current_stop:
                self.current_stop = new_stop

            self.stop_loss = StopLoss(self.current_stop)

            return self.current_stop

        elif side == Parameters.TYPE_SHORT.value:
            trailing_distance = (current_price - self.current_stop) * (50 / 100)
            new_stop = current_price + trailing_distance
            
            #new_stop = current_price + 3.

            if new_stop < self.current_stop:
                self.current_stop = new_stop
            
            self.stop_loss = StopLoss(self.current_stop)

            return self.current_stop
        
    def set_stop(self, new_stop, side):

        if side == Parameters.TYPE_LONG.value:
            if new_stop > self.current_stop:
                self.current_stop = new_stop

            self.stop_loss = StopLoss(self.current_stop)

            return self.current_stop

        if side == Parameters.TYPE_SHORT.value:
            if new_stop < self.current_stop:
                self.current_stop = new_stop

            self.stop_loss = StopLoss(self.current_stop)

            return self.current_stop

    def check_trigger(self, current_price, side):

        return self.stop_loss.check_trigger(current_price, side)


class StopLoss:

    def __init__(self, stop_price):
        self.stop_price = stop_price  # The fixed stop-loss price
    
    def check_trigger(self, current_price, side):

        if side == Parameters.TYPE_LONG.value:
            # Check if the current price has fallen below the stop price
            if current_price < self.stop_price:
                return True  # The stop-loss has triggered
            else:
                return False  # The stop-loss has not triggered
        
        elif side == Parameters.TYPE_SHORT.value:
            # Check if the current price has fallen below the stop price
            if current_price > self.stop_price:
                return True  # The stop-loss has triggered
            else:
                return False  # The stop-loss has not triggered
            

class TakeProfit:

    def __init__(self, stop_price):
        self.stop_price = stop_price

    def check_trigger(self, current_price, side):

        if side == Parameters.TYPE_LONG.value:

            if current_price >= self.stop_price:
                return True
            else:
                return False

        elif side == Parameters.TYPE_SHORT.value:
            
            if current_price <= self.stop_price:
                return True
            else:
                return False