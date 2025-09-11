"""
Simple health check server for Fly.io monitoring
"""
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
from datetime import datetime

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            # Simple health check
            health_data = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "app": "ai-trading-bot",
                "mode": os.getenv("MODE", "paper")
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(health_data).encode())
        else:
            self.send_response(404)
            self.end_headers()

def start_health_server():
    """Start health check server in background thread"""
    server = HTTPServer(('0.0.0.0', 8080), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print("🔍 Health check server started on port 8080")
    return server