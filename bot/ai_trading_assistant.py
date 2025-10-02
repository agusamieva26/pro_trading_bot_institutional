"""
🧠 IA PERSONAL DE TRADING - TU ASISTENTE INTELIGENTE
Combina análisis de noticias, sentiment y ML para generar insights de trading
Integración con blueprint:python_openai y blueprint:web_scraper
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from loguru import logger
import asyncio
import concurrent.futures
from dataclasses import dataclass

from openai import OpenAI
import trafilatura

@dataclass
class MarketSignal:
    """Señal de trading generada por la IA"""
    symbol: str
    action: str  # BUY, SELL, HOLD
    confidence: float  # 0.0 - 1.0
    reasoning: str
    news_sentiment: float  # -1.0 (very negative) to 1.0 (very positive)
    technical_score: float
    timestamp: datetime
    price_target: Optional[float] = None
    stop_loss: Optional[float] = None

class AITradingAssistant:
    """
    🤖 IA Personal de Trading
    - Análisis de noticias en tiempo real
    - Generación de señales inteligentes
    - Evaluación de sentiment del mercado
    - Integración con el bot de trading
    """
    
    def __init__(self):
        self.openai_client = None
        self.news_sources = [
            "https://www.coindesk.com/",
            "https://cointelegraph.com/",
            "https://www.investing.com/news/cryptocurrency-news",
            "https://finance.yahoo.com/news/",
            "https://www.marketwatch.com/",
            "https://www.bloomberg.com/crypto"
        ]
        
        # Inicializar OpenAI
        try:
            api_key = os.environ.get("OPENAI_API_KEY")
            if api_key:
                self.openai_client = OpenAI(api_key=api_key)
                logger.info("🧠 IA Personal inicializada con OpenAI")
            else:
                logger.warning("⚠️ OPENAI_API_KEY no configurado - funciones de IA limitadas")
        except Exception as e:
            logger.error(f"❌ Error inicializando OpenAI: {e}")
    
    async def get_market_news(self, symbols: List[str], max_articles: int = 10) -> List[Dict]:
        """
        🗞️ Obtiene noticias relevantes para los símbolos de trading
        """
        logger.info(f"📰 Obteniendo noticias para {len(symbols)} símbolos...")
        
        all_news = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            
            for source in self.news_sources[:3]:  # Limitar a 3 fuentes por velocidad
                future = executor.submit(self._scrape_news_source, source)
                futures.append(future)
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    source_news = future.result(timeout=10)
                    if source_news:
                        all_news.extend(source_news)
                except Exception as e:
                    logger.warning(f"⚠️ Error obteniendo noticias: {e}")
        
        # Filtrar noticias relevantes para los símbolos
        relevant_news = self._filter_relevant_news(all_news, symbols)
        
        logger.info(f"📊 Obtenidas {len(relevant_news)} noticias relevantes")
        return relevant_news[:max_articles]
    
    def _scrape_news_source(self, url: str) -> List[str]:
        """Extrae contenido de una fuente de noticias"""
        try:
            # Usar trafilatura del blueprint web_scraper
            content = trafilatura.fetch_url(url)
            text = trafilatura.extract(content)
            
            if text and len(text) > 100:
                # Dividir en artículos (simplificado)
                articles = [text[i:i+1000] for i in range(0, len(text), 1000)]
                return articles[:3]  # Máximo 3 artículos por fuente
                
        except Exception as e:
            logger.debug(f"Error scraping {url}: {e}")
        
        return []
    
    def _filter_relevant_news(self, all_news: List[str], symbols: List[str]) -> List[str]:
        """Filtra noticias relevantes para los símbolos"""
        relevant = []
        
        # Keywords por tipo de activo
        crypto_keywords = ["bitcoin", "btc", "ethereum", "eth", "crypto", "blockchain", "defi"]
        stock_keywords = ["stock", "equity", "nasdaq", "s&p", "dow", "market", "earnings"]
        
        for article in all_news:
            article_lower = article.lower()
            
            # Buscar símbolos específicos
            for symbol in symbols:
                symbol_clean = symbol.replace("/USD", "").replace("/", "").lower()
                if symbol_clean in article_lower:
                    relevant.append(article)
                    break
            
            # Buscar keywords generales
            if any(keyword in article_lower for keyword in crypto_keywords + stock_keywords):
                if len(relevant) < 15:  # Limitar cantidad
                    relevant.append(article)
        
        return relevant
    
    async def analyze_news_sentiment(self, news_articles: List[str]) -> Dict:
        """
        📊 Analiza el sentiment de las noticias usando GPT-5
        """
        if not self.openai_client or not news_articles:
            return {"overall_sentiment": 0.0, "confidence": 0.0, "summary": "No analysis available"}
        
        try:
            # Combinar artículos para análisis
            combined_text = " ".join(news_articles)[:4000]  # Limitar tokens
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert financial news analyst. Analyze the sentiment of crypto and stock market news. Respond with JSON containing: overall_sentiment (-1.0 to 1.0), confidence (0.0 to 1.0), key_insights (list), and summary (string)."
                    },
                    {
                        "role": "user", 
                        "content": f"Analyze the market sentiment of this news content:\n\n{combined_text}"
                    }
                ],
                response_format={"type": "json_object"},
                max_tokens=500
            )
            
            result = json.loads(response.choices[0].message.content)
            logger.info(f"📊 Sentiment analizado: {result['overall_sentiment']:.2f} (confianza: {result['confidence']:.2f})")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error analizando sentiment: {e}")
            return {"overall_sentiment": 0.0, "confidence": 0.0, "summary": f"Analysis error: {e}"}
    
    async def generate_trading_signals(self, symbols: List[str], market_data: Dict, news_sentiment: Dict) -> List[MarketSignal]:
        """
        🎯 Genera señales de trading inteligentes combinando noticias + datos técnicos
        """
        if not self.openai_client:
            logger.warning("⚠️ OpenAI no disponible - señales limitadas")
            return []
        
        signals = []
        
        for symbol in symbols[:5]:  # Procesar máximo 5 símbolos por velocidad
            try:
                signal = await self._generate_symbol_signal(symbol, market_data.get(symbol, {}), news_sentiment)
                if signal:
                    signals.append(signal)
            except Exception as e:
                logger.debug(f"Error generando señal para {symbol}: {e}")
        
        # Ordenar por confianza
        signals.sort(key=lambda x: x.confidence, reverse=True)
        
        logger.info(f"🎯 Generadas {len(signals)} señales IA")
        return signals
    
    async def _generate_symbol_signal(self, symbol: str, tech_data: Dict, sentiment: Dict) -> Optional[MarketSignal]:
        """Genera señal para un símbolo específico"""
        try:
            # Preparar contexto para GPT-5
            context = f"""
            Symbol: {symbol}
            Technical Data: {json.dumps(tech_data, indent=2)}
            Market Sentiment: {sentiment.get('overall_sentiment', 0.0):.2f}
            News Summary: {sentiment.get('summary', 'No news available')}
            
            Generate a trading signal considering:
            1. Technical indicators if available
            2. Market sentiment from news
            3. Risk management principles
            4. Current market conditions
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert trader AI. Generate trading signals in JSON format with: action (BUY/SELL/HOLD), confidence (0.0-1.0), reasoning (string), technical_score (0.0-1.0), price_target (optional), stop_loss (optional)."
                    },
                    {"role": "user", "content": context}
                ],
                response_format={"type": "json_object"},
                max_tokens=300
            )
            
            ai_signal = json.loads(response.choices[0].message.content)
            
            # Crear MarketSignal
            signal = MarketSignal(
                symbol=symbol,
                action=ai_signal.get("action", "HOLD"),
                confidence=min(1.0, max(0.0, ai_signal.get("confidence", 0.5))),
                reasoning=ai_signal.get("reasoning", "AI analysis"),
                news_sentiment=sentiment.get("overall_sentiment", 0.0),
                technical_score=ai_signal.get("technical_score", 0.5),
                timestamp=datetime.now(),
                price_target=ai_signal.get("price_target"),
                stop_loss=ai_signal.get("stop_loss")
            )
            
            return signal
            
        except Exception as e:
            logger.debug(f"Error en señal IA para {symbol}: {e}")
            return None
    
    def get_market_summary(self, signals: List[MarketSignal], sentiment: Dict) -> str:
        """
        📋 Genera un resumen inteligente del mercado
        """
        if not signals:
            return "🤖 Sin señales IA disponibles"
        
        # Contar acciones
        buy_signals = len([s for s in signals if s.action == "BUY"])
        sell_signals = len([s for s in signals if s.action == "SELL"])
        hold_signals = len([s for s in signals if s.action == "HOLD"])
        
        # Confianza promedio
        avg_confidence = sum(s.confidence for s in signals) / len(signals)
        
        # Sentiment general
        sentiment_score = sentiment.get("overall_sentiment", 0.0)
        sentiment_text = "Positivo" if sentiment_score > 0.2 else "Negativo" if sentiment_score < -0.2 else "Neutral"
        
        summary = f"""
🧠 IA PERSONAL - RESUMEN DE MERCADO

📊 Señales Generadas: {len(signals)}
   • 🟢 Comprar: {buy_signals}
   • 🔴 Vender: {sell_signals}  
   • 🟡 Mantener: {hold_signals}

🎯 Confianza Promedio: {avg_confidence:.1%}
📰 Sentiment Noticias: {sentiment_text} ({sentiment_score:+.2f})

🏆 Top Recomendaciones:"""
        
        # Agregar top 3 señales
        for i, signal in enumerate(signals[:3]):
            emoji = "🟢" if signal.action == "BUY" else "🔴" if signal.action == "SELL" else "🟡"
            summary += f"""
   {i+1}. {emoji} {signal.symbol}: {signal.action} ({signal.confidence:.1%})
      {signal.reasoning[:60]}..."""
        
        return summary
    
    async def run_full_analysis(self, symbols: List[str], market_data: Dict = None) -> Tuple[List[MarketSignal], Dict, str]:
        """
        🚀 Ejecuta análisis completo: noticias + señales + resumen
        """
        logger.info("🧠 Iniciando análisis completo de la IA Personal...")
        
        try:
            # 1. Obtener noticias
            news = await self.get_market_news(symbols, max_articles=8)
            
            # 2. Analizar sentiment
            sentiment = await self.analyze_news_sentiment(news)
            
            # 3. Generar señales
            signals = await self.generate_trading_signals(symbols, market_data or {}, sentiment)
            
            # 4. Crear resumen
            summary = self.get_market_summary(signals, sentiment)
            
            logger.info(f"✅ Análisis IA completado: {len(signals)} señales, sentiment {sentiment.get('overall_sentiment', 0):.2f}")
            
            return signals, sentiment, summary
            
        except Exception as e:
            logger.error(f"❌ Error en análisis IA: {e}")
            return [], {"overall_sentiment": 0.0}, f"❌ Error en análisis IA: {e}"

# Instancia global
ai_assistant = AITradingAssistant()

# Función de conveniencia para integrar con el bot principal
async def get_ai_recommendations(symbols: List[str]) -> str:
    """
    🎯 Función principal para obtener recomendaciones de la IA
    Uso: signals, sentiment, summary = await get_ai_recommendations(['BTC/USD', 'ETH/USD'])
    """
    signals, sentiment, summary = await ai_assistant.run_full_analysis(symbols)
    return summary

if __name__ == "__main__":
    # Test básico
    import asyncio
    
    async def test_ai():
        logger.info("🧪 Testing AI Trading Assistant...")
        
        test_symbols = ["BTC/USD", "ETH/USD", "AAPL", "TSLA"]
        summary = await get_ai_recommendations(test_symbols)
        
        print(summary)
    
    asyncio.run(test_ai())