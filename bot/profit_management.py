"""
Sistema de Gestión Inteligente de Beneficios
40% Reinversión | 60% Protección

Funcionalidades:
- Cálculo automático de beneficios diarios
- Distribución 40/60 de ganancias 
- Capitalización progresiva del capital de trading
- Protección de beneficios netos
- Notificaciones Telegram detalladas
"""

import json
import os
from datetime import datetime, timezone
from typing import Dict, Tuple
from .util import logger
from .state import BotState


class ProfitManager:
    """Gestor inteligente de beneficios con reinversión automática."""
    
    def __init__(self):
        self.profit_state_file = "bot/profit_management.json"
        self.profit_state = self._load_profit_state()
    
    def _load_profit_state(self) -> Dict:
        """Carga el estado de gestión de beneficios."""
        if os.path.exists(self.profit_state_file):
            try:
                with open(self.profit_state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"❌ Error cargando profit_management.json: {e}")
        
        # Estado inicial
        return {
            "total_profits_protected": 0.0,     # 60% acumulado protegido
            "total_profits_reinvested": 0.0,    # 40% acumulado reinvertido  
            "capital_base_original": 24522.49,  # Capital inicial
            "capital_available_trading": 24522.49,  # Capital actual para trading
            "daily_distributions": [],          # Historial de distribuciones
            "last_distribution_date": None,     # Última distribución
            "reinvestment_rate": 0.40,          # 40% reinversión
            "protection_rate": 0.60             # 60% protección
        }
    
    def _save_profit_state(self):
        """Guarda el estado de gestión de beneficios."""
        try:
            with open(self.profit_state_file, 'w') as f:
                json.dump(self.profit_state, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"❌ Error guardando profit_management.json: {e}")
    
    def calculate_daily_profit(self, current_equity: float) -> float:
        """Calcula el beneficio neto del día actual."""
        bot_state = BotState()
        daily_start = bot_state.state.get("daily_start_equity", self.profit_state["capital_base_original"])
        daily_profit = current_equity - daily_start
        return daily_profit
    
    def should_distribute_profits(self, daily_profit: float) -> bool:
        """Determina si se deben distribuir beneficios (solo si hay ganancia)."""
        today = datetime.now(timezone.utc).date().isoformat()
        last_distribution = self.profit_state.get("last_distribution_date")
        
        # Solo distribuir si:
        # 1. Hay beneficio positivo
        # 2. No se ha distribuido hoy
        should_distribute = daily_profit > 0 and last_distribution != today
        
        if not should_distribute:
            if daily_profit <= 0:
                logger.debug(f"📊 No hay beneficios para distribuir: ${daily_profit:+,.2f}")
            elif last_distribution == today:
                logger.debug(f"📊 Beneficios ya distribuidos hoy ({today})")
        
        return should_distribute
    
    def distribute_daily_profits(self, current_equity: float, daily_profit: float) -> Dict:
        """
        Distribuye beneficios diarios: 40% reinversión, 60% protección.
        
        Returns:
            Dict con detalles de la distribución
        """
        if daily_profit <= 0:
            return {"distributed": False, "reason": "No hay beneficios positivos"}
        
        # Calcular distribución
        amount_to_reinvest = daily_profit * self.profit_state["reinvestment_rate"]
        amount_to_protect = daily_profit * self.profit_state["protection_rate"]
        
        # Actualizar acumulados
        self.profit_state["total_profits_reinvested"] += amount_to_reinvest
        self.profit_state["total_profits_protected"] += amount_to_protect
        
        # Actualizar capital disponible para trading (base + reinversión acumulada)
        new_trading_capital = (
            self.profit_state["capital_base_original"] + 
            self.profit_state["total_profits_reinvested"]
        )
        self.profit_state["capital_available_trading"] = new_trading_capital
        
        # Registrar distribución
        distribution_record = {
            "date": datetime.now(timezone.utc).isoformat(),
            "daily_profit": daily_profit,
            "amount_reinvested": amount_to_reinvest,
            "amount_protected": amount_to_protect,
            "new_trading_capital": new_trading_capital,
            "total_protected_accumulated": self.profit_state["total_profits_protected"],
            "total_reinvested_accumulated": self.profit_state["total_profits_reinvested"]
        }
        
        self.profit_state["daily_distributions"].append(distribution_record)
        self.profit_state["last_distribution_date"] = datetime.now(timezone.utc).date().isoformat()
        
        # Guardar estado
        self._save_profit_state()
        
        # Log de la distribución
        logger.info(f"💰 DISTRIBUCIÓN DE BENEFICIOS EJECUTADA:")
        logger.info(f"   📈 Beneficio diario: ${daily_profit:+,.2f}")
        logger.info(f"   🔄 Reinversión (40%): ${amount_to_reinvest:+,.2f}")
        logger.info(f"   🛡️ Protegido (60%): ${amount_to_protect:+,.2f}")
        logger.info(f"   💵 Nuevo capital trading: ${new_trading_capital:,.2f}")
        logger.info(f"   📊 Total protegido acumulado: ${self.profit_state['total_profits_protected']:,.2f}")
        logger.info(f"   📊 Total reinvertido acumulado: ${self.profit_state['total_profits_reinvested']:,.2f}")
        
        return {
            "distributed": True,
            "daily_profit": daily_profit,
            "amount_reinvested": amount_to_reinvest,
            "amount_protected": amount_to_protect,
            "new_trading_capital": new_trading_capital,
            "total_protected": self.profit_state["total_profits_protected"],
            "total_reinvested": self.profit_state["total_profits_reinvested"],
            "distribution_record": distribution_record
        }
    
    def get_current_trading_capital(self) -> float:
        """Retorna el capital actual disponible para trading."""
        return self.profit_state["capital_available_trading"]
    
    def get_profit_summary(self) -> Dict:
        """Retorna resumen completo de beneficios."""
        return {
            "original_capital": self.profit_state["capital_base_original"],
            "current_trading_capital": self.profit_state["capital_available_trading"],
            "total_protected": self.profit_state["total_profits_protected"],
            "total_reinvested": self.profit_state["total_profits_reinvested"],
            "capital_growth": (
                (self.profit_state["capital_available_trading"] / 
                 self.profit_state["capital_base_original"] - 1) * 100
            ),
            "distributions_count": len(self.profit_state["daily_distributions"]),
            "last_distribution": self.profit_state.get("last_distribution_date")
        }
    
    def send_distribution_notification(self, distribution_data: Dict):
        """Envía notificación Telegram de distribución de beneficios."""
        try:
            from .telegram import send_telegram
            
            if not distribution_data["distributed"]:
                return
            
            telegram_msg = f"""💰 DISTRIBUCIÓN DE BENEFICIOS DIARIOS

📈 Beneficio del día: ${distribution_data['daily_profit']:+,.2f}

📊 DISTRIBUCIÓN:
🔄 Reinversión (40%): ${distribution_data['amount_reinvested']:+,.2f}
🛡️ Protegido (60%): ${distribution_data['amount_protected']:+,.2f}

💵 CAPITAL ACTUALIZADO:
📈 Nuevo capital trading: ${distribution_data['new_trading_capital']:,.2f}
🛡️ Total protegido: ${distribution_data['total_protected']:,.2f}
🔄 Total reinvertido: ${distribution_data['total_reinvested']:,.2f}

⚡ Crecimiento de capital: {((distribution_data['new_trading_capital'] / self.profit_state['capital_base_original'] - 1) * 100):+.1f}%"""
            
            send_telegram(telegram_msg)
            logger.info("📱 Telegram: Notificación de distribución enviada")
            
        except Exception as e:
            logger.error(f"❌ Error enviando notificación de distribución: {e}")


# Instancia global del gestor
profit_manager = ProfitManager()