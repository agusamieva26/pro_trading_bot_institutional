"""
🤖 IA LOCAL GRATUITA - ALTERNATIVA A OPENAI
Usa modelos locales gratuitos para análisis de trading y noticias
Compatible 100% con tu bot existente
"""
import json
import os
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from loguru import logger
import asyncio
from dataclasses import dataclass

@dataclass
class LocalMarketSignal:
    """Señal generada por IA local gratuita"""
    symbol: str
    action: str  # BUY, SELL, HOLD
    confidence: float  # 0.0 - 1.0
    reasoning: str
    news_sentiment: float  # -1.0 to 1.0
    timestamp: datetime

class LocalAITradingAssistant:
    """
    🆓 IA Trading Completamente GRATUITA
    - Sin API keys necesarias
    - Modelos locales potentes
    - Compatible con OpenAI API
    - 100% privado y local
    """
    
    def __init__(self):
        self.local_api_url = "http://localhost:8080/v1"  # LocalAI endpoint
        self.model_name = "microsoft/DialoGPT-large"  # Modelo por defecto
        self.available = self._check_availability()
        
        if self.available:
            logger.info("🤖 IA Local GRATUITA activada - ¡Sin límites ni costos!")
        else:
            logger.info("💤 IA Local no iniciada - usando análisis básico")
    
    def _check_availability(self) -> bool:
        """Verifica si LocalAI está corriendo"""
        try:
            response = requests.get(f"{self.local_api_url}/models", timeout=3)
            return response.status_code == 200
        except:
            return False
    
    def _local_ai_request(self, prompt: str, system_prompt: str = "") -> str:
        """Hace request a LocalAI (compatible con OpenAI API)"""
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            payload = {
                "model": self.model_name,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 300
            }
            
            response = requests.post(
                f"{self.local_api_url}/chat/completions",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                return f"Error: {response.status_code}"
                
        except Exception as e:
            return f"Error local AI: {e}"
    
    async def analyze_trading_sentiment(self, symbol: str, market_data: str) -> Dict:
        """
        📊 Analiza sentiment para trading usando IA local
        """
        if not self.available:
            return {"sentiment": 0.0, "confidence": 0.0, "reasoning": "IA local no disponible"}
        
        system_prompt = """Eres un experto analista financiero. Analiza el sentiment del mercado para trading.
        Responde SOLO con un JSON válido: {"sentiment": float(-1.0 a 1.0), "confidence": float(0.0 a 1.0), "reasoning": "explicación breve"}"""
        
        prompt = f"""Analiza el sentiment de trading para {symbol}:

Datos del mercado: {market_data}

Considera:
1. Tendencias de precio
2. Volatilidad
3. Momentum
4. Indicadores técnicos

Responde con JSON válido."""
        
        try:
            response = self._local_ai_request(prompt, system_prompt)
            
            # Intentar parsear JSON
            try:
                result = json.loads(response)
                return result
            except:
                # Si no es JSON válido, extraer información
                if "positiv" in response.lower() or "bull" in response.lower():
                    sentiment = 0.3
                elif "negativ" in response.lower() or "bear" in response.lower():
                    sentiment = -0.3
                else:
                    sentiment = 0.0
                
                return {
                    "sentiment": sentiment,
                    "confidence": 0.6,
                    "reasoning": response[:100] + "..."
                }
                
        except Exception as e:
            logger.debug(f"Error análisis sentiment local: {e}")
            return {"sentiment": 0.0, "confidence": 0.0, "reasoning": "Error en análisis"}
    
    async def generate_trading_signal(self, symbol: str, price: float, technical_data: Dict) -> Optional[LocalMarketSignal]:
        """
        🎯 Genera señal de trading usando IA local
        """
        if not self.available:
            return None
            
        system_prompt = """Eres un trader experto. Genera una señal de trading clara.
        Responde SOLO con JSON: {"action": "BUY/SELL/HOLD", "confidence": float(0.0-1.0), "reasoning": "explicación clara"}"""
        
        prompt = f"""Genera señal de trading para {symbol} @ ${price}:

Datos técnicos: {json.dumps(technical_data, indent=2)}

Considera:
1. RSI, MACD, EMA
2. Soporte/resistencia
3. Volumen y momentum
4. Risk/reward

Responde con JSON válido."""
        
        try:
            response = self._local_ai_request(prompt, system_prompt)
            
            # Intentar parsear respuesta
            try:
                ai_signal = json.loads(response)
            except:
                # Fallback parsing
                response_lower = response.lower()
                if "buy" in response_lower:
                    action = "BUY"
                    confidence = 0.6
                elif "sell" in response_lower:
                    action = "SELL" 
                    confidence = 0.6
                else:
                    action = "HOLD"
                    confidence = 0.4
                
                ai_signal = {
                    "action": action,
                    "confidence": confidence,
                    "reasoning": response[:150]
                }
            
            # Crear señal
            signal = LocalMarketSignal(
                symbol=symbol,
                action=ai_signal.get("action", "HOLD"),
                confidence=min(1.0, max(0.0, ai_signal.get("confidence", 0.5))),
                reasoning=ai_signal.get("reasoning", "Análisis IA local"),
                news_sentiment=0.0,  # Por ahora neutral
                timestamp=datetime.now()
            )
            
            return signal
            
        except Exception as e:
            logger.debug(f"Error generando señal local: {e}")
            return None
    
    def analyze_market_summary(self, symbols_data: Dict) -> str:
        """
        📋 Genera resumen del mercado usando IA local
        """
        if not self.available:
            return "🤖 IA local no disponible - usando análisis básico"
        
        system_prompt = "Eres un analista de mercados. Crea un resumen profesional y conciso del estado del mercado."
        
        # Preparar datos para análisis
        market_overview = []
        for symbol, data in list(symbols_data.items())[:5]:  # Solo top 5 para no sobrecargar
            market_overview.append(f"{symbol}: ${data.get('price', 0):.2f}")
        
        prompt = f"""Analiza este resumen de mercado:

{chr(10).join(market_overview)}

Genera un resumen profesional de máximo 200 palabras sobre:
1. Tendencia general del mercado
2. Oportunidades destacadas  
3. Riesgos a considerar
4. Recomendación general

Mantén un tono profesional y directo."""
        
        try:
            response = self._local_ai_request(prompt, system_prompt)
            return f"🤖 ANÁLISIS IA LOCAL:\n\n{response}"
            
        except Exception as e:
            return f"🤖 IA local: Error generando análisis - {e}"
    
    async def setup_local_ai(self) -> bool:
        """
        🚀 Instrucciones para instalar LocalAI
        """
        setup_commands = '''
🤖 INSTALACIÓN IA LOCAL GRATUITA:

1. Si tienes Docker:
   docker run -p 8080:8080 localai/localai:latest-cpu

2. Sin Docker (Alternativa Ollama):
   curl -fsSL https://ollama.com/install.sh | sh
   ollama run microsoft/DialoGPT-large
   
3. Verificación:
   Visita: http://localhost:8080/v1/models
   
4. Activación automática:
   El bot detectará y usará la IA local automáticamente
   
💡 VENTAJAS:
✅ 100% Gratuito forever
✅ Completamente privado
✅ Sin límites de uso
✅ Compatible con OpenAI API
✅ Miles de modelos disponibles
        '''
        
        logger.info(setup_commands)
        return True

# Instancia global de IA local gratuita
local_ai_assistant = LocalAITradingAssistant()

# Funciones de integración para el bot principal
async def get_local_ai_analysis(symbols: List[str], market_data: Dict = None) -> Dict:
    """
    🤖 Función principal para análisis con IA local
    """
    if not local_ai_assistant.available:
        return {
            "ai_available": False,
            "message": "IA local no iniciada",
            "setup_required": True
        }
    
    analysis = {}
    
    # Generar señales para símbolos
    signals = []
    for symbol in symbols[:3]:  # Limitar para velocidad
        data = market_data.get(symbol, {}) if market_data else {}
        price = data.get('price', 0)
        
        if price > 0:
            signal = await local_ai_assistant.generate_trading_signal(symbol, price, data)
            if signal:
                signals.append(signal)
    
    # Resumen del mercado
    summary = local_ai_assistant.analyze_market_summary(market_data or {})
    
    analysis = {
        "ai_available": True,
        "signals": signals,
        "market_summary": summary,
        "timestamp": datetime.now()
    }
    
    logger.info(f"🤖 IA Local: {len(signals)} señales generadas")
    return analysis

def get_local_ai_signal_score(symbol: str) -> float:
    """🎯 Score de la IA local para un símbolo"""
    # Por ahora retorna neutral - se implementará con el análisis completo
    return 0.5

if __name__ == "__main__":
    # Test de IA local
    async def test_local_ai():
        logger.info("🧪 Testing Local AI Assistant...")
        
        test_data = {
            "BTC/USD": {"price": 58000, "rsi": 45, "volume": "high"},
            "ETH/USD": {"price": 3200, "rsi": 62, "volume": "medium"}
        }
        
        analysis = await get_local_ai_analysis(["BTC/USD", "ETH/USD"], test_data)
        print(json.dumps(analysis, indent=2, default=str))
    
    asyncio.run(test_local_ai())