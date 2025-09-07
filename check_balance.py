# check_balance.py
from alpaca.trading.client import TradingClient
from bot.config import settings

client = TradingClient(
    api_key=settings.alpaca_api_key,
    secret_key=settings.alpaca_secret_key,
    paper=(settings.mode == "paper")
)

account = client.get_account()
print(f"💵 Cash: {account.cash}")
print(f"💰 Equity: {account.equity}")
print(f"📊 Portfolio Value: {account.portfolio_value}")