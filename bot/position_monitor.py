# bot/position_monitor.py
import csv
import os
import time
import json
from datetime import datetime, timezone, timedelta
from alpaca.trading.client import TradingClient
from alpaca.data.historical import CryptoHistoricalDataClient, StockHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest, StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from typing import Optional
from .config import settings
from .trade_logger import log_trade_exit
from .telegram import alert_trade_exit, alert_risk_stop
from .util import logger
from .data import fetch_bars
from .features import make_features


TRADES_FILE = "trades_log.csv"
POSITION_TIMES_FILE = "bot/position_entry_times.json"

# Clientes Alpaca
trading_client = TradingClient(
    api_key=settings.alpaca_api_key,
    secret_key=settings.alpaca_secret_key,
    paper=(settings.mode == "paper")
)

# Clientes para datos históricos
crypto_client = CryptoHistoricalDataClient(
    api_key=settings.alpaca_api_key,
    secret_key=settings.alpaca_secret_key
)

stock_client = StockHistoricalDataClient(
    api_key=settings.alpaca_api_key,
    secret_key=settings.alpaca_secret_key
)

# Caché de precios
_price_cache = {}
_CACHE_TTL = 5  # segundos


# ⏰ POSITION ENTRY TIME TRACKING SYSTEM
def _load_position_times():
    """Cargar timestamps de entrada de posiciones desde archivo JSON."""
    try:
        if os.path.exists(POSITION_TIMES_FILE):
            with open(POSITION_TIMES_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"⚠️ Error cargando position times: {e}")
    return {}

def _save_position_times(position_times):
    """Guardar timestamps de entrada de posiciones a archivo JSON."""
    try:
        os.makedirs(os.path.dirname(POSITION_TIMES_FILE), exist_ok=True)
        with open(POSITION_TIMES_FILE, 'w') as f:
            json.dump(position_times, f, indent=2)
    except Exception as e:
        logger.error(f"❌ Error guardando position times: {e}")

def _track_new_position(symbol: str, position_times: dict):
    """Registra una nueva posición con timestamp actual."""
    current_time = time.time()
    position_times[symbol] = current_time
    logger.debug(f"🕐 Nueva posición registrada: {symbol} @ {datetime.fromtimestamp(current_time).strftime('%H:%M:%S')}")

def _get_position_age_minutes(symbol: str, position_times: dict) -> float:
    """Retorna la edad de la posición en minutos."""
    if symbol not in position_times:
        return 0.0
    age_seconds = time.time() - position_times[symbol]
    return age_seconds / 60.0

def _cleanup_closed_positions(current_symbols: set, position_times: dict) -> bool:
    """Limpia posiciones cerradas del tracking. Retorna True si hubo cambios."""
    initial_count = len(position_times)
    symbols_to_remove = [sym for sym in position_times.keys() if sym not in current_symbols]
    
    for symbol in symbols_to_remove:
        del position_times[symbol]
        logger.debug(f"🧹 Posición cerrada removida del tracking: {symbol}")
    
    return len(position_times) != initial_count

def normalize_symbol(symbol: str) -> str:
    if "/" in symbol:
        return symbol
    if symbol.endswith("USD"):
        base = symbol.replace("USD", "")
        return f"{base}/USD"
    return symbol


def _get_current_price(symbol: str) -> Optional[float]:
    """
    Obtiene el precio actual usando barras de 1 minuto (alternativa a LatestTradeRequest).
    """
    now = time.time()
    cache_key = f"{symbol}_price"
    if cache_key in _price_cache:
        price, timestamp = _price_cache[cache_key]
        if now - timestamp < _CACHE_TTL:
            return price

    try:
        if "/" in symbol:  # Cripto
            request = CryptoBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=getattr(TimeFrame, 'Minute'),
                limit=1
            )
            bars = crypto_client.get_crypto_bars(request)
            
            # Verificar si bars tiene atributo df y si está vacío
            bars_df = getattr(bars, 'df', None)
            if bars_df is None or bars_df.empty:
                logger.warning(f"⚠️ No hay datos de precio para {symbol} (cripto)")
                return None
            price = float(bars_df.iloc[-1]["close"])
        else:  # Acciones
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=getattr(TimeFrame, 'Minute'),
                limit=1
            )
            bars = stock_client.get_stock_bars(request)
            
            # Verificar si bars tiene atributo df y si está vacío
            bars_df = getattr(bars, 'df', None)
            if bars_df is None or bars_df.empty:
                logger.warning(f"⚠️ No hay datos de precio para {symbol} (probablemente mercado cerrado)")
                return None
            # Manejar MultiIndex si existe
            df = bars_df
            if hasattr(df.index, 'levels'):  # MultiIndex
                df = df.reset_index()
            price = float(df.iloc[-1]["close"])

        _price_cache[cache_key] = (price, now)
        return price
    except Exception as e:
        logger.error(f"❌ No se pudo obtener precio de {symbol}: {e}")
        return None


def monitor_closed_positions(clf):
    """
    Monitorea posiciones continuamente y cierra cuando:
    1. Take Profit / Stop Loss se activan
    2. Modelo ML predice reversión de señal
    3. Sistema TIME-BASED EXIT para rotación de capital
    
    Ejecuta en un bucle continuo cada 10 segundos.
    """
    logger.info("🔄 Position Monitor iniciado - monitoreando posiciones cada 10 segundos...")
    logger.info(f"⏰ TIME-BASED EXIT configurado: {settings.max_position_time_normal}min estancadas, {settings.max_position_time_force}min forzado")
    
    # Cargar timestamps de posiciones
    position_times = _load_position_times()
    
    while True:
        try:
            # 1. Verificar stop diario por pérdida
            try:
                account = trading_client.get_account()
                equity = float(getattr(account, 'equity', 0))
                last_equity = float(getattr(account, "last_equity", equity))
                daily_pnl = equity - last_equity
                daily_pnl_pct = daily_pnl / last_equity if last_equity != 0 else 0.0

                if daily_pnl_pct < -0.10:  # -10% (aumentado para operar hoy)
                    msg = f"🛑 Pérdida diaria de {daily_pnl_pct:.2%} ≥ límite de 10%"
                    logger.critical(f"🚨 {msg}")
                    alert_risk_stop(msg)
                    return "STOP"
            except Exception as e:
                logger.error(f"❌ No se pudo calcular P&L diario: {e}")

            # 2. Obtener posiciones abiertas
            try:
                positions = trading_client.get_all_positions()
                if not positions:
                    # Limpiar position_times si no hay posiciones
                    if position_times:
                        position_times.clear()
                        _save_position_times(position_times)
                        logger.debug("🧹 Position times limpiados - sin posiciones abiertas")
                    
                    logger.debug("💤 Sin posiciones abiertas para monitorear")
                    time.sleep(10)  # Esperar 10 segundos antes de la próxima verificación
                    continue
                else:
                    logger.info(f"👁️ Monitoreando {len(positions)} posiciones abiertas...")
            except Exception as e:
                logger.error(f"❌ No se pudieron obtener posiciones: {e}")
                time.sleep(10)
                continue

            # 3. Actualizar tracking de posiciones
            current_symbols = set()
            position_times_changed = False
            
            for pos in positions:
                symbol = normalize_symbol(getattr(pos, 'symbol', ''))
                current_symbols.add(symbol)
                
                # Trackear nueva posición si no existe
                if symbol not in position_times:
                    _track_new_position(symbol, position_times)
                    position_times_changed = True
            
            # Limpiar posiciones cerradas del tracking
            if _cleanup_closed_positions(current_symbols, position_times):
                position_times_changed = True
            
            # Guardar cambios en position_times si hubo modificaciones
            if position_times_changed:
                _save_position_times(position_times)

            # 4. Revisar cada posición (TP/SL, ML Reversal, TIME-BASED EXIT)
            for pos in positions:
                symbol = normalize_symbol(getattr(pos, 'symbol', ''))
                qty = float(getattr(pos, 'qty', 0))
                entry_price = float(getattr(pos, 'avg_entry_price', 0))
                current_price = _get_current_price(symbol)

                if not current_price:
                    continue

                # --- OBTENER DATOS DE LA POSICIÓN ---
                should_close = False
                reason = ""
                current_side = "long" if qty > 0 else "short"
                
                # Calcular P&L actual
                if qty > 0:  # LONG
                    pnl = (current_price - entry_price) * qty
                    pnl_pct = (current_price - entry_price) / entry_price
                else:  # SHORT
                    pnl = (entry_price - current_price) * abs(qty)
                    pnl_pct = (entry_price - current_price) / entry_price
                
                # Obtener edad de la posición
                position_age_minutes = _get_position_age_minutes(symbol, position_times)
                
                # --- PRIORITY 1: TIME-BASED EXIT SYSTEM (antes que TP/SL tradicional) ---
                
                # A) CIERRE FORZADO (60-75 minutos): Todas las posiciones excepto excepciones
                if position_age_minutes >= settings.max_position_time_force:
                    # EXCEPCIÓN: Mantener si P&L > 1.2% Y señal ML sigue fuerte
                    keep_position = False
                    if pnl_pct > settings.min_pnl_keep_long:
                        try:
                            # Verificar si la señal ML sigue fuerte
                            df = fetch_bars(symbol, start="2023-01-01")
                            if not df.empty and len(df) >= 100:
                                feats = make_features(df, symbol=symbol)
                                latest = feats.iloc[-1]
                                
                                missing = [f for f in clf.feature_names_in_ if f not in latest.index]
                                if not missing:
                                    X = latest[clf.feature_names_in_].to_frame().T
                                    predicted_signal = clf.predict(X)[0]
                                    
                                    # Mantener si señal sigue alineada con posición actual
                                    if current_side == "long" and predicted_signal > 0.05:
                                        keep_position = True
                                    elif current_side == "short" and predicted_signal < -0.05:
                                        keep_position = True
                        except:
                            pass  # Si hay error ML, no mantener la posición
                    
                    if not keep_position:
                        should_close = True
                        reason = f"🕐 CIERRE FORZADO: {position_age_minutes:.0f}min ≥ {settings.max_position_time_force}min"
                    else:
                        logger.info(f"⚡ {symbol}: MANTENIDO tras {position_age_minutes:.0f}min (P&L: {pnl_pct:+.2%}, señal fuerte)")
                
                # B) CIERRE ESTANCADO (30-45 minutos): Posiciones que no van a ningún lado
                elif position_age_minutes >= settings.max_position_time_normal:
                    # Condición 1: P&L estancado (-0.3% a +0.7%)
                    is_stagnant = settings.stagnant_pnl_min <= pnl_pct <= settings.stagnant_pnl_max
                    
                    # Condición 2: Señal ML se debilitó significativamente
                    ml_weakened = False
                    try:
                        df = fetch_bars(symbol, start="2023-01-01")
                        if not df.empty and len(df) >= 100:
                            feats = make_features(df, symbol=symbol)
                            latest = feats.iloc[-1]
                            
                            missing = [f for f in clf.feature_names_in_ if f not in latest.index]
                            if not missing:
                                X = latest[clf.feature_names_in_].to_frame().T
                                predicted_signal = clf.predict(X)[0]
                                
                                # Detectar debilitamiento de señal
                                if current_side == "long" and predicted_signal < 0.02:  # Bajó de alcista fuerte
                                    ml_weakened = True
                                elif current_side == "short" and predicted_signal > -0.02:  # Subió de bajista fuerte
                                    ml_weakened = True
                    except:
                        pass
                    
                    if is_stagnant or ml_weakened:
                        should_close = True
                        condition = "estancado" if is_stagnant else "señal débil"
                        reason = f"🕐 CIERRE POR TIEMPO: {position_age_minutes:.0f}min, {condition}"
                
                # --- PRIORITY 2: TRADITIONAL TP/SL/ML (solo si NO hay cierre por tiempo) ---
                if not should_close:
                    
                    # 1. TAKE PROFIT: Cerrar si ganancia >= 1.5%
                    if pnl_pct >= settings.take_profit_pct:
                        should_close = True
                        reason = f"TAKE PROFIT alcanzado: {pnl_pct:.2%} >= {settings.take_profit_pct:.2%}"
                    
                    # 2. STOP LOSS: Cerrar si pérdida >= 0.7%
                    elif pnl_pct <= -settings.stop_loss_pct:
                        should_close = True
                        reason = f"STOP LOSS activado: {pnl_pct:.2%} <= -{settings.stop_loss_pct:.2%}"
                    
                    # 3. REVERSIÓN DE SEÑAL ML (solo si NO se activó TP/SL)
                    else:
                        try:
                            df = fetch_bars(symbol, start="2023-01-01")
                            if not df.empty and len(df) >= 100:
                                feats = make_features(df, symbol=symbol)
                                latest = feats.iloc[-1]

                                # Validar features
                                missing = [f for f in clf.feature_names_in_ if f not in latest.index]
                                if not missing:  # Solo si NO faltan features
                                    X = latest[clf.feature_names_in_].to_frame().T
                                    predicted_signal = clf.predict(X)[0]

                                    # Evaluar reversión de señal
                                    if current_side == "long" and predicted_signal < -0.05:
                                        should_close = True
                                        reason = f"Reversión bajista: {predicted_signal:+.3f}"
                                    elif current_side == "short" and predicted_signal > 0.05:
                                        should_close = True
                                        reason = f"Reversión alcista: {predicted_signal:+.3f}"
                                else:
                                    logger.debug(f"⚠️ Features faltantes para {symbol}: {missing[:3]}... (TP/SL aún evalúa)")
                        except Exception as e:
                            logger.debug(f"⚠️ Error ML para {symbol}: {e} (TP/SL aún funciona)")

                # EJECUTAR CIERRE si cualquier condición se cumplió
                if should_close:
                    # Formateo inteligente para P&L pequeños (cryptos de bajo valor)
                    pnl_str = f"${pnl:+.6f}" if abs(pnl) < 0.01 else f"${pnl:+.2f}"
                    price_str = f"${current_price:.6f}" if current_price < 0.01 else f"${current_price:.2f}"
                    logger.info(f"🔄 {reason}. Cerrando {current_side} en {symbol} @ {price_str} | P&L: {pnl_str} ({pnl_pct:+.2%})")
                    _close_position(pos, symbol, qty, current_price, pnl, pnl_pct, reason)

        except Exception as e:
            logger.error(f"💥 Error en cycle de position monitor: {e}")
            
        # Esperar 10 segundos antes del próximo ciclo
        logger.debug("⏱️ Position Monitor: esperando 10 segundos...")
        time.sleep(10)


def _close_position(pos, symbol: str, qty: float, exit_price: float, pnl: float, pnl_pct: float, reason: str):
    """Cierra una posición usando la función mejorada de execution.py y registra el cierre."""
    try:
        # Import the enhanced close_position function
        from .execution import close_position
        
        side_str = "long" if qty > 0 else "short"
        
        # Use the enhanced close_position function with PDT and balance protection
        success = close_position(symbol, force_close=False)
        
        if success:
            # Formateo inteligente para P&L pequeños (cryptos de bajo valor)
            pnl_str = f"${pnl:+.6f}" if abs(pnl) < 0.01 else f"${pnl:+.2f}"
            logger.info(f"✅ Cerrada {side_str} {abs(qty)} {symbol} | P&L: {pnl_str} ({pnl_pct:+.2%}) [{reason}]")
            alert_trade_exit(symbol, side_str, abs(qty), exit_price, pnl, pnl_pct)
            log_trade_exit(symbol, abs(qty), exit_price, pnl, pnl_pct)
        else:
            # Handle failed closure gracefully
            is_crypto = "/" in symbol
            asset_type = "CRYPTO" if is_crypto else "STOCK"
            
            if not is_crypto:
                logger.warning(f"⏳ {asset_type} {symbol}: Cierre bloqueado (probablemente PDT) - esperando hasta mañana")
            else:
                logger.warning(f"⚠️ {asset_type} {symbol}: Cierre falló - balance insuficiente o error de sincronización")
                
    except Exception as e:
        logger.error(f"❌ Error crítico cerrando {symbol}: {e}")