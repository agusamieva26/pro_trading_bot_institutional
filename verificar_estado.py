#!/usr/bin/env python3
import sys, os
sys.path.append('.')
from bot.execution import _client

try:
    client = _client()
    account = client.get_account()
    positions = list(client.get_all_positions())
    
    print(f'=== ESTADO ACTUAL POST-LIBERACIÓN ===')
    print(f'Cash: ${float(account.cash):.2f}')
    print(f'Equity: ${float(account.equity):.2f}')
    print(f'Posiciones totales: {len(positions)}')
    
    # Count cryptos
    crypto_symbols = ['BTCUSD', 'ETHUSD', 'SOLUSD', 'AVAXUSD', 'LINKUSD', 'DOGEUSD', 'DOTUSD', 
                     'LTCUSD', 'SHIBUSD', 'XRPUSD', 'UNIUSD', 'AAVEUSD', 'PEPEUSD', 'BCHUSD', 
                     'CRVUSD', 'GRTUSD']
    
    crypto_count = 0
    stock_count = 0
    total_value = 0
    
    for pos in positions:
        value = float(pos.market_value or 0)
        total_value += abs(value)
        
        if pos.symbol in crypto_symbols:
            crypto_count += 1
            print(f'CRYPTO RESTANTE: {pos.symbol} = ${value:.2f}')
        else:
            stock_count += 1
            
    print(f'\n=== RESUMEN ===')
    print(f'Cryptos restantes: {crypto_count}')
    print(f'Stocks restantes: {stock_count}')
    print(f'Valor total posiciones: ${total_value:.2f}')
    
    # Exposure calculation
    equity_val = float(account.equity)
    if equity_val > 0:
        exposure_ratio = total_value / equity_val
        print(f'Exposición actual: {exposure_ratio:.1%}')
        
        if exposure_ratio < 0.40:  # Bajo el límite configurado
            print('🎉 ¡CRISIS MODE RESUELTO! Exposición dentro del límite')
        else:
            print('⚠️ Exposición aún alta - puede necesitar más liberación')
    
except Exception as e:
    print(f'Error: {e}')