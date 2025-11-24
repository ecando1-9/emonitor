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
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)
        
        self.on_cancel_callback = on_cancel
        self.on_confirm_callback = on_confirm
        
        self.countdown = config_manager.get_settings()["emergency"]["grace_period_sec"]
        
        # Style - Dark background for emergency alert
        self.configure(bg="#1a1a1a")
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
        
        self.lbl_info = ttk.Label(self, text="Sending alert to admin and emergency contacts...", style="Emergency.TLabel")
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
            self.btn_cancel.config(state="disabled", text="✕ ALERT SENT - CANNOT CANCEL")
            self.lbl_info.config(text="✓ Alert sent successfully!\n\nEmergency mode is now ACTIVE.\nData is being collected and sent every 15 seconds.\n\nYou can stop emergency mode from the Dashboard or the status window.\n\nYou can close this window now.")
            self.on_confirm_callback() # Call the send function
            
            # Allow window to be closed after alert is sent
            self.attributes('-topmost', False)  # Allow window to go behind others
            
            # Don't close the window - keep it open to show sent status
            # Change cancel button to a "Close" button after a delay
            self.after(3000, self.show_close_button)
    
    def show_close_button(self):
        """Change the cancel button to a close button after alert is sent"""
        try:
            from emergency_alert_manager import is_emergency_active
            if is_emergency_active():
                # Emergency is active - change button to show how to stop
                self.btn_cancel.config(
                    state="normal",
                    text="✓ Alert Sent - Go to Dashboard to Stop",
                    command=self.close_window,
                    bg="#4CAF50",  # Green
                    fg="white"
                )
            else:
                # Emergency was cancelled somehow - just close
                self.close_window()
        except Exception as e:
            log.error(f"Error updating grace period window: {e}")
            self.close_window()
    
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