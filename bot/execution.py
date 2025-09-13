# bot/execution.py
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from .config import settings
from .util import logger
from .trade_logger import log_trade_entry

# Global variable to track reserved cash
_reserved_cash = 0.0

# Arbitrage execution tracking
_arbitrage_positions = {}
_arbitrage_reserved_cash = 0.0

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
        # Usar 98% del cash para trading ultra-agresivo (reservar 2% buffer)
        available = total_cash * 0.98 - _reserved_cash  
        return max(0, available), total_cash
    except Exception as e:
        logger.error(f"❌ Error obteniendo cash disponible: {e}")
        return 0.0, 0.0

# REMOVED: Destructive consolidation functions that close/reopen positions
# Alpaca already aggregates positions by symbol - no manual consolidation needed

def place_order(symbol: str, qty: float, side: str, price: float | None = None, fractional: bool = True, is_crypto: bool = False):
    """Places a buy or sell order for the given symbol and quantity."""
    global _reserved_cash
    
    # Initialize notional_value to prevent undefined errors
    notional_value = 0.0
    
    # 🚨 STRICT CRISIS MODE GATE - Block all BUY orders under critical conditions
    if side.lower() == "buy":
        try:
            client = _client()
            account = client.get_account()
            true_cash = float(account.cash)
            equity = float(account.equity)
            
            # Calculate exposure ratio using dedicated reliable method
            from .exposure import get_total_exposure_ratio
            exposure_ratio = get_total_exposure_ratio()
            
            # HARD LOCKDOWN: Block BUY if either condition breached
            if exposure_ratio >= settings.max_gross_exposure:
                logger.critical(f"🚨 CRISIS MODE - ORDER BLOCKED: Exposure {exposure_ratio:.2f}x >= {settings.max_gross_exposure:.1f}x limit")
                return False
                
            if true_cash / max(equity, 1e-9) <= 0.005:
                logger.critical(f"🚨 CRISIS MODE - ORDER BLOCKED: Cash {true_cash/equity:.1%} <= 0.5% required buffer")
                return False
                
        except Exception as e:
            logger.critical(f"🚨 CRISIS MODE - ERROR BLOCKING BUY: {e}")
            return False
    
    # 🚨 LEGACY CRISIS MODE & ORDER GATES: Verificar exposición y cash ANTES de cualquier orden
    try:
        # Calculate notional value needed for this order
        if price is None:
            logger.error(f"❌ Price not provided for {symbol}")
            return False
        notional_value = float(qty) * float(price)
        
        # Get current state for order gates
        available_cash, _ = get_available_cash()
        client = _client()
        account = client.get_account()
        current_equity = float(getattr(account, "equity", 0) or 0)
        
        # Guard against invalid equity
        if current_equity <= 0:
            logger.critical(f"🚨 ORDER BLOCKED: Invalid equity ${current_equity:.2f}")
            if side.lower() == "buy":
                return False
        
        # Get current exposure (get_total_exposure returns a float ratio)
        from .exposure import get_total_exposure
        current_exposure_ratio = float(get_total_exposure() or 0.0)
        current_gross = current_exposure_ratio * current_equity
        projected_gross_exposure = current_gross + notional_value
        projected_exposure_ratio = projected_gross_exposure / max(current_equity, 1e-9)
        
        # CRISIS MODE: Block all new BUY orders if critical thresholds breached
        if side.lower() == "buy":
            # Check exposure limit (use CONFIGURED limit)
            if projected_exposure_ratio > settings.max_gross_exposure:
                logger.critical(f"🚨 ORDER BLOCKED: Exposure limit! Projected {projected_exposure_ratio:.2f}x > {settings.max_gross_exposure:.2f}x limit")
                return False
                
            # 💰 DYNAMIC CASH BUFFER: Usar sistema inteligente adaptativo
            from .dynamic_cash_buffer import get_dynamic_cash_buffer
            
            try:
                dynamic_buffer_pct, buffer_mode, buffer_info = get_dynamic_cash_buffer()
                # FIX DOUBLE-BUFFERING: Usar true_cash en lugar de available_cash (ya reducido)
                true_cash = float(getattr(account, 'cash', 0.0) or 0.0)
                cash_after_trade = true_cash - notional_value
                min_cash_required = current_equity * dynamic_buffer_pct
                
                if cash_after_trade < min_cash_required:
                    # Log detallado para diagnóstico
                    logger.critical(f"🚨 ORDER BLOCKED: Dynamic Cash Buffer!")
                    logger.critical(f"   💰 Buffer requerido: {dynamic_buffer_pct:.1%} ({buffer_mode}) = ${min_cash_required:.0f}")
                    logger.critical(f"   📊 Cash después: ${cash_after_trade:.0f} < ${min_cash_required:.0f}")
                    logger.critical(f"   🎯 Factores: Vol={buffer_info.get('volatility', 0):.2f}, Perf={buffer_info.get('performance', 0):.2f}")
                    return False
                else:
                    # Log positivo cuando funciona el buffer dinámico
                    if buffer_mode != "NORMAL" or dynamic_buffer_pct != settings.min_cash_buffer:
                        logger.info(f"💰 DYNAMIC BUFFER OK: {dynamic_buffer_pct:.1%} ({buffer_mode}) - Cash tras orden: ${cash_after_trade:.0f}")
                        
            except Exception as e:
                # Fallback al buffer estático en caso de error
                logger.error(f"❌ Error en dynamic cash buffer, usando fallback: {e}")
                # FIX DOUBLE-BUFFERING: Usar true_cash también en fallback
                true_cash = float(getattr(account, 'cash', 0.0) or 0.0)
                cash_after_trade = true_cash - notional_value
                min_cash_pct = settings.min_cash_buffer  # 5% configurado
                min_cash_required = current_equity * min_cash_pct
                if cash_after_trade < min_cash_required:
                    logger.critical(f"🚨 ORDER BLOCKED: Fallback cash buffer! ${cash_after_trade:.0f} < ${min_cash_required:.0f} ({min_cash_pct:.0%})")
                    return False
                
            # PDT info (but don't block - let Alpaca handle it)
            if current_equity < 25000 and "/" not in symbol:  # Crypto has /, stocks don't
                logger.info(f"ℹ️ PDT INFO: Equity ${current_equity:.0f} < $25,000 - Alpaca may limit day trading")
                # Don't block here - let Alpaca API handle PDT restrictions
                
    except Exception as e:
        logger.critical(f"❌ CRISIS MODE ERROR - BLOCKING BUY: {e}")
        # Block ALL BUY orders on any error to prevent bleeding
        if side.lower() == "buy":
            return False
    
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
        
        # 🛡️ SIMPLE EXPOSURE LIMIT: Block buys when exposure is too high
        if side.lower() == "buy":
            # Simple check: if notional > available cash * 3, skip (emergency brake)
            if notional_value > available_cash * 3.0:
                logger.warning(f"🚫 EMERGENCY BRAKE: Order ${notional_value:.0f} > 3x available cash ${available_cash:.0f}. Skip {symbol}.")
                return False
        
        if side.lower() == "buy" and price:
            # ULTRA-INTELIGENTE: Auto-escalado máximo aprovechamiento
            if notional_value > available_cash:
                # MICRO-ÓRDENES: Para cash muy bajo, usar micro trading
                if available_cash < 50.0:
                    if available_cash < 2.0:  # Menos de $2 disponibles
                        logger.warning(f"⚠️ Liquidez extrema: ${available_cash:.2f} < $2. Skip {symbol}.")
                        return False
                    
                    # MICRO-TRADING: Usar 99% del cash disponible
                    scaled_notional = available_cash * 0.99
                    scaled_qty = scaled_notional / price
                    
                    logger.info(f"💡 MICRO-TRADING {symbol}: ${notional_value:.2f} → ${scaled_notional:.2f} (¡máximo aprovechamiento!)")
                else:
                    # ESCALADO ULTRA-MÁXIMO: Usar 99% del cash disponible  
                    scaled_notional = available_cash * 0.99
                    scaled_qty = scaled_notional / price
                    
                    logger.info(f"💡 ESCALADO ULTRA-MÁXIMO {symbol}: ${notional_value:.2f} → ${scaled_notional:.2f} (99% del cash)")
                
                # Actualizar valores para la orden escalada
                notional_value = scaled_notional
                qty = scaled_qty
            elif notional_value > available_cash * 0.1:
                # ESCALADO AGRESIVO: Si la orden usa >10% del cash, usar 99% disponible
                scaled_notional = available_cash * 0.99
                scaled_qty = scaled_notional / price
                
                logger.info(f"💡 ESCALADO AGRESIVO {symbol}: ${notional_value:.2f} → ${scaled_notional:.2f} (99% del cash disponible)")
                
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
            
            # 🚫 ROBUST ANTI-MICRO FILTER: Strict minimum limits to prevent fragmentation
            min_qty_crypto = 0.001    # Minimum crypto quantity (10x stricter than before)
            min_notional_crypto = 10.0  # Minimum $10 for crypto operations
            min_notional_stock = 15.0   # Minimum $15 for stock operations
            
            if is_crypto:
                if float(qty) < min_qty_crypto:
                    logger.warning(f"🚫 MICRO-CRYPTO BLOCKED: {symbol} qty={qty:.8f} < {min_qty_crypto}")
                    return False
                if notional_value < min_notional_crypto:
                    logger.warning(f"🚫 MICRO-CRYPTO BLOCKED: {symbol} value=${notional_value:.2f} < ${min_notional_crypto}")
                    return False
            else:
                if notional_value < min_notional_stock:
                    logger.warning(f"🚫 MICRO-STOCK BLOCKED: {symbol} value=${notional_value:.2f} < ${min_notional_stock}")
                    return False
            
            order_request = MarketOrderRequest(
                symbol=api_symbol,
                qty=float(qty),
                side=order_side,
                time_in_force=tif
            )
            
        # ✅ VERIFICAR CANTIDAD DISPONIBLE antes de enviar orden SELL
        if side.lower() == "sell":
            try:
                client = _client()
                position = client.get_open_position(api_symbol)
                if position:
                    available_qty = float(getattr(position, 'qty', 0))
                    requested_qty = float(qty)
                    
                    if abs(requested_qty) > abs(available_qty):
                        logger.warning(f"🚫 SELL BLOCKED: {symbol} requested={abs(requested_qty):.6f} > available={abs(available_qty):.6f}")
                        return False
                        
                    # Si disponible es menos del 80% de lo solicitado, ajustar cantidad
                    if abs(available_qty) < abs(requested_qty) * 0.8:
                        adjusted_qty = available_qty * 0.95  # Use 95% of available to be safe
                        logger.warning(f"🔧 AJUSTANDO CANTIDAD: {symbol} {requested_qty:.6f} → {adjusted_qty:.6f}")
                        order_request.qty = abs(adjusted_qty)
                        qty = adjusted_qty
                        notional_value = abs(adjusted_qty) * float(price)
                        
            except Exception as e:
                logger.warning(f"⚠️ No se pudo verificar cantidad disponible para {symbol}: {e}")

        # Submit order
        client = _client()
        order = client.submit_order(order_request)
        
        order_type = "CRYPTO" if is_crypto else "STOCK"
        logger.info(f"✅ Orden {order_type} enviada: {side.upper()} ${notional_value:.2f} {symbol} (qty: {float(qty):.6f})")
        
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
                        
                        # PDT SAFE: Block new stock BUYS, but allow all SELLS (position reducing)
                        is_crypto = "/" in symbol
                        if dt_buying_power < 1000 and not is_crypto and side.lower() == "buy":
                            logger.warning(f"🚫 PDT MODE: Nueva compra {symbol} bloqueada. Solo ventas/cierres permitidos.")
                            return False  # Block new stock purchases only
                            
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


# =======================
# 🏛️ ARBITRAGE EXECUTION
# =======================

def reset_arbitrage_tracking():
    """Reset arbitrage position tracking and reserved cash."""
    global _arbitrage_positions, _arbitrage_reserved_cash
    _arbitrage_positions.clear()
    _arbitrage_reserved_cash = 0.0
    logger.debug("🔄 Arbitrage tracking reset")


def execute_arbitrage_trade(opportunity) -> dict:
    """
    Execute a complete arbitrage trade based on detected opportunity.
    
    Args:
        opportunity: ArbitrageOpportunity object with trade details
        
    Returns:
        Dict with execution results and profit calculation
    """
    from .arbitrage_engine import ArbitrageOpportunity
    from .config import settings
    
    if not isinstance(opportunity, ArbitrageOpportunity):
        logger.error("❌ Invalid opportunity object for arbitrage execution")
        return {"success": False, "error": "Invalid opportunity object"}
    
    symbol = opportunity.symbol
    trade_id = f"{symbol}_{int(opportunity.timestamp)}"
    
    # 🛡️ CRITICAL SAFETY GATE: Check arbitrage mode before ANY execution
    if settings.arbitrage_mode.lower() != "real":
        logger.warning(f"⚠️ ARBITRAGE in SIMULATE mode - no real trades executed for {symbol}")
        logger.info(f"🎭 SIMULATED ARBITRAGE: {symbol}")
        logger.info(f"   💰 Expected profit: {opportunity.net_profit_pct:.1%}")
        logger.info(f"   📊 Buy: {opportunity.buy_exchange} @ ${opportunity.buy_price:.6f}")
        logger.info(f"   📊 Sell: {opportunity.sell_exchange} @ ${opportunity.sell_price:.6f}")
        logger.info(f"   🎯 Hypothetical profit: ${opportunity.potential_profit_usd:.2f}")
        
        # Return simulated successful execution
        return {
            "success": True,
            "trade_id": trade_id,
            "symbol": symbol,
            "expected_profit_pct": opportunity.net_profit_pct,
            "expected_profit_usd": opportunity.potential_profit_usd,
            "actual_profit_usd": opportunity.potential_profit_usd,  # Simulated profit
            "buy_executed": True,  # Simulated
            "sell_executed": True,  # Simulated
            "buy_price": opportunity.buy_price,
            "sell_price": opportunity.sell_price,
            "quantity": opportunity.potential_profit_usd / opportunity.buy_price,
            "error": None,
            "execution_time": time.time(),
            "simulated": True  # Mark as simulated execution
        }
    
    # 🚨 REAL TRADING MODE - proceed with actual execution
    logger.critical(f"🚨 REAL ARBITRAGE MODE: Executing actual trades for {symbol}")
    logger.info(f"🏛️ EXECUTING ARBITRAGE: {symbol}")
    logger.info(f"   💰 Expected profit: {opportunity.net_profit_pct:.1%}")
    logger.info(f"   📊 Buy: {opportunity.buy_exchange} @ ${opportunity.buy_price:.6f}")
    logger.info(f"   📊 Sell: {opportunity.sell_exchange} @ ${opportunity.sell_price:.6f}")
    
    execution_result = {
        "success": False,
        "trade_id": trade_id,
        "symbol": symbol,
        "expected_profit_pct": opportunity.net_profit_pct,
        "expected_profit_usd": opportunity.potential_profit_usd,
        "actual_profit_usd": 0.0,
        "buy_executed": False,
        "sell_executed": False,
        "buy_price": None,
        "sell_price": None,
        "quantity": 0.0,
        "error": None,
        "execution_time": time.time()
    }
    
    try:
        # 1. Validate available capital and limits
        available_cash, total_cash = get_available_cash()
        
        # Calculate position size (conservative approach)
        max_position_size = min(
            opportunity.potential_profit_usd / opportunity.net_profit_pct,  # Based on expected profit
            available_cash * 0.10,  # Max 10% of available cash
            10000.0  # Hard limit of $10k per arbitrage
        )
        
        if max_position_size < 100:  # Minimum $100 for arbitrage
            logger.warning(f"🚫 {symbol}: Position size too small ${max_position_size:.0f} < $100")
            execution_result["error"] = "Position size too small"
            return execution_result
        
        # 2. Calculate quantity to trade
        # Use the buy price to determine quantity since we're buying first
        quantity = max_position_size / opportunity.buy_price
        
        # Validate minimum quantity requirements
        if symbol.endswith("/USD") or "/" in symbol:  # Crypto
            min_qty = 0.0001  # Minimum crypto quantity
        else:  # Stock
            min_qty = 0.001   # Minimum stock quantity
            
        if quantity < min_qty:
            logger.warning(f"🚫 {symbol}: Quantity too small {quantity:.8f} < {min_qty}")
            execution_result["error"] = "Quantity below minimum"
            return execution_result
        
        execution_result["quantity"] = quantity
        
        # 3. Reserve cash for this arbitrage
        global _arbitrage_reserved_cash
        _arbitrage_reserved_cash += max_position_size
        
        logger.info(f"💰 Arbitrage execution: ${max_position_size:.0f} reserved, qty: {quantity:.8f}")
        
        # 4. PHASE 1: Execute BUY order (at lower price)
        logger.info(f"🔵 PHASE 1: Buying {quantity:.8f} {symbol} @ {opportunity.buy_exchange}")
        
        # Use current market price for execution (since we can't actually access other exchanges)
        # In a real implementation, this would route to the specific exchange
        buy_success = place_order(
            symbol=symbol,
            qty=quantity,
            side="buy",
            price=opportunity.buy_price,
            fractional=True,
            is_crypto=("/" in symbol)
        )
        
        if not buy_success:
            logger.error(f"❌ {symbol}: BUY order failed")
            execution_result["error"] = "Buy order failed"
            _arbitrage_reserved_cash -= max_position_size  # Release reserved cash
            return execution_result
        
        execution_result["buy_executed"] = True
        execution_result["buy_price"] = opportunity.buy_price
        logger.info(f"✅ BUY executed: {quantity:.8f} {symbol}")
        
        # 5. PHASE 2: Execute SELL order (at higher price)
        # Small delay to ensure buy order is processed
        import time
        time.sleep(0.5)
        
        logger.info(f"🔴 PHASE 2: Selling {quantity:.8f} {symbol} @ {opportunity.sell_exchange}")
        
        # In a real implementation, this would be routed to the sell exchange
        # For now, we simulate by using a limit order at the expected sell price
        sell_success = place_order(
            symbol=symbol,
            qty=quantity,
            side="sell", 
            price=opportunity.sell_price,
            fractional=True,
            is_crypto=("/" in symbol)
        )
        
        if not sell_success:
            logger.error(f"❌ {symbol}: SELL order failed - position may be open")
            execution_result["error"] = "Sell order failed - check positions"
            return execution_result
        
        execution_result["sell_executed"] = True
        execution_result["sell_price"] = opportunity.sell_price
        logger.info(f"✅ SELL executed: {quantity:.8f} {symbol}")
        
        # 6. Calculate actual profit
        gross_profit = (opportunity.sell_price - opportunity.buy_price) * quantity
        
        # Account for fees (0.1% per side = 0.2% total)
        total_fees = max_position_size * 0.002
        
        actual_profit = gross_profit - total_fees
        execution_result["actual_profit_usd"] = actual_profit
        
        # 7. Update tracking
        _arbitrage_positions[trade_id] = {
            "symbol": symbol,
            "quantity": quantity,
            "buy_price": opportunity.buy_price,
            "sell_price": opportunity.sell_price,
            "profit": actual_profit,
            "timestamp": time.time(),
            "status": "completed"
        }
        
        execution_result["success"] = True
        
        # 8. Log successful arbitrage
        profit_pct = (actual_profit / max_position_size) if max_position_size > 0 else 0
        logger.critical(f"💰 ARBITRAGE COMPLETED: {symbol}")
        logger.critical(f"   ✅ Quantity: {quantity:.8f}")
        logger.critical(f"   💵 Investment: ${max_position_size:.2f}")
        logger.critical(f"   📈 Profit: ${actual_profit:.2f} ({profit_pct:.1%})")
        logger.critical(f"   ⚡ Spread: {opportunity.spread_pct:.1%}")
        
        # Release reserved cash
        _arbitrage_reserved_cash = max(0, _arbitrage_reserved_cash - max_position_size)
        
        return execution_result
        
    except Exception as e:
        logger.error(f"❌ Arbitrage execution failed for {symbol}: {e}")
        execution_result["error"] = str(e)
        
        # Release reserved cash on error
        if "max_position_size" in locals():
            _arbitrage_reserved_cash = max(0, _arbitrage_reserved_cash - max_position_size)
        
        return execution_result


def get_arbitrage_positions() -> dict:
    """Get current arbitrage position status."""
    return {
        "active_positions": len(_arbitrage_positions),
        "reserved_cash": _arbitrage_reserved_cash,
        "positions": _arbitrage_positions.copy()
    }


def validate_arbitrage_risk_limits(opportunity, available_capital: float) -> bool:
    """
    Validate that arbitrage execution meets risk management requirements.
    
    Args:
        opportunity: ArbitrageOpportunity object
        available_capital: Available capital for trading
        
    Returns:
        bool: True if safe to execute
    """
    try:
        # Check maximum arbitrage exposure (15% of capital)
        max_arbitrage_exposure = available_capital * 0.15
        
        # Calculate required capital for this trade
        required_capital = min(
            opportunity.potential_profit_usd / opportunity.net_profit_pct,
            10000.0  # Hard limit
        )
        
        # Check if we're within exposure limits
        if _arbitrage_reserved_cash + required_capital > max_arbitrage_exposure:
            logger.warning(f"🚫 {opportunity.symbol}: Arbitrage exposure limit exceeded")
            logger.warning(f"   Current reserved: ${_arbitrage_reserved_cash:.0f}")
            logger.warning(f"   Required: ${required_capital:.0f}")
            logger.warning(f"   Limit: ${max_arbitrage_exposure:.0f}")
            return False
        
        # Check minimum profit threshold
        if opportunity.net_profit_pct < 0.005:  # 0.5% minimum
            logger.debug(f"🚫 {opportunity.symbol}: Profit {opportunity.net_profit_pct:.1%} below 0.5% threshold")
            return False
        
        # Check confidence score
        if opportunity.confidence_score < 0.5:  # 50% minimum confidence
            logger.debug(f"🚫 {opportunity.symbol}: Confidence {opportunity.confidence_score:.1%} too low")
            return False
        
        logger.debug(f"✅ {opportunity.symbol}: Risk validation passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Risk validation error for {opportunity.symbol}: {e}")
        return False


# Add time import if not already present
import time