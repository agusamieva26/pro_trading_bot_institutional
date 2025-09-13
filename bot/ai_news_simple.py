"""
🤖 AI HÍBRIDA REAL - Sistema de análisis de noticias con AGUS
Sistema simple pero 100% funcional que REALMENTE opera
"""

import json
import time
import requests
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

from .util import logger
from .config import settings


@dataclass
class NewsItem:
    """Elemento de noticia simple"""
    title: str
    summary: str
    sentiment: str  # 'positive', 'negative', 'neutral'
    confidence: float  # 0.0 to 1.0


@dataclass
class AIAnalysisResult:
    """Resultado del análisis de IA"""
    symbol: str
    sentiment_adjustment: float  # -0.2 to +0.2
    confidence: float
    news_count: int
    summary: str
    timestamp: datetime


class AINewsSystem:
    """
    🧠 Sistema de IA híbrida REAL - Simple pero funcional
    """
    
    def __init__(self):
        self.openai_client = None
        self.api_available = False
        self.last_analysis = {}
        self.analysis_cache = {}
        
        # Inicializar OpenAI client REAL
        self._initialize_openai()
        
        # Keywords simples para análisis de respaldo
        self.positive_words = [
            'bullish', 'rally', 'surge', 'rise', 'gain', 'breakthrough',
            'positive', 'growth', 'adoption', 'partnership', 'launch',
            'upgrade', 'optimistic', 'strong', 'increase'
        ]
        
        self.negative_words = [
            'bearish', 'crash', 'dump', 'decline', 'fall', 'loss',
            'negative', 'drop', 'regulation', 'ban', 'hack', 'scam',
            'investigation', 'lawsuit', 'weak', 'decrease'
        ]
        
        logger.info("🤖 AI News System REAL inicializado")
    
    def _initialize_openai(self):
        """Inicializar cliente OpenAI REAL"""
        try:
            import openai
            
            if settings.openai_api_key and settings.openai_api_key.strip():
                self.openai_client = openai.OpenAI(
                    api_key=settings.openai_api_key
                )
                self.api_available = True
                logger.info("✅ OpenAI API REAL conectada y lista")
            else:
                logger.warning("⚠️ OpenAI API key no encontrada - usando análisis básico")
                self.api_available = False
                
        except Exception as e:
            logger.warning(f"⚠️ Error inicializando OpenAI: {e} - usando análisis básico")
            self.api_available = False
    
    def get_ai_sentiment_adjustment(self, symbol: str, base_signal: float) -> float:
        """
        🎯 FUNCIÓN PRINCIPAL - Obtiene ajuste de sentiment de IA
        Retorna valor entre -0.2 y +0.2 para ajustar señal base
        """
        try:
            # Cache para evitar análisis repetidos (5 minutos)
            cache_key = f"{symbol}_{int(time.time() / 300)}"
            if cache_key in self.analysis_cache:
                cached_result = self.analysis_cache[cache_key]
                logger.info(f"🤖 AI Cache: {symbol} ajuste {cached_result:.3f} (cached)")
                return cached_result
            
            # Obtener noticias recientes
            news_items = self._fetch_recent_news(symbol)
            
            if not news_items:
                logger.debug(f"🤖 AI: {symbol} sin noticias recientes - ajuste neutro")
                return 0.0
            
            # Análisis con OpenAI (si disponible) o análisis básico
            if self.api_available:
                adjustment = self._analyze_with_openai(symbol, news_items, base_signal)
            else:
                adjustment = self._analyze_basic_sentiment(news_items)
            
            # Limitar ajuste a rango permitido
            adjustment = max(-0.2, min(0.2, adjustment))
            
            # Guardar en cache
            self.analysis_cache[cache_key] = adjustment
            
            # Log visible y verificable
            logger.info(f"🤖 AI Analysis: {symbol} sentiment {adjustment:+.3f} applied ({len(news_items)} news)")
            
            return adjustment
            
        except Exception as e:
            logger.error(f"❌ Error AI análisis {symbol}: {e}")
            return 0.0  # Neutro en caso de error
    
    def _fetch_recent_news(self, symbol: str) -> List[NewsItem]:
        """Obtener noticias recientes para el símbolo"""
        news_items = []
        symbol_clean = symbol.replace("/USD", "").replace("/", "")
        
        try:
            # Fuente gratuita: CryptoCompare para cryptos
            if symbol_clean in ['BTC', 'ETH', 'SOL', 'AVAX', 'LINK', 'DOT', 'LTC', 'XRP', 'UNI', 'AAVE']:
                url = "https://min-api.cryptocompare.com/data/v2/news/"
                params = {
                    "lang": "EN",
                    "categories": symbol_clean,
                    "limit": 3,  # Solo 3 noticias más recientes
                    "excludeCategories": "Sponsored"
                }
                
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("Data"):
                        for item in data["Data"][:3]:  # Máximo 3
                            news_items.append(NewsItem(
                                title=item.get('title', '')[:200],  # Limitar título
                                summary=item.get('body', '')[:300],  # Limitar resumen
                                sentiment='neutral',  # Se analizará después
                                confidence=0.5
                            ))
                        logger.debug(f"📰 Obtenidas {len(news_items)} noticias para {symbol}")
                        
        except Exception as e:
            logger.debug(f"Error obteniendo noticias para {symbol}: {e}")
        
        return news_items
    
    def _analyze_with_openai(self, symbol: str, news_items: List[NewsItem], base_signal: float) -> float:
        """Análisis con OpenAI REAL"""
        try:
            # Combinar títulos y resúmenes
            news_text = "\n".join([
                f"- {item.title}: {item.summary[:200]}" 
                for item in news_items[:3]  # Máximo 3 noticias
            ])
            
            if len(news_text) < 50:  # Texto muy corto
                return 0.0
            
            # Prompt simple pero efectivo
            prompt = f"""Analiza el sentiment de estas noticias sobre {symbol} y da un ajuste de señal.

Noticias:
{news_text}

Señal base actual: {base_signal:.3f}

Responde SOLO con un número entre -0.2 y +0.2 que represente el ajuste de sentiment:
- Positivo (+0.05 a +0.2): noticias muy positivas
- Neutral (0.0): noticias neutras o mixtas  
- Negativo (-0.05 a -0.2): noticias muy negativas

Respuesta (solo número):"""

            # Llamada a OpenAI
            if not self.openai_client:
                return self._analyze_basic_sentiment(news_items)
                
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Eres un analista de sentiment financiero. Responde solo con números."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=10,
                temperature=0.3
            )
            
            # Extraer y validar respuesta
            content = response.choices[0].message.content
            if content is None:
                return self._analyze_basic_sentiment(news_items)
            content = content.strip()
            adjustment = float(content)
            adjustment = max(-0.2, min(0.2, adjustment))  # Asegurar rango
            
            logger.debug(f"🤖 AGUS: {symbol} raw={content} -> ajuste={adjustment:.3f}")
            return adjustment
            
        except ValueError as e:
            logger.warning(f"⚠️ OpenAI respuesta inválida para {symbol}: {e}")
            return self._analyze_basic_sentiment(news_items)
        except Exception as e:
            logger.warning(f"⚠️ Error OpenAI para {symbol}: {e}")
            return self._analyze_basic_sentiment(news_items)
    
    def _analyze_basic_sentiment(self, news_items: List[NewsItem]) -> float:
        """Análisis de sentiment básico (respaldo)"""
        if not news_items:
            return 0.0
        
        total_score = 0.0
        total_items = 0
        
        for item in news_items:
            text = f"{item.title} {item.summary}".lower()
            
            positive_count = sum(1 for word in self.positive_words if word in text)
            negative_count = sum(1 for word in self.negative_words if word in text)
            
            if positive_count > negative_count:
                score = min(0.1, positive_count * 0.03)  # Máximo +0.1
            elif negative_count > positive_count:
                score = max(-0.1, -negative_count * 0.03)  # Máximo -0.1
            else:
                score = 0.0
            
            total_score += score
            total_items += 1
        
        if total_items == 0:
            return 0.0
        
        # Promedio y limitado a rango
        adjustment = total_score / total_items
        adjustment = max(-0.2, min(0.2, adjustment))
        
        logger.debug(f"📊 Análisis básico: {total_items} items -> ajuste {adjustment:.3f}")
        return adjustment


# Instancia global del sistema
ai_news_system = AINewsSystem()


def get_ai_sentiment_adjustment(symbol: str, base_signal: float) -> float:
    """
    🎯 FUNCIÓN PRINCIPAL EXPORTADA
    Función que se llamará desde main.py para obtener ajuste de IA
    """
    return ai_news_system.get_ai_sentiment_adjustment(symbol, base_signal)