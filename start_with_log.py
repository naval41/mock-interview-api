#!/usr/bin/env python3
"""
Start Mock Interview API with logging to file
Kills existing processes and starts server with log output
"""

import os
import sys
import subprocess
import signal
from datetime import datetime
from pathlib import Path

def kill_existing_processes():
    """Kill any existing processes on port 8000."""
    try:
        # Get PIDs of processes using port 8000
        result = subprocess.run(['lsof', '-t', '-i:8000'], 
                               capture_output=True, text=True)
        
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            print(f"🛑 Killing existing processes: {', '.join(pids)}")
            
            for pid in pids:
                try:
                    os.kill(int(pid), signal.SIGKILL)
                except (ProcessLookupError, ValueError):
                    pass  # Process already dead or invalid PID
            
            print("✅ Existing processes killed")
        else:
            print("✅ No existing processes found on port 8000")
            
    except FileNotFoundError:
        print("⚠️  lsof not found, skipping process cleanup")
    except Exception as e:
        print(f"⚠️  Error killing processes: {e}")

def main():
    """Start server with logging."""
    print("🎯 Mock Interview API - Starting with log output")
    print("=" * 50)
    
    # Kill existing processes
    kill_existing_processes()
    
    # Create log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"server_{timestamp}.log"
    
    print(f"📝 Log file: {log_file}")
    print("🚀 Starting server...")
    print("📍 Server URL: http://localhost:8000")
    print("📖 API Docs: http://localhost:8000/docs")
    print("=" * 50)
    print("Press Ctrl+C to stop the server")
    print()
    
    # Set environment
    env = os.environ.copy()
    env['ENV'] = 'local'
    
    # Command to run
    cmd = [
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--reload",
        "--log-level", "debug",
        "--access-log",
        "--use-colors"
    ]
    
    try:
        # Start server and write to both console and log file
        with open(log_file, 'w') as log:
            process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Read output line by line and write to both console and file
            for line in process.stdout:
                print(line, end='')  # Print to console
                log.write(line)      # Write to log file
                log.flush()          # Ensure it's written immediately
                
    except KeyboardInterrupt:
        print("\n🛑 Shutting down server...")
        if 'process' in locals():
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        print("✅ Server stopped")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
