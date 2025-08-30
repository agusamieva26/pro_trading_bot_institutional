from loguru import logger
import sys, os, json, datetime as dt
from .config import settings

logger.remove()
logger.add(sys.stderr, level=settings.log_level)

def jdump(obj, path:str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=str)

def jload(path:str, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default

def now_utc():
    return dt.datetime.now(dt.timezone.utc)
