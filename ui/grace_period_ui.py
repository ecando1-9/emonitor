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
        
        self.protocol("WM_DELETE_WINDOW", self.on_cancel_callback) # Handle "X" button
        
        # Start the countdown
        self.update_countdown()

    def update_countdown(self):
        if self.countdown > 0:
            self.lbl_countdown.config(text=str(self.countdown))
            self.countdown -= 1
            self.after(1000, self.update_countdown) # Run again after 1 second
        else:
            # Time's up! Send the alert.
            self.lbl_countdown.config(text="SENDING", foreground="orange")
            self.btn_cancel.config(state="disabled")
            self.lbl_info.config(text="Alert sent! Emergency mode is now active.\nA status window will appear shortly...")
            self.on_confirm_callback() # Call the send function
            # Close window after a short delay to show the message
            self.after(2000, self.destroy) # Close window after 2 seconds