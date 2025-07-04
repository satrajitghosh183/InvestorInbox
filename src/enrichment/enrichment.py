
"""
Contact Enrichment Engine - Fixed Version
Handles contact enrichment using multiple data sources
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import time
from pathlib import Path

from core.models import Contact, EnrichmentSource
from core.exceptions import EnrichmentError

class EnrichmentCache:
    """Simple in-memory cache for enrichment results"""
    
    def __init__(self, ttl_hours: int = 24):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl_hours = ttl_hours
        self.logger = logging.getLogger(__name__)
    
    def get(self, email: str) -> Optional[Dict[str, Any]]:
        """Get cached enrichment data for email"""
        if email in self.cache:
            cache_entry = self.cache[email]
            cache_time = cache_entry.get('timestamp', 0)
            
            # Check if cache is still valid
            if time.time() - cache_time < (self.ttl_hours * 3600):
                return cache_entry.get('data')
            else:
                # Remove expired entry
                del self.cache[email]
        
        return None
    
    def set(self, email: str, data: Dict[str, Any]):
        """Cache enrichment data for email"""
        self.cache[email] = {
            'data': data,
            'timestamp': time.time()
        }
    
    def clear(self):
        """Clear all cache entries"""
        self.cache.clear()
    
    def size(self) -> int:
        """Get cache size"""
        return len(self.cache)

class EnrichmentResult:
    """Result of contact enrichment operation"""
    
    def __init__(self, 
                 success: bool = False,
                 contact: Optional[Contact] = None,
                 source: Optional[EnrichmentSource] = None,
                 data_added: Optional[Dict[str, Any]] = None,
                 error_message: Optional[str] = None,
                 confidence: float = 0.0,
                 cost: float = 0.0,
                 processing_time: float = 0.0,
                 api_calls_used: int = 0):
        self.success = success
        self.contact = contact
        self.source = source
        self.data_added = data_added or {}
        self.error_message = error_message
        self.confidence = confidence
        self.cost = cost
        self.processing_time = processing_time
        self.api_calls_used = api_calls_used
        self.timestamp = datetime.now()

class ContactEnricher:
    """
    Main contact enrichment engine
    Coordinates multiple enrichment sources and manages caching
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.cache = EnrichmentCache()
        self.sources = {}
        self.total_cost = 0.0
        self.total_api_calls = 0
        
        # Initialize available sources
        self._initialize_sources()
    
    # def _initialize_sources(self):
    #     """Initialize available enrichment sources"""
    #     # Try to import sources, but don't fail if they're not available
        
    #     # Domain inference (always available)
    #     self.sources['domain_inference'] = self._create_domain_inference_source()
        
    #     # Try to import other sources
    #     try:
    #         from enrichment.sources.clearbit_source import ClearbitEnrichmentSource
    #         self.sources['clearbit'] = ClearbitEnrichmentSource()
    #     except ImportError:
    #         self.logger.debug("Clearbit source not available")
        
    #     try:
    #         from enrichment.sources.hunter_source import HunterIOSource
    #         self.sources['hunter'] = HunterIOSource()
    #     except ImportError:
    #         self.logger.debug("Hunter source not available")
        
    #     try:
    #         from enrichment.sources.peopledatalabs_source import PeopleDataLabsSource
    #         self.sources['peopledatalabs'] = PeopleDataLabsSource()
    #     except ImportError:
    #         self.logger.debug("People Data Labs source not available")
        
    #     self.logger.info(f"Initialized {len(self.sources)} enrichment sources")

    def _initialize_sources(self):
        """Initialize available enrichment sources"""
        self.logger.info("Initializing enrichment sources...")

        # Domain inference (always available)
        self.sources['domain_inference'] = self._create_domain_inference_source()

        try:
            from enrichment.sources.clearbit_source import ClearbitEnrichmentSource
            from config.config_manager import get_config_manager
            config = get_config_manager().get_source_config("clearbit")
            if config.get("enabled", False):
                self.sources['clearbit'] = ClearbitEnrichmentSource()
        except ImportError:
            self.logger.debug("Clearbit source not available")
        except Exception as e:
            self.logger.warning(f"Failed to initialize Clearbit source: {e}")

        try:
            from enrichment.sources.hunter_source import HunterIOSource
            from config.config_manager import get_config_manager
            config = get_config_manager().get_source_config("hunter")
            if config.get("enabled", False):
                self.sources['hunter'] = HunterIOSource()
        except ImportError:
            self.logger.debug("Hunter source not available")
        except Exception as e:
            self.logger.warning(f"Failed to initialize Hunter source: {e}")

        try:
            from enrichment.sources.peopledatalabs_source import PeopleDataLabsSource
            from config.config_manager import get_config_manager
            config = get_config_manager().get_source_config("peopledatalabs")
            if config.get("enabled", False):
                self.sources['peopledatalabs'] = PeopleDataLabsSource()
        except ImportError:
            self.logger.debug("People Data Labs source not available")
        except Exception as e:
            self.logger.warning(f"Failed to initialize PeopleDataLabs source: {e}")

        self.logger.info(f"Initialized {len(self.sources)} enrichment sources: {list(self.sources.keys())}")

    
    def _create_domain_inference_source(self):
        """Create basic domain inference source"""
        class DomainInferenceSource:
            def __init__(self):
                self.enabled = True
            
            def is_enabled(self):
                return True
            
            async def enrich_contact(self, contact: Contact) -> EnrichmentResult:
                """Basic domain-based enrichment"""
                try:
                    data = {}
                    
                    # Extract domain
                    if contact.email and '@' in contact.email:
                        domain = contact.email.split('@')[1].lower()
                        
                        # Basic company inference from domain
                        if domain in ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com']:
                            data['email_type'] = 'personal'
                        else:
                            data['email_type'] = 'business'
                            data['company_domain'] = domain
                            
                            # Try to infer company name from domain
                            company_name = domain.replace('.com', '').replace('.org', '').replace('.net', '')
                            company_name = company_name.replace('www.', '').title()
                            data['inferred_company'] = company_name
                    
                    # Basic location inference from TLD
                    if contact.email:
                        if contact.email.endswith('.uk'):
                            data['inferred_country'] = 'United Kingdom'
                        elif contact.email.endswith('.ca'):
                            data['inferred_country'] = 'Canada'
                        elif contact.email.endswith('.au'):
                            data['inferred_country'] = 'Australia'
                        elif contact.email.endswith('.de'):
                            data['inferred_country'] = 'Germany'
                    
                    return EnrichmentResult(
                        success=True,
                        contact=contact,
                        source=EnrichmentSource.DOMAIN_INFERENCE,
                        data_added=data,
                        confidence=0.3,
                        cost=0.0,
                        processing_time=0.01
                    )
                    
                except Exception as e:
                    return EnrichmentResult(
                        success=False,
                        contact=contact,
                        source=EnrichmentSource.DOMAIN_INFERENCE,
                        error_message=str(e)
                    )
        
        return DomainInferenceSource()
    
    async def enrich_contacts(self, contacts: List[Contact]) -> List[Contact]:
        """
        Enrich a list of contacts using available sources
        
        Args:
            contacts: List of contacts to enrich
            
        Returns:
            List of enriched contacts
        """
        if not contacts:
            return []
        
        self.logger.info(f"Starting enrichment for {len(contacts)} contacts")
        start_time = time.time()
        
        enriched_contacts = []
        successful_enrichments = 0
        
        for i, contact in enumerate(contacts):
            try:
                # Check cache first
                cached_data = self.cache.get(contact.email)
                if cached_data:
                    self._apply_cached_data(contact, cached_data)
                    enriched_contacts.append(contact)
                    successful_enrichments += 1
                    continue
                
                # Enrich contact
                enrichment_result = await self._enrich_single_contact(contact)
                
                if enrichment_result.success:
                    # Cache the result
                    self.cache.set(contact.email, enrichment_result.data_added)
                    successful_enrichments += 1
                    
                    # Update totals
                    self.total_cost += enrichment_result.cost
                    self.total_api_calls += enrichment_result.api_calls_used
                
                enriched_contacts.append(contact)
                
                # Progress logging
                if (i + 1) % 10 == 0:
                    self.logger.info(f"Enriched {i + 1}/{len(contacts)} contacts")
                
                # Small delay to be respectful to APIs
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Failed to enrich contact {contact.email}: {e}")
                enriched_contacts.append(contact)  # Add contact even if enrichment failed
        
        processing_time = time.time() - start_time
        
        self.logger.info(
            f"Enrichment completed: {successful_enrichments}/{len(contacts)} successful "
            f"in {processing_time:.2f}s (${self.total_cost:.2f} cost, {self.total_api_calls} API calls)"
        )
        
        return enriched_contacts
    
    async def _enrich_single_contact(self, contact: Contact) -> EnrichmentResult:
        """Enrich a single contact using available sources"""
        
        # Try sources in order of preference
        source_priority = ['clearbit', 'peopledatalabs', 'hunter', 'domain_inference']
        
        for source_name in source_priority:
            if source_name not in self.sources:
                continue
            
            source = self.sources[source_name]
            
            # Check if source is enabled
            if hasattr(source, 'is_enabled') and not source.is_enabled():
                continue
            
            try:
                result = await source.enrich_contact(contact)
                
                if result.success and result.data_added:
                    self.logger.debug(f"Enriched {contact.email} using {source_name}")
                    return result
                    
            except Exception as e:
                self.logger.warning(f"Source {source_name} failed for {contact.email}: {e}")
                continue
        
        # If no source worked, return basic result
        return EnrichmentResult(
            success=False,
            contact=contact,
            error_message="No enrichment sources available or successful"
        )
    
    def _apply_cached_data(self, contact: Contact, cached_data: Dict[str, Any]):
        """Apply cached enrichment data to contact"""
        try:
            for key, value in cached_data.items():
                if hasattr(contact, key) and value:
                    setattr(contact, key, value)
            
            # Update enrichment metadata
            contact.data_source = "Cache"
            contact.confidence = 0.8  # Cached data is reliable
            
        except Exception as e:
            self.logger.warning(f"Failed to apply cached data: {e}")
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            # Cleanup any source connections
            for source_name, source in self.sources.items():
                if hasattr(source, 'close'):
                    try:
                        await source.close()
                    except Exception as e:
                        self.logger.warning(f"Failed to cleanup source {source_name}: {e}")
            
            self.logger.info(f"Enrichment cleanup completed (${self.total_cost:.2f} total cost)")
            
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get enrichment statistics"""
        return {
            'sources_available': len(self.sources),
            'cache_size': self.cache.size(),
            'total_cost': self.total_cost,
            'total_api_calls': self.total_api_calls,
            'sources': list(self.sources.keys())
        }

# For backward compatibility
def create_enricher() -> ContactEnricher:
    """Create a new contact enricher instance"""
    return ContactEnricher()

async def enrich_contact_list(contacts: List[Contact]) -> List[Contact]:
    """Convenience function to enrich a list of contacts"""
    enricher = ContactEnricher()
    try:
        return await enricher.enrich_contacts(contacts)
    finally:
        await enricher.cleanup()