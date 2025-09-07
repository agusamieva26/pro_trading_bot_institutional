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
    symbols: list[str] = Field(default_factory=lambda: [s.strip() for s in os.getenv("SYMBOLS","SPY").split(",") if s.strip()])
    telegram_enabled: bool = Field(default_factory=lambda: os.getenv("TELEGRAM_ENABLED","true").lower() in ("1","true","yes"))
    telegram_bot_token: str = Field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN",""))
    telegram_chat_id: str = Field(default_factory=lambda: os.getenv("TELEGRAM_CHAT_ID",""))
    bar_timeframe: str = Field(default_factory=lambda: os.getenv("BAR_TIMEFRAME","1Hour"))
    initial_equity: float = 30000.0  # Valor fijo
    risk_per_trade: float = Field(default_factory=lambda: float(os.getenv("RISK_PER_TRADE","0.004")))
    max_daily_loss_pct: float = Field(default_factory=lambda: float(os.getenv("MAX_DAILY_LOSS_PCT","2.03")))
    max_gross_exposure: float = Field(default_factory=lambda: float(os.getenv("MAX_GROSS_EXPOSURE","1.5")))
    take_profit_pct: float = Field(default_factory=lambda: float(os.getenv("TAKE_PROFIT_PCT","0.025")))
    stop_loss_pct: float = Field(default_factory=lambda: float(os.getenv("STOP_LOSS_PCT","0.02")))
    trailing_stop_pct: float = Field(default_factory=lambda: float(os.getenv("TRAILING_STOP_PCT","0.01")))
    model_path: str = Field(default_factory=lambda: os.getenv("MODEL_PATH","models/rf_clf.pkl"))
    state_path: str = Field(default_factory=lambda: os.getenv("STATE_PATH","bot/state.json"))
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL","INFO"))
    wfo_train_window: str = Field(default_factory=lambda: os.getenv("WFO_TRAIN_WINDOW","365D"))
    wfo_test_window: str = Field(default_factory=lambda: os.getenv("WFO_TEST_WINDOW","90D"))
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

