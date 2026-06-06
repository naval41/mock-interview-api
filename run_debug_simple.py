#!/usr/bin/env python3
"""
Simple Debug Script for Mock Interview API
Runs the server directly so you can see all uvicorn output
"""

import os
import sys

def main():
    """Run the debug server directly."""
    print("🎯 Mock Interview API - Simple Debug Mode")
    print("=" * 80)
    
    # Set environment
    os.environ['ENV'] = 'local'
    
    print("🔧 Environment: ENV=local")
    print("🚀 Starting server...")
    print("=" * 80)
    print("📍 URLs will be shown by uvicorn below:")
    print("   • API Base: http://localhost:8000")  
    print("   • API Docs: http://localhost:8000/docs")
    print("   • ReDoc: http://localhost:8000/redoc")
    print("=" * 80)
    print()
    
    # Import and run uvicorn directly
    try:
        import uvicorn
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="debug",
            access_log=True,
            use_colors=True
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped.")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
