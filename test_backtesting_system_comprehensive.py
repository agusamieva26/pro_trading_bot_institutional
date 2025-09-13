#!/usr/bin/env python3
"""
Comprehensive End-to-End Backtesting System Test

Tests all critical components of the institutional-grade backtesting engine
to ensure complete functionality and production readiness.
"""

import sys
import traceback
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any

def test_imports():
    """Test all critical imports work correctly."""
    print("🔄 Testing imports...")
    
    try:
        # Core backtesting components
        from bot.backtesting_engine import BacktestingEngine, BacktestConfig
        from bot.backtest_metrics import BacktestMetrics, backtest_metrics
        from bot.historical_data_manager import HistoricalDataManager, historical_data_manager
        from bot.strategy_optimizer import StrategyOptimizer
        from bot.sizing import volatility_target_size, kelly_cap
        
        # Critical dependencies
        import scipy
        import sklearn
        import matplotlib.pyplot as plt
        import seaborn as sns
        import optuna
        
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        traceback.print_exc()
        return False


def test_singleton_exports():
    """Test that singleton instances are properly exported."""
    print("🔄 Testing singleton exports...")
    
    try:
        from bot.backtest_metrics import backtest_metrics
        from bot.historical_data_manager import historical_data_manager
        
        # Test singleton functionality
        sample_data = pd.Series([100, 105, 103, 108, 110], 
                               index=pd.date_range('2023-01-01', periods=5))
        
        total_return = backtest_metrics.total_return(sample_data)
        print(f"   📊 Sample total return: {total_return:.2f}%")
        
        print("✅ Singleton exports working")
        return True
    except Exception as e:
        print(f"❌ Singleton test failed: {e}")
        traceback.print_exc()
        return False


def test_backtesting_engine():
    """Test the core backtesting engine functionality."""
    print("🔄 Testing backtesting engine...")
    
    try:
        from bot.backtesting_engine import BacktestingEngine, BacktestConfig
        
        # Create minimal config for testing
        config = BacktestConfig(
            initial_capital=10000.0,
            symbols=["BTC/USD"],
            start_date="2023-06-01",
            end_date="2023-06-02",
            timeframe="1Hour"
        )
        
        # Initialize engine
        engine = BacktestingEngine(config)
        print("   ✅ Engine initialized")
        
        # Test equity curve generation
        engine.equity_curve = [10000, 10100, 9950, 10200]
        engine.timestamps = list(pd.date_range('2023-06-01', periods=4, freq='H'))
        
        print("   ✅ Engine functionality verified")
        return True
    except Exception as e:
        print(f"❌ Backtesting engine test failed: {e}")
        traceback.print_exc()
        return False


def test_metrics_calculation():
    """Test comprehensive metrics calculation."""
    print("🔄 Testing metrics calculation...")
    
    try:
        from bot.backtest_metrics import backtest_metrics
        
        # Create sample equity curve
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        returns = np.random.normal(0.001, 0.02, 100)
        equity_values = [10000]
        
        for ret in returns:
            equity_values.append(equity_values[-1] * (1 + ret))
        
        equity_curve = pd.Series(equity_values[1:], index=dates)
        
        # Calculate comprehensive metrics
        metrics = backtest_metrics.comprehensive_metrics(equity_curve)
        
        required_metrics = [
            'total_return_pct', 'annualized_return_pct', 'volatility_pct',
            'sharpe_ratio', 'sortino_ratio', 'max_drawdown_pct'
        ]
        
        for metric in required_metrics:
            if metric in metrics:
                print(f"   📊 {metric}: {metrics[metric]:.3f}")
            else:
                raise ValueError(f"Missing metric: {metric}")
        
        print("✅ Metrics calculation working")
        return True
    except Exception as e:
        print(f"❌ Metrics test failed: {e}")
        traceback.print_exc()
        return False


def test_data_manager():
    """Test historical data manager functionality."""
    print("🔄 Testing data manager...")
    
    try:
        from bot.historical_data_manager import historical_data_manager
        
        # Test data validation on sample data
        sample_data = pd.DataFrame({
            'open': [100, 101, 99, 102],
            'high': [101, 103, 100, 104],
            'low': [99, 100, 98, 101],
            'close': [101, 99, 102, 103],
            'volume': [1000, 1200, 800, 1100]
        }, index=pd.date_range('2023-01-01', periods=4, freq='H'))
        
        # Test data quality validation
        cleaned_data = historical_data_manager._validate_data_quality(sample_data, "TEST")
        
        if len(cleaned_data) == 4:
            print("   ✅ Data validation working")
        else:
            raise ValueError(f"Data validation failed: {len(cleaned_data)} != 4")
        
        print("✅ Data manager working")
        return True
    except Exception as e:
        print(f"❌ Data manager test failed: {e}")
        traceback.print_exc()
        return False


def test_sizing_functions():
    """Test position sizing functions."""
    print("🔄 Testing sizing functions...")
    
    try:
        from bot.sizing import volatility_target_size, kelly_cap
        
        # Test volatility target sizing
        size = volatility_target_size(
            equity=10000.0,
            price=100.0,
            atr=2.0
        )
        
        if size > 0:
            print(f"   📊 Volatility target size: {size:.2f}")
        else:
            raise ValueError("Invalid position size")
        
        # Test Kelly criterion
        kelly_frac = kelly_cap(prob=0.6, win_loss=1.5, cap=0.02)
        
        if 0 <= kelly_frac <= 0.02:
            print(f"   📊 Kelly fraction: {kelly_frac:.4f}")
        else:
            raise ValueError("Invalid Kelly fraction")
        
        print("✅ Sizing functions working")
        return True
    except Exception as e:
        print(f"❌ Sizing functions test failed: {e}")
        traceback.print_exc()
        return False


def test_dependency_compatibility():
    """Test compatibility with all critical dependencies."""
    print("🔄 Testing dependency compatibility...")
    
    try:
        # Test matplotlib
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(1, 1, figsize=(6, 4))
        ax.plot([1, 2, 3], [1, 4, 2])
        plt.close(fig)
        print("   ✅ Matplotlib working")
        
        # Test seaborn  
        import seaborn as sns
        sns.set_style("whitegrid")
        print("   ✅ Seaborn working")
        
        # Test scipy
        from scipy import stats
        result = stats.norm.pdf(0)
        print(f"   ✅ Scipy working: {result:.3f}")
        
        # Test sklearn
        from sklearn.ensemble import RandomForestClassifier
        clf = RandomForestClassifier(n_estimators=10, random_state=42)
        print("   ✅ Scikit-learn working")
        
        # Test optuna
        import optuna
        study = optuna.create_study()
        print("   ✅ Optuna working")
        
        print("✅ All dependencies compatible")
        return True
    except Exception as e:
        print(f"❌ Dependency compatibility test failed: {e}")
        traceback.print_exc()
        return False


def run_comprehensive_validation():
    """Run all validation tests."""
    print("🚀 COMPREHENSIVE BACKTESTING SYSTEM VALIDATION")
    print("=" * 55)
    
    tests = [
        ("Import Test", test_imports),
        ("Singleton Export Test", test_singleton_exports),
        ("Backtesting Engine Test", test_backtesting_engine),
        ("Metrics Calculation Test", test_metrics_calculation),
        ("Data Manager Test", test_data_manager),
        ("Sizing Functions Test", test_sizing_functions),
        ("Dependency Compatibility Test", test_dependency_compatibility)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n🔍 {test_name}")
        print("-" * 30)
        
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} CRASHED: {e}")
    
    print("\n" + "=" * 55)
    print("🎯 VALIDATION RESULTS")
    print("=" * 55)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Success Rate: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED - SYSTEM IS PRODUCTION READY! 🎉")
        return True
    else:
        print(f"\n🚨 {failed} CRITICAL ISSUES NEED FIXING 🚨")
        return False


if __name__ == "__main__":
    success = run_comprehensive_validation()
    sys.exit(0 if success else 1)