#!/usr/bin/env python
"""
🧹 SCRIPT DE LIMPIEZA INTELIGENTE

Este script realiza una limpieza segura y selectiva del espacio de trabajo:
- Elimina cachés, logs y reportes antiguos.
- **Inteligentemente** detecta el modelo de ML actualmente en uso.
- Elimina **únicamente** los modelos de ML antiguos y no utilizados, conservando el activo.

Es la forma recomendada y segura de mantener el sistema limpio.
"""
import os
import glob
import shutil
from pathlib import Path

# Navegar a la raíz del proyecto para asegurar que las rutas relativas funcionen
PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(PROJECT_ROOT)

def get_active_model() -> str | None:
    """
    Detecta el nombre del archivo del modelo de ML activo.
    Por ahora, asumimos que es el más reciente. En un futuro, podría leer un archivo de estado.
    """
    models_path = PROJECT_ROOT / "models" / "trained_models"
    if not models_path.exists():
        return None

    # Encuentra todos los modelos y los ordena por fecha de modificación (el más nuevo primero)
    models = sorted(models_path.glob('*.pkl'), key=os.path.getmtime, reverse=True)
    
    if models:
        print(f"🔍 Modelo activo detectado (el más reciente): {models[0].name}")
        return models[0].name
    return None

def cleanup_old_models():
    """Elimina todos los modelos excepto el que está activo."""
    print("\n--- Limpiando modelos antiguos ---")
    active_model = get_active_model()
    if not active_model:
        print("🟡 No se encontraron modelos para limpiar.")
        return

    models_dir = PROJECT_ROOT / "models" / "trained_models"
    for model_file in models_dir.glob('*.pkl'):
        if model_file.name != active_model:
            print(f"🗑️  Eliminando modelo antiguo: {model_file.name}")
            os.remove(model_file)

def cleanup_folders():
    """Elimina el contenido de carpetas temporales."""
    print("\n--- Limpiando cachés, logs y reportes ---")
    folders_to_clean = [
        "data_cache",
        "backtest_cache",
        "logs",
        "reports",
        "bot/backups"
    ]
    for folder in folders_to_clean:
        path = PROJECT_ROOT / folder
        if path.exists():
            print(f"🗑️  Vaciando carpeta: {folder}")
            shutil.rmtree(path)
            os.makedirs(path, exist_ok=True) # Volver a crear la carpeta vacía

def main():
    """Ejecuta el proceso de limpieza completo."""
    print("🧹 Iniciando limpieza inteligente del espacio de trabajo...")
    
    # 1. Limpieza de carpetas temporales
    cleanup_folders()
    
    # 2. Limpieza inteligente de modelos antiguos
    cleanup_old_models()
    
    print("\n✅ ¡Limpieza inteligente completada!")

if __name__ == "__main__":
    main()