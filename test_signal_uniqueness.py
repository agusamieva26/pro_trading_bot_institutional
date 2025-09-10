#!/usr/bin/env python3

import pandas as pd
import sys
import numpy as np
sys.path.append('/home/runner/workspace')

from bot.data import fetch_bars
from bot.features import make_features
from bot.strategy import hybrid_signal, load_trading_model

print('🧪 Testing signal uniqueness after fixes...')
print('=' * 50)

# Test symbols that previously showed identical values
test_symbols = ['ETH/USD', 'SOL/USD', 'AVAX/USD', 'DOT/USD', 'XRP/USD']

# Load the model
clf = load_trading_model()

results = {}
for symbol in test_symbols:
    try:
        # Get data and calculate features with SYMBOL PARAMETER (key fix)
        df = fetch_bars(symbol, min_bars=100)
        if df.empty:
            print(f'❌ {symbol}: No data available')
            continue
        
        # Calculate features with symbol parameter - THIS IS THE FIX!
        features = make_features(df, symbol=symbol)
        latest = features.iloc[-1]
        
        # Get the signal
        signal = hybrid_signal(latest, clf, symbol=symbol)
        
        results[symbol] = {
            'signal': signal,
            'price': float(latest['close']),
            'ema_12': float(latest['ema_12']),
            'rsi_14': float(latest['rsi_14']),
            'crypto_base': symbol.split('/')[0] if '/' in symbol else symbol.replace('USD', '')
        }
        
        print(f'✅ {symbol:12} | Signal: {signal:+.4f} | Price: ${float(latest["close"]):8.2f} | EMA: {float(latest["ema_12"]):8.2f} | RSI: {float(latest["rsi_14"]):5.1f}')
        
    except Exception as e:
        print(f'❌ {symbol}: Error - {e}')

print('\n🔍 Analysis:')
print('=' * 50)

# Check for identical values
signals = [results[s]['signal'] for s in results.keys()]
prices = [results[s]['price'] for s in results.keys()]
emas = [results[s]['ema_12'] for s in results.keys()]
rsis = [results[s]['rsi_14'] for s in results.keys()]

print(f'Signal uniqueness: {len(set([round(s, 4) for s in signals]))}/{len(signals)} unique values')
print(f'EMA uniqueness: {len(set([round(e, 2) for e in emas]))}/{len(emas)} unique values') 
print(f'RSI uniqueness: {len(set([round(r, 1) for r in rsis]))}/{len(rsis)} unique values')

# Check for identical signals (rounded to 4 decimals)
rounded_signals = [round(s, 4) for s in signals]
duplicates = [s for s in set(rounded_signals) if rounded_signals.count(s) > 1]
if duplicates:
    print(f'⚠️  Duplicate signals found: {duplicates}')
else:
    print('✅ All signals are unique!')

print(f'\nSignal range: {min(signals):+.4f} to {max(signals):+.4f}')
print(f'Signal std dev: {np.std(signals):.4f} (higher is better for diversity)')

# Print symbol-specific parameters being used
print('\n🎯 Symbol-specific parameters now in use:')
ema_periods = {
    'BTC': (12, 26), 'ETH': (10, 24), 'SOL': (14, 28), 'AVAX': (11, 25),
    'DOT': (12, 25), 'XRP': (11, 23)
}

for symbol, data in results.items():
    crypto_base = data['crypto_base']
    periods = ema_periods.get(crypto_base, (12, 26))
    print(f'{symbol:12}: EMA periods {periods[0]},{periods[1]} | Current EMA12: {data["ema_12"]:8.2f}')

print('\n✅ TEST COMPLETED - Check if signals are now unique per symbol!')