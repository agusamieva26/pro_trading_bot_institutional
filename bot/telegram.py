# bot/telegram.py
import requests
from .config import settings
from .util import logger


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


def alert_trade_entry(symbol: str, side: str, qty: float, entry_price: float):
    """
    Alerta cuando se abre una posición.
    """
    side_text = "🟢 LONG" if side == "long" else "🔴 SHORT"
    msg = (
        f"{side_text} abierto\n"
        f"──────────────────\n"
        f"• Par: `{symbol}`\n"
        f"• Cantidad: `{qty:.6f}`\n"
        f"• Precio entrada: `${entry_price:,.2f}`"
    )
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

        msg = (
            f"❌ 🟢 {side.upper()} cerrado\n"
            "──────────────────\n"
            f"• Par: {symbol.replace('/', '')}\n"
            f"• Cantidad: {qty:.6f}\n"
            f"• Precio salida: ${exit_price:,.2f}\n"
            f"• P&L: ${pnl:+.2f} ({pnl_pct:+.2%})"
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