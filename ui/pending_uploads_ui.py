import tkinter as tk
from tkinter import ttk, messagebox
import os
import time
from config import DATA_DIR
from logger_setup import log

class PendingUploadsWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Pending Uploads / Unsent Reports")
        self.geometry("700x500")
        
        # Define paths to scan (Active and Legacy)
        from config import BASE_DIR
        self.scan_locations = [
            (os.path.join(DATA_DIR, "outbox"), "Bundled Queue"),
            (os.path.join(DATA_DIR, "instant_outbox"), "Instant Queue"),
            (os.path.join(DATA_DIR, "captures"), "Raw Captures (Processing/Stuck)"),
            (os.path.join(BASE_DIR, "outbox"), "Bundled Queue (Old)"),
            (os.path.join(BASE_DIR, "instant_outbox"), "Instant Queue (Old)"),
            (os.path.join(BASE_DIR, "captures"), "Raw Captures (Old)")
        ]
        
        # UI Setup
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill="both", expand=True)
        
        # Header
        ttk.Label(main_frame, text="Pending Uploads (Not Sent)", font=("Arial", 14, "bold")).pack(pady=(0, 5))
        ttk.Label(main_frame, text="Files waiting for upload. Includes both current and legacy storage.", 
                 foreground="gray").pack(pady=(0, 10))
        
        # Treeview
        columns = ("filename", "location", "size", "created")
        self.tree = ttk.Treeview(main_frame, columns=columns, show="headings", selectmode="extended")
        self.tree.heading("filename", text="File Name")
        self.tree.heading("location", text="Queue Location")
        self.tree.heading("size", text="Size")
        self.tree.heading("created", text="Created")
        
        self.tree.column("filename", width=250)
        self.tree.column("location", width=120)
        self.tree.column("size", width=80)
        self.tree.column("created", width=150)
        
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar)
        
        self.tree.pack(side="top", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=10)
        
        ttk.Button(btn_frame, text="Refresh List", command=self.load_files).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Delete Selected", command=self.delete_selected).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Clear All", command=self.clear_all).pack(side="right", padx=5)
        
        self.status_lbl = ttk.Label(main_frame, text="", foreground="blue")
        self.status_lbl.pack(fill="x")
        
        self.load_files()
        
    def format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
        
    def load_files(self):
        # Clear existing
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        count = 0
        total_size = 0
        
        for path, label in self.scan_locations:
            self._scan_dir(path, label, count, total_size)
    
    def _scan_dir(self, directory, label, count, total_size):
        if not os.path.exists(directory):
            return
            
        try:
            items = os.listdir(directory)
            for f in items:
                path = os.path.join(directory, f)
                if os.path.isfile(path):
                    size = os.path.getsize(path)
                    created = os.path.getctime(path)
                    created_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(created))
                    
                    self.tree.insert("", "end", values=(f, label, self.format_size(size), created_str), tags=(path,)) # Store full path in tag? No, treeview doesn't support easy hidden data
                    # I'll store full path in a dict or just reconstruct it
                    # Better: Store path in 'tags' is tricky if multiple tags.
                    # I'll modify logic to store in a list or just deduce.
                    
                    # Actually, I can use the 'iid' as the path if unique.
                    self.tree.insert("", "end", iid=path, values=(f, label, self.format_size(size), created_str))
        except Exception as e:
            log.error(f"Error scanning {directory}: {e}")
            
    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Selection", "Please select files to delete.")
            return
            
        if not messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete {len(selected)} pending files?"):
            return
            
        deleted_count = 0
        for iid in selected:
            file_path = iid # We stored path as IID
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    deleted_count += 1
            except Exception as e:
                log.error(f"Failed to delete {file_path}: {e}")
        
        self.load_files()
        self.status_lbl.config(text=f"Deleted {deleted_count} files.")
        
    def clear_all(self):
        # Count total items
        items = self.tree.get_children()
        if not items:
            return
            
        if not messagebox.askyesno("Confirm Clear All", "Are you sure you want to delete ALL pending uploads?\nThis action cannot be undone."):
            return
            
        deleted_count = 0
        for iid in items:
            file_path = iid
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    deleted_count += 1
            except Exception as e:
                log.error(f"Failed to delete {file_path}: {e}")
                
        self.load_files()
        self.status_lbl.config(text=f"Cleared {deleted_count} files.")
