#!/usr/bin/env python3
"""
Debug Server Starter for Mock Interview API
Shows URLs clearly and runs in foreground
"""

import os
import sys

def print_banner():
    """Print startup banner with URLs."""
    print("\n" + "=" * 100)
    print("🎯 MOCK INTERVIEW API - DEBUG MODE")
    print("=" * 100)
    print("🔧 Environment: local")
    print("📊 Log Level: debug")
    print("🔄 Auto-reload: enabled")
    print("=" * 100)

def print_urls():
    """Print the server URLs prominently."""
    print("\n" + "🌐 SERVER URLS:")
    print("=" * 100)
    print("📍 API Base URL:       http://localhost:8000")
    print("📖 API Documentation:  http://localhost:8000/docs")
    print("🔍 Alternative Docs:   http://localhost:8000/redoc")
    print("🩺 Health Check:       http://localhost:8000/health")
    print("=" * 100)
    print("💡 Copy and paste these URLs into your browser!")
    print("🛑 Press Ctrl+C to stop the server")
    print("=" * 100)

def main():
    """Start the debug server."""
    print_banner()
    
    # Set environment variables
    os.environ['ENV'] = 'local'
    
    print_urls()
    
    print("\n🚀 Starting uvicorn server...")
    print("⏳ Please wait for startup to complete...\n")
    
    try:
        # Import uvicorn and start server
        import uvicorn
        
        # Run the server
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="debug",
            access_log=True,
            use_colors=True,
            reload_dirs=["app"]  # Only watch app directory for changes
        )
        
    except KeyboardInterrupt:
        print("\n" + "=" * 100)
        print("🛑 SERVER STOPPED")
        print("=" * 100)
        
    except ImportError:
        print("❌ Error: uvicorn is not installed")
        print("💡 Install it with: pip install uvicorn")
        sys.exit(1)
        
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
