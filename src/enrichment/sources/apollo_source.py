"""
Apollo.io API Integration
Sales intelligence and B2B contact database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import asyncio
import aiohttp
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from core.models import Contact, EnrichmentSource, EnrichmentResult
from core.exceptions import EnrichmentError, RateLimitError, AuthenticationError
from config.config_manager import get_config_manager

class ApolloIOSource:
    """
    Apollo.io enrichment source
    Provides comprehensive B2B sales intelligence including:
    - Person enrichment with professional details
    - Company information and technographics
    - Contact search and discovery
    - Email verification
    - Intent data and sales signals
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config_manager = get_config_manager()
        self.source_config = self.config_manager.get_source_config('apollo')
        
        if not self.source_config:
            raise EnrichmentError("Apollo.io configuration not found")
        
        self.api_key = self.source_config.api_key
        self.base_url = self.source_config.base_url
        self.rate_limit = self.source_config.rate_limit
        self.cost_per_request = self.source_config.cost_per_request
        
        # Rate limiting
        self.last_request_time = 0
        self.requests_this_hour = 0
        self.hour_start = time.time()
        
        # Session for HTTP requests
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=self.source_config.timeout)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    'Cache-Control': 'no-cache',
                    'Content-Type': 'application/json',
                    'User-Agent': 'EmailEnrichment/2.0'
                }
            )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
            self.session = None
    
    def is_enabled(self) -> bool:
        """Check if Apollo.io source is enabled and configured"""
        return (self.source_config.enabled and 
                bool(self.api_key) and 
                self.api_key.strip() != "")
    
    async def enrich_contact(self, contact: Contact) -> EnrichmentResult:
        """
        Enrich a contact using Apollo.io APIs
        
        Args:
            contact: Contact to enrich
            
        Returns:
            EnrichmentResult with enriched data
        """
        start_time = time.time()
        
        if not self.is_enabled():
            return EnrichmentResult(
                success=False,
                contact=contact,
                source=EnrichmentSource.APOLLO,
                error_message="Apollo.io not enabled or configured"
            )
        
        try:
            # Rate limiting check
            await self._check_rate_limits()
            
            # Try Apollo.io person enrichment
            enrichment_data = await self._enrich_person(contact.email)
            
            if not enrichment_data:
                return EnrichmentResult(
                    success=False,
                    contact=contact,
                    source=EnrichmentSource.APOLLO,
                    error_message="No data found for email",
                    cost=self.cost_per_request,
                    processing_time=time.time() - start_time,
                    api_calls_used=1
                )
            
            # Process the enrichment data
            processed_data = self._process_apollo_response(enrichment_data)
            
            # Update contact with enriched data
            contact.update_enrichment_data(
                data=processed_data,
                source=EnrichmentSource.APOLLO,
                confidence=self.source_config.confidence_score,
                cost=self.cost_per_request
            )
            
            processing_time = time.time() - start_time
            
            self.logger.info(f"Successfully enriched {contact.email} with Apollo.io")
            
            return EnrichmentResult(
                success=True,
                contact=contact,
                source=EnrichmentSource.APOLLO,
                data_added=processed_data,
                confidence=self.source_config.confidence_score,
                cost=self.cost_per_request,
                processing_time=processing_time,
                api_calls_used=1
            )
            
        except RateLimitError as e:
            self.logger.warning(f"Apollo.io rate limit hit: {e}")
            return EnrichmentResult(
                success=False,
                contact=contact,
                source=EnrichmentSource.APOLLO,
                error_message=f"Rate limit exceeded: {e}",
                processing_time=time.time() - start_time
            )
            
        except AuthenticationError as e:
            self.logger.error(f"Apollo.io authentication failed: {e}")
            return EnrichmentResult(
                success=False,
                contact=contact,
                source=EnrichmentSource.APOLLO,
                error_message=f"Authentication failed: {e}",
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            self.logger.error(f"Unexpected error during Apollo.io enrichment: {e}", exc_info=True)
            return EnrichmentResult(
                success=False,
                contact=contact,
                source=EnrichmentSource.APOLLO,
                error_message=f"Unexpected error: {str(e)}",
                processing_time=time.time() - start_time
            )
            