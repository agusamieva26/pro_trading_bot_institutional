#!/usr/bin/env python3
"""
🚀 INICIAR Y MONITOREAR EL BOT DE TRADING
Script que inicia el bot y luego activa el monitoreo
"""

import subprocess
import time
import threading
import signal
import sys
from datetime import datetime
from loguru import logger
 
def stream_output(process):
    """Lee y muestra la salida de un proceso en tiempo real."""
    def read_stream(stream, log_func):
        for line in iter(stream.readline, ''):
            log_func(f"[BOT] {line.strip()}")
        stream.close()
 
    stdout_thread = threading.Thread(target=read_stream, args=(process.stdout, logger.info))
    stderr_thread = threading.Thread(target=read_stream, args=(process.stderr, logger.error))
    stdout_thread.start()
    stderr_thread.start()
 
def start_bot():
    """Inicia el bot de trading"""
    try:
        logger.info("🚀 Iniciando bot de trading...")
        # Ejecutar el bot en segundo plano
        process = subprocess.Popen([sys.executable, "run.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
        stream_output(process) # Iniciar el streaming de logs
        
        logger.info(f"✅ Bot iniciado con PID: {process.pid}")
        return process
    except Exception as e:
        logger.error(f"❌ Error iniciando bot: {e}")
        return None

def start_monitor():
    """Inicia el monitor del sistema"""
    try:
        logger.info("📊 Iniciando monitor del sistema en 20 segundos (dando tiempo al bot para arrancar)...")
        # Esperar un tiempo prudencial para que todos los servicios del bot se inicien
        time.sleep(20)
        
        # Ejecutar el monitor
        subprocess.run([sys.executable, "monitor_system.py"])
    except Exception as e:
        logger.error(f"❌ Error iniciando monitor: {e}")

def main():
    """Función principal"""
    print("🚀 INICIANDO BOT DE TRADING CON MONITOREO")
    print("=" * 50)
    
    # Iniciar el bot
    bot_process = start_bot()
    if not bot_process:
        print("❌ No se pudo iniciar el bot")
        return
    
    print("✅ Bot iniciado correctamente")
    print("📊 Iniciando monitor en 5 segundos...")
    print("🌐 Dashboard estará disponible en: http://localhost:8501")
    print("=" * 50)
    
    # Iniciar el monitor en un thread separado
    monitor_thread = threading.Thread(target=start_monitor, daemon=True)
    monitor_thread.start()
    
    try:
        # Mantener el proceso principal vivo
        while True:
            time.sleep(1)
            
            # Verificar si el bot sigue corriendo
            if bot_process.poll() is not None:
                logger.warning("⚠️ El bot se detuvo inesperadamente")
                break

    except KeyboardInterrupt:
        print("\n🛑 Deteniendo sistema... (Enviando señal de interrupción al bot)")
        bot_process.send_signal(signal.SIGINT)
        try:
            bot_process.wait(timeout=15) # Esperar 15 segundos para un cierre limpio
            logger.info("✅ Proceso del bot detenido limpiamente.")
        except subprocess.TimeoutExpired:
            logger.warning("⚠️ El bot no se detuvo a tiempo, forzando terminación.")
            bot_process.terminate()

if __name__ == "__main__":
    main()
