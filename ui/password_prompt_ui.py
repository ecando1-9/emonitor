import tkinter as tk
from tkinter import ttk, messagebox
from logger_setup import log
from auth import auth_service

class PasswordConfirmationDialog(tk.Toplevel):
    """
    A modal popup that asks the user to confirm their password.
    If the password is correct, it calls a success_callback.
    """
    def __init__(self, parent, title, message, success_callback):
        super().__init__(parent)
        self.title(title)
        self.transient(parent) # Keep this window on top
        self.grab_set() # Modal behavior
        self.resizable(False, False)
        
        self.success_callback = success_callback
        
        lbl_message = ttk.Label(self, text=message, wraplength=300, justify="center")
        lbl_message.pack(pady=(15, 10), padx=20)
        
        lbl_pass = ttk.Label(self, text="Enter Password:")
        lbl_pass.pack(padx=20, pady=(5, 0))
        
        self.entry_pass = ttk.Entry(self, width=40, show="*")
        self.entry_pass.pack(padx=20, pady=5)
        
        self.lbl_status = ttk.Label(self, text="", foreground="red")
        self.lbl_status.pack(pady=5)
        
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=15)
        
        self.btn_confirm = ttk.Button(btn_frame, text="Confirm", command=self.handle_confirm)
        self.btn_confirm.pack(side="left", padx=10)
        
        btn_cancel = ttk.Button(btn_frame, text="Cancel", command=self.destroy)
        btn_cancel.pack(side="left", padx=10)
        
        self.entry_pass.focus()
        
        # Center the window on the parent
        self.geometry("+%d+%d" % (parent.winfo_rootx() + 50,
                                  parent.winfo_rooty() + 50))

    def handle_confirm(self):
        """Checks the password against the auth service."""
        password = self.entry_pass.get()
        if not password:
            self.lbl_status.config(text="Password cannot be empty.")
            return

        self.lbl_status.config(text="Verifying...", foreground="blue")
        self.btn_confirm.config(state="disabled")
        self.update_idletasks()
        
        # We need to run this in a thread to avoid freezing the UI
        # But for simplicity in a modal, we can risk a small freeze.
        # A better implementation would use threading.
        
        if auth_service.check_password(password):
            log.info("Password confirmed successfully.")
            self.destroy() # Close this popup
            self.success_callback() # Call the original function
        else:
            log.warning("Password confirmation failed.")
            self.lbl_status.config(text="Incorrect password. Please try again.", foreground="red")
            self.btn_confirm.config(state="normal")