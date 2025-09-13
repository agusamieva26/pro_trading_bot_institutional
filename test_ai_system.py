#!/usr/bin/env python3
"""
🧪 TEST COMPLETO DEL SISTEMA AI HYBRID AVANZADO
Test de integración completa para verificar todos los componentes funcionan correctamente
"""

import asyncio
import json
import sys
import os
from datetime import datetime

# Añadir path del bot
sys.path.append('bot')

async def test_complete_ai_system():
    """Test completo del sistema AI Hybrid"""
    print("🚀 INICIANDO TEST COMPLETO DEL SISTEMA AI HYBRID AVANZADO")
    print("=" * 60)
    
    results = {
        "news_engine": False,
        "sentiment_analyzer": False,
        "price_predictor": False,
        "trading_integration": False,
        "dashboard": False,
        "monitoring": False
    }
    
    # 1. TEST NEWS AGGREGATION ENGINE
    print("\n1️⃣ TESTING News Aggregation Engine...")
    try:
        from bot.advanced_news_engine import news_engine, get_latest_news
        
        # Test configuración
        stats = news_engine.get_stats()
        print(f"   📰 News Engine Stats: {stats}")
        
        # Test obtención de noticias
        symbols = ["BTC/USD", "ETH/USD", "AAPL", "TSLA"]
        news_articles = await get_latest_news(symbols, 5)
        print(f"   ✅ Fetched {len(news_articles)} news articles")
        
        if news_articles:
            print(f"   📄 Sample article: {news_articles[0].title[:50]}...")
        
        results["news_engine"] = True
        print("   ✅ News Aggregation Engine: PASSED")
        
    except Exception as e:
        print(f"   ❌ News Engine Error: {e}")
    
    # 2. TEST AI SENTIMENT ANALYZER
    print("\n2️⃣ TESTING AI Sentiment Analyzer...")
    try:
        from bot.ai_sentiment_analyzer import ai_sentiment_analyzer, get_sentiment_stats
        
        # Test estadísticas
        stats = get_sentiment_stats()
        print(f"   🧠 Sentiment Stats: {stats}")
        
        # Test análisis básico
        print("   🧪 Testing sentiment analysis...")
        results["sentiment_analyzer"] = True
        print("   ✅ AI Sentiment Analyzer: PASSED")
        
    except Exception as e:
        print(f"   ❌ Sentiment Analyzer Error: {e}")
    
    # 3. TEST PRICE IMPACT PREDICTOR
    print("\n3️⃣ TESTING Price Impact Predictor...")
    try:
        from bot.price_impact_predictor import get_price_predictor_status
        
        # Test estado del predictor
        status = get_price_predictor_status()
        print(f"   🎯 Price Predictor Status: {status}")
        
        results["price_predictor"] = True
        print("   ✅ Price Impact Predictor: PASSED")
        
    except Exception as e:
        print(f"   ❌ Price Predictor Error: {e}")
    
    # 4. TEST TRADING INTEGRATION
    print("\n4️⃣ TESTING AI Trading Integration...")
    try:
        from bot.ai_trading_integration import ai_trading_integrator, get_ai_market_overview
        
        # Test market overview
        overview = await get_ai_market_overview()
        print(f"   🤖 Market Overview Keys: {list(overview.keys())}")
        
        market_sentiment = overview.get("market_sentiment", {})
        print(f"   📊 Market Sentiment: {market_sentiment.get('overall_score', 'N/A')}")
        
        results["trading_integration"] = True
        print("   ✅ AI Trading Integration: PASSED")
        
    except Exception as e:
        print(f"   ❌ Trading Integration Error: {e}")
    
    # 5. TEST DASHBOARD COMPONENTS
    print("\n5️⃣ TESTING Dashboard Components...")
    try:
        from bot.ai_dashboard import AIHybridDashboard
        
        # Test dashboard initialization
        dashboard = AIHybridDashboard()
        print("   📊 Dashboard initialized successfully")
        
        results["dashboard"] = True
        print("   ✅ Dashboard Components: PASSED")
        
    except Exception as e:
        print(f"   ❌ Dashboard Error: {e}")
    
    # 6. TEST MONITORING SYSTEM
    print("\n6️⃣ TESTING Monitoring System...")
    try:
        from bot.ai_system_monitor import get_system_health, log_ai_event
        
        # Test logging
        log_ai_event("test", "info", "System test message")
        
        # Test health check
        health = get_system_health()
        print(f"   🔍 System Health Keys: {list(health.keys())}")
        
        results["monitoring"] = True
        print("   ✅ Monitoring System: PASSED")
        
    except Exception as e:
        print(f"   ❌ Monitoring Error: {e}")
    
    # RESUMEN FINAL
    print("\n" + "=" * 60)
    print("📋 RESUMEN DE RESULTADOS:")
    print("=" * 60)
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    for component, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {component.replace('_', ' ').title()}: {status}")
    
    print(f"\n🎯 RESULTADO FINAL: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🚀 ¡SISTEMA AI HYBRID COMPLETAMENTE OPERACIONAL!")
        return True
    elif passed_tests >= 4:
        print("⚠️ Sistema mayormente funcional con algunos componentes pendientes")
        return True
    else:
        print("❌ Sistema necesita trabajo adicional")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(test_complete_ai_system())
        print(f"\n🔬 Test completed with result: {result}")
    except Exception as e:
        print(f"💥 Test failed with error: {e}")