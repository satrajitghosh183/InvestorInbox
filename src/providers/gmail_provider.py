

"""
Enhanced Gmail Provider with Multiple Account Support - COMPLETELY FIXED VERSION
Fixes: OAuth scopes AND datetime timezone issues
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pickle
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from pathlib import Path
import base64
import email
from email.mime.text import MIMEText
import re

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_APIS_AVAILABLE = True
except ImportError:
    GOOGLE_APIS_AVAILABLE = False

from providers.base_provider import BaseEmailProvider
from core.models import Contact, InteractionType, EmailProvider, ContactType
from core.exceptions import AuthenticationError, ProviderError

class GmailProvider(BaseEmailProvider):
    """
    Enhanced Gmail provider with account-specific credential management
    FIXED: OAuth scopes AND datetime timezone handling
    """
    
    def __init__(self, account_id: str, email: str, credential_file: str):
        super().__init__(account_id, email, credential_file)
        
        if not GOOGLE_APIS_AVAILABLE:
            raise ProviderError("Google API libraries not available. Install with: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
        
        # FIXED: Gmail-specific configuration with correct scopes including 'openid'
        self.scopes = [
            'openid',  # CRITICAL: Required for OpenID Connect - prevents scope mismatch
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/userinfo.email'
        ]
        
        # API service
        self.service = None
        self.user_profile = None
        
        # Token file for this specific account
        self.token_file = self._get_token_file_path()
        
        # Rate limiting (Gmail API limits)
        self.rate_limit_per_hour = 1000  # Gmail API quota
        self.requests_per_second = 5     # Gmail API burst limit
        
        self.logger.info(f"Initialized Gmail provider for {self.email}")
    
    def _get_provider_type(self) -> str:
        return "gmail"
    
    def _get_token_file_path(self) -> Path:
        """Get account-specific token file path"""
        # Store tokens in data/tokens directory with account-specific names
        tokens_dir = Path("data/tokens")
        tokens_dir.mkdir(parents=True, exist_ok=True)
        
        # Create safe filename from email
        safe_email = self.email.replace('@', '_').replace('.', '_')
        return tokens_dir / f"gmail_{safe_email}_token.json"
    
    async def authenticate(self) -> bool:
        """Authenticate with Gmail using account-specific credentials - FIXED VERSION"""
        try:
            creds = None
            
            # Load existing token if available
            if self.token_file.exists():
                try:
                    # FIXED: Load credentials with updated scopes
                    creds = Credentials.from_authorized_user_file(str(self.token_file), self.scopes)
                    self.logger.debug(f"Loaded existing token for {self.email}")
                except Exception as e:
                    self.logger.warning(f"Failed to load existing token (likely scope mismatch): {e}")
                    # Delete invalid token file to force re-authentication
                    try:
                        self.token_file.unlink(missing_ok=True)
                        self.logger.info(f"Deleted invalid token file: {self.token_file}")
                    except:
                        pass
                    creds = None
            
            # Refresh or create credentials
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                        self.logger.info(f"Refreshed token for {self.email}")
                    except Exception as e:
                        self.logger.warning(f"Token refresh failed (likely scope mismatch): {e}")
                        # Delete invalid token file
                        try:
                            self.token_file.unlink(missing_ok=True)
                            self.logger.info(f"Deleted invalid token file: {self.token_file}")
                        except:
                            pass
                        creds = None
                
                # Create new credentials if refresh failed or no token exists
                if not creds:
                    if not Path(self.credential_file).exists():
                        raise AuthenticationError(f"Credential file not found: {self.credential_file}")
                    
                    self.logger.info(f"Starting OAuth flow for {self.email} with scopes: {self.scopes}")
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credential_file, 
                        self.scopes  # Use the fixed scopes with openid
                    )
                    
                    # Use local server for OAuth flow
                    try:
                        creds = flow.run_local_server(port=0)
                        self.logger.info(f"Successfully completed OAuth flow for {self.email}")
                    except Exception as oauth_error:
                        self.logger.error(f"OAuth flow failed for {self.email}: {oauth_error}")
                        raise AuthenticationError(f"OAuth flow failed: {oauth_error}")
                
                # Save the credentials for next time
                try:
                    with open(self.token_file, 'w') as token:
                        token.write(creds.to_json())
                        self.logger.info(f"Saved token to {self.token_file}")
                except Exception as save_error:
                    self.logger.warning(f"Failed to save token: {save_error}")
            
            # Build Gmail service
            try:
                self.service = build('gmail', 'v1', credentials=creds)
                self.logger.debug("Built Gmail service successfully")
            except Exception as service_error:
                raise ProviderError(f"Failed to build Gmail service: {service_error}")
            
            # Verify authentication by getting user profile
            try:
                self.user_profile = self.service.users().getProfile(userId='me').execute()
                self.logger.debug("Retrieved user profile successfully")
            except HttpError as http_error:
                if http_error.resp.status == 401:
                    raise AuthenticationError("Gmail API authentication failed - invalid credentials")
                elif http_error.resp.status == 403:
                    raise AuthenticationError("Gmail API access forbidden - check API permissions")
                else:
                    raise ProviderError(f"Gmail API error: {http_error}")
            
            # Verify email matches (if not 'primary')
            profile_email = self.user_profile.get('emailAddress', '').lower()
            if self.email != 'primary' and profile_email != self.email.lower():
                self.logger.warning(f"Profile email {profile_email} doesn't match expected {self.email}")
                # Don't fail authentication for this - just log the discrepancy
            
            # Update our email address if it was 'primary'
            if self.email == 'primary':
                self.email = profile_email
                self.logger.info(f"Updated primary account email to: {self.email}")
            
            self.is_authenticated = True
            self.auth_token = creds.token
            self.token_expires_at = creds.expiry
            self.last_auth_check = datetime.now()  # FIXED: Use timezone-aware datetime
            
            self.logger.info(f"Successfully authenticated Gmail account: {self.email}")
            return True
        
        except Exception as e:
            self.logger.error(f"Gmail authentication failed for {self.email}: {e}")
            self.last_error = str(e)
            self.is_authenticated = False
            
            # Clean up any partial state
            self.service = None
            self.user_profile = None
            
            return False
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get Gmail account information"""
        try:
            if not self.is_authenticated:
                raise ProviderError("Not authenticated")
            
            if not self.user_profile:
                self.user_profile = self.service.users().getProfile(userId='me').execute()
            
            return {
                'email': self.user_profile.get('emailAddress'),
                'messages_total': self.user_profile.get('messagesTotal', 0),
                'threads_total': self.user_profile.get('threadsTotal', 0),
                'history_id': self.user_profile.get('historyId'),
                'account_id': self.account_id,
                'provider_type': self.provider_type
            }
        
        except Exception as e:
            self.logger.error(f"Failed to get account info: {e}")
            return {'error': str(e)}
    
    async def extract_contacts(self, days_back: int = 30, max_emails: int = 1000) -> List[Contact]:
        """Extract contacts from Gmail"""
        try:
            if not self.is_authenticated:
                if not await self.authenticate():
                    raise ProviderError("Authentication failed")
            
            self.logger.info(f"Extracting contacts from Gmail account {self.email} (last {days_back} days, max {max_emails} emails)")
            
            # Calculate date range with timezone-aware datetimes
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # Build search query
            query = f"after:{start_date.strftime('%Y/%m/%d')} before:{end_date.strftime('%Y/%m/%d')}"
            
            # Get message list
            messages = await self._get_messages(query, max_emails)
            
            if not messages:
                self.logger.info("No messages found in date range")
                return []
            
            self.logger.info(f"Found {len(messages)} messages, processing contacts...")
            
            # Process messages to extract contacts
            contacts = await self._process_messages(messages)
            
            # Deduplicate contacts
            unique_contacts = self._deduplicate_contacts(contacts)
            
            # Update statistics
            await self.update_extraction_statistics(len(unique_contacts))
            
            self.logger.info(f"Extracted {len(unique_contacts)} unique contacts from {len(messages)} messages")
            return unique_contacts
        
        except Exception as e:
            self.logger.error(f"Contact extraction failed: {e}")
            self.last_error = str(e)
            raise ProviderError(f"Gmail contact extraction failed: {e}")
    
    async def _get_messages(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Get message list from Gmail API"""
        try:
            messages = []
            page_token = None
            
            while len(messages) < max_results:
                # Apply rate limiting
                await self._apply_rate_limit()
                
                # Calculate how many to request this batch
                remaining = max_results - len(messages)
                page_size = min(remaining, 500)  # Gmail API max per page
                
                # Make API request
                request_params = {
                    'userId': 'me',
                    'q': query,
                    'maxResults': page_size
                }
                
                if page_token:
                    request_params['pageToken'] = page_token
                
                try:
                    response = self.service.users().messages().list(**request_params).execute()
                except HttpError as e:
                    if e.resp.status == 429:  # Rate limit
                        self.logger.warning("Hit Gmail API rate limit, waiting...")
                        await asyncio.sleep(10)
                        continue
                    elif e.resp.status == 401:
                        raise AuthenticationError("Gmail API authentication expired")
                    else:
                        raise ProviderError(f"Gmail API error: {e}")
                
                batch_messages = response.get('messages', [])
                messages.extend(batch_messages)
                
                # Check for next page
                page_token = response.get('nextPageToken')
                if not page_token:
                    break
                
                self.logger.debug(f"Retrieved {len(messages)} messages so far...")
            
            return messages[:max_results]
        
        except Exception as e:
            self.logger.error(f"Failed to get messages: {e}")
            return []
    
    async def _process_messages(self, messages: List[Dict[str, Any]]) -> List[Contact]:
        """Process Gmail messages to extract contact information"""
        contacts = {}
        
        for i, message in enumerate(messages):
            try:
                # Apply rate limiting
                await self._apply_rate_limit()
                
                # Get full message details
                msg_id = message['id']
                try:
                    full_message = self.service.users().messages().get(userId='me', id=msg_id).execute()
                except HttpError as e:
                    if e.resp.status == 429:  # Rate limit
                        self.logger.warning("Hit Gmail API rate limit during message processing, waiting...")
                        await asyncio.sleep(5)
                        continue
                    elif e.resp.status == 401:
                        raise AuthenticationError("Gmail API authentication expired during processing")
                    else:
                        self.logger.warning(f"Error getting message {msg_id}: {e}")
                        continue
                
                # Extract contact information
                contact_data = self._extract_contact_from_message(full_message)
                
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
                if (i + 1) % 50 == 0:
                    self.logger.info(f"Processed {i + 1}/{len(messages)} messages")
            
            except Exception as e:
                self.logger.error(f"Failed to process message {message.get('id', 'unknown')}: {e}")
                continue
        
        return list(contacts.values())
    
    def _extract_contact_from_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract contact information from a Gmail message"""
        try:
            headers = {h['name']: h['value'] for h in message['payload'].get('headers', [])}
            
            # Determine if this is sent or received
            from_email = self._extract_email_from_sender(headers.get('From', ''))
            to_emails = self._parse_email_list(headers.get('To', ''))
            cc_emails = self._parse_email_list(headers.get('Cc', ''))
            bcc_emails = self._parse_email_list(headers.get('Bcc', ''))
            
            # Skip if no valid emails found
            if not from_email and not to_emails:
                return None
            
            # Determine the contact email (not our account email)
            contact_email = None
            interaction_type = None
            direction = None
            
            if from_email and from_email.lower() != self.email.lower():
                # This is a received email
                contact_email = from_email
                interaction_type = InteractionType.RECEIVED
                direction = "inbound"
            elif to_emails:
                # This is a sent email, find the primary recipient
                for email in to_emails:
                    if email.lower() != self.email.lower():
                        contact_email = email
                        interaction_type = InteractionType.SENT
                        direction = "outbound"
                        break
            
            if not contact_email or self._should_skip_email(contact_email):
                return None
            
            # Extract contact name
            contact_name = ""
            if interaction_type == InteractionType.RECEIVED:
                contact_name = self._extract_name_from_sender(headers.get('From', ''))
            else:
                # For sent emails, try to extract name from To header
                to_header = headers.get('To', '')
                if '<' in to_header and '>' in to_header:
                    contact_name = self._extract_name_from_sender(to_header)
            
            # Get message details
            subject = headers.get('Subject', '')
            message_id = headers.get('Message-ID', '')
            date_str = headers.get('Date', '')
            
            # FIXED: Parse date with proper timezone handling
            timestamp = self._parse_gmail_date(date_str)
            
            # Get snippet for content preview
            snippet = message.get('snippet', '')
            
            # Handle CC/BCC
            is_cc = contact_email in cc_emails
            is_bcc = contact_email in bcc_emails
            
            if is_cc:
                interaction_type = InteractionType.CC
            elif is_bcc:
                interaction_type = InteractionType.BCC
            
            return {
                'email': contact_email,
                'name': contact_name,
                'interaction_type': interaction_type,
                'direction': direction,
                'timestamp': timestamp,
                'subject': subject,
                'message_id': message_id,
                'content_preview': snippet,
                'is_cc': is_cc,
                'is_bcc': is_bcc
            }
        
        except Exception as e:
            self.logger.error(f"Failed to extract contact from message: {e}")
            return None
    
    def _parse_gmail_date(self, date_str: str) -> datetime:
        """FIXED: Parse Gmail date string to datetime with proper timezone handling"""
        try:
            if not date_str:
                return datetime.now()
            
            # Gmail dates are in RFC 2822 format
            from email.utils import parsedate_to_datetime
            parsed_date = parsedate_to_datetime(date_str)
            
            # Ensure the datetime is timezone-aware
            if parsed_date.tzinfo is None:
                # If no timezone info, assume UTC
                parsed_date = parsed_date.replace(tzinfo=timezone.utc)
            
            return parsed_date
            
        except Exception as e:
            self.logger.debug(f"Failed to parse date '{date_str}': {e}")
            # Fallback to current time with UTC timezone
            return datetime.now()
    
    def _create_contact_from_data(self, contact_data: Dict[str, Any]) -> Contact:
        """FIXED: Create a Contact object from extracted data with timezone-aware timestamps"""
        contact = Contact(
            email=contact_data['email'],
            name=contact_data.get('name', ''),
            provider=EmailProvider.GMAIL
        )
        
        # Set contact type based on domain
        contact.contact_type = ContactType(self._determine_contact_type(contact.email))
        
        # Add source account
        contact.add_source_account(self.account_id)
        
        # FIXED: Ensure timestamp is timezone-aware
        timestamp = contact_data['timestamp']
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        
        # Create interaction
        interaction = self._create_interaction(
            interaction_type=contact_data['interaction_type'],
            timestamp=timestamp,  # Use the timezone-aware timestamp
            subject=contact_data.get('subject', ''),
            message_id=contact_data.get('message_id', ''),
            direction=contact_data.get('direction', ''),
            content_preview=contact_data.get('content_preview', '')
        )
        
        # Add interaction to contact
        contact.add_interaction(interaction)
        
        return contact
    
    def _merge_contact_data(self, contact: Contact, contact_data: Dict[str, Any]) -> None:
        """FIXED: Merge new contact data into existing contact with timezone handling"""
        # FIXED: Ensure timestamp is timezone-aware
        timestamp = contact_data['timestamp']
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        
        # Create new interaction
        interaction = self._create_interaction(
            interaction_type=contact_data['interaction_type'],
            timestamp=timestamp,  # Use the timezone-aware timestamp
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
    
    def _parse_email_list(self, email_str: str) -> List[str]:
        """Parse a comma-separated list of emails"""
        if not email_str:
            return []
        
        emails = []
        # Split by comma and extract emails
        for part in email_str.split(','):
            email = self._extract_email_from_sender(part.strip())
            if email:
                emails.append(email)
        
        return emails
    
    async def send_email(self, to_email: str, subject: str, body: str) -> bool:
        """Send an email (optional feature)"""
        try:
            if not self.is_authenticated:
                if not await self.authenticate():
                    return False
            
            # Create message
            message = MIMEText(body)
            message['to'] = to_email
            message['subject'] = subject
            message['from'] = self.email
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            # Send message
            await self._apply_rate_limit()
            
            send_result = self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            self.logger.info(f"Sent email to {to_email}: {send_result.get('id')}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")
            return False
    
    async def get_labels(self) -> List[Dict[str, Any]]:
        """Get Gmail labels"""
        try:
            if not self.is_authenticated:
                if not await self.authenticate():
                    return []
            
            await self._apply_rate_limit()
            
            results = self.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])
            
            return labels
        
        except Exception as e:
            self.logger.error(f"Failed to get labels: {e}")
            return []
    
    async def cleanup(self):
        """Cleanup Gmail provider resources"""
        try:
            await super().cleanup()
            
            # Close service connection
            if self.service:
                try:
                    self.service.close()
                except:
                    pass  # Service might not have close method
                self.service = None
            
            self.user_profile = None
            
            self.logger.info(f"Cleaned up Gmail provider for {self.email}")
        
        except Exception as e:
            self.logger.error(f"Gmail cleanup failed: {e}")
    
    def get_quota_usage(self) -> Dict[str, Any]:
        """Get Gmail API quota usage information"""
        return {
            'requests_this_hour': self.requests_this_hour,
            'rate_limit_per_hour': self.rate_limit_per_hour,
            'total_requests': self.total_requests,
            'last_request_time': self.last_request_time.isoformat() if self.last_request_time else None
        }