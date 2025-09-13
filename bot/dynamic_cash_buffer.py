"""
Dynamic Cash Buffer System 💰
Sistema inteligente de cash buffer que se adapta automáticamente a las condiciones del mercado.
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from .util import logger
from .config import settings


class DynamicCashBuffer:
    """
    Sistema de cash buffer dinámico que se adapta automáticamente según:
    - Volatilidad del mercado
    - Performance reciente del bot
    - Número de posiciones abiertas
    - Liquidez disponible
    """
    
    def __init__(self):
        self.state_file = "bot/dynamic_cash_buffer_state.json"
        self.load_state()
        
        # Configuración base
        self.min_buffer = 0.02  # 2% mínimo absoluto
        self.max_buffer = 0.25  # 25% máximo absoluto
        self.base_buffer = settings.min_cash_buffer  # 5% base configurado
        
        # Thresholds para modos
        self.aggressive_threshold = 0.05  # ≤5%
        self.normal_threshold = 0.12      # ≤12%
        self.conservative_threshold = 0.25 # ≤25%
        
        # Factores de adaptación
        self.volatility_factor = 0.0
        self.performance_factor = 0.0
        self.position_factor = 0.0
        self.liquidity_factor = 0.0
        
    def load_state(self):
        """Carga el estado persistente del sistema."""
        try:
            with open(self.state_file, 'r') as f:
                self.state = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.state = {
                "last_update": None,
                "volatility_history": [],
                "performance_history": [],
                "buffer_history": [],
                "mode_changes": [],
                "override_active": False,
                "override_expires": None
            }
    
    def save_state(self):
        """Guarda el estado persistente."""
        try:
            self.state["last_update"] = datetime.now().isoformat()
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.warning(f"⚠️ Error guardando estado dynamic cash buffer: {e}")
    
    def calculate_market_volatility(self) -> float:
        """
        Calcula la volatilidad del mercado basada en precios recientes.
        Returns: float entre 0.0 (baja vol) y 1.0+ (alta vol)
        """
        try:
            from .data import fetch_bars
            
            # Obtener datos de SPY como proxy del mercado
            spy_data = fetch_bars("SPY", min_bars=48)  # Últimas 48 barras
            if spy_data is None or len(spy_data) < 10:
                logger.warning("⚠️ No hay datos de SPY para volatilidad, usando valor por defecto")
                return 0.5
            
            # Calcular volatilidad intraday (más sensible)
            returns = spy_data['close'].pct_change().dropna()
            current_vol = returns.rolling(window=12).std().iloc[-1] * np.sqrt(24)  # Anualizada
            
            # Normalizar volatilidad (0.15 = normal, 0.30+ = alta)
            normalized_vol = min(current_vol / 0.15, 2.0)
            
            # Guardar en historial
            self.state["volatility_history"].append({
                "timestamp": datetime.now().isoformat(),
                "value": float(normalized_vol)
            })
            
            # Mantener solo últimas 72 horas de datos
            cutoff = datetime.now() - timedelta(hours=72)
            self.state["volatility_history"] = [
                item for item in self.state["volatility_history"] 
                if datetime.fromisoformat(item["timestamp"]) > cutoff
            ]
            
            return float(normalized_vol)
            
        except Exception as e:
            logger.warning(f"⚠️ Error calculando volatilidad: {e}")
            return 0.5  # Valor neutral por defecto
    
    def calculate_performance_factor(self) -> float:
        """
        Calcula factor de performance basado en PnL reciente.
        Returns: float entre -1.0 (malas pérdidas) y 1.0 (buenas ganancias)
        """
        try:
            from .state import BotState
            from alpaca.trading.client import TradingClient
            
            # Obtener performance del account de Alpaca directamente
            client = TradingClient(
                api_key=settings.alpaca_api_key,
                secret_key=settings.alpaca_secret_key,
                paper=(settings.mode == "paper")
            )
            
            account = client.get_account()
            # Usar unrealized_pl para performance reciente
            unrealized_pl = float(getattr(account, 'unrealized_pl', 0.0) or 0.0)
            equity = float(getattr(account, 'equity', 0.0) or 0.0)
            
            if equity <= 0:
                return 0.0
            
            # Calcular performance como porcentaje del equity
            daily_pnl_pct = unrealized_pl / equity
            weekly_pnl_pct = daily_pnl_pct  # Por simplicidad, usar el mismo valor
            
            # Factor combinado (70% diario, 30% semanal)
            performance = (daily_pnl_pct * 0.7 + weekly_pnl_pct * 0.3)
            
            # Normalizar: -10% = -1.0, +10% = +1.0
            normalized_performance = max(-1.0, min(1.0, performance / 0.10))
            
            # Guardar en historial
            self.state["performance_history"].append({
                "timestamp": datetime.now().isoformat(),
                "daily_pnl": daily_pnl_pct,
                "weekly_pnl": weekly_pnl_pct,
                "normalized": float(normalized_performance)
            })
            
            # Mantener solo últimas 168 horas (7 días)
            cutoff = datetime.now() - timedelta(hours=168)
            self.state["performance_history"] = [
                item for item in self.state["performance_history"] 
                if datetime.fromisoformat(item["timestamp"]) > cutoff
            ]
            
            return float(normalized_performance)
            
        except Exception as e:
            logger.warning(f"⚠️ Error calculando factor de performance: {e}")
            return 0.0
    
    def calculate_position_factor(self) -> float:
        """
        Calcula factor basado en número de posiciones abiertas.
        Returns: float entre 0.0 (pocas posiciones) y 1.0 (muchas posiciones)
        """
        try:
            from alpaca.trading.client import TradingClient
            
            client = TradingClient(
                api_key=settings.alpaca_api_key,
                secret_key=settings.alpaca_secret_key,
                paper=(settings.mode == "paper")
            )
            
            positions = client.get_all_positions()
            num_positions = len(positions)
            
            # Normalizar: 0 posiciones = 0.0, 20+ posiciones = 1.0
            position_factor = min(1.0, num_positions / 20.0)
            
            return float(position_factor)
            
        except Exception as e:
            logger.warning(f"⚠️ Error calculando factor de posiciones: {e}")
            return 0.5
    
    def calculate_liquidity_factor(self) -> float:
        """
        Calcula factor de liquidez disponible.
        Returns: float entre 0.0 (baja liquidez) y 1.0 (alta liquidez)
        """
        try:
            from alpaca.trading.client import TradingClient
            
            client = TradingClient(
                api_key=settings.alpaca_api_key,
                secret_key=settings.alpaca_secret_key,
                paper=(settings.mode == "paper")
            )
            
            account = client.get_account()
            cash = float(getattr(account, 'cash', 0.0) or 0.0)
            equity = float(getattr(account, 'equity', 0.0) or 0.0)
            
            if equity <= 0:
                return 0.0
                
            # Factor de liquidez: cash/equity ratio
            cash_ratio = cash / equity
            
            # Normalizar: 50%+ cash = alta liquidez (1.0), 5%- cash = baja liquidez (0.0)
            liquidity_factor = max(0.0, min(1.0, (cash_ratio - 0.05) / 0.45))
            
            return float(liquidity_factor)
            
        except Exception as e:
            logger.warning(f"⚠️ Error calculando factor de liquidez: {e}")
            return 0.5
    
    def calculate_dynamic_buffer(self) -> Tuple[float, str, Dict]:
        """
        Calcula el cash buffer dinámico basado en todos los factores.
        
        Returns:
            Tuple[float, str, Dict]: (buffer_percentage, mode, factors_info)
        """
        
        # Verificar override activo
        if self.is_override_active():
            override_buffer = self.state.get("override_buffer", 0.01)  # 1% en override
            return override_buffer, "OVERRIDE", {"reason": "Manual override activo"}
        
        # Calcular todos los factores
        volatility = self.calculate_market_volatility()
        performance = self.calculate_performance_factor()
        positions = self.calculate_position_factor()
        liquidity = self.calculate_liquidity_factor()
        
        # Almacenar factores para logging
        self.volatility_factor = volatility
        self.performance_factor = performance
        self.position_factor = positions
        self.liquidity_factor = liquidity
        
        # Algoritmo de cálculo dinámico
        buffer = self.base_buffer  # Comenzar con 5% base
        
        # 1. Ajuste por VOLATILIDAD (factor más importante)
        # Alta volatilidad → más buffer (factor: 0.0-2.0)
        volatility_adjustment = (volatility - 0.5) * 0.08  # ±4% max
        buffer += volatility_adjustment
        
        # 2. Ajuste por PERFORMANCE (segundo más importante)
        # Buena performance → menos buffer, mala performance → más buffer
        performance_adjustment = -performance * 0.05  # ±5% max
        buffer += performance_adjustment
        
        # 3. Ajuste por POSICIONES ABIERTAS
        # Más posiciones → más buffer (mayor riesgo)
        position_adjustment = positions * 0.03  # +3% max
        buffer += position_adjustment
        
        # 4. Ajuste por LIQUIDEZ
        # Alta liquidez → menos buffer, baja liquidez → más buffer
        liquidity_adjustment = -(liquidity - 0.5) * 0.02  # ±1% max
        buffer += liquidity_adjustment
        
        # Aplicar límites absolutos
        buffer = max(self.min_buffer, min(self.max_buffer, buffer))
        
        # Determinar modo
        if buffer <= self.aggressive_threshold:
            mode = "AGRESIVO"
        elif buffer <= self.normal_threshold:
            mode = "NORMAL"
        else:
            mode = "CONSERVADOR"
        
        # Información detallada
        factors_info = {
            "volatility": volatility,
            "performance": performance,
            "positions": positions,
            "liquidity": liquidity,
            "base_buffer": self.base_buffer,
            "adjustments": {
                "volatility": volatility_adjustment,
                "performance": performance_adjustment,
                "positions": position_adjustment,
                "liquidity": liquidity_adjustment
            },
            "final_buffer": buffer
        }
        
        # Guardar en historial
        self.state["buffer_history"].append({
            "timestamp": datetime.now().isoformat(),
            "buffer": float(buffer),
            "mode": mode,
            "factors": factors_info
        })
        
        # Mantener solo últimas 24 horas
        cutoff = datetime.now() - timedelta(hours=24)
        self.state["buffer_history"] = [
            item for item in self.state["buffer_history"] 
            if datetime.fromisoformat(item["timestamp"]) > cutoff
        ]
        
        self.save_state()
        
        return float(buffer), mode, factors_info
    
    def set_override(self, buffer_pct: float, duration_minutes: int = 60):
        """
        Activa override manual del cash buffer por tiempo limitado.
        
        Args:
            buffer_pct: Porcentaje de cash buffer (0.01 = 1%)
            duration_minutes: Duración en minutos del override
        """
        expires = datetime.now() + timedelta(minutes=duration_minutes)
        
        self.state["override_active"] = True
        self.state["override_buffer"] = float(buffer_pct)
        self.state["override_expires"] = expires.isoformat()
        
        self.state["mode_changes"].append({
            "timestamp": datetime.now().isoformat(),
            "action": "override_activated",
            "buffer": float(buffer_pct),
            "duration": duration_minutes
        })
        
        self.save_state()
        
        logger.critical(f"🚨 OVERRIDE ACTIVADO: Cash buffer {buffer_pct:.1%} por {duration_minutes}min hasta {expires.strftime('%H:%M:%S')}")
    
    def clear_override(self):
        """Desactiva el override manual."""
        if self.state.get("override_active", False):
            self.state["override_active"] = False
            self.state["override_expires"] = None
            self.state["override_buffer"] = None
            
            self.state["mode_changes"].append({
                "timestamp": datetime.now().isoformat(),
                "action": "override_cleared"
            })
            
            self.save_state()
            logger.info("✅ OVERRIDE DESACTIVADO: Volviendo a buffer dinámico")
    
    def is_override_active(self) -> bool:
        """Verifica si hay un override activo y válido."""
        if not self.state.get("override_active", False):
            return False
        
        expires_str = self.state.get("override_expires")
        if not expires_str:
            return False
        
        try:
            expires = datetime.fromisoformat(expires_str)
            if datetime.now() > expires:
                # Override expirado
                self.clear_override()
                return False
            return True
        except Exception:
            self.clear_override()
            return False
    
    def get_current_buffer(self) -> Tuple[float, str, Dict]:
        """
        Obtiene el cash buffer actual optimizado para el momento.
        
        Returns:
            Tuple[float, str, Dict]: (buffer_percentage, mode, info)
        """
        return self.calculate_dynamic_buffer()
    
    def emergency_ultra_aggressive_mode(self, duration_minutes: int = 30):
        """
        Activa modo ultra-agresivo para recuperación de emergencia.
        
        Args:
            duration_minutes: Duración en minutos (por defecto 30min)
        """
        buffer = 0.01  # 1% ultra-agresivo
        self.set_override(buffer, duration_minutes)
        
        logger.critical(f"🔥 MODO ULTRA-AGRESIVO ACTIVADO: Cash buffer 1% por {duration_minutes} minutos")
        logger.critical("⚠️ RIESGO EXTREMO: Trading con mínimo cash buffer para recuperación")
    
    def get_buffer_stats(self) -> Dict:
        """Obtiene estadísticas del comportamiento del buffer."""
        if not self.state["buffer_history"]:
            return {"error": "No hay historial disponible"}
        
        recent_buffers = [item["buffer"] for item in self.state["buffer_history"][-24:]]  # Últimas 24 horas
        
        return {
            "current": self.get_current_buffer(),
            "stats_24h": {
                "avg": np.mean(recent_buffers),
                "min": np.min(recent_buffers),
                "max": np.max(recent_buffers),
                "std": np.std(recent_buffers)
            },
            "mode_distribution": self._get_mode_distribution(),
            "override_active": self.is_override_active(),
            "factors": {
                "volatility": self.volatility_factor,
                "performance": self.performance_factor,
                "positions": self.position_factor,
                "liquidity": self.liquidity_factor
            }
        }
    
    def _get_mode_distribution(self) -> Dict:
        """Calcula distribución de modos en las últimas 24h."""
        if not self.state["buffer_history"]:
            return {}
        
        modes = [item["mode"] for item in self.state["buffer_history"][-24:]]
        from collections import Counter
        mode_counts = Counter(modes)
        
        total = len(modes)
        if total == 0:
            return {}
        
        return {mode: count/total for mode, count in mode_counts.items()}


# Global instance
dynamic_cash_buffer = DynamicCashBuffer()


def get_dynamic_cash_buffer() -> Tuple[float, str, Dict]:
    """
    Función helper para obtener el cash buffer dinámico actual.
    
    Returns:
        Tuple[float, str, Dict]: (buffer_percentage, mode, detailed_info)
    """
    return dynamic_cash_buffer.get_current_buffer()


def activate_emergency_mode(duration_minutes: int = 30) -> str:
    """
    Activa modo de emergencia ultra-agresivo.
    
    Args:
        duration_minutes: Duración en minutos
        
    Returns:
        str: Mensaje de confirmación
    """
    dynamic_cash_buffer.emergency_ultra_aggressive_mode(duration_minutes)
    return f"🔥 Modo ultra-agresivo activado por {duration_minutes} minutos"


def get_buffer_diagnostics() -> str:
    """
    Obtiene diagnóstico completo del sistema de buffer dinámico.
    
    Returns:
        str: Reporte detallado del estado del sistema
    """
    stats = dynamic_cash_buffer.get_buffer_stats()
    
    if "error" in stats:
        return f"❌ Error en diagnóstico: {stats['error']}"
    
    current_buffer, mode, info = stats["current"]
    
    report = f"""
📊 DIAGNÓSTICO CASH BUFFER DINÁMICO

🎯 ESTADO ACTUAL:
   Buffer: {current_buffer:.1%} | Modo: {mode}
   Override: {'🔥 ACTIVO' if stats['override_active'] else '✅ Inactivo'}

📈 FACTORES ACTUALES:
   📊 Volatilidad: {info['volatility']:.2f} (0.5=normal)
   💰 Performance: {info['performance']:.2f} (-1=mal, +1=bueno) 
   📊 Posiciones: {info['positions']:.2f} (0=pocas, 1=muchas)
   💧 Liquidez: {info['liquidity']:.2f} (0=baja, 1=alta)

📊 ESTADÍSTICAS 24H:
   Promedio: {stats['stats_24h']['avg']:.1%}
   Rango: {stats['stats_24h']['min']:.1%} - {stats['stats_24h']['max']:.1%}
   Desv.Std: {stats['stats_24h']['std']:.1%}

🎭 DISTRIBUCIÓN MODOS:
"""
    
    for mode, pct in stats['mode_distribution'].items():
        report += f"   {mode}: {pct:.1%}\n"
    
    return report.strip()