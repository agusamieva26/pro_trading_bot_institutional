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
    bar_timeframe: str = Field(default_factory=lambda: os.getenv("BAR_TIMEFRAME","1Min"))  # ⚡ SCALPING OPTIMIZADO
    initial_equity: float = 30000.0  # Valor fijo
    risk_per_trade: float = Field(default_factory=lambda: float(os.getenv("RISK_PER_TRADE","0.0235")))  # OPTIMIZADO: 2.35% (50% reducción)
    max_daily_loss_pct: float = Field(default_factory=lambda: float(os.getenv("MAX_DAILY_LOSS_PCT","10.0")))  # Aumentado para operar hoy
    max_gross_exposure: float = Field(default_factory=lambda: float(os.getenv("MAX_GROSS_EXPOSURE","0.3")))  # CONSERVADOR: Exposición limitada para evitar over-leverage
    enable_extended_hours: bool = Field(default_factory=lambda: os.getenv("ENABLE_EXTENDED_HOURS","true").lower() in ("1","true","yes"))  # 🔥 PRE/POST MARKET
    enable_crypto_shorts: bool = Field(default_factory=lambda: os.getenv("ENABLE_CRYPTO_SHORTS","true").lower() in ("1","true","yes"))  # 🔥 CRYPTO SHORTS FULL
    take_profit_pct: float = Field(default_factory=lambda: float(os.getenv("TAKE_PROFIT_PCT","0.03")))  # SCALPING REALISTA: 3%
    stop_loss_pct: float = Field(default_factory=lambda: float(os.getenv("STOP_LOSS_PCT","0.01")))  # SCALPING REALISTA: 1%
    trailing_stop_pct: float = Field(default_factory=lambda: float(os.getenv("TRAILING_STOP_PCT","0.001")))  # ULTRA-SCALPING: 0.1%
    model_path: str = Field(default_factory=lambda: os.getenv("MODEL_PATH","models/rf_clf.pkl"))
    state_path: str = Field(default_factory=lambda: os.getenv("STATE_PATH","bot/state.json"))
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL","INFO"))
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

