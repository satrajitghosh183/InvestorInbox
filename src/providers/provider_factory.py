


"""
Enhanced Provider Factory with Multiple Account Support
Manages creation and lifecycle of email provider instances for multiple accounts
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path

from core.models import EmailProvider, Contact, ProviderAccount, ProviderStatus, parse_provider_account_string
from core.exceptions import ProviderError, ConfigurationError

# Import provider classes with fallbacks
from providers.base_provider import BaseEmailProvider, ProviderConfig

def safe_import_provider(provider_name: str, provider_class_name: str):
    """Safely import a provider class, returning None if not available"""
    try:
        module = __import__(f'providers.{provider_name}', fromlist=[provider_class_name])
        return getattr(module, provider_class_name)
    except (ImportError, AttributeError) as e:
        logging.getLogger(__name__).debug(f"Provider {provider_name} not available: {e}")
        return None

# Try to import provider classes
GmailProvider = safe_import_provider('gmail_provider', 'GmailProvider')
OutlookProvider = safe_import_provider('outlook_provider', 'OutlookProvider')
YahooProvider = safe_import_provider('yahoo_provider', 'YahooProvider')
IMAPProvider = safe_import_provider('imap_provider', 'IMAPProvider')

class MockProvider(BaseEmailProvider):
    """Mock provider for testing when real providers aren't available"""
    
    def __init__(self, account_id: str, email: str, credential_file: str = "", provider_type: str = "mock"):
        super().__init__(account_id, email, credential_file)
        self._provider_type = provider_type
    
    def _get_provider_type(self) -> str:
        return self._provider_type
    
    async def authenticate(self) -> bool:
        self.is_authenticated = True
        return True
    
    async def get_account_info(self) -> Dict[str, Any]:
        return {
            'email': self.email,
            'provider_type': self.provider_type,
            'status': 'mock_provider'
        }
    
    async def extract_contacts(self, days_back: int = 30, max_emails: int = 1000) -> List[Contact]:
        # Return some mock contacts
        from core.models import Contact, EmailProvider, ContactType
        
        mock_contacts = [
            Contact(
                email="john.doe@example.com",
                name="John Doe",
                provider=EmailProvider.GMAIL,
                contact_type=ContactType.BUSINESS,
                frequency=5,
                sent_to=3,
                received_from=2,
                location="San Francisco, CA",
                estimated_net_worth="$250K - $500K",
                job_title="Software Engineer",
                company="Example Corp",
                data_source="Mock Data",
                confidence=0.8
            ),
            Contact(
                email="jane.smith@company.com",
                name="Jane Smith",
                provider=EmailProvider.GMAIL,
                contact_type=ContactType.BUSINESS,
                frequency=8,
                sent_to=4,
                received_from=4,
                location="New York, NY",
                estimated_net_worth="$500K - $1M",
                job_title="Product Manager",
                company="TechCorp",
                data_source="Mock Data",
                confidence=0.9
            )
        ]
        
        # Add source account
        for contact in mock_contacts:
            contact.add_source_account(self.account_id)
        
        return mock_contacts

class EnhancedProviderFactory:
    """
    Enhanced provider factory that manages multiple accounts per provider
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Active provider instances
        self.active_providers: Dict[str, BaseEmailProvider] = {}
        
        # Provider class mappings
        self.provider_classes = {
            EmailProvider.GMAIL: GmailProvider,
            EmailProvider.OUTLOOK: OutlookProvider,
            EmailProvider.YAHOO: YahooProvider,
            EmailProvider.ICLOUD: IMAPProvider,  # iCloud uses IMAP
            EmailProvider.IMAP: IMAPProvider,
            EmailProvider.OTHER: IMAPProvider
        }
        
        # Remove None values (providers that couldn't be imported)
        self.provider_classes = {k: v for k, v in self.provider_classes.items() if v is not None}
    
    def load_provider_configs(self) -> Dict[str, Any]:
        """Load provider configurations from available sources"""
        configs = {}
        
        try:
            # Check for Gmail credentials
            gmail_creds = Path("config/gmail_credentials.json")
            if gmail_creds.exists() or any(Path("config").glob("gmail_*_credentials.json")):
                configs["gmail"] = {
                    'enabled': True,
                    'type': 'oauth2',
                    'accounts': []
                }
                
                # Find all Gmail credential files
                for cred_file in Path("config").glob("gmail_*_credentials.json"):
                    if cred_file.name != "gmail_credentials.json":
                        # Extract email from filename
                        email = self._extract_email_from_filename(cred_file.name)
                        if email:
                            configs["gmail"]['accounts'].append(email)
                
                if gmail_creds.exists():
                    configs["gmail"]['accounts'].append("primary")
            
            # Check for Outlook credentials
            outlook_client_id = os.getenv('OUTLOOK_CLIENT_ID')
            outlook_client_secret = os.getenv('OUTLOOK_CLIENT_SECRET')
            
            if outlook_client_id and outlook_client_secret:
                configs["outlook"] = {
                    'enabled': True,
                    'type': 'oauth2',
                    'client_id': outlook_client_id,
                    'accounts': ['primary']  # Could be multiple in the future
                }
            
            # Check for Yahoo credentials
            yahoo_email = os.getenv('YAHOO_EMAIL')
            yahoo_password = os.getenv('YAHOO_APP_PASSWORD')
            
            if yahoo_email and yahoo_password:
                configs["yahoo"] = {
                    'enabled': True,
                    'type': 'app_password',
                    'email': yahoo_email,
                    'accounts': [yahoo_email]
                }
            
            # Check for iCloud credentials
            icloud_email = os.getenv('ICLOUD_EMAIL')
            icloud_password = os.getenv('ICLOUD_APP_PASSWORD')
            
            if icloud_email and icloud_password:
                configs["icloud"] = {
                    'enabled': True,
                    'type': 'app_password',
                    'email': icloud_email,
                    'accounts': [icloud_email]
                }
        
        except Exception as e:
            self.logger.error(f"Error loading provider configs: {e}")
        
        return configs
    
    def _extract_email_from_filename(self, filename: str) -> Optional[str]:
        """Extract email from credential filename"""
        # Pattern: gmail_email@domain.com_credentials.json
        import re
        pattern = r'gmail_([^_]+@[^_]+)_credentials\.json'
        match = re.match(pattern, filename)
        return match.group(1) if match else None
    
    async def create_provider_for_account(self, provider_type: str, email: str, credential_file: str = "") -> BaseEmailProvider:
        """Create a provider instance for a specific account"""
        try:
            # Generate account ID
            account_id = f"{provider_type}_{email.replace('@', '_').replace('.', '_')}"
            
            # Get provider class
            email_provider_enum = getattr(EmailProvider, provider_type.upper(), EmailProvider.OTHER)
            provider_class = self.provider_classes.get(email_provider_enum)
            
            if provider_class:
                # Create real provider instance
                provider = provider_class(
                    account_id=account_id,
                    email=email,
                    credential_file=credential_file
                )
            else:
                # Create mock provider
                self.logger.warning(f"Real provider for {provider_type} not available, using mock")
                provider = MockProvider(
                    account_id=account_id,
                    email=email,
                    credential_file=credential_file,
                    provider_type=provider_type
                )
            
            self.logger.info(f"Created provider instance for {email} ({provider_type})")
            return provider
        
        except Exception as e:
            self.logger.error(f"Failed to create provider for {email}: {e}")
            raise ProviderError(f"Provider creation failed: {e}")
    
    async def create_providers_from_request(self, provider_accounts_str: str) -> Dict[str, List[BaseEmailProvider]]:
        """
        Create provider instances from CLI request string
        
        Args:
            provider_accounts_str: String like "gmail=john@example.com,jane@gmail.com outlook=jane@company.com"
        
        Returns:
            Dict mapping provider names to lists of provider instances
        """
        try:
            # Parse the request string
            requested_accounts = parse_provider_account_string(provider_accounts_str)
            
            if not requested_accounts:
                raise ConfigurationError("Invalid provider accounts string format")
            
            # Get available configs
            available_configs = self.load_provider_configs()
            
            # Create provider instances
            providers = {}
            
            for provider_name, emails in requested_accounts.items():
                if provider_name not in available_configs:
                    self.logger.warning(f"Provider {provider_name} not configured")
                    continue
                
                provider_instances = []
                config = available_configs[provider_name]
                
                for email in emails:
                    if email == 'all':
                        # Use all available accounts for this provider
                        available_emails = config.get('accounts', [])
                        for available_email in available_emails:
                            try:
                                # Find credential file
                                credential_file = self._find_credential_file(provider_name, available_email)
                                provider = await self.create_provider_for_account(
                                    provider_name, available_email, credential_file
                                )
                                provider_instances.append(provider)
                                self.active_providers[provider.account_id] = provider
                            except Exception as e:
                                self.logger.error(f"Failed to create provider for {available_email}: {e}")
                    else:
                        try:
                            # Find credential file
                            credential_file = self._find_credential_file(provider_name, email)
                            provider = await self.create_provider_for_account(
                                provider_name, email, credential_file
                            )
                            provider_instances.append(provider)
                            self.active_providers[provider.account_id] = provider
                        except Exception as e:
                            self.logger.error(f"Failed to create provider for {email}: {e}")
                
                if provider_instances:
                    providers[provider_name] = provider_instances
            
            self.logger.info(f"Created {sum(len(instances) for instances in providers.values())} provider instances")
            return providers
        
        except Exception as e:
            self.logger.error(f"Failed to create providers from request: {e}")
            raise
    
    def _find_credential_file(self, provider_name: str, email: str) -> str:
        """Find credential file for provider and email"""
        if provider_name == "gmail":
            # Look for specific credential file
            specific_file = Path(f"config/gmail_{email}_credentials.json")
            if specific_file.exists():
                return str(specific_file)
            
            # Fall back to generic file
            generic_file = Path("config/gmail_credentials.json")
            if generic_file.exists():
                return str(generic_file)
        
        return ""
    
    async def get_all_available_providers(self) -> Dict[str, List[BaseEmailProvider]]:
        """Get provider instances for all discovered accounts"""
        try:
            available_configs = self.load_provider_configs()
            providers = {}
            
            for provider_name, config in available_configs.items():
                provider_instances = []
                accounts = config.get('accounts', [])
                
                for account in accounts:
                    try:
                        account_id = f"{provider_name}_{account.replace('@', '_').replace('.', '_')}"
                        
                        # Check if provider already exists
                        if account_id in self.active_providers:
                            provider_instances.append(self.active_providers[account_id])
                        else:
                            credential_file = self._find_credential_file(provider_name, account)
                            provider = await self.create_provider_for_account(
                                provider_name, account, credential_file
                            )
                            provider_instances.append(provider)
                            self.active_providers[account_id] = provider
                    
                    except Exception as e:
                        self.logger.error(f"Failed to create provider for {account}: {e}")
                        continue
                
                if provider_instances:
                    providers[provider_name] = provider_instances
            
            return providers
        
        except Exception as e:
            self.logger.error(f"Failed to get all available providers: {e}")
            return {}
    
    async def create_provider(self, provider_id: str) -> BaseEmailProvider:
        """
        Create a single provider instance (legacy method for backward compatibility)
        """
        try:
            # Check if this is an account ID
            if provider_id in self.active_providers:
                return self.active_providers[provider_id]
            
            # Check if it's a provider name - get first available account
            configs = self.load_provider_configs()
            if provider_id not in configs:
                raise ConfigurationError(f"No configuration found for provider {provider_id}")
            
            config = configs[provider_id]
            accounts = config.get('accounts', [])
            
            if not accounts:
                raise ConfigurationError(f"No accounts configured for provider {provider_id}")
            
            # Use the first account
            first_account = accounts[0]
            credential_file = self._find_credential_file(provider_id, first_account)
            
            return await self.create_provider_for_account(provider_id, first_account, credential_file)
        
        except Exception as e:
            self.logger.error(f"Failed to create provider {provider_id}: {e}")
            raise
    
    async def test_provider_connection(self, provider: BaseEmailProvider) -> Dict[str, Any]:
        """Test connection for a specific provider"""
        try:
            start_time = datetime.now()
            
            # Test authentication
            auth_success = await provider.authenticate()
            
            if not auth_success:
                return {
                    'success': False,
                    'error': 'Authentication failed',
                    'provider': provider.account_id,
                    'email': getattr(provider, 'email', 'Unknown')
                }
            
            # Test connection
            connection_success = await provider.test_connection()
            
            # Get account info
            account_info = await provider.get_account_info()
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                'success': auth_success and connection_success,
                'provider': provider.account_id,
                'email': account_info.get('email', 'Unknown'),
                'account_info': account_info,
                'processing_time': processing_time,
                'authenticated': auth_success,
                'connection_test': connection_success
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'provider': getattr(provider, 'account_id', 'Unknown'),
                'email': getattr(provider, 'email', 'Unknown')
            }
    
    async def test_all_providers(self, providers: Dict[str, List[BaseEmailProvider]]) -> Dict[str, List[Dict[str, Any]]]:
        """Test connections for all providers"""
        results = {}
        
        for provider_name, provider_instances in providers.items():
            provider_results = []
            
            for provider in provider_instances:
                result = await self.test_provider_connection(provider)
                provider_results.append(result)
            
            results[provider_name] = provider_results
        
        return results
    
    async def extract_contacts_from_providers(self, 
                                           providers: Dict[str, List[BaseEmailProvider]],
                                           days_back: int = 30,
                                           max_emails: int = 1000) -> Dict[str, List[Contact]]:
        """Extract contacts from multiple provider instances"""
        all_contacts = {}
        
        for provider_name, provider_instances in providers.items():
            provider_contacts = []
            
            for provider in provider_instances:
                try:
                    self.logger.info(f"Extracting contacts from {provider.account_id}...")
                    
                    # Authenticate first
                    if not await provider.authenticate():
                        self.logger.error(f"Authentication failed for {provider.account_id}")
                        continue
                    
                    # Extract contacts
                    contacts = await provider.extract_contacts(
                        days_back=days_back,
                        max_emails=max_emails
                    )
                    
                    # Add source account information to each contact
                    for contact in contacts:
                        contact.add_source_account(provider.account_id)
                        
                        # Add to interactions
                        for interaction in contact.interactions:
                            interaction.source_account = provider.account_id
                    
                    provider_contacts.extend(contacts)
                    self.logger.info(f"Extracted {len(contacts)} contacts from {provider.account_id}")
                
                except Exception as e:
                    self.logger.error(f"Contact extraction failed for {provider.account_id}: {e}")
                    continue
            
            if provider_contacts:
                all_contacts[provider_name] = provider_contacts
        
        return all_contacts
    
    def merge_contacts_from_providers(self, provider_contacts: Dict[str, List[Contact]]) -> List[Contact]:
        """Merge contacts from multiple providers, handling duplicates"""
        try:
            # Collect all contacts
            all_contacts = []
            for contacts in provider_contacts.values():
                all_contacts.extend(contacts)
            
            if not all_contacts:
                return []
            
            # Group contacts by email address
            email_groups = defaultdict(list)
            for contact in all_contacts:
                if contact.email:
                    email_groups[contact.email.lower()].append(contact)
            
            # Merge duplicate contacts
            merged_contacts = []
            
            for email, contact_group in email_groups.items():
                if len(contact_group) == 1:
                    merged_contacts.append(contact_group[0])
                else:
                    # Merge multiple contacts for the same email
                    merged_contact = self._merge_contact_group(contact_group)
                    merged_contacts.append(merged_contact)
            
            # Sort by relationship strength
            merged_contacts.sort(key=lambda c: c.calculate_relationship_strength(), reverse=True)
            
            self.logger.info(f"Merged {len(all_contacts)} contacts into {len(merged_contacts)} unique contacts")
            return merged_contacts
        
        except Exception as e:
            self.logger.error(f"Contact merging failed: {e}")
            return all_contacts
    
    def _merge_contact_group(self, contacts: List[Contact]) -> Contact:
        """Merge a group of contacts with the same email address"""
        if not contacts:
            return Contact()
        
        if len(contacts) == 1:
            return contacts[0]
        
        # Start with the contact that has the most interactions
        primary = max(contacts, key=lambda c: c.frequency)
        
        # Merge data from all other contacts
        for contact in contacts:
            if contact == primary:
                continue
            
            # Merge source accounts
            for account_id in contact.source_accounts:
                primary.add_source_account(account_id)
            
            # Merge account stats
            for account_id, stats in contact.account_stats.items():
                if account_id not in primary.account_stats:
                    primary.account_stats[account_id] = stats
                else:
                    # Sum the stats
                    for stat_key, value in stats.items():
                        primary.account_stats[account_id][stat_key] = primary.account_stats[account_id].get(stat_key, 0) + value
            
            # Merge interactions
            primary.interactions.extend(contact.interactions)
            
            # Merge other data (take non-empty values)
            for field in ['name', 'first_name', 'last_name', 'job_title', 'company', 'location', 'estimated_net_worth']:
                if not getattr(primary, field) and getattr(contact, field):
                    setattr(primary, field, getattr(contact, field))
            
            # Merge lists
            primary.phone_numbers.extend(contact.phone_numbers)
            primary.alternative_emails.extend(contact.alternative_emails)
            primary.tags.extend(contact.tags)
            primary.data_sources.extend(contact.data_sources)
            primary.social_profiles.extend(contact.social_profiles)
            
            # Update numerical fields
            primary.frequency += contact.frequency
            primary.sent_to += contact.sent_to
            primary.received_from += contact.received_from
            primary.cc_count += contact.cc_count
            primary.bcc_count += contact.bcc_count
            primary.meeting_count += contact.meeting_count
            primary.call_count += contact.call_count
            
            # Update timestamps
            primary.first_seen = min(primary.first_seen, contact.first_seen)
            primary.last_seen = max(primary.last_seen, contact.last_seen)
            
            # Take higher confidence
            primary.confidence = max(primary.confidence, contact.confidence)
        
        # Remove duplicates from lists
        primary.phone_numbers = list(set(primary.phone_numbers))
        primary.alternative_emails = list(set(primary.alternative_emails))
        primary.tags = list(set(primary.tags))
        primary.data_sources = list(set(primary.data_sources))
        
        # Sort interactions by timestamp
        primary.interactions.sort(key=lambda i: i.timestamp)
        
        return primary
    
    async def cleanup_provider(self, account_id: str):
        """Cleanup a specific provider instance"""
        if account_id in self.active_providers:
            try:
                provider = self.active_providers[account_id]
                if hasattr(provider, 'cleanup'):
                    await provider.cleanup()
                del self.active_providers[account_id]
                self.logger.info(f"Cleaned up provider {account_id}")
            except Exception as e:
                self.logger.error(f"Failed to cleanup provider {account_id}: {e}")
    
    async def cleanup_all_providers(self):
        """Cleanup all active provider instances"""
        cleanup_tasks = []
        
        for account_id in list(self.active_providers.keys()):
            cleanup_tasks.append(self.cleanup_provider(account_id))
        
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        self.active_providers.clear()
        self.logger.info("Cleaned up all provider instances")
    
    def get_active_provider_summary(self) -> Dict[str, Any]:
        """Get summary of active providers"""
        summary = {
            'total_providers': len(self.active_providers),
            'providers_by_type': defaultdict(int),
            'accounts': []
        }
        
        for account_id, provider in self.active_providers.items():
            provider_type = getattr(provider, 'provider_type', 'unknown')
            email = getattr(provider, 'email', 'unknown')
            
            summary['providers_by_type'][provider_type] += 1
            summary['accounts'].append({
                'account_id': account_id,
                'provider_type': provider_type,
                'email': email
            })
        
        return summary
    
    def get_provider_by_account_id(self, account_id: str) -> Optional[BaseEmailProvider]:
        """Get provider instance by account ID"""
        return self.active_providers.get(account_id)
    
    def get_providers_by_type(self, provider_type: str) -> List[BaseEmailProvider]:
        """Get all provider instances of a specific type"""
        providers = []
        
        for provider in self.active_providers.values():
            if getattr(provider, 'provider_type', '') == provider_type:
                providers.append(provider)
        
        return providers


# Global factory instance
_provider_factory = None

def get_provider_factory() -> EnhancedProviderFactory:
    """Get the global provider factory instance"""
    global _provider_factory
    if _provider_factory is None:
        _provider_factory = EnhancedProviderFactory()
    return _provider_factory

def reset_provider_factory():
    """Reset the global provider factory (useful for testing)"""
    global _provider_factory
    if _provider_factory:
        # Cleanup providers if factory exists
        import asyncio
        asyncio.create_task(_provider_factory.cleanup_all_providers())
    _provider_factory = None