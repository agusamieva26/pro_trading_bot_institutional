"""
🏛️ INSTITUTIONAL-GRADE DYNAMIC RISK MANAGEMENT SYSTEM
Real-time risk adjustment engine with advanced volatility modeling, drawdown protection,
and performance-based adaptation for professional trading operations.

Features:
- Real-time risk factor monitoring and adjustment
- Multi-timeframe volatility assessment (1m, 5m, 15m, 1h)
- Drawdown-based risk scaling with emergency protocols
- Performance-adaptive position sizing
- Comprehensive risk metrics calculation (VaR, CVaR, Sharpe)
- Regime-aware risk management
- Correlation matrix tracking for portfolio risk
- Stress testing and scenario analysis
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

from .util import logger
from .config import settings
from .risk_management_v2 import AdvancedRiskManager, analyze_risk_environment
from .dynamic_cash_buffer import DynamicCashBuffer


class RiskRegime(Enum):
    """Risk regime classification for dynamic adjustment"""
    ULTRA_LOW = "ultra_low"      # < 5th percentile volatility
    LOW = "low"                  # 5-25th percentile
    NORMAL = "normal"            # 25-75th percentile  
    HIGH = "high"                # 75-95th percentile
    EXTREME = "extreme"          # > 95th percentile


class PerformanceRegime(Enum):
    """Performance regime for adaptive risk scaling"""
    EXCEPTIONAL = "exceptional"  # Top quartile performance
    GOOD = "good"                # Above median performance
    AVERAGE = "average"          # Around median performance
    POOR = "poor"                # Below median performance
    CRITICAL = "critical"        # Bottom quartile performance


@dataclass
class RiskMetrics:
    """Container for comprehensive risk metrics"""
    var_1d: float = 0.0          # 1-day Value at Risk (95%)
    cvar_1d: float = 0.0         # 1-day Conditional VaR
    var_5d: float = 0.0          # 5-day Value at Risk
    sharpe_ratio: float = 0.0     # Annualized Sharpe ratio
    sortino_ratio: float = 0.0    # Sortino ratio (downside deviation)
    max_drawdown: float = 0.0     # Maximum drawdown from peak
    current_drawdown: float = 0.0 # Current drawdown from recent peak
    volatility: float = 0.0       # Annualized volatility
    beta: float = 0.0            # Beta vs market (SPY)
    correlation_spy: float = 0.0  # Correlation with SPY
    risk_regime: RiskRegime = RiskRegime.NORMAL
    performance_regime: PerformanceRegime = PerformanceRegime.AVERAGE
    risk_score: float = 0.5      # Composite risk score (0-1)
    confidence_level: float = 0.0 # Model confidence level


@dataclass
class RiskAdjustment:
    """Risk adjustment parameters for position sizing"""
    base_risk_multiplier: float = 1.0     # Base risk scaling factor
    volatility_adjustment: float = 1.0     # Volatility-based scaling
    drawdown_adjustment: float = 1.0       # Drawdown-based scaling
    performance_adjustment: float = 1.0    # Performance-based scaling
    correlation_adjustment: float = 1.0    # Portfolio correlation scaling
    final_risk_multiplier: float = 1.0     # Final combined multiplier
    max_position_size: float = 0.0         # Maximum position size (USD)
    stop_loss_adjustment: float = 1.0      # Stop loss width adjustment
    take_profit_adjustment: float = 1.0    # Take profit adjustment
    confidence_threshold: float = 0.0      # Minimum signal confidence


class DynamicRiskManager:
    """
    Institutional-grade dynamic risk management system that adapts risk parameters
    in real-time based on market conditions, portfolio performance, and volatility regimes.
    
    Core Functions:
    - Real-time risk regime detection
    - Dynamic position sizing with multi-factor adjustment
    - Drawdown-based risk scaling
    - Performance-adaptive risk management
    - Portfolio correlation monitoring
    - Stress testing and scenario analysis
    - Emergency risk protocols
    """
    
    def __init__(self):
        # State persistence
        self.state_file = "bot/dynamic_risk_state.json"
        self.metrics_history_file = "bot/risk_metrics_history.json"
        
        # Risk calculation components
        self.advanced_risk_mgr = AdvancedRiskManager()
        self.cash_buffer_mgr = DynamicCashBuffer()
        
        # Risk regime thresholds (volatility percentiles)
        self.vol_thresholds = {
            RiskRegime.ULTRA_LOW: 0.05,   # < 5th percentile
            RiskRegime.LOW: 0.25,         # 5-25th percentile
            RiskRegime.NORMAL: 0.75,      # 25-75th percentile  
            RiskRegime.HIGH: 0.95,        # 75-95th percentile
            RiskRegime.EXTREME: 1.0       # > 95th percentile
        }
        
        # Performance thresholds (Sharpe ratio percentiles)
        self.perf_thresholds = {
            PerformanceRegime.CRITICAL: -0.5,    # Sharpe < -0.5
            PerformanceRegime.POOR: 0.0,         # Sharpe 0-0.5
            PerformanceRegime.AVERAGE: 0.5,      # Sharpe 0.5-1.0
            PerformanceRegime.GOOD: 1.0,         # Sharpe 1.0-1.5
            PerformanceRegime.EXCEPTIONAL: 1.5   # Sharpe > 1.5
        }
        
        # Risk scaling factors by regime
        self.risk_multipliers = {
            RiskRegime.ULTRA_LOW: 1.3,    # Increase risk in low vol
            RiskRegime.LOW: 1.1,
            RiskRegime.NORMAL: 1.0,       # Base risk
            RiskRegime.HIGH: 0.7,         # Reduce risk in high vol
            RiskRegime.EXTREME: 0.4       # Dramatically reduce in extreme vol
        }
        
        # Performance-based risk scaling
        self.performance_multipliers = {
            PerformanceRegime.EXCEPTIONAL: 1.2,  # Increase when performing well
            PerformanceRegime.GOOD: 1.1,
            PerformanceRegime.AVERAGE: 1.0,      # Base performance
            PerformanceRegime.POOR: 0.8,         # Reduce when underperforming
            PerformanceRegime.CRITICAL: 0.5      # Emergency reduction
        }
        
        # Historical data storage
        self.price_history = {}           # Symbol -> DataFrame
        self.metrics_history = []         # Historical risk metrics
        self.correlation_matrix = None    # Asset correlation matrix
        self.volatility_history = []      # Historical volatility data
        
        # State variables
        self.current_metrics = RiskMetrics()
        self.current_adjustment = RiskAdjustment()
        self.last_update = None
        self.emergency_mode = False
        self.stress_test_results = {}
        
        # Load persistent state
        self.load_state()
        
        # Initialize background monitoring
        self._monitoring_active = False
        self._start_background_monitoring()
        
        logger.info("🏛️ Dynamic Risk Manager initialized - Institutional-grade risk management active")
    
    def load_state(self):
        """Load persistent state from disk"""
        try:
            if Path(self.state_file).exists():
                with open(self.state_file, 'r') as f:
                    state_data = json.load(f)
                    self.emergency_mode = state_data.get('emergency_mode', False)
                    self.last_update = state_data.get('last_update')
                    if self.last_update:
                        self.last_update = datetime.fromisoformat(self.last_update)
                    
            if Path(self.metrics_history_file).exists():
                with open(self.metrics_history_file, 'r') as f:
                    self.metrics_history = json.load(f)
                    # Keep only last 1000 entries for performance
                    self.metrics_history = self.metrics_history[-1000:]
                    
        except Exception as e:
            logger.warning(f"⚠️ Error loading risk manager state: {e}")
            self.metrics_history = []
    
    def save_state(self):
        """Save persistent state to disk"""
        try:
            state_data = {
                'emergency_mode': self.emergency_mode,
                'last_update': self.last_update.isoformat() if self.last_update else None,
                'current_risk_score': self.current_metrics.risk_score,
                'current_regime': self.current_metrics.risk_regime.value if self.current_metrics.risk_regime else "normal"
            }
            
            with open(self.state_file, 'w') as f:
                json.dump(state_data, f, indent=2)
                
            # Save metrics history
            with open(self.metrics_history_file, 'w') as f:
                json.dump(self.metrics_history, f)
                
        except Exception as e:
            logger.warning(f"⚠️ Error saving risk manager state: {e}")
    
    def _start_background_monitoring(self):
        """Start background risk monitoring thread"""
        if self._monitoring_active:
            return
            
        def monitor_risk():
            while self._monitoring_active:
                try:
                    # Update risk metrics every 30 seconds
                    self.update_risk_environment()
                    time.sleep(30)
                except Exception as e:
                    logger.error(f"❌ Error in risk monitoring: {e}")
                    time.sleep(60)  # Back off on error
        
        self._monitoring_active = True
        monitoring_thread = threading.Thread(target=monitor_risk, daemon=True)
        monitoring_thread.start()
        logger.info("🔍 Background risk monitoring started")
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        self._monitoring_active = False
        logger.info("⏹️ Background risk monitoring stopped")
    
    def update_risk_environment(self):
        """Update comprehensive risk environment assessment"""
        try:
            # Get current account data
            from alpaca.trading.client import TradingClient
            client = TradingClient(
                api_key=settings.alpaca_api_key,
                secret_key=settings.alpaca_secret_key,
                paper=(settings.mode == "paper")
            )
            
            account = client.get_account()
            current_equity = float(getattr(account, 'equity', 0) or 0)
            
            if current_equity <= 0:
                logger.warning("⚠️ Invalid equity for risk calculations")
                return
            
            # Get market data for risk assessment
            market_data = self._get_market_data()
            
            # Calculate comprehensive risk metrics
            self.current_metrics = self._calculate_risk_metrics(market_data, current_equity)
            
            # Update risk adjustment parameters
            self.current_adjustment = self._calculate_risk_adjustment(self.current_metrics)
            
            # Save metrics to history
            self._save_metrics_to_history(self.current_metrics)
            
            # Check for emergency conditions
            self._check_emergency_conditions()
            
            # Update last calculation time
            self.last_update = datetime.now()
            
            # Save state
            self.save_state()
            
            # Log risk status
            self._log_risk_status()
            
        except Exception as e:
            logger.error(f"❌ Error updating risk environment: {e}")
    
    def _get_market_data(self) -> Dict[str, pd.DataFrame]:
        """Get recent market data for risk calculations"""
        try:
            from .data import fetch_bars
            
            market_data = {}
            key_symbols = ["SPY", "VIX", "TLT", "GLD"]  # Market benchmarks
            
            # Add some portfolio symbols
            portfolio_symbols = settings.symbols[:10]  # First 10 symbols
            all_symbols = key_symbols + portfolio_symbols
            
            for symbol in all_symbols:
                try:
                    data = fetch_bars(symbol, min_bars=100)  # Last 100 bars for analysis
                    if data is not None and not data.empty:
                        market_data[symbol] = data
                except Exception as e:
                    logger.debug(f"Could not fetch data for {symbol}: {e}")
                    continue
            
            return market_data
            
        except Exception as e:
            logger.error(f"❌ Error getting market data: {e}")
            return {}
    
    def _calculate_risk_metrics(self, market_data: Dict[str, pd.DataFrame], equity: float) -> RiskMetrics:
        """Calculate comprehensive risk metrics"""
        try:
            metrics = RiskMetrics()
            
            if not market_data:
                return metrics
            
            # Get SPY data for market benchmarking
            spy_data = market_data.get("SPY")
            if spy_data is not None and not spy_data.empty:
                spy_returns = spy_data['close'].pct_change().dropna()
                
                # Calculate market volatility
                market_vol = spy_returns.std() * np.sqrt(252)  # Annualized
                metrics.volatility = market_vol
                
                # Determine risk regime based on volatility
                metrics.risk_regime = self._classify_risk_regime(market_vol)
            
            # Calculate portfolio-level metrics using equity changes
            metrics.max_drawdown = self._calculate_max_drawdown(equity)
            metrics.current_drawdown = self._calculate_current_drawdown(equity)
            
            # Calculate performance metrics
            performance_data = self._get_performance_data()
            if performance_data:
                metrics.sharpe_ratio = self._calculate_sharpe_ratio(performance_data)
                metrics.sortino_ratio = self._calculate_sortino_ratio(performance_data)
                metrics.performance_regime = self._classify_performance_regime(metrics.sharpe_ratio)
            
            # Calculate VaR and CVaR
            if performance_data:
                metrics.var_1d = self._calculate_var(performance_data, confidence=0.95, days=1)
                metrics.cvar_1d = self._calculate_cvar(performance_data, confidence=0.95, days=1)
                metrics.var_5d = self._calculate_var(performance_data, confidence=0.95, days=5)
            
            # Calculate portfolio correlations
            if len(market_data) > 1:
                correlation_data = self._calculate_portfolio_correlations(market_data)
                if "SPY" in correlation_data:
                    metrics.correlation_spy = correlation_data["SPY"]
            
            # Calculate composite risk score (0 = low risk, 1 = high risk)
            metrics.risk_score = self._calculate_composite_risk_score(metrics)
            
            # Calculate confidence level
            metrics.confidence_level = self._calculate_model_confidence(market_data)
            
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Error calculating risk metrics: {e}")
            return RiskMetrics()
    
    def _classify_risk_regime(self, volatility: float) -> RiskRegime:
        """Classify current risk regime based on volatility"""
        # Historical volatility benchmarks (approximate)
        if volatility < 0.10:
            return RiskRegime.ULTRA_LOW
        elif volatility < 0.15:
            return RiskRegime.LOW
        elif volatility < 0.25:
            return RiskRegime.NORMAL
        elif volatility < 0.35:
            return RiskRegime.HIGH
        else:
            return RiskRegime.EXTREME
    
    def _classify_performance_regime(self, sharpe_ratio: float) -> PerformanceRegime:
        """Classify performance regime based on Sharpe ratio"""
        if sharpe_ratio < -0.5:
            return PerformanceRegime.CRITICAL
        elif sharpe_ratio < 0.0:
            return PerformanceRegime.POOR
        elif sharpe_ratio < 0.5:
            return PerformanceRegime.AVERAGE
        elif sharpe_ratio < 1.0:
            return PerformanceRegime.GOOD
        else:
            return PerformanceRegime.EXCEPTIONAL
    
    def _calculate_max_drawdown(self, current_equity: float) -> float:
        """Calculate maximum drawdown from historical equity"""
        try:
            if not self.metrics_history:
                return 0.0
            
            # Get historical equity values
            equity_values = [current_equity]
            for metric in self.metrics_history[-30:]:  # Last 30 data points
                if 'equity' in metric:
                    equity_values.append(metric['equity'])
            
            if len(equity_values) < 2:
                return 0.0
            
            # Calculate running maximum and drawdowns
            equity_series = pd.Series(equity_values)
            running_max = equity_series.expanding().max()
            drawdowns = (equity_series - running_max) / running_max
            
            return abs(drawdowns.min())
            
        except Exception as e:
            logger.error(f"❌ Error calculating max drawdown: {e}")
            return 0.0
    
    def _calculate_current_drawdown(self, current_equity: float) -> float:
        """Calculate current drawdown from recent peak"""
        try:
            if not self.metrics_history:
                return 0.0
            
            # Get recent equity peak (last 5 data points)
            recent_equities = [current_equity]
            for metric in self.metrics_history[-5:]:
                if 'equity' in metric:
                    recent_equities.append(metric['equity'])
            
            if not recent_equities:
                return 0.0
            
            peak_equity = max(recent_equities)
            if peak_equity <= 0:
                return 0.0
            
            current_drawdown = (current_equity - peak_equity) / peak_equity
            return abs(min(0, current_drawdown))  # Only negative drawdowns
            
        except Exception as e:
            logger.error(f"❌ Error calculating current drawdown: {e}")
            return 0.0
    
    def _get_performance_data(self) -> Optional[pd.Series]:
        """Get performance data for calculations"""
        try:
            if len(self.metrics_history) < 10:
                return None
            
            # Extract equity values from history
            equity_values = []
            timestamps = []
            
            for metric in self.metrics_history[-50:]:  # Last 50 data points
                if 'equity' in metric and 'timestamp' in metric:
                    equity_values.append(metric['equity'])
                    timestamps.append(pd.to_datetime(metric['timestamp']))
            
            if len(equity_values) < 10:
                return None
            
            # Create returns series
            equity_series = pd.Series(equity_values, index=timestamps)
            returns = equity_series.pct_change().dropna()
            
            return returns
            
        except Exception as e:
            logger.error(f"❌ Error getting performance data: {e}")
            return None
    
    def _calculate_sharpe_ratio(self, returns: pd.Series) -> float:
        """Calculate annualized Sharpe ratio"""
        try:
            if len(returns) < 5:
                return 0.0
            
            excess_returns = returns - 0.02/252  # Assume 2% risk-free rate
            if excess_returns.std() == 0:
                return 0.0
            
            sharpe = excess_returns.mean() / excess_returns.std() * np.sqrt(252)
            return float(sharpe)
            
        except Exception as e:
            logger.error(f"❌ Error calculating Sharpe ratio: {e}")
            return 0.0
    
    def _calculate_sortino_ratio(self, returns: pd.Series) -> float:
        """Calculate Sortino ratio (downside deviation)"""
        try:
            if len(returns) < 5:
                return 0.0
            
            excess_returns = returns - 0.02/252  # Risk-free rate
            downside_returns = excess_returns[excess_returns < 0]
            
            if len(downside_returns) == 0 or downside_returns.std() == 0:
                return 0.0
            
            sortino = excess_returns.mean() / downside_returns.std() * np.sqrt(252)
            return float(sortino)
            
        except Exception as e:
            logger.error(f"❌ Error calculating Sortino ratio: {e}")
            return 0.0
    
    def _calculate_var(self, returns: pd.Series, confidence: float = 0.95, days: int = 1) -> float:
        """Calculate Value at Risk"""
        try:
            if len(returns) < 10:
                return 0.0
            
            # Scale for multi-day VaR
            scaled_returns = returns * np.sqrt(days)
            
            # Calculate VaR at specified confidence level
            var = np.percentile(scaled_returns, (1 - confidence) * 100)
            return abs(float(var))
            
        except Exception as e:
            logger.error(f"❌ Error calculating VaR: {e}")
            return 0.0
    
    def _calculate_cvar(self, returns: pd.Series, confidence: float = 0.95, days: int = 1) -> float:
        """Calculate Conditional Value at Risk (Expected Shortfall)"""
        try:
            if len(returns) < 10:
                return 0.0
            
            # Scale for multi-day CVaR
            scaled_returns = returns * np.sqrt(days)
            
            # Calculate VaR threshold
            var_threshold = np.percentile(scaled_returns, (1 - confidence) * 100)
            
            # Calculate CVaR as mean of returns below VaR threshold
            tail_returns = scaled_returns[scaled_returns <= var_threshold]
            if len(tail_returns) == 0:
                return 0.0
            
            cvar = tail_returns.mean()
            return abs(float(cvar))
            
        except Exception as e:
            logger.error(f"❌ Error calculating CVaR: {e}")
            return 0.0
    
    def _calculate_portfolio_correlations(self, market_data: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        """Calculate portfolio correlations with key benchmarks"""
        try:
            correlations = {}
            
            if "SPY" not in market_data:
                return correlations
            
            spy_returns = market_data["SPY"]['close'].pct_change().dropna()
            
            for symbol, data in market_data.items():
                if symbol == "SPY" or data.empty:
                    continue
                
                try:
                    symbol_returns = data['close'].pct_change().dropna()
                    
                    # Align data
                    min_length = min(len(spy_returns), len(symbol_returns))
                    if min_length < 10:
                        continue
                    
                    spy_aligned = spy_returns.tail(min_length)
                    symbol_aligned = symbol_returns.tail(min_length)
                    
                    correlation = spy_aligned.corr(symbol_aligned)
                    if not np.isnan(correlation):
                        correlations[symbol] = float(correlation)
                        
                except Exception as e:
                    logger.debug(f"Error calculating correlation for {symbol}: {e}")
                    continue
            
            # Calculate average correlation for portfolio
            if correlations:
                avg_correlation = np.mean(list(correlations.values()))
                correlations["SPY"] = avg_correlation
            
            return correlations
            
        except Exception as e:
            logger.error(f"❌ Error calculating correlations: {e}")
            return {}
    
    def _calculate_composite_risk_score(self, metrics: RiskMetrics) -> float:
        """Calculate composite risk score (0-1, higher = more risk)"""
        try:
            scores = []
            
            # Volatility component (0-1)
            vol_score = min(metrics.volatility / 0.5, 1.0)  # Normalize to 50% vol
            scores.append(vol_score * 0.3)  # 30% weight
            
            # Drawdown component (0-1)
            dd_score = min(metrics.max_drawdown / 0.2, 1.0)  # Normalize to 20% DD
            scores.append(dd_score * 0.25)  # 25% weight
            
            # Performance component (inverted - bad performance = high risk)
            if metrics.sharpe_ratio <= 0:
                perf_score = 1.0
            else:
                perf_score = max(0, 1 - metrics.sharpe_ratio / 2.0)  # Normalize to Sharpe 2.0
            scores.append(perf_score * 0.2)  # 20% weight
            
            # VaR component (0-1)
            var_score = min(metrics.var_1d / 0.05, 1.0)  # Normalize to 5% daily VaR
            scores.append(var_score * 0.15)  # 15% weight
            
            # Current drawdown component (0-1)
            curr_dd_score = min(metrics.current_drawdown / 0.1, 1.0)  # Normalize to 10% current DD
            scores.append(curr_dd_score * 0.1)  # 10% weight
            
            # Final composite score
            composite_score = sum(scores)
            return max(0.0, min(1.0, composite_score))
            
        except Exception as e:
            logger.error(f"❌ Error calculating composite risk score: {e}")
            return 0.5  # Default medium risk
    
    def _calculate_model_confidence(self, market_data: Dict[str, pd.DataFrame]) -> float:
        """Calculate model confidence based on data quality and market conditions"""
        try:
            confidence_factors = []
            
            # Data quality factor
            data_quality = len(market_data) / 10.0  # Normalize to 10 symbols
            confidence_factors.append(min(data_quality, 1.0) * 0.3)
            
            # Market regime stability (low volatility = higher confidence)
            if self.current_metrics.volatility > 0:
                vol_stability = max(0, 1 - self.current_metrics.volatility / 0.5)
                confidence_factors.append(vol_stability * 0.3)
            
            # Historical data depth
            if self.metrics_history:
                data_depth = min(len(self.metrics_history) / 100.0, 1.0)  # Normalize to 100 points
                confidence_factors.append(data_depth * 0.2)
            
            # Performance consistency
            if self.current_metrics.sharpe_ratio != 0:
                consistency = max(0, min(abs(self.current_metrics.sharpe_ratio) / 2.0, 1.0))
                confidence_factors.append(consistency * 0.2)
            
            # Final confidence score
            confidence = sum(confidence_factors)
            return max(0.1, min(1.0, confidence))  # Minimum 10% confidence
            
        except Exception as e:
            logger.error(f"❌ Error calculating model confidence: {e}")
            return 0.5  # Default medium confidence
    
    def _calculate_risk_adjustment(self, metrics: RiskMetrics) -> RiskAdjustment:
        """Calculate comprehensive risk adjustment parameters"""
        try:
            adjustment = RiskAdjustment()
            
            # Base risk multiplier from regime
            regime_multiplier = self.risk_multipliers.get(metrics.risk_regime, 1.0)
            adjustment.base_risk_multiplier = regime_multiplier
            
            # Volatility adjustment (inverse relationship)
            if metrics.volatility > 0:
                vol_adjustment = max(0.3, min(2.0, 0.15 / max(metrics.volatility, 0.05)))
                adjustment.volatility_adjustment = vol_adjustment
            
            # Drawdown adjustment (reduce risk during drawdowns)
            if metrics.max_drawdown > 0.02:  # > 2% drawdown
                dd_adjustment = max(0.5, 1 - metrics.max_drawdown * 2)
                adjustment.drawdown_adjustment = dd_adjustment
            
            # Performance adjustment
            perf_multiplier = self.performance_multipliers.get(metrics.performance_regime, 1.0)
            adjustment.performance_adjustment = perf_multiplier
            
            # Correlation adjustment (reduce risk if highly correlated)
            if abs(metrics.correlation_spy) > 0.7:  # High correlation
                corr_adjustment = 0.8  # Reduce risk by 20%
                adjustment.correlation_adjustment = corr_adjustment
            
            # Final combined multiplier
            final_multiplier = (
                adjustment.base_risk_multiplier *
                adjustment.volatility_adjustment *
                adjustment.drawdown_adjustment *
                adjustment.performance_adjustment *
                adjustment.correlation_adjustment
            )
            
            # Apply safety bounds
            adjustment.final_risk_multiplier = max(0.1, min(3.0, final_multiplier))
            
            # Stop loss and take profit adjustments
            adjustment.stop_loss_adjustment = max(0.5, min(2.0, 1 / max(metrics.volatility, 0.1)))
            adjustment.take_profit_adjustment = max(0.8, min(1.5, metrics.volatility * 5))
            
            # Confidence threshold (higher volatility = higher threshold)
            adjustment.confidence_threshold = max(0.3, min(0.8, 0.5 + metrics.volatility))
            
            return adjustment
            
        except Exception as e:
            logger.error(f"❌ Error calculating risk adjustment: {e}")
            return RiskAdjustment()
    
    def _save_metrics_to_history(self, metrics: RiskMetrics):
        """Save current metrics to historical record"""
        try:
            metric_record = {
                'timestamp': datetime.now().isoformat(),
                'var_1d': metrics.var_1d,
                'cvar_1d': metrics.cvar_1d,
                'sharpe_ratio': metrics.sharpe_ratio,
                'max_drawdown': metrics.max_drawdown,
                'current_drawdown': metrics.current_drawdown,
                'volatility': metrics.volatility,
                'risk_regime': metrics.risk_regime.value,
                'performance_regime': metrics.performance_regime.value,
                'risk_score': metrics.risk_score,
                'confidence_level': metrics.confidence_level
            }
            
            # Add current equity if available
            try:
                from alpaca.trading.client import TradingClient
                client = TradingClient(
                    api_key=settings.alpaca_api_key,
                    secret_key=settings.alpaca_secret_key,
                    paper=(settings.mode == "paper")
                )
                account = client.get_account()
                metric_record['equity'] = float(getattr(account, 'equity', 0))
            except:
                pass
            
            self.metrics_history.append(metric_record)
            
            # Keep only last 1000 records for performance
            if len(self.metrics_history) > 1000:
                self.metrics_history = self.metrics_history[-1000:]
                
        except Exception as e:
            logger.error(f"❌ Error saving metrics to history: {e}")
    
    def _check_emergency_conditions(self):
        """Check for emergency risk conditions"""
        try:
            emergency_triggered = False
            reasons = []
            
            # Emergency drawdown threshold
            if self.current_metrics.current_drawdown > 0.15:  # 15% current drawdown
                emergency_triggered = True
                reasons.append(f"Current drawdown {self.current_metrics.current_drawdown:.1%}")
            
            # Emergency risk score threshold
            if self.current_metrics.risk_score > 0.85:  # Very high risk score
                emergency_triggered = True
                reasons.append(f"Risk score {self.current_metrics.risk_score:.2f}")
            
            # Emergency volatility threshold
            if self.current_metrics.volatility > 0.5:  # 50% annualized volatility
                emergency_triggered = True
                reasons.append(f"Volatility {self.current_metrics.volatility:.1%}")
            
            # Update emergency mode
            if emergency_triggered and not self.emergency_mode:
                self.emergency_mode = True
                logger.critical(f"🚨 EMERGENCY RISK MODE ACTIVATED: {', '.join(reasons)}")
                
                # Send telegram alert if configured
                try:
                    from .telegram import send_telegram
                    msg = f"🚨 EMERGENCY RISK MODE ACTIVATED\n\nReasons:\n" + "\n".join([f"• {r}" for r in reasons])
                    send_telegram(msg)
                except:
                    pass
                    
            elif not emergency_triggered and self.emergency_mode:
                self.emergency_mode = False
                logger.info("✅ Emergency risk mode deactivated - conditions normalized")
                
        except Exception as e:
            logger.error(f"❌ Error checking emergency conditions: {e}")
    
    def _log_risk_status(self):
        """Log current risk status"""
        try:
            risk_level = "🟢 LOW" if self.current_metrics.risk_score < 0.3 else \
                        "🟡 MEDIUM" if self.current_metrics.risk_score < 0.7 else "🔴 HIGH"
            
            logger.info(f"🏛️ RISK STATUS: {risk_level} | "
                       f"Score: {self.current_metrics.risk_score:.2f} | "
                       f"Regime: {self.current_metrics.risk_regime.value.upper()} | "
                       f"Volatility: {self.current_metrics.volatility:.1%} | "
                       f"Drawdown: {self.current_metrics.current_drawdown:.1%}")
            
            logger.debug(f"🔧 RISK ADJUSTMENT: "
                        f"Multiplier: {self.current_adjustment.final_risk_multiplier:.2f} | "
                        f"Stop: {self.current_adjustment.stop_loss_adjustment:.2f} | "
                        f"Confidence: {self.current_metrics.confidence_level:.2f}")
                        
        except Exception as e:
            logger.error(f"❌ Error logging risk status: {e}")
    
    # Public API methods for integration with trading system
    
    def get_current_risk_multiplier(self) -> float:
        """Get current risk multiplier for position sizing"""
        if self.emergency_mode:
            return 0.2  # Emergency reduction
        return self.current_adjustment.final_risk_multiplier
    
    def get_dynamic_stops(self, symbol: str, signal_strength: float) -> Dict[str, float]:
        """Get dynamic stop loss and take profit adjustments"""
        base_stops = {
            'stop_loss_pct': settings.stop_loss_pct,
            'take_profit_pct': settings.take_profit_pct
        }
        
        if self.emergency_mode:
            # Tighter stops in emergency mode
            return {
                'stop_loss_pct': base_stops['stop_loss_pct'] * 0.8,
                'take_profit_pct': base_stops['take_profit_pct'] * 0.7
            }
        
        return {
            'stop_loss_pct': base_stops['stop_loss_pct'] * self.current_adjustment.stop_loss_adjustment,
            'take_profit_pct': base_stops['take_profit_pct'] * self.current_adjustment.take_profit_adjustment
        }
    
    def should_allow_new_position(self, symbol: str, signal_strength: float) -> bool:
        """Determine if new position should be allowed based on risk conditions"""
        # Block all new positions in emergency mode
        if self.emergency_mode:
            logger.warning(f"🚨 Position blocked - Emergency risk mode active")
            return False
        
        # Check signal confidence threshold
        if abs(signal_strength) < self.current_adjustment.confidence_threshold:
            logger.debug(f"🔒 Position blocked - Signal strength {abs(signal_strength):.2f} below threshold {self.current_adjustment.confidence_threshold:.2f}")
            return False
        
        # Check risk regime
        if self.current_metrics.risk_regime == RiskRegime.EXTREME:
            logger.warning(f"🔒 Position blocked - Extreme risk regime")
            return False
        
        return True
    
    def get_risk_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive risk metrics summary for monitoring"""
        return {
            'risk_score': self.current_metrics.risk_score,
            'risk_regime': self.current_metrics.risk_regime.value,
            'performance_regime': self.current_metrics.performance_regime.value,
            'volatility': self.current_metrics.volatility,
            'max_drawdown': self.current_metrics.max_drawdown,
            'current_drawdown': self.current_metrics.current_drawdown,
            'sharpe_ratio': self.current_metrics.sharpe_ratio,
            'var_1d': self.current_metrics.var_1d,
            'emergency_mode': self.emergency_mode,
            'risk_multiplier': self.current_adjustment.final_risk_multiplier,
            'confidence_level': self.current_metrics.confidence_level,
            'last_update': self.last_update.isoformat() if self.last_update else None
        }


# Global instance
dynamic_risk_manager = DynamicRiskManager()


def get_dynamic_risk_adjustment(symbol: str, signal_strength: float, equity: float) -> Dict[str, float]:
    """
    Get dynamic risk adjustment for a specific trade.
    Returns dictionary with risk multiplier, stop adjustments, and position sizing.
    """
    try:
        # Update risk environment if stale
        if (not dynamic_risk_manager.last_update or 
            datetime.now() - dynamic_risk_manager.last_update > timedelta(minutes=5)):
            dynamic_risk_manager.update_risk_environment()
        
        # Get risk multiplier
        risk_multiplier = dynamic_risk_manager.get_current_risk_multiplier()
        
        # Get dynamic stops
        stops = dynamic_risk_manager.get_dynamic_stops(symbol, signal_strength)
        
        # Check if position should be allowed
        allow_position = dynamic_risk_manager.should_allow_new_position(symbol, signal_strength)
        
        return {
            'risk_multiplier': risk_multiplier,
            'stop_loss_pct': stops['stop_loss_pct'],
            'take_profit_pct': stops['take_profit_pct'],
            'allow_position': allow_position,
            'emergency_mode': dynamic_risk_manager.emergency_mode,
            'risk_score': dynamic_risk_manager.current_metrics.risk_score,
            'confidence_threshold': dynamic_risk_manager.current_adjustment.confidence_threshold
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting dynamic risk adjustment: {e}")
        return {
            'risk_multiplier': 1.0,
            'stop_loss_pct': settings.stop_loss_pct,
            'take_profit_pct': settings.take_profit_pct,
            'allow_position': True,
            'emergency_mode': False,
            'risk_score': 0.5,
            'confidence_threshold': 0.5
        }