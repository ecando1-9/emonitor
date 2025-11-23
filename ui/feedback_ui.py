import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
from logger_setup import log
from config import config_manager
from auth import auth_service
from sender import send_feedback_email

class FeedbackWindow(tk.Toplevel):
    """
    A Toplevel window (popup) for sending feedback.
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Send Feedback to Admin")
        self.geometry("450x400")
        self.transient(parent) # Keep this window on top
        self.grab_set() # Modal behavior
        
        # --- !! THIS IS THE FIX !! ---
        # The 'parent' *is* the controller (MainWindow)
        self.controller = parent 
        
        lbl_title = ttk.Label(self, text="Report an Issue or Send Feedback", font=("Arial", 14))
        lbl_title.pack(pady=10)
        
        lbl_info = ttk.Label(self, 
            text="This will send your message and your application log file\n(emoniter.log) to the admin for review.",
            justify="center")
        lbl_info.pack(padx=10, pady=5)
        
        # Text Entry
        self.text_area = scrolledtext.ScrolledText(self, wrap=tk.WORD, height=15, width=50, font=("Arial", 10))
        self.text_area.pack(pady=10, padx=20, fill="both", expand=True)
        self.text_area.insert(tk.INSERT, "Please describe the problem or your feedback here...")
        
        # Button Frame
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)
        
        self.btn_send = ttk.Button(btn_frame, text="Send Feedback", command=self.send_feedback_thread)
        self.btn_send.pack(side="left", padx=10)
        
        self.btn_cancel = ttk.Button(btn_frame, text="Cancel", command=self.destroy)
        self.btn_cancel.pack(side="left", padx=10)

    def send_feedback_thread(self):
        """Disables button and starts the send in a new thread"""
        self.btn_send.config(state="disabled")
        self.btn_cancel.config(state="disabled")
        
        message = self.text_area.get("1.0", tk.END)
        
        threading.Thread(target=self.send_feedback, args=(message,), daemon=True).start()

    def send_feedback(self, message):
        """The actual sending logic"""
        try:
            admin_email = self.controller.config.get_settings()["admin"]["admin_support_email"]
            if not admin_email or "your-support-email" in admin_email:
                log.error("Feedback failed: Admin email not configured.")
                self.after(0, messagebox.showerror, "Error", "Admin support email is not configured.")
                return

            if not self.controller.auth.current_user:
                log.error("Feedback failed: User not logged in.")
                self.after(0, messagebox.showerror, "Error", "You must be logged in to send feedback.")
                return
            
            user_email = self.controller.auth.current_user.email
            
            creds_result = self.controller.auth.get_sender_assignment()
            if not creds_result.get("success"):
                log.error("Feedback failed: Could not get sender credentials.")
                self.after(0, messagebox.showerror, "Error", "Could not get sender credentials to send email.")
                return

            sender_config = creds_result.get("data")
            log_path = "emoniter.log"
            
            success = send_feedback_email(sender_config, admin_email, user_email, message, log_path)
            
            if success:
                log.info("Feedback sent successfully.")
                self.after(0, self.show_success_and_close)
            else:
                log.error("Feedback send failed.")
                self.after(0, messagebox.showerror, "Error", "Failed to send feedback. Please try again later.")

        except Exception as e:
            log.error(f"Exception in send_feedback: {e}")
            self.after(0, messagebox.showerror, "Error", f"An unexpected error occurred: {e}")
        finally:
            # This ensures the window always closes, even on failure
            self.after(100, self.close_window) 

    def show_success_and_close(self):
        messagebox.showinfo("Feedback Sent", "Thank you! Your feedback and log file have been sent to the admin.")
        self.destroy()

    def close_window(self):
        if self.winfo_exists(): # Check if window wasn't already destroyed
            self.btn_send.config(state="normal")
            self.btn_cancel.config(state="normal")
            self.destroy() # Close the window