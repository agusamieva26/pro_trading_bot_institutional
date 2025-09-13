# bot/price_comparator.py
"""
📊 PRICE COMPARATOR MODULE
Real-time price comparison between multiple exchanges for arbitrage detection.
"""

import time
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd

from .config import settings
from .util import logger, is_crypto_symbol, get_cache_ttl_for_symbol
from .data import fetch_last_bars
from alpaca.trading.client import TradingClient


class PriceComparator:
    """
    📊 REAL-TIME PRICE COMPARATOR
    
    Compares prices across multiple data sources to identify arbitrage opportunities.
    Supports both crypto and stock markets with different data sources.
    """
    
    def __init__(self):
        self.cache = {}
        self.last_update = {}
        self.trading_client = None
        
        logger.info("📊 Price Comparator initialized")
    
    def _get_trading_client(self):
        """Get or create Alpaca trading client."""
        if not self.trading_client:
            self.trading_client = TradingClient(
                api_key=settings.alpaca_api_key,
                secret_key=settings.alpaca_secret_key,
                paper=(settings.mode == "paper")
            )
        return self.trading_client
    
    def _is_cache_valid(self, symbol: str) -> bool:
        """Check if cached price data is still valid."""
        if symbol not in self.last_update:
            return False
            
        cache_ttl = get_cache_ttl_for_symbol(symbol)
        time_since_update = time.time() - self.last_update[symbol]
        
        return time_since_update < cache_ttl
    
    def get_alpaca_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get current price from Alpaca (our primary exchange).
        
        Returns:
            Dict with price, volume, and timestamp info
        """
        try:
            # For real-time pricing, try to get from latest bars
            df = fetch_last_bars(symbol, n=1)
            
            if df.empty:
                logger.debug(f"⚠️ No Alpaca data for {symbol}")
                return None
            
            latest_bar = df.iloc[-1]
            
            return {
                'exchange': 'ALPACA',
                'price': float(latest_bar['close']),
                'volume': float(latest_bar.get('volume', 0)),
                'bid': float(latest_bar.get('close', 0)) * 0.9995,  # Estimate bid
                'ask': float(latest_bar.get('close', 0)) * 1.0005,  # Estimate ask
                'timestamp': time.time(),
                'source': 'historical_bars'
            }
            
        except Exception as e:
            logger.debug(f"❌ Alpaca price fetch failed for {symbol}: {e}")
            return None
    
    def get_simulated_exchange_prices(self, symbol: str, base_price: float) -> Dict[str, Dict[str, Any]]:
        """
        Simulate multiple exchanges with realistic price variations.
        
        This simulates different exchanges having slightly different prices due to:
        - Network latency
        - Order book depth differences  
        - Fee structures
        - Regional arbitrage opportunities
        
        Args:
            symbol: Trading symbol
            base_price: Base price from primary exchange
            
        Returns:
            Dict of exchange prices with realistic variations
        """
        exchanges = {}
        
        try:
            # Base parameters for price variation
            if is_crypto_symbol(symbol):
                # Crypto has higher volatility and spread variations
                spread_range = (0.001, 0.008)  # 0.1% to 0.8% variation
                volume_multiplier = (0.5, 2.0)
            else:
                # Stocks have tighter spreads
                spread_range = (0.0005, 0.003)  # 0.05% to 0.3% variation  
                volume_multiplier = (0.8, 1.5)
            
            # Simulate 4 major exchanges with different characteristics
            exchange_configs = [
                {
                    'name': 'ALPACA',
                    'bias': 0.0,  # Primary exchange (no bias)
                    'volatility': 0.0,
                    'volume_factor': 1.0
                },
                {
                    'name': 'BINANCE',
                    'bias': -0.002,  # Slightly lower prices (good for buying)
                    'volatility': 0.003,
                    'volume_factor': 1.5  # Higher volume
                },
                {
                    'name': 'COINBASE',
                    'bias': 0.003,  # Slightly higher prices (good for selling)
                    'volatility': 0.002,
                    'volume_factor': 1.2
                },
                {
                    'name': 'KRAKEN',
                    'bias': 0.001,  # Neutral with slight premium
                    'volatility': 0.004,
                    'volume_factor': 0.8  # Lower volume
                }
            ]
            
            # Add time-based variation (market movements)
            time_factor = (time.time() % 300) / 300  # 5-minute cycle
            market_drift = (time_factor - 0.5) * 0.002  # ±0.2% drift
            
            for config in exchange_configs:
                # Calculate price with bias and random variation
                price_variation = config['bias'] + (market_drift * config['volatility'])
                
                # Add small random component
                import random
                random_factor = (random.random() - 0.5) * spread_range[1]
                
                final_variation = price_variation + random_factor
                exchange_price = base_price * (1 + final_variation)
                
                # Ensure price is positive
                exchange_price = max(exchange_price, base_price * 0.95)
                
                # Calculate volume (base volume with exchange factor)
                base_volume = 10000  # $10k base volume
                if is_crypto_symbol(symbol):
                    base_volume *= 5  # Crypto has higher volume
                
                volume = base_volume * config['volume_factor'] * (0.8 + 0.4 * random.random())
                
                exchanges[config['name']] = {
                    'exchange': config['name'],
                    'price': round(exchange_price, 8),
                    'volume': round(volume, 2),
                    'bid': round(exchange_price * 0.9995, 8),
                    'ask': round(exchange_price * 1.0005, 8),
                    'timestamp': time.time(),
                    'source': 'simulated',
                    'variation_pct': final_variation
                }
            
            return exchanges
            
        except Exception as e:
            logger.error(f"❌ Simulated exchange price generation failed for {symbol}: {e}")
            return {}
    
    def get_multi_exchange_prices(self, symbol: str) -> Dict[str, Dict[str, Any]]:
        """
        Get prices from multiple exchanges for arbitrage comparison.
        
        Args:
            symbol: Trading symbol to check
            
        Returns:
            Dict mapping exchange names to price data
        """
        # Check cache first
        if self._is_cache_valid(symbol):
            return self.cache.get(symbol, {})
        
        try:
            # Get primary price from Alpaca
            alpaca_data = self.get_alpaca_price(symbol)
            
            if not alpaca_data:
                logger.debug(f"⚠️ No primary price data for {symbol}")
                return {}
            
            base_price = alpaca_data['price']
            
            # Generate simulated exchange prices based on realistic variations
            all_exchanges = self.get_simulated_exchange_prices(symbol, base_price)
            
            # Add the real Alpaca data
            all_exchanges['ALPACA'] = alpaca_data
            
            # Filter out invalid prices
            valid_exchanges = {
                exchange: data for exchange, data in all_exchanges.items()
                if data.get('price', 0) > 0
            }
            
            if len(valid_exchanges) >= 2:
                # Update cache
                self.cache[symbol] = valid_exchanges
                self.last_update[symbol] = time.time()
                
                logger.debug(f"📊 {symbol}: {len(valid_exchanges)} exchange prices updated")
                
                # Log price spread for debugging
                prices = [data['price'] for data in valid_exchanges.values()]
                min_price, max_price = min(prices), max(prices)
                spread_pct = (max_price - min_price) / min_price
                
                if spread_pct >= 0.003:  # 0.3% threshold
                    logger.info(f"💰 {symbol}: {spread_pct:.1%} spread detected "
                               f"(${min_price:.4f} → ${max_price:.4f})")
            
            return valid_exchanges
            
        except Exception as e:
            logger.error(f"❌ Multi-exchange price fetch failed for {symbol}: {e}")
            return {}
    
    def get_best_prices(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get best bid/ask prices across all exchanges.
        
        Returns:
            Dict with best_bid, best_ask, spread info
        """
        try:
            exchange_data = self.get_multi_exchange_prices(symbol)
            
            if len(exchange_data) < 2:
                return None
            
            best_bid = max(data.get('bid', 0) for data in exchange_data.values())
            best_ask = min(data.get('ask', float('inf')) for data in exchange_data.values())
            
            if best_ask == float('inf') or best_bid <= 0:
                return None
            
            spread = best_ask - best_bid
            spread_pct = spread / best_ask if best_ask > 0 else 0
            
            # Find which exchanges have the best prices
            best_bid_exchange = next(
                (exchange for exchange, data in exchange_data.items() 
                 if data.get('bid', 0) == best_bid), 
                'UNKNOWN'
            )
            
            best_ask_exchange = next(
                (exchange for exchange, data in exchange_data.items() 
                 if data.get('ask', float('inf')) == best_ask), 
                'UNKNOWN'
            )
            
            return {
                'symbol': symbol,
                'best_bid': best_bid,
                'best_ask': best_ask,
                'spread': spread,
                'spread_pct': spread_pct,
                'best_bid_exchange': best_bid_exchange,
                'best_ask_exchange': best_ask_exchange,
                'exchanges_count': len(exchange_data),
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"❌ Best prices calculation failed for {symbol}: {e}")
            return None
    
    def detect_price_anomalies(self, symbol: str, anomaly_threshold: float = 0.01) -> List[Dict]:
        """
        Detect unusual price anomalies that might indicate arbitrage opportunities.
        
        Args:
            symbol: Symbol to analyze
            anomaly_threshold: Threshold for detecting anomalies (1% default)
            
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        try:
            exchange_data = self.get_multi_exchange_prices(symbol)
            
            if len(exchange_data) < 3:
                return anomalies
            
            prices = [data['price'] for data in exchange_data.values()]
            exchanges = list(exchange_data.keys())
            
            mean_price = sum(prices) / len(prices)
            
            for i, (exchange, price) in enumerate(zip(exchanges, prices)):
                deviation_pct = abs(price - mean_price) / mean_price
                
                if deviation_pct >= anomaly_threshold:
                    anomaly_type = "HIGH" if price > mean_price else "LOW"
                    
                    anomalies.append({
                        'symbol': symbol,
                        'exchange': exchange,
                        'price': price,
                        'mean_price': mean_price,
                        'deviation_pct': deviation_pct,
                        'anomaly_type': anomaly_type,
                        'potential_arbitrage': deviation_pct >= 0.005,  # 0.5% threshold
                        'timestamp': time.time()
                    })
            
            if anomalies:
                logger.info(f"🚨 {symbol}: {len(anomalies)} price anomalies detected")
                
        except Exception as e:
            logger.error(f"❌ Anomaly detection failed for {symbol}: {e}")
            
        return anomalies
    
    def get_cache_stats(self) -> Dict:
        """Get cache performance statistics."""
        return {
            'cached_symbols': len(self.cache),
            'total_cache_age': sum(time.time() - timestamp for timestamp in self.last_update.values()),
            'avg_cache_age': (sum(time.time() - timestamp for timestamp in self.last_update.values()) / 
                            len(self.last_update)) if self.last_update else 0
        }


# Global price comparator instance
price_comparator = PriceComparator()