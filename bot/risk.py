# bot/risk.py
from typing import NamedTuple, Optional, Callable, Any
from .util import logger

# Importar configuraciones personalizadas por símbolo
SYMBOL_CONFIGS_AVAILABLE = False
get_symbol_config: Optional[Callable[[str], Any]] = None
get_symbol_tp_sl: Optional[Callable[[str], tuple[float, float]]] = None
SymbolConfig: Optional[type] = None

try:
    from .symbol_configs import get_symbol_tp_sl, get_symbol_config, SymbolConfig
    SYMBOL_CONFIGS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠️ Configuraciones personalizadas no disponibles: {e}")
    # Las variables ya están definidas como None arriba

class RiskParams(NamedTuple):
    take_profit_pct: float = 0.015     # 1.5% FALLBACK - Take profit por defecto
    stop_loss_pct: float = 0.007       # 0.7% FALLBACK - Stop loss por defecto
    trail_stop_atr: float = 1.5        # 1.5x ATR para scalping
    max_risk_per_trade: float = 0.025  # 2.5% del equity - Riesgo controlado
    MAX_EXPOSURE_PER_SYMBOL = 0.20     # Máximo 20% del equity por símbolo
    max_gross_exposure: float = 0.3    # 30% del equity - CONSERVADOR


def compute_brackets(entry_price: float, side: str, params: RiskParams, symbol: Optional[str] = None):
    """
    💎 CALCULA TAKE PROFIT Y STOP LOSS PERSONALIZADO POR SÍMBOLO
    
    Usa configuraciones específicas por activo si están disponibles,
    sino utiliza los parámetros por defecto de RiskParams.
    
    Args:
        entry_price: Precio de entrada
        side: "long" o "short"
        params: Parámetros de riesgo por defecto
        symbol: Símbolo del activo (ej: "BTC/USD")
    
    Returns:
        tuple: (take_profit, stop_loss, trailing_stop)
    """
    # Obtener configuraciones personalizadas si están disponibles
    if symbol and SYMBOL_CONFIGS_AVAILABLE and get_symbol_config is not None:
        try:
            # Obtener configuración específica del símbolo
            symbol_config = get_symbol_config(symbol)
            if symbol_config:
                tp_pct = symbol_config.take_profit_pct
                sl_pct = symbol_config.stop_loss_pct
                
                logger.info(f"📊 {symbol}: TP={tp_pct:.1%}, SL={sl_pct:.1%} ({symbol_config.volatility_tier})")
            else:
                tp_pct = params.take_profit_pct
                sl_pct = params.stop_loss_pct
            
        except Exception as e:
            logger.warning(f"⚠️ Error obteniendo config para {symbol}: {e}. Usando fallback.")
            tp_pct = params.take_profit_pct
            sl_pct = params.stop_loss_pct
    else:
        # Usar configuración por defecto
        tp_pct = params.take_profit_pct
        sl_pct = params.stop_loss_pct
        
        if symbol:
            logger.info(f"📊 {symbol}: Usando TP={tp_pct:.1%}, SL={sl_pct:.1%} (por defecto)")
    
    # Calcular precios de take profit y stop loss
    if side == "long":
        tp = entry_price * (1 + tp_pct)
        sl = entry_price * (1 - sl_pct)
    elif side == "short":
        tp = entry_price * (1 - tp_pct)
        sl = entry_price * (1 + sl_pct)
    else:
        tp, sl = None, None

    # Trailing stop opcional (por ahora None)
    trail = None  
    
    return tp, sl, trail


def get_symbol_risk_multiplier(symbol: str) -> float:
    """
    🎯 OBTIENE MULTIPLICADOR DE RIESGO PARA SÍMBOLO ESPECÍFICO
    
    Basado en la volatilidad del activo, ajusta el tamaño de posición.
    
    Returns:
        float: Multiplicador de riesgo (0.1 = 10% del riesgo normal)
    """
    if not SYMBOL_CONFIGS_AVAILABLE or get_symbol_config is None:
        return 1.0
        
    try:
        config = get_symbol_config(symbol)
        
        # Multiplicadores basados en volatilidad
        volatility_multipliers = {
            "ultra_low": 1.5,    # Más agresivo en activos estables
            "low": 1.2,         # Ligeramente más agresivo
            "medium": 1.0,      # Riesgo normal
            "high": 0.7,        # Más conservador
            "ultra_high": 0.4   # Muy conservador
        }
        
        multiplier = volatility_multipliers.get(config.volatility_tier, 1.0)
        
        # Limitar posición máxima según configuración
        max_position_limit = config.max_position_size
        
        logger.debug(f"🎯 {symbol}: Volatilidad {config.volatility_tier} → Multiplicador {multiplier:.1f}x, Max {max_position_limit:.1%}")
        
        return multiplier
        
    except Exception as e:
        logger.warning(f"⚠️ Error calculando multiplicador para {symbol}: {e}")
        return 1.0


def get_symbol_max_position_size(symbol: str, default_max: float = 0.20) -> float:
    """
    📏 OBTIENE TAMAÑO MÁXIMO DE POSICIÓN PARA SÍMBOLO
    
    Returns:
        float: Porcentaje máximo de equity para este símbolo (0.0-1.0)
    """
    if not SYMBOL_CONFIGS_AVAILABLE or get_symbol_config is None:
        return default_max
        
    try:
        config = get_symbol_config(symbol)
        return config.max_position_size
        
    except Exception as e:
        logger.warning(f"⚠️ Error obteniendo max position para {symbol}: {e}")
        return default_max