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
        # Allow resizing and maximizing
        self.resizable(True, True)
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
        
        # Checkbox for log attachment
        self.log_var = tk.BooleanVar(value=True)
        self.chk_log = ttk.Checkbutton(self, text="Attach application log (recommended for debugging)", variable=self.log_var)
        self.chk_log.pack(pady=(0, 5))
        
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
        include_log = self.log_var.get()
        
        threading.Thread(target=self.send_feedback, args=(message, include_log), daemon=True).start()

    def send_feedback(self, message, include_log):
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
            user_id = self.controller.auth.current_user.id
            
            # --- 1. Save to Supabase ---
            try:
                import platform
                import json
                
                device_info = {
                    "node": platform.node(),
                    "system": platform.system(),
                    "release": platform.release(),
                    "version": platform.version(),
                    "machine": platform.machine(),
                    "processor": platform.processor()
                }
                
                # Determine feedback type (simple heuristic)
                feedback_type = "feedback"
                subject_lower = message.lower().split("\n")[0][:50]
                if "bug" in subject_lower or "error" in subject_lower or "crash" in subject_lower:
                    feedback_type = "bug"
                elif "feature" in subject_lower or "request" in subject_lower:
                    feedback_type = "feature_request"
                elif "issue" in subject_lower or "help" in subject_lower:
                    feedback_type = "issue"
                
                # Call RPC function
                from auth import auth_service
                
                rpc_params = {
                    "p_user_email": user_email,
                    "p_user_name": str(self.controller.auth.current_user.user_metadata.get("full_name", "User")),
                    "p_feedback_type": feedback_type,
                    "p_subject": message.split("\n")[0][:100] if message else "No Subject",
                    "p_message": message,
                    "p_device_info": device_info,
                    "p_app_version": "1.0.0" # You might want to get this dynamically
                }
                
                response = auth_service.client.rpc("submit_user_feedback", rpc_params).execute()
                log.info(f"Feedback saved to Supabase: {response.data}")
                
            except Exception as db_err:
                log.error(f"Failed to save feedback to database (continuing to email): {db_err}")

            # --- 2. Send Email ---
            creds_result = self.controller.auth.get_sender_assignment()
            if not creds_result.get("success"):
                log.error("Feedback failed: Could not get sender credentials.")
                self.after(0, messagebox.showerror, "Error", "Could not get sender credentials to send email.")
                return

            sender_config = creds_result.get("data")
            
            # FIX: Use absolute path from DATA_DIR
            from config import DATA_DIR
            import os
            real_log_path = os.path.join(DATA_DIR, "emoniter.log")
            
            log_path = real_log_path if include_log and os.path.exists(real_log_path) else None
            
            if include_log and not log_path:
                log.warning(f"Could not find log file at {real_log_path} to attach.")
            
            success = send_feedback_email(sender_config, admin_email, user_email, message, log_path)
            
            if success:
                log.info(f"Successfully sent feedback to {admin_email}")
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
        messagebox.showinfo("Feedback Sent", "Thank you! Your feedback has been saved and sent to our team.")
        self.destroy()

    def close_window(self):
        if self.winfo_exists(): # Check if window wasn't already destroyed
            self.btn_send.config(state="normal")
            self.btn_cancel.config(state="normal")
            self.destroy() # Close the window