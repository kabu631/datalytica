import os
import subprocess
import sys

def run_command(cmd, cwd=None):
    print(f"Running: {cmd} in {cwd or os.getcwd()}")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    if result.returncode != 0:
        print(f"Command failed with exit code {result.returncode}")
        sys.exit(1)

def main():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    backend_dir = os.path.join(root_dir, 'backend')
    frontend_dir = os.path.join(root_dir, 'frontend')
    installer_dir = os.path.join(root_dir, 'installer')
    
    print("=== Datalytica Build Process ===")
    
    # 1. Install Python dependencies
    print("\n--- Step 1: Installing Python Dependencies ---")
    run_command("pip install -r requirements.txt", cwd=backend_dir)
    run_command("pip install pyinstaller", cwd=backend_dir)
    
    # 2. PyInstaller
    print("\n--- Step 2: Compiling Python Backend via PyInstaller ---")
    run_command(f"pyinstaller datalytica.spec --workpath {os.path.join(root_dir, 'build')} --distpath {os.path.join(root_dir, 'dist')}", cwd=installer_dir)
    
    # 3. Install Node dependencies
    print("\n--- Step 3: Installing Node Dependencies ---")
    run_command("npm install", cwd=frontend_dir)
    
    # 4. electron-builder
    print("\n--- Step 4: Packaging Electron Application ---")
    run_command("npx electron-builder --win", cwd=frontend_dir)
    
    print("\n=== Build Complete! Executable is in dist/ ===")

if __name__ == "__main__":
    main()
