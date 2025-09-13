#!/usr/bin/env python3
"""
🧪 RISK MANAGEMENT INTEGRATION TEST SCRIPT
Test the dynamic risk management system with kill switch bypass enabled.
"""

import os
import sys
import logging
from pathlib import Path

# Set test mode environment variables
os.environ["RISK_MANAGEMENT_TEST_MODE"] = "true"
os.environ["DISABLE_KILL_SWITCH"] = "true"
os.environ["MODE"] = "paper"

# Add bot directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Set up logging to see risk management activity
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def test_risk_integration():
    """Test the integrated risk management system"""
    print("🧪 STARTING RISK MANAGEMENT INTEGRATION TEST")
    print("=" * 60)
    
    try:
        # Import after setting environment variables
        from bot.integrated_risk_system import get_integrated_risk_assessment
        from bot.config import settings
        
        print(f"✅ Test Mode Status:")
        print(f"   - Risk Management Test Mode: {settings.risk_management_test_mode}")
        print(f"   - Disable Kill Switch: {settings.disable_kill_switch}")
        print(f"   - Trading Mode: {settings.mode}")
        print()
        
        # Test with various scenarios
        test_scenarios = [
            {"symbol": "BTC/USD", "signal": 0.15, "equity": 20000, "price": 65000},
            {"symbol": "ETH/USD", "signal": -0.12, "equity": 20000, "price": 2500},
            {"symbol": "AAPL", "signal": 0.08, "equity": 20000, "price": 225},
            {"symbol": "SPY", "signal": 0.25, "equity": 20000, "price": 550},
        ]
        
        print("🧪 TESTING RISK ASSESSMENT SCENARIOS:")
        print("=" * 60)
        
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"\n📊 TEST SCENARIO {i}: {scenario['symbol']}")
            print(f"   Signal: {scenario['signal']:.3f} | Equity: ${scenario['equity']:,} | Price: ${scenario['price']:.2f}")
            
            try:
                # This should trigger the comprehensive logging we added
                risk_assessment = get_integrated_risk_assessment(
                    symbol=scenario["symbol"],
                    signal_strength=scenario["signal"],
                    equity=scenario["equity"],
                    price=scenario["price"],
                    atr=scenario["price"] * 0.02  # 2% ATR
                )
                
                print(f"   ✅ Assessment Complete:")
                print(f"      - Allow Trade: {risk_assessment['allow_trade']}")
                print(f"      - Position Shares: {risk_assessment['position_size_shares']:.2f}")
                print(f"      - Max Position USD: ${risk_assessment['max_position_usd']:.0f}")
                print(f"      - Risk Multiplier: {risk_assessment['risk_multiplier']:.2f}x")
                print(f"      - Emergency Mode: {risk_assessment['emergency_mode']}")
                print(f"      - Volatility Regime: {risk_assessment['volatility_regime']}")
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
                import traceback
                traceback.print_exc()
        
        print("\n🧪 INTEGRATION TEST COMPLETE")
        print("=" * 60)
        print("✅ If you see comprehensive logs above showing risk assessment activity,")
        print("   the integration is working correctly!")
        
    except Exception as e:
        print(f"❌ Critical Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = test_risk_integration()
    sys.exit(0 if success else 1)