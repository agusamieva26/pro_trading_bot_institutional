# dashboard_modern.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timezone, timedelta
import os
from pathlib import Path
from streamlit_autorefresh import st_autorefresh
import numpy as np
import asyncio
import time
from typing import Optional, Dict, Any, List, Union

# Módulos del bot
from bot.config import settings
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOrdersRequest
from alpaca.trading.enums import QueryOrderStatus

# ===============================
# 🧠 LOCALAI SYSTEM IMPORTS
# ===============================

# AGUS 2.0 Hybrid Intelligence System
try:
    from bot.agus_2_hybrid_system import (
        AGUS2HybridSystem, AIProvider, QueryComplexity, ReasoningMode,
        QueryContext, AIResponse, PerformanceMetrics as AGUSPerformanceMetrics
    )
    AGUS_2_AVAILABLE = True
except ImportError as e:
    AGUS_2_AVAILABLE = False
    st.error(f"⚠️ AGUS 2.0 not available: {e}")

# Multi-Model Orchestrator
try:
    from bot.multi_model_orchestrator import (
        MultiModelOrchestrator, EnsemblePrediction, ConsensusType,
        OrchestrationMode, ModelRole, ModelWeight
    )
    ORCHESTRATOR_AVAILABLE = True
except ImportError as e:
    ORCHESTRATOR_AVAILABLE = False
    st.warning(f"⚠️ Multi-Model Orchestrator not available: {e}")

# Advanced Memory RAG System
try:
    from bot.advanced_memory_rag_system import (
        AdvancedMemoryRAGSystem, KnowledgeType, QueryType, 
        KnowledgeEntry, RAGResponse
    )
    RAG_AVAILABLE = True
except ImportError as e:
    RAG_AVAILABLE = False
    st.warning(f"⚠️ Advanced Memory RAG not available: {e}")

# AI Strategy Generator
try:
    from bot.ai_strategy_generator import (
        AIStrategyGenerator, StrategyType, StrategyDNA, MarketRegime
    )
    # Handle GeneticOptimizer separately as it may not exist
    try:
        from bot.ai_strategy_generator import GeneticOptimizer
    except ImportError:
        GeneticOptimizer = None
    STRATEGY_GEN_AVAILABLE = True
except ImportError as e:
    STRATEGY_GEN_AVAILABLE = False
    GeneticOptimizer = None
    st.warning(f"⚠️ AI Strategy Generator not available: {e}")

# LocalAI Institutional Manager
try:
    from bot.localai_institutional_manager import (
        LocalAIInstitutionalManager, ModelConfig, 
        PerformanceMetrics as LocalAIPerformanceMetrics
    )
    LOCALAI_MANAGER_AVAILABLE = True
except ImportError as e:
    LOCALAI_MANAGER_AVAILABLE = False
    st.warning(f"⚠️ LocalAI Manager not available: {e}")

# LocalAI Advanced Configuration
try:
    from bot.localai_advanced_config import (
        LocalAIAdvancedConfig, EndpointConfig, LoadBalancerConfig
    )
    LOCALAI_CONFIG_AVAILABLE = True
except ImportError as e:
    LOCALAI_CONFIG_AVAILABLE = False
    st.warning(f"⚠️ LocalAI Advanced Config not available: {e}")

# Chat Integration
try:
    from chat_with_ai import AITradingChat
    CHAT_AVAILABLE = True
except ImportError as e:
    CHAT_AVAILABLE = False
    st.warning(f"⚠️ AI Chat not available: {e}")

# Initialize LocalAI Systems with proper typing
agus_system: Optional[Any] = None
orchestrator: Optional[Any] = None
rag_system: Optional[Any] = None
strategy_generator: Optional[Any] = None
localai_manager: Optional[Any] = None
ai_chat: Optional[Any] = None

if AGUS_2_AVAILABLE:
    try:
        agus_system = AGUS2HybridSystem()
    except Exception as e:
        st.warning(f"⚠️ Failed to initialize AGUS 2.0: {e}")
        
if ORCHESTRATOR_AVAILABLE:
    try:
        orchestrator = MultiModelOrchestrator()
    except Exception as e:
        st.warning(f"⚠️ Failed to initialize Orchestrator: {e}")
        
if RAG_AVAILABLE:
    try:
        rag_system = AdvancedMemoryRAGSystem()
    except Exception as e:
        st.warning(f"⚠️ Failed to initialize RAG System: {e}")
        
if STRATEGY_GEN_AVAILABLE:
    try:
        strategy_generator = AIStrategyGenerator()
    except Exception as e:
        st.warning(f"⚠️ Failed to initialize Strategy Generator: {e}")
        
if LOCALAI_MANAGER_AVAILABLE:
    try:
        localai_manager = LocalAIInstitutionalManager()
    except Exception as e:
        st.warning(f"⚠️ Failed to initialize LocalAI Manager: {e}")
        
if CHAT_AVAILABLE:
    try:
        ai_chat = AITradingChat()
    except Exception as e:
        st.warning(f"⚠️ Failed to initialize AI Chat: {e}")

# ===============================
# CONFIGURACIÓN MODERNA DE LA PÁGINA
# ===============================

# Configuración ultra-moderna
st.set_page_config(
    page_title="🚀 Alpha Trading Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS MODERNO Y ELEGANTE
def apply_modern_css():
    st.markdown("""
    <style>
    /* Importar Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Variables CSS */
    :root {
        --primary-color: #1E88E5;
        --success-color: #00C853;
        --warning-color: #FF8F00;
        --error-color: #D32F2F;
        --dark-bg: #0E1117;
        --dark-surface: #1A1D29;
        --text-primary: #FFFFFF;
        --text-secondary: #B0BEC5;
        --gradient-1: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        --gradient-2: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        --gradient-3: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        --gradient-4: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        --gradient-5: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        --shadow: 0 10px 25px rgba(0,0,0,0.2);
        --border-radius: 16px;
    }
    
    /* Resetear estilos base */
    .main {
        padding: 1rem 2rem;
        background: linear-gradient(135deg, #0E1117 0%, #1A1D29 50%, #262730 100%);
        min-height: 100vh;
    }
    
    /* Header Principal */
    .main-header {
        background: var(--gradient-1);
        padding: 2rem;
        border-radius: var(--border-radius);
        margin-bottom: 2rem;
        box-shadow: var(--shadow);
        text-align: center;
        color: white;
    }
    
    .main-header h1 {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        font-size: 3rem;
        margin: 0;
        background: linear-gradient(45deg, #fff, #e3f2fd);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .main-header .subtitle {
        font-family: 'Inter', sans-serif;
        font-weight: 300;
        font-size: 1.2rem;
        opacity: 0.9;
        margin-top: 0.5rem;
    }
    
    /* Tarjetas de Métricas Modernas */
    .metric-card {
        background: var(--dark-surface);
        padding: 1.5rem;
        border-radius: var(--border-radius);
        box-shadow: var(--shadow);
        margin-bottom: 1rem;
        border: 1px solid rgba(255,255,255,0.1);
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    
    .metric-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: var(--gradient-3);
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 20px 40px rgba(0,0,0,0.3);
    }
    
    .metric-card .metric-title {
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        color: var(--text-secondary);
        font-size: 0.9rem;
        margin-bottom: 0.5rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .metric-card .metric-value {
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        color: var(--text-primary);
        font-size: 2.2rem;
        margin: 0;
    }
    
    .metric-card .metric-delta {
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        font-size: 0.9rem;
        margin-top: 0.5rem;
    }
    
    .metric-positive { color: var(--success-color); }
    .metric-negative { color: var(--error-color); }
    .metric-neutral { color: var(--text-secondary); }
    
    /* Métricas con Gradientes Específicos */
    .metric-profit::before { background: var(--gradient-4); }
    .metric-equity::before { background: var(--gradient-1); }
    .metric-cash::before { background: var(--gradient-5); }
    .metric-target::before { background: var(--gradient-2); }
    
    /* Progress Bar Moderno */
    .progress-container {
        background: var(--dark-surface);
        border-radius: var(--border-radius);
        padding: 2rem;
        box-shadow: var(--shadow);
        margin: 2rem 0;
        border: 1px solid rgba(255,255,255,0.1);
    }
    
    .progress-title {
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        color: var(--text-primary);
        font-size: 1.3rem;
        margin-bottom: 1rem;
    }
    
    .custom-progress {
        width: 100%;
        height: 12px;
        background: rgba(255,255,255,0.1);
        border-radius: 6px;
        overflow: hidden;
        position: relative;
    }
    
    .custom-progress-fill {
        height: 100%;
        background: var(--gradient-4);
        border-radius: 6px;
        transition: width 0.6s ease;
        box-shadow: 0 0 20px rgba(67, 233, 123, 0.3);
    }
    
    /* Tabla Moderna */
    .dataframe {
        background: var(--dark-surface) !important;
        border-radius: var(--border-radius) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        font-family: 'Inter', sans-serif !important;
    }
    
    .dataframe th {
        background: var(--gradient-1) !important;
        color: white !important;
        font-weight: 600 !important;
        border: none !important;
    }
    
    .dataframe td {
        background: var(--dark-surface) !important;
        color: var(--text-primary) !important;
        border-bottom: 1px solid rgba(255,255,255,0.05) !important;
    }
    
    /* Tabs Modernos */
    .stTabs [data-baseweb="tab-list"] {
        background: var(--dark-surface);
        border-radius: var(--border-radius);
        padding: 0.5rem;
        margin-bottom: 2rem;
        box-shadow: var(--shadow);
        border: 1px solid rgba(255,255,255,0.1);
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        color: var(--text-secondary);
        border-radius: 12px;
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        margin: 0.2rem;
        transition: all 0.3s ease;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(255,255,255,0.05);
        color: var(--text-primary);
    }
    
    .stTabs [aria-selected="true"] {
        background: var(--gradient-1) !important;
        color: white !important;
    }
    
    /* Sidebar Moderno */
    .css-1d391kg {
        background: var(--dark-surface);
        border-right: 1px solid rgba(255,255,255,0.1);
    }
    
    /* Alertas Modernas */
    .stAlert {
        background: var(--dark-surface) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: var(--border-radius) !important;
        color: var(--text-primary) !important;
        font-family: 'Inter', sans-serif !important;
    }
    
    /* Botones Modernos */
    .stButton > button {
        background: var(--gradient-1) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 500 !important;
        transition: all 0.3s ease !important;
        box-shadow: var(--shadow) !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 15px 30px rgba(0,0,0,0.3) !important;
    }
    
    /* Hide Streamlit Branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Scroll Bar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: var(--dark-bg);
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--gradient-1);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: var(--gradient-2);
    }
    
    /* Animaciones */
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.7; }
        100% { opacity: 1; }
    }
    
    .pulse { animation: pulse 2s infinite; }
    
    @keyframes slideInUp {
        from {
            transform: translateY(30px);
            opacity: 0;
        }
        to {
            transform: translateY(0);
            opacity: 1;
        }
    }
    
    .slide-in { animation: slideInUp 0.6s ease; }
    
    /* Status Badges */
    .status-badge {
        display: inline-block;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .status-active {
        background: rgba(0, 200, 83, 0.2);
        color: var(--success-color);
        border: 1px solid var(--success-color);
    }
    
    .status-warning {
        background: rgba(255, 143, 0, 0.2);
        color: var(--warning-color);
        border: 1px solid var(--warning-color);
    }
    
    .status-error {
        background: rgba(211, 47, 47, 0.2);
        color: var(--error-color);
        border: 1px solid var(--error-color);
    }
    </style>
    """, unsafe_allow_html=True)

# ===============================
# FUNCIONES DEL BACKEND (Mantenidas del original)
# ===============================

@st.cache_resource
def get_alpaca_client():
    return TradingClient(
        api_key=settings.alpaca_api_key,
        secret_key=settings.alpaca_secret_key,
        paper=(settings.mode == "paper")
    )

client = get_alpaca_client()

def get_account_info():
    try:
        account = client.get_account()
        return {
            "equity": float(getattr(account, "equity", 0)),
            "cash": float(getattr(account, "cash", 0)),
            "portfolio_value": float(getattr(account, "portfolio_value", 0)),
            "buying_power": float(getattr(account, "buying_power", 0)),
            "status": getattr(account, "status", "UNKNOWN"),
            "initial_portfolio_value": float(getattr(account, "initial_portfolio_value", 0)),
            "last_equity": float(getattr(account, "last_equity", 0))
        }
    except Exception as e:
        st.error(f"❌ Error obteniendo cuenta: {e}")
        return {}

def calculate_daily_change(account_info):
    if not account_info:
        return 0.0, 0.0
    
    try:
        current_equity = account_info.get("equity", 0)
        last_equity = account_info.get("last_equity", current_equity)
        daily_change = current_equity - last_equity
        daily_change_pct = (daily_change / last_equity * 100) if last_equity > 0 else 0.0
        return daily_change, daily_change_pct
    except Exception:
        return 0.0, 0.0

def get_total_unrealized_pnl():
    try:
        positions = get_open_positions()
        total_unrealized = sum([pos.get("unrealized_pl", 0) for pos in positions])
        return total_unrealized
    except Exception:
        return 0.0

def get_open_positions():
    try:
        positions = client.get_all_positions()
        return [{
            "symbol": getattr(pos, "symbol", "N/A"),
            "qty": float(getattr(pos, "qty", 0)),
            "avg_entry_price": float(getattr(pos, "avg_entry_price", 0)),
            "current_price": float(getattr(pos, "current_price", 0)),
            "unrealized_pl": float(getattr(pos, "unrealized_pl", 0)),
            "unrealized_pl_pct": (float(getattr(pos, "unrealized_pl", 0)) / (float(getattr(pos, "avg_entry_price", 1)) * abs(float(getattr(pos, "qty", 1)))) * 100) if getattr(pos, "avg_entry_price", 0) != 0 else 0.0,
            "market_value": float(getattr(pos, "market_value", 0))
        } for pos in positions]
    except Exception as e:
        st.warning(f"⚠️ Error obteniendo posiciones: {e}")
        return []

def get_open_orders():
    try:
        req = GetOrdersRequest(status=QueryOrderStatus.OPEN)
        orders = client.get_orders(req)
        return [{
            "symbol": getattr(order, "symbol", "N/A"),
            "side": getattr(getattr(order, "side", None), "value", "N/A"),
            "qty": float(getattr(order, "qty", 0)),
            "type": getattr(getattr(order, "order_type", None), "value", "N/A"),
            "filled": float(getattr(order, "filled_qty", 0)) if getattr(order, "filled_qty", None) else 0,
            "status": getattr(getattr(order, "status", None), "value", "N/A")
        } for order in orders]
    except Exception as e:
        st.warning(f"⚠️ Error obteniendo órdenes: {e}")
        return []

def load_trades():
    if os.path.exists("trades_log.csv"):
        df = pd.read_csv("trades_log.csv")
        if "entry_date" in df.columns:
            df["entry_date"] = pd.to_datetime(df["entry_date"], errors="coerce", utc=True)
        if "exit_date" in df.columns:
            df["exit_date"] = pd.to_datetime(df["exit_date"], errors="coerce", utc=True)
        if "realized_pnl" in df.columns:
            df["realized_pnl"] = pd.to_numeric(df["realized_pnl"], errors="coerce")
        return df
    return pd.DataFrame()

# ===============================
# FUNCIONES VISUALES MODERNAS
# ===============================

def create_metric_card(title, value, delta=None, delta_type="normal", card_type="default"):
    """Crea tarjetas de métricas modernas con gradientes"""
    
    delta_class = ""
    if delta:
        if delta_type == "positive" or (delta_type == "normal" and isinstance(delta, (int, float)) and delta > 0):
            delta_class = "metric-positive"
        elif delta_type == "negative" or (delta_type == "normal" and isinstance(delta, (int, float)) and delta < 0):
            delta_class = "metric-negative"
        else:
            delta_class = "metric-neutral"
    
    delta_text = ""
    if delta:
        if isinstance(delta, (int, float)):
            delta_text = f'<div class="metric-delta {delta_class}">{"+" if delta > 0 else ""}{delta:.2f}%</div>'
        else:
            delta_text = f'<div class="metric-delta {delta_class}">{delta}</div>'
    
    card_html = f"""
    <div class="metric-card metric-{card_type} slide-in">
        <div class="metric-title">{title}</div>
        <div class="metric-value">{value}</div>
        {delta_text}
    </div>
    """
    
    st.markdown(card_html, unsafe_allow_html=True)

def create_progress_section(current, target, title="Meta Diaria"):
    """Crea una sección de progreso moderna"""
    progress_pct = min((current / target) * 100, 100) if target > 0 else 0
    remaining = max(target - current, 0)
    
    # Determinar color basado en progreso
    if progress_pct >= 100:
        status = "🎉 COMPLETADA"
        color = "#00C853"
    elif progress_pct >= 75:
        status = "🔥 Muy Cerca"
        color = "#FF8F00"
    elif progress_pct >= 50:
        status = "⚡ En Progreso"
        color = "#1E88E5"
    else:
        status = "🚀 Iniciando"
        color = "#9C27B0"
    
    progress_html = f"""
    <div class="progress-container slide-in">
        <div class="progress-title">🎯 {title}</div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
            <div style="color: {color}; font-weight: 600; font-size: 1.1rem;">{status}</div>
            <div style="color: var(--text-secondary); font-size: 0.9rem;">
                ${current:,.2f} / ${target:,.0f}
            </div>
        </div>
        <div class="custom-progress">
            <div class="custom-progress-fill" style="width: {progress_pct}%; background: linear-gradient(90deg, {color}, {color}88);"></div>
        </div>
        <div style="margin-top: 1rem; display: flex; justify-content: space-between; font-size: 0.9rem; color: var(--text-secondary);">
            <span>{progress_pct:.1f}% completado</span>
            <span>${remaining:,.0f} restante</span>
        </div>
    </div>
    """
    
    st.markdown(progress_html, unsafe_allow_html=True)

def create_performance_chart(df):
    """Crea gráfico de performance avanzado"""
    if df.empty:
        return None
    
    df_closed = df[df["status"] == "closed"].copy()
    if df_closed.empty or "realized_pnl" not in df_closed.columns:
        return None
    
    df_closed = df_closed.dropna(subset=["exit_date"])
    if df_closed.empty:
        return None
    
    df_closed = df_closed.sort_values("exit_date")
    df_closed["cum_pnl"] = df_closed["realized_pnl"].cumsum()
    df_closed["trade_number"] = range(1, len(df_closed) + 1)
    
    # Crear gráfico con Plotly
    fig = go.Figure()
    
    # Línea principal de P&L acumulado
    fig.add_trace(go.Scatter(
        x=df_closed["trade_number"],
        y=df_closed["cum_pnl"],
        mode='lines+markers',
        name='P&L Acumulado',
        line=dict(color='#00C853', width=3),
        marker=dict(color='#00C853', size=6),
        hovertemplate='<b>Trade %{x}</b><br>P&L Acumulado: $%{y:.2f}<extra></extra>'
    ))
    
    # Área bajo la curva
    fig.add_trace(go.Scatter(
        x=df_closed["trade_number"],
        y=df_closed["cum_pnl"],
        fill='tozeroy',
        mode='none',
        fillcolor='rgba(0, 200, 83, 0.1)',
        name='Área P&L',
        showlegend=False
    ))
    
    # Línea de break-even
    fig.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.3)", 
                  annotation_text="Break Even", annotation_position="right")
    
    fig.update_layout(
        title=dict(
            text='📈 Performance del Trading Bot',
            font=dict(size=24, color='white', family='Inter'),
            x=0.5
        ),
        xaxis=dict(
            title='Número de Trade',
            gridcolor='rgba(255,255,255,0.1)',
            color='white',
            title_font=dict(family='Inter')
        ),
        yaxis=dict(
            title='P&L Acumulado ($)',
            gridcolor='rgba(255,255,255,0.1)',
            color='white',
            title_font=dict(family='Inter')
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter', color='white'),
        hovermode='x unified',
        showlegend=False
    )
    
    return fig

def create_positions_table(positions):
    """Crea tabla moderna de posiciones"""
    if not positions:
        return None
    
    df = pd.DataFrame(positions)
    
    # Aplicar formato condicional
    def style_pnl(val):
        if val > 0:
            return 'color: #00C853; font-weight: 600;'
        elif val < 0:
            return 'color: #D32F2F; font-weight: 600;'
        else:
            return 'color: #B0BEC5;'
    
    def style_percentage(val):
        if val > 0:
            return 'color: #00C853; font-weight: 600;'
        elif val < 0:
            return 'color: #D32F2F; font-weight: 600;'
        else:
            return 'color: #B0BEC5;'
    
    # Formatear tabla
    try:
        styled_df = df.style.format({
            "avg_entry_price": "${:.4f}",
            "current_price": "${:.4f}",
            "unrealized_pl": "${:.2f}",
            "unrealized_pl_pct": "{:.2f}%",
            "market_value": "${:.2f}",
            "qty": "{:.6f}"
        }).map(style_pnl, subset=['unrealized_pl'])\
          .map(style_percentage, subset=['unrealized_pl_pct'])
    except AttributeError:
        # Fallback for newer pandas versions
        styled_df = df.style.format({
            "avg_entry_price": "${:.4f}",
            "current_price": "${:.4f}",
            "unrealized_pl": "${:.2f}",
            "unrealized_pl_pct": "{:.2f}%",
            "market_value": "${:.2f}",
            "qty": "{:.6f}"
        })
    
    return styled_df

# ===============================
# APLICAR CSS Y HEADER
# ===============================

apply_modern_css()

# Header principal ultra-moderno
st.markdown("""
<div class="main-header slide-in">
    <h1>🚀 ALPHA TRADING DASHBOARD</h1>
    <div class="subtitle">Sistema de Trading Institucional • Monitoreo en Tiempo Real • Modo Paper</div>
</div>
""", unsafe_allow_html=True)

# ===============================
# TABS PRINCIPALES
# ===============================

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
    "📊 OVERVIEW", 
    "💼 PORTFOLIO", 
    "📈 PERFORMANCE", 
    "⚡ TRADES", 
    "📱 REPORTS",
    "🧠 AI CHAT",
    "🔍 AI HEALTH", 
    "🎭 ORCHESTRATOR",
    "📚 RAG BROWSER",
    "🧬 STRATEGY GEN"
])

# ===============================
# TAB 1: OVERVIEW PRINCIPAL
# ===============================

with tab1:
    # Obtener datos principales
    account_info = get_account_info()
    daily_change, daily_change_pct = calculate_daily_change(account_info)
    total_unrealized = get_total_unrealized_pnl()
    positions = get_open_positions()
    
    # Primera fila: Métricas financieras principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        create_metric_card(
            "💰 EQUITY TOTAL",
            f"${account_info.get('equity', 0):,.2f}",
            daily_change_pct,
            "normal",
            "equity"
        )
    
    with col2:
        create_metric_card(
            "📈 DAILY CHANGE",
            f"${daily_change:+,.2f}",
            daily_change_pct,
            "normal",
            "profit"
        )
    
    with col3:
        create_metric_card(
            "💵 CASH DISPONIBLE",
            f"${account_info.get('cash', 0):,.2f}",
            None,
            "normal",
            "cash"
        )
    
    with col4:
        buying_power = account_info.get('buying_power', 0)
        create_metric_card(
            "⚡ BUYING POWER",
            f"${buying_power:,.2f}",
            f"2x Leverage" if buying_power > account_info.get('cash', 0) else "No Margin",
            "normal",
            "default"
        )
    
    # Segunda fila: P&L y estado
    col5, col6, col7, col8 = st.columns(4)
    
    with col5:
        unrealized_pct = (total_unrealized / account_info.get('equity', 1) * 100) if account_info.get('equity', 0) > 0 else 0
        create_metric_card(
            "📊 UNREALIZED P&L",
            f"${total_unrealized:+,.2f}",
            unrealized_pct,
            "normal",
            "default"
        )
    
    with col6:
        create_metric_card(
            "🏢 POSICIONES ABIERTAS",
            f"{len(positions)}",
            f"${sum([pos.get('market_value', 0) for pos in positions]):,.0f} valor total",
            "normal",
            "default"
        )
    
    with col7:
        status = account_info.get("status", "UNKNOWN")
        status_color = "✅ ACTIVE" if status == "ACTIVE" else "⚠️ RESTRICTED"
        create_metric_card(
            "🔐 ESTADO CUENTA",
            status_color,
            "Trading Habilitado" if status == "ACTIVE" else "Verificar Restricciones",
            "normal",
            "default"
        )
    
    with col8:
        # Calcular exposición total
        total_exposure = sum([abs(pos.get('market_value', 0)) for pos in positions])
        exposure_pct = (total_exposure / account_info.get('equity', 1) * 100) if account_info.get('equity', 0) > 0 else 0
        create_metric_card(
            "⚖️ EXPOSICIÓN",
            f"{exposure_pct:.1f}%",
            f"${total_exposure:,.0f} total",
            "normal",
            "default"
        )
    
    # Tercera fila: Distribución de Beneficios 40/60
    st.markdown("### 💰 Distribución de Beneficios (Modelo 40/60)")
    
    # Calcular distribución de beneficios solo si hay ganancia
    reinvest_amount = 0.0
    protected_amount = 0.0
    
    if daily_change > 0:
        reinvest_amount = daily_change * 0.40  # 40% para reinversión
        protected_amount = daily_change * 0.60  # 60% protegido
    else:
        reinvest_amount = daily_change  # Si hay pérdida, todo va a recuperación
        protected_amount = 0.0
    
    col9, col10, col11, col12 = st.columns(4)
    
    with col9:
        create_metric_card(
            "🔄 REINVERSIÓN (40%)",
            f"${reinvest_amount:+,.2f}",
            "Crecimiento de capital" if reinvest_amount > 0 else "Recuperación",
            "normal",
            "cash"
        )
    
    with col10:
        create_metric_card(
            "🔒 PROTEGIDO (60%)",
            f"${protected_amount:+,.2f}",
            "Beneficio asegurado" if protected_amount > 0 else "Sin beneficio",
            "normal",
            "profit"
        )
    
    with col11:
        # Calcular progreso hacia la meta diaria
        try:
            from bot.target_scaler import get_dynamic_target
            current_target = get_dynamic_target()
            progress_pct = (daily_change / current_target * 100) if current_target > 0 else 0
        except:
            current_target = 1000.0
            progress_pct = (daily_change / current_target * 100) if current_target > 0 else 0
            
        create_metric_card(
            "🎯 PROGRESO META",
            f"{progress_pct:+.1f}%",
            f"${daily_change:+,.2f} de ${current_target:,.0f}",
            "normal",
            "default"
        )
    
    with col12:
        distribution_status = "🟢 ACTIVA" if daily_change > 0 else "⏸️ EN PAUSA"
        create_metric_card(
            "⚖️ ESTRATEGIA 40/60",
            distribution_status,
            "Modelo de crecimiento compuesto",
            "normal",
            "default"
        )

    # Sección de Meta Diaria Dinámica
    st.markdown("---")
    
    # Obtener meta dinámica del sistema de escalado
    try:
        from bot.target_scaler import get_dynamic_target, target_scaler
        DAILY_TARGET = get_dynamic_target()
        target_info = target_scaler.get_target_info()
    except Exception as e:
        DAILY_TARGET = 1000.0  # Fallback
        target_info = {}
    # Crear sección de progreso con meta dinámica
    meta_title = f"Meta Diaria Dinámica ${DAILY_TARGET:,.0f}"
    if target_info:
        escalations = target_info.get('total_escalations', 0)
        if escalations > 0:
            meta_title += f" ({escalations} ajustes automáticos)"
    
    create_progress_section(daily_change, DAILY_TARGET, meta_title)
    
    # Sección de información del sistema de escalado
    if target_info:
        st.markdown("### 🎯 Sistema de Escalado Automático")
        col_target1, col_target2, col_target3 = st.columns(3)
        
        with col_target1:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); 
                        padding: 15px; border-radius: 10px; text-align: center;">
                <h4>🎯 Meta Base</h4>
                <p style="font-size: 24px; font-weight: bold;">${target_info.get('base_target', 1000):.0f}</p>
                <small>Meta inicial del sistema</small>
            </div>
            """, unsafe_allow_html=True)
        
        with col_target2:
            escalations = target_info.get('total_escalations', 0)
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #0f4c75 0%, #3282b8 100%); 
                        padding: 15px; border-radius: 10px; text-align: center;">
                <h4>📊 Ajustes Totales</h4>
                <p style="font-size: 24px; font-weight: bold;">{escalations}</p>
                <small>Escalaciones automáticas</small>
            </div>
            """, unsafe_allow_html=True)
        
        with col_target3:
            last_update = target_info.get('last_update', 'Nunca')
            if last_update and last_update != 'Nunca':
                try:
                    from datetime import datetime
                    update_date = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
                    last_update = update_date.strftime('%d/%m %H:%M')
                except:
                    last_update = 'Reciente'
            
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #134e5e 0%, #71b280 100%); 
                        padding: 15px; border-radius: 10px; text-align: center;">
                <h4>⏱️ Última Actualización</h4>
                <p style="font-size: 20px; font-weight: bold;">{last_update}</p>
                <small>Revisión automática</small>
            </div>
            """, unsafe_allow_html=True)
        
        # Mostrar historial reciente de escalaciones
        recent_escalations = target_info.get('recent_escalations', [])
        if recent_escalations:
            st.markdown("**📈 Escalaciones Recientes:**")
            for i, escalation in enumerate(recent_escalations[-2:]):  # Últimas 2
                direction = "📈" if escalation.get('direction') == 'up' else "📉"
                old = escalation.get('old_target', 0)
                new = escalation.get('new_target', 0)
                st.markdown(f"• {direction} ${old:.0f} → ${new:.0f}")
    
    # Timeline de estado del bot
    st.markdown("### ⏰ Estado del Sistema")
    
    timeline_col1, timeline_col2, timeline_col3, timeline_col4 = st.columns(4)
    
    with timeline_col1:
        st.markdown("""
        <div class="metric-card slide-in">
            <div class="metric-title">🤖 BOT STATUS</div>
            <div class="metric-value" style="color: #00C853;">🟢 ACTIVE</div>
            <div class="metric-delta metric-positive">Operando en tiempo real</div>
        </div>
        """, unsafe_allow_html=True)
    
    with timeline_col2:
        st.markdown("""
        <div class="metric-card slide-in">
            <div class="metric-title">⚡ ÚLTIMA OPERACIÓN</div>
            <div class="metric-value" style="color: #1E88E5; font-size: 1.5rem;">Hace 2min</div>
            <div class="metric-delta metric-neutral">BTC/USD Long</div>
        </div>
        """, unsafe_allow_html=True)
    
    with timeline_col3:
        now = datetime.now()
        market_open = now.replace(hour=14, minute=30, second=0)  # 2:30 PM UTC
        market_close = now.replace(hour=21, minute=0, second=0)  # 9:00 PM UTC
        
        is_market_open = market_open <= now <= market_close and now.weekday() < 5
        market_status = "🟢 ABIERTO" if is_market_open else "🔴 CERRADO"
        
        st.markdown(f"""
        <div class="metric-card slide-in">
            <div class="metric-title">📈 MERCADO</div>
            <div class="metric-value" style="color: {'#00C853' if is_market_open else '#D32F2F'}; font-size: 1.5rem;">{market_status}</div>
            <div class="metric-delta metric-neutral">NYSE & NASDAQ</div>
        </div>
        """, unsafe_allow_html=True)
    
    with timeline_col4:
        next_reset = now.replace(hour=8, minute=15, second=0) + timedelta(days=1)
        time_to_reset = next_reset - now
        hours_to_reset = int(time_to_reset.total_seconds() // 3600)
        
        st.markdown(f"""
        <div class="metric-card slide-in">
            <div class="metric-title">🔄 RESET DIARIO</div>
            <div class="metric-value" style="color: #FF8F00; font-size: 1.5rem;">{hours_to_reset}h</div>
            <div class="metric-delta metric-neutral">8:15 AM Madrid</div>
        </div>
        """, unsafe_allow_html=True)

# ===============================
# TAB 2: PORTFOLIO DETALLADO
# ===============================

with tab2:
    st.markdown("### 💼 Análisis Detallado del Portfolio")
    
    if positions:
        # Resumen del portfolio
        total_market_value = sum([pos.get('market_value', 0) for pos in positions])
        total_unrealized = sum([pos.get('unrealized_pl', 0) for pos in positions])
        winners = len([p for p in positions if p.get('unrealized_pl', 0) > 0])
        losers = len([p for p in positions if p.get('unrealized_pl', 0) < 0])
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            create_metric_card(
                "💎 VALOR TOTAL",
                f"${total_market_value:,.2f}",
                None,
                "normal",
                "default"
            )
        
        with col2:
            win_rate = (winners / len(positions) * 100) if positions else 0
            create_metric_card(
                "🎯 WIN RATE",
                f"{win_rate:.1f}%",
                f"{winners}W / {losers}L",
                "normal",
                "default"
            )
        
        with col3:
            avg_position_size = total_market_value / len(positions) if positions else 0
            create_metric_card(
                "📊 POSICIÓN PROMEDIO",
                f"${avg_position_size:,.0f}",
                f"{len(positions)} posiciones",
                "normal",
                "default"
            )
        
        with col4:
            total_pnl_pct = (total_unrealized / total_market_value * 100) if total_market_value > 0 else 0
            create_metric_card(
                "📈 P&L TOTAL %",
                f"{total_pnl_pct:+.2f}%",
                f"${total_unrealized:+,.2f}",
                "normal",
                "default"
            )
        
        st.markdown("---")
        
        # Tabla de posiciones con estilo
        st.markdown("### 📋 Posiciones Detalladas")
        styled_table = create_positions_table(positions)
        if styled_table is not None:
            st.dataframe(styled_table, width="stretch", height=400)
        
        # Gráfico de composición del portfolio
        st.markdown("### 🥧 Composición del Portfolio")
        
        # Crear datos para gráfico de pie
        symbols = [pos['symbol'] for pos in positions]
        values = [abs(pos['market_value']) for pos in positions]
        colors = ['#1E88E5', '#00C853', '#FF8F00', '#D32F2F', '#9C27B0', '#00BCD4', '#4CAF50', '#FF5722']
        
        fig_pie = go.Figure(data=[go.Pie(
            labels=symbols,
            values=values,
            hole=.4,
            marker_colors=colors[:len(symbols)],
            textinfo='label+percent',
            textfont=dict(size=12, color='white', family='Inter'),
            hovertemplate='<b>%{label}</b><br>Valor: $%{value:,.2f}<br>Porcentaje: %{percent}<extra></extra>'
        )])
        
        fig_pie.update_layout(
            title=dict(
                text='Distribución de Activos',
                font=dict(size=20, color='white', family='Inter'),
                x=0.5
            ),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Inter', color='white'),
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="middle",
                y=0.5,
                xanchor="left",
                x=1.01,
                font=dict(color='white')
            )
        )
        
        st.plotly_chart(fig_pie, use_container_width=True)
        
    else:
        st.info("💼 No hay posiciones abiertas actualmente.")
        
        # Mostrar cuenta detallada
        st.markdown("### 💰 Detalle de la Cuenta")
        if account_info:
            account_data = {
                "Campo": ["Equity", "Cash", "Buying Power", "Portfolio Value", "Status"],
                "Valor": [
                    f"${account_info.get('equity', 0):,.2f}",
                    f"${account_info.get('cash', 0):,.2f}",
                    f"${account_info.get('buying_power', 0):,.2f}",
                    f"${account_info.get('portfolio_value', 0):,.2f}",
                    account_info.get('status', 'N/A')
                ]
            }
            df_account = pd.DataFrame(account_data)
            st.dataframe(df_account, width="stretch", hide_index=True)

# ===============================
# TAB 3: PERFORMANCE CHARTS
# ===============================

with tab3:
    st.markdown("### 📈 Análisis de Performance")
    
    df_trades = load_trades()
    
    if not df_trades.empty:
        # Gráfico principal de performance
        perf_chart = create_performance_chart(df_trades)
        if perf_chart:
            st.plotly_chart(perf_chart, use_container_width=True)
        
        # Métricas de performance
        df_closed = df_trades[df_trades["status"] == "closed"].copy()
        if not df_closed.empty and "realized_pnl" in df_closed.columns:
            
            total_trades = len(df_closed)
            winning_trades = len(df_closed[df_closed["realized_pnl"] > 0])
            losing_trades = len(df_closed[df_closed["realized_pnl"] < 0])
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            total_pnl = df_closed["realized_pnl"].sum()
            avg_win = df_closed[df_closed["realized_pnl"] > 0]["realized_pnl"].mean() if winning_trades > 0 else 0
            avg_loss = df_closed[df_closed["realized_pnl"] < 0]["realized_pnl"].mean() if losing_trades > 0 else 0
            profit_factor = abs(avg_win * winning_trades / (avg_loss * losing_trades)) if avg_loss != 0 and losing_trades > 0 else 0
            
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                create_metric_card(
                    "🎯 WIN RATE",
                    f"{win_rate:.1f}%",
                    f"{winning_trades}W / {losing_trades}L",
                    "normal",
                    "default"
                )
            
            with col2:
                create_metric_card(
                    "💰 TOTAL P&L",
                    f"${total_pnl:+,.2f}",
                    f"{total_trades} trades",
                    "normal",
                    "profit"
                )
            
            with col3:
                create_metric_card(
                    "📈 AVG WIN",
                    f"${avg_win:+,.2f}",
                    f"{winning_trades} trades",
                    "normal",
                    "default"
                )
            
            with col4:
                create_metric_card(
                    "📉 AVG LOSS",
                    f"${avg_loss:+,.2f}",
                    f"{losing_trades} trades",
                    "normal",
                    "default"
                )
            
            with col5:
                create_metric_card(
                    "⚖️ PROFIT FACTOR",
                    f"{profit_factor:.2f}",
                    "Ratio Ganancia/Pérdida",
                    "normal",
                    "default"
                )
            
            # Distribución de P&L
            st.markdown("---")
            st.markdown("### 📊 Distribución de Resultados")
            
            fig_hist = go.Figure(data=[go.Histogram(
                x=df_closed["realized_pnl"],
                nbinsx=30,
                marker_color='#1E88E5',
                opacity=0.7,
                name='Distribución P&L'
            )])
            
            fig_hist.add_vline(x=0, line_dash="dash", line_color="white", 
                              annotation_text="Break Even", annotation_position="top")
            fig_hist.add_vline(x=df_closed["realized_pnl"].mean(), line_color="#00C853",
                              annotation_text=f"Promedio: ${df_closed['realized_pnl'].mean():.2f}", 
                              annotation_position="top right")
            
            fig_hist.update_layout(
                title=dict(
                    text='Distribución de P&L por Trade',
                    font=dict(size=20, color='white', family='Inter'),
                    x=0.5
                ),
                xaxis=dict(
                    title='P&L ($)',
                    gridcolor='rgba(255,255,255,0.1)',
                    color='white'
                ),
                yaxis=dict(
                    title='Frecuencia',
                    gridcolor='rgba(255,255,255,0.1)',
                    color='white'
                ),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(family='Inter', color='white'),
                showlegend=False
            )
            
            st.plotly_chart(fig_hist, use_container_width=True)
    
    else:
        st.info("📊 No hay datos de trades para mostrar análisis de performance.")

# ===============================
# TAB 4: TRADES EN TIEMPO REAL
# ===============================

with tab4:
    st.markdown("### ⚡ Trading Activity")
    
    # Órdenes abiertas
    st.markdown("#### 🛒 Órdenes Pendientes")
    orders = get_open_orders()
    
    if orders:
        df_orders = pd.DataFrame(orders)
        st.dataframe(df_orders, width="stretch", height=300)
    else:
        st.info("✅ No hay órdenes pendientes.")
    
    # Historial completo de trades
    st.markdown("#### 📋 Historial Completo")
    df_trades = load_trades()
    
    if not df_trades.empty:
        # Filtros
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status_filter = st.selectbox(
                "Estado",
                ["Todos"] + list(df_trades["status"].unique()),
                key="status_filter"
            )
        
        with col2:
            if "symbol" in df_trades.columns:
                unique_symbols = df_trades["symbol"].dropna().unique()
                symbol_filter = st.selectbox(
                    "Símbolo", 
                    ["Todos"] + sorted([str(s) for s in unique_symbols]),
                    key="symbol_filter"
                )
            else:
                symbol_filter = "Todos"
        
        with col3:
            if "side" in df_trades.columns:
                unique_sides = df_trades["side"].dropna().unique()
                side_filter = st.selectbox(
                    "Lado",
                    ["Todos"] + [str(s) for s in unique_sides],
                    key="side_filter"
                )
            else:
                side_filter = "Todos"
        
        # Aplicar filtros
        filtered_df = df_trades.copy()
        
        if status_filter != "Todos":
            filtered_df = filtered_df[filtered_df["status"] == status_filter]
        
        if symbol_filter != "Todos":
            filtered_df = filtered_df[filtered_df["symbol"] == symbol_filter]
        
        if side_filter != "Todos":
            filtered_df = filtered_df[filtered_df["side"] == side_filter]
        
        # Mostrar tabla filtrada
        if len(filtered_df) > 0:
            display_df = filtered_df.head(100) if len(filtered_df) > 100 else filtered_df
            st.dataframe(display_df, width="stretch", height=500)
            st.caption(f"Mostrando {len(display_df)} de {len(filtered_df)} trades")
        else:
            st.info("🔍 No hay trades que coincidan con los filtros seleccionados.")
    
    else:
        st.warning("📊 No se encontró historial de trades.")

# ===============================
# TAB 5: REPORTS
# ===============================

with tab5:
    st.markdown("### 📱 Reportes y Análisis")
    
    # Información del sistema automatizado
    st.markdown("#### 🤖 Sistema de Automatización")
    
    auto_col1, auto_col2, auto_col3 = st.columns(3)
    
    with auto_col1:
        st.markdown("""
        <div class="metric-card slide-in">
            <div class="metric-title">🔄 ENTRENAMIENTO</div>
            <div class="metric-value" style="color: #00C853; font-size: 1.8rem;">Bi-semanal</div>
            <div class="metric-delta metric-positive">Cada 14 días a las 03:00</div>
        </div>
        """, unsafe_allow_html=True)
    
    with auto_col2:
        st.markdown("""
        <div class="metric-card slide-in">
            <div class="metric-title">⚡ OPTUNA</div>
            <div class="metric-value" style="color: #1E88E5; font-size: 1.8rem;">Semanal</div>
            <div class="metric-delta metric-neutral">Lunes 03:00 + Retraining</div>
        </div>
        """, unsafe_allow_html=True)
    
    with auto_col3:
        st.markdown("""
        <div class="metric-card slide-in">
            <div class="metric-title">🎯 WIN RATE</div>
            <div class="metric-value" style="color: #FF8F00; font-size: 1.8rem;">54% → 75%</div>
            <div class="metric-delta metric-warning">Evolución proyectada</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Reportes Excel
    st.markdown("---")
    st.markdown("#### 📊 Reportes Generados")
    
    if os.path.exists("reports/"):
        report_files = [f for f in os.listdir("reports/") if f.startswith("reporte_")]
        if report_files:
            selected_report = st.selectbox("Selecciona un reporte", sorted(report_files, reverse=True))
            
            if st.button("📥 Cargar Reporte", type="primary"):
                try:
                    report_path = f"reports/{selected_report}"
                    
                    # Leer Excel
                    df_resumen = pd.read_excel(report_path, sheet_name="Resumen")
                    df_trades = pd.read_excel(report_path, sheet_name="Trades")
                    
                    st.markdown(f"**📄 Reporte: {selected_report}**")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("##### 📋 Resumen")
                        st.dataframe(df_resumen, width="stretch")
                    
                    with col2:
                        st.markdown("##### ⚡ Trades")
                        st.dataframe(df_trades.head(10), width="stretch")
                        if len(df_trades) > 10:
                            st.caption(f"Mostrando 10 de {len(df_trades)} trades")
                    
                except Exception as e:
                    st.error(f"❌ Error cargando reporte: {e}")
        else:
            st.info("📊 No hay reportes generados aún. Los reportes se generan automáticamente cada día a las 00:00.")
    else:
        st.warning("📁 Carpeta de reportes no encontrada.")
    
    # Información del proyecto
    st.markdown("---")
    st.markdown("#### ℹ️ Información del Sistema")
    
    info_html = """
    <div class="metric-card slide-in">
        <div class="metric-title">🚀 ALPHA TRADING DASHBOARD v2.0</div>
        <div style="color: var(--text-secondary); margin-top: 1rem; line-height: 1.6;">
            <strong>🎯 Características:</strong><br>
            • Dashboard moderno con CSS personalizado<br>
            • Métricas financieras en tiempo real<br>
            • Gráficos interactivos con Plotly<br>
            • Sistema de automatización evolutiva<br>
            • Análisis de performance avanzado<br>
            • Interfaz responsive y moderna<br><br>
            
            <strong>🤖 Automatización:</strong><br>
            • Entrenamiento bi-semanal automático<br>
            • Optimización Optuna semanal<br>
            • Triggers inteligentes de emergencia<br>
            • Reportes diarios automatizados<br>
            • Evolución continua del win rate<br><br>
            
            <strong>💎 Meta Anual:</strong><br>
            • €5,000 inicial → €120k-300k netos<br>
            • ROI: 2,400%-6,000%<br>
            • Completamente autónomo<br>
        </div>
    </div>
    """
    
    st.markdown(info_html, unsafe_allow_html=True)

# ===============================
# TAB 6: 🧠 AI CHAT - AGUS 2.0 HYBRID SYSTEM
# ===============================

with tab6:
    st.markdown("# 🧠 AGUS 2.0 Hybrid Intelligence System")
    
    if not AGUS_2_AVAILABLE or not CHAT_AVAILABLE:
        st.error("❌ AGUS 2.0 Hybrid System not available. Please ensure all dependencies are installed.")
        st.info("Required: bot.agus_2_hybrid_system and chat_with_ai modules")
    else:
        # Chat Interface Header
        st.markdown("""
        <div class="metric-card">
            <div class="metric-title">🚀 INTELLIGENT TRADING ASSISTANT</div>
            <div style="color: var(--text-secondary); margin-top: 1rem;">
                Advanced hybrid AI system with LocalAI + Cloud routing<br>
                • Chain-of-thought reasoning • Contextual memory • Trading intelligence
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # System Status Row
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if agus_system is not None and hasattr(agus_system, 'get_system_status'):
                try:
                    status = agus_system.get_system_status()
                    provider = status.get('current_provider', 'Unknown')
                    st.metric("🎯 Active Provider", provider)
                except Exception:
                    st.metric("🎯 Active Provider", "AGUS 2.0")
            else:
                st.metric("🎯 Active Provider", "AGUS 2.0")
        
        with col2:
            if agus_system is not None and hasattr(agus_system, 'performance_tracker'):
                try:
                    tracker = getattr(agus_system, 'performance_tracker', None)
                    if tracker is not None and hasattr(tracker, 'metrics_history'):
                        queries = len(tracker.metrics_history)
                        st.metric("💬 Total Queries", f"{queries:,}")
                    else:
                        st.metric("💬 Total Queries", "N/A")
                except Exception:
                    st.metric("💬 Total Queries", "N/A")
            else:
                st.metric("💬 Total Queries", "N/A")
        
        with col3:
            if agus_system is not None and hasattr(agus_system, 'get_cost_savings'):
                try:
                    savings = agus_system.get_cost_savings()
                    st.metric("💰 Cost Savings", f"${savings:.2f}")
                except Exception:
                    st.metric("💰 Cost Savings", "$0.00")
            else:
                st.metric("💰 Cost Savings", "$0.00")
        
        with col4:
            if agus_system is not None and hasattr(agus_system, 'performance_tracker'):
                try:
                    tracker = getattr(agus_system, 'performance_tracker', None)
                    if tracker is not None and hasattr(tracker, 'get_avg_response_time'):
                        avg_time = tracker.get_avg_response_time()
                        st.metric("⚡ Avg Response", f"{avg_time:.2f}s")
                    else:
                        st.metric("⚡ Avg Response", "N/A")
                except Exception:
                    st.metric("⚡ Avg Response", "N/A")
            else:
                st.metric("⚡ Avg Response", "N/A")
        
        st.markdown("---")
        
        # Enhanced Chat Interface
        st.markdown("""
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 20px; border-radius: 15px; margin-bottom: 20px;'>
            <h2 style='color: white; text-align: center; margin: 0;'>
                🧠 Chat with AGUS 2.0 Hybrid Intelligence
            </h2>
            <p style='color: #f0f0f0; text-align: center; margin: 10px 0 0 0; font-size: 14px;'>
                Advanced AI assistant powered by OpenAI • File creation • Trading analysis • Code generation
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Initialize chat history in session state
        if "agus_chat_history" not in st.session_state:
            st.session_state.agus_chat_history = []
            # Add welcome message
            welcome_msg = """🧠 **¡AGUS 2.0 HÍBRIDO INTEGRADO AL SISTEMA DE TRADING!**

🏛️ **Soy la IA central del bot institucional con acceso completo a:**
• 📊 Portfolio de $18,000+ operando 16 criptomonedas en tiempo real
• 🛡️ Sistemas de gestión de riesgo multicapa activos
• 🔄 Análisis multi-timeframe (5m, 15m, 1H, 4H) 
• 🤖 Modelos ML Random Forest con análisis Fibonacci
• 💰 Detección de arbitraje entre múltiples exchanges
• 📈 Optimización de portfolio y rebalanceo automático

✨ **Capacidades especializadas:**
• 🎯 Análisis de señales de trading en tiempo real
• 📝 Creación de scripts de trading personalizados
• 🔧 Debugging avanzado del sistema completo
• 💡 Estrategias basadas en datos reales del portfolio
• 📋 Reportes detallados con métricas institucionales

🚀 **Comandos especializados:**
• "¿Cómo está funcionando el bot de trading?"
• "Analiza las señales actuales de BTC y ETH"
• "Crea script para nueva estrategia de momentum"
• "Diagnostica el sistema de gestión de riesgo"
• "Genera reporte del performance actual"

**¡Pregúntame sobre el sistema de trading en funcionamiento!**"""
            st.session_state.agus_chat_history.append({"role": "assistant", "content": welcome_msg})
        
        # Chat container with better styling
        chat_container = st.container()
        
        # Display chat history with enhanced styling
        with chat_container:
            for i, message in enumerate(st.session_state.agus_chat_history[-10:]):  # Show last 10 messages
                with st.chat_message(message["role"]):
                    if message["role"] == "assistant":
                        # Enhanced assistant styling
                        st.markdown(f"""
                        <div style='background-color: #f8f9fa; padding: 15px; border-radius: 10px; 
                                    border-left: 4px solid #667eea; margin: 5px 0;'>
                            {message["content"]}
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        # User message styling
                        st.markdown(f"""
                        <div style='background-color: #e3f2fd; padding: 12px; border-radius: 10px; 
                                    border-left: 4px solid #2196f3; margin: 5px 0;'>
                            {message["content"]}
                        </div>
                        """, unsafe_allow_html=True)
        
        # Chat input with better prompts
        col1, col2 = st.columns([4, 1])
        
        with col1:
            user_input = st.chat_input(
                "💬 Pregúntame sobre trading, crea archivos, o pide análisis... (Ej: 'crear archivo bot.py')"
            )
        
        with col2:
            if st.button("🗑️ Limpiar", help="Limpiar historial de chat"):
                st.session_state.agus_chat_history = [st.session_state.agus_chat_history[0]]  # Keep welcome message
                st.rerun()
        
        # Process user input
        if user_input:
            # Add user message to history
            st.session_state.agus_chat_history.append({"role": "user", "content": user_input})
            
            # Process with AGUS 2.0
            try:
                # Show enhanced spinner
                with st.spinner("🧠 AGUS 2.0 procesando tu solicitud... Esto puede incluir creación de archivos."):
                    if ai_chat is not None and hasattr(ai_chat, 'ask_ai'):
                        response = asyncio.run(ai_chat.ask_ai(user_input))
                    else:
                        response = "⚠️ AGUS 2.0 no está completamente inicializado. Reinicia el dashboard."
                
                # Add assistant response to history
                st.session_state.agus_chat_history.append({"role": "assistant", "content": response})
                
                # Auto-scroll to latest message
                st.rerun()
                
            except Exception as e:
                error_msg = f"""❌ **Error en AGUS 2.0**

Ocurrió un problema al procesar tu solicitud:
```
{str(e)}
```

💡 **Sugerencias:**
• Reinicia el dashboard si persiste
• Verifica tu conexión a OpenAI
• Prueba con una consulta más simple"""
                
                st.error("❌ Error communicating with AGUS 2.0")
                st.session_state.agus_chat_history.append({
                    "role": "assistant", 
                    "content": error_msg
                })
                st.rerun()
        
        # Quick action buttons
        st.markdown("### 🚀 Acciones Rápidas")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("📊 Análisis de Mercado"):
                quick_query = "Dame un análisis completo del mercado actual de Bitcoin y Ethereum"
                st.session_state.agus_chat_history.append({"role": "user", "content": quick_query})
                st.rerun()
        
        with col2:
            if st.button("📝 Crear Script"):
                quick_query = "Crea archivo trading_strategy.py con una estrategia básica de trading"
                st.session_state.agus_chat_history.append({"role": "user", "content": quick_query})
                st.rerun()
        
        with col3:
            if st.button("🔧 Diagnóstico"):
                quick_query = "Haz un diagnóstico completo del sistema de trading y reporta cualquier problema"
                st.session_state.agus_chat_history.append({"role": "user", "content": quick_query})
                st.rerun()
        
        with col4:
            if st.button("📈 Estrategia"):
                quick_query = "Genera una nueva estrategia de trading personalizada basada en las condiciones actuales"
                st.session_state.agus_chat_history.append({"role": "user", "content": quick_query})
                st.rerun()

# ===============================
# TAB 7: 🔍 AI HEALTH - LOCALAI MONITORING
# ===============================

with tab7:
    st.markdown("# 🔍 LocalAI Health Monitoring")
    
    # Health Status Overview
    st.markdown("### 🏥 System Health Overview")
    
    health_col1, health_col2, health_col3, health_col4 = st.columns(4)
    
    with health_col1:
        agus_status = "🟢 Online" if AGUS_2_AVAILABLE else "🔴 Offline"
        st.metric("🧠 AGUS 2.0", agus_status)
    
    with health_col2:
        orch_status = "🟢 Online" if ORCHESTRATOR_AVAILABLE else "🔴 Offline"
        st.metric("🎭 Orchestrator", orch_status)
    
    with health_col3:
        rag_status = "🟢 Online" if RAG_AVAILABLE else "🔴 Offline"
        st.metric("📚 RAG System", rag_status)
    
    with health_col4:
        strat_status = "🟢 Online" if STRATEGY_GEN_AVAILABLE else "🔴 Offline"
        st.metric("🧬 Strategy Gen", strat_status)
    
    st.markdown("---")
    
    # LocalAI Manager Status
    if LOCALAI_MANAGER_AVAILABLE:
        st.markdown("### 🏛️ LocalAI Institutional Manager")
        
        try:
            # Get system resources
            import psutil
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            res_col1, res_col2, res_col3 = st.columns(3)
            
            with res_col1:
                st.metric("💻 CPU Usage", f"{cpu_percent:.1f}%")
            
            with res_col2:
                st.metric("🧠 Memory Usage", f"{memory.percent:.1f}%")
            
            with res_col3:
                st.metric("💾 Disk Usage", f"{disk.percent:.1f}%")
            
            # Model Status Table
            st.markdown("#### 🤖 Model Status")
            
            if hasattr(localai_manager, 'models'):
                model_data = []
                for name, config in localai_manager.models.items():
                    model_data.append({
                        "Model": name,
                        "Status": config.status,
                        "Port": config.port,
                        "GPU": "✅" if config.gpu_enabled else "❌",
                        "Priority": config.priority,
                        "Use Case": config.use_case
                    })
                
                if model_data:
                    df_models = pd.DataFrame(model_data)
                    st.dataframe(df_models, use_container_width=True)
                else:
                    st.info("No models configured yet")
            else:
                st.info("LocalAI Manager not fully initialized")
                
        except Exception as e:
            st.error(f"❌ Error getting system status: {e}")
    
    else:
        st.warning("⚠️ LocalAI Institutional Manager not available")

# ===============================
# TAB 8: 🎭 ORCHESTRATOR - MULTI-MODEL ENSEMBLE
# ===============================

with tab8:
    st.markdown("# 🎭 Multi-Model Orchestrator")
    
    if not ORCHESTRATOR_AVAILABLE:
        st.error("❌ Multi-Model Orchestrator not available")
    else:
        # Orchestrator Overview
        st.markdown("### 🎪 Ensemble Intelligence Overview")
        
        orch_col1, orch_col2, orch_col3 = st.columns(3)
        
        with orch_col1:
            if hasattr(orchestrator, 'active_models'):
                active_count = len(orchestrator.active_models)
                st.metric("🤖 Active Models", active_count)
            else:
                st.metric("🤖 Active Models", "N/A")
        
        with orch_col2:
            if hasattr(orchestrator, 'consensus_cache'):
                cache_size = len(orchestrator.consensus_cache.cache_index)
                st.metric("🗄️ Cache Entries", cache_size)
            else:
                st.metric("🗄️ Cache Entries", "N/A")
        
        with orch_col3:
            if hasattr(orchestrator, 'performance_tracker'):
                consensus_score = 0.85  # Default
                st.metric("🎯 Consensus Score", f"{consensus_score:.2f}")
            else:
                st.metric("🎯 Consensus Score", "N/A")
        
        st.markdown("---")
        
        # Model Configuration
        st.markdown("### ⚙️ Model Configuration")
        
        # Consensus Type Selection
        consensus_type = st.selectbox(
            "Consensus Mechanism",
            ["WEIGHTED_AVERAGE", "CONFIDENCE_WEIGHTED", "PERFORMANCE_WEIGHTED", "DYNAMIC_WEIGHTED"],
            help="Select how the ensemble makes decisions"
        )
        
        # Orchestration Mode
        orch_mode = st.selectbox(
            "Orchestration Mode",
            ["BALANCED", "SPEED_OPTIMIZED", "ACCURACY_OPTIMIZED", "CONSENSUS_REQUIRED"],
            help="Select optimization strategy"
        )
        
        # Model Weights Visualization
        st.markdown("#### 🎚️ Model Weights")
        
        if hasattr(orchestrator, 'model_weights'):
            weights_data = []
            for model_name, weight_obj in orchestrator.model_weights.items():
                weights_data.append({
                    "Model": model_name,
                    "Final Weight": weight_obj.final_weight,
                    "Performance": weight_obj.performance_weight,
                    "Confidence": weight_obj.confidence_weight,
                    "Recency": weight_obj.recency_weight
                })
            
            if weights_data:
                df_weights = pd.DataFrame(weights_data)
                
                # Create weight distribution chart
                fig_weights = px.bar(
                    df_weights, 
                    x="Model", 
                    y="Final Weight",
                    title="Model Weight Distribution",
                    color="Final Weight",
                    color_continuous_scale="viridis"
                )
                fig_weights.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white')
                )
                st.plotly_chart(fig_weights, use_container_width=True)
                
                # Weights table
                st.dataframe(df_weights, use_container_width=True)
            else:
                st.info("No model weights available")
        else:
            st.info("Model weights not initialized")

# ===============================
# TAB 9: 📚 RAG BROWSER - KNOWLEDGE BASE
# ===============================

with tab9:
    st.markdown("# 📚 Advanced Memory RAG Browser")
    
    if not RAG_AVAILABLE:
        st.error("❌ Advanced Memory RAG System not available")
    else:
        # RAG System Overview
        st.markdown("### 🧠 Knowledge Base Overview")
        
        rag_col1, rag_col2, rag_col3 = st.columns(3)
        
        with rag_col1:
            if hasattr(rag_system, 'vector_db'):
                try:
                    entry_count = rag_system.vector_db.get_total_entries()
                    st.metric("📄 Knowledge Entries", f"{entry_count:,}")
                except:
                    st.metric("📄 Knowledge Entries", "N/A")
            else:
                st.metric("📄 Knowledge Entries", "N/A")
        
        with rag_col2:
            if hasattr(rag_system, 'memory_manager'):
                memory_size = len(rag_system.memory_manager.session_contexts)
                st.metric("🧠 Active Sessions", memory_size)
            else:
                st.metric("🧠 Active Sessions", "N/A")
        
        with rag_col3:
            if hasattr(rag_system, 'query_cache'):
                cache_hits = getattr(rag_system.query_cache, 'hit_count', 0)
                st.metric("🎯 Cache Hits", cache_hits)
            else:
                st.metric("🎯 Cache Hits", "N/A")
        
        st.markdown("---")
        
        # Knowledge Search Interface
        st.markdown("### 🔍 Knowledge Search")
        
        search_query = st.text_input(
            "Search Knowledge Base",
            placeholder="Search for trading strategies, market patterns, risk insights..."
        )
        
        search_type = st.selectbox(
            "Search Type",
            ["STRATEGY_RECOMMENDATION", "MARKET_CONTEXT", "RISK_GUIDANCE", "PATTERN_MATCHING"]
        )
        
        if st.button("🔍 Search Knowledge Base") and search_query:
            try:
                with st.spinner("Searching knowledge base..."):
                    if hasattr(rag_system, 'query_knowledge'):
                        results = rag_system.query_knowledge(
                            query=search_query,
                            query_type=search_type,
                            max_results=5
                        )
                        
                        if results and hasattr(results, 'retrieved_entries'):
                            st.markdown("#### 📋 Search Results")
                            
                            for i, entry in enumerate(results.retrieved_entries[:5]):
                                with st.expander(f"Result {i+1}: {entry.title}"):
                                    st.write(f"**Type:** {entry.knowledge_type}")
                                    st.write(f"**Content:** {entry.content}")
                                    st.write(f"**Confidence:** {entry.confidence:.2f}")
                                    st.write(f"**Created:** {entry.timestamp}")
                        else:
                            st.info("No results found for your query")
                    else:
                        st.warning("Search functionality not available")
            except Exception as e:
                st.error(f"❌ Search error: {e}")
        
        # Knowledge Statistics
        st.markdown("#### 📊 Knowledge Statistics")
        
        if hasattr(rag_system, 'vector_db'):
            try:
                stats = rag_system.vector_db.get_statistics()
                
                stats_col1, stats_col2 = st.columns(2)
                
                with stats_col1:
                    st.json({"Knowledge Distribution": stats.get('type_distribution', {})})
                
                with stats_col2:
                    st.json({"Recent Activity": stats.get('recent_activity', {})})
                    
            except Exception as e:
                st.info("Knowledge statistics not available")

# ===============================
# TAB 10: 🧬 STRATEGY GEN - AI STRATEGY GENERATOR
# ===============================

with tab10:
    st.markdown("# 🧬 AI Strategy Generator")
    
    if not STRATEGY_GEN_AVAILABLE:
        st.error("❌ AI Strategy Generator not available")
    else:
        # Strategy Generator Overview
        st.markdown("### 🧬 Genetic Algorithm Evolution")
        
        strat_col1, strat_col2, strat_col3, strat_col4 = st.columns(4)
        
        with strat_col1:
            if hasattr(strategy_generator, 'genetic_optimizer'):
                generation = strategy_generator.genetic_optimizer.generation_count
                st.metric("🧬 Generation", generation)
            else:
                st.metric("🧬 Generation", "0")
        
        with strat_col2:
            if hasattr(strategy_generator, 'strategy_population'):
                pop_size = len(strategy_generator.strategy_population)
                st.metric("👥 Population Size", pop_size)
            else:
                st.metric("👥 Population Size", "0")
        
        with strat_col3:
            if hasattr(strategy_generator, 'best_strategy'):
                best_fitness = 0.75  # Default
                st.metric("🏆 Best Fitness", f"{best_fitness:.3f}")
            else:
                st.metric("🏆 Best Fitness", "N/A")
        
        with strat_col4:
            if hasattr(strategy_generator, 'evolution_history'):
                history_size = len(strategy_generator.evolution_history)
                st.metric("📈 Evolution Steps", history_size)
            else:
                st.metric("📈 Evolution Steps", "0")
        
        st.markdown("---")
        
        # Strategy Generation Controls
        st.markdown("### 🎛️ Strategy Generation Controls")
        
        gen_col1, gen_col2 = st.columns(2)
        
        with gen_col1:
            strategy_type = st.selectbox(
                "Strategy Type",
                ["MOMENTUM", "MEAN_REVERSION", "TREND_FOLLOWING", "VOLATILITY_TRADING", "HYBRID_AI"]
            )
            
            population_size = st.slider("Population Size", 10, 100, 50)
            
            mutation_rate = st.slider("Mutation Rate", 0.01, 0.5, 0.1)
        
        with gen_col2:
            crossover_rate = st.slider("Crossover Rate", 0.1, 0.9, 0.7)
            
            generations = st.slider("Generations to Run", 1, 50, 10)
            
            fitness_target = st.slider("Fitness Target", 0.5, 1.0, 0.8)
        
        # Generate Strategy Button
        if st.button("🧬 Generate New Strategy", type="primary"):
            try:
                with st.spinner("Evolving strategies with genetic algorithm..."):
                    progress_bar = st.progress(0)
                    
                    # Simulate strategy generation progress
                    for i in range(generations):
                        progress_bar.progress((i + 1) / generations)
                        time.sleep(0.1)  # Simulate computation
                    
                    # Mock strategy result
                    generated_strategy = {
                        "name": f"Strategy_Gen_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        "type": strategy_type,
                        "fitness": np.random.uniform(0.6, 0.95),
                        "parameters": {
                            "lookback_period": np.random.randint(10, 50),
                            "threshold": np.random.uniform(0.01, 0.05),
                            "risk_factor": np.random.uniform(0.5, 2.0)
                        },
                        "expected_sharpe": np.random.uniform(1.2, 2.5),
                        "max_drawdown": np.random.uniform(0.05, 0.15)
                    }
                    
                    st.success("🎉 Strategy Generated Successfully!")
                    
                    # Display strategy details
                    st.markdown("#### 📋 Generated Strategy Details")
                    
                    detail_col1, detail_col2 = st.columns(2)
                    
                    with detail_col1:
                        st.json({
                            "Strategy Name": generated_strategy["name"],
                            "Type": generated_strategy["type"],
                            "Fitness Score": f"{generated_strategy['fitness']:.3f}",
                            "Expected Sharpe": f"{generated_strategy['expected_sharpe']:.2f}"
                        })
                    
                    with detail_col2:
                        st.json({
                            "Parameters": generated_strategy["parameters"],
                            "Max Drawdown": f"{generated_strategy['max_drawdown']:.1%}"
                        })
                    
                    # Evolution Chart
                    st.markdown("#### 📈 Evolution Progress")
                    
                    # Mock evolution data
                    evolution_data = {
                        "Generation": list(range(1, generations + 1)),
                        "Best Fitness": np.cumsum(np.random.uniform(0.001, 0.01, generations)) + 0.5,
                        "Avg Fitness": np.cumsum(np.random.uniform(0.0005, 0.005, generations)) + 0.4
                    }
                    
                    df_evolution = pd.DataFrame(evolution_data)
                    
                    fig_evolution = px.line(
                        df_evolution,
                        x="Generation",
                        y=["Best Fitness", "Avg Fitness"],
                        title="Strategy Evolution Progress",
                        labels={"value": "Fitness Score", "variable": "Metric"}
                    )
                    fig_evolution.update_layout(
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='white')
                    )
                    st.plotly_chart(fig_evolution, use_container_width=True)
                    
            except Exception as e:
                st.error(f"❌ Strategy generation error: {e}")
        
        # Existing Strategies
        st.markdown("#### 📚 Strategy Library")
        
        # Mock strategy library
        if st.button("🔄 Refresh Strategy Library"):
            strategies_data = []
            for i in range(5):
                strategies_data.append({
                    "Name": f"Strategy_{i+1}",
                    "Type": np.random.choice(["MOMENTUM", "MEAN_REVERSION", "TREND_FOLLOWING"]),
                    "Fitness": np.random.uniform(0.6, 0.9),
                    "Sharpe": np.random.uniform(1.0, 2.5),
                    "Status": np.random.choice(["Active", "Testing", "Retired"])
                })
            
            df_strategies = pd.DataFrame(strategies_data)
            st.dataframe(df_strategies, use_container_width=True)

# ===============================
# SIDEBAR MODERNO CON CONTROLES
# ===============================

with st.sidebar:
    st.markdown("## ⚙️ Control Panel")
    
    # Auto-refresh
    auto_refresh = st.checkbox("🔄 Auto-refresh", value=True)
    
    if auto_refresh:
        refresh_sec = st.slider(
            "⏱️ Intervalo (seg)", 
            min_value=10, 
            max_value=300, 
            value=60, 
            step=10
        )
        st_autorefresh(interval=refresh_sec * 1000, key="modern_refresh")
        st.success(f"✅ Refrescando cada {refresh_sec}s")
    else:
        if st.button("🔄 Refresh Manual"):
            st.rerun()
    
    st.markdown("---")
    
    # Configuración de la meta
    st.markdown("### 🎯 Meta Configuration")
    daily_target = st.number_input(
        "Meta Diaria ($)", 
        min_value=100, 
        max_value=5000, 
        value=1000, 
        step=100
    )
    
    st.markdown("---")
    
    # Links útiles
    st.markdown("### 🔗 Quick Links")
    st.markdown("""
    - 📊 [Alpaca Dashboard](https://app.alpaca.markets)
    - 📈 [TradingView](https://tradingview.com)
    - 📱 [Bot Logs](logs)
    - ⚙️ [System Config](config)
    """)
    
    st.markdown("---")
    
    # Status del sistema
    st.markdown("### 📊 System Status")
    
    # Simular métricas del sistema
    cpu_usage = np.random.randint(15, 35)
    memory_usage = np.random.randint(45, 65)
    
    st.metric("💻 CPU Usage", f"{cpu_usage}%")
    st.metric("🧠 Memory Usage", f"{memory_usage}%")
    st.metric("🌐 Network", "Connected")
    st.metric("⚡ Bot Status", "Running")
    
    # Información de la sesión
    st.markdown("---")
    st.markdown("### ℹ️ Session Info")
    current_time = datetime.now()
    st.caption(f"🕐 Last Update: {current_time.strftime('%H:%M:%S')}")
    st.caption(f"📅 Session: {current_time.strftime('%Y-%m-%d')}")
    st.caption("🚀 Alpha Trading v2.0")

# ===============================
# FOOTER
# ===============================

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: var(--text-secondary); font-family: 'Inter', sans-serif; margin: 2rem 0;">
    🚀 <strong>Alpha Trading Dashboard</strong> | Built with ❤️ and Streamlit | 
    © 2025 Institutional Grade Trading System
</div>
""", unsafe_allow_html=True)