import logging
import pandas as pd
import numpy as np
from datetime import datetime
import datetime as dt
import configparser
import requests
import json
import os, sys
import sqlite3
import requests
        
from binance.client import Client
from ..enums import Parameters

class Binance:

    def __init__(self):
        
        self.client = Binance.binance_connect()

    @staticmethod
    def binance_connect():

        client = Client(
            api_key=Parameters.BINANCE_API_KEY.value,
            api_secret=Parameters.BINANCE_SECRET_KEY.value
        )

        return client
    
    def futures_open_position(self, symbol, side, quantity, price=0., isIsolated=True, type=Client.FUTURE_ORDER_TYPE_MARKET):
        
        if side == self.client.SIDE_BUY:

            if type == Client.FUTURE_ORDER_TYPE_MARKET:

                order = self.client.futures_create_order(
                #self.client.futures_create_order(
                    symbol=symbol,
                    isIsolated=isIsolated,
                    side=side,
                    type=type,
                    leverage=Parameters.INDEX_POINT.value, # Leverage value
                    quantity=quantity
                )

            elif type == Client.FUTURE_ORDER_TYPE_LIMIT:

                order = self.client.futures_create_order(
                #self.client.futures_create_order(
                    symbol=symbol,
                    isIsolated=isIsolated,
                    side=side,
                    type=type,
                    timeInForce=Client.TIME_IN_FORCE_GTC,
                    leverage=Parameters.INDEX_POINT.value, # Leverage value
                    quantity=quantity,
                    price=price-0.5 # develop that statement
                )
        
        elif side == self.client.SIDE_SELL:

            if type == Client.FUTURE_ORDER_TYPE_MARKET:

                order = self.client.futures_create_order(
                #self.client.futures_create_order(
                    symbol=symbol,
                    isIsolated=isIsolated,
                    side=side,
                    type=type,
                    leverage=Parameters.INDEX_POINT.value, # Leverage value
                    quantity=quantity
                )

            elif type == Client.FUTURE_ORDER_TYPE_LIMIT:

                order = self.client.futures_create_order(
                #self.client.futures_create_order(
                    symbol=symbol,
                    isIsolated=isIsolated,
                    side=side,
                    type=type,
                    timeInForce=Client.TIME_IN_FORCE_GTC,
                    leverage=Parameters.INDEX_POINT.value, # Leverage value
                    quantity=quantity,
                    price=price+0.5 # develop that statement
                )
        
        # return necessary parts of "order" in json
        return {
            'OrderID': order['orderId'],
            'Symbol': order['symbol'],
            'Status': order['status'],
            'Side': order['side'], # correct in detail
            'Open': order['price']
            #'Commission_open': order['fills'][0]['commission'] # in btc
        }

        #return {}

    def futures_close_position(self, symbol, side, quantity, price=0., isIsolated=True, type=Client.FUTURE_ORDER_TYPE_MARKET):
        
        if side == self.client.SIDE_BUY:

            if type == Client.FUTURE_ORDER_TYPE_MARKET:

                order = self.client.futures_create_order(
                #self.client.futures_create_order(
                    symbol=symbol,
                    #isIsolated=isIsolated,
                    side=side,
                    type=type,
                    leverage=Parameters.INDEX_POINT.value, # Leverage value
                    quantity=quantity
                )

            elif type == Client.FUTURE_ORDER_TYPE_LIMIT:

                order = self.client.futures_create_order(
                #self.client.futures_create_order(
                    symbol=symbol,
                    #isIsolated=isIsolated,
                    side=side,
                    type=type,
                    timeInForce=Client.TIME_IN_FORCE_GTC,
                    leverage=Parameters.INDEX_POINT.value, # Leverage value
                    quantity=quantity,
                    price=price+.5 # develop that statement
                )

        if side == self.client.SIDE_SELL:

            if type == Client.FUTURE_ORDER_TYPE_MARKET:
            
                order = self.client.futures_create_order(
                #self.client.futures_create_order(
                    symbol=symbol,
                    #isIsolated=isIsolated,
                    side=side,
                    type=type,
                    leverage=Parameters.INDEX_POINT.value, # Leverage value
                    quantity=quantity
                )

            elif type == Client.FUTURE_ORDER_TYPE_LIMIT:

                order = self.client.futures_create_order(
                #self.client.futures_create_order(
                    symbol=symbol,
                    #isIsolated=isIsolated,
                    side=side,
                    type=type,
                    timeInForce=Client.TIME_IN_FORCE_GTC,
                    leverage=Parameters.INDEX_POINT.value, # Leverage value
                    quantity=quantity,
                    price=price-.5 # develop that statement
                )
        
        # return necessary parts of "order" in json
        return {
            'OrderID': order['orderId'],
            'Symbol': order['symbol'],
            'Status': order['status'],
            'Side': order['side'], # correct in detail
            'Open': order['price']
            #'Commission_open': order['fills'][0]['commission'] # in btc
        }

        #return {}