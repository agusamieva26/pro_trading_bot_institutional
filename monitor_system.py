#!/usr/bin/env python3
"""
📊 MONITOR DEL SISTEMA DE TRADING
Monitoreo en tiempo real del bot de trading institucional
"""

import os
# 🧠 Force TensorFlow to use CPU only to avoid CUDA errors in all environments
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

import time
import psutil
import requests
import subprocess
import sys
import codecs
from datetime import datetime
from pathlib import Path
from loguru import logger
import json
import os

# 🚀 FIX: Forzar UTF-8 para evitar UnicodeEncodeError en Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

class TradingSystemMonitor:
    """Monitor completo del sistema de trading"""
    
    def __init__(self):
        self.dashboard_url = "http://localhost:5000"
        self.bot_processes = []
        self.start_time = datetime.now()
        
    def check_dashboard_status(self):
        """Verifica si el dashboard está corriendo"""
        try:
            response = requests.get(self.dashboard_url, timeout=5)
            if response.status_code == 200:
                return True, "✅ Dashboard activo"
            else:
                return False, f"❌ Dashboard respondió con código {response.status_code}"
        except requests.exceptions.RequestException:
            return False, "❌ Dashboard no disponible"
    
    def check_python_processes(self):
        """Verifica procesos de Python relacionados con el bot"""
        bot_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] and proc.info['name'].lower().startswith('python'):
                    cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                    if 'run.py' in cmdline or 'dashboard' in cmdline or 'bot' in cmdline:
                        bot_processes.append({
                            'pid': proc.info['pid'],
                            'cmdline': cmdline[:100] + '...' if len(cmdline) > 100 else cmdline
                        })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return bot_processes
    
    def check_port_usage(self):
        """Verifica qué puertos están en uso"""
        ports_to_check = {
            5000: "Dashboard",
            8080: "Health Check"
        }
        ports = {}
        try:
            for conn in psutil.net_connections():
                if conn.status == 'LISTEN' and conn.pid:
                    port = conn.laddr.port
                    if port in ports_to_check:
                        try:
                            proc = psutil.Process(conn.pid)
                            ports[port] = {'pid': conn.pid, 'name': proc.name()}
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            ports[port] = {'pid': conn.pid, 'name': 'N/A'}
        except Exception as e:
            logger.debug(f"Error revisando puertos: {e}")
        return ports
    
    def check_system_resources(self):
        """Verifica recursos del sistema"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            'cpu': cpu_percent,
            'memory_percent': memory.percent,
            'memory_available': memory.available // (1024**3),  # GB
            'disk_percent': disk.percent,
            'disk_free': disk.free // (1024**3)  # GB
        }
    
    def check_log_files(self):
        """Verifica archivos de log recientes"""
        log_files = []
        log_dir = Path("/tmp/logs")
        
        if log_dir.exists():
            for file_path in log_dir.glob("*.log"):
                try:
                    stat = file_path.stat()
                    mod_time = datetime.fromtimestamp(stat.st_mtime)
                    if (datetime.now() - mod_time).seconds < 300:  # Últimos 5 minutos
                        log_files.append({
                            'file': file_path.name,
                            'modified': mod_time.strftime('%H:%M:%S'),
                            'size': stat.st_size
                        })
                except Exception:
                    continue
        return log_files
    
    def display_status(self):
        """Muestra el estado completo del sistema"""
        print("\n" + "="*60)
        print(f"📊 MONITOR DEL SISTEMA DE TRADING - {datetime.now().strftime('%H:%M:%S')}")
        print("="*60)
        
        # Dashboard Status
        dashboard_active, dashboard_msg = self.check_dashboard_status()
        print(f"\n🌐 DASHBOARD:")
        print(f"   {dashboard_msg}")
        if dashboard_active:
            print(f"   🔗 URL: {self.dashboard_url}")
        
        # Procesos Python
        print(f"\n🐍 PROCESOS PYTHON:")
        processes = self.check_python_processes()
        if processes:
            for proc in processes:
                print(f"   ✅ PID {proc['pid']}: {proc['cmdline']}")
        else:
            print("   ❌ No se encontraron procesos del bot")
        
        # Puertos
        print(f"\n🔌 PUERTOS ACTIVOS:")
        ports = self.check_port_usage()
        if ports:
            for port, info in ports.items():
                print(f"   ✅ Puerto {port}: {info.get('name', 'N/A')} (PID {info.get('pid', 'N/A')})")
        else:
            print("   ❌ No hay puertos activos del bot")
        
        # Recursos del sistema
        print(f"\n💻 RECURSOS DEL SISTEMA:")
        resources = self.check_system_resources()
        print(f"   🖥️  CPU: {resources['cpu']:.1f}%")
        print(f"   🧠 RAM: {resources['memory_percent']:.1f}% ({resources['memory_available']:.1f}GB libres)")
        print(f"   💾 Disco: {resources['disk_percent']:.1f}% ({resources['disk_free']:.1f}GB libres)")
        
        # Archivos de log
        print(f"\n📝 ARCHIVOS DE LOG RECIENTES:")
        logs = self.check_log_files()
        if logs:
            for log in logs:
                print(f"   📄 {log['file']}: {log['modified']} ({log['size']} bytes)")
        else:
            print("   ❌ No hay archivos de log recientes")
        
        # Tiempo de ejecución
        uptime = datetime.now() - self.start_time
        print(f"\n⏱️  TIEMPO DE MONITOREO: {uptime}")
        
        print("\n" + "="*60)
    
    def run_monitor(self, interval=10):
        """Ejecuta el monitor con intervalo específico"""
        logger.info("📊 Iniciando monitor del sistema de trading...")
        
        try:
            while True:
                self.display_status()
                print(f"\n⏳ Próxima actualización en {interval} segundos...")
                print("   Presiona Ctrl+C para detener")
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n🛑 Monitor detenido por el usuario")
            logger.info("Monitor detenido")

def main():
    """Función principal"""
    print("🚀 MONITOR DEL SISTEMA DE TRADING INSTITUCIONAL")
    print("=" * 50)
    
    monitor = TradingSystemMonitor()
    
    # Verificar si el bot está corriendo
    processes = monitor.check_python_processes()
    dashboard_active, _ = monitor.check_dashboard_status()
    
    if not processes and not dashboard_active:
        print("⚠️  No se detectó el bot ejecutándose")
        print("💡 Para iniciar el bot: python run.py")
        print("💡 Luego ejecuta este monitor")
        return
    
    print("✅ Sistema detectado, iniciando monitoreo...")
    monitor.run_monitor(interval=15)  # Actualizar cada 15 segundos

if __name__ == "__main__":
    main()
