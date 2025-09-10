# bot/risk.py
from typing import NamedTuple

class RiskParams(NamedTuple):
    take_profit_pct: float = 0.005     # 0.5% SCALPING - Take profit agresivo
    stop_loss_pct: float = 0.003       # 0.3% SCALPING - Stop loss ajustado  
    trail_stop_atr: float = 1.5        # 1.5x ATR para scalping
    max_risk_per_trade: float = 0.025  # 2.5% del equity - Riesgo controlado
    MAX_EXPOSURE_PER_SYMBOL = 0.20  # Máximo 20% del equity por símbolo
    max_gross_exposure: float = 0.3    # 30% del equity - CONSERVADOR


def compute_brackets(entry_price: float, side: str, params: RiskParams):
    """
    Calcula Take Profit y Stop Loss basado en porcentaje.
    """
    if side == "long":
        tp = entry_price * (1 + params.take_profit_pct)
        sl = entry_price * (1 - params.stop_loss_pct)
    elif side == "short":
        tp = entry_price * (1 - params.take_profit_pct)
        sl = entry_price * (1 + params.stop_loss_pct)
    else:
        tp, sl = None, None

    trail = None  # Puedes añadir trailing stop si lo necesitas

    return tp, sl, trail