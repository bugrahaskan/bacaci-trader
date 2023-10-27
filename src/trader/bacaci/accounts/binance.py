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
    
    def futures_open_position(self, symbol, side, quantity, isIsolated=True, type=Client.ORDER_TYPE_MARKET):
        
        if side == self.client.SIDE_BUY:
            #order = self.client.futures_create_order(
            self.client.futures_create_order(
                symbol=symbol,
                isIsolated=isIsolated,
                side=side,
                type=type,
                leverage=Parameters.INDEX_POINT.value, # Leverage value
                quantity=quantity
            )
        
        elif side == self.client.SIDE_SELL:
            #order = self.client.futures_create_order(
            self.client.futures_create_order(
                symbol=symbol,
                isIsolated=isIsolated,
                side=side,
                type=type,
                leverage=Parameters.INDEX_POINT.value, # Leverage value
                quantity=quantity
            )
        
        # return necessary parts of "order" in json
        #return {
        #    'Symbol': order['symbol'],
        #    'Side': order['side'], # correct in detail
        #    'Open': order['price'],
        #    'Commission_open': order['fills'][0]['commission'] # in btc
        #}

        return {}

    def futures_close_position(self, symbol, side, quantity, isIsolated=True, type=Client.ORDER_TYPE_MARKET):
        
        if side == self.client.SIDE_BUY:
            #order = self.client.futures_create_order(
            self.client.futures_create_order(
                symbol=symbol,
                isIsolated=isIsolated,
                side=side,
                type=type,
                leverage=Parameters.INDEX_POINT.value, # Leverage value
                quantity=quantity
            )

        if side == self.client.SIDE_SELL:
            #order = self.client.futures_create_order(
            self.client.futures_create_order(
                symbol=symbol,
                isIsolated=isIsolated,
                side=side,
                type=type,
                leverage=Parameters.INDEX_POINT.value, # Leverage value
                quantity=quantity
            )
        
        # return necessary parts of "order" in json
        return {}