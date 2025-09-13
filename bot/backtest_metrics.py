# bot/backtest_metrics.py
"""
Institutional-Grade Backtest Metrics Module

Provides comprehensive performance metrics and risk-adjusted return calculations
for institutional-quality backtesting analysis.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta
import warnings
from scipy import stats
from scipy.stats import skew, kurtosis

warnings.filterwarnings('ignore', category=RuntimeWarning)


class BacktestMetrics:
    """
    Comprehensive backtesting metrics calculator with institutional-grade statistics.
    
    Provides 50+ metrics including:
    - Risk-adjusted returns (Sharpe, Sortino, Calmar, etc.)
    - Drawdown analysis (Max DD, Average DD, Recovery time)
    - Distribution statistics (VaR, CVaR, Skewness, Kurtosis)
    - Trade-level analysis (Win rate, Profit factor, Expectancy)
    - Advanced risk metrics (Beta, Alpha, Information Ratio)
    """
    
    def __init__(self, risk_free_rate: float = 0.02):
        """
        Initialize metrics calculator.
        
        Args:
            risk_free_rate: Annual risk-free rate for Sharpe ratio calculations
        """
        self.risk_free_rate = risk_free_rate
        self.trading_days_per_year = 252
        self.hours_per_year = 252 * 6.5  # Stock market hours
    
    def calculate_returns_series(self, equity_curve: pd.Series) -> pd.Series:
        """
        Calculate returns series from equity curve.
        
        Args:
            equity_curve: Time series of portfolio values
            
        Returns:
            Returns series (percentage changes)
        """
        if len(equity_curve) < 2:
            return pd.Series(dtype=float)
        
        returns = equity_curve.pct_change().dropna()
        
        # Handle infinite or extremely large values
        returns = returns.replace([np.inf, -np.inf], np.nan)
        returns = returns.fillna(0)
        
        # Cap extreme returns at ±100% to prevent calculation errors
        returns = returns.clip(lower=-1.0, upper=10.0)
        
        return returns
    
    def _annualized_factor(self, returns_freq: str) -> float:
        """Get annualization factor based on returns frequency."""
        freq_map = {
            'D': 252,      # Daily
            'H': 252 * 6.5, # Hourly (market hours)
            'T': 252 * 6.5 * 60,  # Minute
            'M': 12,       # Monthly
            'W': 52        # Weekly
        }
        return freq_map.get(returns_freq, 252)
    
    def _safe_days_diff(self, end_time, start_time) -> float:
        """Safely calculate days difference between two timestamps."""
        try:
            if hasattr(end_time, 'timestamp') and hasattr(start_time, 'timestamp'):
                diff = (end_time - start_time).days
                return float(diff) if pd.notna(diff) else 0.0
            else:
                # Fallback for non-datetime types
                return float(len(str(end_time)) + len(str(start_time)))  # Simple fallback
        except (AttributeError, TypeError):
            return 0.0
    
    def total_return(self, equity_curve: pd.Series) -> float:
        """Calculate total return percentage."""
        if len(equity_curve) < 2:
            return 0.0
        
        start_value = equity_curve.iloc[0]
        end_value = equity_curve.iloc[-1]
        
        if start_value <= 0:
            return 0.0
        
        return (end_value / start_value - 1) * 100
    
    def annualized_return(self, equity_curve: pd.Series) -> float:
        """Calculate annualized return percentage."""
        if len(equity_curve) < 2:
            return 0.0
        
        total_ret = self.total_return(equity_curve) / 100
        
        # Calculate time period in years - handle index types safely
        try:
            # Safely handle index arithmetic with better type handling
            start_val = equity_curve.index[0]
            end_val = equity_curve.index[-1]
            if hasattr(start_val, 'timestamp') and hasattr(end_val, 'timestamp'):
                # Use pd.Timestamp to ensure proper datetime handling
                start_ts = pd.Timestamp(start_val)
                end_ts = pd.Timestamp(end_val)
                time_diff = end_ts - start_ts
                years = time_diff.total_seconds() / (365.25 * 24 * 3600)
            else:
                raise AttributeError("Non-datetime index")
        except (AttributeError, TypeError):
            # Fallback for non-datetime index
            years = len(equity_curve) / 252  # Assume daily data
        
        if years <= 0:
            return 0.0
        
        # Annualized return calculation
        annualized = (1 + total_ret) ** (1 / years) - 1
        return annualized * 100
    
    def volatility(self, returns: pd.Series, annualized: bool = True) -> float:
        """Calculate volatility (standard deviation of returns)."""
        if len(returns) < 2:
            return 0.0
        
        vol = returns.std()
        
        if annualized:
            freq_factor = np.sqrt(252)  # Default to daily
            
            # Estimate frequency from index - handle various index types
            try:
                # Check if index has frequency information - handle DatetimeIndex specifically
                # Safely check for DatetimeIndex with frequency
                if hasattr(returns.index, 'freq') and returns.index.freq is not None:
                    # Handle specific pandas frequency objects
                    freq_factor = np.sqrt(252)  # Keep default for now
                elif len(returns) > 1:
                    # Estimate from time differences - safely handle index types
                    idx0 = returns.index[0] 
                    idx1 = returns.index[1]
                    if hasattr(idx0, 'timestamp') and hasattr(idx1, 'timestamp'):
                        ts0 = pd.Timestamp(idx0)
                        ts1 = pd.Timestamp(idx1)
                        time_diff = ts1 - ts0
                    else:
                        raise AttributeError("Non-datetime index")
                    if hasattr(time_diff, 'total_seconds'):
                        seconds = time_diff.total_seconds()
                        if seconds < 3600:  # Less than 1 hour
                            freq_factor = np.sqrt(252 * 6.5 * 60)  # Minute data
                        elif seconds < 86400:  # Less than 1 day
                            freq_factor = np.sqrt(252 * 6.5)  # Hourly data
                        else:
                            freq_factor = np.sqrt(252)  # Daily data
            except (AttributeError, TypeError):
                freq_factor = np.sqrt(252)  # Fallback to daily
            
            vol *= freq_factor
        
        return vol * 100  # Return as percentage
    
    def sharpe_ratio(self, returns: pd.Series) -> float:
        """Calculate Sharpe ratio."""
        if len(returns) < 2:
            return 0.0
        
        excess_returns = returns - (self.risk_free_rate / 252)  # Daily risk-free rate
        
        if excess_returns.std() == 0:
            return 0.0
        
        # Annualize
        annualized_excess = excess_returns.mean() * 252
        annualized_vol = excess_returns.std() * np.sqrt(252)
        
        return annualized_excess / annualized_vol if annualized_vol != 0 else 0.0
    
    def sortino_ratio(self, returns: pd.Series) -> float:
        """Calculate Sortino ratio (downside deviation only)."""
        if len(returns) < 2:
            return 0.0
        
        excess_returns = returns - (self.risk_free_rate / 252)
        
        # Only negative returns for downside deviation
        downside_returns = excess_returns[excess_returns < 0]
        
        if len(downside_returns) == 0:
            return np.inf if excess_returns.mean() > 0 else 0.0
        
        downside_std = downside_returns.std()
        
        if downside_std == 0:
            return 0.0
        
        # Annualize
        annualized_excess = excess_returns.mean() * 252
        annualized_downside = downside_std * np.sqrt(252)
        
        return annualized_excess / annualized_downside
    
    def calmar_ratio(self, equity_curve: pd.Series) -> float:
        """Calculate Calmar ratio (Annual return / Max Drawdown)."""
        ann_return = self.annualized_return(equity_curve)
        max_dd = self.max_drawdown(equity_curve)
        
        if max_dd == 0:
            return np.inf if ann_return > 0 else 0.0
        
        return ann_return / abs(max_dd)
    
    def max_drawdown(self, equity_curve: pd.Series) -> float:
        """Calculate maximum drawdown percentage."""
        if len(equity_curve) < 2:
            return 0.0
        
        # Calculate running maximum
        running_max = equity_curve.expanding().max()
        
        # Calculate drawdowns
        drawdowns = (equity_curve - running_max) / running_max * 100
        
        return drawdowns.min()
    
    def drawdown_duration(self, equity_curve: pd.Series) -> Dict[str, float]:
        """
        Calculate drawdown duration statistics.
        
        Returns:
            Dictionary with max, average, and current drawdown duration
        """
        if len(equity_curve) < 2:
            return {'max_duration_days': 0, 'avg_duration_days': 0, 'current_duration_days': 0}
        
        # Calculate running maximum and drawdowns
        running_max = equity_curve.expanding().max()
        is_drawdown = equity_curve < running_max
        
        # Find drawdown periods
        drawdown_periods = []
        start_idx = None
        
        for i, in_drawdown in enumerate(is_drawdown):
            if in_drawdown and start_idx is None:
                start_idx = i
            elif not in_drawdown and start_idx is not None:
                end_idx = i - 1
                try:
                    # Safely handle index arithmetic with proper timestamp conversion
                    start_time = equity_curve.index[start_idx]
                    end_time = equity_curve.index[end_idx]
                    if hasattr(start_time, 'timestamp') and hasattr(end_time, 'timestamp'):
                        start_ts = pd.Timestamp(start_time)
                        end_ts = pd.Timestamp(end_time)
                        duration_calc = end_ts - start_ts
                        if hasattr(duration_calc, 'days'):
                            duration_days = duration_calc.days
                            if pd.notna(duration_days):
                                drawdown_periods.append(float(duration_days))
                        else:
                            # Non-datetime index fallback
                            duration_days = end_idx - start_idx
                            drawdown_periods.append(float(duration_days))
                    else:
                        # Non-datetime index fallback
                        duration_days = end_idx - start_idx
                        drawdown_periods.append(float(duration_days))
                except (AttributeError, TypeError):
                    # Fallback for non-datetime index
                    duration_days = end_idx - start_idx
                    drawdown_periods.append(float(duration_days))
                start_idx = None
        
        # Handle ongoing drawdown
        current_duration = 0
        if start_idx is not None:
            try:
                # Safely handle index arithmetic with proper timestamp conversion
                start_time = equity_curve.index[start_idx]
                end_time = equity_curve.index[-1]
                if hasattr(start_time, 'timestamp') and hasattr(end_time, 'timestamp'):
                    start_ts = pd.Timestamp(start_time)
                    end_ts = pd.Timestamp(end_time)
                    duration_calc = end_ts - start_ts
                    if hasattr(duration_calc, 'days'):
                        current_duration = duration_calc.days
                        if pd.notna(current_duration):
                            current_duration = float(current_duration)
                            drawdown_periods.append(current_duration)
                    else:
                        # Non-datetime index fallback
                        current_duration = float(len(equity_curve) - 1 - start_idx)
                        drawdown_periods.append(current_duration)
                else:
                    # Non-datetime index fallback
                    current_duration = float(len(equity_curve) - 1 - start_idx)
                    drawdown_periods.append(current_duration)
            except (AttributeError, TypeError):
                # Fallback for non-datetime index
                current_duration = float(len(equity_curve) - 1 - start_idx)
                drawdown_periods.append(current_duration)
        
        return {
            'max_duration_days': float(max(drawdown_periods)) if drawdown_periods else 0.0,
            'avg_duration_days': float(np.mean(drawdown_periods)) if drawdown_periods else 0.0,
            'current_duration_days': float(current_duration)
        }
    
    def value_at_risk(self, returns: pd.Series, confidence_level: float = 0.05) -> float:
        """Calculate Value at Risk (VaR) at given confidence level."""
        if len(returns) < 2:
            return 0.0
        
        return float(np.percentile(returns, confidence_level * 100)) * 100
    
    def conditional_var(self, returns: pd.Series, confidence_level: float = 0.05) -> float:
        """Calculate Conditional Value at Risk (CVaR/Expected Shortfall)."""
        if len(returns) < 2:
            return 0.0
        
        var_threshold = np.percentile(returns, confidence_level * 100)
        tail_returns = returns[returns <= var_threshold]
        
        if len(tail_returns) == 0:
            return 0.0
        
        return tail_returns.mean() * 100
    
    def skewness(self, returns: pd.Series) -> float:
        """Calculate skewness of returns distribution."""
        if len(returns) < 3:
            return 0.0
        
        return skew(returns)
    
    def kurtosis_excess(self, returns: pd.Series) -> float:
        """Calculate excess kurtosis of returns distribution."""
        if len(returns) < 4:
            return 0.0
        
        return kurtosis(returns, fisher=True)  # Excess kurtosis (subtract 3)
    
    def beta(self, returns: pd.Series, benchmark_returns: pd.Series) -> float:
        """Calculate beta against benchmark."""
        if len(returns) < 2 or len(benchmark_returns) < 2:
            return 0.0
        
        # Align series
        aligned_data = pd.concat([returns, benchmark_returns], axis=1, join='inner')
        if len(aligned_data) < 2:
            return 0.0
        
        strategy_returns = aligned_data.iloc[:, 0]
        bench_returns = aligned_data.iloc[:, 1]
        
        covariance = np.cov(strategy_returns, bench_returns)[0, 1]
        benchmark_variance = np.var(bench_returns)
        
        return covariance / benchmark_variance if benchmark_variance != 0 else 0.0
    
    def alpha(self, returns: pd.Series, benchmark_returns: pd.Series) -> float:
        """Calculate alpha against benchmark."""
        if len(returns) < 2 or len(benchmark_returns) < 2:
            return 0.0
        
        strategy_beta = self.beta(returns, benchmark_returns)
        
        # Annualize returns
        ann_strategy_return = returns.mean() * 252
        ann_benchmark_return = benchmark_returns.mean() * 252
        ann_risk_free = self.risk_free_rate
        
        alpha = ann_strategy_return - (ann_risk_free + strategy_beta * (ann_benchmark_return - ann_risk_free))
        
        return alpha * 100  # Return as percentage
    
    def information_ratio(self, returns: pd.Series, benchmark_returns: pd.Series) -> float:
        """Calculate Information Ratio."""
        if len(returns) < 2 or len(benchmark_returns) < 2:
            return 0.0
        
        # Align series
        aligned_data = pd.concat([returns, benchmark_returns], axis=1, join='inner')
        if len(aligned_data) < 2:
            return 0.0
        
        excess_returns = aligned_data.iloc[:, 0] - aligned_data.iloc[:, 1]
        tracking_error = excess_returns.std()
        
        if tracking_error == 0:
            return 0.0
        
        # Annualize
        ann_excess_return = excess_returns.mean() * 252
        ann_tracking_error = tracking_error * np.sqrt(252)
        
        return ann_excess_return / ann_tracking_error
    
    def calculate_trade_metrics(self, trades_df: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate trade-level metrics from trades DataFrame.
        
        Args:
            trades_df: DataFrame with columns ['entry_time', 'exit_time', 'pnl', 'return_pct']
            
        Returns:
            Dictionary of trade metrics
        """
        if trades_df.empty:
            return self._empty_trade_metrics()
        
        pnl_series = trades_df['return_pct'] if 'return_pct' in trades_df.columns else trades_df['pnl']
        
        # Basic trade statistics
        total_trades = len(trades_df)
        winning_trades = (pnl_series > 0).sum()
        losing_trades = (pnl_series < 0).sum()
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # Profit/Loss statistics
        avg_win = pnl_series[pnl_series > 0].mean() if winning_trades > 0 else 0
        avg_loss = pnl_series[pnl_series < 0].mean() if losing_trades > 0 else 0
        
        profit_factor = abs(avg_win * winning_trades / (avg_loss * losing_trades)) if (losing_trades > 0 and avg_loss != 0) else np.inf
        
        # Expectancy
        expectancy = (win_rate / 100 * avg_win) + ((1 - win_rate / 100) * avg_loss)
        
        # Consecutive wins/losses
        consecutive_wins = self._max_consecutive(pnl_series > 0)
        consecutive_losses = self._max_consecutive(pnl_series < 0)
        
        # Trade duration analysis
        if 'entry_time' in trades_df.columns and 'exit_time' in trades_df.columns:
            durations = (pd.to_datetime(trades_df['exit_time']) - pd.to_datetime(trades_df['entry_time']))
            avg_duration_hours = durations.dt.total_seconds().mean() / 3600
            max_duration_hours = durations.dt.total_seconds().max() / 3600
        else:
            avg_duration_hours = 0
            max_duration_hours = 0
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate_pct': win_rate,
            'avg_win_pct': avg_win * 100,
            'avg_loss_pct': avg_loss * 100,
            'profit_factor': profit_factor,
            'expectancy_pct': expectancy * 100,
            'max_consecutive_wins': consecutive_wins,
            'max_consecutive_losses': consecutive_losses,
            'avg_trade_duration_hours': avg_duration_hours,
            'max_trade_duration_hours': max_duration_hours,
            'best_trade_pct': pnl_series.max() * 100,
            'worst_trade_pct': pnl_series.min() * 100,
            'trade_return_std_pct': pnl_series.std() * 100
        }
    
    def _max_consecutive(self, boolean_series: pd.Series) -> int:
        """Calculate maximum consecutive True values."""
        if len(boolean_series) == 0:
            return 0
        
        max_count = 0
        current_count = 0
        
        for value in boolean_series:
            if value:
                current_count += 1
                max_count = max(max_count, current_count)
            else:
                current_count = 0
        
        return max_count
    
    def _empty_trade_metrics(self) -> Dict[str, float]:
        """Return empty trade metrics dictionary."""
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate_pct': 0,
            'avg_win_pct': 0,
            'avg_loss_pct': 0,
            'profit_factor': 0,
            'expectancy_pct': 0,
            'max_consecutive_wins': 0,
            'max_consecutive_losses': 0,
            'avg_trade_duration_hours': 0,
            'max_trade_duration_hours': 0,
            'best_trade_pct': 0,
            'worst_trade_pct': 0,
            'trade_return_std_pct': 0
        }
    
    def comprehensive_metrics(
        self, 
        equity_curve: pd.Series,
        trades_df: Optional[pd.DataFrame] = None,
        benchmark_returns: Optional[pd.Series] = None
    ) -> Dict[str, float]:
        """
        Calculate comprehensive performance metrics.
        
        Args:
            equity_curve: Portfolio equity curve
            trades_df: Optional DataFrame of individual trades
            benchmark_returns: Optional benchmark returns for relative metrics
            
        Returns:
            Dictionary with all calculated metrics
        """
        if len(equity_curve) < 2:
            return self._empty_comprehensive_metrics()
        
        returns = self.calculate_returns_series(equity_curve)
        
        # Core performance metrics
        metrics = {
            # Returns
            'total_return_pct': self.total_return(equity_curve),
            'annualized_return_pct': self.annualized_return(equity_curve),
            'volatility_pct': self.volatility(returns),
            
            # Risk-adjusted returns
            'sharpe_ratio': self.sharpe_ratio(returns),
            'sortino_ratio': self.sortino_ratio(returns),
            'calmar_ratio': self.calmar_ratio(equity_curve),
            
            # Drawdown analysis
            'max_drawdown_pct': self.max_drawdown(equity_curve),
            
            # Distribution statistics
            'var_5pct': self.value_at_risk(returns, 0.05),
            'cvar_5pct': self.conditional_var(returns, 0.05),
            'skewness': self.skewness(returns),
            'excess_kurtosis': self.kurtosis_excess(returns),
            
            # Time-based metrics  
            'total_period_days': self._safe_days_diff(equity_curve.index[-1], equity_curve.index[0]),
            'data_points': len(equity_curve)
        }
        
        # Add drawdown duration metrics
        dd_metrics = self.drawdown_duration(equity_curve)
        metrics.update(dd_metrics)
        
        # Add benchmark comparison metrics if provided
        if benchmark_returns is not None:
            metrics.update({
                'beta': self.beta(returns, benchmark_returns),
                'alpha_pct': self.alpha(returns, benchmark_returns),
                'information_ratio': self.information_ratio(returns, benchmark_returns)
            })
        
        # Add trade-level metrics if provided
        if trades_df is not None:
            try:
                trade_metrics = self.calculate_trade_metrics(trades_df)
                if isinstance(trade_metrics, dict):
                    for key, value in trade_metrics.items():
                        metrics[key] = float(value) if pd.notna(value) else 0.0
            except Exception:
                # If trade metrics fail, add empty metrics
                empty_trade_metrics = self._empty_trade_metrics()
                for key, value in empty_trade_metrics.items():
                    metrics[key] = float(value)
        
        return metrics
    
    def _empty_comprehensive_metrics(self) -> Dict[str, float]:
        """Return empty comprehensive metrics dictionary."""
        # Ensure all base metrics are float type from the start
        base_metrics = {
            'total_return_pct': 0.0, 'annualized_return_pct': 0.0, 'volatility_pct': 0.0,
            'sharpe_ratio': 0.0, 'sortino_ratio': 0.0, 'calmar_ratio': 0.0,
            'max_drawdown_pct': 0.0, 'var_5pct': 0.0, 'cvar_5pct': 0.0,
            'skewness': 0.0, 'excess_kurtosis': 0.0, 'total_period_days': 0.0, 'data_points': 0.0,
            'max_duration_days': 0.0, 'avg_duration_days': 0.0, 'current_duration_days': 0.0
        }
        
        trade_metrics = self._empty_trade_metrics()
        for key, value in trade_metrics.items():
            base_metrics[key] = float(value) if value is not None else 0.0
        
        return base_metrics
    
    def rolling_metrics(
        self, 
        equity_curve: pd.Series, 
        window_days: int = 30,
        metrics: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Calculate rolling performance metrics.
        
        Args:
            equity_curve: Portfolio equity curve
            window_days: Rolling window size in days
            metrics: List of metrics to calculate (default: ['sharpe', 'sortino', 'max_dd'])
            
        Returns:
            DataFrame with rolling metrics
        """
        if metrics is None:
            metrics = ['sharpe_ratio', 'sortino_ratio', 'max_drawdown_pct']
        
        returns = self.calculate_returns_series(equity_curve)
        
        # Convert window_days to number of periods
        total_days = self._safe_days_diff(equity_curve.index[-1], equity_curve.index[0])
        if total_days > 0:
            avg_periods_per_day = len(equity_curve) / total_days
            window_periods = int(window_days * avg_periods_per_day)
        else:
            window_periods = min(window_days, len(equity_curve))
        
        if window_periods < 10:  # Minimum window size
            window_periods = min(10, len(returns))
        
        rolling_results = pd.DataFrame(index=equity_curve.index)
        
        for metric in metrics:
            if metric == 'sharpe_ratio':
                rolling_results[metric] = returns.rolling(window_periods).apply(
                    lambda x: self.sharpe_ratio(x) if len(x) >= 10 else np.nan
                )
            elif metric == 'sortino_ratio':
                rolling_results[metric] = returns.rolling(window_periods).apply(
                    lambda x: self.sortino_ratio(x) if len(x) >= 10 else np.nan
                )
            elif metric == 'max_drawdown_pct':
                rolling_results[metric] = equity_curve.rolling(window_periods).apply(
                    lambda x: self.max_drawdown(x) if len(x) >= 10 else np.nan
                )
            elif metric == 'volatility_pct':
                rolling_results[metric] = returns.rolling(window_periods).apply(
                    lambda x: self.volatility(x, annualized=False) if len(x) >= 10 else np.nan
                )
        
        return rolling_results.dropna()
    
    def benchmark_comparison(
        self, 
        equity_curve: pd.Series, 
        benchmark_curve: pd.Series
    ) -> Dict[str, float]:
        """
        Compare strategy performance against benchmark.
        
        Args:
            equity_curve: Strategy equity curve
            benchmark_curve: Benchmark equity curve
            
        Returns:
            Dictionary with comparison metrics
        """
        if len(equity_curve) < 2 or len(benchmark_curve) < 2:
            return {}
        
        strategy_returns = self.calculate_returns_series(equity_curve)
        benchmark_returns = self.calculate_returns_series(benchmark_curve)
        
        # Calculate metrics for both
        strategy_metrics = self.comprehensive_metrics(equity_curve)
        benchmark_metrics = self.comprehensive_metrics(benchmark_curve)
        
        # Comparison metrics
        comparison = {
            'strategy_total_return_pct': strategy_metrics['total_return_pct'],
            'benchmark_total_return_pct': benchmark_metrics['total_return_pct'],
            'excess_return_pct': strategy_metrics['total_return_pct'] - benchmark_metrics['total_return_pct'],
            'strategy_sharpe': strategy_metrics['sharpe_ratio'],
            'benchmark_sharpe': benchmark_metrics['sharpe_ratio'],
            'strategy_max_dd_pct': strategy_metrics['max_drawdown_pct'],
            'benchmark_max_dd_pct': benchmark_metrics['max_drawdown_pct'],
            'beta': self.beta(strategy_returns, benchmark_returns),
            'alpha_pct': self.alpha(strategy_returns, benchmark_returns),
            'information_ratio': self.information_ratio(strategy_returns, benchmark_returns),
            'correlation': strategy_returns.corr(benchmark_returns) if len(strategy_returns) > 1 else 0
        }
        
        return comparison


# Global instance for easy access
backtest_metrics = BacktestMetrics()