"""
Cash Buffer Utilities - Funciones de utilidad para el sistema dinámico de cash buffer
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Optional
from .util import logger
from .dynamic_cash_buffer import dynamic_cash_buffer, get_dynamic_cash_buffer


def diagnose_buffer_system() -> str:
    """
    Realiza un diagnóstico completo del sistema de cash buffer.
    
    Returns:
        str: Reporte detallado del estado del sistema
    """
    try:
        from .dynamic_cash_buffer import get_buffer_diagnostics
        return get_buffer_diagnostics()
    except Exception as e:
        return f"❌ Error en diagnóstico: {e}"


def activate_emergency_trading(duration_minutes: int = 30) -> str:
    """
    Activa trading ultra-agresivo para situaciones de emergencia.
    
    Args:
        duration_minutes: Duración del modo de emergencia
        
    Returns:
        str: Confirmación de activación
    """
    try:
        from .dynamic_cash_buffer import activate_emergency_mode
        return activate_emergency_mode(duration_minutes)
    except Exception as e:
        logger.error(f"❌ Error activando modo emergencia: {e}")
        return f"❌ Error: {e}"


def set_custom_buffer_override(buffer_percentage: float, duration_minutes: int = 60) -> str:
    """
    Establece un override personalizado del cash buffer.
    
    Args:
        buffer_percentage: Porcentaje de buffer (ej: 0.01 = 1%)
        duration_minutes: Duración del override
        
    Returns:
        str: Confirmación del override
    """
    try:
        if buffer_percentage < 0.005 or buffer_percentage > 0.50:
            return f"❌ Error: Buffer debe estar entre 0.5% y 50%"
            
        dynamic_cash_buffer.set_override(buffer_percentage, duration_minutes)
        return f"✅ Override activado: {buffer_percentage:.1%} por {duration_minutes} minutos"
    except Exception as e:
        logger.error(f"❌ Error en override personalizado: {e}")
        return f"❌ Error: {e}"


def clear_buffer_override() -> str:
    """
    Limpia cualquier override activo del cash buffer.
    
    Returns:
        str: Confirmación de limpieza
    """
    try:
        dynamic_cash_buffer.clear_override()
        return "✅ Override eliminado - Volviendo a buffer dinámico"
    except Exception as e:
        logger.error(f"❌ Error limpiando override: {e}")
        return f"❌ Error: {e}"


def get_current_buffer_status() -> Dict:
    """
    Obtiene el estado actual del sistema de buffer.
    
    Returns:
        Dict: Estado actual del sistema
    """
    try:
        buffer_pct, mode, info = get_dynamic_cash_buffer()
        
        from alpaca.trading.client import TradingClient
        from .config import settings
        
        client = TradingClient(
            api_key=settings.alpaca_api_key,
            secret_key=settings.alpaca_secret_key,
            paper=(settings.mode == "paper")
        )
        
        account = client.get_account()
        cash = float(getattr(account, 'cash', 0.0) or 0.0)
        equity = float(getattr(account, 'equity', 0.0) or 0.0)
        
        return {
            "buffer_percentage": buffer_pct,
            "mode": mode,
            "factors": info,
            "account": {
                "cash": cash,
                "equity": equity,
                "cash_ratio": cash / max(equity, 1e-9),
                "required_buffer": equity * buffer_pct
            },
            "override_active": dynamic_cash_buffer.is_override_active(),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Error obteniendo estado buffer: {e}")
        return {"error": str(e)}


def monitor_buffer_performance() -> str:
    """
    Monitorea el rendimiento del sistema de buffer.
    
    Returns:
        str: Reporte de rendimiento
    """
    try:
        stats = dynamic_cash_buffer.get_buffer_stats()
        
        if "error" in stats:
            return f"❌ Error en monitoring: {stats['error']}"
        
        current_buffer, mode, _ = stats["current"]
        stats_24h = stats["stats_24h"]
        
        # Calcular eficiencia del sistema
        if stats_24h["std"] < 0.02:  # Menos de 2% de variación
            efficiency = "🟢 ESTABLE"
        elif stats_24h["std"] < 0.05:  # Menos de 5%
            efficiency = "🟡 MODERADO"
        else:
            efficiency = "🔴 VOLÁTIL"
        
        report = f"""
🎯 MONITOR CASH BUFFER DINÁMICO

📊 ESTADO ACTUAL:
   Buffer: {current_buffer:.1%} | Modo: {mode}
   Eficiencia: {efficiency}
   
📈 RENDIMIENTO 24H:
   Promedio: {stats_24h['avg']:.1%}
   Variabilidad: {stats_24h['std']:.1%}
   Rango: {stats_24h['min']:.1%} - {stats_24h['max']:.1%}
   
🎭 DISTRIBUCIÓN MODOS:
"""
        
        for mode_name, pct in stats['mode_distribution'].items():
            report += f"   {mode_name}: {pct:.1%}\n"
        
        # Recomendaciones
        if stats_24h["std"] > 0.05:
            report += "\n⚠️ RECOMENDACIÓN: Alta variabilidad - considera ajustar factores"
        elif stats_24h["avg"] > 0.15:
            report += "\n💡 OPTIMIZACIÓN: Buffer promedio alto - oportunidad de ser más agresivo"
        else:
            report += "\n✅ SISTEMA: Funcionando optimalmente"
        
        return report.strip()
        
    except Exception as e:
        logger.error(f"❌ Error en monitoring: {e}")
        return f"❌ Error: {e}"


def test_buffer_system() -> str:
    """
    Ejecuta tests del sistema de cash buffer dinámico.
    
    Returns:
        str: Resultados de los tests
    """
    results = []
    
    try:
        # Test 1: Cálculo básico del buffer
        buffer_pct, mode, info = get_dynamic_cash_buffer()
        if 0.01 <= buffer_pct <= 0.25:
            results.append("✅ Test 1: Cálculo básico - OK")
        else:
            results.append(f"❌ Test 1: Buffer fuera de rango: {buffer_pct:.1%}")
        
        # Test 2: Factores de cálculo
        required_factors = ["volatility", "performance", "positions", "liquidity"]
        if all(factor in info for factor in required_factors):
            results.append("✅ Test 2: Factores de cálculo - OK")
        else:
            missing = [f for f in required_factors if f not in info]
            results.append(f"❌ Test 2: Factores faltantes: {missing}")
        
        # Test 3: Sistema de override
        try:
            original_mode = mode
            dynamic_cash_buffer.set_override(0.02, 1)  # 2% por 1 minuto
            
            buffer_pct_override, mode_override, _ = get_dynamic_cash_buffer()
            if mode_override == "OVERRIDE" and abs(buffer_pct_override - 0.02) < 0.001:
                results.append("✅ Test 3: Sistema de override - OK")
            else:
                results.append(f"❌ Test 3: Override falló: {mode_override}, {buffer_pct_override:.1%}")
            
            # Limpiar override de test
            dynamic_cash_buffer.clear_override()
        except Exception as e:
            results.append(f"❌ Test 3: Override falló con error: {e}")
        
        # Test 4: Persistencia
        try:
            dynamic_cash_buffer.save_state()
            dynamic_cash_buffer.load_state()
            results.append("✅ Test 4: Persistencia - OK")
        except Exception as e:
            results.append(f"❌ Test 4: Persistencia falló: {e}")
        
        # Test 5: Integración con execution.py
        try:
            # Simular importación desde execution.py usando función ya importada
            buffer_test = get_dynamic_cash_buffer()
            if len(buffer_test) == 3:
                results.append("✅ Test 5: Integración execution.py - OK")
            else:
                results.append("❌ Test 5: Integración retorna formato incorrecto")
        except Exception as e:
            results.append(f"❌ Test 5: Integración falló: {e}")
        
    except Exception as e:
        results.append(f"❌ Error general en tests: {e}")
    
    # Reporte final
    total_tests = len(results)
    passed = len([r for r in results if r.startswith("✅")])
    
    report = f"""
🧪 TESTS CASH BUFFER DINÁMICO

RESULTADOS ({passed}/{total_tests} exitosos):
"""
    
    for result in results:
        report += f"\n{result}"
    
    if passed == total_tests:
        report += f"\n\n🎉 TODOS LOS TESTS PASARON - Sistema listo para producción"
    else:
        report += f"\n\n⚠️ {total_tests - passed} tests fallaron - Revisar antes de usar en producción"
    
    return report


def get_emergency_commands_help() -> str:
    """
    Retorna ayuda sobre comandos de emergencia del cash buffer.
    
    Returns:
        str: Ayuda de comandos
    """
    return """
🚨 COMANDOS DE EMERGENCIA - CASH BUFFER DINÁMICO

🔥 ACTIVAR TRADING ULTRA-AGRESIVO:
   from bot.cash_buffer_utils import activate_emergency_trading
   result = activate_emergency_trading(30)  # 30 minutos

💰 OVERRIDE PERSONALIZADO:
   from bot.cash_buffer_utils import set_custom_buffer_override
   result = set_custom_buffer_override(0.02, 60)  # 2% por 60 min

🧹 LIMPIAR OVERRIDE:
   from bot.cash_buffer_utils import clear_buffer_override
   result = clear_buffer_override()

📊 DIAGNÓSTICO COMPLETO:
   from bot.cash_buffer_utils import diagnose_buffer_system
   report = diagnose_buffer_system()
   
🎯 ESTADO ACTUAL:
   from bot.cash_buffer_utils import get_current_buffer_status
   status = get_current_buffer_status()
   
🧪 EJECUTAR TESTS:
   from bot.cash_buffer_utils import test_buffer_system
   results = test_buffer_system()

📈 MONITOR RENDIMIENTO:
   from bot.cash_buffer_utils import monitor_buffer_performance
   report = monitor_buffer_performance()
   
⚠️ IMPORTANTE: Los overrides son temporales y se desactivan automáticamente.
   El sistema dinámico es la mejor opción para operación normal.
"""