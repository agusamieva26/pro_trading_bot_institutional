#!/usr/bin/env python3
"""
Configuración Especializada para Scalping
Parámetros optimizados para operaciones rápidas y frecuentes
"""

import os
from bot.config import settings

class ScalpingConfig:
    """Configuración agresiva para scalping"""
    
    # 🔥 PARÁMETROS DE SCALPING AGRESIVO
    TAKE_PROFIT_SCALPING = 0.003      # 0.3% - Take profit muy ajustado
    STOP_LOSS_SCALPING = 0.002        # 0.2% - Stop loss muy cerca
    RISK_PER_TRADE_SCALPING = 0.01    # 1% - Mayor riesgo por la frecuencia
    
    # ⚡ TIMEFRAMES PARA SCALPING
    SCALPING_TIMEFRAMES = {
        'ultra_fast': '1Min',     # Ultra scalping
        'fast': '5Min',           # Scalping normal
        'medium': '15Min'         # Scalping moderado
    }
    
    # 🎯 SÍMBOLOS ÓPTIMOS PARA SCALPING
    SCALPING_SYMBOLS = [
        'BTCUSD',    # Bitcoin - Alta volatilidad
        'ETHUSD',    # Ethereum - Buena liquidez  
        'SPY',       # S&P 500 - Movimientos predecibles
        'QQQ',       # Nasdaq - Tech scalping
        'TSLA',      # Tesla - Volatilidad alta
        'AAPL',      # Apple - Líquido y estable
    ]
    
    # 🚀 CONFIGURACIÓN DE EJECUCIÓN RÁPIDA
    EXECUTION_SPEED = {
        'order_timeout': 5,       # 5 segundos máximo por orden
        'max_slippage': 0.001,    # 0.1% slippage máximo
        'retry_attempts': 2,      # Solo 2 intentos por orden
        'position_check_freq': 10, # Verificar posiciones cada 10 segundos
    }
    
    # 📊 MÉTRICAS DE SCALPING
    SCALPING_METRICS = {
        'min_trades_per_hour': 2,    # Mínimo 2 trades/hora
        'max_trades_per_hour': 20,   # Máximo 20 trades/hora  
        'target_win_rate': 0.65,     # 65% win rate objetivo
        'max_drawdown': 0.02,        # 2% drawdown máximo
    }

def apply_scalping_config():
    """Aplicar configuración de scalping al bot"""
    
    print("🔥 APLICANDO CONFIGURACIÓN DE SCALPING AGRESIVO")
    print("=" * 50)
    
    # Actualizar configuración principal
    settings.take_profit_pct = ScalpingConfig.TAKE_PROFIT_SCALPING
    settings.stop_loss_pct = ScalpingConfig.STOP_LOSS_SCALPING  
    settings.risk_per_trade = ScalpingConfig.RISK_PER_TRADE_SCALPING
    settings.bar_timeframe = ScalpingConfig.SCALPING_TIMEFRAMES['fast']
    settings.symbols = ScalpingConfig.SCALPING_SYMBOLS
    
    print(f"✅ Take Profit: {settings.take_profit_pct:.1%}")
    print(f"✅ Stop Loss: {settings.stop_loss_pct:.1%}")  
    print(f"✅ Riesgo/Trade: {settings.risk_per_trade:.1%}")
    print(f"✅ Timeframe: {settings.bar_timeframe}")
    print(f"✅ Símbolos: {', '.join(settings.symbols[:3])}...")
    
    print("\n🎯 CONFIGURACIÓN OPTIMIZADA PARA:")
    print("   • Operaciones cada 5-15 minutos")
    print("   • Take profit pequeños pero frecuentes")
    print("   • Stop loss muy ajustados")
    print("   • Mayor volumen de trades")
    print("   • Aprovechamiento de micro-movimientos")
    
    return settings

def show_scalping_stats():
    """Mostrar estadísticas para scalping"""
    config = ScalpingConfig()
    
    print("\n📊 OBJETIVOS DE SCALPING:")
    print(f"   🎯 Win Rate Objetivo: {config.SCALPING_METRICS['target_win_rate']:.0%}")
    print(f"   ⚡ Trades/Hora: {config.SCALPING_METRICS['min_trades_per_hour']}-{config.SCALPING_METRICS['max_trades_per_hour']}")
    print(f"   🛡️ Drawdown Máx: {config.SCALPING_METRICS['max_drawdown']:.1%}")
    print(f"   💰 Take Profit: {config.TAKE_PROFIT_SCALPING:.1%}")
    print(f"   🛑 Stop Loss: {config.STOP_LOSS_SCALPING:.1%}")

if __name__ == "__main__":
    # Aplicar configuración de scalping
    apply_scalping_config()
    show_scalping_stats()
    
    print("\n🚀 ¡Configuración de scalping aplicada!")
    print("   Ejecuta el bot para comenzar operaciones agresivas.")