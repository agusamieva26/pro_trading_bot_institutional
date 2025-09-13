#!/usr/bin/env python3
"""
🚀 AGUS TRADING BOT - DESKTOP LAUNCHER
Simple launcher for the desktop application
"""
import os
import sys
import subprocess
import tkinter as tk
from tkinter import messagebox

def check_dependencies():
    """Check if required dependencies are available"""
    try:
        import tkinter
        return True
    except ImportError:
        return False

def launch_app():
    """Launch the desktop application"""
    try:
        if not check_dependencies():
            messagebox.showerror("Error", "tkinter not available. Please install Python with tkinter support.")
            return False
        
        # Get the directory of this script
        app_dir = os.path.dirname(os.path.abspath(__file__))
        main_script = os.path.join(app_dir, "main.py")
        
        # Launch the main application
        if os.path.exists(main_script):
            subprocess.run([sys.executable, main_script])
            return True
        else:
            messagebox.showerror("Error", f"Main application file not found: {main_script}")
            return False
            
    except Exception as e:
        messagebox.showerror("Launch Error", f"Failed to launch application:\n{str(e)}")
        return False

if __name__ == "__main__":
    # Simple splash screen
    root = tk.Tk()
    root.title("AGUS Trading Bot")
    root.geometry("400x200")
    root.resizable(False, False)
    
    # Center the window
    root.eval('tk::PlaceWindow . center')
    
    # Splash content
    splash_frame = tk.Frame(root, bg='#1e1e1e')
    splash_frame.pack(fill='both', expand=True)
    
    title_label = tk.Label(splash_frame, text="🚀 AGUS TRADING BOT", 
                          font=('Arial', 18, 'bold'), fg='#00ff88', bg='#1e1e1e')
    title_label.pack(pady=30)
    
    subtitle_label = tk.Label(splash_frame, text="Institutional-Grade Desktop Interface", 
                             font=('Arial', 12), fg='white', bg='#1e1e1e')
    subtitle_label.pack(pady=10)
    
    launch_button = tk.Button(splash_frame, text="🖥️ LAUNCH APPLICATION", 
                             font=('Arial', 12, 'bold'), 
                             command=lambda: [root.destroy(), launch_app()],
                             bg='#00ff88', fg='black', padx=20, pady=10)
    launch_button.pack(pady=30)
    
    # Show splash
    root.mainloop()