import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import sys
from .login_ui import LoginFrame
from .dashboard_ui import DashboardFrame
from .settings_ui import SettingsFrame
from .consent_ui import ConsentFrame
from .data_viewer_ui import DataViewerFrame
from .pin_ui import PinFrame
from .subscription_ui import SubscriptionFrame
from .plans_ui import PlansFrame
from auth import auth_service
from config import config_manager, CURRENT_APP_VERSION, VERSION_CHECK_URL
from consent import consent_manager
from logger_setup import log
import pygame 
from power_manager import allow_sleep
import threading
import requests
import webbrowser
from packaging import version
from alert_manager import stop_hotkey_listener, start_hotkey_listener

class MainWindow(tk.Tk):
    def __init__(self, start_in_emergency_mode=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.start_in_emergency_mode = start_in_emergency_mode
        
        try:
            pygame.mixer.init()
        except Exception as e:
            log.error(f"Failed to initialize pygame.mixer: {e}")
        
        self.title("eMonitor")
        self.geometry("750x600")
        
        # Configure window to properly hide from taskbar when minimized (Windows)
        if sys.platform == "win32":
            try:
                # Ensure window can be properly hidden/shown
                self.attributes('-topmost', False)
            except Exception as e:
                log.warning(f"Could not configure window attributes: {e}")
        
        style = ttk.Style(self)
        default_font = ("Arial", 11)
        style.configure(".", font=default_font)
        style.configure("TLabel", font=default_font)
        style.configure("TButton", font=default_font)
        style.configure("TCheckbutton", font=default_font)
        style.configure("TRadiobutton", font=default_font)
        style.configure("TCombobox", font=default_font)
        style.configure("TLabelFrame.Label", font=("Arial", 11, "bold"))
        self.option_add("*TEntry*Font", default_font)
        self.option_add("*TCombobox*Listbox*Font", default_font)

        self.auth = auth_service
        self.config = config_manager
        
        container = tk.Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)
        
        self.frames = {}
        for F in (LoginFrame, PinFrame, DashboardFrame, SettingsFrame, ConsentFrame, DataViewerFrame, SubscriptionFrame, PlansFrame):
            frame = F(container, self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")
            
        self.attempt_auto_login()

    def attempt_auto_login(self):
        """
        This is the new startup logic. It decides which page
        to show first: Consent, PIN, or Login.
        """
        if not consent_manager.has_user_consented():
            self.show_frame(ConsentFrame)
            return

        settings = self.config.get_settings()
        pin_status = self.auth.check_login_state()
        
        if pin_status == 'show_pin':
            log.info("PIN is valid. Showing PIN screen.")
            self.show_frame(PinFrame)
        
        elif pin_status == 'show_login_expired':
            log.info("PIN expired. Showing manual login.")
            self.show_frame(LoginFrame)
            days = settings['user']['login_expiry_hours'] // 24
            self.frames[LoginFrame].set_status_message(
                f"Your {days}-day PIN session has expired. Please log in with email/password.", "blue"
            )
            
        else: # 'show_login_normal'
            log.info("PIN not enabled or not set. Showing manual login.")
            self.show_frame(LoginFrame)
        
        if self.start_in_emergency_mode:
            # In emergency mode, prioritize PIN if enabled (faster for user)
            if pin_status == 'show_pin':
                log.info("EMERGENCY MODE: Showing PIN screen first (faster for user)")
                self.frames[PinFrame].set_emergency_mode()
            else:
                log.info("EMERGENCY MODE: PIN not available, showing email/password login")
                self.frames[LoginFrame].set_emergency_mode()

    def show_frame(self, cont, setup_mode=False, sub_data=None):
        frame = self.frames[cont]
        if hasattr(frame, 'on_show'):
            if cont == PinFrame:
                frame.on_show(setup_mode=setup_mode)
            elif cont == SubscriptionFrame:
                frame.on_show(sub_data=sub_data)
            else:
                frame.on_show() # For Dashboard, Settings, Plans
        frame.tkraise()
        
    def post_login_setup(self):
        """Called after a successful login (or PIN entry)."""
        self.frames[DashboardFrame].on_show()
        self.frames[SettingsFrame].on_show()
        self.frames[PlansFrame].on_show()
        
        start_hotkey_listener(self)
        
        # Process any queued emergency alerts on startup
        try:
            from emergency_alert_manager import process_emergency_queue
            threading.Thread(target=process_emergency_queue, daemon=True).start()
        except Exception as e:
            log.error(f"Failed to process emergency queue on startup: {e}")
        
        settings = self.config.get_settings()
        if settings["user"].get("was_running", False):
            log.info("App was running on last exit. Auto-starting monitoring...")
            try:
                self.frames[DashboardFrame].start_monitoring()
            except Exception as e:
                log.error(f"Failed to auto-start monitoring: {e}")
        
        log.info("Running update check in background...")
        threading.Thread(target=self.check_for_updates, daemon=True).start()

    def check_for_updates(self):
        if "YOUR_USERNAME" in VERSION_CHECK_URL:
            log.warning("VERSION_CHECK_URL is not set. Skipping update check.")
            return
        try:
            response = requests.get(VERSION_CHECK_URL, timeout=5)
            if response.status_code != 200:
                log.error(f"Update check failed. Server returned {response.status_code}")
                return
            data = response.json()
            latest_version_str = data.get("latest_version")
            download_url = data.get("download_url")
            if not latest_version_str or not download_url:
                log.error("Update check failed. version.json is malformed.")
                return
            current_ver = version.parse(CURRENT_APP_VERSION)
            latest_ver = version.parse(latest_version_str)
            if latest_ver > current_ver:
                log.info(f"New version found! Latest: {latest_ver}, Current: {current_ver}")
                self.after(0, self.show_update_popup, latest_version_str, download_url)
            else:
                log.info("App is up to date.")
        except Exception as e:
            log.error(f"Error during update check: {e}")

    def show_update_popup(self, version_str, url):
        if messagebox.askyesno("Update Available",
            f"A new version of eMonitor ({version_str}) is available.\n\n"
            "Do you want to go to the download page now?"):
            log.info(f"User accepted update. Opening: {url}")
            webbrowser.open(url)
        else:
            log.info("User declined update.")

    def master_quit(self):
        log.info("Master quit called. Shutting down all services.")
        allow_sleep()
        try:
            self.frames[DashboardFrame].stop_monitoring()
        except Exception as e:
            log.error(f"Error during stop_monitoring: {e}")
        try:
            self.frames[DataViewerFrame].cleanup_temp_file()
        except Exception as e:
            log.error(f"Error during temp file cleanup: {e}")
        stop_hotkey_listener()
        cv2.destroyAllWindows()
        try:
            pygame.mixer.quit()
        except Exception as e:
            log.error(f"Error quitting pygame: {e}")
        self.quit()