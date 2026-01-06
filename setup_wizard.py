import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import os
import sys
import subprocess
import threading
import time

class SetupWizard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("eMonitor Setup Wizard")
        self.geometry("600x450")
        self.resizable(False, False)
        
        # Variables
        self.var_create_shortcut = tk.BooleanVar(value=True)
        self.var_install_deps = tk.BooleanVar(value=True)
        
        # UI
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # Header
        ttk.Label(main_frame, text="eMonitor Installation", font=("Arial", 16, "bold")).pack(pady=(0, 10))
        ttk.Label(main_frame, text="This wizard will set up eMonitor on this computer.", font=("Arial", 10)).pack(pady=(0, 20))
        
        # Options
        options_frame = ttk.LabelFrame(main_frame, text="Installation Options", padding=10)
        options_frame.pack(fill="x", pady=10)
        
        ttk.Checkbutton(options_frame, text="Install/Update Dependencies (requirements.txt)", variable=self.var_install_deps).pack(anchor="w", pady=5)
        ttk.Checkbutton(options_frame, text="Create 'Emergency Alert' Desktop Shortcut", variable=self.var_create_shortcut).pack(anchor="w", pady=5)
        
        # Log Area
        ttk.Label(main_frame, text="Installation Log:").pack(anchor="w", pady=(10, 0))
        self.log_text = scrolledtext.ScrolledText(main_frame, height=10, state="disabled", font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True, pady=5)
        
        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=10)
        
        self.btn_install = ttk.Button(btn_frame, text="Start Installation", command=self.start_installation)
        self.btn_install.pack(side="right")
        
    def log(self, message):
        self.log_text.config(state="normal")
        self.log_text.insert("end", f"{message}\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")
        self.update_idletasks()

    def start_installation(self):
        self.btn_install.config(state="disabled")
        threading.Thread(target=self.run_install, daemon=True).start()

    def run_install(self):
        try:
            total_steps = 0
            if self.var_install_deps.get(): total_steps += 1
            if self.var_create_shortcut.get(): total_steps += 1
            
            self.log("=== Starting Installation ===")
            
            current_dir = os.path.dirname(os.path.abspath(__file__))
            
            # Step 1: Dependencies
            if self.var_install_deps.get():
                self.log("Installing dependencies...")
                req_file = os.path.join(current_dir, "requirements.txt")
                if os.path.exists(req_file):
                    try:
                        # Use valid python executable
                        python_exe = sys.executable
                        cmd = [python_exe, "-m", "pip", "install", "-r", req_file]
                        
                        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                        while True:
                            output = process.stdout.readline()
                            if output == '' and process.poll() is not None:
                                break
                            if output:
                                self.log(output.strip())
                        
                        if process.returncode == 0:
                            self.log("Dependencies installed successfully.")
                        else:
                            self.log(f"Error installing dependencies. Code: {process.returncode}")
                    except Exception as e:
                        self.log(f"Failed to install dependencies: {e}")
                else:
                    self.log("requirements.txt not found. Skipping.")
            
            # Step 2: Shortcut
            if self.var_create_shortcut.get():
                self.log("Creating Desktop Shortcut...")
                try:
                    target_script = os.path.join(current_dir, "start_emergency_alert.vbs")
                    icon_path = os.path.join(current_dir, "icon.ico")
                    if not os.path.exists(icon_path):
                        # Fallback to python exe icon or shell32
                        icon_path = "shell32.dll,21" 
                    
                    desktop = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')
                    shortcut_path = os.path.join(desktop, "Emergency Alert.lnk")
                    
                    self.create_shortcut_vbs(target_script, shortcut_path, icon_path)
                    self.log(f"Shortcut created at: {shortcut_path}")
                except Exception as e:
                    self.log(f"Failed to create shortcut: {e}")
            
            self.log("=== Installation Complete ===")
            messagebox.showinfo("Success", "Installation completed successfully!")
            self.btn_install.config(state="normal", text="Close", command=self.destroy)
            
        except Exception as e:
            self.log(f"Critical Error: {e}")
            messagebox.showerror("Error", f"Installation failed: {e}")
            self.btn_install.config(state="normal")

    def create_shortcut_vbs(self, target, shortcut_path, icon_path):
        vbs_content = f'''
        Set oWS = WScript.CreateObject("WScript.Shell")
        sLinkFile = "{shortcut_path}"
        Set oLink = oWS.CreateShortcut(sLinkFile)
        oLink.TargetPath = "{target}"
        oLink.IconLocation = "{icon_path}"
        oLink.WorkingDirectory = "{os.path.dirname(target)}"
        oLink.Save
        '''
        vbs_temp = os.path.join(os.environ['TEMP'], "create_shortcut.vbs")
        with open(vbs_temp, "w") as f:
            f.write(vbs_content)
        
        subprocess.run(["cscript", "//Nologo", vbs_temp], check=True)
        os.remove(vbs_temp)

if __name__ == "__main__":
    app = SetupWizard()
    app.mainloop()
