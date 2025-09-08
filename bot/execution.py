# bot/execution.py
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from .config import settings
from .util import logger
from .trade_logger import log_trade_entry

# Global variable to track reserved cash
_reserved_cash = 0.0

def _client():
    """Create Alpaca trading client"""
    return TradingClient(
        api_key=settings.alpaca_api_key,
        secret_key=settings.alpaca_secret_key,
        paper=(settings.mode == "paper")
    )

def reset_reserved_cash():
    """Resetea el contador de cash reservado. Llamar al inicio de cada iteración."""
    global _reserved_cash
    old_reserved = _reserved_cash
    _reserved_cash = 0.0
    if old_reserved > 0:
        logger.info(f"🔄 Cash reservado reseteado: ${old_reserved:.2f} → $0.00")

def get_available_cash():
    """Retorna el cash realmente disponible para trading."""
    try:
        client = _client()
        account = client.get_account()
        total_cash = float(account.cash)
        available = total_cash * 0.9 - _reserved_cash
        return max(0, available), total_cash
    except Exception as e:
        logger.error(f"❌ Error obteniendo cash disponible: {e}")
        return 0.0, 0.0

def place_order(symbol: str, qty: float, side: str, price: float = None, fractional: bool = True, is_crypto: bool = False):
    """Places a buy or sell order for the given symbol and quantity."""
    global _reserved_cash
    
    try:
        # Convert symbol for API (remove slash for crypto)
        api_symbol = symbol.replace("/", "")
        
        # Calculate notional value needed
        if price is None:
            logger.error(f"❌ Price not provided for {symbol}")
            return False
        notional_value = qty * price
        
        # Check available cash before placing order
        available_cash, total_cash = get_available_cash()
        
        if side.lower() == "buy" and price and notional_value > available_cash:
            logger.warning(f"⚠️ Saldo real insuficiente: necesitas ${notional_value:.2f}, solo tienes ${available_cash:.2f} (reservado: {_reserved_cash}). Skip {symbol}.")
            return False
            
        # Reserve cash for this order
        if side.lower() == "buy":
            _reserved_cash += notional_value
            
        # Create order request
        order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
        
        # Use notional for fractional shares, qty for whole shares
        if fractional and not is_crypto and qty < 1.0:
            # Use notional for fractional stock orders
            order_request = MarketOrderRequest(
                symbol=api_symbol,
                side=order_side,
                time_in_force=TimeInForce.DAY,
                notional=notional_value
            )
        else:
            # Use quantity for crypto and whole shares
            order_request = MarketOrderRequest(
                symbol=api_symbol,
                qty=float(qty),
                side=order_side,
                time_in_force=TimeInForce.DAY
            )
            
        # Submit order
        client = _client()
        order = client.submit_order(order_request)
        
        order_type = "CRYPTO" if is_crypto else "STOCK"
        logger.info(f"✅ Orden {order_type} enviada: {side.upper()} ${notional_value:.2f} {symbol}")
        
        # Log trade entry
        log_trade_entry(symbol, qty, side, price)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error placing order for {symbol}: {e}")
        # Release reserved cash on error
        if side.lower() == "buy":
            _reserved_cash = max(0, _reserved_cash - notional_value)
        return False

def close_position(symbol: str):
    """Close an existing position for the given symbol."""
    try:
        client = _client()
        api_symbol = symbol.replace("/", "")
        
        # Get current position
        try:
            position = client.get_open_position(api_symbol)
            if not position:
                logger.info(f"ℹ️ No hay posición abierta para {symbol}")
                return True
                
            qty = float(str(position.qty))
            side = "sell" if qty > 0 else "buy"
            abs_qty = abs(qty)
            
            # Create market order to close position
            order_side = OrderSide.SELL if qty > 0 else OrderSide.BUY
            order_request = MarketOrderRequest(
                symbol=api_symbol,
                qty=abs_qty,
                side=order_side,
                time_in_force=TimeInForce.DAY
            )
            
            order = client.submit_order(order_request)
            logger.info(f"✅ Posición cerrada: {side.upper()} {abs_qty} {symbol}")
            return True
            
        except Exception as position_error:
            logger.info(f"ℹ️ No hay posición abierta para {symbol}: {position_error}")
            return True
            
    except Exception as e:
        logger.error(f"❌ Error closing position for {symbol}: {e}")
        return False