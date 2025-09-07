# bot/telegram.py
import requests
from .config import settings
from .util import logger


def get_daily_change():
    """
    Obtiene el cambio diario de la cuenta de Alpaca.
    """
    try:
        from alpaca.trading.client import TradingClient
        
        client = TradingClient(
            api_key=settings.alpaca_api_key,
            secret_key=settings.alpaca_secret_key,
            paper=(settings.mode == "paper")
        )
        
        account = client.get_account()
        current_equity = float(account.equity)
        last_equity = float(getattr(account, "last_equity", current_equity))
        
        # Calcular cambio diario
        daily_change = current_equity - last_equity
        daily_change_pct = (daily_change / last_equity * 100) if last_equity > 0 else 0.0
        
        return daily_change, daily_change_pct, current_equity
    except Exception as e:
        logger.warning(f"⚠️ No se pudo obtener daily change: {e}")
        return 0.0, 0.0, 0.0


def send_telegram(message: str):
    """
    Envía un mensaje a Telegram usando el bot configurado.
    """
    if not settings.telegram_enabled:
        logger.info("📢 Telegram desactivado (TELEGRAM_ENABLED=false)")
        return

    try:
        # ✅ URL corregida: sin espacios extra
        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
        payload = {
            "chat_id": settings.telegram_chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        logger.info("📤 Enviando mensaje a Telegram...")
        response = requests.post(url, data=payload)

        if response.status_code == 200:
            logger.info("✅ Mensaje enviado correctamente a Telegram")
        else:
            logger.error(f"❌ Error al enviar a Telegram: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"❌ Excepción al enviar a Telegram: {e}")


def alert_trade_entry(symbol: str, side: str, qty: float, entry_price: float, tp_price=None, sl_price=None):
    """
    Alerta cuando se abre una posición.
    Incluye parámetros opcionales de take profit y stop loss para compatibilidad.
    """
    side_text = "🟢 LONG" if side == "long" else "🔴 SHORT"
    
    # Obtener cambio diario
    daily_change, daily_change_pct, current_equity = get_daily_change()
    daily_emoji = "📈" if daily_change >= 0 else "📉"
    
    # Formatear mensaje base
    msg = (
        f"{side_text} abierto\n"
        f"──────────────────\n"
        f"• Par: `{symbol}`\n"
        f"• Cantidad: `{qty:.6f}`\n"
        f"• Precio entrada: `${entry_price:,.2f}`\n"
        f"──────────────────\n"
        f"{daily_emoji} Daily Change: `${daily_change:+,.2f}` ({daily_change_pct:+.2f}%)\n"
        f"💰 Equity: `${current_equity:,.2f}`"
    )
    
    # Agregar TP/SL si están definidos
    if tp_price and tp_price > 0:
        msg += f"\n• Take Profit: `${tp_price:,.2f}`"
    if sl_price and sl_price > 0:
        msg += f"\n• Stop Loss: `${sl_price:,.2f}`"
    send_telegram(msg)


def alert_trade_exit(symbol: str, side: str, qty: float, exit_price: float, pnl: float, pnl_pct: float):
    """Envía alerta de cierre de posición (compatible con Alpaca v2)."""
    try:
        # ✅ Si exit_price no está definido o es 0, obtenemos la última barra
        if exit_price <= 0:
            from .data import fetch_last_bars
            df = fetch_last_bars(symbol, n=1)
            if not df.empty:
                exit_price = float(df["close"].iloc[-1])

        # Obtener cambio diario
        daily_change, daily_change_pct, current_equity = get_daily_change()
        daily_emoji = "📈" if daily_change >= 0 else "📉"
        pnl_emoji = "💚" if pnl >= 0 else "💔"

        msg = (
            f"❌ 🟢 {side.upper()} cerrado\n"
            "──────────────────\n"
            f"• Par: {symbol.replace('/', '')}\n"
            f"• Cantidad: {qty:.6f}\n"
            f"• Precio salida: ${exit_price:,.2f}\n"
            f"{pnl_emoji} P&L: `${pnl:+.2f}` ({pnl_pct:+.2%})\n"
            f"──────────────────\n"
            f"{daily_emoji} Daily Change: `${daily_change:+,.2f}` ({daily_change_pct:+.2f}%)\n"
            f"💰 Equity: `${current_equity:,.2f}`"
        )

        # Enviar alerta
        send_telegram(msg)

    except Exception as e:
        logger.error(f"❌ Error al enviar alerta de salida: {e}")


def alert_risk_stop(reason: str):
    """
    Alerta cuando se activa un stop de riesgo.
    """
    msg = (
        f"🛑 Stop de riesgo activado\n"
        f"──────────────────\n"
        f"• Motivo: `{reason}`\n"
        f"• Bot detenido para evitar más pérdidas."
    )
    send_telegram(msg)


def alert_error(title: str, details: str):
    """
    Alerta de error crítico.
    """
    msg = (
        f"💥 Error crítico\n"
        f"──────────────────\n"
        f"• Título: `{title}`\n"
        f"• Detalle: `{details}`"
    )
    send_telegram(msg)