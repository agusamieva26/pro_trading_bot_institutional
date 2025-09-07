from bot.config import settings
from alpaca.trading.client import TradingClient

client = TradingClient(
    api_key=settings.alpaca_api_key,
    secret_key=settings.alpaca_secret_key,
    paper=(settings.mode == 'paper')
)

print('🔍 DIAGNÓSTICO DE POSICIONES:')
print('=' * 40)

try:
    positions = client.get_all_positions()
    print(f'📊 Total posiciones encontradas: {len(positions)}')
    
    if positions:
        for pos in positions:
            print(f'• Símbolo: {pos.symbol}')
            print(f'  Cantidad: {pos.qty}') 
            print(f'  Valor: ${float(pos.market_value):.2f}')
            print(f'  P&L: ${float(pos.unrealized_pl):.2f}')
            print()
    else:
        print('❌ No hay posiciones abiertas')
        
    account = client.get_account()
    equity = float(account.equity)
    print(f'💰 Equity: ${equity:.2f}')
    
    if positions:
        gross_value = sum(abs(float(pos.market_value)) for pos in positions)
        exposure = gross_value / equity
        print(f'📈 Exposición calculada: {exposure:.2f}x')
    
except Exception as e:
    print(f'❌ Error: {e}')
