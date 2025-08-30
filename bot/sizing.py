# bot/sizing.py
from .config import settings

def volatility_target_size(
    equity: float,
    price: float,
    atr: float,
    risk_per_trade: float = None
) -> float:
    """
    Calcula el tamaño de posición en unidades (BTC, SPY, etc.) basado en ATR.
    - equity: capital total
    - price: precio actual del activo
    - atr: rango verdadero promedio (en USD)
    - risk_per_trade: fracción del equity a arriesgar (default: settings.risk_per_trade)
    """
    if atr <= 0 or price <= 0:
        return 0.0

    risk_per_trade = risk_per_trade or settings.risk_per_trade
    capital_at_risk = equity * risk_per_trade
    risk_per_unit = atr  # riesgo por unidad en USD

    units = capital_at_risk / risk_per_unit
    return max(units, 0.0)


def kelly_cap(prob: float, win_loss: float = 1.0, cap: float = 0.02) -> float:
    """
    Calcula la fracción de Kelly acotada.
    - prob: probabilidad estimada de éxito
    - win_loss: razón ganancia/pérdida (ej: 2.0 = gano 2x lo que arriesgo)
    - cap: límite máximo de fracción (evita apuestas grandes)
    """
    edge = prob * (1 + win_loss) - 1  # bp - q
    frac = edge / max(win_loss, 1e-6)
    return max(min(frac, cap), 0.0)