#!/usr/bin/env python3
"""
Monitor Inteligente de Posiciones
Optimiza el momento de cierre para maximizar ganancias
"""

import time
import os
from datetime import datetime
from bot.config import settings
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

class PositionOptimizer:
    def __init__(self):
        self.client = TradingClient(
            api_key=settings.alpaca_api_key,
            secret_key=settings.alpaca_secret_key,
            paper=(settings.mode == "paper")
        )
        
        # Configuración de optimización
        self.config = {
            'take_profit_threshold': 0.015,  # 1.5% ganancia mínima para considerar cierre
            'stop_loss_threshold': -0.01,   # -1% pérdida máxima antes de cierre
            'trailing_stop_pct': 0.005,     # 0.5% trailing stop
            'min_hold_time': 300,            # 5 minutos mínimo de tenencia
            'max_hold_time': 3600,           # 1 hora máxima sin reevaluación
        }
        
        self.position_history = {}
        self.alerts = []
        
    def get_positions_with_analysis(self):
        """Obtener posiciones con análisis técnico"""
        positions = self.client.get_all_positions()
        analyzed_positions = []
        
        for pos in positions:
            analysis = self.analyze_position(pos)
            analyzed_positions.append(analysis)
            
        return analyzed_positions
        
    def analyze_position(self, position):
        """Analizar una posición individual"""
        symbol = position.symbol
        current_price = float(position.current_price)
        entry_price = float(position.avg_entry_price)
        unrealized_pl = float(position.unrealized_pl)
        qty = float(position.qty)
        
        # Calcular métricas
        pnl_pct = (unrealized_pl / (entry_price * abs(qty)) * 100) if entry_price != 0 else 0
        
        # Determinar tendencia (simplificada)
        trend = self.get_price_trend(symbol, current_price)
        
        # Generar recomendación
        recommendation = self.generate_recommendation(
            symbol, pnl_pct, trend, unrealized_pl
        )
        
        return {
            'symbol': symbol,
            'qty': qty,
            'entry_price': entry_price,
            'current_price': current_price,
            'unrealized_pl': unrealized_pl,
            'pnl_pct': pnl_pct,
            'trend': trend,
            'recommendation': recommendation,
            'market_value': float(position.market_value)
        }
        
    def get_price_trend(self, symbol, current_price):
        """Analizar tendencia del precio (simplificado)"""
        # Guardar histórico para análisis de tendencia
        if symbol not in self.position_history:
            self.position_history[symbol] = []
            
        now = datetime.now()
        self.position_history[symbol].append((now, current_price))
        
        # Mantener solo últimos 10 registros
        self.position_history[symbol] = self.position_history[symbol][-10:]
        
        if len(self.position_history[symbol]) < 3:
            return "NEUTRAL"
            
        prices = [p[1] for p in self.position_history[symbol][-3:]]
        
        if prices[-1] > prices[-2] > prices[-3]:
            return "SUBIENDO"
        elif prices[-1] < prices[-2] < prices[-3]:
            return "BAJANDO"
        else:
            return "LATERAL"
            
    def generate_recommendation(self, symbol, pnl_pct, trend, unrealized_pl):
        """Generar recomendación de trading"""
        recommendations = []
        
        # Análisis de ganancias
        if pnl_pct >= self.config['take_profit_threshold'] * 100:
            if trend == "BAJANDO":
                recommendations.append("🎯 CERRAR AHORA - Ganancia buena + tendencia bajista")
            elif trend == "SUBIENDO":
                recommendations.append("📈 MANTENER - Tendencia alcista, posible mayor ganancia")
            else:
                recommendations.append("⚖️ EVALUAR - Ganancia objetivo alcanzada")
                
        elif pnl_pct <= self.config['stop_loss_threshold'] * 100:
            recommendations.append("🛑 STOP LOSS - Cerrar para limitar pérdidas")
            
        elif 0 < pnl_pct < self.config['take_profit_threshold'] * 100:
            if trend == "SUBIENDO":
                recommendations.append("📊 MANTENER - Tendencia positiva")
            elif trend == "BAJANDO":
                recommendations.append("⚠️ VIGILAR - Posible retroceso")
            else:
                recommendations.append("➡️ NEUTRO - Sin señales claras")
                
        # Análisis específico por símbolo
        if symbol == "BTCUSD":
            if unrealized_pl > 50:  # Más de $50 de ganancia
                recommendations.append("💰 BTC: Ganancia significativa - considerar cierre parcial")
        elif symbol == "DOGEUSD":
            if unrealized_pl > 10:  # Más de $10 de ganancia  
                recommendations.append("🐕 DOGE: Ganancia sólida para meme coin")
                
        return " | ".join(recommendations) if recommendations else "📊 MANTENER POSICIÓN"
        
    def execute_recommendation(self, position_analysis, action="close"):
        """Ejecutar recomendación (con confirmación del usuario)"""
        if action == "close":
            symbol = position_analysis['symbol']
            qty = abs(position_analysis['qty'])
            
            # Determinar lado de la orden
            side = OrderSide.SELL if position_analysis['qty'] > 0 else OrderSide.BUY
            
            try:
                order_request = MarketOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    side=side,
                    time_in_force=TimeInForce.GTC
                )
                
                order = self.client.submit_order(order_request)
                return f"✅ Orden de cierre enviada para {symbol}: {order.id}"
                
            except Exception as e:
                return f"❌ Error cerrando {symbol}: {e}"
                
    def monitor_positions(self):
        """Monitor principal con recomendaciones en tiempo real"""
        while True:
            try:
                os.system('clear')
                print("🎯 OPTIMIZADOR DE POSICIONES")
                print("=" * 60)
                print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print("=" * 60)
                
                positions = self.get_positions_with_analysis()
                
                if not positions:
                    print("📝 No hay posiciones abiertas para optimizar")
                else:
                    total_unrealized = sum(p['unrealized_pl'] for p in positions)
                    print(f"💰 P&L Total No Realizado: ${total_unrealized:.2f}")
                    print()
                    
                    for i, pos in enumerate(positions, 1):
                        print(f"🔸 POSICIÓN {i}: {pos['symbol']}")
                        print(f"   📊 Cantidad: {pos['qty']:.6f}")
                        print(f"   💵 Entrada: ${pos['entry_price']:.2f}")
                        print(f"   📈 Actual: ${pos['current_price']:.2f}")
                        print(f"   💰 P&L: ${pos['unrealized_pl']:.2f} ({pos['pnl_pct']:.2f}%)")
                        print(f"   📊 Tendencia: {pos['trend']}")
                        print(f"   🎯 RECOMENDACIÓN: {pos['recommendation']}")
                        print("-" * 50)
                
                print("\n🔄 Actualizando en 15 segundos...")
                print("⌨️  Presiona Ctrl+C para salir")
                print("💡 Para cerrar posición manualmente, usar el dashboard")
                
                time.sleep(15)
                
            except KeyboardInterrupt:
                print("\n\n👋 Monitor de optimización detenido")
                break
            except Exception as e:
                print(f"\n❌ Error en monitoring: {e}")
                time.sleep(5)

def main():
    """Función principal"""
    optimizer = PositionOptimizer()
    
    print("🚀 Iniciando Optimizador de Posiciones...")
    print("📊 Analizando tus trades para maximizar ganancias")
    print()
    
    optimizer.monitor_positions()

if __name__ == "__main__":
    main()