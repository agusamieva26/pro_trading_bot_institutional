# limpieza.py
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOrdersRequest
from alpaca.trading.enums import QueryOrderStatus

client = TradingClient(
    api_key="tu_api_key",
    secret_key="tu_secret_key",
    paper=True
)

# Cancelar todas las órdenes abiertas
req = GetOrdersRequest(status=QueryOrderStatus.OPEN)
open_orders = client.get_orders(req)
for order in open_orders:
    client.cancel_order_by_id(order.id)
    print(f"Cancelled order: {order.symbol}")