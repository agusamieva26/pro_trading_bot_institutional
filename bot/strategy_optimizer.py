# bot/strategy_optimizer.py
"""
Strategy Parameter Optimization & Walk-Forward Analysis

Advanced optimization system for strategy parameters with institutional-grade
validation techniques including walk-forward analysis, cross-validation,
and overfitting detection.
"""

import pandas as pd
import numpy as np
import itertools
from typing import Dict, List, Optional, Tuple, Union, Callable, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import warnings
import json
from pathlib import Path
from scipy import stats
from sklearn.model_selection import TimeSeriesSplit
import optuna
from optuna.samplers import TPESampler

from .backtesting_engine import BacktestingEngine, BacktestConfig
from .backtest_metrics import backtest_metrics
from .util import logger

warnings.filterwarnings('ignore', category=FutureWarning)


@dataclass
class OptimizationParameter:
    """Represents a parameter to optimize."""
    name: str
    min_value: float
    max_value: float
    step_size: Optional[float] = None
    values: Optional[List[float]] = None
    parameter_type: str = "float"  # "float", "int", "categorical"
    
    def get_values(self) -> List[float]:
        """Get all possible values for this parameter."""
        if self.values is not None:
            return self.values
        
        if self.parameter_type == "int":
            if self.step_size is None:
                self.step_size = 1
            return list(range(int(self.min_value), int(self.max_value) + 1, int(self.step_size)))
        else:  # float
            if self.step_size is None:
                # Generate 20 evenly spaced values by default
                return list(np.linspace(self.min_value, self.max_value, 20))
            else:
                return list(np.arange(self.min_value, self.max_value + self.step_size, self.step_size))


@dataclass
class OptimizationResult:
    """Results from parameter optimization."""
    best_parameters: Dict[str, float]
    best_score: float
    all_results: List[Dict[str, Any]]
    optimization_metric: str
    total_combinations: int
    successful_runs: int
    optimization_time_seconds: float
    
    def get_top_n(self, n: int = 10) -> List[Dict[str, Any]]:
        """Get top N parameter combinations."""
        sorted_results = sorted(self.all_results, key=lambda x: x['score'], reverse=True)
        return sorted_results[:n]
    
    def get_parameter_sensitivity(self, parameter_name: str) -> Dict[str, float]:
        """Analyze sensitivity of a specific parameter."""
        if not self.all_results:
            return {}
        
        # Group by parameter value and calculate statistics
        param_groups = {}
        for result in self.all_results:
            if parameter_name in result['parameters']:
                param_value = result['parameters'][parameter_name]
                if param_value not in param_groups:
                    param_groups[param_value] = []
                param_groups[param_value].append(result['score'])
        
        # Calculate statistics for each parameter value
        sensitivity = {}
        for value, scores in param_groups.items():
            sensitivity[value] = {
                'mean_score': np.mean(scores),
                'std_score': np.std(scores),
                'min_score': np.min(scores),
                'max_score': np.max(scores),
                'count': len(scores)
            }
        
        return sensitivity


class StrategyOptimizer:
    """
    Advanced strategy parameter optimization with institutional validation techniques.
    
    Features:
    - Grid search and random search optimization
    - Bayesian optimization with Optuna
    - Walk-forward analysis for temporal validation
    - Cross-validation with time series splits
    - Overfitting detection and regularization
    - Parallel processing for speed
    """
    
    def __init__(
        self, 
        base_config: BacktestConfig,
        optimization_metric: str = "sharpe_ratio",
        max_workers: int = 4
    ):
        """
        Initialize strategy optimizer.
        
        Args:
            base_config: Base configuration for backtesting
            optimization_metric: Metric to optimize (sharpe_ratio, total_return_pct, calmar_ratio, etc.)
            max_workers: Maximum parallel workers
        """
        self.base_config = base_config
        self.optimization_metric = optimization_metric
        self.max_workers = max_workers
        
        # Validation settings
        self.walk_forward_periods = 6  # Number of walk-forward windows
        self.min_train_ratio = 0.6     # Minimum training data ratio
        self.cv_splits = 5             # Cross-validation splits
        
        logger.info(f"🔧 Strategy Optimizer initialized")
        logger.info(f"📊 Optimization metric: {optimization_metric}")
    
    def grid_search(
        self, 
        parameters: List[OptimizationParameter],
        max_combinations: Optional[int] = None,
        save_results: bool = True
    ) -> OptimizationResult:
        """
        Perform grid search optimization.
        
        Args:
            parameters: List of parameters to optimize
            max_combinations: Maximum parameter combinations to test
            save_results: Whether to save results to file
            
        Returns:
            Optimization results
        """
        start_time = datetime.now()
        
        # Generate all parameter combinations
        param_values = [param.get_values() for param in parameters]
        param_names = [param.name for param in parameters]
        
        all_combinations = list(itertools.product(*param_values))
        
        # Limit combinations if specified
        if max_combinations and len(all_combinations) > max_combinations:
            logger.info(f"🔄 Limiting to {max_combinations} combinations (from {len(all_combinations)})")
            # Randomly sample combinations for better coverage
            np.random.shuffle(all_combinations)
            all_combinations = all_combinations[:max_combinations]
        
        total_combinations = len(all_combinations)
        logger.info(f"🚀 Starting grid search: {total_combinations} combinations")
        
        # Run optimization
        results = self._run_parallel_optimization(all_combinations, param_names)
        
        # Process results
        end_time = datetime.now()
        optimization_time = (end_time - start_time).total_seconds()
        
        best_result = max(results, key=lambda x: x['score']) if results else None
        
        optimization_result = OptimizationResult(
            best_parameters=best_result['parameters'] if best_result else {},
            best_score=best_result['score'] if best_result else 0.0,
            all_results=results,
            optimization_metric=self.optimization_metric,
            total_combinations=total_combinations,
            successful_runs=len(results),
            optimization_time_seconds=optimization_time
        )
        
        # Save results
        if save_results:
            self._save_optimization_results(optimization_result, "grid_search")
        
        logger.info(f"✅ Grid search completed: {len(results)}/{total_combinations} successful")
        logger.info(f"🏆 Best score: {best_result['score']:.4f}" if best_result else "❌ No successful runs")
        
        return optimization_result
    
    def bayesian_optimization(
        self,
        parameters: List[OptimizationParameter],
        n_trials: int = 100,
        save_results: bool = True
    ) -> OptimizationResult:
        """
        Perform Bayesian optimization using Optuna.
        
        Args:
            parameters: List of parameters to optimize
            n_trials: Number of optimization trials
            save_results: Whether to save results to file
            
        Returns:
            Optimization results
        """
        start_time = datetime.now()
        
        logger.info(f"🧠 Starting Bayesian optimization: {n_trials} trials")
        
        # Create Optuna study
        study = optuna.create_study(
            direction='maximize',
            sampler=TPESampler(seed=42)
        )
        
        # Define objective function
        def objective(trial):
            # Suggest parameter values
            param_dict = {}
            for param in parameters:
                if param.parameter_type == "float":
                    param_dict[param.name] = trial.suggest_float(
                        param.name, param.min_value, param.max_value
                    )
                elif param.parameter_type == "int":
                    param_dict[param.name] = trial.suggest_int(
                        param.name, int(param.min_value), int(param.max_value)
                    )
                elif param.parameter_type == "categorical":
                    param_dict[param.name] = trial.suggest_categorical(
                        param.name, param.values
                    )
            
            # Run backtest with these parameters
            try:
                score = self._evaluate_parameters(param_dict)
                return score
            except Exception as e:
                logger.warning(f"⚠️ Trial failed: {e}")
                return -np.inf
        
        # Run optimization
        study.optimize(objective, n_trials=n_trials)
        
        # Collect all results
        all_results = []
        for trial in study.trials:
            if trial.state == optuna.trial.TrialState.COMPLETE:
                all_results.append({
                    'parameters': trial.params,
                    'score': trial.value,
                    'trial_number': trial.number
                })
        
        # Process results
        end_time = datetime.now()
        optimization_time = (end_time - start_time).total_seconds()
        
        optimization_result = OptimizationResult(
            best_parameters=study.best_params,
            best_score=study.best_value,
            all_results=all_results,
            optimization_metric=self.optimization_metric,
            total_combinations=n_trials,
            successful_runs=len(all_results),
            optimization_time_seconds=optimization_time
        )
        
        # Save results
        if save_results:
            self._save_optimization_results(optimization_result, "bayesian")
        
        logger.info(f"✅ Bayesian optimization completed: {len(all_results)}/{n_trials} successful")
        logger.info(f"🏆 Best score: {study.best_value:.4f}")
        
        return optimization_result
    
    def walk_forward_analysis(
        self,
        parameters: Dict[str, float],
        validation_periods: int = 6,
        min_train_ratio: float = 0.6
    ) -> Dict[str, Any]:
        """
        Perform walk-forward analysis to validate strategy robustness.
        
        Args:
            parameters: Strategy parameters to test
            validation_periods: Number of walk-forward periods
            min_train_ratio: Minimum ratio of data for training
            
        Returns:
            Walk-forward analysis results
        """
        logger.info(f"📈 Starting walk-forward analysis: {validation_periods} periods")
        
        # Parse date range
        start_date = pd.to_datetime(self.base_config.start_date)
        end_date = pd.to_datetime(self.base_config.end_date)
        total_days = (end_date - start_date).days
        
        # Calculate window sizes
        min_train_days = int(total_days * min_train_ratio)
        test_period_days = max(30, (total_days - min_train_days) // validation_periods)
        
        results = []
        
        for i in range(validation_periods):
            # Calculate train and test periods
            test_start = start_date + timedelta(days=min_train_days + i * test_period_days)
            test_end = min(test_start + timedelta(days=test_period_days), end_date)
            
            if test_end <= test_start:
                break
            
            train_start = start_date
            train_end = test_start
            
            logger.info(f"🔄 WF Period {i+1}: Train {train_start.date()} to {train_end.date()}, Test {test_start.date()} to {test_end.date()}")
            
            try:
                # Create configs for train and test periods
                train_config = self._create_config_with_parameters(
                    parameters, train_start.strftime('%Y-%m-%d'), train_end.strftime('%Y-%m-%d')
                )
                test_config = self._create_config_with_parameters(
                    parameters, test_start.strftime('%Y-%m-%d'), test_end.strftime('%Y-%m-%d')
                )
                
                # Run backtests
                train_engine = BacktestingEngine(train_config)
                train_results = train_engine.run_backtest()
                
                test_engine = BacktestingEngine(test_config)
                test_results = test_engine.run_backtest()
                
                # Extract metrics
                train_score = train_results['metrics'].get(self.optimization_metric, 0)
                test_score = test_results['metrics'].get(self.optimization_metric, 0)
                
                period_result = {
                    'period': i + 1,
                    'train_start': train_start.date(),
                    'train_end': train_end.date(),
                    'test_start': test_start.date(),
                    'test_end': test_end.date(),
                    'train_score': train_score,
                    'test_score': test_score,
                    'train_metrics': train_results['metrics'],
                    'test_metrics': test_results['metrics']
                }
                
                results.append(period_result)
                
                logger.info(f"✅ Period {i+1}: Train={train_score:.4f}, Test={test_score:.4f}")
                
            except Exception as e:
                logger.error(f"❌ Period {i+1} failed: {e}")
                continue
        
        # Calculate summary statistics
        if results:
            train_scores = [r['train_score'] for r in results]
            test_scores = [r['test_score'] for r in results]
            
            summary = {
                'periods_completed': len(results),
                'train_mean': np.mean(train_scores),
                'train_std': np.std(train_scores),
                'test_mean': np.mean(test_scores),
                'test_std': np.std(test_scores),
                'correlation': np.corrcoef(train_scores, test_scores)[0, 1] if len(results) > 1 else 0,
                'overfitting_ratio': np.mean(test_scores) / np.mean(train_scores) if np.mean(train_scores) != 0 else 0,
                'consistency_score': 1 - (np.std(test_scores) / max(abs(float(np.mean(test_scores))), 1e-6))
            }
            
            logger.info(f"📊 WF Summary: Test/Train ratio = {summary['overfitting_ratio']:.3f}")
            logger.info(f"📊 Consistency score: {summary['consistency_score']:.3f}")
        else:
            summary = {}
        
        return {
            'parameters': parameters,
            'results': results,
            'summary': summary,
            'validation_periods': validation_periods
        }
    
    def cross_validation(
        self,
        parameters: Dict[str, float],
        n_splits: int = 5
    ) -> Dict[str, Any]:
        """
        Perform time series cross-validation.
        
        Args:
            parameters: Strategy parameters to test
            n_splits: Number of CV splits
            
        Returns:
            Cross-validation results
        """
        logger.info(f"🔄 Starting cross-validation: {n_splits} splits")
        
        # Parse date range
        start_date = pd.to_datetime(self.base_config.start_date)
        end_date = pd.to_datetime(self.base_config.end_date)
        
        # Create time series splits
        total_days = (end_date - start_date).days
        tscv = TimeSeriesSplit(n_splits=n_splits)
        
        # Generate date ranges for each split
        date_ranges = []
        for train_idx, test_idx in tscv.split(range(total_days)):
            train_start = start_date + timedelta(days=train_idx[0])
            train_end = start_date + timedelta(days=train_idx[-1])
            test_start = start_date + timedelta(days=test_idx[0])
            test_end = start_date + timedelta(days=test_idx[-1])
            
            date_ranges.append({
                'train_start': train_start.strftime('%Y-%m-%d'),
                'train_end': train_end.strftime('%Y-%m-%d'),
                'test_start': test_start.strftime('%Y-%m-%d'),
                'test_end': test_end.strftime('%Y-%m-%d')
            })
        
        results = []
        
        for i, date_range in enumerate(date_ranges):
            logger.info(f"🔄 CV Fold {i+1}/{n_splits}")
            
            try:
                # Create test config (we only need test results for CV)
                test_config = self._create_config_with_parameters(
                    parameters, date_range['test_start'], date_range['test_end']
                )
                
                # Run backtest
                engine = BacktestingEngine(test_config)
                backtest_results = engine.run_backtest()
                
                score = backtest_results['metrics'].get(self.optimization_metric, 0)
                
                fold_result = {
                    'fold': i + 1,
                    'score': score,
                    'metrics': backtest_results['metrics'],
                    'date_range': date_range
                }
                
                results.append(fold_result)
                
                logger.info(f"✅ Fold {i+1}: Score = {score:.4f}")
                
            except Exception as e:
                logger.error(f"❌ Fold {i+1} failed: {e}")
                continue
        
        # Calculate CV statistics
        if results:
            scores = [r['score'] for r in results]
            cv_summary = {
                'mean_score': np.mean(scores),
                'std_score': np.std(scores),
                'min_score': np.min(scores),
                'max_score': np.max(scores),
                'cv_score': np.mean(scores) - 2 * np.std(scores),  # Conservative estimate
                'successful_folds': len(results)
            }
            
            logger.info(f"📊 CV Summary: Mean = {cv_summary['mean_score']:.4f} ± {cv_summary['std_score']:.4f}")
        else:
            cv_summary = {}
        
        return {
            'parameters': parameters,
            'fold_results': results,
            'summary': cv_summary,
            'n_splits': n_splits
        }
    
    def detect_overfitting(
        self,
        optimization_result: OptimizationResult,
        validation_threshold: float = 0.8
    ) -> Dict[str, Any]:
        """
        Detect potential overfitting in optimization results.
        
        Args:
            optimization_result: Results from parameter optimization
            validation_threshold: Threshold for overfitting detection
            
        Returns:
            Overfitting analysis results
        """
        logger.info("🔍 Analyzing overfitting patterns...")
        
        if not optimization_result.all_results:
            return {'overfitting_detected': False, 'reason': 'No results to analyze'}
        
        # Get best parameters for validation
        best_params = optimization_result.best_parameters
        
        # Run walk-forward analysis on best parameters
        wf_results = self.walk_forward_analysis(best_params)
        
        # Overfitting indicators
        indicators = {}
        
        # 1. Walk-forward degradation
        if wf_results['summary']:
            overfitting_ratio = wf_results['summary'].get('overfitting_ratio', 1.0)
            consistency_score = wf_results['summary'].get('consistency_score', 0.0)
            
            indicators['wf_overfitting_ratio'] = overfitting_ratio
            indicators['wf_consistency'] = consistency_score
            indicators['wf_degradation'] = overfitting_ratio < validation_threshold
        
        # 2. Parameter sensitivity analysis
        param_sensitivities = {}
        for param_name in best_params.keys():
            sensitivity = optimization_result.get_parameter_sensitivity(param_name)
            if sensitivity:
                # Calculate coefficient of variation
                param_values = list(sensitivity.keys())
                mean_scores = [sensitivity[val]['mean_score'] for val in param_values]
                
                if len(mean_scores) > 1:
                    cv = float(np.std(mean_scores)) / max(abs(float(np.mean(mean_scores))), 1e-6)
                    param_sensitivities[param_name] = cv
        
        indicators['parameter_sensitivities'] = param_sensitivities
        
        # 3. Score distribution analysis
        all_scores = [r['score'] for r in optimization_result.all_results]
        best_score = optimization_result.best_score
        
        # Check if best score is an outlier
        score_percentile = stats.percentileofscore(all_scores, best_score)
        indicators['best_score_percentile'] = score_percentile
        indicators['score_distribution_skew'] = stats.skew(all_scores)
        
        # Overall overfitting assessment
        overfitting_signals = []
        
        if indicators.get('wf_degradation', False):
            overfitting_signals.append('Walk-forward performance degradation')
        
        if indicators.get('best_score_percentile', 0) > 99:
            overfitting_signals.append('Best score is extreme outlier')
        
        if any(sens > 2.0 for sens in param_sensitivities.values()):
            overfitting_signals.append('High parameter sensitivity detected')
        
        overfitting_detected = len(overfitting_signals) >= 2
        
        return {
            'overfitting_detected': overfitting_detected,
            'signals': overfitting_signals,
            'indicators': indicators,
            'walk_forward_results': wf_results,
            'recommendation': 'Use more conservative parameters or increase regularization' if overfitting_detected else 'Parameters appear robust'
        }
    
    def _run_parallel_optimization(
        self,
        parameter_combinations: List[Tuple],
        parameter_names: List[str]
    ) -> List[Dict[str, Any]]:
        """Run parameter combinations in parallel."""
        results = []
        
        # Convert combinations to parameter dictionaries
        param_dicts = []
        for combination in parameter_combinations:
            param_dict = dict(zip(parameter_names, combination))
            param_dicts.append(param_dict)
        
        # Run in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_params = {
                executor.submit(self._evaluate_parameters, params): params
                for params in param_dicts
            }
            
            completed = 0
            total = len(future_to_params)
            
            for future in as_completed(future_to_params):
                params = future_to_params[future]
                completed += 1
                
                try:
                    score = future.result()
                    results.append({
                        'parameters': params,
                        'score': score
                    })
                    
                    if completed % max(1, total // 10) == 0:  # 10% progress updates
                        progress = completed / total * 100
                        logger.info(f"📊 Progress: {progress:.1f}% ({completed}/{total})")
                        
                except Exception as e:
                    logger.debug(f"⚠️ Parameter combination failed: {params} - {e}")
        
        return results
    
    def _evaluate_parameters(self, parameters: Dict[str, float]) -> float:
        """Evaluate a single parameter combination."""
        # Create config with these parameters
        config = self._create_config_with_parameters(parameters)
        
        # Run backtest
        engine = BacktestingEngine(config)
        results = engine.run_backtest()
        
        # Extract optimization metric
        score = results['metrics'].get(self.optimization_metric, 0.0)
        
        # Handle invalid scores
        if np.isnan(score) or np.isinf(score):
            return -np.inf
        
        return score
    
    def _create_config_with_parameters(
        self,
        parameters: Dict[str, float],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> BacktestConfig:
        """Create backtest config with specified parameters."""
        # Create a copy of base config
        config = BacktestConfig(
            initial_capital=self.base_config.initial_capital,
            commission_rate=self.base_config.commission_rate,
            slippage_rate=self.base_config.slippage_rate,
            max_position_size=self.base_config.max_position_size,
            max_total_exposure=self.base_config.max_total_exposure,
            use_stop_loss=self.base_config.use_stop_loss,
            use_take_profit=self.base_config.use_take_profit,
            min_trade_size_usd=self.base_config.min_trade_size_usd,
            max_trades_per_day=self.base_config.max_trades_per_day,
            start_date=start_date or self.base_config.start_date,
            end_date=end_date or self.base_config.end_date,
            timeframe=self.base_config.timeframe,
            symbols=self.base_config.symbols.copy(),
            lookback_periods=self.base_config.lookback_periods
        )
        
        # Apply parameter overrides
        for param_name, param_value in parameters.items():
            if hasattr(config, param_name):
                setattr(config, param_name, param_value)
        
        return config
    
    def _save_optimization_results(
        self,
        results: OptimizationResult,
        optimization_type: str
    ) -> None:
        """Save optimization results to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"optimization_{optimization_type}_{timestamp}.json"
        filepath = Path("results") / filename
        
        # Create results directory
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to serializable format
        serializable_results = {
            'optimization_type': optimization_type,
            'timestamp': timestamp,
            'best_parameters': results.best_parameters,
            'best_score': results.best_score,
            'optimization_metric': results.optimization_metric,
            'total_combinations': results.total_combinations,
            'successful_runs': results.successful_runs,
            'optimization_time_seconds': results.optimization_time_seconds,
            'all_results': results.all_results
        }
        
        with open(filepath, 'w') as f:
            json.dump(serializable_results, f, indent=2, default=str)
        
        logger.info(f"💾 Optimization results saved to {filepath}")


# Convenience functions for quick optimization
def optimize_strategy_parameters(
    symbols: Optional[List[str]] = None,
    start_date: str = "2023-01-01",
    end_date: str = "2024-01-01",
    optimization_method: str = "grid",
    max_trials: int = 100
) -> OptimizationResult:
    """
    Quick strategy parameter optimization.
    
    Args:
        symbols: Symbols to optimize for
        start_date: Start date for optimization
        end_date: End date for optimization
        optimization_method: "grid" or "bayesian"
        max_trials: Maximum trials/combinations
        
    Returns:
        Optimization results
    """
    from .config import settings
    
    if symbols is None:
        symbols = settings.symbols[:3]  # Use first 3 symbols
    
    # Create base config
    base_config = BacktestConfig(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        initial_capital=30000.0
    )
    
    # Define common parameters to optimize
    parameters = [
        OptimizationParameter("commission_rate", 0.0001, 0.002, 0.0001),
        OptimizationParameter("stop_loss_pct", 0.01, 0.05, 0.005),
        OptimizationParameter("take_profit_pct", 0.015, 0.06, 0.005),
        OptimizationParameter("max_position_size", 0.1, 0.3, 0.05)
    ]
    
    # Create optimizer
    optimizer = StrategyOptimizer(base_config, optimization_metric="sharpe_ratio")
    
    # Run optimization
    if optimization_method == "bayesian":
        return optimizer.bayesian_optimization(parameters, n_trials=max_trials)
    else:
        return optimizer.grid_search(parameters, max_combinations=max_trials)


def validate_strategy_robustness(
    parameters: Dict[str, float],
    symbols: Optional[List[str]] = None,
    start_date: str = "2023-01-01",
    end_date: str = "2024-01-01"
) -> Dict[str, Any]:
    """
    Validate strategy robustness using walk-forward analysis.
    
    Args:
        parameters: Strategy parameters to validate
        symbols: Symbols to test
        start_date: Start date
        end_date: End date
        
    Returns:
        Validation results
    """
    from .config import settings
    
    if symbols is None:
        symbols = settings.symbols[:3]
    
    base_config = BacktestConfig(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        initial_capital=30000.0
    )
    
    optimizer = StrategyOptimizer(base_config)
    
    return optimizer.walk_forward_analysis(parameters)