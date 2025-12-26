import tkinter as tk
from tkinter import ttk, messagebox
from scheduler import Scheduler
from capture.typed_activity import start_key_listener, stop_key_listener
from logger_setup import log
from power_manager import prevent_sleep, allow_sleep
from alert_manager import trigger_alert_process
from auth import auth_service
from datetime import datetime

scheduler_thread = None

class DashboardFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        # Register/unregister for emergency state callbacks
        self._registered_for_emergency_callbacks = False
        
        self.grid_columnconfigure(0, weight=1)
        
        # Emergency Button Container Frame for better styling
        emergency_frame = tk.Frame(self, bg="#f0f0f0", relief="ridge", bd=2)
        emergency_frame.pack(fill="x", padx=20, pady=(20, 5))
        emergency_frame.grid_columnconfigure(0, weight=1)
        
        # Status label (shows if emergency is ON or OFF)
        self.lbl_emergency_status = ttk.Label(
            emergency_frame,
            text="Emergency Mode: OFF",
            font=("Arial", 10, "bold"),
            foreground="green"
        )
        self.lbl_emergency_status.pack(anchor="w", padx=10, pady=(5, 0))
        
        # Emergency Button - Enhanced styling for better visibility
        self.btn_emergency = tk.Button(
            emergency_frame, 
            text="🚨 TURN ON EMERGENCY 🚨",
            command=self.handle_emergency_press,
            font=("Arial", 20, "bold"),
            bg="#DC143C",  # Crimson red
            fg="white",
            activebackground="#B22222",  # Firebrick red when pressed
            activeforeground="white",
            relief="raised",
            bd=4,
            padx=40,
            pady=20,
            cursor="hand2",
            highlightthickness=2,
            highlightbackground="#8B0000",  # Dark red border
            highlightcolor="#FF0000"  # Red highlight when focused
        )
        self.btn_emergency.pack(fill="x", padx=5, pady=5)
        
        # Cancel Emergency Button (shown when emergency is active) - Make it more prominent
        self.btn_cancel_emergency = tk.Button(
            emergency_frame,
            text="🛑 TURN OFF EMERGENCY MODE 🛑",
            command=self.handle_cancel_emergency,
            font=("Arial", 18, "bold"),
            bg="#FF6B35",  # Orange-red for cancel
            fg="white",
            activebackground="#E55A2B",
            activeforeground="white",
            relief="raised",
            bd=4,
            padx=40,
            pady=18,
            cursor="hand2",
            highlightthickness=3,
            highlightbackground="#FFD700",
            highlightcolor="#FFD700"
        )
        # Initially hidden, shown when emergency is active
        self.btn_cancel_emergency.pack(fill="x", padx=5, pady=8)
        self.btn_cancel_emergency.pack_forget()  # Hide initially
        
        # Add help text below emergency button (in a separate row)
        self.help_text = ttk.Label(
            self, 
            text="Press button above or use Ctrl+Alt+E • Desktop shortcut requires 4-digit PIN (set in Settings) • Click Settings to configure emergency email and PIN",
            font=("Arial", 9),
            foreground="gray",
            wraplength=600
        )
        self.help_text.pack(pady=(0, 10), padx=20)
        
        # Add a visual separator after emergency button
        separator = ttk.Separator(self, orient="horizontal")
        separator.pack(fill="x", padx=20, pady=(0, 15))
        
        lbl_title = ttk.Label(self, text="eMonitor Dashboard", font=("Arial", 18))
        lbl_title.pack(pady=(0, 20))
        
        self.lbl_welcome = ttk.Label(self, text="Welcome, user!")
        self.lbl_welcome.pack(pady=5)
        
        self.lbl_plan_status = ttk.Label(self, text="Plan: Loading...", font=("Arial", 11, "bold"), foreground="gray")
        self.lbl_plan_status.pack(pady=(0, 10))

        self.lbl_status = ttk.Label(self, text="Status: Stopped", foreground="red", font=("Arial", 12))
        self.lbl_status.pack(pady=10)
        
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=20)
        
        self.btn_start = ttk.Button(btn_frame, text="Start Monitoring", command=self.start_monitoring)
        self.btn_start.pack(side="left", padx=10)
        
        self.btn_stop = ttk.Button(btn_frame, text="Stop Monitoring", command=self.stop_monitoring, state="disabled")
        self.btn_stop.pack(side="left", padx=10)
        
        nav_frame = ttk.Frame(self)
        nav_frame.pack(pady=30)
        
        # --- !! NEW "VIEW PLANS" BUTTON !! ---
        btn_plans = ttk.Button(nav_frame, text="View Subscription Plans", command=self.go_to_plans)
        btn_plans.pack(pady=5)
        
        btn_viewer = ttk.Button(nav_frame, text="View Decrypted Data", command=self.go_to_viewer)
        btn_viewer.pack(pady=5)
        
        btn_settings = ttk.Button(nav_frame, text="Settings", command=self.go_to_settings)
        btn_settings.pack(pady=5)
        
        btn_feedback = ttk.Button(nav_frame, text="Send Feedback / Report Issue", command=self.open_feedback_window)
        btn_feedback.pack(pady=10)
        
        btn_logout = ttk.Button(nav_frame, text="Logout", command=self.handle_logout)
        btn_logout.pack(pady=5)

    def open_feedback_window(self):
        from .feedback_ui import FeedbackWindow
        FeedbackWindow(self.controller)

    def go_to_viewer(self):
        from .data_viewer_ui import DataViewerFrame
        self.controller.show_frame(DataViewerFrame)

    def go_to_settings(self):
        from .settings_ui import SettingsFrame
        self.controller.show_frame(SettingsFrame)

    def go_to_plans(self):
        """Opens the new plans page"""
        from .plans_ui import PlansFrame
        self.controller.show_frame(PlansFrame)

    def handle_emergency_press(self):
        """Handle emergency button press"""
        from emergency_alert_manager import is_emergency_active, stop_emergency_mode
        
        # Check if emergency is already active
        if is_emergency_active():
            # Emergency is active - cancel button should be visible, but handle click anyway
            self.handle_cancel_emergency()
            return
        
        settings = self.controller.config.get_settings()
        emergency_settings = settings.get("emergency", {})
        
        if not emergency_settings.get("enabled", False):
            messagebox.showwarning("Emergency Alert Disabled", 
                                  "Emergency Alert feature is disabled. Please enable it in Settings.")
            return
        
        if not emergency_settings.get("data_sharing_consent", False):
            messagebox.showwarning("Consent Required", 
                                  "You must consent to data sharing in Emergency Alert settings before using this feature.")
            return
        
        trigger_alert_process(self.controller)
        # Immediately update button state to show emergency is ON
        self.after(100, self.update_emergency_button_state)
    
    def handle_cancel_emergency(self):
        """Handle cancel emergency button press"""
        from emergency_alert_manager import is_emergency_active, stop_emergency_mode
        from persistence import verify_pin
        from config import config_manager
        from tkinter import simpledialog

        if is_emergency_active():
            # Require PIN if configured, otherwise confirm
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
                # PIN verified - proceed
            else:
                result = messagebox.askyesno(
                    "Stop Emergency Mode?",
                    "No Emergency PIN is configured. Are you sure you want to stop emergency mode?",
                    icon="warning"
                )
                if not result:
                    return

            stop_emergency_mode()
            # Update button state immediately to show OFF status
            self.update_emergency_button_state()
            # Show info dialog with emphasized message
            messagebox.showinfo(
                "✓ Emergency Stopped", 
                "Emergency mode has been STOPPED successfully.\n\n"
                "• All data collection has stopped\n"
                "• Final data has been sent to emergency contacts\n"
                "• System is back to normal monitoring"
            )
    
    def update_emergency_button_state(self):
        """Update emergency button visibility based on emergency state"""
        from emergency_alert_manager import is_emergency_active
        
        try:
            emergency_active = is_emergency_active()
            
            if emergency_active:
                # Update status label
                self.lbl_emergency_status.config(text="Emergency Mode: ON", foreground="red")
                # Show cancel button, hide emergency button and help text
                self.btn_emergency.pack_forget()
                self.help_text.pack_forget()
                # Make sure cancel button is visible and prominent
                self.btn_cancel_emergency.pack(fill="x", padx=5, pady=8)
                self.btn_cancel_emergency.lift()
            else:
                # Update status label
                self.lbl_emergency_status.config(text="Emergency Mode: OFF", foreground="green")
                # Show emergency button and help text, hide cancel button
                self.btn_emergency.pack(fill="x", padx=5, pady=5)
                self.help_text.pack(fill="x", pady=(0, 10))
                self.btn_cancel_emergency.pack_forget()
        except Exception as e:
            log.error(f"Error updating emergency button state: {e}")
            import traceback
            log.error(traceback.format_exc())
            # On error, try to show cancel button anyway if emergency might be active
            try:
                self.btn_cancel_emergency.pack(fill="x", padx=5, pady=8)
            except:
                pass

    def _on_emergency_state_changed(self):
        try:
            # Ensure UI update runs on mainloop
            self.after(0, self.update_emergency_button_state)
        except Exception:
            pass
    
    def check_emergency_state(self):
        """Periodically check emergency state and update button visibility (only when state changes)"""
        try:
            from emergency_alert_manager import is_emergency_active
            emergency_active = is_emergency_active()
            
            # Only update if state has changed (avoid excessive logging)
            if not hasattr(self, '_last_emergency_state') or self._last_emergency_state != emergency_active:
                self._last_emergency_state = emergency_active
                log.debug(f"Dashboard: Emergency state changed - Active: {emergency_active}")
                self.update_emergency_button_state()
        except Exception as e:
            log.error(f"Error checking emergency state: {e}")
        
        # Check every 5 seconds instead of 2
        self.after(5000, self.check_emergency_state)

    def on_show(self):
        """Called when frame is shown. Updates welcome and plan status."""
        # Update emergency button state
        self.update_emergency_button_state()
        
        # Start periodic check for emergency state changes
        self.check_emergency_state()
        # Register for immediate emergency state notifications (only once)
        try:
            from emergency_alert_manager import register_state_change_callback
            if not self._registered_for_emergency_callbacks:
                register_state_change_callback(self._on_emergency_state_changed)
                self._registered_for_emergency_callbacks = True
                # Unregister when this frame is destroyed
                self.bind('<Destroy>', lambda e: __import__('emergency_alert_manager').unregister_state_change_callback(self._on_emergency_state_changed))
        except Exception:
            pass
        
        # Refresh subscription status to get latest plan info
        if self.controller.auth.current_user:
            log.info("Refreshing subscription status on dashboard...")
            self.controller.auth.get_subscription_status()
        
        user = self.controller.auth.current_user
        sub_data = self.controller.auth.subscription_data
        
        if user:
            self.lbl_welcome.config(text=f"Welcome, {user.email}")
        
        if sub_data:
            status = sub_data.get("status")
            plan_name = "N/A"
            if sub_data.get("plans"):
                plan_name = sub_data["plans"].get("name", "Unknown Plan")
            
            if status == 'trialing':
                try:
                    end_date_str = sub_data.get('trial_ends_at', '...').split('T')[0]
                    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
                    today = datetime.now().date()
                    days_left = (end_date.date() - today).days
                    
                    if days_left > 1:
                        self.lbl_plan_status.config(text=f"Trial Period - {days_left} days left", foreground="blue")
                    elif days_left == 1:
                        self.lbl_plan_status.config(text=f"Trial Period - 1 day left", foreground="orange")
                    else:
                        self.lbl_plan_status.config(text=f"Trial Period Expired", foreground="red")
                except Exception as e:
                     log.error(f"Error parsing trial date: {e}")
                     self.lbl_plan_status.config(text=f"Trial Period", foreground="blue")
            
            elif status == 'active':
                # Calculate days remaining for active subscription
                try:
                    subscription_ends_at = sub_data.get('subscription_ends_at')
                    if subscription_ends_at:
                        end_date = datetime.fromisoformat(subscription_ends_at.replace('Z', '+00:00'))
                        today = datetime.now(end_date.tzinfo)
                        days_remaining = (end_date.date() - today.date()).days
                        
                        if days_remaining > 0:
                            self.lbl_plan_status.config(text=f"Plan: {plan_name} (Active - {days_remaining} days remaining)", foreground="green")
                        elif days_remaining == 0:
                            self.lbl_plan_status.config(text=f"Plan: {plan_name} (Active - Expires today)", foreground="orange")
                        else:
                            self.lbl_plan_status.config(text=f"Plan: {plan_name} (Expired)", foreground="red")
                    else:
                        self.lbl_plan_status.config(text=f"Plan: {plan_name} (Active)", foreground="green")
                except Exception as e:
                    log.error(f"Error calculating days remaining: {e}")
                    self.lbl_plan_status.config(text=f"Plan: {plan_name} (Active)", foreground="green")
            
            else:
                self.lbl_plan_status.config(text=f"Plan: {plan_name} ({status.title()})", foreground="red")
        else:
            self.lbl_plan_status.config(text="Plan: Unknown (Could not load)", foreground="red")
        
        # Disable Start Monitoring if subscription is not active/trialing
        try:
            if sub_data is None or sub_data.get("status") not in ("active", "trialing"):
                self.btn_start.config(state="disabled")
            else:
                self.btn_start.config(state="normal")
        except Exception:
            self.btn_start.config(state="disabled")
        
    def start_monitoring(self):
        global scheduler_thread
        log.info("Start Monitoring button clicked.")
        # Check subscription status before starting monitoring
        try:
            sub_data = self.controller.auth.subscription_data
            if sub_data is None or sub_data.get("status") not in ("active", "trialing"):
                messagebox.showwarning("Subscription Required", "Your subscription is expired or inactive. Start Monitoring is disabled.")
                return
        except Exception:
            # If we can't determine subscription, be conservative and prevent start
            messagebox.showwarning("Subscription Check Failed", "Could not verify subscription status. Please try again later.")
            return
        settings = self.controller.config.get_settings()
        recipient = settings["user"]["recipient_email"]
        if not recipient:
            messagebox.showerror("Error", "Please set your Recipient Email in Settings first.")
            return
        # Clear cache and get fresh sender assignment
        # Use use_cache=False to ensure we get the latest sender (especially after fixing is_active check)
        self.controller.auth.clear_sender_cache()  # Clear any cached failures
        result = self.controller.auth.get_sender_assignment(use_cache=False)
        if not result.get("success"):
            error_msg = result.get("error", "Unknown error")
            log.error(f"Failed to get sender credentials: {error_msg}")
            messagebox.showerror(
                "SMTP Configuration Error", 
                f"Could not get sender credentials:\n{error_msg}\n\n"
                "Please ensure:\n"
                "1. At least one sender in sender_pool has is_active = true\n"
                "2. Or configure SMTP in Settings → SMTP section"
            )
            return
        if scheduler_thread is None or not scheduler_thread.is_alive():
            scheduler_thread = Scheduler()
            log.info("Created new Scheduler thread.")
            scheduler_thread.start()
        start_key_listener()
        if settings["user"].get("prevent_sleep_while_running", True):
            prevent_sleep()
        self.lbl_status.config(text="Status: Running", foreground="green")
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        log.info("Saving state: was_running = True")
        settings["user"]["was_running"] = True
        self.controller.config.update_settings(settings)
        
    def stop_monitoring(self):
        global scheduler_thread
        log.info("Stop Monitoring button clicked. Re-enabling system sleep.")
        allow_sleep()
        if scheduler_thread and scheduler_thread.is_alive():
            scheduler_thread.stop()
            log.info("Scheduler stopping...")
            scheduler_thread = None
        stop_key_listener()
        self.lbl_status.config(text="Status: Stopped", foreground="red")
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        log.info("Saving state: was_running = False")
        settings = self.controller.config.get_settings()
        settings["user"]["was_running"] = False
        self.controller.config.update_settings(settings)
        
    def handle_logout(self):
        from .login_ui import LoginFrame

        self.stop_monitoring()
        auth_service.sign_out()

        # PIN login removed — always go to Login screen
        self.controller.show_frame(LoginFrame)