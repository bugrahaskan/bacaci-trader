from binance.client import Client

from bacaci.accounts.binance import Binance

client = Binance()

ord = client.futures_open_position(
    symbol="ETHUSDT",
    side="BUY",
    quantity = 0.2,
    price=2040.,
    type=Client.FUTURE_ORDER_TYPE_LIMIT
)

print(ord)