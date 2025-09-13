#!/usr/bin/env python3
"""
🔗 BOT CONNECTOR - Real-time data interface
Connects desktop app with trading bot backend
"""
import json
import sqlite3
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class BotConnector:
    """Handles communication between desktop app and trading bot"""
    
    def __init__(self):
        self.data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        os.makedirs(self.data_path, exist_ok=True)
        
    def get_portfolio_data(self) -> Dict[str, Any]:
        """Get current portfolio data from bot"""
        try:
            # Try to get data from bot's state file
            state_file = os.path.join(os.path.dirname(os.path.dirname(self.data_path)), "data", "bot_state.json")
            
            if os.path.exists(state_file):
                with open(state_file, 'r') as f:
                    data = json.load(f)
                return data
            else:
                # Return mock data if no real data available
                return {
                    "equity": 18089.01,
                    "daily_pnl": -23.58,
                    "cash": 18065.74,
                    "positions": [
                        {
                            "symbol": "BTC/USD",
                            "qty": 0.000186,
                            "entry_price": 111964.05,
                            "current_price": 111800.00,
                            "unrealized_pnl": -30.52,
                            "unrealized_pnl_pct": -0.27
                        },
                        {
                            "symbol": "ETH/USD", 
                            "qty": 0.002,
                            "entry_price": 4309.54,
                            "current_price": 4280.00,
                            "unrealized_pnl": -5.91,
                            "unrealized_pnl_pct": -0.69
                        }
                    ],
                    "last_update": datetime.now().isoformat()
                }
                
        except Exception as e:
            print(f"❌ Portfolio data error: {e}")
            return {"error": str(e)}
    
    def get_bot_status(self) -> str:
        """Check if trading bot is running"""
        try:
            # Check if bot process is running
            import psutil
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info['cmdline']
                    if cmdline and 'bot.main' in ' '.join(cmdline):
                        return "RUNNING"
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
            return "STOPPED"
            
        except ImportError:
            # psutil not available, check differently
            return "UNKNOWN"
        except Exception as e:
            print(f"❌ Status check error: {e}")
            return "ERROR"
    
    def get_recent_trades(self, limit: int = 10) -> List[Dict]:
        """Get recent trade history"""
        try:
            trades_file = os.path.join(os.path.dirname(os.path.dirname(self.data_path)), "data", "trades.csv")
            
            if os.path.exists(trades_file):
                import pandas as pd
                df = pd.read_csv(trades_file)
                recent = df.tail(limit).to_dict('records')
                return recent
            else:
                # Return mock trades
                return [
                    {
                        "timestamp": datetime.now().isoformat(),
                        "symbol": "BTC/USD",
                        "side": "BUY",
                        "qty": 0.0001,
                        "price": 111500.00,
                        "pnl": 0
                    },
                    {
                        "timestamp": (datetime.now()).isoformat(),
                        "symbol": "ETH/USD", 
                        "side": "SELL",
                        "qty": 0.001,
                        "price": 4250.00,
                        "pnl": 15.30
                    }
                ]
                
        except Exception as e:
            print(f"❌ Trades data error: {e}")
            return []
    
    def save_risk_settings(self, settings: Dict[str, float]) -> bool:
        """Save risk management settings"""
        try:
            config_file = os.path.join(self.data_path, "risk_config.json")
            settings["updated_at"] = datetime.now().isoformat()
            
            with open(config_file, 'w') as f:
                json.dump(settings, f, indent=2)
                
            return True
            
        except Exception as e:
            print(f"❌ Save settings error: {e}")
            return False
    
    def load_risk_settings(self) -> Dict[str, float]:
        """Load risk management settings"""
        try:
            config_file = os.path.join(self.data_path, "risk_config.json")
            
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    return json.load(f)
            else:
                # Default settings
                return {
                    "risk_per_trade": 0.5,
                    "take_profit": 1.5,
                    "stop_loss": 0.7,
                    "max_positions": 5
                }
                
        except Exception as e:
            print(f"❌ Load settings error: {e}")
            return {}