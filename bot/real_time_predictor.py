"""
⚡ REAL-TIME PREDICTION SYSTEM
High-performance streaming prediction pipeline for live trading with ensemble voting,
confidence scoring, and risk-adjusted signal generation.

Features:
- Streaming prediction pipeline with sub-second latency
- Multi-model ensemble voting with confidence scoring
- Risk-adjusted position sizing integration
- Signal filtering and quality assessment
- Real-time performance monitoring
- Production-ready error handling and recovery
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from datetime import datetime, timedelta
import asyncio
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
import queue
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
import joblib
from pathlib import Path

# Suppress warnings for production
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)

from .util import logger
from .predictive_analytics import PredictiveAnalytics, PredictionResult, PredictionTimeframe, PredictionDirection
from .feature_engineering import AdvancedFeatureEngine, generate_features
from .config import settings


class SignalQuality(Enum):
    """Signal quality levels for filtering."""
    VERY_HIGH = "very_high"    # >90% confidence, high consensus
    HIGH = "high"              # >75% confidence, good consensus  
    MEDIUM = "medium"          # >60% confidence, moderate consensus
    LOW = "low"                # >50% confidence, low consensus
    VERY_LOW = "very_low"      # <50% confidence, poor consensus


@dataclass
class RealTimePrediction:
    """Enhanced prediction with real-time metadata."""
    symbol: str
    timestamp: datetime
    prediction_result: PredictionResult
    signal_quality: SignalQuality
    risk_score: float          # 0.0 to 1.0 (higher = riskier)
    position_size_pct: float   # Suggested position size as % of portfolio
    execution_urgency: int     # 1-5 scale (5 = execute immediately)
    market_regime: str         # trending, ranging, volatile, etc.
    correlation_filter: float  # Cross-asset correlation adjustment
    
    def to_trading_signal(self) -> Dict[str, Any]:
        """Convert to trading system compatible signal."""
        return {
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat(),
            'direction': self.prediction_result.prediction_class.name,
            'signal_strength': self.prediction_result.signal_strength,
            'confidence': self.prediction_result.confidence,
            'quality': self.signal_quality.value,
            'position_size_pct': self.position_size_pct,
            'risk_score': self.risk_score,
            'execution_urgency': self.execution_urgency,
            'timeframe': self.prediction_result.timeframe.value,
            'market_regime': self.market_regime,
            'model_votes': self.prediction_result.model_votes
        }


@dataclass
class StreamingConfig:
    """Configuration for real-time prediction stream."""
    # Processing parameters
    prediction_interval: float = 30.0  # seconds between predictions
    max_concurrent_predictions: int = 10
    feature_cache_size: int = 1000
    prediction_cache_ttl: int = 300  # 5 minutes
    
    # Quality filtering
    min_confidence: float = 0.55
    min_consensus: float = 0.6  # Agreement between models
    enable_signal_filtering: bool = True
    
    # Risk management
    max_position_size_pct: float = 0.20  # 20% max per position
    risk_adjustment_factor: float = 0.8
    enable_correlation_filtering: bool = True
    
    # Performance optimization
    async_processing: bool = True
    enable_prediction_caching: bool = True
    enable_parallel_processing: bool = True


class MarketRegimeDetector:
    """
    Real-time market regime detection for context-aware predictions.
    """
    
    def __init__(self):
        self.regime_cache = {}
        self.cache_ttl = 300  # 5 minutes
        
    def detect_regime(self, data: pd.DataFrame, symbol: str) -> str:
        """Detect current market regime."""
        try:
            cache_key = f"{symbol}_{int(time.time() / self.cache_ttl)}"
            
            if cache_key in self.regime_cache:
                return self.regime_cache[cache_key]
            
            if len(data) < 50:
                return "unknown"
            
            recent_data = data.tail(50)
            
            # Calculate regime indicators
            returns = recent_data['close'].pct_change()
            volatility = returns.rolling(20).std()
            
            # Moving average trend
            sma_20 = recent_data['close'].rolling(20).mean()
            sma_50 = recent_data['close'].rolling(50).mean() if len(recent_data) >= 50 else sma_20
            
            current_price = recent_data['close'].iloc[-1]
            current_vol = volatility.iloc[-1]
            avg_vol = volatility.mean()
            
            # Regime classification logic
            if current_vol > avg_vol * 1.5:
                regime = "volatile"
            elif current_price > sma_20.iloc[-1] > sma_50.iloc[-1]:
                regime = "trending_up"
            elif current_price < sma_20.iloc[-1] < sma_50.iloc[-1]:
                regime = "trending_down"
            else:
                # Check for ranging market
                price_range = recent_data['high'].max() - recent_data['low'].min()
                price_mean = recent_data['close'].mean()
                range_pct = price_range / price_mean
                
                if range_pct < 0.05:  # <5% range
                    regime = "ranging_tight"
                else:
                    regime = "ranging"
            
            # Cache result
            self.regime_cache[cache_key] = regime
            
            return regime
            
        except Exception as e:
            logger.warning(f"⚠️ Market regime detection error for {symbol}: {e}")
            return "unknown"


class CorrelationAnalyzer:
    """
    Real-time cross-asset correlation analysis for signal filtering.
    """
    
    def __init__(self):
        self.correlation_cache = {}
        self.cache_ttl = 600  # 10 minutes
        
    def calculate_cross_correlations(self, data_dict: Dict[str, pd.DataFrame], 
                                   target_symbol: str) -> Dict[str, float]:
        """Calculate correlations between target symbol and other assets."""
        try:
            cache_key = f"{target_symbol}_{int(time.time() / self.cache_ttl)}"
            
            if cache_key in self.correlation_cache:
                return self.correlation_cache[cache_key]
            
            if target_symbol not in data_dict or len(data_dict) < 2:
                return {}
            
            target_returns = data_dict[target_symbol]['close'].pct_change().dropna()
            if len(target_returns) < 20:
                return {}
            
            correlations = {}
            
            for symbol, data in data_dict.items():
                if symbol == target_symbol or data.empty:
                    continue
                
                try:
                    other_returns = data['close'].pct_change().dropna()
                    
                    # Align time series
                    common_index = target_returns.index.intersection(other_returns.index)
                    if len(common_index) < 10:
                        continue
                    
                    target_aligned = target_returns.loc[common_index]
                    other_aligned = other_returns.loc[common_index]
                    
                    # Calculate correlation
                    correlation = target_aligned.corr(other_aligned)
                    
                    if not pd.isna(correlation):
                        correlations[symbol] = float(correlation)
                        
                except Exception as e:
                    logger.debug(f"Correlation calculation error {symbol}: {e}")
                    continue
            
            # Cache result
            self.correlation_cache[cache_key] = correlations
            
            return correlations
            
        except Exception as e:
            logger.warning(f"⚠️ Cross-correlation error for {target_symbol}: {e}")
            return {}
    
    def get_correlation_adjustment(self, correlations: Dict[str, float],
                                 other_signals: Dict[str, float]) -> float:
        """Calculate correlation-based signal adjustment."""
        try:
            if not correlations or not other_signals:
                return 1.0
            
            adjustments = []
            
            for symbol, correlation in correlations.items():
                if symbol in other_signals:
                    other_signal = other_signals[symbol]
                    
                    # If highly correlated assets are giving conflicting signals, reduce confidence
                    if abs(correlation) > 0.7:
                        if np.sign(correlation) != np.sign(other_signal):
                            adjustments.append(0.7)  # Reduce confidence
                        else:
                            adjustments.append(1.1)  # Increase confidence
                    else:
                        adjustments.append(1.0)  # No adjustment
            
            if adjustments:
                return float(np.mean(adjustments))
            
            return 1.0
            
        except Exception as e:
            logger.warning(f"⚠️ Correlation adjustment error: {e}")
            return 1.0


class RiskAdjustedSizer:
    """
    Dynamic position sizing based on prediction confidence and risk metrics.
    """
    
    def __init__(self, config: StreamingConfig):
        self.config = config
        
    def calculate_position_size(self, prediction: PredictionResult, 
                               market_regime: str, 
                               current_portfolio_exposure: float = 0.0) -> float:
        """Calculate optimal position size based on prediction and risk factors."""
        try:
            base_size = self.config.max_position_size_pct
            
            # Confidence adjustment
            confidence_adj = prediction.confidence ** 2  # Quadratic scaling for confidence
            
            # Signal strength adjustment
            signal_strength_adj = min(abs(prediction.signal_strength) / 2.0, 1.0)
            
            # Market regime adjustment
            regime_adj = self._get_regime_adjustment(market_regime)
            
            # Risk score adjustment (lower risk score = larger position)
            risk_adj = 1.0 - (prediction.risk_score * 0.5)
            
            # Portfolio exposure adjustment (reduce size if already heavily exposed)
            exposure_adj = max(0.1, 1.0 - current_portfolio_exposure)
            
            # Model consensus adjustment
            consensus_adj = self._calculate_model_consensus(prediction.model_votes)
            
            # Calculate final position size
            position_size = (base_size * 
                           confidence_adj * 
                           signal_strength_adj * 
                           regime_adj * 
                           risk_adj * 
                           exposure_adj * 
                           consensus_adj *
                           self.config.risk_adjustment_factor)
            
            # Apply bounds
            position_size = max(0.01, min(position_size, self.config.max_position_size_pct))
            
            logger.debug(f"Position sizing: base={base_size:.3f}, confidence={confidence_adj:.3f}, "
                        f"signal={signal_strength_adj:.3f}, regime={regime_adj:.3f}, "
                        f"risk={risk_adj:.3f}, final={position_size:.3f}")
            
            return position_size
            
        except Exception as e:
            logger.error(f"❌ Position sizing error: {e}")
            return 0.01  # Minimum size
    
    def _get_regime_adjustment(self, regime: str) -> float:
        """Get position size adjustment based on market regime."""
        regime_adjustments = {
            'trending_up': 1.2,
            'trending_down': 1.2,
            'ranging': 0.8,
            'ranging_tight': 0.6,
            'volatile': 0.5,
            'unknown': 0.7
        }
        
        return regime_adjustments.get(regime, 0.7)
    
    def _calculate_model_consensus(self, model_votes: Dict[str, PredictionDirection]) -> float:
        """Calculate consensus level among models."""
        if not model_votes or len(model_votes) < 2:
            return 0.5
        
        votes = list(model_votes.values())
        vote_counts = {}
        
        for vote in votes:
            vote_counts[vote] = vote_counts.get(vote, 0) + 1
        
        max_votes = max(vote_counts.values())
        consensus = max_votes / len(votes)
        
        # Scale consensus to adjustment factor
        return 0.5 + (consensus * 0.5)  # Range: 0.5 to 1.0


class StreamingPredictor:
    """
    High-performance streaming prediction system with real-time processing.
    """
    
    def __init__(self, config: Optional[StreamingConfig] = None):
        """Initialize streaming predictor."""
        self.config = config or StreamingConfig()
        
        # Core components
        self.predictive_analytics = PredictiveAnalytics()
        self.feature_engine = AdvancedFeatureEngine()
        self.regime_detector = MarketRegimeDetector()
        self.correlation_analyzer = CorrelationAnalyzer()
        self.position_sizer = RiskAdjustedSizer(self.config)
        
        # Streaming infrastructure
        self.prediction_queue = queue.Queue(maxsize=1000)
        self.feature_cache = {}
        self.prediction_cache = {}
        self.is_streaming = False
        
        # Performance monitoring
        self.prediction_count = 0
        self.last_prediction_time = 0
        self.processing_times = []
        
        # Thread safety
        self._stream_lock = threading.Lock()
        self._cache_lock = threading.Lock()
        
        # Background tasks
        self.stream_thread = None
        self.cleanup_thread = None
        
        logger.info("⚡ Real-Time Prediction System initialized")
    
    def start_streaming(self, data_sources: Dict[str, Callable]) -> bool:
        """
        Start real-time prediction streaming.
        
        Args:
            data_sources: Dict mapping symbols to data source functions
            
        Returns:
            True if streaming started successfully
        """
        try:
            if self.is_streaming:
                logger.warning("⚠️ Streaming already active")
                return False
            
            self.data_sources = data_sources
            self.is_streaming = True
            
            # Start background threads
            self.stream_thread = threading.Thread(
                target=self._streaming_loop,
                daemon=True,
                name="PredictionStream"
            )
            
            self.cleanup_thread = threading.Thread(
                target=self._cleanup_loop,
                daemon=True,
                name="CacheCleanup"
            )
            
            self.stream_thread.start()
            self.cleanup_thread.start()
            
            logger.info(f"🚀 Streaming started for {len(data_sources)} symbols")
            return True
            
        except Exception as e:
            logger.error(f"❌ Streaming startup error: {e}")
            self.is_streaming = False
            return False
    
    def stop_streaming(self):
        """Stop real-time prediction streaming."""
        try:
            self.is_streaming = False
            
            # Wait for threads to finish
            if self.stream_thread and self.stream_thread.is_alive():
                self.stream_thread.join(timeout=10)
            
            if self.cleanup_thread and self.cleanup_thread.is_alive():
                self.cleanup_thread.join(timeout=5)
            
            logger.info("🛑 Streaming stopped")
            
        except Exception as e:
            logger.error(f"❌ Streaming shutdown error: {e}")
    
    def get_latest_prediction(self, symbol: str, timeout: float = 1.0) -> Optional[RealTimePrediction]:
        """Get the latest prediction for a symbol."""
        try:
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    prediction = self.prediction_queue.get_nowait()
                    if prediction.symbol == symbol:
                        return prediction
                    else:
                        # Put back if not for requested symbol
                        self.prediction_queue.put(prediction)
                except queue.Empty:
                    time.sleep(0.1)
                    continue
            
            # Check cache
            cache_key = f"{symbol}_{int(time.time() / 30)}"  # 30-second cache
            return self.prediction_cache.get(cache_key)
            
        except Exception as e:
            logger.error(f"❌ Get prediction error for {symbol}: {e}")
            return None
    
    def get_batch_predictions(self, symbols: List[str], 
                            timeout: float = 5.0) -> Dict[str, RealTimePrediction]:
        """Get latest predictions for multiple symbols."""
        try:
            predictions = {}
            remaining_symbols = set(symbols)
            start_time = time.time()
            
            while remaining_symbols and time.time() - start_time < timeout:
                try:
                    prediction = self.prediction_queue.get(timeout=0.1)
                    
                    if prediction.symbol in remaining_symbols:
                        predictions[prediction.symbol] = prediction
                        remaining_symbols.remove(prediction.symbol)
                    else:
                        # Put back if not requested
                        self.prediction_queue.put(prediction)
                        
                except queue.Empty:
                    continue
            
            # Fill in from cache for remaining symbols
            current_cache_bucket = int(time.time() / 30)
            
            for symbol in remaining_symbols:
                cache_key = f"{symbol}_{current_cache_bucket}"
                cached_pred = self.prediction_cache.get(cache_key)
                if cached_pred:
                    predictions[symbol] = cached_pred
            
            return predictions
            
        except Exception as e:
            logger.error(f"❌ Batch predictions error: {e}")
            return {}
    
    def _streaming_loop(self):
        """Main streaming loop running in background thread."""
        logger.info("🔄 Prediction streaming loop started")
        
        while self.is_streaming:
            try:
                cycle_start = time.time()
                
                # Process all symbols
                if self.config.enable_parallel_processing:
                    self._parallel_prediction_cycle()
                else:
                    self._sequential_prediction_cycle()
                
                # Calculate sleep time
                cycle_time = time.time() - cycle_start
                sleep_time = max(0, self.config.prediction_interval - cycle_time)
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                else:
                    logger.warning(f"⚠️ Prediction cycle overrun: {cycle_time:.2f}s")
                
            except Exception as e:
                logger.error(f"❌ Streaming loop error: {e}")
                time.sleep(5)  # Error recovery
    
    def _parallel_prediction_cycle(self):
        """Process predictions in parallel for better performance."""
        try:
            with ThreadPoolExecutor(max_workers=self.config.max_concurrent_predictions) as executor:
                futures = {}
                
                for symbol, data_source in self.data_sources.items():
                    future = executor.submit(self._process_symbol_prediction, symbol, data_source)
                    futures[future] = symbol
                
                # Collect results
                for future in as_completed(futures, timeout=self.config.prediction_interval):
                    symbol = futures[future]
                    try:
                        prediction = future.result()
                        if prediction:
                            self._publish_prediction(prediction)
                    except Exception as e:
                        logger.error(f"❌ Parallel prediction error for {symbol}: {e}")
                        
        except Exception as e:
            logger.error(f"❌ Parallel cycle error: {e}")
    
    def _sequential_prediction_cycle(self):
        """Process predictions sequentially."""
        for symbol, data_source in self.data_sources.items():
            try:
                prediction = self._process_symbol_prediction(symbol, data_source)
                if prediction:
                    self._publish_prediction(prediction)
            except Exception as e:
                logger.error(f"❌ Sequential prediction error for {symbol}: {e}")
    
    def _process_symbol_prediction(self, symbol: str, data_source: Callable) -> Optional[RealTimePrediction]:
        """Process prediction for a single symbol."""
        try:
            start_time = time.time()
            
            # Get fresh data
            data = data_source()
            
            if data is None or data.empty or len(data) < 50:
                logger.debug(f"Insufficient data for {symbol}")
                return None
            
            # Generate features
            features = self._get_or_generate_features(symbol, data)
            
            if features.empty:
                return None
            
            # Generate prediction
            prediction_result = self.predictive_analytics.predict(symbol, features)
            
            if not prediction_result:
                return None
            
            # Detect market regime
            market_regime = self.regime_detector.detect_regime(data, symbol)
            
            # Calculate cross-asset correlations if enabled
            correlation_adjustment = 1.0
            if self.config.enable_correlation_filtering:
                all_data = {s: ds() for s, ds in self.data_sources.items() if s != symbol}
                correlations = self.correlation_analyzer.calculate_cross_correlations(all_data, symbol)
                
                # Get other symbol signals (simplified)
                other_signals = {}  # Would get actual signals from other predictions
                correlation_adjustment = self.correlation_analyzer.get_correlation_adjustment(
                    correlations, other_signals)
            
            # Assess signal quality
            signal_quality = self._assess_signal_quality(prediction_result, correlation_adjustment)
            
            # Apply quality filtering
            if self.config.enable_signal_filtering and signal_quality == SignalQuality.VERY_LOW:
                logger.debug(f"Signal filtered for {symbol}: very low quality")
                return None
            
            # Calculate position size
            current_exposure = 0.0  # Would get from portfolio manager
            position_size = self.position_sizer.calculate_position_size(
                prediction_result, market_regime, current_exposure)
            
            # Calculate risk score
            risk_score = self._calculate_risk_score(prediction_result, market_regime, data)
            
            # Determine execution urgency
            execution_urgency = self._calculate_execution_urgency(
                prediction_result, signal_quality, market_regime)
            
            # Create real-time prediction
            rt_prediction = RealTimePrediction(
                symbol=symbol,
                timestamp=datetime.now(),
                prediction_result=prediction_result,
                signal_quality=signal_quality,
                risk_score=risk_score,
                position_size_pct=position_size,
                execution_urgency=execution_urgency,
                market_regime=market_regime,
                correlation_filter=correlation_adjustment
            )
            
            # Track performance
            processing_time = time.time() - start_time
            self.processing_times.append(processing_time)
            
            # Keep last 100 processing times
            if len(self.processing_times) > 100:
                self.processing_times = self.processing_times[-100:]
            
            logger.debug(f"Prediction generated for {symbol}: "
                        f"quality={signal_quality.value}, "
                        f"confidence={prediction_result.confidence:.3f}, "
                        f"processing_time={processing_time:.3f}s")
            
            return rt_prediction
            
        except Exception as e:
            logger.error(f"❌ Symbol prediction error for {symbol}: {e}")
            return None
    
    def _get_or_generate_features(self, symbol: str, data: pd.DataFrame) -> pd.DataFrame:
        """Get features from cache or generate new ones."""
        try:
            cache_key = f"{symbol}_{len(data)}_{data['close'].iloc[-1] if not data.empty else 0}"
            
            with self._cache_lock:
                if cache_key in self.feature_cache:
                    return self.feature_cache[cache_key]
            
            # Generate fresh features
            features = generate_features(data, symbol, include_target=False)
            
            if not features.empty:
                with self._cache_lock:
                    # Cache with size limit
                    if len(self.feature_cache) >= self.config.feature_cache_size:
                        # Remove oldest entry
                        oldest_key = next(iter(self.feature_cache))
                        del self.feature_cache[oldest_key]
                    
                    self.feature_cache[cache_key] = features
            
            return features
            
        except Exception as e:
            logger.error(f"❌ Feature generation error for {symbol}: {e}")
            return pd.DataFrame()
    
    def _assess_signal_quality(self, prediction: PredictionResult, 
                              correlation_adj: float) -> SignalQuality:
        """Assess the quality of a prediction signal."""
        try:
            # Base confidence
            confidence = prediction.confidence
            
            # Model consensus (how many models agree)
            model_votes = list(prediction.model_votes.values())
            if len(model_votes) > 1:
                consensus = max([model_votes.count(vote) for vote in set(model_votes)]) / len(model_votes)
            else:
                consensus = 1.0
            
            # Risk-adjusted confidence
            risk_adjusted_confidence = confidence * (1.0 - prediction.risk_score * 0.3)
            
            # Correlation adjustment
            final_confidence = risk_adjusted_confidence * correlation_adj
            
            # Quality thresholds
            if final_confidence >= 0.90 and consensus >= 0.8:
                return SignalQuality.VERY_HIGH
            elif final_confidence >= 0.75 and consensus >= 0.7:
                return SignalQuality.HIGH
            elif final_confidence >= 0.60 and consensus >= 0.6:
                return SignalQuality.MEDIUM
            elif final_confidence >= 0.50 and consensus >= 0.5:
                return SignalQuality.LOW
            else:
                return SignalQuality.VERY_LOW
                
        except Exception as e:
            logger.error(f"❌ Signal quality assessment error: {e}")
            return SignalQuality.LOW
    
    def _calculate_risk_score(self, prediction: PredictionResult, 
                             market_regime: str, data: pd.DataFrame) -> float:
        """Calculate comprehensive risk score for the prediction."""
        try:
            base_risk = prediction.risk_score
            
            # Market regime risk adjustment
            regime_risk = {
                'volatile': 0.3,
                'ranging_tight': 0.1,
                'ranging': 0.2,
                'trending_up': 0.15,
                'trending_down': 0.15,
                'unknown': 0.25
            }.get(market_regime, 0.2)
            
            # Volatility risk
            if not data.empty and len(data) >= 20:
                returns = data['close'].pct_change().dropna()
                current_vol = returns.tail(20).std()
                avg_vol = returns.std()
                vol_risk = min(current_vol / (avg_vol + 1e-8), 2.0) * 0.1
            else:
                vol_risk = 0.1
            
            # Signal strength risk (very strong signals can be riskier)
            strength_risk = min(abs(prediction.signal_strength) / 4.0, 1.0) * 0.05
            
            # Combine risk factors
            total_risk = min(base_risk + regime_risk + vol_risk + strength_risk, 1.0)
            
            return total_risk
            
        except Exception as e:
            logger.error(f"❌ Risk score calculation error: {e}")
            return 0.5
    
    def _calculate_execution_urgency(self, prediction: PredictionResult,
                                   quality: SignalQuality, regime: str) -> int:
        """Calculate execution urgency (1-5 scale)."""
        try:
            urgency = 1
            
            # Base urgency from confidence
            if prediction.confidence > 0.85:
                urgency += 2
            elif prediction.confidence > 0.70:
                urgency += 1
            
            # Quality adjustment
            quality_bonus = {
                SignalQuality.VERY_HIGH: 2,
                SignalQuality.HIGH: 1,
                SignalQuality.MEDIUM: 0,
                SignalQuality.LOW: -1,
                SignalQuality.VERY_LOW: -2
            }.get(quality, 0)
            
            urgency += quality_bonus
            
            # Signal strength adjustment
            if abs(prediction.signal_strength) > 1.5:
                urgency += 1
            
            # Market regime adjustment
            if regime in ['volatile', 'trending_up', 'trending_down']:
                urgency += 1
            
            return max(1, min(urgency, 5))
            
        except Exception as e:
            logger.error(f"❌ Execution urgency calculation error: {e}")
            return 3
    
    def _publish_prediction(self, prediction: RealTimePrediction):
        """Publish prediction to queue and cache."""
        try:
            # Add to queue (non-blocking)
            try:
                self.prediction_queue.put(prediction, block=False)
                self.prediction_count += 1
            except queue.Full:
                # Remove oldest item and add new one
                try:
                    self.prediction_queue.get_nowait()
                except queue.Empty:
                    pass
                self.prediction_queue.put(prediction, block=False)
            
            # Cache prediction
            cache_key = f"{prediction.symbol}_{int(time.time() / 30)}"
            self.prediction_cache[cache_key] = prediction
            
            # Update performance tracking
            self.last_prediction_time = time.time()
            
            logger.debug(f"Published prediction for {prediction.symbol}: "
                        f"{prediction.signal_quality.value} quality")
            
        except Exception as e:
            logger.error(f"❌ Prediction publishing error: {e}")
    
    def _cleanup_loop(self):
        """Background cleanup of caches and old data."""
        while self.is_streaming:
            try:
                current_time = time.time()
                
                # Clean prediction cache
                with self._cache_lock:
                    expired_keys = [
                        key for key in self.prediction_cache.keys()
                        if current_time - int(key.split('_')[-1]) * 30 > self.config.prediction_cache_ttl
                    ]
                    
                    for key in expired_keys:
                        del self.prediction_cache[key]
                
                # Clean feature cache if too large
                if len(self.feature_cache) > self.config.feature_cache_size * 1.2:
                    with self._cache_lock:
                        # Keep only most recent half
                        keep_count = self.config.feature_cache_size // 2
                        cache_items = list(self.feature_cache.items())
                        self.feature_cache = dict(cache_items[-keep_count:])
                
                # Clean regime and correlation caches
                self.regime_detector.regime_cache = {
                    k: v for k, v in self.regime_detector.regime_cache.items()
                    if current_time - int(k.split('_')[-1]) * 300 < 1800  # 30 minutes
                }
                
                self.correlation_analyzer.correlation_cache = {
                    k: v for k, v in self.correlation_analyzer.correlation_cache.items()
                    if current_time - int(k.split('_')[-1]) * 600 < 3600  # 1 hour
                }
                
                time.sleep(60)  # Run every minute
                
            except Exception as e:
                logger.error(f"❌ Cleanup error: {e}")
                time.sleep(60)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics of the streaming system."""
        try:
            current_time = time.time()
            
            stats = {
                'is_streaming': self.is_streaming,
                'total_predictions': self.prediction_count,
                'last_prediction_time': self.last_prediction_time,
                'time_since_last_prediction': current_time - self.last_prediction_time if self.last_prediction_time else 0,
                'queue_size': self.prediction_queue.qsize(),
                'feature_cache_size': len(self.feature_cache),
                'prediction_cache_size': len(self.prediction_cache),
                'data_sources_count': len(getattr(self, 'data_sources', {}))
            }
            
            if self.processing_times:
                stats['avg_processing_time'] = np.mean(self.processing_times)
                stats['max_processing_time'] = np.max(self.processing_times)
                stats['min_processing_time'] = np.min(self.processing_times)
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Performance stats error: {e}")
            return {'error': str(e)}


# Global instance
streaming_predictor = StreamingPredictor()


def start_real_time_predictions(data_sources: Dict[str, Callable], 
                               config: Optional[StreamingConfig] = None) -> bool:
    """Start real-time prediction streaming."""
    if config:
        predictor = StreamingPredictor(config)
        global streaming_predictor
        streaming_predictor = predictor
    
    return streaming_predictor.start_streaming(data_sources)


def stop_real_time_predictions():
    """Stop real-time prediction streaming."""
    streaming_predictor.stop_streaming()


def get_live_prediction(symbol: str, timeout: float = 1.0) -> Optional[RealTimePrediction]:
    """Get latest prediction for a symbol."""
    return streaming_predictor.get_latest_prediction(symbol, timeout)


def get_live_predictions(symbols: List[str], timeout: float = 5.0) -> Dict[str, RealTimePrediction]:
    """Get latest predictions for multiple symbols."""
    return streaming_predictor.get_batch_predictions(symbols, timeout)


def get_streaming_stats() -> Dict[str, Any]:
    """Get streaming system performance statistics."""
    return streaming_predictor.get_performance_stats()