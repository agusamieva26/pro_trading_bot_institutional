# dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timezone
import os
from pathlib import Path
from streamlit_autorefresh import st_autorefresh  # Para recarga automática

# Módulos del bot
from bot.config import settings
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOrdersRequest
from alpaca.trading.enums import QueryOrderStatus

# Configuración de la página
st.set_page_config(page_title="📊 Dashboard del Bot", layout="wide")
st.title("🚀 Bot de Trading Institucional")
st.markdown("### Monitor en tiempo real | Modo Paper")

# Cliente de Alpaca (en caché)
@st.cache_resource
def get_alpaca_client():
    return TradingClient(
        api_key=settings.alpaca_api_key,
        secret_key=settings.alpaca_secret_key,
        paper=(settings.mode == "paper")
    )

client = get_alpaca_client()

# Funciones para obtener datos de Alpaca
def get_account_info():
    try:
        account = client.get_account()
        return {
            "equity": float(account.equity),
            "cash": float(account.cash),
            "portfolio_value": float(account.portfolio_value),
            "buying_power": float(getattr(account, "buying_power", 0)),
            "status": account.status,
            "initial_portfolio_value": float(getattr(account, "initial_portfolio_value", account.portfolio_value)),
            "last_equity": float(getattr(account, "last_equity", account.equity))
        }
    except Exception as e:
        st.error(f"❌ No se pudo obtener cuenta: {e}")
        return {}

def calculate_daily_change(account_info):
    """Calcula el cambio diario basado en equity actual vs inicial del día"""
    if not account_info:
        return 0.0, 0.0
    
    try:
        current_equity = account_info.get("equity", 0)
        last_equity = account_info.get("last_equity", current_equity)
        
        # Daily change en dólares
        daily_change = current_equity - last_equity
        
        # Daily change en porcentaje
        daily_change_pct = (daily_change / last_equity * 100) if last_equity > 0 else 0.0
        
        return daily_change, daily_change_pct
    except Exception:
        return 0.0, 0.0

def get_total_unrealized_pnl():
    """Obtiene el P&L no realizado total de todas las posiciones"""
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
            "symbol": pos.symbol,
            "qty": float(pos.qty),
            "avg_entry_price": float(pos.avg_entry_price),
            "current_price": float(pos.current_price),
            "unrealized_pl": float(pos.unrealized_pl),
            "unrealized_pl_pct": (float(pos.unrealized_pl) / (float(pos.avg_entry_price) * abs(float(pos.qty))) * 100) if pos.avg_entry_price != 0 else 0.0,
            "market_value": float(pos.market_value)
        } for pos in positions]
    except Exception as e:
        st.warning(f"⚠️ No se pudieron obtener posiciones: {e}")
        return []

def get_open_orders():
    try:
        req = GetOrdersRequest(status=QueryOrderStatus.OPEN)
        orders = client.get_orders(req)
        return [{
            "symbol": order.symbol,
            "side": order.side.value,
            "qty": float(order.qty),
            "type": order.order_type.value,
            "filled": float(order.filled_qty) if order.filled_qty else 0,
            "status": order.status.value
        } for order in orders]
    except Exception as e:
        st.warning(f"⚠️ No se pudieron obtener órdenes: {e}")
        return []

# --- Cargar datos del CSV ---
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

# --- Tabs ---
tab1, tab2, tab3, tab4 = st.tabs(["📈 Principal", "💼 Cuenta", "📊 Trades", "📅 Reporte"])

# --- TAB 1: PRINCIPAL ---
with tab1:
    # Métricas principales mejoradas
    account_info = get_account_info()
    daily_change, daily_change_pct = calculate_daily_change(account_info)
    total_unrealized = get_total_unrealized_pnl()
    
    # Primera fila: Métricas principales financieras
    st.markdown("### 💰 Métricas Financieras")
    col1, col2, col3 = st.columns(3)
    
    # Daily Change con color
    daily_color = "normal" if daily_change == 0 else ("inverse" if daily_change > 0 else "off")
    col1.metric(
        label="📈 Daily Change", 
        value=f"${daily_change:+,.2f}",
        delta=f"{daily_change_pct:+.2f}%",
        delta_color=daily_color
    )
    
    # Buying Power
    col2.metric(
        label="💵 Buying Power", 
        value=f"${account_info.get('buying_power', 0):,.2f}"
    )
    
    # Cash disponible
    col3.metric(
        label="💰 Cash", 
        value=f"${account_info.get('cash', 0):,.2f}"
    )
    
    # Segunda fila: P&L y Portfolio
    col4, col5, col6 = st.columns(3)
    
    # Total Unrealized P&L con color
    unrealized_color = "normal" if total_unrealized == 0 else ("inverse" if total_unrealized > 0 else "off")
    col4.metric(
        label="📊 Unrealized P&L", 
        value=f"${total_unrealized:+,.2f}",
        delta_color=unrealized_color
    )
    
    # Equity total
    col5.metric(
        label="🏦 Equity", 
        value=f"${account_info.get('equity', 0):,.2f}"
    )
    
    # Estado de cuenta
    status_emoji = "🟢" if account_info.get("status") == "ACTIVE" else "🔴"
    col6.metric(
        label=f"{status_emoji} Estado", 
        value=account_info.get("status", "N/A")
    )

    # Posiciones abiertas
    st.subheader("💼 Posiciones Abiertas")
    positions = get_open_positions()
    if positions:
        df_pos = pd.DataFrame(positions)
        # ✅ Corregido: nombres consistentes con los del DataFrame
        st.dataframe(
            df_pos.style.format({
                "avg_entry_price": "${:.2f}",
                "current_price": "${:.2f}",
                "unrealized_pl": "${:.2f}",
                "unrealized_pl_pct": "{:.2f}%",
                "market_value": "${:.2f}"
            }),
            width='stretch'
        )
    else:
        st.info("No hay posiciones abiertas.")

# --- TAB 2: CUENTA (Detallado) ---
with tab2:
    st.subheader("📋 Estado de la Cuenta")
    if account_info:
        st.json(account_info)
    else:
        st.warning("No se pudo cargar la cuenta.")

    st.subheader("🛒 Órdenes Abiertas")
    orders = get_open_orders()
    if orders:
        df_orders = pd.DataFrame(orders)
        st.dataframe(df_orders, width='stretch')
    else:
        st.info("No hay órdenes abiertas.")

# --- TAB 3: TRADES ---
with tab3:
    st.subheader("📊 Historial de Trades")
    df = load_trades()
    if not df.empty:
        # Gráfico de P&L acumulado (solo trades cerrados)
        df_closed = df[df["status"] == "closed"].copy()
        if "realized_pnl" in df_closed.columns and not df_closed.empty:
            df_closed = df_closed.sort_values("exit_date")
            df_closed["cum_pnl"] = df_closed["realized_pnl"].cumsum()
            fig = px.line(
                df_closed,
                x="exit_date",
                y="cum_pnl",
                title="P&L Acumulado (Trades Cerrados)",
                labels={"cum_pnl": "P&L ($)", "exit_date": "Fecha"}
            )
            st.plotly_chart(fig, use_column_width=True)

        st.dataframe(df, width='stretch')
    else:
        st.warning("No se encontró `trades_log.csv` o está vacío.")

# --- TAB 4: REPORTE DIARIO ---
with tab4:
    st.subheader("📅 Reportes Diarios")
    if os.path.exists("reports/"):
        report_files = [f for f in os.listdir("reports/") if f.startswith("reporte_")]
        if report_files:
            selected_report = st.selectbox("Selecciona un reporte", sorted(report_files, reverse=True))
            report_path = f"reports/{selected_report}"
            st.write(f"**Reporte: {selected_report}**")

            # Leer Excel
            df_resumen = pd.read_excel(report_path, sheet_name="Resumen")
            df_trades = pd.read_excel(report_path, sheet_name="Trades")

            st.dataframe(df_resumen, width='stretch')
            st.dataframe(df_trades, width='stretch')
        else:
            st.info("No hay reportes generados aún.")
    else:
        st.warning("Carpeta `reports/` no encontrada.")

# --- Control de recarga ---
st.sidebar.header("⚙️ Control")
auto_refresh = st.sidebar.checkbox("Auto-recarga", value=True)

if auto_refresh:
    refresh_sec = st.sidebar.number_input(
        "Refresco (segundos)", min_value=10, max_value=600, value=60, step=10
    )
    st_autorefresh(interval=refresh_sec * 1000, key="datarefresh")
else:
    st.sidebar.button("Recargar ahora")