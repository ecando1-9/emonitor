import logging
import sys
from logging.handlers import RotatingFileHandler
import io

def setup_logging():
    """Configures the application's logger."""
    
    logger = logging.getLogger("eMonitor")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if logger.hasHandlers():
        return logger

    # Determine log path
    import os
    
    # REPLICATE APPDATA LOGIC TO AVOID CIRCULAR IMPORT WITH CONFIG.PY
    if sys.platform == "win32":
        app_data_roaming = os.getenv('APPDATA')
        if app_data_roaming:
            data_dir = os.path.join(app_data_roaming, "eMonitor", "app_data")
        else:
            data_dir = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "eMonitor", "app_data")
    else:
        data_dir = os.path.join(os.path.expanduser("~"), ".eMonitor", "app_data")
        
    if not os.path.exists(data_dir):
        try:
            os.makedirs(data_dir)
        except OSError:
            # Emergency (temp)
            import tempfile
            data_dir = os.path.join(tempfile.gettempdir(), "eMonitorLogs")
            if not os.path.exists(data_dir): os.makedirs(data_dir)
            
    log_path = os.path.join(data_dir, 'emoniter.log')

    # File Handler
    # File Handler
    # DEBUG PROBE: Write a raw file to confirm path is writable
    try:
        debug_probe = os.path.join(data_dir, "logger_debug_probe.txt")
        with open(debug_probe, "w") as f:
            f.write(f"Logger initializing at {log_path}\nDirectory exists: {os.path.exists(data_dir)}")
    except Exception as e:
        pass

    try:
        file_handler = RotatingFileHandler(
            log_path, 
            maxBytes=2*1024*1024, 
            backupCount=3,
            encoding='utf-8'
        )
    except PermissionError:
        # If main file is locked (e.g., by main app), use a separate file for this process
        log_path = os.path.join(data_dir, f'emoniter_trigger_{os.getpid()}.log')
        file_handler = RotatingFileHandler(
            log_path, 
            maxBytes=2*1024*1024, 
            backupCount=3,
            encoding='utf-8'
        )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Console Handler
    # Only add console handler if we have a stdout (not running in --noconsole mode)
    if sys.stdout is not None:
        if sys.platform == 'win32':
            try:
                # Use UTF-8 wrapper for Windows console
                # This fixes the UnicodeEncodeError when logging emojis on Windows
                stream = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            except AttributeError:
                # sys.stdout might not have .buffer in some environments
                stream = sys.stdout
        else:
            stream = sys.stdout
            
        console_handler = logging.StreamHandler(stream)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    return logger

log = setup_logging()