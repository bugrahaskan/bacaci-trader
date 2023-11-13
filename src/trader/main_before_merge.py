import multiprocessing
#from multiprocessing import Manager
import argparse
import configparser
#import os
import time

from bacaci.threads import DataThread, TradeThread
from bacaci.memory import Memory
from bacaci.backtest import Backtest
from bacaci.data import Data
from bacaci.enums import Parameters

def data_retrieving_process(api, symbol, arg):

    thread1 = DataThread(api=api, symbol=symbol, arg=arg)
    thread1.start()
    thread1.join()

def memory_process(api, symbol):

    memory = Memory(api=api, symbol=symbol)

def backtest_process(api, symbol):

    backtest = Backtest(api=api, symbol=symbol)

def simulation_process(api, symbol):

    simulation = TradeThread(api=api, symbol=symbol, test_mode=True)
    simulation.start()
    simulation.join()

def trading_process(api, symbol):

    simulation = TradeThread(api=api, symbol=symbol, test_mode=False)
    simulation.start()
    simulation.join()

def main():

    config = configparser.ConfigParser()
    config.read('config.ini')

    parser = argparse.ArgumentParser(description='Trade Bot for a given Security')
    # ...
    parser.add_argument('-D', '--database', action='store_true', help='Construct Initial Database with all Historical Data')
    parser.add_argument('-g', '--fill_gaps', action='store_true', help='Fill all gaps from last retrieval')
    parser.add_argument('-d', '--data', action='store_true', help='Retrieve Data')
    parser.add_argument('-m', '--memory', action='store_true', help='Memory Process')
    parser.add_argument('-b', '--backtest', action='store_true', help='Backtest of the Strategy for the given Symbol')
    parser.add_argument('-s', '--simulation', action='store_true', help='Simulation in Paper Trade Mode')
    parser.add_argument('-t', '--trade', action='store_true', help='Actual Trading Process')
    parser.add_argument('api', help='API to work in')
    parser.add_argument('symbol', help='Symbol of the Security')

    args = parser.parse_args()

    api_list = [value for key, value in config['API'].items()]
    sym_list = [value for key, value in config['Symbol'].items()]

    if args.api in api_list:
        api = args.api
        print(f"Setting current working API to {api}")
        time.sleep(1)
        # "Press enter to continue..."
    else:
        print("API not recgnized.")

    if args.symbol in sym_list:
        symbol = args.symbol
        print(f"Setting current currency to {symbol}")
        time.sleep(1)
        # "Press enter to continue..."
    else:
        print("Symbol not recognized.")

    if args.database:
        process = multiprocessing.Process(target=data_retrieving_process, args=(api, symbol, "database",))
        process.start()
        process.join()

    elif args.fill_gaps:
        process = multiprocessing.Process(target=data_retrieving_process, args=(api, symbol, "fill_gaps",))
        process.start()
        process.join()
    
    elif args.data:
        process = multiprocessing.Process(target=data_retrieving_process, args=(api, symbol, "data",))
        process.start()
        process.join()
    
    elif args.memory:
        process = multiprocessing.Process(target=memory_process, args=(api, symbol,))
        process.start()
        process.join()

    elif args.data:
        data = Data(api, symbol)
        process = multiprocessing.Process(target=data.initialize_web_sockets)
        process.start()
        process.join()
    
    elif args.backtest:
        process = multiprocessing.Process(target=backtest_process, args=(api, symbol,))
        process.start()
        process.join()

    elif args.simulation:
        process = multiprocessing.Process(target=simulation_process, args=(api, symbol,))
        process.start()
        process.join()
    
    elif args.trade:
        process = multiprocessing.Process(target=trading_process, args=(api, symbol,))
        process.start()
        process.join()
    
    else:
        # kill existing processes before exit
        exit(0)

if __name__ == '__main__':
    main()