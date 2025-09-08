# bot/main.py
import logging
import time
import pandas as pd
from tenacity import retry, wait_exponential, stop_after_attempt
from alpaca.trading.client import TradingClient

from .auto_tuner import tune_risk_parameters
from .config import settings
from .data import fetch_bars, fetch_all_bars
from .features import make_features
from .strategy import load_trading_model, hybrid_signal
from .sizing import volatility_target_size, kelly_cap
from .execution import place_order, close_position
from .state import BotState
from .exposure import get_total_exposure
from .telegram import alert_risk_stop, alert_error
from .position_monitor import monitor_closed_positions
from .profit_taking import auto_profit_taking
from .util import logger


logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))


def _client():
    return TradingClient(
        api_key=settings.alpaca_api_key,
        secret_key=settings.alpaca_secret_key,
        paper=(settings.mode == "paper")
    )


def _is_crypto(symbol: str) -> bool:
    return "/" in symbol or (symbol.endswith("USD") and symbol.isupper() and len(symbol) > 3)


def _get_position(symbol: str):
    client = _client()
    try:
        return client.get_open_position(symbol.replace("/", ""))
    except Exception:
        return None


@retry(wait=wait_exponential(multiplier=1, min=5, max=60), stop=stop_after_attempt(5))
def run_once(state: BotState, clf):
    client = _client()

    # 0. Auto-ajuste
    auto_config = tune_risk_parameters()
    settings.risk_per_trade = auto_config["risk_per_trade"]
    settings.max_gross_exposure = auto_config["max_gross_exposure"]

    # 1. Equity actual y cash disponible
    try:
        account = client.get_account()
        current_equity = float(account.equity)
        available_cash = float(account.cash)
        state.state["equity"] = current_equity
        logger.info(f"💵 Cash disponible al inicio: ${available_cash:,.2f}")
    except Exception as e:
        logger.error(f"❌ No se pudo obtener equity: {e}")
        return

    # 2. Stop diario por pérdida
    daily_pnl_pct = state.get_daily_pnl_pct(current_equity)
    if daily_pnl_pct < -settings.max_daily_loss_pct:
        msg = f"Pérdida diaria de {daily_pnl_pct:.2%} ≥ límite de {settings.max_daily_loss_pct:.0%}"
        logger.critical(f"🛑 {msg}")
        alert_risk_stop(msg)
        return "STOP"  # ✅ Único return "STOP" válido
    logger.info(f"📈 P&L diario: {daily_pnl_pct:.2%}")

    # 3. Exposición bruta - GESTIONAR PERO CONTINUAR
    exposure_managed = False
    try:
        current_exposure = get_total_exposure()
        if current_exposure >= settings.max_gross_exposure:
            logger.warning(f"⚠️ Exposición {current_exposure:.2f}x ≥ límite {settings.max_gross_exposure}x. Reduciendo...")
            try:
                positions = client.get_all_positions()
                sorted_positions = sorted(positions, key=lambda p: abs(float(p.qty)), reverse=False)
                for pos in sorted_positions:
                    qty = float(pos.qty)
                    symbol = pos.symbol
                    side = "long" if qty > 0 else "short"
                    logger.info(f"🔁 Reduciendo exposición: cerrando {abs(qty)} de {symbol}")
                    # ✅ Pasar el objeto de posición directamente para evitar inconsistencias
                    close_position(symbol, side, position_obj=pos)
                    exposure_managed = True
                    break
            except Exception as e:
                logger.error(f"❌ No se pudieron obtener posiciones para cierre: {e}")
        
        # ✅ CONTINUAR después de gestionar exposición
        if exposure_managed:
            logger.info("✅ Exposición gestionada. Continuando con análisis de activos...")
    except Exception as e:
        logger.exception("💥 Error al verificar exposición")
        # ✅ NO return aquí - continuar con otros activos

    # 4. Cash disponible (ya obtenido arriba)
    # available_cash ya se obtuvo en el paso 1

    total_equity = current_equity

    # --- 5. PROFIT-TAKING AUTOMÁTICO ---
    profit_result = auto_profit_taking()
    if profit_result == "PROFITS_TAKEN":
        logger.info("💰 Profit-taking ejecutado. Actualizando equity...")
        # Actualizar equity tras profit-taking
        account = client.get_account()
        current_equity = float(account.equity)
        total_equity = current_equity
        available_cash = float(account.cash)
        logger.info(f"📊 Equity actualizado: ${total_equity:,.2f}, Cash: ${available_cash:,.2f}")

    # --- 6. BTC/USD DIVERSIFICADO (máximo 40% para balance) ---
    btc_max_allocation = 0.40  # Máximo 40% del equity total
    btc_max_cash = min(total_equity * btc_max_allocation, available_cash * 0.6)  # Máx 60% del cash disponible
    equity_for_btc = btc_max_cash

    if "BTC/USD" in settings.symbols:
        try:
            df = fetch_bars("BTC/USD", start=None, end=None, min_bars=50)  # Solo mínimo necesario
            if not df.empty and len(df) >= 100:
                feats = make_features(df)
                latest = feats.iloc[-1]

                sig = hybrid_signal(latest, clf)
                if sig != 0:
                    price = float(latest["close"])
                    atr = float(latest["atr_14"])
                    shares = volatility_target_size(equity_for_btc, price, atr)
                    frac_k = kelly_cap(0.5 + abs(sig)/2, cap=settings.risk_per_trade * 4)
                    leverage = max(min(abs(sig) + frac_k, 1.5), 0.1)
                    qty = shares * leverage
                    side = "buy" if sig > 0 else "sell"

                    # 🎯 LÍMITE INTELIGENTE: máximo 40% del equity o 60% del cash disponible
                    max_qty_by_equity = (total_equity * 0.40) / price  # 40% del equity total
                    max_qty_by_cash = (available_cash * 0.60) / price  # 60% del cash disponible
                    qty = min(qty, max_qty_by_equity, max_qty_by_cash)

                    if qty >= 1e-6:
                        is_crypto = True
                        pos = _get_position("BTC/USD")

                        if pos:
                            current_qty = float(pos.qty)
                            if side == "buy" and current_qty > 0:
                                logger.info(f"🟢 Posición larga existente en BTC/USD. Aumentando...")
                                place_order("BTC/USD", qty, side, price, fractional=False, is_crypto=is_crypto)
                            elif side == "buy" and current_qty < 0:
                                logger.info("🔄 Cerrando corto y abriendo largo en BTC/USD")
                                place_order("BTC/USD", abs(current_qty), "buy", price, fractional=False, is_crypto=is_crypto)
                                place_order("BTC/USD", qty, "buy", price, fractional=False, is_crypto=is_crypto)
                            elif side == "sell" and current_qty > 0:
                                # ✅ CRYPTO: Solo cerrar posición larga, NO abrir short (ARREGLADO SALDO)
                                safe_qty = abs(current_qty) * 0.95  # 95% para evitar errores de saldo
                                logger.info(f"🔄 Señal bajista: cerrando posición larga en BTC/USD ({safe_qty:.6f} de {abs(current_qty):.6f})")
                                place_order("BTC/USD", safe_qty, "sell", price, fractional=True, is_crypto=is_crypto)
                        else:
                            # ✅ CRYPTO: Solo abrir posición si es LONG (buy)
                            if side == "buy":
                                logger.info(f"📈 Abriendo nueva posición LONG en BTC/USD")
                                place_order("BTC/USD", qty, side, price, fractional=False, is_crypto=is_crypto)
                            else:
                                logger.info(f"⚠️ Señal bajista en BTC/USD pero crypto no permite short. Skip.")
        except Exception as e:
            logger.error(f"💥 Error procesando BTC/USD: {e}")

    # --- 7. Resto de símbolos (dinámico según capital disponible) ---
    # Si tomamos profits, tendremos más cash disponible para otros activos
    btc_position_value = 0
    try:
        positions = client.get_all_positions()
        for pos in positions:
            if pos.symbol == "BTCUSD":
                btc_position_value = abs(float(pos.market_value))
                break
    except:
        pass
    
    # 🎯 DIVERSIFICACIÓN FORZADA: Reservar siempre mínimo 30% para otros activos
    btc_percentage = btc_position_value / total_equity if total_equity > 0 else 0
    min_reserved_for_others = total_equity * 0.30  # SIEMPRE 30% reservado para diversificación
    max_btc_allowed = total_equity * 0.50  # BTC nunca más de 50% del portafolio
    
    # Cash real disponible para otros (sin confusión de 'reservado')
    remaining_cash_after_btc = available_cash - (max_btc_allowed * 0.6)  # Reservar 60% del límite BTC
    equity_for_rest = max(min_reserved_for_others, remaining_cash_after_btc)
    equity_for_rest = min(equity_for_rest, available_cash * 0.75)  # Máximo 75% del cash disponible
    
    other_symbols = [s for s in settings.symbols if s != "BTC/USD"]
    signals = []
    
    logger.info(f"🔍 Analizando {len(other_symbols)} activos adicionales")
    logger.info(f"💰 BTC: {btc_percentage:.1%} del portafolio, Disponible para otros: ${equity_for_rest:,.2f} (DIVERSIFICADO)")

    # ⚡ OPTIMIZACIÓN PARALELA: Descargar todos los datos en paralelo primero
    symbols_batch = other_symbols[:8]  # Rotar 8 activos por vez
    logger.info(f"⚡ Modo scalping: analizando primeros {len(symbols_batch)} de {len(other_symbols)} activos")
    
    # 🚀 DESCARGA PARALELA: todos los símbolos a la vez
    all_data = fetch_all_bars(symbols_batch, start=None, end=None, min_bars=50)
    
    # 🧠 PROCESAMIENTO: analizar cada símbolo con datos ya descargados
    for i, symbol in enumerate(symbols_batch, 1):
        try:
            logger.info(f"📊 ({i}/{len(symbols_batch)}) {symbol}...")
            
            # Obtener datos de la descarga paralela
            df = all_data.get(symbol, pd.DataFrame())
            if df.empty or len(df) < 50:
                logger.warning(f"⚠️ {symbol}: Sin datos")
                continue
                
            feats = make_features(df)
            latest = feats.iloc[-1]

            sig = hybrid_signal(latest, clf)
            
            # 📊 MOSTRAR SCORE COMPLETO SIEMPRE
            score_status = "🟢 FUERTE" if abs(sig) >= 0.2 else "🟡 MODERADA" if abs(sig) >= 0.1 else "🔴 DÉBIL"
            signal_direction = "🔺 ALCISTA" if sig > 0 else "🔻 BAJISTA" if sig < 0 else "➡️ NEUTRAL"
            
            logger.info(f"📊 {symbol}: SCORE={sig:+.3f} ({score_status} {signal_direction}) @ ${latest['close']:.2f}")
            
            # ⚡ Solo procesar señales fuertes (>0.1) para scalping
            if abs(sig) < 0.1:
                logger.info(f"⚠️ {symbol}: Score débil, no se opera")
                continue

            signals.append({
                "symbol": symbol,
                "signal": sig,
                "features": latest,
                "price": float(latest["close"]),
                "atr": float(latest["atr_14"])
            })
            logger.info(f"✅ {symbol}: INCLUIDO para trading")
            
        except Exception as e:
            logger.warning(f"⚠️ {symbol}: {e}")

    logger.info(f"⚡ Análisis rápido: {len(signals)}/{len(symbols_batch)} señales fuertes")

    logger.info(f"📈 Total señales detectadas: {len(signals)} de {len(other_symbols)} activos")

    signals.sort(key=lambda x: abs(x["signal"]), reverse=True)

    logger.info(f"💰 Procesando {len(signals)} señales detectadas...")
    
    for i, item in enumerate(signals, 1):
        symbol = item["symbol"]
        sig = item["signal"]
        price = item["price"]
        atr = item["atr"]
        
        # 🎯 SCORE DETALLADO CON EVALUACIÓN
        signal_strength = "MÁXIMA" if abs(sig) >= 0.5 else "ALTA" if abs(sig) >= 0.3 else "MEDIA"
        direction = "LONG" if sig > 0 else "SHORT"
        direction_emoji = "📊" if sig > 0 else "📉"
        
        logger.info(f"{direction_emoji} {direction} ({i}/{len(signals)}) {symbol}: score={sig:+.3f} ({signal_strength}) @ ${price:.2f}")
        
        # 🎯 POSITION SIZING BALANCEADO: Para diversificación óptima
        if abs(sig) >= 0.2:  # Señales fuertes
            position_equity = equity_for_rest * 0.25  # 25% del disponible por señal fuerte
        elif abs(sig) >= 0.15:  # Señales medias
            position_equity = equity_for_rest * 0.15  # 15% del disponible por señal media
        else:  # Señales débiles pero >0.1
            position_equity = equity_for_rest * 0.08  # 8% del disponible por señal débil
        
        shares = volatility_target_size(position_equity, price, atr)
        frac_k = kelly_cap(0.3 + abs(sig)/4, cap=settings.risk_per_trade * 2.5)  # Kelly conservador
        leverage = max(min(abs(sig) * 0.8 + frac_k, 1.0), 0.05)  # Leverage máximo 1.0x
        qty = shares * leverage
        side = "buy" if sig > 0 else "sell"
        
        logger.info(f"💰 {symbol}: qty={qty:.6f} side={side} (leverage={leverage:.2f}x, shares={shares:.6f})")
        
        if qty < 1e-6:
            logger.info(f"⚠️ {symbol}: cantidad muy pequeña, skip")
            continue

        is_crypto = _is_crypto(symbol)
        pos = _get_position(symbol)
        if pos:
            current_qty = float(pos.qty)
            is_long = current_qty > 0
            is_short = current_qty < 0

            if side == "buy":
                if is_long:
                    logger.info(f"📊 LONG {symbol}: score={sig:+.3f}, qty={qty:.6f} (aumentando posición)")
                    place_order(symbol, qty, "buy", price, fractional=not is_crypto, is_crypto=is_crypto)
                elif is_short:
                    logger.info(f"📊 LONG {symbol}: score={sig:+.3f}, qty={qty:.6f} (cerrando short + abrir long)")
                    place_order(symbol, abs(current_qty), "buy", price, fractional=not is_crypto, is_crypto=is_crypto)
                    place_order(symbol, qty, "buy", price, fractional=not is_crypto, is_crypto=is_crypto)
            else:  # side == "sell"
                if is_crypto:
                    # ✅ CRYPTO: Solo cerrar posición larga, NO abrir short
                    if is_long:
                        logger.info(f"📉 CIERRE PARCIAL {symbol}: score={sig:+.3f}, qty={abs(current_qty):.6f} (crypto no permite short)")
                        place_order(symbol, abs(current_qty), "sell", price, fractional=not is_crypto, is_crypto=is_crypto)
                    else:
                        logger.info(f"⚠️ {symbol}: Señal BAJISTA pero crypto no permite SHORT → SKIP")
                else:
                    # ✅ ACCIONES: Permitir short normal
                    if is_short:
                        logger.info(f"📉 SHORT {symbol}: score={sig:+.3f}, qty={qty:.6f} (aumentando short)")
                        place_order(symbol, qty, "sell", price, fractional=not is_crypto, is_crypto=is_crypto)
                    elif is_long:
                        logger.info(f"📉 SHORT {symbol}: score={sig:+.3f}, qty={qty:.6f} (cerrando long + abrir short)")
                        place_order(symbol, abs(current_qty), "sell", price, fractional=not is_crypto, is_crypto=is_crypto)
                        place_order(symbol, qty, "sell", price, fractional=not is_crypto, is_crypto=is_crypto)
        else:
            # ✅ Nueva posición: crypto solo LONG, acciones pueden ser LONG/SHORT
            if is_crypto and side == "sell":
                logger.info(f"⚠️ {symbol}: Señal BAJISTA pero crypto no permite SHORT → SKIP")
            else:
                action = "LONG" if side == "buy" else "SHORT"
                action_emoji = "📊" if side == "buy" else "📉"
                logger.info(f"{action_emoji} {action} {symbol}: score={sig:+.3f}, qty={qty:.6f}, price=${price:.2f}")
                place_order(symbol, qty, side, price, fractional=not is_crypto, is_crypto=is_crypto)

    # 7. Monitorear cierres
    try:
        result = monitor_closed_positions(clf)
        if result == "STOP":
            return "STOP"
    except Exception as e:
        logger.error(f"❌ Error en monitor de cierres: {e}")

    # 8. Guardar estado
    try:
        state.save()
    except Exception as e:
        logger.error(f"❌ No se pudo guardar estado: {e}")

    return  # ✅ Único punto de salida


def main():
    logger.info("🚀 Bot de trading institucional iniciado (modo paper). Ctrl+C para detener.")
    state = BotState()

    try:
        clf = load_trading_model()
        if clf is None:
            logger.critical("❌ No se pudo cargar el modelo. Deteniendo bot.")
            return
        logger.info("✅ Modelo de trading cargado y listo para usar.")
        logger.info(f"🧠 Modelo: {type(clf).__name__} | Features: {len(clf.feature_names_in_)} | Riesgo: {settings.risk_per_trade:.2%}")
    except Exception as e:
        logger.error(f"❌ No se pudo cargar el modelo: {e}")
        return

    while True:
        try:
            result = run_once(state, clf)
            if result == "STOP":
                logger.critical("🛑 Bot detenido por stop diario.")
                break
        except KeyboardInterrupt:
            logger.info("🛑 Bot detenido por el usuario.")
            break
        except Exception as e:
            logger.exception("💥 Error en el loop principal")
            alert_error("Error en loop principal", str(e))
        logger.info("⏳ Esperando 60 segundos para próxima iteración...")
        time.sleep(60)


if __name__ == "__main__":
    main()