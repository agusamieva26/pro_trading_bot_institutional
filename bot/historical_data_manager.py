# bot/historical_data_manager.py
"""
Historical Data Manager for Backtesting Engine

Provides efficient historical data loading, caching, validation, and management
for institutional-grade backtesting with support for multiple timeframes and symbols.
"""

import pandas as pd
import numpy as np
import os
import hashlib
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
from pathlib import Path

from .data import fetch_bars, _tf
from .config import settings
from .util import logger

warnings.filterwarnings('ignore', category=FutureWarning)

# Conditional imports to avoid dill circular import issues
try:
    import pickle
    PICKLE_AVAILABLE = True
except ImportError:
    PICKLE_AVAILABLE = False
    logger.warning("⚠️ pickle not available - cache serialization disabled")


class HistoricalDataManager:
    """
    Advanced historical data management system for backtesting.
    
    Features:
    - Efficient caching with integrity validation
    - Multi-timeframe support with automatic resampling
    - Data quality validation and cleansing
    - Memory-optimized loading for large datasets
    - Parallel data fetching for multiple symbols
    """
    
    def __init__(self, cache_dir: str = "backtest_cache"):
        """
        Initialize Historical Data Manager.
        
        Args:
            cache_dir: Directory for caching historical data
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # Cache for loaded data to avoid repeated file reads
        self._memory_cache = {}
        self._cache_size_limit = 500_000_000  # 500MB limit
        self._current_cache_size = 0
        
        # Data validation thresholds
        self.max_gap_minutes = 60  # Maximum gap between bars
        self.min_volume_threshold = 0.0001  # Minimum volume threshold
        self.price_change_threshold = 0.5  # Maximum single-bar price change (50%)
        
        logger.info(f"📊 Historical Data Manager initialized with cache: {self.cache_dir}")
    
    def _get_cache_key(self, symbol: str, timeframe: str, start_date: str, end_date: str) -> str:
        """Generate unique cache key for data request."""
        key_string = f"{symbol}_{timeframe}_{start_date}_{end_date}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """Get cache file path for given cache key."""
        return self.cache_dir / f"{cache_key}.parquet"
    
    def _safe_strftime(self, timestamp, format_str: str) -> str:
        """Safely format timestamp to string with fallback for non-datetime types."""
        try:
            if hasattr(timestamp, 'strftime'):
                return timestamp.strftime(format_str)
            elif pd.isna(timestamp):
                return 'N/A'
            else:
                return str(timestamp)
        except (AttributeError, TypeError, ValueError):
            return 'Invalid Date'
    
    def _validate_data_quality(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """
        Validate and clean data quality issues.
        
        Args:
            df: Raw price data
            symbol: Symbol name for logging
            
        Returns:
            Cleaned DataFrame
        """
        if df.empty:
            return df
        
        original_len = len(df)
        
        # 1. Remove rows with invalid prices
        invalid_mask = (
            (df['open'] <= 0) | (df['high'] <= 0) | 
            (df['low'] <= 0) | (df['close'] <= 0) |
            df[['open', 'high', 'low', 'close']].isna().any(axis=1)
        )
        # Ensure we maintain DataFrame type
        filtered_df = df[~invalid_mask]
        if isinstance(filtered_df, pd.Series):
            # Handle edge case where filtering returns Series
            df = pd.DataFrame(filtered_df).T if not filtered_df.empty else pd.DataFrame()
        else:
            df = filtered_df
        
        if invalid_mask.sum() > 0:
            logger.warning(f"🔧 {symbol}: Removed {invalid_mask.sum()} rows with invalid prices")
        
        # 2. Fix OHLC logic violations
        df['high'] = df[['open', 'high', 'low', 'close']].max(axis=1)
        df['low'] = df[['open', 'high', 'low', 'close']].min(axis=1)
        
        # 3. Detect and cap extreme price movements
        price_change = df['close'].pct_change().abs()
        extreme_moves = price_change > self.price_change_threshold
        
        if extreme_moves.sum() > 0:
            logger.warning(f"🚨 {symbol}: Found {extreme_moves.sum()} extreme price movements (>{self.price_change_threshold:.1%})")
            # Cap extreme movements to reasonable levels
            for idx in df[extreme_moves].index:
                if idx > 0:
                    prev_close = df.loc[df.index < idx, 'close'].iloc[-1]
                    max_change = self.price_change_threshold
                    
                    # Cap all OHLC values to reasonable range
                    min_price = prev_close * (1 - max_change)
                    max_price = prev_close * (1 + max_change)
                    
                    df.loc[idx, 'open'] = np.clip(df.loc[idx, 'open'], min_price, max_price)
                    df.loc[idx, 'high'] = np.clip(df.loc[idx, 'high'], min_price, max_price)
                    df.loc[idx, 'low'] = np.clip(df.loc[idx, 'low'], min_price, max_price)
                    df.loc[idx, 'close'] = np.clip(df.loc[idx, 'close'], min_price, max_price)
        
        # 4. Handle volume data
        if 'volume' in df.columns:
            # Set minimum volume threshold
            df.loc[df['volume'] < self.min_volume_threshold, 'volume'] = self.min_volume_threshold
        else:
            # Add default volume if missing
            df['volume'] = 1.0
        
        # 5. Fill forward any remaining NaN values
        df = df.fillna(method='ffill').fillna(method='bfill')
        
        if len(df) != original_len:
            logger.info(f"✅ {symbol}: Data validation complete. {original_len} → {len(df)} rows")
        
        return df
    
    def _detect_gaps(self, df: pd.DataFrame, timeframe: str, symbol: str) -> List[Tuple[datetime, datetime]]:
        """
        Detect significant gaps in time series data.
        
        Args:
            df: Price data with DatetimeIndex
            timeframe: Timeframe string (e.g., '1Min', '5Min')
            symbol: Symbol name for logging
            
        Returns:
            List of gap periods (start, end)
        """
        if len(df) < 2:
            return []
        
        # Expected frequency based on timeframe
        freq_map = {
            '1Min': 1, '5Min': 5, '15Min': 15, '30Min': 30,
            '1Hour': 60, '2Hour': 120, '4Hour': 240, '1Day': 1440
        }
        expected_minutes = freq_map.get(timeframe, 60)
        
        # Calculate actual gaps
        time_diffs = df.index.to_series().diff().dt.total_seconds() / 60
        significant_gaps = time_diffs > (expected_minutes * 3)  # 3x expected frequency
        
        gaps = []
        if significant_gaps.sum() > 0:
            gap_indices = df.index[significant_gaps]
            for gap_idx in gap_indices:
                gap_start = df.index[df.index < gap_idx][-1]
                gap_end = gap_idx
                gaps.append((gap_start, gap_end))
                
            logger.info(f"📊 {symbol}: Found {len(gaps)} significant gaps in {timeframe} data")
        
        return gaps
    
    def _resample_data(self, df: pd.DataFrame, target_timeframe: str) -> pd.DataFrame:
        """
        Resample data to target timeframe using proper OHLCV aggregation.
        
        Args:
            df: Source data
            target_timeframe: Target timeframe string
            
        Returns:
            Resampled DataFrame
        """
        if df.empty:
            return df
        
        # Mapping to pandas frequency strings
        freq_map = {
            '1Min': '1T', '5Min': '5T', '15Min': '15T', '30Min': '30T',
            '1Hour': '1H', '2Hour': '2H', '4Hour': '4H', '1Day': '1D'
        }
        
        freq = freq_map.get(target_timeframe, '1H')
        
        # OHLCV aggregation rules
        agg_rules = {
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }
        
        # Apply aggregation only to columns that exist
        available_rules = {k: v for k, v in agg_rules.items() if k in df.columns}
        
        resampled = df.resample(freq).agg(available_rules)
        
        # Remove rows where all OHLC values are NaN (gaps in data)
        ohlc_cols = [col for col in ['open', 'high', 'low', 'close'] if col in resampled.columns]
        
        # Fix dropna signature - use named parameters to ensure correct LSP interpretation
        if ohlc_cols:
            # Remove rows where all specified OHLC columns are NaN
            # Use explicit parameter naming to satisfy LSP type checking
            resampled_result = resampled.dropna(how='all', subset=ohlc_cols)
        else:
            resampled_result = resampled.dropna(how='all')
        
        # Ensure return type is always DataFrame
        return resampled_result if isinstance(resampled_result, pd.DataFrame) else pd.DataFrame(resampled_result)
    
    def _load_from_cache(self, cache_key: str) -> Optional[pd.DataFrame]:
        """Load data from cache if exists and valid."""
        cache_path = self._get_cache_path(cache_key)
        
        if not cache_path.exists():
            return None
        
        try:
            # Check memory cache first
            if cache_key in self._memory_cache:
                logger.debug(f"📁 Memory cache hit: {cache_key[:8]}...")
                return self._memory_cache[cache_key].copy()
            
            # Load from disk
            df = pd.read_parquet(cache_path)
            
            # Add to memory cache if space available
            df_size = df.memory_usage(deep=True).sum()
            if self._current_cache_size + df_size < self._cache_size_limit:
                self._memory_cache[cache_key] = df.copy()
                self._current_cache_size += df_size
                logger.debug(f"📁 Loaded to memory cache: {cache_key[:8]}... ({df_size/1024/1024:.1f}MB)")
            
            return df
            
        except Exception as e:
            logger.warning(f"⚠️ Cache load failed for {cache_key[:8]}...: {e}")
            # Remove corrupted cache file
            if cache_path.exists():
                cache_path.unlink()
            return None
    
    def _save_to_cache(self, df: pd.DataFrame, cache_key: str) -> None:
        """Save data to cache."""
        cache_path = self._get_cache_path(cache_key)
        
        try:
            df.to_parquet(cache_path, compression='snappy')
            logger.debug(f"💾 Cached data: {cache_key[:8]}... ({len(df)} rows)")
        except Exception as e:
            logger.warning(f"⚠️ Cache save failed for {cache_key[:8]}...: {e}")
    
    def load_symbol_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        timeframe: str = "1Hour",
        force_refresh: bool = False,
        validate_quality: bool = True
    ) -> pd.DataFrame:
        """
        Load historical data for a single symbol with caching and validation.
        
        Args:
            symbol: Symbol to load (e.g., 'BTC/USD', 'AAPL')
            start_date: Start date string (YYYY-MM-DD)
            end_date: End date string (YYYY-MM-DD)
            timeframe: Timeframe string (1Min, 5Min, 15Min, 1Hour, 1Day)
            force_refresh: Force refresh from API ignoring cache
            validate_quality: Apply data quality validation
            
        Returns:
            DataFrame with OHLCV data
        """
        cache_key = self._get_cache_key(symbol, timeframe, start_date, end_date)
        
        # Try loading from cache first
        if not force_refresh:
            cached_data = self._load_from_cache(cache_key)
            if cached_data is not None and not cached_data.empty:
                logger.debug(f"📊 {symbol} ({timeframe}): Loaded from cache ({len(cached_data)} bars)")
                return cached_data
        
        # Fetch fresh data from API
        logger.info(f"🔄 {symbol} ({timeframe}): Fetching from API ({start_date} to {end_date})")
        
        try:
            # Convert settings timeframe temporarily if needed
            original_timeframe = settings.bar_timeframe
            settings.bar_timeframe = timeframe
            
            df = fetch_bars(
                symbol=symbol,
                start=start_date,
                end=end_date,
                min_bars=1
            )
            
            # Restore original timeframe
            settings.bar_timeframe = original_timeframe
            
            if df.empty:
                logger.warning(f"⚠️ {symbol}: No data received from API")
                return df
            
            # Apply data validation
            if validate_quality:
                df = self._validate_data_quality(df, symbol)
            
            # Detect and log gaps
            gaps = self._detect_gaps(df, timeframe, symbol)
            
            # Add metadata
            df.attrs['symbol'] = symbol
            df.attrs['timeframe'] = timeframe
            df.attrs['gaps'] = gaps
            df.attrs['loaded_at'] = datetime.now().isoformat()
            
            # Cache the data
            self._save_to_cache(df, cache_key)
            
            logger.info(f"✅ {symbol} ({timeframe}): Loaded {len(df)} bars successfully")
            return df
            
        except Exception as e:
            logger.error(f"❌ {symbol} ({timeframe}): Failed to load data - {e}")
            return pd.DataFrame()
    
    def load_multiple_symbols(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        timeframe: str = "1Hour",
        max_workers: int = 4,
        force_refresh: bool = False
    ) -> Dict[str, pd.DataFrame]:
        """
        Load historical data for multiple symbols in parallel.
        
        Args:
            symbols: List of symbols to load
            start_date: Start date string (YYYY-MM-DD)
            end_date: End date string (YYYY-MM-DD)
            timeframe: Timeframe string
            max_workers: Maximum parallel workers
            force_refresh: Force refresh from API
            
        Returns:
            Dictionary mapping symbols to DataFrames
        """
        logger.info(f"📊 Loading data for {len(symbols)} symbols ({timeframe})")
        
        results = {}
        
        # Use ThreadPoolExecutor for parallel loading
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_symbol = {
                executor.submit(
                    self.load_symbol_data,
                    symbol, start_date, end_date, timeframe, force_refresh
                ): symbol
                for symbol in symbols
            }
            
            # Collect results
            completed = 0
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                completed += 1
                
                try:
                    df = future.result()
                    results[symbol] = df
                    
                    if not df.empty:
                        logger.debug(f"✅ {symbol}: {len(df)} bars ({completed}/{len(symbols)})")
                    else:
                        logger.warning(f"⚠️ {symbol}: No data ({completed}/{len(symbols)})")
                        
                except Exception as e:
                    logger.error(f"❌ {symbol}: Error loading data - {e}")
                    results[symbol] = pd.DataFrame()
        
        successful = len([df for df in results.values() if not df.empty])
        logger.info(f"🎯 Batch load complete: {successful}/{len(symbols)} symbols successful")
        
        return results
    
    def get_data_summary(self, symbols: List[str], timeframe: str = "1Hour") -> pd.DataFrame:
        """
        Get summary statistics for cached data across symbols.
        
        Args:
            symbols: List of symbols to summarize
            timeframe: Timeframe to check
            
        Returns:
            DataFrame with summary statistics
        """
        summary_data = []
        
        for symbol in symbols:
            # Check if data exists in cache
            cache_files = list(self.cache_dir.glob(f"*{symbol.replace('/', '_')}*{timeframe}*.parquet"))
            
            if cache_files:
                try:
                    # Load most recent cache file
                    latest_file = max(cache_files, key=os.path.getctime)
                    df = pd.read_parquet(latest_file)
                    
                    summary_data.append({
                        'symbol': symbol,
                        'bars_count': len(df),
                        'start_date': self._safe_strftime(df.index.min(), '%Y-%m-%d %H:%M'),
                        'end_date': self._safe_strftime(df.index.max(), '%Y-%m-%d %H:%M'),
                        'timeframe': timeframe,
                        'file_size_mb': latest_file.stat().st_size / 1024 / 1024,
                        'gaps_detected': len(df.attrs.get('gaps', [])),
                        'last_cached': datetime.fromtimestamp(latest_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
                    })
                except Exception as e:
                    logger.warning(f"⚠️ {symbol}: Error reading cache summary - {e}")
            else:
                summary_data.append({
                    'symbol': symbol,
                    'bars_count': 0,
                    'start_date': 'No data',
                    'end_date': 'No data',
                    'timeframe': timeframe,
                    'file_size_mb': 0,
                    'gaps_detected': 0,
                    'last_cached': 'Never'
                })
        
        return pd.DataFrame(summary_data)
    
    def clear_cache(self, symbol: Optional[str] = None, timeframe: Optional[str] = None) -> int:
        """
        Clear cache files with optional filtering.
        
        Args:
            symbol: Optional symbol filter
            timeframe: Optional timeframe filter
            
        Returns:
            Number of files removed
        """
        pattern = "*"
        if symbol:
            pattern += f"*{symbol.replace('/', '_')}*"
        if timeframe:
            pattern += f"*{timeframe}*"
        pattern += ".parquet"
        
        cache_files = list(self.cache_dir.glob(pattern))
        removed_count = 0
        
        for cache_file in cache_files:
            try:
                cache_file.unlink()
                removed_count += 1
            except Exception as e:
                logger.warning(f"⚠️ Failed to remove {cache_file}: {e}")
        
        # Clear memory cache
        if symbol is None and timeframe is None:
            self._memory_cache.clear()
            self._current_cache_size = 0
        
        logger.info(f"🗑️ Cleared {removed_count} cache files")
        return removed_count
    
    def optimize_memory_usage(self) -> Dict[str, float]:
        """
        Optimize memory usage by clearing least recently used cache entries.
        
        Returns:
            Memory usage statistics
        """
        initial_size = self._current_cache_size
        
        if self._current_cache_size > self._cache_size_limit * 0.8:  # 80% threshold
            # Remove oldest 25% of cache entries
            sorted_keys = sorted(
                self._memory_cache.keys(),
                key=lambda x: self._memory_cache[x].attrs.get('loaded_at', ''),
                reverse=True
            )
            
            keys_to_remove = sorted_keys[int(len(sorted_keys) * 0.75):]
            
            for key in keys_to_remove:
                if key in self._memory_cache:
                    df_size = self._memory_cache[key].memory_usage(deep=True).sum()
                    del self._memory_cache[key]
                    self._current_cache_size -= df_size
        
        return {
            'initial_size_mb': initial_size / 1024 / 1024,
            'final_size_mb': self._current_cache_size / 1024 / 1024,
            'cache_entries': len(self._memory_cache),
            'freed_mb': (initial_size - self._current_cache_size) / 1024 / 1024
        }


# Global instance for easy access
historical_data_manager = HistoricalDataManager()