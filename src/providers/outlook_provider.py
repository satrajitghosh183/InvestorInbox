

"""
Outlook Provider with Multiple Account Support
Supports Microsoft Graph API for Outlook/Office 365 accounts
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import asyncio

try:
    import aiohttp
    from msal import ConfidentialClientApplication, PublicClientApplication
    MSAL_AVAILABLE = True
except ImportError:
    MSAL_AVAILABLE = False

from providers.base_provider import BaseEmailProvider
from core.models import Contact, InteractionType, EmailProvider, ContactType
from core.exceptions import AuthenticationError, ProviderError

class OutlookProvider(BaseEmailProvider):
    """
    Outlook/Office 365 provider using Microsoft Graph API
    """
    
    def __init__(self, account_id: str, email: str, credential_file: str = ""):
        super().__init__(account_id, email, credential_file)
        
        if not MSAL_AVAILABLE:
            raise ProviderError("MSAL library not available. Install with: pip install msal aiohttp")
        
        # Microsoft Graph configuration
        self.graph_url = "https://graph.microsoft.com/v1.0"
        self.scopes = [
            "https://graph.microsoft.com/Mail.Read",
            "https://graph.microsoft.com/User.Read"
        ]
        
        # OAuth configuration from environment or config
        self.client_id = os.getenv('OUTLOOK_CLIENT_ID')
        self.client_secret = os.getenv('OUTLOOK_CLIENT_SECRET')
        self.tenant_id = os.getenv('OUTLOOK_TENANT_ID', 'common')
        
        if not self.client_id:
            raise ProviderError("OUTLOOK_CLIENT_ID environment variable required")
        
        # MSAL app
        self.app = None
        self.access_token = None
        
        # Token file for this specific account
        self.token_file = self._get_token_file_path()
        
        # HTTP session
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Rate limiting (Microsoft Graph limits)
        self.rate_limit_per_hour = 10000  # Graph API quota
        
        self.logger.info(f"Initialized Outlook provider for {self.email}")
    
    def _get_provider_type(self) -> str:
        return "outlook"
    
    def _get_token_file_path(self) -> Path:
        """Get account-specific token file path"""
        tokens_dir = Path("data/tokens")
        tokens_dir.mkdir(parents=True, exist_ok=True)
        
        safe_email = self.email.replace('@', '_').replace('.', '_')
        return tokens_dir / f"outlook_{safe_email}_token.json"
    
    async def authenticate(self) -> bool:
        """Authenticate with Microsoft Graph"""
        try:
            # Initialize MSAL app
            if self.client_secret:
                # Confidential client (web app)
                self.app = ConfidentialClientApplication(
                    client_id=self.client_id,
                    client_credential=self.client_secret,
                    authority=f"https://login.microsoftonline.com/{self.tenant_id}"
                )
            else:
                # Public client (desktop app)
                self.app = PublicClientApplication(
                    client_id=self.client_id,
                    authority=f"https://login.microsoftonline.com/{self.tenant_id}"
                )
            
            # Try to get token from cache
            accounts = self.app.get_accounts()
            target_account = None
            
            for account in accounts:
                if account.get('username', '').lower() == self.email.lower():
                    target_account = account
                    break
            
            token_result = None
            
            if target_account:
                # Try silent token acquisition
                token_result = self.app.acquire_token_silent(
                    scopes=self.scopes,
                    account=target_account
                )
            
            if not token_result:
                # Interactive authentication required
                if self.client_secret:
                    # For confidential client, use device flow
                    flow = self.app.initiate_device_flow(scopes=self.scopes)
                    
                    print(f"To authenticate {self.email}, visit: {flow['verification_uri']}")
                    print(f"Enter code: {flow['user_code']}")
                    
                    token_result = self.app.acquire_token_by_device_flow(flow)
                else:
                    # For public client, use interactive flow
                    token_result = self.app.acquire_token_interactive(scopes=self.scopes)
            
            if not token_result or 'access_token' not in token_result:
                error = token_result.get('error_description', 'Unknown error') if token_result else 'No token result'
                raise AuthenticationError(f"Authentication failed: {error}")
            
            self.access_token = token_result['access_token']
            
            # Save token info
            if self.token_file:
                with open(self.token_file, 'w') as f:
                    json.dump({
                        'access_token': self.access_token,
                        'expires_at': (datetime.now() + timedelta(seconds=token_result.get('expires_in', 3600))).isoformat(),
                        'email': self.email
                    }, f)
            
            # Verify authentication by getting user profile
            if not await self._verify_authentication():
                raise AuthenticationError("Token verification failed")
            
            self.is_authenticated = True
            self.last_auth_check = datetime.now()
            
            self.logger.info(f"Successfully authenticated Outlook account: {self.email}")
            return True
        
        except Exception as e:
            self.logger.error(f"Outlook authentication failed for {self.email}: {e}")
            self.last_error = str(e)
            self.is_authenticated = False
            return False
    
    async def _verify_authentication(self) -> bool:
        """Verify authentication by getting user profile"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            async with self.session.get(f"{self.graph_url}/me", headers=headers) as response:
                if response.status == 200:
                    user_data = await response.json()
                    profile_email = user_data.get('mail') or user_data.get('userPrincipalName', '')
                    
                    if profile_email.lower() != self.email.lower():
                        self.logger.warning(f"Profile email {profile_email} doesn't match expected {self.email}")
                    
                    return True
                else:
                    self.logger.error(f"Authentication verification failed: {response.status}")
                    return False
        
        except Exception as e:
            self.logger.error(f"Authentication verification error: {e}")
            return False
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get Outlook account information"""
        try:
            if not self.is_authenticated:
                raise ProviderError("Not authenticated")
            
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            # Get user profile
            async with self.session.get(f"{self.graph_url}/me", headers=headers) as response:
                if response.status != 200:
                    raise ProviderError(f"Failed to get user profile: {response.status}")
                
                user_data = await response.json()
            
            # Get mailbox statistics
            mailbox_stats = {}
            try:
                async with self.session.get(f"{self.graph_url}/me/mailFolders/inbox", headers=headers) as response:
                    if response.status == 200:
                        inbox_data = await response.json()
                        mailbox_stats = {
                            'total_item_count': inbox_data.get('totalItemCount', 0),
                            'unread_item_count': inbox_data.get('unreadItemCount', 0)
                        }
            except Exception as e:
                self.logger.warning(f"Failed to get mailbox stats: {e}")
            
            return {
                'email': user_data.get('mail') or user_data.get('userPrincipalName'),
                'display_name': user_data.get('displayName'),
                'id': user_data.get('id'),
                'account_id': self.account_id,
                'provider_type': self.provider_type,
                **mailbox_stats
            }
        
        except Exception as e:
            self.logger.error(f"Failed to get account info: {e}")
            return {'error': str(e)}
    
    async def extract_contacts(self, days_back: int = 30, max_emails: int = 1000) -> List[Contact]:
        """Extract contacts from Outlook"""
        try:
            if not self.is_authenticated:
                if not await self.authenticate():
                    raise ProviderError("Authentication failed")
            
            self.logger.info(f"Extracting contacts from Outlook account {self.email} (last {days_back} days, max {max_emails} emails)")
            
            # Initialize session if needed
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # Calculate date filter
            start_date = datetime.now() - timedelta(days=days_back)
            date_filter = start_date.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            # Get messages
            messages = await self._get_messages(date_filter, max_emails)
            
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
            raise ProviderError(f"Outlook contact extraction failed: {e}")
    
    async def _get_messages(self, date_filter: str, max_results: int) -> List[Dict[str, Any]]:
        """Get message list from Microsoft Graph API"""
        try:
            messages = []
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            # Build query parameters
            filter_param = f"receivedDateTime ge {date_filter}"
            select_param = "id,subject,from,toRecipients,ccRecipients,bccRecipients,receivedDateTime,sentDateTime,bodyPreview,isRead"
            
            url = f"{self.graph_url}/me/messages"
            params = {
                '$filter': filter_param,
                '$select': select_param,
                '$orderby': 'receivedDateTime desc',
                '$top': min(max_results, 1000)  # Graph API max per page
            }
            
            while len(messages) < max_results:
                # Apply rate limiting
                await self._apply_rate_limit()
                
                async with self.session.get(url, headers=headers, params=params) as response:
                    if response.status == 429:  # Rate limit
                        retry_after = int(response.headers.get('Retry-After', 60))
                        self.logger.warning(f"Hit Graph API rate limit, waiting {retry_after} seconds")
                        await asyncio.sleep(retry_after)
                        continue
                    
                    if response.status != 200:
                        self.logger.error(f"Failed to get messages: {response.status}")
                        break
                    
                    data = await response.json()
                    batch_messages = data.get('value', [])
                    messages.extend(batch_messages)
                    
                    # Check for next page
                    next_link = data.get('@odata.nextLink')
                    if not next_link or len(messages) >= max_results:
                        break
                    
                    url = next_link
                    params = {}  # Parameters are included in the next link
                    
                    self.logger.debug(f"Retrieved {len(messages)} messages so far...")
            
            return messages[:max_results]
        
        except Exception as e:
            self.logger.error(f"Failed to get messages: {e}")
            return []
    
    async def _process_messages(self, messages: List[Dict[str, Any]]) -> List[Contact]:
        """Process Outlook messages to extract contact information"""
        contacts = {}
        
        for i, message in enumerate(messages):
            try:
                # Extract contact information
                contact_data = self._extract_contact_from_message(message)
                
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
        """Extract contact information from an Outlook message"""
        try:
            # Get sender and recipients
            from_data = message.get('from', {}).get('emailAddress', {})
            to_recipients = message.get('toRecipients', [])
            cc_recipients = message.get('ccRecipients', [])
            bcc_recipients = message.get('bccRecipients', [])
            
            from_email = from_data.get('address', '').lower()
            from_name = from_data.get('name', '')
            
            # Parse timestamps
            received_time = self._parse_outlook_date(message.get('receivedDateTime'))
            sent_time = self._parse_outlook_date(message.get('sentDateTime'))
            timestamp = received_time or sent_time or datetime.now()
            
            # Determine if this is sent or received
            contact_email = None
            contact_name = ""
            interaction_type = None
            direction = None
            is_cc = False
            is_bcc = False
            
            if from_email and from_email != self.email.lower():
                # This is a received email
                contact_email = from_email
                contact_name = from_name
                interaction_type = InteractionType.RECEIVED
                direction = "inbound"
            else:
                # This is a sent email, find the primary recipient
                for recipient in to_recipients:
                    email_addr = recipient.get('emailAddress', {})
                    email = email_addr.get('address', '').lower()
                    name = email_addr.get('name', '')
                    
                    if email != self.email.lower():
                        contact_email = email
                        contact_name = name
                        interaction_type = InteractionType.SENT
                        direction = "outbound"
                        break
                
                # Check CC recipients
                if not contact_email:
                    for recipient in cc_recipients:
                        email_addr = recipient.get('emailAddress', {})
                        email = email_addr.get('address', '').lower()
                        name = email_addr.get('name', '')
                        
                        if email != self.email.lower():
                            contact_email = email
                            contact_name = name
                            interaction_type = InteractionType.CC
                            direction = "outbound"
                            is_cc = True
                            break
            
            if not contact_email or self._should_skip_email(contact_email):
                return None
            
            # Get message details
            subject = message.get('subject', '')
            message_id = message.get('id', '')
            body_preview = message.get('bodyPreview', '')
            
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
                'is_bcc': is_bcc
            }
        
        except Exception as e:
            self.logger.error(f"Failed to extract contact from message: {e}")
            return None
    
    def _create_contact_from_data(self, contact_data: Dict[str, Any]) -> Contact:
        """Create a Contact object from extracted data"""
        contact = Contact(
            email=contact_data['email'],
            name=contact_data.get('name', ''),
            provider=EmailProvider.OUTLOOK
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
    
    def _parse_outlook_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse Outlook date string to datetime"""
        if not date_str:
            return None
        
        try:
            # Outlook dates are in ISO 8601 format
            if date_str.endswith('Z'):
                date_str = date_str[:-1] + '+00:00'
            
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except Exception as e:
            self.logger.warning(f"Failed to parse date {date_str}: {e}")
            return None
    
    async def send_email(self, to_email: str, subject: str, body: str) -> bool:
        """Send an email via Microsoft Graph"""
        try:
            if not self.is_authenticated:
                if not await self.authenticate():
                    return False
            
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            # Create message payload
            message_payload = {
                "message": {
                    "subject": subject,
                    "body": {
                        "contentType": "Text",
                        "content": body
                    },
                    "toRecipients": [
                        {
                            "emailAddress": {
                                "address": to_email
                            }
                        }
                    ]
                }
            }
            
            # Send message
            await self._apply_rate_limit()
            
            async with self.session.post(
                f"{self.graph_url}/me/sendMail",
                headers=headers,
                json=message_payload
            ) as response:
                
                if response.status == 202:  # Accepted
                    self.logger.info(f"Sent email to {to_email}")
                    return True
                else:
                    error_text = await response.text()
                    self.logger.error(f"Failed to send email: {response.status} - {error_text}")
                    return False
        
        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")
            return False
    
    async def get_folders(self) -> List[Dict[str, Any]]:
        """Get Outlook mail folders"""
        try:
            if not self.is_authenticated:
                if not await self.authenticate():
                    return []
            
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            await self._apply_rate_limit()
            
            async with self.session.get(f"{self.graph_url}/me/mailFolders", headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('value', [])
                else:
                    self.logger.error(f"Failed to get folders: {response.status}")
                    return []
        
        except Exception as e:
            self.logger.error(f"Failed to get folders: {e}")
            return []
    
    async def cleanup(self):
        """Cleanup Outlook provider resources"""
        try:
            await super().cleanup()
            
            # Close HTTP session
            if self.session:
                await self.session.close()
                self.session = None
            
            # Clear tokens
            self.access_token = None
            self.app = None
            
            self.logger.info(f"Cleaned up Outlook provider for {self.email}")
        
        except Exception as e:
            self.logger.error(f"Outlook cleanup failed: {e}")
    
    def get_quota_usage(self) -> Dict[str, Any]:
        """Get Microsoft Graph API quota usage information"""
        return {
            'requests_this_hour': self.requests_this_hour,
            'rate_limit_per_hour': self.rate_limit_per_hour,
            'total_requests': self.total_requests,
            'last_request_time': self.last_request_time.isoformat() if self.last_request_time else None,
            'has_access_token': bool(self.access_token)
        }