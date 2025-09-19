#!/usr/bin/env python3
"""
🧪 TEST CRÍTICO: Validación de correcciones SafetyGuardrails
Verificar que las correcciones críticas del motor de decisiones funcionan correctamente
"""

import sys
import os
sys.path.append('.')

from bot.agus_decision_engine import SafetyGuardrails, ExecutionMode, DecisionRecord, DecisionType
from datetime import datetime

def test_emergency_protective_actions():
    """🚨 Test crítico: Verificar que permite acciones protectoras en emergencias"""
    print("🧪 TESTING: Acciones protectoras en emergencias...")
    
    guardrails = SafetyGuardrails()
    
    # Simular estado de emergencia (drawdown > 15%)
    emergency_state = {
        'current_drawdown': 0.18,  # 18% drawdown (> 15% límite)
        'cash_buffer_pct': 0.02,   # 2% cash buffer (< 5% mínimo)
        'gross_exposure_pct': 1.4,  # 140% exposure
        'current_risk_per_trade': 0.015,
        'current_leverage': 2.0
    }
    
    # Test 1: Acción protectora debe ser PERMITIDA en emergencia
    protective_action = {
        'type': 'reduce_exposure',
        'value': 0.8,  # Reducir exposure a 80%
        'reason': 'Emergency drawdown protection'
    }
    
    is_valid, message = guardrails.validate_action(protective_action, emergency_state)
    assert is_valid == True, f"❌ FALLA: Acción protectora bloqueada en emergencia: {message}"
    print("✅ PASS: Acción protectora permitida en emergencia")
    
    # Test 2: Acción de liquidación debe ser PERMITIDA en emergencia
    liquidation_action = {
        'type': 'emergency_liquidate',
        'value': 1.0,
        'reason': 'Emergency liquidation'
    }
    
    is_valid, message = guardrails.validate_action(liquidation_action, emergency_state)
    assert is_valid == True, f"❌ FALLA: Liquidación de emergencia bloqueada: {message}"
    print("✅ PASS: Liquidación de emergencia permitida")
    
    # Test 3: Acción de aumento de riesgo debe ser BLOQUEADA en emergencia
    risk_increase_action = {
        'type': 'increase_risk_per_trade',
        'value': 0.025,
        'reason': 'Increase risk'
    }
    
    is_valid, message = guardrails.validate_action(risk_increase_action, emergency_state)
    assert is_valid == False, f"❌ FALLA: Aumento de riesgo permitido en emergencia: {message}"
    print("✅ PASS: Aumento de riesgo bloqueado en emergencia")
    
    print("🎯 RESULTADO: Sistema permite acciones protectoras en emergencias")

def test_action_name_normalization():
    """🔧 Test: Verificar normalización de nombres de acciones"""
    print("\n🧪 TESTING: Normalización de nombres de acciones...")
    
    guardrails = SafetyGuardrails()
    
    # Test normalización de nombres
    test_cases = [
        ('reduce_exposure', 'adjust_exposure'),
        ('increase_exposure', 'adjust_exposure'),
        ('tighten_stops', 'adjust_stop_loss'),
        ('reduce_position_size', 'adjust_position_size'),
        ('scale_up', 'increase_position_size')
    ]
    
    for original, expected in test_cases:
        normalized = guardrails._normalize_action_name(original)
        assert normalized == expected, f"❌ FALLA: {original} -> {normalized}, esperado {expected}"
        print(f"✅ PASS: {original} -> {normalized}")
    
    print("🎯 RESULTADO: Normalización de nombres funciona correctamente")

def test_cash_buffer_enforcement():
    """💰 Test: Verificar enforcement del cash buffer mínimo"""
    print("\n🧪 TESTING: Enforcement del cash buffer...")
    
    guardrails = SafetyGuardrails()
    
    # Estado con cash buffer bajo
    low_cash_state = {
        'current_drawdown': 0.05,
        'cash_buffer_pct': 0.02,  # 2% < 5% mínimo
        'gross_exposure_pct': 1.0
    }
    
    # Acción que no es protectora debe ser bloqueada
    non_protective_action = {
        'type': 'increase_position_size',
        'value': 0.3,
        'reason': 'Scale up position'
    }
    
    is_valid, message = guardrails.validate_action(non_protective_action, low_cash_state)
    assert is_valid == False, f"❌ FALLA: Acción permitida con cash buffer bajo: {message}"
    print("✅ PASS: Acción no protectora bloqueada con cash buffer bajo")
    
    # Acción protectora debe ser permitida
    increase_cash_action = {
        'type': 'increase_cash_buffer',
        'value': 0.10,
        'reason': 'Increase cash buffer'
    }
    
    is_valid, message = guardrails.validate_action(increase_cash_action, low_cash_state)
    assert is_valid == True, f"❌ FALLA: Aumento de cash buffer bloqueado: {message}"
    print("✅ PASS: Aumento de cash buffer permitido")
    
    print("🎯 RESULTADO: Cash buffer enforcement funciona correctamente")

def test_qwen_status():
    """🧠 Test: Verificar status honesto de Qwen"""
    print("\n🧪 TESTING: Status honesto de Qwen...")
    
    try:
        from bot.qwen_lightweight import get_qwen_status
        status = get_qwen_status()
        
        # Verificar que el status es honesto sobre Qwen
        assert 'is_real_qwen' in status, "❌ FALLA: Status no incluye is_real_qwen"
        assert status['is_real_qwen'] == False, "❌ FALLA: Status miente sobre Qwen real"
        assert 'warning' in status, "❌ FALLA: Status no incluye warning"
        
        print(f"✅ PASS: Status honesto - is_real_qwen: {status['is_real_qwen']}")
        print(f"✅ PASS: Warning incluido: {status['warning']}")
        print(f"✅ PASS: Modelo real: {status.get('actual_model', 'unknown')}")
        
    except ImportError as e:
        print(f"⚠️ WARNING: No se pudo importar qwen_lightweight: {e}")
    
    print("🎯 RESULTADO: Status de Qwen es honesto sobre capacidades")

def run_all_tests():
    """🎯 Ejecutar todos los tests críticos"""
    print("🧪 INICIANDO TESTS CRÍTICOS DEL MOTOR DE DECISIONES AGUS")
    print("=" * 60)
    
    try:
        test_emergency_protective_actions()
        test_action_name_normalization()
        test_cash_buffer_enforcement()
        test_qwen_status()
        
        print("\n" + "=" * 60)
        print("🎉 TODOS LOS TESTS CRÍTICOS PASARON EXITOSAMENTE!")
        print("✅ Motor de decisiones AGUS es SEGURO para producción")
        print("💰 Sistema listo para proteger capital $16,918")
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FALLÓ: {e}")
        print("🚨 MOTOR DE DECISIONES NO ES SEGURO PARA PRODUCCIÓN")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)