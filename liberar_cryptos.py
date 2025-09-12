#!/usr/bin/env python3
"""
SCRIPT DE EMERGENCIA: LIBERAR TODAS LAS CRIPTOMONEDAS
Cierra todas las posiciones crypto para reducir exposición rápidamente.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bot.config import settings
from bot.execution import _client, close_position
from bot.util import logger
import time

def liberar_todas_las_cryptos():
    """Cierra TODAS las posiciones de criptomonedas inmediatamente."""
    
    logger.info("🚨 INICIANDO LIBERACIÓN MASIVA DE CRIPTOMONEDAS...")
    
    try:
        client = _client()
        positions = list(client.get_all_positions())
        
        crypto_positions = []
        crypto_symbols = ["BTCUSD", "ETHUSD", "SOLUSD", "AVAXUSD", "LINKUSD", "DOGEUSD", "DOTUSD", 
                         "LTCUSD", "SHIBUSD", "XRPUSD", "UNIUSD", "AAVEUSD", "PEPEUSD", "BCHUSD", 
                         "CRVUSD", "GRTUSD"]
        
        for pos in positions:
            if pos.symbol in crypto_symbols:  # Alpaca stores cryptos without "/"
                crypto_positions.append(pos)
        
        if not crypto_positions:
            logger.info("✅ No hay posiciones crypto abiertas para cerrar")
            return
        
        logger.info(f"🎯 ENCONTRADAS {len(crypto_positions)} POSICIONES CRYPTO PARA CERRAR:")
        
        total_value = 0
        for pos in crypto_positions:
            value = float(pos.market_value or 0)
            pnl = float(pos.unrealized_pl or 0)
            pnl_pct = (pnl / value * 100) if value > 0 else 0
            total_value += value
            logger.info(f"  📊 {pos.symbol}: ${value:.0f} | P&L: ${pnl:+.2f} ({pnl_pct:+.1f}%)")
        
        logger.critical(f"💰 VALOR TOTAL A LIBERAR: ${total_value:.0f}")
        
        # Cerrar todas las cryptos
        closed_count = 0
        failed_count = 0
        
        for pos in crypto_positions:
            try:
                logger.warning(f"🚨 CERRANDO: {pos.symbol} (${float(pos.market_value or 0):.0f})")
                
                success = close_position(pos.symbol)
                if success:
                    closed_count += 1
                    logger.info(f"✅ {pos.symbol} cerrado exitosamente")
                else:
                    failed_count += 1
                    logger.error(f"❌ Fallo al cerrar {pos.symbol}")
                
                # Pausa breve entre cierres
                time.sleep(1)
                
            except Exception as e:
                failed_count += 1
                logger.error(f"💥 Error cerrando {pos.symbol}: {e}")
        
        logger.critical(f"📋 RESUMEN FINAL:")
        logger.critical(f"  ✅ Cerradas: {closed_count}")
        logger.critical(f"  ❌ Fallidas: {failed_count}")
        logger.critical(f"  💰 Valor liberado: ~${total_value:.0f}")
        
        if closed_count > 0:
            logger.critical("🎉 LIBERACIÓN EXITOSA - Exposición reducida significativamente")
        else:
            logger.critical("⚠️ NO SE CERRÓ NINGUNA POSICIÓN - Revisar logs para errores")
            
    except Exception as e:
        logger.critical(f"💥 ERROR CRÍTICO en liberación masiva: {e}")

if __name__ == "__main__":
    print("🚨 LIBERANDO TODAS LAS CRIPTOMONEDAS...")
    liberar_todas_las_cryptos()
    print("✅ Proceso completado. Revisa los logs para detalles.")