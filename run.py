# run.py
import threading
import time
import subprocess
import sys
import asyncio
import webbrowser
import os
from bot.main import main
from bot.automated_trainer import run_automated_trainer
from bot.auto_debug_system import auto_debug_system
from bot.util import logger

# Suprimir mensajes informativos de TensorFlow y errores de CUDA si no hay GPU
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

def run_main():
    """Ejecuta el bot principal de trading con debug automático."""
    try:
        # Iniciar sistema de debug automático
        logger.info("🤖 Iniciando sistema de debug automático con IA...")
        
        # Verificar salud del sistema antes de iniciar
        # Comprobar si el modelo existe y entrenarlo si es necesario
        legacy_model_path = "models/rf_clf.pkl"
        new_model_path = "models/ensemble_rf.joblib" # Check for one of the new models
        models_exist = os.path.exists(legacy_model_path) or os.path.exists(new_model_path)

        if not models_exist:
            logger.warning("⚠️ No se encontraron modelos en 'models/'. Iniciando entrenamiento automático...")
            print("="*60)
            print("🤖 MODELO DE IA NO ENCONTRADO. INICIANDO ENTRENAMIENTO INICIAL.")
            print("   Este proceso puede tardar varios minutos. Por favor, espera...")
            print("="*60)
            try:
                # Ejecutar el script de entrenamiento
                subprocess.run([sys.executable, "train_models.py"], check=True, timeout=1800) # 30 min timeout
                logger.info("✅ Entrenamiento completado. El modelo ahora existe.")
            except Exception as e:
                logger.error(f"❌ Falló el entrenamiento automático: {e}. El bot no puede iniciar sin un modelo.")
                return # Detener este hilo si el entrenamiento falla
        health = auto_debug_system.get_system_health()
        logger.info(f"📊 Estado del sistema: {health}")
        
        # Detectar y reparar problemas automáticamente
        issues = auto_debug_system.detect_system_issues()
        if any(issues.values()):
            logger.warning("🔧 Problemas detectados, aplicando reparaciones automáticas...")
            asyncio.run(auto_debug_system.auto_fix_issues(issues))
            logger.info("✅ Reparaciones aplicadas automáticamente")
        
        # Ejecutar bot principal
        main()
        
    except Exception as e:
        logger.error(f"❌ Error en bot principal: {e}")
        
        # Intentar reparación automática del error
        try:
            error_context = {
                'type': 'critical_error',
                'message': str(e),
                'timestamp': time.time()
            }
            
            asyncio.run(auto_debug_system._analyze_error_patterns(error_context))
            logger.info("🤖 IA analizando error crítico...")
            
        except Exception as debug_error:
            logger.error(f"❌ Error en sistema de debug: {debug_error}")

def run_automation():
    """Ejecuta el sistema de automatización completa con debug automático."""
    try:
        # Verificar sistema antes de automatización
        health = auto_debug_system.get_system_health()
        logger.info(f"📊 Estado antes de automatización: {health}")
        
        # Detectar problemas
        issues = auto_debug_system.detect_system_issues()
        if any(issues.values()):
            logger.warning("🔧 Problemas detectados en automatización...")
            asyncio.run(auto_debug_system.auto_fix_issues(issues))
            logger.info("✅ Reparaciones aplicadas")
        
        # Ejecutar automatización
        run_automated_trainer()
        
    except Exception as e:
        logger.error(f"❌ Error en sistema automatizado: {e}")
        
        # Reparación automática
        try:
            error_context = {
                'type': 'automation_error',
                'message': str(e),
                'timestamp': time.time()
            }
            
            asyncio.run(auto_debug_system._analyze_error_patterns(error_context))
            logger.info("🤖 IA analizando error de automatización...")
            
        except Exception as debug_error:
            logger.error(f"❌ Error en debug: {debug_error}")

def run_dashboard():
    """Ejecuta el dashboard moderno en Streamlit."""
    try:
        logger.info("🌐 Iniciando dashboard moderno...")
        # Ejecutar dashboard en puerto 8501
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            "dashboard_modern.py",
            "--server.headless=true",  # <--- ESTA LÍNEA ES CLAVE
            "--server.port=8501",
            "--browser.gatherUsageStats=false"
        ])
    except Exception as e:
        logger.error(f"❌ Error en dashboard: {e}")

def run_qwen_api():
    """Ejecuta el servidor API de Qwen Chat."""
    try:
        # Comprobar si Flask está instalado e instalarlo si es necesario
        try:
            import flask
        except ImportError:
            logger.warning("⚠️ Módulo 'flask' no encontrado. Intentando instalar...")
            print("="*60)
            print("💬 INSTALANDO DEPENDENCIAS PARA EL CHAT DE QWEN (FLASK).")
            print("   Esto puede tardar un momento...")
            print("="*60)
            subprocess.run([sys.executable, "-m", "pip", "install", "flask"], check=True)
            logger.info("✅ 'flask' instalado correctamente.")
        logger.info("💬 Iniciando API de Qwen Chat...")
        # Ejecutar el servidor Flask en un proceso separado para no bloquear
        proc = subprocess.Popen([sys.executable, "dashboard/backend/api_qwen_chat.py"])
        # Esperar unos segundos para que el servidor inicie
        time.sleep(3)
        # Abrir la URL en el navegador
        # webbrowser.open_new_tab("http://localhost:5000")
        logger.info("🌐 Abriendo la página de estado de la API de Qwen en el navegador.")
        proc.wait() # Mantener el thread vivo mientras el proceso exista
    except Exception as e:
        logger.error(f"❌ Error en API de Qwen: {e}")

if __name__ == "__main__":
    logger.info("🚀 Iniciando sistema evolutivo completo...")
    
    # Thread 1: Bot principal de trading
    t1 = threading.Thread(target=run_main, daemon=True, name="TradingBot")
    
    # Thread 2: Sistema de automatización completa (incluye reportes + entrenamiento + Optuna)
    t2 = threading.Thread(target=run_automation, daemon=True, name="AutomatedTrainer")
    
    # Thread 3: Dashboard moderno
    t3 = threading.Thread(target=run_dashboard, daemon=True, name="Dashboard")

    # Thread 4: API de Qwen Chat
    t4 = threading.Thread(target=run_qwen_api, daemon=True, name="QwenAPI")

    logger.info("🤖 Iniciando threads del sistema...")
    t1.start()
    logger.info("✅ Thread 1: Trading Bot iniciado")
    
    t2.start()
    logger.info("✅ Thread 2: Sistema Automatizado iniciado (reportes + training + Optuna)")
    
    t3.start()
    logger.info("✅ Thread 3: Dashboard Moderno iniciado")
    
    t4.start()
    logger.info("✅ Thread 4: Qwen Chat API iniciado en http://localhost:5000")
    
    logger.info("🚀 SISTEMA EVOLUTIVO COMPLETO ACTIVO")
    logger.info("📊 Trading Bot + Reportes automáticos + Entrenamiento + Optuna + Dashboard")
    logger.info("🌐 Dashboard disponible en: http://localhost:8501")

    try:
        # Mantener el proceso principal vivo para que los threads sigan corriendo
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("🛑 Sistema completo detenido por el usuario.")
        print("🛑 Bot detenido por el usuario.")
