from binance import Client
from binance.enums import HistoricalKlinesType
from binance import AsyncClient, BinanceSocketManager
import pandas as pd
from datetime import datetime
import schedule
import configparser
import asyncio
import websockets
import json

from .accounts.binance import Binance
from .database import Database
from .enums import Parameters

class Data:

    def __init__(self, api, symbol, arg):

        self.API = api
        self.SYMBOL = symbol
        self.ARG = arg

        self.lock = asyncio.Lock()

        if self.API == Parameters.BINANCE.value:
            self.client = Binance.binance_connect()

            if self.ARG == "database":

                ''' Collect All Historical Data for Initializing '''
                print("Collecting all historical data")
                self.klines_database(
                    symbol=self.SYMBOL,
                    intervals=[Parameters.BINANCE_INTERVAL_1m.value,
                               Parameters.BINANCE_INTERVAL_5m.value,
                               Parameters.BINANCE_INTERVAL_15m.value])
                print("done")

            elif self.ARG == "fill_gaps":

                ''' Fill the gaps '''
                print("Filling gaps from the last data retrieval")
                self.params = [
                    Data.set_params(self.SYMBOL, Parameters.BINANCE_INTERVAL_1s.value),
                    Data.set_params(self.SYMBOL, Parameters.BINANCE_INTERVAL_1m.value),
                    Data.set_params(self.SYMBOL, Parameters.BINANCE_INTERVAL_5m.value),
                    Data.set_params(self.SYMBOL, Parameters.BINANCE_INTERVAL_15m.value)
                ]
                
                for param in self.params:
                    self.fill_gaps(Parameters.DATABASE.value, param)
                print("done")

            elif self.ARG == "data":

                ''' REST API method: '''
                #self.params = [
                #    Data.set_params(self.SYMBOL, Parameters.BINANCE_INTERVAL_1m.value),
                #    Data.set_params(self.SYMBOL, Parameters.BINANCE_INTERVAL_5m.value)
                #]
                #schedule.every(1).minutes.do(self.my_function, params=self.params[0])
                #schedule.every(5).minutes.do(self.my_function, params=self.params[1])
                #Data.collect_data()

                '''WebSocket method: '''
                print("Initializing Web Sockets")
                loop = asyncio.new_event_loop()
                loop.run_until_complete(self.main())
        
        #elif self.API == Parameters.ALPACA.value:
        #    to do...
        #    pass

        elif self.API == Parameters.IB.value:
            # to do...
            pass

        elif self.API == Parameters.BLOOMBERG.value:
            # to do...
            pass

        else:
            exit(0)

    @staticmethod
    def set_params(symbol, interval, start_str="2 day ago UTC", end_str=None, limit=1000, klines_type=HistoricalKlinesType.FUTURES):
        return {
            "symbol": symbol,
            "interval": interval,
            "start_str": start_str,
            "end_str": end_str,
            "limit": limit,
            "klines_type": klines_type
        }
    
    def get_klines(self, params):
        data = self.client.futures_historical_klines(
            symbol=params["symbol"],
            interval=params["interval"],
            start_str=params["start_str"],
            end_str=params["end_str"],
            limit=params["limit"]
        )
        return data
    
    def klines_database(self, symbol, intervals):
        #for symbol in symbols:
        for interval in intervals:
            params = Data.set_params(symbol, interval, start_str=0, end_str=None)
            tableName = Data.table_name(symbol, interval, self.API)

            data = self.get_klines(params)
            print(
                f"fetched {symbol} {interval} data from {self.API}. length: {len(data)}")

            df = Data.generate_df(data)
            print(f"created {symbol} {interval} dataframe. length: {len(df)}")

            database = Database(Parameters.DATABASE.value)
            database.insert_data(df, tableName)
            print(f"inserted {symbol} {interval} data to the database.")
    
    @staticmethod
    def find_timestamps(df, interval):
        df['time_diff'] = df["timestamp"].diff()
        first_timestamp = None
        second_timestamp = None
        for index, row in df.iterrows():
            if index != 0:
                time_diff = row['time_diff'] if 'time_diff' in df.columns else None

                if time_diff != interval and first_timestamp is None:
                    first_timestamp = df.loc[index - 1, 'timestamp']

                if time_diff == interval and first_timestamp is not None and second_timestamp is None:
                    second_timestamp = row['timestamp']
                    break
        if first_timestamp == None and second_timestamp == None:
            return 0, 0
        return str(first_timestamp), str(second_timestamp)
    
    def fill_gaps(self, database_name, params):
        tableName = Data.table_name(params["symbol"], params["interval"], self.API)
        inter = Data.interval_to_seconds(params["interval"])
        state = True
        while state:
            database = Database(database_name)
            start_time = database.fetch_rows(
                tableName, first=None, column='timestamp')
            start_time = int(start_time[0][0])
            rows = database.fetch_rows(tableName, start_time=start_time)
            df = Data.generate_df(rows, date=True)

            start_str, end_str = Data.find_timestamps(df, inter)
            if start_str == 0 and end_str == 0:
                # print("no gaps in the database")
                state = False
            else:
                new_params = Data.set_params(
                    params["symbol"], params["interval"], start_str, end_str)

                data = self.get_klines(new_params)
                df = Data.generate_df(data)

                database = Database(database_name)
                database.insert_data(df, tableName)
    
    @staticmethod
    def generate_df(data, date=False):
        # from datetime import datetime
        # import pandas as pd
        if not date:
            df = pd.DataFrame(data)
            df = df[[0, 1, 2, 3, 4, 5]]
            df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']

            if len(str(df["timestamp"][0])) > 10:
                df.insert(1, "date", [datetime.fromtimestamp(
                    int(ts)/1000).strftime('%Y-%m-%d %H:%M:%S') for ts in df["timestamp"]])
                df["timestamp"] = [int(ts)/1000 for ts in df["timestamp"]]
            else:
                df.insert(1, "date", [datetime.fromtimestamp(
                    int(ts)).strftime('%Y-%m-%d %H:%M:%S') for ts in df["timestamp"]])
        elif date:
            df = pd.DataFrame(data)
            df = df[[0, 1, 2, 3, 4, 5, 6]]
            df.columns = ['timestamp', 'date', 'open',
                        'high', 'low', 'close', 'volume']
            if len(str(df["timestamp"][0])) > 10:
                df["timestamp"] = [int(ts)/1000 for ts in df["timestamp"]]
        return df

    #@staticmethod
    #def generate_df_backup(data):
    #    # from datetime import datetime
    #    # import pandas as pd
    #    df = pd.DataFrame(data)
    #    df = df[[0, 1, 2, 3, 4, 5]]
    #    df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    #    df.insert(0, "date", [datetime.fromtimestamp(int(ts)/1000).strftime('%Y-%m-%d %H:%M:%S') for ts in df["timestamp"]])
    #    df["timestamp"] = [int(ts)/1000 for ts in df["timestamp"]]
    #    
    #    return df
    
    def my_function(self, params):
        table_name = Data.table_name(self.API, params["symbol"], params["interval"])
        candles = self.client.get_historical_klines(
            symbol=params["symbol"],
            interval=params["interval"],
            start_str=params["start_str"],
            end_str=params["end_str"],
            limit=params["limit"],
            klines_type=params["klines_type"]
        )
        df = Data.generate_df(candles)
        database = Database(
            db_name=Parameters.DATABASE.value
            )
        database.insert_data(df, table_name)
        print(f"{params['interval']} function has worked")
    
    @staticmethod
    def generate_df_ws(res, tick=False):
        if tick:
            df = pd.DataFrame()
            df["timestamp"] = [int(int(res["E"]) / 1000)]
            df["date"] = str(Data.to_datetime(int(df["timestamp"][0])))
            df["price"] = float(res["p"])

            return df
        else:
            df = pd.DataFrame()
            k = res["k"]
            df["timestamp"] = [int(k["t"]) / 1000]
            df["date"] = str(Data.to_datetime(int(df["timestamp"][0])))
            df["open"] = k["o"]
            df["high"] = k["h"]
            df["low"] = k["l"]
            df["close"] = k["c"]
            df["volume"] = k["v"]

            return df

    '''async def data(self, symbol, interval):
        client = await AsyncClient.create()
        #client = Client(
        #    api_key=Parameters.BINANCE_API_KEY.value,
        #    api_secret=Parameters.BINANCE_SECRET_KEY.value,
        #    tld='futures'
        #    )
        bm = BinanceSocketManager(client)
        
        # start any sockets here, i.e a trade socket
        ts = bm.kline_socket(symbol, interval)

        tableName = Data.table_name(symbol, interval, self.API)
        database = Database(
            db_name=Parameters.DATABASE.value
            )

        # then start receiving messages
        async with ts as tscm:
            while True:
                res = await tscm.recv()
                if res["k"]["x"] == True:
                    df = Data.generate_df_ws(res)
                    database.insert_data(df, tableName)
                    print(res["k"])
                    await asyncio.sleep(0.1)

        await client.close_connection()'''

    async def tick_data(self, symbol, interval="1s"):
        uri = f"wss://fstream.binance.com/ws/{symbol.lower()}@markPrice@1s"  # 1s data

        tableName = Data.table_name(symbol, interval, self.API)
        database = Database(
            db_name=Parameters.DATABASE.value
            )

        async with websockets.connect(uri) as websocket:
            while True:
                resp = await websocket.recv()  # Receiving a message
                if resp:
                    resp = json.loads(resp)
                    df = Data.generate_df_ws(resp, tick=True)
                    database.insert_data(df, tableName, tick=True)
                    print(resp["p"])
                    #await asyncio.sleep(0.1)
        
        await client.close_connection()

    async def kline_data(self, symbol, interval):
        uri = f"wss://fstream.binance.com/ws/{symbol.lower()}_perpetual@continuousKline_{interval}" # interval data

        tableName = Data.table_name(symbol, interval, self.API)
        database = Database(
            db_name=Parameters.DATABASE.value
            )
        
        async with websockets.connect(uri) as websocket:
            while True:
                resp = await websocket.recv()  # Receiving a message
                resp = json.loads(resp)
                if resp["k"]["x"]:
                    df = Data.generate_df_ws(resp)
                    database.insert_data(df, tableName)
                    print(resp["k"])
                    #await asyncio.sleep(0.1)
        
        await client.close_connection()
    
    async def main(self):
        config = configparser.ConfigParser()
        config.read('config.ini')
        int_list = [value for key, value in config['Intervals'].items()]
        #intervals = ['1s', '1m', '5m']

        tasks = []
        for interval in int_list:
            if interval == "1s":
                tasks.append(asyncio.create_task(self.tick_data(self.SYMBOL, interval)))
            else:
                tasks.append(asyncio.create_task(self.kline_data(self.SYMBOL, interval)))

        #tasks = [asyncio.create_task(self.data(self.SYMBOL, interval)) for interval in int_list]
        
        async with self.lock:
            await asyncio.gather(*tasks)
    
    # correct it if necessary
    @staticmethod
    def table_name(symbol, interval, api):
        return f"{api}_{symbol}_{interval}"
    
    @staticmethod
    def interval_to_seconds(interval):
        if interval == '1s':
            return 1
        elif interval == '10s':
            return 10
        elif interval == '1m':
            return 60
        elif interval == '5m':
            return 300
    
    @staticmethod
    def to_datetime(ts):
        """Converts a timestamp object to datetime."""
        from datetime import datetime
        
        if isinstance(ts, str):
            ts = int(ts)
        
        return datetime.fromtimestamp(ts)
    
    @staticmethod
    def to_timestamp(dt, date_format='%Y-%m-%d %H:%M:%S'):
        """Converts a datetime object to an integer timestamp."""
        from datetime import datetime
        
        dt = datetime.strptime(dt, date_format)
        
        return int(dt.timestamp())
    
    @staticmethod
    def show_data(df):
        print(f"Columns: {df.columns}")
        print(f"Head: {df.head()}")
        print(f"Tail: {df.tail()}")

    @staticmethod
    def collect_data():

        while True:
            schedule.run_pending()