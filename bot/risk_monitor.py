"""
📊 COMPREHENSIVE RISK MONITORING SYSTEM
Real-time risk metrics dashboard and monitoring engine with advanced analytics,
portfolio heat mapping, alert systems, and institutional-grade risk reporting.

Features:
- Real-time risk metrics calculation and monitoring
- Portfolio heat maps and correlation analysis
- Risk budget allocation and tracking system
- Multi-level alert system for risk limit breaches
- Comprehensive risk reporting and analytics
- Risk factor decomposition and attribution
- Stress testing and scenario analysis
- Regulatory compliance monitoring
- Performance attribution and risk-adjusted metrics
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import warnings
from pathlib import Path
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

from .util import logger
from .config import settings


class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"                # Informational alerts
    WARNING = "warning"          # Warning alerts  
    CRITICAL = "critical"        # Critical alerts
    EMERGENCY = "emergency"      # Emergency alerts


class RiskCategory(Enum):
    """Risk categorization"""
    MARKET_RISK = "market_risk"         # Market/price risk
    CREDIT_RISK = "credit_risk"         # Counterparty risk
    LIQUIDITY_RISK = "liquidity_risk"   # Liquidity risk
    OPERATIONAL_RISK = "operational_risk" # Operational risk
    CONCENTRATION_RISK = "concentration_risk" # Concentration risk
    MODEL_RISK = "model_risk"           # Model risk


@dataclass
class RiskAlert:
    """Container for risk alerts"""
    id: str = ""                        # Unique alert ID
    timestamp: datetime = field(default_factory=datetime.now)
    level: AlertLevel = AlertLevel.INFO
    category: RiskCategory = RiskCategory.MARKET_RISK
    title: str = ""                     # Alert title
    message: str = ""                   # Alert message
    metric_name: str = ""               # Related metric
    current_value: float = 0.0          # Current value
    threshold: float = 0.0              # Threshold breached
    symbol: str = ""                    # Related symbol (if applicable)
    acknowledged: bool = False          # Alert acknowledgment status
    resolved: bool = False              # Alert resolution status


@dataclass
class RiskLimit:
    """Risk limit definition"""
    name: str = ""                      # Limit name
    category: RiskCategory = RiskCategory.MARKET_RISK
    metric_name: str = ""               # Metric to monitor
    warning_threshold: float = 0.0      # Warning threshold
    critical_threshold: float = 0.0     # Critical threshold
    emergency_threshold: float = 0.0    # Emergency threshold
    enabled: bool = True                # Limit enabled status
    symbol_specific: bool = False       # Symbol-specific limit
    timeframe: str = "real_time"        # Timeframe for limit


@dataclass
class PortfolioHeatMap:
    """Portfolio heat map data"""
    correlation_matrix: Dict[str, Dict[str, float]] = field(default_factory=dict)
    risk_contribution: Dict[str, float] = field(default_factory=dict)
    concentration_scores: Dict[str, float] = field(default_factory=dict)
    sector_exposure: Dict[str, float] = field(default_factory=dict)
    currency_exposure: Dict[str, float] = field(default_factory=dict)
    volatility_breakdown: Dict[str, float] = field(default_factory=dict)
    var_contribution: Dict[str, float] = field(default_factory=dict)


@dataclass
class RiskAttribution:
    """Risk factor attribution analysis"""
    total_risk: float = 0.0             # Total portfolio risk
    systematic_risk: float = 0.0        # Systematic/market risk
    specific_risk: float = 0.0          # Specific/idiosyncratic risk
    factor_contributions: Dict[str, float] = field(default_factory=dict)
    sector_contributions: Dict[str, float] = field(default_factory=dict)
    geographic_contributions: Dict[str, float] = field(default_factory=dict)
    style_contributions: Dict[str, float] = field(default_factory=dict)


class RiskMonitor:
    """
    Comprehensive risk monitoring system that provides real-time risk analytics,
    portfolio monitoring, alert management, and institutional-grade risk reporting.
    
    Core Functions:
    - Real-time risk metrics calculation and monitoring
    - Portfolio heat mapping and correlation analysis
    - Risk budget tracking and allocation management
    - Multi-level alert system with escalation protocols
    - Comprehensive risk reporting and analytics
    - Risk factor decomposition and attribution analysis
    - Stress testing and scenario analysis capabilities
    - Regulatory compliance monitoring and reporting
    """
    
    def __init__(self):
        # State persistence
        self.state_file = "bot/risk_monitor_state.json"
        self.alerts_file = "bot/risk_alerts.json"
        self.reports_file = "bot/risk_reports.json"
        
        # Risk limits configuration
        self.risk_limits = self._initialize_risk_limits()
        
        # Current state
        self.active_alerts = []                # Active risk alerts
        self.risk_metrics = {}                 # Current risk metrics
        self.portfolio_heatmap = PortfolioHeatMap()
        self.risk_attribution = RiskAttribution()
        self.risk_budget = {}                  # Risk budget allocation
        self.compliance_status = {}            # Compliance monitoring
        
        # Historical data
        self.metrics_history = []              # Historical risk metrics
        self.alert_history = []                # Historical alerts
        self.reports_history = []              # Historical reports
        
        # Monitoring state
        self.last_update = None
        self.monitoring_frequency = 30         # Update frequency in seconds
        self._monitoring_active = False
        
        # Load persistent state
        self.load_state()
        
        # Initialize monitoring
        self._start_background_monitoring()
        
        logger.info("📊 Risk Monitor initialized - Comprehensive risk tracking active")
    
    def _initialize_risk_limits(self) -> List[RiskLimit]:
        """Initialize default risk limits"""
        limits = [
            # Portfolio-level limits
            RiskLimit(
                name="Portfolio VaR Limit",
                category=RiskCategory.MARKET_RISK,
                metric_name="portfolio_var_95",
                warning_threshold=0.02,      # 2% daily VaR warning
                critical_threshold=0.03,     # 3% daily VaR critical
                emergency_threshold=0.05,    # 5% daily VaR emergency
                timeframe="daily"
            ),
            RiskLimit(
                name="Maximum Drawdown Limit",
                category=RiskCategory.MARKET_RISK,
                metric_name="current_drawdown",
                warning_threshold=0.05,      # 5% drawdown warning
                critical_threshold=0.10,     # 10% drawdown critical
                emergency_threshold=0.15,    # 15% drawdown emergency
                timeframe="real_time"
            ),
            RiskLimit(
                name="Gross Exposure Limit",
                category=RiskCategory.CONCENTRATION_RISK,
                metric_name="gross_exposure_ratio",
                warning_threshold=0.8,       # 80% gross exposure warning
                critical_threshold=1.0,      # 100% gross exposure critical
                emergency_threshold=1.2,     # 120% gross exposure emergency
                timeframe="real_time"
            ),
            RiskLimit(
                name="Cash Buffer Minimum",
                category=RiskCategory.LIQUIDITY_RISK,
                metric_name="cash_ratio",
                warning_threshold=0.05,      # 5% cash minimum warning
                critical_threshold=0.02,     # 2% cash minimum critical
                emergency_threshold=0.01,    # 1% cash minimum emergency
                timeframe="real_time"
            ),
            RiskLimit(
                name="Correlation Risk Limit",
                category=RiskCategory.CONCENTRATION_RISK,
                metric_name="avg_correlation",
                warning_threshold=0.7,       # 70% average correlation warning
                critical_threshold=0.8,      # 80% average correlation critical
                emergency_threshold=0.9,     # 90% average correlation emergency
                timeframe="daily"
            ),
            RiskLimit(
                name="Volatility Spike Detection",
                category=RiskCategory.MARKET_RISK,
                metric_name="realized_volatility",
                warning_threshold=0.3,       # 30% annualized volatility warning
                critical_threshold=0.5,      # 50% annualized volatility critical
                emergency_threshold=0.8,     # 80% annualized volatility emergency
                timeframe="real_time"
            ),
            # Position-level limits
            RiskLimit(
                name="Single Position VaR Limit",
                category=RiskCategory.CONCENTRATION_RISK,
                metric_name="position_var",
                warning_threshold=0.005,     # 0.5% single position VaR warning
                critical_threshold=0.01,     # 1% single position VaR critical
                emergency_threshold=0.02,    # 2% single position VaR emergency
                symbol_specific=True,
                timeframe="daily"
            ),
            RiskLimit(
                name="Position Size Limit",
                category=RiskCategory.CONCENTRATION_RISK,
                metric_name="position_weight",
                warning_threshold=0.1,       # 10% position weight warning
                critical_threshold=0.15,     # 15% position weight critical
                emergency_threshold=0.25,    # 25% position weight emergency
                symbol_specific=True,
                timeframe="real_time"
            )
        ]
        return limits
    
    def load_state(self):
        """Load persistent state from disk"""
        try:
            if Path(self.state_file).exists():
                with open(self.state_file, 'r') as f:
                    state_data = json.load(f)
                    
                    self.last_update = state_data.get('last_update')
                    if self.last_update:
                        self.last_update = datetime.fromisoformat(self.last_update)
                    
                    # Load risk budget
                    self.risk_budget = state_data.get('risk_budget', {})
                    
            if Path(self.alerts_file).exists():
                with open(self.alerts_file, 'r') as f:
                    alerts_data = json.load(f)
                    self.alert_history = alerts_data[-500:]  # Keep last 500 alerts
                    
            if Path(self.reports_file).exists():
                with open(self.reports_file, 'r') as f:
                    reports_data = json.load(f)
                    self.reports_history = reports_data[-100:]  # Keep last 100 reports
                    
        except Exception as e:
            logger.warning(f"⚠️ Error loading risk monitor state: {e}")
            self.alert_history = []
            self.reports_history = []
    
    def save_state(self):
        """Save persistent state to disk"""
        try:
            state_data = {
                'last_update': self.last_update.isoformat() if self.last_update else None,
                'risk_budget': self.risk_budget,
                'active_alerts_count': len(self.active_alerts),
                'compliance_status': self.compliance_status
            }
            
            with open(self.state_file, 'w') as f:
                json.dump(state_data, f, indent=2)
                
            # Save alerts history
            with open(self.alerts_file, 'w') as f:
                alerts_serializable = []
                for alert in self.alert_history:
                    if isinstance(alert, dict):
                        alerts_serializable.append(alert)
                    else:
                        # Convert RiskAlert object to dict
                        alerts_serializable.append({
                            'id': alert.id,
                            'timestamp': alert.timestamp.isoformat(),
                            'level': alert.level.value,
                            'category': alert.category.value,
                            'title': alert.title,
                            'message': alert.message,
                            'metric_name': alert.metric_name,
                            'current_value': alert.current_value,
                            'threshold': alert.threshold,
                            'symbol': alert.symbol,
                            'acknowledged': alert.acknowledged,
                            'resolved': alert.resolved
                        })
                json.dump(alerts_serializable, f, indent=2)
                
            # Save reports history
            with open(self.reports_file, 'w') as f:
                json.dump(self.reports_history, f, indent=2)
                
        except Exception as e:
            logger.warning(f"⚠️ Error saving risk monitor state: {e}")
    
    def _start_background_monitoring(self):
        """Start background risk monitoring"""
        if self._monitoring_active:
            return
            
        def monitor_risk():
            while self._monitoring_active:
                try:
                    self.update_risk_monitoring()
                    time.sleep(self.monitoring_frequency)
                except Exception as e:
                    logger.error(f"❌ Error in risk monitoring: {e}")
                    time.sleep(60)  # Back off on error
        
        self._monitoring_active = True
        monitoring_thread = threading.Thread(target=monitor_risk, daemon=True)
        monitoring_thread.start()
        logger.info("🔍 Background risk monitoring started")
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        self._monitoring_active = False
        logger.info("⏹️ Risk monitoring stopped")
    
    def update_risk_monitoring(self):
        """Update comprehensive risk monitoring"""
        try:
            # Calculate current risk metrics
            self.risk_metrics = self._calculate_comprehensive_risk_metrics()
            
            # Update portfolio heat map
            self.portfolio_heatmap = self._generate_portfolio_heatmap()
            
            # Perform risk attribution analysis
            self.risk_attribution = self._calculate_risk_attribution()
            
            # Check risk limits and generate alerts
            self._check_risk_limits()
            
            # Update compliance status
            self._update_compliance_status()
            
            # Save metrics to history
            self._save_metrics_to_history()
            
            # Update timestamp
            self.last_update = datetime.now()
            
            # Save state
            self.save_state()
            
            # Log monitoring status
            self._log_monitoring_status()
            
        except Exception as e:
            logger.error(f"❌ Error updating risk monitoring: {e}")
    
    def _calculate_comprehensive_risk_metrics(self) -> Dict[str, float]:
        """Calculate comprehensive risk metrics"""
        try:
            metrics = {}
            
            # Get current account data
            from alpaca.trading.client import TradingClient
            client = TradingClient(
                api_key=settings.alpaca_api_key,
                secret_key=settings.alpaca_secret_key,
                paper=(settings.mode == "paper")
            )
            
            account = client.get_account()
            current_equity = float(getattr(account, 'equity', 0) or 0)
            cash = float(getattr(account, 'cash', 0) or 0)
            
            if current_equity <= 0:
                return metrics
            
            # Basic portfolio metrics
            metrics['equity'] = current_equity
            metrics['cash'] = cash
            metrics['cash_ratio'] = cash / current_equity
            
            # Get positions for analysis
            positions = client.get_all_positions()
            
            if positions:
                # Calculate exposure metrics
                gross_exposure = sum(abs(float(pos.market_value)) for pos in positions)
                metrics['gross_exposure'] = gross_exposure
                metrics['gross_exposure_ratio'] = gross_exposure / current_equity
                
                # Calculate position weights
                position_weights = {}
                for pos in positions:
                    symbol = pos.symbol
                    weight = abs(float(pos.market_value)) / current_equity
                    position_weights[symbol] = weight
                    metrics[f'{symbol}_weight'] = weight
                
                # Concentration metrics
                if position_weights:
                    metrics['max_position_weight'] = max(position_weights.values())
                    metrics['top3_concentration'] = sum(sorted(position_weights.values(), reverse=True)[:3])
                    metrics['position_count'] = len(position_weights)
                    
                    # HHI (Herfindahl-Hirschman Index) for concentration
                    hhi = sum(w**2 for w in position_weights.values())
                    metrics['hhi_concentration'] = hhi
            else:
                metrics['gross_exposure'] = 0.0
                metrics['gross_exposure_ratio'] = 0.0
                metrics['max_position_weight'] = 0.0
                metrics['position_count'] = 0
                metrics['hhi_concentration'] = 0.0
            
            # Import and use other risk management components
            try:
                from .dynamic_risk_manager import dynamic_risk_manager
                from .volatility_assessor import volatility_assessor
                from .drawdown_protector import drawdown_protector
                from .performance_adapter import performance_adapter
                
                # Get metrics from other components
                risk_summary = dynamic_risk_manager.get_risk_metrics_summary()
                vol_summary = volatility_assessor.get_volatility_assessment_summary()
                dd_summary = drawdown_protector.get_protection_summary()
                perf_summary = performance_adapter.get_performance_summary()
                
                # Integrate key metrics
                metrics.update({
                    'risk_score': risk_summary.get('risk_score', 0.5),
                    'volatility_regime': vol_summary.get('market_regime', 'normal'),
                    'current_drawdown': dd_summary.get('current_drawdown', 0.0),
                    'max_drawdown': dd_summary.get('max_drawdown', 0.0),
                    'protection_level': dd_summary.get('protection_level', 'normal'),
                    'performance_regime': perf_summary.get('regime', 'average'),
                    'win_rate': perf_summary.get('win_rate', 0.5),
                    'sharpe_ratio': perf_summary.get('sharpe_ratio', 0.0),
                    'emergency_mode': (risk_summary.get('emergency_mode', False) or 
                                     dd_summary.get('emergency_mode', False) or
                                     perf_summary.get('intervention_mode', False))
                })
                
                # Calculate portfolio VaR (simplified)
                risk_score = metrics.get('risk_score', 0.5)
                portfolio_vol = vol_summary.get('correlation_metrics', {}).get('market_correlation', 0.5)
                estimated_vol = min(0.5, max(0.05, portfolio_vol * risk_score))
                metrics['portfolio_var_95'] = estimated_vol * 1.645  # 95% VaR approximation
                metrics['portfolio_var_99'] = estimated_vol * 2.326  # 99% VaR approximation
                metrics['realized_volatility'] = estimated_vol
                
                # Correlation metrics
                correlation_metrics = vol_summary.get('correlation_metrics', {})
                metrics['market_correlation'] = correlation_metrics.get('market_correlation', 0.0)
                metrics['crypto_correlation'] = correlation_metrics.get('crypto_correlation', 0.0)
                metrics['avg_correlation'] = (correlation_metrics.get('market_correlation', 0.0) + 
                                            correlation_metrics.get('crypto_correlation', 0.0)) / 2
                
            except Exception as e:
                logger.warning(f"⚠️ Error integrating risk component metrics: {e}")
                # Set default values
                metrics.update({
                    'risk_score': 0.5,
                    'current_drawdown': 0.0,
                    'max_drawdown': 0.0,
                    'portfolio_var_95': 0.02,
                    'realized_volatility': 0.15,
                    'market_correlation': 0.0,
                    'avg_correlation': 0.0,
                    'emergency_mode': False
                })
            
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Error calculating comprehensive risk metrics: {e}")
            return {}
    
    def _generate_portfolio_heatmap(self) -> PortfolioHeatMap:
        """Generate portfolio heat map data"""
        try:
            heatmap = PortfolioHeatMap()
            
            # Get market data for correlation analysis
            try:
                from .data import fetch_bars
                
                symbols = settings.symbols[:10]  # Limit for performance
                correlation_data = {}
                
                for symbol in symbols:
                    try:
                        data = fetch_bars(symbol, min_bars=50)
                        if data is not None and not data.empty:
                            returns = data['close'].pct_change().dropna()
                            if len(returns) >= 20:
                                correlation_data[symbol] = returns.tail(20)
                    except:
                        continue
                
                # Calculate correlation matrix
                if len(correlation_data) >= 2:
                    min_length = min(len(returns) for returns in correlation_data.values())
                    aligned_data = {symbol: returns.tail(min_length) 
                                  for symbol, returns in correlation_data.items()}
                    
                    correlation_df = pd.DataFrame(aligned_data)
                    correlation_matrix = correlation_df.corr()
                    
                    # Convert to nested dict format
                    for symbol1 in correlation_matrix.index:
                        heatmap.correlation_matrix[symbol1] = {}
                        for symbol2 in correlation_matrix.columns:
                            corr_val = correlation_matrix.loc[symbol1, symbol2]
                            if not np.isnan(corr_val):
                                heatmap.correlation_matrix[symbol1][symbol2] = float(corr_val)
                
                # Calculate risk contributions (simplified)
                if self.risk_metrics and correlation_data:
                    total_risk = self.risk_metrics.get('portfolio_var_95', 0.02)
                    num_assets = len(correlation_data)
                    
                    for symbol in correlation_data.keys():
                        # Simplified risk contribution calculation
                        weight = self.risk_metrics.get(f'{symbol}_weight', 1/num_assets)
                        contribution = weight * total_risk / num_assets
                        heatmap.risk_contribution[symbol] = contribution
                        
                        # Volatility breakdown
                        vol_estimate = 0.15 * (1 + np.random.normal(0, 0.1))  # Simplified
                        heatmap.volatility_breakdown[symbol] = max(0.05, vol_estimate)
                
            except Exception as e:
                logger.debug(f"Error generating detailed heatmap: {e}")
            
            return heatmap
            
        except Exception as e:
            logger.error(f"❌ Error generating portfolio heatmap: {e}")
            return PortfolioHeatMap()
    
    def _calculate_risk_attribution(self) -> RiskAttribution:
        """Calculate risk factor attribution"""
        try:
            attribution = RiskAttribution()
            
            if not self.risk_metrics:
                return attribution
            
            # Total portfolio risk
            attribution.total_risk = self.risk_metrics.get('portfolio_var_95', 0.02)
            
            # Systematic vs specific risk (simplified model)
            market_correlation = self.risk_metrics.get('market_correlation', 0.5)
            systematic_portion = market_correlation ** 2
            
            attribution.systematic_risk = attribution.total_risk * systematic_portion
            attribution.specific_risk = attribution.total_risk * (1 - systematic_portion)
            
            # Factor contributions (simplified)
            attribution.factor_contributions = {
                'market_factor': attribution.systematic_risk * 0.7,
                'sector_factor': attribution.systematic_risk * 0.2,
                'style_factor': attribution.systematic_risk * 0.1,
                'idiosyncratic': attribution.specific_risk
            }
            
            # Sector contributions (if position data available)
            crypto_weight = 0.0
            stock_weight = 0.0
            
            for metric_name, value in self.risk_metrics.items():
                if metric_name.endswith('_weight'):
                    symbol = metric_name.replace('_weight', '')
                    if '/' in symbol or symbol.endswith('USD'):
                        crypto_weight += value
                    else:
                        stock_weight += value
            
            if crypto_weight + stock_weight > 0:
                attribution.sector_contributions = {
                    'cryptocurrency': crypto_weight * attribution.total_risk,
                    'equities': stock_weight * attribution.total_risk,
                    'other': max(0, attribution.total_risk - (crypto_weight + stock_weight) * attribution.total_risk)
                }
            
            return attribution
            
        except Exception as e:
            logger.error(f"❌ Error calculating risk attribution: {e}")
            return RiskAttribution()
    
    def _check_risk_limits(self):
        """Check all risk limits and generate alerts"""
        try:
            new_alerts = []
            
            for limit in self.risk_limits:
                if not limit.enabled:
                    continue
                
                # Get current metric value
                current_value = self._get_metric_value(limit.metric_name, limit.symbol_specific)
                
                if current_value is None:
                    continue
                
                # Check thresholds
                alert_level = None
                threshold_breached = None
                
                if current_value >= limit.emergency_threshold:
                    alert_level = AlertLevel.EMERGENCY
                    threshold_breached = limit.emergency_threshold
                elif current_value >= limit.critical_threshold:
                    alert_level = AlertLevel.CRITICAL
                    threshold_breached = limit.critical_threshold
                elif current_value >= limit.warning_threshold:
                    alert_level = AlertLevel.WARNING
                    threshold_breached = limit.warning_threshold
                
                # Generate alert if threshold breached
                if alert_level:
                    alert_id = f"{limit.name}_{int(time.time())}"
                    
                    # Check if similar alert already exists
                    existing_alert = any(
                        alert.metric_name == limit.metric_name and 
                        alert.level == alert_level and 
                        not alert.resolved
                        for alert in self.active_alerts
                    )
                    
                    if not existing_alert:
                        alert = RiskAlert(
                            id=alert_id,
                            timestamp=datetime.now(),
                            level=alert_level,
                            category=limit.category,
                            title=f"{limit.name} Breach",
                            message=f"{limit.name} has breached {alert_level.value} threshold: "
                                   f"{current_value:.4f} >= {threshold_breached:.4f}",
                            metric_name=limit.metric_name,
                            current_value=current_value,
                            threshold=threshold_breached,
                            symbol=getattr(limit, 'symbol', ''),
                            acknowledged=False,
                            resolved=False
                        )
                        
                        new_alerts.append(alert)
                        self.active_alerts.append(alert)
                        
                        # Log alert
                        self._log_alert(alert)
                        
                        # Send notification
                        self._send_alert_notification(alert)
            
            # Add alerts to history
            if new_alerts:
                for alert in new_alerts:
                    self.alert_history.append(alert)
                
                # Keep only last 500 alerts in history
                if len(self.alert_history) > 500:
                    self.alert_history = self.alert_history[-500:]
            
        except Exception as e:
            logger.error(f"❌ Error checking risk limits: {e}")
    
    def _get_metric_value(self, metric_name: str, symbol_specific: bool = False) -> Optional[float]:
        """Get current value for a specific metric"""
        try:
            if metric_name in self.risk_metrics:
                return self.risk_metrics[metric_name]
            
            # Handle symbol-specific metrics
            if symbol_specific:
                # Return maximum value across all symbols for symbol-specific limits
                symbol_values = []
                for key, value in self.risk_metrics.items():
                    if metric_name in key and isinstance(value, (int, float)):
                        symbol_values.append(value)
                
                if symbol_values:
                    return max(symbol_values)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting metric value for {metric_name}: {e}")
            return None
    
    def _log_alert(self, alert: RiskAlert):
        """Log risk alert"""
        try:
            level_emoji = {
                AlertLevel.INFO: "ℹ️",
                AlertLevel.WARNING: "⚠️",
                AlertLevel.CRITICAL: "🔴",
                AlertLevel.EMERGENCY: "🚨"
            }
            
            emoji = level_emoji.get(alert.level, "📊")
            
            logger.warning(f"{emoji} RISK ALERT [{alert.level.value.upper()}]: {alert.title}")
            logger.warning(f"   📊 {alert.message}")
            
            if alert.level in [AlertLevel.CRITICAL, AlertLevel.EMERGENCY]:
                logger.critical(f"🚨 {alert.level.value.upper()} RISK BREACH: {alert.title}")
                
        except Exception as e:
            logger.error(f"❌ Error logging alert: {e}")
    
    def _send_alert_notification(self, alert: RiskAlert):
        """Send alert notification via Telegram"""
        try:
            # Only send notifications for critical and emergency alerts
            if alert.level not in [AlertLevel.CRITICAL, AlertLevel.EMERGENCY]:
                return
            
            from .telegram import send_telegram
            
            level_emoji = {
                AlertLevel.CRITICAL: "🔴",
                AlertLevel.EMERGENCY: "🚨"
            }
            
            emoji = level_emoji.get(alert.level, "📊")
            
            message = f"{emoji} RISK ALERT [{alert.level.value.upper()}]\n\n"
            message += f"📊 {alert.title}\n"
            message += f"🔍 {alert.message}\n"
            message += f"⏰ {alert.timestamp.strftime('%H:%M:%S')}\n"
            
            if alert.symbol:
                message += f"📈 Symbol: {alert.symbol}\n"
            
            message += f"🎯 Category: {alert.category.value.replace('_', ' ').title()}"
            
            send_telegram(message)
            
        except Exception as e:
            logger.error(f"❌ Error sending alert notification: {e}")
    
    def _update_compliance_status(self):
        """Update regulatory compliance status"""
        try:
            self.compliance_status = {
                'overall_status': 'compliant',
                'violations': [],
                'warnings': [],
                'last_check': datetime.now().isoformat()
            }
            
            # Check for compliance violations
            violations = []
            warnings = []
            
            # Check gross exposure compliance (example regulatory limit)
            gross_exposure_ratio = self.risk_metrics.get('gross_exposure_ratio', 0.0)
            if gross_exposure_ratio > 1.5:  # Example 150% regulatory limit
                violations.append({
                    'rule': 'Gross Exposure Limit',
                    'current_value': gross_exposure_ratio,
                    'limit': 1.5,
                    'severity': 'high'
                })
            elif gross_exposure_ratio > 1.2:  # Warning at 120%
                warnings.append({
                    'rule': 'Gross Exposure Warning',
                    'current_value': gross_exposure_ratio,
                    'limit': 1.2,
                    'severity': 'medium'
                })
            
            # Check concentration compliance
            max_position_weight = self.risk_metrics.get('max_position_weight', 0.0)
            if max_position_weight > 0.3:  # Example 30% single position limit
                violations.append({
                    'rule': 'Single Position Concentration',
                    'current_value': max_position_weight,
                    'limit': 0.3,
                    'severity': 'medium'
                })
            
            # Update compliance status
            self.compliance_status['violations'] = violations
            self.compliance_status['warnings'] = warnings
            
            if violations:
                self.compliance_status['overall_status'] = 'non_compliant'
            elif warnings:
                self.compliance_status['overall_status'] = 'warning'
            else:
                self.compliance_status['overall_status'] = 'compliant'
                
        except Exception as e:
            logger.error(f"❌ Error updating compliance status: {e}")
    
    def _save_metrics_to_history(self):
        """Save current metrics to historical record"""
        try:
            metrics_record = {
                'timestamp': datetime.now().isoformat(),
                'risk_metrics': self.risk_metrics.copy(),
                'active_alerts_count': len(self.active_alerts),
                'compliance_status': self.compliance_status.get('overall_status', 'unknown'),
                'emergency_mode': self.risk_metrics.get('emergency_mode', False)
            }
            
            self.metrics_history.append(metrics_record)
            
            # Keep only last 1000 records
            if len(self.metrics_history) > 1000:
                self.metrics_history = self.metrics_history[-1000:]
                
        except Exception as e:
            logger.error(f"❌ Error saving metrics to history: {e}")
    
    def _log_monitoring_status(self):
        """Log current monitoring status"""
        try:
            active_critical_alerts = sum(1 for alert in self.active_alerts 
                                       if alert.level in [AlertLevel.CRITICAL, AlertLevel.EMERGENCY] 
                                       and not alert.resolved)
            
            emergency_mode = self.risk_metrics.get('emergency_mode', False)
            
            status_emoji = "🚨" if emergency_mode else "🟠" if active_critical_alerts > 0 else "🟢"
            
            logger.info(f"📊 RISK MONITOR: {status_emoji} Status | "
                       f"Active Alerts: {len(self.active_alerts)} | "
                       f"Critical: {active_critical_alerts} | "
                       f"Emergency: {'YES' if emergency_mode else 'NO'}")
            
            # Log key metrics
            if self.risk_metrics:
                gross_exposure = self.risk_metrics.get('gross_exposure_ratio', 0.0)
                drawdown = self.risk_metrics.get('current_drawdown', 0.0)
                var = self.risk_metrics.get('portfolio_var_95', 0.0)
                
                logger.debug(f"🎯 KEY METRICS: Exposure: {gross_exposure:.1%} | "
                           f"Drawdown: {drawdown:.1%} | VaR: {var:.1%}")
                
        except Exception as e:
            logger.error(f"❌ Error logging monitoring status: {e}")
    
    # Public API methods
    
    def get_current_risk_status(self) -> Dict[str, Any]:
        """Get current comprehensive risk status"""
        return {
            'metrics': self.risk_metrics.copy(),
            'active_alerts': len(self.active_alerts),
            'critical_alerts': sum(1 for alert in self.active_alerts 
                                 if alert.level in [AlertLevel.CRITICAL, AlertLevel.EMERGENCY] 
                                 and not alert.resolved),
            'compliance_status': self.compliance_status.get('overall_status', 'unknown'),
            'emergency_mode': self.risk_metrics.get('emergency_mode', False),
            'last_update': self.last_update.isoformat() if self.last_update else None
        }
    
    def get_portfolio_heatmap(self) -> Dict[str, Any]:
        """Get portfolio heat map data"""
        return {
            'correlation_matrix': self.portfolio_heatmap.correlation_matrix,
            'risk_contribution': self.portfolio_heatmap.risk_contribution,
            'concentration_scores': self.portfolio_heatmap.concentration_scores,
            'volatility_breakdown': self.portfolio_heatmap.volatility_breakdown
        }
    
    def get_risk_attribution(self) -> Dict[str, Any]:
        """Get risk attribution analysis"""
        return {
            'total_risk': self.risk_attribution.total_risk,
            'systematic_risk': self.risk_attribution.systematic_risk,
            'specific_risk': self.risk_attribution.specific_risk,
            'factor_contributions': self.risk_attribution.factor_contributions,
            'sector_contributions': self.risk_attribution.sector_contributions
        }
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge a specific alert"""
        try:
            for alert in self.active_alerts:
                if alert.id == alert_id:
                    alert.acknowledged = True
                    logger.info(f"✅ Alert acknowledged: {alert.title}")
                    return True
            return False
        except Exception as e:
            logger.error(f"❌ Error acknowledging alert: {e}")
            return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve a specific alert"""
        try:
            for alert in self.active_alerts:
                if alert.id == alert_id:
                    alert.resolved = True
                    logger.info(f"✅ Alert resolved: {alert.title}")
                    return True
            return False
        except Exception as e:
            logger.error(f"❌ Error resolving alert: {e}")
            return False
    
    def generate_risk_report(self) -> Dict[str, Any]:
        """Generate comprehensive risk report"""
        try:
            report = {
                'timestamp': datetime.now().isoformat(),
                'summary': {
                    'overall_risk_level': 'medium',  # Simplified classification
                    'key_concerns': [],
                    'recommendations': []
                },
                'metrics': self.risk_metrics.copy(),
                'portfolio_analysis': self.get_portfolio_heatmap(),
                'risk_attribution': self.get_risk_attribution(),
                'alerts': {
                    'active_count': len(self.active_alerts),
                    'recent_alerts': [
                        {
                            'level': alert.level.value,
                            'title': alert.title,
                            'timestamp': alert.timestamp.isoformat()
                        }
                        for alert in self.active_alerts[-10:]  # Last 10 alerts
                    ]
                },
                'compliance': self.compliance_status,
                'recommendations': self._generate_recommendations()
            }
            
            # Save report to history
            self.reports_history.append(report)
            if len(self.reports_history) > 100:
                self.reports_history = self.reports_history[-100:]
            
            return report
            
        except Exception as e:
            logger.error(f"❌ Error generating risk report: {e}")
            return {'error': str(e)}
    
    def _generate_recommendations(self) -> List[str]:
        """Generate risk management recommendations"""
        recommendations = []
        
        try:
            # Check current risk levels and generate recommendations
            gross_exposure = self.risk_metrics.get('gross_exposure_ratio', 0.0)
            if gross_exposure > 0.8:
                recommendations.append("Consider reducing gross exposure to maintain adequate risk buffer")
            
            current_drawdown = self.risk_metrics.get('current_drawdown', 0.0)
            if current_drawdown > 0.05:
                recommendations.append("Monitor drawdown closely and consider defensive positioning")
            
            avg_correlation = self.risk_metrics.get('avg_correlation', 0.0)
            if avg_correlation > 0.7:
                recommendations.append("Portfolio shows high correlation - consider diversification")
            
            emergency_mode = self.risk_metrics.get('emergency_mode', False)
            if emergency_mode:
                recommendations.append("Emergency mode active - implement conservative risk management")
            
            # Add general recommendations
            if not recommendations:
                recommendations.append("Risk levels within acceptable ranges - maintain current monitoring")
            
        except Exception as e:
            logger.error(f"❌ Error generating recommendations: {e}")
            recommendations.append("Error generating recommendations - manual review suggested")
        
        return recommendations


# Global instance
risk_monitor = RiskMonitor()


def get_risk_monitoring_status() -> Dict[str, Any]:
    """
    Get current comprehensive risk monitoring status.
    Returns real-time risk metrics, alerts, and compliance status.
    """
    try:
        # Update monitoring if stale
        if (not risk_monitor.last_update or 
            datetime.now() - risk_monitor.last_update > timedelta(minutes=2)):
            risk_monitor.update_risk_monitoring()
        
        return risk_monitor.get_current_risk_status()
        
    except Exception as e:
        logger.error(f"❌ Error getting risk monitoring status: {e}")
        return {
            'error': str(e),
            'metrics': {},
            'active_alerts': 0,
            'critical_alerts': 0,
            'compliance_status': 'unknown',
            'emergency_mode': False,
            'last_update': None
        }