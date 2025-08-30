# bot/util/market.py
import datetime as dt
import pytz

def is_stock_market_open() -> bool:
    """Devuelve True si el mercado de acciones de EE.UU. está abierto ahora."""
    eastern = pytz.timezone("US/Eastern")
    now = dt.datetime.now(eastern)

    # Días hábiles: lunes(0) a viernes(4)
    if now.weekday() > 4:
        return False

    # Horario regular del mercado: 9:30 a 16:00 hora NY
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)

    return market_open <= now <= market_close
