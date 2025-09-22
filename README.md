# Pro Trading Bot — Institutional‑Lite Upgrade

Este bot de trading utiliza una **arquitectura híbrida avanzada**:
- **Modelos Predictivos Locales**: Entrena y optimiza modelos de Machine Learning (Random Forest, XGBoost) en tu propia máquina para generar señales de trading.
- **Inteligencia Artificial por API**: Usa proveedores externos (como Together.ai, Groq, OpenAI) para capacidades de lenguaje y razonamiento avanzado, eliminando la necesidad de descargar modelos de lenguaje pesados.

**Características Principales:**
- **Entrenamiento y Optimización Local**: Tienes control total sobre el entrenamiento (`bot.trainer`) y la optimización (`bot.optimizer`) de los modelos que deciden las operaciones.
- **IA Generativa por API**: Accede a modelos de lenguaje de última generación para análisis, chat y reportes sin sobrecargar tu servidor.
- **Dashboard en Vivo:** Monitorea el rendimiento y las operaciones en tiempo real con `streamlit`.
- **Gestión de Riesgo Avanzada:** Incluye `position sizing` dinámico y gestión de `drawdown`.
- **Sistema Híbrido AGUS 2.0:** Combina múltiples fuentes de inteligencia para tomar decisiones de trading robustas.

> Nota: esta es una base sólida para investigación y despliegue en paper trading. Ajusta a tu infraestructura antes de operar en real.

## Setup rápido

```bash
python3 -m venv .venv && source .venv/bin/activate  # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
# Este comando leerá el archivo `requirements.txt` e instalará todas las librerías necesarias.
cp .env.example .env
```

## Configuración de API Keys

Para que el bot funcione correctamente, necesitas configurar las siguientes claves de API en tu archivo `.env`.

### 1. Alpaca (Para Trading)

-   `ALPACA_API_KEY`
-   `ALPACA_SECRET_KEY`

**Cómo conseguirlas:**
1.  Ve a Alpaca y crea una cuenta.
2.  Selecciona el modo "Paper Trading" (trading simulado).
3.  En el menú de la derecha, ve a "API Keys".
4.  Haz clic en "Generate New Key" y copia la `API Key ID` y la `Secret Key`.

### 2. IA Principal (Compatible con OpenAI)

-   `QWEN_API_KEY`

El bot está configurado para usar un proveedor de API compatible con OpenAI. Por defecto, usa **Together.ai**, pero puedes cambiarlo fácilmente.

> **Nota Importante:** Aunque el modelo (Qwen) se encuentra en Hugging Face, el bot **no usa la API de Hugging Face directamente**. Se conecta a un proveedor como Together.ai que ofrece una API compatible con el formato de OpenAI. Por lo tanto, necesitas una clave de API de uno de estos proveedores, no de Hugging Face.

**Cómo conseguirla (Ejemplo con Together.ai):**
1.  Regístrate en Together.ai.
2.  Una vez dentro, ve a la sección "API Keys" en el menú de la izquierda.
3.  Copia tu clave y pégala en el valor de `QWEN_API_KEY`.

**¿Tiene costo?**
No, **obtener la clave de API es gratis**. Al registrarte, Together.ai te da **créditos gratuitos** (generalmente $25 USD) para que puedas probar la API. Una vez que se agotan los créditos, el servicio funciona con un modelo de "pago por uso" (pay-as-you-go), que suele ser muy económico para los modelos que usa este bot. Los créditos iniciales son más que suficientes para configurar y probar todo.

### 2.1. Alternativas a Together.ai

¡Sí! Puedes usar cualquier proveedor que ofrezca una API compatible con OpenAI. Aquí tienes algunas alternativas populares:

-   **Groq**: Famoso por su **velocidad extremadamente alta**. A menudo tiene un generoso nivel gratuito.
-   **Anyscale**: Ofrece acceso a modelos de código abierto y es conocido por su fiabilidad.
-   **Perplexity Labs**: Proporciona acceso a modelos populares a través de una API compatible.
-   **Fireworks.ai**: Otra plataforma optimizada para servir modelos de código abierto.

#### Ejemplo: Cómo configurar Groq

Groq es una excelente opción si buscas respuestas casi instantáneas.

1.  Regístrate en Groq.
2.  Obtén tu API Key en la sección correspondiente.
3.  Modifica tu archivo `.env` con las siguientes variables:

```bash
# .env
QWEN_API_KEY="tu-api-key-de-groq"
QWEN_API_BASE_URL="https://api.groq.com/openai/v1"
QWEN_MODEL_NAME="llama3-8b-8192" # O el modelo que prefieras de Groq
```

### 3. OpenAI (Opcional, para IA secundaria)

-   `OPENAI_API_KEY`

**Cómo conseguirla:**
1.  Ve a OpenAI Platform y crea una cuenta.
2.  Añade un método de pago (necesario para usar la API, aunque los costos iniciales son muy bajos).
3.  Ve a la sección "API keys" y crea una nueva "Secret key".

## Flujos principales

1) **Entrenamiento ML**  
```bash
python -m bot.trainer --symbols SPY AAPL MSFT --start 2020-01-01 --end 2024-12-31
```

2) **Backtest de portafolio + walk‑forward**  
```bash
python -m bot.portfolio_backtest --symbols SPY AAPL MSFT --start 2022-01-01 --end 2024-12-31
```

3) **Optimización automática con Optuna**  
```bash
python -m bot.optimizer --symbols SPY AAPL MSFT --start 2021-01-01 --end 2024-12-31 --trials 50
```

4) **Dashboard en vivo (Streamlit)**  
```bash
streamlit run dashboard/app.py
```

5) **Ejecución del bot (paper)**  
```bash
python start_and_monitor.py
```

## Estructura
```
bot/
  (módulos base)
  portfolio_backtest.py   # backtest multicartera + walk-forward
  optimizer.py            # búsqueda de hiperparámetros con Optuna
dashboard/
  app.py                  # panel en vivo
research/
  walkforward_template.ipynb
```

## Requisitos
Consulta `requirements.txt`. Si `vectorbt` no se instala en tu entorno, el backtester usará un modo simple de fallback.
