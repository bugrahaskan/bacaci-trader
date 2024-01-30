import threading

from .bacaci import Bacaci

#from .wallet.wallet import Wallet
from .wallet.strategy import Strategy
from bacaci.memory import Memory


class DataThread(threading.Thread):

    def __init__(self, api, symbol, arg):
        threading.Thread.__init__(self)

        self.API = api
        self.SYMBOL = symbol
        self.ARG = arg

    def run(self):
        self.bacaci = Bacaci(self.API, self.SYMBOL, self.ARG)


class TradeThread(threading.Thread):

    def __init__(self, api, symbol, test_mode=False):
        threading.Thread.__init__(self)

        self.API = api
        self.SYMBOL = symbol
        self.TEST_MODE = test_mode

    def run(self):
            self.strategy = Strategy(api=self.API, symbol=self.SYMBOL, test_mode=self.TEST_MODE) # which strategy
            
            # backtest
            if self.TEST_MODE:
                pass