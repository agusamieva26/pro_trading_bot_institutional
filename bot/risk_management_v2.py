"""
Risk Management Dinámico 2.0 - Sistema avanzado de gestión de riesgo.
Incluye volatility clustering, market regime detection y stops dinámicos.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from .util import logger
from .config import settings


class AdvancedRiskManager:
    """
    Sistema avanzado de gestión de riesgo con detección de regímenes de mercado
    y volatility clustering para optimizar stops y position sizing.
    """
    
    def __init__(self):
        self.volatility_window = 20
        self.regime_detection_window = 50
        self.clustering_threshold = 1.5  # Para detectar volatility clustering
        
    def detect_market_regime(self, price_data: pd.DataFrame) -> Dict:
        """
        Detecta el régimen de mercado: trending vs ranging vs volatile.
        """
        if len(price_data) < self.regime_detection_window:
            return {"regime": "unknown", "confidence": 0.0}
        
        prices = price_data["close"].tail(self.regime_detection_window)
        
        # Calcular métricas de régimen
        returns = prices.pct_change().dropna()
        volatility = returns.std() * np.sqrt(252)  # Anualizada
        
        # Trend strength usando regresión lineal
        x = np.arange(len(prices))
        trend_coef = np.polyfit(x, prices, 1)[0]
        trend_strength = abs(trend_coef) / prices.mean()
        
        # Range-bound detection
        high_low_ratio = (prices.max() - prices.min()) / prices.mean()
        
        # Determinar régimen
        if trend_strength > 0.001 and high_low_ratio > 0.1:
            regime = "trending"
            confidence = min(trend_strength * 1000, 1.0)
        elif high_low_ratio < 0.05 and volatility < 0.2:
            regime = "ranging"
            confidence = 1.0 - high_low_ratio * 20
        elif volatility > 0.4:
            regime = "volatile"
            confidence = min(volatility / 0.4, 1.0)
        else:
            regime = "neutral"
            confidence = 0.5
        
        return {
            "regime": regime,
            "confidence": confidence,
            "volatility": volatility,
            "trend_strength": trend_strength,
            "range_ratio": high_low_ratio
        }
    
    def detect_volatility_clustering(self, price_data: pd.DataFrame) -> Dict:
        """
        Detecta volatility clustering para ajustar tamaños de posición.
        """
        if len(price_data) < self.volatility_window:
            return {"clustering": False, "vol_regime": "normal"}
        
        returns = price_data["close"].pct_change().dropna()
        
        # Volatilidad rolling
        rolling_vol = returns.rolling(window=5).std()
        current_vol = rolling_vol.iloc[-1]
        avg_vol = rolling_vol.tail(self.volatility_window).mean()
        
        vol_ratio = current_vol / avg_vol if avg_vol > 0 else 1.0
        
        # Detectar clustering
        is_clustering = vol_ratio > self.clustering_threshold
        
        if vol_ratio > 2.0:
            vol_regime = "extreme"
        elif vol_ratio > self.clustering_threshold:
            vol_regime = "high"
        elif vol_ratio < 0.7:
            vol_regime = "low"
        else:
            vol_regime = "normal"
        
        return {
            "clustering": is_clustering,
            "vol_regime": vol_regime,
            "vol_ratio": vol_ratio,
            "current_vol": current_vol,
            "avg_vol": avg_vol
        }
    
    def calculate_dynamic_stops(self, symbol: str, price: float, atr: float, 
                               signal_strength: float, market_regime: Dict, 
                               vol_clustering: Dict) -> Dict:
        """
        Calcula stops dinámicos basados en régimen de mercado y volatilidad.
        """
        base_stop_loss = settings.stop_loss_pct
        base_take_profit = settings.take_profit_pct
        
        # Ajustes por régimen de mercado
        regime = market_regime["regime"]
        confidence = market_regime["confidence"]
        
        if regime == "trending":
            # En trending: stops más amplios, profits más largos
            stop_multiplier = 1.2 + (confidence * 0.3)
            profit_multiplier = 1.3 + (confidence * 0.5)
        elif regime == "ranging":
            # En ranging: stops más ajustados, profits conservadores
            stop_multiplier = 0.8 - (confidence * 0.2)
            profit_multiplier = 0.9 - (confidence * 0.1)
        elif regime == "volatile":
            # En volátil: stops muy amplios para evitar ruido
            stop_multiplier = 1.5 + (confidence * 0.5)
            profit_multiplier = 1.4 + (confidence * 0.6)
        else:
            # Neutral: usar configuración base
            stop_multiplier = 1.0
            profit_multiplier = 1.0
        
        # Ajustes por volatility clustering
        vol_regime = vol_clustering["vol_regime"]
        vol_ratio = vol_clustering["vol_ratio"]
        
        if vol_regime == "extreme":
            stop_multiplier *= 1.8
            profit_multiplier *= 1.6
        elif vol_regime == "high":
            stop_multiplier *= 1.3
            profit_multiplier *= 1.2
        elif vol_regime == "low":
            stop_multiplier *= 0.8
            profit_multiplier *= 0.9
        
        # Ajuste por fuerza de señal
        signal_multiplier = 0.8 + (abs(signal_strength) * 0.4)
        
        # Calcular stops finales
        dynamic_stop_loss = base_stop_loss * stop_multiplier * signal_multiplier
        dynamic_take_profit = base_take_profit * profit_multiplier * signal_multiplier
        
        # Límites de seguridad
        dynamic_stop_loss = max(min(dynamic_stop_loss, 0.05), 0.003)  # Entre 0.3% y 5%
        dynamic_take_profit = max(min(dynamic_take_profit, 0.15), 0.01)  # Entre 1% y 15%
        
        return {
            "stop_loss_pct": dynamic_stop_loss,
            "take_profit_pct": dynamic_take_profit,
            "stop_price": price * (1 - dynamic_stop_loss) if signal_strength > 0 else price * (1 + dynamic_stop_loss),
            "profit_price": price * (1 + dynamic_take_profit) if signal_strength > 0 else price * (1 - dynamic_take_profit),
            "regime_adjustment": stop_multiplier,
            "vol_adjustment": vol_ratio,
            "signal_adjustment": signal_multiplier
        }
    
    def calculate_position_size_v2(self, equity: float, price: float, atr: float,
                                  signal_strength: float, market_regime: Dict,
                                  vol_clustering: Dict) -> Dict:
        """
        Calcula tamaño de posición optimizado considerando régimen y volatilidad.
        """
        base_risk = settings.risk_per_trade
        
        # Ajuste por régimen de mercado
        regime = market_regime["regime"]
        confidence = market_regime["confidence"]
        
        if regime == "trending" and confidence > 0.7:
            # Mayor confianza en trending markets
            regime_multiplier = 1.2
        elif regime == "ranging":
            # Menor riesgo en ranging markets
            regime_multiplier = 0.8
        elif regime == "volatile":
            # Mucho menor riesgo en mercados volátiles
            regime_multiplier = 0.6
        else:
            regime_multiplier = 1.0
        
        # Ajuste por volatility clustering
        vol_regime = vol_clustering["vol_regime"]
        
        if vol_regime == "extreme":
            vol_multiplier = 0.5  # Reducir drasticamente en volatilidad extrema
        elif vol_regime == "high":
            vol_multiplier = 0.7
        elif vol_regime == "low":
            vol_multiplier = 1.1  # Ligeramente más agresivo en baja volatilidad
        else:
            vol_multiplier = 1.0
        
        # Ajuste por fuerza de señal
        signal_multiplier = 0.7 + (abs(signal_strength) * 0.6)
        
        # Risk final ajustado
        adjusted_risk = base_risk * regime_multiplier * vol_multiplier * signal_multiplier
        
        # Límites de seguridad
        adjusted_risk = max(min(adjusted_risk, 0.02), 0.001)  # Entre 0.1% y 2%
        
        # Calcular shares basado en ATR y risk ajustado
        risk_amount = equity * adjusted_risk
        atr_stop_distance = atr * 2.0  # 2 ATRs como stop dinámico
        
        if atr_stop_distance > 0:
            shares = risk_amount / atr_stop_distance
        else:
            shares = risk_amount / (price * 0.02)  # Fallback: 2% del precio
        
        return {
            "shares": shares,
            "risk_amount": risk_amount,
            "adjusted_risk_pct": adjusted_risk,
            "regime_multiplier": regime_multiplier,
            "vol_multiplier": vol_multiplier,
            "signal_multiplier": signal_multiplier,
            "atr_stop_distance": atr_stop_distance
        }


def analyze_risk_environment(symbols_data: Dict[str, pd.DataFrame]) -> Dict:
    """
    Analiza el entorno general de riesgo del mercado.
    """
    risk_manager = AdvancedRiskManager()
    
    market_regimes = {}
    vol_conditions = {}
    
    # Analizar cada símbolo
    for symbol, df in symbols_data.items():
        if not df.empty:
            market_regimes[symbol] = risk_manager.detect_market_regime(df)
            vol_conditions[symbol] = risk_manager.detect_volatility_clustering(df)
    
    # Calcular condiciones agregadas del mercado
    if market_regimes:
        regime_counts = {}
        avg_volatility = 0
        high_vol_count = 0
        
        for symbol, regime_data in market_regimes.items():
            regime = regime_data["regime"]
            regime_counts[regime] = regime_counts.get(regime, 0) + 1
            avg_volatility += regime_data.get("volatility", 0)
            
            if vol_conditions.get(symbol, {}).get("vol_regime") in ["high", "extreme"]:
                high_vol_count += 1
        
        dominant_regime = max(regime_counts, key=regime_counts.get)
        avg_volatility /= len(market_regimes)
        high_vol_ratio = high_vol_count / len(market_regimes)
        
        # Determinar condición general del mercado
        if high_vol_ratio > 0.6:
            market_condition = "STRESS"
        elif dominant_regime == "volatile":
            market_condition = "VOLATILE"
        elif dominant_regime == "trending":
            market_condition = "TRENDING"
        elif dominant_regime == "ranging":
            market_condition = "RANGING"
        else:
            market_condition = "NEUTRAL"
        
        logger.info(f"🌍 Entorno de mercado: {market_condition} | Vol promedio: {avg_volatility:.2f} | Alto vol: {high_vol_ratio:.1%}")
        
        return {
            "market_condition": market_condition,
            "dominant_regime": dominant_regime,
            "avg_volatility": avg_volatility,
            "high_vol_ratio": high_vol_ratio,
            "symbol_regimes": market_regimes,
            "symbol_vol_conditions": vol_conditions
        }
    
    return {"market_condition": "UNKNOWN", "symbol_regimes": {}, "symbol_vol_conditions": {}}