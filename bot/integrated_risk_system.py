"""
🏛️ INTEGRATED INSTITUTIONAL RISK MANAGEMENT SYSTEM
Unified interface that coordinates all dynamic risk management components
with the existing trading infrastructure for professional-grade risk control.

Features:
- Unified risk management interface for all trading operations
- Real-time integration of all risk management components
- Institutional-grade risk scaling and position sizing
- Emergency protocols and circuit breakers
- Comprehensive risk monitoring and alerting
- Performance attribution and risk-adjusted optimization
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import json
import warnings
from pathlib import Path

from .util import logger
from .config import settings


@dataclass
class IntegratedRiskAssessment:
    """Comprehensive risk assessment from all components"""
    # Risk multipliers from different components
    dynamic_risk_multiplier: float = 1.0        # From dynamic risk manager
    volatility_multiplier: float = 1.0          # From volatility assessor
    drawdown_multiplier: float = 1.0            # From drawdown protector
    performance_multiplier: float = 1.0         # From performance adapter
    final_risk_multiplier: float = 1.0          # Combined final multiplier
    
    # Position sizing recommendations
    max_position_size_usd: float = 0.0          # Maximum position size
    recommended_shares: float = 0.0             # Recommended shares
    confidence_threshold: float = 0.5           # Signal confidence threshold
    
    # Risk management flags
    allow_new_positions: bool = True            # Allow new positions
    emergency_mode: bool = False                # Emergency mode active
    force_close_positions: bool = False         # Force close existing positions
    force_close_ratio: float = 0.0              # Percentage to force close
    
    # Stop loss and take profit adjustments
    stop_loss_adjustment: float = 1.0           # Stop loss tightening factor
    take_profit_adjustment: float = 1.0         # Take profit adjustment factor
    
    # Risk metrics
    portfolio_var_95: float = 0.0               # Portfolio 95% VaR
    current_drawdown: float = 0.0               # Current drawdown
    risk_score: float = 0.5                     # Composite risk score
    volatility_regime: str = "normal"           # Volatility regime
    
    # Compliance and monitoring
    compliance_status: str = "compliant"        # Compliance status
    active_alerts: int = 0                      # Number of active alerts
    last_update: Optional[datetime] = None      # Last assessment time


class IntegratedRiskSystem:
    """
    Unified institutional-grade risk management system that coordinates all
    risk management components and provides a single interface for trading operations.
    
    Core Functions:
    - Unified risk assessment combining all risk components
    - Intelligent position sizing with multi-factor risk scaling
    - Real-time emergency protocols and circuit breakers
    - Comprehensive risk monitoring and alerting
    - Performance attribution and risk-adjusted optimization
    - Institutional compliance and reporting
    """
    
    def __init__(self):
        # Initialize risk management components
        self._initialize_risk_components()
        
        # State tracking
        self.last_assessment = None
        self.assessment_cache = None
        self.cache_duration = timedelta(seconds=30)  # Cache for 30 seconds
        
        # Emergency state
        self.system_emergency_mode = False
        self.emergency_triggered_time = None
        self.emergency_reasons = []
        
        # Integration state
        self.integration_active = True
        self.legacy_fallback = False
        
        logger.info("🏛️ Integrated Risk System initialized - Institutional-grade risk management active")
    
    def _initialize_risk_components(self):
        """Initialize all risk management components"""
        try:
            # Import and initialize all risk components
            from .dynamic_risk_manager import dynamic_risk_manager
            from .volatility_assessor import volatility_assessor
            from .drawdown_protector import drawdown_protector
            from .performance_adapter import performance_adapter
            from .risk_monitor import risk_monitor
            
            self.dynamic_risk_manager = dynamic_risk_manager
            self.volatility_assessor = volatility_assessor
            self.drawdown_protector = drawdown_protector
            self.performance_adapter = performance_adapter
            self.risk_monitor = risk_monitor
            
            logger.info("✅ All risk management components initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Error initializing risk components: {e}")
            logger.warning("⚠️ Falling back to legacy risk management")
            self.legacy_fallback = True
    
    def get_comprehensive_risk_assessment(self, symbol: str, signal_strength: float, 
                                        equity: float, price: float, atr: Optional[float] = None) -> IntegratedRiskAssessment:
        """
        Get comprehensive risk assessment for a trading decision.
        This is the main interface for all trading operations.
        """
        try:
            # Check cache validity
            if (self.assessment_cache and self.last_assessment and 
                datetime.now() - self.last_assessment < self.cache_duration):
                # Update symbol-specific values and return cached assessment
                cached = self.assessment_cache
                if price > 0:
                    cached.max_position_size_usd = min(cached.max_position_size_usd, equity * 0.15)
                    cached.recommended_shares = cached.max_position_size_usd / price
                return cached
            
            # Fallback to legacy system if components not available
            if self.legacy_fallback:
                return self._get_legacy_risk_assessment(symbol, signal_strength, equity, price, atr)
            
            # Get assessments from all components
            assessment = IntegratedRiskAssessment()
            
            # 1. 🎯 Dynamic Risk Manager Assessment
            try:
                logger.info(f"🎯 {symbol} Dynamic Risk Manager: Analyzing market conditions...")
                assessment.dynamic_risk_multiplier = self.dynamic_risk_manager.get_current_risk_multiplier()
                assessment.allow_new_positions = self.dynamic_risk_manager.should_allow_new_position(symbol, signal_strength)
                
                drm_summary = self.dynamic_risk_manager.get_risk_metrics_summary()
                assessment.emergency_mode = drm_summary.get('emergency_mode', False)
                assessment.risk_score = drm_summary.get('risk_score', 0.5)
                
                dynamic_stops = self.dynamic_risk_manager.get_dynamic_stops(symbol, signal_strength)
                assessment.stop_loss_adjustment = dynamic_stops.get('stop_loss_pct', settings.stop_loss_pct) / settings.stop_loss_pct
                assessment.take_profit_adjustment = dynamic_stops.get('take_profit_pct', settings.take_profit_pct) / settings.take_profit_pct
                
                logger.info(f"🎯 {symbol} Dynamic Risk Results: "
                           f"Multiplier={assessment.dynamic_risk_multiplier:.2f} | "
                           f"Score={assessment.risk_score:.2f} | "
                           f"Emergency={assessment.emergency_mode} | "
                           f"AllowPos={assessment.allow_new_positions}")
            except Exception as e:
                logger.warning(f"⚠️ {symbol} Dynamic Risk Manager error: {e}")
                assessment.dynamic_risk_multiplier = 0.8  # Conservative fallback
            
            # 2. 🌪️ Volatility Assessor
            try:
                logger.info(f"🌪️ {symbol} Volatility Assessor: Analyzing market volatility patterns...")
                assessment.volatility_multiplier = self.volatility_assessor.get_volatility_multiplier(symbol)
                assessment.volatility_regime = self.volatility_assessor.get_volatility_regime(symbol).value
                assessment.portfolio_var_95 = self.volatility_assessor.get_var_estimate(symbol, confidence=0.95, days=1)
                
                should_reduce = self.volatility_assessor.should_reduce_exposure(symbol)
                
                logger.info(f"🌪️ {symbol} Volatility Results: "
                           f"Regime={assessment.volatility_regime} | "
                           f"Multiplier={assessment.volatility_multiplier:.2f} | "
                           f"VaR={assessment.portfolio_var_95:.3f} | "
                           f"ReduceExposure={should_reduce}")
                
                # Reduce position allowance if high volatility
                if should_reduce:
                    assessment.allow_new_positions = assessment.allow_new_positions and (assessment.volatility_multiplier > 0.7)
                    logger.warning(f"🌪️ {symbol} High volatility detected: Reducing position allowance")
            except Exception as e:
                logger.warning(f"⚠️ {symbol} Volatility Assessor error: {e}")
                assessment.volatility_multiplier = 0.9  # Conservative fallback
            
            # 3. 🛡️ Drawdown Protector
            try:
                logger.info(f"🛡️ {symbol} Drawdown Protector: Analyzing portfolio protection requirements...")
                assessment.drawdown_multiplier = self.drawdown_protector.get_risk_multiplier()
                assessment.stop_loss_adjustment *= self.drawdown_protector.get_stop_loss_adjustment()
                assessment.force_close_ratio = self.drawdown_protector.get_force_close_ratio()
                assessment.force_close_positions = assessment.force_close_ratio > 0
                
                dd_summary = self.drawdown_protector.get_protection_summary()
                assessment.current_drawdown = dd_summary.get('current_drawdown', 0.0)
                emergency_mode = self.drawdown_protector.is_emergency_mode()
                allow_new_pos = self.drawdown_protector.should_allow_new_position()
                
                logger.info(f"🛡️ {symbol} Drawdown Results: "
                           f"CurrentDD={assessment.current_drawdown:.1%} | "
                           f"Multiplier={assessment.drawdown_multiplier:.2f} | "
                           f"StopAdj={assessment.stop_loss_adjustment:.2f} | "
                           f"ForceClose={assessment.force_close_positions} | "
                           f"Emergency={emergency_mode}")
                
                # Override position allowance if drawdown protection says no
                if not allow_new_pos:
                    assessment.allow_new_positions = False
                    logger.warning(f"🛡️ {symbol} Drawdown Protection: BLOCKING new positions")
                
                # Emergency mode if drawdown protector says so
                if emergency_mode:
                    assessment.emergency_mode = True
                    logger.warning(f"🛡️ {symbol} Drawdown Protection: EMERGENCY MODE activated")
            except Exception as e:
                logger.warning(f"⚠️ {symbol} Drawdown Protector error: {e}")
                assessment.drawdown_multiplier = 0.8  # Conservative fallback
            
            # 4. 📈 Performance Adapter
            try:
                logger.info(f"📈 {symbol} Performance Adapter: Analyzing strategy performance patterns...")
                assessment.performance_multiplier = self.performance_adapter.get_performance_multiplier()
                assessment.confidence_threshold = self.performance_adapter.get_confidence_threshold()
                assessment.stop_loss_adjustment *= self.performance_adapter.get_stop_loss_adjustment()
                assessment.take_profit_adjustment *= self.performance_adapter.get_take_profit_adjustment()
                
                intervention_mode = self.performance_adapter.is_intervention_mode()
                perf_summary = self.performance_adapter.get_performance_summary()
                
                logger.info(f"📈 {symbol} Performance Results: "
                           f"Multiplier={assessment.performance_multiplier:.2f} | "
                           f"Confidence={assessment.confidence_threshold:.2f} | "
                           f"WinRate={perf_summary.get('win_rate', 0):.1%} | "
                           f"Intervention={intervention_mode}")
                
                # Check signal acceptance based on confidence
                if abs(signal_strength) < assessment.confidence_threshold:
                    assessment.allow_new_positions = False
                    logger.warning(f"📈 {symbol} Performance Adapter: SIGNAL REJECTED - below confidence threshold")
                
                # Override if intervention mode
                if intervention_mode:
                    assessment.emergency_mode = True
                    assessment.performance_multiplier *= 0.5  # Reduce further
                    logger.warning(f"📈 {symbol} Performance Adapter: INTERVENTION MODE activated")
            except Exception as e:
                logger.warning(f"⚠️ {symbol} Performance Adapter error: {e}")
                assessment.performance_multiplier = 0.9  # Conservative fallback
            
            # 5. 🔍 Risk Monitor
            try:
                logger.info(f"🔍 {symbol} Risk Monitor: Checking compliance and system alerts...")
                monitor_result = self.risk_monitor.get_current_risk_status()
                assessment.active_alerts = monitor_result.get('critical_alerts', 0)
                assessment.compliance_status = monitor_result.get('compliance_status', 'unknown')
                
                logger.info(f"🔍 {symbol} Risk Monitor Results: "
                           f"Alerts={assessment.active_alerts} | "
                           f"Compliance={assessment.compliance_status}")
                
                # Emergency mode if critical alerts
                if assessment.active_alerts > 0:
                    assessment.emergency_mode = True
                    logger.warning(f"🔍 {symbol} Risk Monitor: {assessment.active_alerts} CRITICAL ALERTS - Emergency mode")
            except Exception as e:
                logger.warning(f"⚠️ {symbol} Risk Monitor error: {e}")
            
            # Calculate final risk multiplier
            assessment.final_risk_multiplier = self._calculate_final_risk_multiplier(assessment)
            
            # Calculate position sizing recommendations
            self._calculate_position_sizing(assessment, equity, price, signal_strength, atr)
            
            # Check emergency conditions
            self._check_system_emergency_conditions(assessment)
            
            # Update cache
            assessment.last_update = datetime.now()
            self.assessment_cache = assessment
            self.last_assessment = datetime.now()
            
            return assessment
            
        except Exception as e:
            logger.error(f"❌ Error in comprehensive risk assessment: {e}")
            return self._get_emergency_fallback_assessment(symbol, signal_strength, equity, price)
    
    def _calculate_final_risk_multiplier(self, assessment: IntegratedRiskAssessment) -> float:
        """Calculate final combined risk multiplier"""
        try:
            # Base multiplier combination
            base_multiplier = (
                assessment.dynamic_risk_multiplier * 0.25 +
                assessment.volatility_multiplier * 0.25 +
                assessment.drawdown_multiplier * 0.3 +
                assessment.performance_multiplier * 0.2
            )
            
            # Emergency mode overrides
            if assessment.emergency_mode:
                base_multiplier *= 0.3  # Reduce to 30% in emergency
            
            # High risk score penalty
            if assessment.risk_score > 0.8:
                base_multiplier *= 0.7
            
            # High drawdown penalty
            if assessment.current_drawdown > 0.1:  # 10% drawdown
                base_multiplier *= max(0.5, 1 - assessment.current_drawdown)
            
            # Active alerts penalty
            if assessment.active_alerts > 0:
                base_multiplier *= max(0.6, 1 - assessment.active_alerts * 0.1)
            
            # Safety bounds
            final_multiplier = max(0.1, min(2.0, base_multiplier))
            
            return final_multiplier
            
        except Exception as e:
            logger.error(f"❌ Error calculating final risk multiplier: {e}")
            return 0.5  # Conservative fallback
    
    def _calculate_position_sizing(self, assessment: IntegratedRiskAssessment, equity: float, 
                                 price: float, signal_strength: float, atr: float = None):
        """Calculate intelligent position sizing recommendations"""
        try:
            # Base risk calculation
            base_risk_pct = settings.risk_per_trade * assessment.final_risk_multiplier
            
            # Emergency mode override
            if assessment.emergency_mode:
                base_risk_pct *= 0.2  # Reduce to 20% in emergency
            
            # Signal strength adjustment
            signal_adj = max(0.3, min(1.5, abs(signal_strength)))
            adjusted_risk_pct = base_risk_pct * signal_adj
            
            # Calculate maximum position size
            max_risk_amount = equity * adjusted_risk_pct
            
            # Use ATR for position sizing if available
            if atr and atr > 0 and price > 0:
                # ATR-based position sizing
                stop_distance = atr * 2.0  # 2 ATR stop
                max_shares = max_risk_amount / stop_distance
                max_position_usd = max_shares * price
            else:
                # Percentage-based position sizing
                max_position_pct = min(0.15, adjusted_risk_pct * 10)  # Max 15% of equity
                max_position_usd = equity * max_position_pct
                max_shares = max_position_usd / price if price > 0 else 0
            
            # Apply additional constraints
            
            # Volatility constraint
            if assessment.volatility_regime in ['high', 'extreme']:
                max_position_usd *= 0.7
                max_shares *= 0.7
            
            # Drawdown constraint
            if assessment.current_drawdown > 0.05:  # 5% drawdown
                drawdown_penalty = max(0.5, 1 - assessment.current_drawdown * 2)
                max_position_usd *= drawdown_penalty
                max_shares *= drawdown_penalty
            
            # Compliance constraint
            if assessment.compliance_status != 'compliant':
                max_position_usd *= 0.8
                max_shares *= 0.8
            
            # Force close adjustment
            if assessment.force_close_positions:
                max_position_usd *= (1 - assessment.force_close_ratio)
                max_shares *= (1 - assessment.force_close_ratio)
            
            # Final safety bounds
            max_position_usd = max(0, min(max_position_usd, equity * 0.25))  # Never more than 25% of equity
            max_shares = max(0, max_position_usd / price if price > 0 else 0)
            
            # Update assessment
            assessment.max_position_size_usd = max_position_usd
            assessment.recommended_shares = max_shares
            
        except Exception as e:
            logger.error(f"❌ Error calculating position sizing: {e}")
            # Emergency fallback
            assessment.max_position_size_usd = equity * 0.01  # 1% emergency limit
            assessment.recommended_shares = assessment.max_position_size_usd / price if price > 0 else 0
    
    def _check_system_emergency_conditions(self, assessment: IntegratedRiskAssessment):
        """Check for system-wide emergency conditions"""
        try:
            emergency_conditions = []
            
            # High risk score
            if assessment.risk_score > 0.9:
                emergency_conditions.append(f"Extreme risk score: {assessment.risk_score:.2f}")
            
            # Severe drawdown
            if assessment.current_drawdown > 0.15:  # 15% drawdown
                emergency_conditions.append(f"Severe drawdown: {assessment.current_drawdown:.1%}")
            
            # Multiple critical alerts
            if assessment.active_alerts >= 3:
                emergency_conditions.append(f"Multiple critical alerts: {assessment.active_alerts}")
            
            # Compliance issues
            if assessment.compliance_status in ['non_compliant', 'violation']:
                emergency_conditions.append(f"Compliance violation: {assessment.compliance_status}")
            
            # System emergency mode
            if emergency_conditions and not self.system_emergency_mode:
                self.system_emergency_mode = True
                self.emergency_triggered_time = datetime.now()
                self.emergency_reasons = emergency_conditions
                
                logger.critical(f"🚨 SYSTEM EMERGENCY MODE ACTIVATED")
                logger.critical(f"   Reasons: {', '.join(emergency_conditions)}")
                
                # Send emergency notification
                try:
                    from .telegram import send_telegram
                    msg = f"🚨 SYSTEM EMERGENCY MODE\n\nReasons:\n" + "\n".join([f"• {r}" for r in emergency_conditions])
                    send_telegram(msg)
                except:
                    pass
                    
            elif not emergency_conditions and self.system_emergency_mode:
                # Check if we can clear emergency mode
                if (self.emergency_triggered_time and 
                    datetime.now() - self.emergency_triggered_time > timedelta(minutes=5)):
                    self.system_emergency_mode = False
                    self.emergency_reasons = []
                    logger.info("✅ System emergency mode cleared")
            
            # Override assessment if system emergency
            if self.system_emergency_mode:
                assessment.emergency_mode = True
                assessment.allow_new_positions = False
                assessment.final_risk_multiplier = min(0.1, assessment.final_risk_multiplier)
                
        except Exception as e:
            logger.error(f"❌ Error checking emergency conditions: {e}")
    
    def _get_legacy_risk_assessment(self, symbol: str, signal_strength: float, 
                                  equity: float, price: float, atr: float = None) -> IntegratedRiskAssessment:
        """Fallback to legacy risk management system"""
        try:
            logger.debug("Using legacy risk management fallback")
            
            assessment = IntegratedRiskAssessment()
            
            # Use existing risk management
            from .risk_management_v2 import AdvancedRiskManager
            risk_manager = AdvancedRiskManager()
            
            # Get basic market data for legacy system
            try:
                from .data import fetch_bars
                data = fetch_bars(symbol, min_bars=50)
                if data is not None and not data.empty:
                    market_regime = risk_manager.detect_market_regime(data)
                    vol_clustering = risk_manager.detect_volatility_clustering(data)
                    
                    # Calculate position size using legacy system
                    legacy_sizing = risk_manager.calculate_position_size_v2(
                        equity=equity, price=price, atr=atr or 0.02,
                        signal_strength=signal_strength,
                        market_regime=market_regime,
                        vol_clustering=vol_clustering
                    )
                    
                    assessment.recommended_shares = legacy_sizing.get('shares', 0)
                    assessment.final_risk_multiplier = legacy_sizing.get('regime_multiplier', 1.0)
                    assessment.max_position_size_usd = assessment.recommended_shares * price
                    
                    # Get dynamic stops
                    dynamic_stops = risk_manager.calculate_dynamic_stops(
                        symbol=symbol, price=price, atr=atr or 0.02,
                        signal_strength=signal_strength,
                        market_regime=market_regime,
                        vol_clustering=vol_clustering
                    )
                    
                    assessment.stop_loss_adjustment = dynamic_stops.get('stop_loss_pct', settings.stop_loss_pct) / settings.stop_loss_pct
                    assessment.take_profit_adjustment = dynamic_stops.get('take_profit_pct', settings.take_profit_pct) / settings.take_profit_pct
                    
            except Exception as e:
                logger.warning(f"⚠️ Legacy system error: {e}")
                # Basic fallback
                assessment.recommended_shares = (equity * settings.risk_per_trade) / price if price > 0 else 0
                assessment.max_position_size_usd = assessment.recommended_shares * price
                assessment.final_risk_multiplier = 1.0
            
            return assessment
            
        except Exception as e:
            logger.error(f"❌ Legacy risk assessment error: {e}")
            return self._get_emergency_fallback_assessment(symbol, signal_strength, equity, price)
    
    def _get_emergency_fallback_assessment(self, symbol: str, signal_strength: float, 
                                         equity: float, price: float) -> IntegratedRiskAssessment:
        """Emergency fallback assessment with minimal risk"""
        assessment = IntegratedRiskAssessment()
        
        # Ultra-conservative emergency settings
        emergency_risk = min(0.005, settings.risk_per_trade * 0.5)  # 0.5% max emergency risk
        assessment.max_position_size_usd = equity * emergency_risk
        assessment.recommended_shares = assessment.max_position_size_usd / price if price > 0 else 0
        assessment.final_risk_multiplier = 0.2
        assessment.emergency_mode = True
        assessment.allow_new_positions = abs(signal_strength) > 0.8  # Only very strong signals
        assessment.confidence_threshold = 0.8
        assessment.stop_loss_adjustment = 0.7  # Tighter stops
        
        logger.warning(f"⚠️ Emergency fallback assessment active - Ultra-conservative mode")
        
        return assessment
    
    # Public API methods for integration with trading system
    
    def should_allow_trade(self, symbol: str, signal_strength: float, equity: float, price: float) -> bool:
        """Check if a trade should be allowed based on comprehensive risk assessment"""
        try:
            assessment = self.get_comprehensive_risk_assessment(symbol, signal_strength, equity, price)
            
            # Check basic allowance
            if not assessment.allow_new_positions:
                return False
            
            # Check signal strength vs confidence threshold
            if abs(signal_strength) < assessment.confidence_threshold:
                return False
            
            # Check emergency mode
            if assessment.emergency_mode and abs(signal_strength) < 0.8:
                return False  # Only very strong signals in emergency
            
            # Check recommended position size
            if assessment.max_position_size_usd < 10:  # Minimum $10 position
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error in trade allowance check: {e}")
            return False  # Fail safe
    
    def get_position_size(self, symbol: str, signal_strength: float, equity: float, price: float, atr: float = None) -> float:
        """Get recommended position size (shares)"""
        try:
            assessment = self.get_comprehensive_risk_assessment(symbol, signal_strength, equity, price, atr)
            return assessment.recommended_shares
        except Exception as e:
            logger.error(f"❌ Error getting position size: {e}")
            return 0.0
    
    def get_stop_loss_take_profit(self, symbol: str, signal_strength: float, equity: float, price: float) -> Tuple[float, float]:
        """Get adjusted stop loss and take profit percentages"""
        try:
            assessment = self.get_comprehensive_risk_assessment(symbol, signal_strength, equity, price)
            
            adjusted_stop = settings.stop_loss_pct * assessment.stop_loss_adjustment
            adjusted_tp = settings.take_profit_pct * assessment.take_profit_adjustment
            
            # Safety bounds
            adjusted_stop = max(0.003, min(0.05, adjusted_stop))  # 0.3% to 5%
            adjusted_tp = max(0.01, min(0.15, adjusted_tp))       # 1% to 15%
            
            return adjusted_stop, adjusted_tp
            
        except Exception as e:
            logger.error(f"❌ Error getting stop/profit levels: {e}")
            return settings.stop_loss_pct, settings.take_profit_pct
    
    def log_trade_result(self, symbol: str, side: str, entry_price: float, exit_price: float, 
                        quantity: float, pnl: float, duration_minutes: float, signal_strength: float):
        """Log trade result to performance adapter for learning"""
        try:
            if not self.legacy_fallback:
                self.performance_adapter.log_trade_result(
                    symbol=symbol, side=side, entry_price=entry_price, exit_price=exit_price,
                    quantity=quantity, pnl=pnl, duration_minutes=duration_minutes, 
                    signal_strength=signal_strength
                )
        except Exception as e:
            logger.error(f"❌ Error logging trade result: {e}")
    
    def get_risk_status_summary(self) -> Dict[str, Any]:
        """Get comprehensive risk status summary for monitoring"""
        try:
            if self.assessment_cache:
                return {
                    'system_emergency_mode': self.system_emergency_mode,
                    'emergency_reasons': self.emergency_reasons,
                    'final_risk_multiplier': self.assessment_cache.final_risk_multiplier,
                    'allow_new_positions': self.assessment_cache.allow_new_positions,
                    'emergency_mode': self.assessment_cache.emergency_mode,
                    'current_drawdown': self.assessment_cache.current_drawdown,
                    'risk_score': self.assessment_cache.risk_score,
                    'volatility_regime': self.assessment_cache.volatility_regime,
                    'active_alerts': self.assessment_cache.active_alerts,
                    'compliance_status': self.assessment_cache.compliance_status,
                    'last_update': self.assessment_cache.last_update.isoformat() if self.assessment_cache.last_update else None,
                    'legacy_fallback': self.legacy_fallback,
                    'integration_active': self.integration_active
                }
            else:
                return {
                    'system_emergency_mode': self.system_emergency_mode,
                    'legacy_fallback': self.legacy_fallback,
                    'integration_active': self.integration_active,
                    'status': 'no_assessment_available'
                }
                
        except Exception as e:
            logger.error(f"❌ Error getting risk status summary: {e}")
            return {'error': str(e)}


# Global instance for system-wide use
integrated_risk_system = IntegratedRiskSystem()


def get_integrated_risk_assessment(symbol: str, signal_strength: float, equity: float, price: float, atr: float = None) -> Dict[str, Any]:
    """
    Main interface for integrated risk management system.
    Returns comprehensive risk assessment for trading decisions.
    """
    try:
        # 🏛️ INSTITUTIONAL-GRADE RISK MANAGEMENT SYSTEM ENTRY POINT
        logger.info(f"🏛️ DYNAMIC RISK ASSESSMENT {symbol}: signal={signal_strength:.3f}, equity=${equity:.0f}, price=${price:.2f}")
        
        assessment = integrated_risk_system.get_comprehensive_risk_assessment(
            symbol=symbol, signal_strength=signal_strength, equity=equity, price=price, atr=atr
        )
        
        # Calculate final trade decision
        allow_trade = assessment.allow_new_positions and abs(signal_strength) >= assessment.confidence_threshold
        
        # 🏛️ COMPREHENSIVE RISK ASSESSMENT RESULTS LOGGING
        logger.info(f"🏛️ {symbol} RISK RESULTS: "
                   f"Allow={allow_trade} | "
                   f"Shares={assessment.recommended_shares:.2f} | "
                   f"MaxUSD=${assessment.max_position_size_usd:.0f} | "
                   f"Risk={assessment.final_risk_multiplier:.2f}x")
        
        logger.info(f"🏛️ {symbol} RISK DETAILS: "
                   f"Emergency={assessment.emergency_mode} | "
                   f"Drawdown={assessment.current_drawdown:.1%} | "
                   f"Vol={assessment.volatility_regime} | "
                   f"Score={assessment.risk_score:.2f}")
        
        return {
            'allow_trade': allow_trade,
            'position_size_shares': assessment.recommended_shares,
            'max_position_usd': assessment.max_position_size_usd,
            'risk_multiplier': assessment.final_risk_multiplier,
            'stop_loss_adjustment': assessment.stop_loss_adjustment,
            'take_profit_adjustment': assessment.take_profit_adjustment,
            'confidence_threshold': assessment.confidence_threshold,
            'emergency_mode': assessment.emergency_mode,
            'force_close_positions': assessment.force_close_positions,
            'force_close_ratio': assessment.force_close_ratio,
            'risk_score': assessment.risk_score,
            'current_drawdown': assessment.current_drawdown,
            'volatility_regime': assessment.volatility_regime,
            'compliance_status': assessment.compliance_status,
            'active_alerts': assessment.active_alerts
        }
        
    except Exception as e:
        logger.error(f"❌ CRITICAL: {symbol} risk assessment failed: {e}")
        logger.critical(f"🏛️ {symbol} EMERGENCY FALLBACK: Blocking trade due to system error")
        return {
            'allow_trade': False,
            'position_size_shares': 0.0,
            'max_position_usd': 0.0,
            'risk_multiplier': 0.2,
            'emergency_mode': True,
            'error': str(e)
        }
