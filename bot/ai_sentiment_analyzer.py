"""
🧠 AI SENTIMENT ANALYZER - SISTEMA AVANZADO DE ANÁLISIS
Análisis sofisticado de sentiment usando OpenAI GPT-5 con detección de eventos críticos
Correlación sentiment-precio para predicción de impacto en trading
"""

import asyncio
import json
import re
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict
import pandas as pd
import numpy as np
from collections import defaultdict, deque
import statistics

from openai import OpenAI
from .util import logger
from .config import settings
from .advanced_news_engine import NewsArticle

@dataclass
class SentimentResult:
    """Resultado completo de análisis de sentiment"""
    article_id: str
    symbol: str
    sentiment_score: float  # -1.0 (very bearish) to +1.0 (very bullish)
    confidence: float      # 0.0 to 1.0
    sentiment_label: str   # "very_bearish", "bearish", "neutral", "bullish", "very_bullish"
    critical_keywords: List[str]
    price_impact_prediction: Dict
    reasoning: str
    timestamp: datetime
    
    # Análisis detallado
    emotional_intensity: float  # 0.0 to 1.0 
    market_relevance: float    # 0.0 to 1.0
    urgency_level: int        # 1-5 scale
    event_type: str          # "earnings", "merger", "regulation", "general", etc.

@dataclass
class MarketSentimentSummary:
    """Resumen de sentiment del mercado"""
    overall_sentiment: float
    confidence: float
    symbol_sentiments: Dict[str, float]
    critical_events: List[Dict]
    market_condition: str  # "fear", "greed", "neutral", "panic", "euphoria"
    recommendation: str
    timestamp: datetime

class CriticalEventDetector:
    """
    🚨 Detector de eventos críticos en noticias
    Identifica noticias que pueden causar movimientos significativos
    """
    
    def __init__(self):
        # Palabras clave críticas organizadas por categoría
        self.critical_keywords = {
            "earnings": {
                "positive": ["beat", "exceed", "outperform", "strong earnings", "record profit", "revenue growth"],
                "negative": ["miss", "below", "disappointing", "weak earnings", "loss", "decline revenue"]
            },
            "corporate_actions": {
                "positive": ["merger", "acquisition", "buyback", "dividend increase", "partnership", "collaboration"],
                "negative": ["bankruptcy", "lawsuit", "investigation", "fraud", "resignation", "scandal"]
            },
            "regulatory": {
                "positive": ["approval", "license", "compliance", "regulation favorable"],
                "negative": ["ban", "violation", "fine", "penalty", "restriction", "investigation"]
            },
            "market_moving": {
                "positive": ["breakthrough", "innovation", "patent", "contract", "expansion"],
                "negative": ["hack", "security breach", "data leak", "recall", "shutdown"]
            },
            "crypto_specific": {
                "positive": ["adoption", "institutional", "etf approval", "mainstream", "integration"],
                "negative": ["regulation", "crackdown", "ban", "delisting", "security issue"]
            }
        }
        
        # Multiplicadores de impacto por tipo de evento
        self.impact_multipliers = {
            "earnings": 1.5,
            "corporate_actions": 2.0,
            "regulatory": 1.8,
            "market_moving": 1.6,
            "crypto_specific": 1.7
        }
        
        logger.info("🚨 Critical Event Detector inicializado")
    
    def analyze_critical_events(self, article: NewsArticle) -> Dict:
        """Analiza eventos críticos en un artículo"""
        text = f"{article.title} {article.content}".lower()
        
        detected_events = {
            "has_critical_event": False,
            "event_types": [],
            "keywords_found": [],
            "impact_multiplier": 1.0,
            "urgency_level": 1,
            "event_details": {}
        }
        
        for category, keywords in self.critical_keywords.items():
            category_score = 0
            found_keywords = []
            
            # Verificar keywords positivas y negativas
            for sentiment_type, keyword_list in keywords.items():
                for keyword in keyword_list:
                    if keyword in text:
                        found_keywords.append(f"{keyword} ({sentiment_type})")
                        category_score += 1 if sentiment_type == "positive" else -1
            
            if found_keywords:
                detected_events["has_critical_event"] = True
                detected_events["event_types"].append(category)
                detected_events["keywords_found"].extend(found_keywords)
                detected_events["impact_multiplier"] *= self.impact_multipliers.get(category, 1.0)
                detected_events["event_details"][category] = {
                    "score": category_score,
                    "keywords": found_keywords
                }
        
        # Calcular nivel de urgencia
        if detected_events["has_critical_event"]:
            num_events = len(detected_events["event_types"])
            impact = detected_events["impact_multiplier"]
            
            if impact > 2.5 or num_events >= 3:
                detected_events["urgency_level"] = 5  # Crítico
            elif impact > 2.0 or num_events >= 2:
                detected_events["urgency_level"] = 4  # Alto
            elif impact > 1.5:
                detected_events["urgency_level"] = 3  # Medio
            else:
                detected_events["urgency_level"] = 2  # Bajo
        
        return detected_events

class AISentimentAnalyzer:
    """
    🧠 Analizador de sentiment usando OpenAI GPT-5
    Análisis sofisticado con contexto financiero y market awareness
    """
    
    def __init__(self):
        # Inicializar OpenAI
        try:
            self.openai_client = OpenAI()  # Usa la variable de entorno OPENAI_API_KEY
            logger.info("🧠 AI Sentiment Analyzer inicializado con OpenAI GPT-5")
        except Exception as e:
            logger.error(f"❌ Error inicializando OpenAI: {e}")
            self.openai_client = None
        
        self.event_detector = CriticalEventDetector()
        
        # Cache para análisis recientes
        self.analysis_cache = {}
        self.cache_ttl = 600  # 10 minutos
        
        # Prompt optimizado para análisis financiero
        self.analysis_prompt = """You are an expert financial analyst specialized in market sentiment analysis. 

Analyze the following financial news article and provide a comprehensive sentiment analysis.

Focus on:
1. Overall market sentiment toward the mentioned assets/companies
2. Potential price impact and direction 
3. Emotional intensity and market relevance
4. Critical events or announcements that could move markets
5. Short-term vs long-term implications

Respond ONLY with valid JSON in this exact format:
{
    "sentiment_score": <float between -1.0 and 1.0>,
    "confidence": <float between 0.0 and 1.0>,
    "sentiment_label": "<very_bearish|bearish|neutral|bullish|very_bullish>",
    "emotional_intensity": <float between 0.0 and 1.0>,
    "market_relevance": <float between 0.0 and 1.0>,
    "event_type": "<earnings|merger|regulation|general|other>",
    "reasoning": "<detailed explanation in 50-100 words>",
    "price_impact": {
        "direction": "<up|down|neutral>",
        "magnitude": <float between 0.0 and 1.0>,
        "timeframe": "<immediate|short_term|medium_term|long_term>",
        "confidence": <float between 0.0 and 1.0>
    }
}"""
        
        # Estadísticas de análisis
        self.stats = {
            "total_analyzed": 0,
            "cache_hits": 0,
            "openai_calls": 0,
            "avg_sentiment": 0.0,
            "last_analysis": None
        }
        
        logger.info("🧠 AI Sentiment Analyzer configurado")
    
    async def analyze_article_sentiment(self, article: NewsArticle, 
                                      symbol: Optional[str] = None) -> SentimentResult:
        """
        🎯 Análisis principal de sentiment para un artículo
        """
        if not self.openai_client:
            return self._create_fallback_sentiment(article, symbol)
        
        # Verificar cache
        cache_key = hashlib.md5(f"{article.id}{symbol or ''}".encode()).hexdigest()
        if cache_key in self.analysis_cache:
            cache_data = self.analysis_cache[cache_key]
            if time.time() - cache_data["timestamp"] < self.cache_ttl:
                self.stats["cache_hits"] += 1
                return cache_data["result"]
        
        try:
            # Detectar eventos críticos primero
            critical_events = self.event_detector.analyze_critical_events(article)
            
            # Preparar contexto para GPT-5
            symbol_context = f" Focus specifically on {symbol}." if symbol else ""
            article_text = f"Title: {article.title}\n\nContent: {article.content[:2000]}"
            
            full_prompt = f"{self.analysis_prompt}\n\n{symbol_context}\n\nArticle:\n{article_text}"
            
            # Llamar a OpenAI GPT-5
            response = await self._call_openai_async(full_prompt)
            
            if response:
                # Parsear respuesta
                ai_analysis = json.loads(response)
                
                # Crear resultado completo
                sentiment_result = SentimentResult(
                    article_id=article.id,
                    symbol=symbol or "GENERAL",
                    sentiment_score=float(ai_analysis.get("sentiment_score", 0.0)),
                    confidence=float(ai_analysis.get("confidence", 0.5)),
                    sentiment_label=ai_analysis.get("sentiment_label", "neutral"),
                    critical_keywords=critical_events.get("keywords_found", []),
                    price_impact_prediction=ai_analysis.get("price_impact", {}),
                    reasoning=ai_analysis.get("reasoning", ""),
                    timestamp=datetime.now(),
                    emotional_intensity=float(ai_analysis.get("emotional_intensity", 0.5)),
                    market_relevance=float(ai_analysis.get("market_relevance", 0.5)),
                    urgency_level=critical_events.get("urgency_level", 1),
                    event_type=ai_analysis.get("event_type", "general")
                )
                
                # Ajustar sentiment basado en eventos críticos
                if critical_events["has_critical_event"]:
                    sentiment_result.sentiment_score *= critical_events["impact_multiplier"]
                    sentiment_result.sentiment_score = max(min(sentiment_result.sentiment_score, 1.0), -1.0)
                
                # Guardar en cache
                self.analysis_cache[cache_key] = {
                    "result": sentiment_result,
                    "timestamp": time.time()
                }
                
                # Actualizar estadísticas
                self.stats["total_analyzed"] += 1
                self.stats["openai_calls"] += 1
                self.stats["avg_sentiment"] = (self.stats["avg_sentiment"] * (self.stats["total_analyzed"] - 1) + sentiment_result.sentiment_score) / self.stats["total_analyzed"]
                self.stats["last_analysis"] = datetime.now()
                
                logger.debug(f"🧠 Sentiment analizado: {sentiment_result.sentiment_score:.3f} ({sentiment_result.sentiment_label})")
                
                return sentiment_result
                
        except Exception as e:
            logger.error(f"❌ Error en análisis AI: {e}")
        
        # Fallback en caso de error
        return self._create_fallback_sentiment(article, symbol)
    
    async def _call_openai_async(self, prompt: str) -> Optional[str]:
        """Llamada asíncrona a OpenAI"""
        try:
            # Ejecutar en thread pool para no bloquear
            loop = asyncio.get_event_loop()
            
            def call_openai():
                response = self.openai_client.chat.completions.create(
                    model="gpt-5",  # the newest OpenAI model is "gpt-5"
                    messages=[
                        {"role": "system", "content": "You are a world-class financial analyst. Respond only with valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    max_tokens=800,
                    temperature=0.3  # Menos creatividad, más consistencia
                )
                return response.choices[0].message.content
            
            return await loop.run_in_executor(None, call_openai)
            
        except Exception as e:
            logger.error(f"❌ Error llamada OpenAI: {e}")
            return None
    
    def _create_fallback_sentiment(self, article: NewsArticle, symbol: Optional[str]) -> SentimentResult:
        """Crear análisis de fallback cuando OpenAI no está disponible"""
        
        # Análisis básico de palabras clave
        text = f"{article.title} {article.content}".lower()
        
        positive_words = ["up", "rise", "gain", "profit", "bullish", "positive", "growth", "increase", "strong"]
        negative_words = ["down", "fall", "loss", "bearish", "negative", "decline", "decrease", "weak", "crash"]
        
        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)
        
        # Calcular sentiment básico
        if positive_count > negative_count:
            sentiment_score = min(0.6, (positive_count - negative_count) * 0.2)
            sentiment_label = "bullish"
        elif negative_count > positive_count:
            sentiment_score = max(-0.6, -(negative_count - positive_count) * 0.2)
            sentiment_label = "bearish"
        else:
            sentiment_score = 0.0
            sentiment_label = "neutral"
        
        # Detectar eventos críticos
        critical_events = self.event_detector.analyze_critical_events(article)
        
        return SentimentResult(
            article_id=article.id,
            symbol=symbol or "GENERAL",
            sentiment_score=sentiment_score,
            confidence=0.4,  # Menor confianza para fallback
            sentiment_label=sentiment_label,
            critical_keywords=critical_events.get("keywords_found", []),
            price_impact_prediction={"direction": "neutral", "magnitude": 0.3, "confidence": 0.4},
            reasoning="Fallback analysis based on keyword sentiment",
            timestamp=datetime.now(),
            emotional_intensity=0.5,
            market_relevance=0.5,
            urgency_level=critical_events.get("urgency_level", 1),
            event_type="general"
        )
    
    async def analyze_batch_sentiment(self, articles: List[NewsArticle], 
                                    symbols: List[str] = None) -> List[SentimentResult]:
        """
        📊 Análisis en lote de múltiples artículos
        """
        logger.info(f"📊 Analizando sentiment de {len(articles)} artículos...")
        
        # Crear tareas asíncronas
        tasks = []
        for article in articles:
            # Determinar símbolo relevante para el artículo
            relevant_symbol = None
            if symbols:
                for symbol in symbols:
                    symbol_clean = symbol.replace("/USD", "").replace("/", "").lower()
                    if symbol_clean in article.title.lower() or symbol_clean in article.content.lower():
                        relevant_symbol = symbol
                        break
            
            task = asyncio.create_task(self.analyze_article_sentiment(article, relevant_symbol))
            tasks.append(task)
        
        # Ejecutar análisis en paralelo (con límite para no sobrecargar API)
        results = []
        batch_size = 5  # Procesar 5 artículos simultáneamente
        
        for i in range(0, len(tasks), batch_size):
            batch_tasks = tasks[i:i + batch_size]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, SentimentResult):
                    results.append(result)
                elif isinstance(result, Exception):
                    logger.debug(f"Error en análisis de lote: {result}")
            
            # Pequeña pausa entre lotes para rate limiting
            if i + batch_size < len(tasks):
                await asyncio.sleep(1)
        
        logger.info(f"✅ Análisis completado: {len(results)} resultados")
        return results

class MarketSentimentAggregator:
    """
    📈 Agregador de sentiment del mercado
    Combina múltiples análisis para generar sentiment general del mercado
    """
    
    def __init__(self):
        self.sentiment_history = defaultdict(lambda: deque(maxlen=50))  # Histórico por símbolo
        self.market_sentiment_history = deque(maxlen=100)  # Sentiment general del mercado
        
        logger.info("📈 Market Sentiment Aggregator inicializado")
    
    def aggregate_sentiment(self, sentiment_results: List[SentimentResult], 
                          symbols: List[str]) -> MarketSentimentSummary:
        """
        🎯 Agrega sentiment de múltiples análisis
        """
        if not sentiment_results:
            return self._create_neutral_summary(symbols)
        
        # Agrupar por símbolo
        symbol_sentiments = defaultdict(list)
        
        for result in sentiment_results:
            symbol = result.symbol
            symbol_sentiments[symbol].append(result)
        
        # Calcular sentiment promedio por símbolo
        symbol_averages = {}
        weighted_sentiments = []
        critical_events = []
        
        for symbol, results in symbol_sentiments.items():
            if results:
                # Calcular promedio ponderado por confianza
                weighted_scores = [r.sentiment_score * r.confidence for r in results]
                total_confidence = sum(r.confidence for r in results)
                
                if total_confidence > 0:
                    avg_sentiment = sum(weighted_scores) / total_confidence
                else:
                    avg_sentiment = statistics.mean([r.sentiment_score for r in results])
                
                symbol_averages[symbol] = avg_sentiment
                weighted_sentiments.append(avg_sentiment)
                
                # Actualizar histórico
                self.sentiment_history[symbol].append({
                    "sentiment": avg_sentiment,
                    "timestamp": datetime.now(),
                    "count": len(results)
                })
                
                # Detectar eventos críticos
                for result in results:
                    if result.urgency_level >= 4:  # Urgencia alta o crítica
                        critical_events.append({
                            "symbol": symbol,
                            "event_type": result.event_type,
                            "sentiment": result.sentiment_score,
                            "urgency": result.urgency_level,
                            "keywords": result.critical_keywords,
                            "reasoning": result.reasoning
                        })
        
        # Calcular sentiment general del mercado
        if weighted_sentiments:
            overall_sentiment = statistics.mean(weighted_sentiments)
            confidence = min(len(sentiment_results) / 10, 1.0)  # Más artículos = más confianza
        else:
            overall_sentiment = 0.0
            confidence = 0.0
        
        # Actualizar histórico del mercado
        self.market_sentiment_history.append({
            "sentiment": overall_sentiment,
            "timestamp": datetime.now(),
            "confidence": confidence
        })
        
        # Determinar condición del mercado
        market_condition = self._determine_market_condition(overall_sentiment, critical_events)
        
        # Generar recomendación
        recommendation = self._generate_recommendation(overall_sentiment, critical_events, symbol_averages)
        
        return MarketSentimentSummary(
            overall_sentiment=overall_sentiment,
            confidence=confidence,
            symbol_sentiments=symbol_averages,
            critical_events=critical_events,
            market_condition=market_condition,
            recommendation=recommendation,
            timestamp=datetime.now()
        )
    
    def _determine_market_condition(self, sentiment: float, critical_events: List[Dict]) -> str:
        """Determina condición del mercado basada en sentiment"""
        
        # Considerar eventos críticos
        high_urgency_events = [e for e in critical_events if e["urgency"] >= 4]
        
        if high_urgency_events:
            negative_events = [e for e in high_urgency_events if e["sentiment"] < -0.3]
            if negative_events:
                return "panic"
            
            positive_events = [e for e in high_urgency_events if e["sentiment"] > 0.3]
            if positive_events:
                return "euphoria"
        
        # Sentiment normal
        if sentiment >= 0.6:
            return "greed"
        elif sentiment >= 0.2:
            return "neutral"
        elif sentiment >= -0.2:
            return "neutral"
        elif sentiment >= -0.6:
            return "fear"
        else:
            return "extreme_fear"
    
    def _generate_recommendation(self, sentiment: float, critical_events: List[Dict], 
                               symbol_sentiments: Dict[str, float]) -> str:
        """Genera recomendación basada en análisis"""
        
        if critical_events:
            high_urgency = [e for e in critical_events if e["urgency"] >= 4]
            if high_urgency:
                return f"ALERT: {len(high_urgency)} critical events detected. Review positions immediately."
        
        if sentiment >= 0.5:
            return "Market sentiment is very bullish. Consider profit taking on existing positions."
        elif sentiment >= 0.2:
            return "Positive market sentiment. Good environment for entering new positions."
        elif sentiment >= -0.2:
            return "Neutral market sentiment. Standard trading strategy applies."
        elif sentiment >= -0.5:
            return "Negative market sentiment. Be cautious with new positions."
        else:
            return "Very negative sentiment. Consider reducing exposure and defensive positioning."
    
    def _create_neutral_summary(self, symbols: List[str]) -> MarketSentimentSummary:
        """Crear resumen neutral cuando no hay datos"""
        return MarketSentimentSummary(
            overall_sentiment=0.0,
            confidence=0.0,
            symbol_sentiments={symbol: 0.0 for symbol in symbols},
            critical_events=[],
            market_condition="neutral",
            recommendation="No sentiment data available. Use standard trading approach.",
            timestamp=datetime.now()
        )
    
    def get_sentiment_trend(self, symbol: Optional[str] = None, 
                          periods: int = 10) -> Dict:
        """Obtiene tendencia de sentiment"""
        
        if symbol:
            history = list(self.sentiment_history.get(symbol, []))[-periods:]
        else:
            history = list(self.market_sentiment_history)[-periods:]
        
        if len(history) < 2:
            return {"trend": "insufficient_data", "slope": 0.0, "volatility": 0.0}
        
        sentiments = [h["sentiment"] for h in history]
        
        # Calcular tendencia (pendiente simple)
        x = list(range(len(sentiments)))
        slope = np.polyfit(x, sentiments, 1)[0] if len(sentiments) > 1 else 0.0
        
        # Calcular volatilidad
        volatility = np.std(sentiments) if len(sentiments) > 1 else 0.0
        
        # Determinar tendencia
        if slope > 0.1:
            trend = "improving"
        elif slope < -0.1:
            trend = "deteriorating"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "slope": float(slope),
            "volatility": float(volatility),
            "current": sentiments[-1],
            "previous": sentiments[-2] if len(sentiments) > 1 else sentiments[-1]
        }

# Instancias globales
ai_sentiment_analyzer = AISentimentAnalyzer()
market_sentiment_aggregator = MarketSentimentAggregator()

# Funciones de conveniencia
async def analyze_news_sentiment(articles: List[NewsArticle], 
                               symbols: List[str] = None) -> MarketSentimentSummary:
    """
    🎯 Función principal para análisis de sentiment de noticias
    """
    # Análizar sentiment de artículos
    sentiment_results = await ai_sentiment_analyzer.analyze_batch_sentiment(articles, symbols)
    
    # Agregar sentiment del mercado
    market_summary = market_sentiment_aggregator.aggregate_sentiment(sentiment_results, symbols or [])
    
    logger.info(f"📊 Sentiment del mercado: {market_summary.overall_sentiment:.3f} ({market_summary.market_condition})")
    
    return market_summary

def get_sentiment_stats() -> Dict:
    """Obtener estadísticas de análisis de sentiment"""
    return {
        "analyzer_stats": ai_sentiment_analyzer.stats,
        "cache_size": len(ai_sentiment_analyzer.analysis_cache),
        "symbol_history_count": len(market_sentiment_aggregator.sentiment_history),
        "market_history_length": len(market_sentiment_aggregator.market_sentiment_history)
    }

if __name__ == "__main__":
    # Test del sistema
    async def test_sentiment_analyzer():
        from .advanced_news_engine import get_latest_news
        
        logger.info("🧪 Testing AI Sentiment Analyzer...")
        
        # Obtener noticias de prueba
        test_symbols = ["BTC/USD", "ETH/USD", "AAPL", "TSLA"]
        articles = await get_latest_news(test_symbols, 10)
        
        if articles:
            # Analizar sentiment
            summary = await analyze_news_sentiment(articles, test_symbols)
            
            print(f"\n✅ Análisis completado:")
            print(f"Sentiment general: {summary.overall_sentiment:.3f}")
            print(f"Condición del mercado: {summary.market_condition}")
            print(f"Confianza: {summary.confidence:.3f}")
            print(f"Eventos críticos: {len(summary.critical_events)}")
            print(f"Recomendación: {summary.recommendation}")
            
            # Mostrar sentiment por símbolo
            print(f"\nSentiment por símbolo:")
            for symbol, sentiment in summary.symbol_sentiments.items():
                print(f"  {symbol}: {sentiment:.3f}")
        else:
            print("❌ No se pudieron obtener noticias para testing")
    
    asyncio.run(test_sentiment_analyzer())