"""
Setup Window GUI for Email Enrichment App
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading

class SetupWindow:
    """GUI wrapper for setup wizard"""
    
    def __init__(self, parent, config_manager):
        self.parent = parent
        self.config_manager = config_manager
        self.window = None
        
    def show(self):
        """Show setup window"""
        self.window = tk.Toplevel(self.parent)
        self.window.title("Email Enrichment App - Setup Wizard")
        self.window.geometry("600x400")
        self.window.resizable(True, True)
        
        # Make modal
        self.window.transient(self.parent)
        self.window.grab_set()
        
        self._create_widgets()
        
        # Center window
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (self.window.winfo_width() // 2)
        y = (self.window.winfo_screenheight() // 2) - (self.window.winfo_height() // 2)
        self.window.geometry(f"+{x}+{y}")
    
    def _create_widgets(self):
        """Create setup window widgets"""
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.pack(fill="both", expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Setup Wizard", 
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Description
        desc_text = """Welcome to the Email Enrichment App Setup Wizard!
        
This wizard will help you configure:
• Email providers (Gmail, Outlook, Yahoo, iCloud)
• API keys for enrichment services
• Application preferences

The setup process will run in the terminal window.
Please follow the prompts in the terminal."""
        
        desc_label = ttk.Label(main_frame, text=desc_text, justify="left")
        desc_label.pack(pady=(0, 20))
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="Ready to start setup...", 
                                     foreground="blue")
        self.status_label.pack(pady=(0, 20))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(20, 0))
        
        self.start_button = ttk.Button(button_frame, text="Start Setup", 
                                      command=self._start_setup)
        self.start_button.pack(side="left", padx=(0, 10))
        
        cancel_button = ttk.Button(button_frame, text="Cancel", 
                                  command=self.window.destroy)
        cancel_button.pack(side="left")
    
    def _start_setup(self):
        """Start setup wizard in background thread"""
        self.start_button.config(state="disabled")
        self.status_label.config(text="Running setup wizard in terminal...", 
                                foreground="orange")
        
        def run_setup():
            try:
                from setup_wizard import SetupWizard
                wizard = SetupWizard()
                success = wizard.run_setup()
                
                # Update UI on main thread
                self.window.after(0, lambda: self._on_setup_complete(success))
                
            except Exception as e:
                self.window.after(0, lambda: self._on_setup_error(str(e)))
        
        threading.Thread(target=run_setup, daemon=True).start()
    
    def _on_setup_complete(self, success):
        """Handle setup completion"""
        if success:
            self.status_label.config(text="✅ Setup completed successfully!", 
                                    foreground="green")
            messagebox.showinfo("Success", "Setup completed successfully!")
            self.window.destroy()
        else:
            self.status_label.config(text="❌ Setup was not completed", 
                                    foreground="red")
            self.start_button.config(state="normal")
    
    def _on_setup_error(self, error_msg):
        """Handle setup error"""
        self.status_label.config(text=f"❌ Setup failed: {error_msg}", 
                                foreground="red")
        self.start_button.config(state="normal")
        messagebox.showerror("Setup Error", f"Setup failed:\n{error_msg}")