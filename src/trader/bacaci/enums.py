import configparser
from enum import Enum
#from datetime import datetime
#import datetime as dt
from binance import Client

class Parameters(Enum):

    config = configparser.ConfigParser()
    config.read('config.ini')

    # DATABASE Name
    DATABASE = config['Database']['name']

    # API Names
    BINANCE = config['API']['binance']
    ALPACA = config['API']['alpaca']
    IB = config['API']['interactiveBrokers']
    BLOOMBERG = config['API']['bloomberg']
    
    # API Keys
    BINANCE_API_KEY = config['Binance']['api_key']
    BINANCE_SECRET_KEY = config['Binance']['secret_key']

    ALPACA_API_KEY = config['Alpaca']['api_key']
    ALPACA_SECRET_KEY = config['Alpaca']['secret_key']

    # Binance Intervals

    BINANCE_INTERVAL_1s = "1s"
    BINANCE_INTERVAL_10s = "10s"
    BINANCE_INTERVAL_1m = Client.KLINE_INTERVAL_1MINUTE
    BINANCE_INTERVAL_5m = Client.KLINE_INTERVAL_5MINUTE
    BINANCE_INTERVAL_15m = Client.KLINE_INTERVAL_15MINUTE
    BINANCE_INTERVAL_1h = Client.KLINE_INTERVAL_1HOUR
    # ...

    # Symbols
    SYMBOLS = []

    # ONE_DAY = 24*60*60
    # TODAY = int(datetime.today().timestamp())
    # END = int(datetime.strptime("10-01-2023 08:00:00", '%d-%m-%Y %H:%M:%S').timestamp())
    # START = int((END - dt.timedelta(days=7)).timestamp())

    # YahooFinance Intervals
    # INTERVALS = ["1m","2m","5m","15m","30m","60m"]
    # INTERVALS_1m = "1m"
    # INTERVALS_2m = "2m"
    # INTERVALS_5m = "5m"
    # INTERVALS_15m = "15m"
    # INTERVALS_30m = "30m"
    # INTERVALS_60m = "60m"
    # INTERVALS_1d = "1d"
    # INTERVALS_1wk = "1wk"
    # INTERVALS_1mo = "1mo"

    # YahooFinance Periods
    # PERIODS = ["1d","5d","1mo","3mo","6mo","1y","2y","5y","10y","ytd","max"]
    # PERIODS_1d = "1d"
    # PERIODS_5d = "5d"
    # PERIODS_1mo = "1mo"
    # PERIODS_3mo = "3mo"
    # PERIODS_6mo = "6mo"
    # PERIODS_1y = "1y"
    # PERIODS_2y = "2y"
    # PERIODS_5y = "5y"
    # PERIODS_10y = "10y"
    # PERIODS_ytd = "ytd"
    # PERIODS_max = "max"

    # YahooFinance Symbols
    # SYMBOLS = ["AMZN", "AKBNK.IS", "TSLA", "GARAN.IS", "BTC-USD", "ETH-USD"]
    # SYMBOLS_AMAZON = "AMZN"
    # SYMBOLS_TESLA = "TSLA"
    # SYMBOLS_AKBANK = "AKBNK.IS"
    # SYMBOLS_GARANTI = "GARAN.IS"
    # SYMBOLS_BTC = "BTC-USD"
    # SYMBOLS_ETH = "ETH-USD"

    COLUMNS = ['date', 'open', 'high', 'low', 'close', 'volume']

    TYPE_LONG = "BUY"
    TYPE_SHORT = "SELL"
    QUANTITY = config['Parameters']['quantity']
    COMMISSION = config['Parameters']['commission']
    INDEX_POINT = config['Parameters']['index_point'] # for NASDAQ
    CAPITAL = config['Parameters']['capital']
    #TRESHOLD = 5.0
    EPSILON = config['Parameters']['epsilon']
    