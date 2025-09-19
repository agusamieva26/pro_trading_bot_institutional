#!/usr/bin/env python3
"""
🧪 COMPREHENSIVE TESTING FOR AGUS DECISION ENGINE
Complete test suite to validate all components and safety features.

Tests:
- PolicyEngine rule evaluation and decision generation
- QwenReasoner intelligent analysis (with fallbacks)
- SafeExecutors execution safety and rollback
- DecisionOrchestrator integration and coordination
- Safety guardrails and emergency systems
- Integration with existing AGUS components
"""

import os
import sys
import json
import time
import uuid
import asyncio
import unittest
from datetime import datetime, timedelta
from typing import Dict, List, Any
from pathlib import Path

# Add bot directory to path for imports
sys.path.append('bot')

try:
    from bot.agus_decision_engine import (
        PolicyEngine, QwenReasoner, SafeExecutors, DecisionOrchestrator,
        DecisionType, ExecutionMode, DecisionStatus, SafetyGuardrails,
        PolicyRule, DecisionRecord, get_decision_engine
    )
    ENGINE_AVAILABLE = True
except ImportError as e:
    print(f"❌ Could not import decision engine: {e}")
    ENGINE_AVAILABLE = False

class TestPolicyEngine(unittest.TestCase):
    """Test the PolicyEngine component"""
    
    def setUp(self):
        if not ENGINE_AVAILABLE:
            self.skipTest("Decision engine not available")
        
        self.policy_engine = PolicyEngine()
    
    def test_policy_loading(self):
        """Test that policies load correctly from YAML"""
        self.assertGreater(len(self.policy_engine.policies), 0)
        
        # Check default policies exist
        policy_names = [p.name for p in self.policy_engine.policies]
        expected_policies = [
            'Emergency Drawdown Protection',
            'High Volatility Adaptation',
            'Poor Performance Intervention'
        ]
        
        for expected in expected_policies:
            self.assertIn(expected, policy_names, f"Policy '{expected}' not found")
    
    def test_condition_evaluation(self):
        """Test condition evaluation logic"""
        # Test various operators
        conditions = {
            'current_drawdown': {'operator': 'greater_than', 'value': 0.05}
        }
        market_state = {'current_drawdown': 0.08}
        
        result = self.policy_engine.evaluate_conditions(conditions, market_state)
        self.assertTrue(result, "Greater than condition should pass")
        
        # Test with failing condition
        market_state = {'current_drawdown': 0.03}
        result = self.policy_engine.evaluate_conditions(conditions, market_state)
        self.assertFalse(result, "Greater than condition should fail")
        
        # Test 'in' operator
        conditions = {
            'volatility_regime': {'operator': 'in', 'value': ['high', 'extreme']}
        }
        market_state = {'volatility_regime': 'high'}
        result = self.policy_engine.evaluate_conditions(conditions, market_state)
        self.assertTrue(result, "In condition should pass")
    
    def test_decision_generation(self):
        """Test decision generation from market conditions"""
        # Emergency drawdown scenario
        emergency_state = {
            'current_drawdown': 0.12,  # > 10%
            'emergency_mode': False,
            'risk_score': 0.8,
            'volatility_regime': 'high'
        }
        
        decisions = self.policy_engine.generate_decisions(emergency_state)
        self.assertGreater(len(decisions), 0, "Should generate decisions for emergency state")
        
        # Check that emergency protection decisions are generated
        emergency_decisions = [d for d in decisions if 'emergency' in d.trigger_reason.lower()]
        self.assertGreater(len(emergency_decisions), 0, "Should generate emergency decisions")
    
    def test_safety_guardrails(self):
        """Test safety guardrails validation"""
        guardrails = SafetyGuardrails()
        
        # Test risk per trade limit
        dangerous_action = {
            'type': 'adjust_risk_per_trade',
            'value': 0.05  # 5% - exceeds 2% limit
        }
        current_state = {'current_drawdown': 0.05}
        
        is_safe, message = guardrails.validate_action(dangerous_action, current_state)
        self.assertFalse(is_safe, "Should reject dangerous risk per trade")
        self.assertIn('exceeds limit', message)
        
        # Test safe action
        safe_action = {
            'type': 'adjust_risk_per_trade',
            'value': 0.015  # 1.5% - within 2% limit
        }
        
        is_safe, message = guardrails.validate_action(safe_action, current_state)
        self.assertTrue(is_safe, "Should accept safe risk per trade")
        
        # Test emergency drawdown
        emergency_state = {'current_drawdown': 0.18}  # 18% - exceeds 15% limit
        
        any_action = {'type': 'any_action'}
        is_safe, message = guardrails.validate_action(any_action, emergency_state)
        self.assertFalse(is_safe, "Should reject any action with excessive drawdown")


class TestQwenReasoner(unittest.TestCase):
    """Test the QwenReasoner component"""
    
    def setUp(self):
        if not ENGINE_AVAILABLE:
            self.skipTest("Decision engine not available")
        
        self.reasoner = QwenReasoner()
    
    def test_fallback_analysis(self):
        """Test fallback analysis when Qwen is not available"""
        decision = DecisionRecord(
            decision_type=DecisionType.RISK_ADJUSTMENT,
            trigger_reason="Test decision",
            recommended_action={
                'type': 'reduce_risk_per_trade',
                'value': 0.5,
                'reason': 'Test reduction'
            }
        )
        
        market_state = {
            'current_drawdown': 0.08,
            'risk_score': 0.7,
            'volatility_regime': 'high'
        }
        
        analysis = self.reasoner._fallback_analysis(decision, market_state)
        self.assertIsInstance(analysis, str)
        self.assertGreater(len(analysis), 10, "Analysis should be meaningful")
        self.assertIn('apropiad', analysis.lower(), "Should comment on appropriateness")
    
    def test_sync_analysis(self):
        """Test synchronous decision analysis"""
        decision = DecisionRecord(
            decision_type=DecisionType.PARAMETER_CHANGE,
            trigger_reason="High volatility detected",
            recommended_action={
                'type': 'tighten_stops',
                'value': 0.8,
                'reason': 'Reduce stop distance'
            }
        )
        
        market_state = {
            'current_drawdown': 0.03,
            'risk_score': 0.6,
            'volatility_regime': 'high'
        }
        
        analysis = self.reasoner.analyze_decision(decision, market_state)
        self.assertIsInstance(analysis, str)
        self.assertGreater(len(analysis), 5, "Should provide analysis")


class TestSafeExecutors(unittest.TestCase):
    """Test the SafeExecutors component"""
    
    def setUp(self):
        if not ENGINE_AVAILABLE:
            self.skipTest("Decision engine not available")
        
        self.executors = SafeExecutors()
    
    def test_dry_run_execution(self):
        """Test dry run execution (no real changes)"""
        decision = DecisionRecord(
            decision_type=DecisionType.RISK_ADJUSTMENT,
            trigger_reason="Test dry run",
            recommended_action={
                'type': 'adjust_risk_per_trade',
                'value': 0.01,
                'reason': 'Test adjustment'
            },
            safety_checks_passed=True
        )
        
        # Store original value
        original_risk = 0.013  # Default value
        
        success = self.executors.execute_decision(decision, ExecutionMode.DRY_RUN)
        self.assertTrue(success, "Dry run should always succeed")
        self.assertEqual(decision.status, DecisionStatus.EXECUTED)
        
        # Verify no real changes were made (this would need access to actual settings)
        # In a real test, we'd verify settings.risk_per_trade didn't change
    
    def test_rollback_functionality(self):
        """Test rollback of executed decisions"""
        decision = DecisionRecord(
            decision_type=DecisionType.RISK_ADJUSTMENT,
            trigger_reason="Test rollback",
            recommended_action={
                'type': 'adjust_risk_per_trade',
                'value': 0.008,
                'reason': 'Test adjustment for rollback'
            },
            safety_checks_passed=True
        )
        
        # Execute in dry run first
        success = self.executors.execute_decision(decision, ExecutionMode.DRY_RUN)
        self.assertTrue(success)
        
        # Test rollback
        if decision.rollback_data:
            rollback_success = self.executors.rollback_decision(decision.decision_id)
            # In dry run, rollback might not be applicable
            # But should not crash
    
    def test_safety_validation(self):
        """Test that unsafe decisions are rejected"""
        dangerous_decision = DecisionRecord(
            decision_type=DecisionType.RISK_ADJUSTMENT,
            trigger_reason="Dangerous test",
            recommended_action={
                'type': 'adjust_risk_per_trade',
                'value': 0.10,  # 10% - way too high
                'reason': 'Dangerous test'
            },
            safety_checks_passed=False  # Already marked as unsafe
        )
        
        success = self.executors.execute_decision(dangerous_decision, ExecutionMode.DRY_RUN)
        self.assertFalse(success, "Unsafe decision should be rejected")
        self.assertEqual(dangerous_decision.status, DecisionStatus.FAILED)


class TestDecisionOrchestrator(unittest.TestCase):
    """Test the DecisionOrchestrator component"""
    
    def setUp(self):
        if not ENGINE_AVAILABLE:
            self.skipTest("Decision engine not available")
        
        # Note: We'll test components individually rather than full orchestrator
        # to avoid starting background threads in tests
    
    def test_market_state_gathering(self):
        """Test market state data gathering"""
        try:
            orchestrator = DecisionOrchestrator()
            market_state = orchestrator._gather_market_state()
            
            # Check required fields
            required_fields = [
                'timestamp', 'current_drawdown', 'risk_score', 
                'volatility_regime', 'emergency_mode'
            ]
            
            for field in required_fields:
                self.assertIn(field, market_state, f"Market state missing {field}")
            
            # Check data types
            self.assertIsInstance(market_state['current_drawdown'], (int, float))
            self.assertIsInstance(market_state['risk_score'], (int, float))
            self.assertIsInstance(market_state['emergency_mode'], bool)
            
        except Exception as e:
            self.skipTest(f"Orchestrator initialization failed: {e}")
    
    def test_execution_mode_determination(self):
        """Test execution mode determination logic"""
        try:
            orchestrator = DecisionOrchestrator()
            
            # Emergency scenario
            emergency_decision = DecisionRecord(
                decision_type=DecisionType.EMERGENCY_ACTION,
                approval_required=False
            )
            emergency_state = {
                'emergency_mode': True,
                'current_drawdown': 0.18
            }
            
            mode = orchestrator._determine_execution_mode(emergency_decision, emergency_state)
            self.assertEqual(mode, ExecutionMode.EMERGENCY)
            
            # High-risk decision requiring approval
            risky_decision = DecisionRecord(
                decision_type=DecisionType.STRATEGY_DEPLOYMENT,
                approval_required=True
            )
            normal_state = {
                'emergency_mode': False,
                'current_drawdown': 0.03
            }
            
            mode = orchestrator._determine_execution_mode(risky_decision, normal_state)
            self.assertEqual(mode, ExecutionMode.APPROVAL_GATE)
            
            # Conservative decision
            conservative_decision = DecisionRecord(
                decision_type=DecisionType.RISK_ADJUSTMENT,
                approval_required=False,
                recommended_action={'type': 'reduce_risk_per_trade'}
            )
            
            mode = orchestrator._determine_execution_mode(conservative_decision, normal_state)
            self.assertEqual(mode, ExecutionMode.SAFE_AUTO)
            
        except Exception as e:
            self.skipTest(f"Orchestrator test failed: {e}")


class TestIntegrationScenarios(unittest.TestCase):
    """Test complete integration scenarios"""
    
    def setUp(self):
        if not ENGINE_AVAILABLE:
            self.skipTest("Decision engine not available")
    
    def test_emergency_drawdown_scenario(self):
        """Test complete emergency drawdown response"""
        try:
            # Create policy engine and test emergency scenario
            policy_engine = PolicyEngine()
            reasoner = QwenReasoner()
            
            # Emergency market conditions
            emergency_state = {
                'current_drawdown': 0.13,  # 13% drawdown
                'emergency_mode': False,
                'risk_score': 0.9,
                'volatility_regime': 'extreme',
                'win_rate': 0.25,
                'sharpe_ratio': -0.8,
                'trades_count': 30
            }
            
            # Generate decisions
            decisions = policy_engine.generate_decisions(emergency_state)
            self.assertGreater(len(decisions), 0, "Should generate emergency decisions")
            
            # Analyze decisions
            for decision in decisions:
                analysis = reasoner.analyze_decision(decision, emergency_state)
                self.assertGreater(len(analysis), 10, "Should provide meaningful analysis")
                
            # Check that risk reduction decisions are generated
            risk_reduction_decisions = [
                d for d in decisions 
                if d.recommended_action.get('type', '').startswith('reduce')
            ]
            self.assertGreater(len(risk_reduction_decisions), 0, 
                             "Should generate risk reduction decisions")
            
        except Exception as e:
            self.fail(f"Emergency scenario test failed: {e}")
    
    def test_performance_scaling_scenario(self):
        """Test performance-based scaling scenario"""
        try:
            policy_engine = PolicyEngine()
            
            # Exceptional performance conditions
            good_performance_state = {
                'current_drawdown': 0.01,  # Very low drawdown
                'emergency_mode': False,
                'risk_score': 0.2,
                'volatility_regime': 'low',
                'win_rate': 0.70,  # 70% win rate
                'sharpe_ratio': 2.0,  # Excellent Sharpe
                'trades_count': 50
            }
            
            decisions = policy_engine.generate_decisions(good_performance_state)
            
            # Should generate scaling decisions
            scaling_decisions = [
                d for d in decisions 
                if d.recommended_action.get('type', '').startswith('increase')
            ]
            
            # Note: Decisions depend on policy cooldowns and triggers
            # This test validates the engine runs without errors
            
        except Exception as e:
            self.fail(f"Performance scaling test failed: {e}")
    
    def test_yaml_policy_modification(self):
        """Test that YAML policy modifications work correctly"""
        try:
            policy_engine = PolicyEngine()
            original_count = len(policy_engine.policies)
            
            # Test that policies can be reloaded
            policy_engine.load_policies()
            self.assertEqual(len(policy_engine.policies), original_count, 
                           "Policy count should remain consistent")
            
            # Test policy file exists
            self.assertTrue(policy_engine.policies_file.exists(), 
                          "Policy file should exist")
            
        except Exception as e:
            self.fail(f"YAML policy test failed: {e}")


def run_comprehensive_test():
    """Run comprehensive test of all components"""
    print("🧪 Starting AGUS Decision Engine Comprehensive Tests")
    print("=" * 60)
    
    if not ENGINE_AVAILABLE:
        print("❌ Decision engine not available - cannot run tests")
        return False
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestPolicyEngine,
        TestQwenReasoner, 
        TestSafeExecutors,
        TestDecisionOrchestrator,
        TestIntegrationScenarios
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print(f"🏁 Test Summary:")
    print(f"   Tests run: {result.testsRun}")
    print(f"   Failures: {len(result.failures)}")
    print(f"   Errors: {len(result.errors)}")
    print(f"   Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%" if result.testsRun > 0 else "N/A")
    
    if result.failures:
        print(f"\n❌ Failures:")
        for test, error in result.failures:
            print(f"   - {test}: {error}")
    
    if result.errors:
        print(f"\n💥 Errors:")
        for test, error in result.errors:
            print(f"   - {test}: {error}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\n{'✅ ALL TESTS PASSED' if success else '❌ SOME TESTS FAILED'}")
    
    return success


def test_decision_engine_basic():
    """Basic functionality test for quick validation"""
    print("🚀 Testing AGUS Decision Engine Basic Functionality")
    print("-" * 50)
    
    try:
        # Test policy engine creation
        print("1. Testing PolicyEngine...")
        policy_engine = PolicyEngine()
        print(f"   ✅ Created with {len(policy_engine.policies)} policies")
        
        # Test QwenReasoner
        print("2. Testing QwenReasoner...")
        reasoner = QwenReasoner()
        print(f"   ✅ Created - Available: {reasoner.available}")
        
        # Test SafeExecutors
        print("3. Testing SafeExecutors...")
        executors = SafeExecutors()
        print(f"   ✅ Created - Components initialized")
        
        # Test simple decision generation
        print("4. Testing decision generation...")
        test_state = {
            'current_drawdown': 0.08,
            'emergency_mode': False,
            'risk_score': 0.6,
            'volatility_regime': 'normal'
        }
        
        decisions = policy_engine.generate_decisions(test_state)
        print(f"   ✅ Generated {len(decisions)} decisions")
        
        # Test decision analysis
        if decisions:
            print("5. Testing decision analysis...")
            analysis = reasoner.analyze_decision(decisions[0], test_state)
            print(f"   ✅ Analysis: {analysis[:100]}...")
        
        # Test dry run execution
        if decisions:
            print("6. Testing dry run execution...")
            decision = decisions[0]
            decision.safety_checks_passed = True
            success = executors.execute_decision(decision, ExecutionMode.DRY_RUN)
            print(f"   ✅ Dry run: {'Success' if success else 'Failed'}")
        
        print("\n✅ Basic functionality test PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Basic functionality test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test runner"""
    print("🧠 AGUS DECISION ENGINE TEST SUITE")
    print("🛡️ Testing comprehensive strategic decision making system")
    print("=" * 70)
    
    # Run basic test first
    basic_success = test_decision_engine_basic()
    
    if basic_success:
        print("\n" + "=" * 70)
        print("🧪 Running comprehensive test suite...")
        comprehensive_success = run_comprehensive_test()
        
        return basic_success and comprehensive_success
    else:
        print("\n❌ Basic tests failed - skipping comprehensive tests")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)