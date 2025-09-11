# bot/telegram.py
import requests
import time
from collections import defaultdict
from .config import settings
from .util import logger

# Rate limiting system for telegram messages
_telegram_message_buffer = []
_last_buffer_send = 0
_BUFFER_TIMEOUT = 30  # seconds
_MAX_MESSAGES_PER_MINUTE = 8


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
        current_equity = float(getattr(account, 'equity', 0.0) or 0.0)
        last_equity = float(getattr(account, "last_equity", current_equity))
        
        # Calcular cambio diario
        daily_change = current_equity - last_equity
        daily_change_pct = (daily_change / last_equity * 100) if last_equity > 0 else 0.0
        
        return daily_change, daily_change_pct, current_equity
    except Exception as e:
        logger.warning(f"⚠️ No se pudo obtener daily change: {e}")
        return 0.0, 0.0, 0.0


def _should_rate_limit() -> bool:
    """Check if we should rate limit telegram messages."""
    global _telegram_message_buffer
    
    current_time = time.time()
    
    # Remove messages older than 1 minute
    minute_ago = current_time - 60
    _telegram_message_buffer = [msg_time for msg_time in _telegram_message_buffer if msg_time > minute_ago]
    
    # Check if we're over the limit
    return len(_telegram_message_buffer) >= _MAX_MESSAGES_PER_MINUTE

def _send_immediate_telegram(message: str) -> bool:
    """Send telegram message immediately without rate limiting."""
    global _telegram_message_buffer
    
    if not settings.telegram_enabled:
        logger.info("📢 Telegram desactivado (TELEGRAM_ENABLED=false)")
        return False

    try:
        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
        payload = {
            "chat_id": settings.telegram_chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        response = requests.post(url, data=payload)
        
        if response.status_code == 200:
            # Add to rate limit buffer
            _telegram_message_buffer.append(time.time())
            logger.info("✅ Mensaje enviado correctamente a Telegram")
            return True
        else:
            logger.error(f"❌ Error al enviar a Telegram: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"❌ Excepción al enviar a Telegram: {e}")
        return False

def send_telegram(message: str):
    """
    Envía un mensaje a Telegram con rate limiting inteligente.
    """
    if _should_rate_limit():
        logger.warning(f"⏰ Rate limit Telegram: mensaje omitido ({len(_telegram_message_buffer)}/{_MAX_MESSAGES_PER_MINUTE})")
        return
    
    logger.info("📤 Enviando mensaje a Telegram...")
    _send_immediate_telegram(message)


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


# Message grouping for position closures to reduce spam
_pending_closures = defaultdict(list)
_last_closure_send = defaultdict(float)

def _group_and_send_closures():
    """Send grouped closure messages to reduce telegram spam."""
    global _pending_closures, _last_closure_send
    
    current_time = time.time()
    
    for symbol, closures in list(_pending_closures.items()):
        # Send if we have multiple closures or it's been >45 seconds
        time_since_last = current_time - _last_closure_send[symbol]
        
        if len(closures) >= 2 or (len(closures) >= 1 and time_since_last > 45):
            if len(closures) == 1:
                # Single closure - send normal message
                closure = closures[0]
                _send_single_closure_message(closure['symbol'], closure['side'], closure['qty'], 
                                           closure['exit_price'], closure['pnl'], closure['pnl_pct'])
            else:
                # Multiple closures - send grouped message
                _send_grouped_closure_message(symbol, closures)
            
            # Clear pending closures for this symbol
            _pending_closures[symbol] = []
            _last_closure_send[symbol] = current_time

def _send_single_closure_message(symbol: str, side: str, qty: float, exit_price: float, pnl: float, pnl_pct: float):
    """Send a single closure message."""
    try:
        if exit_price <= 0:
            from .data import fetch_last_bars
            df = fetch_last_bars(symbol, n=1)
            if not df.empty:
                exit_price = float(df["close"].iloc[-1])

        daily_change, daily_change_pct, current_equity = get_daily_change()
        daily_emoji = "📈" if daily_change >= 0 else "📉"
        pnl_emoji = "💚" if pnl >= 0 else "💔"

        exit_price_str = f"{exit_price:.6f}" if exit_price < 0.01 else f"{exit_price:,.2f}"
        pnl_str = f"{pnl:+.6f}" if abs(pnl) < 0.01 else f"{pnl:+.2f}"
        
        msg = (
            f"❌ 🟢 {side.upper()} cerrado\n"
            "──────────────────\n"
            f"• Par: {symbol.replace('/', '')}\n"
            f"• Cantidad: {qty:.6f}\n"
            f"• Precio salida: ${exit_price_str}\n"
            f"{pnl_emoji} P&L: `${pnl_str}` ({pnl_pct:+.2%})\n"
            f"──────────────────\n"
            f"{daily_emoji} Daily Change: `${daily_change:+,.2f}` ({daily_change_pct:+.2f}%)\n"
            f"💰 Equity: `${current_equity:,.2f}`"
        )
        _send_immediate_telegram(msg)
    except Exception as e:
        logger.error(f"❌ Error enviando mensaje individual: {e}")

def _send_grouped_closure_message(symbol: str, closures: list):
    """Send a grouped message for multiple closures."""
    try:
        daily_change, daily_change_pct, current_equity = get_daily_change()
        daily_emoji = "📈" if daily_change >= 0 else "📉"
        
        total_pnl = sum(c['pnl'] for c in closures)
        total_pnl_emoji = "💚" if total_pnl >= 0 else "💔"
        
        msg = (
            f"❌ {len(closures)}x {symbol.replace('/', '')} cerrados\n"
            "──────────────────\n"
        )
        
        for i, closure in enumerate(closures[:4], 1):  # Max 4 in message
            msg += f"• #{i}: {closure['qty']:.4f} → ${closure['pnl']:+.2f} ({closure['pnl_pct']:+.1%})\n"
        
        if len(closures) > 4:
            msg += f"• +{len(closures)-4} más...\n"
            
        msg += (
            f"──────────────────\n"
            f"{total_pnl_emoji} Total P&L: `${total_pnl:+.2f}`\n"
            f"{daily_emoji} Daily: `${daily_change:+,.2f}` ({daily_change_pct:+.2f}%)\n"
            f"💰 Equity: `${current_equity:,.2f}`"
        )
        
        _send_immediate_telegram(msg)
    except Exception as e:
        logger.error(f"❌ Error enviando mensaje agrupado: {e}")

def alert_trade_exit(symbol: str, side: str, qty: float, exit_price: float, pnl: float, pnl_pct: float):
    """Envía alerta de cierre de posición con grouping inteligente para reducir spam."""
    global _pending_closures
    
    try:
        # Add to pending closures for potential grouping
        _pending_closures[symbol].append({
            'symbol': symbol,
            'side': side,
            'qty': qty,
            'exit_price': exit_price,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'timestamp': time.time()
        })
        
        # Check if we should send grouped messages
        _group_and_send_closures()
        
    except Exception as e:
        logger.error(f"❌ Error al procesar alerta de salida: {e}")


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