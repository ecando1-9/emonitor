import logging
import sys
from logging.handlers import RotatingFileHandler

def setup_logging():
    """Configures the application's logger."""
    
    logger = logging.getLogger("eMonitor")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if logger.hasHandlers():
        return logger

    # File Handler
    file_handler = RotatingFileHandler(
        'emoniter.log', 
        maxBytes=2*1024*1024, 
        backupCount=3
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger

log = setup_logging()