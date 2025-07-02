# """
# Enhanced Contact Enrichment Engine
# Production-ready with multiple data sources, caching, and AI capabilities
# """

# import sys, os
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# import asyncio
# import json
# import time
# import random
# import hashlib
# from datetime import datetime, timedelta
# from typing import List, Dict, Optional, Any, Tuple
# from dataclasses import dataclass
# from pathlib import Path
# import logging

# import aiohttp
# import requests
# from tqdm import tqdm
# import colorama
# from colorama import Fore, Style

# from core.models import Contact, ContactType
# from core.exceptions import EnrichmentError, RateLimitError, ProviderError
# import os
# from pathlib import Path

# # Mock config values to make it work
# ENRICHMENT_CONFIG = {
#     'max_concurrent_enrichments': 5,
#     'sources': {
#         'clearbit': {'enabled': False, 'api_key': '', 'base_url': 'https://person.clearbit.com/v2/people/find', 'cost_per_request': 0.50},
#         'peopledatalabs': {'enabled': False, 'api_key': '', 'base_url': 'https://api.peopledatalabs.com/v5', 'cost_per_request': 0.03},
#         'hunter': {'enabled': False, 'api_key': '', 'base_url': 'https://api.hunter.io/v2', 'cost_per_request': 0.01},
#         'domain_inference': {'enabled': True, 'confidence_score': 0.6},
#         'mock_data': {'enabled': True, 'confidence_score': 0.8}
#     }
# }
# CACHE_DIR = Path("data/cache")
# ENABLE_CACHING = True

# @dataclass
# class EnrichmentResult:
#     """Container for enrichment results"""
#     success: bool
#     data: Dict[str, Any]
#     source: str
#     confidence: float
#     cost: float = 0.0
#     processing_time: float = 0.0
#     error_message: str = ""

# class EnrichmentCache:
#     """Simple file-based cache for enrichment results"""
    
#     def __init__(self, cache_dir: Path = CACHE_DIR):
#         self.cache_dir = cache_dir / "enrichment"
#         self.cache_dir.mkdir(parents=True, exist_ok=True)
#         self.ttl_hours = 24  # Cache TTL
    
#     def _get_cache_key(self, email: str, source: str) -> str:
#         """Generate cache key for email and source"""
#         key_string = f"{email.lower()}_{source}"
#         return hashlib.md5(key_string.encode()).hexdigest()
    
#     def _get_cache_file(self, cache_key: str) -> Path:
#         """Get cache file path"""
#         return self.cache_dir / f"{cache_key}.json"
    
#     def get(self, email: str, source: str) -> Optional[Dict[str, Any]]:
#         """Get cached enrichment data"""
#         if not ENABLE_CACHING:
#             return None
        
#         try:
#             cache_key = self._get_cache_key(email, source)
#             cache_file = self._get_cache_file(cache_key)
            
#             if not cache_file.exists():
#                 return None
            
#             with open(cache_file, 'r') as f:
#                 cache_data = json.load(f)
            
#             # Check if cache is still valid
#             cache_time = datetime.fromisoformat(cache_data['timestamp'])
#             if datetime.now() - cache_time > timedelta(hours=self.ttl_hours):
#                 cache_file.unlink()  # Delete expired cache
#                 return None
            
#             return cache_data['data']
            
#         except Exception:
#             return None
    
#     def set(self, email: str, source: str, data: Dict[str, Any]):
#         """Cache enrichment data"""
#         if not ENABLE_CACHING:
#             return
        
#         try:
#             cache_key = self._get_cache_key(email, source)
#             cache_file = self._get_cache_file(cache_key)
            
#             cache_data = {
#                 'timestamp': datetime.now().isoformat(),
#                 'email': email,
#                 'source': source,
#                 'data': data
#             }
            
#             with open(cache_file, 'w') as f:
#                 json.dump(cache_data, f, indent=2)
                
#         except Exception as e:
#             logging.getLogger(__name__).warning(f"Failed to cache data: {e}")

# class ContactEnricher:
#     """
#     Enhanced contact enrichment engine with multiple data sources
#     Production-ready with caching, rate limiting, and error handling
#     """
    
#     def __init__(self):
#         self.logger = logging.getLogger(__name__)
#         self.session = aiohttp.ClientSession(
#             timeout=aiohttp.ClientTimeout(total=30),
#             headers={'User-Agent': 'EmailEnrichment/2.0'}
#         )
#         self.cache = EnrichmentCache()
        
#         # Statistics tracking
#         self.stats = {
#             'total_processed': 0,
#             'successful_enrichments': 0,
#             'cache_hits': 0,
#             'api_calls': 0,
#             'total_cost': 0.0,
#             'processing_time': 0.0,
#             'source_stats': {}
#         }
        
#         # Mock data for demo/testing
#         self._load_mock_data()
    
#     def _load_mock_data(self):
#         """Load mock data for testing and demo purposes"""
#         self.mock_locations = [
#             "San Francisco, CA", "New York, NY", "London, UK", "Toronto, Canada",
#             "Austin, TX", "Seattle, WA", "Boston, MA", "Chicago, IL", "Los Angeles, CA",
#             "Berlin, Germany", "Amsterdam, Netherlands", "Sydney, Australia", "Tokyo, Japan",
#             "Singapore", "Hong Kong", "Tel Aviv, Israel", "Stockholm, Sweden", "Zurich, Switzerland",
#             "Paris, France", "Barcelona, Spain", "Dublin, Ireland", "Copenhagen, Denmark",
#             "Vancouver, Canada", "Melbourne, Australia", "Bangalore, India", "Shanghai, China"
#         ]
        
#         self.mock_net_worth_ranges = [
#             "$50K - $100K", "$100K - $250K", "$250K - $500K", "$500K - $1M",
#             "$1M - $2.5M", "$2.5M - $5M", "$5M - $10M", "$10M+", "$25M+"
#         ]
        
#         self.job_titles_by_domain = {
#             'google.com': ['Software Engineer', 'Product Manager', 'Data Scientist', 'Engineering Manager'],
#             'microsoft.com': ['Principal Engineer', 'Program Manager', 'Cloud Architect', 'Director'],
#             'amazon.com': ['Senior SDE', 'Principal PM', 'Solutions Architect', 'VP Engineering'],
#             'apple.com': ['iOS Engineer', 'Hardware Engineer', 'Design Lead', 'Product Director'],
#             'meta.com': ['Staff Engineer', 'Product Manager', 'Research Scientist', 'Engineering Director']
#         }
    
#     async def enrich_contacts(self, contacts: List[Contact]) -> List[Contact]:
#         """
#         Enrich a list of contacts with location, net worth, and professional data
#         Enhanced with parallel processing and comprehensive error handling
#         """
#         if not contacts:
#             return contacts
        
#         start_time = time.time()
#         self.logger.info(f"Starting enrichment for {len(contacts)} contacts")
        
#         # Reset statistics
#         self.stats = {
#             'total_processed': 0,
#             'successful_enrichments': 0,
#             'cache_hits': 0,
#             'api_calls': 0,
#             'total_cost': 0.0,
#             'processing_time': 0.0,
#             'source_stats': {}
#         }
        
#         # Process contacts with progress bar
#         enriched_contacts = []
        
#         if len(contacts) > 10:  # Show progress bar for larger batches
#             contact_iterator = tqdm(
#                 contacts, 
#                 desc="Enriching contacts", 
#                 unit="contact",
#                 bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"
#             )
#         else:
#             contact_iterator = contacts
        
#         # Process in batches for better performance
#         batch_size = ENRICHMENT_CONFIG.get('max_concurrent_enrichments', 5)
        
#         for i in range(0, len(contacts), batch_size):
#             batch = contacts[i:i + batch_size]
            
#             # Process batch in parallel
#             tasks = [self._enrich_single_contact(contact) for contact in batch]
#             batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
#             # Handle results
#             for contact, result in zip(batch, batch_results):
#                 if isinstance(result, Exception):
#                     self.logger.error(f"Enrichment failed for {contact.email}: {result}")
#                     enriched_contacts.append(contact)  # Add without enrichment
#                 else:
#                     enriched_contacts.append(result)
            
#             # Rate limiting between batches
#             await asyncio.sleep(0.1)
        
#         # Calculate final statistics
#         self.stats['processing_time'] = time.time() - start_time
#         self.stats['total_processed'] = len(contacts)
        
#         self._print_enrichment_summary()
        
#         return enriched_contacts
    
#     async def _enrich_single_contact(self, contact: Contact) -> Contact:
#         """Enrich a single contact with available data sources"""
#         enrichment_start = time.time()
        
#         try:
#             # Try enrichment sources in order of preference and cost
#             enrichment_result = None
            
#             # 1. Check cache first
#             cached_result = await self._check_cache(contact.email)
#             if cached_result:
#                 enrichment_result = cached_result
#                 self.stats['cache_hits'] += 1
            
#             # 2. Try Clearbit (premium, high accuracy)
#             if not enrichment_result and ENRICHMENT_CONFIG['sources']['clearbit']['enabled']:
#                 enrichment_result = await self._enrich_with_clearbit(contact.email)
            
#             # 3. Try People Data Labs (good coverage, reasonable cost)
#             if not enrichment_result and ENRICHMENT_CONFIG['sources']['peopledatalabs']['enabled']:
#                 enrichment_result = await self._enrich_with_peopledatalabs(contact.email)
            
#             # 4. Try Hunter.io (good for company data)
#             if not enrichment_result and ENRICHMENT_CONFIG['sources']['hunter']['enabled']:
#                 enrichment_result = await self._enrich_with_hunter(contact.email)
            
#             # 5. Use domain-based inference (free, always available)
#             if not enrichment_result and ENRICHMENT_CONFIG['sources']['domain_inference']['enabled']:
#                 enrichment_result = await self._enrich_with_domain_inference(contact.email, contact.name)
            
#             # 6. Fallback to mock data (for testing/demo)
#             if not enrichment_result and ENRICHMENT_CONFIG['sources']['mock_data']['enabled']:
#                 enrichment_result = await self._enrich_with_mock_data(contact.email, contact.name)
            
#             # Apply enrichment data if found
#             if enrichment_result and enrichment_result.success:
#                 contact.update_enrichment_data(
#                     enrichment_result.data,
#                     enrichment_result.source,
#                     enrichment_result.confidence
#                 )
#                 self.stats['successful_enrichments'] += 1
#                 self.stats['total_cost'] += enrichment_result.cost
                
#                 # Update source statistics
#                 source = enrichment_result.source
#                 if source not in self.stats['source_stats']:
#                     self.stats['source_stats'][source] = {'count': 0, 'cost': 0.0}
#                 self.stats['source_stats'][source]['count'] += 1
#                 self.stats['source_stats'][source]['cost'] += enrichment_result.cost
                
#                 # Cache the result
#                 if enrichment_result.source != 'cache':
#                     await self._cache_result(contact.email, enrichment_result)
            
#             # Add processing time
#             processing_time = time.time() - enrichment_start
#             contact.enrichment_processing_time = processing_time
            
#             return contact
            
#         except Exception as e:
#             self.logger.error(f"Enrichment error for {contact.email}: {e}")
#             return contact
    
#     async def _check_cache(self, email: str) -> Optional[EnrichmentResult]:
#         """Check if enrichment data is cached"""
#         try:
#             # Check all sources in cache
#             for source in ['clearbit', 'peopledatalabs', 'hunter', 'domain_inference']:
#                 cached_data = self.cache.get(email, source)
#                 if cached_data:
#                     return EnrichmentResult(
#                         success=True,
#                         data=cached_data,
#                         source='cache',
#                         confidence=cached_data.get('confidence', 0.5)
#                     )
#             return None
#         except Exception:
#             return None
    
#     async def _cache_result(self, email: str, result: EnrichmentResult):
#         """Cache enrichment result"""
#         try:
#             cache_data = result.data.copy()
#             cache_data['confidence'] = result.confidence
#             cache_data['timestamp'] = datetime.now().isoformat()
#             self.cache.set(email, result.source, cache_data)
#         except Exception as e:
#             self.logger.warning(f"Failed to cache result for {email}: {e}")
    
#     async def _enrich_with_clearbit(self, email: str) -> Optional[EnrichmentResult]:
#         """Enrich using Clearbit Person API"""
#         start_time = time.time()
        
#         try:
#             api_key = ENRICHMENT_CONFIG['sources']['clearbit']['api_key']
#             if not api_key:
#                 return None
            
#             url = f"{ENRICHMENT_CONFIG['sources']['clearbit']['base_url']}?email={email}"
            
#             async with self.session.get(
#                 url,
#                 auth=aiohttp.BasicAuth(api_key, ''),
#                 timeout=aiohttp.ClientTimeout(total=10)
#             ) as response:
#                 self.stats['api_calls'] += 1
                
#                 if response.status == 200:
#                     data = await response.json()
                    
#                     enrichment_data = self._process_clearbit_response(data)
#                     processing_time = time.time() - start_time
                    
#                     return EnrichmentResult(
#                         success=True,
#                         data=enrichment_data,
#                         source="Clearbit",
#                         confidence=0.9,
#                         cost=ENRICHMENT_CONFIG['sources']['clearbit']['cost_per_request'],
#                         processing_time=processing_time
#                     )
#                 elif response.status == 404:
#                     # Person not found - not an error
#                     return None
#                 elif response.status == 429:
#                     raise RateLimitError("Clearbit rate limit exceeded", "clearbit", retry_after=3600)
#                 else:
#                     self.logger.warning(f"Clearbit API error {response.status} for {email}")
#                     return None
                    
#         except Exception as e:
#             self.logger.error(f"Clearbit enrichment failed for {email}: {e}")
#             return None
    
#     def _process_clearbit_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
#         """Process Clearbit API response"""
#         result = {}
        
#         # Location data
#         location_parts = []
#         if data.get('location'):
#             if data['location'].get('city'):
#                 location_parts.append(data['location']['city'])
#             if data['location'].get('state'):
#                 location_parts.append(data['location']['state'])
#             if data['location'].get('country'):
#                 location_parts.append(data['location']['country'])
        
#         result['location'] = ', '.join(location_parts) if location_parts else ''
        
#         # Professional data
#         if data.get('employment'):
#             employment = data['employment']
#             result['job_title'] = employment.get('title', '')
#             result['company'] = employment.get('name', '')
#             result['industry'] = employment.get('domain', '')
#             result['seniority_level'] = employment.get('seniority', '')
        
#         # Social profiles
#         if data.get('linkedin'):
#             result['linkedin_url'] = data['linkedin'].get('handle', '')
#         if data.get('twitter'):
#             result['twitter_handle'] = data['twitter'].get('handle', '')
#         if data.get('github'):
#             result['github_username'] = data['github'].get('handle', '')
        
#         # Estimate net worth based on role and company
#         result['estimated_net_worth'] = self._estimate_net_worth_from_clearbit(data)
        
#         return result
    
#     async def _enrich_with_peopledatalabs(self, email: str) -> Optional[EnrichmentResult]:
#         """Enrich using People Data Labs API"""
#         start_time = time.time()
        
#         try:
#             api_key = ENRICHMENT_CONFIG['sources']['peopledatalabs']['api_key']
#             if not api_key:
#                 return None
            
#             url = f"{ENRICHMENT_CONFIG['sources']['peopledatalabs']['base_url']}/person/enrich"
            
#             params = {
#                 'email': email,
#                 'pretty': 'true'
#             }
            
#             headers = {'X-Api-Key': api_key}
            
#             async with self.session.get(url, params=params, headers=headers) as response:
#                 self.stats['api_calls'] += 1
                
#                 if response.status == 200:
#                     data = await response.json()
                    
#                     enrichment_data = self._process_pdl_response(data)
#                     processing_time = time.time() - start_time
                    
#                     return EnrichmentResult(
#                         success=True,
#                         data=enrichment_data,
#                         source="People Data Labs",
#                         confidence=0.85,
#                         cost=ENRICHMENT_CONFIG['sources']['peopledatalabs']['cost_per_request'],
#                         processing_time=processing_time
#                     )
#                 elif response.status == 404:
#                     return None
#                 else:
#                     self.logger.warning(f"PDL API error {response.status} for {email}")
#                     return None
                    
#         except Exception as e:
#             self.logger.error(f"PDL enrichment failed for {email}: {e}")
#             return None
    
#     def _process_pdl_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
#         """Process People Data Labs API response"""
#         result = {}
        
#         # Location data
#         if data.get('location_names'):
#             result['location'] = ', '.join(data['location_names'][:2])  # Take first 2 locations
        
#         # Professional data
#         if data.get('job_title'):
#             result['job_title'] = data['job_title']
#         if data.get('job_company_name'):
#             result['company'] = data['job_company_name']
#         if data.get('industry'):
#             result['industry'] = data['industry']
        
#         # Social profiles
#         if data.get('linkedin_url'):
#             result['linkedin_url'] = data['linkedin_url']
#         if data.get('twitter_url'):
#             result['twitter_handle'] = data['twitter_url'].split('/')[-1] if data['twitter_url'] else ''
#         if data.get('github_url'):
#             result['github_username'] = data['github_url'].split('/')[-1] if data['github_url'] else ''
        
#         # Estimate net worth
#         result['estimated_net_worth'] = self._estimate_net_worth_from_pdl(data)
        
#         return result
    
#     async def _enrich_with_hunter(self, email: str) -> Optional[EnrichmentResult]:
#         """Enrich using Hunter.io API"""
#         start_time = time.time()
        
#         try:
#             api_key = ENRICHMENT_CONFIG['sources']['hunter']['api_key']
#             if not api_key:
#                 return None
            
#             # Hunter works better with domain-based queries
#             domain = email.split('@')[1]
#             url = f"{ENRICHMENT_CONFIG['sources']['hunter']['base_url']}/domain-search"
            
#             params = {
#                 'domain': domain,
#                 'api_key': api_key,
#                 'limit': 10
#             }
            
#             async with self.session.get(url, params=params) as response:
#                 self.stats['api_calls'] += 1
                
#                 if response.status == 200:
#                     data = await response.json()
                    
#                     # Find specific email in results
#                     enrichment_data = self._process_hunter_response(data, email)
#                     processing_time = time.time() - start_time
                    
#                     if enrichment_data:
#                         return EnrichmentResult(
#                             success=True,
#                             data=enrichment_data,
#                             source="Hunter.io",
#                             confidence=0.7,
#                             cost=ENRICHMENT_CONFIG['sources']['hunter']['cost_per_request'],
#                             processing_time=processing_time
#                         )
#                     return None
#                 else:
#                     self.logger.warning(f"Hunter API error {response.status} for {email}")
#                     return None
                    
#         except Exception as e:
#             self.logger.error(f"Hunter enrichment failed for {email}: {e}")
#             return None
    
#     def _process_hunter_response(self, data: Dict[str, Any], target_email: str) -> Optional[Dict[str, Any]]:
#         """Process Hunter.io API response"""
#         emails = data.get('data', {}).get('emails', [])
        
#         # Find the specific email
#         target_data = None
#         for email_data in emails:
#             if email_data.get('value', '').lower() == target_email.lower():
#                 target_data = email_data
#                 break
        
#         if not target_data:
#             return None
        
#         result = {}
        
#         # Basic info
#         if target_data.get('first_name') and target_data.get('last_name'):
#             result['name'] = f"{target_data['first_name']} {target_data['last_name']}"
        
#         if target_data.get('position'):
#             result['job_title'] = target_data['position']
        
#         # Company info from domain data
#         domain_data = data.get('data', {})
#         if domain_data.get('organization'):
#             result['company'] = domain_data['organization']
#         if domain_data.get('country'):
#             result['location'] = domain_data['country']
        
#         # Estimate net worth based on position
#         result['estimated_net_worth'] = self._estimate_net_worth_from_title(
#             target_data.get('position', ''),
#             domain_data.get('organization', '')
#         )
        
#         return result
    
#     async def _enrich_with_domain_inference(self, email: str, name: str = "") -> EnrichmentResult:
#         """Enrich using domain-based inference (free method)"""
#         try:
#             domain = email.split('@')[1].lower()
            
#             result = {
#                 'location': self._infer_location_from_domain(domain),
#                 'estimated_net_worth': self._estimate_net_worth_from_domain(domain, email, name),
#                 'company': self._infer_company_from_domain(domain),
#                 'industry': self._infer_industry_from_domain(domain)
#             }
            
#             return EnrichmentResult(
#                 success=True,
#                 data=result,
#                 source="Domain Inference",
#                 confidence=ENRICHMENT_CONFIG['sources']['domain_inference']['confidence_score'],
#                 cost=0.0
#             )
            
#         except Exception as e:
#             self.logger.error(f"Domain inference failed for {email}: {e}")
#             return EnrichmentResult(
#                 success=False,
#                 data={},
#                 source="Domain Inference",
#                 confidence=0.0,
#                 error_message=str(e)
#             )
    
#     async def _enrich_with_mock_data(self, email: str, name: str = "") -> EnrichmentResult:
#         """Generate realistic mock data for demo purposes"""
#         try:
#             # Use email hash for consistent results
#             seed = hash(email) % 10000
#             random.seed(seed)
            
#             domain = email.split('@')[1].lower()
            
#             # Generate location
#             location = random.choice(self.mock_locations)
            
#             # Generate professional data
#             job_title = ""
#             company = ""
            
#             if domain in self.job_titles_by_domain:
#                 job_title = random.choice(self.job_titles_by_domain[domain])
#                 company = domain.split('.')[0].title()
#             else:
#                 job_titles = [
#                     'Software Engineer', 'Product Manager', 'Sales Director', 'Marketing Manager',
#                     'Data Analyst', 'Business Development', 'Operations Manager', 'Design Lead',
#                     'Financial Analyst', 'HR Manager', 'Customer Success', 'Content Manager'
#                 ]
#                 job_title = random.choice(job_titles)
#                 company = domain.split('.')[0].title()
            
#             # Generate net worth based on factors
#             net_worth = self._estimate_net_worth_from_email_advanced(email, name, job_title, company)
            
#             result = {
#                 'location': location,
#                 'estimated_net_worth': net_worth,
#                 'job_title': job_title,
#                 'company': company,
#                 'industry': self._infer_industry_from_domain(domain)
#             }
            
#             return EnrichmentResult(
#                 success=True,
#                 data=result,
#                 source="Mock Data",
#                 confidence=ENRICHMENT_CONFIG['sources']['mock_data']['confidence_score'],
#                 cost=0.0
#             )
            
#         except Exception as e:
#             return EnrichmentResult(
#                 success=False,
#                 data={},
#                 source="Mock Data",
#                 confidence=0.0,
#                 error_message=str(e)
#             )
    
#     def _infer_location_from_domain(self, domain: str) -> str:
#         """Infer location from email domain"""
#         domain_locations = {
#             # Tech companies
#             'google.com': 'Mountain View, CA',
#             'apple.com': 'Cupertino, CA',
#             'microsoft.com': 'Redmond, WA',
#             'amazon.com': 'Seattle, WA',
#             'meta.com': 'Menlo Park, CA',
#             'netflix.com': 'Los Gatos, CA',
#             'salesforce.com': 'San Francisco, CA',
#             'uber.com': 'San Francisco, CA',
#             'airbnb.com': 'San Francisco, CA',
#             'tesla.com': 'Austin, TX',
#             'nvidia.com': 'Santa Clara, CA',
#             'adobe.com': 'San Jose, CA',
            
#             # International companies
#             'sap.com': 'Walldorf, Germany',
#             'spotify.com': 'Stockholm, Sweden',
#             'nokia.com': 'Espoo, Finland',
#             'asml.com': 'Veldhoven, Netherlands',
#             'shopify.com': 'Ottawa, Canada',
            
#             # Generic domains
#             'gmail.com': 'Global',
#             'yahoo.com': 'Global',
#             'hotmail.com': 'Global',
#             'outlook.com': 'Global'
#         }
        
#         return domain_locations.get(domain, 'Unknown')
    
#     def _infer_company_from_domain(self, domain: str) -> str:
#         """Infer company name from domain"""
#         # Remove common suffixes and return title case
#         company_name = domain.replace('.com', '').replace('.org', '').replace('.net', '')
#         return company_name.replace('-', ' ').replace('_', ' ').title()
    
#     def _infer_industry_from_domain(self, domain: str) -> str:
#         """Infer industry from domain"""
#         tech_domains = {
#             'google.com': 'Internet & Technology',
#             'microsoft.com': 'Software',
#             'apple.com': 'Consumer Electronics',
#             'amazon.com': 'E-commerce & Cloud',
#             'meta.com': 'Social Media',
#             'netflix.com': 'Entertainment & Media',
#             'salesforce.com': 'Enterprise Software',
#             'uber.com': 'Transportation Technology',
#             'airbnb.com': 'Travel & Hospitality',
#             'tesla.com': 'Automotive & Energy'
#         }
        
#         if domain.endswith('.edu'):
#             return 'Education'
#         elif domain.endswith('.gov'):
#             return 'Government'
#         elif domain.endswith('.org'):
#             return 'Non-profit'
#         else:
#             return tech_domains.get(domain, 'Business Services')
    
#     def _estimate_net_worth_from_domain(self, domain: str, email: str, name: str) -> str:
#         """Estimate net worth based on domain and other factors"""
#         base_score = 0
        
#         # Domain-based scoring
#         high_value_domains = {
#             'google.com': 4, 'apple.com': 4, 'microsoft.com': 4, 'amazon.com': 4,
#             'meta.com': 4, 'netflix.com': 3, 'salesforce.com': 3, 'uber.com': 3,
#             'airbnb.com': 3, 'tesla.com': 4, 'nvidia.com': 4
#         }
        
#         base_score += high_value_domains.get(domain, 0)
        
#         # Email pattern analysis
#         local_part = email.split('@')[0].lower()
#         executive_indicators = ['ceo', 'cto', 'cfo', 'founder', 'president', 'vp', 'director']
#         senior_indicators = ['senior', 'principal', 'lead', 'head', 'manager']
        
#         if any(indicator in local_part for indicator in executive_indicators):
#             base_score += 3
#         elif any(indicator in local_part for indicator in senior_indicators):
#             base_score += 1
        
#         # Map score to net worth range
#         if base_score >= 6:
#             return random.choice(['$2.5M - $5M', '$5M - $10M', '$10M+'])
#         elif base_score >= 4:
#             return random.choice(['$1M - $2.5M', '$2.5M - $5M'])
#         elif base_score >= 2:
#             return random.choice(['$500K - $1M', '$1M - $2.5M'])
#         elif base_score >= 1:
#             return random.choice(['$250K - $500K', '$500K - $1M'])
#         else:
#             return random.choice(['$100K - $250K', '$250K - $500K'])
    
#     def _estimate_net_worth_from_email_advanced(self, email: str, name: str, job_title: str, company: str) -> str:
#         """Advanced net worth estimation using multiple factors"""
#         score = 0
        
#         # Job title scoring
#         executive_titles = ['ceo', 'cto', 'cfo', 'founder', 'president', 'vp', 'vice president']
#         director_titles = ['director', 'head of', 'principal', 'senior director']
#         manager_titles = ['manager', 'senior manager', 'lead', 'senior']
        
#         title_lower = job_title.lower()
        
#         if any(title in title_lower for title in executive_titles):
#             score += 4
#         elif any(title in title_lower for title in director_titles):
#             score += 3
#         elif any(title in title_lower for title in manager_titles):
#             score += 2
#         else:
#             score += 1
        
#         # Company size/type scoring
#         big_tech = ['google', 'apple', 'microsoft', 'amazon', 'meta', 'netflix', 'tesla', 'nvidia']
#         if any(company.lower().startswith(tech) for tech in big_tech):
#             score += 2
        
#         # Domain analysis
#         domain = email.split('@')[1].lower()
#         if domain.endswith('.edu'):
#             score -= 1  # Academic typically pays less
#         elif domain.endswith('.org'):
#             score -= 1  # Non-profit typically pays less
        
#         # Convert score to net worth
#         if score >= 6:
#             return random.choice(['$5M - $10M', '$10M+', '$25M+'])
#         elif score >= 5:
#             return random.choice(['$2.5M - $5M', '$5M - $10M'])
#         elif score >= 4:
#             return random.choice(['$1M - $2.5M', '$2.5M - $5M'])
#         elif score >= 3:
#             return random.choice(['$500K - $1M', '$1M - $2.5M'])
#         elif score >= 2:
#             return random.choice(['$250K - $500K', '$500K - $1M'])
#         else:
#             return random.choice(['$100K - $250K', '$250K - $500K'])
    
#     def _estimate_net_worth_from_clearbit(self, data: Dict[str, Any]) -> str:
#         """Estimate net worth from Clearbit data"""
#         score = 0
        
#         employment = data.get('employment', {})
#         title = employment.get('title', '').lower()
#         company = employment.get('name', '').lower()
#         seniority = employment.get('seniority', '').lower()
        
#         # Title-based scoring
#         if any(exec_term in title for exec_term in ['ceo', 'founder', 'president', 'chief']):
#             score += 4
#         elif any(vp_term in title for vp_term in ['vp', 'vice president', 'director']):
#             score += 3
#         elif 'senior' in title or 'principal' in title:
#             score += 2
#         elif 'manager' in title or 'lead' in title:
#             score += 1
        
#         # Seniority scoring
#         if 'executive' in seniority:
#             score += 3
#         elif 'senior' in seniority:
#             score += 2
#         elif 'mid' in seniority:
#             score += 1
        
#         # Company size (estimated from other indicators)
#         if employment.get('domain') and len(employment.get('domain', '')) > 0:
#             score += 1  # Has company domain suggests established company
        
#         # Convert to net worth range
#         if score >= 6:
#             return '$5M - $10M'
#         elif score >= 4:
#             return '$1M - $2.5M'
#         elif score >= 3:
#             return '$500K - $1M'
#         elif score >= 2:
#             return '$250K - $500K'
#         else:
#             return '$100K - $250K'
    
#     def _estimate_net_worth_from_pdl(self, data: Dict[str, Any]) -> str:
#         """Estimate net worth from People Data Labs data"""
#         score = 0
        
#         job_title = data.get('job_title', '').lower()
#         seniority = data.get('job_title_levels', [])
        
#         # Title analysis
#         if any(exec in job_title for exec in ['ceo', 'founder', 'president', 'chief']):
#             score += 4
#         elif any(senior in job_title for senior in ['vp', 'director', 'head']):
#             score += 3
#         elif 'senior' in job_title or 'principal' in job_title:
#             score += 2
        
#         # Seniority levels
#         if 'owner' in seniority or 'c_suite' in seniority:
#             score += 3
#         elif 'director' in seniority or 'vp' in seniority:
#             score += 2
#         elif 'manager' in seniority:
#             score += 1
        
#         # Experience (years)
#         experience_years = data.get('inferred_years_experience', 0)
#         if experience_years > 15:
#             score += 2
#         elif experience_years > 10:
#             score += 1
        
#         # Convert to range
#         if score >= 6:
#             return '$2.5M - $5M'
#         elif score >= 4:
#             return '$1M - $2.5M'
#         elif score >= 3:
#             return '$500K - $1M'
#         elif score >= 2:
#             return '$250K - $500K'
#         else:
#             return '$100K - $250K'
    
#     def _estimate_net_worth_from_title(self, title: str, company: str) -> str:
#         """Estimate net worth from job title and company"""
#         score = 0
#         title_lower = title.lower()
        
#         # Title scoring
#         if any(exec in title_lower for exec in ['ceo', 'founder', 'president', 'chief']):
#             score += 4
#         elif any(vp in title_lower for vp in ['vp', 'vice president', 'director']):
#             score += 3
#         elif any(senior in title_lower for senior in ['senior', 'principal', 'lead']):
#             score += 2
#         elif 'manager' in title_lower:
#             score += 1
        
#         # Company factor
#         if company and len(company) > 0:
#             score += 1
        
#         # Convert to range
#         ranges = [
#             '$100K - $250K', '$250K - $500K', '$500K - $1M',
#             '$1M - $2.5M', '$2.5M - $5M'
#         ]
        
#         index = min(score, len(ranges) - 1)
#         return ranges[index]
    
#     def _print_enrichment_summary(self):
#         """Print comprehensive enrichment summary"""
#         print(f"\n{Fore.GREEN}✅ CONTACT ENRICHMENT COMPLETED!{Style.RESET_ALL}")
#         print("-" * 50)
        
#         # Overall statistics
#         success_rate = (self.stats['successful_enrichments'] / max(self.stats['total_processed'], 1)) * 100
        
#         print(f"{Fore.CYAN}📊 Overall Results:{Style.RESET_ALL}")
#         print(f"   • Total contacts processed: {self.stats['total_processed']}")
#         print(f"   • Successful enrichments: {self.stats['successful_enrichments']}")
#         print(f"   • Success rate: {success_rate:.1f}%")
#         print(f"   • Cache hits: {self.stats['cache_hits']}")
#         print(f"   • API calls made: {self.stats['api_calls']}")
#         print(f"   • Processing time: {self.stats['processing_time']:.1f} seconds")
        
#         if self.stats['total_cost'] > 0:
#             print(f"   • Total cost: ${self.stats['total_cost']:.4f}")
        
#         # Source breakdown
#         if self.stats['source_stats']:
#             print(f"\n{Fore.CYAN}📋 Source Breakdown:{Style.RESET_ALL}")
#             for source, stats in self.stats['source_stats'].items():
#                 percentage = (stats['count'] / max(self.stats['successful_enrichments'], 1)) * 100
#                 cost_info = f" (${stats['cost']:.4f})" if stats['cost'] > 0 else ""
#                 print(f"   • {source}: {stats['count']} ({percentage:.1f}%){cost_info}")
    
#     async def cleanup(self):
#         """Cleanup enrichment resources"""
#         try:
#             if self.session and not self.session.closed:
#                 await self.session.close()
#         except Exception as e:
#             self.logger.warning(f"Error during enrichment cleanup: {e}")
    
#     def __del__(self):
#         """Cleanup when object is destroyed"""
#         if hasattr(self, 'session') and self.session and not self.session.closed:
#             import asyncio
#             try:
#                 loop = asyncio.get_event_loop()
#                 if loop.is_running():
#                     loop.create_task(self.session.close())
#                 else:
#                     loop.run_until_complete(self.session.close())
#             except:
#                 pass\




"""
Enhanced Contact Enrichment Engine - Phase 2-4 Implementation
Integrates premium APIs, AI analysis, and NLP capabilities
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from core.models import Contact, EnrichmentSource, EnrichmentResult
from core.exceptions import EnrichmentError, RateLimitError
from config.config_manager import get_config_manager

# Import enrichment sources
from enrichment.sources.clearbit_source import ClearbitEnrichmentSource
from enrichment.sources.peopledatalabs_source import PeopleDataLabsSource

# Import AI analyzers
from enrichment.ai.openai_analyzer import OpenAIEmailAnalyzer
from enrichment.ai.huggingface_nlp import HuggingFaceNLPEngine

# Import intelligence systems
from intelligence.contact_scorer import ContactScoringEngine

# Original cache and mock functionality
from enrichment.enrichment import EnrichmentCache  # Import from existing file

class EnhancedContactEnricher:
    """
    Enhanced contact enrichment engine with premium APIs and AI capabilities
    
    Features:
    - Premium data sources (Clearbit, People Data Labs, Hunter.io, etc.)
    - AI-powered email analysis (OpenAI GPT-4)
    - NLP analysis (Hugging Face transformers)
    - Advanced contact scoring
    - Smart data inference
    - Location services
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config_manager = get_config_manager()
        
        # Initialize cache
        self.cache = EnrichmentCache()
        
        # Initialize enrichment sources
        self.sources = {}
        self._initialize_sources()
        
        # Initialize AI components
        self.openai_analyzer = None
        self.nlp_engine = None
        self.contact_scorer = None
        self._initialize_ai_components()
        
        # Statistics tracking
        self.stats = {
            'total_processed': 0,
            'successful_enrichments': 0,
            'cache_hits': 0,
            'api_calls': 0,
            'total_cost': 0.0,
            'processing_time': 0.0,
            'source_stats': {},
            'ai_analysis_count': 0,
            'nlp_analysis_count': 0
        }
        
        # Performance settings
        perf_config = self.config_manager.performance_config
        self.max_concurrent = perf_config.max_concurrent_enrichments
        self.daily_budget = perf_config.daily_budget
        self.max_cost_per_contact = perf_config.max_cost_per_contact
    
    def _initialize_sources(self):
        """Initialize all available enrichment sources"""
        try:
            # Premium sources
            if self.config_manager.is_source_enabled('clearbit'):
                self.sources['clearbit'] = ClearbitEnrichmentSource()
                self.logger.info("Initialized Clearbit enrichment source")
            
            if self.config_manager.is_source_enabled('peopledatalabs'):
                self.sources['peopledatalabs'] = PeopleDataLabsSource()
                self.logger.info("Initialized People Data Labs enrichment source")
            
            # Additional sources can be added here (Hunter.io, ZoomInfo, Apollo.io)
            
            # Always available sources
            self.sources['domain_inference'] = DomainInferenceSource()
            self.sources['mock_data'] = MockDataSource()
            
            self.logger.info(f"Initialized {len(self.sources)} enrichment sources")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize enrichment sources: {e}")
    
    def _initialize_ai_components(self):
        """Initialize AI and NLP components"""
        try:
            # OpenAI analyzer
            if self.config_manager.is_ai_enabled('openai'):
                self.openai_analyzer = OpenAIEmailAnalyzer()
                self.logger.info("Initialized OpenAI email analyzer")
            
            # Hugging Face NLP engine
            hf_config = self.config_manager.get_huggingface_config()
            if hf_config.get('enabled', True):
                self.nlp_engine = HuggingFaceNLPEngine()
                self.logger.info("Initialized Hugging Face NLP engine")
            
            # Contact scoring engine
            self.contact_scorer = ContactScoringEngine()
            self.logger.info("Initialized contact scoring engine")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize AI components: {e}")
    
    async def enrich_contacts(self, contacts: List[Contact], 
                            enable_ai_analysis: bool = True,
                            enable_nlp_analysis: bool = True) -> List[Contact]:
        """
        Enhanced contact enrichment with AI and NLP analysis
        
        Args:
            contacts: List of contacts to enrich
            enable_ai_analysis: Enable OpenAI analysis
            enable_nlp_analysis: Enable NLP analysis
            
        Returns:
            List of enriched contacts
        """
        if not contacts:
            return contacts
        
        start_time = time.time()
        self.logger.info(f"Starting enhanced enrichment for {len(contacts)} contacts")
        
        # Reset statistics
        self._reset_stats()
        
        # Check budget constraints
        estimated_cost = self._estimate_enrichment_cost(len(contacts))
        if estimated_cost > self.daily_budget:
            self.logger.warning(f"Estimated cost ${estimated_cost:.2f} exceeds daily budget ${self.daily_budget:.2f}")
            # Consider reducing contacts or using cheaper sources
        
        # Process contacts in batches
        enriched_contacts = []
        batch_size = min(self.max_concurrent, 10)  # Reasonable batch size
        
        for i in range(0, len(contacts), batch_size):
            batch = contacts[i:i + batch_size]
            
            # Process batch concurrently
            tasks = [
                self._enrich_single_contact(contact, enable_ai_analysis, enable_nlp_analysis)
                for contact in batch
            ]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle results
            for contact, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    self.logger.error(f"Enrichment failed for {contact.email}: {result}")
                    enriched_contacts.append(contact)  # Add without enrichment
                else:
                    enriched_contacts.append(result)
            
            # Rate limiting between batches
            await asyncio.sleep(0.1)
            
            # Check budget during processing
            if self.stats['total_cost'] > self.daily_budget:
                self.logger.warning("Daily budget exceeded, stopping enrichment")
                break
        
        # Final statistics
        self.stats['processing_time'] = time.time() - start_time
        self.stats['total_processed'] = len(contacts)
        
        # Calculate and update contact scores
        if self.contact_scorer:
            self.logger.info("Calculating contact scores...")
            for contact in enriched_contacts:
                try:
                    contact.contact_score = self.contact_scorer.calculate_comprehensive_score(contact)
                except Exception as e:
                    self.logger.error(f"Scoring failed for {contact.email}: {e}")
        
        self._print_enrichment_summary()
        
        return enriched_contacts
    
    async def _enrich_single_contact(self, contact: Contact, 
                                   enable_ai: bool, enable_nlp: bool) -> Contact:
        """Enrich a single contact using all available methods"""
        enrichment_start = time.time()
        
        try:
            # Phase 1: Data enrichment from premium sources
            await self._enrich_contact_data(contact)
            
            # Phase 2: AI-powered analysis
            if enable_ai and self.openai_analyzer:
                await self._perform_ai_analysis(contact)
                self.stats['ai_analysis_count'] += 1
            
            # Phase 3: NLP analysis
            if enable_nlp and self.nlp_engine:
                await self._perform_nlp_analysis(contact)
                self.stats['nlp_analysis_count'] += 1
            
            # Phase 4: Smart inference and validation
            await self._perform_smart_inference(contact)
            
            processing_time = time.time() - enrichment_start
            contact.enrichment_metadata.processing_time = processing_time
            
            return contact
            
        except Exception as e:
            self.logger.error(f"Enhanced enrichment failed for {contact.email}: {e}")
            return contact
    
    async def _enrich_contact_data(self, contact: Contact):
        """Enrich contact using premium data sources"""
        # Try sources in priority order
        source_priority = [
            ('clearbit', self.sources.get('clearbit')),
            ('peopledatalabs', self.sources.get('peopledatalabs')),
            ('domain_inference', self.sources.get('domain_inference')),
            ('mock_data', self.sources.get('mock_data'))
        ]
        
        for source_name, source in source_priority:
            if not source:
                continue
            
            try:
                # Check cache first
                cached_result = self.cache.get(contact.email, source_name)
                if cached_result:
                    self._apply_cached_enrichment(contact, cached_result, source_name)
                    self.stats['cache_hits'] += 1
                    break
                
                # Check cost constraints
                source_config = self.config_manager.get_source_config(source_name)
                if source_config and source_config.cost_per_request > 0:
                    if (self.stats['total_cost'] + source_config.cost_per_request > self.daily_budget or
                        source_config.cost_per_request > self.max_cost_per_contact):
                        continue
                
                # Enrich using source
                if hasattr(source, 'enrich_contact'):
                    async with source:  # Use context manager if supported
                        result = await source.enrich_contact(contact)
                        
                        if result.success:
                            self.stats['successful_enrichments'] += 1
                            self.stats['total_cost'] += result.cost
                            self.stats['api_calls'] += result.api_calls_used
                            
                            # Update source stats
                            if source_name not in self.stats['source_stats']:
                                self.stats['source_stats'][source_name] = {'count': 0, 'cost': 0.0}
                            self.stats['source_stats'][source_name]['count'] += 1
                            self.stats['source_stats'][source_name]['cost'] += result.cost
                            
                            # Cache the result
                            self.cache.set(contact.email, source_name, result.data_added)
                            break
                elif callable(source):
                    # For simple function-based sources
                    enrichment_data = await source(contact.email, contact.name)
                    if enrichment_data:
                        contact.update_enrichment_data(
                            enrichment_data, 
                            getattr(EnrichmentSource, source_name.upper(), EnrichmentSource.MOCK_DATA),
                            0.8
                        )
                        break
                        
            except RateLimitError:
                self.logger.warning(f"Rate limit hit for {source_name}, trying next source")
                continue
            except Exception as e:
                self.logger.error(f"Enrichment failed for {source_name}: {e}")
                continue
    
    async def _perform_ai_analysis(self, contact: Contact):
        """Perform AI-powered analysis using OpenAI"""
        if not self.openai_analyzer or not contact.interactions:
            return
        
        try:
            # Get recent interaction for analysis
            recent_interaction = max(contact.interactions, key=lambda x: x.timestamp)
            
            # Analyze email signature
            signature_analysis = await self.openai_analyzer.analyze_email_signature(
                recent_interaction.content_preview
            )
            
            # Analyze relationship type
            relationship_analysis = await self.openai_analyzer.analyze_relationship_type(
                contact, recent_interaction
            )
            
            # Analyze communication patterns
            comm_analysis = await self.openai_analyzer.analyze_communication_patterns(
                recent_interaction
            )
            
            # Update contact with AI analysis
            ai_data = {
                'signature_analysis': signature_analysis,
                'relationship_analysis': relationship_analysis,
                'communication_patterns': comm_analysis
            }
            
            contact.update_ai_analysis(ai_data)
            
        except Exception as e:
            self.logger.error(f"AI analysis failed for {contact.email}: {e}")
    
    async def _perform_nlp_analysis(self, contact: Contact):
        """Perform NLP analysis using Hugging Face models"""
        if not self.nlp_engine or not contact.interactions:
            return
        
        try:
            # Analyze recent interactions
            recent_interactions = sorted(contact.interactions, key=lambda x: x.timestamp, reverse=True)[:5]
            
            sentiment_results = []
            emotion_results = []
            classification_results = []
            
            for interaction in recent_interactions:
                if interaction.content_preview:
                    # Sentiment analysis
                    sentiment = await self.nlp_engine.analyze_sentiment(interaction.content_preview)
                    if sentiment:
                        sentiment_results.append(sentiment)
                        # Update interaction with sentiment
                        interaction.sentiment = sentiment['sentiment']
                        interaction.sentiment_score = sentiment['confidence']
                    
                    # Emotion detection
                    emotions = await self.nlp_engine.detect_emotions(interaction.content_preview)
                    if emotions:
                        emotion_results.append(emotions)
                        # Update interaction with emotions
                        interaction.emotions = emotions.get('emotion_scores', {})
                    
                    # Email classification
                    classification = await self.nlp_engine.classify_email_content(
                        interaction.subject, interaction.content_preview
                    )
                    if classification:
                        classification_results.append(classification)
                        interaction.category = classification.get('primary_category', '')
            
         

            # Perform contact categorization
            if recent_interactions:
                sample_interaction = recent_interactions[0].content_preview[:200]
                categorization = await self.nlp_engine.categorize_contact(contact, sample_interaction)
                
                if categorization:
                    # Update contact type based on categorization
                    category_mapping = {
                        'customer': 'business',
                        'prospect': 'business', 
                        'personal': 'personal',
                        'vendor': 'business',
                        'partner': 'business',
                        'other': 'other'
                    }
                    contact_type = categorization.get('contact_type', 'other').lower()
                    contact.contact_type = category_mapping.get(contact_type, 'other')
        except Exception as e:
            self.logger.error(f"NLP analysis failed for {contact.email}: {e}")

    async def _perform_smart_inference(self, contact: Contact):
        """Perform smart inference and validation (stub for now)"""
        # Example: infer location from email domain, validate phone, etc.
        try:
            # Placeholder for smart inference logic
            pass
        except Exception as e:
            self.logger.error(f"Smart inference failed for {contact.email}: {e}")

    def _apply_cached_enrichment(self, contact: Contact, cached_result: Dict[str, Any], source_name: str):
        """Apply cached enrichment data to contact"""
        try:
            contact.update_enrichment_data(
                cached_result,
                getattr(EnrichmentSource, source_name.upper(), EnrichmentSource.MOCK_DATA),
                1.0  # Confidence for cached data
            )
        except Exception as e:
            self.logger.error(f"Failed to apply cached enrichment for {contact.email}: {e}")

    def _reset_stats(self):
        """Reset enrichment statistics"""
        self.stats = {
            'total_processed': 0,
            'successful_enrichments': 0,
            'cache_hits': 0,
            'api_calls': 0,
            'total_cost': 0.0,
            'processing_time': 0.0,
            'source_stats': {},
            'ai_analysis_count': 0,
            'nlp_analysis_count': 0
        }

    def _estimate_enrichment_cost(self, num_contacts: int) -> float:
        """Estimate the cost of enriching a given number of contacts"""
        # Simple estimation: use max cost per contact
        return num_contacts * self.max_cost_per_contact

    def _print_enrichment_summary(self):
        """Print a summary of the enrichment process"""
        self.logger.info("Enrichment Summary:")
        self.logger.info(f"Total processed: {self.stats['total_processed']}")
        self.logger.info(f"Successful enrichments: {self.stats['successful_enrichments']}")
        self.logger.info(f"Cache hits: {self.stats['cache_hits']}")
        self.logger.info(f"API calls: {self.stats['api_calls']}")
        self.logger.info(f"Total cost: ${self.stats['total_cost']:.2f}")
        self.logger.info(f"Processing time: {self.stats['processing_time']:.2f} seconds")
        self.logger.info(f"Source stats: {self.stats['source_stats']}")
        self.logger.info(f"AI analysis count: {self.stats['ai_analysis_count']}")
        self.logger.info(f"NLP analysis count: {self.stats['nlp_analysis_count']}")