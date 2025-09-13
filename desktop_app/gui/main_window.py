#!/usr/bin/env python3
"""
🖥️ MAIN WINDOW - AGUS Trading Bot Desktop GUI
Professional trading interface with real-time monitoring and control
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import json
import asyncio
from datetime import datetime
import sys
import os
import subprocess
import psutil

# Bot imports
try:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from bot.config import settings
    from chat_with_ai import AITradingChat
    BOT_AVAILABLE = True
except ImportError:
    BOT_AVAILABLE = False

class TradingBotGUI:
    def __init__(self, root):
        self.root = root
        self.setup_main_window()
        self.create_widgets()
        self.bot_status = "STOPPED"
        self.portfolio_data = {}
        self.ai_chat = None
        
        # Initialize AI chat if available
        if BOT_AVAILABLE:
            try:
                self.ai_chat = AITradingChat()
            except Exception as e:
                print(f"⚠️ AI Chat unavailable: {e}")
        
        # Start monitoring thread
        self.start_monitoring()

    def setup_main_window(self):
        """Configure main window properties"""
        self.root.title("🚀 AGUS TRADING BOT - Professional Desktop Interface")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 800)
        
        # Modern styling
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure colors
        self.root.configure(bg='#1e1e1e')
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'), foreground='#00ff88')
        style.configure('Status.TLabel', font=('Arial', 12, 'bold'))
        style.configure('Modern.TButton', font=('Arial', 10, 'bold'))

    def create_widgets(self):
        """Create and arrange GUI components"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="🚀 AGUS INSTITUTIONAL TRADING SYSTEM", 
                               style='Title.TLabel')
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Left panel - Controls
        self.create_control_panel(main_frame)
        
        # Right panel - Monitoring
        self.create_monitoring_panel(main_frame)
        
        # Bottom panel - AGUS Chat
        self.create_chat_panel(main_frame)

    def create_control_panel(self, parent):
        """Create bot control panel"""
        control_frame = ttk.LabelFrame(parent, text="🎛️ BOT CONTROL", padding="10")
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # Bot status
        self.status_var = tk.StringVar(value="🔴 STOPPED")
        status_label = ttk.Label(control_frame, text="Status:")
        status_label.grid(row=0, column=0, sticky=tk.W, pady=5)
        
        self.status_display = ttk.Label(control_frame, textvariable=self.status_var, 
                                       style='Status.TLabel', foreground='red')
        self.status_display.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        # Control buttons
        self.start_btn = ttk.Button(control_frame, text="🚀 START BOT", 
                                   command=self.start_bot, style='Modern.TButton')
        self.start_btn.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.stop_btn = ttk.Button(control_frame, text="🛑 STOP BOT", 
                                  command=self.stop_bot, style='Modern.TButton')
        self.stop_btn.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        self.stop_btn.configure(state='disabled')
        
        # Separator
        separator = ttk.Separator(control_frame, orient='horizontal')
        separator.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        
        # Risk settings
        risk_label = ttk.Label(control_frame, text="⚠️ RISK SETTINGS")
        risk_label.grid(row=4, column=0, columnspan=2, pady=(10, 5))
        
        # Risk per trade
        ttk.Label(control_frame, text="Risk per Trade:").grid(row=5, column=0, sticky=tk.W)
        self.risk_var = tk.DoubleVar(value=0.5)
        risk_spin = ttk.Spinbox(control_frame, from_=0.1, to=2.0, increment=0.1, 
                               textvariable=self.risk_var, width=10)
        risk_spin.grid(row=5, column=1, sticky=tk.W, padx=(10, 0))
        
        # Take profit
        ttk.Label(control_frame, text="Take Profit:").grid(row=6, column=0, sticky=tk.W)
        self.tp_var = tk.DoubleVar(value=1.5)
        tp_spin = ttk.Spinbox(control_frame, from_=0.5, to=10.0, increment=0.5, 
                             textvariable=self.tp_var, width=10)
        tp_spin.grid(row=6, column=1, sticky=tk.W, padx=(10, 0))
        
        # Stop loss
        ttk.Label(control_frame, text="Stop Loss:").grid(row=7, column=0, sticky=tk.W)
        self.sl_var = tk.DoubleVar(value=0.7)
        sl_spin = ttk.Spinbox(control_frame, from_=0.3, to=5.0, increment=0.1, 
                             textvariable=self.sl_var, width=10)
        sl_spin.grid(row=7, column=1, sticky=tk.W, padx=(10, 0))
        
        # Apply settings button
        apply_btn = ttk.Button(control_frame, text="✅ APPLY SETTINGS", 
                              command=self.apply_settings)
        apply_btn.grid(row=8, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)

    def create_monitoring_panel(self, parent):
        """Create real-time monitoring panel"""
        monitor_frame = ttk.LabelFrame(parent, text="📊 PORTFOLIO MONITOR", padding="10")
        monitor_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        monitor_frame.columnconfigure(0, weight=1)
        monitor_frame.rowconfigure(1, weight=1)
        
        # Portfolio summary
        summary_frame = ttk.Frame(monitor_frame)
        summary_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        summary_frame.columnconfigure(0, weight=1)
        summary_frame.columnconfigure(1, weight=1)
        summary_frame.columnconfigure(2, weight=1)
        
        # Equity
        self.equity_var = tk.StringVar(value="$0.00")
        equity_label = ttk.Label(summary_frame, text="💰 EQUITY:")
        equity_label.grid(row=0, column=0, pady=5)
        equity_value = ttk.Label(summary_frame, textvariable=self.equity_var, 
                                font=('Arial', 12, 'bold'), foreground='green')
        equity_value.grid(row=1, column=0, pady=5)
        
        # Daily P&L
        self.pnl_var = tk.StringVar(value="$0.00")
        pnl_label = ttk.Label(summary_frame, text="📈 DAILY P&L:")
        pnl_label.grid(row=0, column=1, pady=5)
        self.pnl_value = ttk.Label(summary_frame, textvariable=self.pnl_var, 
                                  font=('Arial', 12, 'bold'))
        self.pnl_value.grid(row=1, column=1, pady=5)
        
        # Active positions
        self.positions_var = tk.StringVar(value="0")
        pos_label = ttk.Label(summary_frame, text="🎯 POSITIONS:")
        pos_label.grid(row=0, column=2, pady=5)
        pos_value = ttk.Label(summary_frame, textvariable=self.positions_var, 
                             font=('Arial', 12, 'bold'), foreground='blue')
        pos_value.grid(row=1, column=2, pady=5)
        
        # Positions tree
        tree_frame = ttk.Frame(monitor_frame)
        tree_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        
        # Treeview for positions
        columns = ('Symbol', 'Size', 'Entry', 'Current', 'P&L', 'P&L%')
        self.positions_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=15)
        
        # Configure columns
        for col in columns:
            self.positions_tree.heading(col, text=col)
            self.positions_tree.column(col, width=100, anchor=tk.CENTER)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.positions_tree.yview)
        self.positions_tree.configure(yscrollcommand=scrollbar.set)
        
        self.positions_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

    def create_chat_panel(self, parent):
        """Create AGUS chat interface"""
        chat_frame = ttk.LabelFrame(parent, text="🤖 AGUS AI ASSISTANT", padding="10")
        chat_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        chat_frame.columnconfigure(0, weight=1)
        chat_frame.rowconfigure(0, weight=1)
        
        # Chat display
        self.chat_display = scrolledtext.ScrolledText(chat_frame, height=8, state='disabled',
                                                     bg='#2d2d2d', fg='white', font=('Consolas', 10))
        self.chat_display.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Input frame
        input_frame = ttk.Frame(chat_frame)
        input_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        input_frame.columnconfigure(0, weight=1)
        
        # Chat input
        self.chat_input = ttk.Entry(input_frame, font=('Arial', 11))
        self.chat_input.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        self.chat_input.bind('<Return>', self.send_chat_message)
        
        # Send button
        send_btn = ttk.Button(input_frame, text="💬 SEND", command=self.send_chat_message)
        send_btn.grid(row=0, column=1)
        
        # Initial message
        self.add_chat_message("AGUS", "🚀 AGUS AI Assistant ready! Ask me anything about your trading bot.")

    def start_bot(self):
        """Start the trading bot"""
        try:
            self.bot_status = "STARTING"
            self.update_status("🟡 STARTING...", "orange")
            self.start_btn.configure(state='disabled')
            
            # Start bot in separate thread
            thread = threading.Thread(target=self.run_bot, daemon=True)
            thread.start()
            
            self.add_chat_message("SYSTEM", "🚀 Trading bot startup initiated...")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start bot: {e}")
            self.update_status("🔴 ERROR", "red")
            self.start_btn.configure(state='normal')

    def run_bot(self):
        """Run the trading bot process"""
        try:
            # Start bot process
            cmd = [sys.executable, "-m", "bot.main"]
            cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            self.bot_process = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, 
                                              stderr=subprocess.PIPE, text=True)
            
            # Update status
            self.root.after(0, lambda: self.update_status("🟢 RUNNING", "green"))
            self.root.after(0, lambda: self.stop_btn.configure(state='normal'))
            self.root.after(0, lambda: self.add_chat_message("SYSTEM", "✅ Trading bot is now ACTIVE!"))
            
            self.bot_status = "RUNNING"
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Bot startup failed: {e}"))
            self.root.after(0, lambda: self.update_status("🔴 ERROR", "red"))
            self.root.after(0, lambda: self.start_btn.configure(state='normal'))

    def stop_bot(self):
        """Stop the trading bot"""
        try:
            if hasattr(self, 'bot_process'):
                self.bot_process.terminate()
                self.bot_process.wait(timeout=10)
            
            self.bot_status = "STOPPED"
            self.update_status("🔴 STOPPED", "red")
            self.start_btn.configure(state='normal')
            self.stop_btn.configure(state='disabled')
            
            self.add_chat_message("SYSTEM", "🛑 Trading bot has been stopped.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to stop bot: {e}")

    def apply_settings(self):
        """Apply risk management settings"""
        try:
            settings_data = {
                "risk_per_trade": self.risk_var.get(),
                "take_profit": self.tp_var.get(), 
                "stop_loss": self.sl_var.get(),
                "updated": datetime.now().isoformat()
            }
            
            # Save settings
            config_path = os.path.join(os.path.dirname(__file__), "..", "config", "risk_settings.json")
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            
            with open(config_path, 'w') as f:
                json.dump(settings_data, f, indent=2)
            
            self.add_chat_message("SYSTEM", f"✅ Risk settings updated: Risk={self.risk_var.get()}%, TP={self.tp_var.get()}%, SL={self.sl_var.get()}%")
            messagebox.showinfo("Success", "Risk settings applied successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply settings: {e}")

    def send_chat_message(self, event=None):
        """Send message to AGUS AI"""
        message = self.chat_input.get().strip()
        if not message:
            return
            
        self.chat_input.delete(0, tk.END)
        self.add_chat_message("USER", message)
        
        # Process with AGUS in separate thread
        thread = threading.Thread(target=self.process_agus_message, args=(message,), daemon=True)
        thread.start()

    def process_agus_message(self, message):
        """Process message with AGUS AI"""
        try:
            if self.ai_chat:
                # Run async function in thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                response = loop.run_until_complete(self.ai_chat.ask_ai(message))
                loop.close()
                
                self.root.after(0, lambda: self.add_chat_message("AGUS", response))
            else:
                self.root.after(0, lambda: self.add_chat_message("AGUS", "🔧 AGUS AI currently unavailable. Bot monitoring active."))
                
        except Exception as e:
            error_msg = f"❌ AGUS Error: {str(e)}"
            self.root.after(0, lambda: self.add_chat_message("AGUS", error_msg))

    def add_chat_message(self, sender, message):
        """Add message to chat display"""
        self.chat_display.configure(state='normal')
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] {sender}: {message}\n\n"
        
        self.chat_display.insert(tk.END, formatted_msg)
        self.chat_display.configure(state='disabled')
        self.chat_display.see(tk.END)

    def update_status(self, status_text, color):
        """Update bot status display"""
        self.status_var.set(status_text)
        self.status_display.configure(foreground=color)

    def start_monitoring(self):
        """Start monitoring thread for real-time data"""
        def monitor():
            while True:
                try:
                    if self.bot_status == "RUNNING":
                        self.update_portfolio_data()
                    threading.Event().wait(5)  # Update every 5 seconds
                except Exception as e:
                    print(f"Monitor error: {e}")
        
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()

    def update_portfolio_data(self):
        """Update portfolio display with real-time data"""
        try:
            # Mock data for now - in real implementation, fetch from bot
            equity = 18089.01
            daily_pnl = -23.58
            positions = [
                ("BTC/USD", "0.0001", "$111,964", "$111,800", "-$16.4", "-0.15%"),
                ("ETH/USD", "0.002", "$4,309", "$4,280", "-$5.8", "-0.67%"),
            ]
            
            # Update GUI elements in main thread
            self.root.after(0, lambda: self.equity_var.set(f"${equity:,.2f}"))
            self.root.after(0, lambda: self.pnl_var.set(f"${daily_pnl:+.2f}"))
            self.root.after(0, lambda: self.positions_var.set(str(len(positions))))
            
            # Update P&L color
            pnl_color = "green" if daily_pnl >= 0 else "red"
            self.root.after(0, lambda: self.pnl_value.configure(foreground=pnl_color))
            
            # Update positions tree
            self.root.after(0, lambda: self.update_positions_tree(positions))
            
        except Exception as e:
            print(f"Portfolio update error: {e}")

    def update_positions_tree(self, positions):
        """Update the positions treeview"""
        # Clear existing items
        for item in self.positions_tree.get_children():
            self.positions_tree.delete(item)
        
        # Add new items
        for pos in positions:
            self.positions_tree.insert('', tk.END, values=pos)