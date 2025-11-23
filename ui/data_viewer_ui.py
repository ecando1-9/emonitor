import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from encryptor import encryptor
import os
import subprocess
from logger_setup import log

class DataViewerFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        self.grid_columnconfigure(0, weight=1)
        
        lbl_title = ttk.Label(self, text="File Decryptor", font=("Arial", 18))
        lbl_title.grid(row=0, column=0, columnspan=3, pady=20)
        
        lbl_info = ttk.Label(self, 
            text="Use this tool to decrypt any of your .enc files (Screenshots, Logs, Video, etc.).\n"
                 "It will ask you where to save the unlocked (decrypted) file.", 
            justify="center")
        lbl_info.grid(row=1, column=0, columnspan=3, padx=20, pady=10)

        # --- Frame for the steps ---
        main_frame = ttk.Frame(self, padding=20)
        main_frame.grid(row=2, column=0, columnspan=3, sticky="ew")
        main_frame.grid_columnconfigure(1, weight=1)
        
        # --- 1. Open File ---
        self.btn_open = ttk.Button(main_frame, text="1. Open Encrypted File...", command=self.select_file)
        self.btn_open.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        self.lbl_file = ttk.Label(main_frame, text="No file selected.", anchor="w")
        self.lbl_file.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        # --- 2. Password ---
        lbl_pass = ttk.Label(main_frame, text="2. Enter Password:")
        lbl_pass.grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.entry_pass = ttk.Entry(main_frame, width=40, show="*")
        self.entry_pass.grid(row=1, column=1, padx=10, pady=10, sticky="w")
        
        # --- 3. Decrypt Button ---
        self.btn_decrypt = ttk.Button(main_frame, text="3. Decrypt and Save As...", command=self.decrypt_and_save, state="disabled")
        self.btn_decrypt.grid(row=2, column=0, columnspan=2, pady=20)

        self.selected_file_path = None

        # --- Back Button ---
        btn_back = ttk.Button(self, text="Back to Dashboard", command=self.go_to_dashboard)
        btn_back.grid(row=4, column=0, columnspan=3, pady=50)

    def select_file(self):
        """Lets the user select a file to decrypt."""
        self.clear_form()
        
        file_path = filedialog.askopenfilename(
            title="Select Encrypted File",
            filetypes=(("Encrypted Files", "*.enc"), ("All Report Files", "*.*"))
        )
        if not file_path:
            return

        # Check the file
        if file_path.endswith(".zip"):
            messagebox.showinfo("ZIP File", "This is a password-protected ZIP file.\n\nYou can open it directly on your computer using your encryption password.")
            self.btn_decrypt.config(state="disabled")
            return
        if not file_path.endswith(".enc"):
            messagebox.showwarning("Unprotected File", "This is not an encrypted file.\nYou can open it directly on your computer.")
            self.btn_decrypt.config(state="disabled")
            return
            
        self.selected_file_path = file_path
        file_name = os.path.basename(file_path)
        self.lbl_file.config(text=file_name, foreground="black")
        self.btn_decrypt.config(state="normal")

    def decrypt_and_save(self):
        """
        Decrypts ANY file and opens a 'Save As' dialog.
        """
        password = self.entry_pass.get()
        if not password:
            password = self.controller.config.get_settings()["user"]["encryption_password"]
            if not password:
                messagebox.showerror("Error", "Please enter your encryption password.")
                return
            self.entry_pass.insert(0, password)
            
        if not self.selected_file_path:
            return

        file_name = os.path.basename(self.selected_file_path)
        
        # Get the original unlocked filename
        unlocked_name = file_name.replace(".enc", "")
        unlocked_ext = os.path.splitext(unlocked_name)[1]
        
        log.info(f"Decrypting {file_name}...")
        decrypted_data = encryptor.decrypt_data(self.selected_file_path, password)
        
        if decrypted_data is None:
            messagebox.showerror("Decryption Failed", "Could not decrypt file. Please check your password.")
            return
        
        log.info("Decryption successful. Asking user where to save.")

        # Open a "Save As" dialog
        save_path = filedialog.asksaveasfilename(
            title="Save Decrypted File",
            initialfile=unlocked_name,
            defaultextension=unlocked_ext,
            filetypes=[(f"{unlocked_ext.upper()} Files", f"*{unlocked_ext}") ,("All Files", "*.*")]
        )
        
        if not save_path:
            log.info("User cancelled save.")
            return
            
        try:
            # Write the decrypted data to the new file
            with open(save_path, "wb") as f:
                f.write(decrypted_data)
                
            log.info(f"Successfully saved decrypted file to {save_path}")
            
            # Ask to open the folder
            if messagebox.askyesno("Success!", 
                                   f"File saved successfully:\n{save_path}\n\nDo you want to open the file's location?"):
                # Open the folder in Windows Explorer (secure - using list format to prevent injection)
                try:
                    # Use list format to prevent command injection
                    normalized_path = os.path.normpath(save_path)
                    # Validate path exists and is absolute
                    if os.path.exists(normalized_path) and os.path.isabs(normalized_path):
                        subprocess.Popen(['explorer', '/select,', normalized_path], shell=False)
                    else:
                        log.warning(f"Invalid path for explorer: {normalized_path}")
                except Exception as e:
                    log.error(f"Failed to open file location: {e}")
                
            self.clear_form() # Reset the page
                
        except Exception as e:
            log.error(f"Error saving decrypted file: {e}")
            messagebox.showerror("Error", f"Could not save file: {e}")

    def clear_form(self):
        """Resets the page"""
        self.lbl_file.config(text="No file selected.", foreground="black")
        self.btn_decrypt.config(state="disabled")
        self.entry_pass.delete(0, tk.END) # Clear password field
        self.selected_file_path = None
        
    def cleanup_temp_file(self):
        # We no longer use temp files, so this function is empty
        pass

    def go_to_dashboard(self):
        self.clear_form()
        from .dashboard_ui import DashboardFrame
        self.controller.show_frame(DashboardFrame)