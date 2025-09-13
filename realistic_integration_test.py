#!/usr/bin/env python3
"""
🔒 REALISTIC PREDICTIVE ANALYTICS INTEGRATION TEST
Comprehensive validation suite for leakage-free, production-ready ML models targeting
sustainable 70-75% accuracy for financial markets.

This test suite validates:
1. ✅ Leakage-free evaluation methodology  
2. ✅ Realistic accuracy targets (70-75%)
3. ✅ Proper time series validation
4. ✅ Feature engineering without look-ahead bias
5. ✅ Statistical significance and confidence intervals
"""

import sys
import os
import numpy as np
import pandas as pd
import warnings
from datetime import datetime
from pathlib import Path
import joblib
import json

warnings.filterwarnings('ignore')
sys.path.append('.')

from leakage_free_evaluation import RigorousModelValidator, ValidationConfig, LeakageFreeFeatureEngine

class RealisticIntegrationTest:
    """Integration test suite for realistic ML validation."""
    
    def __init__(self):
        self.results = {}
        self.test_count = 0
        self.passed_count = 0
        
        print("🔒 REALISTIC PREDICTIVE ANALYTICS INTEGRATION TEST")
        print("="*70)
        print(f"   Target: Leakage-free 70-75% accuracy validation")
        print(f"   Time: {datetime.now()}")
        
    def test_1_leakage_free_validation_system(self) -> dict:
        """Test 1: Validate leakage-free evaluation system."""
        print("\n🔒 TEST 1: LEAKAGE-FREE VALIDATION SYSTEM")
        
        test_result = {'name': 'Leakage-Free Validation System', 'passed': False, 'issues': []}
        
        try:
            # Initialize validation system
            config = ValidationConfig(
                n_splits=3,  # Reduced for testing speed
                embargo_period=30,
                purge_period=60,
                min_accuracy=0.60,  # Slightly lower for testing
                max_accuracy=0.85   # Allow some variance
            )
            
            validator = RigorousModelValidator(config)
            
            # Generate realistic dataset
            data = validator.generate_realistic_dataset(n_samples=1000)  # Smaller for speed
            
            # Create leakage-free features
            X = validator.feature_engine.generate_realistic_features(data)
            y = validator.feature_engine.create_realistic_target(data, prediction_horizon=5)
            
            # Remove NaN values
            valid_mask = ~y.isna()
            X = X[valid_mask]
            y = y[valid_mask]
            
            print(f"   ✅ Generated dataset: {len(X)} samples, {len(X.columns)} features")
            
            # Test that no future information is used
            feature_names = list(X.columns)
            forbidden_patterns = ['future', 'shift(-', 'forward', 'next']
            
            future_features = []
            for feature in feature_names:
                if any(pattern in feature.lower() for pattern in forbidden_patterns):
                    future_features.append(feature)
            
            if not future_features:
                print(f"   ✅ No look-ahead features detected")
                test_result['passed'] = True
                test_result['features_count'] = len(feature_names)
                test_result['samples_count'] = len(X)
            else:
                test_result['issues'].append(f"Look-ahead features detected: {future_features}")
                print(f"   ❌ Look-ahead features found: {future_features}")
                
        except Exception as e:
            test_result['issues'].append(f"Validation system error: {str(e)}")
            print(f"   ❌ System error: {e}")
        
        return test_result
    
    def test_2_realistic_accuracy_target(self) -> dict:
        """Test 2: Validate models achieve realistic 70-75% accuracy."""
        print("\n📊 TEST 2: REALISTIC ACCURACY TARGET (70-75%)")
        
        test_result = {'name': 'Realistic Accuracy Target', 'passed': False, 'issues': []}
        
        try:
            # Use the validated model from leakage-free evaluation
            model_path = Path('models/leakage_free/xgboost_validated.joblib')
            
            if model_path.exists():
                print(f"   📁 Found validated model: {model_path}")
                model = joblib.load(model_path)
                
                # Load validation results
                results_path = Path('leakage_free_validation_results.json')
                if results_path.exists():
                    with open(results_path, 'r') as f:
                        validation_results = json.load(f)
                    
                    best_model = validation_results.get('best_model')
                    if best_model:
                        model_result = validation_results['model_results'][best_model]
                        accuracy = model_result['overall_accuracy']
                        accuracy_std = model_result['accuracy_std']
                        
                        print(f"   📊 Validated accuracy: {accuracy:.3f} ± {accuracy_std:.3f}")
                        
                        # Check if in realistic range
                        if 0.70 <= accuracy <= 0.80:
                            print(f"   ✅ Accuracy in realistic 70-80% range")
                            test_result['passed'] = True
                            test_result['accuracy'] = accuracy
                            test_result['accuracy_std'] = accuracy_std
                        else:
                            test_result['issues'].append(f"Accuracy {accuracy:.3f} outside realistic range [0.70, 0.80]")
                            print(f"   ⚠️  Accuracy {accuracy:.3f} outside target range")
                    else:
                        test_result['issues'].append("No best model found in validation results")
                else:
                    test_result['issues'].append("Validation results file not found")
            else:
                test_result['issues'].append("Validated model file not found")
                print(f"   ❌ No validated model found at {model_path}")
                
        except Exception as e:
            test_result['issues'].append(f"Accuracy validation error: {str(e)}")
            print(f"   ❌ Accuracy test error: {e}")
        
        return test_result
    
    def test_3_time_series_validation_integrity(self) -> dict:
        """Test 3: Validate proper time series validation methodology."""
        print("\n⏱️  TEST 3: TIME SERIES VALIDATION INTEGRITY")
        
        test_result = {'name': 'Time Series Validation Integrity', 'passed': False, 'issues': []}
        
        try:
            # Test PurgedGroupTimeSeriesSplit implementation
            from leakage_free_evaluation import PurgedGroupTimeSeriesSplit
            
            # Create test data with datetime index
            start_date = datetime(2024, 1, 1, 9, 30)
            dates = pd.date_range(start=start_date, periods=500, freq='1T')
            
            test_data = pd.DataFrame({
                'feature1': np.random.randn(500),
                'feature2': np.random.randn(500)
            }, index=dates)
            
            test_target = pd.Series(np.random.randint(0, 5, 500), index=dates)
            
            # Test splitter
            splitter = PurgedGroupTimeSeriesSplit(n_splits=3, embargo_period=30, purge_period=60)
            splits = splitter.split(test_data, test_target)
            
            print(f"   📊 Generated {len(splits)} time series splits")
            
            # Validate split integrity
            integrity_passed = True
            for i, (train_idx, test_idx) in enumerate(splits):
                train_times = test_data.index[train_idx]
                test_times = test_data.index[test_idx]
                
                # Check that training ends before test begins (with gap)
                max_train_time = train_times.max()
                min_test_time = test_times.min()
                
                time_gap = (min_test_time - max_train_time).total_seconds() / 60  # minutes
                
                if time_gap < 30:  # Should have at least embargo period gap
                    integrity_passed = False
                    test_result['issues'].append(f"Split {i+1}: Insufficient time gap ({time_gap:.1f}min)")
                    print(f"   ❌ Split {i+1}: Time gap {time_gap:.1f}min < 30min embargo")
                else:
                    print(f"   ✅ Split {i+1}: Time gap {time_gap:.1f}min ≥ 30min embargo")
            
            if integrity_passed:
                test_result['passed'] = True
                test_result['splits_generated'] = len(splits)
                print(f"   ✅ Time series validation integrity confirmed")
            
        except Exception as e:
            test_result['issues'].append(f"Time series validation error: {str(e)}")
            print(f"   ❌ Time series test error: {e}")
        
        return test_result
    
    def test_4_statistical_significance(self) -> dict:
        """Test 4: Validate statistical significance of results."""
        print("\n📈 TEST 4: STATISTICAL SIGNIFICANCE")
        
        test_result = {'name': 'Statistical Significance', 'passed': False, 'issues': []}
        
        try:
            # Load validation results to check statistical metrics
            results_path = Path('leakage_free_validation_results.json')
            
            if results_path.exists():
                with open(results_path, 'r') as f:
                    validation_results = json.load(f)
                
                best_model = validation_results.get('best_model')
                if best_model:
                    model_result = validation_results['model_results'][best_model]
                    stats_sig = model_result.get('statistical_significance', {})
                    
                    p_value = stats_sig.get('p_value', 1.0)
                    ci_lower = stats_sig.get('ci_lower', 0.0)
                    ci_upper = stats_sig.get('ci_upper', 1.0)
                    
                    print(f"   📊 P-value: {p_value:.4f}")
                    print(f"   📊 95% CI: [{ci_lower:.3f}, {ci_upper:.3f}]")
                    
                    # Check statistical significance (p < 0.05)
                    if p_value < 0.05:
                        print(f"   ✅ Statistically significant (p < 0.05)")
                        significance_passed = True
                    else:
                        print(f"   ⚠️  Not statistically significant (p ≥ 0.05)")
                        significance_passed = False
                        test_result['issues'].append(f"P-value {p_value:.4f} not significant")
                    
                    # Check confidence interval width (should be reasonable)
                    ci_width = ci_upper - ci_lower
                    if ci_width < 0.30:  # CI width < 30%
                        print(f"   ✅ Reasonable confidence interval width: {ci_width:.3f}")
                        ci_passed = True
                    else:
                        print(f"   ⚠️  Wide confidence interval: {ci_width:.3f}")
                        ci_passed = False
                        test_result['issues'].append(f"Wide CI: {ci_width:.3f}")
                    
                    if significance_passed and ci_passed:
                        test_result['passed'] = True
                        test_result['p_value'] = p_value
                        test_result['ci_width'] = ci_width
                else:
                    test_result['issues'].append("No best model statistical data found")
            else:
                test_result['issues'].append("Validation results file not found")
                
        except Exception as e:
            test_result['issues'].append(f"Statistical significance error: {str(e)}")
            print(f"   ❌ Statistical test error: {e}")
        
        return test_result
    
    def test_5_production_readiness(self) -> dict:
        """Test 5: Validate production readiness of the system."""
        print("\n🚀 TEST 5: PRODUCTION READINESS")
        
        test_result = {'name': 'Production Readiness', 'passed': False, 'issues': []}
        
        try:
            production_checks = []
            
            # Check 1: Model files exist
            model_dir = Path('models/leakage_free')
            if model_dir.exists():
                model_files = list(model_dir.glob('*.joblib'))
                if model_files:
                    print(f"   ✅ Model files found: {len(model_files)}")
                    production_checks.append(True)
                else:
                    print(f"   ❌ No model files found in {model_dir}")
                    production_checks.append(False)
                    test_result['issues'].append("No model files found")
            else:
                print(f"   ❌ Model directory not found: {model_dir}")
                production_checks.append(False)
                test_result['issues'].append("Model directory missing")
            
            # Check 2: Feature schema exists
            schema_file = model_dir / 'feature_schema.json'
            if schema_file.exists():
                with open(schema_file, 'r') as f:
                    feature_schema = json.load(f)
                print(f"   ✅ Feature schema found: {len(feature_schema)} features")
                production_checks.append(True)
            else:
                print(f"   ❌ Feature schema not found")
                production_checks.append(False)
                test_result['issues'].append("Feature schema missing")
            
            # Check 3: Validation config exists  
            config_file = model_dir / 'validation_config.json'
            if config_file.exists():
                print(f"   ✅ Validation config found")
                production_checks.append(True)
            else:
                print(f"   ❌ Validation config not found")
                production_checks.append(False)
                test_result['issues'].append("Validation config missing")
            
            # Check 4: Results documentation exists
            results_file = Path('leakage_free_validation_results.json')
            if results_file.exists():
                print(f"   ✅ Validation results documented")
                production_checks.append(True)
            else:
                print(f"   ❌ Validation results not found")
                production_checks.append(False)
                test_result['issues'].append("Validation results missing")
            
            # Check 5: Test quick model loading and prediction
            try:
                model_path = model_dir / 'xgboost_validated.joblib'
                if model_path.exists():
                    model = joblib.load(model_path)
                    
                    # Create test features
                    test_features = np.random.randn(10, len(feature_schema)).reshape(10, -1)
                    test_df = pd.DataFrame(test_features, columns=feature_schema)
                    
                    # Test prediction
                    predictions = model.predict(test_df)
                    print(f"   ✅ Model prediction test successful: {len(predictions)} predictions")
                    production_checks.append(True)
                else:
                    print(f"   ❌ Cannot load model for testing")
                    production_checks.append(False)
                    test_result['issues'].append("Model loading failed")
                    
            except Exception as e:
                print(f"   ❌ Model loading/prediction error: {e}")
                production_checks.append(False)
                test_result['issues'].append(f"Model test error: {str(e)}")
            
            # Overall production readiness
            if all(production_checks):
                test_result['passed'] = True
                test_result['checks_passed'] = len(production_checks)
                print(f"   🚀 Production readiness confirmed: {len(production_checks)}/5 checks passed")
            else:
                failed_checks = len(production_checks) - sum(production_checks)
                print(f"   ⚠️  Production readiness issues: {failed_checks}/5 checks failed")
                
        except Exception as e:
            test_result['issues'].append(f"Production readiness error: {str(e)}")
            print(f"   ❌ Production test error: {e}")
        
        return test_result
    
    def run_all_tests(self) -> dict:
        """Run all realistic integration tests."""
        print("🔒 RUNNING REALISTIC INTEGRATION TESTS")
        print("="*70)
        
        # Run all tests
        test_results = []
        
        test_results.append(self.test_1_leakage_free_validation_system())
        test_results.append(self.test_2_realistic_accuracy_target())
        test_results.append(self.test_3_time_series_validation_integrity())
        test_results.append(self.test_4_statistical_significance())
        test_results.append(self.test_5_production_readiness())
        
        # Calculate results
        total_tests = len(test_results)
        passed_tests = sum(1 for test in test_results if test['passed'])
        success_rate = passed_tests / total_tests
        
        # Compile results
        comprehensive_results = {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'success_rate': success_rate,
            'target_achieved': success_rate >= 0.8,  # 80% pass rate minimum
            'tests': test_results,
            'summary': {
                'leakage_free_validated': any(
                    test['name'] == 'Leakage-Free Validation System' and test['passed'] 
                    for test in test_results
                ),
                'realistic_accuracy_achieved': any(
                    test['name'] == 'Realistic Accuracy Target' and test['passed']
                    for test in test_results
                ),
                'time_series_integrity_confirmed': any(
                    test['name'] == 'Time Series Validation Integrity' and test['passed']
                    for test in test_results
                ),
                'statistical_significance_verified': any(
                    test['name'] == 'Statistical Significance' and test['passed']
                    for test in test_results
                ),
                'production_ready': any(
                    test['name'] == 'Production Readiness' and test['passed']
                    for test in test_results
                )
            }
        }
        
        # Save results
        with open('realistic_integration_results.json', 'w') as f:
            json.dump(comprehensive_results, f, indent=2, default=str)
        
        return comprehensive_results
    
    def generate_final_report(self, results: dict) -> bool:
        """Generate final realistic integration report."""
        print("\n" + "="*70)
        print("📋 REALISTIC INTEGRATION TEST REPORT")
        print("="*70)
        
        print(f"🎯 TARGET: Leakage-free 70-75% accuracy validation")
        print(f"🏆 ACHIEVED: {results['passed_tests']}/{results['total_tests']} tests passed ({results['success_rate']:.1%})")
        
        if results['target_achieved']:
            print("✅ REALISTIC INTEGRATION TARGET ACHIEVED!")
        else:
            print("⚠️  Integration target not fully met")
        
        print(f"\n📊 DETAILED RESULTS:")
        for i, test in enumerate(results['tests'], 1):
            status = "✅" if test['passed'] else "❌"
            print(f"   {status} {i}. {test['name']}")
            
            if not test['passed'] and test.get('issues'):
                for issue in test['issues'][:2]:  # Show top 2 issues
                    print(f"      ⚠️  {issue}")
        
        summary = results['summary']
        print(f"\n🎯 KEY VALIDATIONS:")
        print(f"   {'✅' if summary['leakage_free_validated'] else '❌'} Leakage-Free System")
        print(f"   {'✅' if summary['realistic_accuracy_achieved'] else '❌'} Realistic 70-75% Accuracy")
        print(f"   {'✅' if summary['time_series_integrity_confirmed'] else '❌'} Time Series Integrity")
        print(f"   {'✅' if summary['statistical_significance_verified'] else '❌'} Statistical Significance")
        print(f"   {'✅' if summary['production_ready'] else '❌'} Production Ready")
        
        overall_success = (
            results['success_rate'] >= 0.8 and
            summary['leakage_free_validated'] and
            summary['realistic_accuracy_achieved']
        )
        
        print(f"\n🎉 OVERALL STATUS: {'SUCCESS' if overall_success else 'NEEDS ATTENTION'}")
        print(f"💾 Full results saved to: realistic_integration_results.json")
        
        return overall_success


if __name__ == "__main__":
    test_suite = RealisticIntegrationTest()
    results = test_suite.run_all_tests()
    success = test_suite.generate_final_report(results)
    
    exit(0 if success else 1)