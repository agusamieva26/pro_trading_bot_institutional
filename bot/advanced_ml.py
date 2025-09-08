"""
Advanced Machine Learning System con LSTM/Transformers, Ensemble Models y Reinforcement Learning.
Sistema de próxima generación para predicciones de alta precisión en mercados financieros.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
import joblib
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# ML Libraries
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score, TimeSeriesSplit
from sklearn.metrics import classification_report, confusion_matrix
import xgboost as xgb

# Deep Learning (will install if needed)
try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential, Model
    from tensorflow.keras.layers import LSTM, Dense, Dropout, Attention, MultiHeadAttention, LayerNormalization
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False

from .util import logger
from .features import make_features


class LSTMPredictor:
    """
    LSTM/GRU network para análisis temporal de series financieras.
    """
    
    def __init__(self, sequence_length=60, features_dim=12):
        self.sequence_length = sequence_length
        self.features_dim = features_dim
        self.model = None
        self.scaler = None
        self.is_trained = False
        
        if not TENSORFLOW_AVAILABLE:
            logger.warning("⚠️ TensorFlow no disponible - LSTM deshabilitado")
            return
        
        # Crear modelo LSTM
        self.model = self._build_lstm_model()
    
    def _build_lstm_model(self):
        """Construye arquitectura LSTM optimizada para trading."""
        if not TENSORFLOW_AVAILABLE:
            return None
        
        model = Sequential([
            # Primera capa LSTM con Dropout
            LSTM(128, return_sequences=True, input_shape=(self.sequence_length, self.features_dim)),
            Dropout(0.2),
            
            # Segunda capa LSTM
            LSTM(64, return_sequences=True),
            Dropout(0.2),
            
            # Tercera capa LSTM
            LSTM(32, return_sequences=False),
            Dropout(0.2),
            
            # Capas densas para clasificación
            Dense(50, activation='relu'),
            Dropout(0.3),
            Dense(25, activation='relu'),
            Dropout(0.2),
            Dense(3, activation='softmax')  # 3 clases: BUY, HOLD, SELL
        ])
        
        model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy']
        )
        
        return model
    
    def prepare_sequences(self, data: pd.DataFrame, target_col: str = 'target') -> Tuple[np.ndarray, np.ndarray]:
        """Convierte datos tabulares en secuencias para LSTM."""
        if len(data) < self.sequence_length:
            return np.array([]), np.array([])
        
        # Normalizar features
        feature_cols = [col for col in data.columns if col != target_col]
        
        if self.scaler is None:
            from sklearn.preprocessing import StandardScaler
            self.scaler = StandardScaler()
            scaled_features = self.scaler.fit_transform(data[feature_cols])
        else:
            scaled_features = self.scaler.transform(data[feature_cols])
        
        # Crear secuencias
        X_sequences = []
        y_sequences = []
        
        for i in range(self.sequence_length, len(data)):
            X_sequences.append(scaled_features[i-self.sequence_length:i])
            
            if target_col in data.columns:
                # Convertir target a clases: -1->0, 0->1, 1->2
                target_val = data[target_col].iloc[i]
                if target_val < -0.1:
                    y_sequences.append(0)  # SELL
                elif target_val > 0.1:
                    y_sequences.append(2)  # BUY
                else:
                    y_sequences.append(1)  # HOLD
        
        return np.array(X_sequences), np.array(y_sequences)
    
    def train(self, data: pd.DataFrame, target_col: str = 'target', epochs: int = 50):
        """Entrena el modelo LSTM."""
        if not TENSORFLOW_AVAILABLE or self.model is None:
            return False
        
        X_seq, y_seq = self.prepare_sequences(data, target_col)
        
        if len(X_seq) == 0:
            logger.warning("⚠️ Datos insuficientes para secuencias LSTM")
            return False
        
        # Split train/validation
        split_idx = int(len(X_seq) * 0.8)
        X_train, X_val = X_seq[:split_idx], X_seq[split_idx:]
        y_train, y_val = y_seq[:split_idx], y_seq[split_idx:]
        
        # Callbacks
        callbacks = [
            EarlyStopping(patience=10, restore_best_weights=True),
            ReduceLROnPlateau(factor=0.5, patience=5)
        ]
        
        # Entrenar
        history = self.model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=epochs,
            batch_size=32,
            callbacks=callbacks,
            verbose=0
        )
        
        self.is_trained = True
        
        # Evaluar
        val_loss, val_acc = self.model.evaluate(X_val, y_val, verbose=0)
        logger.info(f"✅ LSTM entrenado: Accuracy={val_acc:.3f}, Loss={val_loss:.3f}")
        
        return True
    
    def predict(self, data: pd.DataFrame) -> Optional[np.ndarray]:
        """Predice usando el modelo LSTM."""
        if not self.is_trained or not TENSORFLOW_AVAILABLE:
            return None
        
        X_seq, _ = self.prepare_sequences(data, target_col='dummy')
        
        if len(X_seq) == 0:
            return None
        
        predictions = self.model.predict(X_seq, verbose=0)
        
        # Convertir probabilidades a señales: 0->-1, 1->0, 2->+1
        signals = []
        for pred in predictions:
            class_pred = np.argmax(pred)
            confidence = np.max(pred)
            
            if class_pred == 0:  # SELL
                signals.append(-confidence)
            elif class_pred == 2:  # BUY
                signals.append(confidence)
            else:  # HOLD
                signals.append(0.0)
        
        return np.array(signals)


class TransformerPredictor:
    """
    Transformer network para análisis de patrones complejos en datos financieros.
    """
    
    def __init__(self, sequence_length=60, features_dim=12, num_heads=8):
        self.sequence_length = sequence_length
        self.features_dim = features_dim
        self.num_heads = num_heads
        self.model = None
        self.scaler = None
        self.is_trained = False
        
        if not TENSORFLOW_AVAILABLE:
            logger.warning("⚠️ TensorFlow no disponible - Transformer deshabilitado")
            return
        
        self.model = self._build_transformer_model()
    
    def _build_transformer_model(self):
        """Construye arquitectura Transformer para trading."""
        if not TENSORFLOW_AVAILABLE:
            return None
        
        # Input layer
        inputs = tf.keras.Input(shape=(self.sequence_length, self.features_dim))
        
        # Positional encoding (simplificado)
        x = inputs
        
        # Multi-head attention block
        attention_output = MultiHeadAttention(
            num_heads=self.num_heads, 
            key_dim=self.features_dim//self.num_heads
        )(x, x)
        
        # Add & Norm
        x = LayerNormalization()(x + attention_output)
        
        # Feed Forward Network
        ffn = Sequential([
            Dense(128, activation='relu'),
            Dropout(0.1),
            Dense(self.features_dim)
        ])
        
        ffn_output = ffn(x)
        x = LayerNormalization()(x + ffn_output)
        
        # Global pooling y clasificación
        x = tf.keras.layers.GlobalAveragePooling1D()(x)
        x = Dense(64, activation='relu')(x)
        x = Dropout(0.3)(x)
        outputs = Dense(3, activation='softmax')(x)
        
        model = Model(inputs, outputs)
        model.compile(
            optimizer=Adam(learning_rate=0.0001),
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy']
        )
        
        return model
    
    def train(self, data: pd.DataFrame, target_col: str = 'target', epochs: int = 30):
        """Entrena el modelo Transformer."""
        if not TENSORFLOW_AVAILABLE or self.model is None:
            return False
        
        # Reutilizar lógica de LSTM para preparar secuencias
        lstm_helper = LSTMPredictor(self.sequence_length, self.features_dim)
        X_seq, y_seq = lstm_helper.prepare_sequences(data, target_col)
        
        if len(X_seq) == 0:
            return False
        
        # Split y entrenar igual que LSTM
        split_idx = int(len(X_seq) * 0.8)
        X_train, X_val = X_seq[:split_idx], X_seq[split_idx:]
        y_train, y_val = y_seq[:split_idx], y_seq[split_idx:]
        
        callbacks = [
            EarlyStopping(patience=8, restore_best_weights=True),
            ReduceLROnPlateau(factor=0.7, patience=4)
        ]
        
        history = self.model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=epochs,
            batch_size=16,
            callbacks=callbacks,
            verbose=0
        )
        
        self.is_trained = True
        val_loss, val_acc = self.model.evaluate(X_val, y_val, verbose=0)
        logger.info(f"✅ Transformer entrenado: Accuracy={val_acc:.3f}, Loss={val_loss:.3f}")
        
        return True
    
    def predict(self, data: pd.DataFrame) -> Optional[np.ndarray]:
        """Predice usando Transformer."""
        if not self.is_trained or not TENSORFLOW_AVAILABLE:
            return None
        
        lstm_helper = LSTMPredictor(self.sequence_length, self.features_dim)
        X_seq, _ = lstm_helper.prepare_sequences(data, target_col='dummy')
        
        if len(X_seq) == 0:
            return None
        
        predictions = self.model.predict(X_seq, verbose=0)
        
        # Convertir a señales igual que LSTM
        signals = []
        for pred in predictions:
            class_pred = np.argmax(pred)
            confidence = np.max(pred)
            
            if class_pred == 0:
                signals.append(-confidence)
            elif class_pred == 2:
                signals.append(confidence)
            else:
                signals.append(0.0)
        
        return np.array(signals)


class EnsembleModel:
    """
    Ensemble que combina RandomForest, XGBoost, LSTM y Transformer.
    """
    
    def __init__(self):
        self.models = {}
        self.weights = {}
        self.is_trained = False
        
        # Inicializar modelos
        self.models['rf'] = RandomForestClassifier(
            n_estimators=200,
            max_depth=15,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1
        )
        
        self.models['xgb'] = xgb.XGBClassifier(
            n_estimators=150,
            max_depth=8,
            learning_rate=0.1,
            random_state=42,
            n_jobs=-1
        )
        
        if TENSORFLOW_AVAILABLE:
            self.models['lstm'] = LSTMPredictor()
            self.models['transformer'] = TransformerPredictor()
    
    def train(self, data: pd.DataFrame, target_col: str = 'target'):
        """Entrena todos los modelos del ensemble."""
        
        # Preparar datos para modelos tradicionales
        feature_cols = [col for col in data.columns if col != target_col and col != 'timestamp']
        X = data[feature_cols]
        
        # Convertir target continuo a clases
        y_continuous = data[target_col]
        y_classes = []
        for val in y_continuous:
            if val < -0.1:
                y_classes.append(0)  # SELL
            elif val > 0.1:
                y_classes.append(2)  # BUY
            else:
                y_classes.append(1)  # HOLD
        y = np.array(y_classes)
        
        model_scores = {}
        
        # Entrenar RandomForest
        try:
            self.models['rf'].fit(X, y)
            rf_score = cross_val_score(self.models['rf'], X, y, cv=3, scoring='accuracy').mean()
            model_scores['rf'] = rf_score
            logger.info(f"✅ RandomForest: CV Score = {rf_score:.3f}")
        except Exception as e:
            logger.error(f"❌ Error entrenando RandomForest: {e}")
            model_scores['rf'] = 0.0
        
        # Entrenar XGBoost
        try:
            self.models['xgb'].fit(X, y)
            xgb_score = cross_val_score(self.models['xgb'], X, y, cv=3, scoring='accuracy').mean()
            model_scores['xgb'] = xgb_score
            logger.info(f"✅ XGBoost: CV Score = {xgb_score:.3f}")
        except Exception as e:
            logger.error(f"❌ Error entrenando XGBoost: {e}")
            model_scores['xgb'] = 0.0
        
        # Entrenar LSTM
        if TENSORFLOW_AVAILABLE and 'lstm' in self.models:
            try:
                lstm_success = self.models['lstm'].train(data, target_col)
                model_scores['lstm'] = 0.6 if lstm_success else 0.0
            except Exception as e:
                logger.error(f"❌ Error entrenando LSTM: {e}")
                model_scores['lstm'] = 0.0
        
        # Entrenar Transformer
        if TENSORFLOW_AVAILABLE and 'transformer' in self.models:
            try:
                transformer_success = self.models['transformer'].train(data, target_col)
                model_scores['transformer'] = 0.6 if transformer_success else 0.0
            except Exception as e:
                logger.error(f"❌ Error entrenando Transformer: {e}")
                model_scores['transformer'] = 0.0
        
        # Calcular pesos basados en performance
        total_score = sum(model_scores.values())
        if total_score > 0:
            self.weights = {model: score/total_score for model, score in model_scores.items()}
        else:
            # Pesos uniformes si no hay scores válidos
            num_models = len(model_scores)
            self.weights = {model: 1/num_models for model in model_scores.keys()}
        
        self.is_trained = True
        
        logger.info(f"🎯 Ensemble entrenado: {len(self.weights)} modelos")
        for model, weight in self.weights.items():
            logger.info(f"   • {model}: peso={weight:.3f}")
    
    def predict(self, data: pd.DataFrame) -> Optional[float]:
        """Predice combinando todos los modelos."""
        if not self.is_trained:
            return None
        
        predictions = {}
        
        # Predicciones de modelos tradicionales
        feature_cols = [col for col in data.columns if 'target' not in col and 'timestamp' not in col]
        X = data[feature_cols].tail(1)  # Última observación
        
        if 'rf' in self.models and self.weights.get('rf', 0) > 0:
            try:
                rf_pred = self.models['rf'].predict_proba(X)[0]
                # Convertir probabilidades a señal
                rf_signal = rf_pred[2] - rf_pred[0]  # BUY - SELL
                predictions['rf'] = rf_signal
            except:
                predictions['rf'] = 0.0
        
        if 'xgb' in self.models and self.weights.get('xgb', 0) > 0:
            try:
                xgb_pred = self.models['xgb'].predict_proba(X)[0]
                xgb_signal = xgb_pred[2] - xgb_pred[0]
                predictions['xgb'] = xgb_signal
            except:
                predictions['xgb'] = 0.0
        
        # Predicciones de modelos de deep learning
        if TENSORFLOW_AVAILABLE:
            if 'lstm' in self.models and self.weights.get('lstm', 0) > 0:
                lstm_pred = self.models['lstm'].predict(data)
                if lstm_pred is not None and len(lstm_pred) > 0:
                    predictions['lstm'] = lstm_pred[-1]
                else:
                    predictions['lstm'] = 0.0
            
            if 'transformer' in self.models and self.weights.get('transformer', 0) > 0:
                transformer_pred = self.models['transformer'].predict(data)
                if transformer_pred is not None and len(transformer_pred) > 0:
                    predictions['transformer'] = transformer_pred[-1]
                else:
                    predictions['transformer'] = 0.0
        
        # Combinar predicciones con pesos
        weighted_sum = 0.0
        total_weight = 0.0
        
        for model, prediction in predictions.items():
            weight = self.weights.get(model, 0)
            weighted_sum += prediction * weight
            total_weight += weight
        
        if total_weight > 0:
            final_prediction = weighted_sum / total_weight
            return final_prediction
        
        return 0.0
    
    def save_models(self, model_dir: str = "models"):
        """Guarda todos los modelos entrenados."""
        model_path = Path(model_dir)
        model_path.mkdir(exist_ok=True)
        
        try:
            # Guardar modelos tradicionales
            joblib.dump(self.models['rf'], model_path / "ensemble_rf.joblib")
            joblib.dump(self.models['xgb'], model_path / "ensemble_xgb.joblib")
            
            # Guardar configuración
            config = {
                'weights': self.weights,
                'is_trained': self.is_trained
            }
            joblib.dump(config, model_path / "ensemble_config.joblib")
            
            # Guardar modelos de deep learning
            if TENSORFLOW_AVAILABLE:
                if 'lstm' in self.models and self.models['lstm'].is_trained:
                    self.models['lstm'].model.save(model_path / "ensemble_lstm.h5")
                
                if 'transformer' in self.models and self.models['transformer'].is_trained:
                    self.models['transformer'].model.save(model_path / "ensemble_transformer.h5")
            
            logger.info(f"✅ Ensemble models guardados en {model_dir}")
            
        except Exception as e:
            logger.error(f"❌ Error guardando ensemble: {e}")


def auto_load_ml_models(model_dir: str = "models"):
    """
    Carga automáticamente todos los modelos ML disponibles al arrancar el bot.
    """
    logger.info("🔄 Cargando modelos ML automáticamente...")
    
    try:
        model_path = Path(model_dir)
        if not model_path.exists():
            logger.warning(f"⚠️ Directorio {model_dir} no existe - creando...")
            model_path.mkdir(parents=True, exist_ok=True)
            return False
        
        models_loaded = 0
        
        # 1. Cargar Ensemble Model si existe
        ensemble_config = model_path / "ensemble_config.joblib"
        if ensemble_config.exists():
            try:
                logger.info("📊 Cargando Ensemble Model...")
                config = joblib.load(ensemble_config)
                
                # Cargar RandomForest
                rf_file = model_path / "ensemble_rf.joblib"
                if rf_file.exists():
                    advanced_ensemble.models['rf'] = joblib.load(rf_file)
                    logger.info("   ✅ RandomForest cargado")
                    models_loaded += 1
                
                # Cargar XGBoost
                xgb_file = model_path / "ensemble_xgb.joblib"
                if xgb_file.exists():
                    advanced_ensemble.models['xgb'] = joblib.load(xgb_file)
                    logger.info("   ✅ XGBoost cargado")
                    models_loaded += 1
                
                # Cargar modelos de deep learning
                if TENSORFLOW_AVAILABLE:
                    lstm_file = model_path / "ensemble_lstm.h5"
                    if lstm_file.exists():
                        try:
                            advanced_ensemble.models['lstm'].model = tf.keras.models.load_model(str(lstm_file))
                            advanced_ensemble.models['lstm'].is_trained = True
                            logger.info("   ✅ LSTM cargado")
                            models_loaded += 1
                        except Exception as e:
                            logger.warning(f"⚠️ Error cargando LSTM: {e}")
                    
                    transformer_file = model_path / "ensemble_transformer.h5"
                    if transformer_file.exists():
                        try:
                            advanced_ensemble.models['transformer'].model = tf.keras.models.load_model(str(transformer_file))
                            advanced_ensemble.models['transformer'].is_trained = True
                            logger.info("   ✅ Transformer cargado")
                            models_loaded += 1
                        except Exception as e:
                            logger.warning(f"⚠️ Error cargando Transformer: {e}")
                
                # Configurar ensemble
                if models_loaded > 0:
                    advanced_ensemble.weights = config.get('weights', {})
                    advanced_ensemble.is_trained = config.get('is_trained', True)
                    
                    logger.info(f"🎯 Ensemble Model cargado: {models_loaded} modelos")
                    for model_name, weight in advanced_ensemble.weights.items():
                        logger.info(f"   • {model_name}: peso={weight:.3f}")
                        
            except Exception as e:
                logger.error(f"❌ Error cargando Ensemble: {e}")
        else:
            logger.info("ℹ️ Ensemble Model no encontrado - se entrenará cuando sea necesario")
        
        # 2. Cargar Reinforcement Learning
        try:
            from .reinforcement_learning import rl_trading_system
            rl_file = model_path / "rl_model.pkl" 
            if rl_file.exists():
                rl_data = joblib.load(rl_file)
                if rl_data.get('is_trained', False):
                    # Restaurar estado del RL
                    if hasattr(rl_trading_system, 'agent'):
                        rl_trading_system.agent = rl_data.get('agent')
                        rl_trading_system.is_trained = True
                        logger.info("🤖 Reinforcement Learning cargado exitosamente")
                        models_loaded += 1
                    else:
                        logger.warning("⚠️ RL encontrado pero no se puede cargar")
            else:
                logger.info("ℹ️ Reinforcement Learning no encontrado - se entrenará cuando sea necesario")
                
        except Exception as e:
            logger.warning(f"⚠️ Error cargando RL: {e}")
        
        # Resultado final
        if models_loaded > 0:
            logger.info(f"✅ Carga automática completada: {models_loaded} modelos ML cargados")
            return True
        else:
            logger.info("ℹ️ No hay modelos ML pre-entrenados - usando modelos base")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error en carga automática de modelos: {e}")
        return False


# Instancia global del ensemble
advanced_ensemble = EnsembleModel()