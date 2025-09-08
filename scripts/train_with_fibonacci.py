#!/usr/bin/env python3
"""
Script para entrenar el modelo con las nuevas features de Fibonacci.
Este script descarga datos recientes y entrena el modelo ML para incluir:
- Análisis tradicional (EMA, RSI, MACD, etc.)  
- Nuevos indicadores de Fibonacci (soporte, resistencia, tendencia)

Uso:
    python scripts/train_with_fibonacci.py

El modelo entrenado se guardará automáticamente y estará listo para usar.
"""

import sys
import os
sys.path.insert(0, '.')

from bot.trainer import train
from bot.config import settings
from bot.util import logger
from datetime import datetime, timedelta

def main():
    """Entrena el modelo con features de Fibonacci incluidas."""
    
    print("🚀 Iniciando entrenamiento con análisis de Fibonacci...")
    
    # Símbolos para entrenar (los mismos que usa el bot)
    symbols = [
        "BTC/USD", "ETH/USD", "SOL/USD", "AVAX/USD", 
        "LINK/USD", "DOGE/USD", "DOT/USD", "LTC/USD"
    ]
    
    # Fechas para entrenamiento: últimos 30 días
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    
    print(f"📅 Periodo de entrenamiento: {start_str} a {end_str}")
    print(f"📊 Símbolos: {', '.join(symbols)}")
    print(f"💾 Modelo se guardará en: {settings.model_path}")
    
    try:
        # Usar el trainer existente - automáticamente incluirá las nuevas features
        model = train(
            symbols=symbols,
            start=start_str,
            end=end_str,
            model_path=settings.model_path
        )
        
        if model is not None:
            print("✅ ¡Entrenamiento completado exitosamente!")
            print(f"🧠 Modelo entrenado con {len(model.feature_names_in_)} features:")
            for i, feature in enumerate(model.feature_names_in_, 1):
                emoji = "🔮" if feature.startswith("fib_") else "📈"
                print(f"   {i:2d}. {emoji} {feature}")
                
            print(f"\n🎯 El bot ahora puede usar:")
            print("   📊 Análisis técnico tradicional")
            print("   🔮 Niveles de Fibonacci avanzados") 
            print("   🤖 Machine Learning optimizado")
            print("\n🚀 ¡Listo para trading con Fibonacci!")
            
        else:
            print("❌ Error durante el entrenamiento. Revisa los logs.")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Error en el entrenamiento: {e}")
        print(f"❌ Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())