#!/usr/bin/env python3
"""Start both the backend and frontend servers."""
import subprocess
import sys
import platform
import signal
import time
from pathlib import Path

def get_venv_python(backend_dir):
    """Get the Python executable path for the virtual environment."""
    bin_dir = "Scripts" if platform.system() == "Windows" else "bin"
    return backend_dir / "venv" / bin_dir / ("python.exe" if platform.system() == "Windows" else "python")

def setup_backend(backend_dir):
    """Setup backend: create .env, venv, and install dependencies."""
    # Create .env if missing
    env_file = backend_dir / ".env"
    if not env_file.exists():
        env_file.write_text("DATABASE_URL=sqlite:///./wazzap.db\n")
        print("Created .env with SQLite configuration.")
    
    # Create venv if missing
    venv_python = get_venv_python(backend_dir)
    if not venv_python.exists():
        print("Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", str(backend_dir / "venv")], 
                      check=True, shell=platform.system() == "Windows")
        print("Virtual environment created.")
    
    # Install dependencies if missing
    if not subprocess.run([str(venv_python), "-c", "import uvicorn"], 
                         capture_output=True, check=False).returncode == 0:
        print("Installing backend dependencies...")
        subprocess.run([str(venv_python), "-m", "pip", "install", "-r", 
                       str(backend_dir / "requirements.txt")],
                      cwd=backend_dir, check=True, shell=platform.system() == "Windows")
        print("Dependencies installed.")
    
    return venv_python

def main():
    """Start both backend and frontend servers."""
    root = Path(__file__).parent
    backend_dir, frontend_dir = root / "backend", root / "frontend"
    is_windows = platform.system() == "Windows"
    
    # Setup backend
    venv_python = setup_backend(backend_dir)
    
    # Start frontend (only start once)
    print("Starting frontend server...")
    frontend = subprocess.Popen([sys.executable, "start_client.py"],
                                cwd=frontend_dir, shell=is_windows)
    
    # Flag to track if we should keep restarting backend
    should_restart_backend = True
    backend = None
    
    # Cleanup handler
    def cleanup(sig=None, frame=None):
        nonlocal should_restart_backend
        print("\nShutting down servers...")
        should_restart_backend = False
        if backend:
            backend.terminate()
            backend.wait()
        frontend.terminate()
        frontend.wait()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, cleanup)
    if not is_windows:
        signal.signal(signal.SIGTERM, cleanup)
    
    # Keep restarting backend if it exits (e.g., after database reset)
    while should_restart_backend:
        if backend is None or backend.poll() is not None:
            if backend is not None:
                exit_code = backend.poll()
                if exit_code == 0:
                    print("Backend exited. Restarting...")
                else:
                    print(f"Backend exited with code {exit_code}. Restarting...")
            
            print("Starting backend server...")
            backend = subprocess.Popen([str(venv_python), "-m", "uvicorn", "start_backend:app", 
                                        "--reload", "--host", "0.0.0.0", "--port", "8000"],
                                       cwd=backend_dir, shell=is_windows)
            time.sleep(2)
        
        try:
            # Check backend status periodically
            time.sleep(1)
            if frontend.poll() is not None:
                print("Frontend exited. Shutting down...")
                cleanup()
                break
        except KeyboardInterrupt:
            cleanup()
            break

if __name__ == "__main__":
    main()
