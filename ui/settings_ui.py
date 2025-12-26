import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from logger_setup import log
import re
import os
import persistence
from auth import auth_service

# --- !! HELPER DICTIONARY TO MAP CONFIG NAMES TO DATABASE FEATURE NAMES !! ---
# This maps local config keys (screenshot) to database feature names (SCREENSHOT)
CONFIG_TO_DB_MAP = {
    "screenshot": "SCREENSHOT",
    "telemetry": "TELEMETRY",
    "activity": "ACTIVITY_SUMMARY",  # Also accepts ADVANCED_ACTIVITY
    "typed_activity": "TYPING_INTENSITY",
    "camera": "CAMERA",
    "microphone": "MICROPHONE",
    "screen_record": "SCREEN_RECORD"
}

class SettingsFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        try:
            self.settings = self.controller.config.get_settings()
        except Exception as e:
            log.error(f"Failed to load settings on init: {e}")
            self.settings = {} 
            
        self.feature_widgets = {}
        
        self.security_options = {
            "High-Security (.enc)": "high",
            "Password-Protected (.zip)": "zip",
            "No Protection (Not Secure)": "none"
        }
        self.security_options_inv = {v: k for k, v in self.security_options.items()}
        self.destination_options = {
            "Email (Add to Bundle)": "bundle",
            "Email (Send Instantly)": "instant",
            "Save to Local Folder": "local"
        }
        self.destination_options_inv = {v: k for k, v in self.destination_options.items()}

        self.vcmd = (self.register(self.validate_time), '%P')

        # --- SCROLLABLE LAYOUT ---
        self.main_canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.main_canvas.yview)
        self.scrollable_frame = ttk.Frame(self.main_canvas)
        self.main_canvas.configure(yscrollcommand=scrollbar.set)
        self.main_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        def on_configure(event):
            self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))
        self.scrollable_frame.bind("<Configure>", on_configure)
        scrollbar.pack(side="right", fill="y")
        self.main_canvas.pack(side="left", fill="both", expand=True)
        
        # --- WIDGETS GO INTO "self.scrollable_frame" ---
        lbl_title = ttk.Label(self.scrollable_frame, text="Settings", font=("Arial", 18))
        lbl_title.pack(pady=10)
        guide_text = "Time Guide: Use 24-hour format (HH:MM). Examples: 9:00 AM = 09:00 | 5:00 PM = 17:00"
        guide_label = ttk.Label(self.scrollable_frame, text=guide_text, relief="solid", padding=5, background="#FFFFE0")
        guide_label.pack(fill="x", padx=20, pady=(0, 10))

        user_frame = ttk.LabelFrame(self.scrollable_frame, text="User Settings")
        user_frame.pack(fill="x", padx=20, pady=10)
        self.entry_email = self._create_entry_row(user_frame, "Recipient Email:", self.settings.get("user", {}).get("recipient_email", ""))
        self.entry_device_name = self._create_entry_row(user_frame, "Device Name:", self.settings.get("user", {}).get("device_name", "My-Computer"))
        self.entry_pass = self._create_entry_row(user_frame, "Encryption Password:", self.settings.get("user", {}).get("encryption_password", ""), show="*")
        
        security_frame = ttk.LabelFrame(self.scrollable_frame, text="Security & Login")
        security_frame.pack(fill="x", padx=20, pady=10)
        # Secure login PIN option removed from Settings UI
        self.pin_login_var = tk.BooleanVar(value=False)
        # No user-facing control for PIN login. Internal flags remain in config.
        
        # Emergency Alert Settings Frame
        emergency_frame = ttk.LabelFrame(self.scrollable_frame, text="Emergency Alert Settings")
        emergency_frame.pack(fill="x", padx=20, pady=10)
        
        # Emergency feature enabled — user can configure emergency settings
        self.emergency_enabled_var = tk.BooleanVar()
        self.chk_emergency = ttk.Checkbutton(
            emergency_frame,
            text="Enable Emergency Alert Feature",
            variable=self.emergency_enabled_var,
            command=self.toggle_emergency_settings
        )
        self.chk_emergency.pack(side="top", anchor="w", padx=10, pady=5)
        
        self.emergency_consent_var = tk.BooleanVar()
        self.chk_emergency_consent = ttk.Checkbutton(
            emergency_frame,
            text="I consent to share my data with help department in emergency situations",
            variable=self.emergency_consent_var
        )
        self.chk_emergency_consent.pack(side="top", anchor="w", padx=20, pady=5)
        
        # User name field (for emergency alerts)
        name_frame = ttk.Frame(emergency_frame)
        name_frame.pack(fill="x", padx=20, pady=5)
        
        self.entry_user_name = self._create_entry_row(name_frame, "Your Name:", self.settings.get("emergency", {}).get("user_name", ""))
        
        # Phone number fields
        phone_frame = ttk.Frame(emergency_frame)
        phone_frame.pack(fill="x", padx=20, pady=5)
        
        self.entry_user_phone = self._create_entry_row(phone_frame, "Your Phone Number:", self.settings.get("emergency", {}).get("user_phone", ""))
        
        # Emergency email field
        email_frame = ttk.Frame(emergency_frame)
        email_frame.pack(fill="x", padx=20, pady=5)
        
        self.entry_emergency_email = self._create_entry_row(email_frame, "Emergency Email:", self.settings.get("emergency", {}).get("emergency_email", ""))
        
        # Emergency contacts list
        contacts_frame = ttk.Frame(emergency_frame)
        contacts_frame.pack(fill="x", padx=20, pady=5)
        
        ttk.Label(contacts_frame, text="Emergency Contacts (Name - Phone):").pack(anchor="w", pady=(0, 5))
        
        self.emergency_contacts_listbox_frame = ttk.Frame(contacts_frame)
        self.emergency_contacts_listbox_frame.pack(fill="both", expand=True)
        
        scrollbar_contacts = ttk.Scrollbar(self.emergency_contacts_listbox_frame)
        self.emergency_contacts_listbox = tk.Listbox(self.emergency_contacts_listbox_frame, height=4, yscrollcommand=scrollbar_contacts.set)
        scrollbar_contacts.config(command=self.emergency_contacts_listbox.yview)
        self.emergency_contacts_listbox.pack(side="left", fill="both", expand=True)
        scrollbar_contacts.pack(side="right", fill="y")
        
        contacts_btn_frame = ttk.Frame(contacts_frame)
        contacts_btn_frame.pack(fill="x", pady=5)
        
        ttk.Label(contacts_btn_frame, text="Name:").pack(side="left", padx=5)
        self.entry_contact_name = ttk.Entry(contacts_btn_frame, width=15)
        self.entry_contact_name.pack(side="left", padx=5)
        ttk.Label(contacts_btn_frame, text="Phone:").pack(side="left", padx=5)
        self.entry_new_contact = ttk.Entry(contacts_btn_frame, width=20)
        self.entry_new_contact.pack(side="left", padx=5)
        btn_add_contact = ttk.Button(contacts_btn_frame, text="Add Contact", command=self.add_emergency_contact)
        btn_add_contact.pack(side="left", padx=5)
        btn_remove_contact = ttk.Button(contacts_btn_frame, text="Remove Selected", command=self.remove_emergency_contact)
        btn_remove_contact.pack(side="left", padx=5)
        
        # Desktop shortcut option
        shortcut_frame = ttk.Frame(emergency_frame)
        shortcut_frame.pack(fill="x", padx=20, pady=10)
        
        ttk.Label(shortcut_frame, text="Desktop Shortcut:").pack(side="left", padx=(0, 10))
        self.btn_create_shortcut = ttk.Button(shortcut_frame, text="Create Desktop Shortcut", command=self.handle_shortcut_creation)
        self.btn_create_shortcut.pack(side="left", padx=5)
        self.btn_remove_shortcut = ttk.Button(shortcut_frame, text="Remove Desktop Shortcut", command=self.handle_shortcut_removal)
        self.btn_remove_shortcut.pack(side="left", padx=5)
        self.lbl_shortcut_status = ttk.Label(shortcut_frame, text="", foreground="green")
        self.lbl_shortcut_status.pack(side="left", padx=10)
        
        # Emergency Shortcut PIN (separate from login PIN)
        pin_frame = ttk.Frame(emergency_frame)
        pin_frame.pack(fill="x", padx=20, pady=10)
        
        ttk.Label(pin_frame, text="Set 4-Digit PIN for Desktop Shortcut:", font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 5))
        
        info_label = ttk.Label(
            pin_frame, 
            text="When you double-click the Emergency Alert desktop shortcut, you will be asked to enter this PIN. This protects against accidental activation.",
            font=("Arial", 9),
            foreground="blue",
            wraplength=500
        )
        info_label.pack(anchor="w", pady=(0, 10))
        
        pin_input_frame = ttk.Frame(pin_frame)
        pin_input_frame.pack(fill="x")
        
        ttk.Label(pin_input_frame, text="PIN:").pack(side="left", padx=(0, 5))
        self.entry_emergency_pin = ttk.Entry(pin_input_frame, width=10, show="*", font=("Arial", 12), justify="center")
        self.entry_emergency_pin.pack(side="left", padx=(0, 10))
        # Update button for Emergency PIN — user must click to save/confirm PIN
        btn_update_pin = ttk.Button(pin_input_frame, text="Update PIN", command=self.update_emergency_pin)
        btn_update_pin.pack(side="left", padx=(0,10))
        
        # Single PIN entry for desktop shortcut (4 digits)
        self.lbl_emergency_pin_status = ttk.Label(pin_frame, text="", font=("Arial", 9))
        self.lbl_emergency_pin_status.pack(anchor="w", pady=(10, 0))
        
        # Data Sharing Preferences for Emergency Alerts
        data_sharing_frame = ttk.LabelFrame(emergency_frame, text="Emergency Alert Data Sharing Preferences")
        data_sharing_frame.pack(fill="x", padx=20, pady=10)
        
        sharing_info = ttk.Label(data_sharing_frame, 
                                text="Select which data to include when sending emergency alerts to contacts:\n(Admin always receives full data for support purposes)", 
                                font=("Arial", 9), foreground="gray", justify="left")
        sharing_info.pack(anchor="w", padx=10, pady=(5, 10))
        
        # Create checkbox variables for data sharing preferences
        self.data_sharing_prefs = {
            'screenshot': tk.BooleanVar(),
            'device_info': tk.BooleanVar(),
            'last_location': tk.BooleanVar(),
            'activity_summary': tk.BooleanVar(),
            'logs': tk.BooleanVar(),
            'camera': tk.BooleanVar(),
            'microphone': tk.BooleanVar(),
            'screen_record': tk.BooleanVar()
        }
        
        # Load current preferences
        prefs = self.settings.get("emergency", {}).get("data_sharing_preferences", {})
        self.data_sharing_prefs['screenshot'].set(prefs.get('screenshot', False))
        self.data_sharing_prefs['device_info'].set(prefs.get('device_info', False))
        self.data_sharing_prefs['last_location'].set(prefs.get('last_location', False))
        self.data_sharing_prefs['activity_summary'].set(prefs.get('activity_summary', False))
        self.data_sharing_prefs['logs'].set(prefs.get('logs', False))
        # New media capture preferences
        self.data_sharing_prefs['camera'].set(prefs.get('camera', False))
        self.data_sharing_prefs['microphone'].set(prefs.get('microphone', False))
        self.data_sharing_prefs['screen_record'].set(prefs.get('screen_record', False))
        
        # Create checkboxes for each data type
        ttk.Checkbutton(data_sharing_frame, 
                       text="Screenshot - Include a screenshot from the time of emergency",
                       variable=self.data_sharing_prefs['screenshot']).pack(anchor="w", padx=20, pady=3)
        
        ttk.Checkbutton(data_sharing_frame,
                       text="Device Info - Include device name, OS, and system information",
                       variable=self.data_sharing_prefs['device_info']).pack(anchor="w", padx=20, pady=3)
        
        ttk.Checkbutton(data_sharing_frame,
                       text="Last Location - Include last known GPS location or IP-based location",
                       variable=self.data_sharing_prefs['last_location']).pack(anchor="w", padx=20, pady=3)
        
        ttk.Checkbutton(data_sharing_frame,
                       text="Activity Summary - Include currently active application and recent activity",
                       variable=self.data_sharing_prefs['activity_summary']).pack(anchor="w", padx=20, pady=3)
        
        ttk.Checkbutton(data_sharing_frame,
                       text="Application Logs - Include recent system and app logs for debugging",
                       variable=self.data_sharing_prefs['logs']).pack(anchor="w", padx=20, pady=3)

        # Media capture options
        ttk.Checkbutton(data_sharing_frame,
                   text="Camera Capture - Include camera snapshots/recordings",
                   variable=self.data_sharing_prefs['camera']).pack(anchor="w", padx=20, pady=3)

        ttk.Checkbutton(data_sharing_frame,
                   text="Microphone Capture - Include short audio recordings",
                   variable=self.data_sharing_prefs['microphone']).pack(anchor="w", padx=20, pady=3)

        ttk.Checkbutton(data_sharing_frame,
                   text="Screen Recording - Include short screen recording",
                   variable=self.data_sharing_prefs['screen_record']).pack(anchor="w", padx=20, pady=3)
        
        persistence_frame = ttk.LabelFrame(self.scrollable_frame, text="Startup Settings")
        persistence_frame.pack(fill="x", padx=20, pady=10)
        self.startup_var = tk.BooleanVar()
        self.chk_startup = ttk.Checkbutton(
            persistence_frame,
            text="Start eMonitor automatically with Windows",
            variable=self.startup_var,
            command=self.toggle_startup
        )
        self.chk_startup.pack(side="left", padx=10, pady=5, anchor="w")
        self.prevent_sleep_var = tk.BooleanVar()
        self.chk_prevent_sleep = ttk.Checkbutton(
            persistence_frame,
            text="Prevent system sleep while monitoring",
            variable=self.prevent_sleep_var
        )
        self.chk_prevent_sleep.pack(side="left", padx=10, pady=5, anchor="w")
        
        local_save_frame = ttk.LabelFrame(self.scrollable_frame, text="Local Save Destination")
        local_save_frame.pack(fill="x", padx=20, pady=10)
        self.local_save_var = tk.BooleanVar()
        self.chk_local_save = ttk.Checkbutton(
            local_save_frame,
            text="Enable Saving Files to a Local Folder",
            variable=self.local_save_var,
            command=self.toggle_local_save_widgets
        )
        self.chk_local_save.pack(side="top", anchor="w", padx=10, pady=5)
        self.lbl_save_path = ttk.Label(local_save_frame, text="No folder selected.", wraplength=600)
        self.btn_change_folder = ttk.Button(local_save_frame, text="Change Save Folder...", command=self.select_save_folder)
        self.lbl_save_path.pack(fill="x", padx=10, pady=5)
        self.btn_change_folder.pack(padx=10, pady=5)

        self.report_frame = ttk.LabelFrame(self.scrollable_frame, text="Email Report Bundle Schedule")
        self.report_frame.pack(fill="x", padx=20, pady=10)
        self.create_reporting_widgets(self.report_frame)
        
        # --- !! THIS IS THE FIX !! ---
        # 1. Create the frame as a class attribute
        self.feature_frame = ttk.LabelFrame(self.scrollable_frame, text="Monitoring Features (What to capture)")
        self.feature_frame.pack(fill="x", padx=20, pady=10)
        
        # 2. Pass the correct variable to the creation function
        self.feature_widgets["screenshot"] = self._create_feature_row(self.feature_frame, "Screenshots", "screenshot")
        self.feature_widgets["telemetry"] = self._create_feature_row(self.feature_frame, "Telemetry (Location/CPU/RAM/etc)", "telemetry")
        self.feature_widgets["activity"] = self._create_feature_row(self.feature_frame, "Activity (Window Title)", "activity")
        self.feature_widgets["typed_activity"] = self._create_feature_row(self.feature_frame, "Typed-Activity (Count)", "typed_activity", duration_label="Gather (sec):")
        self.feature_widgets["camera"] = self._create_feature_row(self.feature_frame, "Camera Recording", "camera", duration_label="Duration (sec):")
        self.feature_widgets["microphone"] = self._create_feature_row(self.feature_frame, "Microphone Recording", "microphone", duration_label="Duration (sec):")
        self.feature_widgets["screen_record"] = self._create_feature_row(self.feature_frame, "Screen Recording", "screen_record", duration_label="Duration (min):")
        
        button_frame = ttk.Frame(self.scrollable_frame)
        button_frame.pack(pady=20)
        btn_save = ttk.Button(button_frame, text="Save Settings", command=self.handle_save)
        btn_save.pack(side="left", padx=10)
        btn_back = ttk.Button(button_frame, text="Back to Dashboard", command=self.go_to_dashboard)
        btn_back.pack(side="left", padx=10)

        self.main_canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.scrollable_frame.bind("<MouseWheel>", self._on_mousewheel)
        self._bind_children(self.scrollable_frame)
        
        self.update_save_path_label()
        self.toggle_local_save_widgets()

    # Secure login PIN helper methods removed from SettingsFrame

    def toggle_local_save_widgets(self):
        if self.local_save_var.get():
            self.lbl_save_path.pack(fill="x", padx=10, pady=5)
            self.btn_change_folder.pack(padx=10, pady=5)
            self.update_save_path_label()
        else:
            self.lbl_save_path.pack_forget()
            self.btn_change_folder.pack_forget()
    
    def toggle_emergency_settings(self):
        """Enable/disable emergency settings widgets based on checkbox"""
        state = "normal" if self.emergency_enabled_var.get() else "disabled"
        self.chk_emergency_consent.config(state=state)
        self.entry_user_name.config(state=state)
        self.entry_user_phone.config(state=state)
        self.entry_contact_name.config(state=state)
        self.entry_new_contact.config(state=state)
        self.emergency_contacts_listbox.config(state=state)
        self.entry_emergency_pin.config(state=state)
    
    def add_emergency_contact(self):
        """Add a new emergency contact with name and phone number"""
        name = self.entry_contact_name.get().strip()
        phone = self.entry_new_contact.get().strip()
        
        if not phone:
            messagebox.showwarning("Invalid Input", "Please enter a phone number.")
            return
        
        # Format: "Name - Phone" or just "Phone" if no name
        if name:
            contact_display = f"{name} - {phone}"
            contact_data = {"name": name, "phone": phone}
        else:
            contact_display = phone
            contact_data = {"name": "", "phone": phone}
        
        self.emergency_contacts_listbox.insert(tk.END, contact_display)
        self.entry_contact_name.delete(0, tk.END)
        self.entry_new_contact.delete(0, tk.END)
    
    def remove_emergency_contact(self):
        """Remove selected emergency contact"""
        selection = self.emergency_contacts_listbox.curselection()
        if selection:
            self.emergency_contacts_listbox.delete(selection[0])
        else:
            messagebox.showwarning("No Selection", "Please select a contact to remove.")
    
    def handle_shortcut_creation(self):
        """Creates desktop shortcut for emergency alert."""
        try:
            from desktop_shortcut import create_emergency_shortcut
            if create_emergency_shortcut():
                self.lbl_shortcut_status.config(text="Shortcut created!", foreground="green")
                # Check if emergency shortcut PIN is set
                emergency_cfg = self.settings.get("emergency", {})
                if emergency_cfg.get("emergency_shortcut_pin_salt") and emergency_cfg.get("emergency_shortcut_pin_hash"):
                    messagebox.showinfo("Success", "Emergency Alert desktop shortcut created successfully!\n\nDouble-click the shortcut and enter your Emergency Shortcut PIN to trigger an emergency alert.")
                else:
                    messagebox.showinfo("Success", "Emergency Alert desktop shortcut created successfully!\n\nNote: Set an Emergency Shortcut PIN in settings for security.\nDouble-click the shortcut to trigger an emergency alert.")
            else:
                self.lbl_shortcut_status.config(text="Failed to create shortcut", foreground="red")
                messagebox.showerror("Error", "Failed to create desktop shortcut.\n\nPlease ensure pywin32 is installed:\npip install pywin32")
        except Exception as e:
            log.error(f"Failed to create shortcut: {e}")
            messagebox.showerror("Error", f"Failed to create desktop shortcut: {e}")
    
    def handle_shortcut_removal(self):
        """Removes desktop shortcut for emergency alert."""
        try:
            from desktop_shortcut import remove_emergency_shortcut
            if remove_emergency_shortcut():
                self.lbl_shortcut_status.config(text="Shortcut removed!", foreground="green")
                messagebox.showinfo("Success", "Emergency Alert desktop shortcut removed successfully.")
            else:
                self.lbl_shortcut_status.config(text="Failed to remove shortcut", foreground="red")
        except Exception as e:
            log.error(f"Failed to remove shortcut: {e}")
            messagebox.showerror("Error", f"Failed to remove desktop shortcut: {e}")

    def update_emergency_pin(self):
        """Validate and update the emergency shortcut PIN immediately when user clicks Update"""
        try:
            pin = self.entry_emergency_pin.get().strip()
            if not pin:
                messagebox.showwarning("No PIN Entered", "Please enter a 4-digit PIN before clicking Update.")
                return
            if len(pin) != 4 or not pin.isdigit():
                messagebox.showerror("Invalid PIN", "Emergency shortcut PIN must be exactly 4 digits.")
                return
            from persistence import hash_pin
            salt_hex, hashed_hex = hash_pin(pin)
            # Persist immediately to settings
            settings = self.controller.config.get_settings()
            if "emergency" not in settings:
                settings["emergency"] = {}
            settings["emergency"]["emergency_shortcut_pin_salt"] = salt_hex
            settings["emergency"]["emergency_shortcut_pin_hash"] = hashed_hex
            self.controller.config.update_settings(settings)
            self.lbl_emergency_pin_status.config(text="Emergency shortcut PIN updated.", foreground="green")
            messagebox.showinfo("Updated", "Emergency PIN updated successfully.")
            self.entry_emergency_pin.delete(0, tk.END)
        except Exception as e:
            log.error(f"Failed to update emergency PIN: {e}")
            messagebox.showerror("Error", f"Failed to update Emergency PIN: {e}")

    def update_save_path_label(self):
        path = self.settings["user"].get("local_save_path")
        if self.local_save_var.get():
            if path and os.path.isdir(path):
                self.lbl_save_path.config(text=f"Saving to: {path}", foreground="green")
            else:
                self.lbl_save_path.config(text="Folder not selected! 'Save to Local Folder' will fail.", foreground="red")
        else:
            self.lbl_save_path.config(text="")

    def select_save_folder(self):
        path = filedialog.askdirectory(title="Select a Folder to Save Files")
        if path:
            self.settings["user"]["local_save_path"] = path
            self.update_save_path_label()
            self.settings = self.controller.config.get_settings()
            self.settings["user"]["local_save_path"] = path
            self.controller.config.update_settings(self.settings)

    def toggle_startup(self):
        try:
            if self.startup_var.get():
                persistence.set_startup(on=True)
                log.info("Added app to startup.")
                messagebox.showinfo("Startup Enabled", "eMonitor will now start automatically with Windows.")
            else:
                persistence.set_startup(on=False)
                log.info("Removed app from startup.")
                messagebox.showinfo("Startup Disabled", "eMonitor will no longer start automatically.")
        except Exception as e:
            log.error(f"Failed to change startup: {e}")
            messagebox.showerror("Permission Error", 
                "Could not change startup settings.\n\n"
                "Please try running the app as an Administrator to change this setting.")
            self.startup_var.set(False)

    def _on_mousewheel(self, event):
        if event.num == 5 or event.delta == -120:
            self.main_canvas.yview_scroll(1, "units")
        if event.num == 4 or event.delta == 120:
            self.main_canvas.yview_scroll(-1, "units")

    def _bind_children(self, widget):
        for child in widget.winfo_children():
            child.bind("<MouseWheel>", self._on_mousewheel)
            if child.winfo_children():
                self._bind_children(child)

    def create_reporting_widgets(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill="x", padx=10, pady=5)
        lbl_schedule = ttk.Label(frame, text="Send Report Bundle:")
        lbl_schedule.pack(side="left", padx=5)
        self.report_schedule_mode_var = tk.StringVar()
        self.radio_interval = ttk.Radiobutton(frame, text="Every (minutes):", variable=self.report_schedule_mode_var, value="interval", command=self.toggle_daily_time_entry)
        self.radio_interval.pack(side="left", padx=(10,0))
        self.entry_bundle_interval = ttk.Entry(frame, width=7)
        self.entry_bundle_interval.pack(side="left", padx=5)
        self.radio_daily = ttk.Radiobutton(frame, text="Once per Day at (HH:MM):", variable=self.report_schedule_mode_var, value="daily", command=self.toggle_daily_time_entry)
        self.radio_daily.pack(side="left", padx=(10,0))
        self.entry_daily_time = ttk.Entry(frame, width=7, validate="key", validatecommand=self.vcmd)
        self.entry_daily_time.pack(side="left", padx=5)
        
    def toggle_daily_time_entry(self, event=None):
        mode = self.report_schedule_mode_var.get()
        if mode == "daily":
            self.entry_daily_time.config(state="normal")
            self.entry_bundle_interval.config(state="disabled")
        else:
            self.entry_daily_time.config(state="disabled")
            self.entry_bundle_interval.config(state="normal")

    def validate_time(self, P):
        if P == "": return True
        if re.fullmatch(r"([01][0-9]|2[0-3]):[0-5][0-9]?", P) or \
           re.fullmatch(r"([01][0-9]|2[0-3]):?", P) or \
           re.fullmatch(r"([01][0-9]|2[0-3])?", P) or \
           re.fullmatch(r"24:00", P) or re.fullmatch(r"24:0?", P) or re.fullmatch(r"24?", P):
            if len(P) > 5: return False
            return True
        return False

    def _create_entry_row(self, parent, label, default_value, show=None):
        frame = ttk.Frame(parent)
        frame.pack(fill="x", padx=10, pady=5)
        lbl = ttk.Label(frame, text=label, width=20)
        lbl.pack(side="left")
        entry = ttk.Entry(frame, width=40, show=show)
        entry.insert(0, default_value)
        entry.pack(side="left", fill="x", expand=True, padx=5)
        return entry

    def _create_feature_row(self, parent, name, config_key, duration_label=None):
        """
        Helper to create a full feature row.
        config_key is the key in 'user_preferences' (e.g., 'screenshot')
        """
        config = self.settings.get("user_preferences", {})
            
        frame = ttk.Frame(parent, padding=10)
        frame.pack(fill="x", padx=5, pady=5)
        
        top_frame = ttk.Frame(frame)
        top_frame.pack(fill="x")
        
        enabled_var = tk.BooleanVar(value=config.get(f"{config_key}_enabled", False))
        chk = ttk.Checkbutton(top_frame, text=name, variable=enabled_var, width=25)
        chk.pack(side="left", anchor="w")
        
        lbl_int = ttk.Label(top_frame, text="Interval (min):")
        lbl_int.pack(side="left", padx=(10, 0))
        entry_int = ttk.Entry(top_frame, width=5)
        entry_int.insert(0, config.get(f"{config_key}_interval", 5))
        entry_int.pack(side="left", padx=5)

        lbl_start = ttk.Label(top_frame, text="Start (HH:MM):")
        lbl_start.pack(side="left", padx=(10, 0))
        entry_start = ttk.Entry(top_frame, width=7, validate="key", validatecommand=self.vcmd)
        entry_start.insert(0, config.get(f"{config_key}_start_time", "00:00"))
        entry_start.pack(side="left", padx=5)
        
        lbl_end = ttk.Label(top_frame, text="End (HH:MM):")
        lbl_end.pack(side="left", padx=(10, 0))
        entry_end = ttk.Entry(top_frame, width=7, validate="key", validatecommand=self.vcmd)
        entry_end.insert(0, config.get(f"{config_key}_end_time", "23:59"))
        entry_end.pack(side="left", padx=5)

        entry_dur = None
        if duration_label:
            lbl_dur = ttk.Label(top_frame, text=duration_label)
            lbl_dur.pack(side="left", padx=(10, 0))
            entry_dur = ttk.Entry(top_frame, width=5)
            entry_dur.insert(0, config.get(f"{config_key}_duration", 10))
            entry_dur.pack(side="left", padx=5)

        bottom_frame = ttk.Frame(frame)
        bottom_frame.pack(fill="x", pady=(5,0))

        lbl_sec = ttk.Label(bottom_frame, text="Security:", width=25)
        lbl_sec.pack(side="left", anchor="w")

        default_security = self.security_options_inv.get(config.get(f"{config_key}_security", "high"), "High-Security (.enc)")
        security_var = tk.StringVar(value=default_security)
        combo_sec = ttk.Combobox(bottom_frame, textvariable=security_var, values=list(self.security_options.keys()), state="readonly", width=25)
        combo_sec.pack(side="left", padx=(10, 0))

        lbl_dest = ttk.Label(bottom_frame, text="Destination:")
        lbl_dest.pack(side="left", padx=(10, 0))
        default_dest = self.destination_options_inv.get(config.get(f"{config_key}_destination", "bundle"), "Email (Add to Bundle)")
        destination_var = tk.StringVar(value=default_dest)
        combo_dest = ttk.Combobox(bottom_frame, textvariable=destination_var, values=list(self.destination_options.keys()), state="readonly", width=20)
        combo_dest.pack(side="left", padx=5)
        
        sep = ttk.Separator(frame)
        sep.pack(fill="x", pady=10)

        widget_list = [entry_int, entry_start, entry_end, combo_sec, combo_dest]
        if entry_dur:
            widget_list.append(entry_dur)
            
        def toggle_state():
            state = "normal" if enabled_var.get() else "disabled"
            for widget in widget_list:
                widget.config(state=state)
        
        chk.config(command=toggle_state)
        
        # --- !! THIS IS THE SECURITY FIX !! ---
        allowed_features = self.settings.get("allowed_features", [])
        
        # Map config key (e.g., "screenshot") to database feature name (e.g., "SCREENSHOT")
        db_key = CONFIG_TO_DB_MAP.get(config_key)
        if not db_key:
            # Fallback: convert config_key to uppercase
            db_key = config_key.upper().replace("-", "_")

        # Special handling for activity feature (can be ACTIVITY_SUMMARY or ADVANCED_ACTIVITY)
        if config_key == "activity":
            activity_allowed = "ACTIVITY_SUMMARY" in allowed_features or "ADVANCED_ACTIVITY" in allowed_features
            if not activity_allowed:
                db_key = None  # Mark as not allowed

        is_reporting_feature = config_key in ["screenshot", "telemetry", "activity", "typed_activity", "camera", "microphone", "screen_record"]
        reporting_allowed = "REPORT_SCHEDULE" in allowed_features

        # Check if feature is allowed
        feature_allowed = db_key and db_key in allowed_features if db_key else False
        
        # Debug logging
        log.debug(f"Feature '{config_key}' -> DB key '{db_key}', allowed: {feature_allowed}, reporting_allowed: {reporting_allowed}")
        
        if not feature_allowed or (is_reporting_feature and not reporting_allowed):
            chk.config(state="disabled")
            for widget in widget_list:
                widget.config(state="disabled")
            
            lbl_locked = ttk.Label(top_frame, text="(Upgrade Plan to Enable)", foreground="gray")
            lbl_locked.pack(side="left", padx=10)
            log.debug(f"Feature '{config_key}' is DISABLED - not in plan or reporting not allowed")
        else:
            toggle_state()
            log.debug(f"Feature '{config_key}' is ENABLED")
        
        return {
            "config_key": config_key,
            "enabled_var": enabled_var, "entry_int": entry_int,
            "entry_start": entry_start, "entry_end": entry_end,
            "entry_dur": entry_dur,
            "security_var": security_var, "combo_sec_widget": combo_sec,
            "destination_var": destination_var, "combo_dest_widget": combo_dest,
            "chk_widget": chk # Return the checkbox widget
        }

    def on_show(self):
        """Reload settings from config when frame is shown"""
        # Refresh subscription status to get latest allowed features
        if self.controller.auth.current_user:
            log.info("Refreshing subscription status on settings page...")
            self.controller.auth.get_subscription_status()
        
        self.settings = self.controller.config.get_settings()
        allowed_features = self.settings.get("allowed_features", [])
        
        # Check if user is in trial
        sub_data = self.controller.auth.subscription_data
        is_trial = sub_data and sub_data.get("status") == "trialing"
        
        if is_trial:
            log.info("User is in trial period - all premium features should be enabled")
            # Verify all premium features are in allowed_features
            all_premium_features = [
                "SCREENSHOT", "TELEMETRY", "ACTIVITY_SUMMARY", "ADVANCED_ACTIVITY",
                "TYPING_INTENSITY", "SCREEN_RECORD", "CAMERA", "MICROPHONE", "REPORT_SCHEDULE"
            ]
            missing_features = [f for f in all_premium_features if f not in allowed_features]
            if missing_features:
                log.warning(f"Trial user missing features: {missing_features}. Re-granting all features.")
                # Re-grant all features
                settings = self.controller.config.get_settings()
                settings["allowed_features"] = all_premium_features
                self.controller.config.update_settings(settings)
                allowed_features = all_premium_features
        
        log.info(f"Settings page loaded. Allowed features: {allowed_features}")
        prefs = self.settings["user_preferences"]
        
        try:
            self.startup_var.set(persistence.check_startup())
        except Exception as e:
            log.error(f"Failed to check startup: {e}")
            self.startup_var.set(False)
        
        # Secure login PIN removed; do not expose or change this setting from UI
        self.prevent_sleep_var.set(self.settings["user"].get("prevent_sleep_while_running", True))
        
        self.entry_email.delete(0, tk.END)
        self.entry_email.insert(0, self.settings["user"]["recipient_email"])
        self.entry_pass.delete(0, tk.END)
        self.entry_pass.insert(0, self.settings["user"]["encryption_password"])
        self.entry_device_name.delete(0, tk.END)
        self.entry_device_name.insert(0, self.settings["user"]["device_name"])
        
        self.local_save_var.set(self.settings["user"].get("local_save_enabled", False))
        self.update_save_path_label()
        self.toggle_local_save_widgets()

        # Load emergency settings
        emergency_cfg = self.settings.get("emergency", {})
        self.emergency_enabled_var.set(emergency_cfg.get("enabled", False))
        self.emergency_consent_var.set(emergency_cfg.get("data_sharing_consent", False))
        
        # Load user name
        self.entry_user_name.delete(0, tk.END)
        self.entry_user_name.insert(0, emergency_cfg.get("user_name", ""))
        
        # Load user phone
        self.entry_user_phone.delete(0, tk.END)
        self.entry_user_phone.insert(0, emergency_cfg.get("user_phone", ""))
        
        # Load emergency email
        self.entry_emergency_email.delete(0, tk.END)
        self.entry_emergency_email.insert(0, emergency_cfg.get("emergency_email", ""))
        
        # Load emergency shortcut PIN status (don't show the PIN, just status)
        self.entry_emergency_pin.delete(0, tk.END)
        if emergency_cfg.get("emergency_shortcut_pin_salt") and emergency_cfg.get("emergency_shortcut_pin_hash"):
            self.lbl_emergency_pin_status.config(text="Emergency shortcut PIN is set. Enter new PIN to change it.", foreground="green")
        else:
            self.lbl_emergency_pin_status.config(text="No emergency shortcut PIN set. Enter a 4-digit PIN to set it.", foreground="orange")
        
        # Load emergency contacts (handle both old format - just phone, and new format - name - phone)
        self.emergency_contacts_listbox.delete(0, tk.END)
        for contact in emergency_cfg.get("emergency_contacts", []):
            if isinstance(contact, dict):
                # New format: {"name": "...", "phone": "..."}
                if contact.get("name"):
                    display = f"{contact.get('name')} - {contact.get('phone', '')}"
                else:
                    display = contact.get("phone", "")
            else:
                # Old format: just phone number string
                display = str(contact)
            self.emergency_contacts_listbox.insert(tk.END, display)
        self.toggle_emergency_settings()
        
        # Update shortcut status
        try:
            from desktop_shortcut import check_shortcut_exists
            if check_shortcut_exists():
                self.lbl_shortcut_status.config(text="Shortcut exists", foreground="green")
            else:
                self.lbl_shortcut_status.config(text="No shortcut", foreground="gray")
        except Exception as e:
            log.error(f"Failed to check shortcut status: {e}")
            self.lbl_shortcut_status.config(text="", foreground="gray")

        report_cfg = self.settings["reporting"]
        self.report_schedule_mode_var.set(report_cfg["bundle_schedule_mode"])
        self.entry_bundle_interval.delete(0, tk.END)
        self.entry_bundle_interval.insert(0, report_cfg["bundle_interval"])
        self.entry_daily_time.delete(0, tk.END)
        self.entry_daily_time.insert(0, report_cfg["bundle_time_of_day"])
        self.toggle_daily_time_entry() 

        allowed_features = self.settings.get("allowed_features", [])
        
        reporting_allowed = "REPORT_SCHEDULE" in allowed_features
        if not reporting_allowed:
            self.radio_interval.config(state="disabled")
            self.entry_bundle_interval.config(state="disabled")
            self.radio_daily.config(state="disabled")
            self.entry_daily_time.config(state="disabled")

        for name, widgets in self.feature_widgets.items():
            config_key = widgets["config_key"]
            config = prefs
            
            widgets["enabled_var"].set(config.get(f"{config_key}_enabled", False))
            widgets["entry_int"].config(state="normal")
            widgets["entry_int"].delete(0, tk.END)
            widgets["entry_int"].insert(0, config.get(f"{config_key}_interval", 5))
            widgets["entry_start"].config(state="normal")
            widgets["entry_start"].delete(0, tk.END)
            widgets["entry_start"].insert(0, config.get(f"{config_key}_start_time", "00:00"))
            widgets["entry_end"].config(state="normal")
            widgets["entry_end"].delete(0, tk.END)
            widgets["entry_end"].insert(0, config.get(f"{config_key}_end_time", "23:59"))
            if widgets["entry_dur"]:
                widgets["entry_dur"].config(state="normal")
                widgets["entry_dur"].delete(0, tk.END)
                widgets["entry_dur"].insert(0, config.get(f"{config_key}_duration", 10))
            widgets["security_var"].set(self.security_options_inv[config.get(f"{config_key}_security", "high")])
            widgets["destination_var"].set(self.destination_options_inv[config.get(f"{config_key}_destination", "bundle")])
            
            # Check if allowed by plan
            # Map config key (e.g., "screenshot") to database feature name (e.g., "SCREENSHOT")
            db_key = CONFIG_TO_DB_MAP.get(config_key)
            if not db_key:
                # Fallback: convert config_key to uppercase
                db_key = config_key.upper().replace("-", "_")
            
            # Special handling for activity feature (can be ACTIVITY_SUMMARY or ADVANCED_ACTIVITY)
            if config_key == "activity":
                activity_allowed = "ACTIVITY_SUMMARY" in allowed_features or "ADVANCED_ACTIVITY" in allowed_features
                if not activity_allowed:
                    db_key = None  # Mark as not allowed
            
            feature_allowed = db_key and db_key in allowed_features if db_key else False
            
            if not feature_allowed:
                widgets["chk_widget"].config(state="disabled")
                state = "disabled"
            else:
                widgets["chk_widget"].config(state="normal")
                state = "normal" if config.get(f"{config_key}_enabled", False) else "disabled"
            
            widgets["entry_int"].config(state=state)
            widgets["entry_start"].config(state=state)
            widgets["entry_end"].config(state=state)
            widgets["combo_sec_widget"].config(state=state)
            widgets["combo_dest_widget"].config(state=state)
            if widgets["entry_dur"]:
                widgets["entry_dur"].config(state=state)

    def _validate_time_format(self, time_str):
        if time_str == "24:00": return True
        if re.fullmatch(r"([01][0-9]|2[0-3]):[0-5][0-9]", time_str): return True
        return False

    def handle_save(self):
        try:
            prefs = self.settings["user_preferences"]
            
            self.settings["user"]["recipient_email"] = self.entry_email.get()
            self.settings["user"]["encryption_password"] = self.entry_pass.get()
            self.settings["user"]["device_name"] = self.entry_device_name.get()
            self.settings["user"]["local_save_enabled"] = self.local_save_var.get()
            self.settings["user"]["prevent_sleep_while_running"] = self.prevent_sleep_var.get()
            
            # Save emergency settings
            if "emergency" not in self.settings:
                self.settings["emergency"] = {}
            self.settings["emergency"]["enabled"] = self.emergency_enabled_var.get()
            self.settings["emergency"]["data_sharing_consent"] = self.emergency_consent_var.get()
            self.settings["emergency"]["user_name"] = self.entry_user_name.get().strip()
            self.settings["emergency"]["user_phone"] = self.entry_user_phone.get().strip()
            self.settings["emergency"]["emergency_email"] = self.entry_emergency_email.get().strip()
            
            # Handle emergency shortcut PIN (single entry)
            pin = self.entry_emergency_pin.get().strip()
            if pin:  # User entered something
                if len(pin) != 4 or not pin.isdigit():
                    messagebox.showerror("Invalid PIN", "Emergency shortcut PIN must be exactly 4 digits.")
                    return
                # Hash and save the PIN
                from persistence import hash_pin
                salt_hex, hashed_hex = hash_pin(pin)
                self.settings["emergency"]["emergency_shortcut_pin_salt"] = salt_hex
                self.settings["emergency"]["emergency_shortcut_pin_hash"] = hashed_hex
                self.lbl_emergency_pin_status.config(text="Emergency shortcut PIN saved successfully!", foreground="green")
                # Clear the field after saving
                self.entry_emergency_pin.delete(0, tk.END)
            
            # Get emergency contacts from listbox (parse "Name - Phone" format)
            emergency_contacts = []
            for i in range(self.emergency_contacts_listbox.size()):
                contact_display = self.emergency_contacts_listbox.get(i)
                # Parse "Name - Phone" format
                if " - " in contact_display:
                    parts = contact_display.split(" - ", 1)
                    emergency_contacts.append({"name": parts[0].strip(), "phone": parts[1].strip()})
                else:
                    # Just phone number (backward compatibility)
                    emergency_contacts.append({"name": "", "phone": contact_display.strip()})
            self.settings["emergency"]["emergency_contacts"] = emergency_contacts
            
            # Save data sharing preferences
            self.settings["emergency"]["data_sharing_preferences"] = {
                'screenshot': self.data_sharing_prefs['screenshot'].get(),
                'device_info': self.data_sharing_prefs['device_info'].get(),
                'last_location': self.data_sharing_prefs['last_location'].get(),
                'activity_summary': self.data_sharing_prefs['activity_summary'].get(),
                'logs': self.data_sharing_prefs['logs'].get(),
                'camera': self.data_sharing_prefs['camera'].get(),
                'microphone': self.data_sharing_prefs['microphone'].get(),
                'screen_record': self.data_sharing_prefs['screen_record'].get()
            }
            
            if not self.settings["user"]["device_name"]:
                raise ValueError("Device Name cannot be empty.")
            
            mode = self.report_schedule_mode_var.get()
            self.settings["reporting"]["bundle_schedule_mode"] = mode
            if mode == "daily":
                daily_time = self.entry_daily_time.get()
                if not self._validate_time_format(daily_time):
                    raise ValueError("Invalid time for 'Once per Day'. Use HH:MM.")
                self.settings["reporting"]["bundle_time_of_day"] = daily_time
            else:
                interval_str = self.entry_bundle_interval.get()
                interval = int(interval_str)
                if interval <= 0:
                    raise ValueError("Bundle Interval must be a positive number.")
                self.settings["reporting"]["bundle_interval"] = interval
            
            local_save_is_used = False
            
            for name, widgets in self.feature_widgets.items():
                config_key = widgets["config_key"]
                
                interval_str = widgets["entry_int"].get()
                interval = int(interval_str)
                if interval <= 0:
                    raise ValueError(f"Interval for {name} must be positive.")
                start_time = widgets["entry_start"].get()
                end_time = widgets["entry_end"].get()
                if not self._validate_time_format(start_time) or not self._validate_time_format(end_time):
                    raise ValueError(f"Invalid time format for {name}. Use HH:MM.")
                destination = self.destination_options[widgets["destination_var"].get()]
                if destination == "local":
                    local_save_is_used = True
                
                prefs[f"{config_key}_enabled"] = widgets["enabled_var"].get()
                prefs[f"{config_key}_interval"] = interval
                prefs[f"{config_key}_start_time"] = start_time
                prefs[f"{config_key}_end_time"] = end_time
                prefs[f"{config_key}_security"] = self.security_options[widgets["security_var"].get()]
                prefs[f"{config_key}_destination"] = destination
                if widgets["entry_dur"]:
                    dur_str = widgets["entry_dur"].get()
                    duration = int(dur_str)
                    if duration <= 0:
                        raise ValueError(f"Duration for {name} must be positive.")
                    prefs[f"{config_key}_duration"] = duration
            
            if self.local_save_var.get() and not self.settings["user"]["local_save_path"]:
                raise ValueError("Local Saving is enabled, but no save folder has been selected.")
            if local_save_is_used and not self.local_save_var.get():
                raise ValueError("A feature is set to 'Save to Local Folder', but 'Enable Local Saving' is not checked.")
            
            self.controller.config.update_settings(self.settings)
            
            messagebox.showinfo("Success", "Settings saved successfully.\n\nChanges will apply the next time you start monitoring.")
            self.go_to_dashboard()
        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Error in settings:\n{e}\n\nPlease check your intervals and time formats.")
        except Exception as e:
            log.error(f"Failed to save settings: {e}")
            messagebox.showerror("Error", f"Could not save settings: {e}")

    def go_to_dashboard(self):
        from .dashboard_ui import DashboardFrame
        self.controller.show_frame(DashboardFrame)