"""
📈 PERFORMANCE ADAPTATION ENGINE
Intelligent performance-based risk and position sizing system that dynamically adapts
trading parameters based on recent strategy performance, win rates, and consistency metrics.

Features:
- Real-time performance tracking and analysis
- Adaptive position sizing based on recent win rates
- Strategy confidence scoring and model reliability assessment
- Performance-based risk scaling (increase/decrease based on results)
- Multi-timeframe performance evaluation (intraday, daily, weekly)
- Drawdown-adjusted performance metrics
- Sharpe ratio and risk-adjusted return optimization
- Strategy allocation and capital distribution optimization
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import warnings
from pathlib import Path
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from scipy import stats

from .util import logger
from .config import settings


class PerformanceRegime(Enum):
    """Performance regime classification"""
    EXCEPTIONAL = "exceptional"     # Top 10% performance
    STRONG = "strong"              # Top 25% performance
    GOOD = "good"                  # Above median performance
    AVERAGE = "average"            # Around median performance
    WEAK = "weak"                  # Below median performance
    POOR = "poor"                  # Bottom 25% performance
    CRITICAL = "critical"          # Bottom 10% performance


class ConfidenceLevel(Enum):
    """Model confidence levels"""
    VERY_HIGH = "very_high"        # > 90% confidence
    HIGH = "high"                  # 75-90% confidence
    MEDIUM = "medium"              # 50-75% confidence
    LOW = "low"                    # 25-50% confidence
    VERY_LOW = "very_low"          # < 25% confidence


@dataclass
class PerformanceMetrics:
    """Container for comprehensive performance analysis"""
    total_return: float = 0.0              # Total return since inception
    annualized_return: float = 0.0         # Annualized return
    sharpe_ratio: float = 0.0              # Risk-adjusted return metric
    sortino_ratio: float = 0.0             # Downside risk-adjusted return
    calmar_ratio: float = 0.0              # Return/max drawdown
    win_rate: float = 0.0                  # Percentage of winning trades
    profit_factor: float = 0.0             # Gross profit / gross loss
    avg_win: float = 0.0                   # Average winning trade
    avg_loss: float = 0.0                  # Average losing trade
    max_consecutive_wins: int = 0          # Maximum consecutive wins
    max_consecutive_losses: int = 0        # Maximum consecutive losses
    expectancy: float = 0.0                # Expected value per trade
    volatility: float = 0.0                # Return volatility
    beta: float = 0.0                      # Beta vs market
    alpha: float = 0.0                     # Alpha vs market
    information_ratio: float = 0.0         # Risk-adjusted excess return
    tracking_error: float = 0.0            # Volatility of excess returns
    hit_ratio: float = 0.0                 # Frequency of outperformance
    up_capture: float = 0.0                # Upside capture ratio
    down_capture: float = 0.0              # Downside capture ratio
    consistency_score: float = 0.0         # Performance consistency
    regime: PerformanceRegime = PerformanceRegime.AVERAGE


@dataclass
class AdaptationSettings:
    """Adaptive settings based on performance"""
    performance_multiplier: float = 1.0    # Position size multiplier
    confidence_threshold: float = 0.5      # Minimum signal confidence
    max_position_count: int = 10           # Maximum simultaneous positions
    risk_budget_allocation: float = 1.0    # Fraction of risk budget to use
    stop_loss_adjustment: float = 1.0      # Stop loss adjustment factor
    take_profit_adjustment: float = 1.0    # Take profit adjustment factor
    position_timeout: float = 1.0          # Position timeout multiplier
    strategy_weight: float = 1.0           # Strategy allocation weight
    rebalance_frequency: float = 1.0       # Rebalancing frequency multiplier
    confidence_level: ConfidenceLevel = ConfidenceLevel.MEDIUM


class PerformanceAdapter:
    """
    Advanced performance adaptation system that continuously monitors strategy performance
    and dynamically adjusts trading parameters to optimize risk-adjusted returns.
    
    Core Functions:
    - Real-time performance tracking and metrics calculation
    - Adaptive position sizing based on recent performance
    - Strategy confidence assessment and reliability scoring
    - Performance-based risk scaling and parameter optimization
    - Multi-timeframe performance evaluation and trend analysis
    - Allocation optimization across different strategies/timeframes
    - Performance degradation detection and intervention
    """
    
    def __init__(self):
        # State persistence
        self.state_file = "bot/performance_adapter_state.json"
        self.history_file = "bot/performance_history.json"
        self.trades_file = "bot/trade_performance_log.json"
        
        # Performance evaluation windows
        self.short_window = 10               # 10 trades for short-term assessment
        self.medium_window = 50              # 50 trades for medium-term
        self.long_window = 200               # 200 trades for long-term
        
        # Performance thresholds
        self.performance_thresholds = {
            PerformanceRegime.EXCEPTIONAL: 0.90,    # Top 10%
            PerformanceRegime.STRONG: 0.75,         # Top 25%
            PerformanceRegime.GOOD: 0.60,           # Above average
            PerformanceRegime.AVERAGE: 0.40,        # Average
            PerformanceRegime.WEAK: 0.25,           # Below average
            PerformanceRegime.POOR: 0.10,           # Bottom 25%
            PerformanceRegime.CRITICAL: 0.0         # Bottom 10%
        }
        
        # Adaptation multipliers by performance regime
        self.performance_multipliers = {
            PerformanceRegime.EXCEPTIONAL: 1.3,     # Increase position size
            PerformanceRegime.STRONG: 1.15,
            PerformanceRegime.GOOD: 1.05,
            PerformanceRegime.AVERAGE: 1.0,         # Baseline
            PerformanceRegime.WEAK: 0.9,
            PerformanceRegime.POOR: 0.7,
            PerformanceRegime.CRITICAL: 0.5         # Reduce position size significantly
        }
        
        # Confidence thresholds by performance
        self.confidence_thresholds = {
            PerformanceRegime.EXCEPTIONAL: 0.3,     # Lower threshold when performing well
            PerformanceRegime.STRONG: 0.4,
            PerformanceRegime.GOOD: 0.45,
            PerformanceRegime.AVERAGE: 0.5,         # Standard threshold
            PerformanceRegime.WEAK: 0.6,
            PerformanceRegime.POOR: 0.7,
            PerformanceRegime.CRITICAL: 0.8         # Higher threshold when struggling
        }
        
        # Historical data
        self.trade_history = []                     # Individual trade records
        self.performance_history = []               # Performance snapshots
        self.equity_curve = []                      # Equity progression
        
        # Current state
        self.current_metrics = PerformanceMetrics()
        self.current_adaptation = AdaptationSettings()
        self.benchmark_performance = {}             # Benchmark comparisons
        self.last_update = None
        self.performance_declining = False
        self.intervention_mode = False
        
        # Monitoring
        self._monitoring_active = False
        
        # Load persistent state
        self.load_state()
        
        # Initialize background monitoring
        self._start_background_monitoring()
        
        logger.info("📈 Performance Adapter initialized - Intelligent performance tracking active")
    
    def load_state(self):
        """Load persistent state from disk"""
        try:
            if Path(self.state_file).exists():
                with open(self.state_file, 'r') as f:
                    state_data = json.load(f)
                    self.performance_declining = state_data.get('performance_declining', False)
                    self.intervention_mode = state_data.get('intervention_mode', False)
                    
                    self.last_update = state_data.get('last_update')
                    if self.last_update:
                        self.last_update = datetime.fromisoformat(self.last_update)
                    
            if Path(self.history_file).exists():
                with open(self.history_file, 'r') as f:
                    self.performance_history = json.load(f)
                    # Keep only last 1000 entries
                    self.performance_history = self.performance_history[-1000:]
                    
            if Path(self.trades_file).exists():
                with open(self.trades_file, 'r') as f:
                    self.trade_history = json.load(f)
                    # Keep only last 500 trades
                    self.trade_history = self.trade_history[-500:]
                    
        except Exception as e:
            logger.warning(f"⚠️ Error loading performance adapter state: {e}")
            self.performance_history = []
            self.trade_history = []
    
    def save_state(self):
        """Save persistent state to disk"""
        try:
            state_data = {
                'performance_declining': self.performance_declining,
                'intervention_mode': self.intervention_mode,
                'last_update': self.last_update.isoformat() if self.last_update else None,
                'current_regime': self.current_metrics.regime.value,
                'current_multiplier': self.current_adaptation.performance_multiplier
            }
            
            with open(self.state_file, 'w') as f:
                json.dump(state_data, f, indent=2)
                
            # Save performance history
            with open(self.history_file, 'w') as f:
                json.dump(self.performance_history, f)
                
            # Save trade history
            with open(self.trades_file, 'w') as f:
                json.dump(self.trade_history, f)
                
        except Exception as e:
            logger.warning(f"⚠️ Error saving performance adapter state: {e}")
    
    def _start_background_monitoring(self):
        """Start background performance monitoring"""
        if self._monitoring_active:
            return
            
        def monitor_performance():
            while self._monitoring_active:
                try:
                    # Update performance analysis every 60 seconds
                    self.update_performance_analysis()
                    time.sleep(60)
                except Exception as e:
                    logger.error(f"❌ Error in performance monitoring: {e}")
                    time.sleep(120)  # Back off on error
        
        self._monitoring_active = True
        monitoring_thread = threading.Thread(target=monitor_performance, daemon=True)
        monitoring_thread.start()
        logger.info("🔍 Background performance monitoring started")
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        self._monitoring_active = False
        logger.info("⏹️ Performance monitoring stopped")
    
    def log_trade_result(self, symbol: str, side: str, entry_price: float, exit_price: float, 
                        quantity: float, pnl: float, duration_minutes: float, signal_strength: float):
        """Log individual trade result for performance tracking"""
        try:
            trade_record = {
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'side': side.lower(),
                'entry_price': entry_price,
                'exit_price': exit_price,
                'quantity': quantity,
                'pnl': pnl,
                'pnl_pct': (pnl / (entry_price * abs(quantity))) if entry_price * abs(quantity) > 0 else 0,
                'duration_minutes': duration_minutes,
                'signal_strength': signal_strength,
                'is_winner': pnl > 0
            }
            
            self.trade_history.append(trade_record)
            
            # Keep only last 500 trades
            if len(self.trade_history) > 500:
                self.trade_history = self.trade_history[-500:]
            
            # Trigger immediate performance update after new trade
            self.update_performance_analysis()
            
            logger.debug(f"📊 Trade logged: {symbol} {side} PnL: ${pnl:.2f} ({trade_record['pnl_pct']:.2%})")
            
        except Exception as e:
            logger.error(f"❌ Error logging trade result: {e}")
    
    def update_performance_analysis(self):
        """Update comprehensive performance analysis"""
        try:
            # Get current equity for performance calculation
            current_equity = self._get_current_equity()
            if current_equity <= 0:
                logger.warning("⚠️ Invalid equity for performance analysis")
                return
            
            # Update equity curve
            self._update_equity_curve(current_equity)
            
            # Calculate performance metrics
            self.current_metrics = self._calculate_performance_metrics()
            
            # Determine adaptation settings
            self.current_adaptation = self._determine_adaptation_settings()
            
            # Check for performance degradation
            self._check_performance_degradation()
            
            # Update benchmark comparisons
            self._update_benchmark_comparisons()
            
            # Save to history
            self._save_performance_to_history()
            
            # Update timestamp
            self.last_update = datetime.now()
            
            # Save state
            self.save_state()
            
            # Log performance status
            self._log_performance_status()
            
        except Exception as e:
            logger.error(f"❌ Error updating performance analysis: {e}")
    
    def _get_current_equity(self) -> float:
        """Get current account equity"""
        try:
            from alpaca.trading.client import TradingClient
            
            client = TradingClient(
                api_key=settings.alpaca_api_key,
                secret_key=settings.alpaca_secret_key,
                paper=(settings.mode == "paper")
            )
            
            account = client.get_account()
            equity = float(getattr(account, 'equity', 0) or 0)
            
            return equity
            
        except Exception as e:
            logger.error(f"❌ Error getting current equity: {e}")
            return 0.0
    
    def _update_equity_curve(self, current_equity: float):
        """Update equity progression curve"""
        try:
            equity_record = {
                'timestamp': datetime.now().isoformat(),
                'equity': current_equity
            }
            
            self.equity_curve.append(equity_record)
            
            # Keep only last 1000 records
            if len(self.equity_curve) > 1000:
                self.equity_curve = self.equity_curve[-1000:]
                
        except Exception as e:
            logger.error(f"❌ Error updating equity curve: {e}")
    
    def _calculate_performance_metrics(self) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics"""
        try:
            metrics = PerformanceMetrics()
            
            if not self.trade_history and not self.equity_curve:
                return metrics
            
            # Trade-based metrics
            if self.trade_history:
                trades = pd.DataFrame(self.trade_history)
                
                # Basic trade statistics
                winning_trades = trades[trades['is_winner'] == True]
                losing_trades = trades[trades['is_winner'] == False]
                
                metrics.win_rate = len(winning_trades) / len(trades) if len(trades) > 0 else 0
                
                if len(winning_trades) > 0:
                    metrics.avg_win = winning_trades['pnl'].mean()
                if len(losing_trades) > 0:
                    metrics.avg_loss = abs(losing_trades['pnl'].mean())
                
                # Profit factor
                gross_profit = winning_trades['pnl'].sum() if len(winning_trades) > 0 else 0
                gross_loss = abs(losing_trades['pnl'].sum()) if len(losing_trades) > 0 else 1
                metrics.profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
                
                # Expectancy
                win_rate = metrics.win_rate
                avg_win = metrics.avg_win
                avg_loss = metrics.avg_loss
                metrics.expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
                
                # Consecutive wins/losses
                consecutive_wins = 0
                consecutive_losses = 0
                max_wins = 0
                max_losses = 0
                
                for trade in trades.itertuples():
                    if trade.is_winner:
                        consecutive_wins += 1
                        consecutive_losses = 0
                        max_wins = max(max_wins, consecutive_wins)
                    else:
                        consecutive_losses += 1
                        consecutive_wins = 0
                        max_losses = max(max_losses, consecutive_losses)
                
                metrics.max_consecutive_wins = max_wins
                metrics.max_consecutive_losses = max_losses
            
            # Equity-based metrics
            if len(self.equity_curve) >= 2:
                equity_df = pd.DataFrame(self.equity_curve)
                equity_series = equity_df['equity']
                
                # Returns calculation
                returns = equity_series.pct_change().dropna()
                
                if len(returns) > 0:
                    # Total and annualized returns
                    total_return = (equity_series.iloc[-1] / equity_series.iloc[0] - 1)
                    metrics.total_return = total_return
                    
                    # Calculate time period for annualization
                    start_date = datetime.fromisoformat(equity_df['timestamp'].iloc[0])
                    end_date = datetime.fromisoformat(equity_df['timestamp'].iloc[-1])
                    days_elapsed = (end_date - start_date).days
                    
                    if days_elapsed > 0:
                        metrics.annualized_return = (1 + total_return) ** (365 / days_elapsed) - 1
                    
                    # Volatility
                    metrics.volatility = returns.std() * np.sqrt(252) if len(returns) > 1 else 0
                    
                    # Sharpe ratio (assuming 2% risk-free rate)
                    excess_returns = returns - 0.02/252
                    if returns.std() > 0:
                        metrics.sharpe_ratio = excess_returns.mean() / returns.std() * np.sqrt(252)
                    
                    # Sortino ratio (downside deviation)
                    downside_returns = returns[returns < 0]
                    if len(downside_returns) > 0 and downside_returns.std() > 0:
                        metrics.sortino_ratio = excess_returns.mean() / downside_returns.std() * np.sqrt(252)
                    
                    # Calmar ratio (return / max drawdown)
                    max_dd = self._calculate_max_drawdown(equity_series)
                    if max_dd > 0:
                        metrics.calmar_ratio = metrics.annualized_return / max_dd
                    
                    # Consistency score (based on return stability)
                    if len(returns) >= 10:
                        rolling_returns = returns.rolling(5).mean()
                        return_stability = 1 / (1 + rolling_returns.std()) if rolling_returns.std() > 0 else 1
                        metrics.consistency_score = min(1.0, return_stability)
            
            # Classify performance regime
            metrics.regime = self._classify_performance_regime(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Error calculating performance metrics: {e}")
            return PerformanceMetrics()
    
    def _calculate_max_drawdown(self, equity_series: pd.Series) -> float:
        """Calculate maximum drawdown from equity series"""
        try:
            running_max = equity_series.expanding().max()
            drawdowns = (equity_series - running_max) / running_max
            return abs(drawdowns.min())
        except:
            return 0.0
    
    def _classify_performance_regime(self, metrics: PerformanceMetrics) -> PerformanceRegime:
        """Classify current performance regime"""
        try:
            # Use multiple factors for classification
            factors = []
            
            # Sharpe ratio factor
            if metrics.sharpe_ratio > 1.5:
                factors.append(0.9)
            elif metrics.sharpe_ratio > 1.0:
                factors.append(0.75)
            elif metrics.sharpe_ratio > 0.5:
                factors.append(0.6)
            elif metrics.sharpe_ratio > 0.0:
                factors.append(0.4)
            else:
                factors.append(0.2)
            
            # Win rate factor
            if metrics.win_rate > 0.65:
                factors.append(0.9)
            elif metrics.win_rate > 0.55:
                factors.append(0.7)
            elif metrics.win_rate > 0.45:
                factors.append(0.5)
            else:
                factors.append(0.3)
            
            # Profit factor
            if metrics.profit_factor > 2.0:
                factors.append(0.9)
            elif metrics.profit_factor > 1.5:
                factors.append(0.7)
            elif metrics.profit_factor > 1.2:
                factors.append(0.6)
            elif metrics.profit_factor > 1.0:
                factors.append(0.4)
            else:
                factors.append(0.2)
            
            # Consistency factor
            factors.append(metrics.consistency_score)
            
            # Average performance score
            performance_score = np.mean(factors) if factors else 0.5
            
            # Classify regime
            for regime in [PerformanceRegime.EXCEPTIONAL, PerformanceRegime.STRONG,
                          PerformanceRegime.GOOD, PerformanceRegime.AVERAGE,
                          PerformanceRegime.WEAK, PerformanceRegime.POOR,
                          PerformanceRegime.CRITICAL]:
                if performance_score >= self.performance_thresholds[regime]:
                    return regime
            
            return PerformanceRegime.CRITICAL
            
        except Exception as e:
            logger.error(f"❌ Error classifying performance regime: {e}")
            return PerformanceRegime.AVERAGE
    
    def _determine_adaptation_settings(self) -> AdaptationSettings:
        """Determine adaptive settings based on performance"""
        try:
            adaptation = AdaptationSettings()
            
            regime = self.current_metrics.regime
            
            # Performance multiplier
            adaptation.performance_multiplier = self.performance_multipliers.get(regime, 1.0)
            
            # Confidence threshold
            adaptation.confidence_threshold = self.confidence_thresholds.get(regime, 0.5)
            
            # Maximum position count (reduce when performing poorly)
            base_max_positions = 15
            if regime in [PerformanceRegime.POOR, PerformanceRegime.CRITICAL]:
                adaptation.max_position_count = max(5, base_max_positions // 2)
            elif regime in [PerformanceRegime.WEAK]:
                adaptation.max_position_count = max(8, int(base_max_positions * 0.7))
            elif regime in [PerformanceRegime.EXCEPTIONAL, PerformanceRegime.STRONG]:
                adaptation.max_position_count = min(20, int(base_max_positions * 1.3))
            else:
                adaptation.max_position_count = base_max_positions
            
            # Risk budget allocation
            if regime in [PerformanceRegime.EXCEPTIONAL, PerformanceRegime.STRONG]:
                adaptation.risk_budget_allocation = 1.1  # Use slightly more of risk budget
            elif regime in [PerformanceRegime.POOR, PerformanceRegime.CRITICAL]:
                adaptation.risk_budget_allocation = 0.6  # Reduce risk budget usage
            else:
                adaptation.risk_budget_allocation = 1.0
            
            # Stop loss adjustment (tighter when performing poorly)
            if regime in [PerformanceRegime.POOR, PerformanceRegime.CRITICAL]:
                adaptation.stop_loss_adjustment = 0.8  # 20% tighter stops
            elif regime == PerformanceRegime.WEAK:
                adaptation.stop_loss_adjustment = 0.9  # 10% tighter stops
            elif regime in [PerformanceRegime.EXCEPTIONAL, PerformanceRegime.STRONG]:
                adaptation.stop_loss_adjustment = 1.1  # 10% wider stops
            else:
                adaptation.stop_loss_adjustment = 1.0
            
            # Take profit adjustment
            if regime in [PerformanceRegime.EXCEPTIONAL, PerformanceRegime.STRONG]:
                adaptation.take_profit_adjustment = 1.2  # Let winners run longer
            elif regime in [PerformanceRegime.POOR, PerformanceRegime.CRITICAL]:
                adaptation.take_profit_adjustment = 0.8  # Take profits quicker
            else:
                adaptation.take_profit_adjustment = 1.0
            
            # Position timeout adjustment
            if regime in [PerformanceRegime.POOR, PerformanceRegime.CRITICAL]:
                adaptation.position_timeout = 0.7  # Close positions faster
            elif regime in [PerformanceRegime.EXCEPTIONAL, PerformanceRegime.STRONG]:
                adaptation.position_timeout = 1.3  # Hold positions longer
            else:
                adaptation.position_timeout = 1.0
            
            # Confidence level classification
            win_rate = self.current_metrics.win_rate
            sharpe = self.current_metrics.sharpe_ratio
            consistency = self.current_metrics.consistency_score
            
            confidence_score = (win_rate + min(sharpe/2, 1) + consistency) / 3
            
            if confidence_score > 0.8:
                adaptation.confidence_level = ConfidenceLevel.VERY_HIGH
            elif confidence_score > 0.65:
                adaptation.confidence_level = ConfidenceLevel.HIGH
            elif confidence_score > 0.45:
                adaptation.confidence_level = ConfidenceLevel.MEDIUM
            elif confidence_score > 0.25:
                adaptation.confidence_level = ConfidenceLevel.LOW
            else:
                adaptation.confidence_level = ConfidenceLevel.VERY_LOW
            
            return adaptation
            
        except Exception as e:
            logger.error(f"❌ Error determining adaptation settings: {e}")
            return AdaptationSettings()
    
    def _check_performance_degradation(self):
        """Check for performance degradation and trigger interventions"""
        try:
            degradation_detected = False
            reasons = []
            
            # Check recent win rate decline
            if len(self.trade_history) >= 20:
                recent_trades = self.trade_history[-10:]
                recent_win_rate = sum(1 for t in recent_trades if t['is_winner']) / len(recent_trades)
                
                if recent_win_rate < 0.3:  # Less than 30% win rate recently
                    degradation_detected = True
                    reasons.append(f"Low recent win rate: {recent_win_rate:.1%}")
            
            # Check consecutive losses
            if self.current_metrics.max_consecutive_losses >= 5:
                degradation_detected = True
                reasons.append(f"Consecutive losses: {self.current_metrics.max_consecutive_losses}")
            
            # Check Sharpe ratio decline
            if self.current_metrics.sharpe_ratio < -0.5:
                degradation_detected = True
                reasons.append(f"Negative Sharpe ratio: {self.current_metrics.sharpe_ratio:.2f}")
            
            # Check profit factor
            if self.current_metrics.profit_factor < 0.8:
                degradation_detected = True
                reasons.append(f"Low profit factor: {self.current_metrics.profit_factor:.2f}")
            
            # Update degradation state
            if degradation_detected and not self.performance_declining:
                self.performance_declining = True
                self.intervention_mode = True
                logger.warning(f"⚠️ PERFORMANCE DEGRADATION DETECTED: {', '.join(reasons)}")
                
                # Send alert
                try:
                    from .telegram import send_telegram
                    msg = f"⚠️ PERFORMANCE DEGRADATION\n\nReasons:\n" + "\n".join([f"• {r}" for r in reasons])
                    msg += f"\n\nWin Rate: {self.current_metrics.win_rate:.1%}"
                    msg += f"\nSharpe: {self.current_metrics.sharpe_ratio:.2f}"
                    msg += f"\nRegime: {self.current_metrics.regime.value.upper()}"
                    send_telegram(msg)
                except:
                    pass
                    
            elif not degradation_detected and self.performance_declining:
                # Check if we can clear degradation mode
                if (self.current_metrics.win_rate > 0.4 and 
                    self.current_metrics.sharpe_ratio > 0.0):
                    self.performance_declining = False
                    self.intervention_mode = False
                    logger.info("✅ Performance degradation cleared - returning to normal operation")
                    
        except Exception as e:
            logger.error(f"❌ Error checking performance degradation: {e}")
    
    def _update_benchmark_comparisons(self):
        """Update benchmark performance comparisons"""
        try:
            # Simple benchmark tracking (could be expanded)
            self.benchmark_performance = {
                'spy_correlation': 0.0,  # Correlation with SPY
                'outperformance': 0.0,   # Outperformance vs benchmark
                'beta': self.current_metrics.beta,
                'alpha': self.current_metrics.alpha
            }
            
            # This could be enhanced with actual benchmark data
            
        except Exception as e:
            logger.error(f"❌ Error updating benchmark comparisons: {e}")
    
    def _save_performance_to_history(self):
        """Save current performance metrics to history"""
        try:
            performance_record = {
                'timestamp': datetime.now().isoformat(),
                'total_return': self.current_metrics.total_return,
                'annualized_return': self.current_metrics.annualized_return,
                'sharpe_ratio': self.current_metrics.sharpe_ratio,
                'win_rate': self.current_metrics.win_rate,
                'profit_factor': self.current_metrics.profit_factor,
                'expectancy': self.current_metrics.expectancy,
                'regime': self.current_metrics.regime.value,
                'performance_multiplier': self.current_adaptation.performance_multiplier,
                'confidence_level': self.current_adaptation.confidence_level.value,
                'degradation_mode': self.performance_declining
            }
            
            self.performance_history.append(performance_record)
            
            # Keep only last 1000 records
            if len(self.performance_history) > 1000:
                self.performance_history = self.performance_history[-1000:]
                
        except Exception as e:
            logger.error(f"❌ Error saving performance to history: {e}")
    
    def _log_performance_status(self):
        """Log current performance status"""
        try:
            regime_color = {
                PerformanceRegime.EXCEPTIONAL: "🟢",
                PerformanceRegime.STRONG: "🟢",
                PerformanceRegime.GOOD: "🟡",
                PerformanceRegime.AVERAGE: "🟡",
                PerformanceRegime.WEAK: "🟠",
                PerformanceRegime.POOR: "🔴",
                PerformanceRegime.CRITICAL: "🚨"
            }.get(self.current_metrics.regime, "🟡")
            
            logger.info(f"📈 PERFORMANCE STATUS: {regime_color} {self.current_metrics.regime.value.upper()} | "
                       f"Win Rate: {self.current_metrics.win_rate:.1%} | "
                       f"Sharpe: {self.current_metrics.sharpe_ratio:.2f} | "
                       f"Multiplier: {self.current_adaptation.performance_multiplier:.2f}x")
            
            if self.performance_declining:
                logger.warning(f"⚠️ INTERVENTION MODE ACTIVE - Enhanced monitoring and reduced risk")
                
        except Exception as e:
            logger.error(f"❌ Error logging performance status: {e}")
    
    # Public API methods
    
    def get_performance_multiplier(self) -> float:
        """Get current performance-based position size multiplier"""
        return self.current_adaptation.performance_multiplier
    
    def get_confidence_threshold(self) -> float:
        """Get current confidence threshold for signal acceptance"""
        return self.current_adaptation.confidence_threshold
    
    def get_max_position_count(self) -> int:
        """Get maximum number of simultaneous positions allowed"""
        return self.current_adaptation.max_position_count
    
    def get_stop_loss_adjustment(self) -> float:
        """Get stop loss adjustment factor"""
        return self.current_adaptation.stop_loss_adjustment
    
    def get_take_profit_adjustment(self) -> float:
        """Get take profit adjustment factor"""
        return self.current_adaptation.take_profit_adjustment
    
    def is_intervention_mode(self) -> bool:
        """Check if intervention mode is active due to poor performance"""
        return self.intervention_mode
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        return {
            'regime': self.current_metrics.regime.value,
            'win_rate': self.current_metrics.win_rate,
            'profit_factor': self.current_metrics.profit_factor,
            'sharpe_ratio': self.current_metrics.sharpe_ratio,
            'total_return': self.current_metrics.total_return,
            'performance_multiplier': self.current_adaptation.performance_multiplier,
            'confidence_threshold': self.current_adaptation.confidence_threshold,
            'confidence_level': self.current_adaptation.confidence_level.value,
            'max_position_count': self.current_adaptation.max_position_count,
            'intervention_mode': self.intervention_mode,
            'performance_declining': self.performance_declining,
            'trade_count': len(self.trade_history),
            'last_update': self.last_update.isoformat() if self.last_update else None
        }


# Global instance
performance_adapter = PerformanceAdapter()


def get_performance_adaptation(signal_strength: float = None) -> Dict[str, Any]:
    """
    Get current performance-based adaptations for trading parameters.
    Returns comprehensive adaptation settings based on recent performance.
    """
    try:
        # Update analysis if stale
        if (not performance_adapter.last_update or 
            datetime.now() - performance_adapter.last_update > timedelta(minutes=5)):
            performance_adapter.update_performance_analysis()
        
        # Get adaptation settings
        multiplier = performance_adapter.get_performance_multiplier()
        confidence_threshold = performance_adapter.get_confidence_threshold()
        max_positions = performance_adapter.get_max_position_count()
        stop_adjustment = performance_adapter.get_stop_loss_adjustment()
        tp_adjustment = performance_adapter.get_take_profit_adjustment()
        intervention = performance_adapter.is_intervention_mode()
        
        # Check signal acceptance if provided
        signal_accepted = True
        if signal_strength is not None:
            signal_accepted = abs(signal_strength) >= confidence_threshold
        
        return {
            'performance_multiplier': multiplier,
            'confidence_threshold': confidence_threshold,
            'max_position_count': max_positions,
            'stop_loss_adjustment': stop_adjustment,
            'take_profit_adjustment': tp_adjustment,
            'signal_accepted': signal_accepted,
            'intervention_mode': intervention,
            'performance_regime': performance_adapter.current_metrics.regime.value,
            'win_rate': performance_adapter.current_metrics.win_rate,
            'sharpe_ratio': performance_adapter.current_metrics.sharpe_ratio,
            'confidence_level': performance_adapter.current_adaptation.confidence_level.value
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting performance adaptation: {e}")
        return {
            'performance_multiplier': 1.0,
            'confidence_threshold': 0.5,
            'max_position_count': 10,
            'stop_loss_adjustment': 1.0,
            'take_profit_adjustment': 1.0,
            'signal_accepted': True,
            'intervention_mode': False,
            'performance_regime': 'average',
            'win_rate': 0.5,
            'sharpe_ratio': 0.0,
            'confidence_level': 'medium'
        }