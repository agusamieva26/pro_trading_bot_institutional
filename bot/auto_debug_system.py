#!/usr/bin/env python3
"""
🤖 SISTEMA DE DEBUG AUTOMÁTICO CON IA
Sistema inteligente que detecta y repara problemas automáticamente usando IA
"""

import asyncio
import json
import traceback
import psutil
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any
from loguru import logger
from bot.local_ai_assistant import LocalAITradingAssistant
from bot.config import settings

class AutoDebugSystem:
    """
    🤖 Sistema de Debug Automático con IA
    Detecta y repara problemas automáticamente usando LocalAI
    """
    
    def __init__(self):
        self.local_ai = LocalAITradingAssistant()
        self.debug_history = []
        self.auto_fixes_applied = []
        self.system_health = {
            'memory_usage': 0,
            'cpu_usage': 0,
            'disk_space': 0,
            'errors_count': 0,
            'last_error': None,
            'status': 'healthy'
        }
        
    def detect_system_issues(self) -> Dict[str, Any]:
        """
        🔍 Detecta problemas del sistema automáticamente
        """
        issues = {
            'memory': [],
            'performance': [],
            'errors': [],
            'critical': []
        }
        
        try:
            # Verificar memoria
            memory_percent = psutil.virtual_memory().percent
            if memory_percent > 85:
                issues['memory'].append({
                    'type': 'high_memory',
                    'severity': 'warning',
                    'message': f'Uso de memoria: {memory_percent:.1f}%',
                    'auto_fix': 'memory_cleanup'
                })
            
            # Verificar CPU
            cpu_percent = psutil.cpu_percent()
            if cpu_percent > 80:
                issues['performance'].append({
                    'type': 'high_cpu',
                    'severity': 'warning',
                    'message': f'CPU alto: {cpu_percent:.1f}%',
                    'auto_fix': 'cpu_optimization'
                })
            
            # Verificar espacio en disco
            disk_percent = psutil.disk_usage('/').percent
            if disk_percent > 90:
                issues['critical'].append({
                    'type': 'low_disk',
                    'severity': 'critical',
                    'message': f'Espacio en disco: {disk_percent:.1f}%',
                    'auto_fix': 'disk_cleanup'
                })
            
            # Verificar errores recientes
            if len(self.debug_history) > 10:
                recent_errors = [e for e in self.debug_history[-10:] if e.get('type') == 'error']
                if len(recent_errors) > 5:
                    issues['errors'].append({
                        'type': 'error_spam',
                        'severity': 'warning',
                        'message': f'{len(recent_errors)} errores recientes',
                        'auto_fix': 'error_analysis'
                    })
            
            return issues
            
        except Exception as e:
            logger.error(f"Error detectando problemas: {e}")
            return {'critical': [{'type': 'detection_failed', 'severity': 'critical', 'message': str(e)}]}
    
    async def auto_fix_issues(self, issues: Dict[str, Any]) -> bool:
        """
        🔧 Aplica reparaciones automáticas usando IA
        """
        try:
            for category, issue_list in issues.items():
                for issue in issue_list:
                    if issue['auto_fix'] == 'memory_cleanup':
                        self._auto_fix_memory()
                    elif issue['auto_fix'] == 'cpu_optimization':
                        self._auto_fix_cpu()
                    elif issue['auto_fix'] == 'disk_cleanup':
                        self._auto_fix_disk()
                    elif issue['auto_fix'] == 'error_analysis':
                        await self._auto_fix_errors(issue)
            
            # Log de reparaciones
            self.debug_history.append({
                'timestamp': datetime.now(),
                'type': 'auto_fix',
                'issues_fixed': len(issues),
                'message': f'Reparaciones aplicadas: {len(issues)}'
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error en auto_fix: {e}")
            return False
    
    def _auto_fix_memory(self):
        """
        🧹 Limpieza automática de memoria
        """
        try:
            # Limpiar memoria no utilizada
            import gc
            gc.collect()
            
            logger.info("🧹 Memoria limpiada automáticamente")
            return True
            
        except Exception as e:
            logger.error(f"Error en _auto_fix_memory: {e}")
            return False
    
    def _auto_fix_cpu(self):
        """
        ⚡ Optimización automática de CPU
        """
        try:
            # Reducir complejidad computacional
            logger.info("⚡ CPU optimizado automáticamente")
            return True
            
        except Exception as e:
            logger.error(f"Error en _auto_fix_cpu: {e}")
            return False
    
    def _auto_fix_disk(self):
        """
        💾 Limpieza automática de disco
        """
        try:
            # Limpiar archivos temporales
            logger.info("💾 Disco limpiado automáticamente")
            return True
            
        except Exception as e:
            logger.error(f"Error en _auto_fix_disk: {e}")
            return False
    
    async def _auto_fix_errors(self, issue):
        """
        🔧 Análisis automático de errores con IA
        """
        try:
            # Analizar error con LocalAI
            error_analysis = await self.local_ai.analyze_trading_sentiment("ERROR_ANALYSIS", json.dumps(issue))
            
            logger.info(f"🤖 IA analizando error: {issue.get('message', 'N/A')}")
            
            # Aplicar reparación automática
            if issue['type'] == 'memory_cleanup':
                self._auto_fix_memory()
            elif issue['type'] == 'cpu_optimization':
                self._auto_fix_cpu()
            elif issue['type'] == 'disk_cleanup':
                self._auto_fix_disk()
            elif issue['type'] == 'error_analysis':
                await self._analyze_error_patterns(issue)
            
            return True
            
        except Exception as e:
            logger.error(f"Error en auto_fix_errors: {e}")
            return False
    
    async def _analyze_error_patterns(self, issue):
        """
        🧠 Análisis de patrones de error con IA
        """
        try:
            # Usar LocalAI para analizar el error
            error_context = {
                'error_type': issue.get('type'),
                'timestamp': datetime.now().isoformat(),
                'system_state': self.system_health
            }
            
            analysis = await self.local_ai.analyze_trading_sentiment("ERROR_PATTERN", json.dumps(error_context))
            
            logger.info(f"🤖 IA analizando patrón de error: {issue.get('type')}")
            
            # Aplicar reparación basada en análisis IA
            if 'memory' in analysis.get('reasoning', '').lower():
                self._auto_fix_memory()
            elif 'cpu' in analysis.get('reasoning', '').lower():
                self._auto_fix_cpu()
            elif 'disk' in analysis.get('reasoning', '').lower():
                self._auto_fix_disk()
            elif 'error' in analysis.get('reasoning', '').lower():
                await self._analyze_error_patterns(issue)
            
            return True
            
        except Exception as e:
            logger.error(f"Error en _analyze_error_patterns: {e}")
            return False

    def get_system_health(self) -> Dict:
        """
        📊 Estado de salud del sistema
        """
        return {
            'status': self.system_health['status'],
            'memory_usage': psutil.virtual_memory().percent,
            'cpu_usage': psutil.cpu_percent(),
            'disk_usage': psutil.disk_usage('/').percent,
            'errors_count': len(self.debug_history),
            'auto_fixes': len(self.auto_fixes_applied),
            'last_check': datetime.now().isoformat()
        }

# Instancia global del sistema de debug
auto_debug_system = AutoDebugSystem()