#!/usr/bin/env python3
"""
🚀 INICIAR Y MONITOREAR EL BOT DE TRADING
Script que inicia el bot y luego activa el monitoreo
"""

import os
# 🧠 Force TensorFlow to use CPU only to avoid CUDA errors in all environments
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

import subprocess
import time
import threading
import signal
import sys
from datetime import datetime
from loguru import logger
 
def stream_output(process):
    """Lee y muestra la salida de un proceso en tiempo real."""
    def read_stream(stream, is_stderr=False):
        for line in iter(stream.readline, ''):
            line_strip = line.strip()
            if not line_strip:
                continue
            
            log_message = f"[BOT] {line_strip}"
            
            # 🧠 ANÁLISIS INTELIGENTE DE LOGS: Clasificar por contenido, no por stream (stdout/stderr)
            log_level = None
            if "|" in line_strip:
                parts = line_strip.split('|')
                if len(parts) > 2:
                    level_part = parts[1].strip()
                    if level_part in ["INFO", "WARNING", "ERROR", "CRITICAL", "DEBUG", "SUCCESS"]:
                        log_level = level_part

            if log_level:
                if log_level == "CRITICAL":
                    logger.critical(log_message)
                elif log_level == "ERROR":
                    logger.error(log_message)
                elif log_level == "WARNING":
                    logger.warning(log_message)
                else: # INFO, DEBUG, SUCCESS
                    logger.info(log_message)
            elif is_stderr:
                # Fallback para mensajes en stderr que no son de loguru (ej. TensorFlow)
                if "tensorflow" in line_strip.lower() and ("cpu_feature_guard.cc" in line_strip or "AVX2 FMA" in line_strip):
                    logger.info(log_message) # Reclasificar como INFO
                elif "E external/local_xla" in line_strip or "failed call to cuInit" in line_strip:
                    logger.critical(log_message) # Errores CUDA son críticos
                else:
                    logger.error(log_message) # Default para otros mensajes de stderr
            else:
                logger.info(log_message)
        stream.close()
 
    stdout_thread = threading.Thread(target=read_stream, args=(process.stdout, False))
    stderr_thread = threading.Thread(target=read_stream, args=(process.stderr, True))
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
    print("💡 En otra terminal, ejecuta 'python monitor_bot.py' para ver los logs en tiempo real.")
    print("🌐 Dashboard disponible en: http://localhost:5000")
    print("=" * 50)
    
    try:
        # Mantener el proceso principal vivo
        while True:
            time.sleep(1)

            # Verificar si el bot sigue corriendo
            if bot_process.poll() is not None:
                logger.critical("🚨 ¡El proceso principal del bot se ha detenido inesperadamente!")
                logger.info("🔧 Intentando reiniciar el bot en 10 segundos...")
                time.sleep(10)
                
                # Intentar reiniciar el bot
                bot_process = start_bot()
                if not bot_process:
                    logger.error("❌ No se pudo reiniciar el bot. Saliendo.")
                    break

    except KeyboardInterrupt:
        logger.info("\n🛑 Deteniendo sistema... (Enviando señal de interrupción al bot)")
        bot_process.send_signal(signal.SIGINT)
        try:
            bot_process.wait(timeout=15) # Esperar 15 segundos para un cierre limpio
            logger.info("✅ Proceso del bot detenido limpiamente.")
        except subprocess.TimeoutExpired:
            logger.warning("⚠️ El bot no se detuvo a tiempo, forzando terminación.")
            bot_process.terminate()

if __name__ == "__main__":
    main()
