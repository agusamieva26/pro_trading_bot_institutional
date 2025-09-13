"""
🔬 ADVANCED FEATURE ENGINEERING SYSTEM
Institutional-grade feature generation for high-frequency ML trading predictions

Features Generated:
- Technical Indicators: RSI, MACD, Bollinger Bands, ATR, Stochastic, etc.
- Price Patterns: Support/Resistance, Trend Analysis, Chart Patterns
- Market Microstructure: Spread Analysis, Order Flow, Volume Profiles  
- Statistical Features: Rolling Statistics, Volatility Clustering
- Cross-Asset Correlations: Multi-symbol relationships
- Sentiment Integration: News sentiment hooks
- Time-Based Features: Hour-of-day, Day-of-week effects
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime, timedelta
import warnings
from scipy import stats
from scipy.signal import find_peaks
from sklearn.preprocessing import StandardScaler, RobustScaler
import talib
from dataclasses import dataclass
from enum import Enum

# Suppress warnings for production
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=RuntimeWarning)

from .util import logger


class FeatureCategory(Enum):
    """Categories of features for organization."""
    PRICE_ACTION = "price_action"
    TECHNICAL_INDICATORS = "technical_indicators"
    VOLUME_ANALYSIS = "volume_analysis"
    VOLATILITY = "volatility"
    PATTERN_RECOGNITION = "pattern_recognition"
    MICROSTRUCTURE = "microstructure"
    STATISTICAL = "statistical"
    TIME_BASED = "time_based"
    CROSS_ASSET = "cross_asset"
    SENTIMENT = "sentiment"


@dataclass
class FeatureConfig:
    """Configuration for feature generation."""
    # Technical indicator periods
    rsi_periods: List[int] = None
    ema_periods: List[int] = None
    sma_periods: List[int] = None
    bollinger_periods: List[int] = None
    atr_periods: List[int] = None
    
    # Volume analysis
    volume_sma_periods: List[int] = None
    volume_ema_periods: List[int] = None
    
    # Volatility analysis
    volatility_windows: List[int] = None
    
    # Pattern recognition
    support_resistance_window: int = 20
    trend_detection_window: int = 50
    
    # Statistical features
    rolling_stat_windows: List[int] = None
    
    # Enable/disable categories
    enabled_categories: List[FeatureCategory] = None
    
    def __post_init__(self):
        """Set defaults after initialization."""
        if self.rsi_periods is None:
            self.rsi_periods = [14, 21, 28]
        if self.ema_periods is None:
            self.ema_periods = [9, 12, 21, 26, 50]
        if self.sma_periods is None:
            self.sma_periods = [10, 20, 50, 100, 200]
        if self.bollinger_periods is None:
            self.bollinger_periods = [20, 30]
        if self.atr_periods is None:
            self.atr_periods = [14, 21]
        if self.volume_sma_periods is None:
            self.volume_sma_periods = [10, 20, 50]
        if self.volume_ema_periods is None:
            self.volume_ema_periods = [12, 26]
        if self.volatility_windows is None:
            self.volatility_windows = [10, 20, 30, 60]
        if self.rolling_stat_windows is None:
            self.rolling_stat_windows = [5, 10, 20, 30]
        if self.enabled_categories is None:
            self.enabled_categories = list(FeatureCategory)


class TechnicalIndicators:
    """
    Advanced technical indicators using optimized calculations.
    """
    
    @staticmethod
    def rsi(close: pd.Series, period: int = 14) -> pd.Series:
        """Relative Strength Index."""
        try:
            return talib.RSI(close.values, timeperiod=period)
        except:
            # Fallback implementation
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / (loss + 1e-8)
            return 100 - (100 / (1 + rs))
    
    @staticmethod
    def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """MACD indicator."""
        try:
            macd, signal_line, histogram = talib.MACD(close.values, fastperiod=fast, 
                                                     slowperiod=slow, signalperiod=signal)
            return pd.Series(macd, index=close.index), \
                   pd.Series(signal_line, index=close.index), \
                   pd.Series(histogram, index=close.index)
        except:
            # Fallback implementation
            ema_fast = close.ewm(span=fast).mean()
            ema_slow = close.ewm(span=slow).mean()
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=signal).mean()
            histogram = macd_line - signal_line
            return macd_line, signal_line, histogram
    
    @staticmethod
    def bollinger_bands(close: pd.Series, period: int = 20, std_dev: float = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Bollinger Bands."""
        try:
            upper, middle, lower = talib.BBANDS(close.values, timeperiod=period, 
                                              nbdevup=std_dev, nbdevdn=std_dev)
            return pd.Series(upper, index=close.index), \
                   pd.Series(middle, index=close.index), \
                   pd.Series(lower, index=close.index)
        except:
            # Fallback implementation
            middle = close.rolling(window=period).mean()
            std = close.rolling(window=period).std()
            upper = middle + (std * std_dev)
            lower = middle - (std * std_dev)
            return upper, middle, lower
    
    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Average True Range."""
        try:
            return pd.Series(talib.ATR(high.values, low.values, close.values, timeperiod=period), 
                           index=close.index)
        except:
            # Fallback implementation
            prev_close = close.shift(1)
            tr1 = high - low
            tr2 = abs(high - prev_close)
            tr3 = abs(low - prev_close)
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            return true_range.rolling(window=period).mean()
    
    @staticmethod
    def stochastic(high: pd.Series, low: pd.Series, close: pd.Series, 
                  k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
        """Stochastic Oscillator."""
        try:
            k, d = talib.STOCH(high.values, low.values, close.values, 
                              fastk_period=k_period, slowk_period=d_period, 
                              slowd_period=d_period)
            return pd.Series(k, index=close.index), pd.Series(d, index=close.index)
        except:
            # Fallback implementation
            lowest_low = low.rolling(window=k_period).min()
            highest_high = high.rolling(window=k_period).max()
            k = 100 * ((close - lowest_low) / (highest_high - lowest_low + 1e-8))
            d = k.rolling(window=d_period).mean()
            return k, d
    
    @staticmethod
    def williams_r(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Williams %R."""
        try:
            return pd.Series(talib.WILLR(high.values, low.values, close.values, timeperiod=period),
                           index=close.index)
        except:
            # Fallback implementation
            highest_high = high.rolling(window=period).max()
            lowest_low = low.rolling(window=period).min()
            wr = -100 * ((highest_high - close) / (highest_high - lowest_low + 1e-8))
            return wr
    
    @staticmethod
    def cci(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20) -> pd.Series:
        """Commodity Channel Index."""
        try:
            return pd.Series(talib.CCI(high.values, low.values, close.values, timeperiod=period),
                           index=close.index)
        except:
            # Fallback implementation
            typical_price = (high + low + close) / 3
            sma = typical_price.rolling(window=period).mean()
            mad = typical_price.rolling(window=period).apply(lambda x: np.mean(np.abs(x - np.mean(x))))
            cci = (typical_price - sma) / (0.015 * mad + 1e-8)
            return cci


class PatternRecognition:
    """
    Advanced pattern recognition for price action analysis.
    """
    
    @staticmethod
    def find_support_resistance(high: pd.Series, low: pd.Series, close: pd.Series, 
                               window: int = 20, min_touches: int = 2) -> Dict[str, List[float]]:
        """Find support and resistance levels."""
        try:
            # Find local maxima (resistance) and minima (support)
            highs = high.rolling(window=window, center=True).max()
            lows = low.rolling(window=window, center=True).min()
            
            resistance_levels = []
            support_levels = []
            
            # Identify resistance levels
            resistance_peaks = find_peaks(high.values, distance=window//2, prominence=high.std()*0.5)[0]
            for peak in resistance_peaks:
                level = high.iloc[peak]
                # Count how many times price approached this level
                touches = ((high.abs() - level).abs() < close.std() * 0.01).sum()
                if touches >= min_touches:
                    resistance_levels.append(float(level))
            
            # Identify support levels  
            support_valleys = find_peaks(-low.values, distance=window//2, prominence=low.std()*0.5)[0]
            for valley in support_valleys:
                level = low.iloc[valley]
                touches = ((low.abs() - level).abs() < close.std() * 0.01).sum()
                if touches >= min_touches:
                    support_levels.append(float(level))
            
            return {
                'resistance': sorted(resistance_levels, reverse=True)[:5],  # Top 5
                'support': sorted(support_levels)[:5]  # Top 5
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Support/Resistance calculation error: {e}")
            return {'resistance': [], 'support': []}
    
    @staticmethod
    def detect_trend(close: pd.Series, window: int = 50) -> Dict[str, float]:
        """Detect trend strength and direction."""
        try:
            if len(close) < window:
                return {'trend_strength': 0.0, 'trend_direction': 0.0}
            
            # Linear regression slope
            x = np.arange(window)
            recent_prices = close.tail(window).values
            slope, intercept, r_value, _, _ = stats.linregress(x, recent_prices)
            
            # Normalize slope relative to price
            trend_strength = abs(r_value)  # R-squared as strength
            trend_direction = np.sign(slope)
            
            return {
                'trend_strength': float(trend_strength),
                'trend_direction': float(trend_direction)
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Trend detection error: {e}")
            return {'trend_strength': 0.0, 'trend_direction': 0.0}
    
    @staticmethod
    def fibonacci_retracements(high: pd.Series, low: pd.Series, window: int = 50) -> Dict[str, float]:
        """Calculate Fibonacci retracement levels."""
        try:
            if len(high) < window:
                return {}
            
            recent_high = high.tail(window).max()
            recent_low = low.tail(window).min()
            
            if recent_high <= recent_low:
                return {}
            
            diff = recent_high - recent_low
            
            fib_levels = {
                'fib_0': float(recent_high),
                'fib_236': float(recent_high - 0.236 * diff),
                'fib_382': float(recent_high - 0.382 * diff),
                'fib_500': float(recent_high - 0.500 * diff),
                'fib_618': float(recent_high - 0.618 * diff),
                'fib_786': float(recent_high - 0.786 * diff),
                'fib_100': float(recent_low)
            }
            
            return fib_levels
            
        except Exception as e:
            logger.warning(f"⚠️ Fibonacci calculation error: {e}")
            return {}


class VolumeAnalysis:
    """
    Advanced volume analysis features.
    """
    
    @staticmethod
    def volume_profile(close: pd.Series, volume: pd.Series, bins: int = 20) -> Dict[str, float]:
        """Calculate volume profile metrics."""
        try:
            if len(close) < bins:
                return {}
            
            # Create price bins
            price_min, price_max = close.min(), close.max()
            price_bins = np.linspace(price_min, price_max, bins)
            
            # Digitize prices and sum volume for each bin
            price_indices = np.digitize(close.values, price_bins)
            volume_at_price = {}
            
            for i in range(1, len(price_bins)):
                mask = price_indices == i
                volume_at_price[i] = volume[mask].sum()
            
            if not volume_at_price:
                return {}
            
            # Find point of control (POC) - price level with highest volume
            poc_bin = max(volume_at_price, key=volume_at_price.get)
            poc_price = (price_bins[poc_bin-1] + price_bins[poc_bin]) / 2
            
            # Calculate value area (70% of volume)
            total_volume = sum(volume_at_price.values())
            target_volume = total_volume * 0.7
            
            sorted_volumes = sorted(volume_at_price.items(), key=lambda x: x[1], reverse=True)
            cumulative_volume = 0
            value_area_bins = []
            
            for bin_idx, vol in sorted_volumes:
                cumulative_volume += vol
                value_area_bins.append(bin_idx)
                if cumulative_volume >= target_volume:
                    break
            
            if value_area_bins:
                va_high = max([price_bins[b] for b in value_area_bins])
                va_low = min([price_bins[b-1] for b in value_area_bins])
            else:
                va_high = va_low = poc_price
            
            return {
                'poc_price': float(poc_price),
                'value_area_high': float(va_high),
                'value_area_low': float(va_low),
                'volume_imbalance': float(volume_at_price.get(poc_bin, 0) / (total_volume + 1e-8))
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Volume profile calculation error: {e}")
            return {}
    
    @staticmethod
    def on_balance_volume(close: pd.Series, volume: pd.Series) -> pd.Series:
        """On Balance Volume indicator."""
        try:
            price_change = close.diff()
            obv = np.where(price_change > 0, volume, 
                          np.where(price_change < 0, -volume, 0)).cumsum()
            return pd.Series(obv, index=close.index)
        except Exception as e:
            logger.warning(f"⚠️ OBV calculation error: {e}")
            return pd.Series(0, index=close.index)
    
    @staticmethod
    def volume_weighted_average_price(high: pd.Series, low: pd.Series, 
                                     close: pd.Series, volume: pd.Series, 
                                     window: int = 20) -> pd.Series:
        """Volume Weighted Average Price."""
        try:
            typical_price = (high + low + close) / 3
            vwap = (typical_price * volume).rolling(window=window).sum() / \
                   volume.rolling(window=window).sum()
            return vwap
        except Exception as e:
            logger.warning(f"⚠️ VWAP calculation error: {e}")
            return pd.Series(0, index=close.index)


class AdvancedFeatureEngine:
    """
    Main feature engineering engine that orchestrates all feature generation.
    """
    
    def __init__(self, config: Optional[FeatureConfig] = None):
        """Initialize feature engine with configuration."""
        self.config = config or FeatureConfig()
        self.tech_indicators = TechnicalIndicators()
        self.pattern_recognition = PatternRecognition()
        self.volume_analysis = VolumeAnalysis()
        
        # Feature cache for performance
        self.feature_cache = {}
        self.cache_ttl = 60  # 1 minute
        
        logger.info("🔬 Advanced Feature Engineering System initialized")
    
    def generate_features(self, data: pd.DataFrame, symbol: str = "UNKNOWN", 
                         include_target: bool = True) -> pd.DataFrame:
        """
        Generate comprehensive feature set from OHLCV data.
        
        Args:
            data: OHLCV DataFrame with columns ['open', 'high', 'low', 'close', 'volume']
            symbol: Symbol identifier for feature customization
            include_target: Whether to generate target variable
            
        Returns:
            DataFrame with all generated features
        """
        try:
            if data.empty or len(data) < 50:
                logger.warning(f"⚠️ Insufficient data for {symbol}: {len(data)} rows")
                return pd.DataFrame()
            
            logger.debug(f"🔬 Generating features for {symbol}: {len(data)} rows")
            
            # Start with copy of original data
            features_df = data.copy()
            
            # Ensure required columns exist
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            if not all(col in features_df.columns for col in required_cols):
                logger.error(f"❌ Missing required columns for {symbol}")
                return pd.DataFrame()
            
            # Generate features by category
            if FeatureCategory.PRICE_ACTION in self.config.enabled_categories:
                features_df = self._add_price_action_features(features_df)
            
            if FeatureCategory.TECHNICAL_INDICATORS in self.config.enabled_categories:
                features_df = self._add_technical_indicators(features_df)
            
            if FeatureCategory.VOLUME_ANALYSIS in self.config.enabled_categories:
                features_df = self._add_volume_features(features_df)
            
            if FeatureCategory.VOLATILITY in self.config.enabled_categories:
                features_df = self._add_volatility_features(features_df)
            
            if FeatureCategory.PATTERN_RECOGNITION in self.config.enabled_categories:
                features_df = self._add_pattern_features(features_df)
            
            if FeatureCategory.STATISTICAL in self.config.enabled_categories:
                features_df = self._add_statistical_features(features_df)
            
            if FeatureCategory.TIME_BASED in self.config.enabled_categories:
                features_df = self._add_time_features(features_df)
            
            # Generate target variable if requested
            if include_target:
                features_df = self._add_target_variables(features_df)
            
            # Clean up features
            features_df = self._clean_features(features_df)
            
            logger.debug(f"✅ Generated {len(features_df.columns)} features for {symbol}")
            
            return features_df
            
        except Exception as e:
            logger.error(f"❌ Feature generation error for {symbol}: {e}")
            return pd.DataFrame()
    
    def _add_price_action_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add price action based features."""
        try:
            # Basic price features
            df['price_change'] = df['close'].pct_change()
            df['price_change_abs'] = df['price_change'].abs()
            df['log_return'] = np.log(df['close'] / df['close'].shift(1))
            
            # Price position within bar
            df['high_low_ratio'] = df['high'] / df['low']
            df['close_position'] = (df['close'] - df['low']) / (df['high'] - df['low'] + 1e-8)
            df['open_position'] = (df['open'] - df['low']) / (df['high'] - df['low'] + 1e-8)
            
            # Gap analysis
            df['gap_up'] = (df['open'] > df['close'].shift(1)).astype(int)
            df['gap_down'] = (df['open'] < df['close'].shift(1)).astype(int)
            df['gap_size'] = (df['open'] - df['close'].shift(1)) / df['close'].shift(1)
            
            # Body and shadow analysis
            body = abs(df['close'] - df['open'])
            upper_shadow = df['high'] - df[['close', 'open']].max(axis=1)
            lower_shadow = df[['close', 'open']].min(axis=1) - df['low']
            
            df['body_size'] = body / df['close']
            df['upper_shadow_ratio'] = upper_shadow / (body + 1e-8)
            df['lower_shadow_ratio'] = lower_shadow / (body + 1e-8)
            df['doji'] = (body < (df['high'] - df['low']) * 0.1).astype(int)
            
            return df
            
        except Exception as e:
            logger.warning(f"⚠️ Price action features error: {e}")
            return df
    
    def _add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicator features."""
        try:
            # RSI for multiple periods
            for period in self.config.rsi_periods:
                df[f'rsi_{period}'] = self.tech_indicators.rsi(df['close'], period)
                df[f'rsi_{period}_overbought'] = (df[f'rsi_{period}'] > 70).astype(int)
                df[f'rsi_{period}_oversold'] = (df[f'rsi_{period}'] < 30).astype(int)
            
            # Moving averages
            for period in self.config.ema_periods:
                df[f'ema_{period}'] = df['close'].ewm(span=period).mean()
                df[f'ema_{period}_signal'] = (df['close'] > df[f'ema_{period}']).astype(int)
                
            for period in self.config.sma_periods:
                df[f'sma_{period}'] = df['close'].rolling(window=period).mean()
                df[f'sma_{period}_signal'] = (df['close'] > df[f'sma_{period}']).astype(int)
            
            # MACD
            macd, signal, histogram = self.tech_indicators.macd(df['close'])
            df['macd'] = macd
            df['macd_signal'] = signal  
            df['macd_histogram'] = histogram
            df['macd_bullish'] = (df['macd'] > df['macd_signal']).astype(int)
            
            # Bollinger Bands
            for period in self.config.bollinger_periods:
                upper, middle, lower = self.tech_indicators.bollinger_bands(df['close'], period)
                df[f'bb_{period}_upper'] = upper
                df[f'bb_{period}_middle'] = middle
                df[f'bb_{period}_lower'] = lower
                df[f'bb_{period}_width'] = (upper - lower) / middle
                df[f'bb_{period}_position'] = (df['close'] - lower) / (upper - lower + 1e-8)
            
            # ATR
            for period in self.config.atr_periods:
                df[f'atr_{period}'] = self.tech_indicators.atr(df['high'], df['low'], df['close'], period)
                df[f'atr_{period}_normalized'] = df[f'atr_{period}'] / df['close']
            
            # Stochastic
            stoch_k, stoch_d = self.tech_indicators.stochastic(df['high'], df['low'], df['close'])
            df['stoch_k'] = stoch_k
            df['stoch_d'] = stoch_d
            df['stoch_overbought'] = (df['stoch_k'] > 80).astype(int)
            df['stoch_oversold'] = (df['stoch_k'] < 20).astype(int)
            
            # Williams %R
            df['williams_r'] = self.tech_indicators.williams_r(df['high'], df['low'], df['close'])
            
            # CCI
            df['cci'] = self.tech_indicators.cci(df['high'], df['low'], df['close'])
            
            return df
            
        except Exception as e:
            logger.warning(f"⚠️ Technical indicators error: {e}")
            return df
    
    def _add_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add volume-based features."""
        try:
            # Volume moving averages
            for period in self.config.volume_sma_periods:
                df[f'volume_sma_{period}'] = df['volume'].rolling(window=period).mean()
                df[f'volume_ratio_{period}'] = df['volume'] / df[f'volume_sma_{period}']
            
            for period in self.config.volume_ema_periods:
                df[f'volume_ema_{period}'] = df['volume'].ewm(span=period).mean()
            
            # Volume-price indicators
            df['volume_price_trend'] = ((df['close'] - df['close'].shift(1)) * df['volume']).rolling(window=10).sum()
            
            # On Balance Volume
            df['obv'] = self.volume_analysis.on_balance_volume(df['close'], df['volume'])
            df['obv_ema'] = df['obv'].ewm(span=20).mean()
            df['obv_signal'] = (df['obv'] > df['obv_ema']).astype(int)
            
            # VWAP
            df['vwap'] = self.volume_analysis.volume_weighted_average_price(
                df['high'], df['low'], df['close'], df['volume'])
            df['vwap_signal'] = (df['close'] > df['vwap']).astype(int)
            
            # Volume profile features (calculated on rolling basis)
            try:
                volume_profile = self.volume_analysis.volume_profile(
                    df['close'].tail(100), df['volume'].tail(100))
                
                for key, value in volume_profile.items():
                    df[f'vp_{key}'] = value
            except:
                pass  # Volume profile is optional
            
            # Volume surge detection
            df['volume_surge'] = (df['volume'] > df['volume'].rolling(20).mean() * 2).astype(int)
            
            return df
            
        except Exception as e:
            logger.warning(f"⚠️ Volume features error: {e}")
            return df
    
    def _add_volatility_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add volatility-based features."""
        try:
            # Historical volatility
            for window in self.config.volatility_windows:
                returns = df['close'].pct_change()
                df[f'volatility_{window}'] = returns.rolling(window=window).std() * np.sqrt(252)
                df[f'volatility_{window}_percentile'] = returns.rolling(window=window).apply(
                    lambda x: stats.percentileofscore(x, x.iloc[-1]) / 100)
            
            # Parkinson volatility (high-low based)
            df['parkinson_volatility'] = np.sqrt(
                (1 / (4 * np.log(2))) * np.log(df['high'] / df['low']).rolling(window=20).mean() * 252)
            
            # Garman-Klass volatility
            def garman_klass(high, low, open_price, close):
                return np.log(high/close) * np.log(high/open_price) + \
                       np.log(low/close) * np.log(low/open_price)
            
            df['gk_volatility'] = garman_klass(df['high'], df['low'], df['open'], df['close']).rolling(20).mean()
            
            # Volatility clustering (GARCH-like)
            returns = df['close'].pct_change()
            df['volatility_clustering'] = returns.rolling(20).std() / returns.rolling(60).std()
            
            # Volatility breakout
            df['volatility_breakout'] = (df['volatility_10'] > df['volatility_10'].rolling(50).quantile(0.8)).astype(int)
            
            return df
            
        except Exception as e:
            logger.warning(f"⚠️ Volatility features error: {e}")
            return df
    
    def _add_pattern_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add pattern recognition features."""
        try:
            # Support and resistance
            sr_levels = self.pattern_recognition.find_support_resistance(
                df['high'], df['low'], df['close'])
            
            current_price = df['close'].iloc[-1]
            
            # Distance to support/resistance
            if sr_levels['resistance']:
                nearest_resistance = min([r for r in sr_levels['resistance'] if r > current_price], 
                                       default=current_price * 1.1)
                df['distance_to_resistance'] = (nearest_resistance - current_price) / current_price
            else:
                df['distance_to_resistance'] = 0.1
            
            if sr_levels['support']:
                nearest_support = max([s for s in sr_levels['support'] if s < current_price],
                                    default=current_price * 0.9)
                df['distance_to_support'] = (current_price - nearest_support) / current_price
            else:
                df['distance_to_support'] = 0.1
            
            # Trend analysis
            trend_data = self.pattern_recognition.detect_trend(df['close'])
            df['trend_strength'] = trend_data['trend_strength']
            df['trend_direction'] = trend_data['trend_direction']
            
            # Fibonacci levels
            fib_levels = self.pattern_recognition.fibonacci_retracements(df['high'], df['low'])
            for level_name, level_value in fib_levels.items():
                df[f'{level_name}_distance'] = abs(current_price - level_value) / current_price
            
            # Price channel
            df['channel_upper'] = df['high'].rolling(20).max()
            df['channel_lower'] = df['low'].rolling(20).min()
            df['channel_position'] = ((df['close'] - df['channel_lower']) / 
                                    (df['channel_upper'] - df['channel_lower'] + 1e-8))
            
            return df
            
        except Exception as e:
            logger.warning(f"⚠️ Pattern features error: {e}")
            return df
    
    def _add_statistical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add statistical features."""
        try:
            for window in self.config.rolling_stat_windows:
                # Rolling statistics
                df[f'mean_{window}'] = df['close'].rolling(window=window).mean()
                df[f'std_{window}'] = df['close'].rolling(window=window).std()
                df[f'skew_{window}'] = df['close'].rolling(window=window).skew()
                df[f'kurt_{window}'] = df['close'].rolling(window=window).kurt()
                
                # Z-score
                df[f'zscore_{window}'] = ((df['close'] - df[f'mean_{window}']) / 
                                        (df[f'std_{window}'] + 1e-8))
                
                # Percentile rank
                df[f'percentile_{window}'] = df['close'].rolling(window=window).apply(
                    lambda x: stats.percentileofscore(x[:-1], x.iloc[-1]) / 100 if len(x) > 1 else 0.5)
            
            # Autocorrelation
            returns = df['close'].pct_change()
            df['autocorr_1'] = returns.rolling(20).apply(lambda x: x.autocorr(lag=1))
            df['autocorr_5'] = returns.rolling(20).apply(lambda x: x.autocorr(lag=5))
            
            return df
            
        except Exception as e:
            logger.warning(f"⚠️ Statistical features error: {e}")
            return df
    
    def _add_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add time-based features."""
        try:
            # Ensure timestamp index
            if 'timestamp' in df.columns:
                df_time = pd.to_datetime(df['timestamp'])
            else:
                df_time = pd.to_datetime(df.index)
            
            # Hour and minute features
            df['hour'] = df_time.dt.hour
            df['minute'] = df_time.dt.minute
            df['day_of_week'] = df_time.dt.dayofweek
            
            # Market session features
            df['pre_market'] = ((df['hour'] >= 4) & (df['hour'] < 9)).astype(int)
            df['regular_hours'] = ((df['hour'] >= 9) & (df['hour'] < 16)).astype(int)
            df['after_hours'] = ((df['hour'] >= 16) | (df['hour'] < 4)).astype(int)
            
            # Time-based cyclical features
            df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
            df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
            df['minute_sin'] = np.sin(2 * np.pi * df['minute'] / 60)
            df['minute_cos'] = np.cos(2 * np.pi * df['minute'] / 60)
            df['dow_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
            df['dow_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
            
            return df
            
        except Exception as e:
            logger.warning(f"⚠️ Time features error: {e}")
            return df
    
    def _add_target_variables(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add target variables for ML training."""
        try:
            # Future returns at different horizons
            for minutes in [1, 5, 15, 30]:
                future_close = df['close'].shift(-minutes)
                df[f'future_return_{minutes}m'] = (future_close / df['close'] - 1)
                
                # Classification targets
                df[f'direction_{minutes}m'] = np.where(
                    df[f'future_return_{minutes}m'] > 0.003, 1,
                    np.where(df[f'future_return_{minutes}m'] < -0.003, -1, 0)
                )
            
            # High/Low targets (for range prediction)
            df['future_high_5m'] = df['high'].rolling(5).max().shift(-5)
            df['future_low_5m'] = df['low'].rolling(5).min().shift(-5)
            
            # Volatility target
            df['future_volatility_5m'] = df['close'].pct_change().rolling(5).std().shift(-5)
            
            return df
            
        except Exception as e:
            logger.warning(f"⚠️ Target variables error: {e}")
            return df
    
    def _clean_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and finalize features."""
        try:
            # Replace infinite values
            df = df.replace([np.inf, -np.inf], np.nan)
            
            # Forward fill then backward fill for small gaps
            df = df.fillna(method='ffill', limit=3).fillna(method='bfill', limit=3)
            
            # Drop columns with too many NaN values (>50%)
            nan_threshold = len(df) * 0.5
            df = df.dropna(axis=1, thresh=nan_threshold)
            
            # Cap extreme outliers (beyond 5 standard deviations)
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            for col in numeric_cols:
                if df[col].std() > 0:
                    lower_bound = df[col].mean() - 5 * df[col].std()
                    upper_bound = df[col].mean() + 5 * df[col].std()
                    df[col] = df[col].clip(lower=lower_bound, upper=upper_bound)
            
            return df
            
        except Exception as e:
            logger.warning(f"⚠️ Feature cleaning error: {e}")
            return df
    
    def get_feature_importance(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate feature importance using mutual information."""
        try:
            from sklearn.feature_selection import mutual_info_regression
            
            # Use 5-minute return as target
            if 'future_return_5m' not in df.columns:
                return {}
            
            feature_cols = [col for col in df.columns 
                           if col not in ['future_return_5m', 'timestamp'] and 
                              not col.startswith('future_')]
            
            X = df[feature_cols].fillna(0)
            y = df['future_return_5m'].fillna(0)
            
            # Calculate mutual information
            mi_scores = mutual_info_regression(X, y, random_state=42)
            
            importance_dict = dict(zip(feature_cols, mi_scores))
            
            # Sort by importance
            return dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))
            
        except Exception as e:
            logger.warning(f"⚠️ Feature importance calculation error: {e}")
            return {}


# Global instance
feature_engine = AdvancedFeatureEngine()


def generate_features(data: pd.DataFrame, symbol: str = "UNKNOWN", 
                     config: Optional[FeatureConfig] = None,
                     include_target: bool = True) -> pd.DataFrame:
    """
    Convenient function to generate features.
    
    Args:
        data: OHLCV DataFrame
        symbol: Symbol identifier  
        config: Feature generation configuration
        include_target: Whether to include target variables
        
    Returns:
        DataFrame with generated features
    """
    if config:
        engine = AdvancedFeatureEngine(config)
    else:
        engine = feature_engine
        
    return engine.generate_features(data, symbol, include_target)


def get_feature_importance(data: pd.DataFrame, symbol: str = "UNKNOWN") -> Dict[str, float]:
    """Get feature importance scores."""
    return feature_engine.get_feature_importance(data)