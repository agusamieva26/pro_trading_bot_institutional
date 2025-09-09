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
        self.token_purchase_amount = 1.0  # $1 por token
        
    def execute_dynamic_short(self, symbol: str, short_qty: float, short_side: str = "sell") -> Dict:
        """
        Ejecuta short dinámico: compra $1 del token, luego hace short.
        
        Args:
            symbol: Símbolo a operar (ej: BTC/USD)
            short_qty: Cantidad del short principal
            short_side: Debe ser "sell" para short
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            logger.info(f"🔄 INICIO SHORT DINÁMICO {symbol}: Comprando $1 + Short {short_qty}")
            
            # PASO 1: Comprar $1 del token para habilitar short
            logger.info(f"💰 Paso 1/2: Comprando ${self.token_purchase_amount} de {symbol}...")
            
            buy_result = place_order(
                symbol=symbol,
                qty=None,
                side="buy",
                order_type="market",
                time_in_force="day",
                notional=self.token_purchase_amount  # Comprar por valor en USD
            )
            
            if not buy_result or buy_result.get("status") not in ["filled", "new", "partially_filled"]:
                logger.error(f"❌ {symbol}: Fallo en compra de $1 - {buy_result}")
                return {
                    "success": False,
                    "step_failed": "token_purchase",
                    "error": buy_result,
                    "symbol": symbol
                }
            
            logger.info(f"✅ {symbol}: $1 comprado exitosamente - Order ID: {buy_result.get('id')}")
            
            # PASO 2: Ejecutar el short principal
            logger.info(f"📉 Paso 2/2: Ejecutando SHORT de {short_qty} {symbol}...")
            
            short_result = place_order(
                symbol=symbol,
                qty=short_qty,
                side=short_side,
                order_type="market",
                time_in_force="day"
            )
            
            if not short_result or short_result.get("status") not in ["filled", "new", "partially_filled"]:
                logger.error(f"❌ {symbol}: Fallo en SHORT - {short_result}")
                return {
                    "success": False,
                    "step_failed": "short_execution", 
                    "error": short_result,
                    "buy_order": buy_result,
                    "symbol": symbol
                }
            
            logger.info(f"🔥 {symbol}: SHORT DINÁMICO COMPLETADO")
            logger.info(f"   💰 Compra: ${self.token_purchase_amount} (ID: {buy_result.get('id')})")
            logger.info(f"   📉 Short: {short_qty} (ID: {short_result.get('id')})")
            
            return {
                "success": True,
                "symbol": symbol,
                "buy_order": buy_result,
                "short_order": short_result,
                "total_orders": 2
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
            "UNI", "AAVE", "XRP", "DOGE", "SHIB", "PEPE", "BCH", "MKR", "CRV", "GRT"
        ])
    
    def get_dynamic_short_stats(self) -> Dict:
        """Retorna estadísticas de shorts dinámicos."""
        return {
            "purchase_amount_per_token": self.token_purchase_amount,
            "supported_cryptos": [
                "BTC", "ETH", "SOL", "AVAX", "LINK", "DOT", "LTC",
                "UNI", "AAVE", "XRP", "DOGE", "SHIB", "PEPE", "BCH", "MKR", "CRV", "GRT"
            ]
        }


# Instancia global del gestor
dynamic_short_manager = DynamicShortManager()