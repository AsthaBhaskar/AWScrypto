#!/usr/bin/env python3
"""
Simple HTTP server for Naomi Crypto Assistant UI
Run this script to serve the UI locally
"""

import http.server
import socketserver
import os
import sys
from pathlib import Path

def main():
    # Get the directory where this script is located
    script_dir = Path(__file__).parent.absolute()
    
    # Change to the UI directory
    os.chdir(script_dir)
    
    # Set up the server
    PORT = 8080
    
    # Create a custom handler to serve index.html by default
    class CustomHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            # If the path is root, serve index.html
            if self.path == '/':
                self.path = '/index.html'
            return http.server.SimpleHTTPRequestHandler.do_GET(self)
        
        def end_headers(self):
            # Add CORS headers
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            super().end_headers()
    
    try:
        with socketserver.TCPServer(("", PORT), CustomHandler) as httpd:
            print(f"🚀 Naomi Crypto Assistant UI Server")
            print(f"📍 Serving at: http://localhost:{PORT}")
            print(f"🌐 API Base: http://13.60.80.172")
            print(f"📁 Directory: {script_dir}")
            print(f"🛑 Press Ctrl+C to stop the server")
            print(f"=" * 50)
            
            # Check if index.html exists
            if not os.path.exists('index.html'):
                print("❌ Error: index.html not found!")
                print("Make sure you're running this script from the ui/ directory")
                sys.exit(1)
            
            print("✅ UI files found successfully!")
            print("🌐 Open your browser and go to: http://localhost:8080")
            print()
            
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except OSError as e:
        if e.errno == 48:  # Address already in use
            print(f"❌ Port {PORT} is already in use!")
            print(f"Try a different port or stop the existing server")
        else:
            print(f"❌ Server error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main() 