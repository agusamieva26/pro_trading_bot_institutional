# bot/arbitrage_engine.py
"""
🏛️ INSTITUTIONAL ARBITRAGE ENGINE
Advanced arbitrage detection and execution system for guaranteed profit opportunities.
"""

import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

from .config import settings
from .util import logger, is_crypto_symbol
from .data import fetch_bars, fetch_last_bars
from .price_comparator import PriceComparator


@dataclass
class ArbitrageOpportunity:
    """Represents a detected arbitrage opportunity."""
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    spread_pct: float
    net_profit_pct: float
    potential_profit_usd: float
    volume_available: float
    confidence_score: float
    timestamp: float
    
    def is_profitable(self, min_profit_pct: float = 0.5) -> bool:
        """Check if opportunity meets minimum profit threshold."""
        return self.net_profit_pct >= min_profit_pct
    
    def is_high_profit(self, threshold_pct: float = 1.0) -> bool:
        """Check if this is a high-profit opportunity requiring alert."""
        return self.net_profit_pct >= threshold_pct


class ArbitrageEngine:
    """
    🏛️ INSTITUTIONAL ARBITRAGE ENGINE
    
    Detects price differences ≥0.3% between exchanges and calculates guaranteed profit
    opportunities after accounting for trading fees and slippage.
    """
    
    def __init__(self):
        self.price_comparator = PriceComparator()
        self.trading_fee_pct = 0.001  # 0.1% per trade (conservative estimate)
        self.slippage_pct = 0.0005   # 0.05% slippage factor
        self.min_spread_threshold = 0.003  # 0.3% minimum spread
        self.min_profit_threshold = 0.005  # 0.5% minimum net profit
        self.high_profit_threshold = 0.010  # 1.0% high profit alert threshold
        
        # Risk management settings
        self.max_arbitrage_exposure_pct = 0.15  # 15% of capital max
        self.min_volume_usd = 1000.0  # Minimum $1000 volume for arbitrage
        self.max_position_size_usd = 10000.0  # Maximum $10k per arbitrage trade
        
        # Performance tracking
        self.opportunities_detected = 0
        self.opportunities_executed = 0
        self.total_profit_realized = 0.0
        self.success_rate = 0.0
        
        logger.info("🏛️ Institutional Arbitrage Engine initialized")
        
    def calculate_net_profit(self, buy_price: float, sell_price: float) -> Tuple[float, float]:
        """
        Calculate net profit percentage after fees and slippage.
        
        Returns:
            Tuple[spread_pct, net_profit_pct]: Raw spread and net profit after costs
        """
        if buy_price <= 0 or sell_price <= 0:
            return 0.0, 0.0
            
        # Raw spread percentage
        spread_pct = (sell_price - buy_price) / buy_price
        
        # Account for trading fees (0.1% per side = 0.2% total)
        total_fees_pct = self.trading_fee_pct * 2
        
        # Account for slippage (0.05% per side = 0.1% total)
        total_slippage_pct = self.slippage_pct * 2
        
        # Net profit after all costs
        net_profit_pct = spread_pct - total_fees_pct - total_slippage_pct
        
        return spread_pct, net_profit_pct
    
    def validate_liquidity(self, symbol: str, volume_data: Dict) -> bool:
        """
        Validate sufficient liquidity exists for arbitrage execution.
        
        Args:
            symbol: Trading symbol
            volume_data: Volume information from exchanges
            
        Returns:
            bool: True if liquidity is sufficient
        """
        try:
            # Get minimum volume from exchanges
            min_volume = min(volume_data.values()) if volume_data else 0
            
            # Check minimum USD volume requirement
            if min_volume < self.min_volume_usd:
                logger.debug(f"🚫 {symbol}: Insufficient volume ${min_volume:.0f} < ${self.min_volume_usd:.0f}")
                return False
                
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Liquidity validation error for {symbol}: {e}")
            return False
    
    def calculate_confidence_score(self, symbol: str, spread_pct: float, volume_data: Dict) -> float:
        """
        Calculate confidence score for arbitrage opportunity (0.0 to 1.0).
        
        Factors:
        - Spread size (higher = more confident)
        - Volume consistency (more consistent = higher confidence)
        - Symbol volatility (lower volatility = higher confidence)
        """
        try:
            confidence = 0.0
            
            # Factor 1: Spread size (30% weight)
            if spread_pct >= 0.02:  # ≥2% spread
                confidence += 0.30
            elif spread_pct >= 0.01:  # ≥1% spread
                confidence += 0.20
            elif spread_pct >= 0.005:  # ≥0.5% spread
                confidence += 0.10
            
            # Factor 2: Volume consistency (40% weight)
            if volume_data:
                volumes = list(volume_data.values())
                if len(volumes) >= 2:
                    volume_std = pd.Series(volumes).std()
                    volume_mean = pd.Series(volumes).mean()
                    volume_cv = volume_std / volume_mean if volume_mean > 0 else 1.0
                    
                    if volume_cv < 0.1:  # Low coefficient of variation
                        confidence += 0.40
                    elif volume_cv < 0.2:
                        confidence += 0.30
                    elif volume_cv < 0.3:
                        confidence += 0.20
                else:
                    confidence += 0.20  # Default if limited data
            
            # Factor 3: Symbol type stability (30% weight)
            if is_crypto_symbol(symbol):
                # Crypto is more volatile, lower base confidence
                if symbol in ["BTC/USD", "ETH/USD"]:  # Major crypto
                    confidence += 0.25
                else:  # Alt coins
                    confidence += 0.15
            else:
                # Stocks are more stable
                confidence += 0.30
            
            return min(1.0, confidence)
            
        except Exception as e:
            logger.warning(f"⚠️ Confidence calculation error for {symbol}: {e}")
            return 0.5  # Default moderate confidence
    
    def detect_opportunities(self, symbols: List[str]) -> List[ArbitrageOpportunity]:
        """
        Scan for arbitrage opportunities across all provided symbols.
        
        Args:
            symbols: List of symbols to analyze
            
        Returns:
            List of detected arbitrage opportunities sorted by profit potential
        """
        opportunities = []
        
        logger.info(f"🔍 Scanning {len(symbols)} symbols for arbitrage opportunities...")
        
        # Use parallel processing for multiple symbols
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(self._analyze_symbol, symbol): symbol for symbol in symbols}
            
            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    opportunity = future.result()
                    if opportunity:
                        opportunities.append(opportunity)
                        self.opportunities_detected += 1
                        logger.info(f"💰 ARBITRAGE: {symbol} {opportunity.net_profit_pct:.1%} profit opportunity detected")
                except Exception as e:
                    logger.debug(f"🔍 No arbitrage for {symbol}: {e}")
        
        # Sort by net profit potential (highest first)
        opportunities.sort(key=lambda x: x.net_profit_pct, reverse=True)
        
        if opportunities:
            best_opportunity = opportunities[0]
            logger.info(f"🎯 Best opportunity: {best_opportunity.symbol} {best_opportunity.net_profit_pct:.1%} profit")
        
        return opportunities
    
    def _analyze_symbol(self, symbol: str) -> Optional[ArbitrageOpportunity]:
        """
        Analyze a single symbol for arbitrage opportunities.
        
        Args:
            symbol: Symbol to analyze
            
        Returns:
            ArbitrageOpportunity if found, None otherwise
        """
        try:
            # Get current prices from multiple sources
            price_data = self.price_comparator.get_multi_exchange_prices(symbol)
            
            if len(price_data) < 2:
                return None
                
            # Find best buy and sell prices
            prices = [(exchange, data['price']) for exchange, data in price_data.items() 
                     if data['price'] > 0]
            
            if len(prices) < 2:
                return None
                
            # Sort by price (lowest to highest)
            prices.sort(key=lambda x: x[1])
            
            buy_exchange, buy_price = prices[0]  # Lowest price (buy here)
            sell_exchange, sell_price = prices[-1]  # Highest price (sell here)
            
            # Calculate spread and net profit
            spread_pct, net_profit_pct = self.calculate_net_profit(buy_price, sell_price)
            
            # Check minimum thresholds
            if spread_pct < self.min_spread_threshold:
                return None
                
            if net_profit_pct < self.min_profit_threshold:
                return None
            
            # Validate liquidity
            volume_data = {exchange: data.get('volume', 0) for exchange, data in price_data.items()}
            if not self.validate_liquidity(symbol, volume_data):
                return None
            
            # Calculate confidence and potential profit
            confidence_score = self.calculate_confidence_score(symbol, spread_pct, volume_data)
            
            # Estimate position size based on available volume and max position
            min_volume = min(volume_data.values())
            position_size_usd = min(self.max_position_size_usd, min_volume * 0.1)  # Use 10% of min volume
            potential_profit_usd = position_size_usd * net_profit_pct
            
            opportunity = ArbitrageOpportunity(
                symbol=symbol,
                buy_exchange=buy_exchange,
                sell_exchange=sell_exchange,
                buy_price=buy_price,
                sell_price=sell_price,
                spread_pct=spread_pct,
                net_profit_pct=net_profit_pct,
                potential_profit_usd=potential_profit_usd,
                volume_available=min_volume,
                confidence_score=confidence_score,
                timestamp=time.time()
            )
            
            return opportunity
            
        except Exception as e:
            logger.debug(f"🔍 Arbitrage analysis failed for {symbol}: {e}")
            return None
    
    def filter_executable_opportunities(self, opportunities: List[ArbitrageOpportunity], 
                                      available_capital: float) -> List[ArbitrageOpportunity]:
        """
        Filter opportunities that can be executed with available capital and risk limits.
        
        Args:
            opportunities: List of detected opportunities
            available_capital: Available capital for arbitrage trading
            
        Returns:
            Filtered list of executable opportunities
        """
        executable = []
        max_arbitrage_capital = available_capital * self.max_arbitrage_exposure_pct
        
        total_allocated = 0.0
        
        for opportunity in opportunities:
            # Check if we have enough capital remaining
            required_capital = min(opportunity.potential_profit_usd / opportunity.net_profit_pct, 
                                 self.max_position_size_usd)
            
            if total_allocated + required_capital <= max_arbitrage_capital:
                executable.append(opportunity)
                total_allocated += required_capital
                
                logger.info(f"✅ {opportunity.symbol}: Executable arbitrage ${required_capital:.0f} "
                           f"({opportunity.net_profit_pct:.1%} profit)")
            else:
                logger.debug(f"🚫 {opportunity.symbol}: Insufficient capital remaining")
        
        logger.info(f"🎯 Executable opportunities: {len(executable)}/{len(opportunities)} "
                   f"(${total_allocated:.0f}/${max_arbitrage_capital:.0f} allocated)")
        
        return executable
    
    def get_performance_stats(self) -> Dict:
        """Get arbitrage engine performance statistics."""
        if self.opportunities_detected > 0:
            self.success_rate = self.opportunities_executed / self.opportunities_detected
        
        return {
            'opportunities_detected': self.opportunities_detected,
            'opportunities_executed': self.opportunities_executed,
            'success_rate': self.success_rate,
            'total_profit_realized': self.total_profit_realized,
            'avg_profit_per_trade': (self.total_profit_realized / max(1, self.opportunities_executed))
        }
    
    def record_execution(self, opportunity: ArbitrageOpportunity, actual_profit: float):
        """Record executed arbitrage trade for performance tracking."""
        self.opportunities_executed += 1
        self.total_profit_realized += actual_profit
        
        logger.info(f"📊 Arbitrage executed: {opportunity.symbol} "
                   f"Expected: {opportunity.net_profit_pct:.1%}, "
                   f"Actual: ${actual_profit:.2f}")


# Global arbitrage engine instance
arbitrage_engine = ArbitrageEngine()