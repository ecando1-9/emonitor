import tkinter as tk
from tkinter import ttk
from logger_setup import log
from config import config_manager

class GracePeriodWindow(tk.Toplevel):
    """
    A popup window that shows a countdown before sending an alert.
    """
    def __init__(self, parent, on_cancel, on_confirm):
        super().__init__(parent)
        self.title("Emergency Alert")
        self.geometry("400x250")
        # Allow this window to be minimized/maximized independently
        # Do not set transient or grab so it can be minimized to taskbar
        self.resizable(True, True)
        
        self.on_cancel_callback = on_cancel
        self.on_confirm_callback = on_confirm
        
        self.countdown = config_manager.get_settings()["emergency"]["grace_period_sec"]
        
        # Style - Dark background for emergency alert
        self.configure(bg="#1a1a1a")
        # Small in-window controls for minimize / maximize
        self._is_maximized = False
        header_frame = tk.Frame(self, bg="#1a1a1a")
        header_frame.pack(fill="x", side="top", anchor="ne")
        # Minimize button
        self.btn_minimize = tk.Button(header_frame, text="_", width=3, command=self.iconify, bg="#1a1a1a", fg="white", bd=0)
        self.btn_minimize.pack(side="right", padx=(0,4), pady=4)
        # Maximize / Restore toggle
        self.btn_maximize = tk.Button(header_frame, text="▢", width=3, command=self.toggle_maximize, bg="#1a1a1a", fg="white", bd=0)
        self.btn_maximize.pack(side="right", padx=(0,4), pady=4)
        style = ttk.Style()
        style.configure("Emergency.TLabel", font=("Arial", 16), foreground="white", background="#1a1a1a")
        style.configure("Countdown.TLabel", font=("Arial", 48, "bold"), foreground="#FF4444", background="#1a1a1a")
        
        # Configure cancel button style with visible colors
        style.configure("Cancel.TButton", 
                       font=("Arial", 14, "bold"),
                       foreground="white",
                       background="#DC143C",  # Crimson red
                       borderwidth=3,
                       relief="raised",
                       padding=15)
        style.map("Cancel.TButton",
                 background=[("active", "#B22222"), ("pressed", "#8B0000")],
                 foreground=[("active", "white"), ("pressed", "white")])

        self.lbl_title = ttk.Label(self, text="Emergency Alert Triggered!", style="Emergency.TLabel")
        self.lbl_title.pack(pady=(20, 10))
        
        self.lbl_countdown = ttk.Label(self, text=str(self.countdown), style="Countdown.TLabel")
        self.lbl_countdown.pack(pady=10)
        
        self.lbl_info = ttk.Label(self, text="Grace period countdown...\nClick CANCEL to stop the alert.", style="Emergency.TLabel")
        self.lbl_info.pack(pady=5)
        
        # Make window stay on top initially, but allow it to be moved behind after sent
        self.attributes('-topmost', True)
        
        # Use tk.Button instead of ttk.Button for better color control
        self.btn_cancel = tk.Button(
            self,
            text="✕ CANCEL ALERT ✕",
            command=self.on_cancel_callback,
            font=("Arial", 14, "bold"),
            bg="#DC143C",  # Crimson red background
            fg="white",  # White text
            activebackground="#B22222",  # Darker red when pressed
            activeforeground="white",
            relief="raised",
            bd=3,
            padx=30,
            pady=12,
            cursor="hand2"
        )
        self.btn_cancel.pack(pady=20)
        
        self.alert_sent = False  # Track if alert has been sent
        self.protocol("WM_DELETE_WINDOW", self.handle_window_close) # Handle "X" button
        
        # Start the countdown
        self.update_countdown()

    def update_countdown(self):
        if self.countdown > 0:
            self.lbl_countdown.config(text=str(self.countdown))
            self.countdown -= 1
            self.after(1000, self.update_countdown) # Run again after 1 second
        else:
            # Time's up! Send the alert.
            self.alert_sent = True  # Mark that alert has been sent
            self.lbl_countdown.config(text="✓ SENT", foreground="#00FF00")  # Green color
            self.lbl_info.config(text="✓ Alert sent successfully!\n\nEmergency mode is now ACTIVE.\nData is being collected and sent every 30 seconds.\n\nYou can stop emergency mode from the Dashboard.")
            self.btn_cancel.config(state="disabled", text="✕ ALERT SENT - CANNOT CANCEL")
            self.on_confirm_callback() # Call the send function
            
            # Allow window to be closed after alert is sent
            self.attributes('-topmost', False)  # Allow window to go behind others
            
            # Change cancel button to a "Close" button after a short delay
            self.after(2000, self.show_close_button)
    
    def show_close_button(self):
        """Change the cancel button to a close button after alert is sent"""
        try:
            if self.alert_sent:
                # Alert was sent - change button to allow closing
                self.btn_cancel.config(
                    state="normal",
                    text="✓ CLOSE WINDOW",
                    command=self.close_window,
                    bg="#4CAF50",  # Green
                    activebackground="#45a049",
                    fg="white"
                )
        except Exception as e:
            log.error("Error updating grace period window")
            log.debug(f"Grace period window error: {e}")
    
    def handle_window_close(self):
        """Handle window close attempt - allow closing after alert is sent"""
        if self.alert_sent:
            # Alert already sent, allow closing
            self.destroy()
        else:
            # Alert not sent yet, cancel it
            self.on_cancel_callback()
    
    def close_window(self):
        """Close the grace period window"""
        self.destroy()

    def toggle_maximize(self):
        """Toggle between normal and maximized window states."""
        try:
            if getattr(self, "_is_maximized", False):
                try:
                    self.state('normal')
                except Exception:
                    # Fallback: restore to a sensible size
                    self.geometry("400x250")
                self._is_maximized = False
                try:
                    self.btn_maximize.config(text="▢")
                except Exception:
                    pass
            else:
                try:
                    self.state('zoomed')
                except Exception:
                    # Fallback to manual full-screen geometry
                    w = self.winfo_screenwidth()
                    h = self.winfo_screenheight()
                    self.geometry(f"{w}x{h}+0+0")
                self._is_maximized = True
                try:
                    self.btn_maximize.config(text="❐")
                except Exception:
                    pass
        except Exception as e:
            log.debug(f"Error toggling maximize on grace window: {e}")