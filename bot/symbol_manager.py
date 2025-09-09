"""
SymbolManager centralizado para normalización y gestión inteligente de símbolos.
Elimina duplicación de lógica y mejora consistencia en el manejo de símbolos.
"""

import re
from typing import List, Dict, Set, Optional, Tuple
from enum import Enum
from .util import logger


class AssetType(Enum):
    STOCK = "stock"
    CRYPTO = "crypto"
    ETF = "etf"
    FOREX = "forex"
    UNKNOWN = "unknown"


class SymbolManager:
    """
    Gestor centralizado de símbolos con normalización inteligente y categorización.
    """
    
    def __init__(self):
        # Mapeos de símbolos conocidos
        self.crypto_patterns = {
            r'^[A-Z]{2,5}/USD$',  # BTC/USD, ETH/USD, etc.
            r'^[A-Z]{2,5}USD$',   # BTCUSD, ETHUSD, etc.
        }
        
        self.stock_patterns = {
            r'^[A-Z]{1,5}$',      # AAPL, TSLA, etc.
        }
        
        self.etf_symbols = {
            'SPY', 'QQQ', 'IWM', 'VTI', 'VOO', 'VEA', 'VWO', 'AGG', 'BND',
            'GLD', 'SLV', 'TLT', 'EEM', 'FXI', 'EWJ', 'VGK', 'IEFA'
        }
        
        # Mapeo de normalizaciones comunes
        self.symbol_normalizations = {
            # Crypto normalizations
            'BTCUSD': 'BTC/USD',
            'ETHUSD': 'ETH/USD', 
            'SOLUSD': 'SOL/USD',
            'AVAXUSD': 'AVAX/USD',
            'LINKUSD': 'LINK/USD',
            'DOTUSD': 'DOT/USD',
            'LTCUSD': 'LTC/USD',
            'SHIBUDE': 'SHIB/USD',
            'DOGEUSD': 'DOGE/USD',
            # NEW CRYPTOS
            'XRPUSD': 'XRP/USD',
            'UNIUSD': 'UNI/USD',
            'AAVEUSD': 'AAVE/USD',
            'PEPEUSD': 'PEPE/USD',
            'BCHUSD': 'BCH/USD',
            'MKRUSD': 'MKR/USD',
            'CRVUSD': 'CRV/USD',
            'GRTUSD': 'GRT/USD',
        }
        
        # Cache para optimizar lookups
        self._type_cache = {}
        self._normalized_cache = {}
    
    def normalize_symbol(self, symbol: str) -> str:
        """
        Normaliza un símbolo a formato estándar.
        """
        if not symbol:
            return symbol
        
        symbol = symbol.upper().strip()
        
        # Verificar cache
        if symbol in self._normalized_cache:
            return self._normalized_cache[symbol]
        
        # Aplicar normalización directa si existe
        if symbol in self.symbol_normalizations:
            normalized = self.symbol_normalizations[symbol]
            self._normalized_cache[symbol] = normalized
            return normalized
        
        # Normalización automática
        normalized = self._auto_normalize(symbol)
        self._normalized_cache[symbol] = normalized
        
        return normalized
    
    def _auto_normalize(self, symbol: str) -> str:
        """
        Normalización automática basada en patrones.
        """
        # Si ya tiene formato crypto estándar, mantener
        if '/' in symbol and symbol.endswith('USD'):
            return symbol
        
        # Convertir cryptos a formato estándar
        if symbol.endswith('USD') and len(symbol) > 3:
            base = symbol[:-3]
            if len(base) >= 2 and base.isupper():
                return f"{base}/USD"
        
        # Para stocks y ETFs, mantener formato original
        return symbol
    
    def get_asset_type(self, symbol: str) -> AssetType:
        """
        Determina el tipo de activo del símbolo.
        """
        symbol = symbol.upper().strip()
        
        # Verificar cache
        if symbol in self._type_cache:
            return self._type_cache[symbol]
        
        asset_type = self._classify_asset(symbol)
        self._type_cache[symbol] = asset_type
        
        return asset_type
    
    def _classify_asset(self, symbol: str) -> AssetType:
        """
        Clasifica el tipo de activo basado en patrones.
        """
        # ETFs conocidos
        if symbol in self.etf_symbols:
            return AssetType.ETF
        
        # Cryptos
        if '/' in symbol and symbol.endswith('USD'):
            return AssetType.CRYPTO
        
        if symbol.endswith('USD') and len(symbol) > 3:
            base = symbol[:-3]
            if len(base) >= 2:
                return AssetType.CRYPTO
        
        # Stocks (formato simple)
        if re.match(r'^[A-Z]{1,5}$', symbol):
            return AssetType.STOCK
        
        return AssetType.UNKNOWN
    
    def is_crypto(self, symbol: str) -> bool:
        """
        Verifica si un símbolo es cryptocurrency.
        """
        return self.get_asset_type(symbol) == AssetType.CRYPTO
    
    def is_stock(self, symbol: str) -> bool:
        """
        Verifica si un símbolo es stock.
        """
        return self.get_asset_type(symbol) == AssetType.STOCK
    
    def is_etf(self, symbol: str) -> bool:
        """
        Verifica si un símbolo es ETF.
        """
        return self.get_asset_type(symbol) == AssetType.ETF
    
    def get_trading_symbol(self, symbol: str) -> str:
        """
        Obtiene el símbolo en formato apropiado para trading (sin barras).
        """
        normalized = self.normalize_symbol(symbol)
        return normalized.replace('/', '')
    
    def get_display_symbol(self, symbol: str) -> str:
        """
        Obtiene el símbolo en formato apropiado para display.
        """
        return self.normalize_symbol(symbol)
    
    def group_symbols_by_type(self, symbols: List[str]) -> Dict[AssetType, List[str]]:
        """
        Agrupa símbolos por tipo de activo.
        """
        groups = {asset_type: [] for asset_type in AssetType}
        
        for symbol in symbols:
            asset_type = self.get_asset_type(symbol)
            normalized = self.normalize_symbol(symbol)
            groups[asset_type].append(normalized)
        
        return groups
    
    def get_correlation_groups(self, symbols: List[str]) -> Dict[str, List[str]]:
        """
        Agrupa símbolos por correlación esperada para diversificación.
        """
        groups = {
            'crypto_major': [],
            'crypto_alt': [],
            'tech_stocks': [],
            'etf_broad': [],
            'etf_sector': [],
            'other_stocks': []
        }
        
        # Definir agrupaciones
        crypto_major = {'BTC/USD', 'ETH/USD'}
        crypto_alt = {'SOL/USD', 'AVAX/USD', 'LINK/USD', 'DOT/USD', 'LTC/USD', 'DOGE/USD', 'SHIB/USD'}
        tech_stocks = {'AAPL', 'AMZN', 'TSLA', 'NVDA', 'GOOGL', 'MSFT', 'META', 'AMD', 'NFLX'}
        etf_broad = {'SPY', 'QQQ', 'VTI', 'VOO'}
        
        for symbol in symbols:
            normalized = self.normalize_symbol(symbol)
            
            if normalized in crypto_major:
                groups['crypto_major'].append(normalized)
            elif normalized in crypto_alt:
                groups['crypto_alt'].append(normalized)
            elif normalized in tech_stocks:
                groups['tech_stocks'].append(normalized)
            elif normalized in etf_broad:
                groups['etf_broad'].append(normalized)
            elif self.is_etf(normalized):
                groups['etf_sector'].append(normalized)
            else:
                groups['other_stocks'].append(normalized)
        
        # Filtrar grupos vacíos
        return {k: v for k, v in groups.items() if v}
    
    def validate_symbols(self, symbols: List[str]) -> Tuple[List[str], List[str]]:
        """
        Valida lista de símbolos, retorna (válidos, inválidos).
        """
        valid = []
        invalid = []
        
        for symbol in symbols:
            try:
                normalized = self.normalize_symbol(symbol)
                asset_type = self.get_asset_type(normalized)
                
                if asset_type != AssetType.UNKNOWN and normalized:
                    valid.append(normalized)
                else:
                    invalid.append(symbol)
            except Exception:
                invalid.append(symbol)
        
        if invalid:
            logger.warning(f"⚠️ Símbolos inválidos ignorados: {invalid}")
        
        logger.info(f"✅ Símbolos validados: {len(valid)} válidos, {len(invalid)} inválidos")
        
        return valid, invalid
    
    def get_symbol_info(self, symbol: str) -> Dict:
        """
        Obtiene información completa de un símbolo.
        """
        normalized = self.normalize_symbol(symbol)
        asset_type = self.get_asset_type(normalized)
        trading_symbol = self.get_trading_symbol(symbol)
        
        return {
            'original': symbol,
            'normalized': normalized,
            'trading_symbol': trading_symbol,
            'display_symbol': normalized,
            'asset_type': asset_type.value,
            'is_crypto': self.is_crypto(normalized),
            'is_stock': self.is_stock(normalized),
            'is_etf': self.is_etf(normalized)
        }
    
    def clear_cache(self):
        """
        Limpia el cache interno.
        """
        self._type_cache.clear()
        self._normalized_cache.clear()


# Instancia global del manager
symbol_manager = SymbolManager()