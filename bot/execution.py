# bot/execution.py
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from .config import settings
from .util import logger
from .trade_logger import log_trade_entry

# Global variable to track reserved cash
_reserved_cash = 0.0

def normalize_symbol(symbol: str) -> str:
    """Normalize symbol to consistent format (with slash for crypto)."""
    if "/" in symbol:
        return symbol
    if symbol.endswith("USD"):
        base = symbol.replace("USD", "")
        return f"{base}/USD"
    return symbol

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
        total_cash = float(getattr(account, 'cash', 0.0) or 0.0)
        # Usar 85% del cash para rotación agresiva (reservar 15%)
        available = total_cash * 0.85 - _reserved_cash  
        return max(0, available), total_cash
    except Exception as e:
        logger.error(f"❌ Error obteniendo cash disponible: {e}")
        return 0.0, 0.0

def place_order(symbol: str, qty: float, side: str, price: float | None = None, fractional: bool = True, is_crypto: bool = False):
    """Places a buy or sell order for the given symbol and quantity."""
    global _reserved_cash
    
    # Initialize notional_value to prevent undefined errors
    notional_value = 0.0
    
    try:
        # Convert symbol for API (remove slash for crypto)
        api_symbol = symbol.replace("/", "")
        
        # Calculate notional value needed
        if price is None:
            logger.error(f"❌ Price not provided for {symbol}")
            return False
        notional_value = float(qty) * float(price)
        
        # Check available cash before placing order
        available_cash, total_cash = get_available_cash()
        
        if side.lower() == "buy" and price:
            # NUEVO: Si no hay suficiente cash, intentar orden escalada
            if notional_value > available_cash:
                if available_cash < 10.0:  # Menos de $10 disponibles
                    logger.warning(f"⚠️ Liquidez crítica: ${available_cash:.2f} < $10. Skip {symbol}.")
                    return False
                    
                # Escalar orden al 80% del cash disponible
                scaled_notional = available_cash * 0.80
                scaled_qty = scaled_notional / price
                
                logger.info(f"💡 Escalando orden {symbol}: ${notional_value:.2f} → ${scaled_notional:.2f} (qty: {qty:.6f} → {scaled_qty:.6f})")
                
                # Actualizar valores para la orden escalada
                notional_value = scaled_notional
                qty = scaled_qty
            
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
            # Crypto no soporta DAY time_in_force, usar GTC en su lugar
            tif = TimeInForce.GTC if is_crypto else TimeInForce.DAY
            
            # 🚫 FILTRO ANTI-MICRO: Validar cantidad mínima significativa
            min_qty_crypto = 0.0001  # Cantidad mínima para crypto (vs 0.000000002)
            min_notional = 5.0       # Valor mínimo $5 para cualquier operación
            
            if is_crypto and float(qty) < min_qty_crypto:
                logger.warning(f"🚫 MICRO-OP BLOQUEADA: {symbol} qty={qty:.8f} < {min_qty_crypto}")
                return False
                
            if notional_value < min_notional:
                logger.warning(f"🚫 MICRO-OP BLOQUEADA: {symbol} valor=${notional_value:.2f} < ${min_notional}")
                return False
            
            order_request = MarketOrderRequest(
                symbol=api_symbol,
                qty=float(qty),
                side=order_side,
                time_in_force=tif
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
        # Release reserved cash on error (only if notional_value was set)
        if side.lower() == "buy" and notional_value > 0:
            _reserved_cash = max(0, _reserved_cash - notional_value)
        return False

def close_all(force_emergency: bool = False):
    """Cierra todas las posiciones abiertas con manejo inteligente de PDT.
    
    Args:
        force_emergency: Si True, fuerza el cierre ignorando restricciones PDT
    """
    client = _client()
    try:
        positions = client.get_all_positions()
        if not positions:
            logger.info("✅ No hay posiciones abiertas para cerrar")
            return
            
        logger.critical(f"🚨 Cerrando {len(positions)} posiciones abiertas... (Emergency: {force_emergency})")
        closed_count = 0
        pdt_blocked_count = 0
        failed_count = 0
        
        # Separate crypto and stock positions for better handling
        crypto_positions = []
        stock_positions = []
        
        for position in positions:
            pos_symbol = getattr(position, 'symbol', '') or ""
            normalized_symbol = normalize_symbol(pos_symbol)
            
            if "/" in normalized_symbol:
                crypto_positions.append((position, normalized_symbol))
            else:
                stock_positions.append((position, normalized_symbol))
        
        # Close crypto positions first (no PDT restrictions)
        logger.info(f"🪙 Cerrando {len(crypto_positions)} posiciones crypto...")
        for position, symbol in crypto_positions:
            try:
                success = close_position(symbol, force_close=force_emergency)
                if success:
                    closed_count += 1
                    logger.info(f"✅ CRYPTO {symbol}: Cerrado ({closed_count}/{len(positions)})")
                else:
                    failed_count += 1
                    logger.warning(f"⚠️ CRYPTO {symbol}: Falló cierre")
                    
            except Exception as e:
                failed_count += 1
                logger.error(f"❌ Error cerrando crypto {symbol}: {e}")
        
        # Close stock positions with PDT handling
        if stock_positions:
            logger.info(f"📈 Cerrando {len(stock_positions)} posiciones stocks...")
            for position, symbol in stock_positions:
                try:
                    success = close_position(symbol, force_close=force_emergency)
                    if success:
                        closed_count += 1
                        logger.info(f"✅ STOCK {symbol}: Cerrado ({closed_count}/{len(positions)})")
                    else:
                        pdt_blocked_count += 1
                        logger.warning(f"⏳ STOCK {symbol}: Bloqueado por PDT - esperando hasta mañana")
                        
                except Exception as e:
                    failed_count += 1
                    logger.error(f"❌ Error cerrando stock {symbol}: {e}")
        
        # Summary report
        total_attempted = len(positions)
        logger.critical(f"🎯 CIERRE COMPLETADO:")
        logger.critical(f"   ✅ Cerradas exitosamente: {closed_count}/{total_attempted}")
        if pdt_blocked_count > 0:
            logger.critical(f"   ⏳ Bloqueadas por PDT: {pdt_blocked_count} (se cerrarán mañana)")
        if failed_count > 0:
            logger.critical(f"   ❌ Fallaron: {failed_count}")
            
        if force_emergency and (pdt_blocked_count > 0 or failed_count > 0):
            logger.warning("🚨 EMERGENCY MODE: Algunas posiciones no se cerraron a pesar del force")
        
    except Exception as e:
        logger.error(f"❌ Error crítico obteniendo posiciones para cerrar: {e}")

def close_position(symbol: str, force_close: bool = False, retry_count: int = 0):
    """Close an existing position for the given symbol with PDT and balance protection.
    
    Args:
        symbol: The symbol to close
        force_close: If True, attempt closure even with PDT restrictions
        retry_count: Current retry attempt (for internal use)
    """
    import json
    from datetime import datetime, timezone
    
    try:
        client = _client()
        api_symbol = symbol.replace("/", "")
        is_crypto = "/" in symbol
        
        # Get current position with retry for crypto balance sync
        try:
            position = client.get_open_position(api_symbol)
            if not position:
                logger.debug(f"ℹ️ No hay posición abierta para {symbol}")
                return True
                
            qty = float(str(getattr(position, 'qty', 0) or 0))
            
            # 🚫 FILTRO ANTI-MICRO: No cerrar posiciones microscópicas
            market_value = abs(float(str(getattr(position, 'market_value', 0) or 0)))
            min_market_value = 5.0  # Mínimo $5 para que valga la pena cerrar
            min_qty_threshold = 0.0001 if is_crypto else 0.001
            
            if abs(qty) < min_qty_threshold or market_value < min_market_value:
                logger.debug(f"🚫 MICRO-POSICIÓN IGNORADA: {symbol} qty={qty:.8f}, valor=${market_value:.2f}")
                return True  # Considerar como "cerrada exitosamente" para limpiar tracking
                
            side = "sell" if qty > 0 else "buy"
            abs_qty = abs(qty)
            
            # PDT PROTECTION: Check if position was opened today (for stocks)
            if not is_crypto and not force_close:
                try:
                    # Get account to check day trading buying power
                    account = client.get_account()
                    equity = float(getattr(account, 'equity', 0))
                    
                    # If account under $25k, check for PDT restrictions
                    if equity < 25000:
                        # Check day trading buying power
                        dt_buying_power = float(getattr(account, 'day_trading_buying_power', 0))
                        
                        # If minimal day trading power, likely PDT restricted
                        if dt_buying_power < 1000:
                            logger.warning(f"⚠️ PDT RESTRICTION: {symbol} - Account bajo $25k con power limitado. Esperando hasta mañana.")
                            return False  # Don't attempt closure
                            
                except Exception as pdt_check_error:
                    logger.debug(f"Error checking PDT status for {symbol}: {pdt_check_error}")
            
            # CRYPTO BALANCE PROTECTION: Verify balance for crypto positions
            if is_crypto and retry_count == 0:
                try:
                    # For crypto, reduce quantity slightly to avoid precision errors
                    abs_qty = abs_qty * 0.9995  # Reduce by 0.05% for safety
                    logger.debug(f"🔒 {symbol}: Cantidad ajustada por precision: {abs(qty):.8f} → {abs_qty:.8f}")
                except Exception:
                    pass
            
            # Create market order to close position
            order_side = OrderSide.SELL if qty > 0 else OrderSide.BUY
            tif = TimeInForce.GTC if is_crypto else TimeInForce.DAY
            
            order_request = MarketOrderRequest(
                symbol=api_symbol,
                qty=abs_qty,
                side=order_side,
                time_in_force=tif
            )
            
            order = client.submit_order(order_request)
            asset_type = "CRYPTO" if is_crypto else "STOCK"
            logger.info(f"✅ {asset_type} cerrado: {side.upper()} {abs_qty:.8f} {symbol}")
            return True
            
        except Exception as position_error:
            error_str = str(position_error)
            
            # ENHANCED ERROR HANDLING
            if "40310000" in error_str or "day trades permitted" in error_str:
                logger.warning(f"🚫 PDT RESTRICTION: {symbol} - No se puede cerrar posición del mismo día (cuenta < $25k)")
                return False
            elif "insufficient" in error_str.lower() and is_crypto:
                if retry_count < 2:
                    logger.warning(f"⚠️ {symbol}: Balance insuficiente, reintentando con cantidad menor... (intento {retry_count + 1})")
                    import time
                    time.sleep(1)  # Wait for balance sync
                    return close_position(symbol, force_close, retry_count + 1)
                else:
                    logger.error(f"❌ {symbol}: Falló tras {retry_count + 1} intentos - balance persistentemente insuficiente")
                    return False
            elif "position not found" in error_str.lower() or "no position" in error_str.lower():
                logger.debug(f"ℹ️ No hay posición abierta para {symbol}")
                return True
            else:
                logger.error(f"❌ Error inesperado cerrando {symbol}: {position_error}")
                return False
            
    except Exception as e:
        logger.error(f"❌ Error crítico closing position for {symbol}: {e}")
        return False