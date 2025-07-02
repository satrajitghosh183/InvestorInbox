"""
IMAP/POP3 Email Provider
Universal provider for Yahoo, AOL, iCloud, and other email providers
Production-ready with SSL/TLS support and comprehensive error handling
"""

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
import email
import imaplib
import poplib
import ssl
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from email.header import decode_header
from email.utils import parsedate_tz, mktime_tz
import socket
import re

from core.models import Contact, EmailProvider, InteractionType
from core.exceptions import AuthenticationError, ProviderError, ValidationError
from .base_provider import BaseEmailProvider, ProviderConfig

class IMAPProvider(BaseEmailProvider):
    """
    Universal IMAP/POP3 provider for various email services
    Supports Yahoo, AOL, iCloud, and custom IMAP servers
    """
    
    # Pre-configured settings for popular providers
    PROVIDER_SETTINGS = {
        'yahoo': {
            'imap_server': 'imap.mail.yahoo.com',
            'imap_port': 993,
            'pop_server': 'pop.mail.yahoo.com',
            'pop_port': 995,
            'use_ssl': True,
            'provider_type': EmailProvider.YAHOO
        },
        'aol': {
            'imap_server': 'imap.aol.com',
            'imap_port': 993,
            'pop_server': 'pop.aol.com',
            'pop_port': 995,
            'use_ssl': True,
            'provider_type': EmailProvider.OTHER
        },
        'icloud': {
            'imap_server': 'imap.mail.me.com',
            'imap_port': 993,
            'pop_server': None,  # iCloud doesn't support POP3
            'pop_port': None,
            'use_ssl': True,
            'provider_type': EmailProvider.ICLOUD
        },
        'custom': {
            'imap_server': None,  # Must be provided in config
            'imap_port': 993,
            'pop_server': None,
            'pop_port': 995,
            'use_ssl': True,
            'provider_type': EmailProvider.IMAP
        }
    }
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        
        # Connection settings
        self.email_address = config.credentials.get('email')
        self.password = config.credentials.get('password')
        self.app_password = config.credentials.get('app_password')  # For providers requiring app passwords
        
        # Provider-specific settings
        self.provider_name = config.settings.get('provider', 'custom').lower()
        self.protocol = config.settings.get('protocol', 'imap').lower()  # 'imap' or 'pop3'
        
        # Get provider settings
        if self.provider_name in self.PROVIDER_SETTINGS:
            self.provider_settings = self.PROVIDER_SETTINGS[self.provider_name].copy()
            # Override provider_type if specified
            if hasattr(config, 'provider_type'):
                self.provider_type = config.provider_type
            else:
                self.provider_type = self.provider_settings['provider_type']
        else:
            self.provider_settings = self.PROVIDER_SETTINGS['custom'].copy()
            self.provider_type = EmailProvider.IMAP
        
        # Override with custom settings if provided
        for key in ['imap_server', 'imap_port', 'pop_server', 'pop_port', 'use_ssl']:
            if key in config.settings:
                self.provider_settings[key] = config.settings[key]
        
        # Connection objects
        self.imap_connection = None
        self.pop_connection = None
        
        # Validation
        self._validate_settings()
    
    def _validate_settings(self):
        """Validate provider settings"""
        if not self.email_address:
            raise ValidationError("Email address is required", "email")
        
        if not (self.password or self.app_password):
            raise ValidationError("Password or app password is required", "password")
        
        if self.protocol == 'imap' and not self.provider_settings.get('imap_server'):
            raise ValidationError("IMAP server is required for IMAP protocol", "imap_server")
        
        if self.protocol == 'pop3' and not self.provider_settings.get('pop_server'):
            raise ValidationError("POP3 server is required for POP3 protocol", "pop_server")
    
    def _get_required_credentials(self) -> List[str]:
        """Required credentials for IMAP provider"""
        return ['email', 'password']
    
    async def authenticate(self) -> bool:
        """Authenticate with IMAP/POP3 server"""
        try:
            self.logger.info(f"Authenticating with {self.provider_name} using {self.protocol.upper()}")
            
            if self.protocol == 'imap':
                return await self._authenticate_imap()
            elif self.protocol == 'pop3':
                return await self._authenticate_pop3()
            else:
                raise ValidationError(f"Unsupported protocol: {self.protocol}", "protocol")
                
        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            await self._handle_provider_error(e, "authentication")
            return False
    
    async def _authenticate_imap(self) -> bool:
        """Authenticate with IMAP server"""
        try:
            server = self.provider_settings['imap_server']
            port = self.provider_settings['imap_port']
            use_ssl = self.provider_settings['use_ssl']
            
            # Create SSL context
            if use_ssl:
                ssl_context = ssl.create_default_context()
                # For some providers, we might need to be less strict
                if self.provider_name in ['yahoo', 'aol']:
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE
            
            # Connect to server
            if use_ssl:
                self.imap_connection = imaplib.IMAP4_SSL(server, port, ssl_context=ssl_context)
            else:
                self.imap_connection = imaplib.IMAP4(server, port)
            
            # Login
            password = self.app_password or self.password
            result = self.imap_connection.login(self.email_address, password)
            
            if result[0] == 'OK':
                self.is_authenticated = True
                self.logger.info("IMAP authentication successful")
                return True
            else:
                raise AuthenticationError(f"IMAP login failed: {result[1]}", self.provider_name)
                
        except imaplib.IMAP4.error as e:
            if "authentication failed" in str(e).lower():
                raise AuthenticationError(f"IMAP authentication failed: {e}", self.provider_name)
            else:
                raise ProviderError(f"IMAP error: {e}", self.provider_name)
        except socket.error as e:
            raise ProviderError(f"IMAP connection error: {e}", self.provider_name)
    
    async def _authenticate_pop3(self) -> bool:
        """Authenticate with POP3 server"""
        try:
            server = self.provider_settings['pop_server']
            port = self.provider_settings['pop_port']
            use_ssl = self.provider_settings['use_ssl']
            
            # Connect to server
            if use_ssl:
                self.pop_connection = poplib.POP3_SSL(server, port)
            else:
                self.pop_connection = poplib.POP3(server, port)
            
            # Login
            password = self.app_password or self.password
            self.pop_connection.user(self.email_address)
            result = self.pop_connection.pass_(password)
            
            if b'+OK' in result:
                self.is_authenticated = True
                self.logger.info("POP3 authentication successful")
                return True
            else:
                raise AuthenticationError(f"POP3 login failed: {result}", self.provider_name)
                
        except poplib.error_proto as e:
            if "authentication failed" in str(e).lower():
                raise AuthenticationError(f"POP3 authentication failed: {e}", self.provider_name)
            else:
                raise ProviderError(f"POP3 error: {e}", self.provider_name)
        except socket.error as e:
            raise ProviderError(f"POP3 connection error: {e}", self.provider_name)
    
    async def test_connection(self) -> bool:
        """Test connection to email server"""
        try:
            if not self.is_authenticated:
                return False
            
            if self.protocol == 'imap' and self.imap_connection:
                # Test IMAP connection
                result = self.imap_connection.noop()
                return result[0] == 'OK'
            elif self.protocol == 'pop3' and self.pop_connection:
                # Test POP3 connection
                result = self.pop_connection.noop()
                return b'+OK' in result
            
            return False
            
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        return {
            'email': self.email_address,
            'provider': self.provider_name,
            'protocol': self.protocol,
            'server': self.provider_settings.get(f'{self.protocol}_server'),
            'port': self.provider_settings.get(f'{self.protocol}_port'),
            'ssl_enabled': self.provider_settings.get('use_ssl', True)
        }
    
    async def extract_contacts(self, 
                             days_back: int = 30,
                             max_emails: int = 1000,
                             account_id: Optional[str] = None) -> List[Contact]:
        """Extract contacts from emails"""
        try:
            self.logger.info(f"Extracting contacts from last {days_back} days, max {max_emails} emails")
            
            if not self.is_authenticated:
                raise AuthenticationError("Not authenticated", self.provider_name)
            
            contacts_dict = {}
            
            if self.protocol == 'imap':
                contacts_dict = await self._extract_contacts_imap(days_back, max_emails)
            elif self.protocol == 'pop3':
                contacts_dict = await self._extract_contacts_pop3(days_back, max_emails)
            
            contacts = list(contacts_dict.values())
            self.logger.info(f"Extracted {len(contacts)} unique contacts")
            
            return contacts
            
        except Exception as e:
            await self._handle_provider_error(e, "extract_contacts")
    
    async def _extract_contacts_imap(self, days_back: int, max_emails: int) -> Dict[str, Contact]:
        """Extract contacts using IMAP"""
        contacts_dict = {}
        
        try:
            # Select INBOX
            self.imap_connection.select('INBOX')
            
            # Build search criteria
            start_date, _ = self._get_date_range(days_back)
            date_str = start_date.strftime('%d-%b-%Y')
            
            # Search for emails since the start date
            search_criteria = f'(SINCE "{date_str}")'
            result, message_ids = self.imap_connection.search(None, search_criteria)
            
            if result != 'OK':
                raise ProviderError(f"IMAP search failed: {message_ids}", self.provider_name)
            
            # Get message IDs
            msg_ids = message_ids[0].split()
            total_messages = len(msg_ids)
            
            if total_messages == 0:
                self.logger.info("No messages found in date range")
                return contacts_dict
            
            # Limit number of messages
            if total_messages > max_emails:
                msg_ids = msg_ids[-max_emails:]  # Get most recent messages
            
            self.logger.info(f"Processing {len(msg_ids)} messages")
            
            # Process messages
            for i, msg_id in enumerate(msg_ids):
                try:
                    # Fetch message headers
                    result, msg_data = self.imap_connection.fetch(msg_id, '(RFC822.HEADER)')
                    
                    if result == 'OK' and msg_data[0]:
                        # Parse email
                        raw_email = msg_data[0][1]
                        if isinstance(raw_email, bytes):
                            raw_email = raw_email.decode('utf-8', errors='ignore')
                        
                        msg = email.message_from_string(raw_email)
                        self._process_imap_message(msg, contacts_dict)
                    
                    # Rate limiting
                    if i % 50 == 0:
                        await asyncio.sleep(0.1)
                        
                except Exception as e:
                    self.logger.warning(f"Error processing message {msg_id}: {e}")
                    continue
            
            return contacts_dict
            
        except Exception as e:
            raise ProviderError(f"IMAP contact extraction failed: {e}", self.provider_name)
    
    async def _extract_contacts_pop3(self, days_back: int, max_emails: int) -> Dict[str, Contact]:
        """Extract contacts using POP3"""
        contacts_dict = {}
        
        try:
            # Get message count
            num_messages = len(self.pop_connection.list()[1])
            
            if num_messages == 0:
                self.logger.info("No messages found")
                return contacts_dict
            
            # Limit number of messages (POP3 downloads from newest)
            messages_to_process = min(num_messages, max_emails)
            start_msg = max(1, num_messages - messages_to_process + 1)
            
            self.logger.info(f"Processing {messages_to_process} messages")
            
            # Process messages
            for msg_num in range(start_msg, num_messages + 1):
                try:
                    # Get message headers
                    result = self.pop_connection.top(msg_num, 0)  # Get headers only
                    
                    if result:
                        # Parse email headers
                        headers = b'\n'.join(result[1]).decode('utf-8', errors='ignore')
                        msg = email.message_from_string(headers)
                        
                        # Check date filter
                        if self._is_message_in_date_range(msg, days_back):
                            self._process_pop3_message(msg, contacts_dict)
                    
                    # Rate limiting
                    if msg_num % 50 == 0:
                        await asyncio.sleep(0.1)
                        
                except Exception as e:
                    self.logger.warning(f"Error processing message {msg_num}: {e}")
                    continue
            
            return contacts_dict
            
        except Exception as e:
            raise ProviderError(f"POP3 contact extraction failed: {e}", self.provider_name)
    
    def _process_imap_message(self, msg: email.message.Message, contacts_dict: Dict[str, Contact]):
        """Process IMAP message and extract contacts"""
        try:
            # Get message metadata
            subject = self._decode_header(msg.get('Subject', ''))
            message_date = self._parse_date(msg.get('Date', ''))
            message_id = msg.get('Message-ID', '')
            
            # Process email addresses
            for header_name in ['From', 'To', 'Cc', 'Bcc']:
                header_value = msg.get(header_name, '')
                if header_value:
                    decoded_header = self._decode_header(header_value)
                    contacts = self._extract_emails_from_header(decoded_header)
                    
                    for name, email in contacts:
                        if email != self.email_address.lower():
                            interaction_type = self._get_interaction_type(header_name)
                            self._add_or_update_contact(
                                contacts_dict, name, email, interaction_type,
                                subject, message_id, message_date
                            )
                            
        except Exception as e:
            self.logger.warning(f"Error processing IMAP message: {e}")
    
    def _process_pop3_message(self, msg: email.message.Message, contacts_dict: Dict[str, Contact]):
        """Process POP3 message and extract contacts"""
        # Same logic as IMAP since we're working with email.message.Message objects
        self._process_imap_message(msg, contacts_dict)
    
    def _add_or_update_contact(self,
                              contacts_dict: Dict[str, Contact],
                              name: str,
                              email: str,
                              interaction_type: InteractionType,
                              subject: str,
                              message_id: str,
                              message_date: datetime):
        """Add or update contact in the dictionary"""
        try:
            if email in contacts_dict:
                contact = contacts_dict[email]
                
                # Update name if the new one is better
                if len(name) > len(contact.name) and name:
                    contact.name = name
            else:
                contact = Contact(
                    email=email,
                    name=name or email.split('@')[0],
                    provider=self.provider_type,
                    first_seen=message_date
                )
                contacts_dict[email] = contact
            
            # Add interaction
            contact.add_interaction(
                interaction_type=interaction_type,
                subject=subject,
                message_id=message_id
            )
            
        except Exception as e:
            self.logger.warning(f"Error adding/updating contact {email}: {e}")
    
    def _get_interaction_type(self, header_name: str) -> InteractionType:
        """Convert email header to interaction type"""
        header_map = {
            'From': InteractionType.RECEIVED,
            'To': InteractionType.SENT,
            'Cc': InteractionType.CC,
            'Bcc': InteractionType.BCC
        }
        return header_map.get(header_name, InteractionType.RECEIVED)
    
    def _decode_header(self, header_value: str) -> str:
        """Decode email header that might be encoded"""
        if not header_value:
            return ''
        
        try:
            decoded_parts = decode_header(header_value)
            decoded_string = ''
            
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    if encoding:
                        decoded_string += part.decode(encoding, errors='ignore')
                    else:
                        decoded_string += part.decode('utf-8', errors='ignore')
                else:
                    decoded_string += str(part)
            
            return decoded_string.strip()
            
        except Exception:
            # Fallback to original string if decoding fails
            return str(header_value)
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse email date string to datetime object"""
        try:
            if not date_str:
                return datetime.now()
            
            # Parse date string
            time_tuple = parsedate_tz(date_str)
            if time_tuple:
                timestamp = mktime_tz(time_tuple)
                return datetime.fromtimestamp(timestamp)
            else:
                return datetime.now()
                
        except Exception:
            return datetime.now()
    
    def _is_message_in_date_range(self, msg: email.message.Message, days_back: int) -> bool:
        """Check if message is within the specified date range"""
        try:
            msg_date = self._parse_date(msg.get('Date', ''))
            cutoff_date = datetime.now() - timedelta(days=days_back)
            return msg_date >= cutoff_date
        except Exception:
            return True  # Include message if we can't determine date
    
    async def get_email_headers(self, 
                               message_id: str,
                               account_id: Optional[str] = None) -> Dict[str, str]:
        """Get email headers for a specific message"""
        try:
            if self.protocol == 'imap':
                return await self._get_imap_headers(message_id)
            elif self.protocol == 'pop3':
                return await self._get_pop3_headers(message_id)
            else:
                raise ProviderError(f"Unsupported protocol: {self.protocol}", self.provider_name)
                
        except Exception as e:
            await self._handle_provider_error(e, "get_email_headers")
    
    async def _get_imap_headers(self, message_id: str) -> Dict[str, str]:
        """Get headers using IMAP"""
        try:
            self.imap_connection.select('INBOX')
            
            # Search for message by Message-ID
            result, msg_ids = self.imap_connection.search(None, f'HEADER Message-ID "{message_id}"')
            
            if result == 'OK' and msg_ids[0]:
                msg_id = msg_ids[0].split()[0]
                result, msg_data = self.imap_connection.fetch(msg_id, '(RFC822.HEADER)')
                
                if result == 'OK' and msg_data[0]:
                    raw_email = msg_data[0][1].decode('utf-8', errors='ignore')
                    msg = email.message_from_string(raw_email)
                    
                    # Convert to dictionary
                    headers = {}
                    for key, value in msg.items():
                        headers[key] = self._decode_header(value)
                    
                    return headers
            
            return {}
            
        except Exception as e:
            raise ProviderError(f"Failed to get IMAP headers: {e}", self.provider_name)
    
    async def _get_pop3_headers(self, message_id: str) -> Dict[str, str]:
        """Get headers using POP3 (limited functionality)"""
        # POP3 doesn't support searching by Message-ID easily
        # This is a simplified implementation
        raise ProviderError("POP3 header lookup by Message-ID not supported", self.provider_name)
    
    async def search_emails(self,
                           query: str,
                           max_results: int = 100,
                           account_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search emails (IMAP only)"""
        try:
            if self.protocol == 'imap':
                return await self._search_imap(query, max_results)
            else:
                raise ProviderError("Email search not supported for POP3", self.provider_name)
                
        except Exception as e:
            await self._handle_provider_error(e, "search_emails")
    
    async def _search_imap(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Search emails using IMAP"""
        try:
            self.imap_connection.select('INBOX')
            
            # Convert simple query to IMAP search format
            search_criteria = f'TEXT "{query}"'
            result, msg_ids = self.imap_connection.search(None, search_criteria)
            
            if result != 'OK':
                return []
            
            msg_ids = msg_ids[0].split()
            if len(msg_ids) > max_results:
                msg_ids = msg_ids[-max_results:]  # Get most recent
            
            results = []
            for msg_id in msg_ids:
                try:
                    result, msg_data = self.imap_connection.fetch(msg_id, '(RFC822.HEADER)')
                    if result == 'OK' and msg_data[0]:
                        raw_email = msg_data[0][1].decode('utf-8', errors='ignore')
                        msg = email.message_from_string(raw_email)
                        
                        results.append({
                            'id': msg.get('Message-ID', ''),
                            'subject': self._decode_header(msg.get('Subject', '')),
                            'from': self._decode_header(msg.get('From', '')),
                            'date': msg.get('Date', ''),
                            'message_number': msg_id.decode()
                        })
                        
                except Exception as e:
                    self.logger.warning(f"Error processing search result {msg_id}: {e}")
                    continue
            
            return results
            
        except Exception as e:
            raise ProviderError(f"IMAP search failed: {e}", self.provider_name)
    
    async def close(self):
        """Close connections"""
        try:
            if self.imap_connection:
                self.imap_connection.logout()
                self.imap_connection = None
                
            if self.pop_connection:
                self.pop_connection.quit()
                self.pop_connection = None
                
        except Exception as e:
            self.logger.warning(f"Error closing connections: {e}")
    
    def __del__(self):
        """Cleanup connections when object is destroyed"""
        try:
            if self.imap_connection:
                self.imap_connection.logout()
            if self.pop_connection:
                self.pop_connection.quit()
        except:
            pass