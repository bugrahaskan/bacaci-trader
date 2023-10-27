import time

from .accounts.binance import Binance
#from .accounts.alpaca import Alpaca
from .accounts.interactiveBrokers import InteractiveBrokers
from .accounts.bloomberg import Bloomberg
from .data import Data
from .enums import Parameters

class Bacaci:

    def __init__(self, api, symbol, arg):

        self.API = api
        self.SYMBOL = symbol
        self.ARG = arg

        if self.API == Parameters.BINANCE.value:
            self.binance = Binance()
            print("Connected to Binance Account...\n")
            time.sleep(1)

        elif self.API == Parameters.ALPACA.value:
        #    self.alpaca = Alpaca()
        #    print("Connected to Alpaca Account...")
            time.sleep(1)

        elif self.API == Parameters.IB.value:
            self.interactive_brokers = InteractiveBrokers()
            print("Connected to IB Account...")
            time.sleep(1)

        elif self.API == Parameters.BLOOMBERG.value:
            self.bloomberg = Bloomberg()
            print("Connected to Bloomberg Account...")
            time.sleep(1)

        else:
            print("No corresponding API detected.")
            print("Quitting the program.")
            exit(0)

        self.data = Data(self.API, self.SYMBOL, self.ARG)
        # ...