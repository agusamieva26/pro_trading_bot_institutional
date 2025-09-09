# bot/position_monitor.py
import csv
import os
import time
from datetime import datetime, timezone, timedelta
from alpaca.trading.client import TradingClient
from alpaca.data.historical import CryptoHistoricalDataClient, StockHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest, StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from .config import settings
from .trade_logger import log_trade_exit
from .telegram import alert_trade_exit, alert_risk_stop
from .util import logger
from .data import fetch_bars
from .features import make_features


TRADES_FILE = "trades_log.csv"

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


def normalize_symbol(symbol: str) -> str:
    if "/" in symbol:
        return symbol
    if symbol.endswith("USD"):
        base = symbol.replace("USD", "")
        return f"{base}/USD"
    return symbol


def _get_current_price(symbol: str) -> float:
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
                timeframe=TimeFrame.Minute,
                limit=1
            )
            bars = crypto_client.get_crypto_bars(request)
            price = float(bars.df.iloc[-1]["close"])
        else:  # Acciones
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Minute,
                limit=1
            )
            bars = stock_client.get_stock_bars(request)
            price = float(bars.df.iloc[-1]["close"])

        _price_cache[cache_key] = (price, now)
        return price
    except Exception as e:
        logger.error(f"❌ No se pudo obtener precio de {symbol}: {e}")
        return None


def monitor_closed_positions(clf):
    """
    Monitorea posiciones y cierra cuando el modelo predice una reversión.
    """
    # 1. Verificar stop diario por pérdida
    try:
        account = trading_client.get_account()
        equity = float(account.equity)
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
            return
    except Exception as e:
        logger.error(f"❌ No se pudieron obtener posiciones: {e}")
        return

    # 3. Revisar cada posición
    for pos in positions:
        symbol = normalize_symbol(pos.symbol)
        qty = float(pos.qty)
        entry_price = float(pos.avg_entry_price)
        current_price = _get_current_price(symbol)

        if not current_price:
            continue

        # --- Obtener predicción del modelo ---
        try:
            df = fetch_bars(symbol, start="2023-01-01")
            if df.empty or len(df) < 100:
                continue

            feats = make_features(df)
            latest = feats.iloc[-1]

            # Validar features
            missing = [f for f in clf.feature_names_in_ if f not in latest.index]
            if missing:
                logger.warning(f"⚠️ Features faltantes para {symbol}: {missing}")
                continue

            X = latest[clf.feature_names_in_].to_frame().T
            predicted_signal = clf.predict(X)[0]
            current_side = "long" if qty > 0 else "short"
            predicted_side = "long" if predicted_signal > 0 else "short"

            # --- Lógica de cierre inteligente con COOLDOWN ---
            should_close = False
            reason = ""
            
            # ⚡ ANTI-OVERTRADING: Verificar que la posición tenga al menos 3 minutos
            # 🔧 FIX: Verificar atributos de posición
            if not hasattr(pos, 'created_at') and not hasattr(pos, 'created_time'):
                # Si no tiene timestamp, asumir que es nueva (skip por seguridad)
                continue
                
            # Usar created_at o created_time según disponibilidad  
            if hasattr(pos, 'created_at'):
                position_age_minutes = (pos.created_at.timestamp() if hasattr(pos.created_at, 'timestamp') else 0)
            elif hasattr(pos, 'created_time'):
                position_age_minutes = (pos.created_time.timestamp() if hasattr(pos.created_time, 'timestamp') else 0)
            else:
                position_age_minutes = 0
            current_time = time.time()
            age_minutes = (current_time - position_age_minutes) / 60
            
            # 🔥 ULTRA-SCALPING: Solo esperar 15 segundos para cerrar
            min_age_minutes = 0.25  # 15 segundos
            
            if age_minutes < min_age_minutes:
                continue  # Skip - posición muy nueva
                
            # Requiere señal FUERTE para cerrar (no cualquier cambio)
            signal_strength = abs(predicted_signal)
            
            if current_side == "long" and predicted_side == "short" and signal_strength >= 0.1:  # ⚡ SCALPING
                should_close = True
                reason = f"Modelo predice giro a baja fuerte ({predicted_signal:+.3f})"
            elif current_side == "short" and predicted_side == "long" and signal_strength >= 0.1:  # ⚡ SCALPING
                should_close = True
                reason = f"Modelo predice giro a alza fuerte ({predicted_signal:+.3f})"

            if should_close:
                pnl = (current_price - entry_price) * qty if qty > 0 else (entry_price - current_price) * abs(qty)
                pnl_pct = pnl / (entry_price * abs(qty)) if entry_price * abs(qty) != 0 else 0.0

                logger.info(f"🔄 {reason}. Cerrando {current_side} en {symbol} @ ${current_price:.2f}")
                _close_position(pos, symbol, qty, current_price, pnl, pnl_pct, reason)

        except Exception as e:
            logger.error(f"❌ Error al evaluar cierre para {symbol}: {e}")

    return "CONTINUE"


def _close_position(pos, symbol: str, qty: float, exit_price: float, pnl: float, pnl_pct: float, reason: str):
    """Cierra una posición y registra el cierre."""
    try:
        from alpaca.trading.requests import MarketOrderRequest
        from alpaca.trading.enums import OrderSide, TimeInForce
        
        base_symbol = symbol.replace("/", "")
        order_side = OrderSide.SELL if qty > 0 else OrderSide.BUY
        
        # ✅ ARREGLO: Usar MarketOrderRequest correctamente
        order_request = MarketOrderRequest(
            symbol=base_symbol,
            qty=abs(qty),
            side=order_side,
            time_in_force=TimeInForce.GTC
        )
        
        trading_client.submit_order(order_request)
        side_str = "long" if qty > 0 else "short"
        logger.info(f"✅ Cerrada {side_str} {abs(qty)} {symbol} | P&L: ${pnl:.2f} ({pnl_pct:+.2%}) [{reason}]")
        alert_trade_exit(symbol, side_str, abs(qty), exit_price, pnl, pnl_pct)
        log_trade_exit(symbol, abs(qty), exit_price, pnl, pnl_pct)
    except Exception as e:
        logger.error(f"❌ No se pudo cerrar {symbol}: {e}")