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
from alpaca.data.enums import DataFeed
from typing import Optional
from .config import settings
from .trade_logger import log_trade_exit
from .telegram import alert_trade_exit, alert_risk_stop
from .util import logger, should_skip_realtime_pricing, get_cache_ttl_for_symbol
from .symbol_manager import symbol_manager
from .data import fetch_bars
from .symbol_configs import get_symbol_config
from .features import make_features
from .liquidity_unlocker import liquidity_unlocker


TRADES_FILE = "trades_log.csv"
POSITION_TIMES_FILE = "bot/position_entry_times.json"
POSITION_STATE_FILE = "bot/position_states.json"

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

# Caché de precios mejorado con TTL dinámico
_price_cache = {}
_LAST_KNOWN_PRICES = {}  # Fallback cache for when real-time data fails

# 🔇 SPAM PREVENTION: Track which symbols have already shown warnings
_WARNED_SYMBOLS = set()  # Symbols that already showed "no cached price" warning
_MARKET_CLOSED_SYMBOLS = set()  # Track symbols outside market hours for grouped message


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

# 🎯 POSITION STATE TRACKING SYSTEM (for trailing stops & partial profits)
def _load_position_states():
    """Cargar estados de posiciones desde archivo JSON."""
    try:
        if os.path.exists(POSITION_STATE_FILE):
            with open(POSITION_STATE_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"⚠️ Error cargando position states: {e}")
    return {}

def _save_position_states(position_states):
    """Guardar estados de posiciones a archivo JSON."""
    try:
        os.makedirs(os.path.dirname(POSITION_STATE_FILE), exist_ok=True)
        with open(POSITION_STATE_FILE, 'w') as f:
            json.dump(position_states, f, indent=2)
    except Exception as e:
        logger.error(f"❌ Error guardando position states: {e}")

def _init_new_position_state(symbol: str, entry_price: float, quantity: float, position_states: dict):
    """Inicializa el estado de una nueva posición."""
    position_states[symbol] = {
        "trailing_activated": False,
        "max_price_reached": entry_price,
        "partial_profit_taken": False,
        "original_quantity": abs(quantity),
        "entry_price": entry_price
    }
    logger.debug(f"🎯 Estado inicial posición: {symbol} @ ${entry_price:.4f} (qty: {abs(quantity):.6f})")

def _update_position_state(symbol: str, current_price: float, position_states: dict) -> dict:
    """Actualiza el estado de la posición y retorna información de trailing/partial."""
    if symbol not in position_states:
        return {"trailing_stop_triggered": False, "partial_profit_triggered": False}
    
    state = position_states[symbol]
    entry_price = state["entry_price"]
    current_pnl_pct = (current_price - entry_price) / entry_price
    
    # Actualizar precio máximo alcanzado (solo para LONG, para SHORT sería mínimo)
    if current_price > state["max_price_reached"]:
        state["max_price_reached"] = current_price
    
    result = {"trailing_stop_triggered": False, "partial_profit_triggered": False}
    
    # 1. Verificar si activar trailing stop (+2%)
    if not state["trailing_activated"] and current_pnl_pct >= settings.trailing_activation_pct:
        state["trailing_activated"] = True
        logger.info(f"🎯 TRAILING ACTIVADO: {symbol} @ {current_pnl_pct:+.2%} (≥{settings.trailing_activation_pct:.1%})")
    
    # 2. Verificar trailing stop trigger (si está activado)
    if state["trailing_activated"]:
        # Calcular precio de trailing stop (-1% desde el máximo)
        trailing_stop_price = state["max_price_reached"] * (1 - settings.trailing_distance_pct)
        if current_price <= trailing_stop_price:
            result["trailing_stop_triggered"] = True
            decline_pct = (state["max_price_reached"] - current_price) / state["max_price_reached"]
            logger.info(f"🎯 TRAILING STOP TRIGGER: {symbol} bajó {decline_pct:.2%} desde máximo ${state['max_price_reached']:.4f}")
    
    # 3. Verificar cierre parcial (+3%)
    if not state["partial_profit_taken"] and current_pnl_pct >= settings.partial_profit_pct:
        result["partial_profit_triggered"] = True
        state["partial_profit_taken"] = True
        logger.info(f"💎 PARTIAL PROFIT TRIGGER: {symbol} @ {current_pnl_pct:+.2%} (≥{settings.partial_profit_pct:.1%})")
    
    return result

def _cleanup_position_states(current_symbols: set, position_states: dict) -> bool:
    """Limpia estados de posiciones cerradas. Retorna True si hubo cambios."""
    initial_count = len(position_states)
    symbols_to_remove = [sym for sym in position_states.keys() if sym not in current_symbols]
    
    for symbol in symbols_to_remove:
        del position_states[symbol]
        logger.debug(f"🧹 Estado de posición cerrada removido: {symbol}")
    
    return len(position_states) != initial_count

def _execute_partial_close(pos, symbol: str, qty: float, current_price: float, pnl_pct: float, position_states: dict) -> bool:
    """Ejecuta cierre parcial del 50% de la posición."""
    try:
        # Import the close_position function for partial close
        from .execution import place_order
        
        # Calcular cantidad para vender (50% de la posición)
        original_qty = abs(qty)
        partial_qty = original_qty * 0.5
        side_str = "long" if qty > 0 else "short"
        sell_side = "sell" if qty > 0 else "buy"  # Para short, necesitamos "buy" para cerrar
        
        is_crypto = "/" in symbol
        
        # Ejecutar la venta parcial
        success = place_order(
            symbol=symbol,
            qty=partial_qty,
            side=sell_side,
            price=current_price,
            fractional=True,
            is_crypto=is_crypto
        )
        
        if success:
            # Calcular P&L del 50% vendido
            entry_price = position_states[symbol]["entry_price"]
            partial_pnl = (current_price - entry_price) * partial_qty if qty > 0 else (entry_price - current_price) * partial_qty
            
            logger.info(f"💎 CIERRE PARCIAL 50%: {side_str} {partial_qty:.6f} {symbol} @ ${current_price:.4f} | P&L: ${partial_pnl:+.2f} ({pnl_pct:+.2%})")
            
            # Actualizar estado: activar trailing para el 50% restante
            position_states[symbol]["trailing_activated"] = True
            position_states[symbol]["original_quantity"] = original_qty / 2  # Actualizar a 50% restante
            
            # Enviar notificación
            from .telegram import alert_trade_exit
            alert_trade_exit(symbol, f"PARTIAL {side_str}", partial_qty, current_price, partial_pnl, pnl_pct)
            
            # Log trade exit para el cierre parcial
            from .trade_logger import log_trade_exit
            log_trade_exit(symbol, partial_qty, current_price, partial_pnl, pnl_pct)
            
            return True
        else:
            logger.warning(f"⚠️ Fallo en cierre parcial {symbol}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error ejecutando cierre parcial {symbol}: {e}")


def _intelligent_crypto_closure(positions, exposure_ratio: float):
    """
    🚨 CRISIS MODE: Cierre selectivo inteligente de posiciones crypto.
    Evalúa potencial y cierra las peores primero para reducir exposición.
    """
    try:
        # Filtrar solo posiciones crypto
        crypto_positions = []
        for pos in positions:
            symbol = normalize_symbol(getattr(pos, 'symbol', ''))
            if symbol_manager.is_crypto(symbol):
                crypto_positions.append((pos, symbol))
        
        if not crypto_positions:
            return
        
        from .config import settings
        logger.critical(f"🚨 CRISIS MODE: Exposición {exposure_ratio:.1%} ≥ {settings.max_gross_exposure:.0%} - evaluando {len(crypto_positions)} cryptos")
        
        # Evaluar cada posición crypto
        crypto_evaluations = []
        for pos, symbol in crypto_positions:
            try:
                evaluation = _evaluate_crypto_position(pos, symbol)
                if evaluation:
                    crypto_evaluations.append(evaluation)
            except Exception as e:
                logger.error(f"❌ Error evaluando {symbol}: {e}")
        
        if not crypto_evaluations:
            return
        
        # Ordenar por score (peores primero)
        crypto_evaluations.sort(key=lambda x: x['score'])
        
        # Cerrar posiciones de peor performance hasta salir de Crisis Mode
        target_exposure = 0.45  # Reducir a 45%
        closed_count = 0
        
        for evaluation in crypto_evaluations:
            symbol = evaluation['symbol']
            score = evaluation['score']
            pnl_pct = evaluation['pnl_pct']
            
            # Verificar si aún estamos en Crisis Mode
            from .exposure import get_total_exposure_ratio
            current_exposure = get_total_exposure_ratio()
            
            if current_exposure < target_exposure:
                logger.info(f"✅ Crisis Mode resuelto: Exposición reducida a {current_exposure:.1%}")
                break
            
            # Criterio de cierre: Score bajo O pérdidas significativas
            should_close = (
                score < 0.3 or  # Score muy bajo
                pnl_pct < -0.02 or  # Perdiendo >2%
                (pnl_pct < 0.005 and score < 0.5)  # Poco profit y score medio
            )
            
            if should_close:
                logger.critical(f"⚡ CIERRE SELECTIVO: {symbol} | Score: {score:.2f}, P&L: {pnl_pct:+.2%}")
                
                from .execution import close_position
                success = close_position(symbol, force_close=False)
                
                if success:
                    closed_count += 1
                    logger.info(f"✅ {symbol} cerrado exitosamente ({closed_count}/{len(crypto_evaluations)})")
                else:
                    logger.warning(f"⚠️ {symbol}: Fallo al cerrar")
            else:
                logger.info(f"🔒 MANTENIDO: {symbol} | Score: {score:.2f}, P&L: {pnl_pct:+.2%} (buen potencial)")
        
        if closed_count > 0:
            logger.critical(f"🎯 Crisis Mode: {closed_count} posiciones crypto cerradas selectivamente")
        else:
            logger.warning(f"⚠️ Crisis Mode: Todas las cryptos tienen buen potencial - esperando")
    
    except Exception as e:
        logger.error(f"❌ Error en intelligent crypto closure: {e}")


def _evaluate_crypto_position(pos, symbol: str) -> dict:
    """
    Evalúa el potencial de una posición crypto basado en:
    - P&L actual
    - Momentum de precio
    - Tiempo de holding
    - Valor de la posición
    """
    try:
        qty = float(getattr(pos, 'qty', 0))
        entry_price = float(getattr(pos, 'avg_entry_price', 0))
        market_value = abs(float(getattr(pos, 'market_value', 0)))
        
        # Obtener precio actual
        current_price = _get_current_price(symbol)
        if not current_price:
            return None
        
        # Calcular P&L
        if qty > 0:  # LONG
            pnl = (current_price - entry_price) * qty
            pnl_pct = (current_price - entry_price) / entry_price
        else:  # SHORT
            pnl = (entry_price - current_price) * abs(qty)
            pnl_pct = (entry_price - current_price) / entry_price
        
        # Calcular score compuesto (0.0 = peor, 1.0 = mejor)
        score = 0.0
        
        # 1. P&L Component (50% del score)
        if pnl_pct > 0.02:  # >2% profit
            pnl_score = 1.0
        elif pnl_pct > 0.01:  # 1-2% profit
            pnl_score = 0.8
        elif pnl_pct > 0:  # Small profit
            pnl_score = 0.6
        elif pnl_pct > -0.01:  # Small loss
            pnl_score = 0.4
        elif pnl_pct > -0.02:  # Medium loss
            pnl_score = 0.2
        else:  # Big loss
            pnl_score = 0.0
        
        score += pnl_score * 0.5
        
        # 2. Position Size Component (20% del score)
        # Posiciones más grandes tienen más impacto en exposure
        if market_value > 100:  # >$100
            size_score = 0.3  # Más propensas a cerrar
        elif market_value > 50:  # $50-100
            size_score = 0.5
        else:  # <$50
            size_score = 0.8  # Menos propensas a cerrar
        
        score += size_score * 0.2
        
        # 3. Momentum Component (30% del score)
        # Simple momentum basado en cambio de precio reciente
        try:
            momentum_score = 0.5  # Default neutral
            
            # Si hay mucho profit, asumir momentum positivo
            if pnl_pct > 0.015:
                momentum_score = 0.9
            elif pnl_pct > 0.005:
                momentum_score = 0.7
            elif pnl_pct < -0.015:
                momentum_score = 0.1
            elif pnl_pct < -0.005:
                momentum_score = 0.3
            
            score += momentum_score * 0.3
            
        except Exception:
            score += 0.5 * 0.3  # Default momentum
        
        return {
            'symbol': symbol,
            'score': min(1.0, max(0.0, score)),  # Clamp entre 0-1
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'market_value': market_value,
            'current_price': current_price,
            'entry_price': entry_price
        }
    
    except Exception as e:
        logger.error(f"❌ Error evaluando posición {symbol}: {e}")
        return None
        return False

def normalize_symbol(symbol: str) -> str:
    if "/" in symbol:
        return symbol
    if symbol.endswith("USD"):
        base = symbol.replace("USD", "")
        return f"{base}/USD"
    return symbol


def _get_current_price(symbol: str) -> Optional[float]:
    """
    Obtiene el precio actual con manejo robusto de errores SIP y market hours.
    - Crypto: Obtiene precio 24/7
    - Stocks: Obtiene precio solo durante horario de mercado, usa cache fuera de horas
    - Añade feed='iex' para evitar errores SIP
    - Implementa fallback a último precio conocido
    """
    now = time.time()
    cache_key = f"{symbol}_price"
    cache_ttl = get_cache_ttl_for_symbol(symbol)
    
    # 1. Verificar cache con TTL dinámico
    if cache_key in _price_cache:
        price, timestamp = _price_cache[cache_key]
        if now - timestamp < cache_ttl:
            return price
    
    # 2. Skip real-time pricing para stocks fuera de horario
    if should_skip_realtime_pricing(symbol):
        # Usar último precio conocido para stocks después de horas
        if symbol in _LAST_KNOWN_PRICES:
            logger.debug(f"📊 {symbol}: Usando precio cached después de horas ${_LAST_KNOWN_PRICES[symbol]:.4f}")
            return _LAST_KNOWN_PRICES[symbol]
        else:
            # 🔇 SILENT CACHE: Solo log debug para mercado cerrado (comportamiento normal)
            if symbol not in _WARNED_SYMBOLS:
                _WARNED_SYMBOLS.add(symbol)
                _MARKET_CLOSED_SYMBOLS.add(symbol)
                # Solo log consolidado una vez por sesión cuando hay 4+ stocks sin precio
                if len(_WARNED_SYMBOLS) == 4:
                    symbols_list = ', '.join(sorted(_MARKET_CLOSED_SYMBOLS))
                    logger.debug(f"ℹ️ Mercado cerrado - {len(_MARKET_CLOSED_SYMBOLS)} stocks usando último precio conocido: {symbols_list}")
                # Individual warnings downgraded to debug level
                logger.debug(f"📊 {symbol}: Usando fallback - mercado cerrado, sin precio cached")
            return None
    
    # 3. Obtener precio en tiempo real
    try:
        if symbol_manager.is_crypto(symbol):  # Cripto - 24/7
            request = CryptoBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=getattr(TimeFrame, 'Minute'),
                limit=1
            )
            bars = crypto_client.get_crypto_bars(request)
            
            bars_df = getattr(bars, 'df', None)
            if bars_df is None or bars_df.empty:
                logger.warning(f"⚠️ No hay datos de precio para {symbol} (cripto)")
                return _LAST_KNOWN_PRICES.get(symbol)  # Fallback
            price = float(bars_df.iloc[-1]["close"])
            
        else:  # Stocks - CON FEED IEX para evitar SIP errors
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=getattr(TimeFrame, 'Minute'),
                limit=1,
                feed=DataFeed.IEX  # 🔧 FIX: Añadir feed IEX para evitar errores SIP
            )
            bars = stock_client.get_stock_bars(request)
            
            bars_df = getattr(bars, 'df', None)
            if bars_df is None or bars_df.empty:
                logger.warning(f"⚠️ No hay datos IEX para {symbol} (posible mercado cerrado)")
                return _LAST_KNOWN_PRICES.get(symbol)  # Fallback
            
            df = bars_df
            if hasattr(df.index, 'levels'):  # MultiIndex
                df = df.reset_index()
            price = float(df.iloc[-1]["close"])
        
        # 4. Guardar en ambos caches
        _price_cache[cache_key] = (price, now)
        _LAST_KNOWN_PRICES[symbol] = price  # Fallback cache
        return price
        
    except Exception as e:
        error_msg = str(e)
        if "subscription does not permit querying recent SIP data" in error_msg:
            # SIP error específico - usar fallback sin spam de logs
            logger.warning(f"⚠️ SIP access denied para {symbol}, usando precio cached")
        else:
            # Otros errores
            logger.warning(f"⚠️ Error obteniendo precio de {symbol}: {e}")
        
        # Intentar fallback a último precio conocido
        if symbol in _LAST_KNOWN_PRICES:
            logger.debug(f"🔄 Fallback: {symbol} = ${_LAST_KNOWN_PRICES[symbol]:.4f}")
            return _LAST_KNOWN_PRICES[symbol]
        
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
    from .config import settings
    logger.info(f"⏰ TIME-BASED EXIT configurado: {settings.max_position_time_normal}min estancadas, {settings.max_position_time_force}min forzado")
    logger.info(f"🎯 TRAILING STOPS configurado: activación {settings.trailing_activation_pct:.1%}, distancia {settings.trailing_distance_pct:.1%}")
    logger.info(f"💎 PARTIAL PROFIT configurado: cierre parcial 50% @ {settings.partial_profit_pct:.1%}")
    
    # Cargar timestamps y estados de posiciones
    position_times = _load_position_times()
    position_states = _load_position_states()
    
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
                    # Limpiar position_times y states si no hay posiciones
                    if position_times or position_states:
                        position_times.clear()
                        position_states.clear()
                        _save_position_times(position_times)
                        _save_position_states(position_states)
                        logger.debug("🧹 Position times y states limpiados - sin posiciones abiertas")
                    
                    logger.debug("💤 Sin posiciones abiertas para monitorear")
                    time.sleep(10)  # Esperar 10 segundos antes de la próxima verificación
                    continue
                else:
                    # 🚀 FIX: Mostrar los símbolos de las posiciones que se están monitoreando.
                    position_symbols = [normalize_symbol(getattr(p, 'symbol', '')) for p in positions]
                    logger.info(f"👁️ Monitoreando {len(positions)} posiciones abiertas: {', '.join(position_symbols)}")
            except Exception as e:
                logger.error(f"❌ No se pudieron obtener posiciones: {e}")
                time.sleep(10)
                continue

            # 3. Actualizar tracking de posiciones
            current_symbols = set()
            position_times_changed = False
            position_states_changed = False
            
            for pos in positions:
                symbol = normalize_symbol(getattr(pos, 'symbol', ''))
                entry_price = float(getattr(pos, 'avg_entry_price', 0))
                quantity = float(getattr(pos, 'qty', 0))
                current_symbols.add(symbol)
                
                # Trackear nueva posición si no existe
                if symbol not in position_times:
                    _track_new_position(symbol, position_times)
                    position_times_changed = True
                
                # Inicializar estado de nueva posición si no existe
                if symbol not in position_states:
                    _init_new_position_state(symbol, entry_price, quantity, position_states)
                    position_states_changed = True
            
            # Limpiar posiciones cerradas del tracking
            if _cleanup_closed_positions(current_symbols, position_times):
                position_times_changed = True
            if _cleanup_position_states(current_symbols, position_states):
                position_states_changed = True
            
            # Guardar cambios si hubo modificaciones
            if position_times_changed:
                _save_position_times(position_times)
            if position_states_changed:
                _save_position_states(position_states)

            # 🚨 3.5. CRISIS MODE: Cierre selectivo inteligente de cryptos
            try:
                from .exposure import get_total_exposure_ratio
                exposure_ratio = get_total_exposure_ratio()
                
                from .config import settings
                if exposure_ratio >= settings.max_gross_exposure:  # Crisis Mode activado
                    _intelligent_crypto_closure(positions, exposure_ratio)
            except Exception as e:
                logger.error(f"❌ Error en Crisis Mode crypto closure: {e}")

            # 💰 3.6. LIQUIDITY UNLOCK: Verificar si necesitamos liberar capital
            try:
                unlock_executed = liquidity_unlocker.check_and_unlock_liquidity()
                if unlock_executed:
                    # Si se ejecutó un unlock, saltar este ciclo para que el siguiente 
                    # ciclo evalúe las nuevas posiciones abiertas
                    logger.info("💰 Liquidity unlock ejecutado - continuando monitoreo en próximo ciclo")
                    time.sleep(10)
                    continue
            except Exception as e:
                logger.error(f"❌ Error en liquidity unlock: {e}")

            # 4. Revisar cada posición (TP/SL, ML Reversal, TIME-BASED EXIT)
            for pos in positions:
                symbol = normalize_symbol(getattr(pos, 'symbol', ''))
                qty = float(getattr(pos, 'qty', 0))
                entry_price = float(getattr(pos, 'avg_entry_price', 0))
                
                # 🚫 FILTRO ANTI-MICRO: Skip posiciones microscópicas
                market_value = abs(qty * entry_price)
                min_value_threshold = 5.0  # $5 mínimo
                min_qty_threshold = 0.0001 if symbol_manager.is_crypto(symbol) else 0.001
                
                if abs(qty) < min_qty_threshold or market_value < min_value_threshold:
                    logger.debug(f"🚫 SKIP MICRO-POSICIÓN: {symbol} qty={abs(qty):.8f}, valor=${market_value:.2f}")
                    continue
                
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
                
                # 💎 OBTENER CONFIGURACIÓN PERSONALIZADA PARA EL SÍMBOLO
                symbol_config = get_symbol_config(symbol)
                
                # --- PRIORITY 0: TRAILING STOPS & PARTIAL PROFIT (nocturnal optimization) ---
                trailing_info = _update_position_state(symbol, current_price, position_states)
                
                # 🎯 TRAILING STOP: Verificar si se activó el trailing stop
                if trailing_info["trailing_stop_triggered"]:
                    should_close = True
                    reason = f"🎯 TRAILING STOP: precio bajó {settings.trailing_distance_pct:.1%} desde máximo"
                
                # 💎 PARTIAL PROFIT: Verificar si se activó el cierre parcial (solo si no hay trailing stop)
                elif trailing_info["partial_profit_triggered"]:
                    # Aquí necesitamos ejecutar el cierre parcial (50%)
                    try:
                        success = _execute_partial_close(pos, symbol, qty, current_price, pnl_pct, position_states)
                        if success:
                            # Actualizar position_states después del cierre parcial
                            position_states_changed = True
                            continue  # Continuar con la posición restante (50%)
                    except Exception as e:
                        logger.error(f"❌ Error en cierre parcial {symbol}: {e}")
                
                # --- PRIORITY 1: TIME-BASED EXIT SYSTEM (antes que TP/SL tradicional) ---
                
                # A) CIERRE FORZADO (2-4 horas para crypto, 75min para stocks): Timing inteligente
                # 🛡️ PDT CHECK: Antes de cualquier cierre, verificar si es una acción abierta hoy
                is_stock_opened_today = False
                if not symbol_manager.is_crypto(symbol):
                    # Asumimos que la posición se abrió hoy si está en el tracking de tiempos
                    # y tiene menos de 1 día de antigüedad.
                    # Una lógica más robusta podría usar la API de Alpaca para obtener la fecha de apertura.
                    if position_age_minutes > 0 and position_age_minutes < (60 * 16): # Menos de 16 horas de mercado
                        is_stock_opened_today = True


                # 🚀 CRYPTO 24/7: 24 horas para permitir movimientos nocturnos y recuperación
                # 📈 STOCKS: 75min durante horario de mercado
                if symbol_manager.is_crypto(symbol):
                    # Crypto: 24 horas para permitir recuperación completa
                    max_time_force = 1440  # 24 horas (1440 minutos)
                else:
                    # Stocks: mantener 75min original
                    max_time_force = settings.max_position_time_force
                
                if not is_stock_opened_today and position_age_minutes >= max_time_force:
                    # EXCEPCIÓN: Mantener si P&L > 1.2% Y señal ML sigue fuerte
                    keep_position = False
                    if pnl_pct > settings.min_pnl_keep_long:
                        try:
                            # Verificar si la señal ML sigue fuerte
                            df = fetch_bars(symbol, limit=200) # 🚀 FIX: Fetch only recent data
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
                        if symbol_manager.is_crypto(symbol):
                            hours = max_time_force / 60
                            reason = f"🕐 CIERRE FORZADO CRYPTO: {position_age_minutes:.0f}min ≥ {max_time_force}min ({hours:.1f}h)"
                        else:
                            reason = f"🕐 CIERRE FORZADO: {position_age_minutes:.0f}min ≥ {max_time_force}min"
                    else:
                        logger.info(f"⚡ {symbol}: MANTENIDO tras {position_age_minutes:.0f}min (P&L: {pnl_pct:+.2%}, señal fuerte)")
                
                # B) CIERRE ESTANCADO (30-45 minutos): Posiciones que no van a ningún lado
                elif not is_stock_opened_today and position_age_minutes >= settings.max_position_time_normal:
                    # Condición 1: P&L estancado (-0.3% a +0.7%)
                    is_stagnant = settings.stagnant_pnl_min <= pnl_pct <= settings.stagnant_pnl_max
                    
                    # Condición 2: Señal ML se debilitó significativamente
                    ml_weakened = False
                    try:
                        df = fetch_bars(symbol, limit=200) # 🚀 FIX: Fetch only recent data
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
                if not should_close and not is_stock_opened_today:
                    
                    # 1. TAKE PROFIT: Usar TP/SL específico del símbolo
                    take_profit_pct = symbol_config.take_profit_pct
                    stop_loss_pct = symbol_config.stop_loss_pct
                    
                    if pnl_pct >= take_profit_pct:
                        should_close = True
                        reason = f"TAKE PROFIT ({symbol}) alcanzado: {pnl_pct:.2%} >= {take_profit_pct:.2%}"
                    
                    # 2. STOP LOSS: Usar TP/SL específico del símbolo
                    elif pnl_pct <= -stop_loss_pct:
                        should_close = True
                        reason = f"STOP LOSS ({symbol}) activado: {pnl_pct:.2%} <= -{stop_loss_pct:.2%}"
                    
                    # 3. REVERSIÓN DE SEÑAL ML (solo si NO se activó TP/SL)
                    else:
                        try:
                            df = fetch_bars(symbol, limit=200) # 🚀 FIX: Fetch only recent data
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
                
                elif is_stock_opened_today:
                    logger.debug(f"🚫 PDT HOLD: {symbol} se abrió hoy. Cierre pospuesto para evitar restricción PDT.")


                # EJECUTAR CIERRE si cualquier condición se cumplió
                if should_close:
                    # 🚫 FILTRO FINAL ANTI-MICRO: No cerrar posiciones microscópicas
                    market_value = abs(qty * current_price) if current_price else abs(qty * entry_price)
                    min_value_threshold = 5.0  # $5 mínimo
                    min_qty_threshold = 0.0001 if symbol_manager.is_crypto(symbol) else 0.001
                    
                    if abs(qty) < min_qty_threshold or market_value < min_value_threshold:
                        logger.info(f"🚫 SKIP CIERRE MICRO: {symbol} qty={abs(qty):.8f}, valor=${market_value:.6f} - NO vale la pena cerrar")
                        continue  # Skip este cierre y continuar con siguiente posición
                    
                    # Formateo inteligente para P&L pequeños (cryptos de bajo valor)
                    pnl_str = f"${pnl:+.6f}" if abs(pnl) < 0.01 else f"${pnl:+.2f}"
                    price_str = f"${current_price:.6f}" if current_price < 0.01 else f"${current_price:.2f}"
                    logger.info(f"🔄 {reason}. Cerrando {current_side} en {symbol} @ {price_str} | P&L: {pnl_str} ({pnl_pct:+.2%})")
                    _close_position(pos, symbol, qty, current_price, pnl, pnl_pct, reason)
            
            # Guardar estados de posiciones después de procesar todas las posiciones
            if position_states_changed:
                _save_position_states(position_states)

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


def _intelligent_crypto_closure(positions, exposure_ratio: float):
    """
    🚨 CRISIS MODE: Cierre selectivo inteligente de posiciones crypto.
    Evalúa potencial y cierra las peores primero para reducir exposición.
    """
    try:
        # Filtrar solo posiciones crypto
        crypto_positions = []
        for pos in positions:
            symbol = normalize_symbol(getattr(pos, 'symbol', ''))
            if symbol_manager.is_crypto(symbol):
                crypto_positions.append((pos, symbol))
        
        if not crypto_positions:
            return
        
        from .config import settings
        logger.critical(f"🚨 CRISIS MODE: Exposición {exposure_ratio:.1%} ≥ {settings.max_gross_exposure:.0%} - evaluando {len(crypto_positions)} cryptos")
        
        # Evaluar cada posición crypto
        crypto_evaluations = []
        for pos, symbol in crypto_positions:
            try:
                evaluation = _evaluate_crypto_position(pos, symbol)
                if evaluation:
                    crypto_evaluations.append(evaluation)
            except Exception as e:
                logger.error(f"❌ Error evaluando {symbol}: {e}")
        
        if not crypto_evaluations:
            return
        
        # Ordenar por score (peores primero)
        crypto_evaluations.sort(key=lambda x: x['score'])
        
        # Cerrar posiciones de peor performance hasta salir de Crisis Mode
        target_exposure = 0.45  # Reducir a 45%
        closed_count = 0
        
        for evaluation in crypto_evaluations:
            symbol = evaluation['symbol']
            score = evaluation['score']
            pnl_pct = evaluation['pnl_pct']
            
            # Verificar si aún estamos en Crisis Mode
            from .exposure import get_total_exposure_ratio
            current_exposure = get_total_exposure_ratio()
            
            if current_exposure < target_exposure:
                logger.info(f"✅ Crisis Mode resuelto: Exposición reducida a {current_exposure:.1%}")
                break
            
            # Criterio de cierre: Score bajo O pérdidas significativas
            should_close = (
                score < 0.3 or  # Score muy bajo
                pnl_pct < -0.02 or  # Perdiendo >2%
                (pnl_pct < 0.005 and score < 0.5)  # Poco profit y score medio
            )
            
            if should_close:
                logger.critical(f"⚡ CIERRE SELECTIVO: {symbol} | Score: {score:.2f}, P&L: {pnl_pct:+.2%}")
                
                from .execution import close_position
                success = close_position(symbol, force_close=False)
                
                if success:
                    closed_count += 1
                    logger.info(f"✅ {symbol} cerrado exitosamente ({closed_count}/{len(crypto_evaluations)})")
                else:
                    logger.warning(f"⚠️ {symbol}: Fallo al cerrar")
            else:
                logger.info(f"🔒 MANTENIDO: {symbol} | Score: {score:.2f}, P&L: {pnl_pct:+.2%} (buen potencial)")
        
        if closed_count > 0:
            logger.critical(f"🎯 Crisis Mode: {closed_count} posiciones crypto cerradas selectivamente")
        else:
            logger.warning(f"⚠️ Crisis Mode: Todas las cryptos tienen buen potencial - esperando")
    
    except Exception as e:
        logger.error(f"❌ Error en intelligent crypto closure: {e}")


def _evaluate_crypto_position(pos, symbol: str) -> dict:
    """
    Evalúa el potencial de una posición crypto basado en:
    - P&L actual
    - Momentum de precio
    - Tiempo de holding
    - Valor de la posición
    """
    try:
        qty = float(getattr(pos, 'qty', 0))
        entry_price = float(getattr(pos, 'avg_entry_price', 0))
        market_value = abs(float(getattr(pos, 'market_value', 0)))
        
        # Obtener precio actual
        current_price = _get_current_price(symbol)
        if not current_price:
            return None
        
        # Calcular P&L
        if qty > 0:  # LONG
            pnl = (current_price - entry_price) * qty
            pnl_pct = (current_price - entry_price) / entry_price
        else:  # SHORT
            pnl = (entry_price - current_price) * abs(qty)
            pnl_pct = (entry_price - current_price) / entry_price
        
        # Calcular score compuesto (0.0 = peor, 1.0 = mejor)
        score = 0.0
        
        # 1. P&L Component (50% del score)
        if pnl_pct > 0.02:  # >2% profit
            pnl_score = 1.0
        elif pnl_pct > 0.01:  # 1-2% profit
            pnl_score = 0.8
        elif pnl_pct > 0:  # Small profit
            pnl_score = 0.6
        elif pnl_pct > -0.01:  # Small loss
            pnl_score = 0.4
        elif pnl_pct > -0.02:  # Medium loss
            pnl_score = 0.2
        else:  # Big loss
            pnl_score = 0.0
        
        score += pnl_score * 0.5
        
        # 2. Position Size Component (20% del score)
        # Posiciones más grandes tienen más impacto en exposure
        if market_value > 100:  # >$100
            size_score = 0.3  # Más propensas a cerrar
        elif market_value > 50:  # $50-100
            size_score = 0.5
        else:  # <$50
            size_score = 0.8  # Menos propensas a cerrar
        
        score += size_score * 0.2
        
        # 3. Momentum Component (30% del score)
        # Simple momentum basado en cambio de precio reciente
        try:
            momentum_score = 0.5  # Default neutral
            
            # Si hay mucho profit, asumir momentum positivo
            if pnl_pct > 0.015:
                momentum_score = 0.9
            elif pnl_pct > 0.005:
                momentum_score = 0.7
            elif pnl_pct < -0.015:
                momentum_score = 0.1
            elif pnl_pct < -0.005:
                momentum_score = 0.3
            
            score += momentum_score * 0.3
            
        except Exception:
            score += 0.5 * 0.3  # Default momentum
        
        return {
            'symbol': symbol,
            'score': min(1.0, max(0.0, score)),  # Clamp entre 0-1
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'market_value': market_value,
            'current_price': current_price,
            'entry_price': entry_price
        }
    
    except Exception as e:
        logger.error(f"❌ Error evaluando posición {symbol}: {e}")
        return None