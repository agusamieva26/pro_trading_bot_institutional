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
        # Modelos más específicos para trading financiero
        self.model_name = "microsoft/DialoGPT-large"  # Modelo por defecto
        self.financial_models = [
            "microsoft/DialoGPT-large",
            "gpt2",
            "distilgpt2",
            "microsoft/DialoGPT-medium"
        ]
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
            
            # Configuración optimizada para análisis financiero
            payload = {
                "model": self.model_name,
                "messages": messages,
                "temperature": 0.3,  # Más determinístico para análisis técnico
                "max_tokens": 200,   # Respuestas más concisas
                "top_p": 0.9,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0
            }
            
            response = requests.post(
                f"{self.local_api_url}/chat/completions",
                json=payload,
                timeout=15  # Timeout más corto
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                # Limpiar respuesta de caracteres extraños
                content = content.strip()
                if content.startswith('```json'):
                    content = content[7:]
                if content.endswith('```'):
                    content = content[:-3]
                content = content.strip()
                
                return content
            else:
                logger.debug(f"LocalAI error: {response.status_code}")
                return f"Error: {response.status_code}"
                
        except Exception as e:
            logger.debug(f"LocalAI request failed: {e}")
            return f"Error local AI: {e}"
    
    async def analyze_trading_sentiment(self, symbol: str, market_data: str) -> Dict:
        """
        📊 Analiza sentiment para trading usando IA local
        """
        if not self.available:
            return {"sentiment": 0.0, "confidence": 0.0, "reasoning": "IA local no disponible"}
        
        system_prompt = """Eres un trader profesional especializado en análisis técnico. Tu trabajo es analizar datos de mercado y generar señales de trading precisas.

IMPORTANTE: Responde ÚNICAMENTE con JSON válido en este formato exacto:
{"sentiment": <número decimal entre -1.0 y 1.0>, "confidence": <número decimal entre 0.0 y 1.0>, "reasoning": "<explicación técnica específica>"}

NO uses texto libre, NO des consejos genéricos, SOLO JSON."""
        
        prompt = f"""ANÁLISIS TÉCNICO INMEDIATO para {symbol}:

DATOS DE MERCADO:
{market_data}

CALCULA:
- Sentiment: -1.0 (muy bajista) a +1.0 (muy alcista)
- Confidence: 0.0 (incierto) a 1.0 (muy seguro)
- Reasoning: Explicación técnica específica basada en los datos

RESPUESTA REQUERIDA: Solo JSON válido"""
        
        try:
            response = self._local_ai_request(prompt, system_prompt)
            
            # Intentar parsear JSON
            try:
                result = json.loads(response)
                return result
            except:
                # Si no es JSON válido, usar análisis técnico de respaldo
                return self._fallback_technical_analysis(symbol, market_data)
                
        except Exception as e:
            logger.debug(f"Error análisis sentiment local: {e}")
            return {"sentiment": 0.0, "confidence": 0.0, "reasoning": "Error en análisis"}
    
    def _fallback_technical_analysis(self, symbol: str, market_data: str) -> Dict:
        """
        🔧 Análisis técnico de respaldo cuando LocalAI falla
        """
        try:
            # Análisis básico basado en palabras clave
            market_lower = market_data.lower()
            
            # Detectar patrones alcistas
            bullish_indicators = ['rsi oversold', 'support', 'bounce', 'breakout', 'momentum', 'volume increase']
            bearish_indicators = ['rsi overbought', 'resistance', 'rejection', 'breakdown', 'weakness', 'volume decrease']
            
            bullish_score = sum(1 for indicator in bullish_indicators if indicator in market_lower)
            bearish_score = sum(1 for indicator in bearish_indicators if indicator in market_lower)
            
            # Calcular sentiment
            if bullish_score > bearish_score:
                sentiment = min(0.8, 0.3 + (bullish_score * 0.1))
                reasoning = f"Análisis técnico: {bullish_score} indicadores alcistas detectados"
            elif bearish_score > bullish_score:
                sentiment = max(-0.8, -0.3 - (bearish_score * 0.1))
                reasoning = f"Análisis técnico: {bearish_score} indicadores bajistas detectados"
            else:
                sentiment = 0.0
                reasoning = "Análisis técnico: Señales mixtas, mercado lateral"
            
            confidence = min(0.8, 0.4 + (max(bullish_score, bearish_score) * 0.1))
            
            return {
                "sentiment": sentiment,
                "confidence": confidence,
                "reasoning": reasoning
            }
            
        except Exception as e:
            logger.debug(f"Error análisis técnico respaldo: {e}")
            return {"sentiment": 0.0, "confidence": 0.0, "reasoning": "Error en análisis técnico"}
    
    async def generate_trading_signal(self, symbol: str, price: float, technical_data: Dict) -> Optional[LocalMarketSignal]:
        """
        🎯 Genera señal de trading usando IA local
        """
        if not self.available:
            return None
            
        system_prompt = """Eres un trader institucional con 20 años de experiencia. Analizas datos técnicos y generas señales de trading precisas.

IMPORTANTE: Responde ÚNICAMENTE con JSON válido en este formato exacto:
{"action": "<BUY|SELL|HOLD>", "confidence": <número decimal entre 0.0 y 1.0>, "reasoning": "<análisis técnico específico>"}

NO uses texto libre, NO des consejos genéricos, SOLO JSON con análisis técnico."""
        
        prompt = f"""SEÑAL DE TRADING INMEDIATA para {symbol} @ ${price}:

DATOS TÉCNICOS:
{json.dumps(technical_data, indent=2)}

ANÁLISIS REQUERIDO:
- Action: BUY (compra), SELL (venta), HOLD (mantener)
- Confidence: 0.0 (incierto) a 1.0 (muy seguro)
- Reasoning: Análisis técnico específico basado en RSI, MACD, EMA, soporte/resistencia

RESPUESTA REQUERIDA: Solo JSON válido"""
        
        try:
            response = self._local_ai_request(prompt, system_prompt)
            
            # Intentar parsear respuesta
            try:
                ai_signal = json.loads(response)
            except:
                # Usar análisis técnico de respaldo para señales
                ai_signal = self._fallback_trading_signal(symbol, price, technical_data)
            
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
    
    def _fallback_trading_signal(self, symbol: str, price: float, technical_data: Dict) -> Dict:
        """
        🔧 Señal de trading de respaldo basada en análisis técnico
        """
        try:
            # Análisis básico de indicadores técnicos
            rsi = technical_data.get('rsi', 50)
            macd = technical_data.get('macd', 0)
            ema_20 = technical_data.get('ema_20', price)
            ema_50 = technical_data.get('ema_50', price)
            volume = technical_data.get('volume', 0)
            
            # Calcular score técnico
            technical_score = 0
            
            # RSI analysis
            if rsi < 30:
                technical_score += 0.3  # Oversold - bullish
            elif rsi > 70:
                technical_score -= 0.3   # Overbought - bearish
            elif 40 <= rsi <= 60:
                technical_score += 0.1  # Neutral zone
            
            # MACD analysis
            if macd > 0:
                technical_score += 0.2
            else:
                technical_score -= 0.2
            
            # EMA crossover analysis
            if ema_20 > ema_50:
                technical_score += 0.2
            else:
                technical_score -= 0.2
            
            # Volume analysis (if available)
            if volume > technical_data.get('avg_volume', volume * 1.5):
                technical_score += 0.1
            
            # Determinar acción
            if technical_score > 0.3:
                action = "BUY"
                confidence = min(0.9, 0.5 + abs(technical_score))
                reasoning = f"Análisis técnico: RSI {rsi:.1f}, MACD {macd:+.3f}, EMA20>EMA50"
            elif technical_score < -0.3:
                action = "SELL"
                confidence = min(0.9, 0.5 + abs(technical_score))
                reasoning = f"Análisis técnico: RSI {rsi:.1f}, MACD {macd:+.3f}, EMA20<EMA50"
            else:
                action = "HOLD"
                confidence = 0.4
                reasoning = f"Análisis técnico: Señales mixtas, RSI {rsi:.1f}, MACD {macd:+.3f}"
            
            return {
                "action": action,
                "confidence": confidence,
                "reasoning": reasoning
            }
            
        except Exception as e:
            logger.debug(f"Error señal trading respaldo: {e}")
            return {
                "action": "HOLD",
                "confidence": 0.3,
                "reasoning": "Error en análisis técnico"
            }
    
    def analyze_market_summary(self, symbols_data: Dict) -> str:
        """
        📋 Genera resumen del mercado usando IA local
        """
        if not self.available:
            return "🤖 IA local no disponible - usando análisis básico"
        
        system_prompt = """Eres un analista técnico profesional. Analiza datos de mercado y genera insights específicos.

IMPORTANTE: Responde ÚNICAMENTE con análisis técnico específico en máximo 100 palabras.
NO uses texto genérico, NO des consejos vagos, SOLO análisis técnico basado en los datos."""
        
        # Preparar datos para análisis técnico
        market_overview = []
        bullish_count = 0
        bearish_count = 0
        
        for symbol, data in list(symbols_data.items())[:5]:  # Solo top 5 para no sobrecargar
            price = data.get('price', 0)
            change = data.get('change', 0)
            market_overview.append(f"{symbol}: ${price:.2f} ({change:+.2%})")
            
            if change > 0:
                bullish_count += 1
            elif change < 0:
                bearish_count += 1
        
        prompt = f"""ANÁLISIS TÉCNICO DE MERCADO:

DATOS ACTUALES:
{chr(10).join(market_overview)}

ESTADÍSTICAS:
- Alcistas: {bullish_count}
- Bajistas: {bearish_count}

GENERA:
- Tendencias técnicas específicas
- Oportunidades de trading concretas
- Niveles de soporte/resistencia clave

RESPUESTA: Análisis técnico específico (máximo 100 palabras)"""
        
        try:
            response = self._local_ai_request(prompt, system_prompt)
            
            # Limpiar respuesta si contiene texto genérico
            if "CONSEJO DE AGUSTO" in response or "Mi análisis" in response or "AGUS" in response:
                # Generar análisis técnico básico como fallback
                trend = "ALCISTA" if bullish_count > bearish_count else "BAJISTA" if bearish_count > bullish_count else "LATERAL"
                return f"🤖 Análisis técnico: Tendencia {trend}. {bullish_count} alcistas vs {bearish_count} bajistas. Oportunidades en símbolos con mayor momentum."
            
            return f"🤖 Análisis técnico: {response}"
            
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