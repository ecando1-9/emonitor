import tkinter as tk
from pystray import Icon as pystray_icon, MenuItem as item
from PIL import Image, ImageDraw
import threading
import os
import sys
import cv2
from ui.main_window import MainWindow
from logger_setup import log



# --- System Tray Icon ---
icon_image = None
tray_icon = None  # Global reference to tray icon

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def create_icon_image():
    """ Creates a simple 16x16 PIL image for the tray icon """
    global icon_image
    try:
        icon_path = resource_path("icon.png")
        icon_image = Image.open(icon_path)
    except FileNotFoundError:
        log.warning("icon.png not found, using fallback.")
        width = 64
        height = 64
        color1 = (255, 0, 0)
        color2 = (0, 0, 0)
        icon_image = Image.new("RGB", (width, height), color2)
        dc = ImageDraw.Draw(icon_image)
        dc.rectangle((width // 2, 0, width, height // 2), fill=color1)
        dc.rectangle((0, height // 2, width // 2, height), fill=color1)
    return icon_image

def show_window(icon, item):
    """ Show the main application window """
    global tray_icon
    # Stop the tray icon (it will be restarted when window is closed)
    if tray_icon:
        tray_icon.stop()
        tray_icon = None
    # Show the window on the main thread
    main_app.after(0, lambda: main_app.deiconify())
    main_app.after(0, lambda: main_app.lift())
    main_app.after(0, lambda: main_app.focus_force())

def quit_app(icon, item):
    """ Quit the application """
    global tray_icon
    if tray_icon:
        tray_icon.stop()
        tray_icon = None
    main_app.after(0, main_app.master_quit)

def setup_tray_icon():
    """ Sets up and runs the system tray icon in a separate thread """
    global tray_icon
    icon_image = create_icon_image()
    menu = (item('Show App', show_window, default=True), item('Quit', quit_app))
    tray_icon = pystray_icon("eMonitor", icon_image, "eMonitor", menu)
    tray_icon.run()
    
def on_close_to_tray():
    """ Hide the window to the tray instead of closing """
    main_app.withdraw()  # Hide window completely (removes from taskbar)
    log.info("Minimizing to system tray.")
    # We only start a new tray icon thread if one isn't already running
    if not any(t.name == "pystray_thread" for t in threading.enumerate()):
        tray_thread = threading.Thread(target=setup_tray_icon, daemon=True, name="pystray_thread")
        tray_thread.start()
    # If tray icon exists but was stopped, restart it
    elif tray_icon is None:
        tray_thread = threading.Thread(target=setup_tray_icon, daemon=True, name="pystray_thread")
        tray_thread.start()

# --- Main Application ---
if __name__ == "__main__":
    try:
        # --- Create PID Lock File ---
        try:
            from config import DATA_DIR
            import atexit
            
            pid_file = os.path.join(DATA_DIR, "app.lock")
            with open(pid_file, 'w') as f:
                f.write(str(os.getpid()))
                
            def cleanup_pid():
                try:
                    if os.path.exists(pid_file):
                        os.remove(pid_file)
                except: pass
            atexit.register(cleanup_pid)
        except Exception as e:
            log.warning(f"Failed to create PID lock file: {e}")
        # ----------------------------
        
        start_in_emergency_mode = False
        start_minimized = False
        
        if "--emergency" in sys.argv:
            log.warning("EMERGENCY SHORTCUT ACTIVATED!")
            start_in_emergency_mode = True
        
        if "--minimized" in sys.argv:
            log.info("Starting in minimized mode (auto-start on boot)")
            start_minimized = True

        main_app = MainWindow(start_in_emergency_mode=start_in_emergency_mode)
        
        # Configure window to hide from taskbar when minimized
        if sys.platform == "win32":
            try:
                # --- Fix Taskbar Icon ---
                import ctypes
                myappid = 'ecantech.emonitor.app.1.0' # Arbitrary string
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
                # ------------------------
                
                # Hide from taskbar when minimized (Windows-specific)
                main_app.attributes('-toolwindow', False)  # Keep as normal window
                # Use withdraw/iconify to hide from taskbar properly
            except Exception as e:
                log.warning(f"Could not set window attributes: {e}")
        
        # When you click the "X" button, it now minimizes to tray
        main_app.protocol("WM_DELETE_WINDOW", on_close_to_tray)
        
        # If starting minimized (auto-start), hide window and show tray immediately
        if start_minimized:
            log.info("Hiding window and starting tray icon for auto-start mode")
            main_app.withdraw()  # Hide window completely
            # Start tray icon immediately
            if not any(t.name == "pystray_thread" for t in threading.enumerate()):
                tray_thread = threading.Thread(target=setup_tray_icon, daemon=True, name="pystray_thread")
                tray_thread.start()
        
        main_app.mainloop()
        
        log.info("Mainloop finished. Running final cleanup.")
        cv2.destroyAllWindows()
        
    except Exception as e:
        import traceback
        err_msg = f"CRITICAL CRASH:\n{traceback.format_exc()}"
        print(err_msg, file=sys.stderr)
        with open("crash_error.txt", "w") as f:
            f.write(err_msg)
        input("App Crashed. Press Enter to exit...")
    log.info("Application shut down.")
    if "--minimized" in sys.argv:
        log.info("Starting in minimized mode (auto-start on boot)")
        start_minimized = True

    main_app = MainWindow(start_in_emergency_mode=start_in_emergency_mode)
    
    # Configure window to hide from taskbar when minimized
    if sys.platform == "win32":
        try:
            # --- Fix Taskbar Icon ---
            import ctypes
            myappid = 'ecantech.emonitor.app.1.0' # Arbitrary string
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            # ------------------------
            
            # Hide from taskbar when minimized (Windows-specific)
            main_app.attributes('-toolwindow', False)  # Keep as normal window
            # Use withdraw/iconify to hide from taskbar properly
        except Exception as e:
            log.warning(f"Could not set window attributes: {e}")
    
    # When you click the "X" button, it now minimizes to tray
    main_app.protocol("WM_DELETE_WINDOW", on_close_to_tray)
    
    # If starting minimized (auto-start), hide window and show tray immediately
    if start_minimized:
        log.info("Hiding window and starting tray icon for auto-start mode")
        main_app.withdraw()  # Hide window completely
        # Start tray icon immediately
        if not any(t.name == "pystray_thread" for t in threading.enumerate()):
            tray_thread = threading.Thread(target=setup_tray_icon, daemon=True, name="pystray_thread")
            tray_thread.start()
    
    main_app.mainloop()
    
    log.info("Mainloop finished. Running final cleanup.")
    cv2.destroyAllWindows()
    log.info("Application shut down.")