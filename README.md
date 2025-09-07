# Pro Trading Bot — Institutional‑Lite Upgrade

Este paquete amplía el bot con:
- **Backtesting de portafolio** (multi‑símbolo) con *walk‑forward* usando `vectorbt` (o fallback simple si no está instalado).
- **Optimización automática** de hiperparámetros con `optuna` (búsqueda bayesiana o aleatoria).
- **Dashboard en vivo** con `streamlit` para monitoreo y control básico.
- **Gestión de riesgo** y *position sizing* compatibles con el motor anterior.

> Nota: esta es una base sólida para investigación y despliegue en paper trading. Ajusta a tu infraestructura antes de operar en real.

## Setup rápido

```bash
python -m venv .venv && source .venv/bin/activate  # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # coloca tus claves Alpaca (paper por defecto)
```

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
python -m bot.main
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

