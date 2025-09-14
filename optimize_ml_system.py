#!/usr/bin/env python3
"""
Script para ejecutar optimización completa del sistema ML con Optuna.
Optimiza indicadores técnicos, modelos ML, ensemble weights e hiperparámetros.
"""

import sys
sys.path.insert(0, '.')

import argparse
from datetime import datetime, timedelta
from bot.advanced_optimizer import run_advanced_optimization
from bot.util import logger


def main():
    """Ejecuta optimización completa del sistema ML."""
    
    parser = argparse.ArgumentParser(description='Optimización avanzada ML con Optuna')
    parser.add_argument('--symbols', nargs='+', 
                       default=['BTC/USD', 'ETH/USD', 'SOL/USD', 'AVAX/USD'],
                       help='Símbolos para optimizar')
    parser.add_argument('--trials', type=int, default=50,
                       help='Número de trials de Optuna')
    parser.add_argument('--days', type=int, default=90,
                       help='Días de datos históricos para optimización')
    
    args = parser.parse_args()
    
    print("🚀 OPTIMIZACIÓN AVANZADA ML CON OPTUNA")
    print("=" * 50)
    print(f"📊 Símbolos: {', '.join(args.symbols)}")
    print(f"🔬 Trials: {args.trials}")
    print(f"📅 Período: últimos {args.days} días")
    print()
    
    try:
        # Ejecutar optimización
        results = run_advanced_optimization(
            symbols=args.symbols,
            n_trials=args.trials
        )
        
        if 'error' in results:
            print(f"❌ Error en optimización: {results['error']}")
            return False
        
        # Mostrar resultados
        print("\n🏆 RESULTADOS DE OPTIMIZACIÓN")
        print("=" * 50)
        print(f"📈 Mejor score: {results['best_score']:.3f}")
        print(f"🔬 Trials completados: {results['n_trials']}")
        print()
        print("🎯 Mejores parámetros encontrados:")
        print("-" * 40)
        
        best_params = results['best_params']
        
        # Agrupar parámetros por categoría
        traditional = {k: v for k, v in best_params.items() 
                      if k.startswith(('macd_', 'rsi_', 'thr_'))}
        ensemble = {k: v for k, v in best_params.items()
                   if k.startswith(('rf_', 'xgb_', 'ensemble_'))}
        rl = {k: v for k, v in best_params.items() if k.startswith('rl_')}
        neural = {k: v for k, v in best_params.items()
                 if k.startswith(('lstm_', 'transformer_'))}
        selection = {k: v for k, v in best_params.items()
                    if k.startswith(('ml_weight', 'min_confidence', 'model_switch'))}
        
        if traditional:
            print("📊 Indicadores Tradicionales:")
            for k, v in traditional.items():
                print(f"   • {k}: {v}")
            print()
        
        if ensemble:
            print("🤖 Ensemble Model:")
            for k, v in ensemble.items():
                print(f"   • {k}: {v}")
            print()
        
        if rl:
            print("🎯 Reinforcement Learning:")
            for k, v in rl.items():
                print(f"   • {k}: {v}")
            print()
        
        if neural:
            print("🧠 Redes Neuronales:")
            for k, v in neural.items():
                print(f"   • {k}: {v}")
            print()
        
        if selection:
            print("⚖️ Selección de Modelos:")
            for k, v in selection.items():
                print(f"   • {k}: {v}")
            print()
        
        print("✅ Optimización completada exitosamente!")
        print("💾 Resultados guardados en optimization_results/")
        print()
        print("🔄 Para usar los parámetros optimizados:")
        print("   1. Los parámetros se aplicarán automáticamente")
        print("   2. Reinicia el bot para usar la configuración optimizada")
        
        return True
        
    except KeyboardInterrupt:
        print("\n⚠️ Optimización interrumpida por el usuario")
        return False
    except Exception as e:
        print(f"\n❌ Error durante optimización: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)