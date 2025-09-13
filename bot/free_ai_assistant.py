"""
🆓 IA GRATUITA INTEGRADA - SIN API KEYS NECESARIAS
Análisis inteligente usando algoritmos avanzados y patrones de mercado
100% Gratis, Sin límites, Sin dependencias externas
"""
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from loguru import logger
import asyncio
from dataclasses import dataclass
import statistics

@dataclass
class FreeMarketSignal:
    """Señal generada por IA gratuita integrada"""
    symbol: str
    action: str  # BUY, SELL, HOLD
    confidence: float  # 0.0 - 1.0
    reasoning: str
    technical_score: float
    market_sentiment: float
    timestamp: datetime

class FreeAITradingAssistant:
    """
    🆓 IA TRADING COMPLETAMENTE GRATUITA E INTEGRADA
    - Sin API keys ni dependencias
    - Algoritmos de análisis avanzado
    - Patrones de reconocimiento de mercado
    - Compatible 100% con tu bot
    """
    
    def __init__(self):
        self.market_patterns = self._load_market_patterns()
        self.sentiment_keywords = self._load_sentiment_keywords()
        logger.info("🤖 IA GRATUITA Integrada activada - ¡Sin límites ni costos!")
    
    def _load_market_patterns(self) -> Dict:
        """Carga patrones de mercado pre-definidos"""
        return {
            "bullish_patterns": [
                {"name": "Golden Cross", "weight": 0.8, "conditions": ["ema_12 > ema_26", "volume_high"]},
                {"name": "Bullish RSI Divergence", "weight": 0.7, "conditions": ["rsi_rising", "price_rising"]},
                {"name": "Breakout Pattern", "weight": 0.9, "conditions": ["price > resistance", "volume_spike"]},
                {"name": "Support Bounce", "weight": 0.6, "conditions": ["price_near_support", "rsi_oversold"]}
            ],
            "bearish_patterns": [
                {"name": "Death Cross", "weight": 0.8, "conditions": ["ema_12 < ema_26", "volume_high"]},
                {"name": "Bearish RSI Divergence", "weight": 0.7, "conditions": ["rsi_falling", "price_falling"]},
                {"name": "Breakdown Pattern", "weight": 0.9, "conditions": ["price < support", "volume_spike"]},
                {"name": "Resistance Rejection", "weight": 0.6, "conditions": ["price_near_resistance", "rsi_overbought"]}
            ]
        }
    
    def _load_sentiment_keywords(self) -> Dict:
        """Carga keywords para análisis de sentiment"""
        return {
            "bullish": ["bull", "buy", "pump", "moon", "rocket", "breakout", "rally", "surge", "gain", "profit", "positive", "up", "rise", "green"],
            "bearish": ["bear", "sell", "dump", "crash", "drop", "fall", "decline", "red", "loss", "negative", "down", "correction"],
            "crypto_positive": ["bitcoin", "btc", "ethereum", "eth", "adoption", "institutional", "defi", "nft", "blockchain"],
            "market_positive": ["earnings", "revenue", "growth", "expansion", "partnership", "innovation", "upgrade", "launch"]
        }
    
    def analyze_technical_patterns(self, market_data: Dict) -> Dict:
        """
        📊 Analiza patrones técnicos avanzados
        """
        try:
            # Extraer indicadores técnicos
            rsi = market_data.get("rsi_14", 50)
            ema_12 = market_data.get("ema_12", 0)
            ema_26 = market_data.get("ema_26", 0)
            price = market_data.get("close", 0)
            volume = market_data.get("volume", 0)
            atr = market_data.get("atr_14", 0)
            
            # Análisis de momentum
            momentum_score = self._calculate_momentum_score(rsi, ema_12, ema_26, price)
            
            # Análisis de volatilidad
            volatility_score = self._calculate_volatility_score(atr, price)
            
            # Detección de patrones
            pattern_score = self._detect_patterns(market_data)
            
            # Score técnico combinado
            technical_score = (momentum_score * 0.4 + volatility_score * 0.2 + pattern_score * 0.4)
            
            return {
                "technical_score": technical_score,
                "momentum": momentum_score,
                "volatility": volatility_score,
                "patterns": pattern_score,
                "confidence": abs(technical_score) * 0.8 + 0.2
            }
            
        except Exception as e:
            logger.debug(f"Error análisis técnico: {e}")
            return {"technical_score": 0.0, "confidence": 0.1}
    
    def _calculate_momentum_score(self, rsi: float, ema_12: float, ema_26: float, price: float) -> float:
        """Calcula score de momentum"""
        score = 0.0
        
        # RSI analysis
        if rsi > 70:
            score -= 0.3  # Sobrecomprado
        elif rsi < 30:
            score += 0.4  # Sobreventa (más bullish)
        else:
            # RSI neutral, evaluar tendencia
            score += (rsi - 50) / 100  # -0.2 a +0.2
        
        # EMA Cross analysis
        if ema_12 > 0 and ema_26 > 0:
            ema_diff = (ema_12 - ema_26) / ema_26
            score += ema_diff * 2  # Amplificar señal EMA
        
        return max(-1.0, min(1.0, score))
    
    def _calculate_volatility_score(self, atr: float, price: float) -> float:
        """Calcula score de volatilidad (oportunidad)"""
        if price <= 0:
            return 0.0
            
        volatility_ratio = atr / price
        
        # Volatilidad óptima para scalping: 2-5%
        if 0.02 <= volatility_ratio <= 0.05:
            return 0.3  # Volatilidad ideal
        elif volatility_ratio < 0.02:
            return -0.1  # Muy estable, menos oportunidades
        elif volatility_ratio > 0.08:
            return -0.2  # Muy volátil, riesgoso
        else:
            return 0.1  # Volatilidad moderada
    
    def _detect_patterns(self, market_data: Dict) -> float:
        """Detecta patrones de mercado"""
        score = 0.0
        detected_patterns = []
        
        # Extraer datos necesarios
        rsi = market_data.get("rsi_14", 50)
        ema_12 = market_data.get("ema_12", 0)
        ema_26 = market_data.get("ema_26", 0)
        volume = market_data.get("volume", 0)
        
        # Detectar patrones bullish
        for pattern in self.market_patterns["bullish_patterns"]:
            if self._pattern_matches(pattern, market_data):
                score += pattern["weight"] * 0.3
                detected_patterns.append(pattern["name"])
        
        # Detectar patrones bearish  
        for pattern in self.market_patterns["bearish_patterns"]:
            if self._pattern_matches(pattern, market_data):
                score -= pattern["weight"] * 0.3
                detected_patterns.append(pattern["name"])
        
        if detected_patterns:
            logger.debug(f"Patrones detectados: {detected_patterns}")
        
        return max(-1.0, min(1.0, score))
    
    def _pattern_matches(self, pattern: Dict, market_data: Dict) -> bool:
        """Verifica si un patrón coincide con los datos"""
        conditions_met = 0
        total_conditions = len(pattern["conditions"])
        
        rsi = market_data.get("rsi_14", 50)
        ema_12 = market_data.get("ema_12", 0)
        ema_26 = market_data.get("ema_26", 0)
        price = market_data.get("close", 0)
        
        for condition in pattern["conditions"]:
            if condition == "ema_12 > ema_26" and ema_12 > ema_26:
                conditions_met += 1
            elif condition == "ema_12 < ema_26" and ema_12 < ema_26:
                conditions_met += 1
            elif condition == "rsi_oversold" and rsi < 35:
                conditions_met += 1
            elif condition == "rsi_overbought" and rsi > 65:
                conditions_met += 1
            elif condition == "volume_high":  # Asumimos volumen alto si está presente
                conditions_met += 1
        
        # Patrón coincide si se cumplen al menos 60% de condiciones
        return conditions_met >= (total_conditions * 0.6)
    
    def analyze_market_sentiment(self, news_text: str = "") -> Dict:
        """
        📰 Analiza sentiment del mercado sin APIs externas
        """
        if not news_text:
            # Sin noticias, usar sentiment neutral con sesgo ligeramente positivo
            return {
                "sentiment": 0.1,  # Ligeramente bullish por defecto crypto
                "confidence": 0.3,
                "reasoning": "Análisis técnico base - sin noticias disponibles"
            }
        
        # Análisis de keywords
        text_lower = news_text.lower()
        bullish_count = 0
        bearish_count = 0
        
        # Contar keywords bullish
        for keyword_list in [self.sentiment_keywords["bullish"], self.sentiment_keywords["crypto_positive"], self.sentiment_keywords["market_positive"]]:
            bullish_count += sum(1 for keyword in keyword_list if keyword in text_lower)
        
        # Contar keywords bearish
        bearish_count += sum(1 for keyword in self.sentiment_keywords["bearish"] if keyword in text_lower)
        
        # Calcular sentiment
        total_keywords = bullish_count + bearish_count
        if total_keywords == 0:
            sentiment = 0.0
            confidence = 0.2
        else:
            sentiment = (bullish_count - bearish_count) / total_keywords
            confidence = min(0.9, total_keywords / 10)  # Más keywords = más confianza
        
        # Determinar reasoning
        if sentiment > 0.3:
            reasoning = f"Sentiment BULLISH detectado - {bullish_count} indicadores positivos"
        elif sentiment < -0.3:
            reasoning = f"Sentiment BEARISH detectado - {bearish_count} indicadores negativos"  
        else:
            reasoning = "Sentiment NEUTRAL - indicadores mixtos"
        
        return {
            "sentiment": max(-1.0, min(1.0, sentiment)),
            "confidence": confidence,
            "reasoning": reasoning
        }
    
    async def generate_trading_signal(self, symbol: str, market_data: Dict, news_text: str = "") -> Optional[FreeMarketSignal]:
        """
        🎯 Genera señal de trading inteligente
        """
        try:
            # Análisis técnico
            tech_analysis = self.analyze_technical_patterns(market_data)
            tech_score = tech_analysis["technical_score"]
            
            # Análisis de sentiment
            sentiment_analysis = self.analyze_market_sentiment(news_text)
            sentiment_score = sentiment_analysis["sentiment"]
            
            # Score combinado (70% técnico, 30% sentiment)
            combined_score = (tech_score * 0.7) + (sentiment_score * 0.3)
            
            # Determinar acción
            if combined_score > 0.2:
                action = "BUY"
                confidence = min(0.95, abs(combined_score) * 0.8 + 0.4)
            elif combined_score < -0.2:
                action = "SELL"
                confidence = min(0.95, abs(combined_score) * 0.8 + 0.4)
            else:
                action = "HOLD"
                confidence = 0.3 + abs(combined_score) * 0.2
            
            # Construir reasoning
            reasoning_parts = []
            if abs(tech_score) > 0.3:
                reasoning_parts.append(f"Técnico: {tech_score:+.2f}")
            if abs(sentiment_score) > 0.2:
                reasoning_parts.append(f"Sentiment: {sentiment_analysis['reasoning']}")
            
            reasoning = f"IA Gratuita: {' | '.join(reasoning_parts)}" if reasoning_parts else "Análisis neutral"
            
            return FreeMarketSignal(
                symbol=symbol,
                action=action,
                confidence=confidence,
                reasoning=reasoning,
                technical_score=tech_score,
                market_sentiment=sentiment_score,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.debug(f"Error generando señal IA gratuita: {e}")
            return None
    
    def generate_market_summary(self, signals: List[FreeMarketSignal]) -> str:
        """
        📋 Genera resumen inteligente del mercado
        """
        if not signals:
            return "🤖 IA Gratuita: Sin señales disponibles"
        
        # Estadísticas de señales
        buy_signals = [s for s in signals if s.action == "BUY"]
        sell_signals = [s for s in signals if s.action == "SELL"]
        hold_signals = [s for s in signals if s.action == "HOLD"]
        
        # Confianza promedio
        avg_confidence = statistics.mean(s.confidence for s in signals)
        
        # Sentiment general
        avg_sentiment = statistics.mean(s.market_sentiment for s in signals)
        sentiment_text = "BULLISH" if avg_sentiment > 0.1 else "BEARISH" if avg_sentiment < -0.1 else "NEUTRAL"
        
        # Top señales por confianza
        top_signals = sorted(signals, key=lambda x: x.confidence, reverse=True)[:3]
        
        summary = f"""
🤖 IA GRATUITA INTEGRADA - RESUMEN DE MERCADO

📊 Señales Generadas: {len(signals)}
   • 🟢 COMPRAR: {len(buy_signals)}
   • 🔴 VENDER: {len(sell_signals)}
   • 🟡 MANTENER: {len(hold_signals)}

🎯 Confianza Promedio: {avg_confidence:.1%}
📈 Sentiment General: {sentiment_text} ({avg_sentiment:+.2f})

🏆 TOP RECOMENDACIONES (IA Gratis):"""
        
        for i, signal in enumerate(top_signals):
            emoji = "🟢" if signal.action == "BUY" else "🔴" if signal.action == "SELL" else "🟡"
            summary += f"""
   {i+1}. {emoji} {signal.symbol}: {signal.action} ({signal.confidence:.1%})
      💡 {signal.reasoning[:70]}..."""
        
        summary += f"""

✅ VENTAJAS IA GRATUITA:
   • 100% Sin costos ni límites
   • Análisis técnico avanzado  
   • Detección de patrones automática
   • Integración completa con tu bot"""
        
        return summary

# Instancia global de IA gratuita
free_ai_assistant = FreeAITradingAssistant()

# Funciones de integración
def get_free_ai_analysis_sync(symbols: List[str], market_data: Dict = None) -> Dict:
    """
    🤖 Función principal para análisis con IA gratuita (síncrona)
    """
    signals = []
    
    if market_data:
        for symbol in symbols[:5]:  # Top 5 para velocidad
            data = market_data.get(symbol, {})
            if data:
                # Llamada síncrona
                signal = asyncio.run(free_ai_assistant.generate_trading_signal(symbol, data))
                if signal:
                    signals.append(signal)
    
    # Generar resumen
    summary = free_ai_assistant.generate_market_summary(signals)
    
    return {
        "ai_available": True,
        "ai_type": "FREE_INTEGRATED",
        "signals": signals,
        "summary": summary,
        "timestamp": datetime.now()
    }

async def get_free_ai_analysis(symbols: List[str], market_data: Dict = None) -> Dict:
    """
    🤖 Función principal para análisis con IA gratuita (async)
    """
    signals = []
    
    if market_data:
        for symbol in symbols[:5]:  # Top 5 para velocidad
            data = market_data.get(symbol, {})
            if data:
                signal = await free_ai_assistant.generate_trading_signal(symbol, data)
                if signal:
                    signals.append(signal)
    
    # Generar resumen
    summary = free_ai_assistant.generate_market_summary(signals)
    
    return {
        "ai_available": True,
        "ai_type": "FREE_INTEGRATED",
        "signals": signals,
        "summary": summary,
        "timestamp": datetime.now()
    }

def get_free_ai_score(symbol: str, market_data: Dict = None) -> float:
    """🎯 Score IA gratuita para un símbolo"""
    if not market_data:
        return 0.5
    
    try:
        analysis = free_ai_assistant.analyze_technical_patterns(market_data)
        tech_score = analysis.get("technical_score", 0.0)
        
        # Convertir score técnico (-1,1) a score de trading (0,1)
        return max(0.0, min(1.0, 0.5 + tech_score * 0.4))
    except:
        return 0.5

if __name__ == "__main__":
    # Test de IA gratuita
    async def test_free_ai():
        logger.info("🧪 Testing Free AI Assistant...")
        
        test_data = {
            "BTC/USD": {
                "close": 58000,
                "rsi_14": 45,
                "ema_12": 58100,
                "ema_26": 57900,
                "atr_14": 1200,
                "volume": 1000
            }
        }
        
        analysis = await get_free_ai_analysis(["BTC/USD"], test_data)
        print(analysis["summary"])
    
    asyncio.run(test_free_ai())