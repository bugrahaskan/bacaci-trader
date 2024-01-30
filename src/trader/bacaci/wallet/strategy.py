import asyncio
import json
import time
import pandas as pd
import os
from binance.client import Client

from .wallet import Wallet, StopLoss, MyTrailingStop, TakeProfit
from ..memory import Memory
from ..enums import Parameters
from ..data import Data
from ..notification import Notification

class Strategy:

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
        
        self.memory = Memory(
            api=self.API,
            symbol=self.SYMBOL
            )
        
        print("Strategy created")
        time.sleep(1)

        self.lock = asyncio.Lock()

        global event
        event = asyncio.Event()

        #try:
        #    self.mail = Notification()
        #    print("Succesfully connected to SMTP")
        #except:
        #    print("SMTP problem occurred, continue...")

        # process according to strategy
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        if self.TEST_MODE:
            loop.run_until_complete(
                asyncio.gather(
                    self.memory.mem_for_backtest(),
                    self.strategy_2_PROD()
                )
            )

            pass
        else:
            #loop.run_until_complete(self.dummy_strategy(cond=True))
            loop.run_until_complete(
                asyncio.gather(
                    self.memory.mem(),
                    self.strategy_2_PROD()
                )
            )


    def write_to_excel(self):
        '''
        dfs: a list of different dataframes
        '''

        self.OUTPUT_FILE = f"/output/data_{self.API}_{self.SYMBOL}.xlsx"
        self.WRITER = pd.ExcelWriter(os.getcwd()+self.OUTPUT_FILE)

        df_orders = pd.DataFrame.from_dict(self.wallet.orders, orient='index')
        df_orders.to_excel(self.WRITER, sheet_name='orders', index=False)

        self.WRITER.close()

    def read_memory(self):

        with open(f"memory_{self.SYMBOL}.json", "r") as memory:
            data = json.load(memory)
        
        return data

    async def check_conditions(self, cond, t=1):
        
        await asyncio.sleep(t)

        if cond:
            return True
        else:
            return False

    async def check_event(self, event: asyncio.Event, t=1):

        while True:

            await asyncio.sleep(t)

            data = self.read_memory()

            if data["current_state"]["rsi-5m"] < 68:
                event.set()
                break

    async def check_event_is_order_filled(self, event: asyncio.Event, t=1):

        while True:

            await asyncio.sleep(t)

            if self.TEST_MODE:
                event.set()
                break

            else:
                if self.wallet.binance.client.futures_get_order(
                                                symbol=self.wallet.orders[self.wallet.INDEX]['Symbol'],
                                                orderId=self.wallet.orders[self.wallet.INDEX]['IdOpen']
                                                )['status'] == 'FILLED':
                    event.set()
                    break

    async def check_event_reset_conditions(self, event: asyncio.Event, interval="5m",  t=1):

        while True:

            data = self.read_memory()

            await asyncio.sleep(t)

            if self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_LONG.value:
                if not data["current_state"][f"rsi-{interval}"] < (50 + 3.): # < (30 + 3.)
                    event.set()
                    break

            elif self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_SHORT.value:
                if not data["current_state"][f"rsi-{interval}"] > (50 - 3.): # > (70 - 3.)
                    event.set()
                    break
    
    async def check_event_rsi_change(self, event: asyncio.Event, direction, interval="15m", t=1):

        while True:

            data = self.read_memory()
            last_key = list(data["historical_prices"][interval].keys())[-1]

            await asyncio.sleep(t)

            if direction == "down":
                if data["current_state"][f"rsi-{interval}"] - data["historical_prices"][interval][last_key]["rsi"] < 0.:
                    event.set()
                    break
            
            elif direction == "up":
                if data["current_state"][f"rsi-{interval}"] - data["historical_prices"][interval][last_key]["rsi"] > 0.:
                    event.set()
                    break

    async def generate_event(self, event: asyncio.Event):

        i = 0

        while True:

            await asyncio.sleep(1)

            i += 1
            print(f"i is now {i}.")

            if i == 15:
                event.set()
                print("event set True.")
                break

    async def print_statement(self):

        while True:

            await asyncio.sleep(1)

            data = self.read_memory()

            print("actual RSI", data["current_state"]["rsi-5m"])

    async def test(self):

        while True:

            data = self.read_memory()

            last_key_1m = list(data["historical_prices"]["1m"].keys())[-1]
            last_keys_1m = [
                list(data["historical_prices"]["1m"].keys())[-i] for i in range(1,10)
            ]
            last_key_5m = list(data["historical_prices"]["5m"].keys())[-1]

            a = 5
            b = 4

            resp1 = await self.check_conditions(
                cond=all(
                    [
                        a<0 or a>2,
                        b == 4
                    ]
                )
            )

            if resp1:

                print("it is OK.")

    async def dummy_strategy(self, cond=False):

        while True:

            data = self.read_memory()

            last_key = list(data["historical_prices"]["1m"].keys())[-1]
            last_keys_1m = [
                list(data["historical_prices"]["1m"].keys())[-i] for i in range(1,10)
            ]
            last_key_1s = list(data["historical_prices"]["1s"].keys())[-1]

            global event

            print("actual price:", data["historical_prices"]["1s"][last_key_1s]["p"])

            if not self.wallet.is_open():
                #time.sleep(5)
                print("Waiting to open position", Data.to_datetime(data["current_date"]))

                self.wallet.open_position(
                    side="BUY",
                    quantity=self.qty,
                    price=data["historical_prices"]["1s"][last_key_1s]["p"],
                    date=Data.to_datetime(data["historical_prices"]["1s"][last_key_1s]["t"]).strftime("%Y-%m-%d %H:%M:%S"),
                    #type=Client.FUTURE_ORDER_TYPE_LIMIT
                )
                
                #stop_loss = StopLoss(max(data["historical_prices"]["1m"][last_key]["o"], data["historical_prices"]["1m"][last_key]["c"]) - 5.)
                '''for key in last_keys_1m:
                    if data["historical_prices"]["1m"][key]["isMinLocal"]:
                        trailing_stop = MyTrailingStop(
                            min(data["historical_prices"]["1m"][key]["o"], data["historical_prices"]["1m"][key]["c"])
                        )
                        print(f'current stop is {min(data["historical_prices"]["1m"][key]["o"], data["historical_prices"]["1m"][key]["c"])}')
                        break'''
                trailing_stop = MyTrailingStop(data["historical_prices"]["1s"][last_key_1s]["p"] - 5.)
                print(f'current stop is {trailing_stop.actual_stop()}')

                print(self.wallet.orders)

                await asyncio.gather(
                    event.wait(),
                    self.check_event_is_order_filled(
                        event=event,
                        t=1
                    )
                )
                event.clear()
                

                pass

            elif self.wallet.is_open():

                # Calculate PNL %
                if self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_LONG.value:
                    profit_percent = 100 * (data["historical_prices"]["1s"][last_key_1s]["p"] - self.wallet.orders[self.wallet.INDEX]["Open"]) * float(Parameters.INDEX_POINT.value) / self.wallet.orders[self.wallet.INDEX]["Open"]
                elif self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_SHORT.value:
                    profit_percent = 100 * (self.wallet.orders[self.wallet.INDEX]["Open"] - data["historical_prices"]["1s"][last_key_1s]["p"]) * float(Parameters.INDEX_POINT.value) / self.wallet.orders[self.wallet.INDEX]["Open"]

                print("profit percent:", profit_percent)

                if self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_LONG.value:

                    #trailing_stop.update_stop(data["historical_prices"]["1m"][last_key]["c"], Parameters.TYPE_LONG.value)
                    for key in last_keys_1m:
                        if int(key) > Data.to_timestamp(self.wallet.orders[self.wallet.INDEX]["DateOpen"]):
                            if data["historical_prices"]["1m"][key]["isMinLocal"]:
                                curr_stop = trailing_stop.set_stop(
                                    min(data["historical_prices"]["1m"][key]["o"], data["historical_prices"]["1m"][key]["c"]),
                                    Parameters.TYPE_LONG.value
                                )
                                print(f'updated stop is {curr_stop}')
                                
                                break
                    print(f'current stop is {trailing_stop.actual_stop()} at {Data.to_datetime(data["current_date"])}')
                    print("current price:", data["historical_prices"]["1s"][last_key_1s]["p"])
                    print("current bar:", Data.to_datetime(data["historical_prices"]["1m"][last_key]["t"]).strftime("%Y-%m-%d %H:%M:%S"))

                    '''stop_loss = await self.check_conditions(
                        cond=all(
                            [
                                self.wallet.stop_loss_2(data["historical_prices"]["1m"][last_key]["c"], 0.04) #previous_key?
                            ]
                        )
                    )'''

                    resp1 = await self.check_conditions(
                        cond=all(
                            [
                                profit_percent<0 or profit_percent>2,
                                trailing_stop.check_trigger(data["historical_prices"]["1s"][last_key_1s]["p"], Parameters.TYPE_LONG.value)
                            ]
                        )
                    )

                    '''resp1, resp2 = await asyncio.gather(
                        self.check_conditions(
                            cond=all(
                                [
                                    #data["historical_prices"]["1m"][last_key]["c"] > self.wallet.orders[self.wallet.INDEX]['Open'] + 2.,
                                    trailing_stop.check_trigger(data["historical_prices"]["1m"][last_key]["c"], Parameters.TYPE_LONG.value)
                                ]
                            )
                        ),
                        self.check_conditions(
                            cond=all(
                                [
                                    stop_loss.check_trigger(data["historical_prices"]["1m"][last_key]["c"], Parameters.TYPE_LONG.value),
                                    #data["historical_prices"]["1m"][last_key]["c"] < self.wallet.orders[self.wallet.INDEX]['Open'] - 2.,
                                    #data["historical_prices"]["5m"][last_key_5m]["c"] <= min( data["historical_prices"]["5m"][key]["l"] for key in last_keys_5m )
                                ]
                            )
                        )
                    )'''

                    '''if resp2:
                        print("Stop Loss")

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=data["historical_prices"]["1m"][last_key]["c"],
                            date=Data.to_datetime(data["historical_prices"]["1m"][last_key]["t"]).strftime("%Y-%m-%d %H:%M:%S"),
                            #type=Client.FUTURE_ORDER_TYPE_LIMIT
                        )

                        await asyncio.gather(
                            event.wait(),
                            self.check_event_is_order_filled(
                                event=event,
                                t=1
                            )
                        )
                        event.clear()
                        
                        print(self.wallet.orders)'''
                        
                    if resp1:
                        print("Trailing Stop")

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=data["historical_prices"]["1s"][last_key_1s]["p"],
                            date=Data.to_datetime(data["historical_prices"]["1s"][last_key_1s]["t"]).strftime("%Y-%m-%d %H:%M:%S"),
                            #type=Client.FUTURE_ORDER_TYPE_LIMIT
                        )

                        await asyncio.gather(
                            event.wait(),
                            self.check_event_is_order_filled(
                                event=event,
                                t=1
                            )
                        )
                        event.clear()
                        
                        print(self.wallet.orders)

                elif self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_SHORT.value:
                    
                    #time.sleep(10)

                    stop_loss = await self.check_conditions(
                        cond=all(
                            [
                                self.wallet.stop_loss_2(data["historical_prices"]["1m"][last_key]["c"], 0.04) #previous_key?
                            ]
                        )
                    )

                    if stop_loss:
                        print("Stop Loss")

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=data["historical_prices"]["1m"][last_key]["c"],
                            date=data["historical_prices"]["1m"][last_key]["t"]
                        )
                        print(self.wallet.orders)
                        
                        pass

    '''LIVE STRATEGIES'''
    async def strategy_2_PROD(self, order_type="market"):

        while True:

            data = self.read_memory()

            last_key_1s = list(data["historical_prices"]["1s"].keys())[-1]

            last_key_1m = list(data["historical_prices"]["1m"].keys())[-1]
            last_keys_1m = [
                list(data["historical_prices"]["1m"].keys())[-i] for i in range(1,10)
            ]

            last_key_5m = list(data["historical_prices"]["5m"].keys())[-1]
            last_keys_5m = [
                list(data["historical_prices"]["5m"].keys())[-i] for i in range(1,10)
            ]

            global event

            #with open("rsi_output.csv", "a") as r:
            #    d = "{},{:.{}f}\n".format(Data.to_datetime(data["current_date"]), data["historical_prices"]["5m"][last_key_5m]["rsi"], 2)
            #    r.write(d)

            print("current price:", data["historical_prices"]["1s"][last_key_1s]["p"])

            if not self.wallet.is_open():
                #print("Waiting to open position")
                print("Waiting to open position", Data.to_datetime(data["current_date"]))
                #print("1m RSI:", data["historical_prices"]["1m"][last_key_1m]["rsi"])
                print("realtime 1m RSI:", data["current_state"]["rsi-1m"])
                #print("5m RSI:", data["historical_prices"]["5m"][last_key_5m]["rsi"])
                print("realtime 5m RSI:", data["current_state"]["rsi-5m"])
                #print("normalized volume 1m:", data["historical_prices"]["1m"][last_key_1m]["normalized_volume"])
                print("normalized volume 5m:", data["historical_prices"]["5m"][last_key_5m]["normalized_volume"])

                resp1, resp2 = await asyncio.gather(
                    self.check_conditions(
                        cond=all(
                            [
                                #not abs(data["historical_prices"]["1m"][last_key_1m]["rsi"] - 70.) < 4.,
                                not data["current_state"]["rsi-1m"] > (70 - 0.),
                                #data["historical_prices"]["1m"][last_key_1m]["normalized_volume"] <= 0.5,
                                #abs(data["historical_prices"]["5m"][last_key_5m]["rsi"] - 70.) < 3.,
                                data["current_state"]["rsi-5m"] > (70 - 4.),
                                data["historical_prices"]["5m"][last_key_5m]["normalized_volume"] <= 0.5
                            ]
                        )
                    ),
                    self.check_conditions(
                        cond=all(
                            [
                                #not abs(data["historical_prices"]["1m"][last_key_1m]["rsi"] - 30.) < 4.,
                                not data["current_state"]["rsi-1m"] < (30 + 0.),
                                #data["historical_prices"]["1m"][last_key_1m]["normalized_volume"] <= 0.5,
                                #abs(data["historical_prices"]["5m"][last_key_5m]["rsi"] - 30.) < 3.,
                                data["current_state"]["rsi-5m"] < (30 + 4.),
                                data["historical_prices"]["5m"][last_key_5m]["normalized_volume"] <= 0.5
                            ]
                        )
                    )
                )

                if resp1:
                    print("condition 1 satisfied")
                    print("1m RSI:", data["current_state"]["rsi-1m"])
                    print("5m RSI:", data["current_state"]["rsi-5m"])
                    print("1m Volume:", data["historical_prices"]["1m"][last_key_1m]["normalized_volume"])

                    if order_type == "market":

                        # open position...
                        self.wallet.open_position(
                            side="SELL",
                            quantity=self.qty,
                            price=data["historical_prices"]["1m"][last_key_1m]["c"],
                            date=Data.to_datetime(data["historical_prices"]["1m"][last_key_1m]["t"]).strftime("%Y-%m-%d %H:%M:%S")
                            #type=Client.FUTURE_ORDER_TYPE_LIMIT
                        )
                    
                    elif order_type == "limit":

                        # open position...
                        self.wallet.open_position(
                            side="SELL",
                            quantity=self.qty,
                            price=data["historical_prices"]["1m"][last_key_1m]["c"],
                            date=Data.to_datetime(data["historical_prices"]["1m"][last_key_1m]["t"]).strftime("%Y-%m-%d %H:%M:%S"),
                            type=Client.FUTURE_ORDER_TYPE_LIMIT
                        )

                    '''await self.check_conditions(
                        cond=all(
                            [
                                self.wallet.binance.client.futures_get_order(
                                    symbol=self.wallet.orders[self.wallet.INDEX]['Symbol'],
                                    orderId=self.wallet.orders[self.wallet.INDEX]['IdOpen']
                                    ) == 'FILLED'
                            ]
                        ),
                        t=1
                    )'''

                    print(self.wallet.orders)
                
                    await asyncio.gather(
                        event.wait(),
                        self.check_event_is_order_filled(
                            event=event,
                            t=1
                        )
                    )
                    event.clear()

                    #stop_loss = StopLoss(max(data["historical_prices"]["1m"][last_key_1m]["o"], data["historical_prices"]["1m"][last_key_1m]["c"]) + 5.)
                    #take_profit = TakeProfit(data["historical_prices"]["1m"][last_key_1m]["c"] - 9.)

                    trailing_stop = MyTrailingStop(data["historical_prices"]["1s"][last_key_1s]["p"] + 5.)
                    print(f'current stop is {trailing_stop.actual_stop()}')

                    #print(self.wallet.orders)

                    Notification("bhaskan@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))
                    #Notification("oozlen@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))

                    self.write_to_excel()

                if resp2:
                    print("condition 2 satisfied")
                    print("1m RSI:", data["current_state"]["rsi-1m"])
                    print("5m RSI:", data["current_state"]["rsi-5m"])
                    print("1m Volume:", data["historical_prices"]["1m"][last_key_1m]["normalized_volume"])

                    if order_type == "market":

                        # open position...
                        self.wallet.open_position(
                            side="BUY",
                            quantity=self.qty,
                            price=data["historical_prices"]["1m"][last_key_1m]["c"],
                            date=Data.to_datetime(data["historical_prices"]["1m"][last_key_1m]["t"]).strftime("%Y-%m-%d %H:%M:%S")
                            #type=Client.FUTURE_ORDER_TYPE_LIMIT
                        )

                    elif order_type == "limit":

                        # open position...
                        self.wallet.open_position(
                            side="BUY",
                            quantity=self.qty,
                            price=data["historical_prices"]["1m"][last_key_1m]["c"],
                            date=Data.to_datetime(data["historical_prices"]["1m"][last_key_1m]["t"]).strftime("%Y-%m-%d %H:%M:%S"),
                            type=Client.FUTURE_ORDER_TYPE_LIMIT
                        )
                    
                    print(self.wallet.orders)
                    
                    await asyncio.gather(
                        event.wait(),
                        self.check_event_is_order_filled(
                            event=event,
                            t=1
                        )
                    )
                    event.clear()

                    #stop_loss = StopLoss(min(data["historical_prices"]["1m"][last_key_1m]["o"], data["historical_prices"]["1m"][last_key_1m]["c"]) - 5.)
                    #take_profit = TakeProfit(data["historical_prices"]["1m"][last_key_1m]["c"] + 9.)

                    trailing_stop = MyTrailingStop(data["historical_prices"]["1s"][last_key_1s]["p"] - 5.)
                    print(f'current stop is {trailing_stop.actual_stop()}')

                    #print(self.wallet.orders)

                    Notification("bhaskan@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))
                    #Notification("oozlen@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))

                    self.write_to_excel()

            elif self.wallet.is_open():
                print("Waiting to close position", Data.to_datetime(data["current_date"]))
                print("back RSI:", data["historical_prices"]["1s"][last_key_1s]["rsi"])
                print("1m RSI:", data["historical_prices"]["1m"][last_key_1m]["rsi"])
                print("5m RSI:", data["historical_prices"]["5m"][last_key_5m]["rsi"])

                # Calculate PNL %
                if self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_LONG.value:
                    profit_percent = 100 * (data["historical_prices"]["1s"][last_key_1s]["p"] - self.wallet.orders[self.wallet.INDEX]["Open"]) * float(Parameters.INDEX_POINT.value) / self.wallet.orders[self.wallet.INDEX]["Open"]
                elif self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_SHORT.value:
                    profit_percent = 100 * (self.wallet.orders[self.wallet.INDEX]["Open"] - data["historical_prices"]["1s"][last_key_1s]["p"]) * float(Parameters.INDEX_POINT.value) / self.wallet.orders[self.wallet.INDEX]["Open"]

                print("profit percent:", profit_percent)

                if self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_LONG.value:

                    for key in last_keys_1m:
                        if int(key) > Data.to_timestamp(self.wallet.orders[self.wallet.INDEX]["DateOpen"]):
                            if data["historical_prices"]["1m"][key]["isMinLocal"]:
                                curr_stop = trailing_stop.set_stop(
                                    #min(data["historical_prices"]["1m"][key]["o"], data["historical_prices"]["1m"][key]["c"]),
                                    data["historical_prices"]["1m"][key]["l"],
                                    Parameters.TYPE_LONG.value
                                )
                                print(f'updated stop is {curr_stop}')
                                
                                break
                    print(f'current stop is {trailing_stop.actual_stop()} at {Data.to_datetime(data["current_date"])}')
                    print("current price:", data["historical_prices"]["1s"][last_key_1s]["p"])
                    print("current bar:", Data.to_datetime(data["historical_prices"]["1m"][last_key_1m]["t"]).strftime("%Y-%m-%d %H:%M:%S"))
                    
                    '''resp = await self.check_conditions(
                        cond=all(
                            [
                                abs(data["historical_prices"]["5m"][last_key]["rsi"] - 70) < 3.
                            ]
                        )
                    )'''

                    resp1 = await self.check_conditions(
                        cond=all(
                            [
                                profit_percent<0 or profit_percent>0.5,
                                trailing_stop.check_trigger(data["historical_prices"]["1s"][last_key_1s]["p"], Parameters.TYPE_LONG.value)
                            ]
                        )
                    )

                    '''resp1, resp2 = await asyncio.gather(
                        self.check_conditions(
                            cond=all(
                                [
                                    #take_profit.check_trigger(data["historical_prices"]["1s"][last_key_1s]["p"], Parameters.TYPE_LONG.value) or abs(data["current_state"]["rsi-1m"] - 70) < 5.
                                    profit_percent >= 9. # / 20.
                                ]
                            )
                        ),
                        self.check_conditions(
                            cond=all(
                                [
                                    stop_loss.check_trigger(data["historical_prices"]["1s"][last_key_1s]["p"], Parameters.TYPE_LONG.value),
                                    #data["historical_prices"]["1s"][last_key_1s]["p"] < self.wallet.orders[self.wallet.INDEX]['Open'] - 5.,
                                    #data["historical_prices"]["5m"][last_key_5m]["c"] <= min( data["historical_prices"]["5m"][key]["l"] for key in last_keys_5m )
                                ]
                            )
                        )
                    )'''

                    if resp1:
                        print("Position closed - Trailing Stop")
                        print("5m RSI:", data["historical_prices"]["5m"][last_key_5m]["rsi"])

                        if order_type == "market":

                            self.wallet.close_position(
                                side="SELL",
                                quantity=self.qty,
                                price=data["historical_prices"]["1m"][last_key_1m]["c"],
                                date=Data.to_datetime(data["historical_prices"]["1m"][last_key_1m]["t"]).strftime("%Y-%m-%d %H:%M:%S")
                                #type=Client.FUTURE_ORDER_TYPE_LIMIT
                            )
                        
                        elif order_type == "limit":

                            self.wallet.close_position(
                                side="SELL",
                                quantity=self.qty,
                                price=data["historical_prices"]["1m"][last_key_1m]["c"],
                                date=Data.to_datetime(data["historical_prices"]["1m"][last_key_1m]["t"]).strftime("%Y-%m-%d %H:%M:%S"),
                                type=Client.FUTURE_ORDER_TYPE_LIMIT
                            )

                        print(self.wallet.orders)
                        
                        await asyncio.gather(
                            event.wait(),
                            self.check_event_is_order_filled(
                                event=event,
                                t=1
                            )
                        )
                        event.clear()
                        
                        #print(self.wallet.orders)

                        Notification("bhaskan@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))
                        #Notification("oozlen@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))

                        self.write_to_excel()

                        # for security reasons:
                        if profit_percent<0:

                            await asyncio.gather(
                                event.wait(),
                                self.check_event_reset_conditions(
                                    event=event,
                                    interval="5m",
                                    t=1
                                )
                            )
                            event.clear()
                    
                    '''elif resp2:
                        print("Stop Loss")

                        if order_type == "market":

                            self.wallet.close_position(
                                side="SELL",
                                quantity=self.qty,
                                price=data["historical_prices"]["1m"][last_key_1m]["c"],
                                date=Data.to_datetime(data["historical_prices"]["1m"][last_key_1m]["t"]).strftime("%Y-%m-%d %H:%M:%S")
                                #type=Client.FUTURE_ORDER_TYPE_LIMIT
                            )

                        elif order_type == "limit":

                            self.wallet.close_position(
                                side="SELL",
                                quantity=self.qty,
                                price=data["historical_prices"]["1m"][last_key_1m]["c"],
                                date=Data.to_datetime(data["historical_prices"]["1m"][last_key_1m]["t"]).strftime("%Y-%m-%d %H:%M:%S"),
                                type=Client.FUTURE_ORDER_TYPE_LIMIT
                            )

                        await asyncio.gather(
                            event.wait(),
                            self.check_event_is_order_filled(
                                event=event,
                                t=1
                            )
                        )
                        event.clear()

                        print(self.wallet.orders)

                        Notification("bhaskan@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))
                        #Notification("oozlen@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))

                        self.write_to_excel()

                        await asyncio.gather(
                            event.wait(),
                            self.check_event_reset_conditions(
                                event=event,
                                interval="5m",
                                t=1
                            )
                        )
                        event.clear()'''

                elif self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_SHORT.value:

                    for key in last_keys_1m:
                        if int(key) > Data.to_timestamp(self.wallet.orders[self.wallet.INDEX]["DateOpen"]):
                            if data["historical_prices"]["1m"][key]["isMaxLocal"]:
                                curr_stop = trailing_stop.set_stop(
                                    #max(data["historical_prices"]["1m"][key]["o"], data["historical_prices"]["1m"][key]["c"]),
                                    data["historical_prices"]["1m"][key]["h"],
                                    Parameters.TYPE_SHORT.value
                                )
                                print(f'updated stop is {curr_stop}')
                                
                                break
                    print(f'current stop is {trailing_stop.actual_stop()} at {Data.to_datetime(data["current_date"])}')
                    print("current price:", data["historical_prices"]["1s"][last_key_1s]["p"])
                    print("current bar:", Data.to_datetime(data["historical_prices"]["1m"][last_key_1m]["t"]).strftime("%Y-%m-%d %H:%M:%S"))
                    
                    '''resp = await self.check_conditions(
                        cond=all(
                            [
                                abs(data["historical_prices"]["5m"][last_key]["rsi"] - 30) < 3.
                            ]
                        )
                    )'''

                    resp1 = await self.check_conditions(
                        cond=all(
                            [
                                profit_percent<0 or profit_percent>0.5,
                                trailing_stop.check_trigger(data["historical_prices"]["1s"][last_key_1s]["p"], Parameters.TYPE_SHORT.value)
                            ]
                        )
                    )

                    '''resp1, resp2 = await asyncio.gather(
                        self.check_conditions(
                            cond=all(
                                [
                                    #take_profit.check_trigger(data["historical_prices"]["1s"][last_key_1s]["p"], Parameters.TYPE_SHORT.value) or abs(data["current_state"]["rsi-1m"] - 30) < 5.
                                    profit_percent >= 9. # / 20.
                                ]
                            )
                        ),
                        self.check_conditions(
                            cond=all(
                                [
                                    stop_loss.check_trigger(data["historical_prices"]["1s"][last_key_1s]["p"], Parameters.TYPE_SHORT.value),
                                    #data["historical_prices"]["1s"][last_key_1s]["p"] > self.wallet.orders[self.wallet.INDEX]['Open'] + 5.,
                                    #data["historical_prices"]["5m"][last_key_5m]["c"] >= max( data["historical_prices"]["5m"][key]["h"] for key in last_keys_5m )
                                ]
                            )
                        )
                    )'''

                    if resp1:
                        print("Position closed - Trailing Stop")
                        print("5m RSI:", data["historical_prices"]["5m"][last_key_5m]["rsi"])

                        if order_type == "market":

                            self.wallet.close_position(
                                side="BUY",
                                quantity=self.qty,
                                price=data["historical_prices"]["1m"][last_key_1m]["c"],
                                date=Data.to_datetime(data["historical_prices"]["1m"][last_key_1m]["t"]).strftime("%Y-%m-%d %H:%M:%S")
                                #type=Client.FUTURE_ORDER_TYPE_LIMIT
                            )

                        elif order_type == "limit":

                            self.wallet.close_position(
                                side="BUY",
                                quantity=self.qty,
                                price=data["historical_prices"]["1m"][last_key_1m]["c"],
                                date=Data.to_datetime(data["historical_prices"]["1m"][last_key_1m]["t"]).strftime("%Y-%m-%d %H:%M:%S"),
                                type=Client.FUTURE_ORDER_TYPE_LIMIT
                            )

                        print(self.wallet.orders)
                        
                        await asyncio.gather(
                            event.wait(),
                            self.check_event_is_order_filled(
                                event=event,
                                t=1
                            )
                        )
                        event.clear()

                        #print(self.wallet.orders)

                        Notification("bhaskan@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))
                        #Notification("oozlen@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))

                        self.write_to_excel()

                        # for security reasons:
                        if profit_percent<0:

                            await asyncio.gather(
                                event.wait(),
                                self.check_event_reset_conditions(
                                    event=event,
                                    interval="5m",
                                    t=1
                                )
                            )
                            event.clear()

                    '''elif resp2:
                        print("Stop Loss")

                        if order_type == "market":

                            self.wallet.close_position(
                                side="BUY",
                                quantity=self.qty,
                                price=data["historical_prices"]["1m"][last_key_1m]["c"],
                                date=Data.to_datetime(data["historical_prices"]["1m"][last_key_1m]["t"]).strftime("%Y-%m-%d %H:%M:%S")
                                #type=Client.FUTURE_ORDER_TYPE_LIMIT
                            )

                        elif order_type == "limit":

                            self.wallet.close_position(
                                side="BUY",
                                quantity=self.qty,
                                price=data["historical_prices"]["1m"][last_key_1m]["c"],
                                date=Data.to_datetime(data["historical_prices"]["1m"][last_key_1m]["t"]).strftime("%Y-%m-%d %H:%M:%S"),
                                type=Client.FUTURE_ORDER_TYPE_LIMIT
                            )

                        await asyncio.gather(
                            event.wait(),
                            self.check_event_is_order_filled(
                                event=event,
                                t=1
                            )
                        )
                        event.clear()

                        print(self.wallet.orders)

                        Notification("bhaskan@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))
                        #Notification("oozlen@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))

                        self.write_to_excel()

                        await asyncio.gather(
                            event.wait(),
                            self.check_event_reset_conditions(
                                event=event,
                                interval="5m",
                                t=1
                            )
                        )
                        event.clear()'''

            with open(f"log.json", "w") as log:
                log.write(json.dumps(self.wallet.orders))

    async def strategy_2_diff_DEV(self, order_type="market"):

        while True:

            data = self.read_memory()

            last_key_1s = list(data["historical_prices"]["1s"].keys())[-1]

            last_key_1m = list(data["historical_prices"]["1m"].keys())[-1]
            last_keys_1m = [
                list(data["historical_prices"]["1m"].keys())[-i] for i in range(1,10)
            ]

            last_key_5m = list(data["historical_prices"]["5m"].keys())[-1]
            last_keys_5m = [
                list(data["historical_prices"]["5m"].keys())[-i] for i in range(1,10)
            ]

            last_key_15m = list(data["historical_prices"]["15m"].keys())[-1]
            last_keys_15m = [
                list(data["historical_prices"]["15m"].keys())[-i] for i in range(1,10)
            ]

            global event

            #with open("rsi_output.csv", "a") as r:
            #    d = "{},{:.{}f}\n".format(Data.to_datetime(data["current_date"]), data["historical_prices"]["5m"][last_key_5m]["rsi"], 2)
            #    r.write(d)

            if not self.wallet.is_open():
                #print("Waiting to open position")
                print("Waiting to open position", Data.to_datetime(data["current_date"]))
                print("5m RSI:", data["historical_prices"]["5m"][last_key_5m]["rsi"])
                print("15m realtime RSI:", data["current_state"]["rsi-15m"])
                print("15m RSI:", data["historical_prices"]["15m"][last_key_15m]["rsi"])

                resp1, resp2 = await asyncio.gather(
                    self.check_conditions(
                        cond=all(
                            [
                                #not abs(data["historical_prices"]["1m"][last_key_1m]["rsi"] - 70.) < 4.,
                                # not data["historical_prices"]["1m"][last_key_1m]["rsi"] > (70 - 3.),
                                #data["historical_prices"]["1m"][last_key_1m]["normalized_volume"] <= 1.,
                                #abs(data["historical_prices"]["5m"][last_key_5m]["rsi"] - 70.) < 3.,
                                data["historical_prices"]["15m"][last_key_15m]["rsi"] > (75 - 3.),
                                #data["historical_prices"]["5m"][last_key_5m]["normalized_volume"] <= 0.5
                            ]
                        )
                    ),
                    self.check_conditions(
                        cond=all(
                            [
                                #not abs(data["historical_prices"]["1m"][last_key_1m]["rsi"] - 30.) < 4.,
                                # not data["historical_prices"]["1m"][last_key_1m]["rsi"] < (30 + 3.),
                                #data["historical_prices"]["1m"][last_key_1m]["normalized_volume"] <= 1.,
                                #abs(data["historical_prices"]["5m"][last_key_5m]["rsi"] - 30.) < 3.,
                                data["historical_prices"]["15m"][last_key_15m]["rsi"] < (25 + 3.),
                                #data["historical_prices"]["5m"][last_key_5m]["normalized_volume"] <= 0.5
                            ]
                        )
                    )
                )

                if resp1:
                    print("condition 1 satisfied")
                    print("5m RSI:", data["historical_prices"]["5m"][last_key_5m]["rsi"])
                    print("15m RSI:", data["historical_prices"]["15m"][last_key_15m]["rsi"])
                    print(data["current_state"]["rsi-15m"])

                    await asyncio.gather(
                        event.wait(),
                        self.check_event_rsi_change(
                            event=event,
                            direction="down",
                            interval="15m",
                            t=1
                        )
                    )
                    event.clear()

                    if order_type == "market":

                        # open position...
                        self.wallet.open_position(
                            side="SELL",
                            quantity=self.qty,
                            price=data["historical_prices"]["1s"][last_key_1s]["p"],
                            date=Data.to_datetime(data["historical_prices"]["1s"][last_key_1s]["t"]).strftime("%Y-%m-%d %H:%M:%S")
                            #type=Client.FUTURE_ORDER_TYPE_LIMIT
                        )

                    elif order_type == "limit":

                        # open position...
                        self.wallet.open_position(
                            side="SELL",
                            quantity=self.qty,
                            price=data["historical_prices"]["1s"][last_key_1s]["p"],
                            date=Data.to_datetime(data["historical_prices"]["1s"][last_key_1s]["t"]).strftime("%Y-%m-%d %H:%M:%S"),
                            type=Client.FUTURE_ORDER_TYPE_LIMIT
                        )

                    await asyncio.gather(
                        event.wait(),
                        self.check_event_is_order_filled(
                            event=event,
                            t=1
                        )
                    )
                    event.clear()

                    stop_loss = StopLoss(max(data["historical_prices"]["1m"][last_key_1m]["o"], data["historical_prices"]["1m"][last_key_1m]["c"]) + 5.)

                    print(self.wallet.orders)

                    #Notification("bhaskan@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))
                    #Notification("oozlen@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))

                    self.write_to_excel()

                if resp2:
                    print("condition 2 satisfied")
                    print("5m RSI:", data["historical_prices"]["5m"][last_key_5m]["rsi"])
                    print("15m RSI:", data["historical_prices"]["15m"][last_key_15m]["rsi"])
                    print(data["current_state"]["rsi-15m"])

                    await asyncio.gather(
                        event.wait(),
                        self.check_event_rsi_change(
                            event=event,
                            direction="up",
                            interval="15m",
                            t=1
                        )
                    )
                    event.clear()

                    if order_type == "market":

                        # open position...
                        self.wallet.open_position(
                            side="BUY",
                            quantity=self.qty,
                            price=data["historical_prices"]["1s"][last_key_1s]["p"],
                            date=Data.to_datetime(data["historical_prices"]["1s"][last_key_1s]["t"]).strftime("%Y-%m-%d %H:%M:%S")
                            #type=Client.FUTURE_ORDER_TYPE_LIMIT
                        )

                    elif order_type == "limit":

                        # open position...
                        self.wallet.open_position(
                            side="BUY",
                            quantity=self.qty,
                            price=data["historical_prices"]["1s"][last_key_1s]["p"],
                            date=Data.to_datetime(data["historical_prices"]["1s"][last_key_1s]["t"]).strftime("%Y-%m-%d %H:%M:%S"),
                            type=Client.FUTURE_ORDER_TYPE_LIMIT
                        )

                    await asyncio.gather(
                        event.wait(),
                        self.check_event_is_order_filled(
                            event=event,
                            t=1
                        )
                    )
                    event.clear()

                    stop_loss = StopLoss(min(data["historical_prices"]["1m"][last_key_1m]["o"], data["historical_prices"]["1m"][last_key_1m]["c"]) - 5.)

                    print(self.wallet.orders)

                    #Notification("bhaskan@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))
                    #Notification("oozlen@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))

                    self.write_to_excel()

            elif self.wallet.is_open():
                print("Waiting to close position", Data.to_datetime(data["current_date"]))
                print("5m RSI:", data["historical_prices"]["5m"][last_key_5m]["rsi"])
                print(data["current_state"]["rsi-5m"])

                # Calculate PNL %
                if self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_LONG.value:
                    profit_percent = 100 * (data["historical_prices"]["1s"][last_key_1s]["p"] - self.wallet.orders[self.wallet.INDEX]["Open"]) * float(Parameters.INDEX_POINT.value) / self.wallet.orders[self.wallet.INDEX]["Open"]
                elif self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_SHORT.value:
                    profit_percent = 100 * (self.wallet.orders[self.wallet.INDEX]["Open"] - data["historical_prices"]["1s"][last_key_1s]["p"]) * float(Parameters.INDEX_POINT.value) / self.wallet.orders[self.wallet.INDEX]["Open"]

                print("profit percent:", profit_percent)

                if self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_LONG.value:
                    
                    '''resp = await self.check_conditions(
                        cond=all(
                            [
                                abs(data["historical_prices"]["5m"][last_key]["rsi"] - 70) < 3.
                            ]
                        )
                    )'''

                    resp1, resp2 = await asyncio.gather(
                        self.check_conditions(
                            cond=all(
                                [
                                    #abs(data["historical_prices"]["1m"][last_key_1m]["rsi"] - 70) < 2.
                                    data["current_state"]["rsi-15m"] > (68 - 4.)
                                    #profit_percent >= 9. # / 20.
                                ]
                            )
                        ),
                        self.check_conditions(
                            cond=all(
                                [
                                    stop_loss.check_trigger(data["historical_prices"]["1s"][last_key_1s]["p"], Parameters.TYPE_LONG.value),
                                    #data["historical_prices"]["1s"][last_key_1s]["p"] < self.wallet.orders[self.wallet.INDEX]['Open'] - 5.,
                                    #data["historical_prices"]["5m"][last_key_5m]["c"] <= min( data["historical_prices"]["5m"][key]["l"] for key in last_keys_5m )
                                ]
                            )
                        )
                    )

                    if resp1:
                        print("Position closed")
                        print("5m RSI:", data["historical_prices"]["5m"][last_key_5m]["rsi"])

                        if order_type == "market":

                            self.wallet.close_position(
                                side="SELL",
                                quantity=self.qty,
                                price=data["historical_prices"]["1s"][last_key_1s]["p"],
                                date=Data.to_datetime(data["historical_prices"]["1s"][last_key_1s]["t"]).strftime("%Y-%m-%d %H:%M:%S")
                                #type=Client.FUTURE_ORDER_TYPE_LIMIT
                            )

                        elif order_type == "limit":

                            self.wallet.close_position(
                                side="SELL",
                                quantity=self.qty,
                                price=data["historical_prices"]["1s"][last_key_1s]["p"],
                                date=Data.to_datetime(data["historical_prices"]["1s"][last_key_1s]["t"]).strftime("%Y-%m-%d %H:%M:%S"),
                                type=Client.FUTURE_ORDER_TYPE_LIMIT
                            )

                        await asyncio.gather(
                            event.wait(),
                            self.check_event_is_order_filled(
                                event=event,
                                t=1
                            )
                        )
                        event.clear()
                        
                        print(self.wallet.orders)

                        #Notification("bhaskan@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))
                        #Notification("oozlen@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))

                        self.write_to_excel()
                    
                    elif resp2:
                        print("Stop Loss")

                        if order_type == "market":

                            self.wallet.close_position(
                                side="SELL",
                                quantity=self.qty,
                                price=data["historical_prices"]["1s"][last_key_1s]["p"],
                                date=Data.to_datetime(data["historical_prices"]["1s"][last_key_1s]["t"]).strftime("%Y-%m-%d %H:%M:%S")
                                #type=Client.FUTURE_ORDER_TYPE_LIMIT
                            )

                        elif order_type == "limit":

                            self.wallet.close_position(
                                side="SELL",
                                quantity=self.qty,
                                price=data["historical_prices"]["1s"][last_key_1s]["p"],
                                date=Data.to_datetime(data["historical_prices"]["1s"][last_key_1s]["t"]).strftime("%Y-%m-%d %H:%M:%S"),
                                type=Client.FUTURE_ORDER_TYPE_LIMIT
                            )

                        await asyncio.gather(
                            event.wait(),
                            self.check_event_is_order_filled(
                                event=event,
                                t=1
                            )
                        )
                        event.clear()

                        print(self.wallet.orders)

                        #Notification("bhaskan@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))
                        #Notification("oozlen@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))

                        self.write_to_excel()

                        '''await asyncio.gather(
                            event.wait(),
                            self.check_event_reset_conditions(
                                event=event,
                                interval="15m",
                                t=1
                            )
                        )
                        event.clear()'''

                elif self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_SHORT.value:
                    
                    '''resp = await self.check_conditions(
                        cond=all(
                            [
                                abs(data["historical_prices"]["5m"][last_key]["rsi"] - 30) < 3.
                            ]
                        )
                    )'''

                    resp1, resp2 = await asyncio.gather(
                        self.check_conditions(
                            cond=all(
                                [
                                    #abs(data["historical_prices"]["5m"][last_key_5m]["rsi"] - 30) < 5.
                                    data["current_state"]["rsi-15m"] < (32 + 4.)
                                    #profit_percent >= 9. # / 20.
                                ]
                            )
                        ),
                        self.check_conditions(
                            cond=all(
                                [
                                    stop_loss.check_trigger(data["historical_prices"]["1s"][last_key_1s]["p"], Parameters.TYPE_SHORT.value),
                                    #data["historical_prices"]["1s"][last_key_1s]["p"] > self.wallet.orders[self.wallet.INDEX]['Open'] + 5.,
                                    #data["historical_prices"]["5m"][last_key_5m]["c"] >= max( data["historical_prices"]["5m"][key]["h"] for key in last_keys_5m )
                                ]
                            )
                        )
                    )

                    if resp1:
                        print("Position closed")
                        print("5m RSI:", data["historical_prices"]["5m"][last_key_5m]["rsi"])

                        if order_type == "market":

                            self.wallet.close_position(
                                side="BUY",
                                quantity=self.qty,
                                price=data["historical_prices"]["1s"][last_key_1s]["p"],
                                date=Data.to_datetime(data["historical_prices"]["1s"][last_key_1s]["t"]).strftime("%Y-%m-%d %H:%M:%S")
                                #type=Client.FUTURE_ORDER_TYPE_LIMIT
                            )

                        elif order_type == "limit":

                            self.wallet.close_position(
                                side="BUY",
                                quantity=self.qty,
                                price=data["historical_prices"]["1s"][last_key_1s]["p"],
                                date=Data.to_datetime(data["historical_prices"]["1s"][last_key_1s]["t"]).strftime("%Y-%m-%d %H:%M:%S"),
                                type=Client.FUTURE_ORDER_TYPE_LIMIT
                            )

                        await asyncio.gather(
                            event.wait(),
                            self.check_event_is_order_filled(
                                event=event,
                                t=1
                            )
                        )
                        event.clear()

                        print(self.wallet.orders)

                        #Notification("bhaskan@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))
                        #Notification("oozlen@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))

                        self.write_to_excel()

                    elif resp2:
                        print("Stop Loss")

                        if order_type == "market":

                            self.wallet.close_position(
                                side="BUY",
                                quantity=self.qty,
                                price=data["historical_prices"]["1s"][last_key_1s]["p"],
                                date=Data.to_datetime(data["historical_prices"]["1s"][last_key_1s]["t"]).strftime("%Y-%m-%d %H:%M:%S")
                                #type=Client.FUTURE_ORDER_TYPE_LIMIT
                            )

                        elif order_type == "limit":

                            self.wallet.close_position(
                                side="BUY",
                                quantity=self.qty,
                                price=data["historical_prices"]["1s"][last_key_1s]["p"],
                                date=Data.to_datetime(data["historical_prices"]["1s"][last_key_1s]["t"]).strftime("%Y-%m-%d %H:%M:%S"),
                                type=Client.FUTURE_ORDER_TYPE_LIMIT
                            )

                        await asyncio.gather(
                            event.wait(),
                            self.check_event_is_order_filled(
                                event=event,
                                t=1
                            )
                        )
                        event.clear()

                        print(self.wallet.orders)

                        #Notification("bhaskan@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))
                        #Notification("oozlen@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))

                        self.write_to_excel()

                        '''await asyncio.gather(
                            event.wait(),
                            self.check_event_reset_conditions(
                                event=event,
                                interval="15m",
                                t=1
                            )
                        )
                        event.clear()'''

            with open(f"log.json", "w") as log:
                log.write(json.dumps(self.wallet.orders))

    async def strategy_1_PROD(self):

        while True:

            data = self.read_memory()

            last_key_1s = list(data["historical_prices"]["1s"].keys())[-1]

            last_key_1m = list(data["historical_prices"]["1m"].keys())[-1]
            last_keys_1m = [
                list(data["historical_prices"]["1m"].keys())[-i] for i in range(1,10)
            ]

            last_key_5m = list(data["historical_prices"]["5m"].keys())[-1]
            last_keys_5m = [
                list(data["historical_prices"]["5m"].keys())[-i] for i in range(1,10)
            ]

            print("current price:", data["historical_prices"]["1s"][last_key_1s]["p"])

            if not self.wallet.is_open():
                #print("Waiting to open position")
                print("Waiting to open position", Data.to_datetime(data["current_date"]))
                print("RSI 1m:", data["historical_prices"]["1m"][last_key_1m]["rsi"])
                #print("RSI 5m:", data["historical_prices"]["5m"][last_key_5m]["rsi"])
                print("Norm. volume 1m:", data["historical_prices"]["1m"][last_key_1m]["normalized_volume"])
                print("Norm. volume 5m:", data["historical_prices"]["5m"][last_key_5m]["normalized_volume"])

                resp1, resp2 = await asyncio.gather(
                    self.check_conditions(
                        cond=all(
                            [
                                #not abs(data["historical_prices"]["1m"][last_key_1m]["rsi"] - 70.) < 4.,
                                data["historical_prices"]["1m"][last_key_1m]["rsi"] > (70 - 4.),
                                data["historical_prices"]["1m"][last_key_1m]["normalized_volume"] > .5,
                                #abs(data["historical_prices"]["5m"][last_key_5m]["rsi"] - 70.) < 3.,
                                #data["historical_prices"]["5m"][last_key_5m]["rsi"] > (70 - 6.),
                                #data["historical_prices"]["5m"][last_key_5m]["normalized_volume"] > .0
                            ]
                        )
                    ),
                    self.check_conditions(
                        cond=all(
                            [
                                #not abs(data["historical_prices"]["1m"][last_key_1m]["rsi"] - 30.) < 4.,
                                data["historical_prices"]["1m"][last_key_1m]["rsi"] < (30 + 4.),
                                data["historical_prices"]["1m"][last_key_1m]["normalized_volume"] > .5,
                                #abs(data["historical_prices"]["5m"][last_key_5m]["rsi"] - 30.) < 3.,
                                #data["historical_prices"]["5m"][last_key_5m]["rsi"] < (30 + 6.),
                                #data["historical_prices"]["5m"][last_key_5m]["normalized_volume"] > .0
                            ]
                        )
                    )
                )

                if resp1:
                    print("condition 1 satisfied")

                    # open position...
                    self.wallet.open_position(
                        side="BUY",
                        quantity=self.qty,
                        price=data["historical_prices"]["1s"][last_key_1s]["p"],
                        date=Data.to_datetime(data["historical_prices"]["1s"][last_key_1s]["t"]).strftime("%Y-%m-%d %H:%M:%S")
                    )

                    print(self.wallet.orders)
                    
                    await asyncio.gather(
                        event.wait(),
                        self.check_event_is_order_filled(
                            event=event,
                            t=1
                        )
                    )
                    event.clear()

                    #stop_loss = StopLoss(max(data["historical_prices"]["1m"][last_key_1m]["o"], data["historical_prices"]["1m"][last_key_1m]["c"]) - 2.)
                    #trailing_stop = MyTrailingStop(data["historical_prices"]["1m"][last_key_1m]["c"] - 5.)
                    trailing_stop = MyTrailingStop(data["historical_prices"]["1s"][last_key_1s]["p"] - 5.)
                    print(f'current stop is {trailing_stop.actual_stop()}')

                    #print(self.wallet.orders)

                    Notification("bhaskan@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))
                    #Notification("oozlen@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))

                    self.write_to_excel()

                if resp2:
                    print("condition 2 satisfied")

                    # open position...
                    self.wallet.open_position(
                        side="SELL",
                        quantity=self.qty,
                        price=data["historical_prices"]["1s"][last_key_1s]["p"],
                        date=Data.to_datetime(data["historical_prices"]["1s"][last_key_1s]["t"]).strftime("%Y-%m-%d %H:%M:%S")
                    )

                    print(self.wallet.orders)
                    
                    await asyncio.gather(
                        event.wait(),
                        self.check_event_is_order_filled(
                            event=event,
                            t=1
                        )
                    )
                    event.clear()

                    #stop_loss = StopLoss(max(data["historical_prices"]["1m"][last_key_1m]["o"], data["historical_prices"]["1m"][last_key_1m]["c"]) + 2.)
                    #trailing_stop = MyTrailingStop(data["historical_prices"]["1m"][last_key_1m]["c"] + 5.)
                    trailing_stop = MyTrailingStop(data["historical_prices"]["1s"][last_key_1s]["p"] + 5.)
                    print(f'current stop is {trailing_stop.actual_stop()}')

                    #print(self.wallet.orders)

                    Notification("bhaskan@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))
                    #Notification("oozlen@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))

                    self.write_to_excel()

            elif self.wallet.is_open():
                print("Waiting to close position", Data.to_datetime(data["current_date"]))

                if self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_LONG.value:

                    for key in last_keys_1m:
                        if int(key) > Data.to_timestamp(self.wallet.orders[self.wallet.INDEX]["DateOpen"]):
                            if data["historical_prices"]["1m"][key]["isMinLocal"]:
                                curr_stop = trailing_stop.set_stop(
                                    #min(data["historical_prices"]["1m"][key]["o"], data["historical_prices"]["1m"][key]["c"]),
                                    data["historical_prices"]["1m"][key]["l"],
                                    Parameters.TYPE_LONG.value
                                )
                                print(f'updated stop is {curr_stop}')
                                
                                break
                    print(f'current stop is {trailing_stop.actual_stop()} at {Data.to_datetime(data["current_date"])}')
                    print("current price:", data["historical_prices"]["1s"][last_key_1s]["p"])
                    print("current bar:", Data.to_datetime(data["historical_prices"]["1m"][last_key_1m]["t"]).strftime("%Y-%m-%d %H:%M:%S"))

                    #trailing_stop.update_stop(data["historical_prices"]["1s"][last_key_1s]["p"], Parameters.TYPE_LONG.value)
                    #print("Current Stop:", trailing_stop.current_stop)
                    
                    '''resp = await self.check_conditions(
                        cond=all(
                            [
                                abs(data["historical_prices"]["5m"][last_key]["rsi"] - 70) < 3.
                            ]
                        )
                    )'''

                    resp1 = await self.check_conditions(
                        cond=all(
                            [
                                trailing_stop.check_trigger(data["historical_prices"]["1s"][last_key_1s]["p"], Parameters.TYPE_LONG.value)
                            ]
                        )
                    )

                    '''resp1, resp2 = await asyncio.gather(
                        self.check_conditions(
                            cond=all(
                                [
                                    trailing_stop.check_trigger(data["historical_prices"]["1s"][last_key_1s]["p"], Parameters.TYPE_LONG.value)
                                ]
                            )
                        ),
                        self.check_conditions(
                            cond=all(
                                [
                                    #data["historical_prices"]["1s"][last_key_1s]["p"] < self.wallet.orders[self.wallet.INDEX]['Open'] - 5.,
                                    stop_loss.check_trigger(data["historical_prices"]["1s"][last_key_1s]["p"], Parameters.TYPE_LONG.value)
                                ]
                            )
                        )
                    )'''

                    if resp1:
                        print("Position closed - Trailing Stop")

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=data["historical_prices"]["1s"][last_key_1s]["p"],
                            date=Data.to_datetime(data["historical_prices"]["1s"][last_key_1s]["t"]).strftime("%Y-%m-%d %H:%M:%S")
                        )

                        print(self.wallet.orders)
                        
                        await asyncio.gather(
                            event.wait(),
                            self.check_event_is_order_filled(
                                event=event,
                                t=1
                            )
                        )
                        event.clear()

                        #print(self.wallet.orders)

                        Notification("bhaskan@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))
                        #Notification("oozlen@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))

                        self.write_to_excel()
                    
                    '''elif resp2:
                        print("Stop Loss")

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=data["historical_prices"]["1s"][last_key_1s]["p"],
                            date=Data.to_datetime(data["historical_prices"]["1s"][last_key_1s]["t"]).strftime("%Y-%m-%d %H:%M:%S")
                        )

                        await asyncio.gather(
                            event.wait(),
                            self.check_event_is_order_filled(
                                event=event,
                                t=1
                            )
                        )
                        event.clear()

                        print(self.wallet.orders)

                        Notification("bhaskan@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))
                        #Notification("oozlen@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))

                        self.write_to_excel()'''

                elif self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_SHORT.value:

                    for key in last_keys_1m:
                        if int(key) > Data.to_timestamp(self.wallet.orders[self.wallet.INDEX]["DateOpen"]):
                            if data["historical_prices"]["1m"][key]["isMaxLocal"]:
                                curr_stop = trailing_stop.set_stop(
                                    #max(data["historical_prices"]["1m"][key]["o"], data["historical_prices"]["1m"][key]["c"]),
                                    data["historical_prices"]["1m"][key]["h"],
                                    Parameters.TYPE_SHORT.value
                                )
                                print(f'updated stop is {curr_stop}')
                                
                                break
                    print(f'current stop is {trailing_stop.actual_stop()} at {Data.to_datetime(data["current_date"])}')
                    print("current price:", data["historical_prices"]["1s"][last_key_1s]["p"])
                    print("current bar:", Data.to_datetime(data["historical_prices"]["1m"][last_key_1m]["t"]).strftime("%Y-%m-%d %H:%M:%S"))

                    #trailing_stop.update_stop(data["historical_prices"]["1s"][last_key_1s]["p"], Parameters.TYPE_SHORT.value)
                    #print("Current Stop:", trailing_stop.current_stop)
                    
                    '''resp = await self.check_conditions(
                        cond=all(
                            [
                                abs(data["historical_prices"]["5m"][last_key]["rsi"] - 30) < 3.
                            ]
                        )
                    )'''

                    resp1 = await self.check_conditions(
                        cond=all(
                            [
                                trailing_stop.check_trigger(data["historical_prices"]["1s"][last_key_1s]["p"], Parameters.TYPE_SHORT.value)
                            ]
                        )
                    )

                    '''resp1, resp2 = await asyncio.gather(
                        self.check_conditions(
                            cond=all(
                                [
                                    trailing_stop.check_trigger(data["historical_prices"]["1s"][last_key_1s]["p"], Parameters.TYPE_SHORT.value)
                                ]
                            )
                        ),
                        self.check_conditions(
                            cond=all(
                                [
                                    #data["historical_prices"]["1s"][last_key_1s]["p"] > self.wallet.orders[self.wallet.INDEX]['Open'] + 5.,
                                    stop_loss.check_trigger(data["historical_prices"]["1s"][last_key_1s]["p"], Parameters.TYPE_SHORT.value)
                                ]
                            )
                        )
                    )'''

                    if resp1:
                        print("Position closed - Trailing Stop")
                        print("5m RSI:", data["historical_prices"]["5m"][last_key_5m]["rsi"])

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=data["historical_prices"]["1s"][last_key_1s]["p"],
                            date=Data.to_datetime(data["historical_prices"]["1s"][last_key_1s]["t"]).strftime("%Y-%m-%d %H:%M:%S")
                        )

                        print(self.wallet.orders)
                        
                        await asyncio.gather(
                            event.wait(),
                            self.check_event_is_order_filled(
                                event=event,
                                t=1
                            )
                        )
                        event.clear()

                        #print(self.wallet.orders)

                        Notification("bhaskan@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))
                        #Notification("oozlen@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))

                        self.write_to_excel()

                    '''elif resp2:
                        print("Stop Loss")

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=data["historical_prices"]["1s"][last_key_1s]["p"],
                            date=Data.to_datetime(data["historical_prices"]["1s"][last_key_1s]["t"]).strftime("%Y-%m-%d %H:%M:%S")
                        )

                        await asyncio.gather(
                            event.wait(),
                            self.check_event_is_order_filled(
                                event=event,
                                t=1
                            )
                        )
                        event.clear()

                        print(self.wallet.orders)

                        Notification("bhaskan@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))
                        #Notification("oozlen@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))

                        self.write_to_excel()'''

            with open(f"log.json", "w") as log:
                log.write(json.dumps(self.wallet.orders))

    async def strategy_1_diff_DEV(self):

        while True:

            data = self.read_memory()

            last_key_1s = list(data["historical_prices"]["1s"].keys())[-1]

            last_key_1m = list(data["historical_prices"]["1m"].keys())[-1]
            last_keys_1m = [
                list(data["historical_prices"]["1m"].keys())[-i] for i in range(1,10)
            ]

            last_key_5m = list(data["historical_prices"]["5m"].keys())[-1]
            last_keys_5m = [
                list(data["historical_prices"]["5m"].keys())[-i] for i in range(1,10)
            ]

            print(data["historical_prices"]["1m"][last_key_1m]["rsi"])
            print(data["historical_prices"]["1m"][last_key_1m]["minmax_volume"])
            print(abs(data["historical_prices"]["1m"][last_key_1m]["rsi"] - 50) * data["historical_prices"]["1m"][last_key_1m]["minmax_volume"])

            if not self.wallet.is_open():
                #print("Waiting to open position")
                print("Waiting to open position", Data.to_datetime(data["current_date"]))

                resp1, resp2 = await asyncio.gather(
                    self.check_conditions(
                        cond=all(
                            [
                                abs(data["historical_prices"]["1m"][last_key_1m]["rsi"] - 50) * data["historical_prices"]["1m"][last_key_1m]["minmax_volume"] > 10,
                                data["historical_prices"]["1m"][last_key_1m]["rsi"] > data["historical_prices"]["1m"][last_keys_1m[-2]]["rsi"]
                            ]
                        )
                    ),
                    self.check_conditions(
                        cond=all(
                            [
                                abs(data["historical_prices"]["1m"][last_key_1m]["rsi"] - 50) * data["historical_prices"]["1m"][last_key_1m]["minmax_volume"] > 10,
                                data["historical_prices"]["1m"][last_key_1m]["rsi"] < data["historical_prices"]["1m"][last_keys_1m[-2]]["rsi"]
                            ]
                        )
                    )
                )

                if resp1:
                    print("condition 1 satisfied")

                    # open position...
                    self.wallet.open_position(
                        side="BUY",
                        quantity=self.qty,
                        price=data["historical_prices"]["1s"][last_key_1s]["p"],
                        date=Data.to_datetime(data["historical_prices"]["1s"][last_key_1s]["t"]).strftime("%Y-%m-%d %H:%M:%S")
                    )

                    stop_loss = StopLoss(min(data["historical_prices"]["1m"][last_key_1m]["o"], data["historical_prices"]["1m"][last_key_1m]["c"]) - 3.)
                    trailing_stop = MyTrailingStop(data["historical_prices"]["1m"][last_key_1m]["c"] - 5.)

                    print(self.wallet.orders)

                    #Notification("bhaskan@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))
                    #Notification("oozlen@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))

                    self.write_to_excel()

                if resp2:
                    print("condition 2 satisfied")

                    # open position...
                    self.wallet.open_position(
                        side="SELL",
                        quantity=self.qty,
                        price=data["historical_prices"]["1s"][last_key_1s]["p"],
                        date=Data.to_datetime(data["historical_prices"]["1s"][last_key_1s]["t"]).strftime("%Y-%m-%d %H:%M:%S")
                    )

                    stop_loss = StopLoss(max(data["historical_prices"]["1m"][last_key_1m]["o"], data["historical_prices"]["1m"][last_key_1m]["c"]) + 3.)
                    trailing_stop = MyTrailingStop(data["historical_prices"]["1m"][last_key_1m]["c"] + 5.)

                    print(self.wallet.orders)

                    #Notification("bhaskan@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))
                    #Notification("oozlen@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))

                    self.write_to_excel()

            elif self.wallet.is_open():
                print("Waiting to close position", Data.to_datetime(data["current_date"]))

                if self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_LONG.value:

                    trailing_stop.update_stop(data["historical_prices"]["1m"][last_key_1m]["c"], Parameters.TYPE_LONG.value)
                    print("Current Stop:", trailing_stop.actual_stop())
                    
                    '''resp = await self.check_conditions(
                        cond=all(
                            [
                                abs(data["historical_prices"]["5m"][last_key]["rsi"] - 70) < 3.
                            ]
                        )
                    )'''

                    resp1, resp2 = await asyncio.gather(
                        self.check_conditions(
                            cond=all(
                                [
                                    trailing_stop.check_trigger(data["historical_prices"]["1s"][last_key_1s]["p"], Parameters.TYPE_LONG.value)
                                ]
                            ),
                            t=60
                        ),
                        self.check_conditions(
                            cond=all(
                                [
                                    #data["historical_prices"]["1s"][last_key_1s]["p"] < self.wallet.orders[self.wallet.INDEX]['Open'] - 5.,
                                    stop_loss.check_trigger(data["historical_prices"]["1s"][last_key_1s]["p"], Parameters.TYPE_LONG.value)
                                ]
                            )
                        )
                    )

                    if resp1:
                        print("Position closed")

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=data["historical_prices"]["1s"][last_key_1s]["p"],
                            date=Data.to_datetime(data["historical_prices"]["1s"][last_key_1s]["t"]).strftime("%Y-%m-%d %H:%M:%S")
                        )
                        print(self.wallet.orders)

                        #Notification("bhaskan@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))
                        #Notification("oozlen@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))

                        self.write_to_excel()
                    
                    elif resp2:
                        print("Stop Loss")

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=data["historical_prices"]["1s"][last_key_1s]["p"],
                            date=Data.to_datetime(data["historical_prices"]["1s"][last_key_1s]["t"]).strftime("%Y-%m-%d %H:%M:%S")
                        )
                        print(self.wallet.orders)

                        #Notification("bhaskan@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))
                        #Notification("oozlen@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))

                        self.write_to_excel()

                elif self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_SHORT.value:

                    trailing_stop.update_stop(data["historical_prices"]["1m"][last_key_1m]["c"], Parameters.TYPE_SHORT.value)
                    print("Current Stop:", trailing_stop.actual_stop())
                    
                    '''resp = await self.check_conditions(
                        cond=all(
                            [
                                abs(data["historical_prices"]["5m"][last_key]["rsi"] - 30) < 3.
                            ]
                        )
                    )'''

                    resp1, resp2 = await asyncio.gather(
                        self.check_conditions(
                            cond=all(
                                [
                                    trailing_stop.check_trigger(data["historical_prices"]["1s"][last_key_1s]["p"], Parameters.TYPE_SHORT.value)
                                ]
                            )
                        ),
                        self.check_conditions(
                            cond=all(
                                [
                                    #data["historical_prices"]["1s"][last_key_1s]["p"] > self.wallet.orders[self.wallet.INDEX]['Open'] + 5.,
                                    stop_loss.check_trigger(data["historical_prices"]["1s"][last_key_1s]["p"], Parameters.TYPE_SHORT.value)
                                ]
                            )
                        )
                    )

                    if resp1:
                        print("Position closed")
                        print("5m RSI:", data["historical_prices"]["5m"][last_key_5m]["rsi"])

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=data["historical_prices"]["1s"][last_key_1s]["p"],
                            date=Data.to_datetime(data["historical_prices"]["1s"][last_key_1s]["t"]).strftime("%Y-%m-%d %H:%M:%S")
                        )
                        print(self.wallet.orders)

                        #Notification("bhaskan@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))
                        #Notification("oozlen@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))

                        self.write_to_excel()

                    elif resp2:
                        print("Stop Loss")

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=data["historical_prices"]["1s"][last_key_1s]["p"],
                            date=Data.to_datetime(data["historical_prices"]["1s"][last_key_1s]["t"]).strftime("%Y-%m-%d %H:%M:%S")
                        )
                        print(self.wallet.orders)

                        #Notification("bhaskan@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))
                        #Notification("oozlen@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))

                        self.write_to_excel()

            with open(f"log.json", "w") as log:
                log.write(json.dumps(self.wallet.orders))