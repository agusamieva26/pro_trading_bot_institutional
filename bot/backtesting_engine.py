# bot/backtesting_engine.py
"""
Institutional-Grade Backtesting Engine

Core backtesting engine that simulates trading strategies on historical data
with realistic execution modeling, comprehensive performance tracking, and 
institutional-quality metrics.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union, Callable, Any
from datetime import datetime, timedelta
import warnings
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path

from .historical_data_manager import historical_data_manager
from .backtest_metrics import backtest_metrics
from .features import make_features
from .strategy import hybrid_signal, load_trading_model, FEATURES
from .sizing import volatility_target_size, kelly_cap
from .config import settings
from .util import logger

warnings.filterwarnings('ignore', category=FutureWarning)


class OrderType(Enum):
    """Order types supported by the backtesting engine."""
    MARKET = "market"
    LIMIT = "limit"


class OrderSide(Enum):
    """Order sides."""
    BUY = "buy"
    SELL = "sell"


@dataclass
class Position:
    """Represents an open position in the backtesting engine."""
    symbol: str
    side: OrderSide
    quantity: float
    entry_price: float
    entry_time: datetime
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    unrealized_pnl: float = 0.0
    
    def update_unrealized_pnl(self, current_price: float) -> None:
        """Update unrealized P&L based on current price."""
        if self.side == OrderSide.BUY:
            self.unrealized_pnl = (current_price - self.entry_price) * self.quantity
        else:  # SELL
            self.unrealized_pnl = (self.entry_price - current_price) * self.quantity


@dataclass
class Trade:
    """Represents a completed trade."""
    symbol: str
    side: OrderSide
    quantity: float
    entry_price: float
    exit_price: float
    entry_time: datetime
    exit_time: datetime
    commission: float = 0.0
    slippage: float = 0.0
    
    @property
    def gross_pnl(self) -> float:
        """Calculate gross P&L before costs."""
        if self.side == OrderSide.BUY:
            return (self.exit_price - self.entry_price) * self.quantity
        else:  # SELL
            return (self.entry_price - self.exit_price) * self.quantity
    
    @property
    def net_pnl(self) -> float:
        """Calculate net P&L after costs."""
        return self.gross_pnl - self.commission - self.slippage
    
    @property
    def return_pct(self) -> float:
        """Calculate percentage return."""
        cost_basis = self.entry_price * self.quantity
        return (self.net_pnl / cost_basis) if cost_basis > 0 else 0.0
    
    @property
    def duration_hours(self) -> float:
        """Calculate trade duration in hours."""
        return (self.exit_time - self.entry_time).total_seconds() / 3600


@dataclass
class BacktestConfig:
    """Configuration for backtesting engine."""
    initial_capital: float = 30000.0
    commission_rate: float = 0.001  # 0.1% per trade
    slippage_rate: float = 0.0005   # 0.05% slippage
    
    # Position sizing
    max_position_size: float = 0.2  # 20% of capital per position
    max_total_exposure: float = 1.0  # 100% total exposure
    
    # Risk management
    use_stop_loss: bool = True
    use_take_profit: bool = True
    stop_loss_pct: float = 0.02     # 2% stop loss
    take_profit_pct: float = 0.03   # 3% take profit
    
    # Trading constraints
    min_trade_size_usd: float = 100.0
    max_trades_per_day: int = 50
    
    # Data settings
    start_date: str = "2023-01-01"
    end_date: str = "2024-01-01"
    timeframe: str = "1Hour"
    symbols: List[str] = field(default_factory=lambda: ["BTC/USD", "ETH/USD", "SPY"])
    
    # Strategy settings
    lookback_periods: int = 100  # Minimum periods for strategy calculations


class BacktestingEngine:
    """
    Institutional-grade backtesting engine with realistic execution modeling.
    
    Features:
    - Event-driven simulation with realistic execution
    - Multi-symbol and multi-timeframe support
    - Comprehensive position and risk management
    - Transaction cost modeling (commission + slippage)
    - Performance tracking and metrics calculation
    - Extensive logging and debugging capabilities
    """
    
    def __init__(self, config: BacktestConfig):
        """
        Initialize backtesting engine.
        
        Args:
            config: Backtesting configuration
        """
        self.config = config
        self.current_time = None
        self.current_prices = {}
        
        # Portfolio state
        self.cash = config.initial_capital
        self.positions: Dict[str, Position] = {}
        self.completed_trades: List[Trade] = []
        
        # Performance tracking
        self.equity_curve = []
        self.returns_series = []
        self.drawdown_series = []
        self.timestamps = []
        
        # Strategy components
        self.model = None
        self.data_cache = {}
        self.features_cache = {}
        
        # Execution tracking
        self.trades_today = 0
        self.last_trade_date = None
        
        logger.info(f"🔄 Backtesting Engine initialized")
        logger.info(f"📊 Config: ${config.initial_capital:,.0f} capital, {len(config.symbols)} symbols")
    
    def load_model(self) -> bool:
        """Load the trading model for strategy execution."""
        try:
            self.model = load_trading_model()
            if self.model is not None:
                logger.info("✅ Trading model loaded successfully")
                return True
            else:
                logger.warning("⚠️ No trading model available - using rule-based only")
                return False
        except Exception as e:
            logger.error(f"❌ Failed to load trading model: {e}")
            return False
    
    def load_historical_data(self) -> Dict[str, pd.DataFrame]:
        """
        Load historical data for all symbols.
        
        Returns:
            Dictionary mapping symbols to DataFrames
        """
        logger.info(f"📡 Loading historical data for {len(self.config.symbols)} symbols...")
        
        data = historical_data_manager.load_multiple_symbols(
            symbols=self.config.symbols,
            start_date=self.config.start_date,
            end_date=self.config.end_date,
            timeframe=self.config.timeframe,
            max_workers=4
        )
        
        # Filter out empty datasets
        valid_data = {symbol: df for symbol, df in data.items() if not df.empty}
        
        logger.info(f"✅ Loaded data for {len(valid_data)}/{len(self.config.symbols)} symbols")
        
        # Cache the data
        self.data_cache = valid_data
        
        return valid_data
    
    def prepare_features(self, data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        Prepare features for all symbols.
        
        Args:
            data: Raw price data by symbol
            
        Returns:
            Features data by symbol
        """
        logger.info("🔧 Calculating features for all symbols...")
        
        features_data = {}
        
        for symbol, df in data.items():
            if len(df) < self.config.lookback_periods:
                logger.warning(f"⚠️ {symbol}: Insufficient data ({len(df)} < {self.config.lookback_periods})")
                continue
            
            try:
                # Calculate features using existing function
                features = make_features(df, symbol=symbol)
                
                if not features.empty and len(features) >= 50:  # Minimum for meaningful backtesting
                    features_data[symbol] = features
                    logger.debug(f"✅ {symbol}: {len(features)} feature rows calculated")
                else:
                    logger.warning(f"⚠️ {symbol}: Insufficient feature data ({len(features)} rows)")
                    
            except Exception as e:
                logger.error(f"❌ {symbol}: Feature calculation failed - {e}")
        
        logger.info(f"✅ Features prepared for {len(features_data)} symbols")
        
        # Cache features
        self.features_cache = features_data
        
        return features_data
    
    def get_signal(self, symbol: str, timestamp: datetime) -> float:
        """
        Get trading signal for symbol at given timestamp.
        
        Args:
            symbol: Symbol to get signal for
            timestamp: Current timestamp
            
        Returns:
            Signal strength (-1.0 to +1.0)
        """
        if symbol not in self.features_cache:
            return 0.0
        
        features_df = self.features_cache[symbol]
        
        # Find the row for current timestamp (or closest previous)
        try:
            # Use loc to get the exact timestamp or use iloc for index-based access
            if timestamp in features_df.index:
                row = features_df.loc[timestamp]
            else:
                # Find closest previous timestamp
                available_times = features_df.index[features_df.index <= timestamp]
                if len(available_times) == 0:
                    return 0.0
                
                closest_time = available_times[-1]
                row = features_df.loc[closest_time]
            
            # Get signal using existing strategy function
            signal = hybrid_signal(row, model=self.model, symbol=symbol)
            
            return float(signal)
            
        except Exception as e:
            logger.debug(f"⚠️ {symbol}: Signal calculation failed at {timestamp} - {e}")
            return 0.0
    
    def calculate_position_size(self, symbol: str, signal: float, current_price: float) -> float:
        """
        Calculate position size based on signal strength and risk management.
        
        Args:
            symbol: Symbol to trade
            signal: Signal strength (-1.0 to +1.0)
            current_price: Current price
            
        Returns:
            Position size in USD (positive for long, negative for short)
        """
        if abs(signal) < 0.1:  # Minimum signal threshold
            return 0.0
        
        # Current portfolio value
        portfolio_value = self.get_portfolio_value()
        
        if portfolio_value <= 0:
            return 0.0
        
        # Get features for ATR calculation
        if symbol not in self.features_cache:
            return 0.0
        
        features_df = self.features_cache[symbol]
        latest_features = features_df.iloc[-1]
        
        atr = latest_features.get('atr_14', current_price * 0.02)  # Default 2% ATR
        
        # Use volatility targeting
        base_size = volatility_target_size(
            equity=portfolio_value,
            price=current_price,
            atr=atr,
            risk_per_trade=settings.risk_per_trade
        )
        
        # Apply signal strength scaling
        adjusted_size = base_size * abs(signal)
        
        # Apply position size limits
        max_position_usd = portfolio_value * self.config.max_position_size
        position_usd = min(adjusted_size * current_price, max_position_usd)
        
        # Apply minimum trade size
        if position_usd < self.config.min_trade_size_usd:
            return 0.0
        
        # Check exposure limits
        total_exposure = self.get_total_exposure()
        if total_exposure + position_usd > portfolio_value * self.config.max_total_exposure:
            return 0.0
        
        # Return signed size (negative for short)
        position_size = position_usd / current_price
        return position_size if signal > 0 else -position_size
    
    def get_portfolio_value(self) -> float:
        """Calculate current portfolio value."""
        total_value = self.cash
        
        for position in self.positions.values():
            position.update_unrealized_pnl(self.current_prices.get(position.symbol, position.entry_price))
            total_value += position.entry_price * position.quantity + position.unrealized_pnl
        
        return total_value
    
    def get_total_exposure(self) -> float:
        """Calculate total exposure across all positions."""
        total_exposure = 0.0
        
        for position in self.positions.values():
            current_price = self.current_prices.get(position.symbol, position.entry_price)
            exposure = abs(position.quantity * current_price)
            total_exposure += exposure
        
        return total_exposure
    
    def execute_order(self, symbol: str, size: float, current_price: float, timestamp: datetime) -> bool:
        """
        Execute a market order with realistic execution modeling.
        
        Args:
            symbol: Symbol to trade
            size: Position size (positive=buy, negative=sell)
            current_price: Current market price
            timestamp: Order timestamp
            
        Returns:
            True if order executed successfully
        """
        if abs(size) < 1e-6:  # Minimum size threshold
            return False
        
        # Check daily trade limit
        if self.last_trade_date != timestamp.date():
            self.trades_today = 0
            self.last_trade_date = timestamp.date()
        
        if self.trades_today >= self.config.max_trades_per_day:
            logger.debug(f"📊 {symbol}: Daily trade limit reached ({self.trades_today})")
            return False
        
        side = OrderSide.BUY if size > 0 else OrderSide.SELL
        quantity = abs(size)
        
        # Calculate execution costs
        notional = quantity * current_price
        commission = notional * self.config.commission_rate
        slippage = notional * self.config.slippage_rate
        
        # Apply slippage to execution price
        if side == OrderSide.BUY:
            execution_price = current_price * (1 + self.config.slippage_rate)
        else:
            execution_price = current_price * (1 - self.config.slippage_rate)
        
        # Check if we have enough cash (for buys) or existing position (for sells)
        total_cost = quantity * execution_price + commission + slippage
        
        if side == OrderSide.BUY and total_cost > self.cash:
            logger.debug(f"💰 {symbol}: Insufficient cash for buy order (${total_cost:.2f} > ${self.cash:.2f})")
            return False
        
        # Check if we're closing an existing position or opening new one
        existing_position = self.positions.get(symbol)
        
        if existing_position:
            # Close existing position
            trade = Trade(
                symbol=symbol,
                side=existing_position.side,
                quantity=existing_position.quantity,
                entry_price=existing_position.entry_price,
                exit_price=execution_price,
                entry_time=existing_position.entry_time,
                exit_time=timestamp,
                commission=commission,
                slippage=slippage
            )
            
            # Add cash from closing position
            if existing_position.side == OrderSide.BUY:
                self.cash += existing_position.quantity * execution_price - commission - slippage
            else:
                self.cash += existing_position.quantity * (2 * existing_position.entry_price - execution_price) - commission - slippage
            
            self.completed_trades.append(trade)
            del self.positions[symbol]
            
            logger.debug(f"📊 {symbol}: Closed {existing_position.side.value} position - P&L: ${trade.net_pnl:.2f}")
        
        # Open new position if size is different from what we closed
        if not existing_position or (existing_position.side != side):
            # Calculate stop loss and take profit
            stop_loss = None
            take_profit = None
            
            if self.config.use_stop_loss:
                if side == OrderSide.BUY:
                    stop_loss = execution_price * (1 - self.config.stop_loss_pct)
                else:
                    stop_loss = execution_price * (1 + self.config.stop_loss_pct)
            
            if self.config.use_take_profit:
                if side == OrderSide.BUY:
                    take_profit = execution_price * (1 + self.config.take_profit_pct)
                else:
                    take_profit = execution_price * (1 - self.config.take_profit_pct)
            
            # Create new position
            position = Position(
                symbol=symbol,
                side=side,
                quantity=quantity,
                entry_price=execution_price,
                entry_time=timestamp,
                stop_loss=stop_loss,
                take_profit=take_profit
            )
            
            # Deduct cash for new position
            self.cash -= total_cost
            self.positions[symbol] = position
            
            logger.debug(f"📊 {symbol}: Opened {side.value} position - Size: {quantity:.6f} @ ${execution_price:.4f}")
        
        self.trades_today += 1
        return True
    
    def check_stop_loss_take_profit(self, timestamp: datetime) -> None:
        """Check and execute stop-loss and take-profit orders."""
        positions_to_close = []
        
        for symbol, position in self.positions.items():
            current_price = self.current_prices.get(symbol)
            if current_price is None:
                continue
            
            should_close = False
            close_reason = ""
            
            # Check stop-loss
            if position.stop_loss is not None:
                if position.side == OrderSide.BUY and current_price <= position.stop_loss:
                    should_close = True
                    close_reason = "stop-loss"
                elif position.side == OrderSide.SELL and current_price >= position.stop_loss:
                    should_close = True
                    close_reason = "stop-loss"
            
            # Check take-profit
            if position.take_profit is not None:
                if position.side == OrderSide.BUY and current_price >= position.take_profit:
                    should_close = True
                    close_reason = "take-profit"
                elif position.side == OrderSide.SELL and current_price <= position.take_profit:
                    should_close = True
                    close_reason = "take-profit"
            
            if should_close:
                positions_to_close.append((symbol, close_reason))
        
        # Execute closes
        for symbol, reason in positions_to_close:
            current_price = self.current_prices[symbol]
            position = self.positions[symbol]
            
            # Execute closing order
            if position.side == OrderSide.BUY:
                close_size = -position.quantity
            else:
                close_size = position.quantity
            
            success = self.execute_order(symbol, close_size, current_price, timestamp)
            if success:
                logger.debug(f"🎯 {symbol}: Position closed due to {reason}")
    
    def process_bar(self, timestamp: datetime, prices: Dict[str, float]) -> None:
        """
        Process a single bar of market data.
        
        Args:
            timestamp: Current timestamp
            prices: Current prices for all symbols
        """
        self.current_time = timestamp
        self.current_prices = prices.copy()
        
        # Check stop-loss and take-profit first
        self.check_stop_loss_take_profit(timestamp)
        
        # Generate signals and execute trades
        for symbol in self.config.symbols:
            if symbol not in prices:
                continue
            
            current_price = prices[symbol]
            signal = self.get_signal(symbol, timestamp)
            
            if abs(signal) > 0.1:  # Minimum signal threshold
                position_size = self.calculate_position_size(symbol, signal, current_price)
                
                if abs(position_size) > 0:
                    self.execute_order(symbol, position_size, current_price, timestamp)
        
        # Update portfolio tracking
        portfolio_value = self.get_portfolio_value()
        self.equity_curve.append(portfolio_value)
        self.timestamps.append(timestamp)
        
        # Calculate returns
        if len(self.equity_curve) > 1:
            ret = (portfolio_value / self.equity_curve[-2]) - 1
            self.returns_series.append(ret)
        else:
            self.returns_series.append(0.0)
        
        # Calculate drawdown
        peak_value = max(self.equity_curve)
        current_dd = (portfolio_value / peak_value - 1) if peak_value > 0 else 0
        self.drawdown_series.append(current_dd)
    
    def run_backtest(self) -> Dict[str, Any]:
        """
        Run the complete backtest.
        
        Returns:
            Dictionary with backtest results and metrics
        """
        logger.info("🚀 Starting backtesting engine...")
        
        # Step 1: Load model
        model_loaded = self.load_model()
        
        # Step 2: Load historical data
        data = self.load_historical_data()
        if not data:
            raise ValueError("No historical data available for backtesting")
        
        # Step 3: Prepare features
        features_data = self.prepare_features(data)
        if not features_data:
            raise ValueError("No features could be calculated")
        
        # Step 4: Find common time range across all symbols
        all_timestamps = set()
        for symbol_features in features_data.values():
            all_timestamps.update(symbol_features.index)
        
        common_timestamps = sorted(all_timestamps)
        
        if len(common_timestamps) < 100:
            raise ValueError(f"Insufficient common timestamps: {len(common_timestamps)}")
        
        logger.info(f"📊 Backtesting period: {common_timestamps[0]} to {common_timestamps[-1]}")
        logger.info(f"📊 Total bars to process: {len(common_timestamps)}")
        
        # Step 5: Run simulation
        progress_interval = max(1, len(common_timestamps) // 20)  # 5% progress updates
        
        for i, timestamp in enumerate(common_timestamps):
            # Get current prices for all symbols
            current_prices = {}
            
            for symbol in self.config.symbols:
                if symbol in features_data:
                    symbol_data = features_data[symbol]
                    if timestamp in symbol_data.index:
                        current_prices[symbol] = symbol_data.loc[timestamp, 'close']
                    else:
                        # Use forward-fill for missing data
                        available_times = symbol_data.index[symbol_data.index <= timestamp]
                        if len(available_times) > 0:
                            closest_time = available_times[-1]
                            current_prices[symbol] = symbol_data.loc[closest_time, 'close']
            
            if current_prices:  # Only process if we have price data
                self.process_bar(timestamp, current_prices)
            
            # Progress reporting
            if i % progress_interval == 0 or i == len(common_timestamps) - 1:
                progress = (i + 1) / len(common_timestamps) * 100
                portfolio_value = self.get_portfolio_value()
                logger.info(f"📊 Progress: {progress:.1f}% - Portfolio: ${portfolio_value:,.2f}")
        
        # Step 6: Close all remaining positions
        final_timestamp = common_timestamps[-1]
        for symbol, position in list(self.positions.items()):
            if symbol in self.current_prices:
                current_price = self.current_prices[symbol]
                if position.side == OrderSide.BUY:
                    close_size = -position.quantity
                else:
                    close_size = position.quantity
                
                self.execute_order(symbol, close_size, current_price, final_timestamp)
        
        # Step 7: Generate results
        results = self.generate_results()
        
        logger.info("✅ Backtest completed successfully")
        
        return results
    
    def generate_results(self) -> Dict[str, Any]:
        """Generate comprehensive backtest results."""
        
        # Create equity curve DataFrame
        equity_df = pd.Series(self.equity_curve, index=self.timestamps)
        
        # Create trades DataFrame
        trades_data = []
        for trade in self.completed_trades:
            trades_data.append({
                'symbol': trade.symbol,
                'side': trade.side.value,
                'quantity': trade.quantity,
                'entry_price': trade.entry_price,
                'exit_price': trade.exit_price,
                'entry_time': trade.entry_time,
                'exit_time': trade.exit_time,
                'gross_pnl': trade.gross_pnl,
                'net_pnl': trade.net_pnl,
                'return_pct': trade.return_pct,
                'duration_hours': trade.duration_hours,
                'commission': trade.commission,
                'slippage': trade.slippage
            })
        
        trades_df = pd.DataFrame(trades_data) if trades_data else pd.DataFrame()
        
        # Calculate comprehensive metrics
        metrics = backtest_metrics.comprehensive_metrics(
            equity_curve=equity_df,
            trades_df=trades_df
        )
        
        # Additional backtest-specific metrics
        final_value = self.equity_curve[-1] if self.equity_curve else self.config.initial_capital
        total_return = (final_value / self.config.initial_capital - 1) * 100
        
        results = {
            'config': {
                'initial_capital': self.config.initial_capital,
                'start_date': self.config.start_date,
                'end_date': self.config.end_date,
                'timeframe': self.config.timeframe,
                'symbols': self.config.symbols,
                'commission_rate': self.config.commission_rate,
                'slippage_rate': self.config.slippage_rate
            },
            'performance': {
                'initial_capital': self.config.initial_capital,
                'final_value': final_value,
                'total_return_pct': total_return,
                'total_trades': len(self.completed_trades),
                'avg_trades_per_day': len(self.completed_trades) / max(1, len(set(t.entry_time.date() for t in self.completed_trades))),
            },
            'metrics': metrics,
            'equity_curve': equity_df.to_dict(),
            'trades': trades_df.to_dict('records') if not trades_df.empty else [],
            'returns_series': pd.Series(self.returns_series, index=self.timestamps[1:]).to_dict(),
            'drawdown_series': pd.Series(self.drawdown_series, index=self.timestamps).to_dict()
        }
        
        return results
    
    def save_results(self, results: Dict[str, Any], filepath: Union[str, Path]) -> None:
        """Save backtest results to file."""
        # Convert any non-serializable types
        serializable_results = self._make_serializable(results)
        
        filepath_obj = Path(filepath)
        filepath_obj.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath_obj, 'w') as f:
            json.dump(serializable_results, f, indent=2, default=str)
        
        logger.info(f"💾 Results saved to {filepath_obj}")
    
    def _make_serializable(self, obj: Any) -> Any:
        """Convert object to JSON-serializable format."""
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif pd.isna(obj):
            return None
        else:
            return obj


def run_backtest(
    symbols: Optional[List[str]] = None,
    start_date: str = "2023-01-01",
    end_date: str = "2024-01-01",
    timeframe: str = "1Hour",
    initial_capital: float = 30000.0,
    save_results: bool = True
) -> Dict[str, Any]:
    """
    Convenience function to run a backtest with default settings.
    
    Args:
        symbols: List of symbols to test (default: first 5 from config)
        start_date: Start date string
        end_date: End date string  
        timeframe: Timeframe string
        initial_capital: Initial capital amount
        save_results: Whether to save results to file
        
    Returns:
        Backtest results dictionary
    """
    if symbols is None:
        symbols = settings.symbols[:5]  # Use first 5 symbols as default
    
    # Create configuration
    config = BacktestConfig(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        timeframe=timeframe,
        initial_capital=initial_capital
    )
    
    # Create and run engine
    engine = BacktestingEngine(config)
    results = engine.run_backtest()
    
    # Save results if requested
    if save_results:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backtest_results_{timestamp}.json"
        filepath = Path("results") / filename
        engine.save_results(results, str(filepath))
    
    return results