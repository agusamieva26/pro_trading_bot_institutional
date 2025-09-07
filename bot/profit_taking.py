# bot/profit_taking.py
"""
Sistema de profit-taking automático y rebalanceo de portafolio
para diversificación inteligente y gestión de riesgo.
"""

from .config import settings
from .util import logger
from .execution import place_order
import time

# Configuración de profit-taking
PROFIT_THRESHOLD_BTC = 0.03  # 3% ganancia para tomar profits en BTC
MAX_CONCENTRATION_BTC = 0.70  # Máximo 70% en BTC
MIN_CASH_RESERVE = 0.05  # Mantener 5% en cash
REBALANCE_THRESHOLD = 0.15  # 15% desviación para rebalancear

def _client():
    """Cliente de Alpaca"""
    from alpaca.trading.client import TradingClient
    return TradingClient(
        api_key=settings.alpaca_api_key,
        secret_key=settings.alpaca_secret_key,
        paper=(settings.mode == "paper")
    )

def get_position_allocation(client, symbol, total_equity):
    """Obtiene la asignación actual de un activo como % del equity"""
    try:
        positions = client.get_all_positions()
        for pos in positions:
            if pos.symbol == symbol.replace("/", ""):
                market_value = float(pos.market_value)
                allocation = abs(market_value) / total_equity
                return allocation, float(pos.unrealized_pl)
    except Exception as e:
        logger.error(f"❌ Error obteniendo posición de {symbol}: {e}")
    return 0.0, 0.0

def should_take_profits(symbol, allocation, unrealized_pnl, entry_value):
    """Determina si debe tomar profits de un activo"""
    if entry_value <= 0:
        return False, ""
    
    # Calcular % de ganancia
    pnl_pct = unrealized_pnl / entry_value
    
    # Condiciones para profit-taking
    if symbol == "BTC/USD":
        # BTC: Tomar profits si >3% ganancia O >70% concentración
        if pnl_pct >= PROFIT_THRESHOLD_BTC:
            return True, f"Ganancia {pnl_pct:.1%} ≥ objetivo {PROFIT_THRESHOLD_BTC:.1%}"
        if allocation >= MAX_CONCENTRATION_BTC:
            return True, f"Concentración {allocation:.1%} ≥ límite {MAX_CONCENTRATION_BTC:.1%}"
    else:
        # Otros activos: Tomar profits con 2% ganancia
        if pnl_pct >= 0.02:
            return True, f"Ganancia {pnl_pct:.1%} ≥ 2.0%"
    
    return False, ""

def execute_profit_taking(client, symbol, current_qty, reason, target_reduction=0.30):
    """Ejecuta profit-taking vendiendo una parte de la posición"""
    try:
        # Calcular cantidad a vender (por defecto 30% de la posición)
        qty_to_sell = abs(current_qty) * target_reduction
        
        # Asegurar cantidad mínima
        if qty_to_sell < 1e-6:
            logger.warning(f"⚠️ {symbol}: Cantidad a vender muy pequeña ({qty_to_sell})")
            return False
        
        # Determinar símbolo para la API
        api_symbol = symbol.replace("/", "")
        is_crypto = "/" in symbol
        
        logger.info(f"💰 PROFIT-TAKING: {symbol} vendiendo {qty_to_sell:.6f} ({target_reduction:.0%}) - {reason}")
        
        # Ejecutar orden de venta
        from .data import fetch_bars
        from .features import make_features
        
        df = fetch_bars(symbol, start="2024-09-07")
        if not df.empty:
            feats = make_features(df)
            current_price = float(feats.iloc[-1]["close"])
            
            place_order(
                symbol=symbol,
                qty=qty_to_sell,
                side="sell",
                price=current_price,
                fractional=(not is_crypto),
                is_crypto=is_crypto
            )
            
            logger.info(f"✅ PROFIT-TAKING ejecutado: {symbol} vendió {qty_to_sell:.6f} @ ${current_price:.2f}")
            return True
        else:
            logger.error(f"❌ No hay datos de precio para {symbol}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error en profit-taking de {symbol}: {e}")
        return False

def rebalance_portfolio(client, total_equity, target_allocations):
    """Rebalancea el portafolio hacia las asignaciones objetivo"""
    try:
        positions = client.get_all_positions()
        current_cash = float(client.get_account().cash)
        cash_allocation = current_cash / total_equity
        
        logger.info(f"🔄 REBALANCEO: Equity=${total_equity:,.2f}, Cash={cash_allocation:.1%}")
        
        # Revisar cada posición actual
        for pos in positions:
            symbol = pos.symbol
            if symbol == "BTCUSD":
                symbol = "BTC/USD"
            elif symbol.endswith("USD") and len(symbol) <= 6:
                symbol = symbol[:-3] + "/USD"
                
            market_value = abs(float(pos.market_value))
            current_allocation = market_value / total_equity
            target_allocation = target_allocations.get(symbol, 0.05)  # 5% por defecto
            
            deviation = abs(current_allocation - target_allocation)
            
            if deviation >= REBALANCE_THRESHOLD:
                if current_allocation > target_allocation:
                    # Sobrepeso: reducir posición
                    excess_pct = current_allocation - target_allocation
                    qty_current = float(pos.qty)
                    qty_to_reduce = abs(qty_current) * (excess_pct / current_allocation)
                    
                    logger.info(f"⚖️ REBALANCEO: {symbol} sobrepeso {current_allocation:.1%} > {target_allocation:.1%}")
                    logger.info(f"📉 Reduciendo {symbol}: {qty_to_reduce:.6f} de {abs(qty_current):.6f}")
                    
                    # Ejecutar reducción (similar a profit-taking)
                    execute_profit_taking(client, symbol, qty_current, 
                                       f"rebalanceo (sobrepeso {deviation:.1%})", 
                                       excess_pct / current_allocation)
                    
                    time.sleep(2)  # Esperar entre órdenes
        
        logger.info("✅ REBALANCEO completado")
        
    except Exception as e:
        logger.error(f"❌ Error en rebalanceo: {e}")

def auto_profit_taking():
    """Sistema automático de profit-taking y rebalanceo"""
    try:
        client = _client()
        account = client.get_account()
        total_equity = float(account.equity)
        
        logger.info(f"💎 AUTO PROFIT-TAKING: Analizando portafolio (${total_equity:,.2f})")
        
        # Definir asignaciones objetivo
        target_allocations = {
            "BTC/USD": 0.50,    # 50% BTC máximo
            "ETH/USD": 0.20,    # 20% ETH
            "SOL/USD": 0.10,    # 10% SOL
            # Resto distribuido en otros activos
        }
        
        profits_taken = False
        
        # Revisar cada posición para profit-taking
        positions = client.get_all_positions()
        for pos in positions:
            symbol = pos.symbol
            if symbol == "BTCUSD":
                symbol = "BTC/USD"
            elif symbol.endswith("USD"):
                symbol = symbol[:-3] + "/USD"
            
            qty = float(pos.qty)
            unrealized_pnl = float(pos.unrealized_pl)
            entry_value = abs(float(pos.cost_basis))
            
            allocation, _ = get_position_allocation(client, symbol, total_equity)
            
            should_take, reason = should_take_profits(symbol, allocation, unrealized_pnl, entry_value)
            
            if should_take:
                success = execute_profit_taking(client, symbol, qty, reason)
                if success:
                    profits_taken = True
                    time.sleep(3)  # Esperar entre profit-takings
        
        # Si tomamos profits, esperar y rebalancear
        if profits_taken:
            logger.info("⏳ Esperando 10s para rebalanceo tras profit-taking...")
            time.sleep(10)
            
            # Actualizar equity tras profit-taking
            account = client.get_account()
            total_equity = float(account.equity)
            
            # Ejecutar rebalanceo
            rebalance_portfolio(client, total_equity, target_allocations)
            
            return "PROFITS_TAKEN"
        
        return "NO_ACTION"
        
    except Exception as e:
        logger.error(f"❌ Error en auto profit-taking: {e}")
        return "ERROR"