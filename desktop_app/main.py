#!/usr/bin/env python3
"""
🖥️ AGUS TRADING BOT - DESKTOP APPLICATION
Professional desktop interface for institutional-grade trading bot control
"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import json
import sys
import os
from datetime import datetime

# Add parent directory to path for bot imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gui.main_window import TradingBotGUI

def main():
    """Launch the AGUS Trading Bot Desktop Application"""
    try:
        # Create main window
        root = tk.Tk()
        app = TradingBotGUI(root)
        
        # Start the application
        root.mainloop()
        
    except Exception as e:
        messagebox.showerror("Error", f"Failed to start application: {e}")
        print(f"❌ Application error: {e}")

if __name__ == "__main__":
    main()