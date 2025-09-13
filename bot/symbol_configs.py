#!/usr/bin/env python3
"""
💎 CONFIGURACIONES PERSONALIZADAS POR SÍMBOLO
Sistema avanzado de take profit y stop loss individualizados por activo
- Configuraciones basadas en volatilidad histórica
- Ajustes automáticos por tipo de activo
- Optimización por comportamiento individual
"""

from typing import Dict, Optional, Tuple
from dataclasses import dataclass, asdict
import json
import os
from pathlib import Path
from .util import logger

@dataclass
class SymbolConfig:
    """Configuración personalizada por símbolo"""
    symbol: str
    take_profit_pct: float  # Porcentaje de take profit
    stop_loss_pct: float    # Porcentaje de stop loss
    volatility_tier: str    # ultra_low, low, medium, high, ultra_high
    asset_type: str         # crypto_major, crypto_alt, stock, etf
    trailing_stop: bool     # Si usar trailing stop
    partial_profit: bool    # Si usar profit-taking parcial
    min_hold_time: int      # Tiempo mínimo en segundos
    max_position_size: float # Tamaño máximo de posición
    notes: str = ""

class SymbolConfigManager:
    """
    🎯 Gestor de configuraciones personalizadas por símbolo
    """
    
    def __init__(self, config_file: str = "configs/symbol_configs.json"):
        self.config_file = config_file
        self.configs: Dict[str, SymbolConfig] = {}
        self.default_configs = self._create_default_configs()
        self.load_configs()
    
    def _create_default_configs(self) -> Dict[str, SymbolConfig]:
        """Crea configuraciones por defecto basadas en volatilidad y tipo"""
        configs = {}
        
        # 🪙 CRYPTOS MAYORES - Mayor liquidez, menos volatilidad
        configs["BTC/USD"] = SymbolConfig(
            symbol="BTC/USD",
            take_profit_pct=0.025,   # 2.5% - Más conservador
            stop_loss_pct=0.012,     # 1.2% - Más ajustado
            volatility_tier="low",
            asset_type="crypto_major",
            trailing_stop=True,
            partial_profit=True,
            min_hold_time=300,       # 5 min
            max_position_size=0.4,   # 40% max
            notes="Bitcoin - Crypto más estable"
        )
        
        configs["ETH/USD"] = SymbolConfig(
            symbol="ETH/USD", 
            take_profit_pct=0.03,    # 3.0% - Algo más agresivo
            stop_loss_pct=0.015,     # 1.5%
            volatility_tier="medium",
            asset_type="crypto_major",
            trailing_stop=True,
            partial_profit=True,
            min_hold_time=240,       # 4 min
            max_position_size=0.3,   # 30% max
            notes="Ethereum - Segunda crypto más estable"
        )
        
        # 🚀 CRYPTOS ALTERNATIVAS - Mayor volatilidad, más oportunidad
        configs["SOL/USD"] = SymbolConfig(
            symbol="SOL/USD",
            take_profit_pct=0.04,    # 4.0% - Más agresivo
            stop_loss_pct=0.02,      # 2.0%
            volatility_tier="medium",
            asset_type="crypto_alt",
            trailing_stop=True,
            partial_profit=False,    # All or nothing
            min_hold_time=180,       # 3 min
            max_position_size=0.2,   # 20% max
            notes="Solana - Alta volatilidad"
        )
        
        configs["AVAX/USD"] = SymbolConfig(
            symbol="AVAX/USD",
            take_profit_pct=0.045,   # 4.5%
            stop_loss_pct=0.025,     # 2.5%
            volatility_tier="high",
            asset_type="crypto_alt", 
            trailing_stop=False,     # Fixed levels
            partial_profit=False,
            min_hold_time=120,       # 2 min
            max_position_size=0.15,  # 15% max
            notes="Avalanche - Muy volátil"
        )
        
        configs["LINK/USD"] = SymbolConfig(
            symbol="LINK/USD",
            take_profit_pct=0.035,   # 3.5%
            stop_loss_pct=0.018,     # 1.8%
            volatility_tier="medium",
            asset_type="crypto_alt",
            trailing_stop=True,
            partial_profit=True,
            min_hold_time=200,       # 3.3 min
            max_position_size=0.18,  # 18% max
            notes="Chainlink - Volatilidad media"
        )
        
        # 🎲 MEMECOINS - Ultra alta volatilidad
        configs["DOGE/USD"] = SymbolConfig(
            symbol="DOGE/USD",
            take_profit_pct=0.08,    # 8.0% - Muy agresivo
            stop_loss_pct=0.04,      # 4.0%
            volatility_tier="ultra_high",
            asset_type="crypto_alt",
            trailing_stop=False,
            partial_profit=False,
            min_hold_time=60,        # 1 min - Scalping rápido
            max_position_size=0.08,  # 8% max - Riesgo controlado
            notes="Dogecoin - Memecoin ultra volátil"
        )
        
        configs["SHIB/USD"] = SymbolConfig(
            symbol="SHIB/USD", 
            take_profit_pct=0.12,    # 12% - Extremadamente agresivo
            stop_loss_pct=0.06,      # 6.0%
            volatility_tier="ultra_high",
            asset_type="crypto_alt",
            trailing_stop=False,
            partial_profit=False,
            min_hold_time=30,        # 30 seg - Ultra scalping
            max_position_size=0.05,  # 5% max - Muy arriesgado
            notes="Shiba Inu - Ultra memecoin"
        )
        
        configs["PEPE/USD"] = SymbolConfig(
            symbol="PEPE/USD",
            take_profit_pct=0.15,    # 15% - Máxima agresividad
            stop_loss_pct=0.08,      # 8.0%
            volatility_tier="ultra_high",
            asset_type="crypto_alt",
            trailing_stop=False,
            partial_profit=False,
            min_hold_time=30,        # 30 seg
            max_position_size=0.03,  # 3% max - Extremo cuidado
            notes="PEPE - Memecoin extrema"
        )
        
        # 💼 DeFi - Volatilidad alta pero con fundamentos
        configs["UNI/USD"] = SymbolConfig(
            symbol="UNI/USD",
            take_profit_pct=0.05,    # 5.0%
            stop_loss_pct=0.025,     # 2.5% 
            volatility_tier="high",
            asset_type="crypto_alt",
            trailing_stop=True,
            partial_profit=True,
            min_hold_time=180,       # 3 min
            max_position_size=0.12,  # 12% max
            notes="Uniswap - DeFi líder"
        )
        
        configs["AAVE/USD"] = SymbolConfig(
            symbol="AAVE/USD",
            take_profit_pct=0.055,   # 5.5%
            stop_loss_pct=0.03,      # 3.0%
            volatility_tier="high", 
            asset_type="crypto_alt",
            trailing_stop=True,
            partial_profit=False,
            min_hold_time=240,       # 4 min
            max_position_size=0.1,   # 10% max
            notes="AAVE - Lending protocol"
        )
        
        # 🌊 LAYER 1s - Volatilidad media-alta
        configs["DOT/USD"] = SymbolConfig(
            symbol="DOT/USD",
            take_profit_pct=0.04,    # 4.0%
            stop_loss_pct=0.022,     # 2.2%
            volatility_tier="medium",
            asset_type="crypto_alt",
            trailing_stop=True,
            partial_profit=True,
            min_hold_time=180,       # 3 min
            max_position_size=0.15,  # 15% max
            notes="Polkadot - Interoperabilidad"
        )
        
        # 💰 STABLECOINS/FIAT - Ultra baja volatilidad
        configs["XRP/USD"] = SymbolConfig(
            symbol="XRP/USD",
            take_profit_pct=0.025,   # 2.5%
            stop_loss_pct=0.015,     # 1.5%
            volatility_tier="low",
            asset_type="crypto_alt",
            trailing_stop=True,
            partial_profit=True,
            min_hold_time=300,       # 5 min
            max_position_size=0.2,   # 20% max
            notes="Ripple - Más estable"
        )
        
        # 🏛️ OLD SCHOOL CRYPTOS
        configs["LTC/USD"] = SymbolConfig(
            symbol="LTC/USD",
            take_profit_pct=0.03,    # 3.0%
            stop_loss_pct=0.018,     # 1.8%
            volatility_tier="low",
            asset_type="crypto_alt",
            trailing_stop=True,
            partial_profit=True,
            min_hold_time=300,       # 5 min
            max_position_size=0.18,  # 18% max
            notes="Litecoin - Crypto clásica"
        )
        
        configs["BCH/USD"] = SymbolConfig(
            symbol="BCH/USD",
            take_profit_pct=0.035,   # 3.5%
            stop_loss_pct=0.02,      # 2.0%
            volatility_tier="medium",
            asset_type="crypto_alt",
            trailing_stop=True,
            partial_profit=False,
            min_hold_time=240,       # 4 min
            max_position_size=0.15,  # 15% max
            notes="Bitcoin Cash - Fork de BTC"
        )
        
        # 🧪 EXPERIMENTAL/NUEVAS
        configs["CRV/USD"] = SymbolConfig(
            symbol="CRV/USD",
            take_profit_pct=0.06,    # 6.0%
            stop_loss_pct=0.035,     # 3.5%
            volatility_tier="high",
            asset_type="crypto_alt",
            trailing_stop=False,
            partial_profit=False,
            min_hold_time=120,       # 2 min
            max_position_size=0.08,  # 8% max
            notes="Curve - DeFi experimental"
        )
        
        configs["GRT/USD"] = SymbolConfig(
            symbol="GRT/USD",
            take_profit_pct=0.07,    # 7.0%
            stop_loss_pct=0.04,      # 4.0%
            volatility_tier="high",
            asset_type="crypto_alt",
            trailing_stop=False,
            partial_profit=False,
            min_hold_time=90,        # 1.5 min
            max_position_size=0.06,  # 6% max
            notes="The Graph - Indexing protocol"
        )
        
        return configs
    
    def get_config(self, symbol: str) -> SymbolConfig:
        """Obtiene configuración para un símbolo específico"""
        # Normalizar símbolo
        symbol = symbol.upper().replace("/", "/")
        
        if symbol in self.configs:
            return self.configs[symbol]
        elif symbol in self.default_configs:
            return self.default_configs[symbol]
        else:
            # Crear configuración por defecto para símbolo desconocido
            return self._create_fallback_config(symbol)
    
    def _create_fallback_config(self, symbol: str) -> SymbolConfig:
        """Crea configuración por defecto para símbolos no configurados"""
        logger.warning(f"⚠️ No hay configuración específica para {symbol}, usando valores por defecto")
        
        # Detectar tipo de activo
        if "USD" in symbol and "/" in symbol:
            asset_type = "crypto_alt"
        elif symbol in ["AAPL", "MSFT", "GOOGL", "TSLA", "AMZN"]:
            asset_type = "stock"
        else:
            asset_type = "unknown"
        
        return SymbolConfig(
            symbol=symbol,
            take_profit_pct=0.02,    # 2% conservador
            stop_loss_pct=0.01,      # 1% conservador  
            volatility_tier="medium",
            asset_type=asset_type,
            trailing_stop=True,
            partial_profit=True,
            min_hold_time=300,       # 5 min
            max_position_size=0.1,   # 10% max
            notes=f"Configuración automática para {symbol}"
        )
    
    def get_tp_sl_for_symbol(self, symbol: str) -> Tuple[float, float]:
        """Obtiene take profit y stop loss para un símbolo específico"""
        config = self.get_config(symbol)
        return config.take_profit_pct, config.stop_loss_pct
    
    def load_configs(self):
        """Carga configuraciones desde archivo JSON"""
        config_path = Path(self.config_file)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.configs = {}
                for symbol, config_data in data.items():
                    self.configs[symbol] = SymbolConfig(**config_data)
                    
                logger.info(f"✅ Cargadas {len(self.configs)} configuraciones personalizadas")
                
            except Exception as e:
                logger.error(f"❌ Error cargando configuraciones: {e}")
                self.configs = {}
        else:
            # Crear archivo con configuraciones por defecto
            self.save_configs()
            logger.info("📁 Creado archivo de configuraciones con valores por defecto")
    
    def save_configs(self):
        """Guarda configuraciones actuales a archivo JSON"""
        try:
            # Combinar configuraciones personalizadas con por defecto
            all_configs = {**self.default_configs, **self.configs}
            
            config_data = {}
            for symbol, config in all_configs.items():
                config_data[symbol] = asdict(config)
            
            config_path = Path(self.config_file)
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"💾 Guardadas {len(config_data)} configuraciones")
            
        except Exception as e:
            logger.error(f"❌ Error guardando configuraciones: {e}")
    
    def update_config(self, symbol: str, **kwargs):
        """Actualiza configuración para un símbolo"""
        current_config = self.get_config(symbol)
        
        # Actualizar campos especificados
        for field, value in kwargs.items():
            if hasattr(current_config, field):
                setattr(current_config, field, value)
        
        self.configs[symbol] = current_config
        self.save_configs()
        
        logger.info(f"🔄 Actualizada configuración para {symbol}")
    
    def list_all_configs(self) -> Dict[str, SymbolConfig]:
        """Lista todas las configuraciones disponibles"""
        return {**self.default_configs, **self.configs}
    
    def get_volatility_stats(self) -> Dict[str, int]:
        """Estadísticas de distribución de volatilidad"""
        all_configs = self.list_all_configs()
        volatility_counts = {}
        
        for config in all_configs.values():
            tier = config.volatility_tier
            volatility_counts[tier] = volatility_counts.get(tier, 0) + 1
            
        return volatility_counts

# Instancia global para usar en todo el sistema
symbol_config_manager = SymbolConfigManager()

def get_symbol_tp_sl(symbol: str) -> Tuple[float, float]:
    """Función de conveniencia para obtener TP/SL de un símbolo"""
    return symbol_config_manager.get_tp_sl_for_symbol(symbol)

def get_symbol_config(symbol: str) -> SymbolConfig:
    """Función de conveniencia para obtener configuración completa"""
    return symbol_config_manager.get_config(symbol)