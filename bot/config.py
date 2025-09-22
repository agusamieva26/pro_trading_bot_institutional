from pydantic import BaseModel, Field
from dotenv import load_dotenv
load_dotenv()
import os


class Settings(BaseModel):
    alpaca_api_key: str = Field(default_factory=lambda: os.getenv("ALPACA_API_KEY",""))
    alpaca_secret_key: str = Field(default_factory=lambda: os.getenv("ALPACA_SECRET_KEY",""))
    alpaca_base_url: str = Field(default_factory=lambda: os.getenv("ALPACA_BASE_URL","https://paper-api.alpaca.markets"))
    data_base_url: str = Field(default_factory=lambda: os.getenv("DATA_BASE_URL","https://data.alpaca.markets"))
    mode: str = Field(default_factory=lambda: os.getenv("MODE","paper"))
    symbols: list[str] = Field(default_factory=lambda: [
        # 16 CRYPTOS (MKR/USD removido por no ser tradeable)
        "BTC/USD", "ETH/USD", "SOL/USD", "AVAX/USD", "LINK/USD", "DOGE/USD", "DOT/USD", "LTC/USD", "SHIB/USD",
        "XRP/USD", "UNI/USD", "AAVE/USD", "PEPE/USD", "BCH/USD", "CRV/USD", "GRT/USD",
        # 37 STOCKS/ETFS (25 nuevas acciones + 12 originales)
        "AAPL", "AMZN", "TSLA", "NVDA", "GOOGL", "MSFT", "META", "AMD", "NFLX", "GLD", "SPY", "QQQ",
        "AVGO", "CRM", "ADBE", "JPM", "BAC", "V", "MA", "JNJ", "PFE", "UNH", "XOM", "CVX", "CAT", "BA", 
        "KO", "PG", "WMT", "VTI", "VEA", "VWO", "VGK", "XLE", "XLF", "XLK", "XLV", "VNQ", "TLT", "IWM"
    ])
    telegram_enabled: bool = Field(default_factory=lambda: os.getenv("TELEGRAM_ENABLED","true").lower() in ("1","true","yes"))
    telegram_bot_token: str = Field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN",""))
    telegram_chat_id: str = Field(default_factory=lambda: os.getenv("TELEGRAM_CHAT_ID",""))
    openai_api_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY",""))  # 🤖 IA REAL INTEGRATION
    bar_timeframe: str = Field(default_factory=lambda: os.getenv("BAR_TIMEFRAME","1Min"))  # ⚡ SCALPING OPTIMIZADO
    initial_equity: float = 30000.0  # Valor fijo
    risk_per_trade: float = Field(default_factory=lambda: float(os.getenv("RISK_PER_TRADE","0.013")))  # AGRESIVO: 1.3% (rotación rápida)
    max_daily_loss_pct: float = Field(default_factory=lambda: float(os.getenv("MAX_DAILY_LOSS_PCT","10.0")))  # Aumentado para operar hoy
    max_gross_exposure: float = Field(default_factory=lambda: float(os.getenv("MAX_GROSS_EXPOSURE","1.00")))  # LIBERADO: Permitir operar con exposición actual
    min_cash_buffer: float = Field(default_factory=lambda: float(os.getenv("MIN_CASH_BUFFER","0.05")))  # IA FIX: 5% cash buffer para trading agresivo
    enable_extended_hours: bool = Field(default_factory=lambda: os.getenv("ENABLE_EXTENDED_HOURS","true").lower() in ("1","true","yes"))  # 🔥 PRE/POST MARKET
    enable_crypto_shorts: bool = Field(default_factory=lambda: os.getenv("ENABLE_CRYPTO_SHORTS","true").lower() in ("1","true","yes"))  # 🔥 CRYPTO SHORTS FULL
    take_profit_pct: float = Field(default_factory=lambda: float(os.getenv("TAKE_PROFIT_PCT","0.015")))  # ROTACIÓN RÁPIDA: 1.5%
    stop_loss_pct: float = Field(default_factory=lambda: float(os.getenv("STOP_LOSS_PCT","0.007")))  # ROTACIÓN RÁPIDA: 0.7%
    trailing_stop_pct: float = Field(default_factory=lambda: float(os.getenv("TRAILING_STOP_PCT","0.001")))  # ULTRA-SCALPING: 0.1%
    
    # 🎯 TRAILING STOPS & PARTIAL PROFIT SYSTEM (Nocturnal crypto optimization)
    trailing_activation_pct: float = Field(default_factory=lambda: float(os.getenv("TRAILING_ACTIVATION_PCT","0.020")))  # 2.0% gain to activate trailing
    trailing_distance_pct: float = Field(default_factory=lambda: float(os.getenv("TRAILING_DISTANCE_PCT","0.010")))  # 1.0% distance from peak to trigger stop
    partial_profit_pct: float = Field(default_factory=lambda: float(os.getenv("PARTIAL_PROFIT_PCT","0.030")))  # 3.0% gain for 50% partial close
    
    # ⏰ TIME-BASED EXIT SYSTEM (Capital rotation optimization)
    max_position_time_normal: float = Field(default_factory=lambda: float(os.getenv("MAX_POSITION_TIME_NORMAL","45")))  # 45 minutos para posiciones estancadas
    max_position_time_force: float = Field(default_factory=lambda: float(os.getenv("MAX_POSITION_TIME_FORCE","75")))  # 75 minutos cierre forzado
    min_pnl_keep_long: float = Field(default_factory=lambda: float(os.getenv("MIN_PNL_KEEP_LONG","0.012")))  # 1.2% mínimo para mantener en cierre forzado
    stagnant_pnl_min: float = Field(default_factory=lambda: float(os.getenv("STAGNANT_PNL_MIN","-0.003")))  # -0.3% límite inferior estancamiento
    stagnant_pnl_max: float = Field(default_factory=lambda: float(os.getenv("STAGNANT_PNL_MAX","0.007")))  # +0.7% límite superior estancamiento

    # 🎯 DYNAMIC DAILY TARGET
    dynamic_target_enabled: bool = Field(default_factory=lambda: os.getenv("DYNAMIC_TARGET_ENABLED","true").lower() in ("1","true","yes"))
    initial_target_capital: float = Field(default_factory=lambda: float(os.getenv("INITIAL_TARGET_CAPITAL", "30000.0")))
    initial_daily_target_usd: float = Field(default_factory=lambda: float(os.getenv("INITIAL_DAILY_TARGET_USD", "1000.0")))
    min_daily_target_usd: float = Field(default_factory=lambda: float(os.getenv("MIN_DAILY_TARGET_USD", "100.0"))) # Mínimo de $100
    
    # 🏛️ ARBITRAGE SYSTEM CONFIGURATION (CRITICAL SAFETY)
    arbitrage_mode: str = Field(default_factory=lambda: os.getenv("ARBITRAGE_MODE","simulate"))  # "simulate" or "real" - SAFETY FIRST
    arbitrage_enabled: bool = Field(default_factory=lambda: os.getenv("ARBITRAGE_ENABLED","true").lower() in ("1","true","yes"))  # Enable arbitrage subsystem
    arbitrage_max_exposure_pct: float = Field(default_factory=lambda: float(os.getenv("ARBITRAGE_MAX_EXPOSURE_PCT","0.15")))  # 15% max exposure
    arbitrage_min_profit_pct: float = Field(default_factory=lambda: float(os.getenv("ARBITRAGE_MIN_PROFIT_PCT","0.005")))  # 0.5% minimum profit
    arbitrage_max_position_usd: float = Field(default_factory=lambda: float(os.getenv("ARBITRAGE_MAX_POSITION_USD","10000")))  # $10k max per trade
    
    # 🧪 RISK MANAGEMENT TESTING CONFIGURATION
    risk_management_test_mode: bool = Field(default_factory=lambda: os.getenv("RISK_MANAGEMENT_TEST_MODE","false").lower() in ("1","true","yes"))  # Bypass kill switch for testing
    disable_kill_switch: bool = Field(default_factory=lambda: os.getenv("DISABLE_KILL_SWITCH","false").lower() in ("1","true","yes"))  # Emergency bypass for testing
    
    model_path: str = Field(default_factory=lambda: os.getenv("MODEL_PATH","models/rf_clf.pkl"))
    state_path: str = Field(default_factory=lambda: os.getenv("STATE_PATH","bot/state.json"))
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL","INFO"))
    
    # 🧠 PARÁMETROS DE ENTRENAMIENTO
    training_data_days: int = Field(default_factory=lambda: int(os.getenv("TRAINING_DATA_DAYS", "365")))
    wfo_train_window: str = Field(default_factory=lambda: os.getenv("WFO_TRAIN_WINDOW","365D"))
    wfo_test_window: str = Field(default_factory=lambda: os.getenv("WFO_TEST_WINDOW","90D"))
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

# Aplicar configuración optimizada por Optuna
try:
    from .optuna_config import apply_optimized_config
    settings = apply_optimized_config(settings)
except ImportError:
    pass  # Si no existe optuna_config, usar valores por defecto
