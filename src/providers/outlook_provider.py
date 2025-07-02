"""
Microsoft Outlook/Office 365 Email Provider
Uses Microsoft Graph API for email access
Production-ready with OAuth 2.0, rate limiting, and error handling
"""

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from urllib.parse import urlencode
import aiohttp
import msal

from core.models import Contact, EmailProvider, InteractionType
from core.exceptions import AuthenticationError, ProviderError, RateLimitError
from .base_provider import BaseEmailProvider, ProviderConfig

class OutlookProvider(BaseEmailProvider):
    """
    Microsoft Outlook/Office 365 provider using Graph API
    Supports both personal Outlook.com and business Office 365 accounts
    """
    
    # Microsoft Graph API endpoints
    GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
    AUTH_BASE_URL = "https://login.microsoftonline.com"
    
    # OAuth 2.0 scopes for email access
    SCOPES = [
        "https://graph.microsoft.com/Mail.Read",
        "https://graph.microsoft.com/User.Read",
        "https://graph.microsoft.com/Contacts.Read"
    ]
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        
        # Microsoft Graph specific settings
        self.client_id = config.credentials.get('client_id')
        self.client_secret = config.credentials.get('client_secret') 
        self.tenant_id = config.credentials.get('tenant_id', 'common')  # 'common' for personal accounts
        self.redirect_uri = config.credentials.get('redirect_uri', 'http://localhost:8080/auth/callback')
        
        # Authentication state
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        
        # MSAL application for OAuth
        self.msal_app = None
        self._initialize_msal()
        
        # Session for API requests
        self.session = None
    
    def _initialize_msal(self):
        """Initialize MSAL (Microsoft Authentication Library) application"""
        try:
            authority = f"{self.AUTH_BASE_URL}/{self.tenant_id}"
            
            self.msal_app = msal.ConfidentialClientApplication(
                client_id=self.client_id,
                client_credential=self.client_secret,
                authority=authority
            )
            
        except Exception as e:
            raise AuthenticationError(
                message=f"Failed to initialize MSAL application: {e}",
                provider="outlook"
            )
    
    def _get_required_credentials(self) -> List[str]:
        """Required credentials for Outlook provider"""
        return ['client_id', 'client_secret']
    
    async def authenticate(self) -> bool:
        """
        Authenticate with Microsoft Graph API using OAuth 2.0
        Supports both interactive and refresh token flows
        """
        try:
            self.logger.info("Starting Outlook authentication...")
            
            # Try to load existing tokens
            if await self._load_tokens():
                if await self._validate_token():
                    self.is_authenticated = True
                    self.logger.info("Loaded existing valid tokens")
                    return True
                elif self.refresh_token:
                    if await self._refresh_access_token():
                        self.is_authenticated = True
                        self.logger.info("Refreshed access token")
                        return True
            
            # Interactive authentication flow
            return await self._interactive_auth()
            
        except Exception as e:
            self.logger.error(f"Outlook authentication failed: {e}")
            await self._handle_provider_error(e, "authentication")
            return False
    
    async def _load_tokens(self) -> bool:
        """Load tokens from storage"""
        try:
            token_file = self.config.settings.get('token_file', 'data/tokens/outlook_token.json')
            
            with open(token_file, 'r') as f:
                token_data = json.load(f)
            
            self.access_token = token_data.get('access_token')
            self.refresh_token = token_data.get('refresh_token')
            self.token_expires_at = datetime.fromisoformat(token_data.get('expires_at', ''))
            
            return bool(self.access_token)
            
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return False
    
    async def _save_tokens(self):
        """Save tokens to storage"""
        try:
            import os
            token_file = self.config.settings.get('token_file', 'data/tokens/outlook_token.json')
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(token_file), exist_ok=True)
            
            token_data = {
                'access_token': self.access_token,
                'refresh_token': self.refresh_token,
                'expires_at': self.token_expires_at.isoformat() if self.token_expires_at else None
            }
            
            with open(token_file, 'w') as f:
                json.dump(token_data, f, indent=2)
                
        except Exception as e:
            self.logger.warning(f"Failed to save tokens: {e}")
    
    async def _validate_token(self) -> bool:
        """Validate current access token"""
        if not self.access_token:
            return False
        
        if self.token_expires_at and datetime.now() >= self.token_expires_at:
            return False
        
        # Test token by making a simple API call
        try:
            async with aiohttp.ClientSession() as session:
                headers = {'Authorization': f'Bearer {self.access_token}'}
                async with session.get(f"{self.GRAPH_BASE_URL}/me", headers=headers) as response:
                    return response.status == 200
        except:
            return False
    
    async def _refresh_access_token(self) -> bool:
        """Refresh access token using refresh token"""
        try:
            if not self.refresh_token:
                return False
            
            result = self.msal_app.acquire_token_by_refresh_token(
                refresh_token=self.refresh_token,
                scopes=self.SCOPES
            )
            
            if 'access_token' in result:
                self._process_token_response(result)
                await self._save_tokens()
                return True
            else:
                self.logger.error(f"Token refresh failed: {result.get('error_description', 'Unknown error')}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to refresh token: {e}")
            return False
    
    async def _interactive_auth(self) -> bool:
        """
        Perform interactive authentication
        Opens browser for user consent
        """
        try:
            # Get authorization URL
            auth_url = self.msal_app.get_authorization_request_url(
                scopes=self.SCOPES,
                redirect_uri=self.redirect_uri
            )
            
            print(f"Please visit this URL to authorize the application:")
            print(f"{auth_url}")
            print()
            
            # Get authorization code from user
            auth_code = input("Enter the authorization code from the callback URL: ").strip()
            
            if not auth_code:
                raise AuthenticationError("No authorization code provided", "outlook")
            
            # Exchange code for tokens
            result = self.msal_app.acquire_token_by_authorization_code(
                code=auth_code,
                scopes=self.SCOPES,
                redirect_uri=self.redirect_uri
            )
            
            if 'access_token' in result:
                self._process_token_response(result)
                await self._save_tokens()
                self.is_authenticated = True
                self.logger.info("Interactive authentication successful")
                return True
            else:
                error_msg = result.get('error_description', 'Unknown error')
                raise AuthenticationError(f"Token exchange failed: {error_msg}", "outlook")
                
        except Exception as e:
            self.logger.error(f"Interactive authentication failed: {e}")
            return False
    
    def _process_token_response(self, token_response: Dict[str, Any]):
        """Process token response from MSAL"""
        self.access_token = token_response['access_token']
        self.refresh_token = token_response.get('refresh_token')
        
        # Calculate expiration time
        expires_in = token_response.get('expires_in', 3600)
        self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)  # 5 min buffer
    
    async def test_connection(self) -> bool:
        """Test connection to Microsoft Graph API"""
        try:
            if not self.is_authenticated:
                return False
            
            account_info = await self.get_account_info()
            return bool(account_info.get('id'))
            
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information from Microsoft Graph"""
        try:
            await self._ensure_session()
            
            headers = await self._get_auth_headers()
            
            async with self.session.get(f"{self.GRAPH_BASE_URL}/me", headers=headers) as response:
                await self._handle_response_errors(response)
                self._increment_api_call()
                
                data = await response.json()
                
                return {
                    'id': data.get('id'),
                    'email': data.get('mail') or data.get('userPrincipalName'),
                    'display_name': data.get('displayName'),
                    'given_name': data.get('givenName'),
                    'surname': data.get('surname'),
                    'job_title': data.get('jobTitle'),
                    'office_location': data.get('officeLocation'),
                    'tenant_id': self.tenant_id
                }
                
        except Exception as e:
            await self._handle_provider_error(e, "get_account_info")
    
    async def extract_contacts(self, 
                             days_back: int = 30,
                             max_emails: int = 1000,
                             account_id: Optional[str] = None) -> List[Contact]:
        """Extract contacts from Outlook emails"""
        try:
            self.logger.info(f"Extracting contacts from last {days_back} days, max {max_emails} emails")
            
            await self._ensure_session()
            self._check_rate_limits()
            
            # Get account info for reference
            account_info = await self.get_account_info()
            my_email = account_info['email']
            
            # Build date filter
            start_date, end_date = self._get_date_range(days_back)
            date_filter = f"receivedDateTime ge {start_date.isoformat()}Z and receivedDateTime le {end_date.isoformat()}Z"
            
            # Get emails with pagination
            contacts_dict = {}
            processed_count = 0
            
            url = f"{self.GRAPH_BASE_URL}/me/messages"
            params = {
                '$filter': date_filter,
                '$select': 'id,subject,receivedDateTime,from,toRecipients,ccRecipients,bccRecipients,sender',
                '$orderby': 'receivedDateTime desc',
                '$top': min(max_emails, 50)  # Process in batches
            }
            
            while url and processed_count < max_emails:
                headers = await self._get_auth_headers()
                
                async with self.session.get(url, headers=headers, params=params if url == f"{self.GRAPH_BASE_URL}/me/messages" else None) as response:
                    await self._handle_response_errors(response)
                    self._increment_api_call()
                    
                    data = await response.json()
                    messages = data.get('value', [])
                    
                    # Process each message
                    for message in messages:
                        if processed_count >= max_emails:
                            break
                        
                        self._extract_contacts_from_message(
                            message, contacts_dict, my_email, account_id
                        )
                        processed_count += 1
                    
                    # Get next page
                    url = data.get('@odata.nextLink')
                    params = None  # Params are included in nextLink URL
                    
                    # Rate limiting
                    await asyncio.sleep(0.1)  # Small delay between requests
            
            contacts = list(contacts_dict.values())
            self.logger.info(f"Extracted {len(contacts)} unique contacts from {processed_count} emails")
            
            return contacts
            
        except Exception as e:
            await self._handle_provider_error(e, "extract_contacts")
    
    def _extract_contacts_from_message(self, 
                                     message: Dict[str, Any],
                                     contacts_dict: Dict[str, Contact],
                                     my_email: str,
                                     account_id: Optional[str]):
        """Extract contacts from a single message"""
        try:
            subject = message.get('subject', '')
            message_id = message.get('id')
            received_date = datetime.fromisoformat(message.get('receivedDateTime', '').replace('Z', '+00:00'))
            
            # Process From field
            from_data = message.get('from', {})
            if from_data:
                self._process_email_address(
                    from_data, contacts_dict, InteractionType.RECEIVED,
                    subject, message_id, received_date, my_email, account_id
                )
            
            # Process To recipients
            for recipient in message.get('toRecipients', []):
                self._process_email_address(
                    recipient, contacts_dict, InteractionType.SENT,
                    subject, message_id, received_date, my_email, account_id
                )
            
            # Process CC recipients
            for recipient in message.get('ccRecipients', []):
                self._process_email_address(
                    recipient, contacts_dict, InteractionType.CC,
                    subject, message_id, received_date, my_email, account_id
                )
            
            # Process BCC recipients (if available)
            for recipient in message.get('bccRecipients', []):
                self._process_email_address(
                    recipient, contacts_dict, InteractionType.BCC,
                    subject, message_id, received_date, my_email, account_id
                )
                
        except Exception as e:
            self.logger.warning(f"Error processing message {message.get('id', 'unknown')}: {e}")
    
    def _process_email_address(self,
                             address_data: Dict[str, Any],
                             contacts_dict: Dict[str, Contact],
                             interaction_type: InteractionType,
                             subject: str,
                             message_id: str,
                             timestamp: datetime,
                             my_email: str,
                             account_id: Optional[str]):
        """Process a single email address from message data"""
        try:
            email_address = address_data.get('emailAddress', {})
            email = email_address.get('address', '').lower().strip()
            name = email_address.get('name', '').strip()
            
            # Skip my own email and invalid emails
            if not email or email == my_email.lower() or not self._is_valid_contact_email(email):
                return
            
            # Get or create contact
            if email in contacts_dict:
                contact = contacts_dict[email]
                
                # Update name if the new one is better
                if len(name) > len(contact.name) and name:
                    contact.name = name
            else:
                contact = Contact(
                    email=email,
                    name=name or email.split('@')[0],
                    provider=EmailProvider.OUTLOOK,
                    provider_contact_id=message_id,
                    account_id=account_id,
                    first_seen=timestamp
                )
                contacts_dict[email] = contact
            
            # Add interaction
            contact.add_interaction(
                interaction_type=interaction_type,
                subject=subject,
                message_id=message_id
            )
            
        except Exception as e:
            self.logger.warning(f"Error processing email address: {e}")
    
    async def get_email_headers(self, 
                               message_id: str,
                               account_id: Optional[str] = None) -> Dict[str, str]:
        """Get email headers for a specific message"""
        try:
            await self._ensure_session()
            headers = await self._get_auth_headers()
            
            url = f"{self.GRAPH_BASE_URL}/me/messages/{message_id}"
            params = {
                '$select': 'internetMessageHeaders,from,toRecipients,ccRecipients,subject,receivedDateTime'
            }
            
            async with self.session.get(url, headers=headers, params=params) as response:
                await self._handle_response_errors(response)
                self._increment_api_call()
                
                data = await response.json()
                
                # Convert Graph API format to standard headers
                headers_dict = {}
                
                # Add standard headers
                if 'subject' in data:
                    headers_dict['Subject'] = data['subject']
                if 'receivedDateTime' in data:
                    headers_dict['Date'] = data['receivedDateTime']
                
                # Process internet message headers
                for header in data.get('internetMessageHeaders', []):
                    headers_dict[header['name']] = header['value']
                
                return headers_dict
                
        except Exception as e:
            await self._handle_provider_error(e, "get_email_headers")
    
    async def search_emails(self,
                           query: str,
                           max_results: int = 100,
                           account_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search emails using Microsoft Graph search"""
        try:
            await self._ensure_session()
            headers = await self._get_auth_headers()
            
            url = f"{self.GRAPH_BASE_URL}/me/messages"
            params = {
                '$search': f'"{query}"',
                '$select': 'id,subject,from,toRecipients,receivedDateTime,hasAttachments',
                '$top': min(max_results, 100)
            }
            
            async with self.session.get(url, headers=headers, params=params) as response:
                await self._handle_response_errors(response)
                self._increment_api_call()
                
                data = await response.json()
                return data.get('value', [])
                
        except Exception as e:
            await self._handle_provider_error(e, "search_emails")
    
    async def _ensure_session(self):
        """Ensure aiohttp session exists"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def _get_auth_headers(self) -> Dict[str, str]:
        """Get authorization headers for API requests"""
        if not self.access_token:
            raise AuthenticationError("No access token available", "outlook")
        
        # Check if token needs refresh
        if self.token_expires_at and datetime.now() >= self.token_expires_at:
            if not await self._refresh_access_token():
                raise AuthenticationError("Token refresh failed", "outlook")
        
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    async def _handle_response_errors(self, response: aiohttp.ClientResponse):
        """Handle HTTP response errors"""
        if response.status == 401:
            raise AuthenticationError("Authentication failed - token may be invalid", "outlook")
        elif response.status == 429:
            retry_after = int(response.headers.get('Retry-After', 3600))
            raise RateLimitError(
                message="Microsoft Graph rate limit exceeded",
                provider="outlook",
                retry_after=retry_after
            )
        elif response.status >= 400:
            error_text = await response.text()
            raise ProviderError(
                message=f"Microsoft Graph API error: {response.status} - {error_text}",
                provider="outlook"
            )
    
    async def close(self):
        """Close the provider and clean up resources"""
        if self.session:
            await self.session.close()
            self.session = None
    
    def __del__(self):
        """Cleanup when object is destroyed"""
        if self.session and not self.session.closed:
            # Note: This is not ideal but necessary for cleanup
            # In production, always call close() explicitly
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.session.close())
                else:
                    loop.run_until_complete(self.session.close())
            except:
                pass