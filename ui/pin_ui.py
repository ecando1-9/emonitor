import tkinter as tk
from tkinter import ttk, messagebox
from logger_setup import log
from auth import auth_service

class PinFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.mode = "login"
        
        self.grid_columnconfigure(0, weight=1)
        
        self.lbl_title = ttk.Label(self, text="Enter PIN", font=("Arial", 18))
        self.lbl_title.grid(row=0, column=0, pady=(20, 10))
        
        self.lbl_info = ttk.Label(self, text="Enter your 4-digit PIN to unlock.")
        self.lbl_info.grid(row=1, column=0, pady=5)
        
        self.entry_pin1 = ttk.Entry(self, width=20, show="*", font=("Arial", 14), justify="center")
        self.entry_pin1.grid(row=2, column=0, padx=50, pady=10)
        
        self.lbl_confirm = ttk.Label(self, text="Confirm new PIN:")
        self.entry_pin2 = ttk.Entry(self, width=20, show="*", font=("Arial", 14), justify="center")
        
        self.btn_submit = ttk.Button(self, text="Unlock", command=self.handle_submit)
        
        self.lbl_email_login = ttk.Label(self, text="Login with Email/Password instead?", foreground="blue", cursor="hand2")
        self.lbl_email_login.bind("<Button-1>", self.handle_full_logout)
        
        self.lbl_status = ttk.Label(self, text="", foreground="red")
        self.trigger_alert_on_login = False

    def set_emergency_mode(self):
        # Emergency mode removed; do not trigger alerts from PIN screen
        log.info("PIN screen: emergency mode ignored (feature removed).")
        self.lbl_status.config(text="")

    def on_show(self, setup_mode=False):
        """Called when the frame is shown."""
        self.lbl_status.config(text="")
        self.entry_pin1.delete(0, tk.END)
        self.entry_pin2.delete(0, tk.END)
        
        if setup_mode:
            self.mode = "setup"
            self.lbl_title.config(text="Create Your PIN")
            self.lbl_info.config(text="Create a 4-digit PIN for quick login.")
            self.btn_submit.config(text="Set PIN")
            self.lbl_confirm.grid(row=3, column=0, pady=(10, 0))
            self.entry_pin2.grid(row=4, column=0, padx=50, pady=10)
            self.btn_submit.grid(row=5, column=0, pady=20)
            self.lbl_email_login.grid(row=6, column=0, pady=(10, 5))
            self.lbl_status.grid(row=7, column=0, pady=10)
        else:
            self.mode = "login"
            self.lbl_title.config(text="Enter PIN")
            self.lbl_info.config(text="Enter your 4-digit PIN to unlock.")
            self.btn_submit.config(text="Unlock")
            self.lbl_confirm.grid_forget()
            self.entry_pin2.grid_forget()
            self.btn_submit.grid(row=4, column=0, pady=20)
            self.lbl_email_login.grid(row=5, column=0, pady=(10, 5))
            self.lbl_status.grid(row=6, column=0, pady=10)
            
        self.entry_pin1.focus()

    def handle_submit(self):
        """Handles both setting a new PIN and logging in."""
        from .dashboard_ui import DashboardFrame
        from .subscription_ui import SubscriptionFrame
        
        pin1 = self.entry_pin1.get()
        
        if self.mode == "setup":
            pin2 = self.entry_pin2.get()
            if len(pin1) < 4:
                self.lbl_status.config(text="PIN must be at least 4 digits.")
                return
            if pin1 != pin2:
                self.lbl_status.config(text="PINs do not match.")
                return
            
            auth_service.set_new_pin(pin1)
            log.info("New PIN set successfully.")
            self.lbl_status.config(text="")
            
            if auth_service.session:
                auth_service.save_full_login_session(auth_service.session.refresh_token)
            
            self.controller.post_login_setup()
            self.controller.show_frame(DashboardFrame)
            
        else: # self.mode == "login"
            if not pin1:
                self.lbl_status.config(text="Please enter your PIN.")
                return
                
            self.lbl_status.config(text="Verifying...", foreground="blue")
            self.update_idletasks()
            
            success, message, sub_data = auth_service.login_with_token_and_pin(pin1)
            
            if success:
                log.info("PIN login successful.")
                self.lbl_status.config(text="")
                
                # --- !! THIS IS THE FIX for the 'NoneType' error !! ---
                if sub_data is None:
                    log.error("CRITICAL: Login succeeded but no subscription data was returned.")
                    self.lbl_status.config(text="Login Failed: Could not load user subscription.", foreground="red")
                    self.handle_full_logout() # Force full logout
                    return
                
                status = sub_data.get("status")
                if status == 'active' or status == 'trialing':
                    self.controller.post_login_setup()
                    self.controller.show_frame(DashboardFrame)
                else:
                    log.warning(f"Login blocked. User status is: {status}")
                    self.controller.show_frame(SubscriptionFrame, sub_data=sub_data)

                # Emergency-trigger-on-login disabled
            else:
                log.warning(f"PIN login failed: {message}")
                self.lbl_status.config(text=message, foreground="red")
                if "expired" in message:
                    self.handle_full_logout()

    def handle_full_logout(self, event=None):
        """Logs the user out completely and shows the login screen."""
        from .login_ui import LoginFrame
        
        log.info("User clicked 'Login with Email'. Forcing full logout.")
        auth_service.full_logout() # This clears the token and PIN
        self.controller.show_frame(LoginFrame)