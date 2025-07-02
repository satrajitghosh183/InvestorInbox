"""
Abstract base class for email providers
Defines the interface that all email providers must implement
"""

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass

from core.models import Contact, EmailProvider, ProviderStatus
from core.exceptions import ProviderError, AuthenticationError, RateLimitError

@dataclass
class ProviderConfig:
    """Configuration for email providers"""
    provider_type: EmailProvider
    credentials: Dict[str, Any]
    settings: Dict[str, Any]
    rate_limits: Dict[str, int]
    timeout: int = 30
    max_retries: int = 3
    
class BaseEmailProvider(ABC):
    """
    Abstract base class for all email providers
    Defines the common interface and shared functionality
    """
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.provider_type = config.provider_type
        self.logger = logging.getLogger(f"{__name__}.{self.provider_type.value}")
        self.is_authenticated = False
        self.last_sync = None
        self.api_calls_today = 0
        self.rate_limit_remaining = config.rate_limits.get('daily', 10000)
        self._status = ProviderStatus(provider=self.provider_type)
    
    @abstractmethod
    async def authenticate(self) -> bool:
        """
        Authenticate with the email provider
        Returns True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """
        Test if the connection to the provider is working
        Returns True if connection is healthy
        """
        pass
    
    @abstractmethod
    async def get_account_info(self) -> Dict[str, Any]:
        """
        Get account information from the provider
        Returns dict with account details
        """
        pass
    
    @abstractmethod
    async def extract_contacts(self, 
                             days_back: int = 30,
                             max_emails: int = 1000,
                             account_id: Optional[str] = None) -> List[Contact]:
        """
        Extract contacts from emails
        
        Args:
            days_back: Number of days to look back
            max_emails: Maximum number of emails to process
            account_id: Specific account ID (for multi-account providers)
        
        Returns:
            List of Contact objects
        """
        pass
    
    @abstractmethod
    async def get_email_headers(self, 
                               message_id: str,
                               account_id: Optional[str] = None) -> Dict[str, str]:
        """
        Get email headers for a specific message
        
        Args:
            message_id: Provider-specific message identifier
            account_id: Account ID if applicable
        
        Returns:
            Dictionary of email headers
        """
        pass
    
    @abstractmethod
    async def search_emails(self,
                           query: str,
                           max_results: int = 100,
                           account_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search emails using provider-specific query syntax
        
        Args:
            query: Search query
            max_results: Maximum number of results
            account_id: Account ID if applicable
        
        Returns:
            List of email metadata dictionaries
        """
        pass
    
    # Common utility methods (implemented in base class)
    
    def get_status(self) -> ProviderStatus:
        """Get current provider status"""
        self._status.is_connected = self.is_authenticated
        self._status.last_sync = self.last_sync
        self._status.api_calls_today = self.api_calls_today
        self._status.rate_limit_remaining = self.rate_limit_remaining
        return self._status
    
    def _check_rate_limits(self) -> None:
        """Check if we're within rate limits"""
        if self.rate_limit_remaining <= 0:
            raise RateLimitError(
                message=f"{self.provider_type.value} daily rate limit exceeded",
                provider=self.provider_type.value,
                retry_after=86400  # 24 hours
            )
    
    def _increment_api_call(self) -> None:
        """Increment API call counter"""
        self.api_calls_today += 1
        self.rate_limit_remaining = max(0, self.rate_limit_remaining - 1)
    
    def _extract_emails_from_header(self, header_value: str) -> List[Tuple[str, str]]:
        """
        Extract name and email pairs from email header
        Common implementation used by all providers
        """
        if not header_value:
            return []
        
        from email.utils import parseaddr
        import re
        
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
                
                # Filter out system emails
                if self._is_valid_contact_email(email):
                    contacts.append((name, email))
        
        return contacts
    
    def _is_valid_contact_email(self, email: str) -> bool:
        """Filter out system/bot emails - common implementation"""
        if not email or '@' not in email:
            return False
        
        email_lower = email.lower()
        domain = email_lower.split('@')[1]
        
        # Exclude domains (from config)
        exclude_domains = self.config.settings.get('exclude_domains', [
            'noreply.gmail.com', 'mail-noreply.google.com', 
            'noreply.youtube.com', 'noreply.facebook.com',
            'no-reply.uber.com', 'donotreply.com',
            'mailer-daemon', 'postmaster'
        ])
        
        if domain in exclude_domains:
            return False
        
        # Exclude keywords
        exclude_keywords = self.config.settings.get('exclude_keywords', [
            'noreply', 'no-reply', 'donotreply', 'mailer-daemon',
            'postmaster', 'bounce', 'newsletter', 'notification',
            'automated', 'system', 'robot', 'bot'
        ])
        
        if any(keyword in email_lower for keyword in exclude_keywords):
            return False
        
        # Additional filtering for common patterns
        import re
        if re.match(r'^(noreply|no-reply|donotreply)', email_lower):
            return False
        
        return True
    
    def _normalize_contact_data(self, raw_contact: Dict[str, Any]) -> Contact:
        """
        Normalize raw contact data into unified Contact model
        Can be overridden by specific providers for custom fields
        """
        # Extract basic information
        email = raw_contact.get('email', '').lower().strip()
        name = raw_contact.get('name', '').strip()
        
        if not email:
            raise ValueError("Contact must have an email address")
        
        # Create contact with provider-specific information
        contact = Contact(
            email=email,
            name=name,
            provider=self.provider_type,
            provider_contact_id=raw_contact.get('provider_id'),
            account_id=raw_contact.get('account_id')
        )
        
        # Add any additional fields from raw data
        if 'job_title' in raw_contact:
            contact.job_title = raw_contact['job_title']
        if 'company' in raw_contact:
            contact.company = raw_contact['company']
        if 'location' in raw_contact:
            contact.location = raw_contact['location']
        
        return contact
    
    async def _handle_provider_error(self, error: Exception, context: str = "") -> None:
        """
        Handle provider-specific errors and convert to standard exceptions
        """
        self.logger.error(f"Provider error in {context}: {error}")
        
        error_message = str(error)
        
        # Map common HTTP status codes
        if hasattr(error, 'status_code'):
            status_code = error.status_code
            if status_code == 401:
                raise AuthenticationError(
                    message=f"Authentication failed for {self.provider_type.value}: {error_message}",
                    provider=self.provider_type.value,
                    original_exception=error
                )
            elif status_code == 429:
                raise RateLimitError(
                    message=f"Rate limit exceeded for {self.provider_type.value}",
                    provider=self.provider_type.value,
                    retry_after=3600
                )
            elif status_code >= 500:
                raise ProviderError(
                    message=f"Server error from {self.provider_type.value}: {error_message}",
                    provider=self.provider_type.value,
                    original_exception=error
                )
        
        # Generic provider error
        raise ProviderError(
            message=f"Error from {self.provider_type.value}: {error_message}",
            provider=self.provider_type.value,
            original_exception=error
        )
    
    def _get_date_range(self, days_back: int) -> Tuple[datetime, datetime]:
        """Get date range for email queries"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        return start_date, end_date
    
    async def refresh_authentication(self) -> bool:
        """
        Refresh authentication if needed
        Default implementation just calls authenticate()
        """
        try:
            return await self.authenticate()
        except Exception as e:
            self.logger.error(f"Failed to refresh authentication: {e}")
            return False
    
    def get_supported_features(self) -> List[str]:
        """
        Get list of features supported by this provider
        Can be overridden by specific providers
        """
        return [
            'extract_contacts',
            'get_email_headers', 
            'search_emails',
            'test_connection'
        ]
    
    def get_rate_limit_info(self) -> Dict[str, Any]:
        """Get current rate limit information"""
        return {
            'daily_limit': self.config.rate_limits.get('daily', 10000),
            'remaining_calls': self.rate_limit_remaining,
            'calls_made_today': self.api_calls_today,
            'reset_time': datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        }
    
    async def validate_config(self) -> bool:
        """
        Validate provider configuration
        Should be called before using the provider
        """
        try:
            # Check required credentials
            required_creds = self._get_required_credentials()
            for cred in required_creds:
                if cred not in self.config.credentials:
                    raise ValueError(f"Missing required credential: {cred}")
            
            # Test authentication
            if not await self.authenticate():
                return False
            
            # Test connection
            if not await self.test_connection():
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Config validation failed: {e}")
            return False
    
    @abstractmethod
    def _get_required_credentials(self) -> List[str]:
        """
        Get list of required credential keys for this provider
        Must be implemented by each provider
        """
        pass
    
    def __str__(self):
        return f"{self.__class__.__name__}(provider={self.provider_type.value}, authenticated={self.is_authenticated})"
    
    def __repr__(self):
        return self.__str__()