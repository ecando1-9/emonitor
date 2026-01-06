import pygetwindow as gw
import time
import os
import json
from config import config_manager, DATA_DIR
from logger_setup import log

OUTPUT_DIR = os.path.join(DATA_DIR, "captures")

def get_device_name_and_time():
    try:
        device_name = config_manager.get_settings()["user"]["device_name"]
    except Exception:
        device_name = "My-Computer"
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    return device_name, timestamp

def get_running_applications():
    """Get list of all running applications (visible in taskbar)."""
    try:
        running_apps = []
        seen_names = set()
        
        # Get all visible windows
        all_windows = gw.getAllWindows()
        for window in all_windows:
            if window.title and window.visible and window.title.strip():
                # Skip empty titles and system windows
                if window.title not in seen_names:
                    running_apps.append({
                        "title": window.title,
                        "is_active": window == gw.getActiveWindow()
                    })
                    seen_names.add(window.title)
        
        return running_apps
    except Exception as e:
        log.error(f"Error getting running applications: {e}")
        return []

def get_active_window_data():
    """Instantly gets the active window title as a string."""
    try:
        active_window = gw.getActiveWindow()
        title = active_window.title if active_window else "No active window"
        return title
    except Exception as e:
        log.error(f"Error getting active window data: {e}")
        return "Error: Could not get window title"

def get_comprehensive_activity_summary():
    """Get comprehensive activity summary including active window and all running apps."""
    try:
        active_window = get_active_window_data()
        running_apps = get_running_applications()
        
        # Create summary text
        summary = f"Active Window: {active_window}\n\n"
        
        if running_apps:
            summary += f"Running Applications ({len(running_apps)}):\n"
            for i, app in enumerate(running_apps[:20], 1):  # Limit to 20 apps
                status = "🔴 ACTIVE" if app.get("is_active") else ""
                summary += f"{i}. {app['title']} {status}\n"
        else:
            summary += "No running applications detected\n"
        
        return summary
    except Exception as e:
        log.error(f"Error getting comprehensive activity: {e}")
        return f"Active Window: {get_active_window_data()}"

def capture_active_window():
    """ Captures the title of the currently active window and all running apps to a file"""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    try:
        device_name, timestamp = get_device_name_and_time()
        filename = os.path.join(OUTPUT_DIR, f"{device_name} - Activity - {timestamp}.json")
        
        active_window = get_active_window_data()
        running_apps = get_running_applications()
        
        data = {
            "timestamp": time.time(),
            "active_window_title": active_window,
            "running_applications": running_apps,
            "summary": get_comprehensive_activity_summary()
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
        
        log.info(f"Activity captured: {active_window} + {len(running_apps)} running apps")
        return filename
    except Exception as e:
        log.error(f"Error capturing active window: {e}")
        return None