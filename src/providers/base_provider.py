
"""
Enhanced Base Email Provider with Multiple Account Support and ProviderConfig
Abstract base class for all email providers with account-specific functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass

from core.models import Contact, EmailProvider, InteractionType, Interaction
from core.exceptions import AuthenticationError, ProviderError, ValidationError

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
    Enhanced base class for all email providers with account support
    """
    
    def __init__(self, account_id: str, email: str, credential_file: str = ""):
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        
        # Account identification
        self.account_id = account_id
        self.email = email
        self.credential_file = credential_file
        
        # Provider configuration
        self.provider_type = self._get_provider_type()
        self.display_name = f"{self.provider_type.title()} ({self.email})"
        
        # Authentication state
        self.is_authenticated = False
        self.auth_token = None
        self.token_expires_at = None
        self.last_auth_check = None
        
        # Rate limiting and performance
        self.last_request_time = datetime.now()
        self.requests_this_hour = 0
        self.rate_limit_per_hour = 1000  # Default rate limit
        
        # Statistics
        self.total_requests = 0
        self.total_contacts_extracted = 0
        self.last_extraction_time = None
        self.last_error = None
        
        # Configuration
        self.max_emails_per_request = 100
        self.request_delay_seconds = 0.1
        
        self.logger.info(f"Initialized provider for {self.display_name}")
    
    @abstractmethod
    def _get_provider_type(self) -> str:
        """Get the provider type identifier"""
        pass
    
    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with the email provider"""
        pass
    
    @abstractmethod
    async def extract_contacts(self, days_back: int = 30, max_emails: int = 1000) -> List[Contact]:
        """Extract contacts from the email provider"""
        pass
    
    @abstractmethod
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        pass
    
    async def test_connection(self) -> bool:
        """Test connection to the provider"""
        try:
            if not self.is_authenticated:
                auth_success = await self.authenticate()
                if not auth_success:
                    return False
            
            account_info = await self.get_account_info()
            return bool(account_info.get('email'))
        
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            self.last_error = str(e)
            return False
    
    async def refresh_authentication(self) -> bool:
        """Refresh authentication if needed"""
        try:
            # Check if token is still valid
            if self.token_expires_at and datetime.now() < self.token_expires_at:
                return True
            
            # Re-authenticate
            self.is_authenticated = False
            return await self.authenticate()
        
        except Exception as e:
            self.logger.error(f"Authentication refresh failed: {e}")
            self.last_error = str(e)
            return False
    
    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits"""
        now = datetime.now()
        
        # Reset hourly counter if needed
        if (now - self.last_request_time).total_seconds() > 3600:
            self.requests_this_hour = 0
        
        # Check if we've exceeded the rate limit
        if self.requests_this_hour >= self.rate_limit_per_hour:
            return False
        
        return True
    
    async def _apply_rate_limit(self):
        """Apply rate limiting delays"""
        if not self._check_rate_limit():
            wait_time = 3600 - (datetime.now() - self.last_request_time).total_seconds()
            if wait_time > 0:
                self.logger.warning(f"Rate limit exceeded, waiting {wait_time:.1f} seconds")
                await asyncio.sleep(wait_time)
        
        # Apply minimum delay between requests
        if self.request_delay_seconds > 0:
            await asyncio.sleep(self.request_delay_seconds)
        
        # Update tracking
        self.last_request_time = datetime.now()
        self.requests_this_hour += 1
        self.total_requests += 1
    
    def _validate_email_address(self, email: str) -> bool:
        """Validate email address format"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def _extract_email_domain(self, email: str) -> str:
        """Extract domain from email address"""
        if '@' in email:
            return email.split('@')[1].lower()
        return ""
    
    def _determine_contact_type(self, email: str, domain: str = None) -> str:
        """Determine contact type based on email domain"""
        if not domain:
            domain = self._extract_email_domain(email)
        
        # Big tech companies
        big_tech_domains = ['google.com', 'apple.com', 'microsoft.com', 'amazon.com', 'meta.com']
        if any(tech_domain in domain for tech_domain in big_tech_domains):
            return 'big_tech'
        
        # Academic institutions
        if domain.endswith('.edu') or 'university' in domain or 'college' in domain:
            return 'academic'
        
        # Government
        if domain.endswith('.gov') or 'government' in domain:
            return 'government'
        
        # Personal email providers
        personal_domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'icloud.com']
        if domain in personal_domains:
            return 'personal'
        
        # Default to business
        return 'business'
    
    def _create_interaction(self, 
                          interaction_type: InteractionType,
                          timestamp: datetime,
                          subject: str = "",
                          message_id: str = "",
                          direction: str = "",
                          content_preview: str = "") -> Interaction:
        """Create an interaction object"""
        return Interaction(
            type=interaction_type,
            timestamp=timestamp,
            subject=subject,
            message_id=message_id,
            direction=direction,
            source_account=self.account_id,
            content_preview=content_preview
        )
    
    def _extract_name_from_sender(self, sender_info: str) -> str:
        """Extract name from sender information"""
        # Handle formats like "John Doe <john@example.com>" or just "john@example.com"
        if '<' in sender_info and '>' in sender_info:
            name_part = sender_info.split('<')[0].strip()
            if name_part and name_part != sender_info:
                return name_part.strip('"\'')
        
        # If no name found, try to infer from email local part
        if '@' in sender_info:
            local_part = sender_info.split('@')[0]
            # Clean up common email patterns
            name = local_part.replace('.', ' ').replace('_', ' ').replace('-', ' ')
            return name.title()
        
        return ""
    
    def _extract_email_from_sender(self, sender_info: str) -> str:
        """Extract email from sender information"""
        if '<' in sender_info and '>' in sender_info:
            start = sender_info.find('<') + 1
            end = sender_info.find('>')
            email = sender_info[start:end].strip()
        else:
            email = sender_info.strip()
        
        # Validate email format
        if self._validate_email_address(email):
            return email.lower()
        
        return ""
    
    def _should_skip_email(self, email: str) -> bool:
        """Determine if an email should be skipped"""
        skip_patterns = [
            'noreply', 'no-reply', 'donotreply', 'do-not-reply',
            'automated', 'notifications', 'newsletter', 'marketing',
            'support@', 'info@', 'admin@', 'webmaster@'
        ]
        
        email_lower = email.lower()
        return any(pattern in email_lower for pattern in skip_patterns)
    
    async def _process_email_batch(self, emails: List[Any], processor_func) -> List[Contact]:
        """Process a batch of emails with rate limiting"""
        contacts = []
        
        for email in emails:
            try:
                # Apply rate limiting
                await self._apply_rate_limit()
                
                # Process individual email
                contact = await processor_func(email)
                if contact:
                    contacts.append(contact)
            
            except Exception as e:
                self.logger.error(f"Failed to process email: {e}")
                continue
        
        return contacts
    
    def _merge_contact_data(self, existing_contact: Contact, new_contact: Contact) -> Contact:
        """Merge data from new contact into existing contact"""
        # Update interaction counts
        existing_contact.frequency += new_contact.frequency
        existing_contact.sent_to += new_contact.sent_to
        existing_contact.received_from += new_contact.received_from
        existing_contact.cc_count += new_contact.cc_count
        existing_contact.bcc_count += new_contact.bcc_count
        
        # Add interactions
        existing_contact.interactions.extend(new_contact.interactions)
        
        # Update timestamps
        existing_contact.first_seen = min(existing_contact.first_seen, new_contact.first_seen)
        existing_contact.last_seen = max(existing_contact.last_seen, new_contact.last_seen)
        
        # Update contact info if missing
        if not existing_contact.name and new_contact.name:
            existing_contact.name = new_contact.name
        
        if not existing_contact.first_name and new_contact.first_name:
            existing_contact.first_name = new_contact.first_name
        
        if not existing_contact.last_name and new_contact.last_name:
            existing_contact.last_name = new_contact.last_name
        
        # Add source account
        existing_contact.add_source_account(self.account_id)
        
        return existing_contact
    
    def _deduplicate_contacts(self, contacts: List[Contact]) -> List[Contact]:
        """Remove duplicate contacts based on email address"""
        unique_contacts = {}
        
        for contact in contacts:
            email_key = contact.email.lower()
            
            if email_key in unique_contacts:
                # Merge with existing contact
                unique_contacts[email_key] = self._merge_contact_data(
                    unique_contacts[email_key], 
                    contact
                )
            else:
                unique_contacts[email_key] = contact
        
        return list(unique_contacts.values())
    
    async def get_extraction_statistics(self) -> Dict[str, Any]:
        """Get statistics about contact extraction"""
        return {
            'account_id': self.account_id,
            'email': self.email,
            'provider_type': self.provider_type,
            'total_requests': self.total_requests,
            'total_contacts_extracted': self.total_contacts_extracted,
            'last_extraction_time': self.last_extraction_time.isoformat() if self.last_extraction_time else None,
            'is_authenticated': self.is_authenticated,
            'requests_this_hour': self.requests_this_hour,
            'rate_limit_per_hour': self.rate_limit_per_hour,
            'last_error': self.last_error
        }
    
    async def update_extraction_statistics(self, contacts_extracted: int):
        """Update extraction statistics"""
        self.total_contacts_extracted += contacts_extracted
        self.last_extraction_time = datetime.now()
        
        self.logger.info(f"Extracted {contacts_extracted} contacts. Total: {self.total_contacts_extracted}")
    
    def get_credential_file_path(self) -> Optional[Path]:
        """Get the credential file path"""
        if self.credential_file:
            return Path(self.credential_file)
        return None
    
    def validate_configuration(self) -> List[str]:
        """Validate provider configuration"""
        errors = []
        
        if not self.account_id:
            errors.append("Account ID is required")
        
        if not self.email or not self._validate_email_address(self.email):
            errors.append("Valid email address is required")
        
        if self.credential_file and not Path(self.credential_file).exists():
            errors.append(f"Credential file not found: {self.credential_file}")
        
        return errors
    
    async def cleanup(self):
        """Cleanup provider resources"""
        try:
            # Reset authentication state
            self.is_authenticated = False
            self.auth_token = None
            self.token_expires_at = None
            
            self.logger.info(f"Cleaned up provider {self.account_id}")
        
        except Exception as e:
            self.logger.error(f"Cleanup failed for {self.account_id}: {e}")
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.display_name})"
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(account_id='{self.account_id}', email='{self.email}')"