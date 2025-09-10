"""
Configuración optimizada por Optuna con análisis de Fibonacci.
Este archivo contiene los parámetros óptimos encontrados por la optimización.
"""

# Parámetros optimizados para evitar micro-trading y maximizar ganancias netas
OPTIMIZED_PARAMS = {
    "risk_per_trade": 0.047,      # 4.7% - Riesgo EXACTO para meta $1000 diaria
    "take_profit_pct": 0.03,      # 3.0% - Take profit REALISTA para cierres frecuentes
    "stop_loss_pct": 0.01,        # 1.0% - Stop loss AGRESIVO para cortar pérdidas
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
    print(f"   🎯 Risk per trade: {OPTIMIZED_PARAMS['risk_per_trade']*100:.1f}% (META $1000 DIARIA)")
    print(f"   📈 Take profit: {OPTIMIZED_PARAMS['take_profit_pct']*100:.1f}% (SCALPING REALISTA)")
    print(f"   🛡️ Stop loss: {OPTIMIZED_PARAMS['stop_loss_pct']*100:.1f}% (AGRESIVO)")
    print(f"   🏆 Win rate esperado: {EXPECTED_PERFORMANCE['win_rate']*100:.1f}%")
    
    return settings_obj