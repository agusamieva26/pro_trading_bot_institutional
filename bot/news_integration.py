"""
📰 INTEGRACIÓN DE NOTICIAS CON EL BOT DE TRADING
Conecta la IA personal con el sistema principal de trading
"""
import asyncio
from typing import Dict, List
from loguru import logger
from datetime import datetime

try:
    from .ai_trading_assistant import ai_assistant, MarketSignal
    from .telegram import send_telegram
    AI_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠️ IA no disponible: {e}")
    AI_AVAILABLE = False

class NewsIntegration:
    """
    🔗 Integrador de noticias con el bot principal
    """
    
    def __init__(self):
        self.last_analysis = None
        self.last_analysis_time = None
        self.analysis_interval = 1800  # 30 minutos entre análisis completos
        
    def should_run_analysis(self) -> bool:
        """Determina si debe ejecutar un nuevo análisis"""
        if not self.last_analysis_time:
            return True
            
        time_since_last = (datetime.now() - self.last_analysis_time).total_seconds()
        return time_since_last >= self.analysis_interval
    
    async def get_ai_enhanced_signals(self, symbols: List[str], current_positions: Dict = None) -> Dict:
        """
        🧠 Obtiene señales mejoradas con IA para el bot principal
        """
        if not AI_AVAILABLE:
            return {"ai_available": False, "message": "IA no configurada"}
        
        try:
            # Solo ejecutar análisis completo cada 30min para evitar rate limits
            if self.should_run_analysis():
                logger.info("🧠 Ejecutando análisis IA completo...")
                
                signals, sentiment, summary = await ai_assistant.run_full_analysis(symbols, current_positions)
                
                self.last_analysis = {
                    "signals": signals,
                    "sentiment": sentiment,
                    "summary": summary,
                    "timestamp": datetime.now()
                }
                self.last_analysis_time = datetime.now()
                
                # Enviar resumen a Telegram si hay señales fuertes
                strong_signals = [s for s in signals if s.confidence > 0.7 and s.action in ["BUY", "SELL"]]
                if strong_signals:
                    await self._send_ai_alert(strong_signals, sentiment)
            
            return {
                "ai_available": True,
                "analysis": self.last_analysis,
                "fresh_analysis": self.should_run_analysis() == False
            }
            
        except Exception as e:
            logger.error(f"❌ Error en análisis IA: {e}")
            return {"ai_available": True, "error": str(e)}
    
    async def _send_ai_alert(self, strong_signals: List[MarketSignal], sentiment: Dict):
        """Envía alerta de señales fuertes por Telegram"""
        try:
            sentiment_score = sentiment.get("overall_sentiment", 0.0)
            sentiment_text = "📈 Positivo" if sentiment_score > 0.2 else "📉 Negativo" if sentiment_score < -0.2 else "📊 Neutral"
            
            message = f"""🧠 ALERTA IA PERSONAL

{sentiment_text} ({sentiment_score:+.2f})

🎯 SEÑALES FUERTES DETECTADAS:"""
            
            for signal in strong_signals[:3]:
                emoji = "🟢" if signal.action == "BUY" else "🔴"
                message += f"""
{emoji} {signal.symbol}: {signal.action} ({signal.confidence:.1%})
   💡 {signal.reasoning[:80]}"""
            
            await send_telegram(message)
            
        except Exception as e:
            logger.debug(f"Error enviando alerta IA: {e}")
    
    def get_ai_filter_score(self, symbol: str) -> float:
        """
        🎯 Obtiene score de filtro IA para un símbolo
        Retorna: 0.0-1.0 donde >0.6 indica señal positiva
        """
        if not self.last_analysis or not AI_AVAILABLE:
            return 0.5  # Neutral si no hay IA
            
        signals = self.last_analysis.get("signals", [])
        
        # Buscar señal para este símbolo
        for signal in signals:
            if signal.symbol == symbol:
                # Convertir acción a score
                if signal.action == "BUY":
                    return signal.confidence
                elif signal.action == "SELL":
                    return 1.0 - signal.confidence  # Invertir para sell
                else:  # HOLD
                    return 0.5
        
        # Si no hay señal específica, usar sentiment general
        sentiment = self.last_analysis.get("sentiment", {}).get("overall_sentiment", 0.0)
        return max(0.0, min(1.0, 0.5 + sentiment * 0.3))  # Convertir -1,1 a 0.2-0.8
    
    def get_enhanced_reasoning(self, symbol: str, action: str) -> str:
        """
        💭 Obtiene reasoning mejorado de la IA para una operación
        """
        if not self.last_analysis or not AI_AVAILABLE:
            return "Análisis técnico estándar"
            
        signals = self.last_analysis.get("signals", [])
        
        # Buscar reasoning específico
        for signal in signals:
            if signal.symbol == symbol and signal.action == action:
                return f"IA: {signal.reasoning}"
        
        # Reasoning general basado en sentiment
        sentiment = self.last_analysis.get("sentiment", {})
        sentiment_summary = sentiment.get("summary", "Sin análisis de noticias")
        
        return f"Análisis IA + técnico. Sentiment: {sentiment_summary[:100]}"

# Instancia global
news_integration = NewsIntegration()

# Funciones de conveniencia para el bot principal
async def get_ai_market_analysis(symbols: List[str]) -> Dict:
    """🧠 Obtiene análisis de mercado con IA"""
    return await news_integration.get_ai_enhanced_signals(symbols)

def get_ai_symbol_score(symbol: str) -> float:
    """🎯 Score IA para un símbolo (0.0-1.0)"""
    return news_integration.get_ai_filter_score(symbol)

def get_ai_trade_reasoning(symbol: str, action: str) -> str:
    """💭 Reasoning IA para una operación"""
    return news_integration.get_enhanced_reasoning(symbol, action)