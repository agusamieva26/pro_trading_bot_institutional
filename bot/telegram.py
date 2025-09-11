# bot/telegram.py
import requests
import time
from collections import defaultdict
from .config import settings
from .util import logger

# Rate limiting system for telegram messages - ENHANCED ANTI-SPAM
_telegram_message_buffer = []
_last_buffer_send = 0
_BUFFER_TIMEOUT = 60  # seconds - increased for better grouping
_MAX_MESSAGES_PER_MINUTE = 3  # reduced to prevent spam

# Enhanced message deduplication and grouping
_sent_message_hashes = set()  # Track sent messages to prevent duplicates
_HASH_CLEANUP_INTERVAL = 300  # 5 minutes
_last_hash_cleanup = 0


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
    """Enhanced rate limiting with stricter controls."""
    global _telegram_message_buffer
    
    current_time = time.time()
    
    # Remove messages older than 1 minute
    minute_ago = current_time - 60
    _telegram_message_buffer = [msg_time for msg_time in _telegram_message_buffer if msg_time > minute_ago]
    
    # Check if we're over the limit (now stricter: 3/min instead of 8/min)
    return len(_telegram_message_buffer) >= _MAX_MESSAGES_PER_MINUTE

def _cleanup_message_hashes():
    """Clean up old message hashes to prevent memory bloat."""
    global _sent_message_hashes, _last_hash_cleanup
    
    current_time = time.time()
    if current_time - _last_hash_cleanup > _HASH_CLEANUP_INTERVAL:
        _sent_message_hashes.clear()
        _last_hash_cleanup = current_time
        logger.debug("🧹 Limpieza de hashes de mensajes completada")

def _get_message_hash(message: str) -> str:
    """Generate a hash for message deduplication."""
    import hashlib
    # Remove dynamic parts (timestamps, prices) for deduplication
    normalized = message.lower()
    # Remove price patterns, timestamps, and dynamic numbers
    import re
    normalized = re.sub(r'\$[\d,.-]+', '$X', normalized)
    normalized = re.sub(r'[\d,.-]+%', 'X%', normalized)
    normalized = re.sub(r'\d{2}:\d{2}:\d{2}', 'XX:XX:XX', normalized)
    return hashlib.md5(normalized.encode()).hexdigest()[:8]

def _is_duplicate_message(message: str) -> bool:
    """Check if this message was already sent recently."""
    global _sent_message_hashes
    
    _cleanup_message_hashes()
    
    msg_hash = _get_message_hash(message)
    if msg_hash in _sent_message_hashes:
        logger.debug(f"🚫 Mensaje duplicado detectado (hash: {msg_hash})")
        return True
    
    _sent_message_hashes.add(msg_hash)
    return False

def _send_immediate_telegram(message: str) -> bool:
    """Send telegram message immediately with enhanced deduplication."""
    global _telegram_message_buffer
    
    if not settings.telegram_enabled:
        logger.info("📢 Telegram desactivado (TELEGRAM_ENABLED=false)")
        return False

    # Check for duplicate messages
    if _is_duplicate_message(message):
        logger.info("🚫 Mensaje duplicado omitido")
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
    Enhanced telegram sending with strict rate limiting and deduplication.
    """
    if _should_rate_limit():
        logger.warning(f"⏰ Rate limit Telegram: mensaje omitido ({len(_telegram_message_buffer)}/{_MAX_MESSAGES_PER_MINUTE})")
        return
    
    logger.info("📤 Enviando mensaje a Telegram...")
    _send_immediate_telegram(message)

def force_send_pending_closures():
    """Force send any pending closure notifications (useful for cleanup)."""
    global _pending_closures
    if not _pending_closures:
        return
    
    logger.info(f"🚀 Forzando envío de {sum(len(c) for c in _pending_closures.values())} cierres pendientes")
    _send_global_grouped_message(time.time())


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


# ENHANCED MESSAGE GROUPING SYSTEM - Anti-spam for closures
_pending_closures = defaultdict(list)
_last_closure_send = defaultdict(float)
_global_closure_buffer = []  # Global buffer for cross-symbol grouping
_last_global_send = 0
_GLOBAL_BUFFER_TIMEOUT = 90  # seconds - group across all symbols
_MAX_INDIVIDUAL_CLOSURES = 3  # max individual messages before forcing group

def _group_and_send_closures():
    """Enhanced intelligent grouping system to eliminate spam."""
    global _pending_closures, _last_closure_send, _global_closure_buffer, _last_global_send
    
    current_time = time.time()
    total_pending = sum(len(closures) for closures in _pending_closures.values())
    
    # Strategy 1: If many symbols with closures, use global grouping
    if len(_pending_closures) >= 3 or total_pending >= 5:
        _send_global_grouped_message(current_time)
        return
    
    # Strategy 2: Individual symbol grouping (improved timing)
    for symbol, closures in list(_pending_closures.items()):
        time_since_last = current_time - _last_closure_send[symbol]
        should_send = (
            len(closures) >= _MAX_INDIVIDUAL_CLOSURES or  # Force send after 3 closures
            (len(closures) >= 2 and time_since_last > 30) or  # 2+ closures after 30s
            (len(closures) >= 1 and time_since_last > _BUFFER_TIMEOUT)  # Any closure after 60s
        )
        
        if should_send:
            if len(closures) == 1:
                _send_single_closure_message(symbol, closures[0])
            else:
                _send_grouped_closure_message(symbol, closures)
            
            # Clear pending closures for this symbol
            _pending_closures[symbol] = []
            _last_closure_send[symbol] = current_time

def _send_global_grouped_message(current_time: float):
    """Send a consolidated message for multiple symbols."""
    global _pending_closures, _last_global_send
    
    if not _pending_closures:
        return
    
    try:
        daily_change, daily_change_pct, current_equity = get_daily_change()
        daily_emoji = "📈" if daily_change >= 0 else "📉"
        
        # Collect all closures
        all_closures = []
        symbol_summaries = {}
        
        for symbol, closures in _pending_closures.items():
            all_closures.extend(closures)
            symbol_summaries[symbol] = {
                'count': len(closures),
                'total_qty': sum(c['qty'] for c in closures),
                'total_pnl': sum(c['pnl'] for c in closures)
            }
        
        total_pnl = sum(c['pnl'] for c in all_closures)
        total_count = len(all_closures)
        pnl_emoji = "💚" if total_pnl >= 0 else "💔"
        
        # Build consolidated message
        msg = (
            f"❌ {total_count}x Posiciones cerradas\n"
            "──────────────────\n"
        )
        
        # Add symbol summaries (max 4 symbols)
        for i, (symbol, summary) in enumerate(list(symbol_summaries.items())[:4]):
            symbol_clean = symbol.replace('/', '')
            msg += f"• {summary['count']}x {symbol_clean}: {summary['total_qty']:.4f} → ${summary['total_pnl']:+.2f}\n"
        
        if len(symbol_summaries) > 4:
            msg += f"• +{len(symbol_summaries)-4} símbolos más...\n"
        
        msg += (
            f"──────────────────\n"
            f"{pnl_emoji} Total P&L: `${total_pnl:+.2f}`\n"
            f"{daily_emoji} Daily: `${daily_change:+,.2f}` ({daily_change_pct:+.2f}%)\n"
            f"💰 Equity: `${current_equity:,.2f}`"
        )
        
        _send_immediate_telegram(msg)
        
        # Clear all pending closures
        _pending_closures.clear()
        _last_global_send = current_time
        
    except Exception as e:
        logger.error(f"❌ Error enviando mensaje global agrupado: {e}")

def _send_single_closure_message(symbol: str, closure: dict):
    """Send an optimized single closure message."""
    try:
        side = closure['side']
        qty = closure['qty']
        exit_price = closure['exit_price']
        pnl = closure['pnl']
        pnl_pct = closure['pnl_pct']
        
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
            f"❌ {symbol.replace('/', '')} cerrado\n"
            "──────────────────\n"
            f"• Cantidad: {qty:.6f}\n"
            f"• Precio salida: ${exit_price_str}\n"
            f"{pnl_emoji} P&L: `${pnl_str}` ({pnl_pct:+.2%})\n"
            f"──────────────────\n"
            f"{daily_emoji} Daily: `${daily_change:+,.2f}` ({daily_change_pct:+.2f}%)\n"
            f"💰 Equity: `${current_equity:,.2f}`"
        )
        _send_immediate_telegram(msg)
    except Exception as e:
        logger.error(f"❌ Error enviando mensaje individual: {e}")

def _send_grouped_closure_message(symbol: str, closures: list):
    """Send an optimized grouped message for multiple closures of same symbol."""
    try:
        daily_change, daily_change_pct, current_equity = get_daily_change()
        daily_emoji = "📈" if daily_change >= 0 else "📉"
        
        total_qty = sum(c['qty'] for c in closures)
        total_pnl = sum(c['pnl'] for c in closures)
        avg_pnl_pct = sum(c['pnl_pct'] for c in closures) / len(closures)
        total_pnl_emoji = "💚" if total_pnl >= 0 else "💔"
        
        msg = (
            f"❌ {len(closures)}x {symbol.replace('/', '')} cerrados\n"
            "──────────────────\n"
            f"• Total cantidad: {total_qty:.6f}\n"
            f"{total_pnl_emoji} Total P&L: `${total_pnl:+.2f}` (avg: {avg_pnl_pct:+.1%})\n"
        )
        
        # Add details for first few closures if space allows
        if len(closures) <= 3:
            for i, closure in enumerate(closures, 1):
                msg += f"• #{i}: {closure['qty']:.4f} → ${closure['pnl']:+.2f}\n"
        else:
            msg += f"• {len(closures)} operaciones individuales consolidadas\n"
            
        msg += (
            f"──────────────────\n"
            f"{daily_emoji} Daily: `${daily_change:+,.2f}` ({daily_change_pct:+.2f}%)\n"
            f"💰 Equity: `${current_equity:,.2f}`"
        )
        
        _send_immediate_telegram(msg)
    except Exception as e:
        logger.error(f"❌ Error enviando mensaje agrupado: {e}")

def alert_trade_exit(symbol: str, side: str, qty: float, exit_price: float, pnl: float, pnl_pct: float):
    """Enhanced trade exit alerts with intelligent spam prevention."""
    global _pending_closures, _global_closure_buffer
    
    try:
        # Create closure record
        closure = {
            'symbol': symbol,
            'side': side,
            'qty': qty,
            'exit_price': exit_price,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'timestamp': time.time()
        }
        
        # Add to pending closures for intelligent grouping
        _pending_closures[symbol].append(closure)
        _global_closure_buffer.append(closure)
        
        # Log for debugging (but don't send immediate notification)
        logger.debug(f"📤 Closure buffered: {side} {qty:.6f} {symbol} @ ${exit_price:.4f} | P&L: ${pnl:+.2f} ({pnl_pct:+.2%})")
        
        # Trigger intelligent grouping check
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