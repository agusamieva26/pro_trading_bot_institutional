# bot/data.py
import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient, CryptoHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.common.exceptions import APIError
from .config import settings
from .util import logger


# ------------------------------------------------------------------
# Clientes autenticados (globales del módulo)
# ------------------------------------------------------------------
stock_client = StockHistoricalDataClient(
    api_key=settings.alpaca_api_key,
    secret_key=settings.alpaca_secret_key
)

crypto_client = CryptoHistoricalDataClient(
    api_key=settings.alpaca_api_key,
    secret_key=settings.alpaca_secret_key
)


# ------------------------------------------------------------------
# Mapeo de marcos de tiempo
# ------------------------------------------------------------------
def _tf():
    tf_map = {
        "1Min":  TimeFrame.Minute,
        "5Min":  TimeFrame(5, TimeFrameUnit.Minute),
        "15Min": TimeFrame(15, TimeFrameUnit.Minute),
        "1Hour": TimeFrame.Hour,
        "1Day":  TimeFrame.Day,
    }
    return tf_map.get(settings.bar_timeframe, TimeFrame.Hour)


# ------------------------------------------------------------------
# Descarga de barras con fechas UTC correctas
# ------------------------------------------------------------------
def fetch_bars(symbol: str, start: str | None = None, end: str | None = None, min_bars: int = 100):
    """
    Descarga barras desde Alpaca. Si hay pocas, retrocede más en el tiempo automáticamente.
    Compatible con acciones y criptos.
    """
    lookback_days = 30  # Solo último mes para velocidad
    bars = pd.DataFrame()

    max_attempts = 3  # Limite de intentos para evitar loop infinito
    attempt = 0
    
    while attempt < max_attempts:
        attempt += 1
        start_dt = pd.Timestamp(start, tz="UTC") if start else (pd.Timestamp.utcnow() - pd.Timedelta(days=lookback_days))
        end_dt   = pd.Timestamp(end, tz="UTC") if end else (pd.Timestamp.utcnow() - pd.Timedelta(minutes=16))

        try:
            if "/" in symbol:  # cripto
                req = CryptoBarsRequest(
                    symbol_or_symbols=symbol,
                    start=start_dt,
                    end=end_dt,
                    timeframe=_tf()
                )
                df = crypto_client.get_crypto_bars(req).df
            else:  # acción
                req = StockBarsRequest(
                    symbol_or_symbols=symbol,
                    start=start_dt,
                    end=end_dt,
                    timeframe=_tf(),
                    adjustment="raw",
                    feed="iex"
                )
                df = stock_client.get_stock_bars(req).df

            if df.empty:
                logger.warning(f"⚠️ No hay datos para {symbol}")
                return df

            if isinstance(df.index, pd.MultiIndex):
                df = df.xs(symbol, level=0)

            bars = df.sort_index().rename(columns=str.lower)

        except APIError as e:
            logger.error(f"❌ Alpaca API error: {e}")
            return pd.DataFrame()
        except Exception as e:
            logger.exception(f"💥 Error construyendo petición de datos ({symbol}): {e}")
            return pd.DataFrame()

        if len(bars) >= min_bars or lookback_days > 3650 or attempt >= max_attempts:
            if len(bars) < min_bars:
                logger.warning(f"⚠️ Solo {len(bars)} velas para {symbol}, por debajo del mínimo {min_bars}.")
            return bars
        else:
            logger.info(f"🔍 Solo {len(bars)} velas para {symbol}, retrocediendo más... (intento {attempt}/{max_attempts})")
            lookback_days *= 2
    
    # Si llegamos aquí, se agotaron los intentos
    logger.warning(f"⚠️ Máximo de intentos alcanzado para {symbol}, devolviendo datos disponibles")
    return bars

# ------------------------------------------------------------------
# Wrapper para obtener las últimas n barras (para alertas)
# ------------------------------------------------------------------
def fetch_last_bars(symbol: str, n: int = 1):
    """
    Devuelve las últimas 'n' barras de un símbolo sin pasar 'limit' directamente.
    Compatible con Alpaca v2.
    """
    bars = fetch_bars(symbol, start=None, end=None, min_bars=n)
    if bars.empty:
        return pd.DataFrame()
    return bars.tail(n)