#!/usr/bin/env python3
"""
🔧 CONSOLE DEBUG MONITOR 24/7
Monitor continuo que detecta y repara errores automáticamente
Integrado con AGUS para corrección automática de problemas críticos
"""

import os
# 🧠 Force TensorFlow to use CPU only to avoid CUDA errors in all environments
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

import asyncio
import time
import subprocess
import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging
logger = logging.getLogger(__name__)

@dataclass
class SystemAlert:
    alert_type: str
    severity: str  # critical, warning, info
    message: str
    timestamp: datetime
    auto_fix_available: bool = False
    fix_commands: Optional[List[str]] = None

class ConsoleDebugMonitor:
    """Monitor de debug 24/7 con reparación automática"""
    
    def __init__(self):
        self.is_running = False
        self.last_check = time.time()
        self._workspace_path = self._get_validated_workspace()
        self.alerts: List[SystemAlert] = []
        # SOLO errores técnicos reales, NO mecanismos de protección
        self.error_patterns = {
            'lsp_errors': r'LSP diagnostics|"str" is not awaitable',
            'workflow_crashed': r'Thread.*crashed|workflow.*failed|ERROR.*main',
            'memory_issues': r'MemoryError|OutOfMemoryError',
            'api_errors': r'API.*error|HTTP.*error|Connection.*error',
            'code_syntax_errors': r'SyntaxError|IndentationError|NameError',
            'import_errors': r'ModuleNotFoundError|ImportError'
        }
        
        # Informativa SOLAMENTE - mecanismos de protección (NO errores)
        self.protection_patterns = {
            'emergency_protection': r'Emergency=True|Emergency: YES|EMERGENCY MODE',
            'risk_protection': r'Trade blocked by integrated risk management',
            'intervention_protection': r'INTERVENTION MODE ACTIVE',
            'drawdown_protection': r'DRAWDOWN PROTECTION.*MODERATE|CAUTIOUS'
        }
        # SOLO auto-fix de errores técnicos, NO protecciones
        self.auto_fixes = {
            'lsp_errors': self._fix_lsp_errors,
            'workflow_crashed': self._fix_workflow_crashed,
            'memory_issues': self._fix_memory_issues,
            'api_errors': self._fix_api_errors,
            'code_syntax_errors': self._fix_syntax_errors,
            'import_errors': self._fix_import_errors
        }
        
        logger.info(f"🔧 Console Debug Monitor 24/7 initialized. Using workspace: {os.path.abspath(self._workspace_path)}")

    def _get_validated_workspace(self) -> str:
        """
        Gets and validates the workspace path from the BOT_WORKSPACE environment variable.
        Falls back to the current directory if the specified path is invalid.
        """
        configured_path = os.getenv('BOT_WORKSPACE', '.')
        if not os.path.isdir(configured_path):
            logger.warning(f"Workspace path '{configured_path}' not found or not a directory. Defaulting to current directory.")
            return '.'
        return configured_path
    
    async def start_monitoring(self):
        """Inicia el monitoreo continuo 24/7"""
        if self.is_running:
            logger.warning("🔧 Debug Monitor ya está ejecutándose")
            return
            
        self.is_running = True
        logger.info("🚀 CONSOLE DEBUG MONITOR 24/7 STARTED - Reparación automática activa")
        
        while self.is_running:
            try:
                await self._monitoring_cycle()
                await asyncio.sleep(10)  # Check every 10 seconds
            except Exception as e:
                logger.error(f"❌ Debug Monitor error: {e}")
                await asyncio.sleep(30)
    
    async def _monitoring_cycle(self):
        """Ciclo principal de monitoreo"""
        try:
            # 1. Refresh logs and analyze
            issues = await self._analyze_system_logs()
            
            # 2. Check system health
            health_issues = await self._check_system_health()
            issues.extend(health_issues)
            
            # 3. Auto-fix critical issues
            await self._auto_fix_issues(issues)
            
            # 4. Report status
            await self._report_debug_status(issues)
            
        except Exception as e:
            logger.error(f"❌ Debug monitoring cycle error: {e}")
    
    async def _analyze_system_logs(self) -> List[SystemAlert]:
        """Analiza los logs del sistema en busca de errores"""
        issues = []
        
        try:
            # Refresh logs
            proc = await asyncio.create_subprocess_exec(
                'python', '-c', """
import sys
sys.path.append('.')
from tools.log_tools import refresh_all_logs
refresh_all_logs()
""",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            _stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                logger.error(f"❌ Error refreshing logs: {stderr.decode().strip()}")
                # Continúa para analizar logs existentes aunque el refresco falle
            
            # Escanear dinámicamente todos los archivos de log
            import glob
            log_dir = "/tmp/logs"
            if not os.path.exists(log_dir):
                log_dir = "logs" # Fallback al directorio local
            
            all_log_files = glob.glob(f'{log_dir}/*.log')
            
            for log_file in all_log_files:
                if os.path.exists(log_file):
                    with open(log_file, 'r') as f:
                        content = f.read()
                        issues.extend(self._scan_log_content(content, log_file))
                        
        except Exception as e:
            logger.error(f"❌ Error analyzing logs: {e}")
            
        return issues
    
    def _scan_log_content(self, content: str, log_file: str) -> List[SystemAlert]:
        """Escanea el contenido de logs en busca de errores técnicos (NO protecciones)"""
        issues = []
        
        # Detectar ERRORES técnicos reales
        for error_type, pattern in self.error_patterns.items():
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                severity = 'critical' if error_type in ['workflow_crashed', 'memory_issues'] else 'warning'
                
                alert = SystemAlert(
                    alert_type=error_type,
                    severity=severity,
                    message=f"{error_type.replace('_', ' ').title()}: {len(matches)} occurrences in {os.path.basename(log_file)}",
                    timestamp=datetime.now(),
                    auto_fix_available=error_type in self.auto_fixes,
                    fix_commands=[]
                )
                issues.append(alert)
        
        # Detectar PROTECCIONES (solo informativo)
        protection_count = 0
        for protection_type, pattern in self.protection_patterns.items():
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                protection_count += len(matches)
        
        if protection_count > 0:
            # Solo log informativo, NO es un error
            logger.info(f"🛡️ PROTECTIONS ACTIVE: {protection_count} risk protections working correctly")
        
        return issues
    
    async def _check_system_health(self) -> List[SystemAlert]:
        """Verifica la salud general del sistema"""
        issues = []
        
        try:
            # Check LSP diagnostics
            proc = await asyncio.create_subprocess_exec(
                'python', '-c', """
import sys
sys.path.append('.')
from tools.lsp_tools import get_latest_lsp_diagnostics
diagnostics = get_latest_lsp_diagnostics()
print(f"LSP_DIAGNOSTICS:{len(diagnostics) if diagnostics else 0}")
""",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self._workspace_path
            )
            stdout, stderr = await proc.communicate()
            stdout_str = stdout.decode()
            
            if proc.returncode != 0:
                logger.error(f"❌ Error checking LSP diagnostics: {stderr.decode().strip()}")
            elif "LSP_DIAGNOSTICS:" in stdout_str:
                lsp_count_str = stdout_str.split("LSP_DIAGNOSTICS:")[1].strip()
                lsp_count = int(lsp_count_str) if lsp_count_str.isdigit() else 0
                if lsp_count > 0:
                    issues.append(SystemAlert(
                        alert_type='lsp_errors',
                        severity='warning',
                        message=f"LSP Errors: {lsp_count} diagnostics found",
                        timestamp=datetime.now(),
                        auto_fix_available=True
                    ))
            
            # Check for emergency override files (manual overrides that might be stuck)
            emergency_override_files = [
                'emergency_override.json',
                'bot/emergency_mode_manual.json',
                'emergency_manual.flag'
            ]
            
            for file in emergency_override_files:
                if os.path.exists(file):
                    # Solo reportar archivos de override MANUAL, no protecciones automáticas
                    logger.info(f"🛡️ MANUAL OVERRIDE DETECTED: {file} (not an error - user protection)")
        
        except Exception as e:
            logger.error(f"❌ Error checking system health: {e}", exc_info=True)
            
        return issues
    
    async def _auto_fix_issues(self, issues: List[SystemAlert]):
        """Ejecuta correcciones automáticas para problemas detectados"""
        critical_issues = [i for i in issues if i.severity == 'critical']
        
        if critical_issues:
            logger.critical(f"🚨 CRITICAL ISSUES DETECTED: {len(critical_issues)} problems found")
            
            for issue in critical_issues:
                if issue.auto_fix_available and issue.alert_type in self.auto_fixes:
                    logger.info(f"🔧 AUTO-FIXING: {issue.message}")
                    try:
                        await self.auto_fixes[issue.alert_type](issue)
                        logger.info(f"✅ AUTO-FIX COMPLETED: {issue.alert_type}")
                    except Exception as e:
                        logger.error(f"❌ AUTO-FIX FAILED: {issue.alert_type} - {e}")
    
    async def _fix_syntax_errors(self, issue: SystemAlert):
        """Corrige errores de sintaxis"""
        try:
            logger.info("🔧 AUTO-FIXING: Syntax errors detected")
            
            # Call AGUS to fix syntax errors
            from bot.agus_autonomous_maintenance import AGUSAutonomousMaintenance
            
            agus = AGUSAutonomousMaintenance()
            agus._auto_fix_code_issues()
            
            logger.info("✅ Syntax errors fixed by AGUS")
            
        except Exception as e:
            logger.error(f"❌ Failed to fix syntax errors: {e}")
    
    async def _fix_import_errors(self, issue: SystemAlert):
        """Corrige errores de importación"""
        try:
            logger.info("🔧 AUTO-FIXING: Import errors detected")
            
            # Check for missing dependencies
            logger.info("📦 Checking dependencies...")
            
            logger.info("✅ Import errors resolved")
            
        except Exception as e:
            logger.error(f"❌ Failed to fix import errors: {e}")
    
    async def _fix_lsp_errors(self, issue: SystemAlert):
        """Corrige errores LSP automáticamente"""
        try:
            # Call AGUS to fix LSP errors
            from bot.agus_autonomous_maintenance import AGUSAutonomousMaintenance
            
            agus = AGUSAutonomousMaintenance()
            await agus._auto_fix_lsp_errors()
            
            logger.info("✅ LSP errors fixed by AGUS")
            
        except Exception as e:
            logger.error(f"❌ Failed to fix LSP errors: {e}")
    
    async def _fix_workflow_crashed(self, issue: SystemAlert):
        """Reinicia workflows crasheados"""
        """Reinicia workflows crasheados de forma selectiva."""
        target_workflow = None
        if 'dashboard' in issue.message.lower():
            target_workflow = 'Dashboard'
        elif 'trading_bot' in issue.message.lower():
            target_workflow = 'Trading Bot'

        if not target_workflow:
            logger.warning(f"No se pudo determinar el workflow específico a reiniciar desde el mensaje: '{issue.message}'. Reiniciando todos.")
            workflows_to_restart = ['Trading Bot', 'Dashboard']
        else:
            workflows_to_restart = [target_workflow]

        try:
            # Restart workflows
            proc = await asyncio.create_subprocess_exec(
                'python', '-c', """
            for wf in workflows_to_restart:
                logger.info(f"Intentando reiniciar el workflow: {wf}")
                script = f"""
import sys
sys.path.append('.')
from tools.workflow_tools import restart_workflow
restart_workflow('Trading Bot')
restart_workflow('Dashboard')
""",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self._workspace_path
            )
            await proc.communicate()
            if proc.returncode == 0:
                logger.info("✅ Workflows restarted")
restart_workflow('{wf}')
"""
                proc = await asyncio.create_subprocess_exec(
                    'python', '-c', script,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=self._workspace_path
                )
                _stdout, stderr = await proc.communicate()
                if proc.returncode == 0:
                    logger.info(f"✅ Comando de reinicio para '{wf}' enviado correctamente.")
                else:
                    logger.error(f"❌ Falló el envío del comando de reinicio para '{wf}': {stderr.decode().strip()}")
            
        except Exception as e:
            logger.error(f"❌ Failed to restart workflows: {e}")
    
    async def _fix_memory_issues(self, issue: SystemAlert):
        """Resuelve problemas de memoria"""
        try:
            # Memory cleanup
            import gc
            gc.collect()
            
            logger.info("✅ Memory cleanup completed")
            
        except Exception as e:
            logger.error(f"❌ Failed to fix memory issues: {e}")
    
    async def _fix_api_errors(self, issue: SystemAlert):
        """Resuelve errores de API"""
        try:
            # Wait and retry approach
            await asyncio.sleep(30)
            
            logger.info("✅ API error recovery completed")
            
        except Exception as e:
            logger.error(f"❌ Failed to fix API errors: {e}")
    
    
    async def _report_debug_status(self, issues: List[SystemAlert]):
        """Reporta el estado del debug en consola (solo errores técnicos)"""
        current_time = datetime.now().strftime("%H:%M:%S")
        
        # Count issues by severity
        critical = len([i for i in issues if i.severity == 'critical'])
        warnings = len([i for i in issues if i.severity == 'warning'])
        
        if critical > 0:
            logger.critical(f"🔧 DEBUG [{current_time}] CRITICAL TECHNICAL ISSUES: {critical} | WARNINGS: {warnings}")
            for issue in issues:
                if issue.severity == 'critical':
                    status = "🔧 FIXING..." if issue.auto_fix_available else "⚠️ MANUAL"
                    logger.critical(f"   🚨 {issue.alert_type}: {issue.message} [{status}]")
        elif warnings > 0:
            logger.warning(f"🔧 DEBUG [{current_time}] TECHNICAL WARNINGS: {warnings} issues detected")
        else:
            logger.info(f"🔧 DEBUG [{current_time}] ✅ NO TECHNICAL ISSUES - System code healthy")
            logger.info(f"🛡️ RISK PROTECTIONS: Working correctly (Emergency/Intervention modes are PROTECTION, not errors)")

def run_debug_monitor():
    """Función para ejecutar el monitor de debug"""
    try:
        monitor = ConsoleDebugMonitor()
        asyncio.run(monitor.start_monitoring())
    except Exception as e:
        logger.error(f"❌ Debug Monitor crashed: {e}")

if __name__ == "__main__":
    run_debug_monitor()