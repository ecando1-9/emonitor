import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import time

class EmergencyStatusWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("*** EMERGENCY MODE ACTIVE ***")
        
        # 1. Force the window to be an independent "top-level"
        self.attributes('-topmost', True)
        self.withdraw()  # Hide while we calculate size
        
        # 2. Styling
        self.configure(bg="#8B0000")
        
        # 3. Create UI first so it has a "size"
        self.main_frame = tk.Frame(self, bg="#8B0000")
        self.main_frame.pack(fill="both", expand=True)
        
        self.label = tk.Label(
            self.main_frame, 
            text="*** EMERGENCY MODE ACTIVE ***", 
            font=("Arial", 25, "bold"),
            fg="white", bg="#8B0000"
        )
        self.label.pack(expand=True)

        self.stop_btn = tk.Button(
            self.main_frame,
            text="STOP EMERGENCY MODE",
            font=("Arial", 20, "bold"),
            bg="#FF6B35", fg="white",
            command=self.stop_emergency,
            pady=20
        )
        self.stop_btn.pack(pady=50, padx=100, fill="x")

        # Grace period label
        self.grace_seconds = 30
        self.grace_label = tk.Label(self.main_frame, text=f"Grace period: {self.grace_seconds}s", font=("Arial", 14, "bold"), fg="#FFD700", bg="#8B0000")
        self.grace_label.pack()
        self.update_grace_period()

        # 4. Trigger the maximization after a 100ms delay
        # This solves the "stuck at small size" issue
        self.after(100, self.force_maximize)

    def force_maximize(self):
        """Forces the window to the monitor's full resolution."""
        try:
            # Get screen width and height
            screen_w = self.winfo_screenwidth()
            screen_h = self.winfo_screenheight()
            
            # Force the window size to the screen size
            self.geometry(f"{screen_w}x{screen_h}+0+0")
            
            # Try to set the OS state to zoomed as well
            try:
                self.state('zoomed')
            except:
                self.attributes('-zoomed', True)
            
            # Windows fallback using ctypes to force maximize (helps in some environments)
            try:
                import ctypes
                SW_MAXIMIZE = 3
                hwnd = int(self.winfo_id())
                if hwnd:
                    ctypes.windll.user32.ShowWindow(hwnd, SW_MAXIMIZE)
                    try:
                        ctypes.windll.user32.SetForegroundWindow(hwnd)
                    except Exception:
                        pass
            except Exception:
                pass
            
            self.deiconify() # Now show it
            self.lift()
            self.focus_force()
        except Exception as e:
            print(f"Maximize error: {e}")
            self.deiconify()

    def stop_emergency(self):
        # Prompt for PIN (4 digits) before stopping emergency
        try:
            from persistence import verify_pin
            from config import config_manager
            from tkinter import messagebox

            settings = config_manager.get_settings()
            emergency_cfg = settings.get('emergency', {})
            salt = emergency_cfg.get('emergency_shortcut_pin_salt')
            hashed = emergency_cfg.get('emergency_shortcut_pin_hash')

            if salt and hashed:
                pin = simpledialog.askstring("Confirm PIN", "Enter Emergency PIN to stop emergency:", show='*', parent=self)
                if not pin:
                    messagebox.showinfo("Cancelled", "Emergency stop cancelled.", parent=self)
                    return
                if not (pin.isdigit() and len(pin) == 4):
                    messagebox.showerror("Invalid PIN", "PIN must be exactly 4 digits.", parent=self)
                    return
                if not verify_pin(pin, salt, hashed):
                    messagebox.showerror("Incorrect PIN", "The PIN entered is incorrect.", parent=self)
                    return
            else:
                # No PIN configured - ask for confirmation
                if not messagebox.askyesno("Stop Emergency", "No Emergency PIN configured. Stop emergency?", parent=self):
                    return

            from emergency_alert_manager import stop_emergency_mode
            try:
                log.info("EmergencyStatusWindow: calling stop_emergency_mode()")
                stop_emergency_mode()
                log.info("EmergencyStatusWindow: stop_emergency_mode() returned")
            except Exception as stop_err:
                log.error(f"EmergencyStatusWindow: error calling stop_emergency_mode: {stop_err}")
                try:
                    messagebox.showerror("Error", f"Failed to stop emergency: {stop_err}", parent=self)
                except Exception:
                    pass
            try:
                self.destroy()
            except Exception:
                pass
        except Exception as e:
            try:
                messagebox.showerror("Error", f"Failed to stop emergency: {e}", parent=self)
            except Exception:
                pass

    def on_close(self):
        # Disable closing via the X button while emergency is active
        try:
            messagebox.showwarning("Emergency Active", "Emergency mode is active. Use the STOP button to stop emergency.", parent=self)
        except Exception:
            pass

    def update_grace_period(self):
        try:
            if self.grace_seconds > 0:
                self.grace_label.config(text=f"Grace period: {self.grace_seconds}s")
                self.grace_seconds -= 1
                self.after(1000, self.update_grace_period)
            else:
                self.grace_label.config(text="Grace period ended")
        except Exception:
            pass


# Global reference to the status window
_emergency_status_window = None

def show_emergency_status_window(parent):
    """Always create a fresh EmergencyStatusWindow and show it."""
    global _emergency_status_window
    try:
        # Destroy any existing window to ensure fresh UI
        if _emergency_status_window and _emergency_status_window.winfo_exists():
            try:
                _emergency_status_window.destroy()
            except Exception:
                pass
            _emergency_status_window = None

        _emergency_status_window = EmergencyStatusWindow(parent)
        _emergency_status_window.protocol('WM_DELETE_WINDOW', _emergency_status_window.on_close)
        return _emergency_status_window
    except Exception as e:
        print(f"Error showing emergency status window: {e}")


def close_emergency_status_window():
    global _emergency_status_window
    try:
        if _emergency_status_window and _emergency_status_window.winfo_exists():
            _emergency_status_window.destroy()
            _emergency_status_window = None
    except Exception as e:
        print(f"Error closing emergency status window: {e}")