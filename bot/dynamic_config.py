"""
Sistema de configuración dinámica adaptiva que ajusta parámetros
basado en condiciones de mercado y rendimiento histórico.
"""

import json
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pathlib import Path
from .util import logger
from .config import settings


class DynamicConfigManager:
    """
    Gestor de configuración dinámica que adapta parámetros del bot
    basado en condiciones de mercado, rendimiento y volatilidad.
    """
    
    def __init__(self):
        self.config_file = Path("bot/dynamic_config.json")
        self.performance_window = 50  # Trades para evaluación
        self.adaptation_threshold = 0.1  # 10% cambio mínimo para ajustes
        
        # Configuración base y rangos
        self.base_config = {
            'risk_per_trade': settings.risk_per_trade,
            'take_profit_pct': settings.take_profit_pct,
            'stop_loss_pct': settings.stop_loss_pct,
            'max_gross_exposure': settings.max_gross_exposure
        }
        
        # Rangos permitidos para ajustes dinámicos - CLAMPED para seguridad
        self.config_ranges = {
            'risk_per_trade': (0.002, 0.006),      # 0.2% - 0.6% (reducido)
            'take_profit_pct': (0.02, 0.08),       # 2% - 8% (reducido)
            'stop_loss_pct': (0.005, 0.02),        # 0.5% - 2% (reducido)
            'max_gross_exposure': (0.30, 0.50)     # 0.3x - 0.5x (HARD CLAMP)
        }
        
        # Estados de configuración
        self.current_config = self.base_config.copy()
        self.config_history = []
        
        # Cargar configuración existente
        self.load_config()
    
    def load_config(self):
        """
        Carga configuración dinámica desde archivo.
        """
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self.current_config = data.get('current_config', self.base_config)
                    self.config_history = data.get('history', [])
                    logger.info(f"📋 Configuración dinámica cargada: {len(self.config_history)} ajustes históricos")
            else:
                logger.info("📋 Usando configuración base - archivo dinámico no existe")
        except Exception as e:
            logger.warning(f"⚠️ Error cargando configuración dinámica: {e}")
            self.current_config = self.base_config.copy()
    
    def save_config(self):
        """
        Guarda configuración dinámica actual.
        """
        try:
            data = {
                'current_config': self.current_config,
                'history': self.config_history[-100:],  # Mantener últimos 100 cambios
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"❌ Error guardando configuración dinámica: {e}")
    
    def analyze_recent_performance(self, trades_file: str = "trades_log.csv") -> Dict:
        """
        Analiza rendimiento reciente para ajustes de configuración.
        """
        try:
            if not Path(trades_file).exists():
                return {'win_rate': 0.5, 'avg_profit': 0, 'avg_loss': 0, 'trades_count': 0}
            
            df = pd.read_csv(trades_file)
            
            if df.empty or len(df) < 10:
                return {'win_rate': 0.5, 'avg_profit': 0, 'avg_loss': 0, 'trades_count': len(df)}
            
            # Analizar últimos trades
            recent_trades = df.tail(self.performance_window)
            
            # Calcular P&L si existe columna
            if 'pnl' in recent_trades.columns:
                pnl_data = recent_trades['pnl'].dropna()
            elif 'exit_price' in recent_trades.columns and 'entry_price' in recent_trades.columns:
                # Calcular P&L básico
                pnl_data = (recent_trades['exit_price'] - recent_trades['entry_price']) / recent_trades['entry_price']
            else:
                return {'win_rate': 0.5, 'avg_profit': 0, 'avg_loss': 0, 'trades_count': len(recent_trades)}
            
            # Métricas de rendimiento
            winning_trades = pnl_data[pnl_data > 0]
            losing_trades = pnl_data[pnl_data < 0]
            
            win_rate = len(winning_trades) / len(pnl_data) if len(pnl_data) > 0 else 0.5
            avg_profit = winning_trades.mean() if len(winning_trades) > 0 else 0
            avg_loss = abs(losing_trades.mean()) if len(losing_trades) > 0 else 0
            
            # Volatilidad de returns
            return_volatility = pnl_data.std() if len(pnl_data) > 0 else 0
            
            return {
                'win_rate': win_rate,
                'avg_profit': avg_profit,
                'avg_loss': avg_loss,
                'return_volatility': return_volatility,
                'trades_count': len(recent_trades),
                'recent_pnl': pnl_data.sum()
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Error analizando rendimiento: {e}")
            return {'win_rate': 0.5, 'avg_profit': 0, 'avg_loss': 0, 'trades_count': 0}
    
    def calculate_config_adjustments(self, performance_metrics: Dict, 
                                   market_condition: str = "normal") -> Dict:
        """
        Calcula ajustes de configuración basados en rendimiento y condiciones de mercado.
        """
        adjustments = {}
        win_rate = performance_metrics.get('win_rate', 0.5)
        avg_profit = performance_metrics.get('avg_profit', 0)
        avg_loss = performance_metrics.get('avg_loss', 0)
        volatility = performance_metrics.get('return_volatility', 0)
        trades_count = performance_metrics.get('trades_count', 0)
        
        if trades_count < 20:  # Datos insuficientes
            return adjustments
        
        # Ajuste de risk_per_trade basado en win rate
        current_risk = self.current_config['risk_per_trade']
        if win_rate > 0.6:  # Alto win rate
            risk_adjustment = min(current_risk * 1.1, self.config_ranges['risk_per_trade'][1])
        elif win_rate < 0.4:  # Bajo win rate
            risk_adjustment = max(current_risk * 0.9, self.config_ranges['risk_per_trade'][0])
        else:
            risk_adjustment = current_risk
        
        if abs(risk_adjustment - current_risk) > current_risk * self.adaptation_threshold:
            adjustments['risk_per_trade'] = risk_adjustment
        
        # Ajuste de take_profit basado en avg_profit
        current_tp = self.current_config['take_profit_pct']
        if avg_profit > 0.03 and win_rate > 0.5:  # Profits grandes, aumentar target
            tp_adjustment = min(current_tp * 1.05, self.config_ranges['take_profit_pct'][1])
        elif avg_profit < 0.01 and win_rate < 0.5:  # Profits pequeños, reducir target
            tp_adjustment = max(current_tp * 0.95, self.config_ranges['take_profit_pct'][0])
        else:
            tp_adjustment = current_tp
        
        if abs(tp_adjustment - current_tp) > current_tp * self.adaptation_threshold:
            adjustments['take_profit_pct'] = tp_adjustment
        
        # Ajuste de stop_loss basado en avg_loss
        current_sl = self.current_config['stop_loss_pct']
        if avg_loss > 0.02:  # Pérdidas grandes, stop más ajustado
            sl_adjustment = max(current_sl * 0.95, self.config_ranges['stop_loss_pct'][0])
        elif avg_loss < 0.005 and volatility > 0.02:  # Pérdidas pequeñas pero alta volatilidad
            sl_adjustment = min(current_sl * 1.05, self.config_ranges['stop_loss_pct'][1])
        else:
            sl_adjustment = current_sl
        
        if abs(sl_adjustment - current_sl) > current_sl * self.adaptation_threshold:
            adjustments['stop_loss_pct'] = sl_adjustment
        
        # Ajuste de exposure basado en condición de mercado
        current_exposure = self.current_config['max_gross_exposure']
        if market_condition == "VOLATILE":
            exposure_adjustment = max(current_exposure * 0.8, self.config_ranges['max_gross_exposure'][0])
        elif market_condition == "TRENDING" and win_rate > 0.55:
            exposure_adjustment = min(current_exposure * 1.1, self.config_ranges['max_gross_exposure'][1])
        else:
            exposure_adjustment = current_exposure
        
        if abs(exposure_adjustment - current_exposure) > current_exposure * self.adaptation_threshold:
            adjustments['max_gross_exposure'] = exposure_adjustment
        
        return adjustments
    
    def apply_adjustments(self, adjustments: Dict, reason: str = "Performance adaptation"):
        """
        Aplica ajustes de configuración y registra cambios.
        """
        if not adjustments:
            return
        
        # Registrar cambios
        change_record = {
            'timestamp': datetime.now().isoformat(),
            'reason': reason,
            'old_config': self.current_config.copy(),
            'adjustments': adjustments,
            'new_config': {}
        }
        
        # Aplicar cambios
        for param, new_value in adjustments.items():
            old_value = self.current_config.get(param)
            self.current_config[param] = new_value
            change_record['new_config'][param] = new_value
            
            logger.info(f"🔧 Config ajustado: {param} {old_value:.4f} → {new_value:.4f}")
        
        # Guardar en historial
        self.config_history.append(change_record)
        self.save_config()
        
        logger.info(f"✅ Configuración dinámica actualizada: {len(adjustments)} parámetros ajustados")
    
    def get_current_config(self) -> Dict:
        """
        Obtiene configuración actual para usar en el bot.
        """
        return self.current_config.copy()
    
    def adapt_to_market_conditions(self, market_condition: str, 
                                 sentiment_level: str = "neutral"):
        """
        Adapta configuración a condiciones específicas de mercado.
        """
        adjustments = {}
        
        # Ajustes por condición de mercado
        if market_condition == "VOLATILE":
            adjustments.update({
                'risk_per_trade': max(self.current_config['risk_per_trade'] * 0.7, 0.002),
                'stop_loss_pct': min(self.current_config['stop_loss_pct'] * 1.2, 0.03),
                'max_gross_exposure': max(self.current_config['max_gross_exposure'] * 0.8, 0.8)
            })
        
        elif market_condition == "TRENDING":
            adjustments.update({
                'take_profit_pct': min(self.current_config['take_profit_pct'] * 1.1, 0.10),
                'max_gross_exposure': min(self.current_config['max_gross_exposure'] * 1.1, 2.0)
            })
        
        # Ajustes por sentiment
        if sentiment_level == "extreme_greed":
            adjustments.update({
                'risk_per_trade': max(self.current_config['risk_per_trade'] * 0.8, 0.002),
                'take_profit_pct': max(self.current_config['take_profit_pct'] * 0.9, 0.02)
            })
        
        elif sentiment_level == "extreme_fear":
            adjustments.update({
                'risk_per_trade': min(self.current_config['risk_per_trade'] * 1.2, 0.015),
                'stop_loss_pct': max(self.current_config['stop_loss_pct'] * 0.9, 0.005)
            })
        
        # Aplicar ajustes significativos
        significant_adjustments = {}
        for param, new_value in adjustments.items():
            current_value = self.current_config[param]
            if abs(new_value - current_value) > current_value * 0.05:  # 5% threshold
                significant_adjustments[param] = new_value
        
        if significant_adjustments:
            reason = f"Market adaptation: {market_condition}, sentiment: {sentiment_level}"
            self.apply_adjustments(significant_adjustments, reason)
    
    def reset_to_base(self):
        """
        Resetea configuración a valores base.
        """
        adjustments = {}
        for param, base_value in self.base_config.items():
            if self.current_config[param] != base_value:
                adjustments[param] = base_value
        
        if adjustments:
            self.apply_adjustments(adjustments, "Reset to base configuration")


# Instancia global
dynamic_config_manager = DynamicConfigManager()