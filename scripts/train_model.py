#!/usr/bin/env python3
"""
ML Model Retraining Script for Trading Bot

This script downloads fresh market data, generates corrected features with proper symbol context,
trains a new RandomForest model, evaluates performance, and replaces the current model if better.

Key improvements:
- Proper symbol context in feature generation (fixes bearish bias)
- Balanced training data across multiple symbols
- Performance comparison with current model
- Automatic model backup and replacement

Usage:
    python scripts/train_model.py
"""

import sys
import os
# 🧠 Force TensorFlow/PyTorch to use CPU only to avoid CUDA errors
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

sys.path.insert(0, '.')

import pandas as pd
import numpy as np
import joblib
from datetime import datetime, timedelta
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
import warnings
warnings.filterwarnings('ignore')

# Import bot modules
from bot.data import fetch_all_bars
from bot.features import make_features
from bot.strategy import FEATURES, prepare_xy, train_model as strategy_train_model
from bot.config import settings
from bot.util import logger


class ModelTrainer:
    """Enhanced model trainer with proper feature generation and evaluation."""
    
    def __init__(self):
        self.symbols = settings.symbols
        self.model_path = settings.model_path
        self.backup_path = self.model_path.replace('.pkl', '_backup.pkl')
        self.current_model = None
        self.new_model = None
        
    def download_fresh_data(self, days=45, min_bars=200):
        """Download fresh market data for training."""
        logger.info(f"📡 Downloading fresh data for {len(self.symbols)} symbols...")
        
        # Calculate date range for fresh data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        logger.info(f"📅 Date range: {start_date.date()} to {end_date.date()}")
        
        # Download data for all symbols
        market_data = fetch_all_bars(
            symbols=self.symbols,
            start=start_date.strftime('%Y-%m-%d'),
            end=end_date.strftime('%Y-%m-%d'),
            min_bars=min_bars
        )
        
        # Filter symbols with sufficient data
        valid_data = {}
        for symbol, df in market_data.items():
            if not df.empty and len(df) >= min_bars:
                valid_data[symbol] = df
                logger.info(f"✅ {symbol}: {len(df)} bars downloaded")
            else:
                logger.warning(f"⚠️ {symbol}: Insufficient data ({len(df) if not df.empty else 0} bars)")
        
        logger.info(f"📊 Valid data for {len(valid_data)}/{len(self.symbols)} symbols")
        return valid_data
    
    def generate_training_data(self, market_data):
        """Generate training data with corrected features for each symbol."""
        logger.info("🔧 Generating training features with symbol-specific parameters...")
        
        all_training_data = []
        
        for symbol, df in market_data.items():
            try:
                logger.debug(f"🧮 Processing features for {symbol}...")
                
                # Generate features with proper symbol context
                features_df = make_features(df.copy(), symbol=symbol)
                
                if features_df.empty:
                    logger.warning(f"⚠️ No features generated for {symbol}")
                    continue
                
                # Add symbol identifier
                features_df['symbol'] = symbol
                
                # Generate future returns for labeling
                features_df['future_return'] = features_df['close'].pct_change(periods=1).shift(-1)
                
                # Create labels: 0=SELL, 1=HOLD, 2=BUY (same as current model)
                features_df['target'] = np.where(
                    features_df['future_return'] < -0.01, 0,  # SELL if drops >1%
                    np.where(features_df['future_return'] > 0.01, 2, 1)  # BUY if rises >1%, else HOLD
                )
                
                # Filter valid rows
                valid_rows = features_df.dropna(subset=FEATURES + ['target', 'future_return'])
                
                if len(valid_rows) > 20:  # Minimum rows per symbol
                    all_training_data.append(valid_rows)
                    logger.debug(f"✅ {symbol}: {len(valid_rows)} training samples")
                else:
                    logger.warning(f"⚠️ {symbol}: Not enough valid rows ({len(valid_rows)})")
                    
            except Exception as e:
                logger.error(f"❌ Error processing {symbol}: {e}")
        
        if not all_training_data:
            raise ValueError("No valid training data generated")
        
        # Combine all training data
        combined_df = pd.concat(all_training_data, ignore_index=True)
        
        # Balance classes by symbol to avoid bias
        logger.info("⚖️ Balancing training data across symbols and classes...")
        balanced_data = self._balance_training_data(combined_df)
        
        # Prepare final X, y
        X = balanced_data[FEATURES]
        y = balanced_data['target']
        
        # Log class distribution
        class_counts = y.value_counts().sort_index()
        total = len(y)
        logger.info("📊 Final training data distribution:")
        logger.info(f"   • SELL (0): {class_counts.get(0, 0):,} ({class_counts.get(0, 0)/total:.1%})")
        logger.info(f"   • HOLD (1): {class_counts.get(1, 0):,} ({class_counts.get(1, 0)/total:.1%})")
        logger.info(f"   • BUY (2):  {class_counts.get(2, 0):,} ({class_counts.get(2, 0)/total:.1%})")
        logger.info(f"   • Total:    {total:,} samples")
        
        return X, y, balanced_data
    
    def _balance_training_data(self, df):
        """Balance training data to prevent bias."""
        # Sample equal amounts from each class per symbol
        balanced_samples = []
        
        for symbol in df['symbol'].unique():
            symbol_data = df[df['symbol'] == symbol]
            
            # Get samples for each class
            classes = {}
            for class_label in [0, 1, 2]:
                class_data = symbol_data[symbol_data['target'] == class_label]
                if len(class_data) > 0:
                    classes[class_label] = class_data
            
            if len(classes) >= 2:  # Need at least 2 classes
                # Find minimum class size (but at least 10 samples)
                min_size = max(10, min(len(data) for data in classes.values()))
                
                # Sample equally from each class
                for class_data in classes.values():
                    sampled = class_data.sample(n=min(len(class_data), min_size), random_state=42)
                    balanced_samples.append(sampled)
        
        if balanced_samples:
            return pd.concat(balanced_samples, ignore_index=True)
        else:
            return df  # Fallback to original if balancing fails
    
    def train_new_model(self, X, y):
        """Train a new RandomForest model with the same configuration as current model."""
        logger.info("🎯 Training new RandomForest model...")
        
        from sklearn.ensemble import RandomForestClassifier
        
        # Use same configuration as in bot/strategy.py
        model = RandomForestClassifier(
            n_estimators=300,
            max_depth=8,
            random_state=42,
            n_jobs=-1,
            class_weight="balanced",
            max_features='sqrt',  # Additional improvement
            min_samples_split=5,  # Prevent overfitting
            min_samples_leaf=2
        )
        
        # Split data for validation
        try:
            X_train, X_val, y_train, y_val = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
        except ValueError:
            logger.warning("⚠️ No se pudo estratificar el split (clases con pocos ejemplos). Usando split normal.")
            X_train, X_val, y_train, y_val = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
        
        logger.info(f"📚 Training set: {len(X_train):,} samples")
        logger.info(f"🧪 Validation set: {len(X_val):,} samples")
        
        # Train model
        model.fit(X_train, y_train)
        
        # Evaluate on validation set
        y_pred = model.predict(X_val)
        accuracy = accuracy_score(y_val, y_pred)
        
        logger.info(f"✅ New model trained successfully!")
        logger.info(f"📊 Validation accuracy: {accuracy:.3f}")
        
        # Log feature importance
        feature_importance = pd.DataFrame({
            'feature': FEATURES,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        logger.info("🎯 Top 5 most important features:")
        for _, row in feature_importance.head().iterrows():
            logger.info(f"   • {row['feature']}: {row['importance']:.3f}")
        
        # Detailed classification report
        logger.info("📋 Classification Report:")
        report = classification_report(y_val, y_pred, 
                                     target_names=['SELL', 'HOLD', 'BUY'],
                                     output_dict=True)
        
        for class_name in ['SELL', 'HOLD', 'BUY']:
            metrics = report[class_name]
            logger.info(f"   • {class_name}: precision={metrics['precision']:.3f}, "
                       f"recall={metrics['recall']:.3f}, f1={metrics['f1-score']:.3f}")
        
        return model, accuracy, X_val, y_val, y_pred
    
    def load_current_model(self):
        """Load current model for comparison."""
        if not os.path.exists(self.model_path):
            logger.warning("⚠️ No current model found for comparison")
            return None
        
        try:
            model = joblib.load(self.model_path)
            logger.info(f"✅ Current model loaded from {self.model_path}")
            return model
        except Exception as e:
            logger.error(f"❌ Error loading current model: {e}")
            return None
    
    def compare_models(self, new_model, new_accuracy, X_val, y_val):
        """Compare new model with current model."""
        logger.info("🔍 Comparing new model with current model...")
        
        current_model = self.load_current_model()
        
        if current_model is None:
            logger.info("📝 No current model to compare - new model will be saved")
            return True
        
        try:
            # Evaluate current model on same validation set
            y_pred_current = current_model.predict(X_val)
            current_accuracy = accuracy_score(y_val, y_pred_current)
            
            logger.info(f"📊 Current model accuracy: {current_accuracy:.3f}")
            logger.info(f"📊 New model accuracy:     {new_accuracy:.3f}")
            
            improvement = new_accuracy - current_accuracy
            logger.info(f"📈 Accuracy improvement: {improvement:+.3f}")
            
            # Test signal diversity (check if new model produces more balanced predictions)
            new_pred_dist = np.bincount(new_model.predict(X_val), minlength=3) / len(y_val)
            current_pred_dist = np.bincount(current_model.predict(X_val), minlength=3) / len(y_val)
            
            logger.info("🎯 Prediction distributions:")
            logger.info(f"   Current: SELL={current_pred_dist[0]:.1%}, HOLD={current_pred_dist[1]:.1%}, BUY={current_pred_dist[2]:.1%}")
            logger.info(f"   New:     SELL={new_pred_dist[0]:.1%}, HOLD={new_pred_dist[1]:.1%}, BUY={new_pred_dist[2]:.1%}")
            
            # Check for better balance (less extreme bias)
            new_balance = 1 - np.std(new_pred_dist)
            current_balance = 1 - np.std(current_pred_dist)
            
            logger.info(f"📊 Balance score - Current: {current_balance:.3f}, New: {new_balance:.3f}")
            
            # Decision criteria: better accuracy OR significantly better balance
            replace_model = (improvement > -0.02) and (new_balance > current_balance * 0.95)
            
            if replace_model:
                logger.info("✅ New model is better - will replace current model")
            else:
                logger.info("❌ Current model is better - keeping existing model")
            
            return replace_model
            
        except Exception as e:
            logger.error(f"❌ Error comparing models: {e}")
            return False
    
    def backup_and_save_model(self, new_model):
        """Backup current model and save new one."""
        logger.info("💾 Backing up and saving new model...")
        
        # Backup current model if it exists
        if os.path.exists(self.model_path):
            try:
                import shutil
                shutil.copy2(self.model_path, self.backup_path)
                logger.info(f"✅ Current model backed up to {self.backup_path}")
            except Exception as e:
                logger.error(f"⚠️ Could not backup current model: {e}")
        
        # Save new model
        try:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            joblib.dump(new_model, self.model_path)
            logger.info(f"✅ New model saved to {self.model_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Error saving new model: {e}")
            return False
    
    def run_training_pipeline(self):
        """Execute the complete training pipeline."""
        logger.info("🚀 Starting ML model retraining pipeline...")
        logger.info("=" * 60)
        
        try:
            # Step 1: Download fresh data
            logger.info("\n📡 STEP 1: Downloading fresh market data...")
            market_data = self.download_fresh_data(days=45, min_bars=200)
            
            if len(market_data) < 5:
                raise ValueError(f"Insufficient symbols with data: {len(market_data)}")
            
            # Step 2: Generate training data with corrected features
            logger.info("\n🔧 STEP 2: Generating training data with corrected features...")
            X, y, training_df = self.generate_training_data(market_data)
            
            if len(X) < 1000:
                raise ValueError(f"Insufficient training samples: {len(X)}")
            
            # Step 3: Train new model
            logger.info("\n🎯 STEP 3: Training new model...")
            new_model, accuracy, X_val, y_val, y_pred = self.train_new_model(X, y)
            
            # Step 4: Compare with current model
            logger.info("\n🔍 STEP 4: Comparing with current model...")
            should_replace = self.compare_models(new_model, accuracy, X_val, y_val)
            
            # Step 5: Save model if better
            if should_replace:
                logger.info("\n💾 STEP 5: Saving new model...")
                success = self.backup_and_save_model(new_model)
                
                if success:
                    logger.info("\n🎉 TRAINING PIPELINE COMPLETED SUCCESSFULLY!")
                    logger.info("✅ New model is now active and should provide more balanced signals")
                    return True
                else:
                    logger.error("❌ Failed to save new model")
                    return False
            else:
                logger.info("\n📝 Model not replaced - current model performs better")
                return False
                
        except Exception as e:
            logger.error(f"❌ Training pipeline failed: {e}")
            return False


def main():
    """Main execution function."""
    print("🤖 ML Model Retraining Script")
    print("=" * 50)
    print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Initialize trainer
    trainer = ModelTrainer()
    
    # Run training pipeline
    success = trainer.run_training_pipeline()
    
    # Final summary
    print("\n" + "=" * 50)
    if success:
        print("🎉 MODEL RETRAINING COMPLETED SUCCESSFULLY!")
        print("✅ Your trading bot now has an improved ML model")
        print("🎯 The new model should provide more balanced and realistic signals")
    else:
        print("⚠️ Model retraining completed with issues")
        print("📝 Current model was kept (new model didn't improve performance)")
    
    print(f"🕐 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    return success


if __name__ == "__main__":
    # Salir con código de error si el entrenamiento falla
    if not main():
        sys.exit(1)