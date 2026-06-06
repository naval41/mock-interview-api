#!/usr/bin/env python3
"""
Debug Test Script for Mock Interview API
Starts the application in debug mode with enhanced logging and development features.
"""

import os
import sys
import subprocess
import signal
import time
from pathlib import Path

def setup_environment():
    """Setup environment variables for debug mode."""
    # Set environment to local for debug mode
    os.environ['ENV'] = 'local'
    
    # Enable detailed logging for specific modules
    os.environ['PYTHONPATH'] = str(Path(__file__).parent)
    
    print("🔧 Environment setup:")
    print(f"   ENV: {os.environ.get('ENV')}")
    print(f"   LOG_LEVEL: {os.environ.get('LOG_LEVEL')}")
    print(f"   PYTHONPATH: {os.environ.get('PYTHONPATH')}")
    print()

def check_dependencies():
    """Check if required dependencies are available."""
    try:
        import uvicorn
        print("✅ uvicorn is available")
    except ImportError:
        print("❌ uvicorn is not installed. Please install it with: pip install uvicorn")
        return False
    
    try:
        from app.main import app
        print("✅ app.main module is accessible")
    except ImportError as e:
        print(f"❌ Cannot import app.main: {e}")
        return False
    
    return True

def run_debug_server():
    """Run the debug server with enhanced logging."""
    print("🚀 Starting Mock Interview API in DEBUG mode...")
    print("=" * 60)
    
    # Command to run the server
    cmd = [
        sys.executable, "-m", "uvicorn", 
        "app.main:app",
        "--reload",           # Enable auto-reload on code changes
        "--log-level", "debug",  # Set log level to debug
        "--access-log",       # Enable access logging
        "--use-colors",       # Enable colored output
        "--host", "0.0.0.0",  # Listen on all interfaces
        "--port", "8000"      # Default port
    ]
    
    print("Command:", " ".join(cmd))
    print("=" * 60)
    print()
    
    try:
        # Run the server
        process = subprocess.Popen(
            cmd,
            cwd=Path(__file__).parent,
            env=os.environ.copy()
        )
        
        # Give the server a moment to start
        print("⏳ Starting server...")
        time.sleep(2)
        
        print("\n" + "=" * 80)
        print("🎯 SERVER STARTED SUCCESSFULLY!")
        print("=" * 80)
        print("📍 API BASE URL:      http://localhost:8000")
        print("📖 API DOCS (Swagger): http://localhost:8000/docs")
        print("🔍 API DOCS (ReDoc):   http://localhost:8000/redoc")
        print("🔧 Health Check:      http://localhost:8000/health")
        print("=" * 80)
        print("💡 TIP: Open these URLs in your browser to test the API")
        print("🛑 Press Ctrl+C to stop the server")
        print("=" * 80)
        
        # Wait for the process to complete or be interrupted
        process.wait()
        
    except KeyboardInterrupt:
        print("\n🛑 Shutting down server...")
        process.terminate()
        
        # Give it a moment to shut down gracefully
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            print("⚠️  Force killing server...")
            process.kill()
            
        print("✅ Server stopped.")
        
    except Exception as e:
        print(f"❌ Error running server: {e}")
        return False
    
    return True

def main():
    """Main function to run the debug server."""
    print("🎯 Mock Interview API - Debug Mode Runner")
    print("=" * 60)
    
    # Setup environment
    setup_environment()
    
    # Check dependencies
    if not check_dependencies():
        print("\n❌ Dependency check failed. Please install missing dependencies.")
        sys.exit(1)
    
    print("\n🔍 Debug Features Enabled:")
    print("   • Auto-reload on code changes")
    print("   • Enhanced debug logging")
    print("   • Access request logging")
    print("   • Colored console output")
    print("   • Detailed error traces")
    print()
    
    # Run the server
    success = run_debug_server()
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
