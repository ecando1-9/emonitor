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
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "app_data")
    if not os.path.exists(data_dir):
        try:
            os.makedirs(data_dir)
        except OSError:
            data_dir = base_dir # Fallback
            
    log_path = os.path.join(data_dir, 'emoniter.log')

    # File Handler
    # File Handler
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

    # Console Handler with UTF-8 encoding for Windows compatibility
    # This fixes the UnicodeEncodeError when logging emojis on Windows
    if sys.platform == 'win32':
        # Use UTF-8 wrapper for Windows console
        console_handler = logging.StreamHandler(
            io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        )
    else:
        console_handler = logging.StreamHandler(sys.stdout)
    
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger

log = setup_logging()