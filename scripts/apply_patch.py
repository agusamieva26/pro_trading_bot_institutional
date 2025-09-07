# apply_patch.py
import os, pathlib, sys, textwrap

ROOT = pathlib.Path(__file__).parent

FILES = {
    # =============================
    # bot/config.py
    # =============================
    "bot/config.py": """# bot/config.py
from dataclasses import dataclass

@dataclass(frozen=True)
class BrokerCaps:
    supports_fractional_long_equities: bool = True
    supports_fractional_short_equities: bool = False
    min_notional_equity: float = 1.0
    min_notional_crypto: float = 1.0

BROKER = BrokerCaps()

MIN_RISK_PER_TRADE = 0.002   # 0.2%
MAX_RISK_PER_TRADE = 0.01    # 1.0%
MAX_GROSS_EXPOSURE = 0.30    # 0.3x
MAX_NOTIONAL_PER_ORDER_PCT_CASH = 0.95  # seguridad
""",

    # =============================
    # bot/execution.py
    # =============================
    "bot/execution.py": """# bot/execution.py
from __future__ import annotations
import math
import logging
from typing import Optional, Literal
from bot.config import BROKER, MAX_NOTIONAL_PER_ORDER_PCT_CASH

logger = logging.getLogger(__name__)

Side = Literal["buy", "sell"]
AssetClass = Literal["crypto", "equity", "etf"]

class ExecutionError(Exception):
    pass

def _min_notional(asset_class: AssetClass) -> float:
    return BROKER.min_notional_crypto if asset_class == "crypto" else BROKER.min_notional_equity

def _is_fractional(qty: float) -> bool:
    return qty < 1 and not math.isclose(qty, 1.0)

def _short_restricted(is_short: bool, asset_class: AssetClass, qty: float) -> bool:
    if not is_short:
        return False
    if asset_class in ("equity", "etf") and _is_fractional(qty) and not BROKER.supports_fractional_short_equities:
        return True
    return False

def compute_qty_from_notional(price: float, notional: float) -> float:
    if price <= 0:
        raise ExecutionError("Precio inválido para calcular cantidad.")
    return notional / price

def place_order(
    symbol: str,
    side: Side,
    price: float,
    available_cash: float,
    desired_notional: Optional[float] = None,
    desired_qty: Optional[float] = None,
    asset_class: AssetClass = "crypto",
    allow_fractional: bool = True,
) -> dict:
    if desired_notional is None and desired_qty is None:
        raise ExecutionError("Debes especificar desired_notional o desired_qty.")
    cash_cap = max(0.0, available_cash * MAX_NOTIONAL_PER_ORDER_PCT_CASH)
    if desired_notional is None:
        desired_notional = desired_qty * price
    notional = min(desired_notional, cash_cap)
    if notional < _min_notional(asset_class):
        logger.warning(f"Saldo insuficiente o notional muy bajo para {symbol}. Skip.")
        raise ExecutionError("Notional por debajo del mínimo.")
    qty = compute_qty_from_notional(price, notional)
    is_short = (side == "sell")
    if _short_restricted(is_short, asset_class, qty):
        logger.warning(f"Skip {symbol}: short fraccionado no permitido por broker.")
        raise ExecutionError("Short fraccionado no permitido.")
    if not allow_fractional and asset_class in ("equity", "etf"):
        qty = math.floor(qty)
        if qty < 1:
            logger.warning(f"Cantidad < 1 tras redondeo en {symbol}. Skip.")
            raise ExecutionError("Cantidad insuficiente (no fraccional).")
    order = {
        "symbol": symbol,
        "side": side,
        "qty": qty,
        "price": price,
        "notional": qty * price,
        "status": "validated"
    }
    logger.info(f"Orden validada {side} {symbol} qty={qty:.6f} (~${qty*price:,.2f})")
    return order
""",

    # =============================
    # bot/position_monitor.py
    # =============================
    "bot/position_monitor.py": """# bot/position_monitor.py
import logging
from typing import Literal, Optional

logger = logging.getLogger(__name__)

AssetClass = Literal["crypto", "equity", "etf"]

class PriceFeed:
    def __init__(self, crypto_client=None, stock_client=None):
        self.crypto_client = crypto_client
        self.stock_client = stock_client
        self._boot()

    def _boot(self):
        try:
            from alpaca.data.historical import CryptoHistoricalDataClient, StockHistoricalDataClient
            from alpaca.data.requests import CryptoLatestTradeRequest, StockLatestTradeRequest
            self.CryptoHistoricalDataClient = CryptoHistoricalDataClient
            self.StockHistoricalDataClient = StockHistoricalDataClient
            self.CryptoLatestTradeRequest = CryptoLatestTradeRequest
            self.StockLatestTradeRequest = StockLatestTradeRequest
            if self.crypto_client is None:
                self.crypto_client = CryptoHistoricalDataClient()
            if self.stock_client is None:
                self.stock_client = StockHistoricalDataClient()
            logger.info("PriceFeed: usando alpaca-py historical clients.")
        except Exception:
            logger.error("No se pudo inicializar alpaca-py data clients. Instala alpaca-py >= 0.16.")
            raise

    def get_price(self, symbol: str, asset_class: AssetClass) -> Optional[float]:
        try:
            if asset_class == "crypto":
                req = self.CryptoLatestTradeRequest(symbol_or_symbols=symbol)
                trade = self.crypto_client.get_latest_crypto_trades(req)
                t = trade[symbol]
                return float(t.price)
            else:
                req = self.StockLatestTradeRequest(symbol_or_symbols=symbol)
                trade = self.stock_client.get_latest_stock_trades(req)
                t = trade[symbol]
                return float(t.price)
        except Exception as e:
            logger.error(f"No se pudo obtener precio de {symbol}: {e}")
            return None

price_feed = PriceFeed()
""",

    # =============================
    # bot/auto_tuner.py
    # =============================
    "bot/auto_tuner.py": """# bot/auto_tuner.py
import logging
from dataclasses import dataclass
from bot.config import MIN_RISK_PER_TRADE, MAX_RISK_PER_TRADE, MAX_GROSS_EXPOSURE

logger = logging.getLogger(__name__)

@dataclass
class RiskParams:
    risk_per_trade: float
    max_exposure: float

def tune_risk_parameters(pnl_last_24h: float, num_trades: int, current: RiskParams) -> RiskParams:
    r = current.risk_per_trade
    e = current.max_exposure
    if num_trades >= 5 and pnl_last_24h > 0:
        r *= 1.10
    elif pnl_last_24h < 0:
        r *= 0.90
    r = max(MIN_RISK_PER_TRADE, min(MAX_RISK_PER_TRADE, r))
    e = min(MAX_GROSS_EXPOSURE, e)
    tuned = RiskParams(risk_per_trade=r, max_exposure=e)
    logger.info(f"Auto-ajuste aplicado: risk_per_trade={tuned.risk_per_trade*100:.2f}%, max_exposure={tuned.max_exposure:.2f}x")
    return tuned
""",

    # =============================
    # bot/exposure.py
    # =============================
    "bot/exposure.py": """# bot/exposure.py
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

def get_total_exposure(positions: List[Dict]) -> float:
    if not positions:
        return 0.0
    equity = max(1e-6, positions[0].get("equity", 0.0))
    gross = sum(abs(p.get("notional", 0.0)) for p in positions) / equity
    logger.info(f"Exposición bruta: {gross:.2f}x")
    return gross
""",
}

def write_file(path_rel: str, content: str):
    p = ROOT / path_rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    print(f"✔ Escrito {p}")

def main():
    if not (ROOT / "bot").exists():
        print("❌ No parece la raíz del proyecto (falta carpeta bot).")
        sys.exit(1)
    for rel, content in FILES.items():
        write_file(rel, textwrap.dedent(content).strip() + "\\n")
    print("✅ Parche aplicado.")

if __name__ == "__main__":
    main()
