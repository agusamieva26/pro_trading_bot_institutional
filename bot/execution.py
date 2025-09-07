from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.common.exceptions import APIError
from .config import settings
from .telegram import alert_trade_entry, alert_trade_exit
from .util import logger
import math
import logging

logger = logging.getLogger(__name__)

# --- Configuración ---
MIN_ORDER_NOTIONAL = 10.0  # mínimo en USD para cripto y fraccionales

# Variable para rastrear el cash que hemos reservado localmente
_reserved_cash = 0.0


def _client():
    return TradingClient(
        api_key=settings.alpaca_api_key,
        secret_key=settings.alpaca_secret_key,
        paper=(settings.mode == "paper")
    )


def _is_crypto(symbol: str) -> bool:
    return "/" in symbol or (symbol.endswith("USD") and symbol.isupper() and len(symbol) > 3)


def _is_fractional_equity(symbol: str, qty: float) -> bool:
    return not _is_crypto(symbol) and (not float(qty).is_integer())


def place_order(symbol: str, qty: float, side: str, price: float, fractional: bool = True, is_crypto: bool = False):
    """
    Envía una orden de mercado con validación de saldo real.
    """
    global _reserved_cash
    client = _client()
    base_symbol = symbol.replace("/", "")

    if qty < 1e-6:
        logger.warning(f"⚠️ Cantidad {qty} demasiado pequeña. Skip {symbol}.")
        return

    cost = qty * price

    # Validación mínimos
    if is_crypto and cost < MIN_ORDER_NOTIONAL:
        logger.warning(f"⚠️ Costo orden ${cost:.2f} < ${MIN_ORDER_NOTIONAL} en cripto. Skip {symbol}.")
        return

    # Verificar saldo REAL disponible
    try:
        account = client.get_account()
        total_cash = float(account.cash)

        # 🛑 Usa solo el 90% del cash y resta lo ya reservado
        available_cash = total_cash * 0.9 - _reserved_cash

        if side == "buy" and cost > available_cash:
            logger.warning(
                f"⚠️ Saldo real insuficiente: necesitas ${cost:.2f}, solo tienes ${available_cash:.2f} (reservado: {_reserved_cash:.2f}). Skip {symbol}."
            )
            return

        # 🔒 Reserva el cash inmediatamente
        _reserved_cash += cost
    except Exception as e:
        logger.error(f"❌ No se pudo verificar saldo: {e}")
        return

    order_side = OrderSide.BUY if side == "buy" else OrderSide.SELL

    try:
        # Caso 1: CRYPTO → notional + GTC
        if is_crypto:
            order = MarketOrderRequest(
                symbol=base_symbol,
                notional=round(cost, 2),
                side=order_side,
                time_in_force=TimeInForce.GTC,
            )
            client.submit_order(order)
            logger.info(f"✅ Orden CRYPTO enviada: {side.upper()} ${cost:.2f} {symbol}")
            alert_trade_entry(symbol, side, qty, price, tp_price=None, sl_price=None)

        # Caso 2: FRACTIONAL EQUITY → notional + DAY
        elif fractional:
            order = MarketOrderRequest(
                symbol=base_symbol,
                notional=round(cost, 2),
                side=order_side,
                time_in_force=TimeInForce.DAY,
            )
            client.submit_order(order)
            logger.info(f"✅ Orden FRACTIONAL enviada: {side.upper()} ${cost:.2f} {symbol}")
            alert_trade_entry(symbol, side, qty, price, tp_price=None, sl_price=None)

        # Caso 3: NON-FRACTIONAL EQUITY → qty entero + GTC
        else:
            qty_int = math.floor(qty)
            if qty_int < 1:
                logger.warning(f"🚫 Cantidad < 1 para equity no fraccional. Skip {symbol}.")
                return
            order = MarketOrderRequest(
                symbol=base_symbol,
                qty=qty_int,
                side=order_side,
                time_in_force=TimeInForce.GTC,
            )
            client.submit_order(order)
            logger.info(f"✅ Orden EQUITY enviada: {side.upper()} {qty_int} {symbol}")
            alert_trade_entry(symbol, side, qty_int, price, tp_price=None, sl_price=None)

    except APIError as e:
        # 🔁 Libera el cash si falla
        _reserved_cash -= cost
        if "insufficient balance" in str(e).lower():
            logger.error(f"❌ Saldo insuficiente: {e}")
        elif "invalid crypto time_in_force" in str(e).lower():
            logger.error(f"❌ Error time_in_force cripto: {e}")
        elif "cost basis must be >=" in str(e).lower():
            logger.error(f"❌ Costo mínimo no alcanzado: {e}")
        else:
            logger.error(f"❌ Error API al enviar orden {symbol}: {e}")
    except Exception as e:
        # 🔁 Libera el cash si falla
        _reserved_cash -= cost
        logger.error(f"❌ Error inesperado al enviar orden {symbol}: {e}")


def close_position(symbol: str, side: str = None, position_obj=None):
    """
    Cierra TODA la posición abierta en un símbolo dado usando Alpaca API.
    Usa el método nativo close_position para evitar errores de qty/TIF.
    
    Args:
        symbol: Símbolo de la posición
        side: Lado de la posición (opcional)
        position_obj: Objeto de posición de Alpaca (opcional, evita llamada adicional)
    """
    client = _client()
    base_symbol = symbol.replace("/", "")

    # Si tenemos el objeto de posición, úsalo directamente
    if position_obj:
        position = position_obj
        qty = float(position.qty)
    else:
        # Fallback: intentar obtener posición por símbolo
        try:
            position = client.get_position(base_symbol)
            qty = float(position.qty)
        except Exception:
            logger.info(f"No hay posición abierta para {symbol}.")
            return

    try:
        # 🔒 cerrar posición con Alpaca
        client.close_position(base_symbol)
        logger.info(f"✅ Posición cerrada: {base_symbol}")

        # 📩 Intentar estimar precio de salida
        exit_price = 0.0
        try:
            from .data import fetch_last_bars
            df = fetch_last_bars(base_symbol, n=1)
            if not df.empty:
                exit_price = float(df["close"].iloc[-1])
        except Exception:
            logger.warning(f"⚠️ No se pudo obtener precio de salida para {base_symbol}")

        # 🚀 Enviar alerta a Telegram
        try:
            alert_trade_exit(base_symbol, "flat", qty, exit_price, 0.0, 0.0)
        except Exception:
            logger.warning("⚠️ No se pudo enviar alerta de cierre a Telegram.")

    except Exception as e:
        logger.error(f"❌ No se pudo cerrar {symbol}: {e}")



def close_all():
    """
    Cierra TODAS las posiciones abiertas en la cuenta Alpaca
    y envía notificación a Telegram.
    """
    client = _client()
    try:
        positions = client.get_all_positions()
        if not positions:
            logger.info("📭 No hay posiciones abiertas.")
            try:
                from .telegram import send_telegram
                send_telegram("📭 No hay posiciones abiertas para cerrar.")
            except Exception:
                logger.warning("⚠️ No se pudo enviar alerta a Telegram.")
            return

        for pos in positions:
            symbol = pos.symbol
            try:
                close_position(symbol)
            except Exception as e:
                logger.error(f"❌ Error cerrando {symbol}: {e}")

        logger.info("✅ Todas las posiciones fueron cerradas.")
        try:
            from .telegram import send_telegram
            send_telegram("✅ Todas las posiciones han sido cerradas.")
        except Exception:
            logger.warning("⚠️ No se pudo enviar alerta a Telegram.")

    except Exception as e:
        logger.error(f"❌ Error al obtener posiciones: {e}")

# --- NUEVO: asignación dinámica de capital según score (positivo: buy, negativo: sell) ---

# --- NUEVO: asignación de capital optimizada con long/short y alertas Telegram ---
def allocate_and_place_orders(predictions: dict):
    """
    Distribuye capital y abre/cierra posiciones según scores del modelo.
    predictions: dict con {symbol: score}
      - score > 0: abrir o aumentar posición long
      - score < 0: abrir short (acciones) o cerrar long (cripto)
    Envía alertas a Telegram en cada operación.
    """
    client = _client()

    try:
        account = client.get_account()
        total_cash = float(account.cash) * 0.9  # usar solo 90% del cash
    except Exception as e:
        logger.error(f"❌ No se pudo obtener cash de la cuenta: {e}")
        return

    if not predictions:
        logger.warning("⚠️ No se recibieron predicciones para asignación.")
        return

    # Precalcular totales para pesos
    total_positive = sum(v for v in predictions.values() if v > 0)
    total_negative = sum(abs(v) for v in predictions.values() if v < 0)

    for sym, score in predictions.items():
        is_crypto = _is_crypto(sym)
        base_symbol = sym.replace("/", "")

        # Obtener último precio
        try:
            from .data import fetch_last_bars
            df = fetch_last_bars(sym, n=1)
            if df.empty:
                logger.warning(f"⚠️ No se pudo obtener precio para {sym}, skip.")
                continue
            price = float(df["close"].iloc[-1])
        except Exception as e:
            logger.warning(f"⚠️ Error al obtener precio de {sym}: {e}")
            continue

        # --- SCORE POSITIVO: LONG ---
        if score > 0 and total_positive > 0:
            weight = score / total_positive
            alloc_cash = total_cash * weight
            qty = alloc_cash / price
            logger.info(f"📊 LONG {sym}: score={score:.3f}, qty={qty:.6f}")
            place_order(sym, qty, "buy", price, fractional=True, is_crypto=is_crypto)
            try:
                alert_trade_entry(sym, "buy", qty, price, tp_price=None, sl_price=None)
            except Exception:
                logger.warning(f"⚠️ No se pudo enviar alerta Telegram LONG {sym}")

        # --- SCORE NEGATIVO ---
        elif score < 0 and total_negative > 0:
            weight = abs(score) / total_negative

            if is_crypto:
                # Cripto: solo cerrar long existente
                try:
                    position = client.get_position(base_symbol)
                    current_qty = float(position.qty)
                    qty_to_sell = current_qty * weight
                    if qty_to_sell < 1e-6:
                        continue
                    logger.info(f"📊 CIERRE PARCIAL {sym} (cripto): qty={qty_to_sell:.6f}")
                    place_order(sym, qty_to_sell, "sell", price, fractional=True, is_crypto=True)
                    try:
                        alert_trade_exit(sym, "flat", qty_to_sell, price, 0.0, 0.0)
                    except Exception:
                        logger.warning(f"⚠️ No se pudo enviar alerta Telegram cierre {sym}")
                except Exception:
                    logger.info(f"No hay posición abierta para {sym}, skip venta cripto.")
            else:
                # Acciones: abrir short
                alloc_cash = total_cash * weight
                qty = alloc_cash / price
                logger.info(f"📊 SHORT {sym}: score={score:.3f}, qty={qty:.6f}")
                place_order(sym, qty, "sell", price, fractional=True, is_crypto=False)
                try:
                    alert_trade_entry(sym, "sell", qty, price, tp_price=None, sl_price=None)
                except Exception:
                    logger.warning(f"⚠️ No se pudo enviar alerta Telegram SHORT {sym}")

