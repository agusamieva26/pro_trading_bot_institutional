#!/usr/bin/env python3
"""
Comprehensive Smoke Test for Backtesting Engine - Critical Error Validation

Tests all components of the backtesting engine to ensure all LSP diagnostic 
errors have been resolved and the system functions correctly end-to-end.
"""

import os
import sys
import pandas as pd
import numpy as np
import warnings
from datetime import datetime, timedelta
from pathlib import Path

# Add bot directory to path
sys.path.append('.')

def test_imports():
    """Test all critical imports work without errors."""
    print("🔄 Testing critical imports...")
    try:
        from bot.features import make_features
        from bot.sizing import volatility_target_size, kelly_cap
        from bot.backtest_metrics import BacktestMetrics
        from bot.historical_data_manager import HistoricalDataManager
        from bot.backtesting_engine import BacktestingEngine, BacktestConfig
        from bot.strategy_optimizer import StrategyOptimizer
        from bot.backtest_reporting import BacktestReporter
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def test_features():
    """Test features module with synthetic data."""
    print("🔄 Testing features module...")
    try:
        from bot.features import make_features
        
        # Create synthetic OHLC data
        dates = pd.date_range('2024-01-01', periods=100, freq='1H')
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.normal(0, 1, 100))
        
        df = pd.DataFrame({
            'open': prices + np.random.normal(0, 0.1, 100),
            'high': prices + np.abs(np.random.normal(0, 0.5, 100)),
            'low': prices - np.abs(np.random.normal(0, 0.5, 100)),
            'close': prices,
            'volume': np.random.exponential(1000, 100)
        }, index=dates)
        
        # Test with different symbol configurations
        result1 = make_features(df, symbol='BTC/USD')
        result2 = make_features(df, symbol='ETH/USD')
        result3 = make_features(df, symbol=None)
        
        assert not result1.empty, "Features result should not be empty"
        assert 'ema_12' in result1.columns, "EMA_12 should be in features"
        assert 'rsi_14' in result1.columns, "RSI_14 should be in features"
        assert 'macd' in result1.columns, "MACD should be in features"
        
        print("✅ Features module working correctly")
        return True
    except Exception as e:
        print(f"❌ Features error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_sizing():
    """Test sizing module."""
    print("🔄 Testing sizing module...")
    try:
        from bot.sizing import volatility_target_size, kelly_cap
        
        # Test volatility sizing
        size1 = volatility_target_size(10000, 100.0, 2.0)
        size2 = volatility_target_size(10000, 100.0, 2.0, risk_per_trade=0.02)
        
        assert size1 > 0, "Position size should be positive"
        assert size2 > 0, "Position size with risk override should be positive"
        
        # Test Kelly sizing
        kelly1 = kelly_cap(0.6, 2.0)
        kelly2 = kelly_cap(0.4, 1.5, cap=0.05)
        
        assert 0 <= kelly1 <= 1, "Kelly fraction should be between 0 and 1"
        assert 0 <= kelly2 <= 0.05, "Kelly fraction should respect cap"
        
        print("✅ Sizing module working correctly")
        return True
    except Exception as e:
        print(f"❌ Sizing error: {e}")
        return False

def test_backtest_metrics():
    """Test backtest metrics with synthetic equity curve."""
    print("🔄 Testing backtest metrics...")
    try:
        from bot.backtest_metrics import BacktestMetrics
        
        # Create synthetic equity curve
        dates = pd.date_range('2024-01-01', periods=252, freq='D')
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, 252)  # Daily returns
        equity = pd.Series(10000 * np.cumprod(1 + returns), index=dates)
        
        metrics = BacktestMetrics()
        
        # Test key metrics
        returns_series = metrics.calculate_returns_series(equity)
        total_ret = metrics.total_return(equity)
        annual_ret = metrics.annualized_return(equity)
        volatility = metrics.volatility(returns_series)
        sharpe = metrics.sharpe_ratio(returns_series)
        max_dd = metrics.max_drawdown(equity)
        
        # Validate metrics
        assert not returns_series.empty, "Returns series should not be empty"
        assert isinstance(total_ret, (int, float)), "Total return should be numeric"
        assert isinstance(annual_ret, (int, float)), "Annual return should be numeric"
        assert volatility >= 0, "Volatility should be non-negative"
        assert isinstance(sharpe, (int, float)), "Sharpe ratio should be numeric"
        assert max_dd <= 0, "Max drawdown should be negative or zero"
        
        print("✅ Backtest metrics working correctly")
        return True
    except Exception as e:
        print(f"❌ Backtest metrics error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_historical_data_manager():
    """Test historical data manager."""
    print("🔄 Testing historical data manager...")
    try:
        from bot.historical_data_manager import HistoricalDataManager
        
        manager = HistoricalDataManager(cache_dir="test_cache")
        
        # Test cache key generation
        cache_key = manager._get_cache_key('BTC/USD', '1Hour', '2024-01-01', '2024-01-31')
        assert len(cache_key) == 32, "Cache key should be MD5 hash (32 chars)"
        
        # Test data validation with synthetic data
        dates = pd.date_range('2024-01-01', periods=100, freq='1H')
        df = pd.DataFrame({
            'open': np.random.uniform(95, 105, 100),
            'high': np.random.uniform(100, 110, 100),
            'low': np.random.uniform(90, 100, 100),
            'close': np.random.uniform(95, 105, 100),
            'volume': np.random.exponential(1000, 100)
        }, index=dates)
        
        validated_df = manager._validate_data_quality(df, 'TEST/USD')
        assert not validated_df.empty, "Validated data should not be empty"
        
        # Test safe strftime
        test_date = datetime.now()
        formatted = manager._safe_strftime(test_date, '%Y-%m-%d')
        assert len(formatted) >= 10, "Formatted date should be valid"
        
        # Test invalid date handling
        invalid_formatted = manager._safe_strftime(None, '%Y-%m-%d')
        assert invalid_formatted in ['N/A', 'Invalid Date'], "Should handle invalid dates"
        
        print("✅ Historical data manager working correctly")
        return True
    except Exception as e:
        print(f"❌ Historical data manager error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_backtesting_engine():
    """Test backtesting engine core functionality."""
    print("🔄 Testing backtesting engine...")
    try:
        from bot.backtesting_engine import BacktestingEngine, BacktestConfig
        
        # Create minimal config
        config = BacktestConfig(
            initial_capital=10000.0,
            start_date="2024-01-01",
            end_date="2024-01-31",
            symbols=["TEST/USD"]
        )
        
        engine = BacktestingEngine(config)
        
        # Test initialization
        assert engine.cash == config.initial_capital, "Initial cash should match config"
        assert len(engine.positions) == 0, "Should start with no positions"
        assert len(engine.completed_trades) == 0, "Should start with no trades"
        
        print("✅ Backtesting engine working correctly")
        return True
    except Exception as e:
        print(f"❌ Backtesting engine error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_comprehensive_workflow():
    """Test end-to-end workflow."""
    print("🔄 Testing comprehensive workflow...")
    try:
        from bot.features import make_features
        from bot.backtest_metrics import BacktestMetrics
        from bot.backtesting_engine import BacktestConfig
        
        # Create comprehensive synthetic dataset
        dates = pd.date_range('2024-01-01', periods=1000, freq='1H')
        np.random.seed(42)
        
        prices = 100 + np.cumsum(np.random.normal(0, 0.5, 1000))
        df = pd.DataFrame({
            'open': prices + np.random.normal(0, 0.1, 1000),
            'high': prices + np.abs(np.random.normal(0, 0.3, 1000)),
            'low': prices - np.abs(np.random.normal(0, 0.3, 1000)),
            'close': prices,
            'volume': np.random.exponential(1000, 1000)
        }, index=dates)
        
        # Test full pipeline
        features_df = make_features(df, symbol='BTC/USD')
        assert not features_df.empty, "Features should be generated"
        
        # Create equity curve from features
        returns = features_df['ret_1'].fillna(0)
        equity_curve = pd.Series(10000 * np.cumprod(1 + returns), index=features_df.index)
        
        # Test metrics on result
        metrics = BacktestMetrics()
        comprehensive_metrics = metrics.comprehensive_metrics(equity_curve)
        
        assert 'total_return_pct' in comprehensive_metrics, "Should have total return"
        assert 'sharpe_ratio' in comprehensive_metrics, "Should have Sharpe ratio"
        assert 'max_drawdown_pct' in comprehensive_metrics, "Should have max drawdown"
        
        print("✅ Comprehensive workflow working correctly")
        return True
    except Exception as e:
        print(f"❌ Comprehensive workflow error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("🚀 Starting Comprehensive Backtesting Engine Tests")
    print("="*60)
    
    # Suppress warnings during testing
    warnings.filterwarnings('ignore')
    
    tests = [
        ("Imports", test_imports),
        ("Features", test_features),
        ("Sizing", test_sizing),
        ("Backtest Metrics", test_backtest_metrics),
        ("Historical Data Manager", test_historical_data_manager),
        ("Backtesting Engine", test_backtesting_engine),
        ("Comprehensive Workflow", test_comprehensive_workflow)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n📊 Testing {test_name}...")
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} FAILED with exception: {e}")
    
    print("\n" + "="*60)
    print(f"🎯 TEST RESULTS: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED! Backtesting engine is working correctly.")
        return True
    else:
        print("❌ SOME TESTS FAILED! Please fix remaining issues.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)