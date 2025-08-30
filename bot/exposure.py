# bot/exposure.py
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOrdersRequest
from alpaca.trading.enums import QueryOrderStatus
from .config import settings
from .util import logger

def get_total_exposure():
    """
    Calcula la exposición bruta total como porcentaje del equity.
    Ej: 1.2 = 120% del equity en posiciones abiertas.
    """
    client = TradingClient(
        api_key=settings.alpaca_api_key,
        secret_key=settings.alpaca_secret_key,
        paper=(settings.mode == "paper")
    )
    try:
        positions = client.get_all_positions()
        equity = float(client.get_account().equity)
        if equity <= 0:
            logger.error("Equity <= 0, no se puede calcular exposición")
            return 0.0
        gross_value = sum(abs(float(pos.market_value)) for pos in positions)
        exposure_ratio = gross_value / equity
        logger.info(f"📊 Exposición bruta: {exposure_ratio:.2f}x (${gross_value:.2f}) | Equity: ${equity:.2f}")
        return exposure_ratio
    except Exception as e:
        logger.error(f"❌ Error al calcular exposición: {e}")
        return 0.0


def has_open_order(symbol: str) -> bool:
    """
    Verifica si hay órdenes abiertas para el símbolo.
    """
    client = TradingClient(
        api_key=settings.alpaca_api_key,
        secret_key=settings.alpaca_secret_key,
        paper=(settings.mode == "paper")
    )
    base_symbol = symbol.replace("/", "")
    try:
        req = GetOrdersRequest(status=QueryOrderStatus.OPEN, symbols=[base_symbol])
        orders = client.get_orders(req)
        return len(orders) > 0
    except Exception as e:
        logger.warning(f"⚠️ No se verificaron órdenes abiertas para {symbol}: {e}")
        return False