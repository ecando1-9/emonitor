"""
Emergency Email Interval Setting Widget
Add this to your Emergency Alert settings page
"""

import tkinter as tk
from tkinter import ttk, messagebox

def create_email_interval_setting(parent_frame, config_manager):
    """
    Creates a setting widget for emergency email interval.
    
    Args:
        parent_frame: The parent tkinter frame
        config_manager: Config manager instance
        
    Returns:
        tuple: (frame, get_value_func, set_value_func)
    """
    
    # Main frame
    interval_frame = ttk.LabelFrame(
        parent_frame,
        text="📧 Email Update Interval",
        padding=15
    )
    
    # Description
    desc_label = ttk.Label(
        interval_frame,
        text="How often should emergency emails be sent during active emergency mode?",
        font=("Arial", 10),
        wraplength=500
    )
    desc_label.pack(anchor="w", pady=(0, 10))
    
    # Slider frame
    slider_frame = ttk.Frame(interval_frame)
    slider_frame.pack(fill="x", pady=10)
    
    # Current value label
    value_var = tk.StringVar(value="30 seconds")
    value_label = ttk.Label(
        slider_frame,
        textvariable=value_var,
        font=("Arial", 12, "bold"),
        foreground="#2196F3"
    )
    value_label.pack(pady=(0, 5))
    
    # Slider
    slider_var = tk.IntVar(value=30)
    
    def update_label(val):
        seconds = int(float(val))
        if seconds < 60:
            value_var.set(f"{seconds} seconds")
        else:
            minutes = seconds // 60
            remaining_secs = seconds % 60
            if remaining_secs == 0:
                value_var.set(f"{minutes} minute{'s' if minutes > 1 else ''}")
            else:
                value_var.set(f"{minutes}m {remaining_secs}s")
    
    slider = ttk.Scale(
        slider_frame,
        from_=5,
        to=300,
        orient="horizontal",
        variable=slider_var,
        command=update_label
    )
    slider.pack(fill="x", padx=20)
    
    # Min/Max labels
    limits_frame = ttk.Frame(slider_frame)
    limits_frame.pack(fill="x", padx=20)
    
    ttk.Label(
        limits_frame,
        text="⚡ 5 sec (Fast)",
        font=("Arial", 8),
        foreground="green"
    ).pack(side="left")
    
    ttk.Label(
        limits_frame,
        text="🐢 5 min (Slow)",
        font=("Arial", 8),
        foreground="orange"
    ).pack(side="right")
    
    # Recommendations
    rec_frame = ttk.Frame(interval_frame)
    rec_frame.pack(fill="x", pady=10)
    
    ttk.Label(
        rec_frame,
        text="💡 Recommendations:",
        font=("Arial", 9, "bold")
    ).pack(anchor="w")
    
    recommendations = [
        "• 5-15 seconds: Critical emergencies (kidnapping, assault)",
        "• 30 seconds: Balanced (Good and fast, recommended for most situations)",
        "• 60-120 seconds: Battery saving mode",
        "• 180-300 seconds: Low priority monitoring"
    ]
    
    for rec in recommendations:
        ttk.Label(
            rec_frame,
            text=rec,
            font=("Arial", 8),
            foreground="#666"
        ).pack(anchor="w", padx=20)
    
    # Warning
    warning_label = ttk.Label(
        interval_frame,
        text="⚠️ Shorter intervals = More emails = Better evidence, but uses more data/battery",
        font=("Arial", 8, "italic"),
        foreground="#FF6B00",
        wraplength=500
    )
    warning_label.pack(pady=(10, 0))
    
    # Functions to get/set value
    def get_value():
        return slider_var.get()
    
    def set_value(seconds):
        slider_var.set(seconds)
        update_label(seconds)
    
    # Load current value from config
    try:
        settings = config_manager.get_settings()
        current_interval = settings.get("emergency", {}).get("email_interval_seconds", 30)
        set_value(current_interval)
    except Exception:
        set_value(30)  # Default
    
    return interval_frame, get_value, set_value


# Example usage in settings page:
if __name__ == "__main__":
    # Demo window
    root = tk.Tk()
    root.title("Emergency Email Interval Setting Demo")
    root.geometry("600x500")
    
    # Mock config manager
    class MockConfig:
        def get_settings(self):
            return {"emergency": {"email_interval_seconds": 30}}
    
    config = MockConfig()
    
    # Create setting
    frame, get_val, set_val = create_email_interval_setting(root, config)
    frame.pack(fill="both", expand=True, padx=20, pady=20)
    
    # Test button
    def show_value():
        messagebox.showinfo("Current Value", f"Email interval: {get_val()} seconds")
    
    ttk.Button(root, text="Show Current Value", command=show_value).pack(pady=10)
    
    root.mainloop()
