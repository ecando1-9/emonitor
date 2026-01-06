"""
GPS Permission Helper
Prompts user to enable Windows Location Services when GPS features are enabled
"""

import tkinter as tk
from tkinter import messagebox
import subprocess
import os
from logger_setup import log

def check_location_services_enabled():
    """Check if Windows Location Services are enabled."""
    try:
        # Check Windows Registry for location services
        import winreg
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location"
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(key, "Value")
        winreg.CloseKey(key)
        return value == "Allow"
    except Exception as e:
        log.debug(f"Could not check location services status: {e}")
        return None  # Unknown

def open_windows_location_settings():
    """Open Windows Location Settings."""
    try:
        # Windows 10/11 Settings URI
        subprocess.Popen(['start', 'ms-settings:privacy-location'], shell=True)
        return True
    except Exception as e:
        log.error(f"Failed to open location settings: {e}")
        return False

def show_gps_permission_prompt(parent=None):
    """Show GPS permission prompt dialog."""
    
    # Check if already enabled
    location_enabled = check_location_services_enabled()
    if location_enabled:
        log.info("GPS: Location services already enabled")
        return True
    
    # Create custom dialog
    dialog = tk.Toplevel(parent) if parent else tk.Tk()
    dialog.title("GPS Permission Required")
    dialog.geometry("500x400")
    dialog.resizable(False, False)
    
    # Make it modal
    dialog.transient(parent)
    dialog.grab_set()
    
    # Center on screen
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() // 2) - (500 // 2)
    y = (dialog.winfo_screenheight() // 2) - (400 // 2)
    dialog.geometry(f"500x400+{x}+{y}")
    
    # Icon and title
    title_frame = tk.Frame(dialog, bg="#2196F3", height=80)
    title_frame.pack(fill="x")
    title_frame.pack_propagate(False)
    
    title_label = tk.Label(
        title_frame,
        text="📍 GPS Permission Required",
        font=("Arial", 16, "bold"),
        bg="#2196F3",
        fg="white"
    )
    title_label.pack(expand=True)
    
    # Content frame
    content_frame = tk.Frame(dialog, bg="white", padx=30, pady=20)
    content_frame.pack(fill="both", expand=True)
    
    # Message
    message = tk.Label(
        content_frame,
        text="You've enabled location tracking features.\n\n"
             "To use GPS location data, please enable\n"
             "Windows Location Services:",
        font=("Arial", 11),
        bg="white",
        justify="left"
    )
    message.pack(pady=(0, 20))
    
    # Instructions
    instructions_frame = tk.Frame(content_frame, bg="#f5f5f5", relief="solid", borderwidth=1)
    instructions_frame.pack(fill="x", pady=10)
    
    instructions = [
        "1. Click 'Open Settings' below",
        "2. Turn ON 'Location services'",
        "3. Allow apps to access your location",
        "4. Return to eMonitor"
    ]
    
    for i, instruction in enumerate(instructions, 1):
        lbl = tk.Label(
            instructions_frame,
            text=instruction,
            font=("Arial", 10),
            bg="#f5f5f5",
            anchor="w",
            padx=15,
            pady=5
        )
        lbl.pack(fill="x")
    
    # Note
    note = tk.Label(
        content_frame,
        text="Note: Location data is only used for emergency alerts\n"
             "and scheduled reports. Your privacy is protected.",
        font=("Arial", 9, "italic"),
        bg="white",
        fg="#666",
        justify="left"
    )
    note.pack(pady=(10, 20))
    
    # Buttons
    button_frame = tk.Frame(content_frame, bg="white")
    button_frame.pack(fill="x")
    
    def on_open_settings():
        if open_windows_location_settings():
            messagebox.showinfo(
                "Settings Opened",
                "Windows Location Settings opened.\n\n"
                "After enabling location services, click 'Done' to continue.",
                parent=dialog
            )
        else:
            messagebox.showerror(
                "Error",
                "Could not open settings automatically.\n\n"
                "Please open Settings manually:\n"
                "Settings → Privacy → Location",
                parent=dialog
            )
    
    def on_done():
        # Re-check if enabled
        if check_location_services_enabled():
            messagebox.showinfo(
                "Success",
                "✅ Location services are enabled!\n\n"
                "GPS features will now work correctly.",
                parent=dialog
            )
            dialog.destroy()
        else:
            result = messagebox.askyesno(
                "Location Not Enabled",
                "Location services are still disabled.\n\n"
                "GPS features may not work correctly.\n\n"
                "Continue anyway?",
                parent=dialog,
                icon="warning"
            )
            if result:
                dialog.destroy()
    
    def on_remind_later():
        dialog.destroy()
    
    btn_open = tk.Button(
        button_frame,
        text="📍 Open Settings",
        command=on_open_settings,
        font=("Arial", 11, "bold"),
        bg="#2196F3",
        fg="white",
        activebackground="#1976D2",
        activeforeground="white",
        relief="flat",
        padx=20,
        pady=10,
        cursor="hand2"
    )
    btn_open.pack(side="left", padx=5)
    
    btn_done = tk.Button(
        button_frame,
        text="✓ Done",
        command=on_done,
        font=("Arial", 11),
        bg="#4CAF50",
        fg="white",
        activebackground="#45a049",
        activeforeground="white",
        relief="flat",
        padx=20,
        pady=10,
        cursor="hand2"
    )
    btn_done.pack(side="left", padx=5)
    
    btn_later = tk.Button(
        button_frame,
        text="Remind Later",
        command=on_remind_later,
        font=("Arial", 11),
        bg="#9E9E9E",
        fg="white",
        activebackground="#757575",
        activeforeground="white",
        relief="flat",
        padx=20,
        pady=10,
        cursor="hand2"
    )
    btn_later.pack(side="left", padx=5)
    
    # Handle window close
    dialog.protocol("WM_DELETE_WINDOW", on_remind_later)
    
    # Wait for dialog to close
    if parent:
        dialog.wait_window()
    else:
        dialog.mainloop()
    
    return check_location_services_enabled()

if __name__ == "__main__":
    # Test the GPS prompt
    result = show_gps_permission_prompt()
    print(f"Location services enabled: {result}")
