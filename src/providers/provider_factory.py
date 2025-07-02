# """
# Provider factory for managing email providers
# """

# import sys
# import os
# from typing import Dict, List, Optional, Type, Any
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# import json
# import logging
# from pathlib import Path
# from typing import Dict, List, Optional, Type

# from core.models import EmailProvider, Contact, ProviderStatus
# from core.exceptions import ProviderError, ConfigurationError
# from providers.base_provider import BaseEmailProvider, ProviderConfig

# class ProviderFactory:
#     _provider_classes: Dict[EmailProvider, Type[BaseEmailProvider]] = {}
    
#     def __init__(self, config_dir: Path = None):
#         self.config_dir = config_dir or Path("config")
#         self.logger = logging.getLogger(__name__)
#         self._active_providers: Dict[str, BaseEmailProvider] = {}
#         self._provider_configs: Dict[str, ProviderConfig] = {}
    
#     def load_provider_configs(self) -> Dict[str, ProviderConfig]:
#         """Load basic Gmail configuration"""
#         configs = {}
        
#         # Check for Gmail credentials
#         gmail_creds = self.config_dir / "gmail_credentials.json"
#         if gmail_creds.exists():
#             config = ProviderConfig(
#                 provider_type=EmailProvider.GMAIL,
#                 credentials={"credentials_file": str(gmail_creds)},
#                 settings={"token_file": "data/tokens/gmail_token.json"},
#                 rate_limits={"daily": 1000000, "hourly": 250000}
#             )
#             configs["gmail"] = config
            
#         self._provider_configs = configs
#         return configs
    
#     async def create_provider(self, provider_id: str, config: ProviderConfig = None) -> BaseEmailProvider:
#         """Create a basic provider (Gmail only for now)"""
#         if provider_id == "gmail":
#             # Import Gmail provider dynamically
#             try:
#                 from providers.gmail_provider import GmailProvider
#                 provider = GmailProvider(config or self._provider_configs[provider_id])
#                 self._active_providers[provider_id] = provider
#                 return provider
#             except ImportError:
#                 # Fallback to mock provider
#                 return MockGmailProvider(config or self._provider_configs[provider_id])
        
#         raise ProviderError(f"Provider {provider_id} not supported yet")
    
#     def list_providers(self) -> List[str]:
#         return list(self._provider_configs.keys())
    
#     async def extract_contacts_from_all_providers(self, days_back: int = 30, max_emails: int = 1000) -> Dict[str, List[Contact]]:
#         results = {}
#         for provider_id, provider in self._active_providers.items():
#             try:
#                 contacts = await provider.extract_contacts(days_back, max_emails)
#                 results[provider_id] = contacts
#             except Exception as e:
#                 self.logger.error(f"Failed to extract from {provider_id}: {e}")
#                 results[provider_id] = []
#         return results
    
#     def merge_contacts_from_providers(self, provider_contacts: Dict[str, List[Contact]]) -> List[Contact]:
#         all_contacts = []
#         for contacts in provider_contacts.values():
#             all_contacts.extend(contacts)
#         return all_contacts
    
#     async def cleanup_all_providers(self):
#         for provider in self._active_providers.values():
#             if hasattr(provider, 'close'):
#                 await provider.close()

# class MockGmailProvider(BaseEmailProvider):
#     """Mock provider for testing"""
    
#     async def authenticate(self) -> bool:
#         self.is_authenticated = True
#         return True
    
#     async def test_connection(self) -> bool:
#         return self.is_authenticated
    
#     async def get_account_info(self) -> Dict[str, Any]:
#         return {"email": "test@gmail.com", "provider": "mock"}
    
#     async def extract_contacts(self, days_back: int = 30, max_emails: int = 1000, account_id: Optional[str] = None) -> List[Contact]:
#         # Return some mock contacts
#         return [
#             Contact(
#                 email="john.doe@example.com",
#                 name="John Doe",
#                 provider=EmailProvider.GMAIL,
#                 frequency=5,
#                 location="San Francisco, CA",
#                 estimated_net_worth="$250K - $500K"
#             ),
#             Contact(
#                 email="jane.smith@company.com", 
#                 name="Jane Smith",
#                 provider=EmailProvider.GMAIL,
#                 frequency=3,
#                 location="New York, NY",
#                 estimated_net_worth="$500K - $1M"
#             )
#         ]

# _provider_factory_instance = None

# def get_provider_factory(config_dir: Path = None) -> ProviderFactory:
#     global _provider_factory_instance
#     if _provider_factory_instance is None:
#         _provider_factory_instance = ProviderFactory(config_dir)
#     return _provider_factory_instance
"""
Provider factory for managing email providers - COMPLETE FIXED VERSION
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Type, Any

from core.models import EmailProvider, Contact, ProviderStatus
from core.exceptions import ProviderError, ConfigurationError
from providers.base_provider import BaseEmailProvider, ProviderConfig

class ProviderFactory:
    """Factory for creating and managing email providers"""
    
    # Class-level registry of provider classes
    _provider_classes: Dict[EmailProvider, Type[BaseEmailProvider]] = {}
    
    def __init__(self, config_dir: Path = None):
        self.config_dir = config_dir or Path("config")
        self.logger = logging.getLogger(__name__)
        self._active_providers: Dict[str, BaseEmailProvider] = {}
        self._provider_configs: Dict[str, ProviderConfig] = {}
    
    @classmethod
    def register_provider(cls, provider_type: EmailProvider, provider_class: Type[BaseEmailProvider]):
        """Register a new provider class - CLASS METHOD"""
        cls._provider_classes[provider_type] = provider_class
        logging.getLogger(__name__).debug(f"Registered provider: {provider_type.value}")
    
    def load_provider_configs(self) -> Dict[str, ProviderConfig]:
        """Load provider configurations from files"""
        configs = {}
        
        try:
            # Check for Gmail credentials
            gmail_creds = self.config_dir / "gmail_credentials.json"
            if gmail_creds.exists():
                config = ProviderConfig(
                    provider_type=EmailProvider.GMAIL,
                    credentials={"credentials_file": str(gmail_creds)},
                    settings={
                        "token_file": "data/tokens/gmail_token.json",
                        "exclude_domains": ["noreply.gmail.com", "mail-noreply.google.com"],
                        "exclude_keywords": ["noreply", "no-reply", "donotreply"]
                    },
                    rate_limits={"daily": 1000000, "hourly": 250000, "per_minute": 250}
                )
                configs["gmail"] = config
                self.logger.info("Found Gmail credentials file")
            else:
                self.logger.warning(f"Gmail credentials not found at: {gmail_creds}")
            
            # Check for Outlook credentials (environment variables)
            outlook_client_id = os.getenv('OUTLOOK_CLIENT_ID')
            outlook_client_secret = os.getenv('OUTLOOK_CLIENT_SECRET')
            
            if outlook_client_id and outlook_client_secret:
                config = ProviderConfig(
                    provider_type=EmailProvider.OUTLOOK,
                    credentials={
                        "client_id": outlook_client_id,
                        "client_secret": outlook_client_secret,
                        "tenant_id": os.getenv('OUTLOOK_TENANT_ID', 'common')
                    },
                    settings={
                        "token_file": "data/tokens/outlook_token.json",
                        "redirect_uri": "http://localhost:8080/auth/callback"
                    },
                    rate_limits={"daily": 10000, "hourly": 1000, "per_minute": 60}
                )
                configs["outlook"] = config
                self.logger.info("Found Outlook credentials in environment")
            
            # Check for Yahoo credentials
            yahoo_email = os.getenv('YAHOO_EMAIL')
            yahoo_password = os.getenv('YAHOO_APP_PASSWORD')
            
            if yahoo_email and yahoo_password:
                config = ProviderConfig(
                    provider_type=EmailProvider.YAHOO,
                    credentials={
                        "email": yahoo_email,
                        "password": yahoo_password
                    },
                    settings={
                        "provider": "yahoo",
                        "protocol": "imap",
                        "imap_server": "imap.mail.yahoo.com",
                        "imap_port": 993,
                        "use_ssl": True
                    },
                    rate_limits={"daily": 5000, "hourly": 500, "per_minute": 30}
                )
                configs["yahoo"] = config
                self.logger.info("Found Yahoo credentials in environment")
            
        except Exception as e:
            self.logger.error(f"Error loading provider configs: {e}")
        
        self._provider_configs = configs
        return configs
    
    async def create_provider(self, provider_id: str, config: ProviderConfig = None) -> BaseEmailProvider:
        """Create a provider instance"""
        
        if not config:
            if provider_id not in self._provider_configs:
                raise ConfigurationError(f"No configuration found for provider: {provider_id}")
            config = self._provider_configs[provider_id]
        
        provider_type = config.provider_type
        
        # Try to get registered provider class
        provider_class = self._provider_classes.get(provider_type)
        
        if provider_class:
            # Use registered provider
            self.logger.info(f"Using registered provider for {provider_type.value}")
            provider = provider_class(config)
        else:
            # Fallback logic for each provider type
            if provider_type == EmailProvider.GMAIL:
                try:
                    # Try to import real Gmail provider
                    from providers.gmail_provider import GmailProvider
                    provider = GmailProvider(config)
                    self.logger.info("Using real Gmail provider")
                except ImportError as e:
                    self.logger.warning(f"Could not import Gmail provider: {e}")
                    provider = MockGmailProvider(config)
                    self.logger.info("Using mock Gmail provider")
            
            elif provider_type == EmailProvider.OUTLOOK:
                try:
                    from providers.outlook_provider import OutlookProvider
                    provider = OutlookProvider(config)
                    self.logger.info("Using real Outlook provider")
                except ImportError as e:
                    self.logger.warning(f"Could not import Outlook provider: {e}")
                    provider = MockProvider(config, "Outlook")
            
            elif provider_type in [EmailProvider.YAHOO, EmailProvider.IMAP, EmailProvider.ICLOUD]:
                try:
                    from providers.imap_provider import IMAPProvider
                    provider = IMAPProvider(config)
                    self.logger.info(f"Using real IMAP provider for {provider_type.value}")
                except ImportError as e:
                    self.logger.warning(f"Could not import IMAP provider: {e}")
                    provider = MockProvider(config, provider_type.value)
            
            else:
                raise ProviderError(f"Unsupported provider type: {provider_type}")
        
        # Store and return the provider
        self._active_providers[provider_id] = provider
        self.logger.info(f"Created provider: {provider_id}")
        return provider
    
    def list_providers(self) -> List[str]:
        """List all configured providers"""
        return list(self._provider_configs.keys())
    
    def list_active_providers(self) -> List[str]:
        """List all active provider instances"""
        return list(self._active_providers.keys())
    
    async def get_provider(self, provider_id: str) -> Optional[BaseEmailProvider]:
        """Get an active provider instance"""
        return self._active_providers.get(provider_id)
    
    async def extract_contacts_from_all_providers(self, days_back: int = 30, max_emails: int = 1000) -> Dict[str, List[Contact]]:
        """Extract contacts from all active providers"""
        results = {}
        
        for provider_id, provider in self._active_providers.items():
            try:
                self.logger.info(f"Extracting contacts from {provider_id}")
                contacts = await provider.extract_contacts(days_back, max_emails)
                results[provider_id] = contacts
                self.logger.info(f"Extracted {len(contacts)} contacts from {provider_id}")
            except Exception as e:
                self.logger.error(f"Failed to extract contacts from {provider_id}: {e}")
                results[provider_id] = []
        
        return results
    
    def merge_contacts_from_providers(self, provider_contacts: Dict[str, List[Contact]]) -> List[Contact]:
        """Merge and deduplicate contacts from multiple providers"""
        merged_contacts = {}
        
        for provider_id, contacts in provider_contacts.items():
            for contact in contacts:
                email = contact.email.lower()
                
                if email in merged_contacts:
                    # Merge with existing contact
                    existing = merged_contacts[email]
                    
                    # Keep better name
                    if len(contact.name) > len(existing.name):
                        existing.name = contact.name
                    
                    # Merge interaction stats
                    existing.frequency += contact.frequency
                    existing.sent_to += contact.sent_to
                    existing.received_from += contact.received_from
                    existing.cc_count += contact.cc_count
                    existing.bcc_count += contact.bcc_count
                    
                    # Keep better enrichment data
                    if contact.confidence > existing.confidence:
                        existing.location = contact.location
                        existing.estimated_net_worth = contact.estimated_net_worth
                        existing.data_source = contact.data_source
                        existing.confidence = contact.confidence
                else:
                    # Add new contact
                    merged_contacts[email] = contact
        
        # Sort by relationship strength
        contacts_list = list(merged_contacts.values())
        contacts_list.sort(key=lambda c: c.calculate_relationship_strength(), reverse=True)
        
        return contacts_list
    
    async def cleanup_all_providers(self):
        """Cleanup all providers and resources"""
        for provider_id, provider in list(self._active_providers.items()):
            try:
                if hasattr(provider, 'close'):
                    await provider.close()
                del self._active_providers[provider_id]
                self.logger.info(f"Cleaned up provider: {provider_id}")
            except Exception as e:
                self.logger.warning(f"Error cleaning up provider {provider_id}: {e}")

class MockGmailProvider(BaseEmailProvider):
    """Mock Gmail provider for testing"""
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.my_email = "mock@gmail.com"
        self.logger.info("Initialized mock Gmail provider")
    
    async def authenticate(self) -> bool:
        """Mock authentication - always succeeds"""
        self.is_authenticated = True
        self.logger.info("Mock Gmail provider authenticated")
        return True
    
    async def test_connection(self) -> bool:
        """Mock connection test"""
        return self.is_authenticated
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Mock account info"""
        return {
            "email": self.my_email,
            "provider": "mock_gmail",
            "messages_total": 1500,
            "status": "connected (mock)"
        }
    
    async def extract_contacts(self, days_back: int = 30, max_emails: int = 1000, account_id: Optional[str] = None) -> List[Contact]:
        """Generate realistic mock contacts"""
        
        self.logger.info(f"Mock extraction: {days_back} days, {max_emails} emails max")
        
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
            )
        ]
        
        # Return subset based on max_emails
        num_contacts = min(len(mock_contacts), max(1, max_emails // 100))
        return mock_contacts[:num_contacts]

class MockProvider(BaseEmailProvider):
    """Generic mock provider for other types"""
    
    def __init__(self, config: ProviderConfig, provider_name: str):
        super().__init__(config)
        self.provider_name = provider_name
        self.my_email = f"mock@{provider_name.lower()}.com"
    
    async def authenticate(self) -> bool:
        self.is_authenticated = True
        return True
    
    async def test_connection(self) -> bool:
        return self.is_authenticated
    
    async def get_account_info(self) -> Dict[str, Any]:
        return {
            "email": self.my_email,
            "provider": f"mock_{self.provider_name.lower()}",
            "status": "connected (mock)"
        }
    
    async def extract_contacts(self, days_back: int = 30, max_emails: int = 1000, account_id: Optional[str] = None) -> List[Contact]:
        return [
            Contact(
                email=f"test@{self.provider_name.lower()}.com",
                name=f"Test {self.provider_name} Contact",
                provider=self.provider_type,
                frequency=1,
                location="Mock Location",
                estimated_net_worth="$100K - $250K",
                data_source="Mock Data",
                confidence=0.5
            )
        ]

# Singleton instance
_provider_factory_instance = None

def get_provider_factory(config_dir: Path = None) -> ProviderFactory:
    """Get global provider factory instance"""
    global _provider_factory_instance
    if _provider_factory_instance is None:
        _provider_factory_instance = ProviderFactory(config_dir)
    return _provider_factory_instance