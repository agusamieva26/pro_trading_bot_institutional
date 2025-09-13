#!/usr/bin/env python3
"""
📊 ADVANCED MARKET REGIME ANALYZER - INSTITUTIONAL GRADE
Enhanced market regime detection and adaptive strategy optimization system
- Multi-dimensional Regime Classification
- Real-time Regime Transition Detection
- Adaptive Strategy Parameter Optimization
- Risk-based Position Sizing Adjustment
- Volatility Regime Forecasting
"""
import os
import json
import asyncio
import time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from collections import defaultdict, deque
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier
import warnings
warnings.filterwarnings("ignore")

from .config import settings
from .data import fetch_bars, fetch_all_bars
from .util import logger

try:
    from .ai_strategy_generator import MarketRegime, StrategyDNA, StrategyType
except ImportError:
    logger.warning("AI Strategy Generator not available for regime analyzer")

class RegimeIndicator(Enum):
    """Advanced indicators for regime detection"""
    VIX_LEVEL = "vix_level"
    VIX_TERM_STRUCTURE = "vix_term_structure"
    YIELD_CURVE_SLOPE = "yield_curve_slope"
    CREDIT_SPREADS = "credit_spreads"
    DOLLAR_STRENGTH = "dollar_strength"
    COMMODITY_MOMENTUM = "commodity_momentum"
    EQUITY_MOMENTUM = "equity_momentum"
    SECTOR_ROTATION = "sector_rotation"
    MARKET_BREADTH = "market_breadth"
    RISK_PARITY = "risk_parity"

class RegimeTransition(Enum):
    """Types of regime transitions"""
    GRADUAL = "gradual"
    SUDDEN = "sudden"
    OSCILLATING = "oscillating"
    PERSISTENT = "persistent"

@dataclass
class RegimeSignal:
    """Individual regime detection signal"""
    indicator: RegimeIndicator
    value: float
    confidence: float
    regime_vote: MarketRegime
    timestamp: datetime = field(default_factory=datetime.now)
    
@dataclass
class RegimeAnalysis:
    """Comprehensive regime analysis results"""
    current_regime: MarketRegime
    regime_confidence: float
    regime_probability_distribution: Dict[MarketRegime, float]
    transition_type: RegimeTransition
    transition_probability: float
    key_drivers: List[RegimeIndicator]
    regime_persistence_forecast: Dict[str, float]  # 1d, 1w, 1m forecasts
    risk_adjustment_factor: float
    volatility_forecast: float
    correlation_forecast: float
    recommended_strategy_adjustments: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)

class AdvancedRegimeDetector:
    """
    🔍 Advanced Multi-Dimensional Market Regime Detection System
    """
    
    def __init__(self):
        self.regime_history = deque(maxlen=2000)
        self.indicator_cache = {}
        self.regime_model = None
        self.scaler = StandardScaler()
        self.pca = PCA(n_components=0.95)  # Retain 95% variance
        self.regime_persistence = defaultdict(lambda: deque(maxlen=100))
        
        # Regime transition matrix (learned from historical data)
        self.transition_matrix = self._initialize_transition_matrix()
        
        # Indicator weights (can be adjusted based on performance)
        self.indicator_weights = {
            RegimeIndicator.VIX_LEVEL: 0.20,
            RegimeIndicator.EQUITY_MOMENTUM: 0.18,
            RegimeIndicator.MARKET_BREADTH: 0.15,
            RegimeIndicator.YIELD_CURVE_SLOPE: 0.12,
            RegimeIndicator.SECTOR_ROTATION: 0.10,
            RegimeIndicator.CREDIT_SPREADS: 0.08,
            RegimeIndicator.DOLLAR_STRENGTH: 0.07,
            RegimeIndicator.COMMODITY_MOMENTUM: 0.06,
            RegimeIndicator.RISK_PARITY: 0.04
        }
        
        logger.info("🔍 Advanced Regime Detector initialized")
    
    def _initialize_transition_matrix(self) -> Dict[MarketRegime, Dict[MarketRegime, float]]:
        """Initialize regime transition probability matrix"""
        
        return {
            MarketRegime.BULL_TRENDING: {
                MarketRegime.BULL_TRENDING: 0.75,
                MarketRegime.SIDEWAYS: 0.12,
                MarketRegime.HIGH_VOLATILITY: 0.08,
                MarketRegime.BEAR_TRENDING: 0.03,
                MarketRegime.CRISIS: 0.02
            },
            MarketRegime.BEAR_TRENDING: {
                MarketRegime.BEAR_TRENDING: 0.65,
                MarketRegime.HIGH_VOLATILITY: 0.20,
                MarketRegime.CRISIS: 0.10,
                MarketRegime.RECOVERY: 0.04,
                MarketRegime.SIDEWAYS: 0.01
            },
            MarketRegime.SIDEWAYS: {
                MarketRegime.SIDEWAYS: 0.60,
                MarketRegime.BULL_TRENDING: 0.18,
                MarketRegime.BEAR_TRENDING: 0.12,
                MarketRegime.LOW_VOLATILITY: 0.08,
                MarketRegime.HIGH_VOLATILITY: 0.02
            },
            MarketRegime.HIGH_VOLATILITY: {
                MarketRegime.HIGH_VOLATILITY: 0.50,
                MarketRegime.CRISIS: 0.25,
                MarketRegime.RECOVERY: 0.15,
                MarketRegime.BEAR_TRENDING: 0.08,
                MarketRegime.SIDEWAYS: 0.02
            },
            MarketRegime.LOW_VOLATILITY: {
                MarketRegime.LOW_VOLATILITY: 0.70,
                MarketRegime.SIDEWAYS: 0.15,
                MarketRegime.BULL_TRENDING: 0.10,
                MarketRegime.EXPANSION: 0.04,
                MarketRegime.HIGH_VOLATILITY: 0.01
            },
            MarketRegime.CRISIS: {
                MarketRegime.CRISIS: 0.40,
                MarketRegime.RECOVERY: 0.30,
                MarketRegime.HIGH_VOLATILITY: 0.20,
                MarketRegime.BEAR_TRENDING: 0.09,
                MarketRegime.EXPANSION: 0.01
            },
            MarketRegime.RECOVERY: {
                MarketRegime.RECOVERY: 0.45,
                MarketRegime.EXPANSION: 0.25,
                MarketRegime.BULL_TRENDING: 0.20,
                MarketRegime.SIDEWAYS: 0.08,
                MarketRegime.HIGH_VOLATILITY: 0.02
            },
            MarketRegime.EXPANSION: {
                MarketRegime.EXPANSION: 0.60,
                MarketRegime.BULL_TRENDING: 0.25,
                MarketRegime.SIDEWAYS: 0.10,
                MarketRegime.LOW_VOLATILITY: 0.04,
                MarketRegime.HIGH_VOLATILITY: 0.01
            }
        }
    
    async def analyze_market_regime(self, market_data: Dict[str, pd.DataFrame]) -> RegimeAnalysis:
        """Comprehensive market regime analysis"""
        
        try:
            # Generate regime signals from multiple indicators
            regime_signals = await self._generate_regime_signals(market_data)
            
            # Ensemble regime classification
            current_regime, regime_confidence, probability_distribution = self._classify_regime(regime_signals)
            
            # Detect transition patterns
            transition_type, transition_probability = self._analyze_transitions(current_regime)
            
            # Forecast regime persistence
            persistence_forecast = self._forecast_regime_persistence(current_regime, regime_signals)
            
            # Calculate risk and strategy adjustments
            risk_factor, vol_forecast, corr_forecast = self._calculate_risk_adjustments(
                current_regime, regime_signals
            )
            
            # Generate strategy recommendations
            strategy_adjustments = self._generate_strategy_adjustments(current_regime, regime_signals)
            
            # Identify key regime drivers
            key_drivers = self._identify_key_drivers(regime_signals)
            
            analysis = RegimeAnalysis(
                current_regime=current_regime,
                regime_confidence=regime_confidence,
                regime_probability_distribution=probability_distribution,
                transition_type=transition_type,
                transition_probability=transition_probability,
                key_drivers=key_drivers,
                regime_persistence_forecast=persistence_forecast,
                risk_adjustment_factor=risk_factor,
                volatility_forecast=vol_forecast,
                correlation_forecast=corr_forecast,
                recommended_strategy_adjustments=strategy_adjustments
            )
            
            # Store in history
            self.regime_history.append(analysis)
            self.regime_persistence[current_regime].append(datetime.now())
            
            logger.info(f"📊 Regime Analysis: {current_regime.value} "
                       f"(confidence: {regime_confidence:.2f}, transition_prob: {transition_probability:.2f})")
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Market regime analysis failed: {e}")
            return self._create_default_analysis()
    
    async def _generate_regime_signals(self, market_data: Dict[str, pd.DataFrame]) -> List[RegimeSignal]:
        """Generate signals from multiple regime indicators"""
        
        signals = []
        
        try:
            # VIX Level Signal (if available)
            if any('VIX' in symbol for symbol in market_data.keys()):
                vix_signal = self._calculate_vix_signal(market_data)
                if vix_signal:
                    signals.append(vix_signal)
            
            # Equity Momentum Signal
            equity_signal = self._calculate_equity_momentum(market_data)
            if equity_signal:
                signals.append(equity_signal)
            
            # Market Breadth Signal
            breadth_signal = self._calculate_market_breadth(market_data)
            if breadth_signal:
                signals.append(breadth_signal)
            
            # Yield Curve Signal (using bond ETFs if available)
            yield_signal = self._calculate_yield_curve_signal(market_data)
            if yield_signal:
                signals.append(yield_signal)
            
            # Sector Rotation Signal
            sector_signal = self._calculate_sector_rotation(market_data)
            if sector_signal:
                signals.append(sector_signal)
            
            # Credit Spreads Signal (using credit ETFs if available)
            credit_signal = self._calculate_credit_spreads(market_data)
            if credit_signal:
                signals.append(credit_signal)
            
            # Dollar Strength Signal
            dollar_signal = self._calculate_dollar_strength(market_data)
            if dollar_signal:
                signals.append(dollar_signal)
            
            # Commodity Momentum Signal
            commodity_signal = self._calculate_commodity_momentum(market_data)
            if commodity_signal:
                signals.append(commodity_signal)
            
            # Risk Parity Signal
            risk_parity_signal = self._calculate_risk_parity(market_data)
            if risk_parity_signal:
                signals.append(risk_parity_signal)
            
        except Exception as e:
            logger.error(f"❌ Error generating regime signals: {e}")
        
        return signals
    
    def _calculate_vix_signal(self, market_data: Dict[str, pd.DataFrame]) -> Optional[RegimeSignal]:
        """Calculate VIX-based regime signal"""
        
        # Look for VIX data or use SPY volatility as proxy
        vix_data = None
        
        for symbol, df in market_data.items():
            if 'VIX' in symbol and not df.empty:
                vix_data = df
                break
        
        if vix_data is None and 'SPY' in market_data:
            # Calculate implied volatility from SPY
            spy_df = market_data['SPY']
            if not spy_df.empty and len(spy_df) > 20:
                returns = spy_df['close'].pct_change().dropna()
                realized_vol = returns.rolling(20).std() * np.sqrt(252)
                current_vol = realized_vol.iloc[-1] * 100  # Convert to VIX-like scale
                
                # Classify regime based on volatility level
                if current_vol < 12:
                    regime_vote = MarketRegime.LOW_VOLATILITY
                    confidence = min(0.9, (12 - current_vol) / 12)
                elif current_vol < 20:
                    regime_vote = MarketRegime.SIDEWAYS
                    confidence = min(0.8, abs(16 - current_vol) / 8)
                elif current_vol < 30:
                    regime_vote = MarketRegime.HIGH_VOLATILITY
                    confidence = min(0.9, (current_vol - 20) / 10)
                else:
                    regime_vote = MarketRegime.CRISIS
                    confidence = min(0.95, (current_vol - 30) / 20)
                
                return RegimeSignal(
                    indicator=RegimeIndicator.VIX_LEVEL,
                    value=current_vol,
                    confidence=confidence,
                    regime_vote=regime_vote
                )
        
        elif vix_data is not None and not vix_data.empty:
            current_vix = vix_data['close'].iloc[-1]
            
            # Standard VIX regime classification
            if current_vix < 15:
                regime_vote = MarketRegime.LOW_VOLATILITY
                confidence = min(0.9, (15 - current_vix) / 15)
            elif current_vix < 25:
                regime_vote = MarketRegime.SIDEWAYS
                confidence = min(0.8, abs(20 - current_vix) / 10)
            elif current_vix < 35:
                regime_vote = MarketRegime.HIGH_VOLATILITY
                confidence = min(0.9, (current_vix - 25) / 10)
            else:
                regime_vote = MarketRegime.CRISIS
                confidence = min(0.95, (current_vix - 35) / 15)
            
            return RegimeSignal(
                indicator=RegimeIndicator.VIX_LEVEL,
                value=current_vix,
                confidence=confidence,
                regime_vote=regime_vote
            )
        
        return None
    
    def _calculate_equity_momentum(self, market_data: Dict[str, pd.DataFrame]) -> Optional[RegimeSignal]:
        """Calculate equity momentum signal"""
        
        equity_symbols = ['SPY', 'QQQ', 'IWM', 'VTI']
        momentum_scores = []
        
        for symbol in equity_symbols:
            if symbol in market_data and not market_data[symbol].empty:
                df = market_data[symbol]
                if len(df) >= 60:
                    # Calculate multiple timeframe momentum
                    price = df['close']
                    
                    # 20-day momentum
                    mom_20 = (price.iloc[-1] - price.iloc[-20]) / price.iloc[-20]
                    
                    # 60-day momentum
                    mom_60 = (price.iloc[-1] - price.iloc[-60]) / price.iloc[-60]
                    
                    # Momentum score
                    momentum_score = (mom_20 * 0.6 + mom_60 * 0.4)
                    momentum_scores.append(momentum_score)
        
        if not momentum_scores:
            return None
        
        avg_momentum = np.mean(momentum_scores)
        
        # Classify regime based on momentum
        if avg_momentum > 0.15:
            regime_vote = MarketRegime.BULL_TRENDING
            confidence = min(0.9, avg_momentum / 0.3)
        elif avg_momentum > 0.05:
            regime_vote = MarketRegime.EXPANSION
            confidence = min(0.8, (avg_momentum - 0.05) / 0.1)
        elif avg_momentum > -0.05:
            regime_vote = MarketRegime.SIDEWAYS
            confidence = min(0.7, (0.05 - abs(avg_momentum)) / 0.05)
        elif avg_momentum > -0.15:
            regime_vote = MarketRegime.BEAR_TRENDING
            confidence = min(0.8, (abs(avg_momentum) - 0.05) / 0.1)
        else:
            regime_vote = MarketRegime.CRISIS
            confidence = min(0.9, (abs(avg_momentum) - 0.15) / 0.2)
        
        return RegimeSignal(
            indicator=RegimeIndicator.EQUITY_MOMENTUM,
            value=avg_momentum,
            confidence=confidence,
            regime_vote=regime_vote
        )
    
    def _calculate_market_breadth(self, market_data: Dict[str, pd.DataFrame]) -> Optional[RegimeSignal]:
        """Calculate market breadth signal"""
        
        # Use available equity ETFs to measure breadth
        breadth_symbols = ['SPY', 'QQQ', 'IWM', 'VTI', 'VEA', 'VWO']
        advancing_count = 0
        total_count = 0
        
        for symbol in breadth_symbols:
            if symbol in market_data and not market_data[symbol].empty:
                df = market_data[symbol]
                if len(df) >= 20:
                    # Check if advancing (20-day trend)
                    sma_20 = df['close'].rolling(20).mean()
                    if len(sma_20) >= 2:
                        current_price = df['close'].iloc[-1]
                        if current_price > sma_20.iloc[-1]:
                            advancing_count += 1
                        total_count += 1
        
        if total_count == 0:
            return None
        
        breadth_ratio = advancing_count / total_count
        
        # Classify regime based on breadth
        if breadth_ratio >= 0.8:
            regime_vote = MarketRegime.BULL_TRENDING
            confidence = min(0.9, breadth_ratio)
        elif breadth_ratio >= 0.6:
            regime_vote = MarketRegime.EXPANSION
            confidence = min(0.8, (breadth_ratio - 0.4) / 0.4)
        elif breadth_ratio >= 0.4:
            regime_vote = MarketRegime.SIDEWAYS
            confidence = min(0.7, 1 - abs(breadth_ratio - 0.5) / 0.5)
        elif breadth_ratio >= 0.2:
            regime_vote = MarketRegime.BEAR_TRENDING
            confidence = min(0.8, (0.4 - breadth_ratio) / 0.2)
        else:
            regime_vote = MarketRegime.CRISIS
            confidence = min(0.9, (0.2 - breadth_ratio) / 0.2)
        
        return RegimeSignal(
            indicator=RegimeIndicator.MARKET_BREADTH,
            value=breadth_ratio,
            confidence=confidence,
            regime_vote=regime_vote
        )
    
    def _calculate_yield_curve_signal(self, market_data: Dict[str, pd.DataFrame]) -> Optional[RegimeSignal]:
        """Calculate yield curve signal using bond ETFs"""
        
        # Use TLT (20+ year) and short-term bond proxies
        long_bond_data = market_data.get('TLT')
        
        if long_bond_data is None or long_bond_data.empty:
            return None
        
        if len(long_bond_data) < 60:
            return None
        
        # Calculate bond momentum as proxy for yield curve changes
        bond_price = long_bond_data['close']
        bond_momentum = (bond_price.iloc[-1] - bond_price.iloc[-60]) / bond_price.iloc[-60]
        
        # Bond prices up = yields down = potentially stimulative
        # Bond prices down = yields up = potentially restrictive
        
        if bond_momentum > 0.05:  # Bond rally (yields falling)
            regime_vote = MarketRegime.RECOVERY
            confidence = min(0.8, bond_momentum / 0.1)
        elif bond_momentum > -0.05:  # Stable bonds
            regime_vote = MarketRegime.SIDEWAYS
            confidence = min(0.7, (0.05 - abs(bond_momentum)) / 0.05)
        else:  # Bond selloff (yields rising)
            if bond_momentum < -0.15:
                regime_vote = MarketRegime.CRISIS
                confidence = min(0.9, abs(bond_momentum) / 0.2)
            else:
                regime_vote = MarketRegime.HIGH_VOLATILITY
                confidence = min(0.8, abs(bond_momentum) / 0.15)
        
        return RegimeSignal(
            indicator=RegimeIndicator.YIELD_CURVE_SLOPE,
            value=bond_momentum,
            confidence=confidence,
            regime_vote=regime_vote
        )
    
    def _calculate_sector_rotation(self, market_data: Dict[str, pd.DataFrame]) -> Optional[RegimeSignal]:
        """Calculate sector rotation signal"""
        
        # Use sector ETFs to measure rotation patterns
        sector_etfs = ['XLK', 'XLF', 'XLE', 'XLV']  # Tech, Financial, Energy, Healthcare
        sector_momentum = {}
        
        for sector in sector_etfs:
            if sector in market_data and not market_data[sector].empty:
                df = market_data[sector]
                if len(df) >= 30:
                    # Calculate 30-day momentum
                    price = df['close']
                    momentum = (price.iloc[-1] - price.iloc[-30]) / price.iloc[-30]
                    sector_momentum[sector] = momentum
        
        if len(sector_momentum) < 2:
            return None
        
        # Analyze rotation patterns
        momentum_values = list(sector_momentum.values())
        momentum_std = np.std(momentum_values)
        momentum_mean = np.mean(momentum_values)
        
        # High dispersion = active rotation
        # Low dispersion = broad movement or stagnation
        
        if momentum_std > 0.05:  # High rotation
            if momentum_mean > 0.05:
                regime_vote = MarketRegime.EXPANSION  # Positive rotation
                confidence = min(0.8, momentum_std / 0.1)
            elif momentum_mean < -0.05:
                regime_vote = MarketRegime.BEAR_TRENDING  # Negative rotation
                confidence = min(0.8, momentum_std / 0.1)
            else:
                regime_vote = MarketRegime.HIGH_VOLATILITY  # Volatile rotation
                confidence = min(0.7, momentum_std / 0.1)
        else:  # Low rotation
            if abs(momentum_mean) < 0.02:
                regime_vote = MarketRegime.SIDEWAYS
                confidence = min(0.8, (0.02 - abs(momentum_mean)) / 0.02)
            else:
                regime_vote = MarketRegime.LOW_VOLATILITY
                confidence = min(0.7, (0.05 - momentum_std) / 0.05)
        
        return RegimeSignal(
            indicator=RegimeIndicator.SECTOR_ROTATION,
            value=momentum_std,
            confidence=confidence,
            regime_vote=regime_vote
        )
    
    def _calculate_credit_spreads(self, market_data: Dict[str, pd.DataFrame]) -> Optional[RegimeSignal]:
        """Calculate credit spreads signal using corporate bond ETFs"""
        
        # This would ideally use HYG (high yield) vs TLT (treasury) spreads
        # For now, use available bond data as proxy
        
        return None  # Placeholder - would need specific credit data
    
    def _calculate_dollar_strength(self, market_data: Dict[str, pd.DataFrame]) -> Optional[RegimeSignal]:
        """Calculate dollar strength signal"""
        
        # Use inverse relationship with commodities and foreign markets
        dollar_proxy_symbols = ['GLD', 'VEA', 'VWO']  # Gold, Developed, Emerging
        dollar_signals = []
        
        for symbol in dollar_proxy_symbols:
            if symbol in market_data and not market_data[symbol].empty:
                df = market_data[symbol]
                if len(df) >= 30:
                    # Calculate momentum (inverse for dollar strength)
                    price = df['close']
                    momentum = (price.iloc[-1] - price.iloc[-30]) / price.iloc[-30]
                    
                    # Negative momentum in these assets suggests dollar strength
                    dollar_signal = -momentum
                    dollar_signals.append(dollar_signal)
        
        if not dollar_signals:
            return None
        
        dollar_strength = np.mean(dollar_signals)
        
        # Classify regime impact of dollar strength
        if dollar_strength > 0.1:
            regime_vote = MarketRegime.HIGH_VOLATILITY  # Strong dollar can stress markets
            confidence = min(0.7, dollar_strength / 0.2)
        elif dollar_strength > -0.1:
            regime_vote = MarketRegime.SIDEWAYS  # Neutral dollar
            confidence = min(0.6, (0.1 - abs(dollar_strength)) / 0.1)
        else:
            regime_vote = MarketRegime.EXPANSION  # Weak dollar can help risk assets
            confidence = min(0.7, abs(dollar_strength) / 0.2)
        
        return RegimeSignal(
            indicator=RegimeIndicator.DOLLAR_STRENGTH,
            value=dollar_strength,
            confidence=confidence,
            regime_vote=regime_vote
        )
    
    def _calculate_commodity_momentum(self, market_data: Dict[str, pd.DataFrame]) -> Optional[RegimeSignal]:
        """Calculate commodity momentum signal"""
        
        # Use GLD as commodity proxy
        if 'GLD' not in market_data or market_data['GLD'].empty:
            return None
        
        gld_df = market_data['GLD']
        if len(gld_df) < 60:
            return None
        
        # Calculate commodity momentum
        price = gld_df['close']
        short_momentum = (price.iloc[-1] - price.iloc[-20]) / price.iloc[-20]
        long_momentum = (price.iloc[-1] - price.iloc[-60]) / price.iloc[-60]
        
        commodity_momentum = (short_momentum * 0.6 + long_momentum * 0.4)
        
        # Classify regime based on commodity performance
        if commodity_momentum > 0.1:
            regime_vote = MarketRegime.HIGH_VOLATILITY  # Commodity boom often = inflation/volatility
            confidence = min(0.8, commodity_momentum / 0.2)
        elif commodity_momentum > -0.05:
            regime_vote = MarketRegime.SIDEWAYS
            confidence = min(0.7, (0.05 + commodity_momentum) / 0.15)
        else:
            regime_vote = MarketRegime.BEAR_TRENDING  # Commodity bust
            confidence = min(0.8, abs(commodity_momentum) / 0.15)
        
        return RegimeSignal(
            indicator=RegimeIndicator.COMMODITY_MOMENTUM,
            value=commodity_momentum,
            confidence=confidence,
            regime_vote=regime_vote
        )
    
    def _calculate_risk_parity(self, market_data: Dict[str, pd.DataFrame]) -> Optional[RegimeSignal]:
        """Calculate risk parity signal"""
        
        # Simple risk parity calculation using available assets
        asset_returns = {}
        asset_volatilities = {}
        
        key_assets = ['SPY', 'TLT', 'GLD', 'QQQ']
        
        for asset in key_assets:
            if asset in market_data and not market_data[asset].empty:
                df = market_data[asset]
                if len(df) >= 30:
                    returns = df['close'].pct_change().dropna()
                    if len(returns) >= 20:
                        asset_returns[asset] = returns.iloc[-20:].mean()
                        asset_volatilities[asset] = returns.iloc[-20:].std()
        
        if len(asset_returns) < 3:
            return None
        
        # Calculate risk-adjusted returns
        risk_adjusted_returns = {}
        for asset in asset_returns:
            if asset_volatilities[asset] > 0:
                risk_adjusted_returns[asset] = asset_returns[asset] / asset_volatilities[asset]
        
        if not risk_adjusted_returns:
            return None
        
        # Risk parity score based on dispersion of risk-adjusted returns
        ra_returns = list(risk_adjusted_returns.values())
        dispersion = np.std(ra_returns)
        mean_ra_return = np.mean(ra_returns)
        
        # Low dispersion = good risk parity environment
        # High dispersion = regime stress
        
        if dispersion < 0.1 and mean_ra_return > 0:
            regime_vote = MarketRegime.LOW_VOLATILITY
            confidence = min(0.8, (0.1 - dispersion) / 0.1)
        elif dispersion < 0.2:
            regime_vote = MarketRegime.SIDEWAYS
            confidence = min(0.7, (0.2 - dispersion) / 0.2)
        else:
            regime_vote = MarketRegime.HIGH_VOLATILITY
            confidence = min(0.8, dispersion / 0.3)
        
        return RegimeSignal(
            indicator=RegimeIndicator.RISK_PARITY,
            value=dispersion,
            confidence=confidence,
            regime_vote=regime_vote
        )
    
    def _classify_regime(self, signals: List[RegimeSignal]) -> Tuple[MarketRegime, float, Dict[MarketRegime, float]]:
        """Ensemble classification of market regime"""
        
        if not signals:
            return MarketRegime.SIDEWAYS, 0.5, {regime: 1.0/len(MarketRegime) for regime in MarketRegime}
        
        # Weighted voting system
        regime_votes = defaultdict(float)
        total_weight = 0.0
        
        for signal in signals:
            weight = self.indicator_weights.get(signal.indicator, 0.1) * signal.confidence
            regime_votes[signal.regime_vote] += weight
            total_weight += weight
        
        if total_weight == 0:
            return MarketRegime.SIDEWAYS, 0.5, {regime: 1.0/len(MarketRegime) for regime in MarketRegime}
        
        # Normalize votes to probabilities
        regime_probabilities = {}
        for regime in MarketRegime:
            regime_probabilities[regime] = regime_votes[regime] / total_weight
        
        # Get winning regime
        winner = max(regime_probabilities, key=regime_probabilities.get)
        confidence = regime_probabilities[winner]
        
        return winner, confidence, regime_probabilities
    
    def _analyze_transitions(self, current_regime: MarketRegime) -> Tuple[RegimeTransition, float]:
        """Analyze regime transition patterns"""
        
        if len(self.regime_history) < 10:
            return RegimeTransition.GRADUAL, 0.5
        
        # Look at recent regime history
        recent_regimes = [analysis.current_regime for analysis in list(self.regime_history)[-10:]]
        
        # Count regime changes
        regime_changes = 0
        for i in range(1, len(recent_regimes)):
            if recent_regimes[i] != recent_regimes[i-1]:
                regime_changes += 1
        
        # Classify transition type
        if regime_changes == 0:
            transition_type = RegimeTransition.PERSISTENT
            transition_prob = 0.1  # Low probability of change
        elif regime_changes <= 2:
            transition_type = RegimeTransition.GRADUAL
            transition_prob = 0.3
        elif regime_changes <= 4:
            transition_type = RegimeTransition.OSCILLATING
            transition_prob = 0.6
        else:
            transition_type = RegimeTransition.SUDDEN
            transition_prob = 0.8  # High probability of change
        
        # Adjust based on historical transition matrix
        if current_regime in self.transition_matrix:
            base_persistence = self.transition_matrix[current_regime][current_regime]
            adjusted_transition_prob = transition_prob * (1 - base_persistence)
        else:
            adjusted_transition_prob = transition_prob
        
        return transition_type, adjusted_transition_prob
    
    def _forecast_regime_persistence(self, current_regime: MarketRegime, 
                                   signals: List[RegimeSignal]) -> Dict[str, float]:
        """Forecast regime persistence over different timeframes"""
        
        # Base persistence from transition matrix
        base_persistence = self.transition_matrix.get(current_regime, {}).get(current_regime, 0.6)
        
        # Adjust based on signal strength
        signal_strength = np.mean([s.confidence for s in signals]) if signals else 0.5
        
        # Forecast persistence for different timeframes
        daily_persistence = base_persistence * signal_strength
        weekly_persistence = daily_persistence ** 5  # Compound over 5 days
        monthly_persistence = daily_persistence ** 20  # Compound over 20 days
        
        return {
            "1d": min(0.95, daily_persistence),
            "1w": min(0.9, weekly_persistence),
            "1m": min(0.8, monthly_persistence)
        }
    
    def _calculate_risk_adjustments(self, current_regime: MarketRegime, 
                                  signals: List[RegimeSignal]) -> Tuple[float, float, float]:
        """Calculate risk adjustment factors"""
        
        # Base risk adjustments by regime
        regime_risk_factors = {
            MarketRegime.LOW_VOLATILITY: 0.8,
            MarketRegime.SIDEWAYS: 1.0,
            MarketRegime.BULL_TRENDING: 1.1,
            MarketRegime.EXPANSION: 1.2,
            MarketRegime.BEAR_TRENDING: 1.4,
            MarketRegime.HIGH_VOLATILITY: 1.6,
            MarketRegime.RECOVERY: 1.3,
            MarketRegime.CRISIS: 2.0
        }
        
        base_risk_factor = regime_risk_factors.get(current_regime, 1.0)
        
        # Adjust based on signal confidence
        if signals:
            avg_confidence = np.mean([s.confidence for s in signals])
            confidence_adjustment = 1.0 + (1.0 - avg_confidence) * 0.3  # Up to 30% additional risk for low confidence
        else:
            confidence_adjustment = 1.3
        
        risk_adjustment_factor = base_risk_factor * confidence_adjustment
        
        # Volatility forecast
        regime_vol_forecast = {
            MarketRegime.LOW_VOLATILITY: 0.10,
            MarketRegime.SIDEWAYS: 0.15,
            MarketRegime.BULL_TRENDING: 0.18,
            MarketRegime.EXPANSION: 0.20,
            MarketRegime.BEAR_TRENDING: 0.25,
            MarketRegime.HIGH_VOLATILITY: 0.35,
            MarketRegime.RECOVERY: 0.30,
            MarketRegime.CRISIS: 0.50
        }
        
        vol_forecast = regime_vol_forecast.get(current_regime, 0.20)
        
        # Correlation forecast
        regime_corr_forecast = {
            MarketRegime.LOW_VOLATILITY: 0.30,
            MarketRegime.SIDEWAYS: 0.50,
            MarketRegime.BULL_TRENDING: 0.60,
            MarketRegime.EXPANSION: 0.65,
            MarketRegime.BEAR_TRENDING: 0.80,
            MarketRegime.HIGH_VOLATILITY: 0.85,
            MarketRegime.RECOVERY: 0.70,
            MarketRegime.CRISIS: 0.95
        }
        
        corr_forecast = regime_corr_forecast.get(current_regime, 0.60)
        
        return risk_adjustment_factor, vol_forecast, corr_forecast
    
    def _generate_strategy_adjustments(self, current_regime: MarketRegime, 
                                     signals: List[RegimeSignal]) -> Dict[str, Any]:
        """Generate strategy adjustment recommendations"""
        
        adjustments = {
            "position_sizing_multiplier": 1.0,
            "stop_loss_adjustment": 1.0,
            "take_profit_adjustment": 1.0,
            "holding_period_adjustment": 1.0,
            "diversification_requirement": 1.0,
            "strategy_types_preferred": [],
            "strategy_types_avoided": [],
            "special_considerations": []
        }
        
        # Regime-specific adjustments
        if current_regime == MarketRegime.BULL_TRENDING:
            adjustments.update({
                "position_sizing_multiplier": 1.2,
                "stop_loss_adjustment": 0.8,  # Wider stops in trending markets
                "take_profit_adjustment": 1.5,  # Higher profit targets
                "holding_period_adjustment": 1.3,  # Hold longer in trends
                "strategy_types_preferred": [StrategyType.MOMENTUM, StrategyType.TREND_FOLLOWING],
                "strategy_types_avoided": [StrategyType.MEAN_REVERSION],
                "special_considerations": ["trend_following_bias", "momentum_emphasis"]
            })
        
        elif current_regime == MarketRegime.BEAR_TRENDING:
            adjustments.update({
                "position_sizing_multiplier": 0.7,
                "stop_loss_adjustment": 0.8,
                "take_profit_adjustment": 0.8,  # Take profits quicker
                "holding_period_adjustment": 0.8,  # Shorter holds
                "diversification_requirement": 1.3,
                "strategy_types_preferred": [StrategyType.VOLATILITY_TRADING],
                "strategy_types_avoided": [StrategyType.MOMENTUM],
                "special_considerations": ["defensive_positioning", "quick_profit_taking"]
            })
        
        elif current_regime == MarketRegime.HIGH_VOLATILITY:
            adjustments.update({
                "position_sizing_multiplier": 0.6,
                "stop_loss_adjustment": 0.7,  # Tighter stops for volatility
                "take_profit_adjustment": 0.7,
                "holding_period_adjustment": 0.6,  # Very short holds
                "diversification_requirement": 1.5,
                "strategy_types_preferred": [StrategyType.VOLATILITY_TRADING, StrategyType.STATISTICAL_ARBITRAGE],
                "strategy_types_avoided": [StrategyType.TREND_FOLLOWING],
                "special_considerations": ["volatility_targeting", "rapid_exits", "reduced_correlation_exposure"]
            })
        
        elif current_regime == MarketRegime.SIDEWAYS:
            adjustments.update({
                "position_sizing_multiplier": 0.9,
                "stop_loss_adjustment": 1.1,  # Slightly wider stops
                "take_profit_adjustment": 0.9,  # Lower profit targets
                "holding_period_adjustment": 0.9,
                "strategy_types_preferred": [StrategyType.MEAN_REVERSION, StrategyType.STATISTICAL_ARBITRAGE],
                "strategy_types_avoided": [StrategyType.TREND_FOLLOWING],
                "special_considerations": ["range_trading", "mean_reversion_bias"]
            })
        
        elif current_regime == MarketRegime.CRISIS:
            adjustments.update({
                "position_sizing_multiplier": 0.4,
                "stop_loss_adjustment": 0.6,  # Very tight stops
                "take_profit_adjustment": 0.5,  # Quick profit taking
                "holding_period_adjustment": 0.4,  # Very short holds
                "diversification_requirement": 2.0,
                "strategy_types_preferred": [],  # Avoid most strategies
                "strategy_types_avoided": [StrategyType.MOMENTUM, StrategyType.TREND_FOLLOWING],
                "special_considerations": ["capital_preservation", "liquidity_focus", "defensive_only"]
            })
        
        # Adjust based on signal confidence
        if signals:
            avg_confidence = np.mean([s.confidence for s in signals])
            confidence_factor = 0.5 + (avg_confidence * 0.5)  # Scale between 0.5 and 1.0
            
            adjustments["position_sizing_multiplier"] *= confidence_factor
            adjustments["diversification_requirement"] /= confidence_factor
        
        return adjustments
    
    def _identify_key_drivers(self, signals: List[RegimeSignal]) -> List[RegimeIndicator]:
        """Identify the most important regime drivers"""
        
        if not signals:
            return []
        
        # Sort signals by weighted importance
        weighted_signals = []
        for signal in signals:
            weight = self.indicator_weights.get(signal.indicator, 0.1)
            importance = weight * signal.confidence
            weighted_signals.append((signal.indicator, importance))
        
        # Sort by importance and return top drivers
        weighted_signals.sort(key=lambda x: x[1], reverse=True)
        
        return [indicator for indicator, _ in weighted_signals[:3]]  # Top 3 drivers
    
    def _create_default_analysis(self) -> RegimeAnalysis:
        """Create default analysis for error cases"""
        
        return RegimeAnalysis(
            current_regime=MarketRegime.SIDEWAYS,
            regime_confidence=0.5,
            regime_probability_distribution={regime: 1.0/len(MarketRegime) for regime in MarketRegime},
            transition_type=RegimeTransition.GRADUAL,
            transition_probability=0.5,
            key_drivers=[],
            regime_persistence_forecast={"1d": 0.6, "1w": 0.4, "1m": 0.3},
            risk_adjustment_factor=1.0,
            volatility_forecast=0.20,
            correlation_forecast=0.60,
            recommended_strategy_adjustments={}
        )

class RegimeAdaptiveParameterOptimizer:
    """
    ⚙️ Regime-Adaptive Parameter Optimization System
    """
    
    def __init__(self):
        self.regime_parameter_cache = {}
        self.optimization_history = defaultdict(list)
        
    def optimize_strategy_parameters(self, strategy: 'StrategyDNA', 
                                   regime_analysis: RegimeAnalysis) -> 'StrategyDNA':
        """Optimize strategy parameters for current market regime"""
        
        try:
            # Create optimized copy
            optimized_strategy = strategy.__class__(**asdict(strategy))
            optimized_strategy.strategy_id = f"{strategy.strategy_id}_regime_optimized"
            
            # Get regime-specific adjustments
            adjustments = regime_analysis.recommended_strategy_adjustments
            
            # Apply position sizing adjustments
            if "position_sizing_multiplier" in adjustments:
                multiplier = adjustments["position_sizing_multiplier"]
                current_base_size = optimized_strategy.position_sizing.get("base_size", 0.02)
                optimized_strategy.position_sizing["base_size"] = current_base_size * multiplier
                
                # Ensure we don't exceed reasonable bounds
                optimized_strategy.position_sizing["base_size"] = np.clip(
                    optimized_strategy.position_sizing["base_size"], 0.005, 0.10
                )
            
            # Apply stop loss adjustments
            if "stop_loss_adjustment" in adjustments:
                adjustment = adjustments["stop_loss_adjustment"]
                current_stop = optimized_strategy.stop_loss_config.get("threshold", 0.02)
                optimized_strategy.stop_loss_config["threshold"] = current_stop * adjustment
                
                # Ensure reasonable bounds
                optimized_strategy.stop_loss_config["threshold"] = np.clip(
                    optimized_strategy.stop_loss_config["threshold"], 0.005, 0.05
                )
            
            # Apply take profit adjustments
            if "take_profit_adjustment" in adjustments:
                adjustment = adjustments["take_profit_adjustment"]
                current_tp = optimized_strategy.take_profit_config.get("threshold", 0.03)
                optimized_strategy.take_profit_config["threshold"] = current_tp * adjustment
                
                # Ensure reasonable bounds
                optimized_strategy.take_profit_config["threshold"] = np.clip(
                    optimized_strategy.take_profit_config["threshold"], 0.01, 0.08
                )
            
            # Adjust regime sensitivity to favor current regime
            current_regime = regime_analysis.current_regime
            if current_regime in optimized_strategy.regime_sensitivity:
                # Boost sensitivity to current regime
                optimized_strategy.regime_sensitivity[current_regime] *= 1.2
                optimized_strategy.regime_sensitivity[current_regime] = min(
                    1.0, optimized_strategy.regime_sensitivity[current_regime]
                )
            
            # Apply indicator-specific optimizations based on regime
            optimized_strategy = self._optimize_indicators_for_regime(
                optimized_strategy, regime_analysis
            )
            
            # Update metadata
            optimized_strategy.last_updated = datetime.now()
            optimized_strategy.validation_results["regime_optimization"] = {
                "source_strategy": strategy.strategy_id,
                "target_regime": current_regime.value,
                "optimization_timestamp": datetime.now().isoformat(),
                "adjustments_applied": adjustments
            }
            
            logger.info(f"🎯 Optimized strategy {strategy.name} for regime {current_regime.value}")
            
            return optimized_strategy
            
        except Exception as e:
            logger.error(f"❌ Strategy parameter optimization failed: {e}")
            return strategy  # Return original if optimization fails
    
    def _optimize_indicators_for_regime(self, strategy: 'StrategyDNA', 
                                       regime_analysis: RegimeAnalysis) -> 'StrategyDNA':
        """Optimize technical indicators for specific regime"""
        
        current_regime = regime_analysis.current_regime
        
        # Regime-specific indicator optimizations
        if current_regime in [MarketRegime.BULL_TRENDING, MarketRegime.BEAR_TRENDING]:
            # Trending markets: longer periods for trend indicators
            if "moving_averages" in strategy.indicators:
                strategy.indicators["moving_averages"]["fast_period"] = max(
                    strategy.indicators["moving_averages"].get("fast_period", 12), 12
                )
                strategy.indicators["moving_averages"]["slow_period"] = max(
                    strategy.indicators["moving_averages"].get("slow_period", 26), 26
                )
        
        elif current_regime == MarketRegime.HIGH_VOLATILITY:
            # High volatility: shorter periods, more responsive
            if "moving_averages" in strategy.indicators:
                strategy.indicators["moving_averages"]["fast_period"] = min(
                    strategy.indicators["moving_averages"].get("fast_period", 12), 8
                )
            
            if "oscillators" in strategy.indicators:
                strategy.indicators["oscillators"]["rsi_period"] = min(
                    strategy.indicators["oscillators"].get("rsi_period", 14), 10
                )
        
        elif current_regime == MarketRegime.SIDEWAYS:
            # Sideways markets: optimize for mean reversion
            if "oscillators" in strategy.indicators:
                strategy.indicators["oscillators"]["rsi_period"] = max(
                    strategy.indicators["oscillators"].get("rsi_period", 14), 18
                )
                strategy.indicators["oscillators"]["bb_std"] = max(
                    strategy.indicators["oscillators"].get("bb_std", 2.0), 2.2
                )
        
        return strategy

# Integration functions for main trading system

async def get_advanced_regime_analysis(symbols: List[str] = None) -> RegimeAnalysis:
    """Get comprehensive market regime analysis"""
    
    if symbols is None:
        symbols = settings.symbols[:10]  # Use top 10 symbols
    
    try:
        # Initialize detector if needed
        detector = AdvancedRegimeDetector()
        
        # Fetch market data
        market_data = {}
        for symbol in symbols:
            try:
                df = fetch_bars(symbol, start=None, end=None, min_bars=100)
                if not df.empty and len(df) > 50:
                    market_data[symbol] = df
            except Exception as e:
                logger.debug(f"Could not fetch data for {symbol}: {e}")
        
        if not market_data:
            logger.warning("⚠️ No market data available for regime analysis")
            return detector._create_default_analysis()
        
        # Perform comprehensive analysis
        analysis = await detector.analyze_market_regime(market_data)
        
        return analysis
        
    except Exception as e:
        logger.error(f"❌ Advanced regime analysis failed: {e}")
        return AdvancedRegimeDetector()._create_default_analysis()

def apply_regime_adjustments_to_config(regime_analysis: RegimeAnalysis) -> Dict[str, Any]:
    """Apply regime-based adjustments to trading configuration"""
    
    adjustments = regime_analysis.recommended_strategy_adjustments
    config_updates = {}
    
    try:
        # Apply position sizing adjustments
        if "position_sizing_multiplier" in adjustments:
            current_risk = getattr(settings, 'risk_per_trade', 0.02)
            adjusted_risk = current_risk * adjustments["position_sizing_multiplier"]
            config_updates["risk_per_trade"] = np.clip(adjusted_risk, 0.005, 0.08)
        
        # Apply stop loss adjustments
        if "stop_loss_adjustment" in adjustments:
            current_stop = getattr(settings, 'stop_loss_pct', 0.01)
            adjusted_stop = current_stop * adjustments["stop_loss_adjustment"]
            config_updates["stop_loss_pct"] = np.clip(adjusted_stop, 0.005, 0.05)
        
        # Apply take profit adjustments
        if "take_profit_adjustment" in adjustments:
            current_tp = getattr(settings, 'take_profit_pct', 0.02)
            adjusted_tp = current_tp * adjustments["take_profit_adjustment"]
            config_updates["take_profit_pct"] = np.clip(adjusted_tp, 0.01, 0.08)
        
        # Apply exposure adjustments
        if regime_analysis.risk_adjustment_factor > 0:
            current_exposure = getattr(settings, 'max_gross_exposure', 1.0)
            adjusted_exposure = current_exposure / regime_analysis.risk_adjustment_factor
            config_updates["max_gross_exposure"] = np.clip(adjusted_exposure, 0.3, 2.0)
        
        logger.info(f"🎯 Applied regime adjustments: {list(config_updates.keys())}")
        return config_updates
        
    except Exception as e:
        logger.error(f"❌ Error applying regime adjustments: {e}")
        return {}

# Global regime analyzer instance
_regime_detector: Optional[AdvancedRegimeDetector] = None

def get_regime_detector() -> AdvancedRegimeDetector:
    """Get global regime detector instance"""
    global _regime_detector
    
    if _regime_detector is None:
        _regime_detector = AdvancedRegimeDetector()
    
    return _regime_detector