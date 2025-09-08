# Overview

This is a sophisticated institutional-grade trading bot written in Python that combines machine learning, technical analysis, and risk management for automated trading. The system integrates with Alpaca Markets for paper/live trading and supports both equity and cryptocurrency markets. It features a comprehensive backtesting framework, hyperparameter optimization, live monitoring dashboard, and automated reporting capabilities.

## Recent Changes (2025-09-08)

**Performance & Diversification Optimization:**
- Implemented parallel data fetching with ThreadPoolExecutor (4 threads), reducing analysis time from 8+ seconds to 2-3 seconds
- Enhanced strategy.py with global model caching and signal stability filtering for improved performance
- Added professional institutional-grade logging format: "📊 LONG {symbol}: score={score:+.3f}, qty={qty:.6f}"
- **CRITICAL:** Fixed capital management - limited BTC to maximum 40% allocation (was using 90% causing insufficient funds)
- Implemented diversification controls: minimum 30% capital reserved for other assets, preventing over-concentration
- Enhanced position sizing: adaptive allocation based on signal strength (25%/15%/8% for strong/medium/weak signals)
- Improved cash tracking system eliminating "reservado" confusion in execution logging
- Removed MATIC/USD from symbol list due to consistent data availability issues

The bot employs a hybrid trading strategy that combines rule-based technical indicators (EMA crossovers, RSI, MACD) with machine learning predictions using Random Forest classifiers. It includes advanced risk management features like position sizing based on volatility targeting, Kelly criterion optimization, and exposure limits.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Core Trading Engine
- **Strategy Module**: Hybrid approach combining technical indicators (EMA, RSI, MACD, ATR) with Random Forest ML predictions
- **Risk Management**: Volatility-based position sizing, Kelly criterion optimization, stop-loss/take-profit brackets
- **Execution Engine**: Order placement with fractional share support, minimum notional validation, and slippage protection
- **State Management**: Persistent JSON-based state tracking for equity, daily P&L, and position monitoring

## Data Pipeline
- **Market Data**: Alpaca Markets API integration for real-time and historical data (stocks and crypto)
- **Feature Engineering**: Technical indicators calculation with rolling windows and volatility metrics
- **Data Storage**: CSV-based trade logging with comprehensive entry/exit tracking

## Machine Learning Framework
- **Model Training**: Random Forest classifier with feature preparation and target generation
- **Backtesting**: Multi-symbol portfolio backtesting with walk-forward analysis using vectorbt (with fallback)
- **Optimization**: Bayesian hyperparameter optimization using Optuna for strategy tuning
- **Auto-tuning**: Dynamic risk parameter adjustment based on recent performance

## Monitoring and Reporting
- **Live Dashboard**: Streamlit-based real-time monitoring with portfolio metrics and position tracking
- **Automated Reporting**: Daily Excel reports with P&L analysis, trade details, and performance metrics
- **Alert System**: Telegram integration for trade notifications and risk alerts

## Configuration Management
- **Environment-based**: Pydantic settings with .env file support for API keys and parameters
- **Dynamic Config**: Auto-tuning system that adjusts risk parameters based on performance
- **Multi-mode**: Support for paper trading and live trading environments

# External Dependencies

## Trading Infrastructure
- **Alpaca Markets API**: Primary broker integration for order execution and market data
- **alpaca-py**: Official Python SDK for trading and data APIs

## Machine Learning Stack
- **scikit-learn**: Random Forest classifier and model persistence
- **pandas/numpy**: Data manipulation and numerical computations
- **joblib**: Model serialization and loading

## Backtesting and Optimization
- **vectorbt**: Advanced vectorized backtesting framework (optional dependency)
- **optuna**: Bayesian optimization for hyperparameter tuning

## Monitoring and Visualization
- **streamlit**: Web-based dashboard for live monitoring
- **plotly**: Interactive charting and visualization
- **streamlit-autorefresh**: Auto-refresh capability for real-time updates

## Notifications and Reporting
- **Telegram Bot API**: Trade alerts and notifications
- **openpyxl**: Excel report generation for daily summaries

## Utilities and Infrastructure
- **python-dotenv**: Environment variable management
- **pydantic**: Configuration validation and settings management
- **loguru**: Advanced logging with structured output
- **tenacity**: Retry logic for API calls and error handling
- **schedule**: Task scheduling for automated reporting
- **pytz**: Timezone handling for market hours and reporting