"""
🚀 AI TRADING SYSTEM - IMPLEMENTACIÓN REAL Y FUNCIONAL
Sistema simplificado de IA para trading que REALMENTE funciona
"""

import time
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
warnings.filterwarnings('ignore')

from .util import logger
from .config import settings

@dataclass
class AIAnalysisResult:
    """Resultado de análisis de IA simplificado"""
    symbol: str
    sentiment_score: float  # -1.0 a 1.0
    confidence: float      # 0.0 a 1.0
    news_count: int
    critical_events: List[str]
    recommendation: str
    signal_adjustment: float  # Factor de ajuste para señal original
    timestamp: datetime
    
class SimplifiedAIEngine:
    """
    🧠 Motor de IA simplificado que REALMENTE funciona
    """
    
    def __init__(self):
        self.last_analysis_time = 0
        self.analysis_interval = 300  # 5 minutos
        self.analysis_cache = {}
        self.executor = ThreadPoolExecutor(max_workers=3)
        
        # APIs gratuitas para noticias
        self.news_sources = [
            {
                "name": "CryptoNews API",
                "url": "https://min-api.cryptocompare.com/data/v2/news/",
                "params": {"lang": "EN", "limit": 20}
            },
            {
                "name": "Alpha Vantage News",
                "url": "https://www.alphavantage.co/query",
                "api_key": getattr(settings, 'alpha_vantage_api_key', ''),
                "enabled": hasattr(settings, 'alpha_vantage_api_key') and getattr(settings, 'alpha_vantage_api_key', '')
            }
        ]
        
        # AGUS client (modelo REAL)
        try:
            from openai import OpenAI
            self.openai_client = OpenAI(api_key=getattr(settings, 'openai_api_key', ''))
            self.agus_available = bool(getattr(settings, 'openai_api_key', ''))
            logger.info("🤖 AGUS client inicializado correctamente")
        except Exception as e:
            self.openai_client = None
            self.agus_available = False
            logger.warning(f"⚠️ AGUS no disponible: {e}")
        
        # Keywords para sentiment básico
        self.positive_keywords = [
            'bullish', 'rally', 'surge', 'breakthrough', 'positive', 'gains',
            'up', 'rise', 'growth', 'adoption', 'partnership', 'launch'
        ]
        
        self.negative_keywords = [
            'bearish', 'crash', 'dump', 'decline', 'negative', 'losses',
            'down', 'fall', 'drop', 'regulation', 'ban', 'hack', 'scam'
        ]
        
        self.critical_keywords = [
            'bankruptcy', 'fraud', 'investigation', 'lawsuit', 'hack',
            'security breach', 'delisted', 'suspended', 'emergency'
        ]
        
        logger.info("🚀 AI Engine Simplificado inicializado")
    
    def analyze_market_sentiment(self, symbols: List[str]) -> Dict[str, AIAnalysisResult]:
        """
        🔍 Análisis principal de sentiment del mercado
        FUNCIÓN REAL que se ejecuta y es visible en logs
        """
        current_time = time.time()
        
        # Cache para evitar análisis repetidos
        if (current_time - self.last_analysis_time < self.analysis_interval and 
            self.analysis_cache):
            logger.debug("📋 Usando análisis AI reciente del cache")
            return self.analysis_cache
        
        logger.info(f"🧠 INICIANDO ANÁLISIS AI REAL para {len(symbols)} símbolos...")
        start_time = time.time()
        
        results = {}
        news_fetched = 0
        
        # Análisis en paralelo para mejor rendimiento
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_symbol = {
                executor.submit(self._analyze_symbol, symbol): symbol 
                for symbol in symbols[:5]  # Límite de 5 símbolos para eficiencia
            }
            
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    result = future.result(timeout=30)
                    if result:
                        results[symbol] = result
                        news_fetched += result.news_count
                        logger.info(f"✅ AI análisis {symbol}: sentiment={result.sentiment_score:.3f}, "
                                  f"confianza={result.confidence:.3f}, noticias={result.news_count}")
                except Exception as e:
                    logger.error(f"❌ Error AI análisis {symbol}: {e}")
        
        # Actualizar cache
        self.analysis_cache = results
        self.last_analysis_time = current_time
        
        analysis_time = time.time() - start_time
        logger.info(f"🎯 ANÁLISIS AI COMPLETADO: {len(results)} símbolos, "
                   f"{news_fetched} noticias, {analysis_time:.2f}s")
        
        return results
    
    def _analyze_symbol(self, symbol: str) -> Optional[AIAnalysisResult]:
        """Análisis de un símbolo específico"""
        try:
            # 1. Obtener noticias del símbolo
            news_data = self._fetch_symbol_news(symbol)
            
            if not news_data:
                logger.debug(f"📰 Sin noticias para {symbol}")
                return None
            
            # 2. Analizar sentiment
            sentiment_score, confidence = self._analyze_news_sentiment(news_data, symbol)
            
            # 3. Detectar eventos críticos
            critical_events = self._detect_critical_events(news_data)
            
            # 4. Generar recomendación
            recommendation = self._generate_recommendation(sentiment_score, critical_events)
            
            # 5. Calcular ajuste de señal
            signal_adjustment = self._calculate_signal_adjustment(sentiment_score, confidence, critical_events)
            
            return AIAnalysisResult(
                symbol=symbol,
                sentiment_score=sentiment_score,
                confidence=confidence,
                news_count=len(news_data),
                critical_events=critical_events,
                recommendation=recommendation,
                signal_adjustment=signal_adjustment,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"❌ Error analizando {symbol}: {e}")
            return None
    
    def _fetch_symbol_news(self, symbol: str) -> List[Dict]:
        """Obtiene noticias para un símbolo"""
        all_news = []
        symbol_clean = symbol.replace("/USD", "").replace("/", "")
        
        # Fuente 1: CryptoCompare (gratuita)
        try:
            if symbol_clean in ['BTC', 'ETH', 'LTC', 'XRP', 'ADA', 'DOT', 'SOL', 'AVAX']:
                url = "https://min-api.cryptocompare.com/data/v2/news/"
                params = {
                    "lang": "EN",
                    "categories": f"{symbol_clean}",
                    "excludeCategories": "Sponsored",
                    "limit": 15
                }
                
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("Data"):
                        news_items = data["Data"][:10]  # Máximo 10 noticias
                        for item in news_items:
                            all_news.append({
                                'title': item.get('title', ''),
                                'body': item.get('body', '')[:500],  # Limitar texto
                                'source': 'CryptoCompare',
                                'published': item.get('published_on', time.time())
                            })
                        logger.debug(f"📰 CryptoCompare: {len(news_items)} noticias para {symbol}")
                        
        except Exception as e:
            logger.debug(f"Error CryptoCompare para {symbol}: {e}")
        
        # Fuente 2: Alpha Vantage (si disponible)
        if (hasattr(settings, 'alpha_vantage_api_key') and 
            getattr(settings, 'alpha_vantage_api_key', '') and 
            len(all_news) < 5):
            try:
                url = "https://www.alphavantage.co/query"
                params = {
                    "function": "NEWS_SENTIMENT",
                    "tickers": symbol_clean,
                    "apikey": getattr(settings, 'alpha_vantage_api_key', ''),
                    "limit": 10
                }
                
                response = requests.get(url, params=params, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("feed"):
                        for item in data["feed"][:5]:
                            all_news.append({
                                'title': item.get('title', ''),
                                'body': item.get('summary', '')[:500],
                                'source': 'Alpha Vantage',
                                'published': time.time()
                            })
                        logger.debug(f"📰 Alpha Vantage: {len(data['feed'])} noticias para {symbol}")
                        
            except Exception as e:
                logger.debug(f"Error Alpha Vantage para {symbol}: {e}")
        
        return all_news
    
    def _analyze_news_sentiment(self, news_data: List[Dict], symbol: str) -> Tuple[float, float]:
        """Analiza sentiment de las noticias"""
        if not news_data:
            return 0.0, 0.0
        
        # Combinar todo el texto
        all_text = " ".join([f"{item['title']} {item['body']}" for item in news_data]).lower()
        
        # Método 1: OpenAI (si disponible)
        if self.agus_available and len(all_text) > 100:
            try:
                sentiment_score, confidence = self._agus_sentiment_analysis(all_text, symbol)
                if confidence > 0.5:
                    logger.debug(f"🤖 OpenAI sentiment {symbol}: {sentiment_score:.3f}")
                    return sentiment_score, confidence
            except Exception as e:
                logger.debug(f"Error OpenAI sentiment: {e}")
        
        # Método 2: Análisis por keywords (fallback)
        sentiment_score, confidence = self._keyword_sentiment_analysis(all_text)
        logger.debug(f"📝 Keyword sentiment {symbol}: {sentiment_score:.3f}")
        
        return sentiment_score, confidence
    
    def _agus_sentiment_analysis(self, text: str, symbol: str) -> Tuple[float, float]:
        """Análisis de sentiment usando OpenAI"""
        try:
            prompt = f"""Analyze the sentiment of this financial news about {symbol}.
Return only a JSON with:
{{"sentiment_score": number between -1.0 (very bearish) and 1.0 (very bullish), "confidence": number between 0.0 and 1.0}}

News text: {text[:1500]}"""
            
            if not self.openai_client:
                return 0.0, 0.0
                
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # MODELO REAL
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.3
            )
            
            result_text = (response.choices[0].message.content or '').strip()
            
            # Parsear JSON
            if result_text.startswith('{') and result_text.endswith('}'):
                result = json.loads(result_text)
                sentiment = float(result.get('sentiment_score', 0.0))
                confidence = float(result.get('confidence', 0.0))
                
                # Validar rangos
                sentiment = max(-1.0, min(1.0, sentiment))
                confidence = max(0.0, min(1.0, confidence))
                
                return sentiment, confidence
                
        except Exception as e:
            logger.debug(f"Error OpenAI API: {e}")
        
        return 0.0, 0.0
    
    def _keyword_sentiment_analysis(self, text: str) -> Tuple[float, float]:
        """Análisis básico por keywords"""
        positive_count = sum(1 for word in self.positive_keywords if word in text)
        negative_count = sum(1 for word in self.negative_keywords if word in text)
        total_keywords = positive_count + negative_count
        
        if total_keywords == 0:
            return 0.0, 0.1
        
        sentiment_score = (positive_count - negative_count) / max(total_keywords, 1)
        confidence = min(total_keywords / 10.0, 1.0)  # Máximo confianza con 10+ keywords
        
        return sentiment_score, confidence
    
    def _detect_critical_events(self, news_data: List[Dict]) -> List[str]:
        """Detecta eventos críticos en las noticias"""
        critical_events = []
        all_text = " ".join([f"{item['title']} {item['body']}" for item in news_data]).lower()
        
        for keyword in self.critical_keywords:
            if keyword in all_text:
                critical_events.append(keyword)
        
        return critical_events
    
    def _generate_recommendation(self, sentiment_score: float, critical_events: List[str]) -> str:
        """Genera recomendación basada en análisis"""
        if critical_events:
            return f"⚠️ CRITICAL: {', '.join(critical_events[:2])}"
        
        if sentiment_score >= 0.5:
            return "🟢 POSITIVE: Strong bullish sentiment"
        elif sentiment_score >= 0.2:
            return "🔵 MODERATE: Mild positive sentiment"
        elif sentiment_score <= -0.5:
            return "🔴 NEGATIVE: Strong bearish sentiment"
        elif sentiment_score <= -0.2:
            return "🟠 CAUTION: Mild negative sentiment"
        else:
            return "⚪ NEUTRAL: Mixed sentiment"
    
    def _calculate_signal_adjustment(self, sentiment_score: float, confidence: float, critical_events: List[str]) -> float:
        """Calcula factor de ajuste para la señal de trading"""
        if critical_events:
            return 0.1  # Reducir señal drásticamente si hay eventos críticos
        
        # Factor base del sentiment
        base_adjustment = 1.0 + (sentiment_score * 0.3)  # ±30% máximo
        
        # Ajustar por confianza
        confidence_factor = 0.7 + (confidence * 0.3)  # 70-100%
        
        final_adjustment = base_adjustment * confidence_factor
        
        # Límites de seguridad
        return max(0.1, min(1.9, final_adjustment))
    
    def get_ai_signal_adjustment(self, symbol: str, original_signal: float) -> Tuple[float, str]:
        """
        🎯 FUNCIÓN PRINCIPAL: Obtiene ajuste de IA para señal de trading
        Esta función es llamada desde main.py
        """
        try:
            # Obtener análisis reciente
            analysis_results = self.analyze_market_sentiment([symbol])
            
            if symbol not in analysis_results:
                logger.debug(f"📊 Sin análisis AI disponible para {symbol}")
                return original_signal, "No AI data available"
            
            ai_result = analysis_results[symbol]
            
            # Aplicar ajuste
            adjusted_signal = original_signal * ai_result.signal_adjustment
            
            # Log visible
            logger.info(f"🧠 AI AJUSTE {symbol}: "
                       f"Original={original_signal:.3f} → Ajustado={adjusted_signal:.3f} "
                       f"(factor={ai_result.signal_adjustment:.3f}, "
                       f"sentiment={ai_result.sentiment_score:.3f})")
            
            return adjusted_signal, ai_result.recommendation
            
        except Exception as e:
            logger.error(f"❌ Error AI adjustment para {symbol}: {e}")
            return original_signal, "AI Error"

# Instancia global
ai_engine = SimplifiedAIEngine()

def get_ai_adjusted_signal(symbol: str, original_signal: float) -> Tuple[float, str]:
    """
    🎯 FUNCIÓN PRINCIPAL EXPORTADA para main.py
    """
    return ai_engine.get_ai_signal_adjustment(symbol, original_signal)

def force_ai_analysis(symbols: List[str]) -> Dict[str, AIAnalysisResult]:
    """
    🔍 Fuerza análisis completo de AI (para debugging)
    """
    ai_engine.last_analysis_time = 0  # Reset cache
    return ai_engine.analyze_market_sentiment(symbols)

def get_ai_system_status() -> Dict:
    """
    📊 Estado del sistema AI
    """
    return {
        "initialized": True,
        "agus_available": ai_engine.agus_available,
        "last_analysis": ai_engine.last_analysis_time,
        "cache_symbols": list(ai_engine.analysis_cache.keys()),
        "news_sources": len(ai_engine.news_sources)
    }