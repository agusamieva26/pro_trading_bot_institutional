"""
🌪️ ADVANCED VOLATILITY ASSESSMENT ENGINE
Institutional-grade volatility modeling and regime detection system with real-time
calculations for dynamic risk management and portfolio optimization.

Features:
- EWMA (Exponentially Weighted Moving Average) volatility modeling
- GARCH-style volatility forecasting
- Multi-timeframe volatility regime detection (1m, 5m, 15m, 1h, 1d)
- Real-time VaR and CVaR calculations
- Correlation matrix tracking and portfolio risk assessment
- Volatility clustering detection
- Stress testing scenarios and tail risk analysis
- Regime transition modeling (low/medium/high volatility states)
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
import logging

from .util import logger
from .config import settings


class VolatilityRegime(Enum):
    """Volatility regime classification"""
    ULTRA_LOW = "ultra_low"      # Bottom 5% historical volatility
    LOW = "low"                  # 5-20% range
    NORMAL_LOW = "normal_low"    # 20-40% range
    NORMAL = "normal"            # 40-60% range
    NORMAL_HIGH = "normal_high"  # 60-80% range
    HIGH = "high"                # 80-95% range
    EXTREME = "extreme"          # Top 5% historical volatility


class VolatilityTrend(Enum):
    """Volatility trend direction"""
    DECREASING = "decreasing"    # Volatility falling
    STABLE = "stable"            # Volatility stable
    INCREASING = "increasing"    # Volatility rising
    SPIKING = "spiking"         # Volatility rapidly increasing


@dataclass
class VolatilityMetrics:
    """Container for comprehensive volatility metrics"""
    realized_vol_1d: float = 0.0         # 1-day realized volatility
    realized_vol_5d: float = 0.0         # 5-day realized volatility
    realized_vol_20d: float = 0.0        # 20-day realized volatility
    ewma_vol: float = 0.0                # EWMA volatility estimate
    garch_vol: float = 0.0               # GARCH volatility forecast
    vol_regime: VolatilityRegime = VolatilityRegime.NORMAL
    vol_trend: VolatilityTrend = VolatilityTrend.STABLE
    vol_percentile: float = 0.5          # Percentile in historical distribution
    vol_z_score: float = 0.0             # Z-score vs historical mean
    clustering_factor: float = 0.0       # Volatility clustering strength
    autocorr_5lag: float = 0.0           # 5-lag autocorrelation
    skewness: float = 0.0                # Return distribution skewness
    kurtosis: float = 0.0                # Return distribution kurtosis
    tail_risk_score: float = 0.0         # Tail risk assessment score
    regime_stability: float = 0.0        # Regime persistence probability


@dataclass
class RiskMetrics:
    """Container for risk assessment metrics"""
    var_95_1d: float = 0.0               # 1-day 95% VaR
    var_99_1d: float = 0.0               # 1-day 99% VaR
    cvar_95_1d: float = 0.0              # 1-day 95% CVaR
    cvar_99_1d: float = 0.0              # 1-day 99% CVaR
    var_95_5d: float = 0.0               # 5-day 95% VaR
    max_daily_loss: float = 0.0          # Maximum single-day loss estimate
    downside_deviation: float = 0.0      # Downside deviation measure
    upside_capture: float = 0.0          # Upside vs downside asymmetry
    stress_test_loss: float = 0.0        # Worst-case stress scenario loss


@dataclass
class CorrelationMetrics:
    """Container for correlation analysis"""
    market_correlation: float = 0.0      # Correlation with market (SPY)
    sector_correlation: float = 0.0      # Average sector correlation
    crypto_correlation: float = 0.0      # Correlation with crypto market
    portfolio_diversification: float = 0.0  # Portfolio diversification score
    concentration_risk: float = 0.0      # Concentration risk score
    correlation_regime: str = "normal"   # High/normal/low correlation regime


class VolatilityAssessor:
    """
    Advanced volatility assessment engine that provides real-time volatility modeling,
    regime detection, and comprehensive risk analytics for institutional trading.
    
    Core Functions:
    - Real-time volatility calculation using multiple models
    - Multi-timeframe regime detection and classification
    - VaR/CVaR calculations with stress testing
    - Correlation matrix tracking and portfolio risk assessment
    - Volatility clustering and trend analysis
    - Tail risk and extreme event modeling
    """
    
    def __init__(self):
        # State persistence
        self.state_file = "bot/volatility_state.json"
        self.history_file = "bot/volatility_history.json"
        
        # Model parameters
        self.ewma_lambda = 0.94              # EWMA decay factor (RiskMetrics standard)
        self.garch_alpha = 0.1               # GARCH alpha parameter
        self.garch_beta = 0.85               # GARCH beta parameter
        self.vol_lookback = 252              # Lookback window for historical volatility
        self.regime_window = 50              # Window for regime detection
        
        # Volatility regime thresholds (percentiles)
        self.regime_thresholds = {
            VolatilityRegime.ULTRA_LOW: 0.05,
            VolatilityRegime.LOW: 0.20,
            VolatilityRegime.NORMAL_LOW: 0.40,
            VolatilityRegime.NORMAL: 0.60,
            VolatilityRegime.NORMAL_HIGH: 0.80,
            VolatilityRegime.HIGH: 0.95,
            VolatilityRegime.EXTREME: 1.0
        }
        
        # Historical data storage
        self.price_data = {}                 # Symbol -> DataFrame
        self.volatility_history = {}         # Symbol -> historical volatility
        self.correlation_matrix = None       # Current correlation matrix
        self.regime_history = []             # Historical regime data
        
        # Current state
        self.current_metrics = {}            # Symbol -> VolatilityMetrics
        self.current_risk_metrics = {}       # Symbol -> RiskMetrics
        self.current_correlations = CorrelationMetrics()
        self.market_regime = VolatilityRegime.NORMAL
        self.last_update = None
        
        # Background monitoring
        self._monitoring_active = False
        
        # Load persistent state
        self.load_state()
        
        # Initialize background monitoring
        self._start_background_monitoring()
        
        logger.info("🌪️ Volatility Assessor initialized - Advanced volatility modeling active")
    
    def load_state(self):
        """Load persistent state from disk"""
        try:
            if Path(self.state_file).exists():
                with open(self.state_file, 'r') as f:
                    state_data = json.load(f)
                    self.market_regime = VolatilityRegime(state_data.get('market_regime', 'normal'))
                    self.last_update = state_data.get('last_update')
                    if self.last_update:
                        self.last_update = datetime.fromisoformat(self.last_update)
                    
            if Path(self.history_file).exists():
                with open(self.history_file, 'r') as f:
                    self.regime_history = json.load(f)
                    # Keep only last 1000 entries
                    self.regime_history = self.regime_history[-1000:]
                    
        except Exception as e:
            logger.warning(f"⚠️ Error loading volatility assessor state: {e}")
            self.regime_history = []
    
    def save_state(self):
        """Save persistent state to disk"""
        try:
            state_data = {
                'market_regime': self.market_regime.value,
                'last_update': self.last_update.isoformat() if self.last_update else None
            }
            
            with open(self.state_file, 'w') as f:
                json.dump(state_data, f, indent=2)
                
            # Save regime history
            with open(self.history_file, 'w') as f:
                json.dump(self.regime_history, f)
                
        except Exception as e:
            logger.warning(f"⚠️ Error saving volatility assessor state: {e}")
    
    def _start_background_monitoring(self):
        """Start background volatility monitoring"""
        if self._monitoring_active:
            return
            
        def monitor_volatility():
            while self._monitoring_active:
                try:
                    # Update volatility assessment every 60 seconds
                    self.update_volatility_assessment()
                    time.sleep(60)
                except Exception as e:
                    logger.error(f"❌ Error in volatility monitoring: {e}")
                    time.sleep(120)  # Back off on error
        
        self._monitoring_active = True
        monitoring_thread = threading.Thread(target=monitor_volatility, daemon=True)
        monitoring_thread.start()
        logger.info("🔍 Background volatility monitoring started")
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        self._monitoring_active = False
        logger.info("⏹️ Volatility monitoring stopped")
    
    def update_volatility_assessment(self):
        """Update comprehensive volatility assessment"""
        try:
            # Get market data for assessment
            market_data = self._get_market_data()
            
            if not market_data:
                logger.warning("⚠️ No market data available for volatility assessment")
                return
            
            # Calculate volatility metrics for each symbol
            self.current_metrics = {}
            for symbol, data in market_data.items():
                metrics = self._calculate_volatility_metrics(symbol, data)
                self.current_metrics[symbol] = metrics
                
                # Calculate risk metrics
                risk_metrics = self._calculate_risk_metrics(symbol, data)
                self.current_risk_metrics[symbol] = risk_metrics
            
            # Calculate correlation metrics
            self.current_correlations = self._calculate_correlation_metrics(market_data)
            
            # Determine overall market regime
            self.market_regime = self._determine_market_regime()
            
            # Save regime to history
            self._save_regime_to_history()
            
            # Update timestamp
            self.last_update = datetime.now()
            
            # Save state
            self.save_state()
            
            # Log assessment
            self._log_volatility_status()
            
        except Exception as e:
            logger.error(f"❌ Error updating volatility assessment: {e}")
    
    def _get_market_data(self) -> Dict[str, pd.DataFrame]:
        """Get market data for volatility assessment"""
        try:
            from .data import fetch_bars
            
            market_data = {}
            
            # Key market symbols for assessment
            key_symbols = ["SPY", "QQQ", "VIX", "TLT", "GLD"]
            
            # Add portfolio symbols
            portfolio_symbols = settings.symbols[:15]  # First 15 symbols
            all_symbols = list(set(key_symbols + portfolio_symbols))
            
            # Fetch data in parallel for efficiency
            with ThreadPoolExecutor(max_workers=5) as executor:
                future_to_symbol = {
                    executor.submit(fetch_bars, symbol, min_bars=300): symbol 
                    for symbol in all_symbols
                }
                
                for future in as_completed(future_to_symbol):
                    symbol = future_to_symbol[future]
                    try:
                        data = future.result(timeout=10)
                        if data is not None and not data.empty and len(data) >= 50:
                            market_data[symbol] = data
                    except Exception as e:
                        logger.debug(f"Could not fetch data for {symbol}: {e}")
                        continue
            
            return market_data
            
        except Exception as e:
            logger.error(f"❌ Error getting market data for volatility: {e}")
            return {}
    
    def _calculate_volatility_metrics(self, symbol: str, data: pd.DataFrame) -> VolatilityMetrics:
        """Calculate comprehensive volatility metrics for a symbol"""
        try:
            metrics = VolatilityMetrics()
            
            if len(data) < 20:
                return metrics
            
            # Calculate returns
            returns = data['close'].pct_change().dropna()
            if len(returns) < 10:
                return metrics
            
            # Realized volatilities (annualized)
            if len(returns) >= 1:
                metrics.realized_vol_1d = returns.tail(1).std() * np.sqrt(252)
            if len(returns) >= 5:
                metrics.realized_vol_5d = returns.tail(5).std() * np.sqrt(252)
            if len(returns) >= 20:
                metrics.realized_vol_20d = returns.tail(20).std() * np.sqrt(252)
            
            # EWMA volatility
            metrics.ewma_vol = self._calculate_ewma_volatility(returns)
            
            # GARCH volatility forecast
            metrics.garch_vol = self._calculate_garch_volatility(returns)
            
            # Volatility regime classification
            metrics.vol_regime = self._classify_volatility_regime(metrics.ewma_vol, symbol)
            
            # Volatility trend
            metrics.vol_trend = self._detect_volatility_trend(returns)
            
            # Statistical measures
            if len(returns) >= 50:
                # Historical percentile
                historical_vols = returns.rolling(20).std() * np.sqrt(252)
                historical_vols = historical_vols.dropna()
                if len(historical_vols) > 0:
                    metrics.vol_percentile = stats.percentileofscore(historical_vols, metrics.ewma_vol) / 100
                
                # Z-score
                if historical_vols.std() > 0:
                    metrics.vol_z_score = (metrics.ewma_vol - historical_vols.mean()) / historical_vols.std()
            
            # Volatility clustering
            metrics.clustering_factor = self._calculate_clustering_factor(returns)
            
            # Autocorrelation
            if len(returns) >= 10:
                try:
                    abs_returns = np.abs(returns)
                    if len(abs_returns) > 5:
                        autocorr = abs_returns.autocorr(lag=5)
                        metrics.autocorr_5lag = autocorr if not np.isnan(autocorr) else 0.0
                except:
                    metrics.autocorr_5lag = 0.0
            
            # Distribution statistics
            if len(returns) >= 30:
                metrics.skewness = float(returns.skew())
                metrics.kurtosis = float(returns.kurtosis())
            
            # Tail risk score
            metrics.tail_risk_score = self._calculate_tail_risk_score(returns)
            
            # Regime stability
            metrics.regime_stability = self._calculate_regime_stability(symbol)
            
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Error calculating volatility metrics for {symbol}: {e}")
            return VolatilityMetrics()
    
    def _calculate_ewma_volatility(self, returns: pd.Series) -> float:
        """Calculate EWMA volatility using RiskMetrics methodology"""
        try:
            if len(returns) < 2:
                return 0.0
            
            # Initialize with sample variance
            ewma_var = returns.var()
            
            # Apply EWMA recursively
            for ret in returns:
                ewma_var = self.ewma_lambda * ewma_var + (1 - self.ewma_lambda) * (ret ** 2)
            
            # Convert to annualized volatility
            ewma_vol = np.sqrt(ewma_var * 252)
            
            return float(ewma_vol)
            
        except Exception as e:
            logger.error(f"❌ Error calculating EWMA volatility: {e}")
            return 0.0
    
    def _calculate_garch_volatility(self, returns: pd.Series) -> float:
        """Calculate GARCH(1,1) volatility forecast"""
        try:
            if len(returns) < 10:
                return 0.0
            
            # Simple GARCH(1,1) implementation
            # Start with sample variance
            long_run_var = returns.var()
            current_var = long_run_var
            
            # Apply GARCH equation: σ²(t) = ω + α*ε²(t-1) + β*σ²(t-1)
            omega = (1 - self.garch_alpha - self.garch_beta) * long_run_var
            
            for ret in returns.tail(min(50, len(returns))):
                current_var = omega + self.garch_alpha * (ret ** 2) + self.garch_beta * current_var
            
            # Convert to annualized volatility
            garch_vol = np.sqrt(current_var * 252)
            
            return float(garch_vol)
            
        except Exception as e:
            logger.error(f"❌ Error calculating GARCH volatility: {e}")
            return 0.0
    
    def _classify_volatility_regime(self, volatility: float, symbol: str) -> VolatilityRegime:
        """Classify volatility regime based on historical distribution"""
        try:
            # Use historical volatility data if available
            if symbol in self.volatility_history and len(self.volatility_history[symbol]) > 50:
                historical_vols = self.volatility_history[symbol]
                percentile = stats.percentileofscore(historical_vols, volatility) / 100
            else:
                # Use market-wide benchmarks
                if volatility < 0.10:
                    percentile = 0.05
                elif volatility < 0.15:
                    percentile = 0.25
                elif volatility < 0.25:
                    percentile = 0.50
                elif volatility < 0.35:
                    percentile = 0.75
                else:
                    percentile = 0.95
            
            # Classify regime based on percentile
            for regime in VolatilityRegime:
                if percentile <= self.regime_thresholds[regime]:
                    return regime
            
            return VolatilityRegime.EXTREME
            
        except Exception as e:
            logger.error(f"❌ Error classifying volatility regime: {e}")
            return VolatilityRegime.NORMAL
    
    def _detect_volatility_trend(self, returns: pd.Series) -> VolatilityTrend:
        """Detect volatility trend direction"""
        try:
            if len(returns) < 20:
                return VolatilityTrend.STABLE
            
            # Calculate rolling volatility
            rolling_vol = returns.rolling(5).std() * np.sqrt(252)
            rolling_vol = rolling_vol.dropna()
            
            if len(rolling_vol) < 10:
                return VolatilityTrend.STABLE
            
            # Calculate trend slope
            recent_vols = rolling_vol.tail(10)
            x = np.arange(len(recent_vols))
            slope = np.polyfit(x, recent_vols, 1)[0]
            
            # Current vs recent volatility
            current_vol = recent_vols.iloc[-1]
            avg_vol = recent_vols.mean()
            
            # Classify trend
            if slope > 0.01 and current_vol > avg_vol * 1.2:
                return VolatilityTrend.SPIKING
            elif slope > 0.005:
                return VolatilityTrend.INCREASING
            elif slope < -0.005:
                return VolatilityTrend.DECREASING
            else:
                return VolatilityTrend.STABLE
                
        except Exception as e:
            logger.error(f"❌ Error detecting volatility trend: {e}")
            return VolatilityTrend.STABLE
    
    def _calculate_clustering_factor(self, returns: pd.Series) -> float:
        """Calculate volatility clustering strength"""
        try:
            if len(returns) < 30:
                return 0.0
            
            # Calculate absolute returns
            abs_returns = np.abs(returns)
            
            # Calculate autocorrelations at multiple lags
            autocorrs = []
            for lag in [1, 2, 3, 5, 10]:
                if len(abs_returns) > lag:
                    try:
                        autocorr = abs_returns.autocorr(lag=lag)
                        if not np.isnan(autocorr):
                            autocorrs.append(autocorr)
                    except:
                        continue
            
            if not autocorrs:
                return 0.0
            
            # Average autocorrelation as clustering measure
            clustering_factor = np.mean(autocorrs)
            
            return max(0.0, min(1.0, float(clustering_factor)))
            
        except Exception as e:
            logger.error(f"❌ Error calculating clustering factor: {e}")
            return 0.0
    
    def _calculate_tail_risk_score(self, returns: pd.Series) -> float:
        """Calculate tail risk assessment score"""
        try:
            if len(returns) < 30:
                return 0.0
            
            # Calculate tail statistics
            left_tail = returns.quantile(0.05)  # 5th percentile
            right_tail = returns.quantile(0.95)  # 95th percentile
            
            # Tail asymmetry
            tail_asymmetry = abs(left_tail) / right_tail if right_tail > 0 else 1.0
            
            # Extreme value frequency
            extreme_threshold = 2.5 * returns.std()
            extreme_count = (np.abs(returns) > extreme_threshold).sum()
            extreme_frequency = extreme_count / len(returns)
            
            # Kurtosis contribution
            kurt = returns.kurtosis()
            excess_kurtosis = max(0, kurt - 3) / 10  # Normalize excess kurtosis
            
            # Combined tail risk score
            tail_risk_score = (
                0.4 * min(tail_asymmetry / 2.0, 1.0) +       # Asymmetry component
                0.4 * min(extreme_frequency * 20, 1.0) +      # Frequency component
                0.2 * min(excess_kurtosis, 1.0)              # Kurtosis component
            )
            
            return max(0.0, min(1.0, float(tail_risk_score)))
            
        except Exception as e:
            logger.error(f"❌ Error calculating tail risk score: {e}")
            return 0.0
    
    def _calculate_regime_stability(self, symbol: str) -> float:
        """Calculate regime persistence probability"""
        try:
            if not self.regime_history or len(self.regime_history) < 10:
                return 0.5  # Default medium stability
            
            # Get recent regime history for symbol
            recent_regimes = []
            for entry in self.regime_history[-20:]:  # Last 20 entries
                if symbol in entry.get('symbol_regimes', {}):
                    recent_regimes.append(entry['symbol_regimes'][symbol])
            
            if len(recent_regimes) < 5:
                return 0.5
            
            # Calculate regime persistence
            current_regime = recent_regimes[-1] if recent_regimes else 'normal'
            regime_changes = sum(1 for i in range(1, len(recent_regimes)) 
                               if recent_regimes[i] != recent_regimes[i-1])
            
            # Stability = 1 - (change_rate)
            change_rate = regime_changes / max(len(recent_regimes) - 1, 1)
            stability = 1.0 - change_rate
            
            return max(0.0, min(1.0, float(stability)))
            
        except Exception as e:
            logger.error(f"❌ Error calculating regime stability: {e}")
            return 0.5
    
    def _calculate_risk_metrics(self, symbol: str, data: pd.DataFrame) -> RiskMetrics:
        """Calculate comprehensive risk metrics"""
        try:
            metrics = RiskMetrics()
            
            if len(data) < 20:
                return metrics
            
            returns = data['close'].pct_change().dropna()
            if len(returns) < 10:
                return metrics
            
            # VaR calculations (95% and 99% confidence levels)
            if len(returns) >= 30:
                metrics.var_95_1d = float(np.abs(returns.quantile(0.05)))
                metrics.var_99_1d = float(np.abs(returns.quantile(0.01)))
                
                # 5-day VaR (scaling with sqrt(5))
                metrics.var_95_5d = metrics.var_95_1d * np.sqrt(5)
            
            # CVaR (Expected Shortfall) calculations
            if len(returns) >= 30:
                # 95% CVaR
                var_95_threshold = returns.quantile(0.05)
                tail_returns_95 = returns[returns <= var_95_threshold]
                if len(tail_returns_95) > 0:
                    metrics.cvar_95_1d = float(np.abs(tail_returns_95.mean()))
                
                # 99% CVaR
                var_99_threshold = returns.quantile(0.01)
                tail_returns_99 = returns[returns <= var_99_threshold]
                if len(tail_returns_99) > 0:
                    metrics.cvar_99_1d = float(np.abs(tail_returns_99.mean()))
            
            # Maximum daily loss estimate
            if len(returns) >= 50:
                metrics.max_daily_loss = float(np.abs(returns.min()))
            
            # Downside deviation
            negative_returns = returns[returns < 0]
            if len(negative_returns) > 0:
                metrics.downside_deviation = float(negative_returns.std() * np.sqrt(252))
            
            # Upside capture (ratio of upside to downside volatility)
            positive_returns = returns[returns > 0]
            if len(positive_returns) > 0 and len(negative_returns) > 0:
                upside_vol = positive_returns.std()
                downside_vol = negative_returns.std()
                if downside_vol > 0:
                    metrics.upside_capture = float(upside_vol / downside_vol)
            
            # Stress test scenario (3-sigma event)
            if len(returns) >= 30:
                stress_loss = returns.mean() - 3 * returns.std()
                metrics.stress_test_loss = float(np.abs(stress_loss))
            
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Error calculating risk metrics for {symbol}: {e}")
            return RiskMetrics()
    
    def _calculate_correlation_metrics(self, market_data: Dict[str, pd.DataFrame]) -> CorrelationMetrics:
        """Calculate correlation and diversification metrics"""
        try:
            metrics = CorrelationMetrics()
            
            if len(market_data) < 2:
                return metrics
            
            # Build returns matrix
            returns_data = {}
            min_length = float('inf')
            
            for symbol, data in market_data.items():
                if len(data) >= 30:
                    returns = data['close'].pct_change().dropna()
                    if len(returns) >= 20:
                        returns_data[symbol] = returns
                        min_length = min(min_length, len(returns))
            
            if len(returns_data) < 2 or min_length < 20:
                return metrics
            
            # Align returns data
            aligned_returns = {}
            for symbol, returns in returns_data.items():
                aligned_returns[symbol] = returns.tail(min_length)
            
            # Create correlation matrix
            returns_df = pd.DataFrame(aligned_returns)
            correlation_matrix = returns_df.corr()
            self.correlation_matrix = correlation_matrix
            
            # Market correlation (with SPY if available)
            if 'SPY' in correlation_matrix.columns:
                spy_correlations = correlation_matrix['SPY'].drop('SPY')
                if len(spy_correlations) > 0:
                    metrics.market_correlation = float(spy_correlations.mean())
            
            # Crypto correlation (average of crypto assets)
            crypto_symbols = [s for s in correlation_matrix.columns if '/' in s or 'BTC' in s or 'ETH' in s]
            if len(crypto_symbols) >= 2:
                crypto_corr_matrix = correlation_matrix.loc[crypto_symbols, crypto_symbols]
                # Upper triangular correlations (exclude diagonal)
                upper_triangle = np.triu(crypto_corr_matrix.values, k=1)
                crypto_correlations = upper_triangle[upper_triangle != 0]
                if len(crypto_correlations) > 0:
                    metrics.crypto_correlation = float(np.mean(crypto_correlations))
            
            # Portfolio diversification score
            # Based on average pairwise correlation (lower = more diversified)
            all_correlations = []
            for i in range(len(correlation_matrix.columns)):
                for j in range(i+1, len(correlation_matrix.columns)):
                    corr_val = correlation_matrix.iloc[i, j]
                    if not np.isnan(corr_val):
                        all_correlations.append(abs(corr_val))
            
            if all_correlations:
                avg_correlation = np.mean(all_correlations)
                metrics.portfolio_diversification = max(0.0, 1.0 - avg_correlation)
                
                # Concentration risk (high correlation = high concentration)
                metrics.concentration_risk = min(1.0, avg_correlation * 1.5)
            
            # Correlation regime
            if all_correlations:
                avg_abs_corr = np.mean(all_correlations)
                if avg_abs_corr > 0.7:
                    metrics.correlation_regime = "high"
                elif avg_abs_corr < 0.3:
                    metrics.correlation_regime = "low"
                else:
                    metrics.correlation_regime = "normal"
            
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Error calculating correlation metrics: {e}")
            return CorrelationMetrics()
    
    def _determine_market_regime(self) -> VolatilityRegime:
        """Determine overall market volatility regime"""
        try:
            if not self.current_metrics:
                return VolatilityRegime.NORMAL
            
            # Weight by market importance
            regime_votes = {}
            total_weight = 0
            
            for symbol, metrics in self.current_metrics.items():
                # Higher weight for market indices
                if symbol in ['SPY', 'QQQ', 'VIX']:
                    weight = 3.0
                elif symbol in ['TLT', 'GLD']:
                    weight = 1.5
                else:
                    weight = 1.0
                
                regime = metrics.vol_regime
                if regime not in regime_votes:
                    regime_votes[regime] = 0
                regime_votes[regime] += weight
                total_weight += weight
            
            if not regime_votes:
                return VolatilityRegime.NORMAL
            
            # Find regime with highest weighted vote
            weighted_regimes = {regime: votes/total_weight for regime, votes in regime_votes.items()}
            market_regime = max(weighted_regimes, key=weighted_regimes.get)
            
            return market_regime
            
        except Exception as e:
            logger.error(f"❌ Error determining market regime: {e}")
            return VolatilityRegime.NORMAL
    
    def _save_regime_to_history(self):
        """Save current regime assessment to history"""
        try:
            regime_record = {
                'timestamp': datetime.now().isoformat(),
                'market_regime': self.market_regime.value,
                'symbol_regimes': {
                    symbol: metrics.vol_regime.value 
                    for symbol, metrics in self.current_metrics.items()
                },
                'correlation_regime': self.current_correlations.correlation_regime,
                'market_correlation': self.current_correlations.market_correlation,
                'portfolio_diversification': self.current_correlations.portfolio_diversification
            }
            
            self.regime_history.append(regime_record)
            
            # Keep only last 1000 records
            if len(self.regime_history) > 1000:
                self.regime_history = self.regime_history[-1000:]
                
        except Exception as e:
            logger.error(f"❌ Error saving regime to history: {e}")
    
    def _log_volatility_status(self):
        """Log current volatility assessment status"""
        try:
            regime_color = {
                VolatilityRegime.ULTRA_LOW: "🟢",
                VolatilityRegime.LOW: "🟢", 
                VolatilityRegime.NORMAL_LOW: "🟡",
                VolatilityRegime.NORMAL: "🟡",
                VolatilityRegime.NORMAL_HIGH: "🟡",
                VolatilityRegime.HIGH: "🔴",
                VolatilityRegime.EXTREME: "🚨"
            }.get(self.market_regime, "🟡")
            
            logger.info(f"🌪️ VOLATILITY STATUS: {regime_color} {self.market_regime.value.upper()} | "
                       f"Market Corr: {self.current_correlations.market_correlation:.2f} | "
                       f"Diversification: {self.current_correlations.portfolio_diversification:.2f}")
            
            # Log high-risk symbols
            high_risk_symbols = []
            for symbol, metrics in self.current_metrics.items():
                if metrics.vol_regime in [VolatilityRegime.HIGH, VolatilityRegime.EXTREME]:
                    high_risk_symbols.append(f"{symbol}({metrics.vol_regime.value})")
            
            if high_risk_symbols:
                logger.warning(f"⚠️ HIGH VOLATILITY SYMBOLS: {', '.join(high_risk_symbols[:5])}")
                
        except Exception as e:
            logger.error(f"❌ Error logging volatility status: {e}")
    
    # Public API methods
    
    def get_volatility_regime(self, symbol: str = None) -> VolatilityRegime:
        """Get current volatility regime for symbol or market"""
        if symbol and symbol in self.current_metrics:
            return self.current_metrics[symbol].vol_regime
        return self.market_regime
    
    def get_volatility_multiplier(self, symbol: str) -> float:
        """Get volatility-based risk adjustment multiplier"""
        try:
            if symbol not in self.current_metrics:
                return 1.0
            
            regime = self.current_metrics[symbol].vol_regime
            
            # Risk multipliers by regime (inverse relationship with volatility)
            multipliers = {
                VolatilityRegime.ULTRA_LOW: 1.3,    # Increase risk in low vol
                VolatilityRegime.LOW: 1.15,
                VolatilityRegime.NORMAL_LOW: 1.05,
                VolatilityRegime.NORMAL: 1.0,       # Base risk
                VolatilityRegime.NORMAL_HIGH: 0.9,
                VolatilityRegime.HIGH: 0.7,         # Reduce risk in high vol
                VolatilityRegime.EXTREME: 0.4       # Drastically reduce in extreme vol
            }
            
            return multipliers.get(regime, 1.0)
            
        except Exception as e:
            logger.error(f"❌ Error getting volatility multiplier for {symbol}: {e}")
            return 1.0
    
    def get_var_estimate(self, symbol: str, confidence: float = 0.95, days: int = 1) -> float:
        """Get Value at Risk estimate for symbol"""
        try:
            if symbol not in self.current_risk_metrics:
                return 0.02  # Default 2% VaR
            
            risk_metrics = self.current_risk_metrics[symbol]
            
            if days == 1:
                if confidence >= 0.99:
                    return risk_metrics.var_99_1d
                else:
                    return risk_metrics.var_95_1d
            elif days == 5:
                return risk_metrics.var_95_5d
            else:
                # Scale VaR for other horizons
                base_var = risk_metrics.var_95_1d if confidence < 0.99 else risk_metrics.var_99_1d
                return base_var * np.sqrt(days)
                
        except Exception as e:
            logger.error(f"❌ Error getting VaR estimate for {symbol}: {e}")
            return 0.02
    
    def should_reduce_exposure(self, symbol: str = None) -> bool:
        """Determine if exposure should be reduced based on volatility conditions"""
        try:
            # Check market-wide conditions
            if self.market_regime in [VolatilityRegime.HIGH, VolatilityRegime.EXTREME]:
                return True
            
            # Check correlation conditions
            if (self.current_correlations.market_correlation > 0.8 and 
                self.current_correlations.correlation_regime == "high"):
                return True
            
            # Check symbol-specific conditions
            if symbol and symbol in self.current_metrics:
                metrics = self.current_metrics[symbol]
                if (metrics.vol_regime in [VolatilityRegime.HIGH, VolatilityRegime.EXTREME] or
                    metrics.vol_trend == VolatilityTrend.SPIKING or
                    metrics.tail_risk_score > 0.7):
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error determining exposure reduction: {e}")
            return False
    
    def get_volatility_assessment_summary(self) -> Dict[str, Any]:
        """Get comprehensive volatility assessment summary"""
        try:
            summary = {
                'market_regime': self.market_regime.value,
                'last_update': self.last_update.isoformat() if self.last_update else None,
                'correlation_metrics': {
                    'market_correlation': self.current_correlations.market_correlation,
                    'crypto_correlation': self.current_correlations.crypto_correlation,
                    'portfolio_diversification': self.current_correlations.portfolio_diversification,
                    'concentration_risk': self.current_correlations.concentration_risk,
                    'correlation_regime': self.current_correlations.correlation_regime
                },
                'symbol_metrics': {}
            }
            
            # Add key symbol metrics
            for symbol, metrics in self.current_metrics.items():
                if symbol in ['SPY', 'QQQ', 'BTC/USD', 'ETH/USD'] or len(summary['symbol_metrics']) < 10:
                    summary['symbol_metrics'][symbol] = {
                        'vol_regime': metrics.vol_regime.value,
                        'vol_trend': metrics.vol_trend.value,
                        'ewma_vol': metrics.ewma_vol,
                        'vol_percentile': metrics.vol_percentile,
                        'tail_risk_score': metrics.tail_risk_score,
                        'clustering_factor': metrics.clustering_factor
                    }
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Error getting volatility assessment summary: {e}")
            return {'error': str(e)}


# Global instance
volatility_assessor = VolatilityAssessor()


def get_volatility_adjustment(symbol: str) -> Dict[str, float]:
    """
    Get volatility-based risk adjustment for a specific symbol.
    Returns dictionary with volatility multiplier, VaR estimates, and regime info.
    """
    try:
        # Update assessment if stale
        if (not volatility_assessor.last_update or 
            datetime.now() - volatility_assessor.last_update > timedelta(minutes=10)):
            volatility_assessor.update_volatility_assessment()
        
        # Get volatility multiplier
        vol_multiplier = volatility_assessor.get_volatility_multiplier(symbol)
        
        # Get VaR estimates
        var_95 = volatility_assessor.get_var_estimate(symbol, confidence=0.95)
        var_99 = volatility_assessor.get_var_estimate(symbol, confidence=0.99)
        
        # Get regime info
        regime = volatility_assessor.get_volatility_regime(symbol)
        
        # Check if exposure should be reduced
        reduce_exposure = volatility_assessor.should_reduce_exposure(symbol)
        
        return {
            'volatility_multiplier': vol_multiplier,
            'var_95_1d': var_95,
            'var_99_1d': var_99,
            'vol_regime': regime.value,
            'reduce_exposure': reduce_exposure,
            'market_regime': volatility_assessor.market_regime.value,
            'correlation_regime': volatility_assessor.current_correlations.correlation_regime
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting volatility adjustment for {symbol}: {e}")
        return {
            'volatility_multiplier': 1.0,
            'var_95_1d': 0.02,
            'var_99_1d': 0.03,
            'vol_regime': 'normal',
            'reduce_exposure': False,
            'market_regime': 'normal',
            'correlation_regime': 'normal'
        }