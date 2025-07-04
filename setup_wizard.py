"""
Interactive Setup Wizard for Email Enrichment App
Works with existing project structure and configuration
"""

import os
import sys
import getpass
from typing import Dict, Any, List
from pathlib import Path

from config_manager import EnhancedConfigManager
from gmail_oauth import GmailOAuthHelper

class SetupWizard:
    """Interactive setup wizard for first-time configuration"""
    
    def __init__(self):
        self.config_manager = EnhancedConfigManager()
        self.gmail_helper = GmailOAuthHelper(self.config_manager)
        
    def run_setup(self) -> bool:
        """Run the complete setup wizard"""
        print("🚀 EMAIL ENRICHMENT APP - SETUP WIZARD")
        print("=" * 50)
        print("Welcome! Let's configure your email enrichment system.")
        print()
        print("This wizard will help you set up:")
        print("• Email providers (Gmail, Outlook, Yahoo, iCloud)")  
        print("• API keys for enrichment services")
        print("• Application preferences")
        print()
        
        # Check if already configured
        status = self.config_manager.get_configuration_status()
        if not status['first_time']:
            print("⚠️ Configuration already exists:")
            print(f"  Email providers: {status['total_providers']}")
            print(f"  API services: {status['total_apis']}")
            print()
            choice = input("Do you want to reconfigure? (y/N): ").lower()
            if choice != 'y':
                return False
        
        try:
            print("\n" + "="*50)
            print("STEP 1: EMAIL PROVIDERS")
            print("="*50)
            if not self._setup_email_providers():
                return False
            
            print("\n" + "="*50)
            print("STEP 2: API SERVICES")
            print("="*50)
            self._setup_api_services()
            
            print("\n" + "="*50)
            print("STEP 3: APPLICATION SETTINGS")
            print("="*50)
            self._setup_app_preferences()
            
            print("\n" + "="*50)
            print("STEP 4: VERIFICATION")
            print("="*50)
            self._verify_setup()
            
            print("\n🎉 SETUP COMPLETE!")
            print("Your email enrichment system is ready to use.")
            print("You can now run the main application to start extracting contacts!")
            
            return True
            
        except KeyboardInterrupt:
            print("\n\n❌ Setup cancelled by user")
            return False
        except Exception as e:
            print(f"\n❌ Setup failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _setup_email_providers(self) -> bool:
        """Setup email providers - at least one is required"""
        print("Configure your email accounts for contact extraction.")
        print("You need at least ONE email provider to continue.")
        print()
        
        configured_providers = 0
        
        # Gmail Setup
        print("🔹 GMAIL")
        print("Gmail is the most reliable provider with the best API.")
        choice = input("Configure Gmail accounts? (Y/n): ").lower()
        if choice != 'n':
            try:
                count = self.gmail_helper.setup_multiple_accounts()
                if count > 0:
                    configured_providers += 1
                    print(f"✅ {count} Gmail account(s) configured")
            except Exception as e:
                print(f"⚠️ Gmail setup failed: {e}")
        
        # Outlook Setup
        print("\n🔹 OUTLOOK")
        print("Outlook requires Azure app registration (more complex setup).")
        choice = input("Configure Outlook accounts? (y/N): ").lower()
        if choice == 'y':
            if self._setup_outlook():
                configured_providers += 1
        
        # Yahoo Setup  
        print("\n🔹 YAHOO MAIL")
        print("Yahoo requires app-specific passwords (2FA must be enabled).")
        choice = input("Configure Yahoo Mail? (y/N): ").lower()
        if choice == 'y':
            if self._setup_yahoo():
                configured_providers += 1
        
        # iCloud Setup
        print("\n🔹 iCLOUD MAIL")
        print("iCloud requires app-specific passwords.")
        choice = input("Configure iCloud Mail? (y/N): ").lower()
        if choice == 'y':
            if self._setup_icloud():
                configured_providers += 1
        
        # Check if at least one provider is configured
        if configured_providers == 0:
            print("\n❌ NO EMAIL PROVIDERS CONFIGURED!")
            print("You need at least one email provider to use this application.")
            print("Please configure at least Gmail to continue.")
            return False
        
        print(f"\n✅ {configured_providers} email provider(s) configured successfully!")
        return True
    
    def _setup_outlook(self) -> bool:
        """Setup Microsoft Outlook configuration"""
        print("\n📧 OUTLOOK SETUP:")
        print("Outlook requires Azure Active Directory app registration.")
        print()
        print("📋 SETUP STEPS:")
        print("1. Go to: https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade")
        print("2. Click 'New registration'")
        print("3. Name: 'Email Enrichment Tool'")
        print("4. Account types: 'Personal Microsoft accounts only'")
        print("5. Redirect URI: http://localhost:8080/auth/callback")
        print("6. After creation, copy the 'Application (client) ID'")
        print("7. Go to 'Certificates & secrets' > 'New client secret'")
        print("8. Copy the secret VALUE (not the ID)")
        print()
        
        choice = input("Do you have Azure app credentials ready? (y/N): ").lower()
        if choice != 'y':
            print("💡 Come back to this step when you have the credentials!")
            return False
        
        client_id = input("Enter Azure App Client ID: ").strip()
        if not client_id:
            print("❌ Client ID is required")
            return False
        
        client_secret = getpass.getpass("Enter Azure App Client Secret: ").strip()
        if not client_secret:
            print("❌ Client Secret is required")
            return False
        
        # Save configuration
        provider_config = self.config_manager.load_provider_config()
        provider_config['outlook'] = {
            'enabled': True,
            'client_id': client_id,
            'client_secret': client_secret,
            'tenant_id': 'common'
        }
        self.config_manager.save_provider_config(provider_config)
        
        # Set environment variables
        os.environ['OUTLOOK_CLIENT_ID'] = client_id
        os.environ['OUTLOOK_CLIENT_SECRET'] = client_secret
        
        print("✅ Outlook configuration saved")
        return True
    
    def _setup_yahoo(self) -> bool:
        """Setup Yahoo Mail configuration"""
        print("\n📧 YAHOO MAIL SETUP:")
        print("Yahoo requires app-specific passwords (not your regular password).")
        print()
        print("📋 SETUP STEPS:")
        print("1. Go to: https://login.yahoo.com/account/security")
        print("2. Turn on 2-step verification (if not already enabled)")
        print("3. Click 'Generate app password'")
        print("4. Select 'Other app' and enter 'Email Enrichment Tool'")
        print("5. Copy the 16-character password")
        print()
        
        email = input("Enter Yahoo email address: ").strip()
        if not email or '@yahoo.com' not in email.lower():
            print("❌ Please enter a valid Yahoo email address")
            return False
        
        choice = input("Do you have a Yahoo app password ready? (y/N): ").lower()
        if choice != 'y':
            print("💡 Set up the app password first, then come back!")
            return False
        
        app_password = getpass.getpass("Enter Yahoo app password (16 characters): ").strip()
        if not app_password or len(app_password) != 16:
            print("❌ Yahoo app passwords are exactly 16 characters")
            return False
        
        # Save configuration
        provider_config = self.config_manager.load_provider_config()
        provider_config['yahoo'] = {
            'enabled': True,
            'email': email,
            'app_password': app_password
        }
        self.config_manager.save_provider_config(provider_config)
        
        # Set environment variables
        os.environ['YAHOO_EMAIL'] = email
        os.environ['YAHOO_APP_PASSWORD'] = app_password
        
        print("✅ Yahoo Mail configuration saved")
        return True
    
    def _setup_icloud(self) -> bool:
        """Setup iCloud Mail configuration"""
        print("\n📧 iCLOUD MAIL SETUP:")
        print("iCloud requires app-specific passwords.")
        print()
        print("📋 SETUP STEPS:")
        print("1. Go to: https://appleid.apple.com/")
        print("2. Sign in with your Apple ID")
        print("3. Go to 'Security' section")
        print("4. Under 'App-Specific Passwords', click 'Generate Password'")
        print("5. Enter 'Email Enrichment Tool' as the label")
        print("6. Copy the generated password")
        print()
        
        email = input("Enter iCloud email address (@icloud.com or @me.com): ").strip()
        if not email or ('@icloud.com' not in email.lower() and '@me.com' not in email.lower()):
            print("❌ Please enter a valid iCloud email address")
            return False
        
        choice = input("Do you have an iCloud app password ready? (y/N): ").lower()
        if choice != 'y':
            print("💡 Generate the app password first, then come back!")
            return False
        
        app_password = getpass.getpass("Enter iCloud app password: ").strip()
        if not app_password:
            print("❌ App password is required")
            return False
        
        # Save configuration
        provider_config = self.config_manager.load_provider_config()
        provider_config['icloud'] = {
            'enabled': True,
            'email': email,
            'app_password': app_password
        }
        self.config_manager.save_provider_config(provider_config)
        
        # Set environment variables
        os.environ['ICLOUD_EMAIL'] = email
        os.environ['ICLOUD_APP_PASSWORD'] = app_password
        
        print("✅ iCloud Mail configuration saved")
        return True
    
    def _setup_api_services(self):
        """Setup API services for enrichment"""
        print("Configure API keys for contact enrichment.")
        print("These are optional but provide much richer contact data.")
        print()
        
        # Priority services with free tiers
        priority_services = [
            {
                'name': 'OpenAI',
                'key': 'openai',
                'description': 'AI-powered email analysis and insights',
                'signup_url': 'https://platform.openai.com/',
                'free_tier': '$5 free credits for new accounts',
                'cost': '~$0.01 per 1K tokens'
            },
            {
                'name': 'Hunter.io',
                'key': 'hunter',
                'description': 'Email finder and verification',
                'signup_url': 'https://hunter.io/',
                'free_tier': '25 free searches/month',
                'cost': '~$0.01 per request'
            },
            {
                'name': 'People Data Labs',
                'key': 'peopledatalabs',
                'description': 'Comprehensive people data',
                'signup_url': 'https://www.peopledatalabs.com/',
                'free_tier': '100 free credits/month',
                'cost': '~$0.03 per request'
            }
        ]
        
        # Premium services
        premium_services = [
            {
                'name': 'Clearbit',
                'key': 'clearbit',
                'description': 'Premium B2B contact data',
                'signup_url': 'https://clearbit.com/',
                'free_tier': '100 free requests for new accounts',
                'cost': '~$0.50 per request'
            },
            {
                'name': 'Apollo.io',
                'key': 'apollo',
                'description': 'Sales intelligence platform',
                'signup_url': 'https://www.apollo.io/',
                'free_tier': '50 free credits/month',
                'cost': '~$0.05 per request'
            }
        ]
        
        configured_apis = 0
        
        print("🔹 PRIORITY APIS (Recommended - have free tiers):")
        for service in priority_services:
            print(f"\n📊 {service['name']}")
            print(f"   Description: {service['description']}")
            print(f"   Free tier: {service['free_tier']}")
            print(f"   Signup: {service['signup_url']}")
            
            choice = input(f"Configure {service['name']} API? (y/N): ").lower()
            if choice == 'y':
                api_key = getpass.getpass(f"Enter {service['name']} API key: ").strip()
                if api_key:
                    self.config_manager.save_api_key(service['key'], api_key)
                    configured_apis += 1
                    print(f"✅ {service['name']} API key saved")
                else:
                    print(f"⚠️ No API key provided for {service['name']}")
        
        print("\n🔹 PREMIUM APIS (Optional - higher cost but better data):")
        choice = input("Configure premium APIs? (y/N): ").lower()
        if choice == 'y':
            for service in premium_services:
                print(f"\n💰 {service['name']}")
                print(f"   Description: {service['description']}")
                print(f"   Cost: {service['cost']}")
                print(f"   Signup: {service['signup_url']}")
                
                choice = input(f"Configure {service['name']} API? (y/N): ").lower()
                if choice == 'y':
                    api_key = getpass.getpass(f"Enter {service['name']} API key: ").strip()
                    if api_key:
                        self.config_manager.save_api_key(service['key'], api_key)
                        configured_apis += 1
                        print(f"✅ {service['name']} API key saved")
        
        if configured_apis > 0:
            print(f"\n✅ {configured_apis} API service(s) configured")
        else:
            print("\n💡 No API services configured - you can add them later")
            print("   The app will work with basic enrichment only")
    
    def _setup_app_preferences(self):
        """Setup application preferences"""
        print("Configure default application settings.")
        print()
        
        settings = self.config_manager.load_app_settings()
        
        # Extraction defaults
        print("🔧 EXTRACTION SETTINGS:")
        days_back = input(f"Default days back to scan [{settings['extraction']['default_days_back']}]: ").strip()
        if days_back.isdigit():
            settings['extraction']['default_days_back'] = int(days_back)
        
        max_emails = input(f"Default max emails per account [{settings['extraction']['default_max_emails']}]: ").strip()
        if max_emails.isdigit():
            settings['extraction']['default_max_emails'] = int(max_emails)
        
        # Feature preferences
        print("\n🎯 FEATURE PREFERENCES:")
        enhanced_scoring = input(f"Enable enhanced AI scoring? (Y/n): ").lower()
        settings['features']['enhanced_scoring'] = enhanced_scoring != 'n'
        
        api_enrichment = input(f"Enable API enrichment by default? (Y/n): ").lower()
        settings['features']['api_enrichment'] = api_enrichment != 'n'
        
        # Export preferences
        print("\n📊 EXPORT PREFERENCES:")
        export_format = input("Default export format (excel/csv/json) [excel]: ").strip().lower()
        if export_format in ['excel', 'csv', 'json']:
            settings['export']['default_format'] = export_format
        
        include_charts = input("Include charts in Excel exports? (Y/n): ").lower()
        settings['export']['include_charts'] = include_charts != 'n'
        
        auto_open = input("Auto-open exports after completion? (Y/n): ").lower()
        settings['export']['auto_open'] = auto_open != 'n'
        
        # Save settings
        self.config_manager.save_app_settings(settings)
        print("✅ Application settings saved")
    
    def _verify_setup(self):
        """Verify the complete setup"""
        print("Verifying your configuration...")
        print()
        
        status = self.config_manager.get_configuration_status()
        
        # Display summary
        print("📋 CONFIGURATION SUMMARY:")
        print(f"  Email Providers: {status['total_providers']}")
        print(f"  API Services: {status['total_apis']}")
        print()
        
        # Show configured providers
        print("📧 EMAIL PROVIDERS:")
        for provider, count in status['email_providers'].items():
            if provider == 'gmail' and count > 0:
                print(f"  ✅ Gmail: {count} account(s)")
            elif provider != 'gmail' and count:
                print(f"  ✅ {provider.capitalize()}: configured")
        
        # Show configured APIs
        configured_apis = [name for name, configured in status['api_services'].items() if configured]
        if configured_apis:
            print("\n🔍 API SERVICES:")
            for api in configured_apis:
                print(f"  ✅ {api.capitalize()}")
        
        # Validation
        issues = self.config_manager.validate_configuration()
        if issues:
            print("\n⚠️ ISSUES FOUND:")
            for issue in issues:
                print(f"  • {issue}")
        else:
            print("\n✅ Configuration is valid!")
        
        # Setup environment
        print("\n🔧 Setting up environment variables...")
        self.config_manager.setup_environment_variables()
        print("✅ Environment configured")


def main():
    """Run setup wizard as standalone script"""
    wizard = SetupWizard()
    
    try:
        success = wizard.run_setup()
        if success:
            print("\n🚀 Setup completed successfully!")
            print("You can now run the main application:")
            print("  python app.py")
        else:
            print("\n❌ Setup was not completed")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()