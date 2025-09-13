# Overview

This project is an institutional-grade automated trading bot written in Python, designed for both equity and cryptocurrency markets. It integrates machine learning, technical analysis, and robust risk management strategies to facilitate autonomous trading. The system aims for continuous self-improvement through automated training and optimization cycles, targeting significant annual net profits with minimal manual intervention. Key capabilities include comprehensive backtesting, hyperparameter optimization, real-time monitoring, and automated reporting, all integrated with Alpaca Markets for trading execution.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Core Trading Engine
- **Strategy Module**: Employs a hybrid approach combining technical indicators (EMA, RSI, MACD, ATR) and Fibonacci analysis with Random Forest machine learning predictions.
- **Fibonacci Integration**: Real-time calculation of support/resistance levels and trend analysis, contributing 25% to signal weighting.
- **Risk Management**: Features volatility-based position sizing, Optuna-optimized parameters, dynamic stop-loss/take-profit brackets, and an auto-take-profit mechanism at $1000 daily. Includes intelligent profit management distributing 40% for reinvestment and protecting 60% as net gain.
- **Execution Engine**: Handles order placement with fractional share support, minimum notional validation, and slippage protection. Includes intelligent crypto shorting by dynamically acquiring tokens only when needed.
- **State Management**: Persistent JSON-based tracking of equity, daily P&L, and position monitoring.
- **Automation**: Fully automated bi-weekly training, weekly Optuna optimization, and daily performance reporting. Smart triggers (e.g., win rate <50%, drawdown >5%) initiate emergency training/optimization.
- **🤖 24/7 Intelligent Monitoring System**: Advanced AGUS-powered monitoring with automatic error detection, auto-diagnosis, and auto-correction. Monitors system health every 30 seconds, detects critical losses (>$1000 or >5%), and automatically triggers recovery protocols including service restarts, memory cleanup, and emergency position management.

## Data Pipeline
- **Market Data**: Integrates with Alpaca Markets API for real-time and historical stock and cryptocurrency data.
- **Feature Engineering**: Calculates technical indicators and volatility metrics using rolling windows.
- **Data Storage**: Logs trades to CSV, capturing comprehensive entry/exit details.

## Machine Learning Framework
- **Model Training**: Utilizes a Random Forest classifier trained on extensive datasets with 12 features, including three Fibonacci-based features (fib_support, fib_resistance, fib_trend). Addresses score clustering issues for unique and realistic ML scores per symbol.
- **Backtesting**: Supports multi-symbol portfolio backtesting with walk-forward analysis.
- **Optimization**: Uses Optuna for ultra-fast Bayesian hyperparameter optimization to determine optimal trading parameters (e.g., risk_per_trade=0.5%, take_profit=5%, stop_loss=1%, expected_win_rate=54.5%).
- **Auto-tuning**: Dynamically adjusts risk parameters based on recent performance and market conditions.
- **Multi-Timeframe Analysis**: Incorporates 5min, 15min, 1H, and 4H timeframes for signal confirmation, classifying signal quality.
- **Sentiment Analysis**: Integrates Fear & Greed Index for contrarian signals and dynamic position sizing adjustments.

## Monitoring and Reporting
- **Live Dashboard**: Streamlit-based real-time monitoring of portfolio metrics and position tracking.
- **Automated Reporting**: Generates daily Excel reports detailing P&L analysis, trade specifics, and performance metrics.
- **Alert System**: Telegram integration for immediate trade notifications and risk alerts.
- **🧠 AGUS Intelligent Monitoring**: 24/7 autonomous monitoring system that automatically detects critical errors, performs root cause analysis, and executes corrective actions. Features include auto-recovery (service restart, memory cleanup, signal reset), emergency loss response protocols, and intelligent alert analysis with automated fixes based on AGUS recommendations.

## Configuration Management
- **Environment-based**: Pydantic settings with `.env` file support for API keys and parameters.
- **Dynamic Config**: Adapts parameters based on performance, market conditions (volatile, trending, ranging), and sentiment.
- **Centralized Symbol Management**: Unified normalization and classification of assets (stocks, crypto, ETFs) for diverse analysis (e.g., 17 cryptos + 37 stocks/ETFs).
- **Multi-mode**: Supports both paper and live trading environments.

# External Dependencies

## Trading Infrastructure
- **Alpaca Markets API**: Primary broker for order execution and market data.
- **alpaca-py**: Official Python SDK for Alpaca.

## Machine Learning Stack
- **scikit-learn**: For Random Forest classification and model persistence.
- **pandas/numpy**: For data manipulation and numerical computations.
- **joblib**: For model serialization and loading.

## Backtesting and Optimization
- **vectorbt**: Advanced vectorized backtesting framework.
- **optuna**: For hyperparameter tuning and optimization.

## Monitoring and Visualization
- **streamlit**: For the web-based live monitoring dashboard.
- **plotly**: For interactive charting and data visualization.
- **streamlit-autorefresh**: For real-time dashboard updates.

## Notifications and Reporting
- **Telegram Bot API**: For trade alerts and notifications.
- **openpyxl**: For generating daily Excel reports.

## Utilities and Infrastructure
- **python-dotenv**: For managing environment variables.
- **pydantic**: For configuration validation and settings.
- **loguru**: For advanced logging.
- **tenacity**: For handling retry logic in API calls.
- **schedule**: For task scheduling and automated reporting.
- **pytz**: For timezone handling.