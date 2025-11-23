import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
from logger_setup import log

class SubscriptionFrame(tk.Frame):
    """
    This frame is a "wall" shown when a user's trial or
    subscription has expired.
    """
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        self.grid_columnconfigure(0, weight=1)
        
        lbl_title = ttk.Label(self, text="Subscription Expired", font=("Arial", 18, "bold"), foreground="red")
        lbl_title.grid(row=0, column=0, pady=(20, 10))
        
        self.lbl_info = ttk.Label(self, 
            text="Your 7-day free trial has ended.\n\n"
                 "Please upgrade to a paid plan to continue using eMonitor.",
            justify="center",
            font=("Arial", 12))
        self.lbl_info.grid(row=1, column=0, pady=15, padx=20)
        
        # --- Plans Frame ---
        plans_frame = ttk.Frame(self)
        plans_frame.grid(row=2, column=0, pady=20)
        
        # This button will now open the full plans page
        btn_view_plans = ttk.Button(plans_frame, text="View Plans & Upgrade", command=self.go_to_plans)
        btn_view_plans.pack(pady=10)
        
        # --- Button Frame ---
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=3, column=0, pady=20)
        
        btn_logout = ttk.Button(btn_frame, text="Logout", command=self.handle_logout)
        btn_logout.pack(side="left", padx=10)
        
        self.lbl_status = ttk.Label(self, text="", foreground="red")
        self.lbl_status.grid(row=4, column=0, pady=10)
        
    def on_show(self, sub_data=None):
        """Called when the frame is shown. Updates text based on status."""
        log.info(f"Showing subscription wall. Status: {sub_data.get('status') if sub_data else 'Unknown'}")
        if sub_data and sub_data.get('status') == 'trialing':
            trial_end_str = sub_data.get('trial_ends_at', 'N/A').split('T')[0]
            self.lbl_info.config(text=f"Your 7-day free trial has expired.\nTrial ended on: {trial_end_str}")
        elif sub_data and sub_data.get('status') == 'expired':
            self.lbl_info.config(text="Your paid subscription has expired.\n\nPlease renew your plan to continue.")
        elif sub_data and sub_data.get('status') == 'past_due':
            self.lbl_info.config(text="Your last payment failed.\n\nPlease update your payment method to continue.")
        else:
            # Default message
            self.lbl_info.config(text="Your access has expired.\n\nPlease upgrade to a paid plan to continue.")
        
    def go_to_plans(self):
        """Opens the new plans page"""
        from .plans_ui import PlansFrame
        self.controller.show_frame(PlansFrame)

    def handle_logout(self):
        """Logs the user out completely and shows the login screen."""
        from .login_ui import LoginFrame
        log.info("User logged out from subscription page.")
        self.controller.auth.full_logout() # Use full_logout to clear PIN
        self.controller.show_frame(LoginFrame)