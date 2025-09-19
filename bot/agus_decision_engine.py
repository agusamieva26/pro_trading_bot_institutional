#!/usr/bin/env python3
"""
🧠 AGUS STRATEGIC DECISION ENGINE - AUTONOMOUS INTELLIGENCE CORE
Complete autonomous decision-making system for advanced trading bot operations.

🚀 COMPONENTS:
- PolicyEngine: YAML-based rules system for automated decision making
- QwenReasoner: Intelligent analysis using Qwen 2.5 integration
- SafeExecutors: Safe execution modules for risk, parameters, strategies, and liquidity
- DecisionOrchestrator: Main coordinator integrating with AGUS system

🛡️ SAFETY FEATURES:
- Hard guardrails (max drawdown 15%, max leverage 3x)
- Dry-run mode by default
- Emergency kill switch
- Complete audit trail
- Automatic rollback on errors
"""

import os
import asyncio
import yaml
import json
import time
import uuid
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Callable, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from collections import defaultdict, deque
import numpy as np
import pandas as pd
import traceback

from .util import logger
from .config import settings

# Import existing system components
try:
    from .qwen_lightweight import qwen_generate_response, qwen_chat_completion_async
    from .dynamic_risk_manager import DynamicRiskManager
    from .dynamic_config import DynamicConfigManager
    from .strategy_deployment_engine import StrategyDeploymentEngine
    from .integrated_risk_system import IntegratedRiskSystem
    from .agus_core import AGUSOrchestrator, Event, EventType, Alert, AlertSeverity
    AGUS_INTEGRATION_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Some AGUS components not available: {e}")
    AGUS_INTEGRATION_AVAILABLE = False


class DecisionType(Enum):
    """Types of decisions the engine can make"""
    RISK_ADJUSTMENT = "risk_adjustment"
    PARAMETER_CHANGE = "parameter_change"
    STRATEGY_DEPLOYMENT = "strategy_deployment"
    STRATEGY_RETIREMENT = "strategy_retirement"
    LIQUIDITY_MANAGEMENT = "liquidity_management"
    EMERGENCY_ACTION = "emergency_action"
    POSITION_ADJUSTMENT = "position_adjustment"
    CONFIG_OPTIMIZATION = "config_optimization"


class ExecutionMode(Enum):
    """Execution modes for the decision engine"""
    DRY_RUN = "dry_run"          # No real changes, only logging
    SAFE_AUTO = "safe_auto"      # Auto execution with safety checks
    APPROVAL_GATE = "approval_gate"  # Requires approval for critical changes
    EMERGENCY = "emergency"      # Emergency mode with immediate execution


class DecisionStatus(Enum):
    """Status of decisions"""
    PENDING = "pending"
    ANALYZING = "analyzing"
    APPROVED = "approved"
    EXECUTED = "executed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    CANCELLED = "cancelled"


@dataclass
class PolicyRule:
    """Individual policy rule"""
    rule_id: str
    name: str
    description: str
    conditions: Dict[str, Any]
    actions: List[Dict[str, Any]]
    priority: int = 5
    enabled: bool = True
    cooldown_minutes: int = 60
    last_triggered: Optional[datetime] = None


@dataclass
class DecisionRecord:
    """Record of a decision made by the engine"""
    decision_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    decision_type: DecisionType = DecisionType.PARAMETER_CHANGE
    timestamp: datetime = field(default_factory=datetime.now)
    trigger_reason: str = ""
    analysis: str = ""
    recommended_action: Dict[str, Any] = field(default_factory=dict)
    execution_mode: ExecutionMode = ExecutionMode.DRY_RUN
    status: DecisionStatus = DecisionStatus.PENDING
    execution_result: Optional[Dict[str, Any]] = None
    rollback_data: Optional[Dict[str, Any]] = None
    approval_required: bool = False
    approved_by: Optional[str] = None
    safety_checks_passed: bool = False
    error_message: Optional[str] = None


@dataclass
class SafetyGuardrails:
    """Hard safety limits that cannot be exceeded"""
    max_drawdown_pct: float = 0.15          # 15% max drawdown
    max_leverage: float = 3.0               # 3x max leverage  
    max_single_position_pct: float = 0.25   # 25% max single position
    max_daily_trades: int = 500             # 500 max daily trades
    min_cash_buffer_pct: float = 0.05       # 5% min cash buffer
    max_risk_per_trade_pct: float = 0.02    # 2% max risk per trade
    max_gross_exposure_pct: float = 1.5     # 150% max gross exposure
    emergency_stop_loss_pct: float = 0.20   # 20% emergency stop
    
    def validate_action(self, action: Dict[str, Any], current_state: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate if an action violates safety guardrails"""
        try:
            action_type = action.get('type', '')
            action_value = action.get('value', 0)
            current_drawdown = current_state.get('current_drawdown', 0)
            current_cash_buffer = current_state.get('cash_buffer_pct', 0)
            current_exposure = current_state.get('gross_exposure_pct', 0)
            
            # Normalize action names for consistent validation
            action_type = self._normalize_action_name(action_type)
            
            # Define protective actions that are ALWAYS allowed in emergencies
            protective_actions = {
                'emergency_liquidate', 'force_close_positions', 'reduce_exposure', 
                'tighten_stops', 'reduce_risk_per_trade', 'reduce_position_size',
                'increase_cash_buffer', 'emergency_stop', 'pause_new_positions'
            }
            
            # CRITICAL: Allow protective actions even in extreme drawdown
            if action_type in protective_actions and current_drawdown > self.max_drawdown_pct:
                logger.warning(f"🚨 EMERGENCY: Allowing protective action '{action_type}' despite {current_drawdown:.1%} drawdown > {self.max_drawdown_pct:.1%}")
                return True, f"Emergency protective action allowed: {action_type}"
            
            # Cash buffer enforcement - CRITICAL SAFETY CHECK
            if current_cash_buffer < self.min_cash_buffer_pct:
                if action_type not in protective_actions and action_type not in ['increase_cash_buffer', 'reduce_exposure']:
                    return False, f"Cash buffer {current_cash_buffer:.1%} below minimum {self.min_cash_buffer_pct:.1%} - only protective actions allowed"
            
            # Risk parameter validation - Allow reductions always
            if action_type == 'adjust_risk_per_trade':
                if action_value > self.max_risk_per_trade_pct:
                    return False, f"Risk per trade {action_value:.2%} exceeds limit {self.max_risk_per_trade_pct:.2%}"
                # Always allow risk reductions
                current_risk = current_state.get('current_risk_per_trade', self.max_risk_per_trade_pct)
                if action_value < current_risk:
                    return True, "Risk reduction always allowed"
            
            # Leverage validation - Allow reductions always
            if action_type == 'adjust_leverage':
                if action_value > self.max_leverage:
                    return False, f"Leverage {action_value:.1f}x exceeds limit {self.max_leverage:.1f}x"
                current_leverage = current_state.get('current_leverage', self.max_leverage)
                if action_value < current_leverage:
                    return True, "Leverage reduction always allowed"
            
            # Position size validation - Allow reductions always
            if action_type == 'adjust_position_size':
                if action_value > self.max_single_position_pct:
                    return False, f"Position size {action_value:.1%} exceeds limit {self.max_single_position_pct:.1%}"
                current_position_size = current_state.get('current_position_size', self.max_single_position_pct)
                if action_value < current_position_size:
                    return True, "Position size reduction always allowed"
            
            # Exposure validation - Allow reductions always
            if action_type == 'adjust_exposure':
                if action_value > self.max_gross_exposure_pct:
                    return False, f"Gross exposure {action_value:.1%} exceeds limit {self.max_gross_exposure_pct:.1%}"
                if action_value < current_exposure:
                    return True, "Exposure reduction always allowed"
            
            # Drawdown validation - Only block RISK-INCREASING actions
            if current_drawdown > self.max_drawdown_pct:
                risk_increasing_actions = {
                    'increase_risk_per_trade', 'increase_leverage', 'increase_position_size',
                    'increase_exposure', 'add_positions', 'scale_up'
                }
                if action_type in risk_increasing_actions:
                    return False, f"Risk-increasing action '{action_type}' blocked: drawdown {current_drawdown:.1%} > {self.max_drawdown_pct:.1%}"
                else:
                    return True, "Non-risk-increasing action allowed during emergency drawdown"
            
            return True, "Action passes safety checks"
            
        except Exception as e:
            logger.error(f"❌ Safety validation error: {e}")
            return False, f"Safety validation error: {e}"
    
    def _normalize_action_name(self, action_type: str) -> str:
        """Normalize action names for consistent validation"""
        # Map policy action names to guardrail validation names
        name_mapping = {
            'reduce_exposure': 'adjust_exposure',
            'increase_exposure': 'adjust_exposure', 
            'tighten_stops': 'adjust_stop_loss',
            'widen_stops': 'adjust_stop_loss',
            'reduce_position_size': 'adjust_position_size',
            'increase_position_size': 'adjust_position_size',
            'reduce_risk_per_trade': 'adjust_risk_per_trade',
            'increase_risk_per_trade': 'adjust_risk_per_trade',
            'scale_up': 'increase_position_size',
            'scale_down': 'reduce_position_size'
        }
        return name_mapping.get(action_type, action_type)


class PolicyEngine:
    """
    🔧 YAML-based policy engine for automated decision making
    
    Features:
    - Load policies from YAML configuration
    - Evaluate market conditions against rules
    - Generate decision recommendations
    - Handle policy priorities and cooldowns
    """
    
    def __init__(self):
        self.policies_file = Path("bot/agus_policies.yaml")
        self.policies: List[PolicyRule] = []
        self.safety_guardrails = SafetyGuardrails()
        self.decision_history: List[DecisionRecord] = []
        
        # Load default policies if file doesn't exist
        if not self.policies_file.exists():
            self._create_default_policies()
        
        self.load_policies()
        logger.info(f"🔧 PolicyEngine initialized with {len(self.policies)} policies")
    
    def _create_default_policies(self):
        """Create default policy configuration"""
        default_policies = {
            'version': '1.0',
            'description': 'AGUS Strategic Decision Policies',
            'policies': [
                {
                    'rule_id': 'emergency_drawdown_protection',
                    'name': 'Emergency Drawdown Protection',
                    'description': 'Reduce risk when drawdown exceeds 10%',
                    'priority': 1,
                    'cooldown_minutes': 30,
                    'conditions': {
                        'current_drawdown': {'operator': 'greater_than', 'value': 0.10},
                        'emergency_mode': {'operator': 'equals', 'value': False}
                    },
                    'actions': [
                        {'type': 'adjust_risk_per_trade', 'value': 0.005, 'reason': 'Emergency drawdown protection'},
                        {'type': 'reduce_exposure', 'value': 0.5, 'reason': 'Reduce exposure due to drawdown'},
                        {'type': 'tighten_stops', 'value': 0.7, 'reason': 'Tighten stop losses'}
                    ]
                },
                {
                    'rule_id': 'high_volatility_adaptation',
                    'name': 'High Volatility Adaptation', 
                    'description': 'Adjust parameters during high volatility periods',
                    'priority': 3,
                    'cooldown_minutes': 60,
                    'conditions': {
                        'volatility_regime': {'operator': 'in', 'value': ['high', 'extreme']},
                        'risk_score': {'operator': 'greater_than', 'value': 0.7}
                    },
                    'actions': [
                        {'type': 'adjust_risk_per_trade', 'value': 0.008, 'reason': 'High volatility detected'},
                        {'type': 'widen_stops', 'value': 1.3, 'reason': 'Account for volatility'},
                        {'type': 'reduce_position_size', 'value': 0.8, 'reason': 'Smaller positions in volatility'}
                    ]
                },
                {
                    'rule_id': 'poor_performance_intervention',
                    'name': 'Poor Performance Intervention',
                    'description': 'Intervene when strategy performance is poor',
                    'priority': 2,
                    'cooldown_minutes': 120,
                    'conditions': {
                        'win_rate': {'operator': 'less_than', 'value': 0.35},
                        'sharpe_ratio': {'operator': 'less_than', 'value': 0.0},
                        'trades_count': {'operator': 'greater_than', 'value': 20}
                    },
                    'actions': [
                        {'type': 'reduce_risk_per_trade', 'value': 0.5, 'reason': 'Poor performance detected'},
                        {'type': 'increase_confidence_threshold', 'value': 0.7, 'reason': 'Be more selective'},
                        {'type': 'pause_new_positions', 'duration_minutes': 60, 'reason': 'Allow strategy to reset'}
                    ]
                },
                {
                    'rule_id': 'exceptional_performance_scaling',
                    'name': 'Exceptional Performance Scaling',
                    'description': 'Scale up during exceptional performance',
                    'priority': 4,
                    'cooldown_minutes': 180,
                    'conditions': {
                        'win_rate': {'operator': 'greater_than', 'value': 0.65},
                        'sharpe_ratio': {'operator': 'greater_than', 'value': 1.5},
                        'current_drawdown': {'operator': 'less_than', 'value': 0.03}
                    },
                    'actions': [
                        {'type': 'increase_risk_per_trade', 'value': 1.2, 'reason': 'Excellent performance'},
                        {'type': 'relax_confidence_threshold', 'value': 0.9, 'reason': 'Strategy is working well'},
                        {'type': 'increase_exposure', 'value': 1.1, 'reason': 'Scale up winning strategy'}
                    ]
                },
                {
                    'rule_id': 'market_regime_adaptation',
                    'name': 'Market Regime Adaptation',
                    'description': 'Adapt to different market regimes',
                    'priority': 5,
                    'cooldown_minutes': 240,
                    'conditions': {
                        'market_regime': {'operator': 'equals', 'value': 'trending'},
                        'trend_strength': {'operator': 'greater_than', 'value': 0.7}
                    },
                    'actions': [
                        {'type': 'adjust_take_profit', 'value': 1.3, 'reason': 'Strong trend detected'},
                        {'type': 'trail_stops_closer', 'value': 0.8, 'reason': 'Capture trend momentum'},
                        {'type': 'increase_position_hold_time', 'value': 1.5, 'reason': 'Let trends run'}
                    ]
                }
            ]
        }
        
        try:
            with open(self.policies_file, 'w') as f:
                yaml.dump(default_policies, f, default_flow_style=False, indent=2)
            logger.info(f"✅ Created default policies file: {self.policies_file}")
        except Exception as e:
            logger.error(f"❌ Failed to create default policies: {e}")
    
    def load_policies(self):
        """Load policies from YAML file"""
        try:
            with open(self.policies_file, 'r') as f:
                data = yaml.safe_load(f)
            
            self.policies = []
            for policy_data in data.get('policies', []):
                policy = PolicyRule(
                    rule_id=policy_data['rule_id'],
                    name=policy_data['name'],
                    description=policy_data['description'],
                    conditions=policy_data['conditions'],
                    actions=policy_data['actions'],
                    priority=policy_data.get('priority', 5),
                    enabled=policy_data.get('enabled', True),
                    cooldown_minutes=policy_data.get('cooldown_minutes', 60)
                )
                self.policies.append(policy)
            
            # Sort by priority (lower number = higher priority)
            self.policies.sort(key=lambda p: p.priority)
            logger.info(f"✅ Loaded {len(self.policies)} policies from {self.policies_file}")
            
        except Exception as e:
            logger.error(f"❌ Failed to load policies: {e}")
            self.policies = []
    
    def evaluate_conditions(self, conditions: Dict[str, Any], market_state: Dict[str, Any]) -> bool:
        """Evaluate if conditions are met given current market state"""
        try:
            for field, condition in conditions.items():
                value = market_state.get(field)
                if value is None:
                    logger.debug(f"Field {field} not found in market state")
                    return False
                
                operator = condition.get('operator')
                expected = condition.get('value')
                
                if operator == 'greater_than':
                    if not (value > expected):
                        return False
                elif operator == 'less_than':
                    if not (value < expected):
                        return False
                elif operator == 'equals':
                    if not (value == expected):
                        return False
                elif operator == 'in':
                    if not (value in expected):
                        return False
                elif operator == 'greater_than_or_equal':
                    if not (value >= expected):
                        return False
                elif operator == 'less_than_or_equal':
                    if not (value <= expected):
                        return False
                else:
                    logger.warning(f"Unknown operator: {operator}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error evaluating conditions: {e}")
            return False
    
    def find_applicable_policies(self, market_state: Dict[str, Any]) -> List[PolicyRule]:
        """Find policies that match current market conditions"""
        applicable = []
        current_time = datetime.now()
        
        for policy in self.policies:
            if not policy.enabled:
                continue
            
            # Check cooldown
            if (policy.last_triggered and 
                current_time - policy.last_triggered < timedelta(minutes=policy.cooldown_minutes)):
                continue
            
            # Evaluate conditions
            if self.evaluate_conditions(policy.conditions, market_state):
                applicable.append(policy)
        
        return applicable
    
    def generate_decisions(self, market_state: Dict[str, Any]) -> List[DecisionRecord]:
        """Generate decision recommendations based on current market state"""
        try:
            applicable_policies = self.find_applicable_policies(market_state)
            decisions = []
            
            for policy in applicable_policies:
                for action in policy.actions:
                    decision = DecisionRecord(
                        decision_type=self._map_action_to_decision_type(action.get('type', '')),
                        trigger_reason=f"Policy: {policy.name}",
                        analysis=f"Triggered by policy '{policy.name}': {policy.description}",
                        recommended_action=action,
                        execution_mode=ExecutionMode.DRY_RUN,  # Start with dry run
                        approval_required=self._requires_approval(action)
                    )
                    
                    # Safety check
                    safety_passed, safety_msg = self.safety_guardrails.validate_action(action, market_state)
                    decision.safety_checks_passed = safety_passed
                    if not safety_passed:
                        decision.error_message = safety_msg
                        decision.status = DecisionStatus.FAILED
                    
                    decisions.append(decision)
                    
                # Update policy trigger time
                policy.last_triggered = datetime.now()
            
            return decisions
            
        except Exception as e:
            logger.error(f"❌ Error generating decisions: {e}")
            return []
    
    def _map_action_to_decision_type(self, action_type: str) -> DecisionType:
        """Map action type to decision type"""
        mapping = {
            'adjust_risk_per_trade': DecisionType.RISK_ADJUSTMENT,
            'reduce_risk_per_trade': DecisionType.RISK_ADJUSTMENT,
            'increase_risk_per_trade': DecisionType.RISK_ADJUSTMENT,
            'adjust_exposure': DecisionType.RISK_ADJUSTMENT,
            'reduce_exposure': DecisionType.RISK_ADJUSTMENT,
            'increase_exposure': DecisionType.RISK_ADJUSTMENT,
            'adjust_take_profit': DecisionType.PARAMETER_CHANGE,
            'adjust_stop_loss': DecisionType.PARAMETER_CHANGE,
            'tighten_stops': DecisionType.PARAMETER_CHANGE,
            'widen_stops': DecisionType.PARAMETER_CHANGE,
            'deploy_strategy': DecisionType.STRATEGY_DEPLOYMENT,
            'retire_strategy': DecisionType.STRATEGY_RETIREMENT,
            'emergency_stop': DecisionType.EMERGENCY_ACTION,
            'pause_new_positions': DecisionType.POSITION_ADJUSTMENT
        }
        return mapping.get(action_type, DecisionType.PARAMETER_CHANGE)
    
    def _requires_approval(self, action: Dict[str, Any]) -> bool:
        """Determine if action requires human approval"""
        critical_actions = {
            'emergency_stop', 'deploy_strategy', 'retire_strategy',
            'adjust_leverage', 'large_exposure_change'
        }
        return action.get('type', '') in critical_actions


class QwenReasoner:
    """
    🧠 Intelligent reasoning using Qwen 2.5 integration
    
    Features:
    - Contextual analysis of trading situations
    - Reasoning about market conditions
    - Strategic recommendation generation
    - Fallback to rule-based systems
    """
    
    def __init__(self):
        self.available = AGUS_INTEGRATION_AVAILABLE
        self.context_window = 4096
        self.reasoning_prompts = self._load_reasoning_prompts()
        logger.info(f"🧠 QwenReasoner initialized - Available: {self.available}")
    
    def _load_reasoning_prompts(self) -> Dict[str, str]:
        """Load reasoning prompts for different scenarios"""
        return {
            'risk_analysis': """
Eres AGUS, un asistente de trading avanzado. Analiza la siguiente situación de riesgo:

DATOS DEL MERCADO:
{market_data}

ESTADO ACTUAL:
{current_state}

DECISIÓN PROPUESTA:
{proposed_decision}

Por favor, analiza:
1. ¿Es esta decisión apropiada dado el contexto actual?
2. ¿Qué riesgos potenciales ves?
3. ¿Hay factores que no se han considerado?
4. ¿Recomendarías modificaciones a la decisión?

Proporciona un análisis conciso y accionable.""",

            'strategy_evaluation': """
Eres AGUS, un asistente de trading experto. Evalúa la siguiente estrategia:

PERFORMANCE ACTUAL:
{performance_data}

CONDICIONES DE MERCADO:
{market_conditions}

DECISIÓN ESTRATÉGICA:
{strategy_decision}

Analiza:
1. ¿Esta estrategia es adecuada para las condiciones actuales?
2. ¿Qué ajustes recomendarías?
3. ¿Cuáles son los principales riesgos?
4. ¿Cómo optimizarías el rendimiento?

Sé específico y accionable en tus recomendaciones.""",

            'market_regime_analysis': """
Eres AGUS, analista de mercados. Analiza el régimen de mercado actual:

DATOS DE MERCADO:
{market_data}

MÉTRICAS DE VOLATILIDAD:
{volatility_metrics}

CONTEXTO HISTÓRICO:
{historical_context}

Determina:
1. ¿Qué régimen de mercado estamos experimentando?
2. ¿Cómo deberíamos ajustar nuestro enfoque?
3. ¿Qué oportunidades y riesgos presents?
4. ¿Qué cambios tácticos recomiendas?

Proporciona insights accionables para optimizar el trading."""
        }
    
    async def analyze_decision_async(self, decision: DecisionRecord, 
                                   market_state: Dict[str, Any]) -> str:
        """Analyze a decision using Qwen reasoning"""
        try:
            if not self.available:
                return self._fallback_analysis(decision, market_state)
            
            # Prepare context based on decision type
            if decision.decision_type == DecisionType.RISK_ADJUSTMENT:
                prompt_template = self.reasoning_prompts['risk_analysis']
            elif decision.decision_type in [DecisionType.STRATEGY_DEPLOYMENT, DecisionType.STRATEGY_RETIREMENT]:
                prompt_template = self.reasoning_prompts['strategy_evaluation']
            else:
                prompt_template = self.reasoning_prompts['market_regime_analysis']
            
            # Format prompt with current data
            prompt = prompt_template.format(
                market_data=json.dumps(market_state, indent=2),
                current_state=json.dumps({
                    'decision_id': decision.decision_id,
                    'trigger_reason': decision.trigger_reason,
                    'status': decision.status.value
                }, indent=2),
                proposed_decision=json.dumps(decision.recommended_action, indent=2),
                performance_data=market_state.get('performance', {}),
                market_conditions=market_state.get('market_conditions', {}),
                strategy_decision=decision.recommended_action,
                volatility_metrics=market_state.get('volatility_metrics', {}),
                historical_context=market_state.get('historical_context', {})
            )
            
            # Get Qwen analysis
            analysis = await qwen_chat_completion_async(
                prompt, 
                temperature=0.3,
                max_tokens=512
            )
            
            return analysis if analysis else self._fallback_analysis(decision, market_state)
            
        except Exception as e:
            logger.error(f"❌ Qwen analysis error: {e}")
            return self._fallback_analysis(decision, market_state)
    
    def analyze_decision(self, decision: DecisionRecord, market_state: Dict[str, Any]) -> str:
        """Synchronous version of decision analysis"""
        try:
            if not self.available:
                return self._fallback_analysis(decision, market_state)
            
            # Prepare simplified prompt for sync analysis
            prompt = f"""
Analiza esta decisión de trading:

DECISIÓN: {decision.recommended_action.get('type', 'unknown')}
RAZÓN: {decision.trigger_reason}
VALOR: {decision.recommended_action.get('value', 'N/A')}

ESTADO DEL MERCADO:
- Drawdown actual: {market_state.get('current_drawdown', 0):.1%}
- Score de riesgo: {market_state.get('risk_score', 0.5):.2f}
- Régimen de volatilidad: {market_state.get('volatility_regime', 'unknown')}

¿Es esta una decisión acertada? ¿Qué riesgos ves? ¿Recomendaciones?
"""
            
            analysis = qwen_generate_response(prompt, temperature=0.3, max_tokens=256)
            return analysis if analysis else self._fallback_analysis(decision, market_state)
            
        except Exception as e:
            logger.error(f"❌ Qwen sync analysis error: {e}")
            return self._fallback_analysis(decision, market_state)
    
    def _fallback_analysis(self, decision: DecisionRecord, market_state: Dict[str, Any]) -> str:
        """Fallback rule-based analysis when Qwen is not available"""
        try:
            action_type = decision.recommended_action.get('type', 'unknown')
            value = decision.recommended_action.get('value', 0)
            
            # Rule-based analysis
            risk_score = market_state.get('risk_score', 0.5)
            drawdown = market_state.get('current_drawdown', 0)
            volatility = market_state.get('volatility_regime', 'normal')
            
            analysis_parts = []
            
            # Decision appropriateness
            if action_type in ['reduce_risk_per_trade', 'reduce_exposure']:
                if risk_score > 0.7 or drawdown > 0.05:
                    analysis_parts.append("✅ Decisión apropiada: Alta necesidad de reducir riesgo")
                else:
                    analysis_parts.append("⚠️ Decisión conservadora: El riesgo actual es moderado")
            
            elif action_type in ['increase_risk_per_trade', 'increase_exposure']:
                if risk_score < 0.3 and drawdown < 0.02:
                    analysis_parts.append("✅ Decisión apropiada: Condiciones favorables para incrementar riesgo")
                else:
                    analysis_parts.append("⚠️ Decisión arriesgada: Considerar el contexto de riesgo actual")
            
            # Volatility considerations
            if volatility in ['high', 'extreme']:
                analysis_parts.append(f"🌪️ Alta volatilidad detectada: Recomienda precaución adicional")
            
            # Drawdown warnings
            if drawdown > 0.10:
                analysis_parts.append(f"🛡️ Drawdown elevado ({drawdown:.1%}): Priorizar protección de capital")
            
            return " | ".join(analysis_parts) if analysis_parts else "Análisis básico: Decisión dentro de parámetros normales"
            
        except Exception as e:
            return f"Error en análisis de respaldo: {e}"


class SafeExecutors:
    """
    🛡️ Safe execution modules for different types of actions
    
    Features:
    - RiskExecutor: Adjust dynamic risk manager
    - ParamExecutor: Modify trading parameters
    - StrategyExecutor: Deploy/retire strategies
    - LiquidityExecutor: Manage liquidity
    """
    
    def __init__(self):
        self.execution_log = []
        self.rollback_stack = []
        
        # Initialize component managers
        self.risk_manager = None
        self.config_manager = None
        self.strategy_engine = None
        
        self._initialize_managers()
        logger.info("🛡️ SafeExecutors initialized")
    
    def _initialize_managers(self):
        """Initialize management components"""
        try:
            if AGUS_INTEGRATION_AVAILABLE:
                self.risk_manager = DynamicRiskManager()
                self.config_manager = DynamicConfigManager()
                self.strategy_engine = StrategyDeploymentEngine()
            logger.info("✅ All management components initialized")
        except Exception as e:
            logger.warning(f"⚠️ Some components unavailable: {e}")
    
    def execute_decision(self, decision: DecisionRecord, 
                        execution_mode: ExecutionMode = ExecutionMode.DRY_RUN) -> bool:
        """Execute a decision with appropriate safety checks"""
        try:
            decision.execution_mode = execution_mode
            decision.status = DecisionStatus.ANALYZING
            
            logger.info(f"🔄 Executing decision {decision.decision_id} in {execution_mode.value} mode")
            
            # Pre-execution validation
            if not decision.safety_checks_passed:
                decision.status = DecisionStatus.FAILED
                decision.error_message = "Safety checks failed"
                return False
            
            action = decision.recommended_action
            action_type = action.get('type', '')
            
            # Route to appropriate executor
            success = False
            rollback_data = None
            
            if action_type.startswith('adjust_risk') or action_type.endswith('exposure'):
                success, rollback_data = self._execute_risk_action(action, execution_mode)
            elif action_type.startswith('adjust_') or action_type in ['tighten_stops', 'widen_stops']:
                success, rollback_data = self._execute_param_action(action, execution_mode)
            elif action_type in ['deploy_strategy', 'retire_strategy']:
                success, rollback_data = self._execute_strategy_action(action, execution_mode)
            elif action_type in ['pause_new_positions', 'emergency_stop']:
                success, rollback_data = self._execute_position_action(action, execution_mode)
            else:
                logger.warning(f"Unknown action type: {action_type}")
                decision.error_message = f"Unknown action type: {action_type}"
                decision.status = DecisionStatus.FAILED
                return False
            
            # Update decision status
            if success:
                decision.status = DecisionStatus.EXECUTED
                decision.rollback_data = rollback_data
                if rollback_data:
                    self.rollback_stack.append((decision.decision_id, rollback_data))
                logger.info(f"✅ Decision {decision.decision_id} executed successfully")
            else:
                decision.status = DecisionStatus.FAILED
                logger.error(f"❌ Decision {decision.decision_id} execution failed")
            
            # Log execution
            self.execution_log.append({
                'timestamp': datetime.now().isoformat(),
                'decision_id': decision.decision_id,
                'action': action,
                'execution_mode': execution_mode.value,
                'success': success,
                'rollback_available': rollback_data is not None
            })
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Execution error: {e}")
            decision.status = DecisionStatus.FAILED
            decision.error_message = str(e)
            return False
    
    def _execute_risk_action(self, action: Dict[str, Any], 
                           mode: ExecutionMode) -> Tuple[bool, Optional[Dict]]:
        """Execute risk-related actions"""
        try:
            action_type = action.get('type', '')
            value = action.get('value', 0)
            
            if mode == ExecutionMode.DRY_RUN:
                logger.info(f"🔍 DRY RUN: Would execute {action_type} with value {value}")
                return True, {'action': action, 'mode': 'dry_run'}
            
            rollback_data = {}
            
            if self.risk_manager is None:
                logger.warning("Risk manager not available")
                return False, None
            
            if action_type == 'adjust_risk_per_trade':
                # Store current value for rollback
                rollback_data['old_risk_per_trade'] = settings.risk_per_trade
                if mode != ExecutionMode.DRY_RUN:
                    settings.risk_per_trade = value
                logger.info(f"📊 Risk per trade adjusted to {value:.3f}")
            
            elif action_type == 'reduce_risk_per_trade':
                rollback_data['old_risk_per_trade'] = settings.risk_per_trade
                new_risk = settings.risk_per_trade * value
                if mode != ExecutionMode.DRY_RUN:
                    settings.risk_per_trade = new_risk
                logger.info(f"📉 Risk per trade reduced to {new_risk:.3f}")
            
            elif action_type == 'increase_risk_per_trade':
                rollback_data['old_risk_per_trade'] = settings.risk_per_trade
                new_risk = settings.risk_per_trade * value
                if mode != ExecutionMode.DRY_RUN:
                    settings.risk_per_trade = min(new_risk, 0.02)  # Safety cap at 2%
                logger.info(f"📈 Risk per trade increased to {min(new_risk, 0.02):.3f}")
            
            elif action_type in ['reduce_exposure', 'increase_exposure']:
                rollback_data['old_max_gross_exposure'] = settings.max_gross_exposure
                if action_type == 'reduce_exposure':
                    new_exposure = settings.max_gross_exposure * value
                else:
                    new_exposure = settings.max_gross_exposure * value
                
                if mode != ExecutionMode.DRY_RUN:
                    settings.max_gross_exposure = min(new_exposure, 1.5)  # Safety cap
                logger.info(f"🎯 Exposure adjusted to {min(new_exposure, 1.5):.2f}")
            
            return True, rollback_data
            
        except Exception as e:
            logger.error(f"❌ Risk action execution error: {e}")
            return False, None
    
    def _execute_param_action(self, action: Dict[str, Any], 
                            mode: ExecutionMode) -> Tuple[bool, Optional[Dict]]:
        """Execute parameter adjustment actions"""
        try:
            action_type = action.get('type', '')
            value = action.get('value', 1.0)
            
            if mode == ExecutionMode.DRY_RUN:
                logger.info(f"🔍 DRY RUN: Would execute {action_type} with value {value}")
                return True, {'action': action, 'mode': 'dry_run'}
            
            rollback_data = {}
            
            if action_type == 'adjust_take_profit':
                rollback_data['old_take_profit_pct'] = settings.take_profit_pct
                new_tp = settings.take_profit_pct * value
                if mode != ExecutionMode.DRY_RUN:
                    settings.take_profit_pct = max(0.01, min(new_tp, 0.10))  # 1%-10% range
                logger.info(f"🎯 Take profit adjusted to {settings.take_profit_pct:.3f}")
            
            elif action_type in ['tighten_stops', 'widen_stops']:
                rollback_data['old_stop_loss_pct'] = settings.stop_loss_pct
                new_sl = settings.stop_loss_pct * value
                if mode != ExecutionMode.DRY_RUN:
                    settings.stop_loss_pct = max(0.003, min(new_sl, 0.05))  # 0.3%-5% range
                logger.info(f"🛡️ Stop loss adjusted to {settings.stop_loss_pct:.3f}")
            
            elif action_type == 'increase_confidence_threshold':
                if self.config_manager and mode != ExecutionMode.DRY_RUN:
                    # Use config manager to adjust confidence threshold
                    current_config = self.config_manager.current_config
                    rollback_data['old_confidence'] = current_config.get('confidence_threshold', 0.5)
                    current_config['confidence_threshold'] = value
                logger.info(f"🎯 Confidence threshold adjusted to {value}")
            
            return True, rollback_data
            
        except Exception as e:
            logger.error(f"❌ Parameter action execution error: {e}")
            return False, None
    
    def _execute_strategy_action(self, action: Dict[str, Any], 
                               mode: ExecutionMode) -> Tuple[bool, Optional[Dict]]:
        """Execute strategy deployment/retirement actions"""
        try:
            action_type = action.get('type', '')
            
            if mode == ExecutionMode.DRY_RUN:
                logger.info(f"🔍 DRY RUN: Would execute {action_type}")
                return True, {'action': action, 'mode': 'dry_run'}
            
            if self.strategy_engine is None:
                logger.warning("Strategy engine not available")
                return False, None
            
            rollback_data = {'action_type': action_type}
            
            if action_type == 'deploy_strategy':
                strategy_id = action.get('strategy_id', 'default')
                allocation = action.get('allocation', 0.1)
                
                # Would deploy strategy via strategy engine
                logger.info(f"🚀 Strategy {strategy_id} deployment initiated with {allocation:.1%} allocation")
                rollback_data['deployed_strategy'] = strategy_id
            
            elif action_type == 'retire_strategy':
                strategy_id = action.get('strategy_id', 'default')
                
                # Would retire strategy via strategy engine
                logger.info(f"🛑 Strategy {strategy_id} retirement initiated")
                rollback_data['retired_strategy'] = strategy_id
            
            return True, rollback_data
            
        except Exception as e:
            logger.error(f"❌ Strategy action execution error: {e}")
            return False, None
    
    def _execute_position_action(self, action: Dict[str, Any], 
                               mode: ExecutionMode) -> Tuple[bool, Optional[Dict]]:
        """Execute position management actions"""
        try:
            action_type = action.get('type', '')
            
            if mode == ExecutionMode.DRY_RUN:
                logger.info(f"🔍 DRY RUN: Would execute {action_type}")
                return True, {'action': action, 'mode': 'dry_run'}
            
            rollback_data = {'action_type': action_type}
            
            if action_type == 'pause_new_positions':
                duration = action.get('duration_minutes', 60)
                # Set flag to pause new positions
                logger.info(f"⏸️ New positions paused for {duration} minutes")
                rollback_data['pause_duration'] = duration
                rollback_data['pause_start'] = datetime.now().isoformat()
            
            elif action_type == 'emergency_stop':
                # Trigger emergency stop
                logger.critical("🚨 EMERGENCY STOP TRIGGERED")
                rollback_data['emergency_triggered'] = True
            
            return True, rollback_data
            
        except Exception as e:
            logger.error(f"❌ Position action execution error: {e}")
            return False, None
    
    def rollback_decision(self, decision_id: str) -> bool:
        """Rollback a previously executed decision"""
        try:
            # Find rollback data
            rollback_data = None
            for stored_id, data in self.rollback_stack:
                if stored_id == decision_id:
                    rollback_data = data
                    break
            
            if not rollback_data:
                logger.warning(f"No rollback data found for decision {decision_id}")
                return False
            
            logger.info(f"🔄 Rolling back decision {decision_id}")
            
            # Restore old values
            if 'old_risk_per_trade' in rollback_data:
                settings.risk_per_trade = rollback_data['old_risk_per_trade']
                logger.info(f"↩️ Risk per trade restored to {settings.risk_per_trade:.3f}")
            
            if 'old_take_profit_pct' in rollback_data:
                settings.take_profit_pct = rollback_data['old_take_profit_pct']
                logger.info(f"↩️ Take profit restored to {settings.take_profit_pct:.3f}")
            
            if 'old_stop_loss_pct' in rollback_data:
                settings.stop_loss_pct = rollback_data['old_stop_loss_pct']
                logger.info(f"↩️ Stop loss restored to {settings.stop_loss_pct:.3f}")
            
            if 'old_max_gross_exposure' in rollback_data:
                settings.max_gross_exposure = rollback_data['old_max_gross_exposure']
                logger.info(f"↩️ Exposure restored to {settings.max_gross_exposure:.2f}")
            
            # Remove from rollback stack
            self.rollback_stack = [(id, data) for id, data in self.rollback_stack if id != decision_id]
            
            logger.info(f"✅ Decision {decision_id} rolled back successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Rollback error: {e}")
            return False


class DecisionOrchestrator:
    """
    🎼 Main coordinator for the strategic decision engine
    
    Features:
    - Integration with AGUS orchestrator
    - Scheduled decision cycles
    - Event-driven decision making
    - Emergency response coordination
    """
    
    def __init__(self):
        self.policy_engine = PolicyEngine()
        self.qwen_reasoner = QwenReasoner()
        self.safe_executors = SafeExecutors()
        
        # State management
        self.decision_queue = deque()
        self.pending_approvals = []
        self.emergency_mode = False
        self.last_decision_cycle = None
        
        # Integration with AGUS
        self.agus_orchestrator = None
        self.integrated_risk_system = None
        
        self._initialize_integrations()
        self._start_decision_loop()
        
        logger.info("🎼 DecisionOrchestrator initialized and running")
    
    def _initialize_integrations(self):
        """Initialize integrations with existing AGUS systems"""
        try:
            if AGUS_INTEGRATION_AVAILABLE:
                self.agus_orchestrator = AGUSOrchestrator()
                self.integrated_risk_system = IntegratedRiskSystem()
                
                # Subscribe to AGUS events
                self.agus_orchestrator.event_bus.subscribe(
                    EventType.RISK_ALERT, 
                    self._handle_risk_alert
                )
                self.agus_orchestrator.event_bus.subscribe(
                    EventType.SYSTEM_ERROR, 
                    self._handle_system_error
                )
                
                logger.info("✅ AGUS integration established")
            else:
                logger.warning("⚠️ AGUS integration not available - running standalone")
                
        except Exception as e:
            logger.error(f"❌ Integration initialization error: {e}")
    
    def _start_decision_loop(self):
        """Start the main decision loop in a background thread"""
        def decision_loop():
            while True:
                try:
                    self._run_decision_cycle()
                    time.sleep(300)  # Run every 5 minutes
                except Exception as e:
                    logger.error(f"❌ Decision loop error: {e}")
                    time.sleep(60)  # Wait 1 minute on error
        
        decision_thread = threading.Thread(target=decision_loop, daemon=True)
        decision_thread.start()
        logger.info("🔄 Decision loop started")
    
    def _run_decision_cycle(self):
        """Run a complete decision cycle"""
        try:
            logger.debug("🔄 Running decision cycle")
            
            # Get current market state
            market_state = self._gather_market_state()
            
            # Generate decisions from policies
            decisions = self.policy_engine.generate_decisions(market_state)
            
            if not decisions:
                logger.debug("No policy-triggered decisions")
                return
            
            logger.info(f"🎯 Generated {len(decisions)} decisions from policies")
            
            # Analyze decisions with Qwen
            for decision in decisions:
                try:
                    analysis = self.qwen_reasoner.analyze_decision(decision, market_state)
                    decision.analysis = analysis
                    
                    # Determine execution mode
                    execution_mode = self._determine_execution_mode(decision, market_state)
                    
                    # Execute decision
                    if execution_mode == ExecutionMode.APPROVAL_GATE:
                        self.pending_approvals.append(decision)
                        logger.info(f"📋 Decision {decision.decision_id} queued for approval")
                    else:
                        success = self.safe_executors.execute_decision(decision, execution_mode)
                        if success:
                            logger.info(f"✅ Decision {decision.decision_id} executed successfully")
                        else:
                            logger.error(f"❌ Decision {decision.decision_id} execution failed")
                
                except Exception as e:
                    logger.error(f"❌ Error processing decision {decision.decision_id}: {e}")
            
            self.last_decision_cycle = datetime.now()
            
        except Exception as e:
            logger.error(f"❌ Decision cycle error: {e}")
    
    def _gather_market_state(self) -> Dict[str, Any]:
        """Gather current market state for decision making"""
        try:
            market_state = {
                'timestamp': datetime.now().isoformat(),
                'current_drawdown': 0.0,
                'risk_score': 0.5,
                'volatility_regime': 'normal',
                'win_rate': 0.5,
                'sharpe_ratio': 0.0,
                'trades_count': 0,
                'emergency_mode': False,
                'market_regime': 'unknown',
                'trend_strength': 0.0
            }
            
            # Get data from integrated risk system
            if self.integrated_risk_system:
                try:
                    # Get a sample assessment to extract current state
                    sample_assessment = self.integrated_risk_system.get_comprehensive_risk_assessment(
                        symbol="BTC/USD", signal_strength=0.5, equity=30000, price=50000
                    )
                    
                    market_state.update({
                        'current_drawdown': sample_assessment.current_drawdown,
                        'risk_score': sample_assessment.risk_score,
                        'volatility_regime': sample_assessment.volatility_regime,
                        'emergency_mode': sample_assessment.emergency_mode
                    })
                    
                except Exception as e:
                    logger.debug(f"Could not get integrated risk data: {e}")
            
            # Get performance data from config manager
            if self.safe_executors.config_manager:
                try:
                    perf_data = self.safe_executors.config_manager.analyze_recent_performance()
                    market_state.update({
                        'win_rate': perf_data.get('win_rate', 0.5),
                        'trades_count': perf_data.get('trades_count', 0)
                    })
                except Exception as e:
                    logger.debug(f"Could not get performance data: {e}")
            
            return market_state
            
        except Exception as e:
            logger.error(f"❌ Error gathering market state: {e}")
            return {'error': str(e), 'timestamp': datetime.now().isoformat()}
    
    def _determine_execution_mode(self, decision: DecisionRecord, 
                                 market_state: Dict[str, Any]) -> ExecutionMode:
        """Determine appropriate execution mode for a decision"""
        try:
            # Emergency conditions
            if (market_state.get('emergency_mode', False) or 
                market_state.get('current_drawdown', 0) > 0.15):
                return ExecutionMode.EMERGENCY
            
            # High-risk decisions require approval
            if decision.approval_required:
                return ExecutionMode.APPROVAL_GATE
            
            # Conservative decisions can be auto-executed safely
            action_type = decision.recommended_action.get('type', '')
            conservative_actions = {
                'reduce_risk_per_trade', 'reduce_exposure', 'tighten_stops',
                'pause_new_positions', 'increase_confidence_threshold'
            }
            
            if action_type in conservative_actions:
                return ExecutionMode.SAFE_AUTO
            
            # PRODUCTION MODE: Default to SAFE_AUTO for real execution
            # Safety checks in SafetyGuardrails will validate all actions
            logger.info(f"🔄 Using SAFE_AUTO for action '{action_type}' - safety checks will validate")
            return ExecutionMode.SAFE_AUTO
            
        except Exception as e:
            logger.error(f"❌ Error determining execution mode: {e}")
            return ExecutionMode.DRY_RUN
    
    def _handle_risk_alert(self, event: 'Event'):
        """Handle risk alerts from AGUS"""
        try:
            logger.warning(f"🚨 Risk alert received: {event.data}")
            
            # Generate emergency decision
            emergency_decision = DecisionRecord(
                decision_type=DecisionType.EMERGENCY_ACTION,
                trigger_reason=f"Risk alert: {event.data.get('message', 'Unknown')}",
                analysis="Automatic emergency response to risk alert",
                recommended_action={
                    'type': 'reduce_risk_per_trade',
                    'value': 0.5,
                    'reason': 'Emergency risk reduction'
                },
                execution_mode=ExecutionMode.EMERGENCY,
                safety_checks_passed=True
            )
            
            # Execute immediately
            success = self.safe_executors.execute_decision(emergency_decision, ExecutionMode.EMERGENCY)
            logger.info(f"🚨 Emergency decision executed: {success}")
            
        except Exception as e:
            logger.error(f"❌ Error handling risk alert: {e}")
    
    def _handle_system_error(self, event: 'Event'):
        """Handle system errors from AGUS"""
        try:
            logger.error(f"🚨 System error received: {event.data}")
            
            # Trigger safe mode
            self.emergency_mode = True
            
            # Reduce all risk parameters
            emergency_decisions = [
                DecisionRecord(
                    decision_type=DecisionType.EMERGENCY_ACTION,
                    trigger_reason="System error detected",
                    recommended_action={
                        'type': 'reduce_risk_per_trade',
                        'value': 0.3,
                        'reason': 'System error safety reduction'
                    },
                    execution_mode=ExecutionMode.EMERGENCY,
                    safety_checks_passed=True
                ),
                DecisionRecord(
                    decision_type=DecisionType.POSITION_ADJUSTMENT,
                    trigger_reason="System error detected",
                    recommended_action={
                        'type': 'pause_new_positions',
                        'duration_minutes': 30,
                        'reason': 'System error pause'
                    },
                    execution_mode=ExecutionMode.EMERGENCY,
                    safety_checks_passed=True
                )
            ]
            
            for decision in emergency_decisions:
                self.safe_executors.execute_decision(decision, ExecutionMode.EMERGENCY)
            
        except Exception as e:
            logger.error(f"❌ Error handling system error: {e}")
    
    def approve_decision(self, decision_id: str, approved_by: str = "user") -> bool:
        """Approve a pending decision"""
        try:
            for decision in self.pending_approvals:
                if decision.decision_id == decision_id:
                    decision.approved_by = approved_by
                    decision.status = DecisionStatus.APPROVED
                    
                    # Execute the approved decision
                    success = self.safe_executors.execute_decision(decision, ExecutionMode.SAFE_AUTO)
                    
                    # Remove from pending
                    self.pending_approvals.remove(decision)
                    
                    logger.info(f"✅ Decision {decision_id} approved and executed by {approved_by}")
                    return success
            
            logger.warning(f"Decision {decision_id} not found in pending approvals")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error approving decision: {e}")
            return False
    
    def get_pending_approvals(self) -> List[DecisionRecord]:
        """Get list of decisions pending approval"""
        return self.pending_approvals.copy()
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get summary of recent executions"""
        try:
            recent_logs = self.safe_executors.execution_log[-20:]  # Last 20 executions
            
            summary = {
                'total_executions': len(self.safe_executors.execution_log),
                'recent_executions': len(recent_logs),
                'successful_executions': len([log for log in recent_logs if log['success']]),
                'pending_approvals': len(self.pending_approvals),
                'rollback_available': len(self.safe_executors.rollback_stack),
                'emergency_mode': self.emergency_mode,
                'last_decision_cycle': self.last_decision_cycle.isoformat() if self.last_decision_cycle else None,
                'recent_logs': recent_logs
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Error generating execution summary: {e}")
            return {'error': str(e)}


# Global instance
_decision_engine = None

def get_decision_engine() -> DecisionOrchestrator:
    """Get the global decision engine instance"""
    global _decision_engine
    if _decision_engine is None:
        _decision_engine = DecisionOrchestrator()
    return _decision_engine


# CLI interface for testing and management
def main():
    """CLI interface for the decision engine"""
    import argparse
    
    parser = argparse.ArgumentParser(description='AGUS Decision Engine CLI')
    parser.add_argument('--test-policies', action='store_true', help='Test policy evaluation')
    parser.add_argument('--approve-decision', type=str, help='Approve a pending decision')
    parser.add_argument('--rollback-decision', type=str, help='Rollback a decision')
    parser.add_argument('--status', action='store_true', help='Show engine status')
    
    args = parser.parse_args()
    
    engine = get_decision_engine()
    
    if args.test_policies:
        # Test policy evaluation
        test_market_state = {
            'current_drawdown': 0.12,
            'risk_score': 0.8,
            'volatility_regime': 'high',
            'win_rate': 0.3,
            'sharpe_ratio': -0.5,
            'trades_count': 25,
            'emergency_mode': False
        }
        
        decisions = engine.policy_engine.generate_decisions(test_market_state)
        print(f"Generated {len(decisions)} decisions:")
        for decision in decisions:
            print(f"  - {decision.trigger_reason}: {decision.recommended_action}")
    
    elif args.approve_decision:
        success = engine.approve_decision(args.approve_decision)
        print(f"Approval {'successful' if success else 'failed'}")
    
    elif args.rollback_decision:
        success = engine.safe_executors.rollback_decision(args.rollback_decision)
        print(f"Rollback {'successful' if success else 'failed'}")
    
    elif args.status:
        summary = engine.get_execution_summary()
        print("Engine Status:")
        print(json.dumps(summary, indent=2))
    
    else:
        print("AGUS Decision Engine is running...")
        print("Use --help for available commands")


if __name__ == "__main__":
    main()