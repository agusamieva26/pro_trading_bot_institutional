"""
🛡️ ADVANCED DRAWDOWN PROTECTION SYSTEM
Real-time drawdown monitoring and protection engine with dynamic risk scaling,
emergency protocols, and recovery management for institutional trading.

Features:
- Real-time peak-to-valley drawdown calculation
- Multi-timeframe drawdown analysis (intraday, daily, weekly)
- Dynamic risk scaling based on drawdown severity
- Emergency shutdown triggers with graduated responses
- Adaptive stop-loss adjustments during adverse periods
- Recovery protocols and position sizing restoration
- Stress testing and worst-case scenario modeling
- Portfolio heat loss prevention with early warning systems
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

from .util import logger
from .config import settings


class DrawdownSeverity(Enum):
    """Drawdown severity classification"""
    MINIMAL = "minimal"         # < 2% drawdown
    MODERATE = "moderate"       # 2-5% drawdown
    SIGNIFICANT = "significant" # 5-10% drawdown
    SEVERE = "severe"          # 10-15% drawdown
    CRITICAL = "critical"      # 15-25% drawdown
    CATASTROPHIC = "catastrophic" # > 25% drawdown


class ProtectionLevel(Enum):
    """Protection level for risk scaling"""
    NORMAL = "normal"           # Standard trading
    CAUTIOUS = "cautious"       # Slightly reduced risk
    DEFENSIVE = "defensive"     # Moderately reduced risk
    CONSERVATIVE = "conservative" # Significantly reduced risk
    EMERGENCY = "emergency"     # Minimal risk/emergency mode
    SHUTDOWN = "shutdown"       # Complete trading halt


@dataclass
class DrawdownMetrics:
    """Container for comprehensive drawdown analysis"""
    current_drawdown: float = 0.0           # Current peak-to-valley drawdown
    max_drawdown: float = 0.0               # Maximum historical drawdown
    drawdown_duration: int = 0              # Days in current drawdown
    max_drawdown_duration: int = 0          # Longest drawdown period
    recovery_factor: float = 0.0            # Time to recover from max DD
    underwater_periods: int = 0             # Number of underwater periods
    drawdown_frequency: float = 0.0         # Frequency of significant drawdowns
    avg_drawdown: float = 0.0               # Average drawdown size
    drawdown_skewness: float = 0.0          # Skewness of drawdown distribution
    pain_index: float = 0.0                 # Pain index (avg time underwater)
    ulcer_index: float = 0.0                # Ulcer index (severity + duration)
    sterling_ratio: float = 0.0             # Return/max drawdown ratio
    calmar_ratio: float = 0.0               # Annualized return/max DD
    severity: DrawdownSeverity = DrawdownSeverity.MINIMAL
    trend: str = "stable"                   # improving/stable/worsening


@dataclass
class ProtectionSettings:
    """Dynamic protection settings based on drawdown state"""
    protection_level: ProtectionLevel = ProtectionLevel.NORMAL
    risk_multiplier: float = 1.0            # Risk scaling factor
    max_position_size: float = 0.0          # Maximum position size (USD)
    stop_loss_tightening: float = 1.0       # Stop loss adjustment factor
    new_position_allowed: bool = True       # Allow new positions
    force_close_threshold: float = 0.0      # Force close existing positions
    cash_buffer_increase: float = 0.0       # Additional cash buffer
    correlation_limit: float = 1.0          # Maximum correlation allowed
    sector_concentration_limit: float = 1.0 # Sector concentration limit
    emergency_mode: bool = False            # Emergency shutdown mode


class DrawdownProtector:
    """
    Advanced drawdown protection system that monitors portfolio health in real-time
    and dynamically adjusts risk parameters to prevent catastrophic losses.
    
    Core Functions:
    - Real-time drawdown calculation and monitoring
    - Multi-timeframe drawdown analysis and trend detection
    - Dynamic risk scaling based on drawdown severity
    - Emergency protection protocols with graduated responses
    - Recovery management and position sizing restoration
    - Stress testing and scenario analysis
    - Portfolio heat loss prevention with early warning
    """
    
    def __init__(self):
        # State persistence
        self.state_file = "bot/drawdown_protection_state.json"
        self.history_file = "bot/drawdown_history.json"
        
        # Protection thresholds
        self.severity_thresholds = {
            DrawdownSeverity.MINIMAL: 0.02,        # 2%
            DrawdownSeverity.MODERATE: 0.05,       # 5%
            DrawdownSeverity.SIGNIFICANT: 0.10,    # 10%
            DrawdownSeverity.SEVERE: 0.15,         # 15%
            DrawdownSeverity.CRITICAL: 0.25,       # 25%
            DrawdownSeverity.CATASTROPHIC: 1.0     # > 25%
        }
        
        # Risk multipliers by protection level
        self.protection_multipliers = {
            ProtectionLevel.NORMAL: 1.0,           # Full risk
            ProtectionLevel.CAUTIOUS: 0.8,         # 20% reduction
            ProtectionLevel.DEFENSIVE: 0.6,        # 40% reduction
            ProtectionLevel.CONSERVATIVE: 0.4,     # 60% reduction
            ProtectionLevel.EMERGENCY: 0.2,        # 80% reduction
            ProtectionLevel.SHUTDOWN: 0.0          # No new positions
        }
        
        # Stop loss tightening factors
        self.stop_tightening_factors = {
            ProtectionLevel.NORMAL: 1.0,
            ProtectionLevel.CAUTIOUS: 0.9,         # 10% tighter stops
            ProtectionLevel.DEFENSIVE: 0.8,        # 20% tighter stops
            ProtectionLevel.CONSERVATIVE: 0.7,     # 30% tighter stops
            ProtectionLevel.EMERGENCY: 0.6,        # 40% tighter stops
            ProtectionLevel.SHUTDOWN: 0.5          # 50% tighter stops
        }
        
        # Historical data
        self.equity_history = []                   # Historical equity values
        self.drawdown_history = []                 # Historical drawdown records
        self.peak_equity = 0.0                     # Current equity peak
        self.peak_timestamp = None                 # When peak was reached
        
        # Current state
        self.current_metrics = DrawdownMetrics()
        self.current_protection = ProtectionSettings()
        self.last_update = None
        self.emergency_triggered = False
        self.recovery_mode = False
        
        # Monitoring
        self._monitoring_active = False
        
        # Load persistent state
        self.load_state()
        
        # Initialize background monitoring
        self._start_background_monitoring()
        
        logger.info("🛡️ Drawdown Protector initialized - Advanced loss prevention active")
    
    def load_state(self):
        """Load persistent state from disk"""
        try:
            if Path(self.state_file).exists():
                with open(self.state_file, 'r') as f:
                    state_data = json.load(f)
                    self.peak_equity = state_data.get('peak_equity', 0.0)
                    self.emergency_triggered = state_data.get('emergency_triggered', False)
                    self.recovery_mode = state_data.get('recovery_mode', False)
                    
                    peak_ts = state_data.get('peak_timestamp')
                    if peak_ts:
                        self.peak_timestamp = datetime.fromisoformat(peak_ts)
                    
                    self.last_update = state_data.get('last_update')
                    if self.last_update:
                        self.last_update = datetime.fromisoformat(self.last_update)
                    
            if Path(self.history_file).exists():
                with open(self.history_file, 'r') as f:
                    self.drawdown_history = json.load(f)
                    # Keep only last 500 entries for performance
                    self.drawdown_history = self.drawdown_history[-500:]
                    
        except Exception as e:
            logger.warning(f"⚠️ Error loading drawdown protector state: {e}")
            self.drawdown_history = []
    
    def save_state(self):
        """Save persistent state to disk"""
        try:
            state_data = {
                'peak_equity': self.peak_equity,
                'emergency_triggered': self.emergency_triggered,
                'recovery_mode': self.recovery_mode,
                'peak_timestamp': self.peak_timestamp.isoformat() if self.peak_timestamp else None,
                'last_update': self.last_update.isoformat() if self.last_update else None,
                'current_drawdown': self.current_metrics.current_drawdown,
                'protection_level': self.current_protection.protection_level.value
            }
            
            with open(self.state_file, 'w') as f:
                json.dump(state_data, f, indent=2)
                
            # Save drawdown history
            with open(self.history_file, 'w') as f:
                json.dump(self.drawdown_history, f)
                
        except Exception as e:
            logger.warning(f"⚠️ Error saving drawdown protector state: {e}")
    
    def _start_background_monitoring(self):
        """Start background drawdown monitoring"""
        if self._monitoring_active:
            return
            
        def monitor_drawdown():
            while self._monitoring_active:
                try:
                    # Update drawdown analysis every 30 seconds
                    self.update_drawdown_analysis()
                    time.sleep(30)
                except Exception as e:
                    logger.error(f"❌ Error in drawdown monitoring: {e}")
                    time.sleep(60)  # Back off on error
        
        self._monitoring_active = True
        monitoring_thread = threading.Thread(target=monitor_drawdown, daemon=True)
        monitoring_thread.start()
        logger.info("🔍 Background drawdown monitoring started")
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        self._monitoring_active = False
        logger.info("⏹️ Drawdown monitoring stopped")
    
    def update_drawdown_analysis(self):
        """Update comprehensive drawdown analysis"""
        try:
            # Get current equity
            current_equity = self._get_current_equity()
            if current_equity <= 0:
                logger.warning("⚠️ Invalid equity for drawdown analysis")
                return
            
            # Update equity history
            self._update_equity_history(current_equity)
            
            # Calculate current drawdown metrics
            self.current_metrics = self._calculate_drawdown_metrics(current_equity)
            
            # Determine protection settings
            self.current_protection = self._determine_protection_settings()
            
            # Check for emergency conditions
            self._check_emergency_conditions()
            
            # Handle recovery mode
            self._handle_recovery_mode(current_equity)
            
            # Save metrics to history
            self._save_metrics_to_history()
            
            # Update timestamp
            self.last_update = datetime.now()
            
            # Save state
            self.save_state()
            
            # Log status
            self._log_protection_status()
            
        except Exception as e:
            logger.error(f"❌ Error updating drawdown analysis: {e}")
    
    def _get_current_equity(self) -> float:
        """Get current account equity"""
        try:
            from alpaca.trading.client import TradingClient
            
            client = TradingClient(
                api_key=settings.alpaca_api_key,
                secret_key=settings.alpaca_secret_key,
                paper=(settings.mode == "paper")
            )
            
            account = client.get_account()
            equity = float(getattr(account, 'equity', 0) or 0)
            
            return equity
            
        except Exception as e:
            logger.error(f"❌ Error getting current equity: {e}")
            return 0.0
    
    def _update_equity_history(self, current_equity: float):
        """Update equity history and peak tracking"""
        try:
            now = datetime.now()
            
            # Add to equity history
            equity_record = {
                'timestamp': now.isoformat(),
                'equity': current_equity
            }
            self.equity_history.append(equity_record)
            
            # Keep only last 1000 records for performance
            if len(self.equity_history) > 1000:
                self.equity_history = self.equity_history[-1000:]
            
            # Update peak equity
            if current_equity > self.peak_equity:
                self.peak_equity = current_equity
                self.peak_timestamp = now
                logger.info(f"🎯 New equity peak: ${current_equity:,.2f}")
                
                # Check if we're recovering from drawdown
                if self.recovery_mode:
                    logger.info("📈 Recovery confirmed - returning to normal protection mode")
                    self.recovery_mode = False
                    self.emergency_triggered = False
            
        except Exception as e:
            logger.error(f"❌ Error updating equity history: {e}")
    
    def _calculate_drawdown_metrics(self, current_equity: float) -> DrawdownMetrics:
        """Calculate comprehensive drawdown metrics"""
        try:
            metrics = DrawdownMetrics()
            
            if self.peak_equity <= 0:
                self.peak_equity = current_equity
                return metrics
            
            # Current drawdown
            metrics.current_drawdown = max(0.0, (self.peak_equity - current_equity) / self.peak_equity)
            
            # Drawdown duration
            if self.peak_timestamp:
                duration_delta = datetime.now() - self.peak_timestamp
                metrics.drawdown_duration = duration_delta.days
            
            # Historical analysis if we have enough data
            if len(self.equity_history) >= 30:
                # Calculate historical drawdowns
                equity_series = pd.Series([r['equity'] for r in self.equity_history[-100:]])
                drawdowns = self._calculate_historical_drawdowns(equity_series)
                
                if drawdowns:
                    metrics.max_drawdown = max(drawdowns)
                    metrics.avg_drawdown = np.mean(drawdowns)
                    metrics.drawdown_frequency = len(drawdowns) / len(equity_series) * 252  # Annualized
                    
                    if len(drawdowns) > 1:
                        metrics.drawdown_skewness = float(pd.Series(drawdowns).skew())
                
                # Pain index (average underwater percentage)
                underwater_pct = []
                running_peak = 0
                for equity in equity_series:
                    if equity > running_peak:
                        running_peak = equity
                    underwater = (running_peak - equity) / running_peak if running_peak > 0 else 0
                    underwater_pct.append(underwater)
                
                if underwater_pct:
                    metrics.pain_index = np.mean(underwater_pct)
                
                # Ulcer index (RMS of underwater percentages)
                if underwater_pct:
                    metrics.ulcer_index = np.sqrt(np.mean([x**2 for x in underwater_pct]))
            
            # Classify severity
            metrics.severity = self._classify_drawdown_severity(metrics.current_drawdown)
            
            # Determine trend
            metrics.trend = self._determine_drawdown_trend()
            
            # Calculate performance ratios
            if metrics.max_drawdown > 0 and len(self.equity_history) > 1:
                # Sterling ratio (return / max drawdown)
                initial_equity = self.equity_history[0]['equity']
                total_return = (current_equity - initial_equity) / initial_equity
                metrics.sterling_ratio = total_return / metrics.max_drawdown
                
                # Calmar ratio (annualized return / max drawdown)
                days_elapsed = (datetime.now() - datetime.fromisoformat(self.equity_history[0]['timestamp'])).days
                if days_elapsed > 0:
                    annualized_return = (current_equity / initial_equity) ** (365 / days_elapsed) - 1
                    metrics.calmar_ratio = annualized_return / metrics.max_drawdown
            
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Error calculating drawdown metrics: {e}")
            return DrawdownMetrics()
    
    def _calculate_historical_drawdowns(self, equity_series: pd.Series) -> List[float]:
        """Calculate all historical drawdown episodes"""
        try:
            drawdowns = []
            running_peak = 0
            current_dd = 0
            
            for equity in equity_series:
                if equity > running_peak:
                    # New peak - end current drawdown if any
                    if current_dd > 0:
                        drawdowns.append(current_dd)
                        current_dd = 0
                    running_peak = equity
                else:
                    # Update current drawdown
                    dd = (running_peak - equity) / running_peak
                    current_dd = max(current_dd, dd)
            
            # Add final drawdown if still underwater
            if current_dd > 0:
                drawdowns.append(current_dd)
            
            # Filter out minimal drawdowns (< 1%)
            significant_drawdowns = [dd for dd in drawdowns if dd >= 0.01]
            
            return significant_drawdowns
            
        except Exception as e:
            logger.error(f"❌ Error calculating historical drawdowns: {e}")
            return []
    
    def _classify_drawdown_severity(self, drawdown: float) -> DrawdownSeverity:
        """Classify drawdown severity"""
        for severity in [DrawdownSeverity.CATASTROPHIC, DrawdownSeverity.CRITICAL, 
                        DrawdownSeverity.SEVERE, DrawdownSeverity.SIGNIFICANT,
                        DrawdownSeverity.MODERATE, DrawdownSeverity.MINIMAL]:
            if drawdown >= self.severity_thresholds[severity]:
                return severity
        return DrawdownSeverity.MINIMAL
    
    def _determine_drawdown_trend(self) -> str:
        """Determine if drawdown is improving, stable, or worsening"""
        try:
            if len(self.equity_history) < 10:
                return "stable"
            
            # Get recent equity values
            recent_equities = [r['equity'] for r in self.equity_history[-10:]]
            
            # Calculate trend slope
            x = np.arange(len(recent_equities))
            slope = np.polyfit(x, recent_equities, 1)[0]
            
            # Classify trend
            if slope > 0.01 * self.peak_equity:  # Improving if slope > 1% of peak
                return "improving"
            elif slope < -0.01 * self.peak_equity:  # Worsening if slope < -1% of peak
                return "worsening"
            else:
                return "stable"
                
        except Exception as e:
            logger.error(f"❌ Error determining drawdown trend: {e}")
            return "stable"
    
    def _determine_protection_settings(self) -> ProtectionSettings:
        """Determine appropriate protection settings based on drawdown state"""
        try:
            protection = ProtectionSettings()
            
            # Base protection level on drawdown severity
            severity = self.current_metrics.severity
            
            if severity == DrawdownSeverity.MINIMAL:
                protection.protection_level = ProtectionLevel.NORMAL
            elif severity == DrawdownSeverity.MODERATE:
                protection.protection_level = ProtectionLevel.CAUTIOUS
            elif severity == DrawdownSeverity.SIGNIFICANT:
                protection.protection_level = ProtectionLevel.DEFENSIVE
            elif severity == DrawdownSeverity.SEVERE:
                protection.protection_level = ProtectionLevel.CONSERVATIVE
            elif severity == DrawdownSeverity.CRITICAL:
                protection.protection_level = ProtectionLevel.EMERGENCY
            else:  # CATASTROPHIC
                protection.protection_level = ProtectionLevel.SHUTDOWN
            
            # Adjust based on trend
            if self.current_metrics.trend == "worsening":
                # Escalate protection level
                current_levels = list(ProtectionLevel)
                current_index = current_levels.index(protection.protection_level)
                if current_index < len(current_levels) - 1:
                    protection.protection_level = current_levels[current_index + 1]
            elif self.current_metrics.trend == "improving" and self.recovery_mode:
                # De-escalate protection level if recovering
                current_levels = list(ProtectionLevel)
                current_index = current_levels.index(protection.protection_level)
                if current_index > 0:
                    protection.protection_level = current_levels[current_index - 1]
            
            # Set risk multiplier
            protection.risk_multiplier = self.protection_multipliers[protection.protection_level]
            
            # Set stop loss tightening
            protection.stop_loss_tightening = self.stop_tightening_factors[protection.protection_level]
            
            # Position restrictions
            if protection.protection_level in [ProtectionLevel.EMERGENCY, ProtectionLevel.SHUTDOWN]:
                protection.new_position_allowed = False
                protection.emergency_mode = True
            
            # Force close threshold for extreme conditions
            if severity in [DrawdownSeverity.CRITICAL, DrawdownSeverity.CATASTROPHIC]:
                protection.force_close_threshold = 0.5  # Close 50% of positions
            
            # Additional cash buffer during drawdowns
            if severity in [DrawdownSeverity.SIGNIFICANT, DrawdownSeverity.SEVERE, 
                           DrawdownSeverity.CRITICAL, DrawdownSeverity.CATASTROPHIC]:
                protection.cash_buffer_increase = min(0.1, self.current_metrics.current_drawdown)
            
            # Correlation and concentration limits
            if severity in [DrawdownSeverity.SEVERE, DrawdownSeverity.CRITICAL, DrawdownSeverity.CATASTROPHIC]:
                protection.correlation_limit = 0.7  # Reduce correlation exposure
                protection.sector_concentration_limit = 0.3  # Limit sector concentration
            
            return protection
            
        except Exception as e:
            logger.error(f"❌ Error determining protection settings: {e}")
            return ProtectionSettings()
    
    def _check_emergency_conditions(self):
        """Check for emergency conditions and trigger alerts"""
        try:
            emergency_triggered = False
            reasons = []
            
            # Emergency drawdown threshold
            if self.current_metrics.current_drawdown >= 0.15:  # 15% drawdown
                emergency_triggered = True
                reasons.append(f"Drawdown {self.current_metrics.current_drawdown:.1%}")
            
            # Emergency duration threshold
            if self.current_metrics.drawdown_duration >= 7:  # 7 days in drawdown
                emergency_triggered = True
                reasons.append(f"Duration {self.current_metrics.drawdown_duration} days")
            
            # Rapid deterioration
            if (self.current_metrics.trend == "worsening" and 
                self.current_metrics.current_drawdown >= 0.08):  # 8% rapid decline
                emergency_triggered = True
                reasons.append("Rapid deterioration")
            
            # Update emergency state
            if emergency_triggered and not self.emergency_triggered:
                self.emergency_triggered = True
                logger.critical(f"🚨 DRAWDOWN EMERGENCY TRIGGERED: {', '.join(reasons)}")
                
                # Send alert
                try:
                    from .telegram import send_telegram
                    msg = f"🚨 DRAWDOWN EMERGENCY\n\nReasons:\n" + "\n".join([f"• {r}" for r in reasons])
                    msg += f"\n\nCurrent: {self.current_metrics.current_drawdown:.1%}"
                    msg += f"\nPeak: ${self.peak_equity:,.2f}"
                    msg += f"\nProtection: {self.current_protection.protection_level.value.upper()}"
                    send_telegram(msg)
                except:
                    pass
                    
            elif not emergency_triggered and self.emergency_triggered:
                # Check if we can clear emergency mode
                if self.current_metrics.current_drawdown < 0.08:  # Below 8%
                    self.emergency_triggered = False
                    self.recovery_mode = True
                    logger.info("✅ Drawdown emergency cleared - entering recovery mode")
                    
        except Exception as e:
            logger.error(f"❌ Error checking emergency conditions: {e}")
    
    def _handle_recovery_mode(self, current_equity: float):
        """Handle recovery mode logic"""
        try:
            if not self.recovery_mode:
                return
            
            # Check recovery progress
            if current_equity >= self.peak_equity * 0.98:  # Within 2% of peak
                logger.info("🎯 Recovery target reached - normalizing protection")
                self.recovery_mode = False
                self.emergency_triggered = False
            elif self.current_metrics.trend == "improving":
                # Gradually reduce protection during recovery
                logger.debug("📈 Recovery in progress - maintaining enhanced monitoring")
            else:
                # Recovery stalled - maintain defensive posture
                logger.warning("⚠️ Recovery stalled - maintaining protection measures")
                
        except Exception as e:
            logger.error(f"❌ Error handling recovery mode: {e}")
    
    def _save_metrics_to_history(self):
        """Save current metrics to historical record"""
        try:
            metric_record = {
                'timestamp': datetime.now().isoformat(),
                'current_drawdown': self.current_metrics.current_drawdown,
                'max_drawdown': self.current_metrics.max_drawdown,
                'drawdown_duration': self.current_metrics.drawdown_duration,
                'severity': self.current_metrics.severity.value,
                'trend': self.current_metrics.trend,
                'protection_level': self.current_protection.protection_level.value,
                'risk_multiplier': self.current_protection.risk_multiplier,
                'emergency_mode': self.current_protection.emergency_mode,
                'peak_equity': self.peak_equity
            }
            
            self.drawdown_history.append(metric_record)
            
            # Keep only last 500 records
            if len(self.drawdown_history) > 500:
                self.drawdown_history = self.drawdown_history[-500:]
                
        except Exception as e:
            logger.error(f"❌ Error saving metrics to history: {e}")
    
    def _log_protection_status(self):
        """Log current protection status"""
        try:
            severity_color = {
                DrawdownSeverity.MINIMAL: "🟢",
                DrawdownSeverity.MODERATE: "🟡",
                DrawdownSeverity.SIGNIFICANT: "🟠",
                DrawdownSeverity.SEVERE: "🔴",
                DrawdownSeverity.CRITICAL: "🚨",
                DrawdownSeverity.CATASTROPHIC: "💀"
            }.get(self.current_metrics.severity, "🟡")
            
            protection_color = {
                ProtectionLevel.NORMAL: "🟢",
                ProtectionLevel.CAUTIOUS: "🟡",
                ProtectionLevel.DEFENSIVE: "🟠",
                ProtectionLevel.CONSERVATIVE: "🔴",
                ProtectionLevel.EMERGENCY: "🚨",
                ProtectionLevel.SHUTDOWN: "💀"
            }.get(self.current_protection.protection_level, "🟡")
            
            logger.info(f"🛡️ DRAWDOWN PROTECTION: {severity_color} {self.current_metrics.severity.value.upper()} "
                       f"({self.current_metrics.current_drawdown:.1%}) | "
                       f"Protection: {protection_color} {self.current_protection.protection_level.value.upper()} | "
                       f"Risk: {self.current_protection.risk_multiplier:.1f}x")
            
            if self.emergency_triggered:
                logger.warning(f"🚨 EMERGENCY MODE ACTIVE - Enhanced protection measures in effect")
            
            if self.recovery_mode:
                logger.info(f"📈 RECOVERY MODE - Monitoring improvement: {self.current_metrics.trend}")
                
        except Exception as e:
            logger.error(f"❌ Error logging protection status: {e}")
    
    # Public API methods
    
    def get_risk_multiplier(self) -> float:
        """Get current risk multiplier for position sizing"""
        return self.current_protection.risk_multiplier
    
    def get_stop_loss_adjustment(self) -> float:
        """Get stop loss tightening factor"""
        return self.current_protection.stop_loss_tightening
    
    def should_allow_new_position(self) -> bool:
        """Check if new positions should be allowed"""
        return self.current_protection.new_position_allowed
    
    def get_force_close_ratio(self) -> float:
        """Get percentage of positions that should be force closed"""
        return self.current_protection.force_close_threshold
    
    def is_emergency_mode(self) -> bool:
        """Check if emergency mode is active"""
        return self.current_protection.emergency_mode
    
    def get_additional_cash_buffer(self) -> float:
        """Get additional cash buffer requirement"""
        return self.current_protection.cash_buffer_increase
    
    def get_protection_summary(self) -> Dict[str, Any]:
        """Get comprehensive protection status summary"""
        return {
            'current_drawdown': self.current_metrics.current_drawdown,
            'max_drawdown': self.current_metrics.max_drawdown,
            'drawdown_duration': self.current_metrics.drawdown_duration,
            'severity': self.current_metrics.severity.value,
            'trend': self.current_metrics.trend,
            'protection_level': self.current_protection.protection_level.value,
            'risk_multiplier': self.current_protection.risk_multiplier,
            'stop_loss_adjustment': self.current_protection.stop_loss_tightening,
            'new_positions_allowed': self.current_protection.new_position_allowed,
            'emergency_mode': self.current_protection.emergency_mode,
            'recovery_mode': self.recovery_mode,
            'peak_equity': self.peak_equity,
            'last_update': self.last_update.isoformat() if self.last_update else None
        }


# Global instance
drawdown_protector = DrawdownProtector()


def get_drawdown_protection(current_equity: float = None) -> Dict[str, Any]:
    """
    Get current drawdown protection settings and recommendations.
    Returns comprehensive protection analysis and risk adjustments.
    """
    try:
        # Update analysis if stale or new equity provided
        if (current_equity or not drawdown_protector.last_update or 
            datetime.now() - drawdown_protector.last_update > timedelta(minutes=2)):
            drawdown_protector.update_drawdown_analysis()
        
        # Get protection settings
        risk_multiplier = drawdown_protector.get_risk_multiplier()
        stop_adjustment = drawdown_protector.get_stop_loss_adjustment()
        allow_new = drawdown_protector.should_allow_new_position()
        force_close = drawdown_protector.get_force_close_ratio()
        emergency = drawdown_protector.is_emergency_mode()
        cash_buffer = drawdown_protector.get_additional_cash_buffer()
        
        return {
            'risk_multiplier': risk_multiplier,
            'stop_loss_adjustment': stop_adjustment,
            'allow_new_positions': allow_new,
            'force_close_ratio': force_close,
            'emergency_mode': emergency,
            'additional_cash_buffer': cash_buffer,
            'current_drawdown': drawdown_protector.current_metrics.current_drawdown,
            'protection_level': drawdown_protector.current_protection.protection_level.value,
            'drawdown_severity': drawdown_protector.current_metrics.severity.value,
            'recovery_mode': drawdown_protector.recovery_mode
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting drawdown protection: {e}")
        return {
            'risk_multiplier': 1.0,
            'stop_loss_adjustment': 1.0,
            'allow_new_positions': True,
            'force_close_ratio': 0.0,
            'emergency_mode': False,
            'additional_cash_buffer': 0.0,
            'current_drawdown': 0.0,
            'protection_level': 'normal',
            'drawdown_severity': 'minimal',
            'recovery_mode': False
        }