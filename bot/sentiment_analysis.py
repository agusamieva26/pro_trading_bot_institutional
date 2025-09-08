"""
Sentiment Analysis Integration con Fear & Greed Index y market sentiment.
Detecta extremos de mercado para optimizar entrada/salida de posiciones.
"""

import requests
import pandas as pd
import numpy as np
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import json
from .util import logger


class SentimentAnalyzer:
    """
    Analizador de sentiment que integra múltiples fuentes para detectar
    extremos de mercado y ajustar estrategia en consecuencia.
    """
    
    def __init__(self):
        # Configuración de APIs y endpoints
        self.fear_greed_api = "https://api.alternative.me/fng/"
        
        # Umbrales de sentiment
        self.extreme_fear_threshold = 25
        self.fear_threshold = 45
        self.greed_threshold = 75
        self.extreme_greed_threshold = 90
        
        # Cache para evitar llamadas excesivas
        self._cache = {}
        self._cache_ttl = 300  # 5 minutos
    
    def get_fear_greed_index(self) -> Optional[Dict]:
        """
        Obtiene el Fear & Greed Index actual.
        """
        cache_key = "fear_greed"
        now = datetime.now().timestamp()
        
        # Verificar cache
        if (cache_key in self._cache and 
            now - self._cache[cache_key]['timestamp'] < self._cache_ttl):
            return self._cache[cache_key]['data']
        
        try:
            # Llamar a la API
            response = requests.get(self.fear_greed_api, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if 'data' in data and len(data['data']) > 0:
                current_data = data['data'][0]
                
                result = {
                    'value': int(current_data['value']),
                    'classification': current_data['value_classification'],
                    'timestamp': current_data['timestamp'],
                    'time_until_update': current_data.get('time_until_update', 'N/A')
                }
                
                # Guardar en cache
                self._cache[cache_key] = {
                    'data': result,
                    'timestamp': now
                }
                
                logger.debug(f"📊 Fear & Greed Index: {result['value']} ({result['classification']})")
                return result
            
        except requests.RequestException as e:
            logger.warning(f"⚠️ Error obteniendo Fear & Greed Index: {e}")
        except Exception as e:
            logger.error(f"❌ Error procesando Fear & Greed data: {e}")
        
        return None
    
    def calculate_market_sentiment_score(self) -> Dict:
        """
        Calcula score compuesto de sentiment de mercado.
        """
        sentiment_data = {
            'fear_greed_index': None,
            'sentiment_score': 50,  # Neutral por defecto
            'sentiment_level': 'neutral',
            'market_condition': 'normal',
            'trading_adjustment': 1.0
        }
        
        # Obtener Fear & Greed Index
        fg_data = self.get_fear_greed_index()
        
        if fg_data:
            fg_value = fg_data['value']
            sentiment_data['fear_greed_index'] = fg_value
            
            # Clasificar sentiment
            if fg_value <= self.extreme_fear_threshold:
                sentiment_data['sentiment_level'] = 'extreme_fear'
                sentiment_data['market_condition'] = 'oversold'
                sentiment_data['trading_adjustment'] = 1.3  # Más agresivo en extreme fear
            elif fg_value <= self.fear_threshold:
                sentiment_data['sentiment_level'] = 'fear'
                sentiment_data['market_condition'] = 'bearish'
                sentiment_data['trading_adjustment'] = 1.1
            elif fg_value >= self.extreme_greed_threshold:
                sentiment_data['sentiment_level'] = 'extreme_greed'
                sentiment_data['market_condition'] = 'overbought'
                sentiment_data['trading_adjustment'] = 0.6  # Más conservador en extreme greed
            elif fg_value >= self.greed_threshold:
                sentiment_data['sentiment_level'] = 'greed'
                sentiment_data['market_condition'] = 'bullish'
                sentiment_data['trading_adjustment'] = 0.8
            else:
                sentiment_data['sentiment_level'] = 'neutral'
                sentiment_data['market_condition'] = 'normal'
                sentiment_data['trading_adjustment'] = 1.0
            
            sentiment_data['sentiment_score'] = fg_value
        
        return sentiment_data
    
    def get_contrarian_signals(self, sentiment_data: Dict) -> Dict:
        """
        Genera señales contrarian basadas en extremos de sentiment.
        """
        signals = {
            'contrarian_bullish': False,
            'contrarian_bearish': False,
            'strength': 0.0,
            'reasoning': ''
        }
        
        sentiment_level = sentiment_data.get('sentiment_level', 'neutral')
        fg_value = sentiment_data.get('fear_greed_index', 50)
        
        if sentiment_level == 'extreme_fear':
            # Extreme fear = oportunidad de compra contrarian
            signals['contrarian_bullish'] = True
            signals['strength'] = min((self.extreme_fear_threshold - fg_value) / 10, 1.0)
            signals['reasoning'] = f"Extreme fear ({fg_value}) suggests oversold market - contrarian buy opportunity"
            
        elif sentiment_level == 'extreme_greed':
            # Extreme greed = oportunidad de venta contrarian
            signals['contrarian_bearish'] = True
            signals['strength'] = min((fg_value - self.extreme_greed_threshold) / 10, 1.0)
            signals['reasoning'] = f"Extreme greed ({fg_value}) suggests overbought market - contrarian sell opportunity"
        
        return signals
    
    def adjust_position_sizing_by_sentiment(self, base_position_size: float, 
                                          sentiment_data: Dict) -> float:
        """
        Ajusta tamaño de posición basado en sentiment de mercado.
        """
        adjustment = sentiment_data.get('trading_adjustment', 1.0)
        sentiment_level = sentiment_data.get('sentiment_level', 'neutral')
        
        adjusted_size = base_position_size * adjustment
        
        # Límites de seguridad
        adjusted_size = max(min(adjusted_size, base_position_size * 2.0), base_position_size * 0.3)
        
        logger.debug(f"📏 Position sizing: {base_position_size:.4f} → {adjusted_size:.4f} ({sentiment_level})")
        
        return adjusted_size
    
    def should_reduce_exposure(self, sentiment_data: Dict) -> Tuple[bool, str]:
        """
        Determina si se debe reducir exposición basado en sentiment extremo.
        """
        sentiment_level = sentiment_data.get('sentiment_level', 'neutral')
        fg_value = sentiment_data.get('fear_greed_index', 50)
        
        if sentiment_level == 'extreme_greed':
            return True, f"Extreme greed ({fg_value}) - reducing exposure to avoid bubble burst"
        
        if sentiment_level == 'extreme_fear':
            # En extreme fear, podría ser oportunidad, pero también mayor riesgo
            if fg_value < 10:  # Fear extremo
                return True, f"Panic selling ({fg_value}) - reducing exposure until stabilization"
        
        return False, "Normal sentiment conditions"
    
    def get_market_timing_signals(self, sentiment_data: Dict, 
                                 current_positions: int) -> Dict:
        """
        Genera señales de timing de mercado basadas en sentiment.
        """
        timing_signals = {
            'should_enter_new_positions': True,
            'should_close_positions': False,
            'should_hedge': False,
            'market_timing_score': 0.0,
            'recommendations': []
        }
        
        sentiment_level = sentiment_data.get('sentiment_level', 'neutral')
        fg_value = sentiment_data.get('fear_greed_index', 50)
        
        if sentiment_level == 'extreme_fear':
            # Extreme fear: buena oportunidad para entrar, pero con cuidado
            timing_signals['should_enter_new_positions'] = True
            timing_signals['market_timing_score'] = 0.8
            timing_signals['recommendations'].append("Strong buy opportunity - market oversold")
            
        elif sentiment_level == 'fear':
            # Fear moderado: buenas condiciones para entrar
            timing_signals['should_enter_new_positions'] = True
            timing_signals['market_timing_score'] = 0.6
            timing_signals['recommendations'].append("Good buying conditions - market bearish but not extreme")
            
        elif sentiment_level == 'extreme_greed':
            # Extreme greed: reducir exposición, considerar cierre de posiciones
            timing_signals['should_enter_new_positions'] = False
            timing_signals['should_close_positions'] = current_positions > 3
            timing_signals['should_hedge'] = True
            timing_signals['market_timing_score'] = -0.8
            timing_signals['recommendations'].append("High risk environment - consider profit taking")
            
        elif sentiment_level == 'greed':
            # Greed moderado: ser más selectivo
            timing_signals['should_enter_new_positions'] = True
            timing_signals['market_timing_score'] = -0.3
            timing_signals['recommendations'].append("Market bullish but approaching overbought - be selective")
            
        else:
            # Neutral: condiciones normales
            timing_signals['market_timing_score'] = 0.0
            timing_signals['recommendations'].append("Normal market conditions - standard strategy")
        
        return timing_signals


class SentimentIntegrator:
    """
    Integra análisis de sentiment con señales de trading.
    """
    
    def __init__(self):
        self.analyzer = SentimentAnalyzer()
    
    def enhance_signals_with_sentiment(self, trading_signals: List[Dict]) -> List[Dict]:
        """
        Mejora señales de trading con análisis de sentiment.
        """
        # Obtener sentiment de mercado
        sentiment_data = self.analyzer.calculate_market_sentiment_score()
        contrarian_signals = self.analyzer.get_contrarian_signals(sentiment_data)
        
        enhanced_signals = []
        
        for signal in trading_signals:
            symbol = signal['symbol']
            base_signal = signal['signal']
            
            # Ajustar señal por sentiment
            sentiment_adjustment = self._calculate_sentiment_adjustment(
                base_signal, sentiment_data, contrarian_signals
            )
            
            enhanced_signal = base_signal * sentiment_adjustment
            
            # Agregar metadata de sentiment
            enhanced_signals.append({
                **signal,
                'signal': enhanced_signal,
                'base_signal': base_signal,
                'sentiment_adjustment': sentiment_adjustment,
                'sentiment_level': sentiment_data.get('sentiment_level'),
                'fear_greed_index': sentiment_data.get('fear_greed_index'),
                'market_condition': sentiment_data.get('market_condition')
            })
        
        logger.info(f"📊 Señales ajustadas por sentiment: FG={sentiment_data.get('fear_greed_index', 'N/A')} ({sentiment_data.get('sentiment_level', 'neutral')})")
        
        return enhanced_signals
    
    def _calculate_sentiment_adjustment(self, base_signal: float, 
                                      sentiment_data: Dict, 
                                      contrarian_signals: Dict) -> float:
        """
        Calcula ajuste de señal basado en sentiment.
        """
        adjustment = sentiment_data.get('trading_adjustment', 1.0)
        sentiment_level = sentiment_data.get('sentiment_level', 'neutral')
        
        # Aplicar lógica contrarian en extremos
        if contrarian_signals['contrarian_bullish'] and base_signal > 0:
            # Boost señales alcistas en extreme fear
            adjustment *= (1.0 + contrarian_signals['strength'] * 0.3)
            
        elif contrarian_signals['contrarian_bearish'] and base_signal < 0:
            # Boost señales bajistas en extreme greed
            adjustment *= (1.0 + contrarian_signals['strength'] * 0.3)
            
        elif sentiment_level == 'extreme_greed' and base_signal > 0:
            # Reducir señales alcistas en extreme greed
            adjustment *= 0.6
            
        elif sentiment_level == 'extreme_fear' and base_signal < 0:
            # Reducir señales bajistas en extreme fear
            adjustment *= 0.6
        
        # Límites de seguridad
        return max(min(adjustment, 2.0), 0.3)


# Instancia global
sentiment_integrator = SentimentIntegrator()