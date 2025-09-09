"""
Advanced Feature Engineering para ML avanzado.
Genera indicadores técnicos complejos y features de última generación para modelos sofisticados.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

# TA libraries
try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False

from .util import logger


class AdvancedFeatureGenerator:
    """
    Generador de features avanzadas para machine learning en trading.
    """
    
    def __init__(self):
        self.feature_configs = {
            'price_features': True,
            'momentum_features': True,
            'volatility_features': True,
            'pattern_features': True,
            'volume_features': True,
            'cycle_features': False,  # Optimizado: deshabilitado temporalmente
            'statistical_features': True,
            'fractal_features': False  # Optimizado: muy costoso computacionalmente
        }
    
    def generate_advanced_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Genera conjunto completo de features avanzadas.
        """
        df = data.copy()
        
        # Validar datos mínimos
        if len(df) < 50:
            logger.warning("⚠️ Datos insuficientes para features avanzadas")
            return df
        
        # Asegurar columnas básicas
        required_cols = ['open', 'high', 'low', 'close']
        if not all(col in df.columns for col in required_cols):
            logger.error("❌ Columnas OHLC requeridas no encontradas")
            return df
        
        logger.info("🔧 Generando features avanzadas...")
        
        # 1. Price-based features
        if self.feature_configs['price_features']:
            df = self._add_price_features(df)
        
        # 2. Momentum features
        if self.feature_configs['momentum_features']:
            df = self._add_momentum_features(df)
        
        # 3. Volatility features
        if self.feature_configs['volatility_features']:
            df = self._add_volatility_features(df)
        
        # 4. Pattern recognition features
        if self.feature_configs['pattern_features']:
            df = self._add_pattern_features(df)
        
        # 5. Volume features
        if self.feature_configs['volume_features']:
            df = self._add_volume_features(df)
        
        # 6. Cycle features (optimizado)
        if self.feature_configs['cycle_features']:
            try:
                df = self._add_cycle_features(df)
            except Exception as e:
                logger.warning(f"⚠️ Saltando cycle features: {e}")
        
        # 7. Statistical features (optimizado)  
        if self.feature_configs['statistical_features']:
            try:
                df = self._add_statistical_features(df)
            except Exception as e:
                logger.warning(f"⚠️ Saltando statistical features: {e}")
        
        # 8. Fractal features (deshabilitado temporalmente)
        # if self.feature_configs['fractal_features']:
        #     df = self._add_fractal_features(df)
        
        # Limpiar features
        df = self._clean_features(df)
        
        feature_count = len([col for col in df.columns if col not in required_cols + ['volume', 'timestamp']])
        logger.info(f"✅ Features avanzadas generadas: {feature_count} nuevos indicadores")
        
        return df
    
    def _add_price_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Añade features basadas en precio."""
        
        # Price ratios
        df['hl_ratio'] = (df['high'] - df['low']) / df['close']
        df['oc_ratio'] = (df['open'] - df['close']) / df['close']
        df['hc_ratio'] = (df['high'] - df['close']) / df['close']
        df['lc_ratio'] = (df['low'] - df['close']) / df['close']
        
        # Price position in day range
        df['price_position'] = (df['close'] - df['low']) / (df['high'] - df['low'])
        df['price_position'] = df['price_position'].fillna(0.5)
        
        # Gap analysis
        df['gap_up'] = ((df['open'] - df['close'].shift(1)) / df['close'].shift(1)).fillna(0)
        df['gap_down'] = ((df['close'].shift(1) - df['open']) / df['close'].shift(1)).fillna(0)
        
        # Price acceleration
        df['price_accel'] = df['close'].pct_change(2) - df['close'].pct_change(1)
        
        return df
    
    def _add_momentum_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Añade features de momentum avanzados."""
        
        # Multiple timeframe RSI
        df['rsi_fast'] = self._calculate_rsi(df['close'], 7)
        df['rsi_medium'] = self._calculate_rsi(df['close'], 14)
        df['rsi_slow'] = self._calculate_rsi(df['close'], 21)
        
        # RSI divergence
        df['rsi_divergence'] = df['rsi_fast'] - df['rsi_slow']
        
        # Stochastic oscillator
        df['stoch_k'], df['stoch_d'] = self._calculate_stochastic(df, 14, 3)
        
        # Williams %R
        df['williams_r'] = self._calculate_williams_r(df, 14)
        
        # ROC (Rate of Change) multiple periods
        df['roc_5'] = df['close'].pct_change(5) * 100
        df['roc_10'] = df['close'].pct_change(10) * 100
        df['roc_20'] = df['close'].pct_change(20) * 100
        
        # Momentum oscillator
        df['momentum'] = df['close'] / df['close'].shift(10) - 1
        
        # Commodity Channel Index
        df['cci'] = self._calculate_cci(df, 20)
        
        return df
    
    def _add_volatility_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Añade features de volatilidad avanzados."""
        
        # True Range y ATR multiple periods
        df['atr_5'] = self._calculate_atr(df, 5)
        df['atr_14'] = self._calculate_atr(df, 14)
        df['atr_20'] = self._calculate_atr(df, 20)
        
        # ATR ratio
        df['atr_ratio'] = df['atr_5'] / df['atr_20']
        df['atr_ratio'] = df['atr_ratio'].fillna(1.0)
        
        # Volatility percentile
        df['vol_percentile'] = df['atr_14'].rolling(50).rank(pct=True)
        
        # Bollinger Bands multiple periods
        for period in [10, 20, 50]:
            bb_upper, bb_lower = self._calculate_bollinger_bands(df['close'], period)
            df[f'bb_upper_{period}'] = bb_upper
            df[f'bb_lower_{period}'] = bb_lower
            df[f'bb_width_{period}'] = (bb_upper - bb_lower) / df['close']
            df[f'bb_position_{period}'] = (df['close'] - bb_lower) / (bb_upper - bb_lower)
        
        # Keltner Channels
        df['kelt_upper'], df['kelt_lower'] = self._calculate_keltner_channels(df, 20)
        df['kelt_position'] = (df['close'] - df['kelt_lower']) / (df['kelt_upper'] - df['kelt_lower'])
        
        # Donchian Channels
        df['donch_upper'] = df['high'].rolling(20).max()
        df['donch_lower'] = df['low'].rolling(20).min()
        df['donch_position'] = (df['close'] - df['donch_lower']) / (df['donch_upper'] - df['donch_lower'])
        
        return df
    
    def _add_pattern_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Añade features de reconocimiento de patrones."""
        
        # Candlestick patterns (simplified versions)
        df['doji'] = self._is_doji(df)
        df['hammer'] = self._is_hammer(df)
        df['shooting_star'] = self._is_shooting_star(df)
        df['engulfing_bull'] = self._is_bullish_engulfing(df)
        df['engulfing_bear'] = self._is_bearish_engulfing(df)
        
        # Support/Resistance levels
        df['support_level'] = df['low'].rolling(20).min()
        df['resistance_level'] = df['high'].rolling(20).max()
        df['support_distance'] = (df['close'] - df['support_level']) / df['close']
        df['resistance_distance'] = (df['resistance_level'] - df['close']) / df['close']
        
        # Trend strength
        df['trend_strength'] = self._calculate_trend_strength(df, 20)
        
        # Price channels
        df['channel_position'] = self._calculate_channel_position(df, 20)
        
        return df
    
    def _add_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Añade features basados en volumen."""
        
        if 'volume' not in df.columns:
            return df
        
        # Volume moving averages
        df['volume_ma_5'] = df['volume'].rolling(5).mean()
        df['volume_ma_20'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma_20']
        
        # On-Balance Volume
        df['obv'] = self._calculate_obv(df)
        
        # Volume Price Trend
        df['vpt'] = self._calculate_vpt(df)
        
        # Accumulation/Distribution Line
        df['ad_line'] = self._calculate_ad_line(df)
        
        # Money Flow Index
        df['mfi'] = self._calculate_mfi(df, 14)
        
        # Volume oscillator
        df['volume_osc'] = ((df['volume_ma_5'] - df['volume_ma_20']) / df['volume_ma_20']) * 100
        
        return df
    
    def _add_cycle_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Añade features de análisis cíclico."""
        
        # Simple cycle indicators
        for period in [10, 20, 50]:
            df[f'cycle_{period}'] = np.sin(2 * np.pi * np.arange(len(df)) / period)
        
        # Detrended Price Oscillator
        df['dpo'] = self._calculate_dpo(df, 20)
        
        # Fisher Transform
        df['fisher_transform'] = self._calculate_fisher_transform(df, 10)
        
        return df
    
    def _add_statistical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Añade features estadísticos avanzados."""
        
        # Z-scores
        df['price_zscore'] = (df['close'] - df['close'].rolling(50).mean()) / df['close'].rolling(50).std()
        
        # Percentile ranks
        df['price_percentile'] = df['close'].rolling(100).rank(pct=True)
        
        # Variance ratio test
        df['variance_ratio'] = self._calculate_variance_ratio(df['close'], 20)
        
        # Autocorrelation
        df['autocorr'] = df['close'].pct_change().rolling(20).apply(
            lambda x: x.autocorr(lag=1) if len(x.dropna()) > 10 else 0, raw=False
        )
        
        # Hurst exponent (simplified)
        df['hurst'] = self._calculate_hurst_exponent(df['close'], 20)
        
        return df
    
    def _add_fractal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Añade features fractales."""
        
        # Fractal highs and lows
        df['fractal_high'] = self._identify_fractal_highs(df, 5)
        df['fractal_low'] = self._identify_fractal_lows(df, 5)
        
        # Distance to fractals
        df['dist_to_frac_high'] = self._distance_to_fractal(df, 'fractal_high')
        df['dist_to_frac_low'] = self._distance_to_fractal(df, 'fractal_low')
        
        return df
    
    # Utility functions for calculations
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calcula RSI."""
        delta = prices.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        
        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_stochastic(self, df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
        """Calcula Stochastic Oscillator."""
        low_min = df['low'].rolling(k_period).min()
        high_max = df['high'].rolling(k_period).max()
        
        k_percent = 100 * ((df['close'] - low_min) / (high_max - low_min))
        d_percent = k_percent.rolling(d_period).mean()
        
        return k_percent, d_percent
    
    def _calculate_williams_r(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calcula Williams %R."""
        high_max = df['high'].rolling(period).max()
        low_min = df['low'].rolling(period).min()
        
        williams_r = -100 * ((high_max - df['close']) / (high_max - low_min))
        
        return williams_r
    
    def _calculate_cci(self, df: pd.DataFrame, period: int = 20) -> pd.Series:
        """Calcula Commodity Channel Index."""
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        sma = typical_price.rolling(period).mean()
        mean_dev = typical_price.rolling(period).apply(lambda x: np.abs(x - x.mean()).mean())
        
        cci = (typical_price - sma) / (0.015 * mean_dev)
        
        return cci
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calcula Average True Range."""
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift(1)).abs()
        low_close = (df['low'] - df['close'].shift(1)).abs()
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(period).mean()
        
        return atr
    
    def _calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: float = 2) -> Tuple[pd.Series, pd.Series]:
        """Calcula Bollinger Bands."""
        sma = prices.rolling(period).mean()
        std = prices.rolling(period).std()
        
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        
        return upper_band, lower_band
    
    def _calculate_keltner_channels(self, df: pd.DataFrame, period: int = 20, multiplier: float = 2) -> Tuple[pd.Series, pd.Series]:
        """Calcula Keltner Channels."""
        ema = df['close'].ewm(span=period).mean()
        atr = self._calculate_atr(df, period)
        
        upper = ema + (multiplier * atr)
        lower = ema - (multiplier * atr)
        
        return upper, lower
    
    def _calculate_obv(self, df: pd.DataFrame) -> pd.Series:
        """Calcula On-Balance Volume."""
        obv = np.where(df['close'] > df['close'].shift(1), df['volume'],
                      np.where(df['close'] < df['close'].shift(1), -df['volume'], 0))
        return pd.Series(obv, index=df.index).cumsum()
    
    def _calculate_vpt(self, df: pd.DataFrame) -> pd.Series:
        """Calcula Volume Price Trend."""
        vpt = (df['close'].pct_change() * df['volume']).cumsum()
        return vpt
    
    def _calculate_ad_line(self, df: pd.DataFrame) -> pd.Series:
        """Calcula Accumulation/Distribution Line."""
        clv = ((df['close'] - df['low']) - (df['high'] - df['close'])) / (df['high'] - df['low'])
        clv = clv.fillna(0)
        ad_line = (clv * df['volume']).cumsum()
        return ad_line
    
    def _calculate_mfi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calcula Money Flow Index."""
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        money_flow = typical_price * df['volume']
        
        positive_flow = money_flow.where(typical_price > typical_price.shift(1), 0)
        negative_flow = money_flow.where(typical_price < typical_price.shift(1), 0)
        
        positive_mf = positive_flow.rolling(period).sum()
        negative_mf = negative_flow.rolling(period).sum()
        
        mfi = 100 - (100 / (1 + (positive_mf / negative_mf)))
        
        return mfi
    
    def _calculate_dpo(self, df: pd.DataFrame, period: int = 20) -> pd.Series:
        """Calcula Detrended Price Oscillator."""
        sma = df['close'].rolling(period).mean()
        dpo = df['close'] - sma.shift(period // 2 + 1)
        return dpo
    
    def _calculate_fisher_transform(self, df: pd.DataFrame, period: int = 10) -> pd.Series:
        """Calcula Fisher Transform."""
        high_max = df['high'].rolling(period).max()
        low_min = df['low'].rolling(period).min()
        
        value = 2 * ((df['close'] - low_min) / (high_max - low_min) - 0.5)
        value = np.clip(value, -0.999, 0.999)  # Avoid log(0)
        
        fisher = 0.5 * np.log((1 + value) / (1 - value))
        
        return pd.Series(fisher, index=df.index)
    
    def _calculate_variance_ratio(self, prices: pd.Series, period: int = 20) -> pd.Series:
        """Calcula Variance Ratio."""
        returns = prices.pct_change()
        
        def var_ratio(x):
            if len(x) < period:
                return 1.0
            var_1 = x.var()
            var_k = x.rolling(period).sum().var() / period
            return var_k / var_1 if var_1 != 0 else 1.0
        
        return returns.rolling(period * 2).apply(var_ratio, raw=False)
    
    def _calculate_hurst_exponent(self, prices: pd.Series, period: int = 20) -> pd.Series:
        """Calcula Hurst Exponent (simplified)."""
        
        def hurst_calc(x):
            if len(x) < period:
                return 0.5
            
            try:
                # Simple Hurst calculation
                lags = range(2, min(10, len(x)))
                tau = [np.std(np.subtract(x[lag:], x[:-lag])) for lag in lags]
                
                # Linear regression of log(tau) vs log(lags)
                reg = np.polyfit(np.log(lags), np.log(tau), 1)
                return reg[0]  # Hurst exponent
            except:
                return 0.5
        
        return prices.rolling(period * 2).apply(hurst_calc, raw=False)
    
    # Pattern recognition functions
    
    def _is_doji(self, df: pd.DataFrame) -> pd.Series:
        """Identifica patrones Doji."""
        body = abs(df['open'] - df['close'])
        range_size = df['high'] - df['low']
        
        doji = (body / range_size) < 0.1
        return doji.astype(int)
    
    def _is_hammer(self, df: pd.DataFrame) -> pd.Series:
        """Identifica patrones Hammer."""
        body = abs(df['open'] - df['close'])
        lower_shadow = df[['open', 'close']].min(axis=1) - df['low']
        upper_shadow = df['high'] - df[['open', 'close']].max(axis=1)
        
        hammer = (lower_shadow > 2 * body) & (upper_shadow < body)
        return hammer.astype(int)
    
    def _is_shooting_star(self, df: pd.DataFrame) -> pd.Series:
        """Identifica patrones Shooting Star."""
        body = abs(df['open'] - df['close'])
        upper_shadow = df['high'] - df[['open', 'close']].max(axis=1)
        lower_shadow = df[['open', 'close']].min(axis=1) - df['low']
        
        shooting_star = (upper_shadow > 2 * body) & (lower_shadow < body)
        return shooting_star.astype(int)
    
    def _is_bullish_engulfing(self, df: pd.DataFrame) -> pd.Series:
        """Identifica patrones Bullish Engulfing."""
        prev_bearish = df['close'].shift(1) < df['open'].shift(1)
        current_bullish = df['close'] > df['open']
        engulfing = (df['open'] < df['close'].shift(1)) & (df['close'] > df['open'].shift(1))
        
        bullish_engulfing = prev_bearish & current_bullish & engulfing
        return bullish_engulfing.astype(int)
    
    def _is_bearish_engulfing(self, df: pd.DataFrame) -> pd.Series:
        """Identifica patrones Bearish Engulfing."""
        prev_bullish = df['close'].shift(1) > df['open'].shift(1)
        current_bearish = df['close'] < df['open']
        engulfing = (df['open'] > df['close'].shift(1)) & (df['close'] < df['open'].shift(1))
        
        bearish_engulfing = prev_bullish & current_bearish & engulfing
        return bearish_engulfing.astype(int)
    
    def _calculate_trend_strength(self, df: pd.DataFrame, period: int = 20) -> pd.Series:
        """Calcula fortaleza de tendencia."""
        price_change = df['close'].pct_change(period)
        volatility = df['close'].pct_change().rolling(period).std()
        
        trend_strength = price_change / volatility
        return trend_strength.fillna(0)
    
    def _calculate_channel_position(self, df: pd.DataFrame, period: int = 20) -> pd.Series:
        """Calcula posición en canal de precio."""
        high_max = df['high'].rolling(period).max()
        low_min = df['low'].rolling(period).min()
        
        position = (df['close'] - low_min) / (high_max - low_min)
        return position.fillna(0.5)
    
    def _identify_fractal_highs(self, df: pd.DataFrame, window: int = 5) -> pd.Series:
        """Identifica fractales altos."""
        fractals = np.zeros(len(df))
        
        for i in range(window, len(df) - window):
            if df['high'].iloc[i] == df['high'].iloc[i-window:i+window+1].max():
                fractals[i] = 1
        
        return pd.Series(fractals, index=df.index)
    
    def _identify_fractal_lows(self, df: pd.DataFrame, window: int = 5) -> pd.Series:
        """Identifica fractales bajos."""
        fractals = np.zeros(len(df))
        
        for i in range(window, len(df) - window):
            if df['low'].iloc[i] == df['low'].iloc[i-window:i+window+1].min():
                fractals[i] = 1
        
        return pd.Series(fractals, index=df.index)
    
    def _distance_to_fractal(self, df: pd.DataFrame, fractal_col: str) -> pd.Series:
        """Calcula distancia al fractal más reciente."""
        distances = np.full(len(df), np.nan)
        last_fractal_idx = -1
        
        for i in range(len(df)):
            if df[fractal_col].iloc[i] == 1:
                last_fractal_idx = i
            
            if last_fractal_idx >= 0:
                distances[i] = i - last_fractal_idx
        
        return pd.Series(distances, index=df.index).fillna(100)
    
    def _clean_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Limpia y normaliza features."""
        
        # Llenar NaN values
        df = df.fillna(method='ffill').fillna(method='bfill').fillna(0)
        
        # Remover infinitos
        df = df.replace([np.inf, -np.inf], 0)
        
        # Clip valores extremos
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if col not in ['open', 'high', 'low', 'close', 'volume']:
                # Clip a 5 desviaciones estándar
                mean_val = df[col].mean()
                std_val = df[col].std()
                df[col] = np.clip(df[col], mean_val - 5*std_val, mean_val + 5*std_val)
        
        return df


# Instancia global
advanced_feature_generator = AdvancedFeatureGenerator()