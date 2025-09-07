#!/usr/bin/env python3
"""
Monitor Rápido - Versión Simple
Para ver logs del bot en tiempo real
"""

import time
import os
import subprocess
from datetime import datetime

def show_bot_status():
    """Mostrar estado del bot de forma simple"""
    print("🚀 MONITOR DEL BOT - VERSIÓN RÁPIDA")
    print("=" * 50)
    
    # Verificar procesos
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        if 'streamlit' in result.stdout:
            print("✅ Dashboard: Funcionando")
        else:
            print("❌ Dashboard: No detectado")
            
        if 'python' in result.stdout and 'bot.main' in result.stdout:
            print("✅ Bot: Ejecutándose")
        else:
            print("⚠️ Bot: No ejecutándose")
            
    except:
        print("❓ Estado: No se pudo verificar")
        
    # Verificar archivos
    files = ['trades_log.csv', 'bot/state.json']
    for file in files:
        if os.path.exists(file):
            print(f"✅ {file}: Existe")
        else:
            print(f"❌ {file}: No encontrado")
            
    print("=" * 50)
    print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
    print("Ctrl+C para salir\n")

def main():
    """Monitor simple que se actualiza cada 3 segundos"""
    try:
        while True:
            os.system('clear')
            show_bot_status()
            time.sleep(3)
    except KeyboardInterrupt:
        print("\n👋 Monitor detenido")

if __name__ == "__main__":
    main()