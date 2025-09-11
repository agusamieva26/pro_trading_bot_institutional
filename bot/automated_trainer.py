#!/usr/bin/env python3
"""
Sistema de Entrenamiento y Optimización Automática
Máquina evolutiva que se entrena y optimiza automáticamente con triggers inteligentes
"""

import schedule
import time
import sys
import os
import subprocess
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
import numpy as np
from pathlib import Path

# Import bot modules
from bot.util import logger
from bot.config import settings
from bot.telegram import send_telegram
from bot.reporter import generate_daily_report

# Add project root to path
sys.path.insert(0, '.')

class AutomatedTrainer:
    """Sistema de entrenamiento automático inteligente."""
    
    def __init__(self):
        self.madrid_tz = ZoneInfo("Europe/Madrid")
        self.last_training_date = None
        self.last_optimization_date = None
        self.performance_history = []
        self.emergency_training_triggered = False
        
    def analyze_recent_performance(self) -> dict:
        """Analiza el rendimiento reciente del bot."""
        try:
            # Leer últimas operaciones
            trades_file = Path("trades_log.csv")
            if not trades_file.exists():
                return {"win_rate": 55, "daily_pnl": 0, "drawdown": 0}
            
            df = pd.read_csv(trades_file)
            if df.empty:
                return {"win_rate": 55, "daily_pnl": 0, "drawdown": 0}
            
            # Analizar últimas 50 operaciones
            recent_trades = df.tail(50) if len(df) >= 50 else df
            
            # Calcular métricas
            win_rate = (recent_trades['pnl'] > 0).mean() * 100
            daily_pnl = recent_trades['pnl'].sum()
            
            # Calcular drawdown (aproximado)
            cumulative_pnl = recent_trades['pnl'].cumsum()
            peak = cumulative_pnl.expanding().max()
            drawdown = ((peak - cumulative_pnl) / peak * 100).max()
            
            logger.info(f"📊 Performance Analysis: Win Rate={win_rate:.1f}%, Daily P&L=${daily_pnl:.2f}, Drawdown={drawdown:.1f}%")
            
            return {
                "win_rate": win_rate,
                "daily_pnl": daily_pnl,
                "drawdown": drawdown if not np.isnan(drawdown) else 0
            }
            
        except Exception as e:
            logger.error(f"❌ Error analyzing performance: {e}")
            return {"win_rate": 55, "daily_pnl": 0, "drawdown": 0}
    
    def check_intelligent_triggers(self) -> dict:
        """Revisa triggers inteligentes para entrenamiento/optimización."""
        performance = self.analyze_recent_performance()
        triggers = {
            "emergency_training": False,
            "optuna_needed": False,
            "reason": ""
        }
        
        # Trigger 1: Win rate bajo
        if performance["win_rate"] < 50:
            triggers["emergency_training"] = True
            triggers["reason"] = f"Win rate crítico: {performance['win_rate']:.1f}% < 50%"
        
        # Trigger 2: Drawdown alto
        elif performance["drawdown"] > 5:
            triggers["emergency_training"] = True
            triggers["optuna_needed"] = True
            triggers["reason"] = f"Drawdown alto: {performance['drawdown']:.1f}% > 5%"
        
        # Trigger 3: P&L negativo consistente
        elif performance["daily_pnl"] < -100:
            triggers["optuna_needed"] = True
            triggers["reason"] = f"P&L negativo: ${performance['daily_pnl']:.2f}"
        
        return triggers
    
    def run_model_training(self, reason="Programado"):
        """Ejecuta entrenamiento del modelo."""
        try:
            logger.info(f"🔄 Iniciando entrenamiento automático - Razón: {reason}")
            
            # Ejecutar script de entrenamiento
            result = subprocess.run(
                [sys.executable, "scripts/train_model.py"],
                capture_output=True,
                text=True,
                timeout=1800  # 30 minutos máximo
            )
            
            if result.returncode == 0:
                logger.info("✅ Entrenamiento completado exitosamente")
                send_telegram(f"🤖 ENTRENAMIENTO AUTOMÁTICO COMPLETADO\n\n"
                            f"📅 Fecha: {datetime.now(self.madrid_tz).strftime('%Y-%m-%d %H:%M:%S')}\n"
                            f"🎯 Razón: {reason}\n"
                            f"✅ Estado: Exitoso\n"
                            f"🔄 Modelo actualizado y listo")
                self.last_training_date = datetime.now()
                return True
            else:
                logger.error(f"❌ Error en entrenamiento: {result.stderr}")
                send_telegram(f"🚨 ERROR EN ENTRENAMIENTO AUTOMÁTICO\n\n"
                            f"📅 Fecha: {datetime.now(self.madrid_tz).strftime('%Y-%m-%d %H:%M:%S')}\n"
                            f"❌ Error: {result.stderr[:200]}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("⏰ Timeout en entrenamiento (30 min)")
            return False
        except Exception as e:
            logger.error(f"❌ Error ejecutando entrenamiento: {e}")
            return False
    
    def run_optuna_optimization(self, reason="Programado"):
        """Ejecuta optimización Optuna."""
        try:
            logger.info(f"⚡ Iniciando optimización Optuna - Razón: {reason}")
            
            # Ejecutar optimización avanzada
            result = subprocess.run(
                [sys.executable, "-c", "from bot.advanced_optimizer import advanced_optimizer; advanced_optimizer.run_advanced_optimization()"],
                capture_output=True,
                text=True,
                timeout=2400  # 40 minutos máximo
            )
            
            if result.returncode == 0:
                logger.info("✅ Optimización Optuna completada")
                send_telegram(f"⚡ OPTIMIZACIÓN OPTUNA COMPLETADA\n\n"
                            f"📅 Fecha: {datetime.now(self.madrid_tz).strftime('%Y-%m-%d %H:%M:%S')}\n"
                            f"🎯 Razón: {reason}\n"
                            f"✅ Estado: Exitoso\n"
                            f"🚀 Hiperparámetros optimizados\n"
                            f"🔄 Iniciando reentrenamiento con nuevos parámetros...")
                
                # Entrenar con nuevos parámetros
                self.run_model_training("Post-Optuna")
                self.last_optimization_date = datetime.now()
                return True
            else:
                logger.error(f"❌ Error en optimización: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("⏰ Timeout en optimización (40 min)")
            return False
        except Exception as e:
            logger.error(f"❌ Error ejecutando optimización: {e}")
            return False
    
    def daily_performance_check(self):
        """Chequeo diario de rendimiento y triggers."""
        logger.info("📊 Ejecutando chequeo diario de performance...")
        
        # Generar reporte diario
        generate_daily_report()
        
        # Revisar triggers inteligentes
        triggers = self.check_intelligent_triggers()
        
        if triggers["emergency_training"]:
            logger.warning(f"🚨 TRIGGER ACTIVADO: {triggers['reason']}")
            send_telegram(f"🚨 ENTRENAMIENTO EMERGENCIA ACTIVADO\n\n"
                        f"🎯 Razón: {triggers['reason']}\n"
                        f"⏰ Iniciando en 5 minutos...")
            
            # Programar entrenamiento de emergencia en 5 minutos
            schedule.every(5).minutes.do(
                lambda: self.run_emergency_training(triggers['reason'])
            ).tag('emergency')
            
        elif triggers["optuna_needed"]:
            logger.warning(f"⚡ OPTUNA TRIGGER: {triggers['reason']}")
            # Programar optimización en 30 minutos
            schedule.every(30).minutes.do(
                lambda: self.run_optuna_optimization(f"Trigger: {triggers['reason']}")
            ).tag('emergency')
    
    def run_emergency_training(self, reason):
        """Ejecuta entrenamiento de emergencia y limpia el schedule."""
        self.run_model_training(f"EMERGENCIA: {reason}")
        schedule.clear('emergency')  # Limpiar tareas de emergencia
    
    def biweekly_training(self):
        """Entrenamiento bi-semanal programado."""
        logger.info("📅 Ejecutando entrenamiento bi-semanal programado")
        self.run_model_training("Bi-semanal programado")
    
    def weekly_optimization(self):
        """Optimización semanal (lunes)."""
        logger.info("🚀 Ejecutando optimización semanal (Lunes)")
        self.run_optuna_optimization("Semanal - Lunes")
    
    def setup_automated_schedule(self):
        """Configura todo el sistema de programación automática."""
        logger.info("🤖 Configurando sistema de automatización completo...")
        
        # 1. REPORTE DIARIO + PERFORMANCE CHECK (00:00)
        schedule.every().day.at("00:00").do(self.daily_performance_check)
        
        # 2. ENTRENAMIENTO BI-SEMANAL (Viernes 02:00)
        schedule.every(14).days.at("02:00").do(self.biweekly_training)
        
        # 3. OPTIMIZACIÓN SEMANAL (Lunes 02:00) 
        schedule.every().monday.at("02:00").do(self.weekly_optimization)
        
        # Log del setup
        now = datetime.now(self.madrid_tz)
        logger.info(f"✅ SISTEMA AUTOMATIZADO CONFIGURADO:")
        logger.info(f"📅 Diario 00:00: Performance check + Triggers")
        logger.info(f"📅 Cada 14 días (Viernes 02:00): Entrenamiento bi-semanal")
        logger.info(f"📅 Lunes 02:00: Optimización Optuna + Reentrenamiento")
        logger.info(f"⏰ Hora actual España: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        # Telegram de confirmación
        send_telegram(f"🤖 SISTEMA AUTOMATIZADO ACTIVADO\n\n"
                     f"📊 PROGRAMACIÓN:\n"
                     f"• Diario 00:00: Análisis performance\n" 
                     f"• Cada 14 días: Entrenamiento automático\n"
                     f"• Lunes 02:00: Optuna + Reentrenamiento\n\n"
                     f"🚨 TRIGGERS INTELIGENTES:\n"
                     f"• Win rate <50%: Training inmediato\n"
                     f"• Drawdown >5%: Optuna + Training\n"
                     f"• P&L <-$100: Optimización\n\n"
                     f"🚀 TU BOT AHORA ES COMPLETAMENTE EVOLUTIVO")
    
    def run_automated_system(self):
        """Ejecuta el sistema automatizado principal."""
        self.setup_automated_schedule()
        
        logger.info("🔄 Sistema automatizado iniciado - Esperando eventos programados...")
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # Revisa cada minuto


# Instancia global
automated_trainer = AutomatedTrainer()

def run_automated_trainer():
    """Función principal para ejecutar el sistema automatizado."""
    automated_trainer.run_automated_system()

if __name__ == "__main__":
    run_automated_trainer()