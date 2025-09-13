#!/usr/bin/env python3
"""
🤖 INSTALADOR DE IA LOCAL GRATUITA
Instala y configura LocalAI o Ollama para tu bot de trading
100% Gratis, Sin API Keys, Sin Límites
"""
import os
import subprocess
import sys
import requests
import time
from loguru import logger

def check_docker():
    """Verifica si Docker está disponible"""
    try:
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def install_with_docker():
    """Instala LocalAI usando Docker"""
    logger.info("🐳 Instalando LocalAI con Docker...")
    
    try:
        # Descargar e iniciar LocalAI
        cmd = [
            'docker', 'run', '-d', 
            '--name', 'localai-trading',
            '-p', '8080:8080',
            'localai/localai:latest-cpu'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("✅ LocalAI iniciado en Docker!")
            logger.info("🌐 Disponible en: http://localhost:8080")
            return True
        else:
            logger.error(f"❌ Error Docker: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error instalando LocalAI: {e}")
        return False

def install_with_ollama():
    """Instala Ollama como alternativa"""
    logger.info("🦙 Instalando Ollama (alternativa sin Docker)...")
    
    try:
        # Descargar script de instalación
        if os.name != 'nt':  # Unix/Linux
            cmd = ['curl', '-fsSL', 'https://ollama.com/install.sh']
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Ejecutar instalación
                install_script = result.stdout
                subprocess.run(['sh', '-c', install_script], check=True)
                
                # Descargar modelo básico
                logger.info("📥 Descargando modelo base...")
                subprocess.run(['ollama', 'pull', 'llama2:7b'], check=True)
                
                logger.info("✅ Ollama instalado correctamente!")
                return True
            else:
                return False
        else:
            logger.info("💻 Windows detectado - visita: https://ollama.com/download")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error instalando Ollama: {e}")
        return False

def test_local_ai():
    """Prueba la conexión con IA local"""
    logger.info("🧪 Probando conexión con IA local...")
    
    # Probar LocalAI
    try:
        response = requests.get("http://localhost:8080/v1/models", timeout=5)
        if response.status_code == 200:
            logger.info("✅ LocalAI funcionando correctamente!")
            models = response.json()
            logger.info(f"📊 Modelos disponibles: {len(models.get('data', []))}")
            return True
    except:
        logger.debug("LocalAI no disponible en puerto 8080")
    
    # Probar Ollama  
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            logger.info("✅ Ollama funcionando correctamente!")
            models = response.json()
            logger.info(f"📊 Modelos Ollama: {len(models.get('models', []))}")
            return True
    except:
        logger.debug("Ollama no disponible en puerto 11434")
    
    logger.warning("⚠️ No se detectó IA local funcionando")
    return False

def setup_huggingface_fallback():
    """Configura Hugging Face como fallback gratuito"""
    logger.info("🤗 Configurando Hugging Face como respaldo gratuito...")
    
    try:
        # Instalar transformers si no está
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'transformers', 'torch'], check=True)
        
        # Test básico
        from transformers import pipeline
        generator = pipeline('text-generation', model='gpt2', max_length=50)
        result = generator("The stock market today", max_length=30, num_return_sequences=1)
        
        logger.info("✅ Hugging Face configurado como respaldo")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error configurando Hugging Face: {e}")
        return False

def main():
    """Instalación principal"""
    logger.info("🚀 INSTALADOR DE IA LOCAL GRATUITA")
    logger.info("=" * 50)
    
    # Opción 1: Docker + LocalAI
    if check_docker():
        logger.info("🐳 Docker detectado - instalando LocalAI...")
        if install_with_docker():
            time.sleep(10)  # Esperar a que inicie
            if test_local_ai():
                logger.info("🎉 ¡LocalAI instalado correctamente!")
                return True
    
    # Opción 2: Ollama
    logger.info("🦙 Intentando instalación con Ollama...")
    if install_with_ollama():
        if test_local_ai():
            logger.info("🎉 ¡Ollama instalado correctamente!")
            return True
    
    # Opción 3: Hugging Face local
    logger.info("🤗 Configurando Hugging Face como respaldo...")
    if setup_huggingface_fallback():
        logger.info("✅ Hugging Face configurado")
        return True
    
    # Instrucciones manuales
    logger.info("""
    📋 INSTALACIÓN MANUAL:
    
    Opción A - LocalAI (Recomendado):
    1. Instala Docker: https://docs.docker.com/get-docker/
    2. Ejecuta: docker run -p 8080:8080 localai/localai:latest-cpu
    
    Opción B - Ollama:
    1. Visita: https://ollama.com/download
    2. Instala para tu sistema
    3. Ejecuta: ollama pull llama2:7b
    
    Opción C - Hugging Face:
    1. pip install transformers torch
    2. Usa modelos gratuitos directamente
    
    ¡Tu bot funcionará automáticamente una vez instalado!
    """)
    
    return False

if __name__ == "__main__":
    success = main()
    if success:
        logger.info("🎯 ¡IA Local lista para trading!")
    else:
        logger.info("📖 Sigue las instrucciones manuales arriba")