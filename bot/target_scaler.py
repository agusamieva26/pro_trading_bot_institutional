# bot/target_scaler.py
import pandas as pd
import os
from datetime import datetime, timedelta
from typing import Dict, Tuple
from .util import logger
import json

class TargetScaler:
    """
    Sistema de escalado automático de metas diarias basado en rendimiento.
    
    Criterios de escalado:
    - Win rate sostenido ≥ 60%
    - 3+ días consecutivos con beneficios
    - P&L promedio > meta actual
    - Consistencia en resultados
    """
    
    def __init__(self):
        self.trades_file = "trades_log.csv"
        self.config_file = "target_config.json"
        self.base_target = 1000.0
        self.max_target = 5000.0  # Límite máximo de seguridad
        self.min_target = 500.0   # Límite mínimo de seguridad
        self.load_config()
    
    def load_config(self):
        """Cargar configuración de escalado desde archivo JSON"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.current_target = config.get('current_target', self.base_target)
                    self.last_update = config.get('last_update', None)
                    self.escalation_history = config.get('escalation_history', [])
            else:
                self.current_target = self.base_target
                self.last_update = None
                self.escalation_history = []
                self.save_config()
        except Exception as e:
            logger.warning(f"⚠️ Error cargando config de target: {e}")
            self.current_target = self.base_target
            self.last_update = None
            self.escalation_history = []
    
    def save_config(self):
        """Guardar configuración de escalado a archivo JSON"""
        try:
            config = {
                'current_target': self.current_target,
                'last_update': self.last_update,
                'escalation_history': self.escalation_history,
                'updated_at': datetime.now().isoformat()
            }
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            logger.error(f"❌ Error guardando config de target: {e}")
    
    def analyze_performance(self, days_back: int = 7) -> Dict:
        """
        Analizar rendimiento de los últimos N días
        
        Returns:
            Dict con métricas de rendimiento
        """
        if not os.path.exists(self.trades_file):
            logger.warning("⚠️ No hay trades_log.csv para analizar rendimiento")
            return {}
        
        try:
            df = pd.read_csv(self.trades_file)
            if df.empty:
                return {}
            
            # Convertir fechas y filtrar trades cerrados
            df["exit_date"] = pd.to_datetime(df["exit_date"], errors="coerce", utc=True)
            df["realized_pnl"] = pd.to_numeric(df["realized_pnl"], errors="coerce")
            
            # Filtrar últimos N días
            cutoff_date = datetime.now() - timedelta(days=days_back)
            df_recent = df[
                (df["status"].isin(["closed", "partially_closed"])) &
                (df["exit_date"] >= cutoff_date)
            ].copy()
            
            if df_recent.empty:
                return {}
            
            # Agrupar por día
            df_recent["exit_day"] = df_recent["exit_date"].dt.date
            daily_pnl = df_recent.groupby("exit_day")["realized_pnl"].sum()
            
            # Calcular métricas
            total_days = len(daily_pnl)
            winning_days = (daily_pnl > 0).sum()
            losing_days = (daily_pnl < 0).sum()
            win_rate = (winning_days / total_days * 100) if total_days > 0 else 0
            
            # Días consecutivos ganando (últimos)
            consecutive_wins = 0
            for pnl in reversed(daily_pnl.values):
                if pnl > 0:
                    consecutive_wins += 1
                else:
                    break
            
            metrics = {
                'total_days': total_days,
                'winning_days': winning_days,
                'losing_days': losing_days,
                'win_rate': win_rate,
                'consecutive_wins': consecutive_wins,
                'avg_daily_pnl': daily_pnl.mean(),
                'total_pnl': daily_pnl.sum(),
                'max_daily_win': daily_pnl.max(),
                'max_daily_loss': daily_pnl.min(),
                'consistency': (daily_pnl > 0).sum() / len(daily_pnl) if len(daily_pnl) > 0 else 0
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Error analizando rendimiento: {e}")
            return {}
    
    def should_scale_up(self, metrics: Dict) -> Tuple[bool, str]:
        """
        Determinar si se debe escalar la meta hacia arriba
        
        Criterios:
        - Win rate ≥ 65%
        - 4+ días consecutivos ganando
        - P&L promedio > 80% de la meta actual
        - Al menos 5 días de datos
        """
        if not metrics:
            return False, "Sin datos suficientes"
        
        reasons = []
        should_scale = True
        
        # Verificar datos mínimos
        if metrics.get('total_days', 0) < 5:
            return False, "Necesitamos al menos 5 días de datos"
        
        # Criterio 1: Win rate
        win_rate = metrics.get('win_rate', 0)
        if win_rate >= 65:
            reasons.append(f"Win rate excelente: {win_rate:.1f}%")
        else:
            should_scale = False
            reasons.append(f"Win rate insuficiente: {win_rate:.1f}% < 65%")
        
        # Criterio 2: Días consecutivos ganando
        consecutive_wins = metrics.get('consecutive_wins', 0)
        if consecutive_wins >= 4:
            reasons.append(f"Racha ganadora: {consecutive_wins} días")
        else:
            should_scale = False
            reasons.append(f"Racha insuficiente: {consecutive_wins} < 4 días")
        
        # Criterio 3: P&L promedio vs meta actual
        avg_pnl = metrics.get('avg_daily_pnl', 0)
        target_threshold = self.current_target * 0.80
        if avg_pnl > target_threshold:
            reasons.append(f"P&L promedio supera 80% de meta: ${avg_pnl:.2f} > ${target_threshold:.2f}")
        else:
            should_scale = False
            reasons.append(f"P&L promedio bajo: ${avg_pnl:.2f} < ${target_threshold:.2f}")
        
        # Criterio 4: Consistencia mínima
        consistency = metrics.get('consistency', 0)
        if consistency >= 0.70:
            reasons.append(f"Alta consistencia: {consistency:.1%}")
        else:
            should_scale = False
            reasons.append(f"Consistencia baja: {consistency:.1%} < 70%")
        
        return should_scale, " | ".join(reasons)
    
    def should_scale_down(self, metrics: Dict) -> Tuple[bool, str]:
        """
        Determinar si se debe reducir la meta
        
        Criterios:
        - Win rate ≤ 40%
        - P&L promedio negativo
        - 3+ días consecutivos con pérdidas
        """
        if not metrics:
            return False, "Sin datos"
        
        reasons = []
        should_scale = False
        
        # Criterio 1: Win rate muy bajo
        win_rate = metrics.get('win_rate', 0)
        if win_rate <= 40:
            should_scale = True
            reasons.append(f"Win rate crítico: {win_rate:.1f}%")
        
        # Criterio 2: P&L promedio negativo
        avg_pnl = metrics.get('avg_daily_pnl', 0)
        if avg_pnl < 0:
            should_scale = True
            reasons.append(f"P&L promedio negativo: ${avg_pnl:.2f}")
        
        # Criterio 3: Racha perdedora (inverso de consecutive_wins)
        consecutive_wins = metrics.get('consecutive_wins', 0)
        if consecutive_wins == 0 and metrics.get('total_days', 0) >= 3:
            # Verificar si los últimos días fueron pérdidas
            should_scale = True
            reasons.append("Racha de pérdidas detectada")
        
        return should_scale, " | ".join(reasons) if reasons else "No requiere reducción"
    
    def calculate_new_target(self, metrics: Dict, scale_up: bool) -> float:
        """Calcular nueva meta basada en métricas"""
        if scale_up:
            # Incremento entre 10-25% basado en rendimiento
            avg_pnl = metrics.get('avg_daily_pnl', 0)
            win_rate = metrics.get('win_rate', 0)
            
            # Factor de escalado basado en rendimiento
            if win_rate >= 80 and avg_pnl > self.current_target * 1.2:
                scale_factor = 1.25  # 25% de incremento
            elif win_rate >= 70 and avg_pnl > self.current_target:
                scale_factor = 1.20  # 20% de incremento
            else:
                scale_factor = 1.15  # 15% de incremento conservador
            
            new_target = self.current_target * scale_factor
        else:
            # Reducción del 20% para proteger capital
            new_target = self.current_target * 0.80
        
        # Aplicar límites de seguridad
        new_target = max(self.min_target, min(self.max_target, new_target))
        return round(new_target, 2)
    
    def update_target(self) -> Tuple[float, Dict, str]:
        """
        Actualizar meta diaria basándose en análisis de rendimiento
        
        Returns:
            Tuple[nueva_meta, métricas, explicación]
        """
        # Analizar rendimiento de últimos 7 días
        metrics = self.analyze_performance(days_back=7)
        
        if not metrics:
            return self.current_target, {}, "Sin datos para análisis"
        
        # Determinar si escalar hacia arriba o abajo
        scale_up, up_reason = self.should_scale_up(metrics)
        scale_down, down_reason = self.should_scale_down(metrics)
        
        old_target = self.current_target
        explanation = ""
        
        if scale_up and not scale_down:
            # Escalar hacia arriba
            self.current_target = self.calculate_new_target(metrics, True)
            explanation = f"📈 META AUMENTADA: ${old_target:.0f} → ${self.current_target:.0f} | {up_reason}"
            
            # Registrar escalación
            self.escalation_history.append({
                'date': datetime.now().isoformat(),
                'old_target': old_target,
                'new_target': self.current_target,
                'direction': 'up',
                'reason': up_reason,
                'metrics': metrics
            })
            
        elif scale_down and not scale_up:
            # Escalar hacia abajo
            self.current_target = self.calculate_new_target(metrics, False)
            explanation = f"📉 META REDUCIDA: ${old_target:.0f} → ${self.current_target:.0f} | {down_reason}"
            
            # Registrar escalación
            self.escalation_history.append({
                'date': datetime.now().isoformat(),
                'old_target': old_target,
                'new_target': self.current_target,
                'direction': 'down',
                'reason': down_reason,
                'metrics': metrics
            })
            
        else:
            explanation = f"⚖️ META MANTENIDA: ${self.current_target:.0f} | Criterios no cumplidos para cambio"
        
        # Actualizar timestamp
        self.last_update = datetime.now().isoformat()
        
        # Guardar configuración
        self.save_config()
        
        # Log del resultado
        logger.info(f"🎯 {explanation}")
        
        return self.current_target, metrics, explanation
    
    def get_current_target(self) -> float:
        """Obtener meta actual"""
        return self.current_target
    
    def get_target_info(self) -> Dict:
        """Obtener información completa de la meta"""
        return {
            'current_target': self.current_target,
            'base_target': self.base_target,
            'max_target': self.max_target,
            'min_target': self.min_target,
            'last_update': self.last_update,
            'total_escalations': len(self.escalation_history),
            'recent_escalations': self.escalation_history[-3:] if self.escalation_history else []
        }

# Instancia global del escalador
target_scaler = TargetScaler()

def get_dynamic_target() -> float:
    """
    Obtener la meta dinámica actual.
    Esta función se llama desde el dashboard y otros módulos.
    """
    return target_scaler.get_current_target()

def update_daily_target() -> Tuple[float, Dict, str]:
    """
    Actualizar la meta diaria - llamar desde automated_trainer
    """
    return target_scaler.update_target()