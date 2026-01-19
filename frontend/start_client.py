#!/usr/bin/env python3
"""
Start the frontend development server.
"""
import subprocess
import sys
import platform
import os
import json
from pathlib import Path

# #region agent log
def log_debug(location, message, data=None, hypothesis_id=None):
    """Log debug information to file."""
    try:
        log_path = Path(__file__).parent / ".cursor" / "debug.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            log_entry = {
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": hypothesis_id,
                "location": location,
                "message": message,
                "data": data or {},
                "timestamp": int(__import__("time").time() * 1000)
            }
            f.write(json.dumps(log_entry) + "\n")
    except Exception:
        pass  # Silently fail if logging doesn't work
# #endregion

def check_npm_available():
    """Check if npm is available in the system."""
    try:
        result = subprocess.run(
            ["npm", "--version"],
            capture_output=True,
            text=True,
            check=False
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False

def main():
    """Start the Vite development server."""
    # #region agent log
    log_debug("start_client.py:main", "Function entry", {"platform": platform.system()}, "A")
    # #endregion
    
    # Check if npm is available
    if not check_npm_available():
        print("ERROR: npm is not found. Node.js and npm are required to run the frontend.", file=sys.stderr)
        print("\nTo install Node.js and npm on Debian/Ubuntu:", file=sys.stderr)
        print("    curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -", file=sys.stderr)
        print("    sudo apt-get install -y nodejs", file=sys.stderr)
        print("\nOr use the default package manager:", file=sys.stderr)
        print("    sudo apt update", file=sys.stderr)
        print("    sudo apt install nodejs npm", file=sys.stderr)
        print("\nAfter installing, verify with: npm --version", file=sys.stderr)
        sys.exit(1)
    
    cwd = os.getcwd()
    # #region agent log
    log_debug("start_client.py:main", "Current working directory", {"cwd": cwd}, "C")
    # #endregion
    
    package_json_path = Path(cwd) / "package.json"
    node_modules_path = Path(cwd) / "node_modules"
    # #region agent log
    log_debug("start_client.py:main", "Checking package.json existence", {"exists": package_json_path.exists(), "path": str(package_json_path)}, "D")
    log_debug("start_client.py:main", "Checking node_modules existence", {"exists": node_modules_path.exists(), "path": str(node_modules_path)}, "A")
    # #endregion
    
    # Check if vite binary exists
    is_windows = platform.system() == "Windows"
    vite_bin_name = "vite.cmd" if is_windows else "vite"
    vite_bin_path = node_modules_path / ".bin" / vite_bin_name
    # #region agent log
    log_debug("start_client.py:main", "Checking vite binary", {"exists": vite_bin_path.exists(), "path": str(vite_bin_path), "is_windows": is_windows}, "B")
    # #endregion
    
    # Check if dependencies need to be installed
    if not node_modules_path.exists() or not vite_bin_path.exists():
        # #region agent log
        log_debug("start_client.py:main", "Dependencies missing, installing", {"node_modules_exists": node_modules_path.exists(), "vite_exists": vite_bin_path.exists()}, "A")
        # #endregion
        print("Installing dependencies...", file=sys.stderr)
        try:
            use_shell = platform.system() == "Windows"
            # #region agent log
            log_debug("start_client.py:main", "Running npm install", {"use_shell": use_shell, "cwd": cwd}, "A")
            # #endregion
            result = subprocess.run(["npm", "install"], check=True, shell=use_shell, cwd=cwd, capture_output=True, text=True)
            # #region agent log
            log_debug("start_client.py:main", "npm install completed", {"returncode": result.returncode, "stdout_length": len(result.stdout), "stderr_length": len(result.stderr)}, "A")
            # #endregion
            # Re-check vite binary after install
            vite_exists_after = vite_bin_path.exists()
            # #region agent log
            log_debug("start_client.py:main", "Vite binary check after install", {"exists": vite_exists_after, "path": str(vite_bin_path)}, "B")
            # #endregion
        except FileNotFoundError:
            print("ERROR: npm command not found. Please ensure Node.js and npm are installed.", file=sys.stderr)
            print("See installation instructions above.", file=sys.stderr)
            sys.exit(1)
        except subprocess.CalledProcessError as e:
            # #region agent log
            log_debug("start_client.py:main", "npm install failed", {"error": str(e), "returncode": e.returncode, "stdout": getattr(e, "stdout", ""), "stderr": getattr(e, "stderr", "")}, "A")
            # #endregion
            print(f"Error installing dependencies: {e}", file=sys.stderr)
            if hasattr(e, "stdout") and e.stdout:
                print(f"stdout: {e.stdout}", file=sys.stderr)
            if hasattr(e, "stderr") and e.stderr:
                print(f"stderr: {e.stderr}", file=sys.stderr)
            sys.exit(1)
    
    # Check package.json for dev script
    if package_json_path.exists():
        try:
            with open(package_json_path, "r", encoding="utf-8") as f:
                package_data = json.load(f)
            # #region agent log
            has_vite_dep = "vite" in package_data.get("devDependencies", {}) or "vite" in package_data.get("dependencies", {})
            log_debug("start_client.py:main", "Package.json contents", {"has_vite": has_vite_dep, "has_dev_script": "dev" in package_data.get("scripts", {})}, "D")
            # #endregion
        except Exception as e:
            # #region agent log
            log_debug("start_client.py:main", "Error reading package.json", {"error": str(e)}, "D")
            # #endregion
            pass
    
    # Start the dev server
    try:
        use_shell = platform.system() == "Windows"
        # #region agent log
        log_debug("start_client.py:main", "Starting npm run dev", {"use_shell": use_shell, "cwd": cwd, "vite_bin_exists": vite_bin_path.exists()}, "A")
        # #endregion
        # Don't capture output for dev server so user can see it
        subprocess.run(["npm", "run", "dev"], check=True, shell=use_shell, cwd=cwd)
    except FileNotFoundError:
        # #region agent log
        log_debug("start_client.py:main", "npm not found", {"error": "npm command not found"}, "A")
        # #endregion
        print("ERROR: npm command not found. Please ensure Node.js and npm are installed.", file=sys.stderr)
        print("\nTo install Node.js and npm on Debian/Ubuntu:", file=sys.stderr)
        print("    curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -", file=sys.stderr)
        print("    sudo apt-get install -y nodejs", file=sys.stderr)
        print("\nOr use the default package manager:", file=sys.stderr)
        print("    sudo apt update", file=sys.stderr)
        print("    sudo apt install nodejs npm", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        # #region agent log
        log_debug("start_client.py:main", "npm run dev failed", {"error": str(e), "returncode": e.returncode}, "A")
        # #endregion
        print(f"Error starting frontend: {e}", file=sys.stderr)
        if hasattr(e, "stdout") and e.stdout:
            print(f"stdout: {e.stdout}", file=sys.stderr)
        if hasattr(e, "stderr") and e.stderr:
            print(f"stderr: {e.stderr}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # #region agent log
        log_debug("start_client.py:__main__", "Unhandled exception", {"error": str(e), "type": type(e).__name__}, "A")
        # #endregion
        print(f"Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)