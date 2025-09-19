#!/usr/bin/env python3
"""
🧠 QWEN 2.5 LIGHTWEIGHT INTEGRATION
Reemplazo directo de OpenAI/LocalAI con Qwen 2.5 optimizado para trading bot
Sin servidor pesado - integración directa
"""

import os
import asyncio
import time
from typing import Optional, Dict, Any, List
from loguru import logger
import torch
import gc
from threading import Lock
import json

# Lazy imports para optimización
transformers = None
_model = None
_tokenizer = None
_model_lock = Lock()
_model_loaded = False
_last_used = 0

def _lazy_import():
    """Importación lazy de transformers para optimizar arranque"""
    global transformers
    if transformers is None:
        try:
            import transformers as tf
            transformers = tf
            logger.info("🧠 Transformers imported successfully")
        except ImportError as e:
            logger.error(f"❌ Failed to import transformers: {e}")
            transformers = None
    return transformers is not None

def _load_qwen_model():
    """🔄 Carga el modelo Qwen 2.5 de forma lazy"""
    global _model, _tokenizer, _model_loaded, _last_used
    
    if _model_loaded and _model is not None:
        _last_used = time.time()
        return True
    
    with _model_lock:
        if _model_loaded and _model is not None:
            _last_used = time.time()
            return True
            
        try:
            if not _lazy_import():
                return False
            
            logger.info("🚀 Attempting to load AI model for decision analysis...")
            start_time = time.time()
            
            # REALIDAD: Usar modelo disponible basado en recursos del sistema
            # DialoGPT-small es confiable y funcional para análisis básico
            model_name = "microsoft/DialoGPT-small"  # Modelo estable y confiable (117MB)
            
            logger.warning("⚠️ NOTA: Qwen 2.5 no disponible - usando DialoGPT-small como backend AI")
            logger.info(f"🔧 Cargando modelo de respaldo: {model_name}")
            logger.info("📝 Para análisis avanzado, considere instalar Qwen 2.5 o usar API externa")
            
            # Configuración optimizada para CPU
            model_kwargs = {
                "torch_dtype": torch.float16,
                "device_map": "auto",
                "trust_remote_code": True,
                "low_cpu_mem_usage": True,
            }
            
            # Si no hay GPU, usar float32 y quantización
            if not torch.cuda.is_available():
                logger.info("💻 Using CPU - applying memory optimizations...")
                model_kwargs["torch_dtype"] = torch.float32
                model_kwargs["load_in_8bit"] = False  # Desactivar para evitar problemas
            
            _tokenizer = transformers.AutoTokenizer.from_pretrained(
                model_name,
                trust_remote_code=True,
                use_fast=True
            )
            
            _model = transformers.AutoModelForCausalLM.from_pretrained(
                model_name,
                **model_kwargs
            )
            
            # Configurar pad token
            if _tokenizer.pad_token is None:
                _tokenizer.pad_token = _tokenizer.eos_token
            
            load_time = time.time() - start_time
            _model_loaded = True
            _last_used = time.time()
            
            # Logging honesto sobre el modelo real cargado
            logger.info(f"✅ AI Model loaded successfully in {load_time:.2f}s")
            logger.warning(f"⚠️ MODELO ACTUAL: {model_name} (NO Qwen 2.5)")
            logger.info(f"🖥️ Device: {'GPU' if torch.cuda.is_available() else 'CPU'}")
            logger.warning("🚨 MOTOR DE DECISIONES: Usando modelo básico para análisis - capacidades limitadas")
            logger.info("💡 TIP: Para análisis avanzado, instalar Qwen 2.5 real o usar OpenAI API")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error loading Qwen model: {e}")
            _model_loaded = False
            return False

def _cleanup_model_if_idle():
    """🧹 Limpia el modelo si no se usa por un tiempo (ahorro de memoria)"""
    global _model, _tokenizer, _model_loaded, _last_used
    
    current_time = time.time()
    idle_time = current_time - _last_used
    
    # Limpiar después de 30 minutos de inactividad
    if idle_time > 1800 and _model_loaded:  # 30 minutos
        with _model_lock:
            if _model is not None:
                del _model
                _model = None
            if _tokenizer is not None:
                del _tokenizer
                _tokenizer = None
            _model_loaded = False
            gc.collect()
            logger.info("🧹 Qwen model cleaned from memory due to inactivity")

def qwen_generate_response(
    prompt: str,
    temperature: float = 0.3,
    max_tokens: int = 512,
    **kwargs
) -> str:
    """🧠 Genera respuesta usando AI backend disponible (NOT Qwen 2.5)"""
    
    # Limpiar modelo inactivo
    _cleanup_model_if_idle()
    
    # Cargar modelo si es necesario
    if not _load_qwen_model():
        logger.error("❌ No hay backend AI disponible - usando fallback básico")
        return _basic_analysis_fallback(prompt)
    
    # Log transparente sobre capacidades limitadas
    logger.debug("🔄 Generando análisis con DialoGPT-small (capacidades básicas)")
    
    try:
        # Formatear prompt para Qwen
        formatted_prompt = f"<|im_start|>system\nEres AGUS, un asistente de trading avanzado. Proporciona análisis precisos y accionables.<|im_end|>\n<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"
        
        # Tokenizar
        inputs = _tokenizer(
            formatted_prompt, 
            return_tensors="pt", 
            truncation=True, 
            max_length=2048
        )
        
        # Generar
        with torch.inference_mode():
            outputs = _model.generate(
                inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                max_new_tokens=min(max_tokens, 512),
                temperature=temperature,
                top_p=0.9,
                top_k=40,
                repetition_penalty=1.1,
                do_sample=True,
                pad_token_id=_tokenizer.eos_token_id
            )
        
        # Decodificar
        response = _tokenizer.decode(
            outputs[0][inputs["input_ids"].shape[1]:], 
            skip_special_tokens=True
        )
        
        _last_used = time.time()
        return response.strip()
        
    except Exception as e:
        logger.error(f"❌ Error generating Qwen response: {e}")
        return f"❌ Error en generación: {str(e)[:100]}..."

# Funciones de compatibilidad con OpenAI
async def qwen_chat_completion_async(
    messages: List[Dict[str, str]], 
    temperature: float = 0.3,
    max_tokens: int = 512,
    **kwargs
) -> str:
    """💬 Chat completion compatible con OpenAI (async)"""
    
    # Combinar mensajes
    prompt_parts = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            prompt_parts.append(f"Sistema: {content}")
        elif role == "user":
            prompt_parts.append(f"Usuario: {content}")
    
    prompt = "\n".join(prompt_parts)
    
    # Ejecutar en thread pool para no bloquear
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, 
        qwen_generate_response, 
        prompt, 
        temperature, 
        max_tokens
    )

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
    """✅ Verificar si Qwen está disponible"""
    return _lazy_import()

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
    return {
        "available": is_qwen_available(),
        "loaded": _model_loaded,
        "last_used": _last_used,
        "device": "GPU" if torch.cuda.is_available() else "CPU",
        "actual_model": "microsoft/DialoGPT-small" if _model_loaded else "none",
        "is_real_qwen": False,  # HONESTIDAD TOTAL
        "capabilities": "basic" if _model_loaded else "fallback_only",
        "warning": "NOT using Qwen 2.5 - limited AI capabilities"
    }

def force_cleanup_qwen():
    """🧹 Forzar limpieza del modelo"""
    global _model, _tokenizer, _model_loaded
    
    with _model_lock:
        if _model is not None:
            del _model
            _model = None
        if _tokenizer is not None:
            del _tokenizer
            _tokenizer = None
        _model_loaded = False
        gc.collect()
    
    logger.info("🧹 Qwen model force cleaned from memory")

# Test function
async def test_qwen_integration():
    """🧪 Test de la integración Qwen"""
    logger.info("🧪 Testing Qwen integration...")
    
    if not is_qwen_available():
        logger.error("❌ Qwen not available - transformers not installed")
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