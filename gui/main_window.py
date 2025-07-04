"""
Main GUI Window for Email Enrichment App
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any

class MainWindow:
    """Main application GUI window"""
    
    def __init__(self, root: tk.Tk, config_manager):
        self.root = root
        self.config_manager = config_manager
        self.src_dir = Path(__file__).parent.parent / "src"
        self.main_py = self.src_dir / "main.py"
        
        self._setup_window()
        self._create_widgets()
        self._load_settings()
        
    def _setup_window(self):
        """Setup main window properties"""
        self.root.title("Email Enrichment App")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # Configure style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure grid weights
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
    
    def _create_widgets(self):
        """Create main window widgets"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.grid_rowconfigure(2, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Email Enrichment App", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Configuration status
        self._create_status_section(main_frame)
        
        # Settings section
        self._create_settings_section(main_frame)
        
        # Output section
        self._create_output_section(main_frame)
        
        # Control buttons
        self._create_control_buttons(main_frame)
    
    def _create_status_section(self, parent):
        """Create configuration status section"""
        status_frame = ttk.LabelFrame(parent, text="Configuration Status", padding="10")
        status_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        status_frame.grid_columnconfigure(1, weight=1)
        
        # Status labels
        self.status_labels = {}
        
        ttk.Label(status_frame, text="Email Providers:").grid(row=0, column=0, sticky="w")
        self.status_labels['providers'] = ttk.Label(status_frame, text="Loading...", foreground="gray")
        self.status_labels['providers'].grid(row=0, column=1, sticky="w", padx=(10, 0))
        
        ttk.Label(status_frame, text="API Services:").grid(row=1, column=0, sticky="w")
        self.status_labels['apis'] = ttk.Label(status_frame, text="Loading...", foreground="gray")
        self.status_labels['apis'].grid(row=1, column=1, sticky="w", padx=(10, 0))
        
        ttk.Label(status_frame, text="Ready to Extract:").grid(row=2, column=0, sticky="w")
        self.status_labels['ready'] = ttk.Label(status_frame, text="Loading...", foreground="gray")
        self.status_labels['ready'].grid(row=2, column=1, sticky="w", padx=(10, 0))
        
        # Setup button
        setup_btn = ttk.Button(status_frame, text="Run Setup Wizard", 
                              command=self._run_setup_wizard)
        setup_btn.grid(row=0, column=2, rowspan=2, padx=(10, 0))
        
        # Refresh button
        refresh_btn = ttk.Button(status_frame, text="Refresh", 
                                command=self._refresh_status)
        refresh_btn.grid(row=2, column=2, padx=(10, 0))
    
    def _create_settings_section(self, parent):
        """Create extraction settings section"""
        settings_frame = ttk.LabelFrame(parent, text="Extraction Settings", padding="10")
        settings_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(0, 10))
        settings_frame.grid_columnconfigure(1, weight=1)
        
        # Provider selection
        ttk.Label(settings_frame, text="Email Providers:").grid(row=0, column=0, sticky="nw", pady=(5, 0))
        
        providers_frame = ttk.Frame(settings_frame)
        providers_frame.grid(row=0, column=1, sticky="ew", padx=(10, 0))
        
        self.provider_vars = {}
        for i, provider in enumerate(['gmail', 'outlook', 'yahoo', 'icloud']):
            var = tk.BooleanVar()
            self.provider_vars[provider] = var
            cb = ttk.Checkbutton(providers_frame, text=provider.capitalize(), variable=var)
            cb.grid(row=i//2, column=i%2, sticky="w", padx=(0, 20))
        
        # Days back
        ttk.Label(settings_frame, text="Days Back:").grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.days_back_var = tk.StringVar(value="30")
        days_entry = ttk.Entry(settings_frame, textvariable=self.days_back_var, width=10)
        days_entry.grid(row=1, column=1, sticky="w", padx=(10, 0), pady=(10, 0))
        
        # Max emails
        ttk.Label(settings_frame, text="Max Emails:").grid(row=2, column=0, sticky="w", pady=(10, 0))
        self.max_emails_var = tk.StringVar(value="1000")
        emails_entry = ttk.Entry(settings_frame, textvariable=self.max_emails_var, width=10)
        emails_entry.grid(row=2, column=1, sticky="w", padx=(10, 0), pady=(10, 0))
        
        # Features
        ttk.Label(settings_frame, text="Features:").grid(row=3, column=0, sticky="nw", pady=(10, 0))
        
        features_frame = ttk.Frame(settings_frame)
        features_frame.grid(row=3, column=1, sticky="ew", padx=(10, 0), pady=(10, 0))
        
        self.enrich_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(features_frame, text="API Enrichment", 
                       variable=self.enrich_var).grid(row=0, column=0, sticky="w")
        
        self.enhanced_scoring_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(features_frame, text="Enhanced AI Scoring", 
                       variable=self.enhanced_scoring_var).grid(row=0, column=1, sticky="w", padx=(20, 0))
        
        self.analytics_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(features_frame, text="Include Analytics", 
                       variable=self.analytics_var).grid(row=1, column=0, sticky="w")
        
        # Export format
        ttk.Label(settings_frame, text="Export Format:").grid(row=4, column=0, sticky="w", pady=(10, 0))
        self.export_format_var = tk.StringVar(value="excel")
        format_combo = ttk.Combobox(settings_frame, textvariable=self.export_format_var,
                                   values=["excel", "csv", "json"], state="readonly", width=10)
        format_combo.grid(row=4, column=1, sticky="w", padx=(10, 0), pady=(10, 0))
        
        # Output file
        ttk.Label(settings_frame, text="Output File:").grid(row=5, column=0, sticky="w", pady=(10, 0))
        
        output_frame = ttk.Frame(settings_frame)
        output_frame.grid(row=5, column=1, sticky="ew", padx=(10, 0), pady=(10, 0))
        output_frame.grid_columnconfigure(0, weight=1)
        
        self.output_file_var = tk.StringVar()
        output_entry = ttk.Entry(output_frame, textvariable=self.output_file_var)
        output_entry.grid(row=0, column=0, sticky="ew")
        
        browse_btn = ttk.Button(output_frame, text="Browse", command=self._browse_output_file)
        browse_btn.grid(row=0, column=1, padx=(5, 0))
    
    def _create_output_section(self, parent):
        """Create output/log section"""
        output_frame = ttk.LabelFrame(parent, text="Output", padding="10")
        output_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(0, 10))
        output_frame.grid_rowconfigure(0, weight=1)
        output_frame.grid_columnconfigure(0, weight=1)
        
        # Text widget with scrollbar
        text_frame = ttk.Frame(output_frame)
        text_frame.grid(row=0, column=0, sticky="nsew")
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)
        
        self.output_text = tk.Text(text_frame, wrap=tk.WORD, height=10)
        self.output_text.grid(row=0, column=0, sticky="nsew")
        
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.output_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.output_text.configure(yscrollcommand=scrollbar.set)
        
        # Clear button
        clear_btn = ttk.Button(output_frame, text="Clear", command=self._clear_output)
        clear_btn.grid(row=1, column=0, sticky="e", pady=(10, 0))
    
    def _create_control_buttons(self, parent):
        """Create control buttons"""
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=4, column=0, columnspan=2, pady=(10, 0))
        
        # Quick Extract button
        self.quick_btn = ttk.Button(button_frame, text="⚡ Quick Extract", 
                                   command=self._quick_extract, style="Accent.TButton")
        self.quick_btn.grid(row=0, column=0, padx=(0, 10))
        
        # Extract button
        self.extract_btn = ttk.Button(button_frame, text="🚀 Extract Contacts", 
                                     command=self._extract_contacts)
        self.extract_btn.grid(row=0, column=1, padx=(0, 10))
        
        # Status button
        status_btn = ttk.Button(button_frame, text="📊 Show Status", 
                               command=self._show_detailed_status)
        status_btn.grid(row=0, column=2, padx=(0, 10))
        
        # Exit button
        exit_btn = ttk.Button(button_frame, text="Exit", command=self.root.quit)
        exit_btn.grid(row=0, column=3)
    
    def _load_settings(self):
        """Load settings and update UI"""
        try:
            settings = self.config_manager.load_app_settings()
            
            # Load extraction settings
            self.days_back_var.set(str(settings['extraction']['default_days_back']))
            self.max_emails_var.set(str(settings['extraction']['default_max_emails']))
            
            # Load feature settings
            self.enrich_var.set(settings['features']['api_enrichment'])
            self.enhanced_scoring_var.set(settings['features']['enhanced_scoring'])
            self.analytics_var.set(settings['features']['export_analytics'])
            
            # Load export settings
            self.export_format_var.set(settings['export']['default_format'])
            
            # Load available providers
            status = self.config_manager.get_configuration_status()
            
            # Enable checkboxes for available providers
            for provider, configured in status['email_providers'].items():
                if provider in self.provider_vars:
                    if provider == 'gmail':
                        self.provider_vars[provider].set(configured > 0)
                    else:
                        self.provider_vars[provider].set(bool(configured))
            
        except Exception as e:
            self._log_output(f"Error loading settings: {e}")
        
        # Refresh status
        self._refresh_status()
    
    def _refresh_status(self):
        """Refresh configuration status display"""
        try:
            status = self.config_manager.get_configuration_status()
            
            # Update provider status
            provider_text = f"{status['total_providers']} configured"
            if status['total_providers'] > 0:
                self.status_labels['providers'].config(text=provider_text, foreground="green")
            else:
                self.status_labels['providers'].config(text="None configured", foreground="red")
            
            # Update API status
            api_text = f"{status['total_apis']} configured"
            if status['total_apis'] > 0:
                self.status_labels['apis'].config(text=api_text, foreground="green")
            else:
                self.status_labels['apis'].config(text="None configured", foreground="orange")
            
            # Update ready status
            if status['total_providers'] > 0:
                self.status_labels['ready'].config(text="✅ Ready", foreground="green")
                self.extract_btn.config(state="normal")
                self.quick_btn.config(state="normal")
            else:
                self.status_labels['ready'].config(text="❌ Setup required", foreground="red")
                self.extract_btn.config(state="disabled")
                self.quick_btn.config(state="disabled")
                
        except Exception as e:
            self._log_output(f"Error refreshing status: {e}")
    
    def _browse_output_file(self):
        """Browse for output file"""
        format_ext = {"excel": ".xlsx", "csv": ".csv", "json": ".json"}
        ext = format_ext.get(self.export_format_var.get(), ".xlsx")
        
        filename = filedialog.asksaveasfilename(
            title="Save Export As",
            defaultextension=ext,
            filetypes=[
                ("Excel files", "*.xlsx"),
                ("CSV files", "*.csv"),
                ("JSON files", "*.json"),
                ("All files", "*.*")
            ]
        )
        
        if filename:
            self.output_file_var.set(filename)
    
    def _run_setup_wizard(self):
        """Run setup wizard in separate thread"""
        def run_wizard():
            try:
                from setup_wizard import SetupWizard
                wizard = SetupWizard()
                success = wizard.run_setup()
                
                # Update UI on main thread
                self.root.after(0, lambda: self._on_setup_complete(success))
                
            except Exception as e:
                self.root.after(0, lambda: self._log_output(f"Setup wizard error: {e}"))
        
        self._log_output("🔧 Running setup wizard...")
        threading.Thread(target=run_wizard, daemon=True).start()
    
    def _on_setup_complete(self, success: bool):
        """Handle setup wizard completion"""
        if success:
            self._log_output("✅ Setup completed successfully!")
            self._refresh_status()
            self._load_settings()
        else:
            self._log_output("❌ Setup was not completed")
    
    def _quick_extract(self):
        """Run quick extraction"""
        self._run_extraction(quick=True)
    
    def _extract_contacts(self):
        """Run full extraction with current settings"""
        self._run_extraction(quick=False)
    
    def _run_extraction(self, quick: bool = False):
        """Run extraction in separate thread"""
        # Disable buttons during extraction
        self.extract_btn.config(state="disabled")
        self.quick_btn.config(state="disabled")
        
        def run_extraction():
            try:
                # Build command
                cmd = [sys.executable, str(self.main_py)]
                cmd.append("--extract")
                
                if not quick:
                    # Use current settings
                    selected_providers = [p for p, var in self.provider_vars.items() if var.get()]
                    if selected_providers:
                        cmd.extend(["--providers"] + selected_providers)
                    
                    cmd.extend(["--days-back", self.days_back_var.get()])
                    cmd.extend(["--max-emails", self.max_emails_var.get()])
                    
                    if self.enrich_var.get():
                        cmd.append("--enrich")
                    
                    if self.enhanced_scoring_var.get():
                        cmd.append("--enhanced-scoring")
                    
                    cmd.extend(["--export-format", self.export_format_var.get()])
                    
                    if self.output_file_var.get():
                        cmd.extend(["--output-file", self.output_file_var.get()])
                    
                    if self.analytics_var.get():
                        cmd.append("--analytics")
                else:
                    # Quick extraction defaults
                    cmd.extend(["--days-back", "30"])
                    cmd.extend(["--max-emails", "500"])
                    cmd.append("--enrich")
                    cmd.append("--enhanced-scoring")
                    cmd.extend(["--export-format", "excel"])
                    cmd.append("--analytics")
                
                # Setup environment
                self.config_manager.setup_environment_variables()
                
                # Log command
                self.root.after(0, lambda: self._log_output(f"🚀 Running: {' '.join(cmd[2:])}"))
                
                # Run extraction
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                    cwd=self.src_dir.parent
                )
                
                # Stream output
                for line in iter(process.stdout.readline, ''):
                    if line:
                        self.root.after(0, lambda l=line: self._log_output(l.rstrip()))
                
                process.stdout.close()
                return_code = process.wait()
                
                # Handle completion
                if return_code == 0:
                    self.root.after(0, lambda: self._log_output("✅ Extraction completed successfully!"))
                else:
                    self.root.after(0, lambda: self._log_output("❌ Extraction failed"))
                
            except Exception as e:
                self.root.after(0, lambda: self._log_output(f"❌ Extraction error: {e}"))
            
            finally:
                # Re-enable buttons
                self.root.after(0, lambda: self.extract_btn.config(state="normal"))
                self.root.after(0, lambda: self.quick_btn.config(state="normal"))
        
        threading.Thread(target=run_extraction, daemon=True).start()
    
    def _show_detailed_status(self):
        """Show detailed status in popup"""
        try:
            summary = self.config_manager.export_configuration_summary()
            
            # Create popup window
            popup = tk.Toplevel(self.root)
            popup.title("Configuration Status")
            popup.geometry("600x400")
            
            # Text widget with scrollbar
            frame = ttk.Frame(popup, padding="10")
            frame.pack(fill="both", expand=True)
            
            text_widget = tk.Text(frame, wrap=tk.WORD)
            scrollbar = ttk.Scrollbar(frame, orient="vertical", command=text_widget.yview)
            text_widget.configure(yscrollcommand=scrollbar.set)
            
            text_widget.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            text_widget.insert("1.0", summary)
            text_widget.config(state="disabled")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to show status: {e}")
    
    def _log_output(self, message: str):
        """Add message to output log"""
        self.output_text.insert(tk.END, message + "\n")
        self.output_text.see(tk.END)
        self.root.update_idletasks()
    
    def _clear_output(self):
        """Clear output log"""
        self.output_text.delete("1.0", tk.END)