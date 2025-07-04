"""
Gmail OAuth Helper - Works with your existing Gmail setup
"""

import os
import json
import webbrowser
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional

class GmailOAuthHelper:
    """Gmail OAuth setup helper that works with existing structure"""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.redirect_port = 8080
        self.redirect_uri = f"http://localhost:{self.redirect_port}"
    
    def setup_gmail_account(self, email: str = None) -> bool:
        """Setup Gmail account with OAuth"""
        print("\n🔧 GMAIL ACCOUNT SETUP")
        print("=" * 30)
        
        if not email:
            email = input("Enter Gmail address: ").strip()
        
        if not email or '@' not in email:
            print("❌ Invalid email address")
            return False
        
        # Check if already configured
        existing_accounts = self.config_manager.get_gmail_accounts()
        if email in existing_accounts or email.replace('@', '_').replace('.', '_') in [acc.replace('@', '_').replace('.', '_') for acc in existing_accounts]:
            print(f"⚠️ Gmail account {email} already configured")
            choice = input("Reconfigure this account? (y/N): ").lower()
            if choice != 'y':
                return False
        
        print(f"\n📧 Setting up Gmail OAuth for: {email}")
        print("\n📋 BEFORE WE START:")
        print("You need Google Cloud credentials. If you don't have them:")
        print("1. Go to: https://console.cloud.google.com/")
        print("2. Create a project (or select existing)")
        print("3. Enable Gmail API")
        print("4. Create OAuth 2.0 credentials (Desktop Application)")
        print("5. Download the JSON file")
        
        choice = input("\nDo you have OAuth credentials ready? (y/N): ").lower()
        if choice != 'y':
            print("\n💡 Come back when you have the credentials file!")
            return False
        
        # Get credentials
        creds_data = self._get_credentials_data()
        if not creds_data:
            return False
        
        # Perform OAuth flow
        return self._perform_oauth_flow(email, creds_data)
    
    def _get_credentials_data(self) -> Optional[Dict[str, Any]]:
        """Get credentials data from user"""
        print("\n📁 CREDENTIALS INPUT:")
        print("1. Upload/paste file path to credentials JSON")
        print("2. Paste JSON content directly")
        
        choice = input("Choose option (1/2): ").strip()
        
        if choice == '1':
            file_path = input("Enter path to credentials JSON file: ").strip().strip('"')
            
            # Handle common Windows path issues
            if file_path.startswith('C:\\') or file_path.startswith('c:\\'):
                file_path = file_path.replace('\\', '/')
            
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r') as f:
                        return json.load(f)
                except Exception as e:
                    print(f"❌ Error reading file: {e}")
                    return None
            else:
                print("❌ File not found")
                return None
        
        elif choice == '2':
            print("\n📝 Paste the JSON content below (press Enter twice when done):")
            json_lines = []
            empty_lines = 0
            
            while True:
                line = input()
                if line == "":
                    empty_lines += 1
                    if empty_lines >= 2:
                        break
                else:
                    empty_lines = 0
                json_lines.append(line)
            
            json_content = '\n'.join(json_lines)
            
            try:
                return json.loads(json_content)
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON format: {e}")
                return None
        
        else:
            print("❌ Invalid choice")
            return None
    
    def _perform_oauth_flow(self, email: str, creds_data: Dict[str, Any]) -> bool:
        """Perform OAuth 2.0 flow"""
        try:
            # Check if we have the right structure
            if 'installed' not in creds_data:
                print("❌ Invalid credentials format. Expected 'installed' section.")
                return False
            
            # Import Google libraries
            try:
                from google.auth.transport.requests import Request
                from google.oauth2.credentials import Credentials
                from google_auth_oauthlib.flow import InstalledAppFlow
                from googleapiclient.discovery import build
            except ImportError as e:
                print(f"❌ Missing Google libraries: {e}")
                print("Install with: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
                return False
            
            # Gmail scopes
            SCOPES = [
                'https://www.googleapis.com/auth/gmail.readonly',
                'https://www.googleapis.com/auth/gmail.metadata',
                'https://www.googleapis.com/auth/userinfo.email'
            ]
            
            print(f"\n🌐 Starting OAuth flow for {email}...")
            print("📱 Your browser will open for authorization")
            
            # Create flow
            flow = InstalledAppFlow.from_client_config(creds_data, SCOPES)
            
            # Run OAuth flow
            creds = flow.run_local_server(
                port=self.redirect_port,
                open_browser=True,
                prompt='select_account'
            )
            
            # Test the credentials
            print("🧪 Testing Gmail connection...")
            service = build('gmail', 'v1', credentials=creds)
            
            # Get user profile
            profile = service.users().getProfile(userId='me').execute()
            authorized_email = profile.get('emailAddress', '')
            
            print(f"✅ Successfully authorized: {authorized_email}")
            
            # Verify email matches
            if authorized_email.lower() != email.lower():
                print(f"⚠️ Authorized email ({authorized_email}) differs from provided ({email})")
                choice = input("Use the authorized email instead? (Y/n): ").lower()
                if choice != 'n':
                    email = authorized_email
            
            # Save credentials in your format
            creds_to_save = {
                'token': creds.token,
                'refresh_token': creds.refresh_token,
                'token_uri': creds.token_uri,
                'client_id': creds.client_id,
                'client_secret': creds.client_secret,
                'scopes': creds.scopes,
                'email': email,
                'type': 'authorized_user'
            }
            
            # Save using your existing naming convention
            self.config_manager.save_gmail_credentials(email, creds_to_save)
            
            # Test with a simple API call
            print("🔍 Testing email access...")
            try:
                messages = service.users().messages().list(userId='me', maxResults=1).execute()
                message_count = messages.get('resultSizeEstimate', 0)
                print(f"✅ Successfully connected! Found ~{message_count} messages")
            except Exception as e:
                print(f"⚠️ Connection successful but API test failed: {e}")
            
            print(f"✅ Gmail account {email} configured successfully!")
            return True
            
        except Exception as e:
            print(f"❌ OAuth flow failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def list_gmail_accounts(self):
        """List configured Gmail accounts"""
        accounts = self.config_manager.get_gmail_accounts()
        
        if not accounts:
            print("❌ No Gmail accounts configured")
            return
        
        print(f"\n📧 CONFIGURED GMAIL ACCOUNTS:")
        for i, account in enumerate(accounts, 1):
            # Check if credentials file exists
            if account == "primary":
                creds_file = self.config_manager.config_dir / "gmail_credentials.json"
            else:
                creds_file = self.config_manager.config_dir / f"gmail_{account}_credentials.json"
            
            status = "✅" if creds_file.exists() else "❌"
            print(f"  {i}. {account} {status}")
    
    def test_gmail_connection(self, email: str) -> bool:
        """Test Gmail connection for specific account"""
        try:
            # Import Google libraries
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            from google.auth.transport.requests import Request
        except ImportError:
            print("❌ Google libraries not available")
            return False
        
        try:
            # Load credentials
            if email == "primary":
                creds_file = self.config_manager.config_dir / "gmail_credentials.json"
            else:
                creds_file = self.config_manager.config_dir / f"gmail_{email}_credentials.json"
            
            if not creds_file.exists():
                print(f"❌ Credentials file not found for {email}")
                return False
            
            with open(creds_file, 'r') as f:
                creds_data = json.load(f)
            
            # Create credentials object
            creds = Credentials.from_authorized_user_info(creds_data)
            
            # Refresh if needed
            if not creds.valid:
                if creds.expired and creds.refresh_token:
                    print("🔄 Refreshing expired token...")
                    creds.refresh(Request())
                    
                    # Save refreshed token
                    refreshed_data = {
                        'token': creds.token,
                        'refresh_token': creds.refresh_token,
                        'token_uri': creds.token_uri,
                        'client_id': creds.client_id,
                        'client_secret': creds.client_secret,
                        'scopes': creds.scopes,
                        'email': creds_data.get('email', email),
                        'type': 'authorized_user'
                    }
                    
                    with open(creds_file, 'w') as f:
                        json.dump(refreshed_data, f, indent=2)
                else:
                    print(f"❌ Invalid credentials for {email}")
                    return False
            
            # Test API call
            service = build('gmail', 'v1', credentials=creds)
            profile = service.users().getProfile(userId='me').execute()
            
            print(f"✅ Connection successful for {profile.get('emailAddress', email)}")
            return True
            
        except Exception as e:
            print(f"❌ Connection failed for {email}: {e}")
            return False
    
    def setup_multiple_accounts(self) -> int:
        """Interactive setup for multiple Gmail accounts"""
        print("\n📧 MULTIPLE GMAIL ACCOUNTS SETUP")
        print("=" * 40)
        
        configured_count = 0
        
        while True:
            current_accounts = self.config_manager.get_gmail_accounts()
            print(f"\nCurrently configured accounts: {len(current_accounts)}")
            
            if current_accounts:
                self.list_gmail_accounts()
            
            print("\nOptions:")
            print("1. Add new Gmail account")
            print("2. Test existing account")
            print("3. Remove account")
            print("4. Done")
            
            choice = input("Choose (1-4): ").strip()
            
            if choice == '1':
                if self.setup_gmail_account():
                    configured_count += 1
            
            elif choice == '2':
                accounts = self.config_manager.get_gmail_accounts()
                if accounts:
                    print("\nSelect account to test:")
                    for i, account in enumerate(accounts, 1):
                        print(f"  {i}. {account}")
                    
                    try:
                        idx = int(input("Enter account number: ")) - 1
                        if 0 <= idx < len(accounts):
                            self.test_gmail_connection(accounts[idx])
                        else:
                            print("❌ Invalid account number")
                    except ValueError:
                        print("❌ Invalid input")
                else:
                    print("❌ No accounts to test")
            
            elif choice == '3':
                accounts = self.config_manager.get_gmail_accounts()
                if accounts:
                    print("\nSelect account to remove:")
                    for i, account in enumerate(accounts, 1):
                        print(f"  {i}. {account}")
                    
                    try:
                        idx = int(input("Enter account number: ")) - 1
                        if 0 <= idx < len(accounts):
                            if self.config_manager.remove_gmail_account(accounts[idx]):
                                print("✅ Account removed successfully")
                            else:
                                print("❌ Failed to remove account")
                        else:
                            print("❌ Invalid account number")
                    except ValueError:
                        print("❌ Invalid input")
                else:
                    print("❌ No accounts to remove")
            
            elif choice == '4':
                break
            
            else:
                print("❌ Invalid choice")
        
        return configured_count