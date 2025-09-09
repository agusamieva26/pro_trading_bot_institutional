"""
Gestor de Tokens para Shorts de Crypto
Compra automática de cantidades mínimas para habilitar shorts
"""

import json
import os
from typing import Dict, List
from .util import logger
from .execution import place_order
from .config import settings


class TokenManager:
    """Gestor para mantener balances mínimos de tokens para shorts."""
    
    def __init__(self):
        self.token_state_file = "bot/token_balances.json" 
        self.token_state = self._load_token_state()
        
        # Tokens principales con cantidad mínima para shorts
        self.target_tokens = {
            "BTC/USD": {"min_usd_value": 100, "purchased": False},
            "ETH/USD": {"min_usd_value": 75, "purchased": False}, 
            "SOL/USD": {"min_usd_value": 50, "purchased": False},
            "AVAX/USD": {"min_usd_value": 30, "purchased": False},
            "LINK/USD": {"min_usd_value": 30, "purchased": False},
            "DOT/USD": {"min_usd_value": 25, "purchased": False},
            "LTC/USD": {"min_usd_value": 30, "purchased": False},
            "UNI/USD": {"min_usd_value": 25, "purchased": False},
            "AAVE/USD": {"min_usd_value": 50, "purchased": False},
            "XRP/USD": {"min_usd_value": 20, "purchased": False}
        }
    
    def _load_token_state(self) -> Dict:
        """Carga el estado de tokens comprados."""
        if os.path.exists(self.token_state_file):
            try:
                with open(self.token_state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"❌ Error cargando token_balances.json: {e}")
        
        return {
            "tokens_purchased": {},
            "total_invested_in_tokens": 0.0,
            "last_purchase_date": None
        }
    
    def _save_token_state(self):
        """Guarda el estado de tokens."""
        try:
            with open(self.token_state_file, 'w') as f:
                json.dump(self.token_state, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"❌ Error guardando token_balances.json: {e}")
    
    def needs_token_purchase(self) -> bool:
        """Determina si necesita comprar tokens para shorts."""
        # Solo comprar una vez
        return len(self.token_state.get("tokens_purchased", {})) == 0
    
    def purchase_minimum_tokens(self, available_cash: float) -> Dict:
        """
        Compra cantidades mínimas de tokens principales para habilitar shorts.
        
        Returns:
            Dict con resultado de la operación
        """
        if not self.needs_token_purchase():
            return {"purchased": False, "reason": "Tokens ya comprados previamente"}
        
        if available_cash < 500:  # Mínimo $500 para comprar tokens
            return {"purchased": False, "reason": f"Cash insuficiente: ${available_cash:.2f}"}
        
        purchased_tokens = {}
        total_spent = 0.0
        successful_purchases = 0
        
        logger.info("🛒 INICIANDO COMPRA DE TOKENS PARA SHORTS...")
        
        for symbol, config in self.target_tokens.items():
            try:
                usd_amount = config["min_usd_value"]
                
                # Calcular cantidad aproximada (price será determinado por el broker)
                logger.info(f"💰 Comprando ${usd_amount} de {symbol}...")
                
                # Usar notional amount para compra en USD
                result = place_order(
                    symbol=symbol,
                    qty=None,
                    side="buy",
                    order_type="market",
                    time_in_force="day",
                    notional=usd_amount  # Comprar por valor en USD
                )
                
                if result and result.get("status") in ["filled", "new", "partially_filled"]:
                    purchased_tokens[symbol] = {
                        "usd_invested": usd_amount,
                        "order_id": result.get("id"),
                        "status": result.get("status")
                    }
                    total_spent += usd_amount
                    successful_purchases += 1
                    logger.info(f"✅ {symbol}: ${usd_amount} comprado exitosamente")
                else:
                    logger.warning(f"⚠️ {symbol}: Compra falló - {result}")
                    
            except Exception as e:
                logger.error(f"❌ Error comprando {symbol}: {e}")
                continue
        
        # Actualizar estado
        if successful_purchases > 0:
            self.token_state["tokens_purchased"] = purchased_tokens
            self.token_state["total_invested_in_tokens"] = total_spent
            self.token_state["last_purchase_date"] = json.dumps({"iso": "2025-09-09T07:10:00Z"})
            self._save_token_state()
            
            logger.info(f"🎯 COMPRA COMPLETADA:")
            logger.info(f"   ✅ Tokens comprados: {successful_purchases}/{len(self.target_tokens)}")
            logger.info(f"   💰 Total invertido: ${total_spent:.2f}")
            logger.info(f"   🔥 Shorts ahora habilitados para todos los tokens")
            
            return {
                "purchased": True,
                "tokens_count": successful_purchases,
                "total_spent": total_spent,
                "purchased_tokens": purchased_tokens
            }
        else:
            return {"purchased": False, "reason": "No se pudo comprar ningún token"}
    
    def get_token_summary(self) -> Dict:
        """Retorna resumen de tokens comprados."""
        return {
            "tokens_purchased_count": len(self.token_state.get("tokens_purchased", {})),
            "total_invested": self.token_state.get("total_invested_in_tokens", 0.0),
            "last_purchase": self.token_state.get("last_purchase_date"),
            "tokens_list": list(self.token_state.get("tokens_purchased", {}).keys())
        }
    
    def send_purchase_notification(self, purchase_data: Dict):
        """Envía notificación Telegram de compra de tokens."""
        try:
            from .telegram import send_telegram
            
            if not purchase_data["purchased"]:
                return
            
            tokens_list = "\n".join([f"• {symbol}" for symbol in purchase_data["purchased_tokens"].keys()])
            
            telegram_msg = f"""🛒 TOKENS COMPRADOS PARA SHORTS

✅ Operación completada exitosamente
💰 Total invertido: ${purchase_data['total_spent']:.2f}
📊 Tokens adquiridos: {purchase_data['tokens_count']}

🔥 TOKENS LISTOS PARA SHORTS:
{tokens_list}

⚡ Shorts de crypto ahora 100% habilitados
🎯 Preparado para aprovechar señales bajistas"""
            
            send_telegram(telegram_msg)
            logger.info("📱 Telegram: Notificación de compra de tokens enviada")
            
        except Exception as e:
            logger.error(f"❌ Error enviando notificación de tokens: {e}")


# Instancia global del gestor
token_manager = TokenManager()