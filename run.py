# run.py
import threading
import time
import subprocess
import webbrowser
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

def run_dashboard():
    """Ejecuta el dashboard de Streamlit y abre automáticamente el navegador."""
    try:
        logger.info("🚀 Iniciando dashboard de Streamlit...")
        
        # Esperar un poco para que el servidor inicie
        def open_browser():
            time.sleep(3)  # Esperar 3 segundos para que Streamlit inicie
            webbrowser.open('http://0.0.0.0:5000')
            logger.info("🌐 Navegador abierto automáticamente en http://0.0.0.0:5000")
        
        # Abrir navegador en un thread separado
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()
        
        # Iniciar Streamlit
        subprocess.run([
            "streamlit", "run", "dashboard_modern.py", 
            "--server.port=5000", 
            "--server.address=0.0.0.0", 
            "--server.headless=true",
            "--browser.gatherUsageStats=false"
        ])
    except Exception as e:
        logger.error(f"❌ Error en dashboard: {e}")

def run_debug_monitor():
    """Ejecuta el monitor de debug 24/7 con reparación automática."""
    try:
        from bot.console_debug_monitor import run_debug_monitor
        run_debug_monitor()
    except Exception as e:
        logger.error(f"❌ Error en debug monitor: {e}")

if __name__ == "__main__":
    logger.info("🚀 Iniciando sistema evolutivo completo con Dashboard y Debug Monitor...")
    
    # Thread 1: Bot principal de trading
    t1 = threading.Thread(target=run_main, daemon=True, name="TradingBot")
    
    # Thread 2: Sistema de automatización completa (incluye reportes + entrenamiento + Optuna)
    t2 = threading.Thread(target=run_automation, daemon=True, name="AutomatedTrainer")
    
    # Thread 3: Dashboard de Streamlit con auto-apertura del navegador
    t3 = threading.Thread(target=run_dashboard, daemon=True, name="Dashboard")
    
    # Thread 4: Monitor de debug 24/7 con reparación automática
    t4 = threading.Thread(target=run_debug_monitor, daemon=True, name="DebugMonitor")

    logger.info("🤖 Iniciando threads del sistema...")
    t1.start()
    logger.info("✅ Thread 1: Trading Bot iniciado")
    
    t2.start()
    logger.info("✅ Thread 2: Sistema Automatizado iniciado (reportes + training + Optuna)")
    
    t3.start()
    logger.info("✅ Thread 3: Dashboard iniciado con auto-apertura del navegador")
    
    t4.start()
    logger.info("✅ Thread 4: Console Debug Monitor 24/7 iniciado (reparación automática)")
    
    logger.info("🚀 SISTEMA EVOLUTIVO COMPLETO ACTIVO")
    logger.info("📊 Trading Bot + Dashboard + Reportes + Training + Optuna + Debug Monitor")
    logger.info("🌐 Dashboard disponible en: http://0.0.0.0:5000 (se abrirá automáticamente)")
    logger.info("🔧 Debug Monitor: Monitoreo 24/7 con reparación automática de errores")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("🛑 Sistema completo detenido por el usuario.")
        print("🛑 Bot detenido por el usuario.")