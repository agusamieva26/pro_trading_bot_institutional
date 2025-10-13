"""
🎯 AUTOMATED MODEL TRAINING & OPTIMIZATION SYSTEM
Institutional-grade automated training with hyperparameter optimization, walk-forward validation,
and comprehensive performance tracking for high-frequency trading ML models.

Features:
- Automated hyperparameter optimization using Optuna
- Walk-forward optimization for temporal stability
- Time series cross-validation
- Model performance tracking and comparison
- Online learning adaptation
- Production-ready training pipelines
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from datetime import datetime, timedelta
import joblib
import json
import warnings
from pathlib import Path
from dataclasses import dataclass, field
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import optuna
from optuna.samplers import TPESampler
from optuna.pruners import MedianPruner

# Suppress warnings for production
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=optuna.exceptions.ExperimentalWarning)

# ML Libraries
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, classification_report, confusion_matrix
from sklearn.preprocessing import StandardScaler, RobustScaler, LabelEncoder
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
import xgboost as xgb

# 🚀 FIX: Hacer que LightGBM sea opcional para evitar ModuleNotFoundError
try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    lgb = None
    logger.warning("⚠️ LightGBM not available - el modelo LightGBM será deshabilitado.")
    
# Deep Learning (conditional)
try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False

from .util import logger
from .feature_engineering import generate_features, FeatureConfig
from .predictive_analytics import PredictionTimeframe, PredictionDirection


@dataclass
class TrainingConfig:
    """Configuration for model training."""
    # Data parameters
    train_start_date: str = "2023-01-01"
    train_end_date: str = "2024-06-01"
    validation_start_date: str = "2024-06-01"  
    validation_end_date: str = "2024-09-01"
    test_start_date: str = "2024-09-01"
    test_end_date: str = "2024-12-01"
    
    # Training parameters
    target_column: str = "future_return_5m"
    prediction_horizon: int = 5  # minutes
    min_samples_per_class: int = 100
    max_features_per_model: int = 50
    
    # Optimization parameters
    n_trials: int = 200
    optimization_timeout: int = 3600  # 1 hour
    n_jobs: int = -1
    random_state: int = 42
    
    # Validation parameters
    cv_folds: int = 5
    walk_forward_periods: int = 10
    min_train_size: int = 1000
    
    # Performance thresholds
    min_accuracy: float = 0.55
    min_precision: float = 0.60
    min_recall: float = 0.50
    
    # Model selection
    enable_traditional_ml: bool = True
    enable_deep_learning: bool = TENSORFLOW_AVAILABLE
    enable_ensemble: bool = True


@dataclass
class ModelPerformance:
    """Performance metrics for a trained model."""
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    roc_auc: float = 0.0
    confusion_matrix: np.ndarray = None
    feature_importance: Dict[str, float] = field(default_factory=dict)
    cross_val_scores: List[float] = field(default_factory=list)
    training_time: float = 0.0
    prediction_time: float = 0.0
    model_size_mb: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'accuracy': float(self.accuracy),
            'precision': float(self.precision),
            'recall': float(self.recall),
            'f1_score': float(self.f1_score),
            'roc_auc': float(self.roc_auc),
            'confusion_matrix': self.confusion_matrix.tolist() if self.confusion_matrix is not None else None,
            'feature_importance': {k: float(v) for k, v in self.feature_importance.items()},
            'cross_val_scores': [float(x) for x in self.cross_val_scores],
            'training_time': float(self.training_time),
            'prediction_time': float(self.prediction_time),
            'model_size_mb': float(self.model_size_mb)
        }


@dataclass
class TrainingResult:
    """Result of a model training session."""
    model_name: str
    model_type: str
    performance: ModelPerformance
    hyperparameters: Dict[str, Any]
    training_date: datetime
    validation_performance: Dict[str, float]
    test_performance: Dict[str, float] = field(default_factory=dict)
    model_path: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'model_name': self.model_name,
            'model_type': self.model_type,
            'performance': self.performance.to_dict(),
            'hyperparameters': self.hyperparameters,
            'training_date': self.training_date.isoformat(),
            'validation_performance': self.validation_performance,
            'test_performance': self.test_performance,
            'model_path': self.model_path
        }


class HyperparameterOptimizer:
    """
    Advanced hyperparameter optimization using Optuna.
    """
    
    def __init__(self, config: TrainingConfig):
        self.config = config
        self.study_storage = None
        
    def optimize_random_forest(self, X_train: np.ndarray, y_train: np.ndarray,
                              X_val: np.ndarray, y_val: np.ndarray,
                              n_trials: int = 50) -> Dict[str, Any]:
        """Optimize Random Forest hyperparameters."""
        
        def objective(trial):
            params = {
                'n_estimators': trial.suggest_int('n_estimators', 50, 500),
                'max_depth': trial.suggest_int('max_depth', 3, 20),
                'min_samples_split': trial.suggest_int('min_samples_split', 2, 20),
                'min_samples_leaf': trial.suggest_int('min_samples_leaf', 1, 10),
                'max_features': trial.suggest_categorical('max_features', ['sqrt', 'log2', None]),
                'bootstrap': trial.suggest_categorical('bootstrap', [True, False]),
                'class_weight': trial.suggest_categorical('class_weight', ['balanced', None]),
                'random_state': self.config.random_state,
                'n_jobs': -1
            }
            
            model = RandomForestClassifier(**params)
            model.fit(X_train, y_train)
            
            y_pred = model.predict(X_val)
            accuracy = accuracy_score(y_val, y_pred)
            
            return accuracy
        
        study = optuna.create_study(
            direction='maximize',
            sampler=TPESampler(seed=self.config.random_state),
            pruner=MedianPruner()
        )
        
        study.optimize(objective, n_trials=n_trials)
        
        logger.info(f"✅ Random Forest optimization complete: best score = {study.best_value:.4f}")
        return study.best_params
    
    def optimize_xgboost(self, X_train: np.ndarray, y_train: np.ndarray,
                        X_val: np.ndarray, y_val: np.ndarray,
                        n_trials: int = 50) -> Dict[str, Any]:
        """Optimize XGBoost hyperparameters."""
        
        def objective(trial):
            params = {
                'n_estimators': trial.suggest_int('n_estimators', 50, 500),
                'max_depth': trial.suggest_int('max_depth', 3, 12),
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3),
                'subsample': trial.suggest_float('subsample', 0.6, 1.0),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
                'reg_alpha': trial.suggest_float('reg_alpha', 0, 10),
                'reg_lambda': trial.suggest_float('reg_lambda', 0, 10),
                'random_state': self.config.random_state,
                'n_jobs': -1,
                'eval_metric': 'mlogloss',
                'verbosity': 0
            }
            
            model = xgb.XGBClassifier(**params)
            model.fit(X_train, y_train)
            
            y_pred = model.predict(X_val)
            accuracy = accuracy_score(y_val, y_pred)
            
            return accuracy
        
        study = optuna.create_study(
            direction='maximize',
            sampler=TPESampler(seed=self.config.random_state),
            pruner=MedianPruner()
        )
        
        study.optimize(objective, n_trials=n_trials)
        
        logger.info(f"✅ XGBoost optimization complete: best score = {study.best_value:.4f}")
        return study.best_params
    
    def optimize_lightgbm(self, X_train: np.ndarray, y_train: np.ndarray,
                         X_val: np.ndarray, y_val: np.ndarray,
                         n_trials: int = 50) -> Dict[str, Any]:
        """Optimize LightGBM hyperparameters."""
        # 🚀 FIX: No intentar optimizar si LightGBM no está disponible
        if not LIGHTGBM_AVAILABLE:
            logger.warning("Skipping LightGBM optimization: library not found.")
            return {}
        
        def objective(trial):
            params = {
                'n_estimators': trial.suggest_int('n_estimators', 50, 500),
                'max_depth': trial.suggest_int('max_depth', 3, 12),
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3),
                'subsample': trial.suggest_float('subsample', 0.6, 1.0),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
                'reg_alpha': trial.suggest_float('reg_alpha', 0, 10),
                'reg_lambda': trial.suggest_float('reg_lambda', 0, 10),
                'num_leaves': trial.suggest_int('num_leaves', 10, 300),
                'min_child_samples': trial.suggest_int('min_child_samples', 5, 100),
                'random_state': self.config.random_state,
                'n_jobs': -1,
                'verbosity': -1
            }
            
            model = lgb.LGBMClassifier(**params)
            model.fit(X_train, y_train)
            
            y_pred = model.predict(X_val)
            accuracy = accuracy_score(y_val, y_pred)
            
            return accuracy
        
        study = optuna.create_study(
            direction='maximize',
            sampler=TPESampler(seed=self.config.random_state),
            pruner=MedianPruner()
        )
        
        study.optimize(objective, n_trials=n_trials)
        
        logger.info(f"✅ LightGBM optimization complete: best score = {study.best_value:.4f}")
        return study.best_params
    
    def optimize_lstm(self, X_train: np.ndarray, y_train: np.ndarray,
                     X_val: np.ndarray, y_val: np.ndarray,
                     n_trials: int = 30) -> Dict[str, Any]:
        """Optimize LSTM hyperparameters."""
        
        if not TENSORFLOW_AVAILABLE:
            return {}
        
        def objective(trial):
            params = {
                'lstm_units': trial.suggest_int('lstm_units', 32, 128),
                'dropout_rate': trial.suggest_float('dropout_rate', 0.1, 0.5),
                'learning_rate': trial.suggest_float('learning_rate', 0.0001, 0.01),
                'batch_size': trial.suggest_int('batch_size', 16, 64),
                'epochs': trial.suggest_int('epochs', 20, 100)
            }
            
            # Build LSTM model
            model = Sequential([
                LSTM(params['lstm_units'], return_sequences=False, 
                     input_shape=(X_train.shape[1], X_train.shape[2])),
                Dropout(params['dropout_rate']),
                Dense(32, activation='relu'),
                Dropout(params['dropout_rate']),
                Dense(len(np.unique(y_train)), activation='softmax')
            ])
            
            model.compile(
                optimizer=Adam(learning_rate=params['learning_rate']),
                loss='sparse_categorical_crossentropy',
                metrics=['accuracy']
            )
            
            # Early stopping
            callbacks = [EarlyStopping(patience=10, restore_best_weights=True)]
            
            # Train model
            model.fit(
                X_train, y_train,
                validation_data=(X_val, y_val),
                epochs=params['epochs'],
                batch_size=params['batch_size'],
                callbacks=callbacks,
                verbose=0
            )
            
            # Evaluate
            y_pred = np.argmax(model.predict(X_val, verbose=0), axis=1)
            accuracy = accuracy_score(y_val, y_pred)
            
            # Clean up
            del model
            tf.keras.backend.clear_session()
            
            return accuracy
        
        study = optuna.create_study(
            direction='maximize',
            sampler=TPESampler(seed=self.config.random_state)
        )
        
        study.optimize(objective, n_trials=n_trials)
        
        logger.info(f"✅ LSTM optimization complete: best score = {study.best_value:.4f}")
        return study.best_params


class WalkForwardValidator:
    """
    Walk-forward validation for time series models.
    """
    
    def __init__(self, config: TrainingConfig):
        self.config = config
        
    def validate(self, data: pd.DataFrame, model_builder: Callable,
                hyperparameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform walk-forward validation.
        
        Args:
            data: Time series data with features and target
            model_builder: Function to build model with hyperparameters
            hyperparameters: Model hyperparameters
            
        Returns:
            Validation results with performance metrics
        """
        try:
            # Prepare data
            feature_cols = [col for col in data.columns 
                           if not col.startswith('future_') and col not in ['timestamp', 'symbol']]
            X = data[feature_cols].fillna(0)
            y = self._prepare_target(data[self.config.target_column])
            
            # Time-based splits
            n_splits = self.config.walk_forward_periods
            min_train_size = self.config.min_train_size
            
            results = []
            
            # Walk-forward splits
            for i in range(n_splits):
                # Calculate split indices
                total_size = len(data)
                test_size = total_size // n_splits
                
                train_end = min_train_size + (i + 1) * test_size
                train_start = 0
                test_start = train_end
                test_end = min(test_start + test_size, total_size)
                
                if test_end >= total_size or train_end >= test_start:
                    break
                
                # Split data
                X_train = X.iloc[train_start:train_end]
                y_train = y[train_start:train_end]
                X_test = X.iloc[test_start:test_end]
                y_test = y[test_start:test_end]
                
                if len(X_train) < 100 or len(X_test) < 20:
                    continue
                
                # Scale features
                scaler = RobustScaler()
                X_train_scaled = scaler.fit_transform(X_train)
                X_test_scaled = scaler.transform(X_test)
                
                # Build and train model
                model = model_builder(hyperparameters)
                
                start_time = time.time()
                model.fit(X_train_scaled, y_train)
                training_time = time.time() - start_time
                
                # Predict
                start_time = time.time()
                y_pred = model.predict(X_test_scaled)
                prediction_time = time.time() - start_time
                
                # Calculate metrics
                accuracy = accuracy_score(y_test, y_pred)
                precision, recall, f1, _ = precision_recall_fscore_support(y_test, y_pred, average='weighted')
                
                results.append({
                    'fold': i,
                    'accuracy': accuracy,
                    'precision': precision,
                    'recall': recall,
                    'f1_score': f1,
                    'training_time': training_time,
                    'prediction_time': prediction_time,
                    'train_size': len(X_train),
                    'test_size': len(X_test)
                })
                
                logger.debug(f"Fold {i}: Accuracy={accuracy:.3f}, F1={f1:.3f}")
            
            if not results:
                return {}
            
            # Aggregate results
            aggregated = {
                'mean_accuracy': np.mean([r['accuracy'] for r in results]),
                'std_accuracy': np.std([r['accuracy'] for r in results]),
                'mean_precision': np.mean([r['precision'] for r in results]),
                'mean_recall': np.mean([r['recall'] for r in results]),
                'mean_f1_score': np.mean([r['f1_score'] for r in results]),
                'mean_training_time': np.mean([r['training_time'] for r in results]),
                'mean_prediction_time': np.mean([r['prediction_time'] for r in results]),
                'fold_results': results,
                'n_folds': len(results)
            }
            
            return aggregated
            
        except Exception as e:
            logger.error(f"❌ Walk-forward validation error: {e}")
            return {}
    
    def _prepare_target(self, target_series: pd.Series) -> np.ndarray:
        """Convert continuous target to classification labels."""
        # Convert returns to classes
        # < -0.5% = 0 (Strong Sell)
        # -0.5% to -0.1% = 1 (Sell)  
        # -0.1% to +0.1% = 2 (Hold)
        # +0.1% to +0.5% = 3 (Buy)
        # > +0.5% = 4 (Strong Buy)
        
        classes = []
        for val in target_series:
            if pd.isna(val):
                classes.append(2)  # Hold for NaN
            elif val < -0.005:
                classes.append(0)
            elif val < -0.001:
                classes.append(1)
            elif val > 0.005:
                classes.append(4)
            elif val > 0.001:
                classes.append(3)
            else:
                classes.append(2)
        
        return np.array(classes)


class ModelTrainer:
    """
    Main model training orchestrator with advanced optimization and validation.
    """
    
    def __init__(self, config: Optional[TrainingConfig] = None):
        """Initialize model trainer."""
        self.config = config or TrainingConfig()
        self.optimizer = HyperparameterOptimizer(self.config)
        self.validator = WalkForwardValidator(self.config)
        
        # Training history
        self.training_history = []
        self.best_models = {}
        
        # Thread safety
        self._training_lock = threading.Lock()
        
        logger.info("🎯 Model Training System initialized")
    
    def train_all_models(self, data: Dict[str, pd.DataFrame]) -> Dict[str, TrainingResult]:
        """
        Train all models with comprehensive optimization and validation.
        
        Args:
            data: Dictionary mapping symbols to feature DataFrames
            
        Returns:
            Dictionary of trained models and their results
        """
        try:
            logger.info("🔄 Starting comprehensive model training...")
            
            # Combine data from all symbols
            combined_data = self._prepare_training_data(data)
            
            if combined_data.empty:
                logger.error("❌ No training data available")
                return {}
            
            logger.info(f"📊 Training on {len(combined_data)} samples from {len(data)} symbols")
            
            # Split data
            train_data, val_data, test_data = self._split_data(combined_data)
            
            # Prepare features and targets
            X_train, y_train = self._prepare_features_target(train_data)
            X_val, y_val = self._prepare_features_target(val_data)
            X_test, y_test = self._prepare_features_target(test_data)
            
            if len(X_train) == 0:
                logger.error("❌ No valid training features")
                return {}
            
            # Scale features
            scaler = RobustScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_val_scaled = scaler.transform(X_val)
            X_test_scaled = scaler.transform(X_test)
            
            results = {}
            
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {}
                
                # Traditional ML models
                if self.config.enable_traditional_ml:
                    futures['random_forest'] = executor.submit(
                        self._train_random_forest, X_train_scaled, y_train, X_val_scaled, y_val, X_test_scaled, y_test)
                    
                    futures['xgboost'] = executor.submit(
                        self._train_xgboost, X_train_scaled, y_train, X_val_scaled, y_val, X_test_scaled, y_test)
                    
                    futures['lightgbm'] = executor.submit(
                        self._train_lightgbm, X_train_scaled, y_train, X_val_scaled, y_val, X_test_scaled, y_test)
                
                # Collect results
                for model_name, future in futures.items():
                    try:
                        result = future.result()
                        if result:
                            results[model_name] = result
                            logger.info(f"✅ {model_name} training complete: Accuracy={result.performance.accuracy:.3f}")
                    except Exception as e:
                        logger.error(f"❌ {model_name} training failed: {e}")
            
            # Deep learning models (sequential due to GPU memory)
            if self.config.enable_deep_learning and TENSORFLOW_AVAILABLE:
                lstm_result = self._train_lstm(train_data, val_data, test_data)
                if lstm_result:
                    results['lstm'] = lstm_result
                    logger.info(f"✅ LSTM training complete: Accuracy={lstm_result.performance.accuracy:.3f}")
            
            # Save best models
            self._save_training_results(results)
            
            logger.info(f"🎯 Training complete: {len(results)} models trained successfully")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Model training failed: {e}")
            return {}
    
    def _prepare_training_data(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Prepare and combine training data from multiple symbols."""
        try:
            combined_data = []
            
            for symbol, df in data.items():
                if df.empty or len(df) < 100:
                    continue
                
                # Generate features if not already present
                if 'future_return_5m' not in df.columns:
                    df = generate_features(df, symbol, include_target=True)
                
                if not df.empty:
                    df['symbol'] = symbol
                    combined_data.append(df)
            
            if not combined_data:
                return pd.DataFrame()
            
            # Combine all data
            result = pd.concat(combined_data, ignore_index=True)
            
            # Remove rows with missing target
            result = result.dropna(subset=[self.config.target_column])
            
            # Balance classes if needed
            result = self._balance_classes(result)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Training data preparation error: {e}")
            return pd.DataFrame()
    
    def _balance_classes(self, data: pd.DataFrame) -> pd.DataFrame:
        """Balance classes in the dataset."""
        try:
            target_col = self.config.target_column
            
            # Convert to classes
            y_classes = self.validator._prepare_target(data[target_col])
            data['target_class'] = y_classes
            
            # Check class distribution
            class_counts = pd.Series(y_classes).value_counts()
            min_samples = self.config.min_samples_per_class
            
            # Filter out classes with too few samples
            valid_classes = class_counts[class_counts >= min_samples].index
            data = data[data['target_class'].isin(valid_classes)]
            
            # Balance classes by undersampling majority classes
            balanced_data = []
            max_samples_per_class = class_counts.min() * 2  # Allow some imbalance
            
            for class_label in valid_classes:
                class_data = data[data['target_class'] == class_label]
                if len(class_data) > max_samples_per_class:
                    class_data = class_data.sample(n=max_samples_per_class, random_state=self.config.random_state)
                balanced_data.append(class_data)
            
            result = pd.concat(balanced_data, ignore_index=True)
            result = result.drop('target_class', axis=1)
            
            logger.info(f"📊 Class balancing: {len(data)} -> {len(result)} samples")
            
            return result
            
        except Exception as e:
            logger.warning(f"⚠️ Class balancing error: {e}")
            return data
    
    def _split_data(self, data: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Split data into train/validation/test sets temporally."""
        try:
            # Sort by timestamp if available
            if 'timestamp' in data.columns:
                data = data.sort_values('timestamp')
            else:
                # If no timestamp, assume data is already sorted
                data = data.reset_index(drop=True)
            
            # Time-based splits (70% train, 20% validation, 10% test)
            total_size = len(data)
            train_size = int(total_size * 0.7)
            val_size = int(total_size * 0.2)
            
            train_data = data.iloc[:train_size]
            val_data = data.iloc[train_size:train_size + val_size]
            test_data = data.iloc[train_size + val_size:]
            
            logger.info(f"📊 Data split: Train={len(train_data)}, Val={len(val_data)}, Test={len(test_data)}")
            
            return train_data, val_data, test_data
            
        except Exception as e:
            logger.error(f"❌ Data splitting error: {e}")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    def _prepare_features_target(self, data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare features and target arrays."""
        try:
            # Select feature columns
            feature_cols = [col for col in data.columns
                           if not col.startswith('future_') and
                              col not in ['timestamp', 'symbol', self.config.target_column, 'target_class']]
            
            # 🎯 ADVANCED FEATURE SELECTION: Use feature importance to select the best features
            if len(feature_cols) > self.config.max_features_per_model:
                logger.info(f"🔬 Performing feature selection: {len(feature_cols)} -> {self.config.max_features_per_model}")
                
                # Use a temporary, fast model to get feature importances
                temp_model = RandomForestClassifier(n_estimators=50, random_state=self.config.random_state, n_jobs=-1)
                temp_X = data[feature_cols].fillna(0)
                temp_y = self.validator._prepare_target(data[self.config.target_column])
                
                temp_model.fit(temp_X, temp_y)
                
                # Create a series of feature importances and select the top N
                importances = pd.Series(temp_model.feature_importances_, index=feature_cols)
                top_features = importances.nlargest(self.config.max_features_per_model).index.tolist()
                feature_cols = top_features
                logger.info(f"✅ Top features selected: {feature_cols[:5]}...")
            
            X = data[feature_cols].fillna(0).values
            y = self.validator._prepare_target(data[self.config.target_column])
            
            return X, y
            
        except Exception as e:
            logger.error(f"❌ Feature/target preparation error: {e}")
            return np.array([]), np.array([])
    
    def _train_random_forest(self, X_train: np.ndarray, y_train: np.ndarray,
                            X_val: np.ndarray, y_val: np.ndarray,
                            X_test: np.ndarray, y_test: np.ndarray) -> Optional[TrainingResult]:
        """Train Random Forest with optimization."""
        try:
            logger.info("🌲 Training Random Forest...")
            
            # Hyperparameter optimization
            best_params = self.optimizer.optimize_random_forest(X_train, y_train, X_val, y_val, n_trials=50)
            
            # Train final model
            model = RandomForestClassifier(**best_params)
            
            start_time = time.time()
            model.fit(X_train, y_train)
            training_time = time.time() - start_time
            
            # Evaluate
            performance = self._evaluate_model(model, X_test, y_test, training_time)
            
            # Cross-validation
            cv_scores = cross_val_score(model, X_train, y_train, cv=TimeSeriesSplit(n_splits=5))
            performance.cross_val_scores = cv_scores.tolist()
            
            # Feature importance
            if hasattr(model, 'feature_importances_'):
                performance.feature_importance = dict(enumerate(model.feature_importances_))
            
            # Model size
            import sys
            performance.model_size_mb = sys.getsizeof(model) / (1024 * 1024)
            
            return TrainingResult(
                model_name="random_forest",
                model_type="RandomForestClassifier",
                performance=performance,
                hyperparameters=best_params,
                training_date=datetime.now(),
                validation_performance={'accuracy': performance.accuracy},
                model_path=f"models/random_forest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.joblib"
            )
            
        except Exception as e:
            logger.error(f"❌ Random Forest training error: {e}")
            return None
    
    def _train_xgboost(self, X_train: np.ndarray, y_train: np.ndarray,
                      X_val: np.ndarray, y_val: np.ndarray,
                      X_test: np.ndarray, y_test: np.ndarray) -> Optional[TrainingResult]:
        """Train XGBoost with optimization."""
        try:
            logger.info("🚀 Training XGBoost...")
            
            # Hyperparameter optimization
            best_params = self.optimizer.optimize_xgboost(X_train, y_train, X_val, y_val, n_trials=50)
            
            # Train final model
            model = xgb.XGBClassifier(**best_params)
            
            start_time = time.time()
            model.fit(X_train, y_train)
            training_time = time.time() - start_time
            
            # Evaluate
            performance = self._evaluate_model(model, X_test, y_test, training_time)
            
            # Cross-validation
            cv_scores = cross_val_score(model, X_train, y_train, cv=TimeSeriesSplit(n_splits=5))
            performance.cross_val_scores = cv_scores.tolist()
            
            # Feature importance
            if hasattr(model, 'feature_importances_'):
                performance.feature_importance = dict(enumerate(model.feature_importances_))
            
            return TrainingResult(
                model_name="xgboost",
                model_type="XGBClassifier", 
                performance=performance,
                hyperparameters=best_params,
                training_date=datetime.now(),
                validation_performance={'accuracy': performance.accuracy},
                model_path=f"models/xgboost_{datetime.now().strftime('%Y%m%d_%H%M%S')}.joblib"
            )
            
        except Exception as e:
            logger.error(f"❌ XGBoost training error: {e}")
            return None
    
    def _train_lightgbm(self, X_train: np.ndarray, y_train: np.ndarray,
                       X_val: np.ndarray, y_val: np.ndarray,
                       X_test: np.ndarray, y_test: np.ndarray) -> Optional[TrainingResult]:
        """Train LightGBM with optimization."""
        # 🚀 FIX: No intentar entrenar si LightGBM no está disponible
        if not LIGHTGBM_AVAILABLE:
            return None
            
        try:
            logger.info("💡 Training LightGBM...")
            
            # Hyperparameter optimization
            best_params = self.optimizer.optimize_lightgbm(X_train, y_train, X_val, y_val, n_trials=50)
            
            # Train final model
            model = lgb.LGBMClassifier(**best_params)
            
            start_time = time.time()
            model.fit(X_train, y_train)
            training_time = time.time() - start_time
            
            # Evaluate
            performance = self._evaluate_model(model, X_test, y_test, training_time)
            
            # Cross-validation
            cv_scores = cross_val_score(model, X_train, y_train, cv=TimeSeriesSplit(n_splits=5))
            performance.cross_val_scores = cv_scores.tolist()
            
            # Feature importance
            if hasattr(model, 'feature_importances_'):
                performance.feature_importance = dict(enumerate(model.feature_importances_))
            
            return TrainingResult(
                model_name="lightgbm",
                model_type="LGBMClassifier",
                performance=performance,
                hyperparameters=best_params,
                training_date=datetime.now(),
                validation_performance={'accuracy': performance.accuracy},
                model_path=f"models/lightgbm_{datetime.now().strftime('%Y%m%d_%H%M%S')}.joblib"
            )
            
        except Exception as e:
            logger.error(f"❌ LightGBM training error: {e}")
            return None
    
    def _train_lstm(self, train_data: pd.DataFrame, val_data: pd.DataFrame,
                   test_data: pd.DataFrame) -> Optional[TrainingResult]:
        """Train LSTM with optimization."""
        if not TENSORFLOW_AVAILABLE:
            return None
            
        try:
            logger.info("🧠 Training LSTM...")
            
            # Prepare sequence data for LSTM
            sequence_length = 30
            X_train, y_train = self._prepare_lstm_data(train_data, sequence_length)
            X_val, y_val = self._prepare_lstm_data(val_data, sequence_length)
            X_test, y_test = self._prepare_lstm_data(test_data, sequence_length)
            
            if len(X_train) == 0:
                logger.warning("⚠️ Insufficient data for LSTM")
                return None
            
            # Hyperparameter optimization
            best_params = self.optimizer.optimize_lstm(X_train, y_train, X_val, y_val, n_trials=20)
            
            if not best_params:
                # Use default parameters
                best_params = {
                    'lstm_units': 64,
                    'dropout_rate': 0.2,
                    'learning_rate': 0.001,
                    'batch_size': 32,
                    'epochs': 50
                }
            
            # Build final model
            model = Sequential([
                LSTM(best_params['lstm_units'], return_sequences=False,
                     input_shape=(X_train.shape[1], X_train.shape[2])),
                Dropout(best_params['dropout_rate']),
                Dense(32, activation='relu'),
                Dropout(best_params['dropout_rate']),
                Dense(len(np.unique(y_train)), activation='softmax')
            ])
            
            model.compile(
                optimizer=Adam(learning_rate=best_params['learning_rate']),
                loss='sparse_categorical_crossentropy',
                metrics=['accuracy']
            )
            
            # Train model
            callbacks = [
                EarlyStopping(patience=15, restore_best_weights=True),
                ReduceLROnPlateau(factor=0.5, patience=8)
            ]
            
            start_time = time.time()
            history = model.fit(
                X_train, y_train,
                validation_data=(X_val, y_val),
                epochs=best_params['epochs'],
                batch_size=best_params['batch_size'],
                callbacks=callbacks,
                verbose=0
            )
            training_time = time.time() - start_time
            
            # Evaluate
            y_pred = np.argmax(model.predict(X_test, verbose=0), axis=1)
            
            accuracy = accuracy_score(y_test, y_pred)
            precision, recall, f1, _ = precision_recall_fscore_support(y_test, y_pred, average='weighted')
            conf_matrix = confusion_matrix(y_test, y_pred)
            
            performance = ModelPerformance(
                accuracy=accuracy,
                precision=precision,
                recall=recall,
                f1_score=f1,
                confusion_matrix=conf_matrix,
                training_time=training_time,
                prediction_time=0.1  # Estimated
            )
            
            return TrainingResult(
                model_name="lstm",
                model_type="LSTM",
                performance=performance,
                hyperparameters=best_params,
                training_date=datetime.now(),
                validation_performance={'accuracy': accuracy},
                model_path=f"models/lstm_{datetime.now().strftime('%Y%m%d_%H%M%S')}.h5"
            )
            
        except Exception as e:
            logger.error(f"❌ LSTM training error: {e}")
            return None
    
    def _prepare_lstm_data(self, data: pd.DataFrame, sequence_length: int) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare sequence data for LSTM."""
        try:
            if len(data) < sequence_length:
                return np.array([]), np.array([])
            
            # Select features
            feature_cols = [col for col in data.columns 
                           if not col.startswith('future_') and 
                              col not in ['timestamp', 'symbol', self.config.target_column]]
            
            X_data = data[feature_cols].fillna(0).values
            y_data = self.validator._prepare_target(data[self.config.target_column])
            
            # Create sequences
            X_sequences = []
            y_sequences = []
            
            for i in range(sequence_length, len(X_data)):
                X_sequences.append(X_data[i-sequence_length:i])
                y_sequences.append(y_data[i])
            
            return np.array(X_sequences), np.array(y_sequences)
            
        except Exception as e:
            logger.error(f"❌ LSTM data preparation error: {e}")
            return np.array([]), np.array([])
    
    def _evaluate_model(self, model: Any, X_test: np.ndarray, y_test: np.ndarray,
                       training_time: float) -> ModelPerformance:
        """Evaluate model performance."""
        start_time = time.time()
        y_pred = model.predict(X_test)
        prediction_time = time.time() - start_time
        
        accuracy = accuracy_score(y_test, y_pred)
        precision, recall, f1, _ = precision_recall_fscore_support(y_test, y_pred, average='weighted')
        conf_matrix = confusion_matrix(y_test, y_pred)
        
        return ModelPerformance(
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1,
            confusion_matrix=conf_matrix,
            training_time=training_time,
            prediction_time=prediction_time
        )
    
    def _save_training_results(self, results: Dict[str, TrainingResult]):
        """Save training results and models."""
        try:
            models_dir = Path("models/trained_models")
            models_dir.mkdir(parents=True, exist_ok=True)

            for model_name, result in results.items():
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                base_filename = f"{model_name}_{timestamp}"

                # 🚀 FIX: Actualizar la ruta del modelo en el resultado para que coincida con el nuevo nombre
                model_extension = ".h5" if model_name == "lstm" else ".joblib"
                model_path = models_dir / f"{base_filename}{model_extension}"
                result.model_path = str(model_path)

                # Guardar metadatos del resultado
                result_file = models_dir / f"{base_filename}_result.json"
                with open(result_file, 'w') as f:
                    json.dump(result.to_dict(), f, indent=2, default=str)

                # Actualizar el mejor modelo si este es superior
                if (model_name not in self.best_models or
                        result.performance.accuracy > self.best_models[model_name].performance.accuracy):
                    self.best_models[model_name] = result

            # 🚀 FIX: Guardar un resumen de los mejores modelos para la limpieza inteligente
            best_models_file = models_dir / "best_models_summary.json"
            best_summary = {}
            if self.best_models:
                best_summary = {
                    name: res.to_dict()
                    for name, res in self.best_models.items()
                }

            with open(best_models_file, 'w') as f:
                json.dump(best_summary, f, indent=2, default=str)

            # Add to training history
            self.training_history.append({
                'timestamp': datetime.now().isoformat(),
                'models_trained': list(results.keys()),
                'best_accuracy': max(
                    (r.performance.accuracy for r in results.values() if r and r.performance), 
                    default=0.0
                ),
                'training_summary': {name: {
                    'accuracy': result.performance.accuracy,
                    'f1_score': result.performance.f1_score
                } for name, result in results.items()}
            })
            
            logger.info(f"✅ Training results saved to {models_dir}")

        except Exception as e:
            logger.error(f"❌ Error saving training results: {e}")
    
    def get_best_model(self, metric: str = 'accuracy') -> Optional[TrainingResult]:
        """Get the best model based on specified metric."""
        if not self.best_models:
            return None
        
        metric_values = {}
        for name, result in self.best_models.items():
            if metric == 'accuracy':
                metric_values[name] = result.performance.accuracy
            elif metric == 'f1_score':
                metric_values[name] = result.performance.f1_score
            elif metric == 'precision':
                metric_values[name] = result.performance.precision
            elif metric == 'recall':
                metric_values[name] = result.performance.recall
        
        if metric_values:
            best_model_name = max(metric_values, key=metric_values.get)
            return self.best_models[best_model_name]
        
        return None
    
    def get_training_summary(self) -> Dict[str, Any]:
        """Get comprehensive training summary."""
        summary = {
            'total_training_sessions': len(self.training_history),
            'best_models_count': len(self.best_models),
            'training_history': self.training_history[-10:],  # Last 10 sessions
            'config': {
                'min_accuracy': self.config.min_accuracy,
                'optimization_trials': self.config.n_trials,
                'cv_folds': self.config.cv_folds,
                'walk_forward_periods': self.config.walk_forward_periods
            }
        }
        
        if self.best_models:
            summary['best_models'] = {
                name: {
                    'accuracy': result.performance.accuracy,
                    'f1_score': result.performance.f1_score,
                    'training_date': result.training_date.isoformat(),
                    'model_type': result.model_type
                }
                for name, result in self.best_models.items()
            }
        
        return summary


# Global instance
model_trainer = ModelTrainer()


def train_models(data: Dict[str, pd.DataFrame], 
                config: Optional[TrainingConfig] = None) -> Dict[str, TrainingResult]:
    """Convenient function to train all models."""
    if config:
        trainer = ModelTrainer(config)
    else:
        trainer = model_trainer
        
    return trainer.train_all_models(data)


def get_best_model(metric: str = 'accuracy') -> Optional[TrainingResult]:
    """Get the best trained model."""
    return model_trainer.get_best_model(metric)


def get_training_summary() -> Dict[str, Any]:
    """Get training summary."""
    return model_trainer.get_training_summary()
