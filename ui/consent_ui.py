import tkinter as tk
from tkinter import ttk, scrolledtext
from consent import consent_manager # <-- Imports from the file above
from .login_ui import LoginFrame

CONSENT_TEXT = """
Welcome to eMonitor.

This is NOT spyware. This application is designed to be used by the owner of this device to monitor their own activity for security or productivity purposes.

By clicking "I Agree", you confirm:
1.  You are the owner of this computer or have explicit, authorized permission from the owner to install this software.
2.  You understand that this app will capture screenshots, system activity, and other data.
3.  This data will be ENCRYPTED LOCALLY using a password YOU set.
4.  The encrypted data will be sent via email to an address YOU specify.
5.  The admin (service provider) CANNOT read your data, as they do not have your encryption password.
6.  You consent to the automatic assignment of a "sender-only" email account from the admin's pool to send your encrypted data.

Please read this carefully. By agreeing, you take full responsibility for the use of this software in compliance with all local laws.
"""

class ConsentFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        lbl_title = ttk.Label(self, text="User Consent", font=("Arial", 18))
        lbl_title.pack(pady=20)
        
        txt_consent = scrolledtext.ScrolledText(self, wrap=tk.WORD, width=45, height=15, state="disabled")
        txt_consent.pack(pady=10, padx=20)
        
        # Make text editable to insert, then disable
        txt_consent.config(state="normal")
        txt_consent.insert(tk.INSERT, CONSENT_TEXT)
        txt_consent.config(state="disabled")
        
        btn_agree = ttk.Button(self, text="I Agree and Consent", command=self.handle_agree)
        btn_agree.pack(pady=20)
        
    def handle_agree(self):
        # 1. Record consent
        consent_manager.grant_consent()
        
        # 2. Move to the login screen
        # We call the controller's main login check
        self.controller.attempt_auto_login()