"""
Main Application Entry Point - Email Enrichment App
Can run as GUI or CLI, handles setup wizard, and wraps your existing main.py
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from typing import Optional, List

# Add src directory to path to import your existing code
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config_manager import EnhancedConfigManager
from setup_wizard import SetupWizard

class EmailEnrichmentApp:
    """Main application wrapper that handles setup and execution"""
    
    def __init__(self):
        self.config_manager = EnhancedConfigManager()
        self.setup_wizard = SetupWizard()
        self.src_dir = Path(__file__).parent / "src"
        self.main_py = self.src_dir / "main.py"
        
    def run(self, args: Optional[List[str]] = None):
        """Main application entry point"""
        parser = self._create_parser()
        parsed_args = parser.parse_args(args)
        
        # Handle different run modes
        if parsed_args.setup:
            return self._run_setup()
        elif parsed_args.gui:
            return self._run_gui()
        elif parsed_args.status:
            return self._show_status()
        elif parsed_args.wizard:
            return self._run_setup()
        else:
            return self._run_cli(parsed_args)
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """Create argument parser"""
        parser = argparse.ArgumentParser(
            description="Email Enrichment App - Extract and enrich email contacts",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  python app.py --setup           # Run setup wizard
  python app.py --gui             # Launch GUI interface
  python app.py --status          # Show configuration status
  python app.py                   # Run with default settings
  python app.py --extract --enrich --export excel
            """
        )
        
        # App modes
        mode_group = parser.add_mutually_exclusive_group()
        mode_group.add_argument("--setup", "--wizard", action="store_true", 
                               help="Run setup wizard")
        mode_group.add_argument("--gui", action="store_true", 
                               help="Launch GUI interface")
        mode_group.add_argument("--status", action="store_true", 
                               help="Show configuration status")
        
        # Quick action shortcuts
        parser.add_argument("--quick-extract", action="store_true",
                           help="Quick extract with default settings")
        parser.add_argument("--extract", action="store_true",
                           help="Extract contacts")
        
        # Provider selection
        parser.add_argument("--providers", nargs="+", 
                           choices=["gmail", "outlook", "yahoo", "icloud"],
                           help="Email providers to use")
        
        # Extraction settings
        parser.add_argument("--days-back", type=int, default=30,
                           help="Days to look back (default: 30)")
        parser.add_argument("--max-emails", type=int, default=1000,
                           help="Max emails per account (default: 1000)")
        
        # Features
        parser.add_argument("--enrich", action="store_true",
                           help="Enable API enrichment")
        parser.add_argument("--enhanced-scoring", action="store_true",
                           help="Enable enhanced AI scoring")
        parser.add_argument("--basic-scoring", action="store_true",
                           help="Use basic scoring only")
        
        # Export options
        parser.add_argument("--export", "--export-format", 
                           choices=["excel", "csv", "json"],
                           help="Export format")
        parser.add_argument("--output-file", help="Output filename")
        parser.add_argument("--analytics", action="store_true",
                           help="Include analytics in export")
        
        # Other options
        parser.add_argument("--top-contacts", type=int, default=10,
                           help="Number of top contacts to show")
        parser.add_argument("--detailed-report", action="store_true",
                           help="Generate detailed analysis report")
        
        return parser
    
    def _run_setup(self) -> bool:
        """Run the setup wizard"""
        print("🚀 EMAIL ENRICHMENT APP - SETUP")
        print("=" * 40)
        
        try:
            return self.setup_wizard.run_setup()
        except Exception as e:
            print(f"❌ Setup failed: {e}")
            return False
    
    def _run_gui(self) -> bool:
        """Launch GUI interface"""
        try:
            # Try to import GUI components
            from gui.main_window import MainWindow
            import tkinter as tk
            
            print("🖥️ Launching GUI interface...")
            
            # Create and run GUI
            root = tk.Tk()
            app = MainWindow(root, self.config_manager)
            root.mainloop()
            
            return True
            
        except ImportError as e:
            print(f"❌ GUI not available: {e}")
            print("💡 Install GUI dependencies: pip install tkinter")
            print("💡 Or run in CLI mode instead")
            return False
        except Exception as e:
            print(f"❌ GUI failed to start: {e}")
            return False
    
    def _show_status(self) -> bool:
        """Show configuration status"""
        print("📊 EMAIL ENRICHMENT APP - STATUS")
        print("=" * 40)
        
        try:
            # Show configuration summary
            print(self.config_manager.export_configuration_summary())
            
            # Test connections if configured
            status = self.config_manager.get_configuration_status()
            if status['total_providers'] > 0:
                print("\n🧪 TESTING CONNECTIONS:")
                
                # Test Gmail accounts
                if status['email_providers']['gmail'] > 0:
                    from gmail_oauth import GmailOAuthHelper
                    gmail_helper = GmailOAuthHelper(self.config_manager)
                    
                    accounts = self.config_manager.get_gmail_accounts()
                    for account in accounts[:2]:  # Test first 2 accounts
                        print(f"  Testing Gmail ({account})...", end=" ")
                        if gmail_helper.test_gmail_connection(account):
                            print("✅")
                        else:
                            print("❌")
            
            return True
            
        except Exception as e:
            print(f"❌ Status check failed: {e}")
            return False
    
    def _run_cli(self, args) -> bool:
        """Run CLI interface (wraps your existing main.py)"""
        # Check if first time setup is needed
        if self.config_manager.is_first_time_setup():
            print("👋 Welcome to Email Enrichment App!")
            print("This appears to be your first time running the application.")
            print()
            choice = input("Would you like to run the setup wizard? (Y/n): ").lower()
            if choice != 'n':
                if not self._run_setup():
                    print("❌ Setup required to continue")
                    return False
        
        # Setup environment variables
        self.config_manager.setup_environment_variables()
        
        # Handle quick extract
        if args.quick_extract:
            return self._run_quick_extract()
        
        # Build command for your existing main.py
        cmd = [sys.executable, str(self.main_py)]
        
        # Convert arguments to main.py format
        if args.extract:
            cmd.append("--extract")
        
        if args.providers:
            cmd.extend(["--providers"] + args.providers)
        
        if args.days_back != 30:
            cmd.extend(["--days-back", str(args.days_back)])
        
        if args.max_emails != 1000:
            cmd.extend(["--max-emails", str(args.max_emails)])
        
        if args.enrich:
            cmd.append("--enrich")
        
        if args.enhanced_scoring:
            cmd.append("--enhanced-scoring")
        elif args.basic_scoring:
            cmd.append("--basic-scoring")
        
        if args.export:
            cmd.extend(["--export-format", args.export])
        
        if args.output_file:
            cmd.extend(["--output-file", args.output_file])
        
        if args.analytics:
            cmd.append("--analytics")
        
        if args.top_contacts != 10:
            cmd.extend(["--top-contacts", str(args.top_contacts)])
        
        if args.detailed_report:
            cmd.append("--detailed-report")
        
        # If no specific action, run with sensible defaults
        if not any([args.extract, args.export, args.enrich, args.enhanced_scoring]):
            # Load user preferences
            settings = self.config_manager.load_app_settings()
            
            cmd.append("--extract")
            
            if settings['features']['enhanced_scoring']:
                cmd.append("--enhanced-scoring")
            
            if settings['features']['api_enrichment']:
                cmd.append("--enrich")
            
            if settings['export']['default_format']:
                cmd.extend(["--export-format", settings['export']['default_format']])
            
            if settings['features']['export_analytics']:
                cmd.append("--analytics")
        
        # Run the command
        try:
            print(f"🚀 Running: {' '.join(cmd[2:])}")  # Skip python and script path
            print("=" * 50)
            
            result = subprocess.run(cmd, cwd=self.src_dir.parent)
            return result.returncode == 0
            
        except Exception as e:
            print(f"❌ Execution failed: {e}")
            return False
    
    def _run_quick_extract(self) -> bool:
        """Run quick extraction with optimal defaults"""
        print("⚡ QUICK EXTRACT MODE")
        print("=" * 25)
        
        # Load user settings
        settings = self.config_manager.load_app_settings()
        status = self.config_manager.get_configuration_status()
        
        # Build optimized command
        cmd = [sys.executable, str(self.main_py)]
        cmd.append("--extract")
        
        # Use configured providers or default to Gmail
        if status['email_providers']['gmail'] > 0:
            cmd.extend(["--providers", "gmail"])
        elif status['total_providers'] > 0:
            # Use first available provider
            for provider, configured in status['email_providers'].items():
                if configured:
                    cmd.extend(["--providers", provider])
                    break
        
        # Optimal settings for quick extraction
        cmd.extend(["--days-back", "30"])
        cmd.extend(["--max-emails", "500"])  # Reduced for speed
        
        # Enable features based on configuration
        if status['total_apis'] > 0 and settings['features']['api_enrichment']:
            cmd.append("--enrich")
        
        if settings['features']['enhanced_scoring']:
            cmd.append("--enhanced-scoring")
        
        # Always export for quick extract
        cmd.extend(["--export-format", settings['export']['default_format']])
        cmd.append("--analytics")
        
        # Show fewer contacts for quick overview
        cmd.extend(["--top-contacts", "5"])
        
        try:
            print("Running optimized extraction...")
            result = subprocess.run(cmd, cwd=self.src_dir.parent)
            
            if result.returncode == 0:
                print("\n✅ Quick extract completed successfully!")
                
                # Auto-open export if enabled
                if settings['export']['auto_open']:
                    self._try_open_latest_export()
            
            return result.returncode == 0
            
        except Exception as e:
            print(f"❌ Quick extract failed: {e}")
            return False
    
    def _try_open_latest_export(self):
        """Try to open the latest export file"""
        try:
            exports_dir = self.config_manager.exports_dir
            if not exports_dir.exists():
                return
            
            # Find latest export file
            export_files = []
            for ext in ['*.xlsx', '*.csv', '*.json']:
                export_files.extend(exports_dir.glob(ext))
            
            if export_files:
                latest_file = max(export_files, key=lambda f: f.stat().st_mtime)
                
                # Try to open with default application
                if os.name == 'nt':  # Windows
                    os.startfile(str(latest_file))
                elif os.name == 'posix':  # macOS and Linux
                    subprocess.run(['open' if sys.platform == 'darwin' else 'xdg-open', str(latest_file)])
                
                print(f"📁 Opened: {latest_file.name}")
                
        except Exception as e:
            print(f"⚠️ Could not auto-open export: {e}")


def main():
    """Main entry point"""
    app = EmailEnrichmentApp()
    
    try:
        success = app.run()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Application error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()