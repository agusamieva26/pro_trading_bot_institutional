"""
🚀 ADVANCED NEWS AGGREGATION ENGINE
Sistema avanzado de análisis de noticias financieras en tiempo real
Integra múltiples fuentes y APIs profesionales con IA para trading
"""

import asyncio
import aiohttp
import json
import re
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import numpy as np
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
import trafilatura

from .util import logger
from .config import settings

@dataclass
class NewsArticle:
    """Artículo de noticias enriquecido con metadata"""
    id: str
    title: str
    content: str
    source: str
    url: str
    published_at: datetime
    symbols: List[str]
    sentiment_score: float = 0.0
    confidence: float = 0.0
    keywords: List[str] = None
    impact_prediction: Dict = None
    price_targets: Dict = None
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.impact_prediction is None:
            self.impact_prediction = {}
        if self.price_targets is None:
            self.price_targets = {}

class NewsAPIIntegrator:
    """
    🔌 Integrador de APIs de noticias profesionales
    Admite Alpha Vantage, Polygon, Finnhub y fuentes web
    """
    
    def __init__(self):
        self.alpha_vantage_key = settings.__dict__.get("alpha_vantage_api_key", "")
        self.polygon_key = settings.__dict__.get("polygon_api_key", "")
        self.finnhub_key = settings.__dict__.get("finnhub_api_key", "")
        
        # Endpoints de APIs
        self.alpha_vantage_base = "https://www.alphavantage.co/query"
        self.polygon_base = "https://api.polygon.io/v2"
        self.finnhub_base = "https://finnhub.io/api/v1"
        
        # Rate limiting
        self.rate_limits = {
            "alpha_vantage": {"calls": 0, "reset_time": time.time()},
            "polygon": {"calls": 0, "reset_time": time.time()},
            "finnhub": {"calls": 0, "reset_time": time.time()},
        }
        
        # Cache para evitar duplicados
        self.news_cache = {}
        self.cache_ttl = 300  # 5 minutos
        
        logger.info("🔌 News API Integrator inicializado")
    
    def _check_rate_limit(self, api_name: str, max_calls: int = 500, window: int = 3600) -> bool:
        """Verifica límites de rate por API"""
        current_time = time.time()
        rate_info = self.rate_limits[api_name]
        
        # Resetear contador si pasó la ventana
        if current_time - rate_info["reset_time"] > window:
            rate_info["calls"] = 0
            rate_info["reset_time"] = current_time
        
        if rate_info["calls"] >= max_calls:
            logger.warning(f"⚠️ Rate limit alcanzado para {api_name}")
            return False
        
        rate_info["calls"] += 1
        return True
    
    async def fetch_alpha_vantage_news(self, symbols: List[str]) -> List[NewsArticle]:
        """🔍 Obtiene noticias de Alpha Vantage"""
        if not self.alpha_vantage_key or not self._check_rate_limit("alpha_vantage"):
            return []
        
        articles = []
        
        try:
            # Alpha Vantage News Sentiment endpoint
            params = {
                "function": "NEWS_SENTIMENT",
                "tickers": ",".join(symbols[:10]),  # Máximo 10 symbols
                "apikey": self.alpha_vantage_key,
                "limit": 200
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.alpha_vantage_base, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if "feed" in data:
                            for item in data["feed"][:50]:  # Limitar a 50 artículos
                                try:
                                    article = self._parse_alpha_vantage_article(item, symbols)
                                    if article:
                                        articles.append(article)
                                except Exception as e:
                                    logger.debug(f"Error procesando artículo Alpha Vantage: {e}")
                        
            logger.info(f"📰 Alpha Vantage: {len(articles)} artículos obtenidos")
            
        except Exception as e:
            logger.error(f"❌ Error Alpha Vantage News: {e}")
        
        return articles
    
    def _parse_alpha_vantage_article(self, item: Dict, symbols: List[str]) -> Optional[NewsArticle]:
        """Parsea artículo de Alpha Vantage"""
        try:
            # Crear ID único
            article_id = hashlib.md5(f"{item.get('url', '')}{item.get('time_published', '')}".encode()).hexdigest()
            
            # Filtrar símbolos relevantes
            article_symbols = []
            ticker_sentiment = item.get("ticker_sentiment", [])
            
            for ticker_data in ticker_sentiment:
                ticker = ticker_data.get("ticker", "")
                if any(symbol.replace("/USD", "").replace("/", "") == ticker for symbol in symbols):
                    article_symbols.append(ticker)
            
            if not article_symbols and not any(symbol.replace("/USD", "").replace("/", "").lower() in item.get("title", "").lower() for symbol in symbols):
                return None
            
            # Crear artículo
            article = NewsArticle(
                id=article_id,
                title=item.get("title", ""),
                content=item.get("summary", ""),
                source="Alpha Vantage",
                url=item.get("url", ""),
                published_at=self._parse_alpha_vantage_datetime(item.get("time_published", "")),
                symbols=article_symbols or symbols,
                sentiment_score=float(item.get("overall_sentiment_score", 0.0)),
                confidence=0.8  # Alpha Vantage es bastante confiable
            )
            
            return article
            
        except Exception as e:
            logger.debug(f"Error parseando Alpha Vantage: {e}")
            return None
    
    def _parse_alpha_vantage_datetime(self, time_str: str) -> datetime:
        """Parsea datetime de Alpha Vantage format: 20240913T143000"""
        try:
            return datetime.strptime(time_str, "%Y%m%dT%H%M%S")
        except:
            return datetime.now()
    
    async def fetch_polygon_news(self, symbols: List[str]) -> List[NewsArticle]:
        """🔍 Obtiene noticias de Polygon.io"""
        if not self.polygon_key or not self._check_rate_limit("polygon"):
            return []
        
        articles = []
        
        try:
            # Polygon News API
            headers = {"Authorization": f"Bearer {self.polygon_key}"}
            
            # Convertir símbolos a formato Polygon
            polygon_symbols = [symbol.replace("/USD", "").replace("/", "") for symbol in symbols]
            
            for symbol in polygon_symbols[:5]:  # Procesar máximo 5 símbolos
                params = {
                    "ticker": symbol,
                    "limit": 20,
                    "order": "desc"
                }
                
                url = f"{self.polygon_base}/reference/news"
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            if "results" in data:
                                for item in data["results"]:
                                    try:
                                        article = self._parse_polygon_article(item, [symbol])
                                        if article:
                                            articles.append(article)
                                    except Exception as e:
                                        logger.debug(f"Error procesando artículo Polygon: {e}")
                
                await asyncio.sleep(0.1)  # Rate limiting
            
            logger.info(f"📰 Polygon: {len(articles)} artículos obtenidos")
            
        except Exception as e:
            logger.error(f"❌ Error Polygon News: {e}")
        
        return articles
    
    def _parse_polygon_article(self, item: Dict, symbols: List[str]) -> Optional[NewsArticle]:
        """Parsea artículo de Polygon"""
        try:
            article_id = hashlib.md5(f"{item.get('article_url', '')}{item.get('published_utc', '')}".encode()).hexdigest()
            
            article = NewsArticle(
                id=article_id,
                title=item.get("title", ""),
                content=item.get("description", ""),
                source="Polygon",
                url=item.get("article_url", ""),
                published_at=self._parse_polygon_datetime(item.get("published_utc", "")),
                symbols=symbols,
                confidence=0.7
            )
            
            return article
            
        except Exception as e:
            logger.debug(f"Error parseando Polygon: {e}")
            return None
    
    def _parse_polygon_datetime(self, time_str: str) -> datetime:
        """Parsea datetime de Polygon"""
        try:
            return datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        except:
            return datetime.now()
    
    async def fetch_finnhub_news(self, symbols: List[str]) -> List[NewsArticle]:
        """🔍 Obtiene noticias de Finnhub"""
        if not self.finnhub_key or not self._check_rate_limit("finnhub"):
            return []
        
        articles = []
        
        try:
            # Finnhub Company News
            for symbol in symbols[:10]:  # Máximo 10 símbolos
                symbol_clean = symbol.replace("/USD", "").replace("/", "")
                
                params = {
                    "symbol": symbol_clean,
                    "token": self.finnhub_key
                }
                
                url = f"{self.finnhub_base}/company-news"
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            if isinstance(data, list):
                                for item in data[:20]:  # Máximo 20 por símbolo
                                    try:
                                        article = self._parse_finnhub_article(item, [symbol_clean])
                                        if article:
                                            articles.append(article)
                                    except Exception as e:
                                        logger.debug(f"Error procesando artículo Finnhub: {e}")
                
                await asyncio.sleep(0.2)  # Rate limiting
            
            logger.info(f"📰 Finnhub: {len(articles)} artículos obtenidos")
            
        except Exception as e:
            logger.error(f"❌ Error Finnhub News: {e}")
        
        return articles
    
    def _parse_finnhub_article(self, item: Dict, symbols: List[str]) -> Optional[NewsArticle]:
        """Parsea artículo de Finnhub"""
        try:
            article_id = hashlib.md5(f"{item.get('url', '')}{item.get('datetime', '')}".encode()).hexdigest()
            
            article = NewsArticle(
                id=article_id,
                title=item.get("headline", ""),
                content=item.get("summary", ""),
                source="Finnhub",
                url=item.get("url", ""),
                published_at=datetime.fromtimestamp(item.get("datetime", time.time())),
                symbols=symbols,
                confidence=0.6
            )
            
            return article
            
        except Exception as e:
            logger.debug(f"Error parseando Finnhub: {e}")
            return None

class WebNewsAggregator:
    """
    🌐 Agregador de noticias desde sitios web especializados
    Backup cuando APIs no están disponibles
    """
    
    def __init__(self):
        self.news_sources = [
            {
                "name": "CoinDesk",
                "url": "https://www.coindesk.com/",
                "category": "crypto",
                "selectors": {
                    "articles": "article, .article-card",
                    "title": "h2, h3, .headline",
                    "link": "a"
                }
            },
            {
                "name": "CoinTelegraph", 
                "url": "https://cointelegraph.com/",
                "category": "crypto",
                "selectors": {
                    "articles": ".post-card, article",
                    "title": ".post-card__title, h2",
                    "link": "a"
                }
            },
            {
                "name": "MarketWatch",
                "url": "https://www.marketwatch.com/",
                "category": "stocks",
                "selectors": {
                    "articles": ".article__content, article",
                    "title": ".article__headline, h3",
                    "link": "a"
                }
            },
            {
                "name": "Yahoo Finance",
                "url": "https://finance.yahoo.com/news/",
                "category": "general",
                "selectors": {
                    "articles": "[data-module='NewsStream'] li, .js-stream-content li",
                    "title": "h3, .C\\(\\$c-link\\)",
                    "link": "a"
                }
            }
        ]
        
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.session_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        
        logger.info("🌐 Web News Aggregator inicializado")
    
    async def fetch_web_news(self, symbols: List[str], max_articles: int = 50) -> List[NewsArticle]:
        """🕷️ Obtiene noticias de sitios web"""
        all_articles = []
        
        # Ejecutar scraping en paralelo
        tasks = []
        for source in self.news_sources:
            task = asyncio.create_task(self._scrape_news_source(source, symbols))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                all_articles.extend(result)
            elif isinstance(result, Exception):
                logger.debug(f"Error en scraping: {result}")
        
        # Filtrar y deduplicar
        filtered_articles = self._filter_and_deduplicate(all_articles, symbols)
        
        logger.info(f"🌐 Web scraping: {len(filtered_articles)} artículos relevantes")
        return filtered_articles[:max_articles]
    
    async def _scrape_news_source(self, source: Dict, symbols: List[str]) -> List[NewsArticle]:
        """Scraping de una fuente específica"""
        articles = []
        
        try:
            # Usar trafilatura para extracción robusta
            loop = asyncio.get_event_loop()
            
            # Ejecutar en thread pool para no bloquear
            content = await loop.run_in_executor(
                self.executor,
                self._fetch_and_extract,
                source["url"]
            )
            
            if content:
                # Parsear con BeautifulSoup para obtener estructura
                soup = BeautifulSoup(content[:50000], 'html.parser')  # Limitar tamaño
                
                # Extraer artículos usando selectores CSS
                article_elements = soup.select(source["selectors"]["articles"])[:20]
                
                for element in article_elements:
                    try:
                        article = self._parse_web_article(element, source, symbols)
                        if article:
                            articles.append(article)
                    except Exception as e:
                        logger.debug(f"Error parseando elemento: {e}")
                        continue
            
        except Exception as e:
            logger.debug(f"Error scraping {source['name']}: {e}")
        
        return articles[:15]  # Máximo 15 por fuente
    
    def _fetch_and_extract(self, url: str) -> Optional[str]:
        """Fetch y extracción con trafilatura"""
        try:
            # Usar requests con headers apropiados
            response = requests.get(url, headers=self.session_headers, timeout=10)
            response.raise_for_status()
            
            # Extraer contenido principal con trafilatura
            return trafilatura.extract(response.content, include_comments=False)
            
        except Exception as e:
            logger.debug(f"Error fetch/extract {url}: {e}")
            return None
    
    def _parse_web_article(self, element, source: Dict, symbols: List[str]) -> Optional[NewsArticle]:
        """Parsea elemento HTML a NewsArticle"""
        try:
            # Extraer título
            title_elem = element.select_one(source["selectors"]["title"])
            title = title_elem.get_text(strip=True) if title_elem else ""
            
            # Extraer link
            link_elem = element.select_one(source["selectors"]["link"])
            if link_elem:
                href = link_elem.get("href", "")
                if href.startswith("/"):
                    href = urljoin(source["url"], href)
                url = href
            else:
                url = source["url"]
            
            # Filtrar por relevancia
            if not self._is_relevant_to_symbols(title, symbols):
                return None
            
            # Crear artículo
            article_id = hashlib.md5(f"{url}{title}".encode()).hexdigest()
            
            article = NewsArticle(
                id=article_id,
                title=title,
                content=title,  # Contenido limitado desde scraping
                source=source["name"],
                url=url,
                published_at=datetime.now(),  # Aproximado
                symbols=self._extract_relevant_symbols(title, symbols),
                confidence=0.4  # Menor confianza para scraping web
            )
            
            return article
            
        except Exception as e:
            logger.debug(f"Error parseando artículo web: {e}")
            return None
    
    def _is_relevant_to_symbols(self, text: str, symbols: List[str]) -> bool:
        """Verifica si el texto es relevante para los símbolos"""
        text_lower = text.lower()
        
        # Verificar símbolos específicos
        for symbol in symbols:
            symbol_clean = symbol.replace("/USD", "").replace("/", "").lower()
            if symbol_clean in text_lower:
                return True
        
        # Keywords genéricas importantes
        crypto_keywords = ["bitcoin", "btc", "ethereum", "eth", "crypto", "blockchain", "defi", "altcoin"]
        stock_keywords = ["stock", "earnings", "revenue", "market", "trading", "investment", "nasdaq", "s&p"]
        critical_keywords = ["merger", "acquisition", "bankruptcy", "fda", "approval", "lawsuit", "regulation"]
        
        all_keywords = crypto_keywords + stock_keywords + critical_keywords
        
        return any(keyword in text_lower for keyword in all_keywords)
    
    def _extract_relevant_symbols(self, text: str, symbols: List[str]) -> List[str]:
        """Extrae símbolos relevantes del texto"""
        relevant = []
        text_lower = text.lower()
        
        for symbol in symbols:
            symbol_clean = symbol.replace("/USD", "").replace("/", "").lower()
            if symbol_clean in text_lower:
                relevant.append(symbol)
        
        return relevant or symbols[:3]  # Fallback a primeros 3 símbolos
    
    def _filter_and_deduplicate(self, articles: List[NewsArticle], symbols: List[str]) -> List[NewsArticle]:
        """Filtra y elimina duplicados"""
        seen_titles = set()
        seen_urls = set()
        filtered = []
        
        # Ordenar por timestamp (más recientes primero)
        articles.sort(key=lambda x: x.published_at, reverse=True)
        
        for article in articles:
            # Filtro de calidad
            if len(article.title) < 10:
                continue
                
            # Deduplicación por título similar
            title_hash = hashlib.md5(article.title.lower().encode()).hexdigest()
            if title_hash in seen_titles:
                continue
            
            # Deduplicación por URL
            if article.url in seen_urls:
                continue
            
            seen_titles.add(title_hash)
            seen_urls.add(article.url)
            filtered.append(article)
        
        return filtered

class AdvancedNewsEngine:
    """
    🚀 Motor principal de agregación de noticias avanzado
    Combina APIs profesionales y web scraping con IA
    """
    
    def __init__(self):
        self.api_integrator = NewsAPIIntegrator()
        self.web_aggregator = WebNewsAggregator()
        
        # Cache y estado
        self.news_cache = {}
        self.last_fetch_time = {}
        self.cache_ttl = 300  # 5 minutos
        
        # Estadísticas
        self.stats = {
            "total_articles_fetched": 0,
            "api_articles": 0,
            "web_articles": 0,
            "cache_hits": 0,
            "last_update": datetime.now()
        }
        
        logger.info("🚀 Advanced News Engine inicializado")
    
    async def fetch_all_news(self, symbols: List[str], 
                           max_articles: int = 100,
                           use_cache: bool = True) -> List[NewsArticle]:
        """
        🎯 Función principal: obtiene noticias de todas las fuentes
        """
        cache_key = f"news_{'_'.join(sorted(symbols))}"
        current_time = time.time()
        
        # Verificar cache
        if (use_cache and cache_key in self.news_cache and 
            current_time - self.last_fetch_time.get(cache_key, 0) < self.cache_ttl):
            self.stats["cache_hits"] += 1
            logger.info(f"📋 Usando cache para {len(symbols)} símbolos")
            return self.news_cache[cache_key]
        
        logger.info(f"🔍 Obteniendo noticias para {len(symbols)} símbolos...")
        
        all_articles = []
        
        # 1. APIs profesionales (paralelo)
        api_tasks = [
            self.api_integrator.fetch_alpha_vantage_news(symbols),
            self.api_integrator.fetch_polygon_news(symbols),
            self.api_integrator.fetch_finnhub_news(symbols)
        ]
        
        api_results = await asyncio.gather(*api_tasks, return_exceptions=True)
        
        for result in api_results:
            if isinstance(result, list):
                all_articles.extend(result)
                self.stats["api_articles"] += len(result)
        
        # 2. Web scraping como backup
        web_articles = await self.web_aggregator.fetch_web_news(symbols, max_articles // 3)
        all_articles.extend(web_articles)
        self.stats["web_articles"] += len(web_articles)
        
        # 3. Filtrar, deduplicar y ordenar
        final_articles = self._process_articles(all_articles, symbols, max_articles)
        
        # Actualizar cache y estadísticas
        self.news_cache[cache_key] = final_articles
        self.last_fetch_time[cache_key] = current_time
        self.stats["total_articles_fetched"] = len(final_articles)
        self.stats["last_update"] = datetime.now()
        
        logger.info(f"✅ News Engine: {len(final_articles)} artículos finales")
        return final_articles
    
    def _process_articles(self, articles: List[NewsArticle], 
                         symbols: List[str], 
                         max_articles: int) -> List[NewsArticle]:
        """Procesa y filtra artículos finales"""
        
        # Deduplicar por ID
        seen_ids = set()
        unique_articles = []
        
        for article in articles:
            if article.id not in seen_ids:
                seen_ids.add(article.id)
                unique_articles.append(article)
        
        # Filtrar por relevancia y calidad
        filtered_articles = []
        for article in unique_articles:
            # Filtros de calidad
            if (len(article.title) >= 15 and 
                len(article.content) >= 20 and 
                article.confidence >= 0.3):
                filtered_articles.append(article)
        
        # Ordenar por relevancia (timestamp + confidence)
        filtered_articles.sort(
            key=lambda x: (x.published_at.timestamp() + x.confidence * 3600), 
            reverse=True
        )
        
        return filtered_articles[:max_articles]
    
    def get_stats(self) -> Dict:
        """Estadísticas del motor de noticias"""
        return {
            **self.stats,
            "cache_size": len(self.news_cache),
            "uptime_minutes": (datetime.now() - self.stats["last_update"]).total_seconds() / 60
        }

# Instancia global
news_engine = AdvancedNewsEngine()

# Función de conveniencia
async def get_latest_news(symbols: List[str], max_articles: int = 50) -> List[NewsArticle]:
    """
    🎯 Función principal para obtener noticias desde el bot
    """
    return await news_engine.fetch_all_news(symbols, max_articles)

if __name__ == "__main__":
    # Test del sistema
    async def test_news_engine():
        test_symbols = ["BTC/USD", "ETH/USD", "AAPL", "TSLA"]
        
        logger.info("🧪 Testing Advanced News Engine...")
        articles = await get_latest_news(test_symbols, 20)
        
        print(f"\n✅ Obtenidos {len(articles)} artículos")
        for i, article in enumerate(articles[:5]):
            print(f"{i+1}. {article.title[:80]}...")
            print(f"   Fuente: {article.source} | Símbolos: {article.symbols}")
            print(f"   Confianza: {article.confidence:.2f} | {article.published_at}")
            print()
    
    asyncio.run(test_news_engine())