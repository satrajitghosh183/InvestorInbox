"""
Yahoo Provider with Multiple Account Support
Uses IMAP with app-specific passwords for Yahoo Mail
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import imaplib
import email
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import re
import ssl

from providers.base_provider import BaseEmailProvider
from core.models import Contact, InteractionType, EmailProvider, ContactType
from core.exceptions import AuthenticationError, ProviderError

class YahooProvider(BaseEmailProvider):
    """
    Yahoo Mail provider using IMAP with app-specific passwords
    """
    
    def __init__(self, account_id: str, email: str, credential_file: str = ""):
        super().__init__(account_id, email, credential_file)
        
        # Yahoo IMAP configuration
        self.imap_server = "imap.mail.yahoo.com"
        self.imap_port = 993
        
        # Credentials from environment variables
        self.yahoo_email = os.getenv('YAHOO_EMAIL') or self.email
        self.app_password = os.getenv('YAHOO_APP_PASSWORD')
        
        if not self.app_password:
            raise ProviderError("YAHOO_APP_PASSWORD environment variable required")
        
        # IMAP connection
        self.imap_connection = None
        
        # Rate limiting (be conservative with IMAP)
        self.rate_limit_per_hour = 3600  # 1 request per second max
        self.request_delay_seconds = 1.0  # 1 second between IMAP operations
        
        self.logger.info(f"Initialized Yahoo provider for {self.email}")
    
    def _get_provider_type(self) -> str:
        return "yahoo"
    
    async def authenticate(self) -> bool:
        """Authenticate with Yahoo IMAP"""
        try:
            # Create SSL context
            ssl_context = ssl.create_default_context()
            
            # Connect to Yahoo IMAP
            self.imap_connection = imaplib.IMAP4_SSL(
                self.imap_server, 
                self.imap_port, 
                ssl_context=ssl_context
            )
            
            # Login with app password
            self.imap_connection.login(self.yahoo_email, self.app_password)
            
            # Verify connection by selecting INBOX
            status, messages = self.imap_connection.select("INBOX")
            
            if status != 'OK':
                raise AuthenticationError("Failed to select INBOX")
            
            self.is_authenticated = True
            self.last_auth_check = datetime.now()
            
            self.logger.info(f"Successfully authenticated Yahoo account: {self.email}")
            return True
        
        except Exception as e:
            self.logger.error(f"Yahoo authentication failed for {self.email}: {e}")
            self.last_error = str(e)
            self.is_authenticated = False
            
            # Cleanup failed connection
            if self.imap_connection:
                try:
                    self.imap_connection.close()
                    self.imap_connection.logout()
                except:
                    pass
                self.imap_connection = None
            
            return False
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get Yahoo account information"""
        try:
            if not self.is_authenticated:
                raise ProviderError("Not authenticated")
            
            # Get INBOX statistics
            status, messages = self.imap_connection.select("INBOX")
            
            if status != 'OK':
                raise ProviderError("Failed to select INBOX")
            
            total_messages = int(messages[0]) if messages and messages[0] else 0
            
            # Get recent messages count
            since_date = (datetime.now() - timedelta(days=30)).strftime("%d-%b-%Y")
            status, recent_messages = self.imap_connection.search(None, f'SINCE {since_date}')
            recent_count = len(recent_messages[0].split()) if recent_messages and recent_messages[0] else 0
            
            return {
                'email': self.yahoo_email,
                'total_messages': total_messages,
                'recent_messages_30_days': recent_count,
                'account_id': self.account_id,
                'provider_type': self.provider_type,
                'imap_server': self.imap_server
            }
        
        except Exception as e:
            self.logger.error(f"Failed to get account info: {e}")
            return {'error': str(e)}
    
    async def extract_contacts(self, days_back: int = 30, max_emails: int = 1000) -> List[Contact]:
        """Extract contacts from Yahoo Mail"""
        try:
            if not self.is_authenticated:
                if not await self.authenticate():
                    raise ProviderError("Authentication failed")
            
            self.logger.info(f"Extracting contacts from Yahoo account {self.email} (last {days_back} days, max {max_emails} emails)")
            
            # Select INBOX
            status, messages = self.imap_connection.select("INBOX")
            if status != 'OK':
                raise ProviderError("Failed to select INBOX")
            
            # Search for messages in date range
            since_date = (datetime.now() - timedelta(days=days_back)).strftime("%d-%b-%Y")
            status, message_ids = self.imap_connection.search(None, f'SINCE {since_date}')
            
            if status != 'OK' or not message_ids[0]:
                self.logger.info("No messages found in date range")
                return []
            
            # Get message IDs
            msg_ids = message_ids[0].split()
            msg_ids = msg_ids[-max_emails:] if len(msg_ids) > max_emails else msg_ids
            
            self.logger.info(f"Found {len(msg_ids)} messages, processing contacts...")
            
            # Process messages to extract contacts
            contacts = await self._process_messages(msg_ids)
            
            # Deduplicate contacts
            unique_contacts = self._deduplicate_contacts(contacts)
            
            # Update statistics
            await self.update_extraction_statistics(len(unique_contacts))
            
            self.logger.info(f"Extracted {len(unique_contacts)} unique contacts from {len(msg_ids)} messages")
            return unique_contacts
        
        except Exception as e:
            self.logger.error(f"Contact extraction failed: {e}")
            self.last_error = str(e)
            raise ProviderError(f"Yahoo contact extraction failed: {e}")
    
    async def _process_messages(self, message_ids: List[bytes]) -> List[Contact]:
        """Process Yahoo messages to extract contact information"""
        contacts = {}
        
        for i, msg_id in enumerate(message_ids):
            try:
                # Apply rate limiting
                await self._apply_rate_limit()
                
                # Fetch message
                status, msg_data = self.imap_connection.fetch(msg_id, '(RFC822)')
                
                if status != 'OK' or not msg_data or not msg_data[0]:
                    continue
                
                # Parse email message
                raw_email = msg_data[0][1]
                email_message = email.message_from_bytes(raw_email)
                
                # Extract contact information
                contact_data = self._extract_contact_from_message(email_message)
                
                if contact_data and contact_data['email']:
                    email_key = contact_data['email'].lower()
                    
                    if email_key in contacts:
                        # Merge with existing contact
                        existing_contact = contacts[email_key]
                        self._merge_contact_data(existing_contact, contact_data)
                    else:
                        # Create new contact
                        contact = self._create_contact_from_data(contact_data)
                        contacts[email_key] = contact
                
                # Progress logging
                if (i + 1) % 25 == 0:
                    self.logger.info(f"Processed {i + 1}/{len(message_ids)} messages")
            
            except Exception as e:
                self.logger.error(f"Failed to process message {msg_id}: {e}")
                continue
        
        return list(contacts.values())
    
    def _extract_contact_from_message(self, email_message) -> Optional[Dict[str, Any]]:
        """Extract contact information from a Yahoo email message"""
        try:
            # Get headers
            from_header = email_message.get('From', '')
            to_header = email_message.get('To', '')
            cc_header = email_message.get('Cc', '')
            date_header = email_message.get('Date', '')
            subject = email_message.get('Subject', '')
            message_id = email_message.get('Message-ID', '')
            
            # Parse date
            timestamp = self._parse_email_date(date_header)
            
            # Extract emails and names
            from_email = self._extract_email_from_sender(from_header)
            from_name = self._extract_name_from_sender(from_header)
            
            to_emails = self._parse_email_list(to_header)
            cc_emails = self._parse_email_list(cc_header)
            
            # Determine contact and interaction type
            contact_email = None
            contact_name = ""
            interaction_type = None
            direction = None
            is_cc = False
            
            if from_email and from_email.lower() != self.email.lower():
                # This is a received email
                contact_email = from_email
                contact_name = from_name
                interaction_type = InteractionType.RECEIVED
                direction = "inbound"
            else:
                # This is a sent email, find the primary recipient
                for email_addr in to_emails:
                    if email_addr.lower() != self.email.lower():
                        contact_email = email_addr
                        interaction_type = InteractionType.SENT
                        direction = "outbound"
                        break
                
                # Check CC if no TO recipient found
                if not contact_email:
                    for email_addr in cc_emails:
                        if email_addr.lower() != self.email.lower():
                            contact_email = email_addr
                            interaction_type = InteractionType.CC
                            direction = "outbound"
                            is_cc = True
                            break
            
            if not contact_email or self._should_skip_email(contact_email):
                return None
            
            # Get message body preview
            body_preview = self._extract_body_preview(email_message)
            
            return {
                'email': contact_email,
                'name': contact_name,
                'interaction_type': interaction_type,
                'direction': direction,
                'timestamp': timestamp,
                'subject': subject,
                'message_id': message_id,
                'content_preview': body_preview,
                'is_cc': is_cc,
                'is_bcc': False
            }
        
        except Exception as e:
            self.logger.error(f"Failed to extract contact from message: {e}")
            return None
    
    def _create_contact_from_data(self, contact_data: Dict[str, Any]) -> Contact:
        """Create a Contact object from extracted data"""
        contact = Contact(
            email=contact_data['email'],
            name=contact_data.get('name', ''),
            provider=EmailProvider.YAHOO
        )
        
        # Set contact type based on domain
        contact.contact_type = ContactType(self._determine_contact_type(contact.email))
        
        # Add source account
        contact.add_source_account(self.account_id)
        
        # Create interaction
        interaction = self._create_interaction(
            interaction_type=contact_data['interaction_type'],
            timestamp=contact_data['timestamp'],
            subject=contact_data.get('subject', ''),
            message_id=contact_data.get('message_id', ''),
            direction=contact_data.get('direction', ''),
            content_preview=contact_data.get('content_preview', '')
        )
        
        # Add interaction to contact
        contact.add_interaction(interaction)
        
        return contact
    
    def _merge_contact_data(self, contact: Contact, contact_data: Dict[str, Any]) -> None:
        """Merge new contact data into existing contact"""
        # Create new interaction
        interaction = self._create_interaction(
            interaction_type=contact_data['interaction_type'],
            timestamp=contact_data['timestamp'],
            subject=contact_data.get('subject', ''),
            message_id=contact_data.get('message_id', ''),
            direction=contact_data.get('direction', ''),
            content_preview=contact_data.get('content_preview', '')
        )
        
        # Add interaction
        contact.add_interaction(interaction)
        
        # Update name if we have a better one
        if not contact.name and contact_data.get('name'):
            contact.name = contact_data['name']
    
    def _parse_email_list(self, header_value: str) -> List[str]:
        """Parse comma-separated email list"""
        if not header_value:
            return []
        
        emails = []
        # Split by comma and extract emails
        for part in header_value.split(','):
            email = self._extract_email_from_sender(part.strip())
            if email:
                emails.append(email)
        
        return emails
    
    def _parse_email_date(self, date_str: str) -> datetime:
        """Parse email date string to datetime"""
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
        except:
            return datetime.now()
    
    def _extract_body_preview(self, email_message) -> str:
        """Extract a preview of the email body"""
        try:
            # Try to get plain text body
            if email_message.is_multipart():
                for part in email_message.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            text = payload.decode('utf-8', errors='ignore')
                            # Return first 200 characters
                            return text[:200].replace('\n', ' ').replace('\r', ' ').strip()
            else:
                if email_message.get_content_type() == "text/plain":
                    payload = email_message.get_payload(decode=True)
                    if payload:
                        text = payload.decode('utf-8', errors='ignore')
                        return text[:200].replace('\n', ' ').replace('\r', ' ').strip()
            
            return ""
        except Exception as e:
            self.logger.debug(f"Failed to extract body preview: {e}")
            return ""
    
    async def get_folders(self) -> List[str]:
        """Get Yahoo Mail folders"""
        try:
            if not self.is_authenticated:
                if not await self.authenticate():
                    return []
            
            # List folders
            status, folders = self.imap_connection.list()
            
            if status != 'OK':
                return []
            
            folder_names = []
            for folder in folders:
                # Parse folder name from IMAP response
                folder_str = folder.decode('utf-8')
                # Extract folder name (last part after quotes)
                match = re.search(r'"([^"]*)"$', folder_str)
                if match:
                    folder_names.append(match.group(1))
            
            return folder_names
        
        except Exception as e:
            self.logger.error(f"Failed to get folders: {e}")
            return []
    
    async def cleanup(self):
        """Cleanup Yahoo provider resources"""
        try:
            await super().cleanup()
            
            # Close IMAP connection
            if self.imap_connection:
                try:
                    self.imap_connection.close()
                    self.imap_connection.logout()
                except:
                    pass
                self.imap_connection = None
            
            self.logger.info(f"Cleaned up Yahoo provider for {self.email}")
        
        except Exception as e:
            self.logger.error(f"Yahoo cleanup failed: {e}")
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get IMAP connection status"""
        return {
            'is_connected': self.imap_connection is not None,
            'is_authenticated': self.is_authenticated,
            'imap_server': self.imap_server,
            'imap_port': self.imap_port,
            'requests_this_hour': self.requests_this_hour,
            'total_requests': self.total_requests,
            'last_request_time': self.last_request_time.isoformat() if self.last_request_time else None
        }