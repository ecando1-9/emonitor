import tkinter as tk
from tkinter import ttk, messagebox
from logger_setup import log
from auth import auth_service

class LoginFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.trigger_alert_on_login = False
        
        self.grid_columnconfigure(0, weight=1)
        
        lbl_title = ttk.Label(self, text="eMonitor Login", font=("Arial", 18))
        lbl_title.grid(row=0, column=0, pady=20)
        
        lbl_email = ttk.Label(self, text="Email:")
        lbl_email.grid(row=1, column=0, sticky="w", padx=50)
        self.entry_email = ttk.Entry(self, width=40)
        self.entry_email.grid(row=2, column=0, padx=50, pady=5)
        
        lbl_pass = ttk.Label(self, text="Password:")
        lbl_pass.grid(row=3, column=0, sticky="w", padx=50)
        self.entry_pass = ttk.Entry(self, width=40, show="*")
        self.entry_pass.grid(row=4, column=0, padx=50, pady=5)
        
        # --- Remember Me Checkbox ---
        self.var_remember = tk.BooleanVar()
        self.chk_remember = ttk.Checkbutton(self, text="Remember my credentials", variable=self.var_remember)
        self.chk_remember.grid(row=5, column=0, pady=5)
        # ----------------------------
        
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=6, column=0, pady=20)
        
        btn_login = ttk.Button(btn_frame, text="Login", command=self.handle_login)
        btn_login.pack(side="left", padx=10)
        
        btn_signup = ttk.Button(btn_frame, text="Sign Up", command=self.handle_signup)
        btn_signup.pack(side="left", padx=10)
        
        self.lbl_status = ttk.Label(self, text="", foreground="red")
        self.lbl_status.grid(row=7, column=0, pady=10)
        
        # PIN login removed; no shortcut to PIN screen
        
        self.lbl_forgot = ttk.Label(self, text="Forgot Password?", foreground="blue", cursor="hand2")
        self.lbl_forgot.grid(row=9, column=0, pady=5)
        self.lbl_forgot.bind("<Button-1>", self.handle_forgot_password)
        
        # Load saved credentials if any
        self.load_saved_credentials()

    def set_status_message(self, message, color):
        self.lbl_status.config(text=message, foreground=color)

    def set_emergency_mode(self):
        # Emergency mode removed; do not trigger alerts on login
        self.lbl_status.config(text="", foreground="red")

    def check_emergency_auto_login(self):
        """If started in emergency mode and credentials exist, auto-login"""
        if getattr(self.controller, 'start_in_emergency_mode', False):
            if self.entry_email.get() and self.entry_pass.get():
                log.info("Emergency Mode: Auto-logging in via saved credentials...")
                self.handle_login()
        
    def load_saved_credentials(self):
        try:
            from config import config_manager
            import base64
            
            settings = config_manager.get_settings()
            saved = settings.get("saved_credentials", {})
            
            if saved.get("remember", False):
                email = saved.get("email", "")
                enc_pass = saved.get("password_b64", "")
                
                if email:
                    self.entry_email.delete(0, tk.END)
                    self.entry_email.insert(0, email)
                    self.var_remember.set(True)
                
                if enc_pass:
                    try:
                        password = base64.b64decode(enc_pass).decode("utf-8")
                        self.entry_pass.delete(0, tk.END)
                        self.entry_pass.insert(0, password)
                    except:
                        pass
            
            # Check for auto-login after loading
            self.after(500, self.check_emergency_auto_login)
            
        except Exception as e:
            log.warning(f"Failed to load saved credentials: {e}")

    def save_credentials(self, email, password):
        try:
            from config import config_manager
            import base64
            
            settings = config_manager.get_settings()
            
            if self.var_remember.get():
                pass_b64 = base64.b64encode(password.encode("utf-8")).decode("utf-8")
                settings["saved_credentials"] = {
                    "remember": True,
                    "email": email,
                    "password_b64": pass_b64
                }
            else:
                settings["saved_credentials"] = {
                    "remember": False,
                    "email": "",
                    "password_b64": ""
                }
            
            config_manager.save_settings()
        except Exception as e:
            log.error(f"Failed to save credentials: {e}")

    def handle_forgot_password(self, event=None):
        email = self.entry_email.get()
        if not email:
            messagebox.showwarning("Email Needed", "Please enter your email address in the email field first.")
            return
        self.lbl_status.config(text="Sending reset link...", foreground="blue")
        self.update_idletasks()
        result = self.controller.auth.send_password_reset_email(email)
        if result.get("success"):
            self.lbl_status.config(text="")
            messagebox.showinfo("Check Your Email", "A password reset link has been sent.")
        else:
            raw_error = str(result.get('error', 'Unknown error'))
            log.error(f"Password reset failed: {raw_error}")
            
            if "security purposes" in raw_error and "seconds" in raw_error:
                # Extract seconds using regex or simple split
                try:
                    import re
                    match = re.search(r"after (\d+) seconds", raw_error)
                    seconds = match.group(1) if match else "a few"
                    messagebox.showwarning("Wait a moment", f"Please wait {seconds} seconds before requesting another email.")
                    self.lbl_status.config(text=f"Please wait {seconds}s...", foreground="orange")
                except:
                    messagebox.showwarning("Too Fast", "Please wait a minute before requesting another email.")
            else:
                self.lbl_status.config(text="Error sending reset link.", foreground="red")

    def handle_login(self):
        from .dashboard_ui import DashboardFrame
        from .subscription_ui import SubscriptionFrame # <-- Import
        
        email = self.entry_email.get()
        password = self.entry_pass.get()

        if not email or not password:
            self.lbl_status.config(text="Email and Password cannot be empty.", foreground="red")
            return
            
        self.lbl_status.config(text="Logging in...", foreground="blue")
        self.update_idletasks()
        
        result = auth_service.sign_in(email, password)
        
        if result.get("success"):
            self.lbl_status.config(text="")
            
            # Save credentials if checked
            self.save_credentials(email, password)
            
            sub_data = result.get("subscription")
            
            # --- !! THIS IS THE FIX for the 'NoneType' error !! ---
            if sub_data is None:
                log.error("CRITICAL: Login succeeded but no subscription data was returned. This might be a database trigger issue.")
                self.lbl_status.config(text="Login Failed: Could not load user subscription.", foreground="red")
                auth_service.full_logout() # Log them out
                return
            
            status = sub_data.get("status")
            
            if status == 'active' or status == 'trialing':
                self.controller.post_login_setup()
                # PIN-login option removed: always show dashboard after successful login
                self.controller.show_frame(DashboardFrame)
            else:
                log.warning(f"Login blocked. User status is: {status}")
                self.controller.show_frame(SubscriptionFrame, sub_data=sub_data)

            # Emergency trigger disabled
        else:
            raw_error = str(result.get('error', 'Unknown error'))
            log.error(f"Login failed: {raw_error}")
            self.lbl_status.config(text="Login Failed: Invalid email or password.", foreground="red")

    def handle_signup(self):
        from .dashboard_ui import DashboardFrame
        
        email = self.entry_email.get()
        password = self.entry_pass.get()

        if not email or not password:
            self.lbl_status.config(text="Email and Password cannot be empty.", foreground="red")
            return
        if len(password) < 6:
            self.lbl_status.config(text="Password must be at least 6 characters.", foreground="red")
            return
            
        self.lbl_status.config(text="Signing up and checking device...", foreground="blue")
        self.update_idletasks()

        result = auth_service.sign_up(email, password)
        
        if result.get("success"):
            self.lbl_status.config(text="")
            log.info("Sign up and auto-login successful.")
            messagebox.showinfo("Sign Up Successful", "Account created! You are now logged in.")
            
            self.controller.post_login_setup()
            
            # --- !! NEW SUBSCRIPTION CHECK !! ---
            sub_data = result.get("subscription")
            if sub_data is None:
                log.error("CRITICAL: Signup succeeded but no subscription data was returned.")
                self.lbl_status.config(text="Signup Failed: Could not create user subscription.", foreground="red")
                auth_service.full_logout() # Log them out
                return
            status = sub_data.get("status")
            if status == 'trialing' or status == 'active':
                self.controller.show_frame(DashboardFrame)
            else:
                from .subscription_ui import SubscriptionFrame
                log.error(f"Signup user has bad status: {status}")
                self.controller.show_frame(SubscriptionFrame, sub_data=sub_data)

            # Emergency trigger disabled
        else:
            raw_error = str(result.get('error', 'Unknown error'))
            log.error(f"Sign up failed: {raw_error}")
            user_message = "Sign Up Failed. An unknown error occurred."
            if "Trial limit reached" in raw_error:
                user_message = "Sign Up Failed: Trial limit reached for this device."
            elif "User already exists" in raw_error:
                user_message = "Sign Up Failed: An account with this email already exists."
            self.lbl_status.config(text=user_message, foreground="red")