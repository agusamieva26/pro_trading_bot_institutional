"""
Configuración optimizada por Optuna con análisis de Fibonacci.
Este archivo contiene los parámetros óptimos encontrados por la optimización.
"""

# Parámetros optimizados por Optuna (15 trials, score: 5911.78)
OPTIMIZED_PARAMS = {
    "risk_per_trade": 0.015,      # 1.5% - Riesgo optimizado para meta $1000
    "take_profit_pct": 0.05,      # 5.0% - Target de ganancia optimizado
    "stop_loss_pct": 0.01,        # 1.0% - Stop loss optimizado
}

# Métricas de rendimiento esperado
EXPECTED_PERFORMANCE = {
    "win_rate": 0.545,            # 54.5% de trades ganadores
    "total_trades": 319,          # Trades analizados en backtest
    "max_drawdown": 4.70,         # Drawdown máximo esperado
    "total_pnl": 3.91,            # P&L positivo
}

def apply_optimized_config(settings_obj):
    """
    Aplica la configuración optimizada a un objeto settings.
    """
    settings_obj.risk_per_trade = OPTIMIZED_PARAMS["risk_per_trade"]
    settings_obj.take_profit_pct = OPTIMIZED_PARAMS["take_profit_pct"] 
    settings_obj.stop_loss_pct = OPTIMIZED_PARAMS["stop_loss_pct"]
    
    print("✅ Configuración optimizada por Optuna aplicada:")
    print(f"   🎯 Risk per trade: {OPTIMIZED_PARAMS['risk_per_trade']*100:.1f}% (META $1000)")
    print(f"   📈 Take profit: {OPTIMIZED_PARAMS['take_profit_pct']*100:.1f}%")
    print(f"   🛡️ Stop loss: {OPTIMIZED_PARAMS['stop_loss_pct']*100:.1f}%")
    print(f"   🏆 Win rate esperado: {EXPECTED_PERFORMANCE['win_rate']*100:.1f}%")
    
    return settings_obj