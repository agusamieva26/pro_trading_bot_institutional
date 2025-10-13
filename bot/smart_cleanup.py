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
import json
from pathlib import Path

# Navegar a la raíz del proyecto para asegurar que las rutas relativas funcionen
PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(PROJECT_ROOT)

def get_best_models_from_summary() -> set:
    """Lee el summary y retorna un set con los nombres base de los mejores modelos."""
    models_path = PROJECT_ROOT / "models" / "trained_models"
    summary_file = models_path / "best_models_summary.json"
    best_model_files = set()

    if summary_file.exists():
        try:
            with open(summary_file, 'r') as f:
                summary = json.load(f)
            for model_info in summary.values():
                model_path = model_info.get('model_path')
                if model_path:
                    # Extraer el nombre base del archivo (sin extensión)
                    base_name = Path(model_path).stem
                    best_model_files.add(base_name)
            print(f"🔍 Modelos a conservar detectados: {len(best_model_files)}")
        except Exception as e:
            print(f"⚠️ Error leyendo best_models_summary.json: {e}")
    return best_model_files

def cleanup_old_models():
    """Elimina todos los modelos excepto el que está activo."""
    print("\n--- 2. Limpiando modelos de ML antiguos ---")
    models_to_keep = get_best_models_from_summary()
    models_dir = PROJECT_ROOT / "models" / "trained_models"

    if not models_dir.exists():
        print("🟡 Directorio de modelos no encontrado.")
        return
    
    for file_path in list(models_dir.iterdir()): # Usar list() para evitar problemas al eliminar
        if file_path.is_file() and file_path.stem not in models_to_keep and file_path.name != "best_models_summary.json":
            print(f"🗑️  Eliminando archivo de modelo obsoleto: {file_path.name}")
            os.remove(file_path)

def cleanup_folders():
    """Elimina el contenido de carpetas temporales."""
    print("\n--- Limpiando cachés, logs y reportes ---")
    folders_to_clean = [ # Rutas relativas a la raíz del proyecto
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
            os.makedirs(path, exist_ok=True) # Re-crear la carpeta vacía

def cleanup_pycache():
    """Elimina todos los directorios __pycache__ del proyecto."""
    print("\n--- 3. Limpiando caché de Python (__pycache__) ---")
    for path in PROJECT_ROOT.rglob('__pycache__'):
        if path.is_dir():
            print(f"🗑️  Eliminando {path}")
            shutil.rmtree(path)

def main():
    """Ejecuta el proceso de limpieza completo."""
    print("🧹 Iniciando limpieza inteligente del espacio de trabajo...")
    
    # 1. Limpieza de carpetas temporales
    cleanup_folders() # Esta función fue renombrada en el remoto, pero la lógica es la misma.
    
    # 2. Limpieza inteligente de modelos antiguos
    cleanup_old_models()

    # 3. Limpieza de __pycache__
    cleanup_pycache()
    
    print("\n✅ ¡Limpieza inteligente completada!")

if __name__ == "__main__":
    main()