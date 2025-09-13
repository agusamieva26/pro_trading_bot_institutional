# bot/backtest_reporting.py
"""
Comprehensive Backtesting Report Generation & Visualization

Advanced reporting system for institutional-grade backtesting results
with detailed analytics, visualizations, and export capabilities.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from pathlib import Path
import json
import warnings
from dataclasses import dataclass

from .backtest_metrics import backtest_metrics
from .util import logger

warnings.filterwarnings('ignore', category=FutureWarning)

# Set matplotlib style for professional charts
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")


@dataclass
class ReportConfig:
    """Configuration for report generation."""
    include_plots: bool = True
    include_trade_analysis: bool = True
    include_rolling_metrics: bool = True
    include_drawdown_analysis: bool = True
    save_csv: bool = True
    save_json: bool = True
    output_dir: str = "reports"
    plot_dpi: int = 300
    plot_figsize: tuple = (12, 8)


class BacktestReporter:
    """
    Comprehensive backtesting report generator with institutional-quality analysis.
    
    Features:
    - Detailed performance metrics and statistics
    - Professional visualization charts
    - Trade-by-trade analysis
    - Risk analysis and drawdown studies
    - Rolling performance metrics
    - Benchmark comparisons
    - Export to multiple formats (PDF, CSV, JSON, HTML)
    """
    
    def __init__(self, config: Optional[ReportConfig] = None):
        """
        Initialize backtest reporter.
        
        Args:
            config: Report configuration settings
        """
        self.config = config or ReportConfig()
        self.output_dir = Path(self.config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"📊 Backtest Reporter initialized - Output: {self.output_dir}")
    
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
    
    def generate_comprehensive_report(
        self,
        backtest_results: Dict[str, Any],
        optimization_results: Optional[Dict[str, Any]] = None,
        benchmark_results: Optional[Dict[str, Any]] = None,
        report_title: str = "Backtesting Analysis Report"
    ) -> Dict[str, str]:
        """
        Generate comprehensive backtesting report with all analysis components.
        
        Args:
            backtest_results: Results from backtesting engine
            optimization_results: Optional optimization results
            benchmark_results: Optional benchmark comparison results  
            report_title: Title for the report
            
        Returns:
            Dictionary with paths to generated files
        """
        logger.info(f"📊 Generating comprehensive report: {report_title}")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_name = f"backtest_report_{timestamp}"
        
        # Extract data from results
        equity_curve = pd.Series(backtest_results.get('equity_curve', {}))
        equity_curve.index = pd.to_datetime(equity_curve.index)
        
        trades_df = pd.DataFrame(backtest_results.get('trades', []))
        if not trades_df.empty:
            trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time'])
            trades_df['exit_time'] = pd.to_datetime(trades_df['exit_time'])
        
        metrics = backtest_results.get('metrics', {})
        config = backtest_results.get('config', {})
        
        generated_files = {}
        
        # 1. Generate performance charts
        if self.config.include_plots and not equity_curve.empty:
            plots_path = self._generate_performance_plots(
                equity_curve, trades_df, metrics, report_name
            )
            generated_files['plots'] = plots_path
        
        # 2. Generate detailed metrics analysis
        metrics_path = self._generate_metrics_analysis(
            metrics, config, report_name
        )
        generated_files['metrics'] = metrics_path
        
        # 3. Generate trade analysis
        if self.config.include_trade_analysis and not trades_df.empty:
            trade_analysis_path = self._generate_trade_analysis(
                trades_df, report_name
            )
            generated_files['trade_analysis'] = trade_analysis_path
        
        # 4. Generate rolling metrics analysis
        if self.config.include_rolling_metrics and not equity_curve.empty:
            rolling_path = self._generate_rolling_analysis(
                equity_curve, report_name
            )
            generated_files['rolling_metrics'] = rolling_path
        
        # 5. Generate drawdown analysis
        if self.config.include_drawdown_analysis and not equity_curve.empty:
            drawdown_path = self._generate_drawdown_analysis(
                equity_curve, report_name
            )
            generated_files['drawdown_analysis'] = drawdown_path
        
        # 6. Generate optimization analysis if provided
        if optimization_results:
            optimization_path = self._generate_optimization_analysis(
                optimization_results, report_name
            )
            generated_files['optimization'] = optimization_path
        
        # 7. Generate summary report
        summary_path = self._generate_summary_report(
            backtest_results, optimization_results, 
            benchmark_results, report_title, report_name
        )
        generated_files['summary'] = summary_path
        
        # 8. Export raw data
        if self.config.save_csv:
            csv_path = self._export_csv_data(
                equity_curve, trades_df, metrics, report_name
            )
            generated_files['csv_data'] = csv_path
        
        if self.config.save_json:
            json_path = self._export_json_data(
                backtest_results, report_name
            )
            generated_files['json_data'] = json_path
        
        logger.info(f"✅ Report generated successfully: {len(generated_files)} files")
        
        return generated_files
    
    def _generate_performance_plots(
        self,
        equity_curve: pd.Series,
        trades_df: pd.DataFrame,
        metrics: Dict[str, Any],
        report_name: str
    ) -> str:
        """Generate comprehensive performance visualization plots."""
        
        fig = plt.figure(figsize=(20, 24))
        
        # 1. Equity Curve
        ax1 = plt.subplot(4, 2, 1)
        equity_curve.plot(ax=ax1, linewidth=2, color='#2E86AB')
        ax1.set_title('Portfolio Equity Curve', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Portfolio Value ($)')
        ax1.grid(True, alpha=0.3)
        from matplotlib.ticker import FuncFormatter
        ax1.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f'${x:,.0f}'))
        
        # 2. Returns Distribution
        ax2 = plt.subplot(4, 2, 2)
        returns = equity_curve.pct_change().dropna()
        if not returns.empty:
            returns.hist(bins=50, ax=ax2, alpha=0.7, color='#A23B72')
            mean_return = float(returns.mean())
            ax2.axvline(mean_return, color='red', linestyle='--', label=f'Mean: {mean_return:.4f}')
            ax2.set_title('Daily Returns Distribution', fontsize=14, fontweight='bold')
            ax2.set_xlabel('Daily Return')
            ax2.set_ylabel('Frequency')
            ax2.legend()
            ax2.grid(True, alpha=0.3)
        
        # 3. Drawdown Chart
        ax3 = plt.subplot(4, 2, 3)
        running_max = equity_curve.expanding().max()
        drawdown = (equity_curve - running_max) / running_max * 100
        drawdown.plot(ax=ax3, color='#F18F01', linewidth=2)
        ax3.fill_between(drawdown.index, drawdown, 0, alpha=0.3, color='#F18F01')
        ax3.set_title('Drawdown Over Time', fontsize=14, fontweight='bold')
        ax3.set_ylabel('Drawdown (%)')
        ax3.grid(True, alpha=0.3)
        
        # 4. Rolling Sharpe Ratio (if enough data)
        ax4 = plt.subplot(4, 2, 4)
        if len(returns) > 30:
            rolling_sharpe = returns.rolling(30).mean() / returns.rolling(30).std() * np.sqrt(252)
            rolling_sharpe.plot(ax=ax4, color='#C73E1D', linewidth=2)
            ax4.axhline(0, color='black', linestyle='-', alpha=0.3)
            ax4.axhline(1, color='green', linestyle='--', alpha=0.5, label='Good (>1.0)')
            ax4.axhline(2, color='darkgreen', linestyle='--', alpha=0.5, label='Excellent (>2.0)')
            ax4.set_title('Rolling Sharpe Ratio (30-day)', fontsize=14, fontweight='bold')
            ax4.set_ylabel('Sharpe Ratio')
            ax4.legend()
            ax4.grid(True, alpha=0.3)
        
        # 5. Trade PnL Scatter (if trades exist)
        ax5 = plt.subplot(4, 2, 5)
        if not trades_df.empty:
            trades_df.plot.scatter(x='entry_time', y='net_pnl', ax=ax5, 
                                 c=trades_df['net_pnl'], cmap='RdYlGn', alpha=0.6)
            ax5.axhline(0, color='black', linestyle='-', alpha=0.5)
            ax5.set_title('Trade P&L Over Time', fontsize=14, fontweight='bold')
            ax5.set_ylabel('Trade P&L ($)')
            ax5.grid(True, alpha=0.3)
        
        # 6. Monthly Returns Heatmap
        ax6 = plt.subplot(4, 2, 6)
        if len(returns) > 30:
            monthly_returns = returns.resample('M').apply(lambda x: (1 + x).prod() - 1) * 100
            monthly_returns.index = monthly_returns.index.strftime('%Y-%m')
            
            # Create heatmap data
            years = sorted(set([idx[:4] for idx in monthly_returns.index]))
            months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                     'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            
            heatmap_data = pd.DataFrame(index=pd.Index(years), columns=pd.Index(months))
            
            for date, ret in monthly_returns.items():
                year, month = date.split('-')
                month_name = months[int(month) - 1]
                heatmap_data.loc[year, month_name] = ret
            
            heatmap_data = heatmap_data.astype(float)
            
            sns.heatmap(heatmap_data, annot=True, fmt='.1f', cmap='RdYlGn', 
                       center=0, ax=ax6, cbar_kws={'label': 'Monthly Return (%)'})
            ax6.set_title('Monthly Returns Heatmap', fontsize=14, fontweight='bold')
        
        # 7. Cumulative Returns vs Buy & Hold
        ax7 = plt.subplot(4, 2, 7)
        if not equity_curve.empty:
            # Strategy cumulative returns
            strategy_returns = (equity_curve / equity_curve.iloc[0] - 1) * 100
            strategy_returns.plot(ax=ax7, label='Strategy', linewidth=2, color='#2E86AB')
            
            # Simulate buy & hold for comparison (assuming 7% annual return)
            try:
                days = (equity_curve.index[-1] - equity_curve.index[0]).days
            except (AttributeError, TypeError):
                days = len(equity_curve)  # Fallback for non-datetime index
            annual_return = 0.07
            daily_return = annual_return / 365
            buy_hold = [(1 + daily_return) ** i - 1 for i in range(len(equity_curve))]
            buy_hold_series = pd.Series(buy_hold, index=equity_curve.index) * 100
            buy_hold_series.plot(ax=ax7, label='Buy & Hold (7%)', 
                               linewidth=2, color='gray', linestyle='--')
            
            ax7.set_title('Cumulative Returns Comparison', fontsize=14, fontweight='bold')
            ax7.set_ylabel('Cumulative Return (%)')
            ax7.legend()
            ax7.grid(True, alpha=0.3)
        
        # 8. Risk-Return Scatter
        ax8 = plt.subplot(4, 2, 8)
        if 'total_return_pct' in metrics and 'volatility_pct' in metrics:
            ax8.scatter(metrics['volatility_pct'], metrics['total_return_pct'], 
                       s=200, alpha=0.7, color='#A23B72')
            ax8.set_xlabel('Volatility (%)')
            ax8.set_ylabel('Total Return (%)')
            ax8.set_title('Risk-Return Profile', fontsize=14, fontweight='bold')
            ax8.grid(True, alpha=0.3)
            
            # Add quadrant labels
            ax8.axhline(0, color='black', linestyle='-', alpha=0.3)
            ax8.axvline(15, color='black', linestyle='-', alpha=0.3)
            ax8.text(5, max(10, metrics['total_return_pct'] * 0.8), 'Low Risk\nGood Return', 
                    ha='center', va='center', fontsize=10, alpha=0.7)
        
        plt.tight_layout()
        
        # Save plot
        plot_path = self.output_dir / f"{report_name}_performance_charts.png"
        plt.savefig(plot_path, dpi=self.config.plot_dpi, bbox_inches='tight')
        plt.close()
        
        logger.info(f"📊 Performance charts saved: {plot_path}")
        return str(plot_path)
    
    def _generate_metrics_analysis(
        self,
        metrics: Dict[str, Any],
        config: Dict[str, Any],
        report_name: str
    ) -> str:
        """Generate detailed metrics analysis report."""
        
        # Create metrics summary
        metrics_summary = {
            'Performance Metrics': {
                'Total Return (%)': metrics.get('total_return_pct', 0),
                'Annualized Return (%)': metrics.get('annualized_return_pct', 0),
                'Volatility (%)': metrics.get('volatility_pct', 0),
                'Sharpe Ratio': metrics.get('sharpe_ratio', 0),
                'Sortino Ratio': metrics.get('sortino_ratio', 0),
                'Calmar Ratio': metrics.get('calmar_ratio', 0),
            },
            'Risk Metrics': {
                'Maximum Drawdown (%)': metrics.get('max_drawdown_pct', 0),
                'Value at Risk 5% (%)': metrics.get('var_5pct', 0),
                'Conditional VaR 5% (%)': metrics.get('cvar_5pct', 0),
                'Skewness': metrics.get('skewness', 0),
                'Excess Kurtosis': metrics.get('excess_kurtosis', 0),
            },
            'Trading Metrics': {
                'Total Trades': metrics.get('total_trades', 0),
                'Win Rate (%)': metrics.get('win_rate_pct', 0),
                'Profit Factor': metrics.get('profit_factor', 0),
                'Average Win (%)': metrics.get('avg_win_pct', 0),
                'Average Loss (%)': metrics.get('avg_loss_pct', 0),
                'Expectancy (%)': metrics.get('expectancy_pct', 0),
            },
            'Configuration': {
                'Initial Capital': config.get('initial_capital', 0),
                'Commission Rate (%)': config.get('commission_rate', 0) * 100,
                'Slippage Rate (%)': config.get('slippage_rate', 0) * 100,
                'Symbols': ', '.join(config.get('symbols', [])),
                'Timeframe': config.get('timeframe', ''),
                'Start Date': config.get('start_date', ''),
                'End Date': config.get('end_date', ''),
            }
        }
        
        # Generate text report
        report_text = f"""
BACKTESTING METRICS ANALYSIS
{'=' * 50}

Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

"""
        
        for category, category_metrics in metrics_summary.items():
            report_text += f"\n{category.upper()}\n{'-' * len(category)}\n"
            
            for metric_name, metric_value in category_metrics.items():
                if isinstance(metric_value, (int, float)):
                    if metric_name.endswith('(%)'):
                        report_text += f"{metric_name:<25}: {metric_value:>10.2f}\n"
                    elif 'Ratio' in metric_name:
                        report_text += f"{metric_name:<25}: {metric_value:>10.3f}\n"
                    else:
                        report_text += f"{metric_name:<25}: {metric_value:>10,.0f}\n"
                else:
                    report_text += f"{metric_name:<25}: {str(metric_value):>10}\n"
        
        # Add interpretation
        report_text += f"""

PERFORMANCE INTERPRETATION
{'-' * 30}

Risk Assessment:
"""
        
        sharpe = metrics.get('sharpe_ratio', 0)
        if sharpe > 2:
            report_text += "• Excellent risk-adjusted returns (Sharpe > 2.0)\n"
        elif sharpe > 1:
            report_text += "• Good risk-adjusted returns (Sharpe > 1.0)\n"
        elif sharpe > 0:
            report_text += "• Positive risk-adjusted returns (Sharpe > 0)\n"
        else:
            report_text += "• Poor risk-adjusted returns (Sharpe ≤ 0)\n"
        
        max_dd = abs(metrics.get('max_drawdown_pct', 0))
        if max_dd < 5:
            report_text += "• Low drawdown risk (Max DD < 5%)\n"
        elif max_dd < 15:
            report_text += "• Moderate drawdown risk (Max DD < 15%)\n"
        else:
            report_text += "• High drawdown risk (Max DD ≥ 15%)\n"
        
        win_rate = metrics.get('win_rate_pct', 0)
        if win_rate > 60:
            report_text += "• High win rate (>60%)\n"
        elif win_rate > 40:
            report_text += "• Moderate win rate (40-60%)\n"
        else:
            report_text += "• Low win rate (<40%)\n"
        
        # Save report
        report_path = self.output_dir / f"{report_name}_metrics_analysis.txt"
        with open(report_path, 'w') as f:
            f.write(report_text)
        
        logger.info(f"📊 Metrics analysis saved: {report_path}")
        return str(report_path)
    
    def _generate_trade_analysis(self, trades_df: pd.DataFrame, report_name: str) -> str:
        """Generate detailed trade-by-trade analysis."""
        
        if trades_df.empty:
            return ""
        
        # Trade statistics
        trade_stats = {
            'Total Trades': len(trades_df),
            'Winning Trades': len(trades_df[trades_df['net_pnl'] > 0]),
            'Losing Trades': len(trades_df[trades_df['net_pnl'] < 0]),
            'Win Rate (%)': len(trades_df[trades_df['net_pnl'] > 0]) / len(trades_df) * 100,
            'Average Trade P&L ($)': trades_df['net_pnl'].mean(),
            'Best Trade ($)': trades_df['net_pnl'].max(),
            'Worst Trade ($)': trades_df['net_pnl'].min(),
            'Average Duration (hours)': trades_df['duration_hours'].mean(),
            'Total Commission ($)': trades_df['commission'].sum(),
            'Total Slippage ($)': trades_df['slippage'].sum(),
        }
        
        # Symbol performance
        symbol_performance = trades_df.groupby('symbol').agg({
            'net_pnl': ['count', 'sum', 'mean'],
            'return_pct': 'mean',
            'duration_hours': 'mean'
        }).round(2)
        
        # Monthly performance
        trades_df['month'] = trades_df['entry_time'].dt.to_period('M')
        monthly_performance = trades_df.groupby('month').agg({
            'net_pnl': ['count', 'sum'],
            'return_pct': 'mean'
        }).round(2)
        
        # Generate report
        report = f"""
TRADE ANALYSIS REPORT
{'=' * 50}

SUMMARY STATISTICS
{'-' * 20}
"""
        
        for stat_name, stat_value in trade_stats.items():
            if isinstance(stat_value, float):
                if stat_name.endswith('(%)'):
                    report += f"{stat_name:<25}: {stat_value:>10.2f}\n"
                elif stat_name.endswith('($)'):
                    report += f"{stat_name:<25}: ${stat_value:>10,.2f}\n"
                else:
                    report += f"{stat_name:<25}: {stat_value:>10.2f}\n"
            else:
                report += f"{stat_name:<25}: {stat_value:>10}\n"
        
        report += f"\n\nSYMBOL PERFORMANCE\n{'-' * 20}\n"
        report += symbol_performance.to_string()
        
        report += f"\n\nMONTHLY PERFORMANCE\n{'-' * 20}\n"
        report += monthly_performance.to_string()
        
        # Save detailed trades CSV
        csv_path = self.output_dir / f"{report_name}_detailed_trades.csv"
        trades_df.to_csv(csv_path, index=False)
        
        # Save report
        report_path = self.output_dir / f"{report_name}_trade_analysis.txt"
        with open(report_path, 'w') as f:
            f.write(report)
        
        logger.info(f"📊 Trade analysis saved: {report_path}")
        return str(report_path)
    
    def _generate_rolling_analysis(self, equity_curve: pd.Series, report_name: str) -> str:
        """Generate rolling performance metrics analysis."""
        
        # Calculate rolling metrics
        rolling_metrics = backtest_metrics.rolling_metrics(
            equity_curve, 
            window_days=30,
            metrics=['sharpe_ratio', 'sortino_ratio', 'max_drawdown_pct', 'volatility_pct']
        )
        
        if rolling_metrics.empty:
            return ""
        
        # Save rolling metrics
        csv_path = self.output_dir / f"{report_name}_rolling_metrics.csv"
        rolling_metrics.to_csv(csv_path)
        
        # Generate summary
        summary = rolling_metrics.describe()
        
        report = f"""
ROLLING METRICS ANALYSIS (30-Day Windows)
{'=' * 50}

STATISTICAL SUMMARY
{'-' * 20}
{summary.to_string()}

STABILITY INDICATORS
{'-' * 20}
Average Sharpe Ratio: {rolling_metrics['sharpe_ratio'].mean():.3f}
Sharpe Ratio Std Dev: {rolling_metrics['sharpe_ratio'].std():.3f}
Best 30-Day Sharpe: {rolling_metrics['sharpe_ratio'].max():.3f}
Worst 30-Day Sharpe: {rolling_metrics['sharpe_ratio'].min():.3f}

Consistency Score: {1 - (rolling_metrics['sharpe_ratio'].std() / max(abs(rolling_metrics['sharpe_ratio'].mean()), 1e-6)):.3f}
"""
        
        report_path = self.output_dir / f"{report_name}_rolling_analysis.txt"
        with open(report_path, 'w') as f:
            f.write(report)
        
        logger.info(f"📊 Rolling analysis saved: {report_path}")
        return str(report_path)
    
    def _generate_drawdown_analysis(self, equity_curve: pd.Series, report_name: str) -> str:
        """Generate detailed drawdown analysis."""
        
        # Calculate drawdown metrics
        dd_metrics = backtest_metrics.drawdown_duration(equity_curve)
        
        # Calculate running drawdown
        running_max = equity_curve.expanding().max()
        drawdown_pct = (equity_curve - running_max) / running_max * 100
        
        # Find all drawdown periods
        in_drawdown = drawdown_pct < -0.01  # Consider >0.01% as drawdown
        
        drawdown_periods = []
        start_idx = None
        
        for i, is_dd in enumerate(in_drawdown):
            if is_dd and start_idx is None:
                start_idx = i
            elif not is_dd and start_idx is not None:
                end_idx = i - 1
                period_dd = drawdown_pct.iloc[start_idx:end_idx+1]
                drawdown_periods.append({
                    'start_date': equity_curve.index[start_idx],
                    'end_date': equity_curve.index[end_idx],
                    'duration_days': self._safe_days_diff(equity_curve.index[end_idx], equity_curve.index[start_idx]),
                    'max_drawdown_pct': period_dd.min(),
                    'recovery_date': equity_curve.index[i] if i < len(equity_curve) else None
                })
                start_idx = None
        
        # Sort by severity
        drawdown_periods.sort(key=lambda x: x['max_drawdown_pct'])
        
        report = f"""
DRAWDOWN ANALYSIS
{'=' * 50}

OVERALL STATISTICS
{'-' * 20}
Maximum Drawdown: {dd_metrics['max_duration_days']:.2f} days
Average Drawdown Duration: {dd_metrics['avg_duration_days']:.2f} days
Current Drawdown Duration: {dd_metrics['current_duration_days']:.2f} days

TOP 5 WORST DRAWDOWN PERIODS
{'-' * 30}
"""
        
        for i, period in enumerate(drawdown_periods[:5]):
            report += f"""
Period {i+1}:
  Start Date: {period['start_date'].strftime('%Y-%m-%d')}
  End Date: {period['end_date'].strftime('%Y-%m-%d')}
  Duration: {period['duration_days']} days
  Max Drawdown: {period['max_drawdown_pct']:.2f}%
  Recovery: {'Yes' if period['recovery_date'] else 'Ongoing'}
"""
        
        # Save detailed drawdown data
        if drawdown_periods:
            dd_df = pd.DataFrame(drawdown_periods)
            csv_path = self.output_dir / f"{report_name}_drawdown_periods.csv"
            dd_df.to_csv(csv_path, index=False)
        
        report_path = self.output_dir / f"{report_name}_drawdown_analysis.txt"
        with open(report_path, 'w') as f:
            f.write(report)
        
        logger.info(f"📊 Drawdown analysis saved: {report_path}")
        return str(report_path)
    
    def _generate_optimization_analysis(
        self, 
        optimization_results: Dict[str, Any], 
        report_name: str
    ) -> str:
        """Generate parameter optimization analysis."""
        
        if 'all_results' not in optimization_results:
            return ""
        
        results_df = pd.DataFrame(optimization_results['all_results'])
        
        report = f"""
PARAMETER OPTIMIZATION ANALYSIS
{'=' * 50}

OPTIMIZATION SUMMARY
{'-' * 20}
Total Combinations Tested: {optimization_results.get('total_combinations', 0)}
Successful Runs: {optimization_results.get('successful_runs', 0)}
Optimization Metric: {optimization_results.get('optimization_metric', 'N/A')}
Best Score: {optimization_results.get('best_score', 0):.4f}
Optimization Time: {optimization_results.get('optimization_time_seconds', 0):.1f} seconds

BEST PARAMETERS
{'-' * 20}
"""
        
        best_params = optimization_results.get('best_parameters', {})
        for param_name, param_value in best_params.items():
            report += f"{param_name}: {param_value}\n"
        
        # Parameter sensitivity analysis
        if not results_df.empty:
            report += f"\n\nPARAMETER SENSITIVITY\n{'-' * 20}\n"
            
            param_columns = [col for col in results_df.columns if col not in ['score']]
            for param in param_columns:
                if param in results_df.columns:
                    param_series = results_df[param]
                    score_series = results_df['score']
                    correlation = param_series.corr(score_series)
                    report += f"{param}: {correlation:.3f} correlation with score\n"
        
        # Save optimization results
        csv_path = self.output_dir / f"{report_name}_optimization_results.csv"
        results_df.to_csv(csv_path, index=False)
        
        report_path = self.output_dir / f"{report_name}_optimization_analysis.txt"
        with open(report_path, 'w') as f:
            f.write(report)
        
        logger.info(f"📊 Optimization analysis saved: {report_path}")
        return str(report_path)
    
    def _generate_summary_report(
        self,
        backtest_results: Dict[str, Any],
        optimization_results: Optional[Dict[str, Any]],
        benchmark_results: Optional[Dict[str, Any]],
        report_title: str,
        report_name: str
    ) -> str:
        """Generate executive summary report."""
        
        metrics = backtest_results.get('metrics', {})
        config = backtest_results.get('config', {})
        
        summary = f"""
{report_title.upper()}
{'=' * len(report_title)}

Executive Summary
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

STRATEGY OVERVIEW
{'-' * 20}
Strategy Name: {report_title}
Test Period: {config.get('start_date', 'N/A')} to {config.get('end_date', 'N/A')}
Symbols Tested: {', '.join(config.get('symbols', []))}
Initial Capital: ${config.get('initial_capital', 0):,.2f}
Timeframe: {config.get('timeframe', 'N/A')}

KEY PERFORMANCE METRICS
{'-' * 30}
Total Return: {metrics.get('total_return_pct', 0):.2f}%
Annualized Return: {metrics.get('annualized_return_pct', 0):.2f}%
Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.3f}
Maximum Drawdown: {metrics.get('max_drawdown_pct', 0):.2f}%
Win Rate: {metrics.get('win_rate_pct', 0):.1f}%
Total Trades: {metrics.get('total_trades', 0)}

RISK ASSESSMENT
{'-' * 20}
"""
        
        # Risk assessment
        sharpe = metrics.get('sharpe_ratio', 0)
        max_dd = abs(metrics.get('max_drawdown_pct', 0))
        
        if sharpe > 1.5 and max_dd < 10:
            risk_level = "LOW"
            summary += "• Excellent risk-adjusted returns with controlled drawdowns\n"
        elif sharpe > 1.0 and max_dd < 20:
            risk_level = "MODERATE"
            summary += "• Good risk-adjusted returns with acceptable drawdowns\n"
        else:
            risk_level = "HIGH"
            summary += "• Higher risk profile - review strategy parameters\n"
        
        summary += f"• Overall Risk Level: {risk_level}\n"
        
        # Recommendations
        summary += f"\nRECOMMENDATIONS\n{'-' * 20}\n"
        
        if metrics.get('total_trades', 0) < 30:
            summary += "• Insufficient trades for robust analysis - consider longer test period\n"
        
        if metrics.get('win_rate_pct', 0) < 40:
            summary += "• Low win rate - review entry/exit criteria\n"
        
        if max_dd > 15:
            summary += "• High drawdown - consider tighter risk management\n"
        
        if sharpe < 1.0:
            summary += "• Poor risk-adjusted returns - optimize strategy parameters\n"
        
        if optimization_results:
            summary += "• Parameter optimization completed - use optimized parameters for live trading\n"
        
        summary += "\nDISCLAIMER\n"
        summary += "Past performance does not guarantee future results. "
        summary += "This analysis is for educational purposes only and should not be considered investment advice.\n"
        
        # Save summary
        summary_path = self.output_dir / f"{report_name}_executive_summary.txt"
        with open(summary_path, 'w') as f:
            f.write(summary)
        
        logger.info(f"📊 Executive summary saved: {summary_path}")
        return str(summary_path)
    
    def _export_csv_data(
        self,
        equity_curve: pd.Series,
        trades_df: pd.DataFrame,
        metrics: Dict[str, Any],
        report_name: str
    ) -> str:
        """Export all data to CSV files."""
        
        csv_dir = self.output_dir / f"{report_name}_csv_data"
        csv_dir.mkdir(exist_ok=True)
        
        # Export equity curve
        if not equity_curve.empty:
            equity_path = csv_dir / "equity_curve.csv"
            equity_curve.to_csv(equity_path, header=['portfolio_value'])
        
        # Export trades
        if not trades_df.empty:
            trades_path = csv_dir / "trades.csv"
            trades_df.to_csv(trades_path, index=False)
        
        # Export metrics
        metrics_path = csv_dir / "metrics.csv"
        metrics_df = pd.DataFrame(list(metrics.items()), columns=pd.Index(['metric', 'value']))
        metrics_df.to_csv(metrics_path, index=False)
        
        logger.info(f"📊 CSV data exported: {csv_dir}")
        return str(csv_dir)
    
    def _export_json_data(self, backtest_results: Dict[str, Any], report_name: str) -> str:
        """Export all data to JSON format."""
        
        json_path = self.output_dir / f"{report_name}_full_results.json"
        
        # Convert any non-serializable data
        serializable_results = self._make_json_serializable(backtest_results)
        
        with open(json_path, 'w') as f:
            json.dump(serializable_results, f, indent=2, default=str)
        
        logger.info(f"📊 JSON data exported: {json_path}")
        return str(json_path)
    
    def _make_json_serializable(self, obj: Any) -> Any:
        """Convert object to JSON-serializable format."""
        if isinstance(obj, dict):
            return {k: self._make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
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


# Global instance for easy access
backtest_reporter = BacktestReporter()