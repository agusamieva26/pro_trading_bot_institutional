"""
📊 AI HYBRID DASHBOARD - MONITOREO EN TIEMPO REAL
Dashboard avanzado para monitoreo de sistema AI con noticias, sentiment y alertas
Integra todos los componentes del sistema AI Hybrid para visualización en tiempo real
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import asyncio
import time
from datetime import datetime, timedelta
import json

# Imports del sistema AI
from bot.ai_trading_integration import (
    ai_trading_integrator, get_ai_market_overview, 
    get_ai_symbol_status, check_emergency_stops
)
from bot.advanced_news_engine import news_engine
from bot.ai_sentiment_analyzer import ai_sentiment_analyzer, get_sentiment_stats
from bot.price_impact_predictor import get_price_predictor_status
from bot.util import logger

# Configuración de página
st.set_page_config(
    page_title="🚀 AI Hybrid Trading Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1f1f2e 0%, #16213e 100%);
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        color: white;
        text-align: center;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
    }
    
    .alert-critical {
        background: #ff4757;
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
        border-left: 5px solid #ff3838;
    }
    
    .alert-warning {
        background: #ffa726;
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
        border-left: 5px solid #ff9800;
    }
    
    .alert-info {
        background: #2ed573;
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
        border-left: 5px solid #00b894;
    }
    
    .news-card {
        background: #f8f9ff;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 4px solid #667eea;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .sentiment-positive {
        color: #2ed573;
        font-weight: bold;
    }
    
    .sentiment-negative {
        color: #ff4757;
        font-weight: bold;
    }
    
    .sentiment-neutral {
        color: #57606f;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

class AIHybridDashboard:
    """Dashboard principal para sistema AI Hybrid"""
    
    def __init__(self):
        self.refresh_interval = 30  # segundos
        self.last_refresh = 0
        self.cached_data = {}
        
    async def get_dashboard_data(self, force_refresh=False):
        """Obtiene todos los datos para el dashboard"""
        current_time = time.time()
        
        if (not force_refresh and 
            current_time - self.last_refresh < self.refresh_interval and
            self.cached_data):
            return self.cached_data
        
        try:
            # Obtener datos en paralelo (simulado con gather)
            market_overview = await get_ai_market_overview()
            emergency_alerts = await check_emergency_stops()
            
            # Datos del sistema
            news_stats = news_engine.get_stats()
            sentiment_stats = get_sentiment_stats()
            price_predictor_status = get_price_predictor_status()
            
            self.cached_data = {
                "market_overview": market_overview,
                "emergency_alerts": emergency_alerts,
                "news_stats": news_stats,
                "sentiment_stats": sentiment_stats,
                "price_predictor_status": price_predictor_status,
                "last_update": datetime.now()
            }
            
            self.last_refresh = current_time
            return self.cached_data
            
        except Exception as e:
            logger.error(f"Error obteniendo datos dashboard: {e}")
            return self.cached_data or {}
    
    def render_header(self):
        """Renderiza header principal"""
        st.markdown("""
        <div class="main-header">
            <h1>🚀 AI Hybrid Trading Dashboard</h1>
            <p>Sistema Avanzado de Análisis de Noticias Financieras en Tiempo Real</p>
        </div>
        """, unsafe_allow_html=True)
    
    def render_system_status(self, data):
        """Renderiza estado del sistema"""
        st.subheader("🔧 Estado del Sistema AI")
        
        col1, col2, col3, col4 = st.columns(4)
        
        # Estado general
        with col1:
            market_data = data.get("market_overview", {})
            system_status = market_data.get("system_status", {})
            
            if system_status.get("analysis_active"):
                status_color = "🟡"
                status_text = "Analizando"
            elif system_status.get("last_analysis"):
                status_color = "🟢"
                status_text = "Activo"
            else:
                status_color = "🔴"
                status_text = "Inactivo"
            
            st.metric(
                "Estado AI",
                f"{status_color} {status_text}",
                delta=f"Actualizado: {system_status.get('last_analysis', 'N/A')}"
            )
        
        # Noticias
        with col2:
            news_stats = data.get("news_stats", {})
            articles_count = news_stats.get("total_articles_fetched", 0)
            cache_hits = news_stats.get("cache_hits", 0)
            
            st.metric(
                "Motor de Noticias",
                f"📰 {articles_count} artículos",
                delta=f"Cache: {cache_hits} hits"
            )
        
        # Sentiment
        with col3:
            sentiment_stats = data.get("sentiment_stats", {})
            analyzer_stats = sentiment_stats.get("analyzer_stats", {})
            total_analyzed = analyzer_stats.get("total_analyzed", 0)
            
            st.metric(
                "Análisis Sentiment",
                f"🧠 {total_analyzed} análisis",
                delta=f"AGUS: {analyzer_stats.get('agus_calls', 0)} calls"
            )
        
        # Predictor de precios
        with col4:
            price_status = data.get("price_predictor_status", {})
            model_trained = price_status.get("model_trained", False)
            data_records = price_status.get("data_records", 0)
            
            model_status = "🟢 Entrenado" if model_trained else "🔴 No entrenado"
            
            st.metric(
                "Predictor ML",
                model_status,
                delta=f"Datos: {data_records} registros"
            )
    
    def render_emergency_alerts(self, emergency_alerts):
        """Renderiza alertas de emergencia"""
        st.subheader("🚨 Alertas de Emergencia")
        
        if not emergency_alerts:
            st.markdown("""
            <div class="alert-info">
                ✅ <strong>Sin Emergencias Activas</strong><br>
                Todos los sistemas operando normalmente
            </div>
            """, unsafe_allow_html=True)
            return
        
        # Mostrar alertas por nivel de criticidad
        critical_alerts = []
        warning_alerts = []
        
        for symbol, alert in emergency_alerts.items():
            if alert.alert_level.value >= 4:  # Critical/Emergency
                critical_alerts.append((symbol, alert))
            else:
                warning_alerts.append((symbol, alert))
        
        # Alertas críticas
        if critical_alerts:
            st.markdown("### 🔴 Alertas Críticas")
            for symbol, alert in critical_alerts:
                st.markdown(f"""
                <div class="alert-critical">
                    <strong>🚨 {symbol} - {alert.alert_level.name}</strong><br>
                    {alert.trigger_reason}<br>
                    <em>Acción recomendada: {alert.recommended_action}</em><br>
                    <small>Sentiment: {alert.sentiment_score:.3f} | {alert.timestamp}</small>
                </div>
                """, unsafe_allow_html=True)
        
        # Alertas de advertencia
        if warning_alerts:
            st.markdown("### 🟡 Advertencias")
            for symbol, alert in warning_alerts:
                st.markdown(f"""
                <div class="alert-warning">
                    <strong>⚠️ {symbol} - {alert.alert_level.name}</strong><br>
                    {alert.trigger_reason}<br>
                    <em>{alert.recommended_action}</em><br>
                    <small>Sentiment: {alert.sentiment_score:.3f}</small>
                </div>
                """, unsafe_allow_html=True)
    
    def render_market_sentiment(self, market_data):
        """Renderiza análisis de sentiment del mercado"""
        st.subheader("📈 Sentiment del Mercado")
        
        sentiment_data = market_data.get("market_sentiment", {})
        overall_sentiment = sentiment_data.get("overall_score", 0.0)
        market_condition = sentiment_data.get("market_condition", "unknown")
        confidence = sentiment_data.get("confidence", 0.0)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Gráfico de sentiment general
            fig = go.Figure(go.Indicator(
                mode = "gauge+number+delta",
                value = overall_sentiment,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "Sentiment General"},
                delta = {'reference': 0},
                gauge = {
                    'axis': {'range': [-1, 1]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [-1, -0.5], 'color': "red"},
                        {'range': [-0.5, 0], 'color': "orange"},
                        {'range': [0, 0.5], 'color': "lightgreen"},
                        {'range': [0.5, 1], 'color': "green"}
                    ],
                    'threshold': {
                        'line': {'color': "black", 'width': 4},
                        'thickness': 0.75,
                        'value': 0
                    }
                }
            ))
            
            fig.update_layout(height=300)
            st.plotly_chart(fig, width="stretch")
        
        with col2:
            # Métricas de sentiment
            sentiment_class = ("sentiment-positive" if overall_sentiment > 0.2 else
                             "sentiment-negative" if overall_sentiment < -0.2 else
                             "sentiment-neutral")
            
            st.markdown(f"""
            <div class="metric-card">
                <h4>Estado del Mercado</h4>
                <p class="{sentiment_class}">{market_condition.title()}</p>
                <p><strong>Score:</strong> {overall_sentiment:.3f}</p>
                <p><strong>Confianza:</strong> {confidence:.1%}</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Sentiment por símbolo
        symbol_sentiments = sentiment_data.get("symbol_sentiments", {})
        if symbol_sentiments:
            st.markdown("#### Sentiment por Símbolo")
            
            # Crear DataFrame para gráfico
            df_symbols = pd.DataFrame([
                {"Symbol": symbol, "Sentiment": sentiment}
                for symbol, sentiment in symbol_sentiments.items()
            ])
            
            if not df_symbols.empty:
                # Gráfico de barras
                fig = px.bar(
                    df_symbols, 
                    x="Symbol", 
                    y="Sentiment",
                    color="Sentiment",
                    color_continuous_scale=["red", "yellow", "green"],
                    title="Sentiment por Símbolo"
                )
                
                fig.update_layout(height=400)
                st.plotly_chart(fig, width="stretch")
    
    def render_ai_adjustments(self, market_data):
        """Renderiza información de ajustes de IA"""
        st.subheader("⚡ Ajustes de Trading AI")
        
        ai_adjustments = market_data.get("ai_adjustments", {})
        
        if ai_adjustments.get("total_adjustments", 0) == 0:
            st.info("📊 Aún no hay datos de ajustes AI. Los datos aparecerán cuando el sistema comience a realizar ajustes.")
            return
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_adjustments = ai_adjustments.get("total_adjustments", 0)
            emergency_stops = ai_adjustments.get("emergency_stops", 0)
            
            st.metric(
                "Total Ajustes",
                total_adjustments,
                delta=f"Emergency stops: {emergency_stops}"
            )
        
        with col2:
            positive_adj = ai_adjustments.get("positive_adjustments", 0)
            negative_adj = ai_adjustments.get("negative_adjustments", 0)
            
            if total_adjustments > 0:
                pos_pct = (positive_adj / total_adjustments) * 100
                st.metric(
                    "Ajustes Positivos",
                    f"{positive_adj} ({pos_pct:.1f}%)",
                    delta=f"Negativos: {negative_adj}"
                )
            else:
                st.metric("Ajustes Positivos", "0", delta="Sin datos")
        
        with col3:
            avg_sentiment = ai_adjustments.get("avg_sentiment", 0.0)
            avg_boost = ai_adjustments.get("avg_boost_factor", 1.0)
            
            st.metric(
                "Sentiment Promedio",
                f"{avg_sentiment:.3f}",
                delta=f"Boost promedio: {avg_boost:.2f}x"
            )
    
    def render_live_news_feed(self, news_stats):
        """Renderiza feed de noticias en vivo"""
        st.subheader("📰 Feed de Noticias en Tiempo Real")
        
        # Por ahora mostramos estadísticas hasta que tengamos noticias reales
        if news_stats.get("total_articles_fetched", 0) == 0:
            st.info("📡 Conectando con fuentes de noticias... Las noticias aparecerán en tiempo real cuando estén disponibles.")
            
            # Mostrar fuentes configuradas
            st.markdown("#### Fuentes Configuradas:")
            sources = [
                "📊 Alpha Vantage News API",
                "📈 Polygon.io News",
                "📰 Finnhub Company News", 
                "🌐 Web Scraping (CoinDesk, CoinTelegraph, MarketWatch)"
            ]
            
            for source in sources:
                st.markdown(f"- {source}")
            
            return
        
        # Aquí iría el feed real de noticias cuando esté disponible
        st.markdown("#### Últimas Noticias Analizadas")
        
        # Placeholder para noticias reales
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown("""
            <div class="news-card">
                <h5>📈 Bitcoin Sentiment Analysis Complete</h5>
                <p>AI analysis detected <span class="sentiment-positive">positive sentiment</span> from recent market news.</p>
                <small>Fuente: Alpha Vantage | Confianza: 85% | Hace 2 minutos</small>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("""
            <div class="news-card">
                <h5>⚠️ Market Volatility Alert</h5>
                <p>Increased volatility detected in crypto markets. <span class="sentiment-neutral">Neutral sentiment</span> maintained.</p>
                <small>Fuente: Web Analysis | Confianza: 72% | Hace 5 minutos</small>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("#### Stats")
            st.metric("Artículos Hoy", news_stats.get("total_articles_fetched", 0))
            st.metric("API Calls", news_stats.get("api_articles", 0))
            st.metric("Web Scraping", news_stats.get("web_articles", 0))
    
    def render_performance_metrics(self, data):
        """Renderiza métricas de rendimiento del sistema"""
        st.subheader("📊 Métricas de Rendimiento")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("#### 🧠 AI Sentiment Engine")
            sentiment_stats = data.get("sentiment_stats", {})
            analyzer_stats = sentiment_stats.get("analyzer_stats", {})
            
            cache_size = sentiment_stats.get("cache_size", 0)
            agus_calls = analyzer_stats.get("agus_calls", 0)
            cache_hits = analyzer_stats.get("cache_hits", 0)
            
            st.metric("Cache Size", cache_size)
            st.metric("AGUS Calls", agus_calls)
            st.metric("Cache Hits", cache_hits)
        
        with col2:
            st.markdown("#### 📰 News Engine")
            news_stats = data.get("news_stats", {})
            
            total_articles = news_stats.get("total_articles_fetched", 0)
            api_articles = news_stats.get("api_articles", 0)
            web_articles = news_stats.get("web_articles", 0)
            
            st.metric("Total Artículos", total_articles)
            st.metric("API Articles", api_articles)
            st.metric("Web Articles", web_articles)
        
        with col3:
            st.markdown("#### 🎯 Price Predictor")
            price_status = data.get("price_predictor_status", {})
            
            model_trained = "✅ Sí" if price_status.get("model_trained", False) else "❌ No"
            data_records = price_status.get("data_records", 0)
            complete_records = price_status.get("complete_records", 0)
            
            st.metric("Modelo Entrenado", model_trained)
            st.metric("Registros", data_records)
            st.metric("Completos", complete_records)
    
    async def render_dashboard(self):
        """Renderiza dashboard completo"""
        self.render_header()
        
        # Sidebar con controles
        with st.sidebar:
            st.header("🔧 Controles")
            
            if st.button("🔄 Refrescar Datos", key="refresh_main"):
                st.rerun()
            
            if st.button("🚨 Verificar Emergencias", key="check_emergencies"):
                with st.spinner("Verificando emergencias..."):
                    try:
                        emergency_alerts = await check_emergency_stops()
                        if emergency_alerts:
                            st.error(f"⚠️ {len(emergency_alerts)} emergencias detectadas!")
                        else:
                            st.success("✅ Sin emergencias activas")
                    except Exception as e:
                        st.error(f"Error: {e}")
            
            # Configuración de refresh
            auto_refresh = st.checkbox("🔄 Auto-refresh", value=True)
            if auto_refresh:
                refresh_rate = st.selectbox("Intervalo", [15, 30, 60, 120], index=1)
                st.write(f"Refrescando cada {refresh_rate} segundos")
                time.sleep(refresh_rate)
                st.rerun()
        
        # Obtener datos
        with st.spinner("Cargando datos del sistema AI..."):
            try:
                data = await self.get_dashboard_data()
            except Exception as e:
                st.error(f"Error cargando datos: {e}")
                data = {}
        
        if not data:
            st.error("❌ No se pudieron cargar los datos del sistema AI")
            return
        
        # Renderizar secciones
        self.render_system_status(data)
        
        # Alertas de emergencia (prioritario)
        emergency_alerts = data.get("emergency_alerts", {})
        if emergency_alerts:
            self.render_emergency_alerts(emergency_alerts)
        
        # Dos columnas principales
        col1, col2 = st.columns([2, 1])
        
        with col1:
            market_data = data.get("market_overview", {})
            self.render_market_sentiment(market_data)
            self.render_ai_adjustments(market_data)
        
        with col2:
            news_stats = data.get("news_stats", {})
            self.render_live_news_feed(news_stats)
        
        # Métricas de rendimiento
        self.render_performance_metrics(data)
        
        # Footer
        st.markdown("---")
        last_update = data.get("last_update", datetime.now())
        st.caption(f"🔄 Última actualización: {last_update.strftime('%H:%M:%S')}")

# Función principal para Streamlit
async def main():
    """Función principal del dashboard"""
    dashboard = AIHybridDashboard()
    await dashboard.render_dashboard()

# Ejecutar dashboard
if __name__ == "__main__":
    try:
        # Usar asyncio para ejecutar función async
        asyncio.run(main())
    except Exception as e:
        st.error(f"Error ejecutando dashboard: {e}")
        logger.error(f"Dashboard error: {e}")

# Función para integrar con dashboard principal
def render_ai_section():
    """Función para integrar sección AI en dashboard principal"""
    st.header("🤖 AI Hybrid Analysis")
    
    # Versión simplificada para integración
    loop = None
    try:
        # Ejecutar en loop de asyncio existente o crear uno nuevo
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        dashboard = AIHybridDashboard()
        data = loop.run_until_complete(dashboard.get_dashboard_data())
        
        if data:
            # Renderizar secciones principales
            dashboard.render_system_status(data)
            
            emergency_alerts = data.get("emergency_alerts", {})
            if emergency_alerts:
                dashboard.render_emergency_alerts(emergency_alerts)
            
            market_data = data.get("market_overview", {})
            dashboard.render_market_sentiment(market_data)
        else:
            st.warning("⚠️ No se pudieron cargar datos AI")
            
    except Exception as e:
        st.error(f"Error en sección AI: {e}")
        logger.error(f"AI section error: {e}")
    finally:
        if loop:
            loop.close()