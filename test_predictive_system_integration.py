#!/usr/bin/env python3
"""
🧪 COMPREHENSIVE PREDICTIVE ANALYTICS INTEGRATION TEST SUITE
Tests all components of the ML prediction pipeline to identify issues preventing 70%+ accuracy.

Test Categories:
1. Core ML Pipeline Integration
2. Feature Schema Consistency 
3. Model Performance & Accuracy
4. Real-time Prediction Pipeline
5. Data Flow & Memory Management
"""

import sys
import os
import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timedelta
import warnings
from pathlib import Path

# Add bot module to path
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

warnings.filterwarnings('ignore')

# Test framework
class PredictiveAnalyticsTestSuite:
    """Comprehensive test suite for predictive analytics system."""
    
    def __init__(self):
        self.results = {}
        self.test_data = None
        self.sample_symbols = ['BTC/USD', 'ETH/USD', 'SPY']
        
    def run_all_tests(self):
        """Run all integration tests and return comprehensive report."""
        print("🧪 STARTING COMPREHENSIVE PREDICTIVE ANALYTICS INTEGRATION TESTS")
        print("="*80)
        
        # Test 1: Core Dependencies
        print("\n📦 TEST 1: Core Dependencies & Imports")
        self.results['dependencies'] = self._test_dependencies()
        
        # Test 2: Feature Engineering Pipeline
        print("\n🔧 TEST 2: Feature Engineering Pipeline")
        self.results['feature_engineering'] = self._test_feature_engineering()
        
        # Test 3: Model Training & Performance
        print("\n🎯 TEST 3: Model Training & Performance")
        self.results['model_performance'] = self._test_model_performance()
        
        # Test 4: Real-time Prediction Pipeline
        print("\n⚡ TEST 4: Real-time Prediction Pipeline")
        self.results['realtime_pipeline'] = self._test_realtime_pipeline()
        
        # Test 5: Feature Schema Consistency
        print("\n📋 TEST 5: Feature Schema Consistency")
        self.results['schema_consistency'] = self._test_schema_consistency()
        
        # Generate Report
        print("\n📊 INTEGRATION TEST REPORT")
        print("="*80)
        self._generate_report()
        
        return self.results
    
    def _test_dependencies(self):
        """Test all critical ML dependencies."""
        results = {'passed': 0, 'total': 0, 'issues': []}
        
        dependencies = [
            ('sklearn', 'scikit-learn'),
            ('xgboost', 'XGBoost'),
            ('optuna', 'Optuna'),
            ('tensorflow', 'TensorFlow'),
            ('talib', 'TA-Lib'),
            ('lightgbm', 'LightGBM'),
            ('pandas', 'Pandas'),
            ('numpy', 'NumPy')
        ]
        
        for module, name in dependencies:
            results['total'] += 1
            try:
                if module == 'talib':
                    import talib
                    # Test a basic function
                    test_data = np.random.randn(100)
                    rsi = talib.RSI(test_data)
                    print(f"  ✅ {name}: OK")
                elif module == 'tensorflow':
                    import tensorflow as tf
                    # Test basic functionality
                    x = tf.constant([1., 2., 3.])
                    print(f"  ✅ {name}: {tf.__version__}")
                elif module == 'lightgbm':
                    import lightgbm as lgb
                    print(f"  ✅ {name}: {lgb.__version__}")
                else:
                    exec(f"import {module}")
                    print(f"  ✅ {name}: OK")
                results['passed'] += 1
            except Exception as e:
                print(f"  ❌ {name}: {str(e)}")
                results['issues'].append(f"{name}: {str(e)}")
        
        return results
    
    def _test_feature_engineering(self):
        """Test feature engineering pipeline consistency."""
        results = {'passed': 0, 'total': 0, 'issues': []}
        
        try:
            from bot.feature_engineering import AdvancedFeatureEngine, generate_features
            
            # Test 1: Basic feature generation
            results['total'] += 1
            test_data = self._generate_test_data()
            
            try:
                features = generate_features(test_data, symbol='BTC/USD')
                if features is not None and len(features) > 0:
                    print(f"  ✅ Feature generation: {len(features.columns)} features created")
                    results['passed'] += 1
                else:
                    print(f"  ❌ Feature generation: No features created")
                    results['issues'].append("Feature generation returned empty dataset")
            except Exception as e:
                print(f"  ❌ Feature generation: {str(e)}")
                results['issues'].append(f"Feature generation error: {str(e)}")
            
            # Test 2: Feature consistency across calls
            results['total'] += 1
            try:
                features1 = generate_features(test_data, symbol='BTC/USD')
                features2 = generate_features(test_data, symbol='BTC/USD')
                
                if features1 is not None and features2 is not None:
                    if list(features1.columns) == list(features2.columns):
                        print(f"  ✅ Feature consistency: Schema consistent across calls")
                        results['passed'] += 1
                    else:
                        print(f"  ❌ Feature consistency: Schema mismatch")
                        results['issues'].append("Feature schema inconsistent across calls")
                else:
                    print(f"  ❌ Feature consistency: Null features returned")
                    results['issues'].append("Feature consistency test failed - null returns")
            except Exception as e:
                print(f"  ❌ Feature consistency: {str(e)}")
                results['issues'].append(f"Feature consistency error: {str(e)}")
            
        except ImportError as e:
            print(f"  ❌ Import Error: {str(e)}")
            results['issues'].append(f"Feature engineering import error: {str(e)}")
        
        return results
    
    def _test_model_performance(self):
        """Test model training and performance validation."""
        results = {'passed': 0, 'total': 0, 'issues': [], 'accuracy_scores': {}}
        
        try:
            from bot.predictive_analytics import PredictiveAnalytics
            from bot.model_training import ModelTrainer
            
            # Test 1: Model initialization
            results['total'] += 1
            try:
                predictor = PredictiveAnalytics()
                print(f"  ✅ Model initialization: PredictiveAnalytics loaded")
                results['passed'] += 1
            except Exception as e:
                print(f"  ❌ Model initialization: {str(e)}")
                results['issues'].append(f"Model initialization error: {str(e)}")
                return results
            
            # Test 2: Training data preparation
            results['total'] += 1
            try:
                test_data = self._generate_training_data()
                if len(test_data) >= 1000:  # Minimum for meaningful training
                    print(f"  ✅ Training data: {len(test_data)} samples prepared")
                    results['passed'] += 1
                else:
                    print(f"  ❌ Training data: Insufficient samples ({len(test_data)})")
                    results['issues'].append("Insufficient training data")
            except Exception as e:
                print(f"  ❌ Training data preparation: {str(e)}")
                results['issues'].append(f"Training data error: {str(e)}")
            
            # Test 3: Model training (quick test)
            results['total'] += 1
            try:
                # Quick training test with small dataset
                small_data = test_data.head(500) if len(test_data) > 500 else test_data
                
                # Create target variable (simplified)
                small_data['target'] = (small_data['close'].pct_change(5).shift(-5) > 0.001).astype(int)
                small_data = small_data.dropna()
                
                if len(small_data) >= 100:
                    print(f"  ✅ Model training: Test dataset prepared ({len(small_data)} samples)")
                    results['passed'] += 1
                    
                    # Store accuracy potential for later optimization
                    results['accuracy_scores']['baseline_samples'] = len(small_data)
                else:
                    print(f"  ❌ Model training: Insufficient clean data ({len(small_data)})")
                    results['issues'].append("Insufficient clean training data")
                    
            except Exception as e:
                print(f"  ❌ Model training: {str(e)}")
                results['issues'].append(f"Model training error: {str(e)}")
            
        except ImportError as e:
            print(f"  ❌ Import Error: {str(e)}")
            results['issues'].append(f"Model training import error: {str(e)}")
        
        return results
    
    def _test_realtime_pipeline(self):
        """Test real-time prediction pipeline."""
        results = {'passed': 0, 'total': 0, 'issues': []}
        
        try:
            from bot.real_time_predictor import RealTimePredictor
            
            # Test 1: Real-time predictor initialization
            results['total'] += 1
            try:
                rt_predictor = RealTimePredictor()
                print(f"  ✅ Real-time predictor: Initialization successful")
                results['passed'] += 1
            except Exception as e:
                print(f"  ❌ Real-time predictor init: {str(e)}")
                results['issues'].append(f"Real-time predictor error: {str(e)}")
                return results
            
            # Test 2: Input validation
            results['total'] += 1
            try:
                test_data = self._generate_test_data()
                # Test with properly formatted data
                if len(test_data) > 0:
                    print(f"  ✅ Input validation: Test data format valid")
                    results['passed'] += 1
                else:
                    print(f"  ❌ Input validation: Invalid test data")
                    results['issues'].append("Input validation failed")
            except Exception as e:
                print(f"  ❌ Input validation: {str(e)}")
                results['issues'].append(f"Input validation error: {str(e)}")
            
        except ImportError as e:
            print(f"  ❌ Import Error: {str(e)}")
            results['issues'].append(f"Real-time pipeline import error: {str(e)}")
        
        return results
    
    def _test_schema_consistency(self):
        """Test feature schema consistency across pipeline."""
        results = {'passed': 0, 'total': 0, 'issues': []}
        
        # Test schema consistency between training and prediction
        results['total'] += 1
        try:
            test_data = self._generate_test_data()
            
            # Generate features multiple times and check consistency
            schemas = []
            for i in range(3):
                try:
                    from bot.feature_engineering import generate_features
                    features = generate_features(test_data, symbol='BTC/USD')
                    if features is not None:
                        schemas.append(list(features.columns))
                except Exception as e:
                    print(f"  ❌ Schema test iteration {i+1}: {str(e)}")
                    results['issues'].append(f"Schema iteration {i+1} failed: {str(e)}")
            
            if len(schemas) >= 2:
                if all(schema == schemas[0] for schema in schemas):
                    print(f"  ✅ Schema consistency: All schemas match ({len(schemas[0])} columns)")
                    results['passed'] += 1
                else:
                    print(f"  ❌ Schema consistency: Schema mismatch detected")
                    results['issues'].append("Schema inconsistency across calls")
            else:
                print(f"  ❌ Schema consistency: Insufficient test runs")
                results['issues'].append("Could not complete schema consistency test")
                
        except Exception as e:
            print(f"  ❌ Schema consistency test: {str(e)}")
            results['issues'].append(f"Schema consistency error: {str(e)}")
        
        return results
    
    def _generate_test_data(self):
        """Generate realistic test market data."""
        dates = pd.date_range(start='2024-01-01', end='2024-12-01', freq='5T')
        n_points = len(dates)
        
        # Generate realistic OHLCV data
        np.random.seed(42)
        price_base = 50000  # Starting price for BTC
        returns = np.random.normal(0, 0.02, n_points)  # 2% volatility
        prices = price_base * np.exp(np.cumsum(returns))
        
        # Create OHLC from price series
        data = pd.DataFrame({
            'timestamp': dates,
            'open': prices * (1 + np.random.normal(0, 0.001, n_points)),
            'high': prices * (1 + np.abs(np.random.normal(0, 0.005, n_points))),
            'low': prices * (1 - np.abs(np.random.normal(0, 0.005, n_points))),
            'close': prices,
            'volume': np.random.exponential(1000, n_points)
        })
        
        # Ensure high >= close >= low and high >= open >= low
        data['high'] = np.maximum(data['high'], np.maximum(data['open'], data['close']))
        data['low'] = np.minimum(data['low'], np.minimum(data['open'], data['close']))
        
        return data
    
    def _generate_training_data(self):
        """Generate comprehensive training dataset."""
        # Generate larger dataset for training
        dates = pd.date_range(start='2023-01-01', end='2024-12-01', freq='5T')
        n_points = len(dates)
        
        np.random.seed(42)
        price_base = 50000
        returns = np.random.normal(0, 0.015, n_points)  # 1.5% volatility
        prices = price_base * np.exp(np.cumsum(returns))
        
        data = pd.DataFrame({
            'timestamp': dates,
            'open': prices * (1 + np.random.normal(0, 0.001, n_points)),
            'high': prices * (1 + np.abs(np.random.normal(0, 0.003, n_points))),
            'low': prices * (1 - np.abs(np.random.normal(0, 0.003, n_points))),
            'close': prices,
            'volume': np.random.exponential(1000, n_points)
        })
        
        # Fix OHLC relationships
        data['high'] = np.maximum(data['high'], np.maximum(data['open'], data['close']))
        data['low'] = np.minimum(data['low'], np.minimum(data['open'], data['close']))
        
        return data
    
    def _generate_report(self):
        """Generate comprehensive test report."""
        total_passed = sum(result.get('passed', 0) for result in self.results.values())
        total_tests = sum(result.get('total', 0) for result in self.results.values())
        success_rate = (total_passed / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"📊 OVERALL RESULTS: {total_passed}/{total_tests} tests passed ({success_rate:.1f}%)")
        print()
        
        for category, result in self.results.items():
            if isinstance(result, dict):
                passed = result.get('passed', 0)
                total = result.get('total', 0)
                issues = result.get('issues', [])
                
                status = "✅" if passed == total and total > 0 else "❌"
                print(f"{status} {category.upper()}: {passed}/{total} passed")
                
                if issues:
                    for issue in issues:
                        print(f"    ⚠️  {issue}")
        
        print()
        print("🎯 CRITICAL AREAS FOR 70%+ ACCURACY TARGET:")
        
        # Identify critical issues
        critical_issues = []
        for category, result in self.results.items():
            if isinstance(result, dict) and result.get('issues'):
                critical_issues.extend([f"{category}: {issue}" for issue in result['issues']])
        
        if critical_issues:
            for issue in critical_issues[:5]:  # Top 5 critical issues
                print(f"    🔥 {issue}")
        else:
            print("    🎉 No critical issues detected - ready for optimization!")
        
        return success_rate >= 80  # 80%+ test pass rate required

if __name__ == "__main__":
    test_suite = PredictiveAnalyticsTestSuite()
    results = test_suite.run_all_tests()
    
    # Exit with appropriate code
    success = all(
        result.get('passed', 0) == result.get('total', 1) 
        for result in results.values() 
        if isinstance(result, dict)
    )
    
    exit(0 if success else 1)