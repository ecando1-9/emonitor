import tkinter as tk
from tkinter import ttk
from logger_setup import log
import threading
import time

class EmergencyStatusWindow(tk.Toplevel):
    """
    A persistent window that shows emergency mode is active and provides a cancel button.
    This window stays visible until emergency mode is stopped.
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.title("⚠️ EMERGENCY MODE ACTIVE ⚠️")
        self.geometry("450x300")
        self.transient(parent)
        self.resizable(False, False)
        
        # Make window always on top
        self.attributes('-topmost', True)
        
        # Style - Red/Orange background for emergency
        self.configure(bg="#8B0000")
        
        # Main container
        main_frame = tk.Frame(self, bg="#8B0000")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title
        title_label = tk.Label(
            main_frame,
            text="⚠️ EMERGENCY MODE ACTIVE ⚠️",
            font=("Arial", 18, "bold"),
            bg="#8B0000",
            fg="white"
        )
        title_label.pack(pady=(10, 20))
        
        # Status info
        info_text = """Emergency alert has been triggered and is actively collecting data.

Data is being sent every 15 seconds to:
• Emergency contacts
• Admin email
• Emergency email

All monitoring features are enabled."""
        
        info_label = tk.Label(
            main_frame,
            text=info_text,
            font=("Arial", 11),
            bg="#8B0000",
            fg="white",
            justify="left",
            wraplength=400
        )
        info_label.pack(pady=10)
        
        # Timer label (shows how long emergency has been active)
        self.timer_label = tk.Label(
            main_frame,
            text="Active for: 0 seconds",
            font=("Arial", 12, "bold"),
            bg="#8B0000",
            fg="#FFD700"  # Gold color
        )
        self.timer_label.pack(pady=10)
        
        # Cancel button - Large and prominent
        cancel_button = tk.Button(
            main_frame,
            text="⛔ STOP EMERGENCY MODE ⛔",
            command=self.stop_emergency,
            font=("Arial", 16, "bold"),
            bg="#FF6B35",  # Orange-red
            fg="white",
            activebackground="#E55A2B",
            activeforeground="white",
            relief="raised",
            bd=4,
            padx=40,
            pady=15,
            cursor="hand2"
        )
        cancel_button.pack(pady=20)
        
        # Warning text
        warning_label = tk.Label(
            main_frame,
            text="Click the button above to stop emergency mode",
            font=("Arial", 10, "italic"),
            bg="#8B0000",
            fg="#FFD700"
        )
        warning_label.pack(pady=5)
        
        # Start timer
        self.start_time = time.time()
        self.update_timer()
        
        # Handle window close - don't allow closing without stopping emergency
        self.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def update_timer(self):
        """Update the timer showing how long emergency has been active"""
        try:
            from emergency_alert_manager import is_emergency_active
            if is_emergency_active():
                elapsed = int(time.time() - self.start_time)
                minutes = elapsed // 60
                seconds = elapsed % 60
                if minutes > 0:
                    self.timer_label.config(text=f"Active for: {minutes}m {seconds}s")
                else:
                    self.timer_label.config(text=f"Active for: {seconds} seconds")
                # Update every second
                self.after(1000, self.update_timer)
            else:
                # Emergency stopped, close window
                self.destroy()
        except Exception as e:
            log.error(f"Error updating timer: {e}")
            # Still try to update
            self.after(1000, self.update_timer)
    
    def stop_emergency(self):
        """Stop emergency mode"""
        try:
            from emergency_alert_manager import stop_emergency_mode
            from tkinter import messagebox
            
            # Ask for confirmation
            result = messagebox.askyesno(
                "Stop Emergency Mode?",
                "Are you sure you want to stop emergency mode?\n\n"
                "This will:\n"
                "• Stop all data collection\n"
                "• Send final data update\n"
                "• Restore normal monitoring settings",
                icon="warning"
            )
            
            if result:
                stop_emergency_mode()
                messagebox.showinfo("Emergency Stopped", "Emergency mode has been stopped successfully.")
                self.destroy()
        except Exception as e:
            log.error(f"Error stopping emergency: {e}")
            from tkinter import messagebox
            messagebox.showerror("Error", f"Failed to stop emergency mode: {e}")
    
    def on_close(self):
        """Handle window close attempt"""
        from tkinter import messagebox
        result = messagebox.askyesno(
            "Emergency Mode Active",
            "Emergency mode is still active!\n\n"
            "You cannot close this window while emergency mode is active.\n"
            "Please click 'STOP EMERGENCY MODE' to stop it first.",
            icon="warning"
        )
        # Don't close the window - keep it open

# Global reference to the status window
_emergency_status_window = None

def show_emergency_status_window(parent):
    """Show the emergency status window"""
    global _emergency_status_window
    try:
        if _emergency_status_window is None or not _emergency_status_window.winfo_exists():
            _emergency_status_window = EmergencyStatusWindow(parent)
            log.info("Emergency status window opened")
        else:
            # Window already exists, just bring it to front
            _emergency_status_window.lift()
            _emergency_status_window.focus_force()
    except Exception as e:
        log.error(f"Error showing emergency status window: {e}")

def close_emergency_status_window():
    """Close the emergency status window"""
    global _emergency_status_window
    try:
        if _emergency_status_window and _emergency_status_window.winfo_exists():
            _emergency_status_window.destroy()
            _emergency_status_window = None
            log.info("Emergency status window closed")
    except Exception as e:
        log.error(f"Error closing emergency status window: {e}")

