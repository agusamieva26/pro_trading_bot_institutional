#!/usr/bin/env python3
"""
💬 MODERN CHAT INTERFACE - Like Replit Assistant
Interactive chat interface with code execution and modern styling
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import asyncio
import json
import sys
import os
import subprocess
from datetime import datetime
import re

# Add parent directory for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from chat_with_ai import AITradingChat
    CHAT_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ AITradingChat unavailable: {e}")
    CHAT_AVAILABLE = False
    AITradingChat = None

class ModernChatInterface:
    def __init__(self, parent):
        self.parent = parent
        self.chat_history = []
        
        # Initialize AI chat FIRST - before setting up interface
        print(f"🔍 DEBUG: CHAT_AVAILABLE = {CHAT_AVAILABLE}")
        self.ai_chat = None  # Initialize to None first
        
        if CHAT_AVAILABLE and AITradingChat is not None:
            try:
                print("🔍 DEBUG: Attempting to initialize AITradingChat...")
                self.ai_chat = AITradingChat()
                print("✅ DEBUG: AITradingChat initialized successfully!")
            except Exception as e:
                print(f"❌ DEBUG: AI Chat initialization failed: {e}")
                import traceback
                traceback.print_exc()
                self.ai_chat = None
        else:
            print("❌ DEBUG: AITradingChat not available")
            self.ai_chat = None
        
        print(f"🔍 DEBUG: Final ai_chat status: {self.ai_chat is not None}")
        
        # THEN setup interface
        self.setup_modern_interface()

    def setup_modern_interface(self):
        """Create modern chat interface similar to Replit Assistant"""
        
        # Main chat frame with modern styling
        self.chat_frame = ttk.Frame(self.parent, style='Modern.TFrame')
        self.chat_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Configure styles
        style = ttk.Style()
        style.configure('Modern.TFrame', background='#0d1117')
        style.configure('Chat.TText', background='#161b22', foreground='#f0f6fc', 
                       font=('SF Pro Display', 11), relief='flat', borderwidth=0)
        style.configure('Input.TFrame', background='#21262d', relief='flat')
        style.configure('Send.TButton', background='#238636', foreground='white',
                       font=('SF Pro Display', 10, 'bold'), relief='flat')
        
        # Header with AGUS branding
        self.create_chat_header()
        
        # Chat display area (modern styling)
        self.create_chat_display()
        
        # Input area (like Replit's interface)
        self.create_input_area()
        
        # Quick actions (like Replit's suggestions)
        self.create_quick_actions()

    def create_chat_header(self):
        """Create modern chat header"""
        header_frame = ttk.Frame(self.chat_frame, style='Modern.TFrame')
        header_frame.pack(fill='x', pady=(0, 15))
        
        # AGUS logo and title
        title_frame = ttk.Frame(header_frame, style='Modern.TFrame')
        title_frame.pack(side='left')
        
        agus_label = tk.Label(title_frame, text="🤖", font=('SF Pro Display', 24), 
                             bg='#0d1117', fg='#58a6ff')
        agus_label.pack(side='left', padx=(0, 10))
        
        title_label = tk.Label(title_frame, text="AGUS", 
                              font=('SF Pro Display', 18, 'bold'), 
                              bg='#0d1117', fg='#f0f6fc')
        title_label.pack(side='left', anchor='w')
        
        subtitle_label = tk.Label(title_frame, text="Your AI Trading Assistant", 
                                 font=('SF Pro Display', 12), 
                                 bg='#0d1117', fg='#7d8590')
        subtitle_label.pack(side='left', padx=(10, 0), anchor='w')
        
        # Status indicator
        self.status_indicator = tk.Label(header_frame, text="●", 
                                        font=('SF Pro Display', 16), 
                                        bg='#0d1117', fg='#238636')
        self.status_indicator.pack(side='right')
        
        status_text = tk.Label(header_frame, text="Online", 
                              font=('SF Pro Display', 11), 
                              bg='#0d1117', fg='#238636')
        status_text.pack(side='right', padx=(0, 5))

    def create_chat_display(self):
        """Create modern chat display area"""
        # Chat container with custom styling
        chat_container = tk.Frame(self.chat_frame, bg='#0d1117')
        chat_container.pack(fill='both', expand=True, pady=(0, 15))
        
        # Create custom text widget for messages
        self.chat_display = tk.Text(chat_container, 
                                   background='#0d1117',
                                   foreground='#f0f6fc',
                                   font=('SF Pro Display', 12),
                                   relief='flat',
                                   borderwidth=0,
                                   wrap='word',
                                   state='disabled',
                                   cursor='arrow')
        
        # Custom scrollbar
        scrollbar = ttk.Scrollbar(chat_container, orient='vertical', 
                                 command=self.chat_display.yview)
        self.chat_display.configure(yscrollcommand=scrollbar.set)
        
        self.chat_display.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Auto-scroll when scrollbar position changes
        def on_scrollbar_set(*args):
            scrollbar.set(*args)
            # Auto scroll to bottom if new content added
            if float(args[1]) == 1.0:
                self.chat_display.see('end')
        
        self.chat_display.configure(yscrollcommand=on_scrollbar_set)
        
        # Configure text tags for styling
        self.setup_message_tags()
        
        # Welcome message with status
        if self.ai_chat:
            status_msg = "🚀 AGUS is ready to help with your trading bot! I can execute code, fix problems, and create files directly."
        else:
            status_msg = "🤖 AGUS Chat Interface Loaded\n⚠️ AI system currently unavailable. Responses will show technical solutions when available."
        self.add_system_message(status_msg)

    def setup_message_tags(self):
        """Configure text tags for different message types"""
        # User message styling
        self.chat_display.tag_configure('user_message', 
                                       background='#1f6feb', 
                                       foreground='white',
                                       font=('SF Pro Display', 12),
                                       relief='flat',
                                       borderwidth=1,
                                       lmargin1=20, lmargin2=20,
                                       rmargin=20, spacing1=10, spacing3=10)
        
        # AGUS response styling
        self.chat_display.tag_configure('agus_message',
                                       background='#161b22',
                                       foreground='#f0f6fc', 
                                       font=('SF Pro Display', 12),
                                       lmargin1=20, lmargin2=20,
                                       rmargin=20, spacing1=10, spacing3=10)
        
        # Code block styling
        self.chat_display.tag_configure('code_block',
                                       background='#0d1117',
                                       foreground='#79c0ff',
                                       font=('SF Mono', 11),
                                       lmargin1=40, lmargin2=40,
                                       rmargin=40, spacing1=5, spacing3=5)
        
        # System message styling
        self.chat_display.tag_configure('system_message',
                                       foreground='#7d8590',
                                       font=('SF Pro Display', 11, 'italic'),
                                       lmargin1=20, lmargin2=20,
                                       spacing1=5, spacing3=5)

    def create_input_area(self):
        """Create modern input area like Replit's interface"""
        input_container = tk.Frame(self.chat_frame, bg='#21262d', relief='flat')
        input_container.pack(fill='x', pady=(0, 10))
        
        # Input frame with padding
        input_frame = tk.Frame(input_container, bg='#21262d')
        input_frame.pack(fill='x', padx=15, pady=12)
        
        # Text input with modern styling
        self.message_input = tk.Text(input_frame,
                                    background='#0d1117',
                                    foreground='#f0f6fc',
                                    font=('SF Pro Display', 12),
                                    relief='flat',
                                    borderwidth=1,
                                    height=2,
                                    wrap='word',
                                    insertbackground='#58a6ff')
        
        # Placeholder text
        self.message_input.insert('1.0', 'Ask AGUS anything... (Press Ctrl+Enter to send)')
        self.message_input.configure(foreground='#7d8590')
        
        # Bind events
        self.message_input.bind('<Control-Return>', self.send_message)
        self.message_input.bind('<FocusIn>', self.clear_placeholder)
        self.message_input.bind('<FocusOut>', self.restore_placeholder)
        self.message_input.bind('<KeyRelease>', self.on_input_change)
        
        self.message_input.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        # Send button with modern styling
        self.send_button = tk.Button(input_frame,
                                    text='→',
                                    font=('SF Pro Display', 16, 'bold'),
                                    background='#238636',
                                    foreground='white',
                                    relief='flat',
                                    borderwidth=0,
                                    width=3,
                                    height=2,
                                    cursor='hand2',
                                    command=self.send_message)
        self.send_button.pack(side='right')

    def create_quick_actions(self):
        """Create quick action buttons like Replit's suggestions"""
        actions_frame = tk.Frame(self.chat_frame, bg='#0d1117')
        actions_frame.pack(fill='x')
        
        actions_label = tk.Label(actions_frame, 
                               text="Quick actions:", 
                               font=('SF Pro Display', 10),
                               bg='#0d1117', fg='#7d8590')
        actions_label.pack(side='left', padx=(5, 10))
        
        # Quick action buttons
        actions = [
            ("📊 Portfolio Status", "Show current portfolio status with live data"),
            ("🔧 Fix Bot Issue", "Diagnose and fix any bot problems"),
            ("📝 Create Strategy", "Create a new trading strategy file"),
            ("⚡ Execute Command", "Run a specific trading command")
        ]
        
        for text, command in actions:
            btn = tk.Button(actions_frame,
                           text=text,
                           font=('SF Pro Display', 9),
                           background='#21262d',
                           foreground='#58a6ff',
                           relief='flat',
                           borderwidth=1,
                           padx=10, pady=5,
                           cursor='hand2',
                           command=lambda cmd=command: self.send_quick_action(cmd))
            btn.pack(side='left', padx=5)

    def clear_placeholder(self, event=None):
        """Clear placeholder text on focus"""
        content = self.message_input.get('1.0', 'end-1c')
        if content.strip() == 'Ask AGUS anything... (Press Ctrl+Enter to send)':
            self.message_input.delete('1.0', 'end')
            self.message_input.configure(foreground='#f0f6fc')

    def restore_placeholder(self, event=None):
        """Restore placeholder if empty"""
        content = self.message_input.get('1.0', 'end-1c')
        if not content.strip():
            self.message_input.insert('1.0', 'Ask AGUS anything... (Press Ctrl+Enter to send)')
            self.message_input.configure(foreground='#7d8590')

    def on_input_change(self, event=None):
        """Handle input changes for dynamic styling"""
        content = self.message_input.get('1.0', 'end-1c')
        has_content = content.strip() and content.strip() != 'Ask AGUS anything... (Press Ctrl+Enter to send)'
        
        # Update send button state
        if has_content:
            self.send_button.configure(background='#238636', state='normal')
        else:
            self.send_button.configure(background='#656d76', state='disabled')

    def send_quick_action(self, action):
        """Send a quick action command"""
        self.clear_placeholder()
        self.message_input.delete('1.0', 'end')
        self.message_input.insert('1.0', action)
        self.message_input.configure(foreground='#f0f6fc')
        self.send_message()

    def send_message(self, event=None):
        """Send message to AGUS"""
        content = self.message_input.get('1.0', 'end-1c').strip()
        
        if not content or content == 'Ask AGUS anything... (Press Ctrl+Enter to send)':
            return
            
        # Add user message to display
        self.add_user_message(content)
        
        # Clear input
        self.message_input.delete('1.0', 'end')
        self.restore_placeholder()
        
        # Show typing indicator
        self.show_typing_indicator()
        
        # Process message in separate thread
        thread = threading.Thread(target=self.process_message, args=(content,), daemon=True)
        thread.start()

    def process_message(self, message):
        """Process message with AGUS AI"""
        try:
            print(f"🔍 DEBUG: Processing message: {message[:50]}...")
            
            if self.ai_chat:
                print("🔍 DEBUG: AI chat available, sending to AGUS...")
                
                # Run async function
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                response = loop.run_until_complete(self.ai_chat.ask_ai(message))
                loop.close()
                
                print(f"🔍 DEBUG: Got response: {response[:100]}...")
                
                # Update UI in main thread
                self.parent.after(0, lambda: self.hide_typing_indicator())
                self.parent.after(0, lambda: self.add_agus_message(response))
                self.parent.after(0, lambda: print("🔍 DEBUG: Response added to chat"))
                
            else:
                print("🔍 DEBUG: AI chat NOT available!")
                
                # Provide a helpful response even without AI
                fallback_msg = f"""🔧 **AGUS SYSTEM STATUS**

**Current Issue**: AI system temporarily unavailable
**Reason**: Database connection error or initialization failure

**Available Actions**:
- ✅ Check bot status in main dashboard
- ✅ Review trading performance 
- ✅ Monitor portfolio positions
- ✅ Restart application if needed

**Technical Status**:
- 🟢 Chat Interface: Running
- 🟡 AI Backend: Initializing
- 🟢 Trading Bot: Active

*Try your request again in a few moments as the AI system initializes.*"""
                
                self.parent.after(0, lambda: self.hide_typing_indicator())
                self.parent.after(0, lambda: self.add_agus_message(fallback_msg))
                
        except Exception as e:
            print(f"🔍 DEBUG: Exception in process_message: {e}")
            error_msg = f"❌ Error: {str(e)}\n\n🔧 **Quick Fix**: Restart the chat interface or check bot status."
            self.parent.after(0, lambda: self.hide_typing_indicator())
            self.parent.after(0, lambda: self.add_agus_message(error_msg))

    def show_typing_indicator(self):
        """Show AGUS typing indicator"""
        self.chat_display.configure(state='normal')
        self.chat_display.insert('end', '\n🤖 AGUS is thinking...\n', 'system_message')
        self.chat_display.configure(state='disabled')
        self.chat_display.see('end')

    def hide_typing_indicator(self):
        """Hide typing indicator"""
        self.chat_display.configure(state='normal')
        content = self.chat_display.get('1.0', 'end')
        if '🤖 AGUS is thinking...' in content:
            # Remove the typing indicator
            lines = content.split('\n')
            filtered_lines = [line for line in lines if '🤖 AGUS is thinking...' not in line]
            self.chat_display.delete('1.0', 'end')
            self.chat_display.insert('1.0', '\n'.join(filtered_lines))
        self.chat_display.configure(state='disabled')

    def add_user_message(self, message):
        """Add user message with modern styling"""
        self.chat_display.configure(state='normal')
        
        timestamp = datetime.now().strftime('%H:%M')
        self.chat_display.insert('end', f'\n[{timestamp}] You:\n', 'system_message')
        self.chat_display.insert('end', f'{message}\n', 'user_message')
        
        self.chat_display.configure(state='disabled')
        
        # Ensure scroll to bottom
        self.chat_display.see('end')
        self.chat_display.update()

    def add_agus_message(self, message):
        """Add AGUS message with code highlighting"""
        self.chat_display.configure(state='normal')
        
        timestamp = datetime.now().strftime('%H:%M')
        self.chat_display.insert('end', f'\n[{timestamp}] AGUS:\n', 'system_message')
        
        # Parse and style the message
        self.parse_and_insert_message(message)
        
        self.chat_display.configure(state='disabled')
        
        # Force scroll to bottom with multiple calls
        self.chat_display.see('end')
        self.chat_display.update()
        self.parent.after(100, lambda: self.chat_display.see('end'))
        self.parent.after(200, lambda: self.chat_display.see('end'))

    def parse_and_insert_message(self, message):
        """Parse message and apply appropriate styling"""
        # Split message by code blocks
        parts = re.split(r'```(\w+)?\n?(.*?)\n?```', message, flags=re.DOTALL)
        
        for i, part in enumerate(parts):
            if i % 3 == 0:  # Regular text
                if part.strip():
                    self.chat_display.insert('end', part, 'agus_message')
            elif i % 3 == 2:  # Code content
                if part.strip():
                    self.chat_display.insert('end', f'\n{part}\n', 'code_block')
        
        # Add extra newline for spacing
        self.chat_display.insert('end', '\n')

    def add_system_message(self, message):
        """Add system message"""
        self.chat_display.configure(state='normal')
        self.chat_display.insert('end', f'{message}\n\n', 'system_message')
        self.chat_display.configure(state='disabled')
        self.chat_display.see('end')