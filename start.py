#!/usr/bin/env python3
"""Start both the backend and frontend servers."""
import subprocess
import sys
import platform
import signal
import time
import urllib.request
from pathlib import Path

def get_venv_python(backend_dir):
    """Get the Python executable path for the virtual environment."""
    bin_dir = "Scripts" if platform.system() == "Windows" else "bin"
    return backend_dir / "venv" / bin_dir / ("python.exe" if platform.system() == "Windows" else "python")

def setup_backend(backend_dir):
    """Setup backend: check .env, venv, and install dependencies."""
    # Check if root .env exists
    root_env = backend_dir.parent / ".env"
    if not root_env.exists():
        print("WARNING: .env file not found at project root.")
        print("Please create a .env file with required configuration.")
        print("See ENV_SETUP.md for details.")
    
    # Check if venv module is available
    try:
        import venv
    except ImportError:
        print("ERROR: The 'venv' module is not available.")
        print("\nOn Debian/Ubuntu systems, install it with:")
        print("    sudo apt install python3-venv")
        print("\nOr for a specific Python version:")
        print(f"    sudo apt install python{sys.version_info.major}.{sys.version_info.minor}-venv")
        sys.exit(1)
    
    # Check if global pip is available
    global_pip_check = subprocess.run(
        [sys.executable, "-m", "pip", "--version"],
        capture_output=True,
        text=True,
        check=False
    )
    global_pip_available = global_pip_check.returncode == 0
    
    # Check if ensurepip is available in system Python
    ensurepip_check = subprocess.run(
        [sys.executable, "-m", "ensurepip", "--version"],
        capture_output=True,
        text=True,
        check=False
    )
    ensurepip_available = ensurepip_check.returncode == 0
    
    venv_python = get_venv_python(backend_dir)
    venv_exists = venv_python.exists()
    
    # Check if pip is available in existing venv
    pip_available = False
    if venv_exists:
        pip_check = subprocess.run(
            [str(venv_python), "-m", "pip", "--version"],
            capture_output=True,
            text=True,
            check=False
        )
        pip_available = pip_check.returncode == 0
    
    # If venv exists but pip is missing, try to install it
    if venv_exists and not pip_available:
        print("pip is not available in virtual environment. Installing pip...")
        
        # Try ensurepip first (if available)
        if ensurepip_available:
            try:
                subprocess.run(
                    [str(venv_python), "-m", "ensurepip", "--upgrade"],
                    check=True,
                    capture_output=True,
                    text=True
                )
                print("pip bootstrapped successfully using ensurepip.")
                pip_available = True
            except subprocess.CalledProcessError:
                pass
        
        # If ensurepip didn't work, try using global pip or get-pip.py
        if not pip_available:
            if global_pip_available:
                # Use global pip to install pip into the venv
                print("Installing pip into venv using global pip...")
                try:
                    # Download get-pip.py and run it with venv python
                    get_pip_url = "https://bootstrap.pypa.io/get-pip.py"
                    get_pip_path = backend_dir / "get-pip.py"
                    try:
                        urllib.request.urlretrieve(get_pip_url, get_pip_path)
                        subprocess.run(
                            [str(venv_python), str(get_pip_path)],
                            check=True,
                            capture_output=True,
                            text=True
                        )
                        get_pip_path.unlink()  # Clean up
                        print("pip installed successfully using get-pip.py.")
                        pip_available = True
                    except Exception as e:
                        if get_pip_path.exists():
                            get_pip_path.unlink()
                        raise
                except Exception as e:
                    print(f"Failed to install pip using get-pip.py: {e}")
            
            if not pip_available:
                print("ERROR: Cannot install pip in virtual environment.")
                if not global_pip_available:
                    print("\nGlobal pip is not available. Install it with:")
                    print(f"    sudo apt install python{sys.version_info.major}-pip")
                    print("    or")
                    print(f"    sudo apt install python{sys.version_info.major}.{sys.version_info.minor}-pip")
                print("\nAlternatively, install python3-venv which includes ensurepip:")
                print(f"    sudo apt install python{sys.version_info.major}.{sys.version_info.minor}-venv")
                print(f"\nThen remove the venv and recreate it:")
                print(f"    rm -rf {backend_dir / 'venv'}")
                print("    python3 start.py")
                sys.exit(1)
    
    # Create venv if missing
    if not venv_exists:
        print("Creating virtual environment...")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "venv", str(backend_dir / "venv")], 
                check=True, 
                shell=platform.system() == "Windows",
                capture_output=True,
                text=True
            )
            print("Virtual environment created.")
            
            # Check if pip was included, if not install it
            venv_python = get_venv_python(backend_dir)
            pip_check = subprocess.run(
                [str(venv_python), "-m", "pip", "--version"],
                capture_output=True,
                text=True,
                check=False
            )
            if pip_check.returncode != 0:
                # Try ensurepip first
                if ensurepip_available:
                    print("Bootstrapping pip using ensurepip...")
                    try:
                        subprocess.run(
                            [str(venv_python), "-m", "ensurepip", "--upgrade"],
                            check=True,
                            capture_output=True,
                            text=True
                        )
                        print("pip bootstrapped successfully.")
                    except subprocess.CalledProcessError:
                        pass
                
                # If ensurepip didn't work, use get-pip.py
                if subprocess.run([str(venv_python), "-m", "pip", "--version"],
                                 capture_output=True, check=False).returncode != 0:
                    if global_pip_available:
                        print("Installing pip into venv using get-pip.py...")
                        try:
                            get_pip_url = "https://bootstrap.pypa.io/get-pip.py"
                            get_pip_path = backend_dir / "get-pip.py"
                            urllib.request.urlretrieve(get_pip_url, get_pip_path)
                            subprocess.run(
                                [str(venv_python), str(get_pip_path)],
                                check=True,
                                capture_output=True,
                                text=True
                            )
                            get_pip_path.unlink()  # Clean up
                            print("pip installed successfully.")
                        except Exception as e:
                            if get_pip_path.exists():
                                get_pip_path.unlink()
                            print(f"Warning: Could not install pip: {e}")
        except subprocess.CalledProcessError as e:
            print("ERROR: Failed to create virtual environment.")
            print(f"Exit code: {e.returncode}")
            if e.stderr:
                print(f"Error output: {e.stderr}")
            if "ensurepip is not available" in (e.stderr or ""):
                if not global_pip_available:
                    print("\nNeither ensurepip nor global pip is available.")
                    print("Install pip globally with:")
                    print(f"    sudo apt install python{sys.version_info.major}-pip")
                    print("    or")
                    print(f"    sudo apt install python{sys.version_info.major}.{sys.version_info.minor}-pip")
                else:
                    print("\nOn Debian/Ubuntu systems, you may also install python3-venv with:")
                    print(f"    sudo apt install python{sys.version_info.major}.{sys.version_info.minor}-venv")
            sys.exit(1)
    
    # Check if critical dependencies are installed
    # Test by actually trying to import the backend module (same way uvicorn will)
    critical_modules = ["uvicorn", "fastapi", "starlette", "sqlalchemy", "pydantic"]
    missing_modules = []
    
    # First check individual modules
    for module in critical_modules:
        check_result = subprocess.run(
            [str(venv_python), "-c", f"import {module}"],
            capture_output=True,
            check=False,
            text=True,
            cwd=backend_dir
        )
        if check_result.returncode != 0:
            missing_modules.append(module)
            if check_result.stderr:
                print(f"  Warning: Cannot import {module}: {check_result.stderr.strip()[:100]}")
    
    # Also test if we can import the actual backend module
    backend_import_test = subprocess.run(
        [str(venv_python), "-c", "import sys; sys.path.insert(0, '.'); import start_backend"],
        capture_output=True,
        check=False,
        text=True,
        cwd=backend_dir
    )
    if backend_import_test.returncode != 0 and "fastapi" not in missing_modules and "pydantic" not in str(backend_import_test.stderr):
        # If individual modules pass but backend import fails, add pydantic to check
        if "pydantic" in str(backend_import_test.stderr).lower():
            if "pydantic" not in [m.lower() for m in missing_modules]:
                missing_modules.append("pydantic")
    
    # Install dependencies if any are missing
    if missing_modules:
        print(f"Installing backend dependencies (missing: {', '.join(missing_modules)})...")
        try:
            # First upgrade pip to ensure it's working
            subprocess.run(
                [str(venv_python), "-m", "pip", "install", "--upgrade", "pip"],
                cwd=backend_dir,
                check=True,
                shell=platform.system() == "Windows",
                capture_output=True,
                text=True
            )
            
            # Install requirements - use --force-reinstall if this is a retry
            install_cmd = [str(venv_python), "-m", "pip", "install", "-r", str(backend_dir / "requirements.txt")]
            
            # If we're missing critical modules, force reinstall to fix any corruption
            if len(missing_modules) >= 2 or "fastapi" in missing_modules or "pydantic" in missing_modules:
                print("Force reinstalling dependencies to fix potential corruption...")
                install_cmd.extend(["--force-reinstall", "--no-cache-dir"])
            
            result = subprocess.run(
                install_cmd,
                cwd=backend_dir,
                check=True,
                shell=platform.system() == "Windows",
                capture_output=True,
                text=True
            )
            print("Dependencies installed.")
            
            # Verify critical modules are now available by actually importing them
            # Use a more thorough check that matches how uvicorn will import
            still_missing = []
            for module in critical_modules:
                # Try importing the module with full error output
                check_result = subprocess.run(
                    [str(venv_python), "-c", f"import {module}; print('OK')"],
                    capture_output=True,
                    check=False,
                    text=True
                )
                if check_result.returncode != 0:
                    still_missing.append(module)
                    if check_result.stderr:
                        print(f"  Import error for {module}: {check_result.stderr.strip()}")
            
            if still_missing:
                print(f"ERROR: Some modules are still missing after installation: {', '.join(still_missing)}")
                print("This usually indicates a corrupted venv or Python path issue.")
                print("\nTry the following:")
                print(f"1. Remove and recreate the venv:")
                print(f"   rm -rf {backend_dir / 'venv'}")
                print(f"   python3 start.py")
                print(f"\n2. Or manually reinstall in the venv:")
                print(f"   {venv_python} -m pip install --force-reinstall --no-cache-dir -r {backend_dir / 'requirements.txt'}")
                sys.exit(1)
        except subprocess.CalledProcessError as e:
            print("ERROR: Failed to install dependencies.")
            print(f"Exit code: {e.returncode}")
            if e.stdout:
                print(f"Output: {e.stdout}")
            if e.stderr:
                print(f"Error output: {e.stderr}")
            print("\nTry installing dependencies manually:")
            print(f"    {venv_python} -m pip install -r {backend_dir / 'requirements.txt'}")
            sys.exit(1)
    
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
