#!/usr/bin/env python3
"""
🧬 AI STRATEGY GENERATOR - INSTITUTIONAL GRADE
Advanced AI-powered system for automatic trading strategy creation, validation, and deployment
- Dynamic Strategy Creation Engine with Genetic Algorithms
- Market Regime Adaptation System
- Strategy DNA System with Multi-objective Optimization
- Institutional Strategy Library & Knowledge Base
- Real-time Strategy Deployment with A/B Testing
- Integration with Advanced Memory RAG System
"""
import os
import json
import asyncio
import time
import uuid
import hashlib
import pickle
import random
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict, deque
import numpy as np
import pandas as pd
from loguru import logger
from sklearn.metrics import accuracy_score
from sklearn.model_selection import cross_val_score, ParameterGrid
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import warnings
warnings.filterwarnings("ignore")

def calculate_sharpe_ratio(returns: np.ndarray, risk_free_rate: float = 0.0) -> float:
    """
    Calculate Sharpe ratio with numerical guards
    
    Args:
        returns: Array of returns
        risk_free_rate: Risk-free rate (default 0.0)
    
    Returns:
        Sharpe ratio, with proper handling of edge cases
    """
    if len(returns) == 0:
        return 0.0
    
    excess_returns = returns - risk_free_rate
    mean_excess = np.mean(excess_returns)
    std_excess = np.std(excess_returns, ddof=1)
    
    # Handle edge cases
    if std_excess == 0 or np.isnan(std_excess) or np.isinf(std_excess):
        return 0.0 if mean_excess <= 0 else np.inf
    
    sharpe = mean_excess / std_excess
    
    # Return 0 for invalid results
    if np.isnan(sharpe) or np.isinf(sharpe):
        return 0.0
    
    return float(sharpe)

# Internal imports
try:
    from .advanced_memory_rag_system import (
        AdvancedMemoryRAGSystem, KnowledgeType, QueryType, KnowledgeEntry, RAGResponse
    )
    from .backtesting_engine import BacktestingEngine, Trade, Position
    from .backtest_metrics import backtest_metrics
    from .multi_model_orchestrator import MultiModelOrchestrator, EnsemblePrediction, ConsensusType
    from .strategy import hybrid_signal, load_trading_model, FEATURES
    from .features import make_features
    from .config import settings
    from .data import fetch_bars, fetch_all_bars
    from .util import logger
    from .historical_data_manager import historical_data_manager
except ImportError as e:
    logger.warning(f"Some advanced integrations not available: {e}")

class StrategyType(Enum):
    """Types of trading strategies that can be generated"""
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    TREND_FOLLOWING = "trend_following"
    STATISTICAL_ARBITRAGE = "statistical_arbitrage"
    VOLATILITY_TRADING = "volatility_trading"
    NEWS_DRIVEN = "news_driven"
    MULTI_TIMEFRAME = "multi_timeframe"
    HYBRID_AI = "hybrid_ai"
    REGIME_ADAPTIVE = "regime_adaptive"

class MarketRegime(Enum):
    """Market regime classifications"""
    BULL_TRENDING = "bull_trending"
    BEAR_TRENDING = "bear_trending"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    SIDEWAYS = "sideways"
    CRISIS = "crisis"
    RECOVERY = "recovery"
    EXPANSION = "expansion"

class StrategyObjective(Enum):
    """Multi-objective optimization targets"""
    PROFIT_MAXIMIZATION = "profit_maximization"
    RISK_MINIMIZATION = "risk_minimization"
    SHARPE_OPTIMIZATION = "sharpe_optimization"
    DRAWDOWN_CONTROL = "drawdown_control"
    WIN_RATE_OPTIMIZATION = "win_rate_optimization"
    VOLATILITY_TARGETING = "volatility_targeting"

@dataclass
class StrategyDNA:
    """Genetic representation of a trading strategy"""
    strategy_id: str
    name: str
    strategy_type: StrategyType
    
    # Technical indicators configuration
    indicators: Dict[str, Dict[str, Any]]
    
    # Entry/Exit rules
    entry_conditions: List[Dict[str, Any]]
    exit_conditions: List[Dict[str, Any]]
    
    # Risk management parameters
    position_sizing: Dict[str, Any]
    stop_loss_config: Dict[str, Any]
    take_profit_config: Dict[str, Any]
    
    # Market regime adaptivity
    regime_sensitivity: Dict[MarketRegime, float]
    
    # Performance characteristics
    expected_sharpe: float = 0.0
    expected_profit: float = 0.0
    expected_drawdown: float = 0.0
    expected_win_rate: float = 0.0
    
    # Genetic characteristics
    generation: int = 0
    parent_ids: List[str] = field(default_factory=list)
    mutation_rate: float = 0.1
    fitness_score: float = 0.0
    
    # Metadata
    created_timestamp: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    validation_results: Dict[str, Any] = field(default_factory=dict)
    deployment_status: str = "untested"  # untested, validated, deployed, retired

@dataclass
class StrategyPerformance:
    """Comprehensive strategy performance metrics"""
    strategy_id: str
    
    # Return metrics
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    
    # Risk metrics
    max_drawdown: float
    avg_drawdown: float
    var_95: float
    cvar_95: float
    
    # Trade metrics
    total_trades: int
    win_rate: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    
    # Advanced metrics
    beta: float
    alpha: float
    information_ratio: float
    treynor_ratio: float
    
    # Regime-specific performance
    regime_performance: Dict[MarketRegime, float] = field(default_factory=dict)
    
    # Validation period
    start_date: datetime = field(default_factory=datetime.now)
    end_date: datetime = field(default_factory=datetime.now)
    evaluation_timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class StrategyGenerationTask:
    """Task for generating new strategies"""
    task_id: str
    generation_type: str  # random, crossover, mutation, evolution
    parent_strategies: List[str]
    target_objectives: List[StrategyObjective]
    market_regime_focus: MarketRegime
    symbols: List[str]
    constraints: Dict[str, Any]
    priority: int = 5
    timestamp: datetime = field(default_factory=datetime.now)

class GeneticStrategyEvolution:
    """
    🧬 Genetic Algorithm Engine for Strategy Evolution
    """
    
    def __init__(self, population_size: int = 50, mutation_rate: float = 0.1):
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.generation_count = 0
        self.best_strategies: List[StrategyDNA] = []
        self.evolution_history: List[Dict[str, Any]] = []
        
        # Strategy building blocks (genes)
        self.indicator_genes = {
            "moving_averages": {
                "fast_period": [5, 10, 12, 15, 20],
                "slow_period": [20, 26, 30, 50, 100],
                "type": ["sma", "ema", "wma"]
            },
            "oscillators": {
                "rsi_period": [8, 14, 21, 30],
                "stoch_k": [5, 14, 21],
                "stoch_d": [3, 5, 9],
                "bb_period": [20, 30, 50],
                "bb_std": [1.5, 2.0, 2.5]
            },
            "momentum": {
                "macd_fast": [8, 12, 15],
                "macd_slow": [20, 26, 30],
                "macd_signal": [7, 9, 12],
                "atr_period": [10, 14, 20],
                "adx_period": [10, 14, 20]
            },
            "volume": {
                "vol_sma": [10, 20, 30],
                "vol_ratio_period": [5, 10, 20],
                "obv_smoothing": [3, 5, 10]
            }
        }
        
        self.condition_operators = ["<", ">", "<=", ">=", "cross_above", "cross_below"]
        self.logic_operators = ["AND", "OR", "NOT"]
        
    def create_random_strategy(self, strategy_type: StrategyType, 
                             regime_focus: MarketRegime = MarketRegime.SIDEWAYS) -> StrategyDNA:
        """Generate a completely random strategy"""
        strategy_id = str(uuid.uuid4())[:8]
        
        # Random indicator configuration
        indicators = {}
        num_indicators = random.randint(3, 6)  # Use 3-6 indicators
        
        selected_categories = random.sample(list(self.indicator_genes.keys()), 
                                          min(num_indicators, len(self.indicator_genes)))
        
        for category in selected_categories:
            category_config = {}
            for param, values in self.indicator_genes[category].items():
                category_config[param] = random.choice(values)
            indicators[category] = category_config
        
        # Random entry conditions
        entry_conditions = []
        num_entry_conditions = random.randint(2, 4)
        
        for _ in range(num_entry_conditions):
            condition = {
                "indicator": random.choice(list(indicators.keys())),
                "parameter": random.choice(list(indicators[random.choice(list(indicators.keys()))].keys())),
                "operator": random.choice(self.condition_operators),
                "threshold": random.uniform(-2, 2),
                "weight": random.uniform(0.1, 1.0)
            }
            entry_conditions.append(condition)
        
        # Random exit conditions
        exit_conditions = []
        num_exit_conditions = random.randint(1, 3)
        
        for _ in range(num_exit_conditions):
            condition = {
                "type": random.choice(["profit_target", "stop_loss", "time_based", "signal_reversal"]),
                "parameter": random.uniform(0.01, 0.05),
                "weight": random.uniform(0.1, 1.0)
            }
            exit_conditions.append(condition)
        
        # Position sizing
        position_sizing = {
            "method": random.choice(["fixed", "volatility_target", "kelly", "risk_parity"]),
            "base_size": random.uniform(0.01, 0.05),
            "max_position": random.uniform(0.1, 0.3),
            "scale_factor": random.uniform(0.8, 1.2)
        }
        
        # Stop loss configuration
        stop_loss_config = {
            "type": random.choice(["fixed", "atr_based", "trailing"]),
            "threshold": random.uniform(0.005, 0.03),
            "trailing_distance": random.uniform(0.001, 0.01)
        }
        
        # Take profit configuration
        take_profit_config = {
            "type": random.choice(["fixed", "dynamic", "partial"]),
            "threshold": random.uniform(0.01, 0.05),
            "partial_levels": [random.uniform(0.01, 0.02), random.uniform(0.02, 0.04)]
        }
        
        # Regime sensitivity
        regime_sensitivity = {}
        for regime in MarketRegime:
            if regime == regime_focus:
                regime_sensitivity[regime] = random.uniform(0.7, 1.0)
            else:
                regime_sensitivity[regime] = random.uniform(0.1, 0.6)
        
        return StrategyDNA(
            strategy_id=strategy_id,
            name=f"{strategy_type.value}_{regime_focus.value}_{strategy_id}",
            strategy_type=strategy_type,
            indicators=indicators,
            entry_conditions=entry_conditions,
            exit_conditions=exit_conditions,
            position_sizing=position_sizing,
            stop_loss_config=stop_loss_config,
            take_profit_config=take_profit_config,
            regime_sensitivity=regime_sensitivity,
            generation=0,
            mutation_rate=self.mutation_rate
        )
    
    def crossover_strategies(self, parent1: StrategyDNA, parent2: StrategyDNA) -> StrategyDNA:
        """Create offspring strategy from two parents"""
        child_id = str(uuid.uuid4())[:8]
        
        # Blend characteristics from both parents
        child_indicators = {}
        
        # Mix indicators from both parents
        all_indicators = set(parent1.indicators.keys()) | set(parent2.indicators.keys())
        for indicator in all_indicators:
            if indicator in parent1.indicators and indicator in parent2.indicators:
                # Blend parameters from both parents
                child_config = {}
                p1_config = parent1.indicators[indicator]
                p2_config = parent2.indicators[indicator]
                
                all_params = set(p1_config.keys()) | set(p2_config.keys())
                for param in all_params:
                    if param in p1_config and param in p2_config:
                        # Choose randomly or blend
                        if isinstance(p1_config[param], (int, float)) and isinstance(p2_config[param], (int, float)):
                            child_config[param] = (p1_config[param] + p2_config[param]) / 2
                        else:
                            child_config[param] = random.choice([p1_config[param], p2_config[param]])
                    else:
                        # Take from available parent
                        child_config[param] = p1_config.get(param) or p2_config.get(param)
                
                child_indicators[indicator] = child_config
            else:
                # Inherit from one parent
                source_parent = parent1 if indicator in parent1.indicators else parent2
                child_indicators[indicator] = source_parent.indicators[indicator].copy()
        
        # Crossover entry/exit conditions
        child_entry_conditions = []
        all_entry_conditions = parent1.entry_conditions + parent2.entry_conditions
        num_conditions = min(len(all_entry_conditions), random.randint(2, 4))
        child_entry_conditions = random.sample(all_entry_conditions, num_conditions)
        
        child_exit_conditions = []
        all_exit_conditions = parent1.exit_conditions + parent2.exit_conditions
        num_exit_conditions = min(len(all_exit_conditions), random.randint(1, 3))
        child_exit_conditions = random.sample(all_exit_conditions, num_exit_conditions)
        
        # Blend other parameters
        child_position_sizing = parent1.position_sizing.copy()
        child_position_sizing.update({
            "base_size": (parent1.position_sizing["base_size"] + parent2.position_sizing["base_size"]) / 2,
            "max_position": (parent1.position_sizing["max_position"] + parent2.position_sizing["max_position"]) / 2
        })
        
        # Blend regime sensitivity
        child_regime_sensitivity = {}
        for regime in MarketRegime:
            p1_sens = parent1.regime_sensitivity.get(regime, 0.5)
            p2_sens = parent2.regime_sensitivity.get(regime, 0.5)
            child_regime_sensitivity[regime] = (p1_sens + p2_sens) / 2
        
        return StrategyDNA(
            strategy_id=child_id,
            name=f"crossover_{parent1.strategy_type.value}_{child_id}",
            strategy_type=parent1.strategy_type,  # Inherit from first parent
            indicators=child_indicators,
            entry_conditions=child_entry_conditions,
            exit_conditions=child_exit_conditions,
            position_sizing=child_position_sizing,
            stop_loss_config=parent1.stop_loss_config.copy(),
            take_profit_config=parent2.take_profit_config.copy(),
            regime_sensitivity=child_regime_sensitivity,
            generation=max(parent1.generation, parent2.generation) + 1,
            parent_ids=[parent1.strategy_id, parent2.strategy_id],
            mutation_rate=self.mutation_rate
        )
    
    def mutate_strategy(self, strategy: StrategyDNA) -> StrategyDNA:
        """Apply random mutations to a strategy"""
        mutated = strategy.__class__(**asdict(strategy))
        mutated.strategy_id = str(uuid.uuid4())[:8]
        mutated.name = f"mutated_{strategy.strategy_type.value}_{mutated.strategy_id}"
        mutated.generation = strategy.generation + 1
        mutated.parent_ids = [strategy.strategy_id]
        
        # Mutate indicators with probability
        for indicator, config in mutated.indicators.items():
            if random.random() < self.mutation_rate:
                for param, value in config.items():
                    if isinstance(value, (int, float)):
                        # Apply gaussian noise
                        noise_factor = random.gauss(0, 0.1)
                        mutated.indicators[indicator][param] = max(0.01, value * (1 + noise_factor))
                    elif isinstance(value, str) and indicator in self.indicator_genes:
                        # Random replacement from valid options
                        if param in self.indicator_genes[indicator]:
                            mutated.indicators[indicator][param] = random.choice(
                                self.indicator_genes[indicator][param]
                            )
        
        # Mutate conditions
        if random.random() < self.mutation_rate:
            if mutated.entry_conditions:
                condition_to_mutate = random.choice(mutated.entry_conditions)
                if 'threshold' in condition_to_mutate:
                    noise = random.gauss(0, 0.2)
                    condition_to_mutate['threshold'] += noise
                if 'weight' in condition_to_mutate:
                    condition_to_mutate['weight'] = max(0.1, min(1.0, 
                        condition_to_mutate['weight'] + random.gauss(0, 0.1)))
        
        # Mutate position sizing
        if random.random() < self.mutation_rate:
            noise = random.gauss(0, 0.05)
            mutated.position_sizing["base_size"] = max(0.01, 
                mutated.position_sizing["base_size"] * (1 + noise))
        
        # Mutate regime sensitivity
        if random.random() < self.mutation_rate:
            regime_to_mutate = random.choice(list(MarketRegime))
            noise = random.gauss(0, 0.1)
            current_sens = mutated.regime_sensitivity.get(regime_to_mutate, 0.5)
            mutated.regime_sensitivity[regime_to_mutate] = max(0.0, min(1.0, current_sens + noise))
        
        return mutated
    
    def evolve_population(self, population: List[StrategyDNA], 
                         performance_scores: List[float]) -> List[StrategyDNA]:
        """Evolve a population of strategies to the next generation"""
        
        # Selection: Keep top performers
        sorted_indices = np.argsort(performance_scores)[::-1]  # Descending order
        elite_size = max(2, self.population_size // 10)  # Top 10%
        elite_strategies = [population[i] for i in sorted_indices[:elite_size]]
        
        # Create next generation
        next_generation = elite_strategies.copy()  # Elitism
        
        while len(next_generation) < self.population_size:
            if random.random() < 0.7:  # 70% crossover
                # Tournament selection
                parent1 = self._tournament_selection(population, performance_scores)
                parent2 = self._tournament_selection(population, performance_scores)
                child = self.crossover_strategies(parent1, parent2)
                
                # Apply mutation
                if random.random() < self.mutation_rate:
                    child = self.mutate_strategy(child)
                
                next_generation.append(child)
            else:  # 30% mutation only
                parent = self._tournament_selection(population, performance_scores)
                mutated_child = self.mutate_strategy(parent)
                next_generation.append(mutated_child)
        
        self.generation_count += 1
        
        # Update evolution history
        generation_stats = {
            "generation": self.generation_count,
            "best_fitness": max(performance_scores),
            "avg_fitness": np.mean(performance_scores),
            "diversity": self._calculate_diversity(population),
            "timestamp": datetime.now()
        }
        self.evolution_history.append(generation_stats)
        
        return next_generation[:self.population_size]
    
    def _tournament_selection(self, population: List[StrategyDNA], 
                            fitness_scores: List[float], tournament_size: int = 3) -> StrategyDNA:
        """Tournament selection for genetic algorithm"""
        tournament_indices = random.sample(range(len(population)), 
                                         min(tournament_size, len(population)))
        tournament_fitness = [fitness_scores[i] for i in tournament_indices]
        winner_idx = tournament_indices[np.argmax(tournament_fitness)]
        return population[winner_idx]
    
    def _calculate_diversity(self, population: List[StrategyDNA]) -> float:
        """Calculate genetic diversity of population"""
        # Simple diversity metric based on strategy types and indicator usage
        strategy_types = [s.strategy_type for s in population]
        type_diversity = len(set(strategy_types)) / len(StrategyType)
        
        # Indicator diversity
        all_indicators = set()
        for strategy in population:
            all_indicators.update(strategy.indicators.keys())
        indicator_diversity = len(all_indicators) / len(self.indicator_genes)
        
        return (type_diversity + indicator_diversity) / 2

class MarketRegimeDetector:
    """
    📊 Advanced Market Regime Detection System
    """
    
    def __init__(self):
        self.regime_cache = {}
        self.regime_history = deque(maxlen=1000)
        self.regime_indicators = {}
        
    def detect_current_regime(self, market_data: Dict[str, pd.DataFrame]) -> MarketRegime:
        """Detect current market regime based on multiple assets"""
        
        if not market_data:
            return MarketRegime.SIDEWAYS
        
        try:
            # Aggregate market indicators
            volatility_scores = []
            trend_scores = []
            correlation_scores = []
            
            for symbol, df in market_data.items():
                if df is None or df.empty or len(df) < 50:
                    continue
                
                # Volatility analysis
                returns = df['close'].pct_change().dropna()
                if len(returns) > 20:
                    vol_20d = returns.tail(20).std() * np.sqrt(252)
                    vol_60d = returns.tail(60).std() * np.sqrt(252) if len(returns) >= 60 else vol_20d
                    vol_ratio = vol_20d / vol_60d if vol_60d > 0 else 1.0
                    volatility_scores.append(vol_ratio)
                
                # Trend analysis
                if len(df) >= 50:
                    sma_20 = df['close'].rolling(20).mean().iloc[-1]
                    sma_50 = df['close'].rolling(50).mean().iloc[-1]
                    current_price = df['close'].iloc[-1]
                    
                    trend_strength = (current_price - sma_50) / sma_50 if sma_50 > 0 else 0
                    trend_consistency = (sma_20 - sma_50) / sma_50 if sma_50 > 0 else 0
                    
                    trend_scores.append(trend_strength + trend_consistency)
            
            # Market-wide correlation analysis
            if len(market_data) > 1:
                price_matrix = pd.DataFrame({
                    symbol: df['close'] if df is not None and not df.empty else pd.Series()
                    for symbol, df in market_data.items()
                }).dropna()
                
                if not price_matrix.empty and price_matrix.shape[1] > 1:
                    correlation_matrix = price_matrix.pct_change().corr()
                    avg_correlation = correlation_matrix.values[
                        np.triu_indices_from(correlation_matrix.values, k=1)
                    ].mean()
                    correlation_scores.append(avg_correlation)
            
            # Regime classification logic
            avg_volatility = np.mean(volatility_scores) if volatility_scores else 1.0
            avg_trend = np.mean(trend_scores) if trend_scores else 0.0
            avg_correlation = np.mean(correlation_scores) if correlation_scores else 0.5
            
            # Decision tree for regime classification
            if avg_volatility > 1.5:  # High volatility
                if abs(avg_trend) > 0.2:  # Strong trend
                    regime = MarketRegime.CRISIS if avg_trend < 0 else MarketRegime.EXPANSION
                else:  # No clear trend
                    regime = MarketRegime.HIGH_VOLATILITY
            elif avg_volatility < 0.7:  # Low volatility
                if abs(avg_trend) > 0.1:  # Moderate trend
                    regime = MarketRegime.BULL_TRENDING if avg_trend > 0 else MarketRegime.BEAR_TRENDING
                else:  # Very little movement
                    regime = MarketRegime.LOW_VOLATILITY
            else:  # Normal volatility
                if avg_trend > 0.1:
                    regime = MarketRegime.BULL_TRENDING
                elif avg_trend < -0.1:
                    regime = MarketRegime.BEAR_TRENDING
                else:
                    regime = MarketRegime.SIDEWAYS
            
            # Cache and update history
            self.regime_cache[datetime.now().date()] = regime
            self.regime_history.append({
                "timestamp": datetime.now(),
                "regime": regime,
                "volatility": avg_volatility,
                "trend": avg_trend,
                "correlation": avg_correlation
            })
            
            logger.info(f"🏛️ Market Regime Detected: {regime.value} "
                       f"(Vol: {avg_volatility:.2f}, Trend: {avg_trend:.2f}, Corr: {avg_correlation:.2f})")
            
            return regime
            
        except Exception as e:
            logger.error(f"❌ Error detecting market regime: {e}")
            return MarketRegime.SIDEWAYS
    
    def get_regime_transition_probability(self, current_regime: MarketRegime) -> Dict[MarketRegime, float]:
        """Calculate probability of transitioning to other regimes"""
        
        # Historical transition matrix (simplified)
        transition_matrix = {
            MarketRegime.BULL_TRENDING: {
                MarketRegime.BULL_TRENDING: 0.70,
                MarketRegime.SIDEWAYS: 0.15,
                MarketRegime.HIGH_VOLATILITY: 0.10,
                MarketRegime.BEAR_TRENDING: 0.05
            },
            MarketRegime.BEAR_TRENDING: {
                MarketRegime.BEAR_TRENDING: 0.60,
                MarketRegime.HIGH_VOLATILITY: 0.20,
                MarketRegime.SIDEWAYS: 0.15,
                MarketRegime.RECOVERY: 0.05
            },
            MarketRegime.SIDEWAYS: {
                MarketRegime.SIDEWAYS: 0.50,
                MarketRegime.BULL_TRENDING: 0.20,
                MarketRegime.BEAR_TRENDING: 0.15,
                MarketRegime.LOW_VOLATILITY: 0.15
            },
            MarketRegime.HIGH_VOLATILITY: {
                MarketRegime.HIGH_VOLATILITY: 0.40,
                MarketRegime.CRISIS: 0.25,
                MarketRegime.RECOVERY: 0.20,
                MarketRegime.SIDEWAYS: 0.15
            },
            MarketRegime.LOW_VOLATILITY: {
                MarketRegime.LOW_VOLATILITY: 0.60,
                MarketRegime.SIDEWAYS: 0.25,
                MarketRegime.BULL_TRENDING: 0.10,
                MarketRegime.EXPANSION: 0.05
            }
        }
        
        # Add default transitions for other regimes
        for regime in MarketRegime:
            if regime not in transition_matrix:
                # Default equal probability distribution
                num_regimes = len(MarketRegime)
                transition_matrix[regime] = {r: 1.0/num_regimes for r in MarketRegime}
        
        return transition_matrix.get(current_regime, {r: 1.0/len(MarketRegime) for r in MarketRegime})

class StrategyValidator:
    """
    🔬 Advanced Strategy Validation & Backtesting System
    """
    
    def __init__(self, memory_rag_system: Optional['AdvancedMemoryRAGSystem'] = None):
        self.memory_rag = memory_rag_system
        self.validation_cache = {}
        self.backtesting_engine = None
        
        try:
            self.backtesting_engine = BacktestingEngine()
        except:
            logger.warning("BacktestingEngine not available, using simplified validation")
    
    async def validate_strategy(self, strategy: StrategyDNA, 
                              symbols: List[str] = None,
                              start_date: datetime = None,
                              end_date: datetime = None) -> StrategyPerformance:
        """Comprehensive strategy validation"""
        
        if symbols is None:
            symbols = settings.symbols[:10]  # Top 10 symbols for validation
        
        if start_date is None:
            start_date = datetime.now() - timedelta(days=365)  # 1 year backtest
        
        if end_date is None:
            end_date = datetime.now() - timedelta(days=1)
        
        try:
            # Generate validation key for caching
            validation_key = self._generate_validation_key(strategy, symbols, start_date, end_date)
            
            if validation_key in self.validation_cache:
                logger.info(f"📋 Using cached validation for strategy {strategy.strategy_id}")
                return self.validation_cache[validation_key]
            
            # Fetch historical data
            logger.info(f"📊 Validating strategy {strategy.name} on {len(symbols)} symbols")
            historical_data = {}
            
            for symbol in symbols:
                try:
                    df = fetch_bars(symbol, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
                    if not df.empty and len(df) > 100:
                        historical_data[symbol] = df
                except Exception as e:
                    logger.debug(f"Could not fetch data for {symbol}: {e}")
            
            if not historical_data:
                logger.warning(f"❌ No historical data available for validation")
                return self._create_empty_performance(strategy.strategy_id)
            
            # Run backtesting simulation
            performance_results = await self._run_backtest_simulation(strategy, historical_data)
            
            # Store in cache
            self.validation_cache[validation_key] = performance_results
            
            # Store validation insights in RAG system
            if self.memory_rag:
                await self._store_validation_insights(strategy, performance_results)
            
            return performance_results
            
        except Exception as e:
            logger.error(f"❌ Strategy validation failed: {e}")
            return self._create_empty_performance(strategy.strategy_id)
    
    def _generate_validation_key(self, strategy: StrategyDNA, symbols: List[str], 
                               start_date: datetime, end_date: datetime) -> str:
        """Generate unique validation key for caching"""
        key_data = {
            "strategy_id": strategy.strategy_id,
            "strategy_hash": hashlib.md5(json.dumps(asdict(strategy), sort_keys=True).encode()).hexdigest()[:8],
            "symbols": sorted(symbols),
            "start_date": start_date.isoformat()[:10],
            "end_date": end_date.isoformat()[:10]
        }
        return hashlib.sha256(json.dumps(key_data, sort_keys=True).encode()).hexdigest()[:16]
    
    async def _run_backtest_simulation(self, strategy: StrategyDNA, 
                                     historical_data: Dict[str, pd.DataFrame]) -> StrategyPerformance:
        """Run comprehensive backtesting simulation"""
        
        # Initialize simulation state
        initial_capital = 100000.0
        current_capital = initial_capital
        positions = {}
        trades = []
        equity_curve = []
        
        # Combine all data with timestamps
        all_timestamps = set()
        for df in historical_data.values():
            if not df.empty:
                all_timestamps.update(df.index)
        
        sorted_timestamps = sorted(all_timestamps)
        
        for timestamp in sorted_timestamps:
            daily_equity = current_capital
            
            # Update positions MTM
            for symbol, position_info in list(positions.items()):
                if symbol in historical_data and timestamp in historical_data[symbol].index:
                    current_price = historical_data[symbol].loc[timestamp, 'close']
                    position_value = position_info['quantity'] * current_price
                    daily_equity += position_value - (position_info['quantity'] * position_info['entry_price'])
            
            equity_curve.append({
                'timestamp': timestamp,
                'equity': daily_equity
            })
            
            # Generate signals for each symbol
            for symbol, df in historical_data.items():
                if timestamp not in df.index:
                    continue
                
                try:
                    # Create features for current timestamp
                    symbol_data = df.loc[:timestamp].tail(100)  # Use last 100 bars for context
                    if len(symbol_data) < 50:
                        continue
                    
                    features_df = make_features(symbol_data, symbol=symbol)
                    if features_df.empty:
                        continue
                    
                    current_row = features_df.iloc[-1]
                    
                    # Generate strategy signal
                    signal = self._generate_strategy_signal(strategy, current_row, symbol)
                    current_price = df.loc[timestamp, 'close']
                    
                    # Position management
                    if symbol in positions:
                        # Check exit conditions
                        should_exit = self._check_exit_conditions(strategy, positions[symbol], 
                                                               current_price, timestamp)
                        
                        if should_exit:
                            # Close position
                            position_info = positions[symbol]
                            trade_pnl = (current_price - position_info['entry_price']) * position_info['quantity']
                            
                            trade = {
                                'symbol': symbol,
                                'entry_price': position_info['entry_price'],
                                'exit_price': current_price,
                                'quantity': position_info['quantity'],
                                'entry_time': position_info['entry_time'],
                                'exit_time': timestamp,
                                'pnl': trade_pnl
                            }
                            trades.append(trade)
                            
                            current_capital += trade_pnl
                            del positions[symbol]
                    
                    else:
                        # Check entry conditions
                        should_enter, position_size = self._check_entry_conditions(
                            strategy, signal, current_capital, current_price
                        )
                        
                        if should_enter and position_size > 0:
                            # Open new position
                            positions[symbol] = {
                                'entry_price': current_price,
                                'quantity': position_size,
                                'entry_time': timestamp,
                                'symbol': symbol
                            }
                            
                except Exception as e:
                    logger.debug(f"Error processing {symbol} at {timestamp}: {e}")
                    continue
        
        # Calculate final performance metrics
        performance = self._calculate_performance_metrics(
            strategy.strategy_id, equity_curve, trades, initial_capital
        )
        
        return performance
    
    def _generate_strategy_signal(self, strategy: StrategyDNA, 
                                current_features: pd.Series, symbol: str) -> float:
        """Generate trading signal based on strategy DNA"""
        
        signal_strength = 0.0
        total_weight = 0.0
        
        try:
            # Process each entry condition
            for condition in strategy.entry_conditions:
                condition_met = False
                condition_strength = 0.0
                
                indicator = condition.get('indicator', '')
                parameter = condition.get('parameter', '')
                operator = condition.get('operator', '>')
                threshold = condition.get('threshold', 0.0)
                weight = condition.get('weight', 1.0)
                
                # Try to get indicator value from features
                feature_name = self._map_condition_to_feature(indicator, parameter)
                
                if feature_name in current_features.index:
                    feature_value = float(current_features[feature_name])
                    
                    # Apply operator logic
                    if operator == '>':
                        condition_met = feature_value > threshold
                        condition_strength = max(0, feature_value - threshold) / max(0.01, abs(threshold))
                    elif operator == '<':
                        condition_met = feature_value < threshold
                        condition_strength = max(0, threshold - feature_value) / max(0.01, abs(threshold))
                    elif operator == '>=':
                        condition_met = feature_value >= threshold
                        condition_strength = max(0, feature_value - threshold) / max(0.01, abs(threshold))
                    elif operator == '<=':
                        condition_met = feature_value <= threshold
                        condition_strength = max(0, threshold - feature_value) / max(0.01, abs(threshold))
                    
                    if condition_met:
                        signal_strength += condition_strength * weight
                        total_weight += weight
            
            # Normalize signal
            if total_weight > 0:
                normalized_signal = signal_strength / total_weight
                return np.clip(normalized_signal, -1.0, 1.0)
            
        except Exception as e:
            logger.debug(f"Error generating signal: {e}")
        
        return 0.0
    
    def _map_condition_to_feature(self, indicator: str, parameter: str) -> str:
        """Map strategy conditions to feature names"""
        
        # Mapping from strategy indicators to actual feature names
        feature_mapping = {
            ('moving_averages', 'fast_period'): 'ema_12',
            ('moving_averages', 'slow_period'): 'ema_26',
            ('oscillators', 'rsi_period'): 'rsi_14',
            ('momentum', 'macd_fast'): 'macd',
            ('momentum', 'macd_signal'): 'macd_sig',
            ('momentum', 'atr_period'): 'atr_14',
            ('volume', 'vol_sma'): 'vol_roll'
        }
        
        # Try exact match first
        if (indicator, parameter) in feature_mapping:
            return feature_mapping[(indicator, parameter)]
        
        # Try partial matches
        if 'moving_averages' in indicator:
            return 'ema_12'  # Default to EMA12
        elif 'oscillators' in indicator:
            return 'rsi_14'  # Default to RSI
        elif 'momentum' in indicator:
            return 'macd'  # Default to MACD
        elif 'volume' in indicator:
            return 'vol_roll'  # Default to volume
        
        # Fallback to return value
        return 'ret_1'
    
    def _check_entry_conditions(self, strategy: StrategyDNA, signal: float, 
                              available_capital: float, current_price: float) -> Tuple[bool, float]:
        """Check if entry conditions are met and calculate position size"""
        
        # Simple entry logic: enter if signal is strong enough
        signal_threshold = 0.3  # Minimum signal strength
        
        if abs(signal) < signal_threshold:
            return False, 0.0
        
        # Calculate position size based on strategy configuration
        sizing_config = strategy.position_sizing
        method = sizing_config.get('method', 'fixed')
        base_size = sizing_config.get('base_size', 0.02)
        max_position = sizing_config.get('max_position', 0.1)
        
        # Calculate position size
        if method == 'fixed':
            position_value = available_capital * base_size
        elif method == 'volatility_target':
            # Simplified volatility targeting
            position_value = available_capital * base_size * min(2.0, abs(signal))
        else:
            position_value = available_capital * base_size
        
        # Apply maximum position limit
        max_position_value = available_capital * max_position
        position_value = min(position_value, max_position_value)
        
        # Convert to quantity
        quantity = position_value / current_price if current_price > 0 else 0
        
        return quantity > 0, quantity
    
    def _check_exit_conditions(self, strategy: StrategyDNA, position_info: Dict, 
                             current_price: float, timestamp: datetime) -> bool:
        """Check if exit conditions are met"""
        
        entry_price = position_info['entry_price']
        entry_time = position_info['entry_time']
        
        # Calculate current P&L
        current_pnl = (current_price - entry_price) / entry_price
        
        # Check stop loss
        stop_loss_config = strategy.stop_loss_config
        stop_loss_threshold = stop_loss_config.get('threshold', 0.02)
        
        if current_pnl <= -stop_loss_threshold:
            return True  # Stop loss triggered
        
        # Check take profit
        take_profit_config = strategy.take_profit_config
        take_profit_threshold = take_profit_config.get('threshold', 0.03)
        
        if current_pnl >= take_profit_threshold:
            return True  # Take profit triggered
        
        # Check time-based exit (simplified)
        time_in_position = (timestamp - entry_time).total_seconds() / 3600  # Hours
        max_hold_time = 24  # 24 hours max hold
        
        if time_in_position > max_hold_time:
            return True  # Time-based exit
        
        return False
    
    def _calculate_performance_metrics(self, strategy_id: str, equity_curve: List[Dict], 
                                     trades: List[Dict], initial_capital: float) -> StrategyPerformance:
        """Calculate comprehensive performance metrics"""
        
        if not equity_curve:
            return self._create_empty_performance(strategy_id)
        
        # Convert equity curve to series
        equity_df = pd.DataFrame(equity_curve)
        equity_series = equity_df.set_index('timestamp')['equity']
        returns = equity_series.pct_change().dropna()
        
        # Basic performance metrics
        total_return = (equity_series.iloc[-1] - initial_capital) / initial_capital
        annualized_return = (1 + total_return) ** (252 / len(equity_series)) - 1
        volatility = returns.std() * np.sqrt(252)
        
        # Risk metrics
        sharpe_ratio = (annualized_return - 0.02) / volatility if volatility > 0 else 0
        downside_returns = returns[returns < 0]
        sortino_ratio = (annualized_return - 0.02) / (downside_returns.std() * np.sqrt(252)) if len(downside_returns) > 0 else sharpe_ratio
        
        # Drawdown analysis
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = abs(drawdown.min())
        avg_drawdown = abs(drawdown[drawdown < 0].mean()) if (drawdown < 0).any() else 0
        
        # Trade analysis
        if trades:
            winning_trades = [t for t in trades if t['pnl'] > 0]
            losing_trades = [t for t in trades if t['pnl'] <= 0]
            
            win_rate = len(winning_trades) / len(trades)
            avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
            avg_loss = np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0
            profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        else:
            win_rate = 0
            avg_win = 0
            avg_loss = 0
            profit_factor = 0
        
        # Risk-adjusted metrics (simplified)
        var_95 = returns.quantile(0.05) if len(returns) > 0 else 0
        cvar_95 = returns[returns <= var_95].mean() if len(returns) > 0 and (returns <= var_95).any() else var_95
        
        return StrategyPerformance(
            strategy_id=strategy_id,
            total_return=total_return,
            annualized_return=annualized_return,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=annualized_return / max_drawdown if max_drawdown > 0 else 0,
            max_drawdown=max_drawdown,
            avg_drawdown=avg_drawdown,
            var_95=var_95,
            cvar_95=cvar_95,
            total_trades=len(trades),
            win_rate=win_rate,
            profit_factor=profit_factor,
            avg_win=avg_win,
            avg_loss=avg_loss,
            beta=0.0,  # Simplified
            alpha=annualized_return,  # Simplified
            information_ratio=sharpe_ratio,  # Simplified
            treynor_ratio=annualized_return,  # Simplified
            start_date=equity_df['timestamp'].iloc[0] if not equity_df.empty else datetime.now(),
            end_date=equity_df['timestamp'].iloc[-1] if not equity_df.empty else datetime.now()
        )
    
    def _create_empty_performance(self, strategy_id: str) -> StrategyPerformance:
        """Create empty performance metrics for failed validations"""
        return StrategyPerformance(
            strategy_id=strategy_id,
            total_return=0.0,
            annualized_return=0.0,
            volatility=0.0,
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
            calmar_ratio=0.0,
            max_drawdown=0.0,
            avg_drawdown=0.0,
            var_95=0.0,
            cvar_95=0.0,
            total_trades=0,
            win_rate=0.0,
            profit_factor=0.0,
            avg_win=0.0,
            avg_loss=0.0,
            beta=0.0,
            alpha=0.0,
            information_ratio=0.0,
            treynor_ratio=0.0
        )
    
    async def _store_validation_insights(self, strategy: StrategyDNA, performance: StrategyPerformance):
        """Store validation insights in RAG memory system"""
        
        if not self.memory_rag:
            return
        
        try:
            # Create knowledge entry for strategy performance
            content = f"""
            Strategy Validation Results:
            - Strategy: {strategy.name} (ID: {strategy.strategy_id})
            - Type: {strategy.strategy_type.value}
            - Generation: {strategy.generation}
            
            Performance Metrics:
            - Total Return: {performance.total_return:.2%}
            - Annualized Return: {performance.annualized_return:.2%}
            - Sharpe Ratio: {performance.sharpe_ratio:.2f}
            - Max Drawdown: {performance.max_drawdown:.2%}
            - Win Rate: {performance.win_rate:.2%}
            - Total Trades: {performance.total_trades}
            
            Strategy Configuration:
            - Indicators: {list(strategy.indicators.keys())}
            - Entry Conditions: {len(strategy.entry_conditions)}
            - Exit Conditions: {len(strategy.exit_conditions)}
            - Position Sizing: {strategy.position_sizing.get('method', 'unknown')}
            """
            
            knowledge_entry = KnowledgeEntry(
                id=f"strategy_validation_{strategy.strategy_id}",
                content=content,
                knowledge_type=KnowledgeType.PERFORMANCE_INSIGHT,
                metadata={
                    "strategy_id": strategy.strategy_id,
                    "strategy_type": strategy.strategy_type.value,
                    "sharpe_ratio": performance.sharpe_ratio,
                    "total_return": performance.total_return,
                    "validation_date": datetime.now().isoformat()
                },
                tags=["strategy_validation", "performance", strategy.strategy_type.value],
                source="ai_strategy_generator"
            )
            
            await self.memory_rag.store_knowledge(knowledge_entry)
            logger.info(f"📚 Stored validation insights for strategy {strategy.strategy_id}")
            
        except Exception as e:
            logger.error(f"❌ Error storing validation insights: {e}")

class StrategyLibrary:
    """
    📚 Institutional Strategy Library & Repository
    """
    
    def __init__(self, db_path: str = "bot/strategy_library.db"):
        self.db_path = db_path
        self.strategies: Dict[str, StrategyDNA] = {}
        self.performance_history: Dict[str, List[StrategyPerformance]] = defaultdict(list)
        self.deployment_history: List[Dict[str, Any]] = []
        
        self._initialize_database()
        self._load_strategies()
    
    def _initialize_database(self):
        """Initialize SQLite database for strategy storage"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS strategies (
                        strategy_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        strategy_type TEXT NOT NULL,
                        strategy_data TEXT NOT NULL,
                        created_timestamp TEXT NOT NULL,
                        last_updated TEXT NOT NULL,
                        deployment_status TEXT DEFAULT 'untested',
                        fitness_score REAL DEFAULT 0.0
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS strategy_performance (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        strategy_id TEXT NOT NULL,
                        performance_data TEXT NOT NULL,
                        evaluation_timestamp TEXT NOT NULL,
                        FOREIGN KEY (strategy_id) REFERENCES strategies (strategy_id)
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS deployment_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        strategy_id TEXT NOT NULL,
                        deployment_type TEXT NOT NULL,
                        deployment_data TEXT NOT NULL,
                        deployment_timestamp TEXT NOT NULL,
                        FOREIGN KEY (strategy_id) REFERENCES strategies (strategy_id)
                    )
                """)
                
                conn.commit()
                logger.info("✅ Strategy library database initialized")
                
        except Exception as e:
            logger.error(f"❌ Error initializing strategy database: {e}")
    
    def _load_strategies(self):
        """Load strategies from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT strategy_id, strategy_data FROM strategies")
                
                for row in cursor.fetchall():
                    strategy_id, strategy_data_json = row
                    try:
                        strategy_data = json.loads(strategy_data_json)
                        
                        # Convert back to StrategyDNA
                        strategy = StrategyDNA(**strategy_data)
                        self.strategies[strategy_id] = strategy
                        
                    except Exception as e:
                        logger.debug(f"Error loading strategy {strategy_id}: {e}")
                
                logger.info(f"📚 Loaded {len(self.strategies)} strategies from library")
                
        except Exception as e:
            logger.error(f"❌ Error loading strategies: {e}")
    
    def add_strategy(self, strategy: StrategyDNA) -> bool:
        """Add new strategy to library"""
        try:
            # Store in memory
            self.strategies[strategy.strategy_id] = strategy
            
            # Store in database
            with sqlite3.connect(self.db_path) as conn:
                strategy_data_json = json.dumps(asdict(strategy), default=str)
                
                conn.execute("""
                    INSERT OR REPLACE INTO strategies 
                    (strategy_id, name, strategy_type, strategy_data, 
                     created_timestamp, last_updated, deployment_status, fitness_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    strategy.strategy_id,
                    strategy.name,
                    strategy.strategy_type.value,
                    strategy_data_json,
                    strategy.created_timestamp.isoformat(),
                    strategy.last_updated.isoformat(),
                    strategy.deployment_status,
                    strategy.fitness_score
                ))
                
                conn.commit()
            
            logger.info(f"📚 Added strategy {strategy.name} to library")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error adding strategy to library: {e}")
            return False
    
    def add_performance_record(self, strategy_id: str, performance: StrategyPerformance) -> bool:
        """Add performance record for a strategy"""
        try:
            # Store in memory
            self.performance_history[strategy_id].append(performance)
            
            # Store in database
            with sqlite3.connect(self.db_path) as conn:
                performance_data_json = json.dumps(asdict(performance), default=str)
                
                conn.execute("""
                    INSERT INTO strategy_performance 
                    (strategy_id, performance_data, evaluation_timestamp)
                    VALUES (?, ?, ?)
                """, (
                    strategy_id,
                    performance_data_json,
                    performance.evaluation_timestamp.isoformat()
                ))
                
                conn.commit()
            
            logger.info(f"📊 Added performance record for strategy {strategy_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error adding performance record: {e}")
            return False
    
    def get_best_strategies(self, strategy_type: Optional[StrategyType] = None, 
                          regime: Optional[MarketRegime] = None, 
                          limit: int = 10) -> List[Tuple[StrategyDNA, StrategyPerformance]]:
        """Get best performing strategies with filters"""
        
        candidates = []
        
        for strategy_id, strategy in self.strategies.items():
            # Apply filters
            if strategy_type and strategy.strategy_type != strategy_type:
                continue
            
            if regime and strategy.regime_sensitivity.get(regime, 0.5) < 0.6:
                continue
            
            # Get latest performance
            if strategy_id in self.performance_history and self.performance_history[strategy_id]:
                latest_performance = self.performance_history[strategy_id][-1]
                
                # Calculate composite score
                composite_score = (
                    latest_performance.sharpe_ratio * 0.3 +
                    latest_performance.total_return * 0.3 +
                    (1 - latest_performance.max_drawdown) * 0.2 +
                    latest_performance.win_rate * 0.2
                )
                
                candidates.append((strategy, latest_performance, composite_score))
        
        # Sort by composite score and return top strategies
        candidates.sort(key=lambda x: x[2], reverse=True)
        return [(strategy, performance) for strategy, performance, _ in candidates[:limit]]
    
    def get_strategy_lineage(self, strategy_id: str) -> List[StrategyDNA]:
        """Get the evolutionary lineage of a strategy"""
        lineage = []
        current_strategy = self.strategies.get(strategy_id)
        
        if not current_strategy:
            return lineage
        
        lineage.append(current_strategy)
        
        # Traverse parent chain
        for parent_id in current_strategy.parent_ids:
            parent_lineage = self.get_strategy_lineage(parent_id)
            lineage.extend(parent_lineage)
        
        return lineage
    
    def retire_strategy(self, strategy_id: str, reason: str = "performance_degradation"):
        """Retire a strategy from active use"""
        if strategy_id in self.strategies:
            self.strategies[strategy_id].deployment_status = "retired"
            self.strategies[strategy_id].last_updated = datetime.now()
            
            # Update database
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        UPDATE strategies 
                        SET deployment_status = 'retired', last_updated = ?
                        WHERE strategy_id = ?
                    """, (datetime.now().isoformat(), strategy_id))
                    conn.commit()
                
                # Record deployment event
                deployment_event = {
                    "strategy_id": strategy_id,
                    "action": "retirement",
                    "reason": reason,
                    "timestamp": datetime.now()
                }
                self.deployment_history.append(deployment_event)
                
                logger.info(f"🏁 Retired strategy {strategy_id}: {reason}")
                
            except Exception as e:
                logger.error(f"❌ Error retiring strategy: {e}")
    
    def get_library_stats(self) -> Dict[str, Any]:
        """Get comprehensive library statistics"""
        
        stats = {
            "total_strategies": len(self.strategies),
            "by_type": defaultdict(int),
            "by_status": defaultdict(int),
            "by_generation": defaultdict(int),
            "performance_summary": {
                "avg_sharpe": 0.0,
                "avg_return": 0.0,
                "avg_drawdown": 0.0,
                "best_sharpe": 0.0,
                "best_return": 0.0
            }
        }
        
        all_performances = []
        
        for strategy in self.strategies.values():
            stats["by_type"][strategy.strategy_type.value] += 1
            stats["by_status"][strategy.deployment_status] += 1
            stats["by_generation"][strategy.generation] += 1
            
            if strategy.strategy_id in self.performance_history:
                performances = self.performance_history[strategy.strategy_id]
                if performances:
                    latest_perf = performances[-1]
                    all_performances.append(latest_perf)
        
        if all_performances:
            stats["performance_summary"]["avg_sharpe"] = np.mean([p.sharpe_ratio for p in all_performances])
            stats["performance_summary"]["avg_return"] = np.mean([p.total_return for p in all_performances])
            stats["performance_summary"]["avg_drawdown"] = np.mean([p.max_drawdown for p in all_performances])
            stats["performance_summary"]["best_sharpe"] = max([p.sharpe_ratio for p in all_performances])
            stats["performance_summary"]["best_return"] = max([p.total_return for p in all_performances])
        
        return stats

class AIStrategyGenerator:
    """
    🧠 MAIN AI STRATEGY GENERATOR SYSTEM
    Orchestrates the entire strategy generation, validation, and deployment pipeline
    """
    
    def __init__(self, memory_rag_system: Optional['AdvancedMemoryRAGSystem'] = None):
        self.memory_rag = memory_rag_system or self._initialize_memory_rag()
        
        # Core components
        self.genetic_engine = GeneticStrategyEvolution(population_size=30, mutation_rate=0.15)
        self.regime_detector = MarketRegimeDetector()
        self.validator = StrategyValidator(self.memory_rag)
        self.library = StrategyLibrary()
        
        # System state
        self.current_population: List[StrategyDNA] = []
        self.active_strategies: Dict[str, StrategyDNA] = {}
        self.generation_tasks = deque(maxlen=1000)
        self.validation_queue = deque(maxlen=500)
        
        # Performance tracking
        self.system_metrics = {
            "strategies_generated": 0,
            "strategies_validated": 0,
            "strategies_deployed": 0,
            "avg_generation_time": 0.0,
            "avg_validation_time": 0.0,
            "best_sharpe_achieved": 0.0,
            "system_start_time": datetime.now()
        }
        
        # Threading for background processing
        self.generation_thread = None
        self.validation_thread = None
        self.running = False
        
        logger.info("🧬 AI Strategy Generator initialized")
    
    def _initialize_memory_rag(self) -> Optional['AdvancedMemoryRAGSystem']:
        """Initialize RAG system if available"""
        try:
            from .advanced_memory_rag_system import AdvancedMemoryRAGSystem
            return AdvancedMemoryRAGSystem()
        except Exception as e:
            logger.warning(f"RAG system not available: {e}")
            return None
    
    async def start_system(self):
        """Start the AI Strategy Generator system"""
        if self.running:
            logger.warning("🔄 System already running")
            return
        
        self.running = True
        logger.info("🚀 Starting AI Strategy Generator system...")
        
        # Initialize with random population if empty
        if not self.current_population:
            await self.generate_initial_population()
        
        # Start background threads
        self.generation_thread = threading.Thread(target=self._generation_worker, daemon=True)
        self.validation_thread = threading.Thread(target=self._validation_worker, daemon=True)
        
        self.generation_thread.start()
        self.validation_thread.start()
        
        logger.info("✅ AI Strategy Generator system started")
    
    async def stop_system(self):
        """Stop the AI Strategy Generator system"""
        self.running = False
        logger.info("🛑 Stopping AI Strategy Generator system...")
        
        # Wait for threads to finish
        if self.generation_thread:
            self.generation_thread.join(timeout=5.0)
        if self.validation_thread:
            self.validation_thread.join(timeout=5.0)
        
        logger.info("✅ AI Strategy Generator system stopped")
    
    async def generate_initial_population(self, size: int = 20):
        """Generate initial random population of strategies"""
        logger.info(f"🌱 Generating initial population of {size} strategies...")
        
        start_time = time.time()
        
        # Get current market regime for context
        try:
            # Fetch recent market data for regime detection
            market_data = {}
            for symbol in settings.symbols[:5]:  # Use top 5 symbols
                try:
                    df = fetch_bars(symbol, start=None, end=None, min_bars=100)
                    if not df.empty:
                        market_data[symbol] = df
                except:
                    continue
            
            current_regime = self.regime_detector.detect_current_regime(market_data)
        except:
            current_regime = MarketRegime.SIDEWAYS
        
        # Generate diverse strategy types
        strategy_types = list(StrategyType)
        self.current_population = []
        
        for i in range(size):
            strategy_type = random.choice(strategy_types)
            strategy = self.genetic_engine.create_random_strategy(strategy_type, current_regime)
            
            # Add to population and library
            self.current_population.append(strategy)
            self.library.add_strategy(strategy)
            
            self.system_metrics["strategies_generated"] += 1
        
        generation_time = time.time() - start_time
        self.system_metrics["avg_generation_time"] = generation_time / size
        
        logger.info(f"✅ Generated {len(self.current_population)} initial strategies "
                   f"in {generation_time:.2f}s (regime: {current_regime.value})")
    
    async def generate_new_strategies(self, count: int = 5, 
                                    strategy_type: Optional[StrategyType] = None,
                                    market_regime: Optional[MarketRegime] = None) -> List[StrategyDNA]:
        """Generate new strategies using various methods"""
        
        generated_strategies = []
        
        # Detect current market regime if not provided
        if market_regime is None:
            try:
                market_data = fetch_all_bars(settings.symbols[:3], start="", end="", min_bars=50)
                market_regime = self.regime_detector.detect_current_regime(market_data)
            except:
                market_regime = MarketRegime.SIDEWAYS
        
        for i in range(count):
            try:
                generation_method = random.choices(
                    ['random', 'crossover', 'mutation', 'best_practices'],
                    weights=[0.3, 0.4, 0.2, 0.1]  # Favor crossover and mutation
                )[0]
                
                strategy = None
                
                if generation_method == 'random':
                    # Generate completely random strategy
                    selected_type = strategy_type or random.choice(list(StrategyType))
                    strategy = self.genetic_engine.create_random_strategy(selected_type, market_regime)
                
                elif generation_method == 'crossover' and len(self.current_population) >= 2:
                    # Crossover of existing strategies
                    parent1, parent2 = random.sample(self.current_population, 2)
                    strategy = self.genetic_engine.crossover_strategies(parent1, parent2)
                
                elif generation_method == 'mutation' and self.current_population:
                    # Mutation of existing strategy
                    parent = random.choice(self.current_population)
                    strategy = self.genetic_engine.mutate_strategy(parent)
                
                elif generation_method == 'best_practices':
                    # Generate based on best performing strategies
                    best_strategies = self.library.get_best_strategies(strategy_type, market_regime, limit=3)
                    if best_strategies:
                        parent_strategy, _ = random.choice(best_strategies)
                        strategy = self.genetic_engine.mutate_strategy(parent_strategy)
                    else:
                        # Fallback to random
                        selected_type = strategy_type or random.choice(list(StrategyType))
                        strategy = self.genetic_engine.create_random_strategy(selected_type, market_regime)
                
                if strategy:
                    generated_strategies.append(strategy)
                    self.library.add_strategy(strategy)
                    self.system_metrics["strategies_generated"] += 1
                    
                    logger.debug(f"🧬 Generated strategy {strategy.name} via {generation_method}")
                
            except Exception as e:
                logger.error(f"❌ Error generating strategy {i}: {e}")
                continue
        
        logger.info(f"✨ Generated {len(generated_strategies)} new strategies "
                   f"for regime {market_regime.value}")
        
        return generated_strategies
    
    async def validate_strategy_batch(self, strategies: List[StrategyDNA],
                                    symbols: List[str] = None) -> List[Tuple[StrategyDNA, StrategyPerformance]]:
        """Validate a batch of strategies"""
        
        if not strategies:
            return []
        
        if symbols is None:
            symbols = settings.symbols[:8]  # Use top 8 symbols for validation
        
        logger.info(f"🔬 Validating {len(strategies)} strategies on {len(symbols)} symbols...")
        
        validation_results = []
        start_time = time.time()
        
        for strategy in strategies:
            try:
                performance = await self.validator.validate_strategy(strategy, symbols)
                validation_results.append((strategy, performance))
                
                # Update strategy fitness score
                strategy.fitness_score = self._calculate_fitness_score(performance)
                
                # Store performance in library
                self.library.add_performance_record(strategy.strategy_id, performance)
                
                # Update system metrics
                self.system_metrics["strategies_validated"] += 1
                if performance.sharpe_ratio > self.system_metrics["best_sharpe_achieved"]:
                    self.system_metrics["best_sharpe_achieved"] = performance.sharpe_ratio
                
                logger.debug(f"✅ Validated {strategy.name}: "
                           f"Sharpe={performance.sharpe_ratio:.2f}, "
                           f"Return={performance.total_return:.2%}")
                
            except Exception as e:
                logger.error(f"❌ Validation failed for {strategy.strategy_id}: {e}")
                continue
        
        validation_time = time.time() - start_time
        self.system_metrics["avg_validation_time"] = validation_time / len(strategies)
        
        # Sort by performance
        validation_results.sort(key=lambda x: x[1].sharpe_ratio, reverse=True)
        
        logger.info(f"🏆 Validation complete: {len(validation_results)} strategies validated "
                   f"in {validation_time:.2f}s")
        
        return validation_results
    
    def _calculate_fitness_score(self, performance: StrategyPerformance) -> float:
        """Calculate multi-objective fitness score"""
        
        # Multi-objective optimization
        profit_score = max(0, performance.total_return) * 100
        risk_score = max(0, performance.sharpe_ratio) * 50
        consistency_score = max(0, performance.win_rate) * 30
        drawdown_penalty = performance.max_drawdown * 100
        
        fitness = profit_score + risk_score + consistency_score - drawdown_penalty
        
        return max(0, fitness)
    
    async def evolve_population(self) -> bool:
        """Evolve the current population to next generation"""
        
        if len(self.current_population) < 10:
            logger.warning("⚠️ Population too small for evolution")
            return False
        
        logger.info(f"🧬 Evolving population (generation {self.genetic_engine.generation_count + 1})")
        
        try:
            # Validate current population
            validation_results = await self.validate_strategy_batch(self.current_population)
            
            if not validation_results:
                logger.error("❌ No valid strategies for evolution")
                return False
            
            # Extract fitness scores
            strategies, performances = zip(*validation_results)
            fitness_scores = [perf.sharpe_ratio for perf in performances]
            
            # Evolve to next generation
            next_generation = self.genetic_engine.evolve_population(
                list(strategies), fitness_scores
            )
            
            # Update population
            self.current_population = next_generation
            
            # Add new strategies to library
            for strategy in next_generation:
                self.library.add_strategy(strategy)
            
            # Log evolution statistics
            best_fitness = max(fitness_scores)
            avg_fitness = np.mean(fitness_scores)
            
            logger.info(f"🚀 Evolution complete: Gen {self.genetic_engine.generation_count}, "
                       f"Best Fitness: {best_fitness:.3f}, Avg: {avg_fitness:.3f}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Evolution failed: {e}")
            return False
    
    def deploy_strategy(self, strategy: StrategyDNA, deployment_type: str = "live") -> bool:
        """Deploy strategy for live trading"""
        
        try:
            # Validate strategy is ready for deployment
            if strategy.deployment_status != "validated":
                logger.warning(f"⚠️ Strategy {strategy.strategy_id} not validated for deployment")
                return False
            
            # Check performance requirements
            if strategy.strategy_id in self.library.performance_history:
                latest_perf = self.library.performance_history[strategy.strategy_id][-1]
                
                if latest_perf.sharpe_ratio < 0.5:
                    logger.warning(f"⚠️ Strategy {strategy.strategy_id} has low Sharpe ratio: {latest_perf.sharpe_ratio:.2f}")
                    return False
                
                if latest_perf.max_drawdown > 0.15:
                    logger.warning(f"⚠️ Strategy {strategy.strategy_id} has high drawdown: {latest_perf.max_drawdown:.2%}")
                    return False
            
            # Deploy strategy
            self.active_strategies[strategy.strategy_id] = strategy
            strategy.deployment_status = "deployed"
            strategy.last_updated = datetime.now()
            
            # Update library
            self.library.add_strategy(strategy)
            
            # Record deployment
            deployment_event = {
                "strategy_id": strategy.strategy_id,
                "deployment_type": deployment_type,
                "timestamp": datetime.now(),
                "performance_at_deployment": self.library.performance_history[strategy.strategy_id][-1].__dict__ if strategy.strategy_id in self.library.performance_history else {}
            }
            self.library.deployment_history.append(deployment_event)
            
            self.system_metrics["strategies_deployed"] += 1
            
            logger.info(f"🚀 Deployed strategy {strategy.name} for {deployment_type} trading")
            
            # Store deployment knowledge in RAG
            if self.memory_rag:
                asyncio.create_task(self._store_deployment_knowledge(strategy, deployment_event))
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Strategy deployment failed: {e}")
            return False
    
    async def _store_deployment_knowledge(self, strategy: StrategyDNA, deployment_event: Dict):
        """Store deployment knowledge in RAG system"""
        
        try:
            content = f"""
            Strategy Deployment Event:
            - Strategy: {strategy.name} (ID: {strategy.strategy_id})
            - Type: {strategy.strategy_type.value}
            - Generation: {strategy.generation}
            - Deployment Type: {deployment_event['deployment_type']}
            - Deployment Time: {deployment_event['timestamp']}
            
            Strategy Characteristics:
            - Indicators: {list(strategy.indicators.keys())}
            - Entry Conditions: {len(strategy.entry_conditions)}
            - Exit Conditions: {len(strategy.exit_conditions)}
            - Position Sizing Method: {strategy.position_sizing.get('method', 'unknown')}
            
            Deployment Rationale:
            - Passed validation requirements
            - Met performance thresholds
            - Ready for live trading implementation
            """
            
            knowledge_entry = KnowledgeEntry(
                id=f"strategy_deployment_{strategy.strategy_id}",
                content=content,
                knowledge_type=KnowledgeType.TRADING_DECISION,
                metadata={
                    "strategy_id": strategy.strategy_id,
                    "deployment_type": deployment_event['deployment_type'],
                    "deployment_timestamp": deployment_event['timestamp'].isoformat()
                },
                tags=["strategy_deployment", "live_trading", strategy.strategy_type.value],
                source="ai_strategy_generator"
            )
            
            await self.memory_rag.store_knowledge(knowledge_entry)
            
        except Exception as e:
            logger.error(f"❌ Error storing deployment knowledge: {e}")
    
    def get_best_strategy_for_regime(self, regime: MarketRegime, 
                                   strategy_type: Optional[StrategyType] = None) -> Optional[StrategyDNA]:
        """Get the best strategy for a specific market regime"""
        
        best_strategies = self.library.get_best_strategies(strategy_type, regime, limit=1)
        
        if best_strategies:
            strategy, performance = best_strategies[0]
            logger.info(f"🎯 Best strategy for {regime.value}: {strategy.name} "
                       f"(Sharpe: {performance.sharpe_ratio:.2f})")
            return strategy
        
        logger.warning(f"⚠️ No suitable strategy found for regime {regime.value}")
        return None
    
    def _generation_worker(self):
        """Background worker for strategy generation"""
        while self.running:
            try:
                if len(self.generation_tasks) > 0:
                    task = self.generation_tasks.popleft()
                    # Process generation task
                    asyncio.run(self._process_generation_task(task))
                else:
                    time.sleep(5)  # Wait for new tasks
            except Exception as e:
                logger.error(f"❌ Generation worker error: {e}")
                time.sleep(10)
    
    def _validation_worker(self):
        """Background worker for strategy validation"""
        while self.running:
            try:
                if len(self.validation_queue) > 0:
                    strategies_to_validate = []
                    # Batch up to 5 strategies for efficient validation
                    for _ in range(min(5, len(self.validation_queue))):
                        strategies_to_validate.append(self.validation_queue.popleft())
                    
                    if strategies_to_validate:
                        asyncio.run(self.validate_strategy_batch(strategies_to_validate))
                else:
                    time.sleep(10)  # Wait for new strategies
            except Exception as e:
                logger.error(f"❌ Validation worker error: {e}")
                time.sleep(15)
    
    async def _process_generation_task(self, task: StrategyGenerationTask):
        """Process a strategy generation task"""
        try:
            if task.generation_type == "evolution":
                await self.evolve_population()
            elif task.generation_type == "new_batch":
                strategies = await self.generate_new_strategies(
                    count=5, 
                    market_regime=task.market_regime_focus
                )
                # Add to validation queue
                for strategy in strategies:
                    self.validation_queue.append(strategy)
            
        except Exception as e:
            logger.error(f"❌ Error processing generation task: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        
        uptime = datetime.now() - self.system_metrics["system_start_time"]
        
        status = {
            "running": self.running,
            "uptime_hours": uptime.total_seconds() / 3600,
            "current_population_size": len(self.current_population),
            "active_strategies": len(self.active_strategies),
            "generation_tasks_queued": len(self.generation_tasks),
            "validation_queue_size": len(self.validation_queue),
            "metrics": self.system_metrics.copy(),
            "library_stats": self.library.get_library_stats(),
            "genetic_engine": {
                "generation": self.genetic_engine.generation_count,
                "evolution_history": len(self.genetic_engine.evolution_history)
            }
        }
        
        return status
    
    async def optimize_for_regime(self, target_regime: MarketRegime, 
                                objectives: List[StrategyObjective] = None) -> List[StrategyDNA]:
        """Optimize strategies specifically for a market regime"""
        
        if objectives is None:
            objectives = [StrategyObjective.SHARPE_OPTIMIZATION, StrategyObjective.DRAWDOWN_CONTROL]
        
        logger.info(f"🎯 Optimizing strategies for regime: {target_regime.value}")
        
        # Generate regime-specific strategies
        regime_strategies = await self.generate_new_strategies(
            count=10, 
            market_regime=target_regime
        )
        
        # Validate with regime-specific data
        symbols_for_regime = self._get_symbols_for_regime(target_regime)
        validation_results = await self.validate_strategy_batch(regime_strategies, symbols_for_regime)
        
        # Filter and rank by objectives
        optimized_strategies = self._rank_by_objectives(validation_results, objectives)
        
        logger.info(f"✅ Optimized {len(optimized_strategies)} strategies for {target_regime.value}")
        
        return [strategy for strategy, _ in optimized_strategies[:5]]  # Top 5
    
    def _get_symbols_for_regime(self, regime: MarketRegime) -> List[str]:
        """Get symbols most suitable for a market regime"""
        
        # Regime-specific symbol selection logic
        if regime in [MarketRegime.BULL_TRENDING, MarketRegime.EXPANSION]:
            # Growth and momentum symbols
            return ["TSLA", "NVDA", "QQQ", "BTC/USD", "ETH/USD", "SPY"]
        
        elif regime in [MarketRegime.BEAR_TRENDING, MarketRegime.CRISIS]:
            # Defensive and volatility symbols
            return ["GLD", "TLT", "VIX", "JPM", "JNJ", "PG"]
        
        elif regime == MarketRegime.HIGH_VOLATILITY:
            # High volatility crypto and stocks
            return ["BTC/USD", "ETH/USD", "TSLA", "AMD", "SHIB/USD", "DOGE/USD"]
        
        else:  # SIDEWAYS, LOW_VOLATILITY, RECOVERY
            # Balanced selection
            return settings.symbols[:10]
    
    def _rank_by_objectives(self, validation_results: List[Tuple[StrategyDNA, StrategyPerformance]], 
                          objectives: List[StrategyObjective]) -> List[Tuple[StrategyDNA, StrategyPerformance]]:
        """Rank strategies by multiple objectives"""
        
        def calculate_objective_score(performance: StrategyPerformance) -> float:
            score = 0.0
            
            for objective in objectives:
                if objective == StrategyObjective.PROFIT_MAXIMIZATION:
                    score += performance.total_return * 100
                elif objective == StrategyObjective.SHARPE_OPTIMIZATION:
                    score += performance.sharpe_ratio * 50
                elif objective == StrategyObjective.DRAWDOWN_CONTROL:
                    score += (1 - performance.max_drawdown) * 30
                elif objective == StrategyObjective.WIN_RATE_OPTIMIZATION:
                    score += performance.win_rate * 20
                elif objective == StrategyObjective.RISK_MINIMIZATION:
                    score += max(0, 2 - performance.volatility) * 25
            
            return score
        
        # Calculate objective scores and sort
        scored_results = []
        for strategy, performance in validation_results:
            objective_score = calculate_objective_score(performance)
            scored_results.append((strategy, performance, objective_score))
        
        scored_results.sort(key=lambda x: x[2], reverse=True)
        
        return [(strategy, performance) for strategy, performance, _ in scored_results]


# Global instance for system-wide access
ai_strategy_generator: Optional[AIStrategyGenerator] = None

async def initialize_ai_strategy_generator() -> AIStrategyGenerator:
    """Initialize and start the AI Strategy Generator system"""
    global ai_strategy_generator
    
    if ai_strategy_generator is None:
        logger.info("🧬 Initializing AI Strategy Generator...")
        ai_strategy_generator = AIStrategyGenerator()
        await ai_strategy_generator.start_system()
    
    return ai_strategy_generator

async def get_ai_strategy_generator() -> Optional[AIStrategyGenerator]:
    """Get the global AI Strategy Generator instance"""
    return ai_strategy_generator

# Utility functions for integration with main trading system

def get_best_strategy_signal(symbol: str, market_data: pd.DataFrame, 
                           current_regime: MarketRegime = None) -> Tuple[float, str, Dict[str, Any]]:
    """
    Get trading signal from the best AI-generated strategy for current conditions
    
    Returns:
        Tuple of (signal_strength, strategy_name, metadata)
    """
    
    try:
        if ai_strategy_generator is None:
            return 0.0, "no_ai_system", {}
        
        # Detect current regime if not provided
        if current_regime is None:
            current_regime = ai_strategy_generator.regime_detector.detect_current_regime({symbol: market_data})
        
        # Get best strategy for current regime
        best_strategy = ai_strategy_generator.get_best_strategy_for_regime(current_regime)
        
        if best_strategy is None:
            return 0.0, "no_suitable_strategy", {"regime": current_regime.value}
        
        # Generate features for current data
        try:
            features = make_features(market_data, symbol=symbol)
            if features.empty:
                return 0.0, "no_features", {"strategy": best_strategy.name}
            
            current_features = features.iloc[-1]
            
            # Generate signal using strategy validator's signal generation
            signal = ai_strategy_generator.validator._generate_strategy_signal(
                best_strategy, current_features, symbol
            )
            
            metadata = {
                "strategy_id": best_strategy.strategy_id,
                "strategy_name": best_strategy.name,
                "strategy_type": best_strategy.strategy_type.value,
                "regime": current_regime.value,
                "generation": best_strategy.generation,
                "fitness_score": best_strategy.fitness_score
            }
            
            return float(signal), best_strategy.name, metadata
            
        except Exception as e:
            logger.debug(f"Error generating AI strategy signal for {symbol}: {e}")
            return 0.0, "signal_generation_error", {"error": str(e)}
    
    except Exception as e:
        logger.error(f"❌ Error in get_best_strategy_signal: {e}")
        return 0.0, "system_error", {"error": str(e)}

def get_regime_adaptive_signal(symbol: str, market_data: pd.DataFrame) -> Dict[str, Any]:
    """
    Get regime-adaptive signals from multiple strategies
    
    Returns:
        Dictionary with signals for different regimes and meta-information
    """
    
    try:
        if ai_strategy_generator is None:
            return {"available": False, "reason": "system_not_initialized"}
        
        # Detect current regime
        current_regime = ai_strategy_generator.regime_detector.detect_current_regime({symbol: market_data})
        
        # Get regime transition probabilities
        transition_probs = ai_strategy_generator.regime_detector.get_regime_transition_probability(current_regime)
        
        # Get signals for multiple regimes
        regime_signals = {}
        
        # Current regime signal (highest weight)
        main_signal, main_strategy, main_metadata = get_best_strategy_signal(symbol, market_data, current_regime)
        regime_signals[current_regime.value] = {
            "signal": main_signal,
            "strategy": main_strategy,
            "weight": 0.6,  # Primary weight
            "metadata": main_metadata
        }
        
        # Secondary regime signals based on transition probabilities
        secondary_regimes = sorted(transition_probs.items(), key=lambda x: x[1], reverse=True)[:2]
        
        remaining_weight = 0.4
        for regime, prob in secondary_regimes:
            if regime != current_regime:
                signal, strategy, metadata = get_best_strategy_signal(symbol, market_data, regime)
                weight = remaining_weight * prob
                
                regime_signals[regime.value] = {
                    "signal": signal,
                    "strategy": strategy,
                    "weight": weight,
                    "metadata": metadata,
                    "transition_probability": prob
                }
                
                remaining_weight -= weight
                
                if remaining_weight <= 0.1:  # Don't go below 10% remaining
                    break
        
        # Calculate weighted composite signal
        composite_signal = 0.0
        total_weight = 0.0
        
        for regime_data in regime_signals.values():
            composite_signal += regime_data["signal"] * regime_data["weight"]
            total_weight += regime_data["weight"]
        
        if total_weight > 0:
            composite_signal /= total_weight
        
        return {
            "available": True,
            "composite_signal": composite_signal,
            "current_regime": current_regime.value,
            "regime_signals": regime_signals,
            "transition_probabilities": {r.value: p for r, p in transition_probs.items()},
            "confidence": min(1.0, total_weight)
        }
    
    except Exception as e:
        logger.error(f"❌ Error in regime adaptive signal: {e}")
        return {"available": False, "reason": "error", "error": str(e)}


if __name__ == "__main__":
    # Example usage and testing
    async def test_ai_strategy_generator():
        """Test the AI Strategy Generator system"""
        
        # Initialize system
        generator = await initialize_ai_strategy_generator()
        
        # Generate initial population
        await generator.generate_initial_population(size=10)
        
        # Generate some new strategies
        new_strategies = await generator.generate_new_strategies(count=3)
        print(f"Generated {len(new_strategies)} new strategies")
        
        # Validate strategies
        validation_results = await generator.validate_strategy_batch(new_strategies[:2])
        print(f"Validated {len(validation_results)} strategies")
        
        # Get system status
        status = generator.get_system_status()
        print(f"System status: {status['metrics']}")
        
        # Test market regime detection
        try:
            market_data = fetch_all_bars(settings.symbols[:3], start="", end="", min_bars=100)
            regime = generator.regime_detector.detect_current_regime(market_data)
            print(f"Current market regime: {regime.value}")
            
            # Test strategy signal generation
            if market_data:
                symbol = list(market_data.keys())[0]
                df = market_data[symbol]
                signal, strategy_name, metadata = get_best_strategy_signal(symbol, df, regime)
                print(f"Best strategy signal for {symbol}: {signal:.3f} ({strategy_name})")
        
        except Exception as e:
            print(f"Error testing market data: {e}")
        
        # Stop system
        await generator.stop_system()
    
    # Run test
    asyncio.run(test_ai_strategy_generator())