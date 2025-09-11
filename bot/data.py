# bot/data.py
import pandas as pd
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from alpaca.data.historical import StockHistoricalDataClient, CryptoHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.common.exceptions import APIError
from .config import settings
from .util import logger


# ------------------------------------------------------------------
# Caché de datos y clientes autenticados
# ------------------------------------------------------------------
CACHE_DIR = "data_cache"
os.makedirs(CACHE_DIR, exist_ok=True)
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
def fetch_all_bars(symbols: list[str], start: str = None, end: str = None, min_bars: int = 50):
    """
    Descarga datos para múltiples símbolos en paralelo usando ThreadPoolExecutor.
    Optimizada para usar caché incremental: solo descarga si faltan datos o hay huecos.
    """
    results = {}
    max_workers = min(4, len(symbols))
    logger.info(f"📡 Descargando datos de {len(symbols)} símbolos en paralelo ({max_workers} hilos)...")

    def fetch_with_retry(sym, retries=3, delay=1.0):
        cache_file = os.path.join(CACHE_DIR, f"{sym.replace('/', '_')}.parquet")
        cached_df = pd.DataFrame()

        # 1️⃣ Cargar caché si existe
        if os.path.exists(cache_file):
            try:
                cached_df = pd.read_parquet(cache_file).sort_index()
                # Si tengo suficientes datos en cache, usar esos
                if len(cached_df) >= min_bars:
                    logger.debug(f"✅ {sym}: {len(cached_df)} velas en caché")
                    return cached_df
            except Exception as e:
                logger.warning(f"⚠️ Error leyendo caché de {sym}: {e}")
                cached_df = pd.DataFrame()

        # 2️⃣ Descarga incremental con reintentos
        for attempt in range(retries):
            try:
                df = fetch_bars(sym, start, end, min_bars)
                
                # Guardar en caché si descarga exitosa
                if not df.empty:
                    try:
                        df.to_parquet(cache_file)
                        logger.debug(f"💾 {sym}: datos guardados en caché")
                    except Exception as e:
                        logger.warning(f"⚠️ No se pudo guardar caché de {sym}: {e}")
                
                return df
            except APIError as e:
                if "too many requests" in str(e).lower() or "rate limit" in str(e).lower():
                    wait_time = delay * (2 ** attempt)
                    logger.warning(f"⏳ Rate limit para {sym}, reintentando en {wait_time:.1f}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"💥 Error API {sym}: {e}")
                    break
            except Exception as e:
                logger.error(f"💥 Error inesperado con {sym}: {e}")
                break
        
        # Si falla todo, devolver caché (aunque esté vacío)
        return cached_df

    # 3️⃣ Ejecutar en paralelo
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_with_retry, sym): sym for sym in symbols}

        for future in as_completed(futures):
            sym = futures[future]
            try:
                df = future.result()
                if not df.empty:
                    results[sym] = df
                else:
                    logger.warning(f"⚠️ {sym} sin datos")
                    results[sym] = pd.DataFrame()
            except Exception as e:
                logger.error(f"💥 Error descargando {sym}: {e}")
                results[sym] = pd.DataFrame()

            # Pausa mayor para evitar rate limiting de Alpaca
            time.sleep(0.5)

    successful = len([v for v in results.values() if not v.empty])
    logger.info(f"✅ Descarga completada: {successful}/{len(symbols)} símbolos con datos.")
    return results

def fetch_last_bars(symbol: str, n: int = 1):
    """
    Devuelve las últimas 'n' barras de un símbolo sin pasar 'limit' directamente.
    Compatible con Alpaca v2.
    """
    bars = fetch_bars(symbol, start=None, end=None, min_bars=n)
    if bars.empty:
        return pd.DataFrame()
    return bars.tail(n)