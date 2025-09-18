# 🤖 Pro Trading Bot Institutional

## 🚀 Sistema de Trading Institucional con IA

Bot de trading profesional con sistema de debug automático, análisis técnico avanzado y monitoreo en tiempo real.

## ✨ Características Principales

### 🧠 Sistema de IA Híbrido
- **LocalAI**: Análisis gratuito sin límites
- **OpenAI**: Análisis avanzado con GPT-4o-mini
- **Análisis técnico**: RSI, MACD, EMA, volumen, soporte/resistencia
- **Señales de trading**: BUY/SELL/HOLD con confianza

### 🔧 Sistema de Debug Automático
- **Detección automática**: Memoria, CPU, disco, errores
- **Reparación automática**: Limpieza y optimización
- **Análisis con IA**: Patrones de error inteligentes
- **Monitoreo continuo**: 24/7 sin intervención manual

### 📊 Dashboard Moderno
- **Streamlit**: Interfaz web moderna
- **Gráficos en tiempo real**: Plotly interactivo
- **Métricas del bot**: Rendimiento, señales, análisis
- **Puerto**: http://localhost:8501

### 🎯 Configuración Agresiva
- **Risk per trade**: 1.3% (ROTACIÓN RÁPIDA)
- **Take profit**: 1.5% (CIERRES FRECUENTES)
- **Stop loss**: 0.7% (ULTRA-AGRESIVO)
- **Win rate esperado**: 54.5%

## 🛠️ Instalación

### Requisitos
```bash
Python 3.8+
pip install -r requirements.txt
```

### Dependencias Principales
- `loguru`: Logging avanzado
- `streamlit`: Dashboard web
- `plotly`: Gráficos interactivos
- `psutil`: Monitoreo del sistema
- `asyncio`: Programación asíncrona

### Configuración
1. Clona el repositorio:
```bash
git clone https://github.com/agusamieva26/pro_trading_bot_institutional.git
cd pro_trading_bot_institutional
```

2. Instala dependencias:
```bash
pip install -r requirements.txt
```

3. Configura variables de entorno (opcional):
```bash
# Crear archivo .env
OPENAI_API_KEY=tu_api_key_aqui
```

## 🚀 Uso

### Iniciar el Bot Completo
```bash
python run.py
```

**El bot incluye:**
- 🤖 Trading Bot principal
- 📊 Sistema de automatización
- 🌐 Dashboard moderno
- 🔧 Debug automático

### Componentes del Sistema

#### 1. Bot Principal (`bot/main.py`)
- Análisis técnico en tiempo real
- Generación de señales de trading
- Gestión de posiciones
- Profit-taking automático

#### 2. Sistema de Debug (`bot/auto_debug_system.py`)
- Detección automática de problemas
- Reparación automática con IA
- Monitoreo continuo del sistema
- Análisis de patrones de error

#### 3. Dashboard (`dashboard_modern.py`)
- Interfaz web moderna
- Gráficos en tiempo real
- Métricas del bot
- Estado del sistema

#### 4. LocalAI Assistant (`bot/local_ai_assistant.py`)
- Análisis gratuito sin límites
- Prompts optimizados para trading
- Análisis técnico específico
- Sistema de respaldo robusto

## 📈 Funcionalidades Avanzadas

### Sistema de Debug Automático
```python
# Detección automática
issues = auto_debug_system.detect_system_issues()

# Reparación automática
await auto_debug_system.auto_fix_issues(issues)

# Monitoreo continuo
health = auto_debug_system.get_system_health()
```

### Análisis con IA
```python
# Análisis de sentimiento
sentiment = await local_ai.analyze_trading_sentiment(symbol, market_data)

# Generación de señales
signal = await local_ai.generate_trading_signal(symbol, price, technical_data)

# Resumen de mercado
summary = await local_ai.analyze_market_summary(market_data)
```

## 🔍 Monitoreo

### Estado del Sistema
- **Memoria**: Uso actual y alertas
- **CPU**: Rendimiento y optimización
- **Disco**: Espacio disponible
- **Errores**: Conteo y análisis

### Dashboard Web
- **URL**: http://localhost:8501
- **Gráficos**: Tiempo real con Plotly
- **Métricas**: Rendimiento del bot
- **Señales**: Análisis técnico actual

## 📊 Arquitectura

```
pro_trading_bot_institutional/
├── bot/
│   ├── main.py                    # Bot principal
│   ├── auto_debug_system.py       # Debug automático
│   ├── local_ai_assistant.py      # IA Local
│   ├── config.py                  # Configuración
│   └── ...
├── dashboard_modern.py            # Dashboard Streamlit
├── run.py                         # Punto de entrada
├── requirements.txt               # Dependencias
└── README.md                      # Documentación
```

## 🎯 Configuración de Trading

### Parámetros Agresivos
- **Risk per trade**: 1.3%
- **Take profit**: 1.5%
- **Stop loss**: 0.7%
- **Win rate**: 54.5%

### Símbolos Soportados
- BTC/USD, ETH/USD, SOL/USD
- Y más criptomonedas principales

## 🔧 Troubleshooting

### Problemas Comunes
1. **Error de memoria**: El sistema de debug lo repara automáticamente
2. **CPU alto**: Optimización automática aplicada
3. **Disco lleno**: Limpieza automática de archivos temporales
4. **Errores de IA**: Sistema de respaldo activado

### Logs
```bash
# Ver logs en tiempo real
tail -f logs/trading_bot.log
```

## 📝 Changelog

### v1.0.0 - Sistema de Debug Automático
- ✅ Implementado sistema de debug automático con IA
- ✅ Detección automática de problemas del sistema
- ✅ Reparación automática sin intervención manual
- ✅ Análisis de patrones de error con LocalAI
- ✅ Monitoreo continuo 24/7
- ✅ Integración completa en run.py

### Mejoras de LocalAI
- ✅ Prompts optimizados para análisis técnico
- ✅ Sistema de respaldo robusto
- ✅ Análisis específico de trading
- ✅ Generación de señales mejorada

## 🤝 Contribuciones

1. Fork el repositorio
2. Crea una rama para tu feature
3. Commit tus cambios
4. Push a la rama
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver `LICENSE` para más detalles.

## 👨‍💻 Autor

**Agus Amieva**
- GitHub: [@agusamieva26](https://github.com/agusamieva26)
- Repositorio: [pro_trading_bot_institutional](https://github.com/agusamieva26/pro_trading_bot_institutional)

## 🚨 Disclaimer

Este bot es para fines educativos y de investigación. El trading conlleva riesgos significativos. Usa bajo tu propia responsabilidad.

---

**Estado**: ✅ Sistema completo funcionando  
**Última actualización**: 14 de Septiembre 2025  
**Versión**: 1.0.0 con Debug Automático