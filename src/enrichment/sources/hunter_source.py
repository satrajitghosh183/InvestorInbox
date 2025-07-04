"""
Hunter.io API Integration
Email finder and domain search for contact enrichment
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

class HunterIOSource:
    """
    Hunter.io enrichment source
    Provides email finder and verification services including:
    - Email verification and deliverability
    - Domain-based email discovery
    - Company information from domains
    - Email pattern detection
    - Professional email validation
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config_manager = get_config_manager()
        self.source_config = self.config_manager.get_source_config('hunter')
        
        if not self.source_config:
            raise EnrichmentError("Hunter.io configuration not found")
        
        # self.api_key = self.source_config.api_key
        # self.base_url = self.source_config.base_url
        # self.rate_limit = self.source_config.rate_limit
        # self.cost_per_request = self.source_config.cost_per_request
        self.api_key = self.source_config['api_key']
        self.base_url = self.source_config['base_url']
        self.rate_limit = self.source_config['rate_limit']
        self.cost_per_request = self.source_config['cost_per_request']

        
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
                    'User-Agent': 'EmailEnrichment/2.0',
                    'Accept': 'application/json'
                }
            )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
            self.session = None
    
    def is_enabled(self) -> bool:
        """Check if Hunter.io source is enabled and configured"""
        return (self.source_config.enabled and 
                bool(self.api_key) and 
                self.api_key.strip() != "")
    
    async def enrich_contact(self, contact: Contact) -> EnrichmentResult:
        """
        Enrich a contact using Hunter.io APIs
        
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
                source=EnrichmentSource.HUNTER,
                error_message="Hunter.io not enabled or configured"
            )
        
        try:
            # Rate limiting check
            await self._check_rate_limits()
            
            # Try multiple Hunter.io endpoints
            enrichment_data = {}
            
            # 1. Email verification
            if contact.email:
                verification_data = await self._verify_email(contact.email)
                if verification_data:
                    enrichment_data.update(verification_data)
            
            # 2. Domain search for additional contacts and company info
            if contact.domain:
                domain_data = await self._search_domain(contact.domain)
                if domain_data:
                    enrichment_data.update(domain_data)
            
            # 3. Author finder (if we have name and domain)
            if contact.name and contact.domain:
                author_data = await self._find_author(contact.name, contact.domain)
                if author_data:
                    enrichment_data.update(author_data)
            
            if not enrichment_data:
                return EnrichmentResult(
                    success=False,
                    contact=contact,
                    source=EnrichmentSource.HUNTER,
                    error_message="No data found",
                    cost=self.cost_per_request,
                    processing_time=time.time() - start_time,
                    api_calls_used=1
                )
            
            # Process the enrichment data
            processed_data = self._process_hunter_response(enrichment_data)
            
            # Update contact with enriched data
            contact.update_enrichment_data(
                data=processed_data,
                source=EnrichmentSource.HUNTER,
                confidence=self.source_config.confidence_score,
                cost=self.cost_per_request
            )
            
            processing_time = time.time() - start_time
            
            self.logger.info(f"Successfully enriched {contact.email} with Hunter.io")
            
            return EnrichmentResult(
                success=True,
                contact=contact,
                source=EnrichmentSource.HUNTER,
                data_added=processed_data,
                confidence=self.source_config.confidence_score,
                cost=self.cost_per_request,
                processing_time=processing_time,
                api_calls_used=1
            )
            
        except RateLimitError as e:
            self.logger.warning(f"Hunter.io rate limit hit: {e}")
            return EnrichmentResult(
                success=False,
                contact=contact,
                source=EnrichmentSource.HUNTER,
                error_message=f"Rate limit exceeded: {e}",
                processing_time=time.time() - start_time
            )
            
        except AuthenticationError as e:
            self.logger.error(f"Hunter.io authentication failed: {e}")
            return EnrichmentResult(
                success=False,
                contact=contact,
                source=EnrichmentSource.HUNTER,
                error_message=f"Authentication failed: {e}",
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            self.logger.error(f"Hunter.io enrichment failed for {contact.email}: {e}")
            return EnrichmentResult(
                success=False,
                contact=contact,
                source=EnrichmentSource.HUNTER,
                error_message=str(e),
                processing_time=time.time() - start_time
            )
    
    async def _verify_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Verify email using Hunter.io Email Verifier"""
        if not self.session:
            raise EnrichmentError("Session not initialized")
        
        url = f"{self.base_url}/email-verifier"
        params = {
            'email': email,
            'api_key': self.api_key
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                self._update_rate_limiting()
                
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get('data'):
                        verification_data = data['data']
                        return {
                            'email_verification': {
                                'status': verification_data.get('status'),
                                'result': verification_data.get('result'),
                                'score': verification_data.get('score'),
                                'regexp': verification_data.get('regexp'),
                                'gibberish': verification_data.get('gibberish'),
                                'disposable': verification_data.get('disposable'),
                                'webmail': verification_data.get('webmail'),
                                'mx_records': verification_data.get('mx_records'),
                                'smtp_server': verification_data.get('smtp_server'),
                                'smtp_check': verification_data.get('smtp_check'),
                                'accept_all': verification_data.get('accept_all'),
                                'block': verification_data.get('block')
                            }
                        }
                
                elif response.status == 401:
                    raise AuthenticationError("Invalid Hunter.io API key", "hunter")
                
                elif response.status == 429:
                    retry_after = int(response.headers.get('Retry-After', 3600))
                    raise RateLimitError(
                        "Hunter.io rate limit exceeded",
                        "hunter",
                        retry_after=retry_after
                    )
                
                elif response.status == 400:
                    # Invalid email format - not an error for our purposes
                    return None
                
                else:
                    error_text = await response.text()
                    self.logger.warning(f"Hunter.io email verification error {response.status}: {error_text}")
                    return None
                    
        except aiohttp.ClientError as e:
            raise EnrichmentError(f"Network error calling Hunter.io email verifier: {e}")
        
        return None
    
    async def _search_domain(self, domain: str) -> Optional[Dict[str, Any]]:
        """Search domain for company information and email patterns"""
        if not self.session:
            raise EnrichmentError("Session not initialized")
        
        url = f"{self.base_url}/domain-search"
        params = {
            'domain': domain,
            'api_key': self.api_key,
            'limit': 10  # Limit results to avoid excessive data
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                self._update_rate_limiting()
                
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get('data'):
                        domain_data = data['data']
                        return {
                            'domain_info': {
                                'domain': domain_data.get('domain'),
                                'disposable': domain_data.get('disposable'),
                                'webmail': domain_data.get('webmail'),
                                'accept_all': domain_data.get('accept_all'),
                                'pattern': domain_data.get('pattern'),
                                'organization': domain_data.get('organization'),
                                'country': domain_data.get('country'),
                                'state': domain_data.get('state'),
                                'emails': domain_data.get('emails', [])[:5]  # Limit to 5 emails
                            }
                        }
                
                elif response.status == 401:
                    raise AuthenticationError("Invalid Hunter.io API key", "hunter")
                
                elif response.status == 429:
                    retry_after = int(response.headers.get('Retry-After', 3600))
                    raise RateLimitError(
                        "Hunter.io rate limit exceeded",
                        "hunter",
                        retry_after=retry_after
                    )
                
                else:
                    error_text = await response.text()
                    self.logger.warning(f"Hunter.io domain search error {response.status}: {error_text}")
                    return None
                    
        except aiohttp.ClientError as e:
            raise EnrichmentError(f"Network error calling Hunter.io domain search: {e}")
        
        return None
    
    async def _find_author(self, name: str, domain: str) -> Optional[Dict[str, Any]]:
        """Find email author using name and domain"""
        if not self.session:
            raise EnrichmentError("Session not initialized")
        
        url = f"{self.base_url}/email-finder"
        params = {
            'domain': domain,
            'first_name': name.split()[0] if name else '',
            'last_name': ' '.join(name.split()[1:]) if len(name.split()) > 1 else '',
            'api_key': self.api_key
        }
        
        # Skip if we don't have enough name information
        if not params['first_name']:
            return None
        
        try:
            async with self.session.get(url, params=params) as response:
                self._update_rate_limiting()
                
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get('data'):
                        author_data = data['data']
                        return {
                            'author_info': {
                                'email': author_data.get('email'),
                                'first_name': author_data.get('first_name'),
                                'last_name': author_data.get('last_name'),
                                'position': author_data.get('position'),
                                'seniority': author_data.get('seniority'),
                                'department': author_data.get('department'),
                                'linkedin': author_data.get('linkedin'),
                                'twitter': author_data.get('twitter'),
                                'phone_number': author_data.get('phone_number'),
                                'score': author_data.get('score'),
                                'verification': author_data.get('verification')
                            }
                        }
                
                elif response.status == 401:
                    raise AuthenticationError("Invalid Hunter.io API key", "hunter")
                
                elif response.status == 429:
                    retry_after = int(response.headers.get('Retry-After', 3600))
                    raise RateLimitError(
                        "Hunter.io rate limit exceeded",
                        "hunter",
                        retry_after=retry_after
                    )
                
                else:
                    # Author not found is normal
                    return None
                    
        except aiohttp.ClientError as e:
            raise EnrichmentError(f"Network error calling Hunter.io email finder: {e}")
        
        return None
    
    def _process_hunter_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process Hunter.io API response into standardized format"""
        result = {}
        
        # Process email verification data
        if 'email_verification' in data:
            verification = data['email_verification']
            
            # Email quality score
            if verification.get('score') is not None:
                result['email_quality_score'] = verification['score']
            
            # Email deliverability
            if verification.get('result'):
                result['email_deliverable'] = verification['result'] == 'deliverable'
            
            # Email type classification
            if verification.get('webmail'):
                result['email_type'] = 'webmail' if verification['webmail'] else 'corporate'
            
            # Disposable email detection
            if verification.get('disposable'):
                result['is_disposable_email'] = verification['disposable']
            
            # Store full verification data
            result['email_verification_details'] = verification
        
        # Process domain information
        if 'domain_info' in data:
            domain_info = data['domain_info']
            
            # Company information
            if domain_info.get('organization'):
                result['company'] = domain_info['organization']
            
            # Location information
            location_parts = []
            if domain_info.get('state'):
                location_parts.append(domain_info['state'])
            if domain_info.get('country'):
                location_parts.append(domain_info['country'])
            
            if location_parts:
                result['location'] = ', '.join(location_parts)
            
            # Email pattern for the domain
            if domain_info.get('pattern'):
                result['email_pattern'] = domain_info['pattern']
            
            # Company domain characteristics
            if domain_info.get('accept_all') is not None:
                result['domain_accepts_all'] = domain_info['accept_all']
            
            # Related emails from domain
            if domain_info.get('emails'):
                related_emails = []
                for email_data in domain_info['emails']:
                    if isinstance(email_data, dict) and email_data.get('value'):
                        related_emails.append({
                            'email': email_data['value'],
                            'first_name': email_data.get('first_name', ''),
                            'last_name': email_data.get('last_name', ''),
                            'position': email_data.get('position', ''),
                            'seniority': email_data.get('seniority', ''),
                            'department': email_data.get('department', '')
                        })
                
                if related_emails:
                    result['related_emails'] = related_emails
        
        # Process author/finder information
        if 'author_info' in data:
            author_info = data['author_info']
            
            # Professional information
            if author_info.get('position'):
                result['job_title'] = author_info['position']
            
            if author_info.get('seniority'):
                result['seniority_level'] = author_info['seniority'].title()
            
            if author_info.get('department'):
                result['department'] = author_info['department']
            
            # Contact information
            if author_info.get('phone_number'):
                result['phone_numbers'] = [author_info['phone_number']]
            
            # Social profiles
            social_profiles = []
            
            if author_info.get('linkedin'):
                social_profiles.append({
                    'platform': 'linkedin',
                    'url': author_info['linkedin'],
                    'username': author_info['linkedin'].split('/')[-1] if author_info['linkedin'] else ''
                })
                result['linkedin_url'] = author_info['linkedin']
            
            if author_info.get('twitter'):
                social_profiles.append({
                    'platform': 'twitter',
                    'url': f"https://twitter.com/{author_info['twitter']}" if not author_info['twitter'].startswith('http') else author_info['twitter'],
                    'username': author_info['twitter'].replace('@', '').replace('https://twitter.com/', '')
                })
                result['twitter_handle'] = author_info['twitter'].replace('@', '')
            
            if social_profiles:
                result['social_profiles'] = social_profiles
            
            # Hunter.io specific scores
            if author_info.get('score') is not None:
                result['hunter_confidence_score'] = author_info['score']
        
        # Industry inference based on domain and company info
        if result.get('company'):
            result['industry'] = self._infer_industry_from_company(result['company'])
        
        # Data source attribution
        result['enrichment_source'] = 'Hunter.io'
        result['enrichment_timestamp'] = datetime.now().isoformat()
        
        return result
    
    def _infer_industry_from_company(self, company_name: str) -> str:
        """Infer industry from company name"""
        company_lower = company_name.lower()
        
        industry_keywords = {
            'Technology': ['tech', 'software', 'digital', 'app', 'platform', 'cloud', 'ai', 'data'],
            'Finance': ['bank', 'financial', 'capital', 'investment', 'trading', 'fund', 'insurance'],
            'Healthcare': ['health', 'medical', 'pharma', 'bio', 'hospital', 'clinic', 'care'],
            'Education': ['university', 'school', 'education', 'learning', 'academy', 'institute'],
            'Consulting': ['consulting', 'advisory', 'strategy', 'solutions', 'services'],
            'Manufacturing': ['manufacturing', 'industrial', 'production', 'factory', 'automotive'],
            'Retail': ['retail', 'store', 'shop', 'commerce', 'marketplace', 'fashion'],
            'Media': ['media', 'news', 'publishing', 'content', 'entertainment', 'broadcasting'],
            'Real Estate': ['real estate', 'property', 'construction', 'development', 'building'],
            'Legal': ['law', 'legal', 'attorney', 'counsel', 'court']
        }
        
        for industry, keywords in industry_keywords.items():
            if any(keyword in company_lower for keyword in keywords):
                return industry
        
        return 'Other'
    
    async def _check_rate_limits(self):
        """Check and enforce rate limits"""
        current_time = time.time()
        
        # Reset hourly counter if needed
        if current_time - self.hour_start >= 3600:
            self.requests_this_hour = 0
            self.hour_start = current_time
        
        # Check hourly limit
        if self.requests_this_hour >= self.rate_limit:
            wait_time = 3600 - (current_time - self.hour_start)
            raise RateLimitError(
                f"Hunter.io hourly rate limit ({self.rate_limit}) exceeded",
                "hunter",
                retry_after=int(wait_time)
            )
        
        # Minimum delay between requests (Hunter.io recommends this)
        min_delay = 1.0  # 1 second between requests
        if self.last_request_time > 0:
            elapsed = current_time - self.last_request_time
            if elapsed < min_delay:
                await asyncio.sleep(min_delay - elapsed)
    
    def _update_rate_limiting(self):
        """Update rate limiting counters"""
        self.last_request_time = time.time()
        self.requests_this_hour += 1
    
    async def search_company_emails(self, domain: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Search for all emails in a company domain
        
        Args:
            domain: Company domain to search
            limit: Maximum number of emails to return
            
        Returns:
            List of email data dictionaries
        """
        if not self.is_enabled():
            raise EnrichmentError("Hunter.io not enabled or configured")
        
        domain_data = await self._search_domain(domain)
        
        if domain_data and domain_data.get('domain_info', {}).get('emails'):
            return domain_data['domain_info']['emails'][:limit]
        
        return []
    
    async def find_email(self, first_name: str, last_name: str, domain: str) -> Optional[Dict[str, Any]]:
        """
        Find email for a specific person
        
        Args:
            first_name: Person's first name
            last_name: Person's last name
            domain: Company domain
            
        Returns:
            Email finder result or None
        """
        if not self.is_enabled():
            raise EnrichmentError("Hunter.io not enabled or configured")
        
        full_name = f"{first_name} {last_name}".strip()
        author_data = await self._find_author(full_name, domain)
        
        if author_data and author_data.get('author_info'):
            return author_data['author_info']
        
        return None
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test Hunter.io API connection"""
        if not self.is_enabled():
            return {
                'success': False,
                'error': 'Hunter.io not enabled or configured'
            }
        
        try:
            # Test with a simple email verification
            async with self:
                test_email = "test@hunter.io"
                result = await self._verify_email(test_email)
                
                return {
                    'success': True,
                    'message': 'Hunter.io API connection successful',
                    'rate_limit': self.rate_limit,
                    'cost_per_request': self.cost_per_request,
                    'test_result': result is not None
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_cost_estimate(self, contact_count: int) -> Dict[str, float]:
        """Get cost estimate for enriching contacts"""
        return {
            'per_contact': self.cost_per_request,
            'total_cost': contact_count * self.cost_per_request,
            'currency': 'USD'
        }
    
    def get_source_info(self) -> Dict[str, Any]:
        """Get information about this enrichment source"""
        return {
            'name': 'Hunter.io',
            'description': 'Email finder and verification service',
            'confidence_score': self.source_config.confidence_score,
            'cost_per_request': self.cost_per_request,
            'rate_limit_per_hour': self.rate_limit,
            'enabled': self.is_enabled(),
            'data_points': [
                'Email verification and deliverability',
                'Company information from domains',
                'Professional contact details',
                'Email patterns and formats',
                'Related company emails',
                'Social profiles (LinkedIn, Twitter)',
                'Department and seniority information'
            ],
            'use_cases': [
                'Email verification',
                'Lead generation',
                'Contact discovery',
                'Email deliverability checking',
                'Company research'
            ],
            'api_endpoints': [
                'Email Verifier',
                'Domain Search', 
                'Email Finder',
                'Email Count'
            ]
        }