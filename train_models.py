"""
Script de entrenamiento completo para todos los modelos ML del bot de trading.
Entrena Ensemble Models, Reinforcement Learning, LSTM/Transformers con datos históricos.
"""

import sys
sys.path.insert(0, '.')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Import bot modules
from bot.data import fetch_all_bars
from bot.advanced_ml import advanced_ensemble, EnsembleModel
from bot.reinforcement_learning import rl_trading_system
from bot.advanced_features import advanced_feature_generator
from bot.model_selection import advanced_model_selector
from bot.config import settings
from bot.util import logger
from bot.strategy import train_model as train_legacy_model

def fetch_training_data(symbols, timeframe='1Day', bars_count=1000):
    """
    Obtiene datos históricos para entrenamiento.
    """
    print("📡 Obteniendo datos históricos para entrenamiento...")
    
    all_data = {}
    
    # Usar función fetch_all_bars existente
    try:
        print(f"   • Descargando {len(symbols)} símbolos...")
        symbol_data = fetch_all_bars(symbols, timeframe, bars_count)
        
        for symbol, bars in symbol_data.items():
            if bars is not None and len(bars) > 50:
                all_data[symbol] = bars
                print(f"   ✅ {symbol}: {len(bars)} barras")
            else:
                print(f"   ❌ {symbol}: Datos insuficientes")
                
    except Exception as e:
        print(f"   ⚠️ Error general: {e}")
    
    return all_data

def prepare_training_data(all_data):
    """
    Prepara datos combinados para entrenamiento.
    """
    print("\n🔧 Preparando datos para entrenamiento ML...")
    
    combined_data = []
    
    for symbol, data in all_data.items():
        print(f"   • Procesando {symbol}...")
        
        # Generar features avanzadas
        enhanced_data = advanced_feature_generator.generate_advanced_features(data.copy())
        
        # Agregar columna de símbolo para identificación
        enhanced_data['symbol'] = symbol
        
        combined_data.append(enhanced_data)
    
    # Combinar todos los datos
    full_dataset = pd.concat(combined_data, ignore_index=True)
    
    # Crear columna target para entrenamiento
    print("   • Creando targets de entrenamiento...")
    
    # Verificar si hay columna de tiempo
    time_col = None
    for col in ['timestamp', 'time', 'datetime', 'date']:
        if col in full_dataset.columns:
            time_col = col
            break
    
    if time_col:
        full_dataset = full_dataset.sort_values(['symbol', time_col]).reset_index(drop=True)
    else:
        # Si no hay columna de tiempo, usar el índice
        full_dataset = full_dataset.reset_index().sort_values(['symbol', 'index']).drop('index', axis=1).reset_index(drop=True)
    
    # Calcular target basado en rendimiento futuro
    full_dataset['future_return'] = full_dataset.groupby('symbol')['close'].pct_change(5).shift(-5)
    
    # Convertir a clases: -1 (SELL), 0 (HOLD), 1 (BUY)
    conditions = [
        full_dataset['future_return'] < -0.02,  # Caída > 2%
        full_dataset['future_return'] > 0.02,   # Subida > 2%
    ]
    choices = [-1, 1]  # SELL, BUY
    full_dataset['target'] = np.select(conditions, choices, default=0)  # Default: HOLD
    
    # Limpiar datos
    full_dataset = full_dataset.dropna(subset=['close', 'target'])
    full_dataset = full_dataset.fillna(method='ffill').fillna(method='bfill').fillna(0)
    
    # Remover columnas auxiliares y no numéricas  
    full_dataset = full_dataset.drop(['future_return', 'symbol'], axis=1)
    
    print(f"✅ Dataset combinado: {len(full_dataset)} filas, {len(full_dataset.columns)} columnas")
    print(f"   • Distribución target: SELL={sum(full_dataset['target'] == -1)}, HOLD={sum(full_dataset['target'] == 0)}, BUY={sum(full_dataset['target'] == 1)}")
    
    return full_dataset

def train_ensemble_model(training_data):
    """
    Entrena el modelo Ensemble completo.
    """
    print("\n🎯 ENTRENANDO ENSEMBLE MODEL...")
    print("=" * 50)
    
    try:
        # Entrenar ensemble con datos completos
        advanced_ensemble.train(training_data, target_col='target')
        
        # Verificar entrenamiento
        if advanced_ensemble.is_trained:
            print("✅ Ensemble Model entrenado exitosamente!")
            
            # Mostrar información del ensemble
            for model_name, weight in advanced_ensemble.weights.items():
                print(f"   • {model_name}: peso={weight:.3f}")
            
            # Guardar modelo
            advanced_ensemble.save_models("models")
            print("✅ Ensemble Model guardado en directorio 'models'")
            
            return True
        else:
            print("❌ Error: Ensemble no se entrenó correctamente")
            return False
            
    except Exception as e:
        print(f"❌ Error entrenando Ensemble: {e}")
        return False

def train_reinforcement_learning(training_data, episodes=200):
    """
    Entrena el sistema de Reinforcement Learning.
    """
    print(f"\n🤖 ENTRENANDO REINFORCEMENT LEARNING ({episodes} episodios)...")
    print("=" * 60)
    
    try:
        # Entrenar RL con más episodios para mejor aprendizaje
        training_result = rl_trading_system.train(training_data, episodes=episodes)
        
        if training_result.get('success', False):
            print("✅ Reinforcement Learning entrenado exitosamente!")
            
            # Mostrar métricas de entrenamiento
            metrics = [
                ('Win Rate Promedio', f"{training_result.get('avg_win_rate', 0):.1%}"),
                ('Reward Promedio', f"{training_result.get('avg_reward', 0):.3f}"),
                ('Balance Final Promedio', f"${training_result.get('avg_balance', 0):.0f}"),
                ('Epsilon Final', f"{training_result.get('final_epsilon', 0):.3f}")
            ]
            
            for metric_name, metric_value in metrics:
                print(f"   • {metric_name}: {metric_value}")
            
            return True
        else:
            print("❌ Error: RL no se entrenó correctamente")
            return False
            
    except Exception as e:
        print(f"❌ Error entrenando RL: {e}")
        return False

def train_deep_learning_models(training_data):
    """
    Entrena modelos LSTM y Transformer.
    """
    print("\n🧠 ENTRENANDO MODELOS DEEP LEARNING...")
    print("=" * 50)
    
    success_count = 0
    
    # Intentar entrenar LSTM
    try:
        if hasattr(advanced_ensemble, 'models') and 'lstm' in advanced_ensemble.models:
            lstm_model = advanced_ensemble.models['lstm']
            print("   📊 Entrenando LSTM Network...")
            
            if lstm_model.train(training_data, target_col='target', epochs=50):
                print("   ✅ LSTM entrenado exitosamente")
                success_count += 1
            else:
                print("   ⚠️ LSTM no pudo entrenarse")
        else:
            print("   ⚠️ LSTM no disponible")
            
    except Exception as e:
        print(f"   ❌ Error LSTM: {e}")
    
    # Intentar entrenar Transformer
    try:
        if hasattr(advanced_ensemble, 'models') and 'transformer' in advanced_ensemble.models:
            transformer_model = advanced_ensemble.models['transformer']
            print("   🔄 Entrenando Transformer Network...")
            
            if transformer_model.train(training_data, target_col='target', epochs=30):
                print("   ✅ Transformer entrenado exitosamente")
                success_count += 1
            else:
                print("   ⚠️ Transformer no pudo entrenarse")
        else:
            print("   ⚠️ Transformer no disponible")
            
    except Exception as e:
        print(f"   ❌ Error Transformer: {e}")
    
    return success_count > 0

def validate_trained_models(training_data):
    """
    Valida que todos los modelos entrenados funcionen correctamente.
    """
    print("\n✅ VALIDANDO MODELOS ENTRENADOS...")
    print("=" * 40)
    
    validation_results = {}
    
    try:
        # Ejecutar comparación completa de modelos
        comparison_result = advanced_model_selector.run_model_comparison(training_data)
        
        best_model = comparison_result.get('best_model', 'ensemble')
        best_score = comparison_result.get('best_score', 0.0)
        model_rankings = comparison_result.get('model_rankings', {})
        
        print(f"🏆 Mejor modelo: {best_model} (Score: {best_score:.3f})")
        print("\n📊 Ranking de modelos:")
        
        for i, (model_name, score) in enumerate(model_rankings.items(), 1):
            print(f"   {i}. {model_name}: {score:.3f}")
        
        # Test predicción con mejor modelo
        test_prediction, model_used, confidence = advanced_model_selector.get_optimal_prediction(training_data)
        
        print(f"\n🎯 Test de predicción:")
        print(f"   • Modelo usado: {model_used}")
        print(f"   • Predicción: {test_prediction:+.3f}")
        print(f"   • Confianza: {confidence:.3f}")
        
        validation_results = {
            'best_model': best_model,
            'best_score': best_score,
            'model_count': len(model_rankings),
            'test_prediction_success': test_prediction is not None
        }
        
        return validation_results
        
    except Exception as e:
        print(f"❌ Error en validación: {e}")
        return {'success': False}

def train_legacy_model_for_compatibility(historical_data: Dict[str, pd.DataFrame]) -> bool:
    """
    Entrena y guarda el modelo legacy 'rf_clf.pkl' para compatibilidad.
    Esto asegura que el bot principal pueda arrancar.
    """
    print("\n\n🔧 ENTRENANDO MODELO LEGACY (rf_clf.pkl) PARA COMPATIBILIDAD...")
    print("=" * 60)
    try:
        # Usar datos de un símbolo principal como BTC/USD
        main_symbol_data = historical_data.get('BTC/USD')
        if main_symbol_data is None or main_symbol_data.empty:
            # Usar cualquier otro si BTC no está
            if not historical_data:
                logger.error("❌ No hay datos para entrenar modelo legacy.")
                return False
            main_symbol_data = next(iter(historical_data.values()))
        
        logger.info(f"   • Usando datos de {next(iter(historical_data.keys()))} para modelo legacy...")
        
        # La función train_legacy_model se encarga de todo (features, training, save)
        model = train_legacy_model(main_symbol_data)
        
        return model is not None
            
    except Exception as e:
        logger.error(f"❌ Error entrenando modelo legacy: {e}")
        return False

def main():
    """
    Ejecuta entrenamiento completo de todos los modelos ML.
    """
    print("🚀 INICIANDO ENTRENAMIENTO COMPLETO DE MODELOS ML")
    print("=" * 60)
    print(f"Fecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Símbolos para entrenamiento (diversificado)
    training_symbols = [
        'BTC/USD', 'ETH/USD', 'SOL/USD', 'AVAX/USD',  # Crypto major
        'AAPL', 'GOOGL', 'MSFT', 'NVDA',              # Tech stocks
        'SPY', 'QQQ', 'IWM'                           # ETFs
    ]
    
    print(f"📋 Símbolos para entrenamiento: {len(training_symbols)}")
    for symbol in training_symbols:
        print(f"   • {symbol}")
    
    # 1. Obtener datos históricos
    historical_data = fetch_training_data(training_symbols, timeframe='1Day', bars_count=500)
    
    if len(historical_data) == 0:
        print("❌ Error: No se pudieron obtener datos históricos")
        return False
    
    print(f"\n✅ Datos obtenidos para {len(historical_data)} símbolos")
    
    # 2. Preparar datos de entrenamiento
    training_data = prepare_training_data(historical_data)
    
    if len(training_data) < 100:
        print("❌ Error: Datos insuficientes para entrenamiento")
        return False
    
    # 3. Entrenar Ensemble Model
    ensemble_success = train_ensemble_model(training_data)
    
    # 4. Entrenar Reinforcement Learning
    rl_success = train_reinforcement_learning(training_data, episodes=150)
    
    # 5. Entrenar Deep Learning models
    dl_success = train_deep_learning_models(training_data)
    
    # 6. Entrenar modelo legacy para compatibilidad
    legacy_success = train_legacy_model_for_compatibility(historical_data)
    
    # 7. Validar modelos entrenados
    validation_results = validate_trained_models(training_data)
    
    # Resumen final
    print("\n" + "=" * 60)
    print("🏆 RESUMEN FINAL DE ENTRENAMIENTO")
    print("=" * 60)

    results = [
        ('Ensemble Model', '✅' if ensemble_success else '❌'),
        ('Reinforcement Learning', '✅' if rl_success else '❌'),
        ('Deep Learning Models', '✅' if dl_success else '❌'),
        ('Legacy Compatibility Model', '✅' if legacy_success else '❌'),
        ('Validación Final', '✅' if validation_results.get('test_prediction_success') else '❌')
    ]
    
    for component, status in results:
        print(f"{status} {component}")
    
    if validation_results.get('best_model'):
        print(f"\n🎯 Mejor modelo: {validation_results['best_model']}")
        print(f"📊 Score: {validation_results.get('best_score', 0):.3f}")
        print(f"🔢 Modelos disponibles: {validation_results.get('model_count', 0)}")
    
    success_rate = sum([ensemble_success, rl_success, dl_success, legacy_success]) / 4
    print(f"\n📈 Tasa de éxito general: {success_rate:.1%}")
    
    if success_rate >= 0.67:
        print("\n🎉 ¡ENTRENAMIENTO COMPLETADO EXITOSAMENTE!")
        print("   Tu bot ahora tiene modelos ML entrenados y listos.")
        print("   • Ensemble Model con múltiples algoritmos")
        print("   • Sistema de Reinforcement Learning adaptativo")
        print("   • Redes neuronales para análisis temporal")
        print("   • Selección automática del mejor modelo")
        return True
    else:
        print("\n⚠️ Entrenamiento parcial completado")
        print("   Algunos modelos no se entrenaron correctamente.")
        print("   El bot funcionará con los modelos disponibles.")
        return False

if __name__ == "__main__":
    main()