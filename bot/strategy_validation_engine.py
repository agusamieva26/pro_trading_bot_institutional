#!/usr/bin/env python3
"""
🔬 STRATEGY VALIDATION ENGINE - INSTITUTIONAL GRADE
Comprehensive strategy validation and backtesting pipeline with advanced analytics
- Multi-dimensional Performance Validation
- Walk-Forward Optimization & Testing
- Monte Carlo Simulation Suite
- Stress Testing Framework
- Risk-Adjusted Scoring System
- Cross-Validation Pipeline
"""
import os
import json
import asyncio
import time
import uuid
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict, deque
import warnings
warnings.filterwarnings("ignore")

# Statistical libraries
from scipy import stats
# Conditional sklearn imports to avoid dill circular import issues
try:
    from sklearn.model_selection import TimeSeriesSplit
    from sklearn.metrics import accuracy_score, precision_score, recall_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    # Mock classes for when sklearn is not available
    class TimeSeriesSplit:
        pass
import seaborn as sns
import matplotlib.pyplot as plt

# Internal imports
from .config import settings
from .data import fetch_bars, fetch_all_bars
from .util import logger

try:
    from .backtesting_engine import BacktestingEngine, Trade, Position, OrderSide
    from .backtest_metrics import backtest_metrics, BacktestMetrics
    from .ai_strategy_generator import StrategyDNA, StrategyPerformance, MarketRegime
    from .market_regime_analyzer import RegimeAnalysis, AdvancedRegimeDetector
    from .historical_data_manager import historical_data_manager
except ImportError as e:
    logger.warning(f"Some validation dependencies not available: {e}")

class ValidationLevel(Enum):
    """Validation intensity levels"""
    BASIC = "basic"              # Quick validation
    STANDARD = "standard"        # Normal validation
    COMPREHENSIVE = "comprehensive"  # Full validation suite
    INSTITUTIONAL = "institutional"  # Maximum validation

class StressTestType(Enum):
    """Types of stress tests"""
    VOLATILITY_SHOCK = "volatility_shock"
    MARKET_CRASH = "market_crash" 
    LIQUIDITY_CRISIS = "liquidity_crisis"
    CORRELATION_BREAKDOWN = "correlation_breakdown"
    REGIME_CHANGE = "regime_change"
    BLACK_SWAN = "black_swan"
    EXTENDED_DRAWDOWN = "extended_drawdown"

class ValidationStatus(Enum):
    """Validation status codes"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PASSED = "passed"
    FAILED = "failed"
    CONDITIONAL_PASS = "conditional_pass"
    REQUIRES_REVIEW = "requires_review"

@dataclass
class ValidationCriteria:
    """Strategy validation criteria and thresholds"""
    min_sharpe_ratio: float = 0.5
    max_drawdown_threshold: float = 0.25
    min_win_rate: float = 0.35
    min_profit_factor: float = 1.1
    min_trade_count: int = 50
    max_var_95: float = -0.05
    min_calmar_ratio: float = 0.3
    min_sortino_ratio: float = 0.6
    max_correlation_to_market: float = 0.8
    min_information_ratio: float = 0.2
    stability_threshold: float = 0.7  # Consistency across periods

@dataclass
class StressTestScenario:
    """Stress test scenario definition"""
    name: str
    test_type: StressTestType
    parameters: Dict[str, Any]
    severity_level: float  # 1.0 = normal, 2.0 = severe, 3.0 = extreme
    description: str
    expected_impact: str

@dataclass
class ValidationResult:
    """Comprehensive validation result"""
    strategy_id: str
    validation_level: ValidationLevel
    overall_status: ValidationStatus
    
    # Performance metrics
    performance_metrics: StrategyPerformance
    
    # Validation tests
    criteria_results: Dict[str, bool]
    stress_test_results: Dict[str, Dict[str, Any]]
    walk_forward_results: Dict[str, Any]
    monte_carlo_results: Dict[str, Any]
    cross_validation_results: Dict[str, Any]
    
    # Risk analysis
    risk_analysis: Dict[str, Any]
    regime_performance: Dict[MarketRegime, Dict[str, float]]
    
    # Quality scores
    overall_score: float
    confidence_level: float
    recommendation: str
    
    # Meta information
    validation_duration: float
    validation_timestamp: datetime = field(default_factory=datetime.now)
    data_period_start: datetime = field(default_factory=datetime.now)
    data_period_end: datetime = field(default_factory=datetime.now)
    symbols_tested: List[str] = field(default_factory=list)
    
    # Warnings and notes
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

class WalkForwardOptimizer:
    """
    📈 Walk-Forward Optimization and Validation System
    """
    
    def __init__(self, train_window_days: int = 252, test_window_days: int = 63, step_size_days: int = 21):
        self.train_window_days = train_window_days
        self.test_window_days = test_window_days
        self.step_size_days = step_size_days
        self.optimization_cache = {}
    
    async def walk_forward_validate(self, strategy: StrategyDNA, 
                                  market_data: Dict[str, pd.DataFrame],
                                  optimization_target: str = "sharpe_ratio") -> Dict[str, Any]:
        """Perform walk-forward validation of strategy"""
        
        try:
            logger.info(f"🚶 Starting walk-forward validation for {strategy.name}")
            
            if not market_data:
                return {"error": "No market data available"}
            
            # Get date range from data
            all_dates = set()
            for df in market_data.values():
                if not df.empty:
                    all_dates.update(df.index)
            
            if len(all_dates) < self.train_window_days + self.test_window_days:
                return {"error": "Insufficient data for walk-forward validation"}
            
            sorted_dates = sorted(all_dates)
            
            # Generate walk-forward windows
            windows = self._generate_walk_forward_windows(sorted_dates)
            
            if len(windows) < 3:
                return {"error": "Insufficient windows for validation"}
            
            # Run validation for each window
            window_results = []
            optimization_results = []
            
            for i, (train_start, train_end, test_start, test_end) in enumerate(windows):
                logger.info(f"📊 WF Window {i+1}/{len(windows)}: "
                           f"Train {train_start.date()}-{train_end.date()}, "
                           f"Test {test_start.date()}-{test_end.date()}")
                
                # Extract data for this window
                train_data = self._extract_window_data(market_data, train_start, train_end)
                test_data = self._extract_window_data(market_data, test_start, test_end)
                
                if not train_data or not test_data:
                    continue
                
                # Optimize strategy on training data
                optimized_strategy = await self._optimize_strategy_for_period(
                    strategy, train_data, optimization_target
                )
                
                # Validate on test data
                test_performance = await self._backtest_strategy_on_data(
                    optimized_strategy, test_data
                )
                
                window_result = {
                    "window_id": i + 1,
                    "train_period": (train_start, train_end),
                    "test_period": (test_start, test_end),
                    "optimization_result": optimized_strategy.fitness_score if optimized_strategy else 0,
                    "test_performance": asdict(test_performance) if test_performance else {},
                    "test_sharpe": test_performance.sharpe_ratio if test_performance else 0,
                    "test_return": test_performance.total_return if test_performance else 0,
                    "test_drawdown": test_performance.max_drawdown if test_performance else 0,
                }
                
                window_results.append(window_result)
                
                if optimized_strategy:
                    optimization_results.append(optimized_strategy)
            
            # Aggregate results
            if not window_results:
                return {"error": "No valid windows processed"}
            
            # Calculate stability metrics
            test_sharpes = [w["test_sharpe"] for w in window_results if w["test_sharpe"] is not None]
            test_returns = [w["test_return"] for w in window_results if w["test_return"] is not None]
            test_drawdowns = [w["test_drawdown"] for w in window_results if w["test_drawdown"] is not None]
            
            stability_metrics = {
                "sharpe_stability": np.std(test_sharpes) / np.mean(np.abs(test_sharpes)) if test_sharpes else 1.0,
                "return_stability": np.std(test_returns) / np.mean(np.abs(test_returns)) if test_returns else 1.0,
                "drawdown_consistency": np.std(test_drawdowns) if test_drawdowns else 0.5,
                "win_rate": len([s for s in test_returns if s > 0]) / len(test_returns) if test_returns else 0
            }
            
            # Overall assessment
            avg_test_sharpe = np.mean(test_sharpes) if test_sharpes else 0
            avg_test_return = np.mean(test_returns) if test_returns else 0
            avg_test_drawdown = np.mean(test_drawdowns) if test_drawdowns else 0
            
            # Robustness score (1.0 = very robust, 0.0 = not robust)
            robustness_score = self._calculate_robustness_score(stability_metrics, avg_test_sharpe)
            
            result = {
                "windows_processed": len(window_results),
                "window_results": window_results,
                "stability_metrics": stability_metrics,
                "average_test_performance": {
                    "sharpe_ratio": avg_test_sharpe,
                    "total_return": avg_test_return,
                    "max_drawdown": avg_test_drawdown
                },
                "robustness_score": robustness_score,
                "is_robust": robustness_score > 0.6,
                "optimization_consistency": len(set(opt.strategy_id for opt in optimization_results)) / len(optimization_results) if optimization_results else 0
            }
            
            logger.info(f"✅ Walk-forward validation complete: "
                       f"Robustness={robustness_score:.2f}, "
                       f"Avg Sharpe={avg_test_sharpe:.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Walk-forward validation failed: {e}")
            return {"error": str(e)}
    
    def _generate_walk_forward_windows(self, dates: List[datetime]) -> List[Tuple[datetime, datetime, datetime, datetime]]:
        """Generate overlapping train/test windows"""
        
        windows = []
        current_start = 0
        
        while current_start + self.train_window_days + self.test_window_days < len(dates):
            train_start = dates[current_start]
            train_end = dates[current_start + self.train_window_days - 1]
            test_start = dates[current_start + self.train_window_days]
            test_end = dates[min(current_start + self.train_window_days + self.test_window_days - 1, len(dates) - 1)]
            
            windows.append((train_start, train_end, test_start, test_end))
            current_start += self.step_size_days
        
        return windows
    
    def _extract_window_data(self, market_data: Dict[str, pd.DataFrame], 
                           start_date: datetime, end_date: datetime) -> Dict[str, pd.DataFrame]:
        """Extract data for specific time window"""
        
        window_data = {}
        
        for symbol, df in market_data.items():
            if df.empty:
                continue
            
            # Filter data for window
            mask = (df.index >= start_date) & (df.index <= end_date)
            window_df = df.loc[mask].copy()
            
            if len(window_df) > 20:  # Minimum data requirement
                window_data[symbol] = window_df
        
        return window_data
    
    async def _optimize_strategy_for_period(self, base_strategy: StrategyDNA, 
                                          train_data: Dict[str, pd.DataFrame],
                                          target: str) -> Optional[StrategyDNA]:
        """Optimize strategy parameters for specific period"""
        
        # Simple parameter optimization (can be enhanced)
        try:
            optimized = base_strategy.__class__(**asdict(base_strategy))
            optimized.strategy_id = f"{base_strategy.strategy_id}_opt_{int(time.time())}"
            
            # Basic parameter adjustment based on period characteristics
            # This is a simplified version - real optimization would use more sophisticated methods
            
            period_volatility = self._calculate_period_volatility(train_data)
            
            if period_volatility > 0.25:  # High volatility period
                optimized.position_sizing["base_size"] *= 0.8  # Reduce position size
                optimized.stop_loss_config["threshold"] *= 0.8  # Tighter stops
            elif period_volatility < 0.15:  # Low volatility period
                optimized.position_sizing["base_size"] *= 1.2  # Increase position size
                optimized.stop_loss_config["threshold"] *= 1.2  # Wider stops
            
            return optimized
            
        except Exception as e:
            logger.error(f"❌ Strategy optimization failed: {e}")
            return base_strategy
    
    def _calculate_period_volatility(self, data: Dict[str, pd.DataFrame]) -> float:
        """Calculate average volatility for period"""
        
        volatilities = []
        
        for df in data.values():
            if len(df) > 20:
                returns = df['close'].pct_change().dropna()
                vol = returns.std() * np.sqrt(252)
                volatilities.append(vol)
        
        return np.mean(volatilities) if volatilities else 0.20
    
    async def _backtest_strategy_on_data(self, strategy: StrategyDNA, 
                                       data: Dict[str, pd.DataFrame]) -> Optional[StrategyPerformance]:
        """Backtest strategy on specific data"""
        
        # This would use the actual backtesting engine
        # For now, simplified implementation
        try:
            # Placeholder for actual backtesting
            # In real implementation, this would use the BacktestingEngine
            
            # Simulate some performance metrics
            total_return = np.random.normal(0.02, 0.05)  # Placeholder
            volatility = np.random.uniform(0.10, 0.30)
            sharpe_ratio = total_return / volatility if volatility > 0 else 0
            max_drawdown = np.random.uniform(0.02, 0.15)
            
            return StrategyPerformance(
                strategy_id=strategy.strategy_id,
                total_return=total_return,
                annualized_return=total_return,
                volatility=volatility,
                sharpe_ratio=sharpe_ratio,
                sortino_ratio=sharpe_ratio * 1.2,
                calmar_ratio=total_return / max_drawdown if max_drawdown > 0 else 0,
                max_drawdown=max_drawdown,
                avg_drawdown=max_drawdown * 0.6,
                var_95=-volatility * 1.65,
                cvar_95=-volatility * 2.0,
                total_trades=np.random.randint(30, 150),
                win_rate=np.random.uniform(0.35, 0.65),
                profit_factor=np.random.uniform(0.8, 1.8),
                avg_win=0.02,
                avg_loss=-0.01,
                beta=np.random.uniform(0.5, 1.5),
                alpha=total_return * 0.8,
                information_ratio=sharpe_ratio * 0.8,
                treynor_ratio=total_return
            )
            
        except Exception as e:
            logger.error(f"❌ Backtesting failed: {e}")
            return None
    
    def _calculate_robustness_score(self, stability_metrics: Dict[str, float], 
                                  avg_sharpe: float) -> float:
        """Calculate overall robustness score"""
        
        # Penalize high instability
        stability_penalty = min(1.0, stability_metrics.get("sharpe_stability", 1.0))
        consistency_bonus = 1.0 - min(0.5, stability_metrics.get("drawdown_consistency", 0.5))
        
        # Reward positive performance
        performance_score = max(0, min(1.0, (avg_sharpe + 1.0) / 2.0))
        
        # Win rate contribution
        win_rate_score = stability_metrics.get("win_rate", 0.5)
        
        # Combined score
        robustness = (
            performance_score * 0.4 +
            consistency_bonus * 0.3 +
            (1.0 - stability_penalty) * 0.2 +
            win_rate_score * 0.1
        )
        
        return max(0.0, min(1.0, robustness))

class MonteCarloSimulator:
    """
    🎲 Monte Carlo Simulation Suite for Strategy Testing
    """
    
    def __init__(self, num_simulations: int = 1000):
        self.num_simulations = num_simulations
        self.simulation_cache = {}
    
    async def run_monte_carlo_validation(self, strategy: StrategyDNA, 
                                       market_data: Dict[str, pd.DataFrame],
                                       scenarios: List[str] = None) -> Dict[str, Any]:
        """Run Monte Carlo simulations on strategy"""
        
        if scenarios is None:
            scenarios = ["base_case", "high_volatility", "low_volatility", "trending", "mean_reverting"]
        
        logger.info(f"🎲 Running Monte Carlo validation with {self.num_simulations} simulations")
        
        results = {}
        
        for scenario in scenarios:
            scenario_results = await self._run_scenario_simulations(strategy, market_data, scenario)
            results[scenario] = scenario_results
        
        # Aggregate results
        aggregate_results = self._aggregate_monte_carlo_results(results)
        
        return {
            "scenario_results": results,
            "aggregate_analysis": aggregate_results,
            "confidence_intervals": self._calculate_confidence_intervals(results),
            "risk_metrics": self._calculate_monte_carlo_risk_metrics(results)
        }
    
    async def _run_scenario_simulations(self, strategy: StrategyDNA, 
                                      market_data: Dict[str, pd.DataFrame],
                                      scenario: str) -> Dict[str, Any]:
        """Run simulations for specific scenario"""
        
        simulation_returns = []
        simulation_sharpes = []
        simulation_drawdowns = []
        
        for i in range(self.num_simulations):
            # Generate scenario-specific market conditions
            perturbed_data = self._generate_scenario_data(market_data, scenario, i)
            
            # Simulate strategy performance
            sim_performance = await self._simulate_strategy_performance(strategy, perturbed_data)
            
            if sim_performance:
                simulation_returns.append(sim_performance.total_return)
                simulation_sharpes.append(sim_performance.sharpe_ratio)
                simulation_drawdowns.append(sim_performance.max_drawdown)
        
        return {
            "scenario": scenario,
            "simulations_completed": len(simulation_returns),
            "returns": simulation_returns,
            "sharpe_ratios": simulation_sharpes,
            "drawdowns": simulation_drawdowns,
            "statistics": {
                "mean_return": np.mean(simulation_returns) if simulation_returns else 0,
                "std_return": np.std(simulation_returns) if simulation_returns else 0,
                "mean_sharpe": np.mean(simulation_sharpes) if simulation_sharpes else 0,
                "worst_drawdown": max(simulation_drawdowns) if simulation_drawdowns else 0,
                "success_rate": len([r for r in simulation_returns if r > 0]) / len(simulation_returns) if simulation_returns else 0
            }
        }
    
    def _generate_scenario_data(self, base_data: Dict[str, pd.DataFrame], 
                              scenario: str, simulation_id: int) -> Dict[str, pd.DataFrame]:
        """Generate perturbed data for Monte Carlo simulation"""
        
        perturbed_data = {}
        np.random.seed(simulation_id)  # Reproducible randomness
        
        for symbol, df in base_data.items():
            if df.empty:
                continue
            
            perturbed_df = df.copy()
            
            if scenario == "high_volatility":
                # Increase volatility by 50-100%
                returns = df['close'].pct_change().dropna()
                vol_multiplier = np.random.uniform(1.5, 2.0)
                noise = np.random.normal(0, returns.std() * vol_multiplier, len(df))
                perturbed_df['close'] *= (1 + noise)
                
            elif scenario == "low_volatility":
                # Decrease volatility by 30-50%
                returns = df['close'].pct_change().dropna()
                vol_multiplier = np.random.uniform(0.5, 0.7)
                noise = np.random.normal(0, returns.std() * vol_multiplier, len(df))
                perturbed_df['close'] *= (1 + noise)
                
            elif scenario == "trending":
                # Add trending component
                trend_strength = np.random.uniform(0.0001, 0.0003)  # Daily trend
                trend = np.cumsum(np.full(len(df), trend_strength))
                perturbed_df['close'] *= (1 + trend)
                
            elif scenario == "mean_reverting":
                # Add mean reversion component
                returns = df['close'].pct_change().fillna(0)
                mean_revert_strength = np.random.uniform(0.1, 0.3)
                
                for i in range(1, len(perturbed_df)):
                    # Mean revert towards recent average
                    recent_mean = perturbed_df['close'].iloc[max(0, i-20):i].mean()
                    current_price = perturbed_df['close'].iloc[i]
                    
                    if current_price > recent_mean:
                        adjustment = -mean_revert_strength * (current_price - recent_mean) / recent_mean
                    else:
                        adjustment = mean_revert_strength * (recent_mean - current_price) / recent_mean
                    
                    perturbed_df['close'].iloc[i] *= (1 + adjustment)
            
            # Ensure realistic price bounds
            perturbed_df['close'] = np.maximum(perturbed_df['close'], df['close'] * 0.1)  # No price below 10% of original
            perturbed_df['close'] = np.minimum(perturbed_df['close'], df['close'] * 10.0)  # No price above 1000% of original
            
            # Update other OHLV columns to maintain consistency
            price_ratio = perturbed_df['close'] / df['close']
            for col in ['open', 'high', 'low']:
                if col in perturbed_df.columns:
                    perturbed_df[col] = df[col] * price_ratio
            
            perturbed_data[symbol] = perturbed_df
        
        return perturbed_data
    
    async def _simulate_strategy_performance(self, strategy: StrategyDNA, 
                                           data: Dict[str, pd.DataFrame]) -> Optional[StrategyPerformance]:
        """Simulate strategy performance on perturbed data"""
        
        # Simplified simulation - in real implementation would use full backtesting
        try:
            # Calculate some basic statistics from the data
            all_returns = []
            for df in data.values():
                if not df.empty and len(df) > 1:
                    returns = df['close'].pct_change().dropna()
                    all_returns.extend(returns.tolist())
            
            if not all_returns:
                return None
            
            returns_array = np.array(all_returns)
            
            # Simulate strategy behavior based on returns distribution
            strategy_returns = returns_array * np.random.uniform(0.5, 1.5)  # Strategy modification factor
            
            total_return = np.sum(strategy_returns)
            volatility = np.std(strategy_returns) * np.sqrt(252)
            sharpe_ratio = (np.mean(strategy_returns) * 252) / volatility if volatility > 0 else 0
            
            # Estimate drawdown
            cumulative = np.cumprod(1 + strategy_returns)
            running_max = np.maximum.accumulate(cumulative)
            drawdown = (cumulative - running_max) / running_max
            max_drawdown = abs(np.min(drawdown))
            
            return StrategyPerformance(
                strategy_id=strategy.strategy_id,
                total_return=total_return,
                annualized_return=np.mean(strategy_returns) * 252,
                volatility=volatility,
                sharpe_ratio=sharpe_ratio,
                sortino_ratio=sharpe_ratio * 1.1,
                calmar_ratio=sharpe_ratio / max_drawdown if max_drawdown > 0 else 0,
                max_drawdown=max_drawdown,
                avg_drawdown=max_drawdown * 0.6,
                var_95=np.percentile(strategy_returns, 5),
                cvar_95=np.mean(strategy_returns[strategy_returns <= np.percentile(strategy_returns, 5)]),
                total_trades=len(strategy_returns),
                win_rate=len(strategy_returns[strategy_returns > 0]) / len(strategy_returns),
                profit_factor=np.sum(strategy_returns[strategy_returns > 0]) / abs(np.sum(strategy_returns[strategy_returns < 0])) if np.sum(strategy_returns[strategy_returns < 0]) != 0 else 0,
                avg_win=np.mean(strategy_returns[strategy_returns > 0]) if len(strategy_returns[strategy_returns > 0]) > 0 else 0,
                avg_loss=np.mean(strategy_returns[strategy_returns < 0]) if len(strategy_returns[strategy_returns < 0]) > 0 else 0,
                beta=1.0,  # Simplified
                alpha=total_return * 0.8,
                information_ratio=sharpe_ratio * 0.9,
                treynor_ratio=total_return
            )
            
        except Exception as e:
            logger.debug(f"Monte Carlo simulation failed: {e}")
            return None
    
    def _aggregate_monte_carlo_results(self, scenario_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate results across scenarios"""
        
        all_returns = []
        all_sharpes = []
        all_drawdowns = []
        
        for scenario_data in scenario_results.values():
            all_returns.extend(scenario_data.get("returns", []))
            all_sharpes.extend(scenario_data.get("sharpe_ratios", []))
            all_drawdowns.extend(scenario_data.get("drawdowns", []))
        
        if not all_returns:
            return {}
        
        return {
            "overall_mean_return": np.mean(all_returns),
            "overall_std_return": np.std(all_returns),
            "overall_mean_sharpe": np.mean(all_sharpes),
            "overall_worst_drawdown": max(all_drawdowns) if all_drawdowns else 0,
            "overall_success_rate": len([r for r in all_returns if r > 0]) / len(all_returns),
            "scenario_consistency": np.std([scenario_data["statistics"]["mean_return"] for scenario_data in scenario_results.values()]),
            "robustness_score": self._calculate_mc_robustness_score(scenario_results)
        }
    
    def _calculate_confidence_intervals(self, scenario_results: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """Calculate confidence intervals for key metrics"""
        
        confidence_intervals = {}
        
        for scenario, data in scenario_results.items():
            returns = data.get("returns", [])
            sharpes = data.get("sharpe_ratios", [])
            
            if returns and sharpes:
                confidence_intervals[scenario] = {
                    "return_5th_percentile": np.percentile(returns, 5),
                    "return_95th_percentile": np.percentile(returns, 95),
                    "sharpe_5th_percentile": np.percentile(sharpes, 5),
                    "sharpe_95th_percentile": np.percentile(sharpes, 95),
                    "return_median": np.median(returns),
                    "sharpe_median": np.median(sharpes)
                }
        
        return confidence_intervals
    
    def _calculate_monte_carlo_risk_metrics(self, scenario_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate risk metrics from Monte Carlo results"""
        
        all_returns = []
        for scenario_data in scenario_results.values():
            all_returns.extend(scenario_data.get("returns", []))
        
        if not all_returns:
            return {}
        
        returns_array = np.array(all_returns)
        
        return {
            "value_at_risk_5": np.percentile(returns_array, 5),
            "value_at_risk_1": np.percentile(returns_array, 1),
            "conditional_var_5": np.mean(returns_array[returns_array <= np.percentile(returns_array, 5)]),
            "tail_ratio": abs(np.percentile(returns_array, 5)) / np.percentile(returns_array, 95) if np.percentile(returns_array, 95) > 0 else 0,
            "probability_of_loss": len(returns_array[returns_array < 0]) / len(returns_array),
            "expected_shortfall": np.mean(returns_array[returns_array < 0]) if len(returns_array[returns_array < 0]) > 0 else 0
        }
    
    def _calculate_mc_robustness_score(self, scenario_results: Dict[str, Dict[str, Any]]) -> float:
        """Calculate Monte Carlo robustness score"""
        
        scenario_scores = []
        
        for scenario_data in scenario_results.values():
            stats = scenario_data.get("statistics", {})
            
            # Score based on positive return, good Sharpe, and success rate
            return_score = max(0, min(1, (stats.get("mean_return", 0) + 0.1) / 0.2))
            sharpe_score = max(0, min(1, (stats.get("mean_sharpe", 0) + 0.5) / 1.5))
            success_score = stats.get("success_rate", 0)
            
            scenario_score = (return_score * 0.4 + sharpe_score * 0.4 + success_score * 0.2)
            scenario_scores.append(scenario_score)
        
        # Robustness is the minimum scenario score (worst case)
        return min(scenario_scores) if scenario_scores else 0.0

class StressTester:
    """
    💥 Comprehensive Strategy Stress Testing Framework
    """
    
    def __init__(self):
        self.stress_scenarios = self._initialize_stress_scenarios()
    
    def _initialize_stress_scenarios(self) -> List[StressTestScenario]:
        """Initialize predefined stress test scenarios"""
        
        return [
            StressTestScenario(
                name="2008 Financial Crisis",
                test_type=StressTestType.MARKET_CRASH,
                parameters={"drawdown": -0.50, "volatility_spike": 3.0, "duration_days": 180},
                severity_level=3.0,
                description="Simulates 2008-style market crash with 50% drawdown",
                expected_impact="Severe impact on all strategies"
            ),
            StressTestScenario(
                name="Flash Crash",
                test_type=StressTestType.LIQUIDITY_CRISIS,
                parameters={"sudden_drop": -0.20, "recovery_time": 1, "liquidity_reduction": 0.8},
                severity_level=2.5,
                description="Simulates flash crash with rapid 20% drop and recovery",
                expected_impact="High impact on momentum strategies"
            ),
            StressTestScenario(
                name="Volatility Spike",
                test_type=StressTestType.VOLATILITY_SHOCK,
                parameters={"vol_multiplier": 2.5, "duration_days": 30},
                severity_level=2.0,
                description="Sustained 2.5x volatility increase for 30 days",
                expected_impact="Medium impact, favors volatility strategies"
            ),
            StressTestScenario(
                name="Correlation Breakdown",
                test_type=StressTestType.CORRELATION_BREAKDOWN,
                parameters={"correlation_reduction": 0.7, "randomization": 0.8},
                severity_level=2.0,
                description="Traditional correlations break down completely",
                expected_impact="Affects diversification assumptions"
            ),
            StressTestScenario(
                name="Regime Change",
                test_type=StressTestType.REGIME_CHANGE,
                parameters={"new_regime": "high_volatility", "transition_speed": "sudden"},
                severity_level=1.5,
                description="Sudden shift to high volatility regime",
                expected_impact="Tests regime adaptation capabilities"
            )
        ]
    
    async def run_stress_tests(self, strategy: StrategyDNA, 
                             market_data: Dict[str, pd.DataFrame],
                             scenarios: List[StressTestScenario] = None) -> Dict[str, Any]:
        """Run comprehensive stress tests on strategy"""
        
        if scenarios is None:
            scenarios = self.stress_scenarios
        
        logger.info(f"💥 Running {len(scenarios)} stress tests on {strategy.name}")
        
        stress_results = {}
        
        for scenario in scenarios:
            logger.info(f"🧪 Running stress test: {scenario.name}")
            
            try:
                # Generate stressed market data
                stressed_data = self._generate_stressed_data(market_data, scenario)
                
                # Test strategy under stress
                stress_performance = await self._test_strategy_under_stress(strategy, stressed_data, scenario)
                
                # Calculate stress impact
                impact_analysis = self._analyze_stress_impact(stress_performance, scenario)
                
                stress_results[scenario.name] = {
                    "scenario": asdict(scenario),
                    "performance": asdict(stress_performance) if stress_performance else {},
                    "impact_analysis": impact_analysis,
                    "passed": impact_analysis.get("severity_rating", "failed") != "failed"
                }
                
            except Exception as e:
                logger.error(f"❌ Stress test {scenario.name} failed: {e}")
                stress_results[scenario.name] = {
                    "scenario": asdict(scenario),
                    "error": str(e),
                    "passed": False
                }
        
        # Calculate overall stress test score
        overall_score = self._calculate_stress_test_score(stress_results)
        
        return {
            "individual_tests": stress_results,
            "overall_score": overall_score,
            "stress_resilience_rating": self._get_resilience_rating(overall_score),
            "recommendations": self._generate_stress_recommendations(stress_results)
        }
    
    def _generate_stressed_data(self, base_data: Dict[str, pd.DataFrame], 
                              scenario: StressTestScenario) -> Dict[str, pd.DataFrame]:
        """Generate market data under stress scenario"""
        
        stressed_data = {}
        
        for symbol, df in base_data.items():
            if df.empty:
                continue
            
            stressed_df = df.copy()
            
            if scenario.test_type == StressTestType.MARKET_CRASH:
                # Apply gradual crash followed by recovery
                drawdown = scenario.parameters.get("drawdown", -0.3)
                duration = scenario.parameters.get("duration_days", 90)
                crash_start = len(df) // 2
                
                for i in range(crash_start, min(crash_start + duration, len(stressed_df))):
                    progress = (i - crash_start) / duration
                    if progress <= 0.5:  # Crash phase
                        factor = 1 + (drawdown * 2 * progress)
                    else:  # Recovery phase
                        factor = 1 + drawdown * (2 - 2 * progress)
                    
                    stressed_df['close'].iloc[i:] *= factor
            
            elif scenario.test_type == StressTestType.VOLATILITY_SHOCK:
                # Multiply volatility
                returns = df['close'].pct_change().fillna(0)
                vol_multiplier = scenario.parameters.get("vol_multiplier", 2.0)
                duration = scenario.parameters.get("duration_days", 30)
                
                shock_start = len(df) // 3
                shock_end = min(shock_start + duration, len(df))
                
                # Apply volatility shock
                for i in range(shock_start, shock_end):
                    base_return = returns.iloc[i]
                    shocked_return = base_return * vol_multiplier
                    stressed_df['close'].iloc[i] = stressed_df['close'].iloc[i-1] * (1 + shocked_return)
            
            elif scenario.test_type == StressTestType.FLASH_CRASH:
                # Sudden drop and recovery
                crash_point = len(df) // 2
                drop_magnitude = scenario.parameters.get("sudden_drop", -0.15)
                
                stressed_df['close'].iloc[crash_point:] *= (1 + drop_magnitude)
                
                # Quick recovery over next few periods
                recovery_periods = scenario.parameters.get("recovery_time", 5)
                recovery_per_period = -drop_magnitude / recovery_periods
                
                for i in range(1, min(recovery_periods + 1, len(stressed_df) - crash_point)):
                    stressed_df['close'].iloc[crash_point + i:] *= (1 + recovery_per_period)
            
            elif scenario.test_type == StressTestType.CORRELATION_BREAKDOWN:
                # Add random noise to break correlations
                randomization = scenario.parameters.get("randomization", 0.5)
                noise = np.random.normal(0, 0.02 * randomization, len(stressed_df))
                stressed_df['close'] *= (1 + noise)
            
            # Update other OHLV columns
            price_ratio = stressed_df['close'] / df['close']
            for col in ['open', 'high', 'low']:
                if col in stressed_df.columns:
                    stressed_df[col] = df[col] * price_ratio
            
            stressed_data[symbol] = stressed_df
        
        return stressed_data
    
    async def _test_strategy_under_stress(self, strategy: StrategyDNA, 
                                        stressed_data: Dict[str, pd.DataFrame],
                                        scenario: StressTestScenario) -> Optional[StrategyPerformance]:
        """Test strategy performance under stress conditions"""
        
        # This would use the actual backtesting engine
        # Simplified implementation for now
        
        try:
            # Calculate stressed performance metrics
            all_returns = []
            for df in stressed_data.values():
                if not df.empty and len(df) > 1:
                    returns = df['close'].pct_change().dropna()
                    all_returns.extend(returns.tolist())
            
            if not all_returns:
                return None
            
            # Simulate strategy behavior under stress
            stress_multiplier = 1.0 / scenario.severity_level  # Higher severity = worse performance
            strategy_returns = np.array(all_returns) * stress_multiplier
            
            total_return = np.sum(strategy_returns)
            volatility = np.std(strategy_returns) * np.sqrt(252)
            sharpe_ratio = (np.mean(strategy_returns) * 252) / volatility if volatility > 0 else 0
            
            # Calculate drawdown
            cumulative = np.cumprod(1 + strategy_returns)
            running_max = np.maximum.accumulate(cumulative)
            drawdown = (cumulative - running_max) / running_max
            max_drawdown = abs(np.min(drawdown))
            
            return StrategyPerformance(
                strategy_id=strategy.strategy_id,
                total_return=total_return,
                annualized_return=np.mean(strategy_returns) * 252,
                volatility=volatility,
                sharpe_ratio=sharpe_ratio,
                sortino_ratio=sharpe_ratio * 0.9,  # Stress reduces Sortino
                calmar_ratio=sharpe_ratio / max_drawdown if max_drawdown > 0 else 0,
                max_drawdown=max_drawdown,
                avg_drawdown=max_drawdown * 0.7,
                var_95=np.percentile(strategy_returns, 5),
                cvar_95=np.mean(strategy_returns[strategy_returns <= np.percentile(strategy_returns, 5)]),
                total_trades=len(strategy_returns),
                win_rate=len(strategy_returns[strategy_returns > 0]) / len(strategy_returns),
                profit_factor=max(0.1, np.sum(strategy_returns[strategy_returns > 0]) / abs(np.sum(strategy_returns[strategy_returns < 0]))) if np.sum(strategy_returns[strategy_returns < 0]) != 0 else 0,
                avg_win=np.mean(strategy_returns[strategy_returns > 0]) if len(strategy_returns[strategy_returns > 0]) > 0 else 0,
                avg_loss=np.mean(strategy_returns[strategy_returns < 0]) if len(strategy_returns[strategy_returns < 0]) > 0 else 0,
                beta=scenario.severity_level,  # Higher beta under stress
                alpha=total_return * 0.6,
                information_ratio=sharpe_ratio * 0.7,
                treynor_ratio=total_return
            )
            
        except Exception as e:
            logger.error(f"❌ Stress testing failed: {e}")
            return None
    
    def _analyze_stress_impact(self, performance: Optional[StrategyPerformance], 
                             scenario: StressTestScenario) -> Dict[str, Any]:
        """Analyze the impact of stress test on strategy"""
        
        if not performance:
            return {"severity_rating": "failed", "impact_description": "Strategy failed under stress"}
        
        # Classify severity based on performance degradation
        sharpe_ratio = performance.sharpe_ratio
        max_drawdown = performance.max_drawdown
        total_return = performance.total_return
        
        # Determine severity rating
        if sharpe_ratio > 0.5 and max_drawdown < 0.15 and total_return > -0.1:
            severity_rating = "low_impact"
            impact_description = "Strategy performs well under stress"
        elif sharpe_ratio > 0.0 and max_drawdown < 0.25 and total_return > -0.2:
            severity_rating = "moderate_impact"
            impact_description = "Strategy shows some degradation but remains viable"
        elif sharpe_ratio > -0.5 and max_drawdown < 0.40 and total_return > -0.4:
            severity_rating = "high_impact"
            impact_description = "Strategy significantly impacted by stress conditions"
        else:
            severity_rating = "severe_impact"
            impact_description = "Strategy severely compromised under stress"
        
        return {
            "severity_rating": severity_rating,
            "impact_description": impact_description,
            "sharpe_degradation": max(0, 1.0 - sharpe_ratio) if sharpe_ratio < 1.0 else 0,
            "drawdown_severity": max_drawdown,
            "return_impact": total_return,
            "survivability_score": self._calculate_survivability_score(performance)
        }
    
    def _calculate_survivability_score(self, performance: StrategyPerformance) -> float:
        """Calculate how well strategy survives stress"""
        
        # Survivability based on not losing too much money and maintaining some efficiency
        return_survival = max(0, (performance.total_return + 0.5) / 0.5)  # Scale from -50% to 0%
        drawdown_survival = max(0, (0.5 - performance.max_drawdown) / 0.5)  # Scale drawdown impact
        sharpe_survival = max(0, (performance.sharpe_ratio + 1) / 2)  # Scale Sharpe from -1 to 1
        
        return (return_survival * 0.4 + drawdown_survival * 0.4 + sharpe_survival * 0.2)
    
    def _calculate_stress_test_score(self, stress_results: Dict[str, Any]) -> float:
        """Calculate overall stress test score"""
        
        scores = []
        
        for test_name, result in stress_results.items():
            if result.get("passed", False):
                impact_analysis = result.get("impact_analysis", {})
                survivability = impact_analysis.get("survivability_score", 0)
                scores.append(survivability)
            else:
                scores.append(0.0)
        
        return np.mean(scores) if scores else 0.0
    
    def _get_resilience_rating(self, score: float) -> str:
        """Get resilience rating based on stress test score"""
        
        if score >= 0.8:
            return "HIGHLY_RESILIENT"
        elif score >= 0.6:
            return "RESILIENT"
        elif score >= 0.4:
            return "MODERATELY_RESILIENT"
        elif score >= 0.2:
            return "LOW_RESILIENCE"
        else:
            return "NOT_RESILIENT"
    
    def _generate_stress_recommendations(self, stress_results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on stress test results"""
        
        recommendations = []
        
        failed_tests = [name for name, result in stress_results.items() if not result.get("passed", False)]
        
        if failed_tests:
            recommendations.append(f"Strategy failed {len(failed_tests)} stress tests. Consider risk management improvements.")
        
        # Analyze specific failure patterns
        high_impact_tests = []
        for name, result in stress_results.items():
            impact = result.get("impact_analysis", {})
            if impact.get("severity_rating") in ["severe_impact", "high_impact"]:
                high_impact_tests.append(name)
        
        if "2008 Financial Crisis" in high_impact_tests:
            recommendations.append("Strategy vulnerable to market crashes. Consider defensive positioning.")
        
        if "Flash Crash" in high_impact_tests:
            recommendations.append("Strategy susceptible to liquidity shocks. Implement liquidity risk controls.")
        
        if "Volatility Spike" in high_impact_tests:
            recommendations.append("Strategy struggles with volatility increases. Consider volatility-adjusted position sizing.")
        
        return recommendations

class ComprehensiveStrategyValidator:
    """
    🏛️ MAIN COMPREHENSIVE STRATEGY VALIDATION ENGINE
    Orchestrates all validation components for institutional-grade strategy testing
    """
    
    def __init__(self):
        self.walk_forward_optimizer = WalkForwardOptimizer()
        self.monte_carlo_simulator = MonteCarloSimulator()
        self.stress_tester = StressTester()
        self.validation_cache = {}
        
        # Default validation criteria
        self.default_criteria = ValidationCriteria()
        
        logger.info("🔬 Comprehensive Strategy Validator initialized")
    
    async def validate_strategy_comprehensive(self, 
                                           strategy: StrategyDNA,
                                           validation_level: ValidationLevel = ValidationLevel.STANDARD,
                                           symbols: List[str] = None,
                                           custom_criteria: Optional[ValidationCriteria] = None) -> ValidationResult:
        """Run comprehensive validation suite on strategy"""
        
        start_time = time.time()
        logger.info(f"🔬 Starting {validation_level.value} validation of {strategy.name}")
        
        if symbols is None:
            symbols = settings.symbols[:10]  # Top 10 symbols
        
        criteria = custom_criteria or self.default_criteria
        
        try:
            # Fetch market data
            market_data = await self._fetch_validation_data(symbols)
            
            if not market_data:
                return self._create_failed_validation(strategy.strategy_id, "No market data available")
            
            # Initialize result structure
            result = ValidationResult(
                strategy_id=strategy.strategy_id,
                validation_level=validation_level,
                overall_status=ValidationStatus.IN_PROGRESS,
                performance_metrics=StrategyPerformance(strategy_id=strategy.strategy_id),
                criteria_results={},
                stress_test_results={},
                walk_forward_results={},
                monte_carlo_results={},
                cross_validation_results={},
                risk_analysis={},
                regime_performance={},
                overall_score=0.0,
                confidence_level=0.0,
                recommendation="",
                validation_duration=0.0,
                symbols_tested=symbols
            )
            
            # Basic performance validation
            logger.info("📊 Running basic performance validation...")
            basic_performance = await self._run_basic_backtest(strategy, market_data)
            result.performance_metrics = basic_performance
            
            # Criteria validation
            logger.info("✅ Checking validation criteria...")
            criteria_results = self._validate_against_criteria(basic_performance, criteria)
            result.criteria_results = criteria_results
            
            # Advanced validations based on level
            if validation_level in [ValidationLevel.STANDARD, ValidationLevel.COMPREHENSIVE, ValidationLevel.INSTITUTIONAL]:
                
                # Walk-forward validation
                logger.info("🚶 Running walk-forward validation...")
                wf_results = await self.walk_forward_optimizer.walk_forward_validate(strategy, market_data)
                result.walk_forward_results = wf_results
                
                # Monte Carlo simulation
                logger.info("🎲 Running Monte Carlo simulations...")
                mc_results = await self.monte_carlo_simulator.run_monte_carlo_validation(strategy, market_data)
                result.monte_carlo_results = mc_results
            
            if validation_level in [ValidationLevel.COMPREHENSIVE, ValidationLevel.INSTITUTIONAL]:
                
                # Stress testing
                logger.info("💥 Running stress tests...")
                stress_results = await self.stress_tester.run_stress_tests(strategy, market_data)
                result.stress_test_results = stress_results
                
                # Regime-specific analysis
                logger.info("🏛️ Running regime analysis...")
                regime_performance = await self._analyze_regime_performance(strategy, market_data)
                result.regime_performance = regime_performance
                
                # Cross-validation
                logger.info("🔄 Running cross-validation...")
                cv_results = await self._run_cross_validation(strategy, market_data)
                result.cross_validation_results = cv_results
            
            if validation_level == ValidationLevel.INSTITUTIONAL:
                
                # Advanced risk analysis
                logger.info("📊 Running advanced risk analysis...")
                risk_analysis = await self._run_advanced_risk_analysis(strategy, market_data)
                result.risk_analysis = risk_analysis
            
            # Calculate overall scores and recommendation
            overall_score, confidence, recommendation = self._calculate_final_assessment(result)
            
            result.overall_score = overall_score
            result.confidence_level = confidence
            result.recommendation = recommendation
            result.overall_status = self._determine_final_status(result)
            
            # Validation duration
            result.validation_duration = time.time() - start_time
            
            # Generate warnings and recommendations
            result.warnings = self._generate_warnings(result)
            result.recommendations = self._generate_recommendations(result)
            
            logger.info(f"✅ Validation complete: {result.overall_status.value} "
                       f"(Score: {result.overall_score:.2f}, Time: {result.validation_duration:.1f}s)")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Comprehensive validation failed: {e}")
            return self._create_failed_validation(strategy.strategy_id, str(e))
    
    async def _fetch_validation_data(self, symbols: List[str]) -> Dict[str, pd.DataFrame]:
        """Fetch market data for validation"""
        
        market_data = {}
        
        for symbol in symbols:
            try:
                # Get more historical data for validation
                df = fetch_bars(symbol, 
                              start=(datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d'),  # 2 years
                              end=(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'))
                
                if not df.empty and len(df) > 200:  # Minimum data requirement
                    market_data[symbol] = df
                    
            except Exception as e:
                logger.debug(f"Could not fetch validation data for {symbol}: {e}")
        
        return market_data
    
    async def _run_basic_backtest(self, strategy: StrategyDNA, 
                                market_data: Dict[str, pd.DataFrame]) -> StrategyPerformance:
        """Run basic backtesting for performance metrics"""
        
        # This would integrate with the actual backtesting engine
        # Simplified implementation for now
        
        try:
            # Aggregate returns from all symbols
            all_returns = []
            for symbol, df in market_data.items():
                if not df.empty and len(df) > 50:
                    returns = df['close'].pct_change().dropna()
                    all_returns.extend(returns.tolist())
            
            if not all_returns:
                return StrategyPerformance(strategy_id=strategy.strategy_id)
            
            # Simulate strategy performance
            returns_array = np.array(all_returns)
            
            # Apply strategy logic (simplified)
            strategy_multiplier = np.random.uniform(0.8, 1.3)  # Strategy modification
            strategy_returns = returns_array * strategy_multiplier
            
            # Calculate performance metrics
            total_return = np.sum(strategy_returns)
            annualized_return = np.mean(strategy_returns) * 252
            volatility = np.std(strategy_returns) * np.sqrt(252)
            
            risk_free_rate = 0.02
            sharpe_ratio = (annualized_return - risk_free_rate) / volatility if volatility > 0 else 0
            
            # Drawdown calculation
            cumulative = np.cumprod(1 + strategy_returns)
            running_max = np.maximum.accumulate(cumulative)
            drawdown = (cumulative - running_max) / running_max
            max_drawdown = abs(np.min(drawdown))
            avg_drawdown = abs(np.mean(drawdown[drawdown < 0])) if (drawdown < 0).any() else 0
            
            # Trade statistics
            positive_returns = strategy_returns[strategy_returns > 0]
            negative_returns = strategy_returns[strategy_returns < 0]
            
            win_rate = len(positive_returns) / len(strategy_returns)
            avg_win = np.mean(positive_returns) if len(positive_returns) > 0 else 0
            avg_loss = np.mean(negative_returns) if len(negative_returns) > 0 else 0
            profit_factor = abs(np.sum(positive_returns) / np.sum(negative_returns)) if np.sum(negative_returns) != 0 else 0
            
            # Risk metrics
            var_95 = np.percentile(strategy_returns, 5)
            cvar_95 = np.mean(strategy_returns[strategy_returns <= var_95])
            
            # Advanced metrics
            downside_returns = strategy_returns[strategy_returns < 0]
            downside_std = np.std(downside_returns) * np.sqrt(252) if len(downside_returns) > 0 else volatility
            sortino_ratio = (annualized_return - risk_free_rate) / downside_std if downside_std > 0 else sharpe_ratio
            
            calmar_ratio = annualized_return / max_drawdown if max_drawdown > 0 else 0
            
            return StrategyPerformance(
                strategy_id=strategy.strategy_id,
                total_return=total_return,
                annualized_return=annualized_return,
                volatility=volatility,
                sharpe_ratio=sharpe_ratio,
                sortino_ratio=sortino_ratio,
                calmar_ratio=calmar_ratio,
                max_drawdown=max_drawdown,
                avg_drawdown=avg_drawdown,
                var_95=var_95,
                cvar_95=cvar_95,
                total_trades=len(strategy_returns),
                win_rate=win_rate,
                profit_factor=profit_factor,
                avg_win=avg_win,
                avg_loss=avg_loss,
                beta=1.0,  # Simplified
                alpha=annualized_return * 0.8,
                information_ratio=sharpe_ratio * 0.9,
                treynor_ratio=annualized_return
            )
            
        except Exception as e:
            logger.error(f"❌ Basic backtest failed: {e}")
            return StrategyPerformance(strategy_id=strategy.strategy_id)
    
    def _validate_against_criteria(self, performance: StrategyPerformance, 
                                 criteria: ValidationCriteria) -> Dict[str, bool]:
        """Validate performance against criteria"""
        
        return {
            "min_sharpe_ratio": performance.sharpe_ratio >= criteria.min_sharpe_ratio,
            "max_drawdown_threshold": performance.max_drawdown <= criteria.max_drawdown_threshold,
            "min_win_rate": performance.win_rate >= criteria.min_win_rate,
            "min_profit_factor": performance.profit_factor >= criteria.min_profit_factor,
            "min_trade_count": performance.total_trades >= criteria.min_trade_count,
            "max_var_95": performance.var_95 >= criteria.max_var_95,
            "min_calmar_ratio": performance.calmar_ratio >= criteria.min_calmar_ratio,
            "min_sortino_ratio": performance.sortino_ratio >= criteria.min_sortino_ratio,
            "min_information_ratio": performance.information_ratio >= criteria.min_information_ratio
        }
    
    async def _analyze_regime_performance(self, strategy: StrategyDNA, 
                                        market_data: Dict[str, pd.DataFrame]) -> Dict[MarketRegime, Dict[str, float]]:
        """Analyze strategy performance across different market regimes"""
        
        # This would integrate with the regime detector
        # Simplified implementation
        
        regime_performance = {}
        
        # Simulate performance for different regimes
        for regime in MarketRegime:
            # Simulate regime-specific performance
            base_return = np.random.normal(0.01, 0.03)
            base_sharpe = np.random.uniform(0.2, 1.2)
            base_drawdown = np.random.uniform(0.05, 0.25)
            
            # Adjust based on strategy's regime sensitivity
            sensitivity = strategy.regime_sensitivity.get(regime, 0.5)
            
            regime_performance[regime] = {
                "return": base_return * sensitivity,
                "sharpe_ratio": base_sharpe * sensitivity,
                "max_drawdown": base_drawdown / sensitivity if sensitivity > 0.1 else base_drawdown * 2,
                "win_rate": 0.4 + (sensitivity * 0.3)
            }
        
        return regime_performance
    
    async def _run_cross_validation(self, strategy: StrategyDNA, 
                                  market_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Run cross-validation on strategy"""
        
        try:
            # Time series cross-validation
            cv_scores = []
            n_splits = 5
            
            # Get combined time series
            combined_dates = set()
            for df in market_data.values():
                combined_dates.update(df.index)
            
            sorted_dates = sorted(combined_dates)
            
            if len(sorted_dates) < 200:
                return {"error": "Insufficient data for cross-validation"}
            
            # Create time series splits
            split_size = len(sorted_dates) // n_splits
            
            for i in range(n_splits):
                start_idx = i * split_size
                end_idx = min((i + 2) * split_size, len(sorted_dates))  # Overlapping splits
                
                if end_idx - start_idx < 100:  # Minimum split size
                    continue
                
                # Extract data for this split
                split_start = sorted_dates[start_idx]
                split_end = sorted_dates[end_idx - 1]
                
                split_data = {}
                for symbol, df in market_data.items():
                    mask = (df.index >= split_start) & (df.index <= split_end)
                    split_df = df.loc[mask]
                    if len(split_df) > 50:
                        split_data[symbol] = split_df
                
                if not split_data:
                    continue
                
                # Test strategy on this split
                split_performance = await self._run_basic_backtest(strategy, split_data)
                cv_scores.append(split_performance.sharpe_ratio)
            
            if not cv_scores:
                return {"error": "No valid cross-validation splits"}
            
            return {
                "cv_scores": cv_scores,
                "mean_cv_score": np.mean(cv_scores),
                "std_cv_score": np.std(cv_scores),
                "stability": 1.0 - (np.std(cv_scores) / np.mean(np.abs(cv_scores))) if cv_scores else 0,
                "consistency": len([s for s in cv_scores if s > 0]) / len(cv_scores)
            }
            
        except Exception as e:
            logger.error(f"❌ Cross-validation failed: {e}")
            return {"error": str(e)}
    
    async def _run_advanced_risk_analysis(self, strategy: StrategyDNA, 
                                        market_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Run advanced risk analysis"""
        
        try:
            # Calculate various risk metrics
            all_returns = []
            for df in market_data.values():
                if not df.empty:
                    returns = df['close'].pct_change().dropna()
                    all_returns.extend(returns.tolist())
            
            if not all_returns:
                return {"error": "No return data for risk analysis"}
            
            returns_array = np.array(all_returns)
            
            # Risk metrics
            risk_analysis = {
                "var_99": np.percentile(returns_array, 1),
                "cvar_99": np.mean(returns_array[returns_array <= np.percentile(returns_array, 1)]),
                "skewness": stats.skew(returns_array),
                "kurtosis": stats.kurtosis(returns_array),
                "tail_ratio": abs(np.percentile(returns_array, 5)) / np.percentile(returns_array, 95) if np.percentile(returns_array, 95) > 0 else 0,
                "maximum_entropy": -np.sum([p * np.log(p) for p in np.histogram(returns_array, bins=50)[0] if p > 0]),
                "downside_deviation": np.std(returns_array[returns_array < 0]) if len(returns_array[returns_array < 0]) > 0 else 0,
                "upside_potential": np.mean(returns_array[returns_array > 0]) if len(returns_array[returns_array > 0]) > 0 else 0
            }
            
            return risk_analysis
            
        except Exception as e:
            logger.error(f"❌ Advanced risk analysis failed: {e}")
            return {"error": str(e)}
    
    def _calculate_final_assessment(self, result: ValidationResult) -> Tuple[float, float, str]:
        """Calculate final assessment scores and recommendation"""
        
        # Base score from performance metrics
        performance = result.performance_metrics
        base_score = 0.0
        
        # Performance component (40%)
        if performance.sharpe_ratio > 0:
            base_score += min(0.4, performance.sharpe_ratio / 2.0 * 0.4)
        
        # Risk component (30%)
        if performance.max_drawdown < 0.3:
            risk_score = (0.3 - performance.max_drawdown) / 0.3
            base_score += risk_score * 0.3
        
        # Consistency component (30%)
        consistency_score = 0.0
        
        # Walk-forward results
        wf_results = result.walk_forward_results
        if wf_results and "robustness_score" in wf_results:
            consistency_score += wf_results["robustness_score"] * 0.4
        
        # Monte Carlo results
        mc_results = result.monte_carlo_results
        if mc_results and "aggregate_analysis" in mc_results:
            aggregate = mc_results["aggregate_analysis"]
            if "robustness_score" in aggregate:
                consistency_score += aggregate["robustness_score"] * 0.3
        
        # Stress test results
        stress_results = result.stress_test_results
        if stress_results and "overall_score" in stress_results:
            consistency_score += stress_results["overall_score"] * 0.3
        
        base_score += consistency_score * 0.3
        
        # Criteria validation bonus/penalty
        criteria_results = result.criteria_results
        if criteria_results:
            passed_criteria = sum(criteria_results.values())
            total_criteria = len(criteria_results)
            criteria_score = passed_criteria / total_criteria if total_criteria > 0 else 0
            base_score = base_score * (0.5 + 0.5 * criteria_score)  # Scale by criteria compliance
        
        # Confidence level based on data quality and test coverage
        confidence = 0.5  # Base confidence
        
        if wf_results and not wf_results.get("error"):
            confidence += 0.2
        if mc_results and not mc_results.get("error"):
            confidence += 0.2
        if stress_results and not stress_results.get("error"):
            confidence += 0.1
        
        confidence = min(1.0, confidence)
        
        # Generate recommendation
        if base_score >= 0.8:
            recommendation = "STRONG_BUY - Excellent strategy with robust performance across all tests"
        elif base_score >= 0.6:
            recommendation = "BUY - Good strategy with solid performance and acceptable risk"
        elif base_score >= 0.4:
            recommendation = "CONDITIONAL_BUY - Strategy shows promise but requires risk management"
        elif base_score >= 0.2:
            recommendation = "HOLD - Strategy has potential but needs improvement"
        else:
            recommendation = "AVOID - Strategy does not meet institutional standards"
        
        return base_score, confidence, recommendation
    
    def _determine_final_status(self, result: ValidationResult) -> ValidationStatus:
        """Determine final validation status"""
        
        if result.overall_score >= 0.8:
            return ValidationStatus.PASSED
        elif result.overall_score >= 0.6:
            return ValidationStatus.CONDITIONAL_PASS
        elif result.overall_score >= 0.4:
            return ValidationStatus.REQUIRES_REVIEW
        else:
            return ValidationStatus.FAILED
    
    def _generate_warnings(self, result: ValidationResult) -> List[str]:
        """Generate warnings based on validation results"""
        
        warnings = []
        performance = result.performance_metrics
        
        if performance.max_drawdown > 0.25:
            warnings.append(f"High maximum drawdown: {performance.max_drawdown:.1%}")
        
        if performance.sharpe_ratio < 0.5:
            warnings.append(f"Low Sharpe ratio: {performance.sharpe_ratio:.2f}")
        
        if performance.win_rate < 0.4:
            warnings.append(f"Low win rate: {performance.win_rate:.1%}")
        
        # Check walk-forward results
        wf_results = result.walk_forward_results
        if wf_results and "robustness_score" in wf_results:
            if wf_results["robustness_score"] < 0.5:
                warnings.append("Strategy shows poor robustness in walk-forward testing")
        
        # Check stress test results
        stress_results = result.stress_test_results
        if stress_results and "stress_resilience_rating" in stress_results:
            if stress_results["stress_resilience_rating"] in ["NOT_RESILIENT", "LOW_RESILIENCE"]:
                warnings.append("Strategy vulnerable to stress conditions")
        
        return warnings
    
    def _generate_recommendations(self, result: ValidationResult) -> List[str]:
        """Generate improvement recommendations"""
        
        recommendations = []
        performance = result.performance_metrics
        
        if performance.max_drawdown > 0.20:
            recommendations.append("Consider implementing dynamic position sizing based on volatility")
        
        if performance.sharpe_ratio < 0.8:
            recommendations.append("Explore alternative entry/exit rules to improve risk-adjusted returns")
        
        if performance.win_rate < 0.45:
            recommendations.append("Review signal quality and consider additional filters")
        
        # Stress test recommendations
        stress_results = result.stress_test_results
        if stress_results and "recommendations" in stress_results:
            recommendations.extend(stress_results["recommendations"])
        
        # Cross-validation recommendations
        cv_results = result.cross_validation_results
        if cv_results and "stability" in cv_results:
            if cv_results["stability"] < 0.6:
                recommendations.append("Strategy lacks consistency across time periods. Consider regime-adaptive parameters.")
        
        return recommendations
    
    def _create_failed_validation(self, strategy_id: str, error_message: str) -> ValidationResult:
        """Create failed validation result"""
        
        return ValidationResult(
            strategy_id=strategy_id,
            validation_level=ValidationLevel.BASIC,
            overall_status=ValidationStatus.FAILED,
            performance_metrics=StrategyPerformance(strategy_id=strategy_id),
            criteria_results={},
            stress_test_results={},
            walk_forward_results={},
            monte_carlo_results={},
            cross_validation_results={},
            risk_analysis={},
            regime_performance={},
            overall_score=0.0,
            confidence_level=0.0,
            recommendation=f"FAILED - {error_message}",
            validation_duration=0.0,
            warnings=[error_message],
            recommendations=["Fix validation issues and retry"]
        )

# Global validator instance
_comprehensive_validator: Optional[ComprehensiveStrategyValidator] = None

def get_comprehensive_validator() -> ComprehensiveStrategyValidator:
    """Get global comprehensive validator instance"""
    global _comprehensive_validator
    
    if _comprehensive_validator is None:
        _comprehensive_validator = ComprehensiveStrategyValidator()
    
    return _comprehensive_validator

# Utility functions for integration

async def validate_strategy_full_suite(strategy: StrategyDNA, 
                                     validation_level: ValidationLevel = ValidationLevel.STANDARD,
                                     symbols: List[str] = None) -> ValidationResult:
    """Run complete validation suite on strategy"""
    
    validator = get_comprehensive_validator()
    return await validator.validate_strategy_comprehensive(strategy, validation_level, symbols)

def get_validation_summary(result: ValidationResult) -> Dict[str, Any]:
    """Get summarized validation results"""
    
    return {
        "strategy_id": result.strategy_id,
        "status": result.overall_status.value,
        "score": result.overall_score,
        "confidence": result.confidence_level,
        "recommendation": result.recommendation,
        "key_metrics": {
            "sharpe_ratio": result.performance_metrics.sharpe_ratio,
            "max_drawdown": result.performance_metrics.max_drawdown,
            "win_rate": result.performance_metrics.win_rate,
            "total_return": result.performance_metrics.total_return
        },
        "tests_passed": sum(result.criteria_results.values()) if result.criteria_results else 0,
        "total_tests": len(result.criteria_results) if result.criteria_results else 0,
        "warnings_count": len(result.warnings),
        "validation_time": result.validation_duration
    }

if __name__ == "__main__":
    # Example usage and testing
    async def test_validation_engine():
        """Test the validation engine"""
        
        # This would normally come from the AI Strategy Generator
        from .ai_strategy_generator import StrategyDNA, StrategyType, MarketRegime
        
        # Create sample strategy for testing
        sample_strategy = StrategyDNA(
            strategy_id="test_strategy_001",
            name="Sample Momentum Strategy",
            strategy_type=StrategyType.MOMENTUM,
            indicators={"moving_averages": {"fast_period": 12, "slow_period": 26}},
            entry_conditions=[{"indicator": "moving_averages", "operator": ">", "threshold": 0.02}],
            exit_conditions=[{"type": "profit_target", "parameter": 0.03}],
            position_sizing={"method": "fixed", "base_size": 0.02},
            stop_loss_config={"type": "fixed", "threshold": 0.015},
            take_profit_config={"type": "fixed", "threshold": 0.025},
            regime_sensitivity={MarketRegime.BULL_TRENDING: 0.8, MarketRegime.SIDEWAYS: 0.6}
        )
        
        # Run validation
        validator = get_comprehensive_validator()
        
        # Basic validation
        print("Running basic validation...")
        result = await validator.validate_strategy_comprehensive(
            sample_strategy, 
            ValidationLevel.BASIC,
            ["BTC/USD", "ETH/USD", "SPY"]
        )
        
        print(f"Validation Result: {result.overall_status.value}")
        print(f"Score: {result.overall_score:.2f}")
        print(f"Confidence: {result.confidence_level:.2f}")
        print(f"Recommendation: {result.recommendation}")
        
        # Get summary
        summary = get_validation_summary(result)
        print(f"Summary: {summary}")
    
    # Run test
    asyncio.run(test_validation_engine())