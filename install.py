import os, sys, platform, subprocess

def install():
    print("🛠️ Installing TimeTrace Executive...")
    
    # 1. Determine Paths
    home = os.path.expanduser("~")
    script_path = os.path.abspath("trace.py")
    
    if not os.path.exists(script_path):
        print("❌ Error: 'trace.py' not found in this folder. Please place it here first.")
        return

    # 2. Check Dependencies (Windows needs windows-curses)
    if platform.system() == "Windows":
        try:
            import _curses
        except ImportError:
            print("📦 Installing 'windows-curses' dependency...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "windows-curses"])
                print("✅ 'windows-curses' installed.")
            except subprocess.CalledProcessError:
                print("❌ Failed to install 'windows-curses'. Please install it manually.")

    # 3. Add Alias
    if platform.system() == "Windows":
        shells = ["powershell", "pwsh"]
        for shell in shells:
            try:
                # check if shell is available
                subprocess.call([shell, "-Command", "echo test"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except FileNotFoundError:
                continue

            try:
                profile_path = subprocess.check_output([shell, "-NoProfile", "-Command", "Write-Host $PROFILE"], text=True).strip()
            except subprocess.CalledProcessError:
                continue

            if not profile_path:
                continue
                
            if not os.path.exists(os.path.dirname(profile_path)):
                os.makedirs(os.path.dirname(profile_path))
            
            # Check if alias already exists to avoid duplicates
            already_in = False
            if os.path.exists(profile_path):
                with open(profile_path, "r") as f:
                    if f'function tt {{ python "{script_path}" $args }}' in f.read():
                        already_in = True
            
            if not already_in:
                with open(profile_path, "a") as f:
                    f.write(f'\nfunction tt {{ python "{script_path}" $args }}\n')
                print(f"✅ Alias 'tt' added to {shell} Profile: {profile_path}")
            else:
                print(f"ℹ️  Alias 'tt' already exists in {shell} Profile.")
        
    else: # Mac/Linux
        shell_config = os.path.join(home, ".zshrc") if "zsh" in os.environ.get("SHELL", "") else os.path.join(home, ".bashrc")
        with open(shell_config, "a") as f:
            f.write(f"\nalias tt='python3 {script_path}'\n")
        print(f"✅ Mac/Linux Alias 'tt' added to {shell_config}.")

    print("\n🎉 SETUP COMPLETE!")
    print("👉 Restart your terminal and type 'tt' to launch.")

if __name__ == "__main__":
    install()