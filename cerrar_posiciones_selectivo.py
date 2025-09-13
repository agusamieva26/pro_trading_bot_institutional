#!/usr/bin/env python3
"""
Script para cerrar selectivamente posiciones viejas manteniendo las de hoy
"""

import os
import sys
from loguru import logger
from dotenv import load_dotenv
import datetime

# Cargar variables de entorno
load_dotenv()

try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import MarketOrderRequest
    from alpaca.trading.enums import OrderSide, TimeInForce
except ImportError:
    logger.error("❌ Alpaca library no encontrada. Usando configuración del bot...")
    sys.path.append('/home/runner/workspace')
    from bot.config import settings

# Configuración usando la config del bot
try:
    from bot.config import settings
    client = TradingClient(settings.alpaca_api_key, settings.alpaca_secret_key, paper=True)
    logger.info("✅ Cliente Alpaca configurado correctamente")
except Exception as e:
    logger.error(f"❌ Error configurando cliente: {e}")
    sys.exit(1)

# Posiciones abiertas HOY (13 septiembre 2025 a las 10:01) - MANTENER ESTAS
POSICIONES_HOY = {
    'PEPE/USD': 3693.28,   # Valor invertido aproximado
    'CRV/USD': 1643.27,
    'GRT/USD': 1703.61,
    'BTC/USD': 4224.97,
    'LINK/USD': 1406.95,
    'AAVE/USD': 793.83,
    'UNI/USD': 311.68,
    'XRP/USD': 519.43
}

def main():
    logger.info("🔍 Obteniendo posiciones actuales...")
    
    try:
        positions = client.get_all_positions()
        logger.info(f"📊 Total posiciones encontradas: {len(positions)}")
        
        if not positions:
            logger.info("✅ No hay posiciones abiertas")
            return
            
        logger.info("\n" + "="*60)
        logger.info("📊 ANÁLISIS DE POSICIONES:")
        logger.info("="*60)
        
        posiciones_a_cerrar = []
        posiciones_a_mantener = []
        
        for pos in positions:
            symbol = pos.symbol
            qty = float(pos.qty)
            market_value = float(pos.market_value) if hasattr(pos, 'market_value') else 0.0
            unrealized_pnl = float(pos.unrealized_pl) if hasattr(pos, 'unrealized_pl') else 0.0
            unrealized_pnl_pct = float(pos.unrealized_plpc) * 100 if hasattr(pos, 'unrealized_plpc') else 0.0
            
            # Determinar si es una posición de hoy o vieja
            if symbol in POSICIONES_HOY:
                # Verificar si el tamaño coincide aproximadamente con la inversión de hoy
                valor_esperado_hoy = POSICIONES_HOY[symbol]
                
                # Si el valor de mercado es similar al invertido hoy (+/- 50%), es de hoy
                if abs(market_value - valor_esperado_hoy) < (valor_esperado_hoy * 0.5):
                    status = "🟢 MANTENER (Posición de HOY)"
                    posiciones_a_mantener.append((symbol, qty, market_value, unrealized_pnl))
                else:
                    status = "🔴 CERRAR (Residuo de posición vieja)"
                    posiciones_a_cerrar.append((symbol, qty, market_value, unrealized_pnl))
            else:
                status = "🔴 CERRAR (Posición vieja)"
                posiciones_a_cerrar.append((symbol, qty, market_value, unrealized_pnl))
            
            pnl_status = "🟢" if unrealized_pnl > 0 else "🔴" if unrealized_pnl < 0 else "⚪"
            
            logger.info(f"{status} {symbol}:")
            logger.info(f"   💰 Cantidad: {qty:.6f}")
            logger.info(f"   💵 Valor: ${market_value:.2f}")
            logger.info(f"   {pnl_status} P&L: ${unrealized_pnl:+.2f} ({unrealized_pnl_pct:+.2f}%)")
            logger.info("")
        
        # Resumen
        logger.info("="*60)
        logger.info("📋 RESUMEN DE ACCIÓN:")
        logger.info("="*60)
        
        total_mantener_valor = sum(pos[2] for pos in posiciones_a_mantener)
        total_mantener_pnl = sum(pos[3] for pos in posiciones_a_mantener)
        total_cerrar_valor = sum(pos[2] for pos in posiciones_a_cerrar)
        total_cerrar_pnl = sum(pos[3] for pos in posiciones_a_cerrar)
        
        logger.info(f"🟢 MANTENER: {len(posiciones_a_mantener)} posiciones")
        logger.info(f"   💰 Valor total: ${total_mantener_valor:.2f}")
        logger.info(f"   📈 P&L total: ${total_mantener_pnl:+.2f}")
        logger.info("")
        
        logger.info(f"🔴 CERRAR: {len(posiciones_a_cerrar)} posiciones")
        logger.info(f"   💰 Valor total: ${total_cerrar_valor:.2f}")
        logger.info(f"   📈 P&L total: ${total_cerrar_pnl:+.2f}")
        logger.info("")
        
        if not posiciones_a_cerrar:
            logger.info("✅ No hay posiciones viejas que cerrar")
            return
            
        # Confirmación - cerrar solo posiciones pequeñas (residuos)
        logger.info("⚠️ CERRANDO AUTOMÁTICAMENTE SOLO POSICIONES RESIDUALES (<$50):")
        
        posiciones_finales_a_cerrar = []
        posiciones_grandes_mantener = []
        
        for symbol, qty, valor, pnl in posiciones_a_cerrar:
            if valor < 50.0:  # Solo residuos pequeños
                posiciones_finales_a_cerrar.append((symbol, qty, valor, pnl))
                logger.info(f"   🗑️ {symbol}: ${valor:.2f} (residuo)")
            else:  # Posiciones grandes - mantener
                posiciones_grandes_mantener.append((symbol, qty, valor, pnl))
                logger.info(f"   🟢 {symbol}: ${valor:.2f} (MANTENER - es de hoy)")
                
        if not posiciones_finales_a_cerrar:
            logger.info("✅ No hay posiciones residuales que cerrar")
            return
            
        logger.info(f"\n📊 Cerrando {len(posiciones_finales_a_cerrar)} residuos, manteniendo {len(posiciones_grandes_mantener)} posiciones grandes")
        posiciones_a_cerrar = posiciones_finales_a_cerrar
            
        # Cerrar posiciones
        logger.info("\n🚀 Iniciando cierre de posiciones viejas...")
        
        for symbol, qty, valor, pnl in posiciones_a_cerrar:
            try:
                logger.info(f"🔄 Cerrando {symbol}: {qty:.6f} unidades...")
                
                # Crear orden de venta de mercado para cerrar completamente
                order_request = MarketOrderRequest(
                    symbol=symbol,
                    qty=abs(qty),  # Cantidad positiva para venta
                    side=OrderSide.SELL,
                    time_in_force=TimeInForce.GTC
                )
                
                order = client.submit_order(order_request)
                logger.info(f"✅ Orden de cierre enviada para {symbol}: ID {order.id}")
                
            except Exception as e:
                logger.error(f"❌ Error cerrando {symbol}: {e}")
                
        logger.info("\n✅ Proceso de cierre completado!")
        logger.info(f"🎯 Mantenidas {len(posiciones_a_mantener)} posiciones rentables de hoy")
        logger.info(f"🗑️ Cerradas {len(posiciones_a_cerrar)} posiciones viejas")
        
    except Exception as e:
        logger.error(f"❌ Error general: {e}")

if __name__ == "__main__":
    main()