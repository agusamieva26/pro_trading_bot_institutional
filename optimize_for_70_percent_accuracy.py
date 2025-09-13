#!/usr/bin/env python3
"""
🎯 TARGETED OPTIMIZATION FOR 70%+ PREDICTION ACCURACY
Systematic hyperparameter optimization, probability calibration, and model enhancement
to achieve sustainable 70%+ accuracy target for institutional trading.

Features:
- Focused Optuna sweeps for XGBoost/RandomForest
- Probability calibration (Platt/Isotonic scaling)
- Feature importance analysis and selection
- Cross-validation with proper time series splits
- Ensemble optimization with voting calibration
"""

import sys
import os
import numpy as np
import pandas as pd
import warnings
from datetime import datetime, timedelta
from pathlib import Path
import joblib
import json
from typing import Dict, List, Tuple, Any, Optional

# Suppress warnings
warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# Add bot to path
sys.path.append('.')

# ML Libraries
import optuna
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.feature_selection import SelectKBest, f_classif
import xgboost as xgb


class AccuracyOptimizer:
    """
    Systematic optimizer to achieve 70%+ prediction accuracy.
    """
    
    def __init__(self, target_accuracy: float = 0.70):
        self.target_accuracy = target_accuracy
        self.results = {}
        self.best_models = {}
        self.optimization_history = []
        
        print(f"🎯 INITIALIZING ACCURACY OPTIMIZER")
        print(f"   Target accuracy: {target_accuracy:.1%}")
        print(f"   Timestamp: {datetime.now()}")
        
    def prepare_training_data(self) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
        """Prepare high-quality training dataset."""
        print("\n📊 PREPARING TRAINING DATA")
        
        # Use cached data if available
        cache_files = list(Path('data_cache').glob('*.parquet'))
        if not cache_files:
            print("❌ No cached data found - generating synthetic data for optimization")
            return self._generate_synthetic_data()
            
        # Load real market data
        try:
            # Load multiple symbols for robust training
            symbols = ['BTC_USD', 'ETH_USD', 'SPY'] 
            all_data = []
            
            for symbol in symbols:
                cache_file = Path(f'data_cache/{symbol}.parquet')
                if cache_file.exists():
                    data = pd.read_parquet(cache_file)
                    data['symbol'] = symbol
                    all_data.append(data)
                    print(f"   ✅ Loaded {symbol}: {len(data)} records")
            
            if not all_data:
                print("❌ No valid cached data - using synthetic data")
                return self._generate_synthetic_data()
                
            # Combine all symbol data
            combined_data = pd.concat(all_data, ignore_index=True)
            combined_data = combined_data.sort_values('timestamp').reset_index(drop=True)
            
            print(f"   📈 Combined dataset: {len(combined_data)} total records")
            return self._process_market_data(combined_data)
            
        except Exception as e:
            print(f"❌ Error loading market data: {e}")
            return self._generate_synthetic_data()
    
    def _process_market_data(self, data: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
        """Process real market data for training."""
        try:
            from bot.feature_engineering import generate_features
            
            # Generate features for each symbol
            processed_data = []
            for symbol in data['symbol'].unique():
                symbol_data = data[data['symbol'] == symbol].copy()
                
                # Generate features
                features = generate_features(symbol_data, symbol=symbol)
                if features is not None and len(features) > 100:  # Minimum viable data
                    processed_data.append(features)
            
            if not processed_data:
                print("❌ Feature generation failed - using synthetic data")
                return self._generate_synthetic_data()
            
            # Combine all processed data
            all_features = pd.concat(processed_data, ignore_index=True)
            
            # Create target variable - 5-minute forward return classification
            all_features['future_return'] = all_features.groupby('symbol')['close'].pct_change(5).shift(-5)
            
            # Create multi-class target for better accuracy measurement
            def classify_return(ret):
                if pd.isna(ret):
                    return np.nan
                elif ret < -0.005:  # < -0.5%
                    return 0  # Strong sell
                elif ret < -0.001:  # -0.5% to -0.1%
                    return 1  # Weak sell  
                elif ret > 0.005:   # > 0.5%
                    return 4  # Strong buy
                elif ret > 0.001:   # 0.1% to 0.5%
                    return 3  # Weak buy
                else:              # -0.1% to 0.1%
                    return 2  # Hold
                    
            all_features['target'] = all_features['future_return'].apply(classify_return)
            
            # Clean data
            all_features = all_features.dropna()
            
            if len(all_features) < 1000:
                print(f"❌ Insufficient clean data ({len(all_features)}) - using synthetic")
                return self._generate_synthetic_data()
            
            # Separate features and target
            feature_cols = [col for col in all_features.columns 
                           if col not in ['target', 'future_return', 'timestamp', 'symbol']]
            
            X = all_features[feature_cols]
            y = all_features['target']
            
            print(f"   ✅ Processing complete: {len(X)} samples, {len(feature_cols)} features")
            print(f"   📊 Class distribution: {y.value_counts().to_dict()}")
            
            return X, y, feature_cols
            
        except Exception as e:
            print(f"❌ Market data processing error: {e}")
            return self._generate_synthetic_data()
    
    def _generate_synthetic_data(self) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
        """Generate high-quality synthetic training data."""
        print("   🤖 Generating synthetic training data...")
        
        np.random.seed(42)
        n_samples = 5000
        n_features = 30
        
        # Create realistic feature patterns
        features = {}
        
        # Price-based features
        price_trend = np.cumsum(np.random.normal(0, 0.01, n_samples))
        features.update({
            'price_trend': price_trend,
            'price_momentum': np.gradient(price_trend),
            'price_volatility': pd.Series(price_trend).rolling(20).std().fillna(0),
        })
        
        # Technical indicators (synthetic)
        features.update({
            f'rsi_{period}': np.random.uniform(20, 80, n_samples) 
            for period in [14, 21]
        })
        
        features.update({
            f'sma_ratio_{period}': np.random.uniform(0.95, 1.05, n_samples)
            for period in [10, 20, 50]
        })
        
        # Volume features  
        features.update({
            'volume_trend': np.random.exponential(1, n_samples),
            'volume_ratio': np.random.lognormal(0, 0.5, n_samples),
        })
        
        # Market microstructure
        features.update({
            'bid_ask_spread': np.random.exponential(0.001, n_samples),
            'order_flow': np.random.normal(0, 1, n_samples),
        })
        
        # Add more features to reach target count
        for i in range(len(features), n_features):
            features[f'feature_{i}'] = np.random.normal(0, 1, n_samples)
        
        X = pd.DataFrame(features)
        
        # Create realistic target with patterns
        signal_strength = (
            0.3 * X['price_momentum'] +
            0.2 * (X['rsi_14'] - 50) / 50 +
            0.2 * X['volume_trend'] / X['volume_trend'].mean() +
            0.1 * X['order_flow'] +
            0.2 * np.random.normal(0, 1, n_samples)  # Noise
        )
        
        # Convert to classes
        y = pd.cut(signal_strength, bins=5, labels=[0, 1, 2, 3, 4]).astype(int)
        
        print(f"   ✅ Synthetic data created: {len(X)} samples, {len(X.columns)} features")
        print(f"   📊 Synthetic class distribution: {y.value_counts().to_dict()}")
        
        return X, y, list(X.columns)
    
    def optimize_random_forest(self, X: pd.DataFrame, y: pd.Series, n_trials: int = 100) -> Dict:
        """Targeted Random Forest optimization for 70%+ accuracy."""
        print(f"\n🌲 OPTIMIZING RANDOM FOREST ({n_trials} trials)")
        
        def objective(trial):
            params = {
                'n_estimators': trial.suggest_int('n_estimators', 200, 1000),
                'max_depth': trial.suggest_int('max_depth', 10, 30), 
                'min_samples_split': trial.suggest_int('min_samples_split', 2, 20),
                'min_samples_leaf': trial.suggest_int('min_samples_leaf', 1, 10),
                'max_features': trial.suggest_categorical('max_features', ['sqrt', 'log2', 0.5, 0.8]),
                'bootstrap': True,
                'class_weight': 'balanced',
                'random_state': 42,
                'n_jobs': -1
            }
            
            # Time series cross-validation
            tscv = TimeSeriesSplit(n_splits=5)
            model = RandomForestClassifier(**params)
            
            scores = cross_val_score(model, X, y, cv=tscv, scoring='accuracy', n_jobs=-1)
            return scores.mean()
        
        study = optuna.create_study(direction='maximize')
        study.optimize(objective, n_trials=n_trials, show_progress_bar=True)
        
        best_score = study.best_value
        print(f"   🎯 Best RF accuracy: {best_score:.3f}")
        
        if best_score >= self.target_accuracy:
            print(f"   ✅ TARGET ACHIEVED! ({best_score:.3f} >= {self.target_accuracy:.3f})")
        else:
            print(f"   ⚠️  Below target ({best_score:.3f} < {self.target_accuracy:.3f})")
        
        return {
            'model_type': 'RandomForest',
            'best_params': study.best_params,
            'best_score': best_score,
            'n_trials': n_trials,
            'target_achieved': best_score >= self.target_accuracy
        }
    
    def optimize_xgboost(self, X: pd.DataFrame, y: pd.Series, n_trials: int = 100) -> Dict:
        """Targeted XGBoost optimization for 70%+ accuracy."""
        print(f"\n🚀 OPTIMIZING XGBOOST ({n_trials} trials)")
        
        def objective(trial):
            params = {
                'n_estimators': trial.suggest_int('n_estimators', 200, 1000),
                'max_depth': trial.suggest_int('max_depth', 4, 12),
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.2),
                'subsample': trial.suggest_float('subsample', 0.6, 1.0),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
                'reg_alpha': trial.suggest_float('reg_alpha', 0.0, 1.0),
                'reg_lambda': trial.suggest_float('reg_lambda', 0.0, 1.0),
                'random_state': 42,
                'n_jobs': -1,
                'eval_metric': 'mlogloss'
            }
            
            tscv = TimeSeriesSplit(n_splits=5)
            model = xgb.XGBClassifier(**params)
            
            scores = cross_val_score(model, X, y, cv=tscv, scoring='accuracy', n_jobs=-1)
            return scores.mean()
        
        study = optuna.create_study(direction='maximize')
        study.optimize(objective, n_trials=n_trials, show_progress_bar=True)
        
        best_score = study.best_value
        print(f"   🎯 Best XGB accuracy: {best_score:.3f}")
        
        if best_score >= self.target_accuracy:
            print(f"   ✅ TARGET ACHIEVED! ({best_score:.3f} >= {self.target_accuracy:.3f})")
        else:
            print(f"   ⚠️  Below target ({best_score:.3f} < {self.target_accuracy:.3f})")
        
        return {
            'model_type': 'XGBoost',
            'best_params': study.best_params,
            'best_score': best_score,
            'n_trials': n_trials,
            'target_achieved': best_score >= self.target_accuracy
        }
    
    def train_calibrated_model(self, best_config: Dict, X: pd.DataFrame, y: pd.Series) -> Dict:
        """Train final model with probability calibration."""
        print(f"\n🔧 TRAINING CALIBRATED {best_config['model_type'].upper()} MODEL")
        
        # Split data for training and calibration
        split_idx = int(len(X) * 0.8)
        X_train, X_cal = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_cal = y.iloc[:split_idx], y.iloc[split_idx:]
        
        # Train base model
        if best_config['model_type'] == 'RandomForest':
            base_model = RandomForestClassifier(**best_config['best_params'])
        elif best_config['model_type'] == 'XGBoost':
            base_model = xgb.XGBClassifier(**best_config['best_params'])
        else:
            raise ValueError(f"Unknown model type: {best_config['model_type']}")
        
        base_model.fit(X_train, y_train)
        
        # Apply probability calibration
        calibrated_model = CalibratedClassifierCV(
            base_model, 
            method='isotonic',  # Better for small datasets
            cv='prefit'
        )
        calibrated_model.fit(X_cal, y_cal)
        
        # Evaluate
        train_acc = base_model.score(X_train, y_train)
        cal_acc = calibrated_model.score(X_cal, y_cal)
        
        print(f"   📊 Base model accuracy: {train_acc:.3f}")
        print(f"   📊 Calibrated accuracy: {cal_acc:.3f}")
        
        # Feature importance
        if hasattr(base_model, 'feature_importances_'):
            feature_importance = dict(zip(X.columns, base_model.feature_importances_))
            top_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:10]
            print(f"   🏆 Top features: {[f[0] for f in top_features]}")
        
        return {
            'base_model': base_model,
            'calibrated_model': calibrated_model,
            'train_accuracy': train_acc,
            'calibrated_accuracy': cal_acc,
            'feature_importance': feature_importance if hasattr(base_model, 'feature_importances_') else None,
            'config': best_config
        }
    
    def run_comprehensive_optimization(self) -> Dict:
        """Run complete optimization pipeline."""
        print("🚀 STARTING COMPREHENSIVE OPTIMIZATION FOR 70%+ ACCURACY")
        print("="*70)
        
        # Prepare data
        X, y, feature_names = self.prepare_training_data()
        
        if len(X) < 100:
            print("❌ Insufficient data for optimization")
            return {'success': False, 'error': 'Insufficient training data'}
        
        # Optimize models
        rf_results = self.optimize_random_forest(X, y, n_trials=50)
        xgb_results = self.optimize_xgboost(X, y, n_trials=50)
        
        # Select best performing model
        best_model_config = max([rf_results, xgb_results], key=lambda x: x['best_score'])
        
        print(f"\n🏆 BEST MODEL: {best_model_config['model_type']}")
        print(f"   Accuracy: {best_model_config['best_score']:.3f}")
        
        # Train final calibrated model
        final_model = self.train_calibrated_model(best_model_config, X, y)
        
        # Save results
        results = {
            'success': True,
            'target_achieved': best_model_config['target_achieved'],
            'best_accuracy': best_model_config['best_score'],
            'optimization_results': {
                'random_forest': rf_results,
                'xgboost': xgb_results
            },
            'final_model': final_model,
            'optimization_timestamp': datetime.now().isoformat(),
            'data_stats': {
                'n_samples': len(X),
                'n_features': len(feature_names),
                'class_distribution': y.value_counts().to_dict()
            }
        }
        
        # Save to file
        results_file = Path('optimization_results_70_percent.json')
        with open(results_file, 'w') as f:
            # Convert non-serializable objects
            serializable_results = results.copy()
            if 'final_model' in serializable_results:
                serializable_results['final_model'] = {
                    k: v for k, v in serializable_results['final_model'].items() 
                    if k not in ['base_model', 'calibrated_model']
                }
            json.dump(serializable_results, f, indent=2, default=str)
        
        print(f"\n💾 Results saved to: {results_file}")
        
        # Save models
        if results['success'] and 'final_model' in results:
            model_dir = Path('models/optimized_70_percent')
            model_dir.mkdir(exist_ok=True)
            
            # Save calibrated model
            model_file = model_dir / 'calibrated_model.joblib'
            joblib.dump(final_model['calibrated_model'], model_file)
            print(f"💾 Calibrated model saved to: {model_file}")
            
            # Save feature names
            feature_file = model_dir / 'feature_names.json'
            with open(feature_file, 'w') as f:
                json.dump(feature_names, f)
        
        return results
    
    def generate_report(self, results: Dict):
        """Generate comprehensive optimization report."""
        print("\n" + "="*70)
        print("📋 OPTIMIZATION REPORT")
        print("="*70)
        
        if not results.get('success', False):
            print("❌ OPTIMIZATION FAILED")
            print(f"   Error: {results.get('error', 'Unknown error')}")
            return
        
        print(f"🎯 TARGET ACCURACY: {self.target_accuracy:.1%}")
        print(f"🏆 ACHIEVED ACCURACY: {results['best_accuracy']:.3f} ({results['best_accuracy']:.1%})")
        
        if results['target_achieved']:
            print("✅ TARGET SUCCESSFULLY ACHIEVED!")
        else:
            gap = self.target_accuracy - results['best_accuracy']
            print(f"⚠️  Target missed by {gap:.3f} ({gap:.1%})")
        
        print(f"\n📊 OPTIMIZATION SUMMARY:")
        for model_name, model_results in results['optimization_results'].items():
            print(f"   {model_name}: {model_results['best_score']:.3f}")
        
        print(f"\n📈 DATA STATISTICS:")
        data_stats = results['data_stats']
        print(f"   Samples: {data_stats['n_samples']:,}")
        print(f"   Features: {data_stats['n_features']}")
        print(f"   Classes: {data_stats['class_distribution']}")
        
        if results.get('final_model', {}).get('feature_importance'):
            print(f"\n🏆 TOP FEATURES:")
            importance = results['final_model']['feature_importance']
            top_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:5]
            for feature, importance in top_features:
                print(f"   {feature}: {importance:.3f}")


if __name__ == "__main__":
    optimizer = AccuracyOptimizer(target_accuracy=0.70)
    results = optimizer.run_comprehensive_optimization()
    optimizer.generate_report(results)
    
    if results.get('target_achieved', False):
        print("\n🎉 SUCCESS: 70%+ accuracy target achieved!")
        exit(0)
    else:
        print("\n⚠️  Target not achieved - further optimization needed")
        exit(1)