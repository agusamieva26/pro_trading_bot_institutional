"""
Portfolio Rebalancing automático basado en correlaciones y diversificación.
Optimiza la distribución de activos para maximizar diversificación y minimizar riesgo.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from .symbol_manager import symbol_manager
from .util import logger


class PortfolioRebalancer:
    """
    Sistema de rebalanceo automático que optimiza la diversificación del portfolio
    basado en correlaciones históricas y exposición por sector/tipo de activo.
    """
    
    def __init__(self):
        # Límites de concentración por tipo de activo
        self.asset_limits = {
            'crypto_major': 0.40,    # BTC, ETH máximo 40%
            'crypto_alt': 0.30,      # Altcoins máximo 30%
            'tech_stocks': 0.35,     # Tech stocks máximo 35%
            'etf_broad': 0.50,       # ETFs amplios máximo 50%
            'etf_sector': 0.25,      # ETFs sectoriales máximo 25%
            'other_stocks': 0.40     # Otras acciones máximo 40%
        }
        
        # Correlaciones esperadas (simplificadas)
        self.expected_correlations = {
            ('BTC/USD', 'ETH/USD'): 0.8,
            ('AAPL', 'MSFT'): 0.7,
            ('AAPL', 'GOOGL'): 0.6,
            ('SPY', 'QQQ'): 0.85,
            ('BTC/USD', 'AAPL'): 0.3,
            ('ETH/USD', 'SOL/USD'): 0.7,
        }
        
        # Pesos óptimos por grupo (suma = 1.0)
        self.optimal_weights = {
            'crypto_major': 0.25,
            'crypto_alt': 0.20,
            'tech_stocks': 0.25,
            'etf_broad': 0.15,
            'etf_sector': 0.05,
            'other_stocks': 0.10
        }
    
    def analyze_current_portfolio(self, positions: List[Dict]) -> Dict:
        """
        Analiza el portfolio actual y calcula métricas de diversificación.
        """
        if not positions:
            return {
                'total_value': 0,
                'asset_allocation': {},
                'concentration_risk': 0,
                'diversification_score': 1.0,
                'rebalancing_needed': False
            }
        
        # Calcular valor total y agrupación
        total_value = sum(abs(float(pos.get('market_value', 0))) for pos in positions)
        
        # Agrupar por correlación
        correlation_groups = symbol_manager.get_correlation_groups([pos['symbol'] for pos in positions])
        
        # Calcular allocación actual por grupo
        current_allocation = {}
        group_values = defaultdict(float)
        
        for pos in positions:
            symbol = pos['symbol']
            value = abs(float(pos.get('market_value', 0)))
            
            # Encontrar grupo del símbolo
            for group_name, symbols in correlation_groups.items():
                if symbol in symbols:
                    group_values[group_name] += value
                    break
        
        # Convertir a porcentajes
        for group, value in group_values.items():
            current_allocation[group] = value / total_value if total_value > 0 else 0
        
        # Calcular métricas de riesgo
        concentration_risk = self._calculate_concentration_risk(current_allocation)
        diversification_score = self._calculate_diversification_score(current_allocation)
        rebalancing_needed = self._assess_rebalancing_need(current_allocation)
        
        return {
            'total_value': total_value,
            'asset_allocation': current_allocation,
            'concentration_risk': concentration_risk,
            'diversification_score': diversification_score,
            'rebalancing_needed': rebalancing_needed,
            'group_values': dict(group_values)
        }
    
    def _calculate_concentration_risk(self, allocation: Dict[str, float]) -> float:
        """
        Calcula el riesgo de concentración del portfolio.
        """
        # Herfindahl-Hirschman Index para medir concentración
        hhi = sum(weight ** 2 for weight in allocation.values())
        
        # Normalizar: 0 = perfectamente diversificado, 1 = completamente concentrado
        max_hhi = 1.0  # Si todo está en un solo activo
        min_hhi = 1.0 / len(self.optimal_weights)  # Distribución perfectamente igual
        
        if max_hhi > min_hhi:
            concentration_risk = (hhi - min_hhi) / (max_hhi - min_hhi)
        else:
            concentration_risk = 0
        
        return max(0, min(1, concentration_risk))
    
    def _calculate_diversification_score(self, allocation: Dict[str, float]) -> float:
        """
        Calcula score de diversificación (0-1, mayor es mejor).
        """
        score = 1.0
        
        # Penalizar exceso sobre límites
        for group, weight in allocation.items():
            limit = self.asset_limits.get(group, 0.5)
            if weight > limit:
                excess = weight - limit
                score -= excess * 2  # Penalización por exceso
        
        # Bonus por distribución balanceada
        optimal_total = sum(self.optimal_weights.values())
        if optimal_total > 0:
            for group, optimal_weight in self.optimal_weights.items():
                current_weight = allocation.get(group, 0)
                optimal_normalized = optimal_weight / optimal_total
                
                # Distancia de peso óptimo
                distance = abs(current_weight - optimal_normalized)
                score -= distance * 0.5
        
        return max(0, min(1, score))
    
    def _assess_rebalancing_need(self, allocation: Dict[str, float]) -> bool:
        """
        Determina si es necesario rebalancear el portfolio.
        """
        # Verificar violaciones de límites
        for group, weight in allocation.items():
            limit = self.asset_limits.get(group, 0.5)
            if weight > limit * 1.1:  # 10% de tolerancia
                return True
        
        # Verificar desviación de pesos óptimos
        for group, optimal_weight in self.optimal_weights.items():
            current_weight = allocation.get(group, 0)
            deviation = abs(current_weight - optimal_weight)
            if deviation > 0.15:  # 15% de desviación máxima
                return True
        
        return False
    
    def generate_rebalancing_recommendations(self, positions: List[Dict], 
                                           available_cash: float) -> List[Dict]:
        """
        Genera recomendaciones específicas de rebalanceo.
        """
        portfolio_analysis = self.analyze_current_portfolio(positions)
        
        if not portfolio_analysis['rebalancing_needed']:
            return []
        
        recommendations = []
        current_allocation = portfolio_analysis['asset_allocation']
        total_value = portfolio_analysis['total_value']
        
        # Calcular target allocation
        target_allocation = self._calculate_target_allocation(current_allocation, total_value, available_cash)
        
        # Generar recomendaciones de ajuste
        for group, current_weight in current_allocation.items():
            target_weight = target_allocation.get(group, 0)
            difference = target_weight - current_weight
            
            if abs(difference) > 0.05:  # 5% threshold para recomendación
                value_change = difference * total_value
                
                action = "INCREASE" if difference > 0 else "DECREASE"
                urgency = "HIGH" if abs(difference) > 0.2 else "MEDIUM" if abs(difference) > 0.1 else "LOW"
                
                recommendations.append({
                    'group': group,
                    'action': action,
                    'current_weight': current_weight,
                    'target_weight': target_weight,
                    'difference': difference,
                    'value_change': value_change,
                    'urgency': urgency,
                    'reason': self._get_rebalancing_reason(group, current_weight, target_weight)
                })
        
        # Ordenar por urgencia
        priority_order = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
        recommendations.sort(key=lambda x: priority_order.get(x['urgency'], 0), reverse=True)
        
        return recommendations
    
    def _calculate_target_allocation(self, current_allocation: Dict[str, float], 
                                   total_value: float, available_cash: float) -> Dict[str, float]:
        """
        Calcula la allocación target considerando límites y condiciones actuales.
        """
        target = {}
        
        # Empezar con pesos óptimos como base
        for group, optimal_weight in self.optimal_weights.items():
            current_weight = current_allocation.get(group, 0)
            limit = self.asset_limits.get(group, 0.5)
            
            # Ajustar gradualmente hacia óptimo, respetando límites
            if current_weight > limit:
                # Reducir gradualmente si está sobre límite
                target[group] = min(current_weight * 0.9, limit)
            elif current_weight < optimal_weight * 0.5:
                # Aumentar gradualmente si está muy bajo
                target[group] = min(current_weight * 1.2, optimal_weight)
            else:
                # Movimiento gradual hacia óptimo
                adjustment = (optimal_weight - current_weight) * 0.3
                target[group] = current_weight + adjustment
            
            # Asegurar que no exceda límites
            target[group] = min(target[group], limit)
        
        # Normalizar para que sume 1.0
        total_target = sum(target.values())
        if total_target > 0:
            target = {k: v / total_target for k, v in target.items()}
        
        return target
    
    def _get_rebalancing_reason(self, group: str, current: float, target: float) -> str:
        """
        Genera explicación del rebalanceo recomendado.
        """
        limit = self.asset_limits.get(group, 0.5)
        difference = target - current
        
        if current > limit:
            return f"Overexposed to {group} ({current:.1%} > {limit:.1%} limit)"
        elif difference > 0.1:
            return f"Underweight in {group} - increasing for better diversification"
        elif difference < -0.1:
            return f"Overweight in {group} - reducing to optimize allocation"
        else:
            return f"Minor adjustment to optimize {group} allocation"
    
    def apply_rebalancing_to_signals(self, trading_signals: List[Dict], 
                                   portfolio_analysis: Dict) -> List[Dict]:
        """
        Aplica consideraciones de rebalanceo a las señales de trading.
        """
        if not portfolio_analysis['rebalancing_needed']:
            return trading_signals
        
        current_allocation = portfolio_analysis['asset_allocation']
        adjusted_signals = []
        
        for signal in trading_signals:
            symbol = signal['symbol']
            base_signal = signal['signal']
            
            # Encontrar grupo del símbolo
            correlation_groups = symbol_manager.get_correlation_groups([symbol])
            symbol_group = None
            
            for group_name, symbols in correlation_groups.items():
                if symbol in symbols:
                    symbol_group = group_name
                    break
            
            if symbol_group:
                current_weight = current_allocation.get(symbol_group, 0)
                limit = self.asset_limits.get(symbol_group, 0.5)
                
                # Ajustar señal por rebalanceo
                rebalancing_adjustment = 1.0
                
                if current_weight > limit * 0.9:  # Cerca del límite
                    if base_signal > 0:  # Señal de compra
                        rebalancing_adjustment = 0.5  # Reducir agresividad de compra
                    else:  # Señal de venta
                        rebalancing_adjustment = 1.3  # Aumentar agresividad de venta
                
                elif current_weight < self.optimal_weights.get(symbol_group, 0.1) * 0.5:  # Muy bajo peso
                    if base_signal > 0:  # Señal de compra
                        rebalancing_adjustment = 1.2  # Aumentar agresividad de compra
                
                adjusted_signal = base_signal * rebalancing_adjustment
                
                adjusted_signals.append({
                    **signal,
                    'signal': adjusted_signal,
                    'base_signal': base_signal,
                    'rebalancing_adjustment': rebalancing_adjustment,
                    'symbol_group': symbol_group,
                    'group_weight': current_weight
                })
                
                if rebalancing_adjustment != 1.0:
                    logger.info(f"🔄 {symbol}: Señal ajustada por rebalanceo {base_signal:+.3f} → {adjusted_signal:+.3f} ({symbol_group})")
            else:
                adjusted_signals.append(signal)
        
        return adjusted_signals


# Instancia global
portfolio_rebalancer = PortfolioRebalancer()