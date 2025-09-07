# bot/main.py
import logging
import time
from tenacity import retry, wait_exponential, stop_after_attempt
from alpaca.trading.client import TradingClient

from .auto_tuner import tune_risk_parameters
from .config import settings
from .data import fetch_bars
from .features import make_features
from .strategy import load_trading_model, hybrid_signal
from .sizing import volatility_target_size, kelly_cap
from .execution import place_order, close_position
from .state import BotState
from .exposure import get_total_exposure
from .telegram import alert_risk_stop, alert_error
from .position_monitor import monitor_closed_positions
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

    # 1. Equity actual
    try:
        account = client.get_account()
        current_equity = float(account.equity)
        state.state["equity"] = current_equity
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

    # 3. Exposición bruta
    try:
        current_exposure = get_total_exposure()
        if current_exposure >= settings.max_gross_exposure:
            logger.critical(f"🛑 Exposición {current_exposure:.2f}x ≥ límite {settings.max_gross_exposure}x. Cerrando posiciones...")
            try:
                positions = client.get_all_positions()
                sorted_positions = sorted(positions, key=lambda p: abs(float(p.qty)), reverse=False)
                for pos in sorted_positions:
                    qty = float(pos.qty)
                    symbol = pos.symbol
                    side = "long" if qty > 0 else "short"
                    logger.info(f"🔁 Reduciendo exposición: cerrando {abs(qty)} de {symbol}")
                    close_position(symbol, side)
                    break
            except Exception as e:
                logger.error(f"❌ No se pudieron obtener posiciones para cierre: {e}")
            return
    except Exception as e:
        logger.exception("💥 Error al verificar exposición")
        return

    # 4. Cash disponible
    try:
        available_cash = float(client.get_account().cash)
        logger.info(f"💵 Cash disponible al inicio: ${available_cash:,.2f}")
    except Exception as e:
        logger.warning(f"⚠️ No se pudo obtener cash: {e}")
        available_cash = 10000.0

    total_equity = current_equity

    # --- 5. BTC/USD 40% ---
    btc_allocation = 0.40
    equity_for_btc = total_equity * btc_allocation

    if "BTC/USD" in settings.symbols:
        try:
            df = fetch_bars("BTC/USD", start="2023-01-01")
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

                    # 🔥 Límite: no usar más del 90% del cash disponible
                    max_qty_by_cash = (available_cash * 0.9) / price
                    qty = min(qty, max_qty_by_cash)

                    if qty >= 1e-6:
                        is_crypto = True
                        pos = _get_position("BTC/USD")

                        if pos:
                            current_qty = float(pos.qty)
                            if (side == "buy" and current_qty > 0) or (side == "sell" and current_qty < 0):
                                logger.info(f"🟢 Posición {'larga' if current_qty > 0 else 'corta'} existente en BTC/USD. Aumentando...")
                                place_order("BTC/USD", qty, side, price, fractional=False, is_crypto=is_crypto)
                            elif side == "buy" and current_qty < 0:
                                logger.info("🔄 Cerrando corto y abriendo largo en BTC/USD")
                                place_order("BTC/USD", abs(current_qty), "buy", price, fractional=False, is_crypto=is_crypto)
                                place_order("BTC/USD", qty, "buy", price, fractional=False, is_crypto=is_crypto)
                            elif side == "sell" and current_qty > 0:
                                logger.info("🔄 Cerrando largo y abriendo corto en BTC/USD")
                                place_order("BTC/USD", abs(current_qty), "sell", price, fractional=False, is_crypto=is_crypto)
                                place_order("BTC/USD", qty, "sell", price, fractional=False, is_crypto=is_crypto)
                        else:
                            logger.info(f"📈 Abriendo nueva posición en BTC/USD ({'long' if side == 'buy' else 'short'})")
                            place_order("BTC/USD", qty, side, price, fractional=False, is_crypto=is_crypto)
        except Exception as e:
            logger.error(f"💥 Error procesando BTC/USD: {e}")

    # --- 6. Resto de símbolos 60% ---
    equity_for_rest = total_equity * 0.60
    other_symbols = [s for s in settings.symbols if s != "BTC/USD"]
    signals = []

    for symbol in other_symbols:
        try:
            df = fetch_bars(symbol, start="2023-01-01")
            if df.empty or len(df) < 100:
                continue
            feats = make_features(df)
            latest = feats.iloc[-1]

            sig = hybrid_signal(latest, clf)
            if sig == 0:
                continue

            signals.append({
                "symbol": symbol,
                "signal": sig,
                "features": latest,
                "price": float(latest["close"]),
                "atr": float(latest["atr_14"])
            })
        except Exception as e:
            logger.warning(f"⚠️ Error al calcular señal para {symbol}: {e}")

    signals.sort(key=lambda x: abs(x["signal"]), reverse=True)

    for item in signals:
        symbol = item["symbol"]
        sig = item["signal"]
        price = item["price"]
        atr = item["atr"]
        shares = volatility_target_size(equity_for_rest, price, atr)
        frac_k = kelly_cap(0.5 + abs(sig)/2, cap=settings.risk_per_trade * 4)
        leverage = max(min(abs(sig) + frac_k, 1.5), 0.1)
        qty = shares * leverage
        side = "buy" if sig > 0 else "sell"
        if qty < 1e-6:
            continue

        is_crypto = _is_crypto(symbol)
        pos = _get_position(symbol)
        if pos:
            current_qty = float(pos.qty)
            is_long = current_qty > 0
            is_short = current_qty < 0

            if side == "buy":
                if is_long:
                    logger.info(f"🟢 Posición larga existente en {symbol}. Aumentando...")
                    place_order(symbol, qty, "buy", price, fractional=not is_crypto, is_crypto=is_crypto)
                elif is_short:
                    logger.info(f"🔄 Cerrando corto y abriendo largo en {symbol}")
                    place_order(symbol, abs(current_qty), "buy", price, fractional=not is_crypto, is_crypto=is_crypto)
                    place_order(symbol, qty, "buy", price, fractional=not is_crypto, is_crypto=is_crypto)
            else:
                if is_short:
                    logger.info(f"🔴 Posición corta existente en {symbol}. Aumentando...")
                    place_order(symbol, qty, "sell", price, fractional=not is_crypto, is_crypto=is_crypto)
                elif is_long:
                    logger.info(f"🔄 Cerrando largo y abriendo corto en {symbol}")
                    place_order(symbol, abs(current_qty), "sell", price, fractional=not is_crypto, is_crypto=is_crypto)
                    place_order(symbol, qty, "sell", price, fractional=not is_crypto, is_crypto=is_crypto)
        else:
            logger.info(f"📈 Abriendo nueva posición en {symbol}")
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