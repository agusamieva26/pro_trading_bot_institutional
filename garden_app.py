import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import os

# Configuración de la página
st.set_page_config(
    page_title="Gestión de Jardinería",
    page_icon="🌱",
    layout="wide"
)

def init_database():
    """Inicializar la base de datos SQLite"""
    conn = sqlite3.connect('jardin.db')
    cursor = conn.cursor()
    
    # Crear tabla de visitas si no existe
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS visitas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATE NOT NULL,
            planta TEXT NOT NULL,
            actividad TEXT NOT NULL,
            observaciones TEXT,
            tiempo_minutos INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def registrar_visita():
    """Sección para registrar una nueva visita al jardín"""
    st.header("📝 Registrar Visita")
    
    with st.form("registro_visita"):
        col1, col2 = st.columns(2)
        
        with col1:
            fecha_visita = st.date_input(
                "Fecha de la visita",
                value=date.today()
            )
            
            planta = st.text_input(
                "Nombre de la planta",
                placeholder="Ej: Tomates, Rosas, Lavanda..."
            )
            
            actividad = st.selectbox(
                "Actividad realizada",
                ["Riego", "Poda", "Fertilización", "Siembra", "Trasplante", 
                 "Control de plagas", "Cosecha", "Limpieza", "Otro"]
            )
        
        with col2:
            tiempo_minutos = st.number_input(
                "Tiempo dedicado (minutos)",
                min_value=1,
                max_value=600,
                value=30
            )
            
            observaciones = st.text_area(
                "Observaciones",
                placeholder="Notas adicionales sobre la actividad...",
                height=100
            )
        
        submitted = st.form_submit_button("🌱 Registrar Visita")
        
        if submitted:
            if planta and actividad:
                conn = sqlite3.connect('jardin.db')
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO visitas (fecha, planta, actividad, observaciones, tiempo_minutos)
                    VALUES (?, ?, ?, ?, ?)
                ''', (fecha_visita, planta, actividad, observaciones, tiempo_minutos))
                
                conn.commit()
                conn.close()
                
                st.success(f"✅ Visita registrada exitosamente para {planta}!")
                st.rerun()
            else:
                st.error("❌ Por favor completa los campos obligatorios (Planta y Actividad)")

def ver_visitas():
    """Sección para ver todas las visitas registradas"""
    st.header("📊 Ver Visitas")
    
    conn = sqlite3.connect('jardin.db')
    
    # Cargar datos
    df = pd.read_sql_query('''
        SELECT fecha, planta, actividad, tiempo_minutos, observaciones
        FROM visitas
        ORDER BY fecha DESC
    ''', conn)
    
    conn.close()
    
    if not df.empty:
        # Filtros
        col1, col2, col3 = st.columns(3)
        
        with col1:
            plantas_unicas = ['Todas'] + sorted(df['planta'].unique().tolist())
            planta_filtro = st.selectbox("Filtrar por planta", plantas_unicas)
        
        with col2:
            actividades_unicas = ['Todas'] + sorted(df['actividad'].unique().tolist())
            actividad_filtro = st.selectbox("Filtrar por actividad", actividades_unicas)
        
        with col3:
            fecha_desde = st.date_input("Fecha desde", value=None)
        
        # Aplicar filtros
        df_filtrado = df.copy()
        
        if planta_filtro != 'Todas':
            df_filtrado = df_filtrado[df_filtrado['planta'] == planta_filtro]
        
        if actividad_filtro != 'Todas':
            df_filtrado = df_filtrado[df_filtrado['actividad'] == actividad_filtro]
        
        if fecha_desde:
            df_filtrado = df_filtrado[pd.to_datetime(df_filtrado['fecha']) >= pd.to_datetime(fecha_desde)]
        
        # Mostrar estadísticas rápidas
        if not df_filtrado.empty:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Visitas", len(df_filtrado))
            
            with col2:
                st.metric("Plantas Diferentes", df_filtrado['planta'].nunique())
            
            with col3:
                st.metric("Tiempo Total", f"{df_filtrado['tiempo_minutos'].sum()} min")
            
            with col4:
                st.metric("Promedio por Visita", f"{df_filtrado['tiempo_minutos'].mean():.1f} min")
            
            st.divider()
            
            # Tabla de datos
            st.dataframe(
                df_filtrado,
                use_container_width=True,
                column_config={
                    "fecha": st.column_config.DateColumn("Fecha"),
                    "planta": "Planta",
                    "actividad": "Actividad",
                    "tiempo_minutos": st.column_config.NumberColumn("Tiempo (min)"),
                    "observaciones": "Observaciones"
                }
            )
        else:
            st.info("No hay visitas que coincidan con los filtros aplicados.")
    else:
        st.info("🌱 Aún no hay visitas registradas. ¡Comienza registrando tu primera visita!")

def resumen_mensual():
    """Sección para ver resumen mensual"""
    st.header("📈 Resumen Mensual")
    
    conn = sqlite3.connect('jardin.db')
    
    # Cargar datos
    df = pd.read_sql_query('''
        SELECT fecha, planta, actividad, tiempo_minutos
        FROM visitas
        ORDER BY fecha DESC
    ''', conn)
    
    conn.close()
    
    if not df.empty:
        df['fecha'] = pd.to_datetime(df['fecha'])
        df['mes_año'] = df['fecha'].dt.to_period('M')
        
        # Selector de mes
        meses_disponibles = sorted(df['mes_año'].unique(), reverse=True)
        mes_seleccionado = st.selectbox(
            "Seleccionar mes",
            options=meses_disponibles,
            format_func=lambda x: x.strftime('%B %Y')
        )
        
        # Filtrar por mes seleccionado
        df_mes = df[df['mes_año'] == mes_seleccionado]
        
        if not df_mes.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📊 Estadísticas del Mes")
                
                # Métricas
                st.metric("Total Visitas", len(df_mes))
                st.metric("Plantas Atendidas", df_mes['planta'].nunique())
                st.metric("Tiempo Total", f"{df_mes['tiempo_minutos'].sum()} minutos")
                st.metric("Promedio por Día", f"{df_mes['tiempo_minutos'].sum() / df_mes['fecha'].dt.day.nunique():.1f} min/día")
                
                st.subheader("🌿 Plantas Más Atendidas")
                plantas_mes = df_mes.groupby('planta')['tiempo_minutos'].agg(['count', 'sum']).reset_index()
                plantas_mes.columns = ['Planta', 'Visitas', 'Tiempo Total (min)']
                plantas_mes = plantas_mes.sort_values('Tiempo Total (min)', ascending=False)
                st.dataframe(plantas_mes, use_container_width=True)
            
            with col2:
                st.subheader("📋 Actividades del Mes")
                actividades_mes = df_mes.groupby('actividad')['tiempo_minutos'].agg(['count', 'sum']).reset_index()
                actividades_mes.columns = ['Actividad', 'Frecuencia', 'Tiempo Total (min)']
                actividades_mes = actividades_mes.sort_values('Tiempo Total (min)', ascending=False)
                st.dataframe(actividades_mes, use_container_width=True)
                
                st.subheader("📅 Distribución por Días")
                dias_mes = df_mes.groupby(df_mes['fecha'].dt.day)['tiempo_minutos'].sum()
                st.bar_chart(dias_mes)
        else:
            st.info(f"No hay datos registrados para {mes_seleccionado.strftime('%B %Y')}")
    else:
        st.info("🌱 Aún no hay datos para mostrar resúmenes. ¡Registra algunas visitas primero!")

def main():
    """Función principal de la aplicación"""
    # Inicializar base de datos
    init_database()
    
    # Título principal
    st.title("🌱 Gestión de Jardinería")
    st.markdown("*Lleva un registro detallado del cuidado de tu jardín*")
    
    # Navegación
    tab1, tab2, tab3 = st.tabs(["📝 Registrar Visita", "📊 Ver Visitas", "📈 Resumen Mensual"])
    
    with tab1:
        registrar_visita()
    
    with tab2:
        ver_visitas()
    
    with tab3:
        resumen_mensual()

if __name__ == "__main__":
    main()