"""
Gmail Contact Extractor - Real Data Version
Connects to your actual Gmail account and extracts real contact information
"""

import os
import re
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Set, Tuple
from email.utils import parseaddr
from collections import defaultdict, Counter

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from tqdm import tqdm
import colorama
from colorama import Fore, Style

from config.config import *

# Initialize colorama
colorama.init()

class RealContact:
    """Enhanced contact data structure for real Gmail data"""
    def __init__(self, name: str, email: str):
        self.name = self._clean_name(name)
        self.email = email.lower().strip()
        self.frequency = 1
        self.first_seen = datetime.now()
        self.last_seen = datetime.now()
        self.location = ""
        self.estimated_net_worth = ""
        self.data_source = ""
        self.confidence = 0.0
        self.domain = email.split('@')[1] if '@' in email else ""
        self.sent_to = 0      # Emails you sent to them
        self.received_from = 0  # Emails you received from them
        self.in_cc = 0        # Times they were CC'd
        self.contact_type = self._determine_contact_type()
    
    def _clean_name(self, name: str) -> str:
        """Clean and normalize contact name"""
        if not name:
            return ""
        
        # Remove common email artifacts
        name = re.sub(r'[<>"\']', '', name)
        name = re.sub(r'\s+', ' ', name)
        name = name.strip()
        
        # If name looks like an email, extract the local part
        if '@' in name:
            name = name.split('@')[0]
        
        # Convert from "lastname, firstname" to "firstname lastname"
        if ',' in name and len(name.split(',')) == 2:
            parts = [p.strip() for p in name.split(',')]
            name = f"{parts[1]} {parts[0]}"
        
        return name
    
    def _determine_contact_type(self) -> str:
        """Determine the type of contact based on domain"""
        domain = self.domain.lower()
        
        if domain in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'icloud.com']:
            return 'personal'
        elif domain.endswith('.edu'):
            return 'academic'
        elif domain.endswith('.gov'):
            return 'government'
        elif domain in ['apple.com', 'google.com', 'microsoft.com', 'amazon.com', 'meta.com', 'salesforce.com']:
            return 'big_tech'
        else:
            return 'business'
    
    def update_interaction(self, direction: str):
        """Update interaction statistics"""
        self.frequency += 1
        self.last_seen = datetime.now()
        
        if direction == 'sent':
            self.sent_to += 1
        elif direction == 'received':
            self.received_from += 1
        elif direction == 'cc':
            self.in_cc += 1
    
    def __hash__(self):
        return hash(self.email)
    
    def __eq__(self, other):
        return isinstance(other, RealContact) and self.email == other.email
    
    def to_dict(self):
        return {
            'name': self.name,
            'email': self.email,
            'frequency': self.frequency,
            'sent_to': self.sent_to,
            'received_from': self.received_from,
            'in_cc': self.in_cc,
            'contact_type': self.contact_type,
            'domain': self.domain,
            'first_seen': self.first_seen.isoformat(),
            'last_seen': self.last_seen.isoformat(),
            'location': self.location,
            'estimated_net_worth': self.estimated_net_worth,
            'data_source': self.data_source,
            'confidence': self.confidence
        }

class RealGmailExtractor:
    """Gmail API integration for extracting real contact data"""
    
    def __init__(self):
        self.service = None
        self.contacts = {}  # email -> RealContact
        self.my_email = ""
        self.processed_messages = 0
        self.api_calls = 0
        
    def authenticate(self):
        """Authenticate with Gmail API using OAuth 2.0"""
        print(f"{Fore.CYAN}🔐 Authenticating with Gmail API...{Style.RESET_ALL}")
        
        creds = None
        
        # Load existing token if available
        if GMAIL_TOKEN_FILE.exists():
            try:
                with open(GMAIL_TOKEN_FILE, 'r') as token:
                    creds_data = json.load(token)
                    creds = Credentials.from_authorized_user_info(creds_data, GMAIL_SCOPES)
                print(f"{Fore.GREEN}📄 Found existing authentication token{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.YELLOW}⚠️ Error reading token file: {e}{Style.RESET_ALL}")
                creds = None
        
        # If there are no valid credentials, request authorization
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print(f"{Fore.YELLOW}🔄 Refreshing expired token...{Style.RESET_ALL}")
                try:
                    creds.refresh(Request())
                    print(f"{Fore.GREEN}✅ Token refreshed successfully{Style.RESET_ALL}")
                except Exception as e:
                    print(f"{Fore.RED}❌ Token refresh failed: {e}{Style.RESET_ALL}")
                    creds = None
            
            if not creds:
                if not GMAIL_CREDENTIALS_FILE.exists():
                    print(f"{Fore.RED}❌ Gmail credentials file not found!{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}Expected location: {GMAIL_CREDENTIALS_FILE}{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}Please download credentials from Google Cloud Console{Style.RESET_ALL}")
                    return False
                
                print(f"{Fore.YELLOW}🌐 Opening browser for Gmail authorization...{Style.RESET_ALL}")
                print(f"{Fore.WHITE}Please complete the authentication in your browser{Style.RESET_ALL}")
                
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(GMAIL_CREDENTIALS_FILE), GMAIL_SCOPES)
                    creds = flow.run_local_server(port=0)
                    print(f"{Fore.GREEN}✅ Authentication completed{Style.RESET_ALL}")
                except Exception as e:
                    print(f"{Fore.RED}❌ Authentication failed: {e}{Style.RESET_ALL}")
                    return False
            
            # Save credentials for next run
            try:
                with open(GMAIL_TOKEN_FILE, 'w') as token:
                    token.write(creds.to_json())
                print(f"{Fore.GREEN}💾 Authentication token saved{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.YELLOW}⚠️ Could not save token: {e}{Style.RESET_ALL}")
        
        try:
            self.service = build('gmail', 'v1', credentials=creds)
            self.api_calls += 1
            
            # Test the connection and get user info
            profile = self.service.users().getProfile(userId='me').execute()
            self.my_email = profile.get('emailAddress', 'Unknown')
            
            print(f"{Fore.GREEN}✅ Successfully connected to Gmail{Style.RESET_ALL}")
            print(f"{Fore.CYAN}📧 Account: {self.my_email}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}📊 Total messages in account: {profile.get('messagesTotal', 'Unknown')}{Style.RESET_ALL}")
            
            return True
            
        except HttpError as error:
            print(f"{Fore.RED}❌ Gmail API Error: {error}{Style.RESET_ALL}")
            return False
    
    def extract_emails_from_header(self, header_value: str) -> List[Tuple[str, str]]:
        """Extract name and email pairs from email header"""
        if not header_value:
            return []
        
        contacts = []
        
        # Split by comma to handle multiple recipients
        parts = [part.strip() for part in header_value.split(',')]
        
        for part in parts:
            # Try to parse name and email
            name, email = parseaddr(part)
            
            if email and '@' in email:
                # Clean up the name
                name = name.strip(' "\'')
                email = email.lower().strip()
                
                # Filter out system emails and my own email
                if self._is_valid_contact_email(email) and email != self.my_email.lower():
                    contacts.append((name, email))
        
        return contacts
    
    def _is_valid_contact_email(self, email: str) -> bool:
        """Filter out system/bot emails"""
        if not email or '@' not in email:
            return False
        
        email_lower = email.lower()
        domain = email_lower.split('@')[1]
        
        # Check exclude domains
        if domain in EXCLUDE_DOMAINS:
            return False
        
        # Check exclude keywords
        if any(keyword in email_lower for keyword in EXCLUDE_KEYWORDS):
            return False
        
        # Additional filtering for common patterns
        if re.match(r'^(noreply|no-reply|donotreply)', email_lower):
            return False
        
        return True
    
    def scan_emails(self, days_back: int = DAYS_BACK, max_emails: int = MAX_EMAILS_TO_PROCESS):
        """Scan Gmail for real contact data"""
        if not self.service:
            print(f"{Fore.RED}❌ Not authenticated with Gmail{Style.RESET_ALL}")
            return []
        
        print(f"{Fore.CYAN}📧 Scanning Gmail for contacts...{Style.RESET_ALL}")
        print(f"   📅 Looking back {days_back} days")
        print(f"   📊 Processing up to {max_emails} emails")
        print()
        
        try:
            # Build query for recent emails
            since_date = datetime.now() - timedelta(days=days_back)
            query = f'after:{since_date.strftime("%Y/%m/%d")}'
            
            # Get message list
            print(f"{Fore.YELLOW}🔍 Fetching message list from Gmail...{Style.RESET_ALL}")
            result = self.service.users().messages().list(
                userId='me', 
                q=query, 
                maxResults=max_emails
            ).execute()
            self.api_calls += 1
            
            messages = result.get('messages', [])
            total_messages = len(messages)
            
            if total_messages == 0:
                print(f"{Fore.YELLOW}⚠️ No messages found in the last {days_back} days{Style.RESET_ALL}")
                return []
            
            print(f"{Fore.GREEN}📬 Found {total_messages} messages to analyze{Style.RESET_ALL}")
            print(f"{Fore.CYAN}🔄 Starting contact extraction...{Style.RESET_ALL}")
            print()
            
            # Process each message with progress bar
            if SHOW_PROGRESS_BARS:
                message_iterator = tqdm(
                    messages, 
                    desc="Extracting contacts", 
                    unit="email",
                    bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"
                )
            else:
                message_iterator = messages
            
            processed_count = 0
            error_count = 0
            
            for message in message_iterator:
                try:
                    # Get message metadata (efficient, minimal data transfer)
                    msg = self.service.users().messages().get(
                        userId='me', 
                        id=message['id'], 
                        format='metadata',
                        metadataHeaders=['From', 'To', 'Cc', 'Bcc', 'Subject', 'Date']
                    ).execute()
                    self.api_calls += 1
                    
                    # Extract contacts from headers
                    headers = msg['payload'].get('headers', [])
                    subject = ""
                    
                    for header in headers:
                        header_name = header['name'].lower()
                        header_value = header.get('value', '')
                        
                        if header_name == 'subject':
                            subject = header_value
                        elif header_name in ['from', 'to', 'cc', 'bcc']:
                            contacts = self.extract_emails_from_header(header_value)
                            
                            for name, email in contacts:
                                # Determine interaction direction
                                if header_name == 'from':
                                    direction = 'received'
                                elif header_name == 'to':
                                    direction = 'sent'
                                else:  # cc, bcc
                                    direction = 'cc'
                                
                                self._add_or_update_contact(name, email, direction, subject)
                    
                    processed_count += 1
                    self.processed_messages += 1
                    
                    # Rate limiting - be nice to Gmail API
                    if processed_count % 100 == 0:
                        time.sleep(0.1)  # Small pause every 100 messages
                
                except Exception as e:
                    error_count += 1
                    if SHOW_PROGRESS_BARS:
                        tqdm.write(f"{Fore.YELLOW}⚠️ Error processing message: {str(e)[:50]}...{Style.RESET_ALL}")
                    continue
            
            unique_contacts = len(self.contacts)
            print()
            print(f"{Fore.GREEN}✅ Email scanning completed!{Style.RESET_ALL}")
            print(f"   📊 Processed: {processed_count} emails")
            print(f"   👥 Found: {unique_contacts} unique contacts")
            print(f"   ⚠️ Errors: {error_count}")
            print(f"   🔗 API calls made: {self.api_calls}")
            
            if error_count > 0:
                print(f"{Fore.YELLOW}   Note: {error_count} emails had processing errors (this is normal){Style.RESET_ALL}")
            
            return list(self.contacts.values())
            
        except HttpError as error:
            print(f"{Fore.RED}❌ Gmail API Error: {error}{Style.RESET_ALL}")
            return []
        except Exception as e:
            print(f"{Fore.RED}❌ Unexpected error: {e}{Style.RESET_ALL}")
            return []
    
    def _add_or_update_contact(self, name: str, email: str, direction: str, subject: str = ""):
        """Add new contact or update existing one with interaction data"""
        if email in self.contacts:
            # Update existing contact
            contact = self.contacts[email]
            contact.update_interaction(direction)
            
            # Update name if the new one is better (longer/more complete)
            if len(name) > len(contact.name) and name:
                contact.name = name
        else:
            # Create new contact
            contact = RealContact(name or email.split('@')[0], email)
            contact.update_interaction(direction)
            self.contacts[email] = contact
    
    def get_contacts_summary(self):
        """Get a detailed summary of extracted contacts"""
        if not self.contacts:
            return "No contacts found"
        
        total = len(self.contacts)
        with_names = sum(1 for c in self.contacts.values() if c.name and c.name != c.email.split('@')[0])
        frequent = sum(1 for c in self.contacts.values() if c.frequency >= 5)
        
        # Analyze by contact type
        type_counts = Counter(c.contact_type for c in self.contacts.values())
        
        # Get top domains
        domain_counts = Counter(c.domain for c in self.contacts.values())
        top_domains = domain_counts.most_common(5)
        
        summary = f"""
{Fore.CYAN}📊 Real Gmail Contact Analysis:{Style.RESET_ALL}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{Fore.WHITE}📈 Overview:{Style.RESET_ALL}
• Total unique contacts: {total}
• Contacts with real names: {with_names} ({with_names/total*100:.1f}%)
• Frequent contacts (5+ emails): {frequent} ({frequent/total*100:.1f}%)

{Fore.WHITE}👥 Contact Types:{Style.RESET_ALL}
"""
        
        for contact_type, count in type_counts.items():
            percentage = (count / total) * 100
            summary += f"• {contact_type.replace('_', ' ').title()}: {count} ({percentage:.1f}%)\n"
        
        summary += f"""
{Fore.WHITE}🏢 Top Domains:{Style.RESET_ALL}
"""
        
        for domain, count in top_domains:
            percentage = (count / total) * 100
            summary += f"• {domain}: {count} ({percentage:.1f}%)\n"
        
        summary += f"""
{Fore.WHITE}🔝 Most Frequent Contacts:{Style.RESET_ALL}
"""
        
        # Show top contacts by frequency
        top_contacts = sorted(self.contacts.values(), key=lambda x: x.frequency, reverse=True)[:5]
        
        for i, contact in enumerate(top_contacts, 1):
            name_display = contact.name if contact.name else "Unknown"
            domain = contact.domain
            frequency = contact.frequency
            contact_type = contact.contact_type.replace('_', ' ').title()
            
            summary += f"{i}. {name_display} (@{domain}) - {frequency} emails [{contact_type}]\n"
        
        return summary

# Test function for real Gmail data
def test_real_gmail_extraction():
    """Test function for real Gmail extraction"""
    print(f"{Fore.MAGENTA}🚀 Real Gmail Contact Extraction{Style.RESET_ALL}")
    print("=" * 60)
    
    extractor = RealGmailExtractor()
    
    # Step 1: Authenticate
    if not extractor.authenticate():
        print(f"{Fore.RED}❌ Authentication failed. Please check your setup.{Style.RESET_ALL}")
        return None
    
    # Step 2: Extract contacts (start small for testing)
    print(f"\n{Fore.CYAN}Starting with a small sample for testing...{Style.RESET_ALL}")
    contacts = extractor.scan_emails(days_back=7, max_emails=50)  # Small test first
    
    if contacts:
        # Step 3: Show summary
        print(extractor.get_contacts_summary())
        return contacts
    else:
        print(f"{Fore.YELLOW}⚠️ No contacts extracted{Style.RESET_ALL}")
        return None

if __name__ == "__main__":
    test_real_gmail_extraction()