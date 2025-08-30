# limpieza.py
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOrdersRequest

client = TradingClient(
    api_key="tu_api_key_de_paper_aqui",
    secret_key="tu_secret_key_de_paper_aqui",
    paper=True
)

try:
    req = GetOrdersRequest(status="open")
    open_orders = client.get_orders(req)
    for order in open_orders:
        client.cancel_order_by_id(order.id)
        print(f"✅ Cancelado: {order.symbol}")
except Exception as e:
    print(f"❌ Error: {e}")