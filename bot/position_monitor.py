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
            if bars.df.empty:
                logger.warning(f"⚠️ No hay datos de precio para {symbol} (cripto)")
                return None
            price = float(bars.df.iloc[-1]["close"])
        else:  # Acciones
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Minute,
                limit=1
            )
            bars = stock_client.get_stock_bars(request)
            if bars.df.empty:
                logger.warning(f"⚠️ No hay datos de precio para {symbol} (probablemente mercado cerrado)")
                return None
            # Manejar MultiIndex si existe
            df = bars.df
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
    Monitorea posiciones continuamente y cierra cuando el modelo predice una reversión.
    Ejecuta en un bucle continuo cada 10 segundos.
    """
    logger.info("🔄 Position Monitor iniciado - monitoreando posiciones cada 10 segundos...")
    
    while True:
        try:
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
                    logger.debug("💤 Sin posiciones abiertas para monitorear")
                    time.sleep(10)  # Esperar 10 segundos antes de la próxima verificación
                    continue
                else:
                    logger.info(f"👁️ Monitoreando {len(positions)} posiciones abiertas...")
            except Exception as e:
                logger.error(f"❌ No se pudieron obtener posiciones: {e}")
                time.sleep(10)
                continue

            # 3. Revisar cada posición
            for pos in positions:
                symbol = normalize_symbol(pos.symbol)
                qty = float(pos.qty)
                entry_price = float(pos.avg_entry_price)
                current_price = _get_current_price(symbol)

                if not current_price:
                    continue

                # --- CALCULAR P&L Y EVALUAR TP/SL SIEMPRE (sin depender del modelo ML) ---
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
                
                # 1. TAKE PROFIT: Cerrar si ganancia >= 3%
                if pnl_pct >= settings.take_profit_pct:
                    should_close = True
                    reason = f"TAKE PROFIT alcanzado: {pnl_pct:.2%} >= {settings.take_profit_pct:.2%}"
                
                # 2. STOP LOSS: Cerrar si pérdida >= 1%
                elif pnl_pct <= -settings.stop_loss_pct:
                    should_close = True
                    reason = f"STOP LOSS activado: {pnl_pct:.2%} <= -{settings.stop_loss_pct:.2%}"
                
                # 3. REVERSIÓN DE SEÑAL ML (solo si NO se activó TP/SL)
                elif not should_close:
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
    """Cierra una posición y registra el cierre."""
    try:
        from alpaca.trading.requests import MarketOrderRequest
        from alpaca.trading.enums import OrderSide, TimeInForce
        
        base_symbol = symbol.replace("/", "")
        order_side = OrderSide.SELL if qty > 0 else OrderSide.BUY
        
        # ✅ ARREGLO: Usar MarketOrderRequest correctamente
        # Para crypto, reducir ligeramente la cantidad para evitar errores de precisión
        safe_qty = abs(qty)
        if "/USD" in symbol:  # Es crypto
            safe_qty = abs(qty) * 0.9999  # Reducir 0.01% para evitar errores microscópicos
        
        order_request = MarketOrderRequest(
            symbol=base_symbol,
            qty=safe_qty,
            side=order_side,
            time_in_force=TimeInForce.GTC
        )
        
        trading_client.submit_order(order_request)
        side_str = "long" if qty > 0 else "short"
        # Formateo inteligente para P&L pequeños (cryptos de bajo valor)
        pnl_str = f"${pnl:+.6f}" if abs(pnl) < 0.01 else f"${pnl:+.2f}"
        logger.info(f"✅ Cerrada {side_str} {abs(qty)} {symbol} | P&L: {pnl_str} ({pnl_pct:+.2%}) [{reason}]")
        alert_trade_exit(symbol, side_str, abs(qty), exit_price, pnl, pnl_pct)
        log_trade_exit(symbol, abs(qty), exit_price, pnl, pnl_pct)
    except Exception as e:
        logger.error(f"❌ No se pudo cerrar {symbol}: {e}")