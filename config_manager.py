"""
Enhanced Configuration Manager for Email Enrichment App
Works with existing file structure and naming conventions
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
import keyring
from cryptography.fernet import Fernet
import getpass

class EnhancedConfigManager:
    """Enhanced configuration manager that respects existing file structure"""
    
    def __init__(self):
        # Use existing directory structure
        self.project_root = Path(__file__).parent
        self.config_dir = self.project_root / "config"
        self.data_dir = self.project_root / "data"
        self.exports_dir = self.project_root / "exports"
        
        # Ensure directories exist
        self.config_dir.mkdir(exist_ok=True)
        self.data_dir.mkdir(exist_ok=True)
        self.exports_dir.mkdir(exist_ok=True)
        
        # Configuration files (respecting existing naming)
        self.provider_config_file = self.config_dir / "provider_config.yaml"
        self.enrichment_config_file = self.config_dir / "enrichment_config.yaml"
        self.app_settings_file = self.config_dir / "app_settings.yaml"
        self.env_file = self.project_root / ".env"
        
        # Initialize encryption for sensitive data
        self._init_encryption()
    
    def _init_encryption(self):
        """Initialize encryption for sensitive data storage"""
        app_name = "EmailEnrichmentApp"
        try:
            # Try to use Windows Credential Manager
            key_b64 = keyring.get_password(app_name, "encryption_key")
            if key_b64:
                self.fernet = Fernet(key_b64.encode())
            else:
                key = Fernet.generate_key()
                keyring.set_password(app_name, "encryption_key", key.decode())
                self.fernet = Fernet(key)
        except Exception:
            # Fallback to file-based encryption
            key_file = self.config_dir / ".app_encryption_key"
            if key_file.exists():
                with open(key_file, 'rb') as f:
                    key = f.read()
            else:
                key = Fernet.generate_key()
                with open(key_file, 'wb') as f:
                    f.write(key)
                # Hide the file on Windows
                if os.name == 'nt':
                    try:
                        os.system(f'attrib +h "{key_file}"')
                    except:
                        pass
            self.fernet = Fernet(key)
    
    def encrypt_value(self, value: str) -> str:
        """Encrypt sensitive value"""
        return self.fernet.encrypt(value.encode()).decode()
    
    def decrypt_value(self, encrypted_value: str) -> str:
        """Decrypt sensitive value"""
        return self.fernet.decrypt(encrypted_value.encode()).decode()
    
    # === Gmail Account Management ===
    def save_gmail_credentials(self, email: str, credentials_data: Dict[str, Any]) -> str:
        """Save Gmail OAuth credentials using existing naming convention"""
        # Use your existing naming: gmail_email@domain.com_credentials.json
        creds_file = self.config_dir / f"gmail_{email}_credentials.json"
        
        with open(creds_file, 'w') as f:
            json.dump(credentials_data, f, indent=2)
        
        print(f"✅ Gmail credentials saved: {creds_file.name}")
        return str(creds_file)
    
    def get_gmail_accounts(self) -> List[str]:
        """Get list of configured Gmail accounts"""
        accounts = []
        
        # Check for primary credentials file
        primary_creds = self.config_dir / "gmail_credentials.json"
        if primary_creds.exists():
            accounts.append("primary")
        
        # Check for email-specific credentials files
        for file in self.config_dir.glob("gmail_*_credentials.json"):
            filename = file.stem
            if filename.startswith("gmail_") and filename.endswith("_credentials"):
                email = filename[6:-12]  # Remove "gmail_" and "_credentials"
                if email != "credentials":  # Skip the primary one
                    accounts.append(email)
        
        return accounts
    
    def remove_gmail_account(self, email: str) -> bool:
        """Remove Gmail account configuration"""
        try:
            if email == "primary":
                creds_file = self.config_dir / "gmail_credentials.json"
            else:
                creds_file = self.config_dir / f"gmail_{email}_credentials.json"
            
            if creds_file.exists():
                creds_file.unlink()
                print(f"✅ Removed Gmail account: {email}")
                return True
            else:
                print(f"❌ Gmail account not found: {email}")
                return False
        except Exception as e:
            print(f"❌ Error removing Gmail account: {e}")
            return False
    
    # === API Key Management ===
    def save_api_key(self, service: str, api_key: str, use_keyring: bool = True):
        """Save API key securely"""
        if use_keyring:
            try:
                keyring.set_password("EmailEnrichmentApp", f"{service}_api_key", api_key)
                print(f"✅ {service} API key saved to Windows Credential Manager")
                return
            except Exception as e:
                print(f"⚠️ Keyring failed, using encrypted file storage: {e}")
        
        # Fallback to encrypted environment file
        self._update_env_file(f"{service.upper()}_API_KEY", self.encrypt_value(api_key))
        print(f"✅ {service} API key saved to encrypted .env file")
    
    def get_api_key(self, service: str) -> Optional[str]:
        """Get API key securely"""
        # Try keyring first
        try:
            api_key = keyring.get_password("EmailEnrichmentApp", f"{service}_api_key")
            if api_key:
                return api_key
        except Exception:
            pass
        
        # Try environment variable
        env_key = f"{service.upper()}_API_KEY"
        encrypted_value = os.getenv(env_key)
        if encrypted_value:
            try:
                return self.decrypt_value(encrypted_value)
            except Exception:
                # Might be unencrypted legacy value
                return encrypted_value
        
        return None
    
    def _update_env_file(self, key: str, value: str):
        """Update .env file with key-value pair"""
        env_vars = {}
        
        # Read existing .env file
        if self.env_file.exists():
            with open(self.env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        env_vars[k.strip()] = v.strip()
        
        # Update the value
        env_vars[key] = value
        
        # Write back to .env file
        with open(self.env_file, 'w') as f:
            f.write("# Email Enrichment App Configuration\n")
            f.write("# Auto-generated - do not edit manually\n\n")
            for k, v in env_vars.items():
                f.write(f"{k}={v}\n")
    
    # === Provider Configuration ===
    def save_provider_config(self, config: Dict[str, Any]):
        """Save provider configuration"""
        with open(self.provider_config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, indent=2)
        print(f"✅ Provider configuration saved to {self.provider_config_file.name}")
    
    def load_provider_config(self) -> Dict[str, Any]:
        """Load provider configuration"""
        if self.provider_config_file.exists():
            with open(self.provider_config_file, 'r') as f:
                return yaml.safe_load(f) or {}
        return {}
    
    def save_enrichment_config(self, config: Dict[str, Any]):
        """Save enrichment configuration"""
        with open(self.enrichment_config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, indent=2)
        print(f"✅ Enrichment configuration saved to {self.enrichment_config_file.name}")
    
    def load_enrichment_config(self) -> Dict[str, Any]:
        """Load enrichment configuration"""
        if self.enrichment_config_file.exists():
            with open(self.enrichment_config_file, 'r') as f:
                return yaml.safe_load(f) or {}
        return self._get_default_enrichment_config()
    
    def _get_default_enrichment_config(self) -> Dict[str, Any]:
        """Get default enrichment configuration"""
        return {
            'sources': {
                'clearbit': {'enabled': False, 'api_key': ''},
                'hunter': {'enabled': False, 'api_key': ''},
                'peopledatalabs': {'enabled': False, 'api_key': ''},
                'apollo': {'enabled': False, 'api_key': ''},
                'zoominfo': {'enabled': False, 'api_key': ''},
                'openai': {'enabled': False, 'api_key': ''}
            }
        }
    
    # === App Settings ===
    def save_app_settings(self, settings: Dict[str, Any]):
        """Save application settings"""
        with open(self.app_settings_file, 'w') as f:
            yaml.dump(settings, f, default_flow_style=False, indent=2)
    
    def load_app_settings(self) -> Dict[str, Any]:
        """Load application settings"""
        if self.app_settings_file.exists():
            with open(self.app_settings_file, 'r') as f:
                return yaml.safe_load(f) or {}
        return self._get_default_app_settings()
    
    def _get_default_app_settings(self) -> Dict[str, Any]:
        """Get default application settings"""
        return {
            'extraction': {
                'default_days_back': 30,
                'default_max_emails': 1000,
                'default_providers': ['gmail']
            },
            'features': {
                'enhanced_scoring': True,
                'api_enrichment': True,
                'export_analytics': True
            },
            'export': {
                'default_format': 'excel',
                'include_charts': True,
                'auto_open': True
            },
            'ui': {
                'theme': 'light',
                'show_advanced_options': False,
                'remember_last_settings': True
            }
        }
    
    # === Environment Setup ===
    def setup_environment_variables(self):
        """Setup environment variables from stored credentials"""
        # Load API keys
        api_services = ['clearbit', 'hunter', 'peopledatalabs', 'apollo', 'zoominfo', 'openai']
        for service in api_services:
            api_key = self.get_api_key(service)
            if api_key:
                os.environ[f"{service.upper()}_API_KEY"] = api_key
        
        # Load provider configs
        provider_config = self.load_provider_config()
        
        # Set Outlook environment variables
        outlook_config = provider_config.get('outlook', {})
        if outlook_config.get('client_id'):
            os.environ['OUTLOOK_CLIENT_ID'] = outlook_config['client_id']
        if outlook_config.get('client_secret'):
            os.environ['OUTLOOK_CLIENT_SECRET'] = outlook_config['client_secret']
        
        # Set Yahoo environment variables
        yahoo_config = provider_config.get('yahoo', {})
        if yahoo_config.get('email'):
            os.environ['YAHOO_EMAIL'] = yahoo_config['email']
        if yahoo_config.get('app_password'):
            os.environ['YAHOO_APP_PASSWORD'] = yahoo_config['app_password']
        
        # Set iCloud environment variables
        icloud_config = provider_config.get('icloud', {})
        if icloud_config.get('email'):
            os.environ['ICLOUD_EMAIL'] = icloud_config['email']
        if icloud_config.get('app_password'):
            os.environ['ICLOUD_APP_PASSWORD'] = icloud_config['app_password']
    
    # === Status and Validation ===
    def is_first_time_setup(self) -> bool:
        """Check if this is first time setup"""
        return not (
            self.provider_config_file.exists() or 
            self.get_gmail_accounts() or 
            any(self.get_api_key(service) for service in ['clearbit', 'hunter', 'peopledatalabs', 'openai'])
        )
    
    def get_configuration_status(self) -> Dict[str, Any]:
        """Get comprehensive configuration status"""
        # Count configured providers
        provider_config = self.load_provider_config()
        gmail_accounts = self.get_gmail_accounts()
        
        # API keys status
        api_services = ['clearbit', 'hunter', 'peopledatalabs', 'apollo', 'zoominfo', 'openai']
        api_status = {service: bool(self.get_api_key(service)) for service in api_services}
        
        return {
            'first_time': self.is_first_time_setup(),
            'email_providers': {
                'gmail': len(gmail_accounts),
                'outlook': bool(provider_config.get('outlook', {}).get('client_id')),
                'yahoo': bool(provider_config.get('yahoo', {}).get('email')),
                'icloud': bool(provider_config.get('icloud', {}).get('email'))
            },
            'api_services': api_status,
            'gmail_accounts': gmail_accounts,
            'total_providers': len(gmail_accounts) + sum([
                bool(provider_config.get('outlook', {}).get('client_id')),
                bool(provider_config.get('yahoo', {}).get('email')),
                bool(provider_config.get('icloud', {}).get('email'))
            ]),
            'total_apis': sum(api_status.values()),
            'config_files': {
                'provider_config': self.provider_config_file.exists(),
                'enrichment_config': self.enrichment_config_file.exists(),
                'app_settings': self.app_settings_file.exists()
            }
        }
    
    def validate_configuration(self) -> List[str]:
        """Validate current configuration and return issues"""
        issues = []
        status = self.get_configuration_status()
        
        if status['total_providers'] == 0:
            issues.append("No email providers configured")
        
        if status['total_apis'] == 0:
            issues.append("No API keys configured - enrichment will be limited")
        
        # Check for required directories
        if not self.config_dir.exists():
            issues.append("Config directory missing")
        
        if not self.data_dir.exists():
            issues.append("Data directory missing")
        
        return issues
    
    def export_configuration_summary(self) -> str:
        """Export configuration summary for debugging"""
        status = self.get_configuration_status()
        
        summary = []
        summary.append("=== EMAIL ENRICHMENT APP CONFIGURATION ===")
        summary.append(f"Project Root: {self.project_root}")
        summary.append(f"Config Directory: {self.config_dir}")
        summary.append("")
        
        summary.append("EMAIL PROVIDERS:")
        for provider, configured in status['email_providers'].items():
            status_str = f"{configured} accounts" if provider == 'gmail' else ("✅" if configured else "❌")
            summary.append(f"  {provider.capitalize()}: {status_str}")
        
        summary.append("")
        summary.append("API SERVICES:")
        for service, configured in status['api_services'].items():
            summary.append(f"  {service.capitalize()}: {'✅' if configured else '❌'}")
        
        summary.append("")
        summary.append("CONFIGURATION FILES:")
        for file, exists in status['config_files'].items():
            summary.append(f"  {file}: {'✅' if exists else '❌'}")
        
        if status['gmail_accounts']:
            summary.append("")
            summary.append("GMAIL ACCOUNTS:")
            for account in status['gmail_accounts']:
                summary.append(f"  • {account}")
        
        validation_issues = self.validate_configuration()
        if validation_issues:
            summary.append("")
            summary.append("ISSUES:")
            for issue in validation_issues:
                summary.append(f"  ⚠️ {issue}")
        
        return "\n".join(summary)