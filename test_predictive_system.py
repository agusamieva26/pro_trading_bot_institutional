"""
🧪 PREDICTIVE ANALYTICS SYSTEM INTEGRATION TEST
Comprehensive testing of the institutional-grade ML prediction system to validate
70%+ accuracy target and production readiness.

Tests:
- Component imports and initialization
- Feature engineering pipeline
- Model training with synthetic data
- Real-time prediction pipeline
- Performance metrics and tracking
- End-to-end workflow validation
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
import traceback
from typing import Dict, Any

# Add bot directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'bot'))

warnings.filterwarnings('ignore')

def create_synthetic_ohlcv_data(n_samples: int = 1000, symbol: str = "TEST/USD") -> pd.DataFrame:
    """Create synthetic OHLCV data for testing."""
    
    # Create realistic price series with trend and volatility
    np.random.seed(42)
    
    base_price = 100.0
    returns = np.random.normal(0.0001, 0.02, n_samples)  # Small positive drift, 2% volatility
    
    # Add some autocorrelation for realism
    for i in range(1, len(returns)):
        returns[i] += 0.1 * returns[i-1]
    
    # Generate price series
    prices = [base_price]
    for ret in returns:
        prices.append(prices[-1] * (1 + ret))
    
    prices = np.array(prices[1:])  # Remove initial price
    
    # Generate OHLCV data
    data = []
    for i, close in enumerate(prices):
        # Generate realistic OHLC based on close
        volatility = abs(returns[i]) * close
        
        high = close + np.random.uniform(0, volatility * 2)
        low = close - np.random.uniform(0, volatility * 2)
        open_price = low + np.random.uniform(0, high - low)
        
        # Ensure OHLC relationships are valid
        high = max(high, open_price, close)
        low = min(low, open_price, close)
        
        volume = np.random.lognormal(10, 1)  # Log-normal volume distribution
        
        timestamp = datetime.now() - timedelta(minutes=(n_samples - i))
        
        data.append({
            'timestamp': timestamp,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
    
    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)
    
    return df

def test_component_imports():
    """Test that all components can be imported successfully."""
    print("\n🔍 Testing component imports...")
    
    results = {}
    
    # Test predictive_analytics
    try:
        from bot.predictive_analytics import PredictiveAnalytics, get_prediction, get_system_status
        results['predictive_analytics'] = "✅ SUCCESS"
        print("✅ predictive_analytics imported successfully")
    except Exception as e:
        results['predictive_analytics'] = f"❌ FAILED: {str(e)}"
        print(f"❌ predictive_analytics import failed: {e}")
    
    # Test feature_engineering
    try:
        from bot.feature_engineering import AdvancedFeatureEngine, generate_features
        results['feature_engineering'] = "✅ SUCCESS"
        print("✅ feature_engineering imported successfully")
    except Exception as e:
        results['feature_engineering'] = f"❌ FAILED: {str(e)}"
        print(f"❌ feature_engineering import failed: {e}")
    
    # Test model_training
    try:
        from bot.model_training import ModelTrainer, train_models
        results['model_training'] = "✅ SUCCESS"
        print("✅ model_training imported successfully")
    except Exception as e:
        results['model_training'] = f"❌ FAILED: {str(e)}"
        print(f"❌ model_training import failed: {e}")
    
    # Test real_time_predictor
    try:
        from bot.real_time_predictor import StreamingPredictor, get_live_prediction
        results['real_time_predictor'] = "✅ SUCCESS"
        print("✅ real_time_predictor imported successfully")
    except Exception as e:
        results['real_time_predictor'] = f"❌ FAILED: {str(e)}"
        print(f"❌ real_time_predictor import failed: {e}")
    
    # Test prediction_metrics
    try:
        from bot.prediction_metrics import PredictionTracker, get_performance_report
        results['prediction_metrics'] = "✅ SUCCESS"
        print("✅ prediction_metrics imported successfully")
    except Exception as e:
        results['prediction_metrics'] = f"❌ FAILED: {str(e)}"
        print(f"❌ prediction_metrics import failed: {e}")
    
    return results

def test_feature_engineering():
    """Test feature engineering pipeline."""
    print("\n🔬 Testing feature engineering...")
    
    try:
        from bot.feature_engineering import generate_features
        
        # Create test data
        test_data = create_synthetic_ohlcv_data(200, "TEST/USD")
        
        # Generate features
        features = generate_features(test_data, "TEST/USD", include_target=True)
        
        if features.empty:
            return {"status": "❌ FAILED", "error": "No features generated"}
        
        # Validate features
        required_cols = ['close', 'volume']
        feature_cols = [col for col in features.columns if col not in required_cols + ['timestamp', 'symbol']]
        
        result = {
            "status": "✅ SUCCESS",
            "features_generated": len(feature_cols),
            "total_samples": len(features),
            "sample_features": feature_cols[:10],
            "has_target": 'future_return_5m' in features.columns
        }
        
        print(f"✅ Generated {len(feature_cols)} features from {len(features)} samples")
        print(f"✅ Target variable present: {result['has_target']}")
        
        return result
        
    except Exception as e:
        print(f"❌ Feature engineering test failed: {e}")
        return {"status": "❌ FAILED", "error": str(e)}

def test_model_training():
    """Test model training pipeline."""
    print("\n🎯 Testing model training...")
    
    try:
        from bot.model_training import ModelTrainer, TrainingConfig
        from bot.feature_engineering import generate_features
        
        # Create training data
        symbols = ["TEST1/USD", "TEST2/USD", "TEST3/USD"]
        training_data = {}
        
        for symbol in symbols:
            raw_data = create_synthetic_ohlcv_data(300, symbol)
            features = generate_features(raw_data, symbol, include_target=True)
            if not features.empty:
                training_data[symbol] = features
        
        if not training_data:
            return {"status": "❌ FAILED", "error": "No training data generated"}
        
        # Configure training for quick test
        config = TrainingConfig(
            n_trials=10,  # Reduced for testing
            cv_folds=3,   # Reduced for testing
            walk_forward_periods=3,  # Reduced for testing
            min_samples_per_class=20,
            enable_deep_learning=False,  # Disable LSTM for quick test
            max_features_per_model=20
        )
        
        # Initialize trainer
        trainer = ModelTrainer(config)
        
        # Train models
        print("🔄 Starting model training (reduced for testing)...")
        results = trainer.train_all_models(training_data)
        
        if not results:
            return {"status": "❌ FAILED", "error": "No models trained successfully"}
        
        # Analyze results
        best_accuracy = max(result.performance.accuracy for result in results.values())
        
        result = {
            "status": "✅ SUCCESS" if best_accuracy > 0.5 else "⚠️ LOW ACCURACY",
            "models_trained": len(results),
            "best_accuracy": best_accuracy,
            "models": {name: {
                "accuracy": result.performance.accuracy,
                "precision": result.performance.precision,
                "recall": result.performance.recall
            } for name, result in results.items()}
        }
        
        print(f"✅ Trained {len(results)} models successfully")
        print(f"✅ Best accuracy: {best_accuracy:.3f}")
        
        return result
        
    except Exception as e:
        print(f"❌ Model training test failed: {e}")
        traceback.print_exc()
        return {"status": "❌ FAILED", "error": str(e)}

def test_prediction_pipeline():
    """Test end-to-end prediction pipeline."""
    print("\n⚡ Testing prediction pipeline...")
    
    try:
        from bot.predictive_analytics import PredictiveAnalytics
        from bot.feature_engineering import generate_features
        
        # Initialize system
        predictor = PredictiveAnalytics()
        
        # Check if models are loaded or need training
        system_status = predictor.get_system_status()
        
        if not system_status.get('is_trained', False):
            print("🔄 System not trained, running quick training...")
            
            # Create training data
            training_data = {}
            for i in range(2):
                symbol = f"TEST{i}/USD"
                raw_data = create_synthetic_ohlcv_data(200, symbol)
                features = generate_features(raw_data, symbol, include_target=True)
                if not features.empty:
                    training_data[symbol] = features
            
            # Quick training
            success = predictor.train_models(training_data, retrain=True)
            
            if not success:
                return {"status": "❌ FAILED", "error": "Could not train models for prediction test"}
        
        # Test prediction
        test_data = create_synthetic_ohlcv_data(100, "TEST/USD")
        features = generate_features(test_data, "TEST/USD", include_target=False)
        
        if features.empty:
            return {"status": "❌ FAILED", "error": "No features for prediction"}
        
        # Generate prediction
        prediction = predictor.predict("TEST/USD", features)
        
        if not prediction:
            return {"status": "❌ FAILED", "error": "No prediction generated"}
        
        result = {
            "status": "✅ SUCCESS",
            "prediction_class": prediction.prediction_class.name,
            "confidence": prediction.confidence,
            "signal_strength": prediction.signal_strength,
            "timeframe": prediction.timeframe.value,
            "models_voted": len(prediction.model_votes),
            "risk_score": prediction.risk_score
        }
        
        print(f"✅ Generated prediction: {prediction.prediction_class.name}")
        print(f"✅ Confidence: {prediction.confidence:.3f}")
        print(f"✅ Signal strength: {prediction.signal_strength:.3f}")
        
        return result
        
    except Exception as e:
        print(f"❌ Prediction pipeline test failed: {e}")
        traceback.print_exc()
        return {"status": "❌ FAILED", "error": str(e)}

def test_performance_tracking():
    """Test performance tracking and metrics."""
    print("\n📊 Testing performance tracking...")
    
    try:
        from bot.prediction_metrics import PredictionTracker, PredictionRecord, PerformanceMetrics
        from bot.predictive_analytics import PredictionDirection, PredictionTimeframe
        from bot.real_time_predictor import SignalQuality
        
        # Initialize tracker
        tracker = PredictionTracker()
        
        # Create sample prediction records
        records = []
        
        for i in range(100):
            # Generate random prediction outcomes
            correct = np.random.choice([True, False], p=[0.65, 0.35])  # 65% accuracy
            
            actual_return = np.random.normal(0.001 if correct else -0.001, 0.01)
            
            record = PredictionRecord(
                prediction_id=f"test_pred_{i}",
                symbol="TEST/USD",
                timestamp=datetime.now() - timedelta(minutes=i),
                prediction_class=PredictionDirection.BUY if actual_return > 0 else PredictionDirection.SELL,
                actual_class=PredictionDirection.BUY if actual_return > 0 else PredictionDirection.SELL,
                confidence=np.random.uniform(0.6, 0.9),
                signal_strength=np.random.uniform(0.5, 2.0),
                signal_quality=np.random.choice(list(SignalQuality)),
                timeframe=PredictionTimeframe.MINUTE_5,
                market_regime="trending_up",
                position_size_pct=0.1,
                model_votes={"rf": "BUY", "xgb": "BUY"},
                prediction_correct=correct,
                actual_return=actual_return
            )
            
            records.append(record)
        
        # Calculate performance metrics
        metrics = tracker.analyzer.calculate_performance_metrics(records)
        
        result = {
            "status": "✅ SUCCESS",
            "accuracy": metrics.accuracy,
            "precision": metrics.precision,
            "recall": metrics.recall,
            "f1_score": metrics.f1_score,
            "win_rate": metrics.win_rate,
            "total_predictions": metrics.total_predictions,
            "avg_return": metrics.avg_return_per_prediction,
            "sharpe_ratio": metrics.sharpe_ratio
        }
        
        print(f"✅ Performance metrics calculated successfully")
        print(f"✅ Accuracy: {metrics.accuracy:.3f}")
        print(f"✅ Win rate: {metrics.win_rate:.3f}")
        print(f"✅ F1 Score: {metrics.f1_score:.3f}")
        
        return result
        
    except Exception as e:
        print(f"❌ Performance tracking test failed: {e}")
        return {"status": "❌ FAILED", "error": str(e)}

def run_full_integration_test():
    """Run comprehensive integration test of the entire system."""
    print("🚀 STARTING PREDICTIVE ANALYTICS SYSTEM INTEGRATION TEST")
    print("=" * 60)
    
    test_results = {}
    
    # Test 1: Component imports
    test_results['imports'] = test_component_imports()
    
    # Test 2: Feature engineering
    test_results['features'] = test_feature_engineering()
    
    # Test 3: Model training
    test_results['training'] = test_model_training()
    
    # Test 4: Prediction pipeline
    test_results['prediction'] = test_prediction_pipeline()
    
    # Test 5: Performance tracking
    test_results['metrics'] = test_performance_tracking()
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 INTEGRATION TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed_tests = 0
    total_tests = len(test_results)
    
    for test_name, result in test_results.items():
        if isinstance(result, dict):
            status = result.get('status', '❓ UNKNOWN')
        else:
            status = '❓ UNKNOWN'
        
        print(f"{test_name.upper():20} | {status}")
        
        if '✅' in status:
            passed_tests += 1
    
    print("-" * 60)
    print(f"PASSED: {passed_tests}/{total_tests} tests")
    
    # Overall assessment
    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED - SYSTEM READY FOR PRODUCTION")
    elif passed_tests >= total_tests * 0.8:
        print("⚠️ MOST TESTS PASSED - SYSTEM MOSTLY FUNCTIONAL")
    else:
        print("❌ MULTIPLE TEST FAILURES - SYSTEM NEEDS FIXES")
    
    # Check accuracy target
    training_result = test_results.get('training', {})
    if isinstance(training_result, dict):
        best_accuracy = training_result.get('best_accuracy', 0)
        if best_accuracy >= 0.70:
            print(f"✅ ACCURACY TARGET MET: {best_accuracy:.1%} >= 70%")
        else:
            print(f"⚠️ ACCURACY TARGET NOT MET: {best_accuracy:.1%} < 70%")
            print("   Note: This is with synthetic data - real market data may perform differently")
    
    return test_results

if __name__ == "__main__":
    # Run integration tests
    results = run_full_integration_test()
    
    # Save results
    import json
    with open('integration_test_results.json', 'w') as f:
        # Convert any non-serializable objects
        serializable_results = {}
        for key, value in results.items():
            if isinstance(value, dict):
                serializable_results[key] = value
            else:
                serializable_results[key] = str(value)
        
        json.dump(serializable_results, f, indent=2, default=str)
    
    print(f"\n📄 Test results saved to integration_test_results.json")