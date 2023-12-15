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

        #loop.run_until_complete(self.dummy_strategy(cond=True))
        loop.run_until_complete(
            asyncio.gather(
                self.memory.mem(),
                self.strategy_2_DEV()
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

    async def check_conditions(self, cond, t=10):
        
        await asyncio.sleep(t)

        if cond:
            return True
        else:
            return False

    async def check_event(self, event: asyncio.Event, t=10):

        while True:

            await asyncio.sleep(t)

            data = self.read_memory()

            if data["current_state"]["rsi-5m"] < 68:
                event.set()
                break

    async def check_event_is_order_filled(self, event: asyncio.Event, t=10):

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

    async def check_event_reset_conditions(self, event: asyncio.Event, t=10):

        while True:

            data = self.read_memory()

            await asyncio.sleep(t)

            if self.TEST_MODE:
                event.set()
                break

            else:
                if self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_LONG.value:
                    if not data["current_state"]["rsi-5m"] < (30 + 3.):
                        event.set()
                        break

                if self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_SHORT.value:
                    if not data["current_state"]["rsi-5m"] > (70 - 3.):
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
            last_key_5m = list(data["historical_prices"]["5m"].keys())[-1]

            print("RSI 1m", data["historical_prices"]["1m"][last_key_1m]["rsi"])
            print("RSI 5m", data["historical_prices"]["5m"][last_key_5m]["rsi"])
            print("realtime RSI 5m", data["current_state"]["rsi-5m"])

            '''await self.check_conditions(
                cond=all([
                    abs(data["current_state"]["rsi-1m"] - 50) < 10
                ])
            )'''

            #event = asyncio.Event()

            '''await asyncio.gather(
                event.wait(),
                self.generate_event(event=event)
            )'''

            await asyncio.gather(
                event.wait(),
                self.check_event(
                    event=event,
                    t=1
                    )
            )

            event.clear()


            print("it is OK.")

    async def dummy_strategy(self, cond=False):
        # WORKING ON STOP_LOSS

        while True:

            data = self.read_memory()

            last_key = list(data["historical_prices"]["1m"].keys())[-1]
            last_key_1s = list(data["historical_prices"]["1s"].keys())[-1]

            global event

            print("actual price:", data["historical_prices"]["1s"][last_key_1s]["c"])

            if not self.wallet.is_open():
                time.sleep(5)
                print("Waiting to open position", Data.to_datetime(data["current_date"]))

                self.wallet.open_position(
                    side="BUY",
                    quantity=self.qty,
                    price=data["historical_prices"]["1m"][last_key]["c"],
                    date=Data.to_datetime(data["historical_prices"]["1m"][last_key]["t"]).strftime("%Y-%m-%d %H:%M:%S"),
                    #type=Client.FUTURE_ORDER_TYPE_LIMIT
                )
                
                stop_loss = StopLoss(max(data["historical_prices"]["1m"][last_key]["o"], data["historical_prices"]["1m"][last_key]["c"]) - 5.)
                trailing_stop = MyTrailingStop(data["historical_prices"]["1m"][last_key]["c"] - 2.)

                print(self.wallet.orders)

                #event = asyncio.Event()
                await asyncio.gather(
                    event.wait(),
                    self.check_event_is_order_filled(
                        event=event,
                        t=1
                    )
                )
                event.clear()

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

                pass

            elif self.wallet.is_open():

                # Calculate PNL %
                if self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_LONG.value:
                    profit_percent = 100 * (data["historical_prices"]["1s"][last_key_1s]["c"] - self.wallet.orders[self.wallet.INDEX]["Open"]) * float(Parameters.INDEX_POINT.value) / self.wallet.orders[self.wallet.INDEX]["Open"]
                elif self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_SHORT.value:
                    profit_percent = 100 * (self.wallet.orders[self.wallet.INDEX]["Open"] - data["historical_prices"]["1s"][last_key_1s]["c"]) * float(Parameters.INDEX_POINT.value) / self.wallet.orders[self.wallet.INDEX]["Open"]

                print("profit percent:", profit_percent)

                if self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_LONG.value:

                    trailing_stop.update_stop(data["historical_prices"]["1m"][last_key]["c"], Parameters.TYPE_LONG.value)
                    
                    #time.sleep(10)

                    '''stop_loss = await self.check_conditions(
                        cond=all(
                            [
                                self.wallet.stop_loss_2(data["historical_prices"]["1m"][last_key]["c"], 0.04) #previous_key?
                            ]
                        )
                    )'''

                    resp1, resp2 = await asyncio.gather(
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
                    )

                    if resp2:
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
                        
                        print(self.wallet.orders)
                        
                    elif resp1:
                        print("Trailing Stop")

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

    async def strategy_1(self):

        while True:

            data = self.read_memory()

            last_key = list(data["historical_prices"]["1m"].keys())[-1]

            if not self.wallet.is_open():
                #print("Waiting to open position")
                print("Waiting to open position", Data.to_datetime(data["current_date"]))

                resp1, resp2 = await asyncio.gather(
                    self.check_conditions(
                        cond=all(
                            [
                                data["historical_prices"]["1m"][last_key]["rsi"] >= (70 - 3),
                                data["historical_prices"]["1m"][last_key]["normalized_volume"] >= 25.,
                            ]
                        )
                    ),
                    self.check_conditions(
                        cond=all(
                            [
                                data["historical_prices"]["1m"][last_key]["rsi"] <= (30 + 3),
                                data["historical_prices"]["1m"][last_key]["normalized_volume"] >= 25.,
                            ]
                        )
                    )
                )

                if resp1:
                    print("condition 1 satisfied")
                    print("RSI:", data["historical_prices"]["1m"][last_key]["rsi"])
                    print("Volume:", data["historical_prices"]["1m"][last_key]["v"])

                    # open position...
                    self.wallet.open_position(
                        side="BUY",
                        quantity=self.qty,
                        price=data["historical_prices"]["1m"][last_key]["c"],
                        date=data["historical_prices"]["1m"][last_key]["t"]
                    )
                    print(self.wallet.orders)

                if resp2:
                    print("condition 2 satisfied")
                    print("RSI:", data["historical_prices"]["1m"][last_key]["rsi"])
                    print("Volume:", data["historical_prices"]["1m"][last_key]["v"])

                    # open position...
                    self.wallet.open_position(
                        side="SELL",
                        quantity=self.qty,
                        price=data["historical_prices"]["1m"][last_key]["c"],
                        date=data["historical_prices"]["1m"][last_key]["t"]
                    )
                    print(self.wallet.orders)

            elif self.wallet.is_open():
                print("Waiting to close position")

                # check the COMMON condition for close:
                resp = await self.check_conditions(
                    cond=all(
                        [
                            data["historical_prices"]["1m"][last_key]["normalized_volume"] < 40.
                        ]
                    )
                )

                if self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_LONG.value:
                    # work on trailing stop...

                    if  resp:
                        print("Position closed")

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=data["historical_prices"]["1m"][last_key]["c"],
                            date=data["historical_prices"]["1m"][last_key]["t"]
                        )
                        print(self.wallet.orders)
                    
                    else:
                        # stop loss...
                        pass

                elif self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_SHORT.value:
                    
                    if resp:
                        print("Position closed")

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=data["historical_prices"]["1m"][last_key]["c"],
                            date=data["historical_prices"]["1m"][last_key]["t"]
                        )
                        print(self.wallet.orders)

                    else:
                        # stop loss...
                        pass
        
            with open(f"log.json", "w") as log:
                log.write(json.dumps(self.wallet.orders))

    async def strategy_2_5min(self):

        while True:

            data = self.read_memory()

            last_key = list(data["historical_prices"]["5m"].keys())[-1]

            last_5_keys = [
                list(data["historical_prices"]["5m"].keys())[-5],
                list(data["historical_prices"]["5m"].keys())[-4],
                list(data["historical_prices"]["5m"].keys())[-3],
                list(data["historical_prices"]["5m"].keys())[-2],
                list(data["historical_prices"]["5m"].keys())[-1]
            ]

            if not self.wallet.is_open():
                #print("Waiting to open position")
                print("Waiting to open position", Data.to_datetime(data["current_date"]))

                resp1, resp2 = await asyncio.gather(
                    self.check_conditions(
                        cond=all(
                            [
                                abs(data["historical_prices"]["5m"][last_key]["rsi"] - 70.) < 4.,
                                data["historical_prices"]["5m"][last_key]["normalized_volume"] <= 25.,
                            ]
                        )
                    ),
                    self.check_conditions(
                        cond=all(
                            [
                                abs(data["historical_prices"]["5m"][last_key]["rsi"] - 30.) < 4.,
                                data["historical_prices"]["5m"][last_key]["normalized_volume"] <= 25.,
                            ]
                        )
                    )
                )

                if resp1:
                    print("condition 1 satisfied")
                    print("RSI:", data["historical_prices"]["5m"][last_key]["rsi"])
                    print("Volume:", data["historical_prices"]["5m"][last_key]["v"])

                    # open position...
                    self.wallet.open_position(
                        side="SELL",
                        #quantity=1,
                        quantity=self.qty,
                        price=data["historical_prices"]["5m"][last_key]["c"],
                        date=data["historical_prices"]["5m"][last_key]["t"]
                    )
                    print(self.wallet.orders)

                if resp2:
                    print("condition 2 satisfied")
                    print("RSI:", data["historical_prices"]["5m"][last_key]["rsi"])
                    print("Volume:", data["historical_prices"]["5m"][last_key]["v"])

                    # open position...
                    self.wallet.open_position(
                        side="BUY",
                        #quantity=1,
                        quantity=self.qty,
                        price=data["historical_prices"]["5m"][last_key]["c"],
                        date=data["historical_prices"]["5m"][last_key]["t"]
                    )
                    print(self.wallet.orders)

            elif self.wallet.is_open():
                print("Waiting to close position")

                if self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_LONG.value:
                    
                    '''resp = await self.check_conditions(
                        cond=all(
                            [
                                abs(data["historical_prices"]["5m"][last_key]["rsi"] - 70) < 3.
                            ]
                        )
                    )'''

                    resp, stop_loss = await asyncio.gather(
                        self.check_conditions(
                            cond=all(
                                [
                                    abs(data["historical_prices"]["5m"][last_key]["rsi"] - 70) < 3.
                                ]
                            )
                        ),
                        self.check_conditions(
                            cond=all(
                                [
                                    #self.wallet.stop_loss_2(data["historical_prices"]["5m"][last_key]["c"], 0.15),
                                    data["historical_prices"]["5m"][last_key]["c"] <= min( data["historical_prices"]["5m"][key]["l"] for key in last_5_keys )
                                ]
                            )
                        )
                    )

                    if resp:
                        print("Position closed")

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=data["historical_prices"]["5m"][last_key]["c"],
                            date=data["historical_prices"]["5m"][last_key]["t"]
                        )
                        print(self.wallet.orders)
                    
                    elif stop_loss:
                        print("Stop Loss")

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=data["historical_prices"]["5m"][last_key]["c"],
                            date=data["historical_prices"]["5m"][last_key]["t"]
                        )
                        print(self.wallet.orders)

                elif self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_SHORT.value:
                    
                    '''resp = await self.check_conditions(
                        cond=all(
                            [
                                abs(data["historical_prices"]["5m"][last_key]["rsi"] - 30) < 3.
                            ]
                        )
                    )'''

                    resp, stop_loss = await asyncio.gather(
                        self.check_conditions(
                            cond=all(
                                [
                                    abs(data["historical_prices"]["5m"][last_key]["rsi"] - 70) < 3.
                                ]
                            )
                        ),
                        self.check_conditions(
                            cond=all(
                                [
                                    #self.wallet.stop_loss_2(data["historical_prices"]["5m"][last_key]["c"], 0.15),
                                    data["historical_prices"]["5m"][last_key]["c"] >= max( data["historical_prices"]["5m"][key]["h"] for key in last_5_keys )
                                ]
                            )
                        )
                    )

                    if resp:
                        print("Position closed")

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=data["historical_prices"]["5m"][last_key]["c"],
                            date=data["historical_prices"]["5m"][last_key]["t"]
                        )
                        print(self.wallet.orders)

                    elif stop_loss:
                        print("Stop Loss")

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=data["historical_prices"]["5m"][last_key]["c"],
                            date=data["historical_prices"]["5m"][last_key]["t"]
                        )
                        print(self.wallet.orders)

            with open(f"log.json", "w") as log:
                log.write(json.dumps(self.wallet.orders))

    ''' TRAILING TESTS: '''
    async def strategy_1_trailing(self):

        while True:

            data = self.read_memory()

            last_key = list(data["historical_prices"]["1m"].keys())[-1]
            previous_key = list(data["historical_prices"]["1m"].keys())[-2]

            if not self.wallet.is_open():
                #print("Waiting to open position")
                print("Waiting to open position", Data.to_datetime(data["current_date"]))

                resp1, resp2 = await asyncio.gather(
                    self.check_conditions(
                        cond=all(
                            [
                                data["historical_prices"]["1m"][last_key]["rsi"] >= (70 - 3),
                                data["historical_prices"]["1m"][last_key]["normalized_volume"] >= 25.,
                            ]
                        )
                    ),
                    self.check_conditions(
                        cond=all(
                            [
                                data["historical_prices"]["1m"][last_key]["rsi"] <= (30 + 3),
                                data["historical_prices"]["1m"][last_key]["normalized_volume"] >= 25.,
                            ]
                        )
                    )
                )

                if resp1:
                    print("condition 1 satisfied")
                    print("RSI:", data["historical_prices"]["1m"][last_key]["rsi"])
                    print("Volume:", data["historical_prices"]["1m"][last_key]["v"])

                    # open position...
                    self.wallet.open_position(
                        side="BUY",
                        #quantity=1,
                        quantity=self.qty,
                        price=data["historical_prices"]["1m"][last_key]["c"],
                        date=data["historical_prices"]["1m"][last_key]["t"]
                    )
                    print(self.wallet.orders)

                if resp2:
                    print("condition 2 satisfied")
                    print("RSI:", data["historical_prices"]["1m"][last_key]["rsi"])
                    print("Volume:", data["historical_prices"]["1m"][last_key]["v"])

                    # open position...
                    self.wallet.open_position(
                        side="SELL",
                        #quantity=1,
                        quantity=self.qty,
                        price=data["historical_prices"]["1m"][last_key]["c"],
                        date=data["historical_prices"]["1m"][last_key]["t"]
                    )
                    print(self.wallet.orders)

            elif self.wallet.is_open():
                print("Waiting to close position")

                # check the COMMON condition for close:
                '''resp = await self.check_conditions(
                    cond=all(
                        [
                            data["historical_prices"]["1m"][last_key]["normalized_volume"] < 40.
                        ]
                    )
                )'''

                if self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_LONG.value:
                    # work on trailing stop...

                    actual_profit = data["historical_prices"]["1m"][last_key]["c"] - self.wallet.orders[self.wallet.INDEX]["Open"]
                    previous_profit = data["historical_prices"]["1m"][previous_key]["c"] - self.wallet.orders[self.wallet.INDEX]["Open"]

                    '''resp = await self.check_conditions(
                        cond=all(
                            [
                                actual_profit > 0,
                                actual_profit < 0.7 * previous_profit
                            ]
                        )
                    )'''

                    resp, stop_loss = await asyncio.gather(
                        self.check_conditions(
                            cond=all(
                                [
                                    actual_profit > 0,
                                    actual_profit < 0.7 * previous_profit
                                ]
                            )
                        ),
                        self.check_conditions(
                            cond=all(
                                [
                                    self.wallet.stop_loss_2(data["historical_prices"]["1m"][last_key]["c"], 0.15) #previous_key?
                                ]
                            )
                        )
                    )

                    if resp:
                        print("Position closed")

                        self.wallet.close_position(
                            side="SELL",
                            #quantity=1,
                            quantity=self.qty,
                            price=data["historical_prices"]["1m"][last_key]["c"],
                            date=data["historical_prices"]["1m"][last_key]["t"]
                        )
                        print(self.wallet.orders)
                    
                    elif stop_loss:
                        print("Stop Loss")

                        self.wallet.close_position(
                            side="SELL",
                            #quantity=1,
                            quantity=self.qty,
                            price=data["historical_prices"]["1m"][last_key]["c"],
                            date=data["historical_prices"]["1m"][last_key]["t"]
                        )
                        print(self.wallet.orders)

                elif self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_SHORT.value:

                    actual_profit = self.wallet.orders[self.wallet.INDEX]["Open"] - data["historical_prices"]["1m"][last_key]["c"]
                    previous_profit = self.wallet.orders[self.wallet.INDEX]["Open"] - data["historical_prices"]["1m"][previous_key]["c"]
                    
                    '''resp = await self.check_conditions(
                        cond=all(
                            [
                                actual_profit > 0,
                                actual_profit < 0.7 * previous_profit
                            ]
                        )
                    )'''

                    resp, stop_loss = await asyncio.gather(
                        self.check_conditions(
                            cond=all(
                                [
                                    actual_profit > 0,
                                    actual_profit < 0.7 * previous_profit
                                ]
                            )
                        ),
                        self.check_conditions(
                            cond=all(
                                [
                                    self.wallet.stop_loss_2(data["historical_prices"]["1m"][last_key]["c"], 0.15) #previous_key?
                                ]
                            )
                        )
                    )
                    
                    if resp:
                        print("Position closed")

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=data["historical_prices"]["1m"][last_key]["c"],
                            date=data["historical_prices"]["1m"][last_key]["t"]
                        )
                        print(self.wallet.orders)

                    elif stop_loss:
                        print("Stop Loss")

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=data["historical_prices"]["1m"][last_key]["c"],
                            date=data["historical_prices"]["1m"][last_key]["t"]
                        )
                        print(self.wallet.orders)
        
            with open(f"log.json", "w") as log:
                log.write(json.dumps(self.wallet.orders))

    async def strategy_2_5min_trailing(self):

        while True:

            data = self.read_memory()

            last_key = list(data["historical_prices"]["5m"].keys())[-1]
            previous_key = list(data["historical_prices"]["5m"].keys())[-2]

            if not self.wallet.is_open():
                #print("Waiting to open position")
                print("Waiting to open position", Data.to_datetime(data["current_date"]))

                resp1, resp2 = await asyncio.gather(
                    self.check_conditions(
                        cond=all(
                            [
                                abs(data["historical_prices"]["5m"][last_key]["rsi"] - 70.) < 4.,
                                data["historical_prices"]["5m"][last_key]["normalized_volume"] <= 25.,
                            ]
                        )
                    ),
                    self.check_conditions(
                        cond=all(
                            [
                                abs(data["historical_prices"]["5m"][last_key]["rsi"] - 30.) < 4.,
                                data["historical_prices"]["5m"][last_key]["normalized_volume"] <= 25.,
                            ]
                        )
                    )
                )

                if resp1:
                    print("condition 1 satisfied")
                    print("RSI:", data["historical_prices"]["5m"][last_key]["rsi"])
                    print("Volume:", data["historical_prices"]["5m"][last_key]["v"])

                    # open position...
                    self.wallet.open_position(
                        side="SELL",
                        #quantity=1,
                        quantity=self.qty,
                        price=data["historical_prices"]["5m"][last_key]["c"],
                        date=data["historical_prices"]["5m"][last_key]["t"]
                    )
                    print(self.wallet.orders)

                if resp2:
                    print("condition 2 satisfied")
                    print("RSI:", data["historical_prices"]["5m"][last_key]["rsi"])
                    print("Volume:", data["historical_prices"]["5m"][last_key]["v"])

                    # open position...
                    self.wallet.open_position(
                        side="BUY",
                        #quantity=1,
                        quantity=self.qty,
                        price=data["historical_prices"]["5m"][last_key]["c"],
                        date=data["historical_prices"]["5m"][last_key]["t"]
                    )
                    print(self.wallet.orders)

            elif self.wallet.is_open():
                print("Waiting to close position")

                if self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_LONG.value:

                    actual_profit = data["historical_prices"]["5m"][last_key]["c"] - self.wallet.orders[self.wallet.INDEX]["Open"]
                    previous_profit = data["historical_prices"]["5m"][previous_key]["c"] - self.wallet.orders[self.wallet.INDEX]["Open"]
                    
                    '''resp = await self.check_conditions(
                        cond=all(
                            [
                                actual_profit > 0,
                                actual_profit < 0.7 * previous_profit
                            ]
                        )
                    )'''

                    resp, stop_loss = await asyncio.gather(
                        self.check_conditions(
                            cond=all(
                                [
                                    actual_profit > 0,
                                    actual_profit < 0.7 * previous_profit
                                ]
                            )
                        ),
                        self.check_conditions(
                            cond=all(
                                [
                                    self.wallet.stop_loss_2(data["historical_prices"]["5m"][last_key]["c"], 0.15) #previous_key?
                                ]
                            )
                        )
                    )

                    if resp:
                        print("Position closed")

                        self.wallet.close_position(
                            side="SELL",
                            #quantity=1,
                            quantity=self.qty,
                            price=data["historical_prices"]["5m"][last_key]["c"],
                            date=data["historical_prices"]["5m"][last_key]["t"]
                        )
                        print(self.wallet.orders)

                    elif stop_loss:
                        print("Stop Loss")

                        self.wallet.close_position(
                            side="SELL",
                            #quantity=1,
                            quantity=self.qty,
                            price=data["historical_prices"]["5m"][last_key]["c"],
                            date=data["historical_prices"]["5m"][last_key]["t"]
                        )
                        print(self.wallet.orders)

                elif self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_SHORT.value:

                    actual_profit = self.wallet.orders[self.wallet.INDEX]["Open"] - data["historical_prices"]["5m"][last_key]["c"]
                    previous_profit = self.wallet.orders[self.wallet.INDEX]["Open"] - data["historical_prices"]["5m"][previous_key]["c"]
                    
                    '''resp = await self.check_conditions(
                        cond=all(
                            [
                                actual_profit > 0,
                                actual_profit < 0.7 * previous_profit
                            ]
                        )
                    )'''

                    resp, stop_loss = await asyncio.gather(
                        self.check_conditions(
                            cond=all(
                                [
                                    actual_profit > 0,
                                    actual_profit < 0.7 * previous_profit
                                ]
                            )
                        ),
                        self.check_conditions(
                            cond=all(
                                [
                                    self.wallet.stop_loss_2(data["historical_prices"]["5m"][last_key]["c"], 0.15) #previous_key?
                                ]
                            )
                        )
                    )

                    if resp:
                        print("Position closed")

                        self.wallet.close_position(
                            side="BUY",
                            #quantity=1,
                            quantity=self.qty,
                            price=data["historical_prices"]["5m"][last_key]["c"],
                            date=data["historical_prices"]["5m"][last_key]["t"]
                        )
                        print(self.wallet.orders)

                    elif stop_loss:
                        print("Stop Loss")

                        self.wallet.close_position(
                            side="BUY",
                            #quantity=1,
                            quantity=self.qty,
                            price=data["historical_prices"]["5m"][last_key]["c"],
                            date=data["historical_prices"]["5m"][last_key]["t"]
                        )
                        print(self.wallet.orders)

            with open(f"log.json", "w") as log:
                log.write(json.dumps(self.wallet.orders))

    ''' 10s TESTS: '''
    async def strategy_10s(self):

        while True:

            data = self.read_memory()

            last_key = list(data["historical_prices"]["10s"].keys())[-1]
            previous_key = list(data["historical_prices"]["10s"].keys())[-2]

            if not self.wallet.is_open():
                print("Waiting to open position", Data.to_datetime(data["current_date"]))

                print(data["historical_prices"]["10s"][last_key]["normalized_volume"])
                
                resp1, resp2 = await asyncio.gather(
                    self.check_conditions(
                        cond=all(
                            [
                                data["historical_prices"]["10s"][last_key]["rsi"] >= (70 - 3),
                                data["historical_prices"]["10s"][last_key]["normalized_volume"] >= 20.,
                            ]
                        )
                    ),
                    self.check_conditions(
                        cond=all(
                            [
                                data["historical_prices"]["10s"][last_key]["rsi"] <= (30 + 3),
                                data["historical_prices"]["10s"][last_key]["normalized_volume"] >= 20.,
                            ]
                        )
                    )
                )

                if resp1:
                    print("condition 1 satisfied")
                    print("RSI:", data["historical_prices"]["10s"][last_key]["rsi"])
                    print("Volume:", data["historical_prices"]["10s"][last_key]["v"])

                    # open position...
                    self.wallet.open_position(
                        side="BUY",
                        quantity=self.qty,
                        price=data["historical_prices"]["10s"][last_key]["c"],
                        date=data["historical_prices"]["10s"][last_key]["t"]
                    )
                    print(self.wallet.orders)

                if resp2:
                    print("condition 2 satisfied")
                    print("RSI:", data["historical_prices"]["10s"][last_key]["rsi"])
                    print("Volume:", data["historical_prices"]["10s"][last_key]["v"])

                    # open position...
                    self.wallet.open_position(
                        side="SELL",
                        quantity=self.qty,
                        price=data["historical_prices"]["10s"][last_key]["c"],
                        date=data["historical_prices"]["10s"][last_key]["t"]
                    )
                    print(self.wallet.orders)

            elif self.wallet.is_open():
                print("Waiting to close position")

                if self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_LONG.value:
                    
                    actual_profit = data["historical_prices"]["10s"][last_key]["c"] - self.wallet.orders[self.wallet.INDEX]["Open"]
                    previous_profit = data["historical_prices"]["10s"][previous_key]["c"] - self.wallet.orders[self.wallet.INDEX]["Open"]

                    resp, stop_loss = await asyncio.gather(
                        self.check_conditions(
                            cond=all(
                                [
                                    actual_profit > 0,
                                    actual_profit < 0.7 * previous_profit
                                ]
                            )
                        ),
                        self.check_conditions(
                            cond=all(
                                [
                                    self.wallet.stop_loss_2(data["historical_prices"]["10s"][last_key]["c"], 0.1) #previous_key?
                                ]
                            )
                        )
                    )

                    if resp:
                        print("Position closed")

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=data["historical_prices"]["10s"][last_key]["c"],
                            date=data["historical_prices"]["10s"][last_key]["t"]
                        )
                        print(self.wallet.orders)
                    
                    elif stop_loss:
                        print("Stop Loss")

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=data["historical_prices"]["10s"][last_key]["c"],
                            date=data["historical_prices"]["10s"][last_key]["t"]
                        )
                        print(self.wallet.orders)

                elif self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_SHORT.value:
                    
                    actual_profit = self.wallet.orders[self.wallet.INDEX]["Open"] - data["historical_prices"]["10s"][last_key]["c"]
                    previous_profit = self.wallet.orders[self.wallet.INDEX]["Open"] - data["historical_prices"]["10s"][previous_key]["c"]

                    resp, stop_loss = await asyncio.gather(
                        self.check_conditions(
                            cond=all(
                                [
                                    actual_profit > 0,
                                    actual_profit < 0.7 * previous_profit
                                ]
                            )
                        ),
                        self.check_conditions(
                            cond=all(
                                [
                                    self.wallet.stop_loss_2(data["historical_prices"]["10s"][last_key]["c"], 0.1)
                                ]
                            )
                        )
                    )

                    if resp:
                        print("Position closed")

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=data["historical_prices"]["10s"][last_key]["c"],
                            date=data["historical_prices"]["10s"][last_key]["t"]
                        )
                        print(self.wallet.orders)

                    elif stop_loss:
                        print("Stop Loss")

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=data["historical_prices"]["10s"][last_key]["c"],
                            date=data["historical_prices"]["10s"][last_key]["t"]
                        )
                        print(self.wallet.orders)
        
            with open(f"log.json", "w") as log:
                log.write(json.dumps(self.wallet.orders))

    '''LIVE STRATEGIES'''
    async def strategy_2_DEV(self):

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

            if not self.wallet.is_open():
                #print("Waiting to open position")
                print("Waiting to open position", Data.to_datetime(data["current_date"]))
                #print("1m RSI:", data["historical_prices"]["1m"][last_key_1m]["rsi"])
                print("realtime 1m RSI:", data["current_state"]["rsi-1m"])
                #print("5m RSI:", data["historical_prices"]["5m"][last_key_5m]["rsi"])
                print("realtime 5m RSI:", data["current_state"]["rsi-5m"])
                print("normalized volume 1m:", data["historical_prices"]["1m"][last_key_1m]["normalized_volume"])
                print("normalized volume 5m:", data["historical_prices"]["5m"][last_key_5m]["normalized_volume"])

                resp1, resp2 = await asyncio.gather(
                    self.check_conditions(
                        cond=all(
                            [
                                #not abs(data["historical_prices"]["1m"][last_key_1m]["rsi"] - 70.) < 4.,
                                not data["current_state"]["rsi-1m"] > (70 - 0.),
                                data["historical_prices"]["1m"][last_key_1m]["normalized_volume"] <= 0.5,
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
                                data["historical_prices"]["1m"][last_key_1m]["normalized_volume"] <= 0.5,
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

                    # open position...
                    self.wallet.open_position(
                        side="SELL",
                        quantity=self.qty,
                        price=data["historical_prices"]["1m"][last_key_1m]["c"],
                        date=Data.to_datetime(data["historical_prices"]["1m"][last_key_1m]["t"]).strftime("%Y-%m-%d %H:%M:%S")
                        #type=Client.FUTURE_ORDER_TYPE_LIMIT
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
                
                    await asyncio.gather(
                        event.wait(),
                        self.check_event_is_order_filled(
                            event=event,
                            t=1
                        )
                    )
                    event.clear()

                    stop_loss = StopLoss(max(data["historical_prices"]["1m"][last_key_1m]["o"], data["historical_prices"]["1m"][last_key_1m]["c"]) + 5.)
                    take_profit = TakeProfit(data["historical_prices"]["1m"][last_key_1m]["c"] - 9.)

                    print(self.wallet.orders)

                    Notification("bhaskan@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))
                    #Notification("oozlen@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))

                    self.write_to_excel()

                if resp2:
                    print("condition 2 satisfied")
                    print("1m RSI:", data["current_state"]["rsi-1m"])
                    print("5m RSI:", data["current_state"]["rsi-5m"])
                    print("1m Volume:", data["historical_prices"]["1m"][last_key_1m]["normalized_volume"])

                    # open position...
                    self.wallet.open_position(
                        side="BUY",
                        quantity=self.qty,
                        price=data["historical_prices"]["1m"][last_key_1m]["c"],
                        date=Data.to_datetime(data["historical_prices"]["1m"][last_key_1m]["t"]).strftime("%Y-%m-%d %H:%M:%S")
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

                    stop_loss = StopLoss(min(data["historical_prices"]["1m"][last_key_1m]["o"], data["historical_prices"]["1m"][last_key_1m]["c"]) - 5.)
                    take_profit = TakeProfit(data["historical_prices"]["1m"][last_key_1m]["c"] + 9.)

                    print(self.wallet.orders)

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
                    profit_percent = 100 * (data["historical_prices"]["1s"][last_key_1s]["c"] - self.wallet.orders[self.wallet.INDEX]["Open"]) * float(Parameters.INDEX_POINT.value) / self.wallet.orders[self.wallet.INDEX]["Open"]
                elif self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_SHORT.value:
                    profit_percent = 100 * (self.wallet.orders[self.wallet.INDEX]["Open"] - data["historical_prices"]["1s"][last_key_1s]["c"]) * float(Parameters.INDEX_POINT.value) / self.wallet.orders[self.wallet.INDEX]["Open"]

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
                                    #take_profit.check_trigger(data["historical_prices"]["1s"][last_key_1s]["c"], Parameters.TYPE_LONG.value) or abs(data["current_state"]["rsi-1m"] - 70) < 5.
                                    profit_percent >= 9. / 20.
                                ]
                            )
                        ),
                        self.check_conditions(
                            cond=all(
                                [
                                    stop_loss.check_trigger(data["historical_prices"]["1s"][last_key_1s]["c"], Parameters.TYPE_LONG.value),
                                    #data["historical_prices"]["1s"][last_key_1s]["c"] < self.wallet.orders[self.wallet.INDEX]['Open'] - 5.,
                                    #data["historical_prices"]["5m"][last_key_5m]["c"] <= min( data["historical_prices"]["5m"][key]["l"] for key in last_keys_5m )
                                ]
                            )
                        )
                    )

                    if resp1:
                        print("Position closed")
                        print("5m RSI:", data["historical_prices"]["5m"][last_key_5m]["rsi"])

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=data["historical_prices"]["1m"][last_key_1m]["c"],
                            date=Data.to_datetime(data["historical_prices"]["1m"][last_key_1m]["t"]).strftime("%Y-%m-%d %H:%M:%S")
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

                        Notification("bhaskan@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))
                        #Notification("oozlen@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))

                        self.write_to_excel()
                    
                    elif resp2:
                        print("Stop Loss")

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=data["historical_prices"]["1m"][last_key_1m]["c"],
                            date=Data.to_datetime(data["historical_prices"]["1m"][last_key_1m]["t"]).strftime("%Y-%m-%d %H:%M:%S")
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

                        Notification("bhaskan@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))
                        #Notification("oozlen@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))

                        self.write_to_excel()

                        
                        await asyncio.gather(
                            event.wait(),
                            self.check_event_reset_conditions(
                                event=event,
                                t=1
                            )
                        )
                        event.clear()

                        '''event2 = asyncio.Event()
                        await asyncio.gather(
                            event2.wait(),
                            self.check_event(
                                cond=all(
                                            [
                                                #not data["historical_prices"]["5m"][last_key_5m]["rsi"] < (30 + 3.)
                                                not data["historical_prices"]["5m"][last_key_5m]["rsi"] < (50 + 3.)
                                            ]
                                        ),
                                event=event2,
                                t=5
                            )
                        )'''

                        '''await self.check_conditions(
                            cond=all([
                                abs(data["current_state"]["rsi-1m"] - 50) < 10
                            ])
                        )'''

                        '''await self.check_conditions(
                            cond=all([
                                not data["historical_prices"]["5m"][last_key_5m]["rsi"] < (30 + 3.)
                            ])
                        )'''

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
                                    #take_profit.check_trigger(data["historical_prices"]["1s"][last_key_1s]["c"], Parameters.TYPE_SHORT.value) or abs(data["current_state"]["rsi-1m"] - 30) < 5.
                                    profit_percent >= 9. / 20.
                                ]
                            )
                        ),
                        self.check_conditions(
                            cond=all(
                                [
                                    stop_loss.check_trigger(data["historical_prices"]["1s"][last_key_1s]["c"], Parameters.TYPE_SHORT.value),
                                    #data["historical_prices"]["1s"][last_key_1s]["c"] > self.wallet.orders[self.wallet.INDEX]['Open'] + 5.,
                                    #data["historical_prices"]["5m"][last_key_5m]["c"] >= max( data["historical_prices"]["5m"][key]["h"] for key in last_keys_5m )
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
                            price=data["historical_prices"]["1m"][last_key_1m]["c"],
                            date=Data.to_datetime(data["historical_prices"]["1m"][last_key_1m]["t"]).strftime("%Y-%m-%d %H:%M:%S")
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

                        Notification("bhaskan@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))
                        #Notification("oozlen@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))

                        self.write_to_excel()

                    elif resp2:
                        print("Stop Loss")

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=data["historical_prices"]["1m"][last_key_1m]["c"],
                            date=Data.to_datetime(data["historical_prices"]["1m"][last_key_1m]["t"]).strftime("%Y-%m-%d %H:%M:%S")
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

                        Notification("bhaskan@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))
                        #Notification("oozlen@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))

                        self.write_to_excel()

                        await asyncio.gather(
                            event.wait(),
                            self.check_event_reset_conditions(
                                event=event,
                                t=1
                            )
                        )
                        event.clear()

                        '''event2 = asyncio.Event()
                        await asyncio.gather(
                            event2.wait(),
                            self.check_event(
                                cond=all(
                                            [
                                                #not data["historical_prices"]["5m"][last_key_5m]["rsi"] > (70 - 3.)
                                                not data["historical_prices"]["5m"][last_key_5m]["rsi"] > (50 - 3.)
                                            ]
                                        ),
                                event=event2,
                                t=5
                            )
                        )'''

                        '''await self.check_conditions(
                            cond=all([
                                abs(data["current_state"]["rsi-1m"] - 50) < 10
                            ])
                        )'''

                        '''await self.check_conditions(
                            cond=all([
                                not data["historical_prices"]["5m"][last_key_5m]["rsi"] > (70 - 3.)
                            ])
                        )'''

            with open(f"log.json", "w") as log:
                log.write(json.dumps(self.wallet.orders))

    async def strategy_2_diff_DEV(self):

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
                                data["historical_prices"]["15m"][last_key_15m]["rsi"] > (74 - 3.),
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
                                data["historical_prices"]["15m"][last_key_15m]["rsi"] < (26 + 3.),
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

                    # to correct:
                    event0 = asyncio.Event()
                    await asyncio.gather(
                        event0.wait(),
                        self.check_event(
                            cond=all(
                                        [
                                            data["current_state"]["rsi-15m"] - data["historical_prices"]["15m"][last_key_15m]["rsi"] < 0.
                                        ]
                                    ),
                            event=event0,
                            t=1
                        )
                    )

                    '''await self.check_conditions(
                            cond=all([
                                data["current_state"]["rsi-5m"] - data["historical_prices"]["5m"][last_key_5m]["rsi"] < 0.
                            ])
                        )'''

                    # open position...
                    self.wallet.open_position(
                        side="SELL",
                        quantity=self.qty,
                        price=data["historical_prices"]["1s"][last_key_1s]["c"],
                        date=Data.to_datetime(data["historical_prices"]["1s"][last_key_1s]["t"]).strftime("%Y-%m-%d %H:%M:%S")
                        #type=Client.FUTURE_ORDER_TYPE_LIMIT
                    )

                    event = asyncio.Event()
                    await asyncio.gather(
                        event.wait(),
                        self.check_event(
                            cond=all(
                                        [
                                            self.wallet.binance.client.futures_get_order(
                                                symbol=self.wallet.orders[self.wallet.INDEX]['Symbol'],
                                                orderId=self.wallet.orders[self.wallet.INDEX]['IdOpen']
                                                )['status'] == 'FILLED'
                                        ]
                                    ),
                            event=event,
                            t=1
                        )
                    )

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

                    # to correct:
                    event0 = asyncio.Event()
                    await asyncio.gather(
                        event0.wait(),
                        self.check_event(
                            cond=all(
                                        [
                                            data["current_state"]["rsi-15m"] - data["historical_prices"]["15m"][last_key_15m]["rsi"] < 0.
                                        ]
                                    ),
                            event=event0,
                            t=1
                        )
                    )

                    '''await self.check_conditions(
                            cond=all([
                                data["current_state"]["rsi-5m"] - data["historical_prices"]["5m"][last_key_5m]["rsi"] > 0.
                            ])
                        )'''

                    # open position...
                    self.wallet.open_position(
                        side="BUY",
                        quantity=self.qty,
                        price=data["historical_prices"]["1s"][last_key_1s]["c"],
                        date=Data.to_datetime(data["historical_prices"]["1s"][last_key_1s]["t"]).strftime("%Y-%m-%d %H:%M:%S")
                        #type=Client.FUTURE_ORDER_TYPE_LIMIT
                    )

                    event = asyncio.Event()
                    await asyncio.gather(
                        event.wait(),
                        self.check_event(
                            cond=all(
                                        [
                                            self.wallet.binance.client.futures_get_order(
                                                symbol=self.wallet.orders[self.wallet.INDEX]['Symbol'],
                                                orderId=self.wallet.orders[self.wallet.INDEX]['IdOpen']
                                                )['status'] == 'FILLED'
                                        ]
                                    ),
                            event=event,
                            t=1
                        )
                    )

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
                    profit_percent = 100 * (data["historical_prices"]["1s"][last_key_1s]["c"] - self.wallet.orders[self.wallet.INDEX]["Open"]) * float(Parameters.INDEX_POINT.value) / self.wallet.orders[self.wallet.INDEX]["Open"]
                elif self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_SHORT.value:
                    profit_percent = 100 * (self.wallet.orders[self.wallet.INDEX]["Open"] - data["historical_prices"]["1s"][last_key_1s]["c"]) * float(Parameters.INDEX_POINT.value) / self.wallet.orders[self.wallet.INDEX]["Open"]

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
                                    #data["current_state"]["rsi-5m"] > (70 - 4.)
                                    profit_percent >= 9. / 20.
                                ]
                            )
                        ),
                        self.check_conditions(
                            cond=all(
                                [
                                    stop_loss.check_trigger(data["historical_prices"]["1s"][last_key_1s]["c"], Parameters.TYPE_LONG.value),
                                    #data["historical_prices"]["1s"][last_key_1s]["c"] < self.wallet.orders[self.wallet.INDEX]['Open'] - 5.,
                                    #data["historical_prices"]["5m"][last_key_5m]["c"] <= min( data["historical_prices"]["5m"][key]["l"] for key in last_keys_5m )
                                ]
                            )
                        )
                    )

                    if resp1:
                        print("Position closed")
                        print("5m RSI:", data["historical_prices"]["5m"][last_key_5m]["rsi"])

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=data["historical_prices"]["1s"][last_key_1s]["c"],
                            date=Data.to_datetime(data["historical_prices"]["1s"][last_key_1s]["t"]).strftime("%Y-%m-%d %H:%M:%S")
                            #type=Client.FUTURE_ORDER_TYPE_LIMIT
                        )

                        event = asyncio.Event()
                        await asyncio.gather(
                            event.wait(),
                            self.check_event(
                                cond=all(
                                            [
                                                self.wallet.binance.client.futures_get_order(
                                                    symbol=self.wallet.orders[self.wallet.INDEX]['Symbol'],
                                                    orderId=self.wallet.orders[self.wallet.INDEX]['IdOpen']
                                                    )['status'] == 'FILLED'
                                            ]
                                        ),
                                event=event,
                                t=1
                            )
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
                            price=data["historical_prices"]["1s"][last_key_1s]["c"],
                            date=Data.to_datetime(data["historical_prices"]["1s"][last_key_1s]["t"]).strftime("%Y-%m-%d %H:%M:%S")
                            #type=Client.FUTURE_ORDER_TYPE_LIMIT
                        )

                        event = asyncio.Event()
                        await asyncio.gather(
                            event.wait(),
                            self.check_event(
                                cond=all(
                                            [
                                                self.wallet.binance.client.futures_get_order(
                                                    symbol=self.wallet.orders[self.wallet.INDEX]['Symbol'],
                                                    orderId=self.wallet.orders[self.wallet.INDEX]['IdOpen']
                                                    )['status'] == 'FILLED'
                                            ]
                                        ),
                                event=event,
                                t=1
                            )
                        )

                        print(self.wallet.orders)

                        #Notification("bhaskan@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))
                        #Notification("oozlen@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))

                        self.write_to_excel()

                        event2 = asyncio.Event()
                        await asyncio.gather(
                            event2.wait(),
                            self.check_event(
                                cond=all(
                                            [
                                                not data["historical_prices"]["15m"][last_key_15m]["rsi"] < (30 + 3.)
                                            ]
                                        ),
                                event=event2,
                                t=5
                            )
                        )

                        '''await self.check_conditions(
                            cond=all([
                                not data["historical_prices"]["15m"][last_key_15m]["rsi"] < (30 + 3.)
                            ])
                        )'''

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
                                    #data["current_state"]["rsi-5m"] < (30 + 4.)
                                    profit_percent >= 9. / 20.
                                ]
                            )
                        ),
                        self.check_conditions(
                            cond=all(
                                [
                                    stop_loss.check_trigger(data["historical_prices"]["1s"][last_key_1s]["c"], Parameters.TYPE_SHORT.value),
                                    #data["historical_prices"]["1s"][last_key_1s]["c"] > self.wallet.orders[self.wallet.INDEX]['Open'] + 5.,
                                    #data["historical_prices"]["5m"][last_key_5m]["c"] >= max( data["historical_prices"]["5m"][key]["h"] for key in last_keys_5m )
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
                            price=data["historical_prices"]["1s"][last_key_1s]["c"],
                            date=Data.to_datetime(data["historical_prices"]["1s"][last_key_1s]["t"]).strftime("%Y-%m-%d %H:%M:%S")
                            #type=Client.FUTURE_ORDER_TYPE_LIMIT
                        )

                        event = asyncio.Event()
                        await asyncio.gather(
                            event.wait(),
                            self.check_event(
                                cond=all(
                                            [
                                                self.wallet.binance.client.futures_get_order(
                                                    symbol=self.wallet.orders[self.wallet.INDEX]['Symbol'],
                                                    orderId=self.wallet.orders[self.wallet.INDEX]['IdOpen']
                                                    )['status'] == 'FILLED'
                                            ]
                                        ),
                                event=event,
                                t=1
                            )
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
                            price=data["historical_prices"]["1s"][last_key_1s]["c"],
                            date=Data.to_datetime(data["historical_prices"]["1s"][last_key_1s]["t"]).strftime("%Y-%m-%d %H:%M:%S")
                            #type=Client.FUTURE_ORDER_TYPE_LIMIT
                        )

                        event = asyncio.Event()
                        await asyncio.gather(
                            event.wait(),
                            self.check_event(
                                cond=all(
                                            [
                                                self.wallet.binance.client.futures_get_order(
                                                    symbol=self.wallet.orders[self.wallet.INDEX]['Symbol'],
                                                    orderId=self.wallet.orders[self.wallet.INDEX]['IdOpen']
                                                    )['status'] == 'FILLED'
                                            ]
                                        ),
                                event=event,
                                t=1
                            )
                        )

                        print(self.wallet.orders)

                        #Notification("bhaskan@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))
                        #Notification("oozlen@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))

                        self.write_to_excel()

                        event2 = asyncio.Event()
                        await asyncio.gather(
                            event2.wait(),
                            self.check_event(
                                cond=all(
                                            [
                                                not data["historical_prices"]["15m"][last_key_15m]["rsi"] > (70 - 3.)
                                            ]
                                        ),
                                event=event2,
                                t=5
                            )
                        )

                        '''await self.check_conditions(
                            cond=all([
                                not data["historical_prices"]["15m"][last_key_15m]["rsi"] > (70 - 3.)
                            ])
                        )'''

            with open(f"log.json", "w") as log:
                log.write(json.dumps(self.wallet.orders))

    async def strategy_2_trailing_DEV(self):

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

            if not self.wallet.is_open():
                #print("Waiting to open position")
                print("Waiting to open position", Data.to_datetime(data["current_date"]))
                print("back RSI:", data["historical_prices"]["1s"][last_key_1s]["rsi"])
                print("1m RSI:", data["historical_prices"]["1m"][last_key_1m]["rsi"])
                print("5m RSI:", data["historical_prices"]["5m"][last_key_5m]["rsi"])
                print("normalized volume 1m:", data["historical_prices"]["1m"][last_key_1m]["normalized_volume"])

                resp1, resp2 = await asyncio.gather(
                    self.check_conditions(
                        cond=all(
                            [
                                #not abs(data["historical_prices"]["1m"][last_key_1m]["rsi"] - 70.) < 4.,
                                not data["historical_prices"]["1m"][last_key_1m]["rsi"] > (70 - 0.),
                                data["historical_prices"]["1m"][last_key_1m]["normalized_volume"] <= 0.,
                                #abs(data["historical_prices"]["5m"][last_key_5m]["rsi"] - 70.) < 3.,
                                data["historical_prices"]["5m"][last_key_5m]["rsi"] > (70 - 4.),
                                data["historical_prices"]["5m"][last_key_5m]["normalized_volume"] <= 0.
                            ]
                        )
                    ),
                    self.check_conditions(
                        cond=all(
                            [
                                #not abs(data["historical_prices"]["1m"][last_key_1m]["rsi"] - 30.) < 4.,
                                not data["historical_prices"]["1m"][last_key_1m]["rsi"] < (30 + 0.),
                                data["historical_prices"]["1m"][last_key_1m]["normalized_volume"] <= 0.,
                                #abs(data["historical_prices"]["5m"][last_key_5m]["rsi"] - 30.) < 3.,
                                data["historical_prices"]["5m"][last_key_5m]["rsi"] < (30 + 4.),
                                data["historical_prices"]["5m"][last_key_5m]["normalized_volume"] <= 0.
                            ]
                        )
                    )
                )

                if resp1:
                    print("condition 1 satisfied")
                    print("1m RSI:", data["historical_prices"]["1m"][last_key_1m]["rsi"])
                    print("5m RSI:", data["historical_prices"]["5m"][last_key_5m]["rsi"])
                    print("1m Volume:", data["historical_prices"]["1m"][last_key_1m]["normalized_volume"])

                    # open position...
                    self.wallet.open_position(
                        side="SELL",
                        #quantity=1,
                        quantity=self.qty,
                        price=data["historical_prices"]["1m"][last_key_1m]["c"],
                        date=Data.to_datetime(data["historical_prices"]["1m"][last_key_1m]["t"]).strftime("%Y-%m-%d %H:%M:%S")
                    )

                    stop_loss = StopLoss(max(data["historical_prices"]["1m"][last_key_1m]["o"], data["historical_prices"]["1m"][last_key_1m]["c"]) + 5.)
                    trailing_stop = MyTrailingStop(data["historical_prices"]["1m"][last_key_1m]["c"] + 5.)

                    print(self.wallet.orders)

                    Notification("bhaskan@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))
                    #Notification("oozlen@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))

                    self.write_to_excel()

                if resp2:
                    print("condition 2 satisfied")
                    print("1m RSI:", data["historical_prices"]["1m"][last_key_1m]["rsi"])
                    print("5m RSI:", data["historical_prices"]["5m"][last_key_5m]["rsi"])
                    print("1m Volume:", data["historical_prices"]["1m"][last_key_1m]["normalized_volume"])

                    # open position...
                    self.wallet.open_position(
                        side="BUY",
                        #quantity=1,
                        quantity=self.qty,
                        price=data["historical_prices"]["1m"][last_key_1m]["c"],
                        date=Data.to_datetime(data["historical_prices"]["1m"][last_key_1m]["t"]).strftime("%Y-%m-%d %H:%M:%S")
                    )

                    stop_loss = StopLoss(max(data["historical_prices"]["1m"][last_key_1m]["o"], data["historical_prices"]["1m"][last_key_1m]["c"]) - 5.)
                    trailing_stop = MyTrailingStop(data["historical_prices"]["1m"][last_key_1m]["c"] - 5.)

                    print(self.wallet.orders)

                    Notification("bhaskan@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))
                    #Notification("oozlen@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))

                    self.write_to_excel()

            elif self.wallet.is_open():
                print("Waiting to close position", Data.to_datetime(data["current_date"]))
                print("back RSI:", data["historical_prices"]["1s"][last_key_1s]["rsi"])
                print("1m RSI:", data["historical_prices"]["1m"][last_key_1m]["rsi"])
                print("5m RSI:", data["historical_prices"]["5m"][last_key_5m]["rsi"])

                if self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_LONG.value:

                    trailing_stop.update_stop(data["historical_prices"]["1m"][last_key_1m]["c"], Parameters.TYPE_LONG.value)
                    
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
                                    trailing_stop.check_trigger(data["historical_prices"]["1m"][last_key_1m]["c"], Parameters.TYPE_LONG.value)
                                ]
                            )
                        ),
                        self.check_conditions(
                            cond=all(
                                [
                                    stop_loss.check_trigger(data["historical_prices"]["1s"][last_key_1s]["c"], Parameters.TYPE_LONG.value),
                                    #data["historical_prices"]["1s"][last_key_1s]["c"] < self.wallet.orders[self.wallet.INDEX]['Open'] - 5.,
                                    #data["historical_prices"]["5m"][last_key_5m]["c"] <= min( data["historical_prices"]["5m"][key]["l"] for key in last_keys_5m )
                                ]
                            )
                        )
                    )

                    if resp1:
                        print("Trailing Stop")
                        print("5m RSI:", data["historical_prices"]["5m"][last_key_5m]["rsi"])

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=data["historical_prices"]["1m"][last_key_1m]["c"],
                            date=Data.to_datetime(data["historical_prices"]["1m"][last_key_1m]["t"]).strftime("%Y-%m-%d %H:%M:%S")
                        )
                        print(self.wallet.orders)

                        Notification("bhaskan@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))
                        #Notification("oozlen@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))

                        self.write_to_excel()
                    
                    elif resp2:
                        print("Stop Loss")

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=data["historical_prices"]["1m"][last_key_1m]["c"],
                            date=Data.to_datetime(data["historical_prices"]["1m"][last_key_1m]["t"]).strftime("%Y-%m-%d %H:%M:%S")
                        )
                        print(self.wallet.orders)

                        Notification("bhaskan@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))
                        #Notification("oozlen@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))

                        self.write_to_excel()

                elif self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_SHORT.value:

                    trailing_stop.update_stop(data["historical_prices"]["1s"][last_key_1s]["c"], Parameters.TYPE_SHORT.value)
                    
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
                                    trailing_stop.check_trigger(data["historical_prices"]["1m"][last_key_1m]["c"], Parameters.TYPE_SHORT.value)
                                ]
                            )
                        ),
                        self.check_conditions(
                            cond=all(
                                [
                                    stop_loss.check_trigger(data["historical_prices"]["1s"][last_key_1s]["c"], Parameters.TYPE_SHORT.value),
                                    #data["historical_prices"]["1s"][last_key_1s]["c"] > self.wallet.orders[self.wallet.INDEX]['Open'] + 5.,
                                    #data["historical_prices"]["5m"][last_key_5m]["c"] >= max( data["historical_prices"]["5m"][key]["h"] for key in last_keys_5m )
                                ]
                            )
                        )
                    )

                    if resp1:
                        print("Trailing Stop")
                        print("5m RSI:", data["historical_prices"]["5m"][last_key_5m]["rsi"])

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=data["historical_prices"]["1m"][last_key_1m]["c"],
                            date=Data.to_datetime(data["historical_prices"]["1m"][last_key_1m]["t"]).strftime("%Y-%m-%d %H:%M:%S")
                        )
                        print(self.wallet.orders)

                        Notification("bhaskan@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))
                        #Notification("oozlen@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))

                        self.write_to_excel()

                    elif resp2:
                        print("Stop Loss")

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=data["historical_prices"]["1m"][last_key_1m]["c"],
                            date=Data.to_datetime(data["historical_prices"]["1m"][last_key_1m]["t"]).strftime("%Y-%m-%d %H:%M:%S")
                        )
                        print(self.wallet.orders)

                        Notification("bhaskan@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))
                        #Notification("oozlen@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))

                        self.write_to_excel()

            with open(f"log.json", "w") as log:
                log.write(json.dumps(self.wallet.orders))

    async def strategy_1_DEV(self):

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

            if not self.wallet.is_open():
                #print("Waiting to open position")
                print("Waiting to open position", Data.to_datetime(data["current_date"]))

                resp1, resp2 = await asyncio.gather(
                    self.check_conditions(
                        cond=all(
                            [
                                #not abs(data["historical_prices"]["1m"][last_key_1m]["rsi"] - 70.) < 4.,
                                data["historical_prices"]["1m"][last_key_1m]["rsi"] > (70 - 1.),
                                data["historical_prices"]["1m"][last_key_1m]["normalized_volume"] > 1.,
                                #abs(data["historical_prices"]["5m"][last_key_5m]["rsi"] - 70.) < 3.,
                                data["historical_prices"]["5m"][last_key_5m]["rsi"] > (70 - 4.),
                                data["historical_prices"]["5m"][last_key_5m]["normalized_volume"] > 1.
                            ]
                        )
                    ),
                    self.check_conditions(
                        cond=all(
                            [
                                #not abs(data["historical_prices"]["1m"][last_key_1m]["rsi"] - 30.) < 4.,
                                data["historical_prices"]["1m"][last_key_1m]["rsi"] < (30 + 1.),
                                data["historical_prices"]["1m"][last_key_1m]["normalized_volume"] > 1.,
                                #abs(data["historical_prices"]["5m"][last_key_5m]["rsi"] - 30.) < 3.,
                                data["historical_prices"]["5m"][last_key_5m]["rsi"] < (30 + 4.),
                                data["historical_prices"]["5m"][last_key_5m]["normalized_volume"] > 1.
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
                        price=data["historical_prices"]["1s"][last_key_1s]["c"],
                        date=Data.to_datetime(data["historical_prices"]["1s"][last_key_1s]["t"]).strftime("%Y-%m-%d %H:%M:%S")
                    )

                    stop_loss = StopLoss(max(data["historical_prices"]["1m"][last_key_1m]["o"], data["historical_prices"]["1m"][last_key_1m]["c"]) - 2.)
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
                        price=data["historical_prices"]["1s"][last_key_1s]["c"],
                        date=Data.to_datetime(data["historical_prices"]["1s"][last_key_1s]["t"]).strftime("%Y-%m-%d %H:%M:%S")
                    )

                    stop_loss = StopLoss(max(data["historical_prices"]["1m"][last_key_1m]["o"], data["historical_prices"]["1m"][last_key_1m]["c"]) + 2.)
                    trailing_stop = MyTrailingStop(data["historical_prices"]["1m"][last_key_1m]["c"] + 5.)

                    print(self.wallet.orders)

                    #Notification("bhaskan@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))
                    #Notification("oozlen@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))

                    self.write_to_excel()

            elif self.wallet.is_open():
                print("Waiting to close position", Data.to_datetime(data["current_date"]))

                if self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_LONG.value:

                    trailing_stop.update_stop(data["historical_prices"]["1s"][last_key_1s]["c"], Parameters.TYPE_LONG.value)
                    print("Current Stop:", trailing_stop.current_stop)
                    
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
                                    trailing_stop.check_trigger(data["historical_prices"]["1s"][last_key_1s]["c"], Parameters.TYPE_LONG.value)
                                ]
                            )
                        ),
                        self.check_conditions(
                            cond=all(
                                [
                                    #data["historical_prices"]["1s"][last_key_1s]["c"] < self.wallet.orders[self.wallet.INDEX]['Open'] - 5.,
                                    stop_loss.check_trigger(data["historical_prices"]["1s"][last_key_1s]["c"], Parameters.TYPE_LONG.value)
                                ]
                            )
                        )
                    )

                    if resp1:
                        print("Position closed")

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=data["historical_prices"]["1s"][last_key_1s]["c"],
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
                            price=data["historical_prices"]["1s"][last_key_1s]["c"],
                            date=Data.to_datetime(data["historical_prices"]["1s"][last_key_1s]["t"]).strftime("%Y-%m-%d %H:%M:%S")
                        )
                        print(self.wallet.orders)

                        #Notification("bhaskan@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))
                        #Notification("oozlen@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))

                        self.write_to_excel()

                elif self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_SHORT.value:

                    trailing_stop.update_stop(data["historical_prices"]["1s"][last_key_1s]["c"], Parameters.TYPE_SHORT.value)
                    print("Current Stop:", trailing_stop.current_stop)
                    
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
                                    trailing_stop.check_trigger(data["historical_prices"]["1s"][last_key_1s]["c"], Parameters.TYPE_SHORT.value)
                                ]
                            )
                        ),
                        self.check_conditions(
                            cond=all(
                                [
                                    #data["historical_prices"]["1s"][last_key_1s]["c"] > self.wallet.orders[self.wallet.INDEX]['Open'] + 5.,
                                    stop_loss.check_trigger(data["historical_prices"]["1s"][last_key_1s]["c"], Parameters.TYPE_SHORT.value)
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
                            price=data["historical_prices"]["1s"][last_key_1s]["c"],
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
                            price=data["historical_prices"]["1s"][last_key_1s]["c"],
                            date=Data.to_datetime(data["historical_prices"]["1s"][last_key_1s]["t"]).strftime("%Y-%m-%d %H:%M:%S")
                        )
                        print(self.wallet.orders)

                        #Notification("bhaskan@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))
                        #Notification("oozlen@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))

                        self.write_to_excel()

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
                        price=data["historical_prices"]["1s"][last_key_1s]["c"],
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
                        price=data["historical_prices"]["1s"][last_key_1s]["c"],
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
                                    trailing_stop.check_trigger(data["historical_prices"]["1s"][last_key_1s]["c"], Parameters.TYPE_LONG.value)
                                ]
                            ),
                            t=60
                        ),
                        self.check_conditions(
                            cond=all(
                                [
                                    #data["historical_prices"]["1s"][last_key_1s]["c"] < self.wallet.orders[self.wallet.INDEX]['Open'] - 5.,
                                    stop_loss.check_trigger(data["historical_prices"]["1s"][last_key_1s]["c"], Parameters.TYPE_LONG.value)
                                ]
                            )
                        )
                    )

                    if resp1:
                        print("Position closed")

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=data["historical_prices"]["1s"][last_key_1s]["c"],
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
                            price=data["historical_prices"]["1s"][last_key_1s]["c"],
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
                                    trailing_stop.check_trigger(data["historical_prices"]["1s"][last_key_1s]["c"], Parameters.TYPE_SHORT.value)
                                ]
                            )
                        ),
                        self.check_conditions(
                            cond=all(
                                [
                                    #data["historical_prices"]["1s"][last_key_1s]["c"] > self.wallet.orders[self.wallet.INDEX]['Open'] + 5.,
                                    stop_loss.check_trigger(data["historical_prices"]["1s"][last_key_1s]["c"], Parameters.TYPE_SHORT.value)
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
                            price=data["historical_prices"]["1s"][last_key_1s]["c"],
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
                            price=data["historical_prices"]["1s"][last_key_1s]["c"],
                            date=Data.to_datetime(data["historical_prices"]["1s"][last_key_1s]["t"]).strftime("%Y-%m-%d %H:%M:%S")
                        )
                        print(self.wallet.orders)

                        #Notification("bhaskan@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))
                        #Notification("oozlen@bacaciyatirim.com", json.dumps(self.wallet.orders[self.wallet.INDEX]))

                        self.write_to_excel()

            with open(f"log.json", "w") as log:
                log.write(json.dumps(self.wallet.orders))