# run.py
import threading
import time
from bot.main import main
from bot.automated_trainer import run_automated_trainer
from bot.util import logger

def run_main():
    """Ejecuta el bot principal de trading."""
    try:
        main()
    except Exception as e:
        logger.error(f"❌ Error en bot principal: {e}")

def run_automation():
    """Ejecuta el sistema de automatización completa (incluye reportes)."""
    try:
        run_automated_trainer()
    except Exception as e:
        logger.error(f"❌ Error en sistema automatizado: {e}")

if __name__ == "__main__":
    logger.info("🚀 Iniciando sistema evolutivo completo...")
    
    # Thread 1: Bot principal de trading
    t1 = threading.Thread(target=run_main, daemon=True, name="TradingBot")
    
    # Thread 2: Sistema de automatización completa (incluye reportes + entrenamiento + Optuna)
    t2 = threading.Thread(target=run_automation, daemon=True, name="AutomatedTrainer")

    logger.info("🤖 Iniciando threads del sistema...")
    t1.start()
    logger.info("✅ Thread 1: Trading Bot iniciado")
    
    t2.start()
    logger.info("✅ Thread 2: Sistema Automatizado iniciado (reportes + training + Optuna)")
    
    logger.info("🚀 SISTEMA EVOLUTIVO COMPLETO ACTIVO")
    logger.info("📊 Trading Bot + Reportes automáticos + Entrenamiento + Optuna")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("🛑 Sistema completo detenido por el usuario.")
        print("🛑 Bot detenido por el usuario.")