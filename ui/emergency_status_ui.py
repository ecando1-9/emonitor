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
        self.title("*** EMERGENCY MODE ACTIVE ***")
        self.geometry("700x500")
        self.transient(parent)
        self.resizable(True, True)  # Make window resizable
        self.minsize(600, 400)  # Set minimum size
        
        # Make window always on top
        self.attributes('-topmost', True)
        
        # Add a Maximize/Restore button frame
        control_frame = tk.Frame(self, bg="#8B0000")
        control_frame.pack(fill="x", side="top", anchor="e", padx=5, pady=5)

        self.maximized = False
        self.btn_maximize = tk.Button(
            control_frame,
            text="Maximize [ ]",
            command=self.toggle_maximize,
            font=("Arial", 9),
            bg="#FF6B35",
            fg="white",
            relief="raised"
        )
        self.btn_maximize.pack(side="right")

        # Style - Red/Orange background for emergency
        self.configure(bg="#8B0000")
        
        # Main container - make it expandable and configure for resizing
        main_frame = tk.Frame(self, bg="#8B0000")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = tk.Label(
            main_frame,
            text="*** EMERGENCY MODE ACTIVE ***",
            font=("Arial", 18, "bold"),
            bg="#8B0000",
            fg="white"
        )
        title_label.pack(pady=(10, 20))
        
        # Status info - make it more detailed and expandable
        info_text = """Emergency alert has been triggered and is actively collecting data.

Data is being sent every 15 seconds to:
• Emergency contacts
• Admin email
• Emergency email

All monitoring features are enabled:
• Screen recording
• Camera capture
• Activity monitoring
• Location tracking
• Telemetry data"""
        
        # Use a frame for info text that can expand
        info_frame = tk.Frame(main_frame, bg="#8B0000")
        info_frame.pack(fill="both", expand=True, pady=15, padx=20)
        
        info_label = tk.Label(
            info_frame,
            text=info_text,
            font=("Arial", 12),
            bg="#8B0000",
            fg="white",
            justify="left",
            wraplength=600
        )
        info_label.pack(anchor="w")
        
        # Update wraplength when window is resized
        def update_wraplength(event=None):
            if event:
                new_width = max(400, event.width - 80)  # Account for padding
                info_label.config(wraplength=new_width)
        
        self.bind('<Configure>', update_wraplength)
        
        # Timer label (shows how long emergency has been active)
        self.timer_label = tk.Label(
            main_frame,
            text="Active for: 0 seconds",
            font=("Arial", 12, "bold"),
            bg="#8B0000",
            fg="#FFD700"  # Gold color
        )
        self.timer_label.pack(pady=10)
        
        # Add separator before cancel button
        separator = tk.Frame(main_frame, bg="#FF6B35", height=2)
        separator.pack(fill="x", pady=20, padx=20)
        
        # Cancel button - Large and very prominent
        cancel_button = tk.Button(
            main_frame,
            text="[STOP] CANCEL / STOP EMERGENCY MODE [STOP]",
            command=self.stop_emergency,
            font=("Arial", 18, "bold"),
            bg="#FF6B35",  # Orange-red
            fg="white",
            activebackground="#E55A2B",
            activeforeground="white",
            relief="raised",
            bd=5,
            padx=50,
            pady=20,
            cursor="hand2",
            highlightthickness=3,
            highlightbackground="#FFD700",
            highlightcolor="#FFD700"
        )
        cancel_button.pack(pady=25, padx=20, fill="x", expand=True)
        
        # Warning text - make it more visible
        warning_label = tk.Label(
            main_frame,
            text="!!! Click the button above to cancel and stop emergency mode !!!",
            font=("Arial", 12, "bold"),
            bg="#8B0000",
            fg="#FFD700"
        )
        warning_label.pack(pady=10)
        
        # Start timer
        self.start_time = time.time()
        self.update_timer()
        
        # Handle window close - don't allow closing without stopping emergency
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def toggle_maximize(self):
        """Toggle maximize state"""
        if self.maximized:
            # Restore
            self.state('normal')
            self.btn_maximize.config(text="Maximize [ ]")
            self.maximized = False
        else:
            # Maximize
            self.state('zoomed')
            self.btn_maximize.config(text="Restore [-]")
            self.maximized = True
    
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

