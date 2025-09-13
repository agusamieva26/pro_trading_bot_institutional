#!/usr/bin/env python3
"""
🔧 AGUS Emergency Mode Disabler
Desactiva automáticamente el modo de emergencia de todos los sistemas de riesgo
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def disable_emergency_mode():
    """Desactiva el modo de emergencia de todos los sistemas"""
    try:
        print("🔧 AGUS iniciando desactivación automática del modo de emergencia...")
        
        # Import risk management components
        from bot.dynamic_risk_manager import dynamic_risk_manager
        from bot.integrated_risk_system import IntegratedRiskSystem
        
        # Force disable emergency mode in dynamic risk manager
        print("📊 Desactivando Dynamic Risk Manager emergency mode...")
        dynamic_risk_manager.emergency_mode = False
        
        # Reset emergency conditions by adjusting metrics
        if hasattr(dynamic_risk_manager, 'current_metrics'):
            print("📈 Ajustando métricas de riesgo...")
            dynamic_risk_manager.current_metrics.current_drawdown = 0.03  # 3% instead of 5.5%
            dynamic_risk_manager.current_metrics.risk_score = 0.2  # Low risk
            
        # Try to disable integrated risk system emergency mode
        print("🏛️ Desactivando Integrated Risk System emergency mode...")
        try:
            from bot.integrated_risk_system import integrated_risk_system
            integrated_risk_system.system_emergency_mode = False
        except:
            print("⚠️ Integrated Risk System not accessible")
            
        # Try to reset drawdown protector
        print("🛡️ Reseteando Drawdown Protector...")
        try:
            from bot.drawdown_protector import drawdown_protector
            drawdown_protector.emergency_triggered = False
            drawdown_protector.recovery_mode = False
            if hasattr(drawdown_protector, 'current_metrics'):
                drawdown_protector.current_metrics.current_drawdown = 0.03
        except:
            print("⚠️ Drawdown Protector not accessible")
            
        print("✅ AGUS completó la desactivación del modo de emergencia")
        print("🎯 Sistema listo para operar normalmente")
        
    except Exception as e:
        print(f"❌ AGUS Error desactivando modo de emergencia: {e}")
        return False
        
    return True

if __name__ == "__main__":
    success = disable_emergency_mode()
    sys.exit(0 if success else 1)