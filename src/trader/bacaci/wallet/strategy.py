import asyncio
import json
import time
import pandas as pd

from .wallet import Wallet, StopLoss
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
        
        print("Strategy created")
        time.sleep(1)

        #try:
        #    mail = Notification()
        #    print("Succesfully connected to SMTP")
        #except:
        #    print("SMTP problem occurred, continue...")

        # process according to strategy
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        #loop.run_until_complete(self.dummy_strategy(cond=True))
        loop.run_until_complete(self.strategy_2_DEV())

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

    async def test(self):

        while True:

            data = self.read_memory()

            last_key = list(data["historical_prices"]["1s"].keys())[-1]

            print(Data.to_datetime(data["current_date"]), data["historical_prices"]["1s"][last_key]["rsi"], data["historical_prices"]["1s"][last_key]["normalized_volume"])
            time.sleep(10)

    async def dummy_strategy(self, cond=False):
        # WORKING ON STOP_LOSS

        while True:

            data = self.read_memory()

            last_key = list(data["historical_prices"]["1m"].keys())[-1]

            if not self.wallet.is_open():
                time.sleep(5)
                print("Waiting to open position", Data.to_datetime(data["current_date"]))

                self.wallet.open_position(
                    side="BUY",
                    quantity=self.qty,
                    price=data["historical_prices"]["1m"][last_key]["c"],
                    date=data["historical_prices"]["1m"][last_key]["t"]
                )
                print(self.wallet.orders)
                
                pass

            elif self.wallet.is_open():

                if self.wallet.orders[self.wallet.INDEX]["Side"] == Parameters.TYPE_LONG.value:
                    
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
                                not data["historical_prices"]["1m"][last_key_1m]["rsi"] > (70 - 4.),
                                data["historical_prices"]["1m"][last_key_1m]["normalized_volume"] <= 0.,
                                #abs(data["historical_prices"]["5m"][last_key_5m]["rsi"] - 70.) < 3.,
                                data["historical_prices"]["5m"][last_key_5m]["rsi"] > (70 - 3.)
                                #data["historical_prices"]["5m"][last_keys_5m]["normalized_volume"] <= 0.
                            ]
                        )
                    ),
                    self.check_conditions(
                        cond=all(
                            [
                                #not abs(data["historical_prices"]["1m"][last_key_1m]["rsi"] - 30.) < 4.,
                                not data["historical_prices"]["1m"][last_key_1m]["rsi"] < (30 + 4.),
                                data["historical_prices"]["1m"][last_key_1m]["normalized_volume"] <= 0.,
                                #abs(data["historical_prices"]["5m"][last_key_5m]["rsi"] - 30.) < 3.,
                                data["historical_prices"]["5m"][last_key_5m]["rsi"] < (30 + 3.)
                                #data["historical_prices"]["5m"][last_keys_5m]["normalized_volume"] <= 0.
                            ]
                        )
                    )
                )

                if resp1:
                    print("condition 1 satisfied")
                    print("RSI:", data["historical_prices"]["1m"][last_key_1m]["rsi"])
                    print("Volume:", data["historical_prices"]["1m"][last_key_1m]["v"])

                    # open position...
                    self.wallet.open_position(
                        side="SELL",
                        #quantity=1,
                        quantity=self.qty,
                        price=data["historical_prices"]["1m"][last_key_1m]["c"],
                        date=data["historical_prices"]["1m"][last_key_1m]["t"]
                    )

                    stop_loss = StopLoss(max(data["historical_prices"]["1m"][last_key_1m]["o"], data["historical_prices"]["1m"][last_key_1m]["c"]) + 5.)

                    print(self.wallet.orders)

                if resp2:
                    print("condition 2 satisfied")
                    print("RSI:", data["historical_prices"]["1m"][last_key_1m]["rsi"])
                    print("Volume:", data["historical_prices"]["1m"][last_key_1m]["v"])

                    # open position...
                    self.wallet.open_position(
                        side="BUY",
                        #quantity=1,
                        quantity=self.qty,
                        price=data["historical_prices"]["1m"][last_key_1m]["c"],
                        date=data["historical_prices"]["1m"][last_key_1m]["t"]
                    )

                    stop_loss = StopLoss(max(data["historical_prices"]["1m"][last_key_1m]["o"], data["historical_prices"]["1m"][last_key_1m]["c"]) - 5.)

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
                                    abs(data["historical_prices"]["5m"][last_key_5m]["rsi"] - 70) < 5.
                                ]
                            )
                        ),
                        self.check_conditions(
                            cond=all(
                                [
                                    stop_loss.check_trigger(data["historical_prices"]["5m"][last_key_5m]["c"], Parameters.TYPE_LONG.value),
                                    #data["historical_prices"]["5m"][last_key_5m]["c"] <= min( data["historical_prices"]["5m"][key]["l"] for key in last_keys_5m )
                                ]
                            )
                        )
                    )

                    if resp:
                        print("Position closed")

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=data["historical_prices"]["1m"][last_key_1m]["c"],
                            date=data["historical_prices"]["1m"][last_key_1m]["t"]
                        )
                        print(self.wallet.orders)
                    
                    elif stop_loss:
                        print("Stop Loss")

                        self.wallet.close_position(
                            side="SELL",
                            quantity=self.qty,
                            price=data["historical_prices"]["1m"][last_key_1m]["c"],
                            date=data["historical_prices"]["1m"][last_key_1m]["t"]
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
                                    abs(data["historical_prices"]["5m"][last_key_5m]["rsi"] - 30) < 5.
                                ]
                            )
                        ),
                        self.check_conditions(
                            cond=all(
                                [
                                    stop_loss.check_trigger(data["historical_prices"]["5m"][last_key_5m]["c"], Parameters.TYPE_SHORT.value),
                                    #data["historical_prices"]["5m"][last_key_5m]["c"] >= max( data["historical_prices"]["5m"][key]["h"] for key in last_keys_5m )
                                ]
                            )
                        )
                    )

                    if resp:
                        print("Position closed")

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=data["historical_prices"]["1m"][last_key_1m]["c"],
                            date=data["historical_prices"]["1m"][last_key_1m]["t"]
                        )
                        print(self.wallet.orders)

                    elif stop_loss:
                        print("Stop Loss")

                        self.wallet.close_position(
                            side="BUY",
                            quantity=self.qty,
                            price=data["historical_prices"]["1m"][last_key_1m]["c"],
                            date=data["historical_prices"]["1m"][last_key_1m]["t"]
                        )
                        print(self.wallet.orders)

            with open(f"log.json", "w") as log:
                log.write(json.dumps(self.wallet.orders))