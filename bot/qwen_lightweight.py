#!/usr/bin/env python3
"""
🧠 QWEN 2.5 LIGHTWEIGHT INTEGRATION
Reemplazo directo de OpenAI/LocalAI con Qwen 2.5 optimizado para trading bot
Usa API de proveedor en vez de modelo local.
"""

import os
import asyncio
import time
from typing import Optional, Dict, Any, List
from loguru import logger
import json
import httpx
import requests

# --- API CONFIGURATION ---
# Using an OpenAI-compatible endpoint for Qwen models (e.g., Together.ai)
QWEN_API_BASE_URL = os.environ.get("QWEN_API_BASE_URL", "https://api.together.xyz/v1")
QWEN_API_KEY = os.environ.get("QWEN_API_KEY")
QWEN_MODEL_NAME = os.environ.get("QWEN_MODEL_NAME", "Qwen/Qwen1.5-7B-Chat") # Model name for Together.ai


def qwen_generate_response(
    prompt: str,
    temperature: float = 0.3,
    max_tokens: int = 512,
    **kwargs
) -> str:
    """🧠 Genera respuesta usando Qwen API (sync wrapper)"""
    if not is_qwen_available():
        logger.warning("⚠️ QWEN_API_KEY no configurado, usando fallback.")
        return _basic_analysis_fallback(prompt)
    
    messages = [
        {"role": "system", "content": "Eres AGUS, un asistente de trading avanzado. Proporciona análisis precisos y accionables."},
        {"role": "user", "content": prompt}
    ]

    try:
        headers = {
            "Authorization": f"Bearer {QWEN_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": QWEN_MODEL_NAME,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        response = requests.post(
            f"{QWEN_API_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=45
        )
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()
        
    except Exception as e:
        logger.error(f"❌ Error generando respuesta con Qwen API: {e}")
        return f"❌ Error en generación: {str(e)[:100]}..."

# Funciones de compatibilidad con OpenAI
async def qwen_chat_completion_async(
    messages: List[Dict[str, str]], 
    temperature: float = 0.3,
    max_tokens: int = 512,
    **kwargs
) -> str:
    """💬 Chat completion via API (async)"""
    if not is_qwen_available():
        user_prompt = next((m['content'] for m in reversed(messages) if m['role'] == 'user'), "No prompt")
        return _basic_analysis_fallback(user_prompt)

    logger.debug(f"🔄 Generando análisis con Qwen API ({QWEN_MODEL_NAME})")

    headers = {
        "Authorization": f"Bearer {QWEN_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": QWEN_MODEL_NAME,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    async with httpx.AsyncClient(timeout=45.0) as client:
        try:
            response = await client.post(
                f"{QWEN_API_BASE_URL}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"❌ Error generando respuesta con Qwen API: {e}")
            return f"❌ Error en generación: {str(e)[:100]}..."

def qwen_chat_completion_sync(
    messages: List[Dict[str, str]], 
    temperature: float = 0.3,
    max_tokens: int = 512,
    **kwargs
) -> str:
    """💬 Chat completion compatible con OpenAI (sync)"""
    return asyncio.run(qwen_chat_completion_async(
        messages, temperature, max_tokens, **kwargs
    ))

# Análisis especializado de trading
async def qwen_analyze_trading_data(
    symbol: str,
    market_data: Dict[str, Any],
    question: str,
    **kwargs
) -> str:
    """📊 Análisis especializado de trading"""
    
    trading_prompt = f"""
Análisis de trading para {symbol}:

Datos de mercado:
{json.dumps(market_data, indent=2) if market_data else "No hay datos específicos"}

Pregunta específica: {question}

Proporciona un análisis técnico detallado, incluyendo:
1. Tendencia actual
2. Niveles de soporte/resistencia
3. Recomendación de entrada/salida
4. Gestión de riesgo

Responde en español, de forma clara y concisa.
"""
    
    return await qwen_chat_completion_async([
        {"role": "system", "content": "Eres AGUS, un experto en análisis de trading con conocimientos avanzados en análisis técnico y gestión de riesgos."},
        {"role": "user", "content": trading_prompt}
    ], temperature=0.2, **kwargs)

# Funciones de utilidad
def is_qwen_available() -> bool:
    """✅ Verificar si la API de Qwen está configurada"""
    if not QWEN_API_KEY:
        logger.debug("⚠️ QWEN_API_KEY no está configurado. La IA no funcionará.")
        return False
    return True

def _basic_analysis_fallback(prompt: str) -> str:
    """📝 Fallback de análisis básico cuando no hay modelo AI disponible"""
    try:
        # Análisis de keywords básico para trading
        prompt_lower = prompt.lower()
        
        if "drawdown" in prompt_lower and ("reduce" in prompt_lower or "emergency" in prompt_lower):
            return """🚨 ANÁLISIS BÁSICO: PROTECCIÓN DE DRAWDOWN RECOMENDADA
            
Recomendaciones conservadoras:
• Reducir riesgo por trade a 0.5-1%
• Aumentar cash buffer al 10-15%
• Considerar cierre parcial de posiciones
• Implementar stops más estrictos
• Pausar nuevas posiciones hasta estabilización

⚠️ ANÁLISIS LIMITADO: Sin modelo AI avanzado disponible"""

        elif "volatility" in prompt_lower and "high" in prompt_lower:
            return """🌪️ ANÁLISIS BÁSICO: ADAPTACIÓN A ALTA VOLATILIDAD
            
Ajustes recomendados:
• Reducir tamaño de posiciones 20-30%
• Ampliar stops para evitar whipsaws
• Aumentar umbral de confianza para señales
• Monitorear correlaciones más frecuentemente
• Preparar para movimientos bruscos

⚠️ ANÁLISIS LIMITADO: Sin modelo AI avanzado disponible"""

        elif "performance" in prompt_lower and ("poor" in prompt_lower or "bad" in prompt_lower):
            return """📉 ANÁLISIS BÁSICO: INTERVENCIÓN POR BAJO RENDIMIENTO
            
Acciones correctivas:
• Revisar parámetros de estrategia
• Reducir riesgo temporalmente
• Aumentar selectividad de trades
• Pausa operativa de 1-2 horas
• Análisis de causas fundamentales

⚠️ ANÁLISIS LIMITADO: Sin modelo AI avanzado disponible"""
        
        else:
            return f"""🤖 ANÁLISIS BÁSICO GENÉRICO
            
Se detectó solicitud de análisis pero sin modelo AI avanzado disponible.

Consulta: {prompt[:100]}{'...' if len(prompt) > 100 else ''}

Recomendaciones generales:
• Mantener gestión de riesgo conservadora
• Monitorear métricas clave regularmente
• Evitar decisiones impulsivas
• Consultar con sistemas de respaldo

⚠️ ANÁLISIS LIMITADO: Para análisis avanzado, instalar Qwen 2.5 o usar OpenAI API"""
            
    except Exception as e:
        logger.error(f"❌ Error en fallback básico: {e}")
        return f"❌ Error en análisis básico: {str(e)[:100]}"

def get_qwen_status() -> Dict[str, Any]:
    """📊 Obtener estado honesto del backend AI"""
    available = is_qwen_available()
    return {
        "available": available,
        "mode": "api",
        "provider_url": QWEN_API_BASE_URL,
        "model": QWEN_MODEL_NAME,
        "is_real_qwen": "qwen" in QWEN_MODEL_NAME.lower(),
        "capabilities": "advanced" if available else "fallback_only",
        "warning": "Using API-based AI. Ensure QWEN_API_KEY is set." if not available else "API connection configured."
    }

# Test function
async def test_qwen_integration():
    """🧪 Test de la integración Qwen"""
    logger.info("🧪 Testing Qwen integration...")
    
    if not is_qwen_available():
        logger.error("❌ Qwen API no disponible - QWEN_API_KEY no configurado")
        return False
    
    try:
        response = await qwen_chat_completion_async([
            {"role": "user", "content": "¿Cómo está el mercado de Bitcoin hoy?"}
        ])
        
        logger.info(f"✅ Qwen test response: {response[:100]}...")
        return True
        
    except Exception as e:
        logger.error(f"❌ Qwen test failed: {e}")
        return False

if __name__ == "__main__":
    # Test directo
    asyncio.run(test_qwen_integration())