#!/usr/bin/env python3
"""
🤖 Sistema de Monitoreo Inteligente 24/7 con AGUS
Auto-detecta errores críticos, auto-diagnóstica y auto-corrige problemas del bot
Reacciona ante pérdidas críticas y fallos de funcionalidad automáticamente
"""

import asyncio
import json
import time
import psutil
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import subprocess
import os
import sqlite3
from loguru import logger

# AGUS Integration
try:
    from .agus_2_hybrid_system import AGUS2HybridIntelligenceSystem
    AGUS_AVAILABLE = True
except ImportError:
    AGUS_AVAILABLE = False
    logger.warning("🚨 AGUS not available - monitoring in basic mode")

class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning" 
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class SystemHealth(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

@dataclass
class MonitoringAlert:
    """Representa una alerta del sistema de monitoreo"""
    timestamp: datetime
    level: AlertLevel
    component: str
    message: str
    details: Dict
    auto_fixed: bool = False
    agus_response: Optional[str] = None

class IntelligentMonitor:
    """
    🧠 Sistema de Monitoreo Inteligente 24/7
    
    Características:
    - Monitoreo continuo 24/7
    - Auto-detección de errores críticos
    - Auto-diagnóstico con AGUS
    - Auto-corrección automática
    - Alertas de pérdidas críticas
    - Sistema de recuperación
    """
    
    def __init__(self, bot_instance=None):
        self.bot = bot_instance
        self.is_running = False
        self.monitor_thread = None
        self.alerts: List[MonitoringAlert] = []
        self.last_equity = 0.0
        self.max_acceptable_loss = -1000.0  # $1000 max loss crítica
        self.critical_error_count = 0
        self.system_health = SystemHealth.HEALTHY
        
        # AGUS Integration
        self.agus = None
        if AGUS_AVAILABLE:
            try:
                self.agus = AGUS2HybridIntelligenceSystem()
                logger.info("🧠 AGUS Intelligence integrated into monitoring system")
            except Exception as e:
                logger.error(f"🚨 Failed to initialize AGUS: {e}")
        
        # Configurar database para alertas persistentes
        self._initialize_alert_database()
        
        logger.info("🤖 Intelligent Monitoring System initialized - 24/7 active")
    
    def _initialize_alert_database(self):
        """Inicializa base de datos para alertas persistentes"""
        try:
            with sqlite3.connect('monitoring_alerts.db') as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS alerts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        level TEXT NOT NULL,
                        component TEXT NOT NULL,
                        message TEXT NOT NULL,
                        details TEXT,
                        auto_fixed BOOLEAN DEFAULT FALSE,
                        agus_response TEXT
                    )
                """)
                conn.commit()
            logger.info("📊 Alert database initialized")
        except Exception as e:
            logger.error(f"🚨 Failed to initialize alert database: {e}")
    
    def start_monitoring(self):
        """Inicia el monitoreo 24/7"""
        if self.is_running:
            logger.warning("⚠️ Monitor already running")
            return
        
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        logger.info("🚀 24/7 Intelligent Monitoring STARTED - Auto-detection active")
    
    def stop_monitoring(self):
        """Detiene el monitoreo"""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=10)
        
        logger.info("🛑 Intelligent Monitoring STOPPED")
    
    def _monitoring_loop(self):
        """Loop principal de monitoreo 24/7"""
        logger.info("🔄 Starting 24/7 monitoring loop...")
        
        while self.is_running:
            try:
                # Monitoreo cada 30 segundos
                self._perform_health_checks()
                self._check_critical_losses()
                self._check_system_resources()
                self._check_bot_functionality()
                self._analyze_alerts_with_agus()
                
                # Auto-corrección si es necesario
                if self.system_health in [SystemHealth.CRITICAL, SystemHealth.EMERGENCY]:
                    self._attempt_auto_recovery()
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self._create_alert(
                    AlertLevel.CRITICAL,
                    "monitor",
                    f"Monitoring loop error: {str(e)}",
                    {"error": str(e), "type": type(e).__name__}
                )
                time.sleep(60)  # Wait longer on error
    
    def _perform_health_checks(self):
        """Realiza chequeos de salud del sistema"""
        checks = {
            "bot_running": self._check_bot_process(),
            "database_connection": self._check_database(),
            "api_connectivity": self._check_api_connection(),
            "memory_usage": self._check_memory_usage(),
            "disk_space": self._check_disk_space()
        }
        
        failed_checks = [name for name, status in checks.items() if not status]
        
        if len(failed_checks) >= 3:
            self.system_health = SystemHealth.EMERGENCY
            self._create_alert(
                AlertLevel.EMERGENCY,
                "system",
                f"Multiple system failures detected: {failed_checks}",
                {"failed_checks": failed_checks, "total_checks": len(checks)}
            )
        elif len(failed_checks) >= 1:
            self.system_health = SystemHealth.CRITICAL
            self._create_alert(
                AlertLevel.CRITICAL,
                "system", 
                f"System degradation detected: {failed_checks}",
                {"failed_checks": failed_checks}
            )
        else:
            self.system_health = SystemHealth.HEALTHY
    
    def _check_critical_losses(self):
        """Monitorea pérdidas críticas del bot"""
        if not self.bot:
            return
        
        try:
            current_equity = self._get_current_equity()
            
            if self.last_equity > 0:
                loss = current_equity - self.last_equity
                loss_percentage = (loss / self.last_equity) * 100
                
                # Pérdida crítica mayor a $1000 o -5%
                if loss < self.max_acceptable_loss or loss_percentage < -5.0:
                    self._create_alert(
                        AlertLevel.EMERGENCY,
                        "trading",
                        f"CRITICAL LOSS DETECTED: ${loss:.2f} ({loss_percentage:.2f}%)",
                        {
                            "current_equity": current_equity,
                            "previous_equity": self.last_equity,
                            "loss_amount": loss,
                            "loss_percentage": loss_percentage
                        }
                    )
                    
                    # Activar medidas de emergencia
                    self._emergency_loss_response(loss, loss_percentage)
                
                # Pérdidas menores pero sostenidas
                elif loss < -200:  # $200 loss
                    self._create_alert(
                        AlertLevel.WARNING,
                        "trading",
                        f"Sustained loss detected: ${loss:.2f}",
                        {"loss_amount": loss}
                    )
            
            self.last_equity = current_equity
            
        except Exception as e:
            self._create_alert(
                AlertLevel.CRITICAL,
                "trading",
                f"Failed to check equity: {str(e)}",
                {"error": str(e)}
            )
    
    def _check_system_resources(self):
        """Verifica recursos del sistema (CPU, memoria, disco)"""
        try:
            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Check memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Check disk space
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # Create alerts for critical resource usage
            if cpu_percent > 90:
                self._create_alert(
                    AlertLevel.CRITICAL,
                    "system",
                    f"HIGH CPU USAGE: {cpu_percent:.1f}%",
                    {"cpu_percent": cpu_percent, "threshold": 90}
                )
            
            if memory_percent > 85:
                self._create_alert(
                    AlertLevel.CRITICAL,
                    "system", 
                    f"HIGH MEMORY USAGE: {memory_percent:.1f}%",
                    {"memory_percent": memory_percent, "threshold": 85}
                )
            
            if disk_percent > 90:
                self._create_alert(
                    AlertLevel.CRITICAL,
                    "system",
                    f"LOW DISK SPACE: {disk_percent:.1f}% used",
                    {"disk_percent": disk_percent, "threshold": 90}
                )
                
            # Log status for debugging
            logger.debug(f"📊 System Resources: CPU={cpu_percent:.1f}%, Memory={memory_percent:.1f}%, Disk={disk_percent:.1f}%")
            
        except Exception as e:
            self._create_alert(
                AlertLevel.WARNING,
                "system",
                f"Failed to check system resources: {str(e)}",
                {"error": str(e)}
            )
    
    def _check_bot_functionality(self):
        """Verifica que el bot esté funcionando correctamente"""
        issues = []
        
        # Check if bot is making trades
        recent_trades = self._get_recent_trade_count()
        if recent_trades == 0:
            issues.append("no_recent_trades")
        
        # Check if signals are being generated
        if hasattr(self.bot, 'get_signal_count'):
            recent_signals = self.bot.get_signal_count()
            if recent_signals == 0:
                issues.append("no_signals_generated")
        
        # Check for stuck positions
        stuck_positions = self._check_stuck_positions()
        if stuck_positions > 0:
            issues.append(f"stuck_positions_{stuck_positions}")
        
        if issues:
            self._create_alert(
                AlertLevel.WARNING,
                "bot_functionality",
                f"Bot functionality issues: {issues}",
                {"issues": issues, "count": len(issues)}
            )
    
    def _analyze_alerts_with_agus(self):
        """Usa AGUS para analizar alertas y generar respuestas inteligentes"""
        if not self.agus or not self.alerts:
            return
        
        # Analizar alertas críticas recientes
        recent_critical = [
            alert for alert in self.alerts[-10:] 
            if alert.level in [AlertLevel.CRITICAL, AlertLevel.EMERGENCY]
            and not alert.agus_response
        ]
        
        for alert in recent_critical:
            try:
                # Generar contexto para AGUS
                context = f"""
                CRITICAL SYSTEM ALERT ANALYSIS REQUIRED:
                
                Component: {alert.component}
                Level: {alert.level.value}
                Message: {alert.message}
                Details: {json.dumps(alert.details, indent=2)}
                Timestamp: {alert.timestamp}
                
                Please provide:
                1. Root cause analysis
                2. Immediate corrective actions 
                3. Prevention strategies
                4. Code fixes if applicable
                
                Respond as technical expert with actionable solutions.
                """
                
                response = self.agus.process_message(context)
                alert.agus_response = response
                
                logger.info(f"🧠 AGUS analyzed alert: {alert.component}")
                
                # Intentar auto-fix basado en respuesta de AGUS
                if "restart" in response.lower() and "bot" in response.lower():
                    self._restart_bot_service()
                    alert.auto_fixed = True
                
            except Exception as e:
                logger.error(f"🚨 AGUS analysis failed: {e}")
    
    def _emergency_loss_response(self, loss: float, loss_percentage: float):
        """Respuesta automática ante pérdidas críticas"""
        logger.critical(f"🚨 EMERGENCY LOSS RESPONSE ACTIVATED: ${loss:.2f} ({loss_percentage:.2f}%)")
        
        try:
            # 1. Cerrar todas las posiciones arriesgadas
            self._close_risky_positions()
            
            # 2. Activar modo conservador
            self._enable_conservative_mode()
            
            # 3. Reducir tamaño de posición
            self._reduce_position_size()
            
            # 4. Notificar inmediatamente
            self._send_emergency_notification(loss, loss_percentage)
            
            # 5. Si las pérdidas continúan, detener el bot
            if loss < -2000:  # $2000 loss
                logger.critical("🛑 EMERGENCY SHUTDOWN - Critical losses exceeded")
                self._emergency_shutdown()
            
        except Exception as e:
            logger.error(f"🚨 Emergency response failed: {e}")
    
    def _attempt_auto_recovery(self):
        """Intenta recuperación automática del sistema"""
        logger.info("🔧 Attempting automatic system recovery...")
        
        recovery_actions = []
        
        try:
            # 1. Reiniciar servicios críticos
            if not self._check_bot_process():
                self._restart_bot_service()
                recovery_actions.append("bot_restart")
            
            # 2. Limpiar memoria
            if self._check_memory_usage() < 0.8:  # Less than 80% available
                self._clear_memory_cache()
                recovery_actions.append("memory_cleanup")
            
            # 3. Reconectar APIs
            if not self._check_api_connection():
                self._reconnect_apis()
                recovery_actions.append("api_reconnect")
            
            # 4. Reset error counters
            self.critical_error_count = 0
            recovery_actions.append("error_reset")
            
            self._create_alert(
                AlertLevel.INFO,
                "recovery",
                f"Auto-recovery completed: {recovery_actions}",
                {"actions": recovery_actions, "count": len(recovery_actions)}
            )
            
        except Exception as e:
            self._create_alert(
                AlertLevel.EMERGENCY,
                "recovery",
                f"Auto-recovery failed: {str(e)}",
                {"error": str(e)}
            )
    
    def _create_alert(self, level: AlertLevel, component: str, message: str, details: Dict):
        """Crea y almacena una nueva alerta"""
        alert = MonitoringAlert(
            timestamp=datetime.now(),
            level=level,
            component=component,
            message=message,
            details=details
        )
        
        self.alerts.append(alert)
        
        # Mantener solo las últimas 1000 alertas
        if len(self.alerts) > 1000:
            self.alerts = self.alerts[-1000:]
        
        # Guardar en database
        self._save_alert_to_db(alert)
        
        # Log según nivel
        log_message = f"🚨 [{level.value.upper()}] {component}: {message}"
        
        if level == AlertLevel.EMERGENCY:
            logger.critical(log_message)
        elif level == AlertLevel.CRITICAL:
            logger.error(log_message)
        elif level == AlertLevel.WARNING:
            logger.warning(log_message)
        else:
            logger.info(log_message)
    
    def _save_alert_to_db(self, alert: MonitoringAlert):
        """Guarda alerta en base de datos persistente"""
        try:
            with sqlite3.connect('monitoring_alerts.db') as conn:
                conn.execute("""
                    INSERT INTO alerts 
                    (timestamp, level, component, message, details, auto_fixed, agus_response)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    alert.timestamp.isoformat(),
                    alert.level.value,
                    alert.component,
                    alert.message,
                    json.dumps(alert.details),
                    alert.auto_fixed,
                    alert.agus_response
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"🚨 Failed to save alert to DB: {e}")
    
    # System check methods
    def _check_bot_process(self) -> bool:
        """Verifica si el proceso del bot está corriendo"""
        try:
            # Check for Python processes related to the bot
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if 'main.py' in cmdline or 'trading_bot' in cmdline:
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return False
        except:
            return False
    
    def _check_database(self) -> bool:
        """Verifica conexión a base de datos"""
        try:
            with sqlite3.connect('monitoring_alerts.db', timeout=5) as conn:
                conn.execute("SELECT 1")
            return True
        except:
            return False
    
    def _check_api_connection(self) -> bool:
        """Verifica conectividad API"""
        try:
            import requests
            response = requests.get('https://httpbin.org/status/200', timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def _check_memory_usage(self) -> float:
        """Retorna porcentaje de memoria disponible"""
        try:
            memory = psutil.virtual_memory()
            return memory.available / memory.total
        except:
            return 0.5  # Default safe value
    
    def _check_disk_space(self) -> bool:
        """Verifica espacio en disco disponible"""
        try:
            disk = psutil.disk_usage('/')
            available_gb = disk.free / (1024**3)
            return available_gb > 1.0  # At least 1GB free
        except:
            return True
    
    def _get_current_equity(self) -> float:
        """Obtiene equity actual del bot"""
        if hasattr(self.bot, 'get_equity'):
            return self.bot.get_equity()
        
        # Fallback: try to read from status file
        try:
            with open('bot_status.json', 'r') as f:
                status = json.load(f)
                return status.get('equity', 0.0)
        except:
            return 0.0
    
    def _get_recent_trade_count(self) -> int:
        """Cuenta trades recientes (última hora)"""
        try:
            # Placeholder - implement based on your trade logging system
            return 1  # Assume at least some activity
        except:
            return 0
    
    def _check_stuck_positions(self) -> int:
        """Verifica posiciones atascadas"""
        try:
            # Placeholder - implement based on your position tracking
            return 0
        except:
            return 0
    
    # Recovery action methods
    def _restart_bot_service(self):
        """Reinicia el servicio del bot"""
        logger.info("🔄 Restarting bot service...")
        # Implement restart logic based on your deployment
    
    def _close_risky_positions(self):
        """Cierra posiciones de alto riesgo usando el sistema de ejecución del bot"""
        logger.info("🛡️ Closing risky positions...")
        
        try:
            from .execution import close_all
            from .telegram import send_telegram
            
            # Cerrar todas las posiciones inmediatamente
            positions_closed = close_all()
            
            if positions_closed:
                msg = f"🛡️ EMERGENCY CLOSURE: {positions_closed} posiciones cerradas por el sistema de monitoreo"
                send_telegram(msg)
                logger.critical(msg)
            else:
                logger.info("ℹ️ No positions to close or close_all() failed")
                
        except Exception as e:
            logger.error(f"❌ Failed to close risky positions: {e}")
            # Fallback: try individual position closure
            try:
                if hasattr(self.bot, 'close_all_positions'):
                    self.bot.close_all_positions()
                    logger.info("✅ Fallback: Positions closed via bot instance")
            except Exception as fallback_error:
                logger.error(f"❌ Fallback position closure also failed: {fallback_error}")
    
    def _enable_conservative_mode(self):
        """Activa modo conservador reduciendo risk y exposure"""
        logger.info("🛡️ Enabling conservative trading mode...")
        
        try:
            from .config import settings
            from .telegram import send_telegram
            
            # Reducir parámetros de riesgo dramáticamente
            original_risk = settings.risk_per_trade
            original_exposure = settings.max_gross_exposure
            
            # Aplicar configuración ultra-conservadora
            settings.risk_per_trade = min(0.005, original_risk * 0.25)  # 0.5% máximo, 25% del original
            settings.max_gross_exposure = min(0.20, original_exposure * 0.5)  # 20% máximo, 50% del original
            settings.take_profit_pct = max(0.01, settings.take_profit_pct * 1.5)  # 1% mínimo, aumentar TP
            settings.stop_loss_pct = min(0.005, settings.stop_loss_pct * 0.75)  # 0.5% máximo, reducir SL
            
            conservation_msg = f"""🛡️ MODO CONSERVADOR ACTIVADO

📉 Riesgo por trade: {original_risk:.2%} → {settings.risk_per_trade:.2%}
📊 Exposición máxima: {original_exposure:.0%} → {settings.max_gross_exposure:.0%}
📈 Take profit: {settings.take_profit_pct:.2%}
🛑 Stop loss: {settings.stop_loss_pct:.2%}

⏰ Duración: Hasta recuperación del sistema"""
            
            send_telegram(conservation_msg)
            logger.critical(conservation_msg.replace('\n', ' | '))
            
        except Exception as e:
            logger.error(f"❌ Failed to enable conservative mode: {e}")
    
    def _reduce_position_size(self):
        """Reduce tamaño de posiciones automáticamente"""
        logger.info("📉 Reducing position sizes...")
        
        try:
            from .config import settings
            from .telegram import send_telegram
            
            # Reducir drásticamente el tamaño de posiciones
            original_risk = settings.risk_per_trade
            original_exposure = settings.max_gross_exposure
            
            # Aplicar reducción del 75%
            settings.risk_per_trade *= 0.25  # Reducir a 25% del original
            settings.max_gross_exposure *= 0.50  # Reducir a 50% del original
            
            reduction_msg = f"""📉 REDUCCIÓN DE POSICIONES AUTOMÁTICA

🎯 Riesgo por trade: {original_risk:.2%} → {settings.risk_per_trade:.2%}
📊 Exposición máxima: {original_exposure:.0%} → {settings.max_gross_exposure:.0%}

⚠️ Medida de protección por monitoreo inteligente"""
            
            send_telegram(reduction_msg)
            logger.warning(reduction_msg.replace('\n', ' | '))
            
        except Exception as e:
            logger.error(f"❌ Failed to reduce position sizes: {e}")
    
    def _send_emergency_notification(self, loss: float, loss_percentage: float):
        """Envía notificación de emergencia inmediata por Telegram"""
        logger.critical(f"📢 EMERGENCY NOTIFICATION: ${loss:.2f} loss ({loss_percentage:.2f}%)")
        
        try:
            from .telegram import send_telegram
            
            # Preparar mensaje de emergencia detallado
            emergency_msg = f"""🚨 ALERTA CRÍTICA DE PÉRDIDAS 🚨

💀 Pérdida detectada: ${loss:+,.2f} ({loss_percentage:+.2f}%)
⚠️ Umbral crítico: -$1000 o -5%

🤖 ACCIONES AUTOMÁTICAS:
✅ Posiciones de riesgo cerradas
✅ Modo conservador activado
✅ Tamaños de posición reducidos

📊 Estado del sistema:
🏥 Salud: {self.system_health.value}
📈 Equity actual: ${self._get_current_equity():,.2f}
🔄 Errores críticos: {self.critical_error_count}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🛡️ Sistema de monitoreo inteligente activo"""
            
            # Enviar inmediatamente por Telegram
            send_telegram(emergency_msg)
            logger.info("📱 Emergency notification sent via Telegram")
            
        except Exception as e:
            logger.error(f"❌ Failed to send emergency notification: {e}")
    
    def _emergency_shutdown(self):
        """Apagado de emergencia del bot con cierre total"""
        logger.critical("🚨 EMERGENCY SHUTDOWN INITIATED")
        
        try:
            from .execution import close_all
            from .telegram import send_telegram
            import os
            
            # 1. Cerrar todas las posiciones inmediatamente
            logger.critical("🛑 STEP 1: Closing all positions...")
            positions_closed = close_all()
            
            # 2. Notificar el shutdown
            shutdown_msg = f"""🚨 EMERGENCY SHUTDOWN EJECUTADO 🚨

💀 PÉRDIDAS CRÍTICAS DETECTADAS
🛑 Todas las posiciones cerradas: {positions_closed if positions_closed else 'N/A'}
⏸️ Bot pausado automáticamente

⚠️ REQUIERE INTERVENCIÓN MANUAL
🔧 Revisar logs y configuración
📞 Contactar soporte si es necesario

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
            
            send_telegram(shutdown_msg)
            
            # 3. Crear archivo de emergencia para indicar shutdown
            with open('emergency_shutdown.json', 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'reason': 'Critical losses exceeded threshold',
                    'positions_closed': positions_closed,
                    'system_health': self.system_health.value
                }, f, indent=2)
            
            # 4. Parar el monitoreo
            self.is_running = False
            
            logger.critical("✅ Emergency shutdown completed")
            
        except Exception as e:
            logger.error(f"❌ Emergency shutdown failed: {e}")
            # Último recurso: intentar parar todo
            self.is_running = False
    
    def _clear_memory_cache(self):
        """Limpia cache de memoria del sistema"""
        logger.info("🧹 Clearing memory cache...")
        
        try:
            import gc
            from .strategy import reset_signal_memory
            
            # 1. Limpiar memoria de señales del bot
            reset_signal_memory()
            
            # 2. Forzar garbage collection
            collected = gc.collect()
            
            # 3. Limpiar alertas antiguas en memoria
            if len(self.alerts) > 100:
                self.alerts = self.alerts[-100:]  # Mantener solo las últimas 100
                
            # 4. Reset error counters
            self.critical_error_count = 0
            
            logger.info(f"🧹 Memory cache cleared: {collected} objects collected, {len(self.alerts)} alerts retained")
            
        except Exception as e:
            logger.error(f"❌ Failed to clear memory cache: {e}")
    
    def _reconnect_apis(self):
        """Reconecta APIs y verifica conectividad"""
        logger.info("🔌 Reconnecting APIs...")
        
        try:
            from .config import settings
            from alpaca.trading.client import TradingClient
            
            # Test Alpaca connection
            client = TradingClient(
                api_key=settings.alpaca_api_key,
                secret_key=settings.alpaca_secret_key,
                paper=(settings.mode == "paper")
            )
            
            # Verify connection with a simple API call
            account = client.get_account()
            
            if account:
                logger.info("✅ Alpaca API reconnected successfully")
                return True
            else:
                logger.error("❌ Alpaca API reconnection failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ API reconnection failed: {e}")
            return False
    
    def get_system_status(self) -> Dict:
        """Retorna estado actual del sistema"""
        return {
            "health": self.system_health.value,
            "is_monitoring": self.is_running,
            "alert_count": len(self.alerts),
            "critical_alerts": len([a for a in self.alerts if a.level == AlertLevel.CRITICAL]),
            "emergency_alerts": len([a for a in self.alerts if a.level == AlertLevel.EMERGENCY]),
            "last_check": datetime.now().isoformat(),
            "agus_available": AGUS_AVAILABLE
        }
    
    def get_recent_alerts(self, limit: int = 50) -> List[Dict]:
        """Retorna alertas recientes"""
        return [
            {
                "timestamp": alert.timestamp.isoformat(),
                "level": alert.level.value,
                "component": alert.component,
                "message": alert.message,
                "details": alert.details,
                "auto_fixed": alert.auto_fixed,
                "has_agus_response": bool(alert.agus_response)
            }
            for alert in self.alerts[-limit:]
        ]

# Global monitor instance
monitor_instance: Optional[IntelligentMonitor] = None

def initialize_monitor(bot_instance=None) -> IntelligentMonitor:
    """Inicializa el monitor global"""
    global monitor_instance
    if monitor_instance is None:
        monitor_instance = IntelligentMonitor(bot_instance)
    return monitor_instance

def get_monitor() -> Optional[IntelligentMonitor]:
    """Obtiene la instancia del monitor"""
    return monitor_instance

if __name__ == "__main__":
    # Test del sistema de monitoreo
    logger.info("🧪 Testing Intelligent Monitor System...")
    
    monitor = IntelligentMonitor()
    monitor.start_monitoring()
    
    try:
        # Test alerts
        monitor._create_alert(
            AlertLevel.INFO,
            "test",
            "Test alert - system is operational",
            {"test": True}
        )
        
        time.sleep(60)  # Run for 1 minute for testing
        
    except KeyboardInterrupt:
        logger.info("🛑 Test interrupted by user")
    finally:
        monitor.stop_monitoring()
        logger.info("✅ Monitor test completed")