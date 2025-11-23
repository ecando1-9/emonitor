import tkinter as tk
from tkinter import ttk, messagebox
from logger_setup import log
from auth import auth_service
import webbrowser
from datetime import datetime

# --- !! YOUR GOOGLE FORM LINK !! ---
YOUR_PAYMENT_LINK = "https://emonitor-tau.vercel.app/"

class PlansFrame(tk.Frame):
    """
    This frame shows the user all available plans, their current plan,
    and a button to upgrade.
    """
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        self.grid_columnconfigure(0, weight=1)
        
        lbl_title = ttk.Label(self, text="Subscription Plans", font=("Arial", 18, "bold"))
        lbl_title.pack(pady=(10, 0))

        self.lbl_status = ttk.Label(self, text="Your current plan: Loading...", font=("Arial", 12, "bold"), foreground="blue")
        self.lbl_status.pack(pady=(5, 5))
        
        # Button to view subscription details
        btn_view_subscription = ttk.Button(self, text="View Subscription Details", command=self.show_subscription_details)
        btn_view_subscription.pack(pady=(0, 15))

        self.cards_frame = ttk.Frame(self)
        self.cards_frame.pack(fill="x", expand=True, padx=20)
        self.cards_frame.grid_columnconfigure(0, weight=1)
        self.cards_frame.grid_columnconfigure(1, weight=1)
        self.cards_frame.grid_columnconfigure(2, weight=1)
        
        btn_back = ttk.Button(self, text="Back to Dashboard", command=self.go_to_dashboard)
        btn_back.pack(pady=20)
        
        # Bind the on_show event
        self.bind("<<ShowFrame>>", self.on_show)

    def on_show(self, event=None):
        """Called when the frame is shown. Fetches and displays plan info."""
        log.info("Loading Plans page...")
        # Refresh subscription status to get latest plan info
        if self.controller.auth.current_user:
            log.info("Refreshing subscription status on plans page...")
            self.controller.auth.get_subscription_status()
        self.update_current_plan_status()
        self.fetch_and_display_plans()

    def update_current_plan_status(self):
        """Updates the label at the top with the user's current status."""
        sub_data = self.controller.auth.subscription_data
        if not sub_data:
            self.lbl_status.config(text="Could not load your subscription.", foreground="red")
            return

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
                
                if days_left > 0:
                    self.lbl_status.config(text=f"Trial Period - {days_left} days left", foreground="blue")
                else:
                    self.lbl_status.config(text=f"Trial Period Expired", foreground="red")
            except Exception as e:
                 log.error(f"Error parsing trial date: {e}")
                 self.lbl_status.config(text=f"Trial Period", foreground="blue")
        
        elif status == 'active':
            # Calculate days remaining for active subscription
            try:
                subscription_ends_at = sub_data.get('subscription_ends_at')
                if subscription_ends_at:
                    end_date = datetime.fromisoformat(subscription_ends_at.replace('Z', '+00:00'))
                    today = datetime.now(end_date.tzinfo)
                    days_remaining = (end_date.date() - today.date()).days
                    
                    if days_remaining > 0:
                        self.lbl_status.config(text=f"Your Plan: {plan_name} (Active - {days_remaining} days remaining)", foreground="green")
                    elif days_remaining == 0:
                        self.lbl_status.config(text=f"Your Plan: {plan_name} (Active - Expires today)", foreground="orange")
                    else:
                        self.lbl_status.config(text=f"Your Plan: {plan_name} (Expired)", foreground="red")
                else:
                    self.lbl_status.config(text=f"Your Plan: {plan_name} (Active)", foreground="green")
            except Exception as e:
                log.error(f"Error calculating days remaining: {e}")
                self.lbl_status.config(text=f"Your Plan: {plan_name} (Active)", foreground="green")
        
        else: # 'expired', 'canceled', 'past_due'
            self.lbl_status.config(text=f"Your Plan: {plan_name} ({status.title()})", foreground="red")

    def fetch_and_display_plans(self):
        """Fetches all plans from Supabase and creates the UI cards."""
        for widget in self.cards_frame.winfo_children():
            widget.destroy()

        try:
            log.info("Fetching all plans...")
            plans = auth_service.get_all_plans()
            if not plans:
                raise Exception("No plans returned from database.")

            plans.sort(key=lambda p: p.get('price', 0))

            for i, plan in enumerate(plans):
                self._create_plan_card(self.cards_frame, plan, column=i)
                
        except Exception as e:
            log.error(f"Failed to fetch and display plans: {e}")
            lbl_error = ttk.Label(self.cards_frame, text=f"Error loading plans: {e}", foreground="red")
            lbl_error.grid(row=0, column=0)

    def _create_plan_card(self, parent, plan, column):
        """Creates a single card for a subscription plan."""
        
        card = ttk.Frame(parent, relief="solid", borderwidth=1, padding=15)
        card.grid(row=0, column=column, padx=10, pady=10, sticky="nsew")
        parent.grid_rowconfigure(0, weight=1)
        
        lbl_name = ttk.Label(card, text=plan.get("name", "No Name"), font=("Arial", 14, "bold"))
        lbl_name.pack(pady=5)
        
        price_str = f"₹{plan.get('price', 0)}/month"
        lbl_price = ttk.Label(card, text=price_str, font=("Arial", 12, "bold"))
        lbl_price.pack(pady=5)
        
        if plan.get("price_original"):
            lbl_orig_price = ttk.Label(card, text=f"was ₹{plan.get('price_original')}", font=("Arial", 10))
            lbl_orig_price.config(font=("Arial", 10, "overstrike"))
            lbl_orig_price.pack()
            
        sep = ttk.Separator(card)
        sep.pack(fill="x", pady=10)

        lbl_features_title = ttk.Label(card, text="Features:", font=("Arial", 11, "bold"))
        lbl_features_title.pack(anchor="w")

        features_frame = ttk.Frame(card)
        features_frame.pack(fill="both", expand=True, anchor="w", pady=5)
        
        features = plan.get("features", [])
        if not features:
            ttk.Label(features_frame, text="No features listed.").pack(anchor="w", padx=10)
            
        for feature in features:
            feature_name = feature.replace("_", " ").title()
            lbl_feature = ttk.Label(features_frame, text=f"• {feature_name}")
            lbl_feature.pack(anchor="w", padx=10)

        # --- !! UPDATED: Link to your Google Form !! ---
        btn_upgrade = ttk.Button(card, text="Pay with UPI / Request Plan", command=self.go_to_payment_form)
        btn_upgrade.pack(pady=15)

    def go_to_payment_form(self):
        """Opens your Google Form link."""
        log.info(f"Opening payment form: {YOUR_PAYMENT_LINK}")
        webbrowser.open(YOUR_PAYMENT_LINK)

    def show_subscription_details(self):
        """Shows a window with detailed subscription information including start and end dates."""
        sub_data = self.controller.auth.subscription_data
        if not sub_data:
            messagebox.showerror("Error", "Could not load subscription information.")
            return
        
        # Create a new window
        details_window = tk.Toplevel(self)
        details_window.title("Subscription Details")
        details_window.geometry("600x500")
        details_window.transient(self)
        details_window.grab_set()
        # Enable maximize and minimize buttons
        details_window.resizable(True, True)
        details_window.minsize(500, 400)
        
        # Main frame with padding
        main_frame = ttk.Frame(details_window, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Subscription Details", font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Subscription info frame
        info_frame = ttk.LabelFrame(main_frame, text="Current Subscription", padding=15)
        info_frame.pack(fill="x", pady=10)
        
        status = sub_data.get("status", "Unknown")
        plan_name = "N/A"
        if sub_data.get("plans"):
            plan_name = sub_data["plans"].get("name", "Unknown Plan")
        
        # Plan name and status
        ttk.Label(info_frame, text=f"Plan:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", pady=5)
        ttk.Label(info_frame, text=plan_name, font=("Arial", 10)).grid(row=0, column=1, sticky="w", padx=10, pady=5)
        
        ttk.Label(info_frame, text=f"Status:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w", pady=5)
        status_color = "green" if status == "active" else "blue" if status == "trialing" else "red"
        status_label = ttk.Label(info_frame, text=status.title(), font=("Arial", 10), foreground=status_color)
        status_label.grid(row=1, column=1, sticky="w", padx=10, pady=5)
        
        # Dates section
        dates_frame = ttk.LabelFrame(main_frame, text="Subscription Dates", padding=15)
        dates_frame.pack(fill="x", pady=10)
        
        # Start date (created_at or trial start)
        created_at = sub_data.get("created_at")
        if created_at:
            try:
                start_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                start_str = start_date.strftime("%Y-%m-%d %H:%M:%S")
            except:
                start_str = created_at.split('T')[0] if 'T' in created_at else created_at
        else:
            start_str = "N/A"
        
        ttk.Label(dates_frame, text="Start Date:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", pady=5)
        ttk.Label(dates_frame, text=start_str, font=("Arial", 10)).grid(row=0, column=1, sticky="w", padx=10, pady=5)
        
        # Trial end date (if trialing)
        trial_ends_at = sub_data.get("trial_ends_at")
        if trial_ends_at:
            try:
                trial_end = datetime.fromisoformat(trial_ends_at.replace('Z', '+00:00'))
                trial_end_str = trial_end.strftime("%Y-%m-%d %H:%M:%S")
            except:
                trial_end_str = trial_ends_at.split('T')[0] if 'T' in trial_ends_at else trial_ends_at
            
            ttk.Label(dates_frame, text="Trial End Date:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w", pady=5)
            ttk.Label(dates_frame, text=trial_end_str, font=("Arial", 10)).grid(row=1, column=1, sticky="w", padx=10, pady=5)
        
        # Subscription end date (if active)
        subscription_ends_at = sub_data.get("subscription_ends_at")
        if subscription_ends_at:
            try:
                sub_end = datetime.fromisoformat(subscription_ends_at.replace('Z', '+00:00'))
                sub_end_str = sub_end.strftime("%Y-%m-%d %H:%M:%S")
            except:
                sub_end_str = subscription_ends_at.split('T')[0] if 'T' in subscription_ends_at else subscription_ends_at
            
            ttk.Label(dates_frame, text="Subscription End Date:", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky="w", pady=5)
            ttk.Label(dates_frame, text=sub_end_str, font=("Arial", 10)).grid(row=2, column=1, sticky="w", padx=10, pady=5)
        
        # Features section
        features_frame = ttk.LabelFrame(main_frame, text="Plan Features", padding=15)
        features_frame.pack(fill="both", expand=True, pady=10)
        
        # If user is in trial, show all premium features
        if status == "trialing":
            # All premium features available during trial
            all_premium_features = [
                "SCREENSHOT",
                "TELEMETRY", 
                "ACTIVITY_SUMMARY",
                "ADVANCED_ACTIVITY",
                "TYPING_INTENSITY",
                "SCREEN_RECORD",
                "CAMERA",
                "MICROPHONE",
                "REPORT_SCHEDULE"
            ]
            
            # Trial message
            trial_msg = ttk.Label(
                features_frame, 
                text="🎉 In Trial Period - You Can Access All Premium Features!",
                font=("Arial", 10, "bold"),
                foreground="green"
            )
            trial_msg.pack(anchor="w", pady=(0, 10))
            
            # Feature names mapping for display
            feature_display_names = {
                "SCREENSHOT": "Screenshots",
                "TELEMETRY": "Telemetry (Location/CPU/RAM/etc)",
                "ACTIVITY_SUMMARY": "Activity Summary (Window Title)",
                "ADVANCED_ACTIVITY": "Advanced Activity Tracking",
                "TYPING_INTENSITY": "Typed Activity (Keystroke Count)",
                "SCREEN_RECORD": "Screen Recording",
                "CAMERA": "Camera Recording",
                "MICROPHONE": "Microphone Recording",
                "REPORT_SCHEDULE": "Report Scheduling"
            }
            
            features_text = "\n".join([
                f"✓ {feature_display_names.get(f, f.replace('_', ' ').title())}" 
                for f in all_premium_features
            ])
        else:
            # Show actual plan features
            features = []
            if sub_data.get("plans"):
                features = sub_data["plans"].get("features", [])
            
            if features:
                features_text = "\n".join([f"• {f.replace('_', ' ').title()}" for f in features])
            else:
                features_text = "No features available"
        
        # Create scrollable text widget for features
        features_canvas = tk.Canvas(features_frame, height=150)
        features_scrollbar = ttk.Scrollbar(features_frame, orient="vertical", command=features_canvas.yview)
        features_scrollable = ttk.Frame(features_canvas)
        
        features_scrollable.bind(
            "<Configure>",
            lambda e: features_canvas.configure(scrollregion=features_canvas.bbox("all"))
        )
        
        features_canvas.create_window((0, 0), window=features_scrollable, anchor="nw")
        features_canvas.configure(yscrollcommand=features_scrollbar.set)
        
        features_label = ttk.Label(features_scrollable, text=features_text, font=("Arial", 9), justify="left")
        features_label.pack(anchor="w", padx=5, pady=5)
        
        features_canvas.pack(side="left", fill="both", expand=True)
        features_scrollbar.pack(side="right", fill="y")
        
        # Close button
        btn_close = ttk.Button(main_frame, text="Close", command=details_window.destroy)
        btn_close.pack(pady=20)
    
    def go_to_dashboard(self):
        from .dashboard_ui import DashboardFrame
        self.controller.show_frame(DashboardFrame)