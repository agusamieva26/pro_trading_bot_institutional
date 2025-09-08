"""
Advanced ML Optimizer con Optuna para optimización completa del sistema.
Optimiza indicadores técnicos, modelos ML avanzados, ensemble weights y hiperparámetros.
"""

import optuna
import pandas as pd
import numpy as np
from typing import Dict, Any, List
import joblib
from pathlib import Path

from .data import fetch_bars
from .features import make_features
from .strategy import hybrid_signal
from .advanced_ml import advanced_ensemble
from .reinforcement_learning import rl_trading_system
from .model_selection import advanced_model_selector
from .config import settings
from .util import logger


class AdvancedMLOptimizer:
    """
    Optimizador completo que usa Optuna para todos los componentes ML del bot.
    """
    
    def __init__(self):
        self.best_params = {}
        self.optimization_history = []
        
    def suggest_traditional_params(self, trial: optuna.Trial) -> Dict[str, Any]:
        """Sugiere parámetros para indicadores técnicos tradicionales."""
        return {
            'macd_fast': trial.suggest_int("macd_fast", 8, 18),
            'macd_slow': trial.suggest_int("macd_slow", 20, 30), 
            'macd_sig': trial.suggest_int("macd_sig", 5, 12),
            'rsi_len': trial.suggest_int("rsi_len", 8, 21),
            'thr_entry': trial.suggest_float("thr_entry", 0.3, 0.7),
            'thr_exit': trial.suggest_float("thr_exit", -0.7, -0.3)
        }
    
    def suggest_ensemble_params(self, trial: optuna.Trial) -> Dict[str, Any]:
        """Sugiere parámetros para el Ensemble Model."""
        return {
            'rf_n_estimators': trial.suggest_int("rf_n_estimators", 50, 200),
            'rf_max_depth': trial.suggest_int("rf_max_depth", 5, 20),
            'rf_min_samples_split': trial.suggest_int("rf_min_samples_split", 2, 10),
            'xgb_n_estimators': trial.suggest_int("xgb_n_estimators", 50, 200),
            'xgb_max_depth': trial.suggest_int("xgb_max_depth", 3, 10),
            'xgb_learning_rate': trial.suggest_float("xgb_learning_rate", 0.01, 0.3),
            'ensemble_rf_weight': trial.suggest_float("ensemble_rf_weight", 0.1, 0.9),
        }
    
    def suggest_rl_params(self, trial: optuna.Trial) -> Dict[str, Any]:
        """Sugiere parámetros para Reinforcement Learning."""
        return {
            'rl_learning_rate': trial.suggest_float("rl_learning_rate", 0.001, 0.1),
            'rl_epsilon_start': trial.suggest_float("rl_epsilon_start", 0.9, 1.0),
            'rl_epsilon_end': trial.suggest_float("rl_epsilon_end", 0.01, 0.1),
            'rl_epsilon_decay': trial.suggest_float("rl_epsilon_decay", 0.995, 0.999),
            'rl_batch_size': trial.suggest_categorical("rl_batch_size", [16, 32, 64]),
            'rl_memory_size': trial.suggest_int("rl_memory_size", 1000, 10000),
        }
    
    def suggest_neural_params(self, trial: optuna.Trial) -> Dict[str, Any]:
        """Sugiere parámetros para redes neuronales LSTM/Transformer."""
        return {
            'lstm_units_1': trial.suggest_categorical("lstm_units_1", [64, 128, 256]),
            'lstm_units_2': trial.suggest_categorical("lstm_units_2", [32, 64, 128]),
            'lstm_dropout': trial.suggest_float("lstm_dropout", 0.1, 0.5),
            'lstm_sequence_length': trial.suggest_int("lstm_sequence_length", 30, 120),
            'transformer_heads': trial.suggest_categorical("transformer_heads", [4, 8, 12]),
            'transformer_layers': trial.suggest_int("transformer_layers", 1, 4),
        }
    
    def suggest_model_selection_params(self, trial: optuna.Trial) -> Dict[str, Any]:
        """Sugiere parámetros para selección de modelos."""
        return {
            'ml_weight': trial.suggest_float("ml_weight", 0.2, 0.8),  # Peso de ML vs tradicional
            'min_confidence_threshold': trial.suggest_float("min_confidence_threshold", 0.5, 0.9),
            'model_switch_sensitivity': trial.suggest_float("model_switch_sensitivity", 0.05, 0.2),
        }
    
    def objective_function(self, trial: optuna.Trial, symbols: List[str], 
                          start: str, end: str) -> float:
        """
        Función objetivo completa que optimiza todo el sistema ML.
        """
        try:
            # 1. Obtener todos los parámetros sugeridos
            traditional_params = self.suggest_traditional_params(trial)
            ensemble_params = self.suggest_ensemble_params(trial)
            rl_params = self.suggest_rl_params(trial)
            neural_params = self.suggest_neural_params(trial)
            selection_params = self.suggest_model_selection_params(trial)
            
            logger.info(f"🔬 Evaluando trial {trial.number}: ML weight={selection_params['ml_weight']:.2f}")
            
            total_pnl = 0.0
            
            for symbol in symbols:
                try:
                    # 2. Obtener datos históricos
                    data = fetch_bars(symbol, start, end)
                    if data is None or len(data) < 100:
                        continue
                    
                    # 3. Configurar y entrenar modelos con parámetros sugeridos
                    symbol_pnl = self.evaluate_symbol_with_params(
                        symbol, data, traditional_params, ensemble_params,
                        rl_params, neural_params, selection_params
                    )
                    
                    total_pnl += symbol_pnl
                    
                except Exception as e:
                    logger.warning(f"⚠️ Error evaluando {symbol}: {e}")
                    continue
            
            # 4. Calcular métricas adicionales
            risk_adjusted_return = total_pnl / max(len(symbols), 1)
            
            logger.info(f"📊 Trial {trial.number}: PnL total=${total_pnl:.2f}, "
                       f"Risk-adj=${risk_adjusted_return:.2f}")
            
            return risk_adjusted_return
            
        except Exception as e:
            logger.error(f"❌ Error en objective function: {e}")
            return -1000.0  # Penalty severo por errores
    
    def evaluate_symbol_with_params(self, symbol: str, data: pd.DataFrame,
                                   traditional_params: Dict, ensemble_params: Dict,
                                   rl_params: Dict, neural_params: Dict,
                                   selection_params: Dict) -> float:
        """
        Evalúa un símbolo específico con los parámetros dados.
        """
        try:
            # Preparar features con parámetros tradicionales
            features_data = self.prepare_features_with_params(data, traditional_params)
            
            # Configurar ensemble temporal con parámetros sugeridos
            temp_ensemble = self.configure_temp_ensemble(features_data, ensemble_params)
            
            # Configurar RL temporal
            temp_rl = self.configure_temp_rl(features_data, rl_params)
            
            # Simular trading con modelo híbrido
            pnl = self.simulate_trading(features_data, temp_ensemble, temp_rl,
                                      traditional_params, selection_params)
            
            return pnl
            
        except Exception as e:
            logger.debug(f"Error evaluando {symbol}: {e}")
            return 0.0
    
    def prepare_features_with_params(self, data: pd.DataFrame, 
                                   traditional_params: Dict) -> pd.DataFrame:
        """Prepara features usando parámetros tradicionales optimizados."""
        features_data = data.copy()
        
        # Aplicar parámetros MACD personalizados
        from .features import macd, rsi, ema, atr
        
        try:
            # MACD con parámetros optimizados
            macd_line, macd_signal, macd_hist = macd(
                features_data['close'],
                traditional_params['macd_fast'],
                traditional_params['macd_slow'], 
                traditional_params['macd_sig']
            )
            features_data['macd'] = macd_line
            features_data['macd_sig'] = macd_signal
            features_data['macd_hist'] = macd_hist
            
            # RSI con longitud optimizada
            features_data['rsi_14'] = rsi(features_data['close'], 
                                        traditional_params['rsi_len'])
            
            # EMAs
            features_data['ema_12'] = ema(features_data['close'], 12)
            features_data['ema_26'] = ema(features_data['close'], 26)
            
            # ATR
            features_data['atr_14'] = atr(features_data, 14)
            
            # Returns y volatilidad
            features_data['ret_1'] = features_data['close'].pct_change()
            features_data['vol_roll'] = features_data['ret_1'].rolling(24).std() * (24**0.5)
            
            features_data = features_data.dropna()
            
        except Exception as e:
            logger.debug(f"Error preparando features: {e}")
        
        return features_data
    
    def configure_temp_ensemble(self, data: pd.DataFrame, 
                               ensemble_params: Dict) -> object:
        """Configura ensemble temporal con parámetros optimizados."""
        try:
            from sklearn.ensemble import RandomForestClassifier
            import xgboost as xgb
            
            # Crear target simple
            target = np.where(data['close'].pct_change().shift(-1) > 0.005, 1, 0)
            
            # Preparar features básicas
            feature_cols = ['close', 'volume', 'rsi_14', 'macd_hist']
            available_cols = [col for col in feature_cols if col in data.columns]
            
            if len(available_cols) < 2:
                return None
            
            X = data[available_cols].fillna(0)
            y = target
            
            # Configurar RandomForest con parámetros optimizados
            rf_model = RandomForestClassifier(
                n_estimators=ensemble_params['rf_n_estimators'],
                max_depth=ensemble_params['rf_max_depth'],
                min_samples_split=ensemble_params['rf_min_samples_split'],
                random_state=42
            )
            
            # Configurar XGBoost con parámetros optimizados
            xgb_model = xgb.XGBClassifier(
                n_estimators=ensemble_params['xgb_n_estimators'],
                max_depth=ensemble_params['xgb_max_depth'],
                learning_rate=ensemble_params['xgb_learning_rate'],
                random_state=42
            )
            
            # Entrenar modelos si hay suficientes datos
            if len(X) > 50:
                rf_model.fit(X, y)
                xgb_model.fit(X, y)
                
                return {
                    'rf': rf_model,
                    'xgb': xgb_model,
                    'rf_weight': ensemble_params['ensemble_rf_weight'],
                    'xgb_weight': 1 - ensemble_params['ensemble_rf_weight']
                }
            
        except Exception as e:
            logger.debug(f"Error configurando ensemble: {e}")
        
        return None
    
    def configure_temp_rl(self, data: pd.DataFrame, rl_params: Dict) -> object:
        """Configura RL temporal con parámetros optimizados."""
        try:
            # Crear un agente RL simplificado con parámetros optimizados
            # (implementación simplificada para optimización rápida)
            
            temp_rl = {
                'learning_rate': rl_params['rl_learning_rate'],
                'epsilon': rl_params['rl_epsilon_start'],
                'trained': len(data) > 100  # Simula entrenamiento
            }
            
            return temp_rl
            
        except Exception as e:
            logger.debug(f"Error configurando RL: {e}")
            return None
    
    def simulate_trading(self, data: pd.DataFrame, temp_ensemble: object,
                        temp_rl: object, traditional_params: Dict,
                        selection_params: Dict) -> float:
        """
        Simula trading con el sistema híbrido optimizado.
        """
        try:
            position = 0
            entry_price = 0
            total_pnl = 0
            
            ml_weight = selection_params['ml_weight']
            traditional_weight = 1 - ml_weight
            
            for i, (_, row) in enumerate(data.iterrows()):
                if i < 20:  # Skip primeras filas para indicadores
                    continue
                
                # 1. Señal tradicional
                traditional_signal = self.get_traditional_signal(row, traditional_params)
                
                # 2. Señal ML (ensemble)
                ml_signal = self.get_ml_signal(row, data, temp_ensemble, i)
                
                # 3. Combinar señales con pesos optimizados
                combined_signal = (traditional_weight * traditional_signal + 
                                 ml_weight * ml_signal)
                
                # 4. Decisiones de trading
                current_price = row['close']
                
                # Cerrar posición
                if position != 0:
                    if (position > 0 and combined_signal < traditional_params['thr_exit']) or \
                       (position < 0 and combined_signal > -traditional_params['thr_exit']):
                        pnl = position * (current_price - entry_price)
                        total_pnl += pnl
                        position = 0
                
                # Abrir posición
                if position == 0 and abs(combined_signal) > traditional_params['thr_entry']:
                    if combined_signal > 0:
                        position = 1  # Long
                        entry_price = current_price
                    elif combined_signal < 0:
                        position = -1  # Short
                        entry_price = current_price
            
            # Cerrar posición final
            if position != 0:
                final_pnl = position * (data.iloc[-1]['close'] - entry_price)
                total_pnl += final_pnl
            
            return total_pnl
            
        except Exception as e:
            logger.debug(f"Error simulando trading: {e}")
            return 0.0
    
    def get_traditional_signal(self, row: pd.Series, params: Dict) -> float:
        """Genera señal tradicional con parámetros optimizados."""
        try:
            # Lógica simplificada de señal tradicional
            macd_signal = row.get('macd_hist', 0)
            rsi_signal = (row.get('rsi_14', 50) - 50) / 50
            
            combined = 0.6 * macd_signal + 0.4 * rsi_signal
            return np.clip(combined, -1, 1)
            
        except:
            return 0.0
    
    def get_ml_signal(self, row: pd.Series, data: pd.DataFrame, 
                     temp_ensemble: object, index: int) -> float:
        """Genera señal ML con ensemble optimizado."""
        try:
            if temp_ensemble is None:
                return 0.0
            
            # Preparar features para predicción
            feature_cols = ['close', 'volume', 'rsi_14', 'macd_hist']
            available_cols = [col for col in feature_cols if col in data.columns]
            
            if len(available_cols) < 2:
                return 0.0
            
            features = np.array([row[col] for col in available_cols]).reshape(1, -1)
            features = np.nan_to_num(features)
            
            # Predicción con ensemble
            rf_pred = temp_ensemble['rf'].predict_proba(features)[0][1] if 'rf' in temp_ensemble else 0.5
            xgb_pred = temp_ensemble['xgb'].predict_proba(features)[0][1] if 'xgb' in temp_ensemble else 0.5
            
            # Combinar con pesos optimizados
            ensemble_pred = (temp_ensemble['rf_weight'] * rf_pred + 
                           temp_ensemble['xgb_weight'] * xgb_pred)
            
            # Convertir a señal [-1, 1]
            signal = (ensemble_pred - 0.5) * 2
            return np.clip(signal, -1, 1)
            
        except Exception as e:
            logger.debug(f"Error en señal ML: {e}")
            return 0.0
    
    def optimize_complete_system(self, symbols: List[str], start: str, end: str,
                               n_trials: int = 100) -> Dict[str, Any]:
        """
        Ejecuta optimización completa del sistema ML con Optuna.
        """
        logger.info(f"🚀 Iniciando optimización completa con Optuna: {n_trials} trials")
        logger.info(f"📊 Símbolos: {symbols}")
        logger.info(f"📅 Período: {start} a {end}")
        
        try:
            # Crear estudio Optuna
            study = optuna.create_study(
                direction="maximize",
                sampler=optuna.samplers.TPESampler(seed=42),
                pruner=optuna.pruners.MedianPruner()
            )
            
            # Optimizar
            objective = lambda trial: self.objective_function(trial, symbols, start, end)
            study.optimize(objective, n_trials=n_trials, timeout=3600)  # Max 1 hora
            
            # Guardar mejores parámetros
            self.best_params = study.best_trial.params
            
            logger.info(f"🏆 Optimización completada!")
            logger.info(f"📈 Mejor score: {study.best_trial.value:.3f}")
            logger.info(f"🎯 Mejores parámetros encontrados:")
            
            for key, value in self.best_params.items():
                logger.info(f"   • {key}: {value}")
            
            # Guardar resultados
            self.save_optimization_results(study)
            
            return {
                'best_params': self.best_params,
                'best_score': study.best_trial.value,
                'n_trials': len(study.trials),
                'study': study
            }
            
        except Exception as e:
            logger.error(f"❌ Error en optimización: {e}")
            return {'error': str(e)}
    
    def save_optimization_results(self, study: optuna.Study):
        """Guarda resultados de optimización."""
        try:
            results_dir = Path("optimization_results")
            results_dir.mkdir(exist_ok=True)
            
            # Guardar mejores parámetros
            joblib.dump(self.best_params, results_dir / "best_params.pkl")
            
            # Guardar estudio completo
            joblib.dump(study, results_dir / "optuna_study.pkl")
            
            logger.info("✅ Resultados de optimización guardados")
            
        except Exception as e:
            logger.error(f"❌ Error guardando resultados: {e}")


# Instancia global del optimizador avanzado
ml_optimizer = AdvancedMLOptimizer()


def run_advanced_optimization(symbols: List[str] = None, n_trials: int = 50):
    """
    Función principal para ejecutar optimización completa del sistema.
    """
    if symbols is None:
        symbols = ['ETH/USD', 'BTC/USD', 'SOL/USD']
    
    # Período de optimización (últimos 3 meses)
    from datetime import datetime, timedelta
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    
    logger.info("🎯 Iniciando optimización avanzada ML con Optuna")
    
    results = ml_optimizer.optimize_complete_system(
        symbols=symbols,
        start=start_date,
        end=end_date,
        n_trials=n_trials
    )
    
    return results


if __name__ == "__main__":
    # Ejecutar optimización desde línea de comandos
    results = run_advanced_optimization(n_trials=30)
    print("🏆 Optimización completada!")
    print(f"Mejores parámetros: {results.get('best_params', {})}")