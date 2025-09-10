"""
Sistema de Shorts Dinámicos
Compra $1 del token antes de hacer short
"""

from typing import Dict, Optional
from .util import logger
from .execution import place_order


class DynamicShortManager:
    """Gestiona shorts con compra dinámica de tokens."""
    
    def __init__(self):
        self.default_purchase_amount = 50.0  # Cantidad moderada por defecto
        
    def execute_dynamic_short(self, symbol: str, short_qty: float, current_price: float, short_side: str = "sell", purchase_amount: float = None) -> Dict:
        """
        Ejecuta short dinámico: compra cantidad basada en riesgo, luego hace short del 80% comprado.
        
        Args:
            symbol: Símbolo a operar (ej: BTC/USD)
            short_qty: Cantidad original (se ignora, se calcula del token comprado)
            current_price: Precio actual del activo
            short_side: Debe ser "sell" para short
            purchase_amount: Cantidad en USD a comprar (usa riesgo si no se especifica)
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            # Limitar la cantidad máxima para evitar problemas de liquidez
            max_purchase = 200.0  # Máximo $200 por short dinámico
            if purchase_amount and purchase_amount > max_purchase:
                token_purchase_amount = max_purchase
                logger.info(f"🔧 {symbol}: Limitando purchase_amount de ${purchase_amount:.2f} a ${max_purchase:.2f}")
            else:
                token_purchase_amount = purchase_amount or self.default_purchase_amount
            
            # Calcular la cantidad que realmente podemos comprar y hacer short
            buy_qty = token_purchase_amount / current_price if current_price > 0 else 0.001
            # Solo hacer short del 80% de lo comprado para dejar margen de seguridad
            actual_short_qty = buy_qty * 0.8
            
            logger.info(f"🔄 INICIO SHORT DINÁMICO {symbol}: Comprando ${token_purchase_amount:.2f} + Short {actual_short_qty:.6f} (vs original {short_qty:.6f})")
            
            # PASO 1: Comprar cantidad basada en riesgo del token para habilitar short
            logger.info(f"💰 Paso 1/2: Comprando ${token_purchase_amount:.2f} de {symbol}...")
            
            buy_result = place_order(
                symbol=symbol,
                qty=buy_qty,
                side="buy",
                price=current_price,
                is_crypto=True
            )
            
            if not buy_result:
                logger.error(f"❌ {symbol}: Fallo en compra de $10 - {buy_result}")
                return {
                    "success": False,
                    "step_failed": "token_purchase",
                    "error": buy_result,
                    "symbol": symbol
                }
            
            # Si buy_result es solo True/False, no tiene atributo 'get'
            if isinstance(buy_result, bool):
                if not buy_result:
                    logger.error(f"❌ {symbol}: Compra falló (resultado booleano)")
                    return {
                        "success": False,
                        "step_failed": "token_purchase",
                        "error": "Order returned False",
                        "symbol": symbol
                    }
                buy_order_id = "boolean_success"
            else:
                # Es un diccionario con información de la orden
                if buy_result.get("status") not in ["filled", "new", "partially_filled"]:
                    logger.error(f"❌ {symbol}: Estado de compra inválido - {buy_result}")
                    return {
                        "success": False,
                        "step_failed": "token_purchase",
                        "error": buy_result,
                        "symbol": symbol
                    }
                buy_order_id = buy_result.get('id', 'unknown')
            
            logger.info(f"✅ {symbol}: ${token_purchase_amount:.2f} comprado exitosamente - Order ID: {buy_order_id}")
            
            # PASO 2: Ejecutar el short principal (solo el 80% de lo comprado)
            logger.info(f"📉 Paso 2/2: Ejecutando SHORT de {actual_short_qty:.6f} {symbol} (80% de {buy_qty:.6f} comprado)...")
            
            short_result = place_order(
                symbol=symbol,
                qty=actual_short_qty,
                side=short_side,
                price=current_price,
                is_crypto=True
            )
            
            if not short_result:
                logger.error(f"❌ {symbol}: Fallo en SHORT - {short_result}")
                return {
                    "success": False,
                    "step_failed": "short_execution", 
                    "error": short_result,
                    "buy_order": buy_result,
                    "symbol": symbol
                }
            
            # Manejar resultado booleano vs diccionario
            if isinstance(short_result, bool):
                if not short_result:
                    logger.error(f"❌ {symbol}: SHORT falló (resultado booleano)")
                    return {
                        "success": False,
                        "step_failed": "short_execution",
                        "error": "Short returned False",
                        "buy_order": buy_result,
                        "symbol": symbol
                    }
                short_order_id = "boolean_success"
            else:
                if short_result.get("status") not in ["filled", "new", "partially_filled"]:
                    logger.error(f"❌ {symbol}: Estado de SHORT inválido - {short_result}")
                    return {
                        "success": False,
                        "step_failed": "short_execution",
                        "error": short_result,
                        "buy_order": buy_result,
                        "symbol": symbol
                    }
                short_order_id = short_result.get('id', 'unknown')
            
            logger.info(f"🔥 {symbol}: SHORT DINÁMICO COMPLETADO")
            logger.info(f"   💰 Compra: ${token_purchase_amount:.2f} = {buy_qty:.6f} tokens (ID: {buy_order_id})")
            logger.info(f"   📉 Short: {actual_short_qty:.6f} tokens = 80% comprado (ID: {short_order_id})")
            
            return {
                "success": True,
                "symbol": symbol,
                "buy_order": buy_result,
                "short_order": short_result,
                "total_orders": 2,
                "actual_short_qty": actual_short_qty,
                "original_short_qty": short_qty,
                "buy_qty": buy_qty
            }
            
        except Exception as e:
            logger.error(f"💥 Error en SHORT DINÁMICO {symbol}: {e}")
            return {
                "success": False,
                "step_failed": "exception",
                "error": str(e),
                "symbol": symbol
            }
    
    def should_use_dynamic_short(self, symbol: str) -> bool:
        """
        Determina si se debe usar short dinámico.
        Para crypto shorts siempre usar dinámico.
        """
        return symbol.endswith("/USD") and any(crypto in symbol for crypto in [
            "BTC", "ETH", "SOL", "AVAX", "LINK", "DOT", "LTC", 
            "UNI", "AAVE", "XRP", "DOGE", "SHIB", "PEPE", "BCH", "CRV", "GRT"
        ])
    
    def get_dynamic_short_stats(self) -> Dict:
        """Retorna estadísticas de shorts dinámicos."""
        return {
            "purchase_amount_per_token": self.token_purchase_amount,
            "supported_cryptos": [
                "BTC", "ETH", "SOL", "AVAX", "LINK", "DOT", "LTC",
                "UNI", "AAVE", "XRP", "DOGE", "SHIB", "PEPE", "BCH", "CRV", "GRT"
            ]
        }


# Instancia global del gestor
dynamic_short_manager = DynamicShortManager()