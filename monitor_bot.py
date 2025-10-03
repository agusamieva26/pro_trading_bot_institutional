#!/usr/bin/env python3
"""
Monitor de Logs del Bot de Trading
Monitorea en tiempo real todos los logs y actividad del bot
"""

import os
import sys
import time
import subprocess
from datetime import datetime
import json
import psutil
from pathlib import Path

class BotMonitor:
    def __init__(self):
        self.colors = {
            'INFO': '\033[32m',      # Verde
            'WARNING': '\033[33m',   # Amarillo
            'CRITICAL': '\033[31m',  # Rojo
            'ERROR': '\033[91m',     # Rojo brillante
            'DEBUG': '\033[36m',     # Cian
            'RESET': '\033[0m',      # Reset
            'BOLD': '\033[1m',       # Negrita
            'BLUE': '\033[34m'       # Azul
        }
        
    def clear_screen(self):
        """Limpiar pantalla"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
    def print_header(self):
        """Mostrar header del monitor"""
        print(f"{self.colors['BOLD']}{self.colors['BLUE']}")
        print("=" * 70)
        print("🚀 MONITOR DEL BOT DE TRADING INSTITUCIONAL")
        print("=" * 70)
        print(f"⏰ Iniciado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("📊 Dashboard: http://localhost:5000")
        print("🔄 Actualizando cada 2 segundos | Ctrl+C para salir")
        print("=" * 70)
        print(f"{self.colors['RESET']}")
        
    def get_system_info(self):
        """Obtener información del sistema"""
        try:
            # Verificar procesos del bot de forma multi-plataforma con psutil
            streamlit_running = False
            for proc in psutil.process_iter(['name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                    if 'streamlit' in cmdline and 'run' in cmdline:
                        streamlit_running = True
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Verificar archivos importantes
            files_status = {
                'trades_log.csv': os.path.exists('trades_log.csv'),
                'bot/state.json': os.path.exists('bot/state.json'),
                'models/rf_clf.pkl': os.path.exists('models/rf_clf.pkl')
            }
            
            return {
                'streamlit_running': streamlit_running,
                'files': files_status
            }
        except Exception as e:
            return {'error': str(e)}
            
    def get_recent_logs(self, lines=10):
        """Obtener logs recientes del bot"""
        logs = []
        
        # Buscar archivos de log
        log_files = []
        for pattern in ['*.log', 'logs/*.log', 'bot/*.log']:
            log_files.extend(Path('.').glob(pattern))
            
        # Si no hay archivos de log, simular con información del estado
        if not log_files:
            # Leer estado del bot si existe
            if os.path.exists('bot/state.json'):
                try:
                    with open('bot/state.json', 'r') as f:
                        state = json.load(f)
                    logs.append(f"📊 Estado del bot cargado: Equity ${state.get('equity', 0):,.2f}")
                except:
                    pass
                    
            # Verificar trades
            if os.path.exists('trades_log.csv'):
                try:
                    with open('trades_log.csv', 'r') as f:
                        lines_count = sum(1 for _ in f) - 1  # -1 para el header
                    logs.append(f"📋 Trades registrados: {lines_count}")
                except:
                    pass
        else:
            # Leer logs reales
            for log_file in log_files[-1:]:  # Solo el más reciente
                try:
                    with open(log_file, 'r') as f:
                        recent_lines = f.readlines()[-lines:]
                    logs.extend([line.strip() for line in recent_lines if line.strip()])
                except:
                    pass
                    
        return logs[-lines:] if logs else ["⚠️ No hay logs disponibles"]
        
    def colorize_log(self, log_line):
        """Colorear línea de log según su tipo"""
        line = log_line
        
        for level in ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG']:
            if level in line:
                line = line.replace(level, f"{self.colors[level]}{level}{self.colors['RESET']}")
                break
                
        # Colorear timestamps
        if '2025-' in line:
            parts = line.split(' ', 2)
            if len(parts) >= 2:
                timestamp = f"{parts[0]} {parts[1]}"
                rest = parts[2] if len(parts) > 2 else ""
                line = f"{self.colors['BLUE']}{timestamp}{self.colors['RESET']} {rest}"
                
        # Colorear emojis y símbolos importantes
        emoji_colors = {
            '🚀': self.colors['BOLD'],
            '✅': self.colors['INFO'],
            '⚠️': self.colors['WARNING'],
            '🛑': self.colors['CRITICAL'],
            '📊': self.colors['BLUE'],
            '💰': self.colors['INFO'],
            '📋': self.colors['BLUE']
        }
        
        for emoji, color in emoji_colors.items():
            if emoji in line:
                line = line.replace(emoji, f"{color}{emoji}{self.colors['RESET']}")
                
        return line
        
    def show_files_status(self, files_status):
        """Mostrar estado de archivos importantes"""
        print(f"\n{self.colors['BOLD']}📁 ARCHIVOS IMPORTANTES:{self.colors['RESET']}")
        for file, exists in files_status.items():
            status = f"{self.colors['INFO']}✅{self.colors['RESET']}" if exists else f"{self.colors['WARNING']}❌{self.colors['RESET']}"
            print(f"  {status} {file}")
            
    def show_quick_stats(self):
        """Mostrar estadísticas rápidas"""
        print(f"\n{self.colors['BOLD']}📊 ESTADÍSTICAS RÁPIDAS:{self.colors['RESET']}")
        
        # Leer equity si existe
        if os.path.exists('bot/state.json'):
            try:
                with open('bot/state.json', 'r') as f:
                    state = json.load(f)
                equity = state.get('equity', 0)
                print(f"  💰 Equity actual: ${equity:,.2f}")
            except:
                print("  💰 Equity: No disponible")
        else:
            print("  💰 Equity: No disponible")
            
        # Contar trades
        if os.path.exists('trades_log.csv'):
            try:
                with open('trades_log.csv', 'r') as f:
                    lines = sum(1 for _ in f) - 1
                print(f"  📋 Trades totales: {lines}")
            except:
                print("  📋 Trades: Error leyendo archivo")
        else:
            print("  📋 Trades: 0 (archivo no existe)")
            
    def run(self):
        """Ejecutar monitor principal"""
        try:
            while True:
                self.clear_screen()
                self.print_header()
                
                # Información del sistema
                sys_info = self.get_system_info()
                
                # Estado del dashboard
                dashboard_status = f"{self.colors['INFO']}✅ Funcionando{self.colors['RESET']}" if sys_info.get('streamlit_running') else f"{self.colors['WARNING']}❌ No detectado{self.colors['RESET']}"
                print(f"📊 Dashboard Streamlit: {dashboard_status}")
                
                # Estado de archivos
                if 'files' in sys_info:
                    self.show_files_status(sys_info['files'])
                    
                # Estadísticas rápidas
                self.show_quick_stats()
                
                # Logs recientes
                print(f"\n{self.colors['BOLD']}📝 LOGS RECIENTES:{self.colors['RESET']}")
                logs = self.get_recent_logs(8)
                
                for log in logs:
                    colored_log = self.colorize_log(log)
                    print(f"  {colored_log}")
                    
                print(f"\n{self.colors['BLUE']}⏰ Última actualización: {datetime.now().strftime('%H:%M:%S')}{self.colors['RESET']}")
                print("🔄 Presiona Ctrl+C para salir")
                
                time.sleep(2)
                
        except KeyboardInterrupt:
            print(f"\n\n{self.colors['INFO']}👋 Monitor detenido por el usuario{self.colors['RESET']}")
            print("¡Gracias por usar el monitor del bot!")
            
        except Exception as e:
            print(f"\n{self.colors['CRITICAL']}❌ Error en el monitor: {e}{self.colors['RESET']}")

def main():
    """Función principal"""
    monitor = BotMonitor()
    monitor.run()

if __name__ == "__main__":
    main()