"""
Reinforcement Learning System para estrategias de trading adaptivas.
Implementa Q-Learning y Deep Q-Networks (DQN) para optimización automática de decisiones.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from collections import deque
import random
import json
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import Dense, Dropout
    from tensorflow.keras.optimizers import Adam
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False

from .util import logger


class TradingEnvironment:
    """
    Environment de trading para Reinforcement Learning.
    Simula mercado y calcula recompensas por acciones de trading.
    """
    
    def __init__(self, data: pd.DataFrame, initial_balance: float = 10000.0):
        self.data = data.copy()
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.position = 0.0  # Posición actual (-1 a 1)
        self.current_step = 0
        self.max_steps = len(data) - 1
        self.trade_history = []
        
        # Estados y acciones
        self.action_space_size = 3  # 0=SELL, 1=HOLD, 2=BUY
        self.state_size = 10  # Número de features para el estado
        
        # Métricas de performance
        self.total_reward = 0.0
        self.trades_count = 0
        self.winning_trades = 0
        
        self.reset()
    
    def reset(self):
        """Reinicia el environment."""
        self.balance = self.initial_balance
        self.position = 0.0
        self.current_step = 0
        self.trade_history = []
        self.total_reward = 0.0
        self.trades_count = 0
        self.winning_trades = 0
        
        return self._get_state()
    
    def _get_state(self) -> np.ndarray:
        """Obtiene estado actual del environment."""
        if self.current_step >= len(self.data):
            return np.zeros(self.state_size)
        
        row = self.data.iloc[self.current_step]
        
        # Estado incluye: precio, indicadores técnicos, posición actual, balance normalizado
        state = np.array([
            row.get('close_norm', 0.0),      # Precio normalizado
            row.get('rsi', 50.0) / 100.0,    # RSI normalizado
            row.get('ema_short', 0.0),       # EMA corto
            row.get('ema_long', 0.0),        # EMA largo
            row.get('macd', 0.0),            # MACD
            row.get('bb_position', 0.5),     # Posición en Bollinger Bands
            row.get('volume_norm', 0.5),     # Volumen normalizado
            self.position,                    # Posición actual
            (self.balance / self.initial_balance) - 1.0,  # Balance normalizado
            min(self.current_step / self.max_steps, 1.0)  # Progreso temporal
        ])
        
        return state
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict]:
        """
        Ejecuta acción y retorna (next_state, reward, done, info).
        """
        if self.current_step >= self.max_steps:
            return self._get_state(), 0.0, True, {}
        
        # Obtener precios
        current_price = self.data.iloc[self.current_step]['close']
        next_step = min(self.current_step + 1, self.max_steps - 1)
        next_price = self.data.iloc[next_step]['close']
        
        # Ejecutar acción
        reward = self._execute_action(action, current_price, next_price)
        
        # Avanzar step
        self.current_step += 1
        
        # Verificar si terminó
        done = self.current_step >= self.max_steps
        
        # Info adicional
        info = {
            'balance': self.balance,
            'position': self.position,
            'total_reward': self.total_reward,
            'trades_count': self.trades_count,
            'win_rate': self.winning_trades / max(self.trades_count, 1)
        }
        
        return self._get_state(), reward, done, info
    
    def _execute_action(self, action: int, current_price: float, next_price: float) -> float:
        """
        Ejecuta acción de trading y calcula recompensa.
        """
        old_position = self.position
        price_change = (next_price - current_price) / current_price
        
        # Definir nueva posición basada en acción
        if action == 0:      # SELL
            target_position = -0.5
        elif action == 1:    # HOLD
            target_position = self.position  # Mantener posición
        else:               # BUY (action == 2)
            target_position = 0.5
        
        # Calcular cambio de posición
        position_change = target_position - self.position
        
        # Costo de transacción (0.1%)
        transaction_cost = abs(position_change) * 0.001
        
        # Reward basado en P&L de la posición
        pnl_reward = self.position * price_change * self.balance
        
        # Penalty por cambios excesivos de posición
        position_change_penalty = abs(position_change) * 0.01
        
        # Reward por mantener posición ganadora
        consistency_bonus = 0.0
        if abs(self.position) > 0.1 and self.position * price_change > 0:
            consistency_bonus = 0.02
        
        # Penalty por drawdown excesivo
        drawdown_penalty = 0.0
        if self.balance < self.initial_balance * 0.9:  # >10% drawdown
            drawdown_penalty = 0.05
        
        # Reward total
        total_reward = (
            pnl_reward - 
            transaction_cost - 
            position_change_penalty + 
            consistency_bonus - 
            drawdown_penalty
        )
        
        # Actualizar estado
        self.position = target_position
        self.balance += pnl_reward - (transaction_cost * self.balance)
        self.total_reward += total_reward
        
        # Registrar trade si hubo cambio significativo
        if abs(position_change) > 0.1:
            self.trades_count += 1
            if total_reward > 0:
                self.winning_trades += 1
            
            self.trade_history.append({
                'step': self.current_step,
                'action': action,
                'old_position': old_position,
                'new_position': self.position,
                'price': current_price,
                'reward': total_reward,
                'balance': self.balance
            })
        
        return total_reward


class DQNAgent:
    """
    Deep Q-Network Agent para trading con experiencia replay.
    """
    
    def __init__(self, state_size: int = 10, action_size: int = 3, learning_rate: float = 0.001):
        self.state_size = state_size
        self.action_size = action_size
        self.learning_rate = learning_rate
        
        # Hyperparámetros
        self.epsilon = 1.0          # Exploration rate
        self.epsilon_min = 0.01     # Minimum exploration rate
        self.epsilon_decay = 0.995  # Decay rate
        self.memory_size = 2000
        self.batch_size = 32
        self.gamma = 0.95           # Discount factor
        
        # Experience replay buffer
        self.memory = deque(maxlen=self.memory_size)
        
        # Neural networks
        self.q_network = None
        self.target_network = None
        
        if TENSORFLOW_AVAILABLE:
            self.q_network = self._build_network()
            self.target_network = self._build_network()
            self.update_target_network()
    
    def _build_network(self):
        """Construye red neuronal para Q-values."""
        if not TENSORFLOW_AVAILABLE:
            return None
        
        model = Sequential([
            Dense(128, input_dim=self.state_size, activation='relu'),
            Dropout(0.2),
            Dense(64, activation='relu'),
            Dropout(0.2),
            Dense(32, activation='relu'),
            Dense(self.action_size, activation='linear')
        ])
        
        model.compile(
            optimizer=Adam(learning_rate=self.learning_rate),
            loss='mse'
        )
        
        return model
    
    def remember(self, state: np.ndarray, action: int, reward: float, 
                 next_state: np.ndarray, done: bool):
        """Almacena experiencia en memoria."""
        self.memory.append((state, action, reward, next_state, done))
    
    def act(self, state: np.ndarray, training: bool = True) -> int:
        """Selecciona acción usando epsilon-greedy policy."""
        if not TENSORFLOW_AVAILABLE or self.q_network is None:
            return random.choice(range(self.action_size))
        
        # Exploration vs Exploitation
        if training and random.random() <= self.epsilon:
            return random.choice(range(self.action_size))
        
        # Predict Q-values
        state_batch = np.reshape(state, (1, self.state_size))
        q_values = self.q_network.predict(state_batch, verbose=0)[0]
        
        return np.argmax(q_values)
    
    def replay(self) -> float:
        """Entrena la red con experiencias almacenadas."""
        if not TENSORFLOW_AVAILABLE or len(self.memory) < self.batch_size:
            return 0.0
        
        # Sample random batch
        batch = random.sample(self.memory, self.batch_size)
        
        # Prepare training data
        states = np.array([e[0] for e in batch])
        actions = np.array([e[1] for e in batch])
        rewards = np.array([e[2] for e in batch])
        next_states = np.array([e[3] for e in batch])
        dones = np.array([e[4] for e in batch])
        
        # Predict Q-values
        current_q_values = self.q_network.predict(states, verbose=0)
        next_q_values = self.target_network.predict(next_states, verbose=0)
        
        # Update Q-values with Bellman equation
        for i in range(self.batch_size):
            if dones[i]:
                current_q_values[i][actions[i]] = rewards[i]
            else:
                current_q_values[i][actions[i]] = rewards[i] + self.gamma * np.max(next_q_values[i])
        
        # Train the network
        history = self.q_network.fit(states, current_q_values, epochs=1, verbose=0)
        loss = history.history['loss'][0]
        
        # Decay epsilon
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
        
        return loss
    
    def update_target_network(self):
        """Actualiza la target network con pesos de la main network."""
        if TENSORFLOW_AVAILABLE and self.target_network is not None:
            self.target_network.set_weights(self.q_network.get_weights())


class RLTradingSystem:
    """
    Sistema completo de Reinforcement Learning para trading.
    """
    
    def __init__(self):
        self.agent = None
        self.environment = None
        self.training_history = []
        self.is_trained = False
        
        if TENSORFLOW_AVAILABLE:
            self.agent = DQNAgent()
    
    def train(self, data: pd.DataFrame, episodes: int = 100) -> Dict:
        """
        Entrena el agente de RL en datos históricos.
        """
        if not TENSORFLOW_AVAILABLE or self.agent is None:
            logger.warning("⚠️ TensorFlow no disponible - RL deshabilitado")
            return {'success': False, 'reason': 'TensorFlow not available'}
        
        # Preparar datos para RL
        rl_data = self._prepare_rl_data(data)
        
        if len(rl_data) < 100:
            logger.warning("⚠️ Datos insuficientes para RL")
            return {'success': False, 'reason': 'Insufficient data'}
        
        self.environment = TradingEnvironment(rl_data)
        
        training_metrics = {
            'episode_rewards': [],
            'episode_lengths': [],
            'win_rates': [],
            'final_balances': []
        }
        
        logger.info(f"🧠 Iniciando entrenamiento RL: {episodes} episodios")
        
        for episode in range(episodes):
            state = self.environment.reset()
            total_reward = 0.0
            step_count = 0
            
            while True:
                # Seleccionar acción
                action = self.agent.act(state, training=True)
                
                # Ejecutar acción
                next_state, reward, done, info = self.environment.step(action)
                
                # Almacenar experiencia
                self.agent.remember(state, action, reward, next_state, done)
                
                state = next_state
                total_reward += reward
                step_count += 1
                
                if done:
                    break
            
            # Entrenar agente
            if len(self.agent.memory) > self.agent.batch_size:
                loss = self.agent.replay()
                
                # Update target network cada 10 episodios
                if episode % 10 == 0:
                    self.agent.update_target_network()
            
            # Registrar métricas
            training_metrics['episode_rewards'].append(total_reward)
            training_metrics['episode_lengths'].append(step_count)
            training_metrics['win_rates'].append(info['win_rate'])
            training_metrics['final_balances'].append(info['balance'])
            
            # Log progreso
            if episode % 20 == 0 or episode == episodes - 1:
                avg_reward = np.mean(training_metrics['episode_rewards'][-20:])
                avg_balance = np.mean(training_metrics['final_balances'][-20:])
                current_epsilon = self.agent.epsilon
                
                logger.info(f"📊 Episodio {episode+1}/{episodes}: "
                          f"Reward={avg_reward:.3f}, "
                          f"Balance=${avg_balance:.0f}, "
                          f"ε={current_epsilon:.3f}")
        
        self.is_trained = True
        self.training_history = training_metrics
        
        # Calcular métricas finales
        final_metrics = {
            'success': True,
            'total_episodes': episodes,
            'avg_reward': np.mean(training_metrics['episode_rewards'][-50:]),
            'avg_balance': np.mean(training_metrics['final_balances'][-50:]),
            'avg_win_rate': np.mean(training_metrics['win_rates'][-50:]),
            'final_epsilon': self.agent.epsilon
        }
        
        logger.info(f"✅ Entrenamiento RL completado: "
                   f"Reward={final_metrics['avg_reward']:.3f}, "
                   f"Win Rate={final_metrics['avg_win_rate']:.1%}")
        
        return final_metrics
    
    def _prepare_rl_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Prepara datos para entrenamiento de RL.
        """
        rl_data = data.copy()
        
        # Normalizar precio
        rl_data['close_norm'] = (rl_data['close'] - rl_data['close'].mean()) / rl_data['close'].std()
        
        # Normalizar volumen
        if 'volume' in rl_data.columns:
            rl_data['volume_norm'] = (rl_data['volume'] - rl_data['volume'].mean()) / rl_data['volume'].std()
        else:
            rl_data['volume_norm'] = 0.0
        
        # Asegurar que tenemos las columnas necesarias
        required_cols = ['rsi', 'ema_short', 'ema_long', 'macd', 'bb_position']
        for col in required_cols:
            if col not in rl_data.columns:
                rl_data[col] = 0.0
        
        # Llenar NaN values
        rl_data = rl_data.fillna(method='forward').fillna(0)
        
        return rl_data
    
    def predict_action(self, current_state: np.ndarray) -> Tuple[int, float]:
        """
        Predice mejor acción para estado actual.
        """
        if not self.is_trained or not TENSORFLOW_AVAILABLE or self.agent is None:
            return 1, 0.0  # HOLD con confianza 0
        
        # Predecir sin exploration
        action = self.agent.act(current_state, training=False)
        
        # Calcular confianza basada en Q-values
        if self.agent.q_network is not None:
            state_batch = np.reshape(current_state, (1, len(current_state)))
            q_values = self.agent.q_network.predict(state_batch, verbose=0)[0]
            
            # Confianza = diferencia entre mejor y segunda mejor acción
            sorted_q = np.sort(q_values)
            confidence = sorted_q[-1] - sorted_q[-2] if len(sorted_q) > 1 else 0.0
            confidence = max(0.0, min(1.0, confidence))  # Normalizar 0-1
        else:
            confidence = 0.0
        
        return action, confidence
    
    def get_rl_signal(self, data: pd.DataFrame) -> float:
        """
        Convierte acción de RL a señal de trading (-1 a +1).
        """
        if not self.is_trained or len(data) < 10:
            return 0.0
        
        # Preparar estado actual
        rl_data = self._prepare_rl_data(data)
        current_state = self._get_state_from_data(rl_data.iloc[-1])
        
        # Predecir acción
        action, confidence = self.predict_action(current_state)
        
        # Convertir acción a señal
        if action == 0:      # SELL
            return -confidence
        elif action == 2:    # BUY
            return confidence
        else:               # HOLD
            return 0.0
    
    def _get_state_from_data(self, row: pd.Series) -> np.ndarray:
        """Convierte fila de datos a estado para RL."""
        state = np.array([
            row.get('close_norm', 0.0),
            row.get('rsi', 50.0) / 100.0,
            row.get('ema_short', 0.0),
            row.get('ema_long', 0.0),
            row.get('macd', 0.0),
            row.get('bb_position', 0.5),
            row.get('volume_norm', 0.5),
            0.0,  # position (unknown in prediction)
            0.0,  # balance change (unknown)
            1.0   # time progress (assume end)
        ])
        
        return state


# Instancia global del sistema RL
rl_trading_system = RLTradingSystem()