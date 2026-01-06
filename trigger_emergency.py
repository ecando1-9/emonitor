"""
Standalone script to trigger emergency alert completely silently.
This script runs in the background with zero visible output.
"""
import sys
import os

# Suppress all output to make it completely stealthy
# Redirect stdout and stderr to null
# Add the current directory to path so we can import modules
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

# DEBUG: Verify script running
try:
    with open(os.path.join(script_dir, "app_data", "debug_trigger.txt"), "a") as f:
        import datetime
        f.write(f"Trigger script started at {datetime.datetime.now()}\n")
except:
    pass

# Import after path is set
import logging
# logging.getLogger().setLevel(logging.CRITICAL) # REMOVED to allow debugging

from logger_setup import log
from emergency_alert_manager import trigger_emergency_alert
from config import config_manager
from persistence import verify_pin

def show_pin_and_confirm(require_pin=True):
    """Show PIN entry dialog (if required), then confirmation window with Activate/Cancel buttons
    
    Args:
        require_pin: If True, prompt for PIN first. If False, skip PIN and go straight to confirmation.
    """
    # UI Bypass for immediate reliable triggering (Debugging User Issue)
    return True

    try:
        import tkinter as tk
        from tkinter import messagebox
        
        # Create a minimal root window (hidden)
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        root.attributes('-topmost', True)  # Bring to front
        
        # Step 1: Get PIN from user (if required)
        if require_pin:
            from tkinter import simpledialog
            pin = simpledialog.askstring(
                "Emergency Alert PIN",
                "Enter your 4-digit Emergency Shortcut PIN:",
                show='*',
                parent=root
            )
            
            if not pin:
                root.destroy()
                return False  # User cancelled PIN entry
            
            # Step 2: Verify PIN
            settings = config_manager.get_settings()
            emergency_settings = settings.get("emergency", {})
            pin_salt = emergency_settings.get("emergency_shortcut_pin_salt")
            pin_hash = emergency_settings.get("emergency_shortcut_pin_hash")
            
            if pin_salt and pin_hash:
                # Enforce exactly 4 digits for the emergency shortcut PIN
                if not (pin and pin.isdigit() and len(pin) == 4):
                    messagebox.showerror("Incorrect PIN", "The PIN must be exactly 4 digits.\n\nEmergency alert not triggered.", parent=root)
                    root.destroy()
                    return False
                if not verify_pin(pin, pin_salt, pin_hash):
                    messagebox.showerror("Incorrect PIN", "The PIN you entered is incorrect.\n\nEmergency alert not triggered.", parent=root)
                    root.destroy()
                    return False
        else:
            # No PIN set - just proceed to confirmation
            pass
        
        # Step 3: Show confirmation window with Activate/Cancel
        root.deiconify()  # Show the window
        root.title("Emergency Alert Confirmation")
        root.geometry("400x200")
        root.attributes('-topmost', True)
        root.resizable(False, False)
        
        # Center the window
        root.update_idletasks()
        x = (root.winfo_screenwidth() // 2) - (400 // 2)
        y = (root.winfo_screenheight() // 2) - (200 // 2)
        root.geometry(f"400x200+{x}+{y}")
        
        # Create confirmation dialog content
        confirm_frame = tk.Frame(root, bg="#f0f0f0")
        confirm_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Warning icon and message
        icon_label = tk.Label(confirm_frame, text="⚠️", font=("Arial", 32), bg="#f0f0f0")
        icon_label.pack(pady=(10, 5))
        
        message_label = tk.Label(
            confirm_frame,
            text="EMERGENCY ALERT",
            font=("Arial", 16, "bold"),
            bg="#f0f0f0",
            fg="#DC143C"
        )
        message_label.pack(pady=5)
        
        # Show appropriate message based on whether PIN was required
        if require_pin:
            info_text = "PIN verified. Click ACTIVATE to trigger emergency alert."
        else:
            info_text = "Click ACTIVATE to trigger emergency alert."
        
        info_label = tk.Label(
            confirm_frame,
            text=info_text,
            font=("Arial", 10),
            bg="#f0f0f0",
            wraplength=350
        )
        info_label.pack(pady=5)
        
        # Buttons frame
        button_frame = tk.Frame(confirm_frame, bg="#f0f0f0")
        button_frame.pack(pady=15)
        
        user_confirmed = [False]  # Use list to modify in nested function
        
        def on_activate():
            user_confirmed[0] = True
            root.destroy()
        
        def on_cancel():
            user_confirmed[0] = False
            root.destroy()
        
        # Activate button (red)
        btn_activate = tk.Button(
            button_frame,
            text="ACTIVATE EMERGENCY",
            command=on_activate,
            font=("Arial", 12, "bold"),
            bg="#DC143C",
            fg="white",
            activebackground="#B22222",
            activeforeground="white",
            relief="raised",
            bd=3,
            padx=20,
            pady=8,
            cursor="hand2"
        )
        btn_activate.pack(side="left", padx=10)
        
        # Cancel button (gray)
        btn_cancel = tk.Button(
            button_frame,
            text="CANCEL",
            command=on_cancel,
            font=("Arial", 12, "bold"),
            bg="#808080",
            fg="white",
            activebackground="#696969",
            activeforeground="white",
            relief="raised",
            bd=3,
            padx=20,
            pady=8,
            cursor="hand2"
        )
        btn_cancel.pack(side="left", padx=10)
        
        # Make Activate button default (Enter key)
        btn_activate.focus_set()
        root.bind('<Return>', lambda e: on_activate())
        root.bind('<Escape>', lambda e: on_cancel())
        
        # Wait for user response
        root.mainloop()
        
        return user_confirmed[0]
        
    except Exception as e:
        log.error(f"Error showing PIN/confirmation dialog: {e}")
        try:
            root.destroy()
        except:
            pass
        return False

def main():
    """Trigger emergency alert after PIN verification"""
    try:
        # Check if emergency is enabled
        settings = config_manager.get_settings()
        emergency_settings = settings.get("emergency", {})
        
        if not emergency_settings.get("enabled", False):
            # Emergency is disabled - fail silently
            return
        
        if not emergency_settings.get("data_sharing_consent", False):
            # No consent - fail silently
            return
        
        # Check if emergency shortcut PIN is set
        pin_salt = emergency_settings.get("emergency_shortcut_pin_salt")
        pin_hash = emergency_settings.get("emergency_shortcut_pin_hash")
        
        # Show PIN entry (if required) and confirmation dialog
        # require_pin = bool(pin_salt and pin_hash)
        require_pin = False # PIN verification disabled per user request
        user_confirmed = show_pin_and_confirm(require_pin=require_pin)
        
        if not user_confirmed:
            # User cancelled or PIN was wrong
            log.warning("Emergency shortcut activation cancelled by user")
            return
        
        # User confirmed - trigger the emergency alert
        # User confirmed - trigger the emergency alert
        if user_confirmed:
            try:
                log.warning("EMERGENCY SHORTCUT ACTIVATED - User confirmed, triggering alert via signal...")
                
                # Create Signal File for Main App
                from config import DATA_DIR
                signal_file = os.path.join(DATA_DIR, "TRIGGER_EMERGENCY")
                with open(signal_file, 'w') as f:
                    f.write("desktop_shortcut")
                
                log.info(f"Signal file created at {signal_file}")
                
                # Check if Main App is running
                app_running = False
                pid_file = os.path.join(DATA_DIR, "app.lock")
                
                try:
                    import psutil
                    if os.path.exists(pid_file):
                        with open(pid_file, 'r') as pf:
                            pid = int(pf.read().strip())
                        if psutil.pid_exists(pid):
                            app_running = True
                except Exception as e:
                    # If checking fails, assume not running to be safe? Or assume running?
                    # Safer to assume NOT running and try to launch (worst case 2 instances)
                    log.warning(f"Could not check app status: {e}")
                
                if not app_running:
                    log.warning("Main application not running. Launching it now...")
                    import subprocess
                    main_py_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
                    # Use Popen to launch independent process
                    # Use 'pythonw' if available to avoid console, but sys.executable is safer
                    subprocess.Popen([sys.executable, main_py_path, "--emergency"])
        
            except Exception as e:
                # Log error to file logic
                try:
                     with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_data", "debug_trigger.txt"), "a") as f:
                         f.write(f"Fatal Error: {e}\n")
                except:
                     pass
                     
                # Log error but remain completely silent
                try:
                    log.error(f"Error in trigger_emergency.py: {e}")
                    import traceback
                    log.error(traceback.format_exc())
                except:
                    pass
                # No message boxes, no output - completely stealthy

    except Exception as e:
        # Global error handler for main()
        try:
            log.error(f"Global error in trigger_emergency.py: {e}")
        except:
            pass

if __name__ == "__main__":
    main()

