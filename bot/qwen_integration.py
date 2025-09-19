#!/usr/bin/env python3
"""
🧠 QWEN 2.5 INTEGRATION - Reemplazo completo de OpenAI y LocalAI
Integración optimizada para el sistema de trading AGUS
"""

import os
import asyncio
import aiohttp
import json
import time
from typing import Optional, Dict, Any, List
from loguru import logger
import requests
from datetime import datetime
import concurrent.futures

class QwenClient:
    """🚀 Cliente Qwen 2.5 - Reemplaza OpenAI y LocalAI"""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url.rstrip('/')
        self.timeout = 30.0
        self.max_retries = 3
        self.session = None
        
    async def ensure_session(self):
        """📡 Asegurar sesión HTTP activa"""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def close_session(self):
        """🔄 Cerrar sesión HTTP"""
        if self.session:
            await self.session.close()
            self.session = None
    
    def is_healthy(self) -> bool:
        """🩺 Verificar salud del servidor Qwen"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5.0)
            return response.status_code == 200 and response.json().get("status") == "healthy"
        except Exception as e:
            logger.warning(f"❌ Qwen health check failed: {e}")
            return False
    
    async def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.3,
        max_tokens: int = 1024,
        **kwargs
    ) -> str:
        """💬 Chat completion compatible con OpenAI"""
        await self.ensure_session()
        
        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }
        
        for attempt in range(self.max_retries):
            try:
                async with self.session.post(
                    f"{self.base_url}/v1/chat/completions",
                    json=payload
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result["choices"][0]["message"]["content"]
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Qwen API error {response.status}: {error_text}")
                        
            except Exception as e:
                logger.error(f"❌ Qwen request attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1 * (attempt + 1))  # Backoff exponencial
        
        return "❌ Error comunicándose con Qwen después de varios intentos"
    
    async def generate_text(self, prompt: str, **kwargs) -> str:
        """✨ Generación directa de texto"""
        await self.ensure_session()
        
        payload = {
            "prompt": prompt,
            **kwargs
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/generate",
                json=payload
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["response"]
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Qwen generate error {response.status}: {error_text}")
                    return f"❌ Error: {error_text[:100]}..."
        except Exception as e:
            logger.error(f"❌ Qwen generate request failed: {e}")
            return f"❌ Error de conexión: {str(e)[:100]}..."
    
    async def trading_analysis(
        self,
        symbol: str,
        market_data: Dict[str, Any],
        question: str,
        **kwargs
    ) -> str:
        """📊 Análisis especializado de trading"""
        await self.ensure_session()
        
        payload = {
            "symbol": symbol,
            "market_data": market_data,
            "question": question,
            **kwargs
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/trading/analyze",
                json=payload
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["analysis"]
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Qwen trading error {response.status}: {error_text}")
                    return f"❌ Error en análisis: {error_text[:100]}..."
        except Exception as e:
            logger.error(f"❌ Qwen trading request failed: {e}")
            return f"❌ Error de análisis: {str(e)[:100]}..."

# Instancia global para reemplazar OpenAI
qwen_client = QwenClient()

# Funciones de compatibilidad para reemplazar OpenAI
async def openai_chat_completion(messages, temperature=0.3, max_tokens=1024, **kwargs):
    """🔄 Reemplazo de OpenAI chat completion"""
    return await qwen_client.chat_completion(
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs
    )

def openai_completion_sync(prompt, temperature=0.3, max_tokens=1024, **kwargs):
    """🔄 Reemplazo síncrono de OpenAI completion"""
    return asyncio.run(qwen_client.generate_text(
        prompt=prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs
    ))

# Funciones para el sistema AGUS
async def qwen_analyze_trading_query(query: str, symbol: str = "", context: Dict = None) -> str:
    """🧠 Análisis de query de trading con Qwen"""
    try:
        market_data = context or {}
        
        if symbol:
            return await qwen_client.trading_analysis(
                symbol=symbol,
                market_data=market_data,
                question=query
            )
        else:
            # Query general
            messages = [
                {"role": "system", "content": "Eres AGUS, un asistente de trading experto. Proporciona análisis precisos y accionables."},
                {"role": "user", "content": query}
            ]
            return await qwen_client.chat_completion(messages)
            
    except Exception as e:
        logger.error(f"❌ Error en Qwen trading query: {e}")
        return f"❌ Error procesando consulta: {str(e)[:100]}..."

async def qwen_financial_analysis(data: Dict[str, Any], query: str) -> str:
    """💹 Análisis financiero con Qwen"""
    try:
        prompt = f"""
Análisis financiero requerido:
{query}

Datos disponibles:
{json.dumps(data, indent=2)}

Proporciona un análisis detallado, técnico y accionable.
"""
        return await qwen_client.generate_text(prompt, temperature=0.2)
        
    except Exception as e:
        logger.error(f"❌ Error en análisis financiero Qwen: {e}")
        return f"❌ Error en análisis: {str(e)[:100]}..."

# Función de inicialización
async def initialize_qwen():
    """🚀 Inicializar integración Qwen"""
    logger.info("🧠 Inicializando integración Qwen 2.5...")
    
    # Verificar que el servidor esté funcionando
    max_wait = 60  # 60 segundos máximo
    wait_time = 0
    
    while wait_time < max_wait:
        if qwen_client.is_healthy():
            logger.info("✅ Qwen 2.5 Server conectado y saludable")
            return True
            
        logger.info(f"⏳ Esperando servidor Qwen... ({wait_time}s/{max_wait}s)")
        await asyncio.sleep(5)
        wait_time += 5
    
    logger.error("❌ No se pudo conectar al servidor Qwen después de 60s")
    return False

# Cleanup
async def cleanup_qwen():
    """🧹 Limpiar recursos Qwen"""
    await qwen_client.close_session()
    logger.info("🔄 Qwen client session cerrada")

# Compatibilidad con sistema existente
class QwenAGUSIntegration:
    """🎯 Integración AGUS con Qwen 2.5"""
    
    def __init__(self):
        self.client = qwen_client
        self.integration_active = True
    
    async def process_agus_enhanced_query(self, query: str, user_id: str = "default") -> str:
        """🧠 Procesar query AGUS con Qwen"""
        return await qwen_analyze_trading_query(query)
    
    async def analyze_market_data(self, symbol: str, data: Dict) -> str:
        """📊 Análizar datos de mercado"""
        return await self.client.trading_analysis(
            symbol=symbol,
            market_data=data,
            question="Proporciona un análisis técnico completo de este símbolo"
        )
    
    def is_available(self) -> bool:
        """✅ Verificar disponibilidad"""
        return self.client.is_healthy()

# Instancia para AGUS
qwen_agus_integration = QwenAGUSIntegration()

if __name__ == "__main__":
    # Test de la integración
    async def test_qwen():
        if await initialize_qwen():
            response = await qwen_analyze_trading_query("¿Cómo está el mercado de Bitcoin?")
            print(f"Respuesta: {response}")
        await cleanup_qwen()
    
    asyncio.run(test_qwen())