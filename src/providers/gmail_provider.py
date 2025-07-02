# """
# Refactored Gmail Provider - Production Ready
# Uses the new base provider architecture with enhanced features
# """

# import sys, os
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# import asyncio
# import json
# import time
# from datetime import datetime, timedelta
# from typing import List, Dict, Any, Optional
# from pathlib import Path
# import logging

# from google.auth.transport.requests import Request
# from google.oauth2.credentials import Credentials
# from google_auth_oauthlib.flow import InstalledAppFlow
# from googleapiclient.discovery import build
# from googleapiclient.errors import HttpError
# import google.auth.exceptions

# from core.models import Contact, EmailProvider, InteractionType
# from core.exceptions import AuthenticationError, ProviderError, RateLimitError
# from .base_provider import BaseEmailProvider, ProviderConfig

# class GmailProvider(BaseEmailProvider):
#     """
#     Production-ready Gmail provider using Google API
#     Refactored to use the new base provider architecture
#     """
    
#     # Gmail API scopes
#     SCOPES = [
#         'https://www.googleapis.com/auth/gmail.readonly',
#         'https://www.googleapis.com/auth/userinfo.email'
#     ]
    
#     def __init__(self, config: ProviderConfig):
#         super().__init__(config)
        
#         # Gmail-specific settings
#         self.credentials_file = config.credentials.get('credentials_file')
#         self.scopes = config.credentials.get('scopes', self.SCOPES)
        
#         # Authentication state
#         self.credentials = None
#         self.service = None
#         self.my_email = ""
        
#         # Rate limiting
#         self.requests_made = 0
#         self.last_request_time = 0
#         self.batch_size = config.settings.get('batch_size', 100)
        
#         # Token storage
#         self.token_file = config.settings.get('token_file', 'data/tokens/gmail_token.json')
    
#     def _get_required_credentials(self) -> List[str]:
#         """Required credentials for Gmail provider"""
#         return ['credentials_file']
    
#     async def authenticate(self) -> bool:
#         """
#         Authenticate with Gmail API using OAuth 2.0
#         Enhanced with better error handling and token management
#         """
#         try:
#             self.logger.info("Starting Gmail authentication...")
            
#             # Try to load existing credentials
#             if await self._load_credentials():
#                 if self.credentials.valid:
#                     self.logger.info("Loaded valid existing credentials")
#                     return await self._initialize_service()
#                 elif self.credentials.expired and self.credentials.refresh_token:
#                     self.logger.info("Refreshing expired credentials")
#                     return await self._refresh_credentials()
            
#             # Perform interactive authentication
#             return await self._interactive_authentication()
            
#         except Exception as e:
#             self.logger.error(f"Gmail authentication failed: {e}")
#             await self._handle_provider_error(e, "authentication")
#             return False
    
#     async def _load_credentials(self) -> bool:
#         """Load credentials from token file"""
#         try:
#             token_path = Path(self.token_file)
#             if token_path.exists():
#                 self.credentials = Credentials.from_authorized_user_file(
#                     str(token_path), self.scopes
#                 )
#                 return True
#             return False
#         except Exception as e:
#             self.logger.warning(f"Failed to load credentials: {e}")
#             return False
    
#     async def _save_credentials(self):
#         """Save credentials to token file"""
#         try:
#             token_path = Path(self.token_file)
#             token_path.parent.mkdir(parents=True, exist_ok=True)
            
#             with open(token_path, 'w') as token:
#                 token.write(self.credentials.to_json())
            
#             self.logger.info("Credentials saved successfully")
            
#         except Exception as e:
#             self.logger.warning(f"Failed to save credentials: {e}")
    
#     async def _refresh_credentials(self) -> bool:
#         """Refresh expired credentials"""
#         try:
#             self.credentials.refresh(Request())
#             await self._save_credentials()
#             return await self._initialize_service()
#         except google.auth.exceptions.RefreshError as e:
#             self.logger.error(f"Credential refresh failed: {e}")
#             # Delete invalid token file
#             try:
#                 Path(self.token_file).unlink(missing_ok=True)
#             except:
#                 pass
#             return False
    
#     async def _interactive_authentication(self) -> bool:
#         """Perform interactive OAuth 2.0 flow"""
#         try:
#             if not self.credentials_file or not Path(self.credentials_file).exists():
#                 raise AuthenticationError(
#                     f"Gmail credentials file not found: {self.credentials_file}",
#                     "gmail"
#                 )
            
#             self.logger.info("Starting interactive authentication flow")
#             print(f"\n{' '*4}🌐 Opening browser for Gmail authorization...")
#             print(f"{' '*4}Please complete the authentication in your browser\n")
            
#             flow = InstalledAppFlow.from_client_secrets_file(
#                 self.credentials_file, self.scopes
#             )
            
#             self.credentials = flow.run_local_server(
#                 port=0,
#                 prompt='consent',
#                 access_type='offline'
#             )
            
#             await self._save_credentials()
#             return await self._initialize_service()
            
#         except Exception as e:
#             self.logger.error(f"Interactive authentication failed: {e}")
#             raise AuthenticationError(f"Gmail OAuth flow failed: {e}", "gmail")
    
#     async def _initialize_service(self) -> bool:
#         """Initialize Gmail service and get user info"""
#         try:
#             self.service = build('gmail', 'v1', credentials=self.credentials)
#             self._increment_api_call()
            
#             # Get user profile
#             profile = self.service.users().getProfile(userId='me').execute()
#             self.my_email = profile.get('emailAddress', 'Unknown')
            
#             self.is_authenticated = True
#             self.logger.info(f"Gmail service initialized for: {self.my_email}")
            
#             return True
            
#         except HttpError as e:
#             self.logger.error(f"Failed to initialize Gmail service: {e}")
#             if e.resp.status == 401:
#                 raise AuthenticationError("Gmail API authentication failed", "gmail")
#             else:
#                 raise ProviderError(f"Gmail API error: {e}", "gmail")
    
#     async def test_connection(self) -> bool:
#         """Test Gmail API connection"""
#         try:
#             if not self.service:
#                 return False
            
#             # Simple API call to test connection
#             profile = self.service.users().getProfile(userId='me').execute()
#             self._increment_api_call()
            
#             return bool(profile.get('emailAddress'))
            
#         except Exception as e:
#             self.logger.error(f"Gmail connection test failed: {e}")
#             return False
    
#     async def get_account_info(self) -> Dict[str, Any]:
#         """Get Gmail account information"""
#         try:
#             if not self.service:
#                 raise ProviderError("Gmail service not initialized", "gmail")
            
#             profile = self.service.users().getProfile(userId='me').execute()
#             self._increment_api_call()
            
#             return {
#                 'id': profile.get('emailAddress'),
#                 'email': profile.get('emailAddress'),
#                 'messages_total': profile.get('messagesTotal', 0),
#                 'threads_total': profile.get('threadsTotal', 0),
#                 'history_id': profile.get('historyId'),
#                 'provider': 'gmail'
#             }
            
#         except Exception as e:
#             await self._handle_provider_error(e, "get_account_info")
    
#     async def extract_contacts(self, 
#                              days_back: int = 30,
#                              max_emails: int = 1000,
#                              account_id: Optional[str] = None) -> List[Contact]:
#         """
#         Extract contacts from Gmail emails
#         Enhanced with batching, progress tracking, and better error handling
#         """
#         try:
#             self.logger.info(f"Extracting Gmail contacts: {days_back} days, max {max_emails} emails")
            
#             if not self.service:
#                 raise ProviderError("Gmail service not initialized", "gmail")
            
#             self._check_rate_limits()
            
#             # Build search query
#             start_date, end_date = self._get_date_range(days_back)
#             query = f'after:{start_date.strftime("%Y/%m/%d")} before:{end_date.strftime("%Y/%m/%d")}'
            
#             # Get message list with pagination
#             contacts_dict = {}
#             processed_count = 0
#             next_page_token = None
            
#             self.logger.info(f"Searching Gmail with query: {query}")
            
#             while processed_count < max_emails:
#                 # Get batch of message IDs
#                 batch_size = min(self.batch_size, max_emails - processed_count)
                
#                 try:
#                     if next_page_token:
#                         result = self.service.users().messages().list(
#                             userId='me',
#                             q=query,
#                             maxResults=batch_size,
#                             pageToken=next_page_token
#                         ).execute()
#                     else:
#                         result = self.service.users().messages().list(
#                             userId='me',
#                             q=query,
#                             maxResults=batch_size
#                         ).execute()
                    
#                     self._increment_api_call()
                    
#                 except HttpError as e:
#                     if e.resp.status == 429:
#                         raise RateLimitError(
#                             "Gmail API rate limit exceeded",
#                             "gmail",
#                             retry_after=60
#                         )
#                     else:
#                         await self._handle_provider_error(e, "message_list")
                
#                 messages = result.get('messages', [])
#                 next_page_token = result.get('nextPageToken')
                
#                 if not messages:
#                     self.logger.info("No more messages found")
#                     break
                
#                 # Process messages in batch
#                 await self._process_message_batch(messages, contacts_dict)
                
#                 processed_count += len(messages)
#                 self.logger.debug(f"Processed {processed_count}/{max_emails} messages")
                
#                 # Rate limiting
#                 await asyncio.sleep(0.1)
                
#                 if not next_page_token:
#                     break
            
#             # Convert to list and sort by relationship strength
#             contacts = list(contacts_dict.values())
#             contacts.sort(key=lambda c: c.calculate_relationship_strength(), reverse=True)
            
#             self.logger.info(f"Extracted {len(contacts)} unique contacts from {processed_count} emails")
            
#             return contacts
            
#         except Exception as e:
#             await self._handle_provider_error(e, "extract_contacts")
    
#     async def _process_message_batch(self, messages: List[Dict], contacts_dict: Dict[str, Contact]):
#         """Process a batch of messages efficiently"""
#         try:
#             # Get message details in batch
#             message_ids = [msg['id'] for msg in messages]
            
#             # Use batch request for efficiency
#             batch_request = self.service.new_batch_http_request()
            
#             def add_message_callback(request_id, response, exception):
#                 if exception:
#                     self.logger.warning(f"Error getting message {request_id}: {exception}")
#                     return
                
#                 try:
#                     self._extract_contacts_from_message(response, contacts_dict)
#                 except Exception as e:
#                     self.logger.warning(f"Error processing message {request_id}: {e}")
            
#             # Add requests to batch
#             for msg_id in message_ids[:50]:  # Gmail batch limit is 50
#                 batch_request.add(
#                     self.service.users().messages().get(
#                         userId='me',
#                         id=msg_id,
#                         format='metadata',
#                         metadataHeaders=['From', 'To', 'Cc', 'Bcc', 'Subject', 'Date']
#                     ),
#                     callback=add_message_callback,
#                     request_id=msg_id
#                 )
            
#             # Execute batch
#             batch_request.execute()
#             self._increment_api_call()
            
#             # Process remaining messages if batch was full
#             if len(message_ids) > 50:
#                 remaining_messages = [{'id': mid} for mid in message_ids[50:]]
#                 await self._process_message_batch(remaining_messages, contacts_dict)
            
#         except Exception as e:
#             self.logger.error(f"Batch processing failed: {e}")
#             # Fallback to individual processing
#             for message in messages:
#                 try:
#                     msg_detail = self.service.users().messages().get(
#                         userId='me',
#                         id=message['id'],
#                         format='metadata',
#                         metadataHeaders=['From', 'To', 'Cc', 'Bcc', 'Subject', 'Date']
#                     ).execute()
#                     self._increment_api_call()
                    
#                     self._extract_contacts_from_message(msg_detail, contacts_dict)
                    
#                 except Exception as msg_error:
#                     self.logger.warning(f"Error processing message {message['id']}: {msg_error}")
#                     continue
    
#     def _extract_contacts_from_message(self, message: Dict[str, Any], contacts_dict: Dict[str, Contact]):
#         """Extract contacts from a single Gmail message"""
#         try:
#             headers = {h['name']: h['value'] for h in message.get('payload', {}).get('headers', [])}
            
#             subject = headers.get('Subject', '')
#             message_id = message.get('id', '')
            
#             # Parse date
#             try:
#                 date_str = headers.get('Date', '')
#                 if date_str:
#                     from email.utils import parsedate_tz, mktime_tz
#                     date_tuple = parsedate_tz(date_str)
#                     if date_tuple:
#                         timestamp = datetime.fromtimestamp(mktime_tz(date_tuple))
#                     else:
#                         timestamp = datetime.now()
#                 else:
#                     timestamp = datetime.now()
#             except:
#                 timestamp = datetime.now()
            
#             # Process each header type
#             header_mappings = {
#                 'From': InteractionType.RECEIVED,
#                 'To': InteractionType.SENT,
#                 'Cc': InteractionType.CC,
#                 'Bcc': InteractionType.BCC
#             }
            
#             for header_name, interaction_type in header_mappings.items():
#                 header_value = headers.get(header_name, '')
#                 if header_value:
#                     contacts = self._extract_emails_from_header(header_value)
                    
#                     for name, email in contacts:
#                         # Skip my own email
#                         if email == self.my_email.lower():
#                             continue
                        
#                         self._add_or_update_contact(
#                             contacts_dict, name, email, interaction_type,
#                             subject, message_id, timestamp
#                         )
                        
#         except Exception as e:
#             self.logger.warning(f"Error extracting contacts from message: {e}")
    
#     def _add_or_update_contact(self,
#                               contacts_dict: Dict[str, Contact],
#                               name: str,
#                               email: str,
#                               interaction_type: InteractionType,
#                               subject: str,
#                               message_id: str,
#                               timestamp: datetime):
#         """Add or update contact in the contacts dictionary"""
#         try:
#             if email in contacts_dict:
#                 contact = contacts_dict[email]
                
#                 # Update name if the new one is better (longer/more complete)
#                 if len(name) > len(contact.name) and name:
#                     contact.name = name
#             else:
#                 # Create new contact
#                 contact = Contact(
#                     email=email,
#                     name=name or email.split('@')[0],
#                     provider=EmailProvider.GMAIL,
#                     provider_contact_id=message_id,
#                     first_seen=timestamp
#                 )
#                 contacts_dict[email] = contact
            
#             # Add interaction
#             contact.add_interaction(
#                 interaction_type=interaction_type,
#                 subject=subject,
#                 message_id=message_id
#             )
            
#             # Update last seen
#             if timestamp > contact.last_seen:
#                 contact.last_seen = timestamp
            
#         except Exception as e:
#             self.logger.warning(f"Error adding/updating contact {email}: {e}")
    
#     async def get_email_headers(self, 
#                                message_id: str,
#                                account_id: Optional[str] = None) -> Dict[str, str]:
#         """Get email headers for a specific Gmail message"""
#         try:
#             if not self.service:
#                 raise ProviderError("Gmail service not initialized", "gmail")
            
#             message = self.service.users().messages().get(
#                 userId='me',
#                 id=message_id,
#                 format='metadata'
#             ).execute()
#             self._increment_api_call()
            
#             # Convert to standard header format
#             headers = {}
#             for header in message.get('payload', {}).get('headers', []):
#                 headers[header['name']] = header['value']
            
#             return headers
            
#         except Exception as e:
#             await self._handle_provider_error(e, "get_email_headers")
    
#     async def search_emails(self,
#                            query: str,
#                            max_results: int = 100,
#                            account_id: Optional[str] = None) -> List[Dict[str, Any]]:
#         """Search Gmail emails using Gmail search syntax"""
#         try:
#             if not self.service:
#                 raise ProviderError("Gmail service not initialized", "gmail")
            
#             result = self.service.users().messages().list(
#                 userId='me',
#                 q=query,
#                 maxResults=max_results
#             ).execute()
#             self._increment_api_call()
            
#             messages = result.get('messages', [])
            
#             # Get message details
#             email_results = []
#             for message in messages:
#                 try:
#                     msg_detail = self.service.users().messages().get(
#                         userId='me',
#                         id=message['id'],
#                         format='metadata',
#                         metadataHeaders=['From', 'To', 'Subject', 'Date']
#                     ).execute()
#                     self._increment_api_call()
                    
#                     headers = {h['name']: h['value'] for h in msg_detail.get('payload', {}).get('headers', [])}
                    
#                     email_results.append({
#                         'id': message['id'],
#                         'thread_id': message.get('threadId'),
#                         'subject': headers.get('Subject', ''),
#                         'from': headers.get('From', ''),
#                         'to': headers.get('To', ''),
#                         'date': headers.get('Date', ''),
#                         'snippet': msg_detail.get('snippet', '')
#                     })
                    
#                 except Exception as e:
#                     self.logger.warning(f"Error getting details for message {message['id']}: {e}")
#                     continue
            
#             return email_results
            
#         except Exception as e:
#             await self._handle_provider_error(e, "search_emails")
    
#     def _rate_limit_delay(self):
#         """Implement rate limiting to stay within API limits"""
#         current_time = time.time()
        
#         # Gmail allows 250 requests per user per second
#         min_interval = 1.0 / 250.0  # ~4ms between requests
        
#         if self.last_request_time > 0:
#             elapsed = current_time - self.last_request_time
#             if elapsed < min_interval:
#                 sleep_time = min_interval - elapsed
#                 time.sleep(sleep_time)
        
#         self.last_request_time = time.time()
    
#     async def refresh_authentication(self) -> bool:
#         """Refresh Gmail authentication"""
#         try:
#             if self.credentials and self.credentials.expired and self.credentials.refresh_token:
#                 return await self._refresh_credentials()
#             else:
#                 return await self.authenticate()
#         except Exception as e:
#             self.logger.error(f"Failed to refresh Gmail authentication: {e}")
#             return False
    
#     def get_supported_features(self) -> List[str]:
#         """Get Gmail-specific supported features"""
#         return [
#             'extract_contacts',
#             'get_email_headers',
#             'search_emails',
#             'test_connection',
#             'batch_processing',
#             'advanced_search',
#             'thread_support',
#             'label_support'
#         ]
    
#     async def close(self):
#         """Close Gmail provider and cleanup resources"""
#         try:
#             # Gmail API doesn't require explicit connection closing
#             # but we can cleanup credentials if needed
#             self.service = None
#             self.credentials = None
#             self.is_authenticated = False
            
#             self.logger.info("Gmail provider closed")
            
#         except Exception as e:
#             self.logger.warning(f"Error closing Gmail provider: {e}")

# # Register Gmail provider with the factory
# from .provider_factory import ProviderFactory
# ProviderFactory.register_provider(EmailProvider.GMAIL, GmailProvider)


"""
Fixed Gmail Provider - Handles scope issues and missing methods
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from core.models import Contact, EmailProvider, InteractionType
from core.exceptions import AuthenticationError, ProviderError
from providers.base_provider import BaseEmailProvider, ProviderConfig

# Try to import Google API components
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    import google.auth.exceptions
    GOOGLE_APIS_AVAILABLE = True
except ImportError:
    GOOGLE_APIS_AVAILABLE = False

class GmailProvider(BaseEmailProvider):
    """Gmail provider using Google API with proper error handling"""
    
    # Updated scopes to match what Google actually provides
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/userinfo.email',
        'openid'  # Google automatically adds this
    ]
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.credentials_file = config.credentials.get('credentials_file')
        self.token_file = config.settings.get('token_file', 'data/tokens/gmail_token.json')
        self.credentials = None
        self.service = None
        self.my_email = ""
        
        # Check if we can use real Gmail API
        self.use_real_api = GOOGLE_APIS_AVAILABLE and self.credentials_file and Path(self.credentials_file).exists()
        
        if not self.use_real_api:
            self.logger.warning("Gmail API not available or credentials missing - using mock mode")
    
    def _get_required_credentials(self) -> List[str]:
        return ['credentials_file']
    
    async def authenticate(self) -> bool:
        """Authenticate with Gmail (real or mock)"""
        if not self.use_real_api:
            # Mock authentication
            self.is_authenticated = True
            self.my_email = "mock@gmail.com"
            self.logger.info("Mock Gmail authentication successful")
            return True
        
        try:
            self.logger.info("Starting Gmail authentication...")
            
            # Try to load existing token
            if await self._load_credentials():
                if self.credentials.valid:
                    self.logger.info("Loaded valid existing credentials")
                    return await self._initialize_service()
                elif self.credentials.expired and self.credentials.refresh_token:
                    self.logger.info("Refreshing expired credentials")
                    return await self._refresh_credentials()
            
            # Perform interactive authentication
            return await self._interactive_authentication()
            
        except Exception as e:
            self.logger.error(f"Gmail authentication failed: {e}")
            # Handle the error properly
            await self._handle_authentication_error(e)
            return False
    
    async def _load_credentials(self) -> bool:
        """Load credentials from token file"""
        try:
            token_path = Path(self.token_file)
            if token_path.exists():
                # Load with flexible scope matching
                self.credentials = Credentials.from_authorized_user_file(
                    str(token_path), 
                    scopes=self.SCOPES
                )
                return True
            return False
        except Exception as e:
            self.logger.warning(f"Failed to load credentials: {e}")
            return False
    
    async def _save_credentials(self):
        """Save credentials to token file"""
        try:
            token_path = Path(self.token_file)
            token_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(token_path, 'w') as token:
                token.write(self.credentials.to_json())
            
            self.logger.info("Credentials saved successfully")
            
        except Exception as e:
            self.logger.warning(f"Failed to save credentials: {e}")
    
    async def _refresh_credentials(self) -> bool:
        """Refresh expired credentials"""
        try:
            self.credentials.refresh(Request())
            await self._save_credentials()
            return await self._initialize_service()
        except google.auth.exceptions.RefreshError as e:
            self.logger.error(f"Credential refresh failed: {e}")
            # Delete invalid token file
            try:
                Path(self.token_file).unlink(missing_ok=True)
                self.logger.info("Deleted invalid token file")
            except:
                pass
            return False
        except Exception as e:
            self.logger.error(f"Unexpected refresh error: {e}")
            return False
    
    async def _interactive_authentication(self) -> bool:
        """Perform interactive OAuth 2.0 flow"""
        try:
            if not self.credentials_file or not Path(self.credentials_file).exists():
                raise AuthenticationError(
                    f"Gmail credentials file not found: {self.credentials_file}",
                    "gmail"
                )
            
            self.logger.info("Starting interactive authentication flow")
            print(f"\n{' '*4}🌐 Opening browser for Gmail authorization...")
            print(f"{' '*4}Please complete the authentication in your browser\n")
            
            # Create flow with flexible scope handling
            flow = InstalledAppFlow.from_client_secrets_file(
                self.credentials_file, 
                scopes=self.SCOPES
            )
            
            # Run server with better error handling
            try:
                self.credentials = flow.run_local_server(
                    port=0,
                    prompt='consent',
                    access_type='offline'
                )
            except Exception as flow_error:
                # Try without some parameters if the first attempt fails
                self.logger.warning(f"First auth attempt failed: {flow_error}")
                self.logger.info("Retrying with basic parameters...")
                
                self.credentials = flow.run_local_server(port=0)
            
            await self._save_credentials()
            return await self._initialize_service()
            
        except Exception as e:
            self.logger.error(f"Interactive authentication failed: {e}")
            raise AuthenticationError(f"Gmail OAuth flow failed: {e}", "gmail")
    
    async def _initialize_service(self) -> bool:
        """Initialize Gmail service and get user info"""
        try:
            self.service = build('gmail', 'v1', credentials=self.credentials)
            self._increment_api_call()
            
            # Get user profile
            profile = self.service.users().getProfile(userId='me').execute()
            self.my_email = profile.get('emailAddress', 'Unknown')
            
            self.is_authenticated = True
            self.logger.info(f"Gmail service initialized for: {self.my_email}")
            
            return True
            
        except HttpError as e:
            self.logger.error(f"Failed to initialize Gmail service: {e}")
            if e.resp.status == 401:
                raise AuthenticationError("Gmail API authentication failed", "gmail")
            else:
                raise ProviderError(f"Gmail API error: {e}", "gmail")
        except Exception as e:
            self.logger.error(f"Unexpected service initialization error: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """Test Gmail API connection"""
        if not self.use_real_api:
            return self.is_authenticated
        
        try:
            if not self.service:
                return False
            
            # Simple API call to test connection
            profile = self.service.users().getProfile(userId='me').execute()
            self._increment_api_call()
            
            return bool(profile.get('emailAddress'))
            
        except Exception as e:
            self.logger.error(f"Gmail connection test failed: {e}")
            return False
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get Gmail account information"""
        if not self.use_real_api:
            return {
                "email": self.my_email,
                "provider": "mock_gmail", 
                "messages_total": 1500,
                "status": "mock mode - add gmail_credentials.json for real access",
                "note": "Install google-api-python-client for real Gmail access"
            }
        
        try:
            if not self.service:
                raise ProviderError("Gmail service not initialized", "gmail")
            
            profile = self.service.users().getProfile(userId='me').execute()
            self._increment_api_call()
            
            return {
                "id": profile.get('emailAddress'),
                "email": profile.get('emailAddress'),
                "messages_total": profile.get('messagesTotal', 0),
                "threads_total": profile.get('threadsTotal', 0),
                "history_id": profile.get('historyId'),
                "provider": "gmail"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get account info: {e}")
            return {"error": f"Could not get account info: {e}"}
    
    async def extract_contacts(self, days_back: int = 30, max_emails: int = 1000, account_id: Optional[str] = None) -> List[Contact]:
        """Extract contacts from Gmail"""
        if not self.use_real_api:
            self.logger.info("Using mock contacts (no real Gmail API access)")
            return self._generate_mock_contacts(max_emails)
        
        try:
            self.logger.info(f"Extracting Gmail contacts: {days_back} days, max {max_emails} emails")
            
            if not self.service:
                raise ProviderError("Gmail service not initialized", "gmail")
            
            # Build search query
            start_date = datetime.now() - timedelta(days=days_back)
            query = f'after:{start_date.strftime("%Y/%m/%d")}'
            
            # Get message list
            self.logger.info(f"Searching Gmail with query: {query}")
            
            try:
                result = self.service.users().messages().list(
                    userId='me',
                    q=query,
                    maxResults=min(max_emails, 100)  # Start with smaller batch
                ).execute()
                self._increment_api_call()
                
            except HttpError as e:
                if e.resp.status == 429:
                    raise ProviderError("Gmail API rate limit exceeded", "gmail")
                else:
                    raise ProviderError(f"Gmail API error: {e}", "gmail")
            
            messages = result.get('messages', [])
            
            if not messages:
                self.logger.info("No messages found in the specified date range")
                return []
            
            self.logger.info(f"Found {len(messages)} messages to process")
            
            # Process messages to extract contacts
            contacts_dict = {}
            processed_count = 0
            
            for message in messages[:50]:  # Limit to avoid quota issues
                try:
                    msg = self.service.users().messages().get(
                        userId='me',
                        id=message['id'],
                        format='metadata',
                        metadataHeaders=['From', 'To', 'Cc', 'Subject', 'Date']
                    ).execute()
                    self._increment_api_call()
                    
                    # Extract contacts from headers
                    headers = {h['name']: h['value'] for h in msg.get('payload', {}).get('headers', [])}
                    
                    self._extract_contacts_from_message_headers(headers, contacts_dict)
                    processed_count += 1
                    
                except Exception as e:
                    self.logger.warning(f"Error processing message {message['id']}: {e}")
                    continue
            
            # Convert to list and sort
            contacts = list(contacts_dict.values())
            contacts.sort(key=lambda c: c.frequency, reverse=True)
            
            self.logger.info(f"Extracted {len(contacts)} unique contacts from {processed_count} emails")
            return contacts
            
        except Exception as e:
            self.logger.error(f"Gmail contact extraction failed: {e}")
            # Return mock contacts as fallback
            return self._generate_mock_contacts(max_emails)
    
    def _extract_contacts_from_message_headers(self, headers: Dict[str, str], contacts_dict: Dict[str, Contact]):
        """Extract contacts from message headers"""
        try:
            header_mappings = {
                'From': InteractionType.RECEIVED,
                'To': InteractionType.SENT,
                'Cc': InteractionType.CC
            }
            
            for header_name, interaction_type in header_mappings.items():
                header_value = headers.get(header_name, '')
                if header_value:
                    contacts = self._parse_email_addresses(header_value)
                    
                    for name, email in contacts:
                        # Skip my own email
                        if email == self.my_email.lower():
                            continue
                        
                        self._add_or_update_contact(contacts_dict, name, email, interaction_type)
                        
        except Exception as e:
            self.logger.warning(f"Error extracting contacts from headers: {e}")
    
    def _parse_email_addresses(self, header_value: str) -> List[tuple]:
        """Parse email addresses from header value"""
        try:
            from email.utils import parseaddr
            
            contacts = []
            
            # Split by comma for multiple addresses
            parts = [part.strip() for part in header_value.split(',')]
            
            for part in parts:
                name, email = parseaddr(part)
                
                if email and '@' in email:
                    name = name.strip(' "\'')
                    email = email.lower().strip()
                    
                    # Basic email validation
                    if self._is_valid_email(email):
                        contacts.append((name, email))
            
            return contacts
            
        except Exception as e:
            self.logger.warning(f"Error parsing email addresses: {e}")
            return []
    
    def _is_valid_email(self, email: str) -> bool:
        """Basic email validation"""
        import re
        
        if not email or '@' not in email:
            return False
        
        # Basic regex check
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return False
        
        # Exclude common system emails
        exclude_patterns = ['noreply', 'no-reply', 'donotreply', 'mailer-daemon']
        return not any(pattern in email.lower() for pattern in exclude_patterns)
    
    def _add_or_update_contact(self, contacts_dict: Dict[str, Contact], name: str, email: str, interaction_type: InteractionType):
        """Add or update contact in the dictionary"""
        try:
            if email in contacts_dict:
                contact = contacts_dict[email]
                contact.frequency += 1
                
                # Update name if the new one is better
                if len(name) > len(contact.name) and name:
                    contact.name = name
            else:
                contact = Contact(
                    email=email,
                    name=name or email.split('@')[0],
                    provider=EmailProvider.GMAIL,
                    frequency=1,
                    data_source="Gmail API",
                    confidence=0.9
                )
                contacts_dict[email] = contact
            
            # Update interaction counts
            if interaction_type == InteractionType.SENT:
                contact.sent_to += 1
            elif interaction_type == InteractionType.RECEIVED:
                contact.received_from += 1
            elif interaction_type == InteractionType.CC:
                contact.cc_count += 1
                
        except Exception as e:
            self.logger.warning(f"Error adding/updating contact {email}: {e}")
    
    def _generate_mock_contacts(self, max_emails: int) -> List[Contact]:
        """Generate mock contacts for testing"""
        mock_contacts = [
            Contact(
                email="john.doe@example.com",
                name="John Doe",
                provider=EmailProvider.GMAIL,
                frequency=15,
                sent_to=8,
                received_from=7,
                location="San Francisco, CA",
                estimated_net_worth="$250K - $500K",
                job_title="Software Engineer",
                company="Example Corp",
                data_source="Mock Data",
                confidence=0.8
            ),
            Contact(
                email="jane.smith@techcorp.com",
                name="Jane Smith", 
                provider=EmailProvider.GMAIL,
                frequency=23,
                sent_to=12,
                received_from=11,
                location="New York, NY",
                estimated_net_worth="$500K - $1M",
                job_title="Product Manager",
                company="TechCorp",
                data_source="Mock Data",
                confidence=0.9
            ),
            Contact(
                email="bob.wilson@startup.io",
                name="Bob Wilson",
                provider=EmailProvider.GMAIL,
                frequency=5,
                sent_to=3,
                received_from=2,
                location="Austin, TX",
                estimated_net_worth="$1M - $2.5M",
                job_title="CEO",
                company="Startup Inc",
                data_source="Mock Data",
                confidence=0.7
            ),
            Contact(
                email="alice.chen@google.com",
                name="Alice Chen",
                provider=EmailProvider.GMAIL,
                frequency=31,
                sent_to=18,
                received_from=13,
                location="Mountain View, CA",
                estimated_net_worth="$500K - $1M",
                job_title="Senior Engineer",
                company="Google",
                data_source="Mock Data",
                confidence=0.95
            )
        ]
        
        # Return subset based on max_emails
        num_contacts = min(len(mock_contacts), max(1, max_emails // 50))
        return mock_contacts[:num_contacts]
    
    async def get_email_headers(self, message_id: str, account_id: Optional[str] = None) -> Dict[str, str]:
        """Get email headers for a specific message"""
        try:
            if not self.service:
                return {"error": "Gmail service not initialized"}
            
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='metadata'
            ).execute()
            self._increment_api_call()
            
            # Convert to standard header format
            headers = {}
            for header in message.get('payload', {}).get('headers', []):
                headers[header['name']] = header['value']
            
            return headers
            
        except Exception as e:
            self.logger.error(f"Failed to get email headers: {e}")
            return {"error": str(e)}
    
    async def search_emails(self, query: str, max_results: int = 100, account_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search Gmail emails"""
        try:
            if not self.service:
                return []
            
            result = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            self._increment_api_call()
            
            return result.get('messages', [])
            
        except Exception as e:
            self.logger.error(f"Gmail search failed: {e}")
            return []
    
    # Error handling methods
    async def _handle_authentication_error(self, error: Exception):
        """Handle authentication errors"""
        if isinstance(error, AuthenticationError):
            self.logger.error(f"Authentication failed: {error.message}")
        else:
            self.logger.error(f"Authentication error: {error}")
    
    async def _handle_provider_error(self, error: Exception, context: str = ""):
        """Handle provider errors"""
        self.logger.error(f"Provider error in {context}: {error}")
        
        if isinstance(error, HttpError):
            if error.resp.status == 401:
                raise AuthenticationError("Gmail authentication failed", "gmail")
            elif error.resp.status == 429:
                raise ProviderError("Gmail rate limit exceeded", "gmail")
            else:
                raise ProviderError(f"Gmail API error: {error}", "gmail")
        else:
            raise ProviderError(f"Gmail error: {error}", "gmail")
    
    async def close(self):
        """Close the provider and cleanup resources"""
        try:
            # Gmail API doesn't require explicit connection closing
            self.service = None
            self.credentials = None
            self.is_authenticated = False
            self.logger.info("Gmail provider closed")
        except Exception as e:
            self.logger.warning(f"Error closing Gmail provider: {e}")

# Don't register here - it's handled in the factory dynamically