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

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from ..enums import Parameters

class Alpaca:
    
    def __init__(self):
        
        self.trading_client = Alpaca.alpaca_connect()

    @staticmethod
    def alpaca_connect():

        trading_client = TradingClient(
            Parameters.ALPACA_API_KEY.value,
            Parameters.ALPACA_SECRET_KEY.value,
            paper=True
        )

        return trading_client
    
    def open_position(self, symbol, side, quantity):
        
        if side == OrderSide.BUY:
            # check the variable "order" in alpaca
            order = MarketOrderRequest(
                symbol=symbol,
                qty=quantity,
                side=side,
                time_in_force=TimeInForce.GTC
            )
            order = self.trading_client.submit_order(order)

        elif side == OrderSide.SELL:
            # check the variable "order" in alpaca
            order = MarketOrderRequest(
                symbol=symbol,
                qty=quantity,
                side=side,
                time_in_force=TimeInForce.GTC
            )
            order = self.trading_client.submit_order(order)
        
        # return necessary parts of "order" in json
        return {}

    def close_position(self, symbol, side, quantity):
        
        if side == OrderSide.BUY:
            # check the variable "order" in alpaca
            order = MarketOrderRequest(
                symbol=symbol,
                qty=quantity,
                side=side,
                time_in_force=TimeInForce.GTC
            )
            order = self.trading_client.submit_order(order)

        elif side == OrderSide.SELL:
            # check the variable "order" in alpaca
            order = MarketOrderRequest(
                symbol=symbol,
                qty=quantity,
                side=side,
                time_in_force=TimeInForce.GTC
            )
            order = self.trading_client.submit_order(order)
        
        # return necessary parts of "order" in json
        return {}