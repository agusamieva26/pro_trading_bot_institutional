#!/usr/bin/env python3
"""
🔍 AGUS 24/7 COMPREHENSIVE MONITORING SYSTEM
Advanced autonomous monitoring agents for system health, performance, trading, and risk monitoring.
"""

import asyncio
import sqlite3
import json
import time
import threading
import uuid
import re
import psutil
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union, Pattern
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from collections import defaultdict, deque

# Import orchestrator components with relative imports
from .agus_core import AGUSOrchestrator, EventType, AlertSeverity, Event, Alert, EventBus, StateStore

# Import bot modules with relative imports
try:
    from .util import logger
    from .config import settings
except ImportError:
    # Fallback logging if bot utils not available
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)
    settings = None


class MonitoringEventType(Enum):
    LOG_ERROR_DETECTED = "monitoring.log_error"
    PERFORMANCE_DEGRADED = "monitoring.performance_degraded"
    TRADING_ANOMALY = "monitoring.trading_anomaly"
    RISK_THRESHOLD_BREACH = "monitoring.risk_breach"


@dataclass
class LogPattern:
    name: str = ""
    pattern: Pattern = None
    severity: str = "warning"
    alert_severity: AlertSeverity = AlertSeverity.WARNING
    description: str = ""
    throttle_seconds: int = 60


@dataclass
class PerformanceMetrics:
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_available_gb: float = 0.0
    disk_usage_percent: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


class BaseMonitoringAgent:
    def __init__(self, name: str, orchestrator: AGUSOrchestrator):
        self.name = name
        self.orchestrator = orchestrator
        self.is_running = False
        self.last_check = None
        self.check_interval = 30
        self.alert_history = deque(maxlen=100)
        self.alert_throttle = {}
        self.default_throttle = 60
        
    async def start_monitoring(self):
        self.is_running = True
        logger.info(f"🔍 {self.name} - Starting monitoring...")
        
        while self.is_running:
            try:
                await self.check_system()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"❌ {self.name} - Error: {e}")
                await asyncio.sleep(5)
    
    async def stop_monitoring(self):
        self.is_running = False
        logger.info(f"🔍 {self.name} - Monitoring stopped")
    
    async def check_system(self):
        pass
    
    def should_throttle_alert(self, alert_key: str, throttle_seconds: int = None) -> bool:
        if throttle_seconds is None:
            throttle_seconds = self.default_throttle
            
        now = datetime.now()
        last_alert = self.alert_throttle.get(alert_key)
        
        if last_alert and (now - last_alert).total_seconds() < throttle_seconds:
            return True
            
        self.alert_throttle[alert_key] = now
        return False
    
    async def emit_alert(self, severity: AlertSeverity, title: str, message: str, 
                        context: Dict[str, Any] = None, throttle_key: str = None):
        if throttle_key and self.should_throttle_alert(throttle_key):
            return
            
        alert = Alert(
            severity=severity,
            title=title,
            message=message,
            source=self.name,
            context=context or {},
            timestamp=datetime.now()
        )
        
        # Store alert in orchestrator database
        try:
            conn = sqlite3.connect(self.orchestrator.state_store.db_path)
            conn.execute('''INSERT INTO alerts 
                           (alert_id, severity, title, message, source, context, timestamp, resolved)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                        (alert.alert_id, alert.severity.value, alert.title, alert.message,
                         alert.source, json.dumps(alert.context), alert.timestamp.isoformat(), 0))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"❌ {self.name} - Error storing alert: {e}")
        
        self.alert_history.append(alert)
        
        # Emit event
        priority = 1 if severity == AlertSeverity.EMERGENCY else 3 if severity == AlertSeverity.CRITICAL else 5
        event = Event(
            event_type=EventType.SYSTEM_ERROR if severity in [AlertSeverity.ERROR, AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY] else EventType.SYSTEM_START,
            source=self.name,
            data={
                "alert_id": alert.alert_id,
                "severity": alert.severity.value,
                "title": alert.title,
                "message": alert.message,
                "context": alert.context
            },
            priority=priority
        )
        
        self.orchestrator.event_bus.publish(event)
        logger.warning(f"🚨 {self.name} - {severity.value.upper()}: {title}")


class LogMonitorAgent(BaseMonitoringAgent):
    """Log monitoring agent for real-time error detection"""
    
    def __init__(self, orchestrator: AGUSOrchestrator):
        super().__init__("LogMonitor", orchestrator)
        self.check_interval = 15
        
        # Critical patterns to detect
        self.log_patterns = [
            LogPattern(
                name="alpaca_api_error",
                pattern=re.compile(r"Alpaca API error.*too many requests", re.IGNORECASE),
                alert_severity=AlertSeverity.WARNING,
                description="Alpaca API rate limit exceeded",
                throttle_seconds=300
            ),
            LogPattern(
                name="disk_quota_exceeded",
                pattern=re.compile(r"Disk quota exceeded", re.IGNORECASE),
                alert_severity=AlertSeverity.CRITICAL,
                description="Disk quota exceeded - system storage full",
                throttle_seconds=600
            ),
            LogPattern(
                name="symbol_limit_exceeded",
                pattern=re.compile(r"SYMBOL LIMIT EXCEEDED", re.IGNORECASE),
                alert_severity=AlertSeverity.CRITICAL,
                description="Trading symbol exposure limits breached",
                throttle_seconds=120
            ),
            LogPattern(
                name="emergency_mode",
                pattern=re.compile(r"EMERGENCY|emergency mode", re.IGNORECASE),
                alert_severity=AlertSeverity.EMERGENCY,
                description="Emergency mode detected in trading system",
                throttle_seconds=60
            ),
            LogPattern(
                name="intervention_mode",
                pattern=re.compile(r"INTERVENTION MODE ACTIVE", re.IGNORECASE),
                alert_severity=AlertSeverity.WARNING,
                description="Performance intervention mode activated",
                throttle_seconds=300
            )
        ]
        
        self.last_log_positions = {}
    
    async def check_system(self):
        """Check logs for patterns and anomalies"""
        try:
            await self._check_workflow_logs()
            self.last_check = datetime.now()
        except Exception as e:
            logger.error(f"❌ LogMonitor - Error checking logs: {e}")
    
    async def _check_workflow_logs(self):
        """Check workflow logs for patterns"""
        try:
            # Check local logs/ directory first
            log_dir = Path("logs")
            if not log_dir.exists():
                log_dir.mkdir(exist_ok=True)
            
            log_files = list(log_dir.glob("*.log"))
            for log_file in log_files:
                await self._analyze_log_file(log_file)
                
        except Exception as e:
            logger.error(f"❌ LogMonitor - Error checking workflow logs: {e}")
    
    async def _analyze_log_file(self, log_file: Path):
        """Analyze a specific log file for patterns"""
        try:
            file_key = str(log_file)
            last_position = self.last_log_positions.get(file_key, 0)
            
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(last_position)
                new_content = f.read()
                self.last_log_positions[file_key] = f.tell()
            
            if not new_content.strip():
                return
            
            lines = new_content.split('\n')
            for line in lines:
                if not line.strip():
                    continue
                await self._check_line_against_patterns(line, log_file.name)
        except Exception as e:
            logger.error(f"❌ LogMonitor - Error analyzing {log_file}: {e}")
    
    async def _check_line_against_patterns(self, line: str, source_file: str):
        """Check a log line against known patterns"""
        for pattern in self.log_patterns:
            if pattern.pattern.search(line):
                throttle_key = f"{pattern.name}_{source_file}"
                
                if not self.should_throttle_alert(throttle_key, pattern.throttle_seconds):
                    await self.emit_alert(
                        severity=pattern.alert_severity,
                        title=f"Log Pattern Detected: {pattern.name}",
                        message=f"{pattern.description}\nSource: {source_file}\nLine: {line[:200]}",
                        context={
                            "pattern_name": pattern.name,
                            "source_file": source_file,
                            "matched_line": line
                        },
                        throttle_key=throttle_key
                    )


class PerformanceMonitorAgent(BaseMonitoringAgent):
    """Performance monitoring agent for system metrics"""
    
    def __init__(self, orchestrator: AGUSOrchestrator):
        super().__init__("PerformanceMonitor", orchestrator)
        self.check_interval = 30
        
        # Performance thresholds
        self.cpu_warning_threshold = 80.0
        self.cpu_critical_threshold = 95.0
        self.memory_warning_threshold = 85.0
        self.memory_critical_threshold = 95.0
        self.disk_warning_threshold = 90.0
        self.disk_critical_threshold = 98.0
        
        self.performance_history = deque(maxlen=100)
    
    async def check_system(self):
        """Check system performance metrics"""
        try:
            metrics = await self._collect_performance_metrics()
            self.performance_history.append(metrics)
            
            await self._check_performance_thresholds(metrics)
            await self._check_performance_trends()
            
            self.last_check = datetime.now()
        except Exception as e:
            logger.error(f"❌ PerformanceMonitor - Error checking performance: {e}")
    
    async def _collect_performance_metrics(self) -> PerformanceMetrics:
        """Collect current system performance metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_gb = memory.available / (1024**3)
            disk = psutil.disk_usage('/')
            disk_usage_percent = disk.percent
            
            return PerformanceMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_available_gb=memory_available_gb,
                disk_usage_percent=disk_usage_percent,
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.error(f"❌ PerformanceMonitor - Error collecting metrics: {e}")
            return PerformanceMetrics()
    
    async def _check_performance_thresholds(self, metrics: PerformanceMetrics):
        """Check performance metrics against thresholds"""
        # CPU check
        if metrics.cpu_percent >= self.cpu_critical_threshold:
            await self.emit_alert(
                severity=AlertSeverity.CRITICAL,
                title="Critical CPU Usage",
                message=f"CPU usage at {metrics.cpu_percent:.1f}%",
                context={"cpu_percent": metrics.cpu_percent},
                throttle_key="cpu_critical"
            )
        elif metrics.cpu_percent >= self.cpu_warning_threshold:
            await self.emit_alert(
                severity=AlertSeverity.WARNING,
                title="High CPU Usage",
                message=f"CPU usage at {metrics.cpu_percent:.1f}%",
                context={"cpu_percent": metrics.cpu_percent},
                throttle_key="cpu_warning"
            )
        
        # Memory check
        if metrics.memory_percent >= self.memory_critical_threshold:
            await self.emit_alert(
                severity=AlertSeverity.CRITICAL,
                title="Critical Memory Usage",
                message=f"Memory usage at {metrics.memory_percent:.1f}% ({metrics.memory_available_gb:.1f}GB available)",
                context={"memory_percent": metrics.memory_percent},
                throttle_key="memory_critical"
            )
        elif metrics.memory_percent >= self.memory_warning_threshold:
            await self.emit_alert(
                severity=AlertSeverity.WARNING,
                title="High Memory Usage",
                message=f"Memory usage at {metrics.memory_percent:.1f}%",
                context={"memory_percent": metrics.memory_percent},
                throttle_key="memory_warning"
            )
        
        # Disk check - this will likely trigger given current issues
        if metrics.disk_usage_percent >= self.disk_critical_threshold:
            await self.emit_alert(
                severity=AlertSeverity.CRITICAL,
                title="Critical Disk Usage",
                message=f"Disk usage at {metrics.disk_usage_percent:.1f}%",
                context={"disk_percent": metrics.disk_usage_percent},
                throttle_key="disk_critical"
            )
        elif metrics.disk_usage_percent >= self.disk_warning_threshold:
            await self.emit_alert(
                severity=AlertSeverity.WARNING,
                title="High Disk Usage",
                message=f"Disk usage at {metrics.disk_usage_percent:.1f}%",
                context={"disk_percent": metrics.disk_usage_percent},
                throttle_key="disk_warning"
            )
    
    async def _check_performance_trends(self):
        """Analyze performance trends for degradation detection"""
        if len(self.performance_history) < 10:
            return
        
        try:
            recent_metrics = list(self.performance_history)[-10:]
            
            # Check for sustained high CPU
            high_cpu_count = sum(1 for m in recent_metrics if m.cpu_percent > 70)
            if high_cpu_count >= 8:
                await self.emit_alert(
                    severity=AlertSeverity.WARNING,
                    title="Sustained High CPU Usage",
                    message=f"CPU usage above 70% for {high_cpu_count}/10 recent checks",
                    context={"high_cpu_count": high_cpu_count},
                    throttle_key="sustained_cpu"
                )
        except Exception as e:
            logger.error(f"❌ PerformanceMonitor - Error checking trends: {e}")


class TradingMarketMonitorAgent(BaseMonitoringAgent):
    """Trading and market monitoring agent"""
    
    def __init__(self, orchestrator: AGUSOrchestrator):
        super().__init__("TradingMarketMonitor", orchestrator)
        self.check_interval = 45
        
        # Trading thresholds
        self.max_daily_loss_threshold = 0.15
        self.high_exposure_threshold = 0.85
        self.volatility_spike_threshold = 3.0
    
    async def check_system(self):
        """Check trading and market conditions"""
        try:
            await self._check_trading_thresholds()
            await self._check_market_conditions()
            self.last_check = datetime.now()
        except Exception as e:
            logger.error(f"❌ TradingMarketMonitor - Error checking trading: {e}")
    
    async def _check_trading_thresholds(self):
        """Check trading metrics against thresholds"""
        try:
            # Try to get data from risk monitor if available
            from . import risk_monitor
            if hasattr(risk_monitor, 'risk_metrics'):
                risk_data = risk_monitor.risk_metrics
                current_drawdown = risk_data.get('current_drawdown', 0.0)
                
                # Drawdown alerts
                if current_drawdown >= 0.20:
                    await self.emit_alert(
                        severity=AlertSeverity.EMERGENCY,
                        title="Severe Drawdown Alert",
                        message=f"Current drawdown at {current_drawdown*100:.1f}%",
                        context={"drawdown": current_drawdown},
                        throttle_key="severe_drawdown"
                    )
                elif current_drawdown >= 0.10:
                    await self.emit_alert(
                        severity=AlertSeverity.CRITICAL,
                        title="Significant Drawdown Alert",
                        message=f"Current drawdown at {current_drawdown*100:.1f}%",
                        context={"drawdown": current_drawdown},
                        throttle_key="significant_drawdown"
                    )
        except Exception:
            pass
    
    async def _check_market_conditions(self):
        """Check market regime and conditions"""
        try:
            # Check volatility regime if available
            from . import volatility_assessor
            vol_status = volatility_assessor.get_current_status()
            volatility_regime = vol_status.get('volatility_regime', 'normal')
            
            if volatility_regime in ["extreme", "high"]:
                await self.emit_alert(
                    severity=AlertSeverity.WARNING,
                    title=f"High Volatility Regime",
                    message=f"Market volatility regime: {volatility_regime}",
                    context={"volatility_regime": volatility_regime},
                    throttle_key="high_volatility_regime"
                )
        except Exception:
            pass


class RiskDrawdownMonitorAgent(BaseMonitoringAgent):
    """Risk and drawdown monitoring agent"""
    
    def __init__(self, orchestrator: AGUSOrchestrator):
        super().__init__("RiskDrawdownMonitor", orchestrator)
        self.check_interval = 20
        
        # Risk thresholds
        self.critical_drawdown_threshold = 0.12
        self.emergency_drawdown_threshold = 0.18
        self.var_critical_threshold = 0.03
        
        self.last_emergency_mode = False
    
    async def check_system(self):
        """Check risk management and drawdown protection systems"""
        try:
            await self._check_drawdown_protection()
            await self._check_integrated_risk_system()
            self.last_check = datetime.now()
        except Exception as e:
            logger.error(f"❌ RiskDrawdownMonitor - Error checking risk systems: {e}")
    
    async def _check_drawdown_protection(self):
        """Check drawdown protection system status"""
        try:
            from . import drawdown_protector
            
            status = drawdown_protector.get_protection_status()
            current_drawdown = status.get('current_drawdown', 0.0)
            emergency_mode = status.get('emergency_mode', False)
            protection_level = status.get('protection_level', 'normal')
            
            # Check for emergency mode changes
            if emergency_mode and not self.last_emergency_mode:
                await self.emit_alert(
                    severity=AlertSeverity.EMERGENCY,
                    title="Drawdown Emergency Mode Activated",
                    message=f"Drawdown protection emergency mode activated. Current drawdown: {current_drawdown*100:.1f}%",
                    context={"current_drawdown": current_drawdown, "protection_level": protection_level},
                    throttle_key="emergency_mode_activated"
                )
            
            self.last_emergency_mode = emergency_mode
            
            # Check drawdown thresholds
            if current_drawdown >= self.emergency_drawdown_threshold:
                await self.emit_alert(
                    severity=AlertSeverity.EMERGENCY,
                    title="Emergency Drawdown Level",
                    message=f"Portfolio drawdown at critical level: {current_drawdown*100:.1f}%",
                    context={"drawdown": current_drawdown},
                    throttle_key="emergency_drawdown"
                )
            elif current_drawdown >= self.critical_drawdown_threshold:
                await self.emit_alert(
                    severity=AlertSeverity.CRITICAL,
                    title="Critical Drawdown Level",
                    message=f"Portfolio drawdown approaching critical level: {current_drawdown*100:.1f}%",
                    context={"drawdown": current_drawdown},
                    throttle_key="critical_drawdown"
                )
        except Exception as e:
            logger.error(f"❌ RiskDrawdownMonitor - Error checking drawdown protection: {e}")
    
    async def _check_integrated_risk_system(self):
        """Check integrated risk system status"""
        try:
            from . import integrated_risk_system
            
            system_status = integrated_risk_system.get_system_status()
            emergency_mode = system_status.get('system_emergency_mode', False)
            emergency_reasons = system_status.get('emergency_reasons', [])
            
            if emergency_mode and emergency_reasons:
                await self.emit_alert(
                    severity=AlertSeverity.EMERGENCY,
                    title="Integrated Risk System Emergency",
                    message=f"Risk system emergency activated. Reasons: {', '.join(emergency_reasons)}",
                    context={"emergency_reasons": emergency_reasons},
                    throttle_key="integrated_risk_emergency"
                )
        except Exception as e:
            logger.error(f"❌ RiskDrawdownMonitor - Error checking integrated risk system: {e}")


class AGUSMonitoringSystem:
    """Main AGUS 24/7 monitoring system orchestrator"""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.orchestrator = AGUSOrchestrator(dry_run=dry_run)
        
        # Initialize monitoring agents
        self.agents = {
            'log_monitor': LogMonitorAgent(self.orchestrator),
            'performance_monitor': PerformanceMonitorAgent(self.orchestrator),
            'trading_market_monitor': TradingMarketMonitorAgent(self.orchestrator),
            'risk_drawdown_monitor': RiskDrawdownMonitorAgent(self.orchestrator)
        }
        
        self.monitoring_tasks = {}
        self._system_running = False
        
    async def start_monitoring(self):
        """Start all monitoring agents"""
        if self._system_running:
            return
            
        self._system_running = True
        
        # Start orchestrator
        await self.orchestrator.start()
        
        # Start all monitoring agents
        for agent_name, agent in self.agents.items():
            try:
                task = asyncio.create_task(agent.start_monitoring())
                self.monitoring_tasks[agent_name] = task
                logger.info(f"🚀 Started {agent_name}")
            except Exception as e:
                logger.error(f"❌ Failed to start {agent_name}: {e}")
        
        logger.info("🔍 AGUS Monitoring System fully operational")
    
    async def stop_monitoring(self):
        """Stop all monitoring agents"""
        self._system_running = False
        
        # Stop all monitoring agents
        for agent_name, agent in self.agents.items():
            try:
                await agent.stop_monitoring()
                logger.info(f"🛑 Stopped {agent_name}")
            except Exception as e:
                logger.error(f"❌ Error stopping {agent_name}: {e}")
        
        # Cancel tasks
        for task in self.monitoring_tasks.values():
            task.cancel()
        
        # Stop orchestrator
        await self.orchestrator.stop()
        
        logger.info("🔍 AGUS Monitoring System stopped")
    
    def get_system_status(self) -> Dict:
        """Get comprehensive system status"""
        status = {
            "system_running": self._system_running,
            "orchestrator_status": self.orchestrator.get_system_status(),
            "agents_status": {},
            "recent_alerts": self.orchestrator.state_store.get_recent_alerts(limit=20)
        }
        
        for agent_name, agent in self.agents.items():
            status["agents_status"][agent_name] = {
                "running": agent.is_running,
                "last_check": agent.last_check.isoformat() if agent.last_check else None,
                "check_interval": agent.check_interval,
                "recent_alerts": len(agent.alert_history)
            }
        
        return status

# Global monitoring system instance
_monitoring_system = None

def get_monitoring_system(dry_run: bool = False) -> AGUSMonitoringSystem:
    """Get or create the global monitoring system instance"""
    global _monitoring_system
    if _monitoring_system is None:
        orchestrator = get_orchestrator(dry_run=dry_run)
        _monitoring_system = AGUSMonitoringSystem(orchestrator, dry_run=dry_run)
    return _monitoring_system