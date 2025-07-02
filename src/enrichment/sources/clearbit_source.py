"""
Clearbit Person API Integration
Premium B2B data enrichment with high accuracy
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

class ClearbitEnrichmentSource:
    """
    Clearbit Person API enrichment source
    Provides high-quality B2B contact data including:
    - Professional information (job title, company, seniority)
    - Location data (city, state, country)
    - Social profiles (LinkedIn, Twitter, GitHub)
    - Company information and technographics
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config_manager = get_config_manager()
        self.source_config = self.config_manager.get_source_config('clearbit')
        
        if not self.source_config:
            raise EnrichmentError("Clearbit configuration not found")
        
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
        """Check if Clearbit source is enabled and configured"""
        return (self.source_config.enabled and 
                bool(self.api_key) and 
                self.api_key.strip() != "")
    
    async def enrich_contact(self, contact: Contact) -> EnrichmentResult:
        """
        Enrich a contact using Clearbit Person API
        
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
                source=EnrichmentSource.CLEARBIT,
                error_message="Clearbit not enabled or configured"
            )
        
        try:
            # Rate limiting check
            await self._check_rate_limits()
            
            # Make API request
            enrichment_data = await self._fetch_person_data(contact.email)
            
            if not enrichment_data:
                return EnrichmentResult(
                    success=False,
                    contact=contact,
                    source=EnrichmentSource.CLEARBIT,
                    error_message="No data found for email",
                    cost=self.cost_per_request,
                    processing_time=time.time() - start_time,
                    api_calls_used=1
                )
            
            # Process the enrichment data
            processed_data = self._process_clearbit_response(enrichment_data)
            
            # Update contact with enriched data
            contact.update_enrichment_data(
                data=processed_data,
                source=EnrichmentSource.CLEARBIT,
                confidence=self.source_config.confidence_score,
                cost=self.cost_per_request
            )
            
            processing_time = time.time() - start_time
            
            self.logger.info(f"Successfully enriched {contact.email} with Clearbit")
            
            return EnrichmentResult(
                success=True,
                contact=contact,
                source=EnrichmentSource.CLEARBIT,
                data_added=processed_data,
                confidence=self.source_config.confidence_score,
                cost=self.cost_per_request,
                processing_time=processing_time,
                api_calls_used=1
            )
            
        except RateLimitError as e:
            self.logger.warning(f"Clearbit rate limit hit: {e}")
            return EnrichmentResult(
                success=False,
                contact=contact,
                source=EnrichmentSource.CLEARBIT,
                error_message=f"Rate limit exceeded: {e}",
                processing_time=time.time() - start_time
            )
            
        except AuthenticationError as e:
            self.logger.error(f"Clearbit authentication failed: {e}")
            return EnrichmentResult(
                success=False,
                contact=contact,
                source=EnrichmentSource.CLEARBIT,
                error_message=f"Authentication failed: {e}",
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            self.logger.error(f"Clearbit enrichment failed for {contact.email}: {e}")
            return EnrichmentResult(
                success=False,
                contact=contact,
                source=EnrichmentSource.CLEARBIT,
                error_message=str(e),
                processing_time=time.time() - start_time
            )
    
    async def _fetch_person_data(self, email: str) -> Optional[Dict[str, Any]]:
        """Fetch person data from Clearbit API"""
        if not self.session:
            raise EnrichmentError("Session not initialized")
        
        url = f"{self.base_url}?email={email}"
        
        auth = aiohttp.BasicAuth(self.api_key, '')
        
        try:
            async with self.session.get(url, auth=auth) as response:
                self._update_rate_limiting()
                
                if response.status == 200:
                    data = await response.json()
                    return data
                
                elif response.status == 202:
                    # Clearbit is processing the request
                    self.logger.info(f"Clearbit is processing request for {email}")
                    await asyncio.sleep(2)  # Wait a bit and try again
                    
                    async with self.session.get(url, auth=auth) as retry_response:
                        if retry_response.status == 200:
                            data = await retry_response.json()
                            return data
                        elif retry_response.status == 404:
                            self.logger.debug(f"No Clearbit data found for {email}")
                            return None
                        else:
                            self.logger.warning(f"Clearbit retry failed: {retry_response.status}")
                            return None
                
                elif response.status == 404:
                    # Person not found - not an error
                    self.logger.debug(f"No Clearbit data found for {email}")
                    return None
                
                elif response.status == 401:
                    raise AuthenticationError("Invalid Clearbit API key", "clearbit")
                
                elif response.status == 402:
                    raise EnrichmentError("Clearbit quota exceeded")
                
                elif response.status == 422:
                    raise EnrichmentError(f"Invalid email format: {email}")
                
                elif response.status == 429:
                    # Rate limit exceeded
                    retry_after = int(response.headers.get('Retry-After', 3600))
                    raise RateLimitError(
                        "Clearbit rate limit exceeded",
                        "clearbit",
                        retry_after=retry_after
                    )
                
                else:
                    error_text = await response.text()
                    raise EnrichmentError(f"Clearbit API error {response.status}: {error_text}")
                    
        except aiohttp.ClientError as e:
            raise EnrichmentError(f"Network error calling Clearbit: {e}")
    
    def _process_clearbit_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process Clearbit API response into standardized format"""
        result = {}
        
        # Basic person information
        if data.get('name'):
            name_parts = data['name'].get('fullName', '').split()
            if len(name_parts) >= 2:
                result['first_name'] = name_parts[0]
                result['last_name'] = ' '.join(name_parts[1:])
                result['name'] = data['name']['fullName']
        
        # Location information
        if data.get('location'):
            location_parts = []
            location_data = data['location']
            
            if location_data.get('city'):
                location_parts.append(location_data['city'])
            if location_data.get('state'):
                location_parts.append(location_data['state'])
            if location_data.get('country'):
                location_parts.append(location_data['country'])
            
            result['location'] = ', '.join(location_parts)
            
            if location_data.get('timeZone'):
                result['timezone'] = location_data['timeZone']
        
        # Employment information
        if data.get('employment'):
            employment = data['employment']
            
            if employment.get('title'):
                result['job_title'] = employment['title']
            
            if employment.get('name'):
                result['company'] = employment['name']
            
            if employment.get('domain'):
                result['company_domain'] = employment['domain']
            
            if employment.get('seniority'):
                result['seniority_level'] = employment['seniority']
            
            if employment.get('role'):
                result['department'] = employment['role']
        
        # Social profiles
        social_profiles = []
        
        if data.get('linkedin'):
            linkedin_data = data['linkedin']
            if linkedin_data.get('handle'):
                result['linkedin_url'] = f"https://linkedin.com/in/{linkedin_data['handle']}"
                social_profiles.append({
                    'platform': 'linkedin',
                    'url': result['linkedin_url'],
                    'username': linkedin_data['handle']
                })
        
        if data.get('twitter'):
            twitter_data = data['twitter']
            if twitter_data.get('handle'):
                result['twitter_handle'] = twitter_data['handle']
                social_profiles.append({
                    'platform': 'twitter',
                    'url': f"https://twitter.com/{twitter_data['handle']}",
                    'username': twitter_data['handle'],
                    'followers': twitter_data.get('followers', 0)
                })
        
        if data.get('github'):
            github_data = data['github']
            if github_data.get('handle'):
                result['github_username'] = github_data['handle']
                social_profiles.append({
                    'platform': 'github',
                    'url': f"https://github.com/{github_data['handle']}",
                    'username': github_data['handle'],
                    'followers': github_data.get('followers', 0)
                })
        
        if social_profiles:
            result['social_profiles'] = social_profiles
        
        # Additional contact information
        if data.get('email'):
            result['email_verified'] = True
        
        if data.get('phone'):
            result['phone_numbers'] = [data['phone']]
        
        # Estimate net worth based on employment data
        result['estimated_net_worth'] = self._estimate_net_worth_from_clearbit(data)
        
        # Industry classification
        if data.get('employment', {}).get('name'):
            result['industry'] = self._classify_industry_from_company(
                data['employment']['name']
            )
        
        # Add raw data for reference
        result['_raw_clearbit_data'] = data
        
        return result
    
    def _estimate_net_worth_from_clearbit(self, data: Dict[str, Any]) -> str:
        """Estimate net worth based on Clearbit employment data"""
        score = 0
        
        employment = data.get('employment', {})
        
        # Job title scoring
        title = employment.get('title', '').lower()
        if any(exec_term in title for exec_term in ['ceo', 'founder', 'president', 'chief']):
            score += 4
        elif any(vp_term in title for vp_term in ['vp', 'vice president', 'director']):
            score += 3
        elif any(senior_term in title for senior_term in ['senior', 'principal', 'lead']):
            score += 2
        elif 'manager' in title:
            score += 1
        
        # Company factor
        company = employment.get('name', '').lower()
        if any(big_tech in company for big_tech in ['google', 'apple', 'microsoft', 'amazon', 'meta']):
            score += 2
        elif any(unicorn in company for unicorn in ['uber', 'airbnb', 'stripe', 'spacex']):
            score += 1.5
        
        # Seniority level
        seniority = employment.get('seniority', '').lower()
        if 'executive' in seniority:
            score += 2
        elif 'senior' in seniority:
            score += 1
        
        # Location factor (rough cost of living adjustment)
        location = data.get('location', {})
        city = location.get('city', '').lower()
        if city in ['san francisco', 'new york', 'london', 'zurich']:
            score += 1
        elif city in ['seattle', 'boston', 'los angeles', 'singapore']:
            score += 0.5
        
        # Convert score to net worth range
        if score >= 7:
            return "$5M - $10M+"
        elif score >= 5:
            return "$2.5M - $5M"
        elif score >= 4:
            return "$1M - $2.5M"
        elif score >= 3:
            return "$500K - $1M"
        elif score >= 2:
            return "$250K - $500K"
        else:
            return "$100K - $250K"
    
    def _classify_industry_from_company(self, company_name: str) -> str:
        """Classify industry based on company name"""
        company_lower = company_name.lower()
        
        # Technology companies
        tech_keywords = ['tech', 'software', 'digital', 'cloud', 'ai', 'data', 'cyber']
        if any(keyword in company_lower for keyword in tech_keywords):
            return "Technology"
        
        # Financial services
        finance_keywords = ['bank', 'financial', 'capital', 'investment', 'fund', 'trading']
        if any(keyword in company_lower for keyword in finance_keywords):
            return "Financial Services"
        
        # Healthcare
        health_keywords = ['health', 'medical', 'pharma', 'bio', 'hospital', 'clinic']
        if any(keyword in company_lower for keyword in health_keywords):
            return "Healthcare"
        
        # Consulting
        consulting_keywords = ['consulting', 'advisory', 'strategy', 'mckinsey', 'bain', 'bcg']
        if any(keyword in company_lower for keyword in consulting_keywords):
            return "Consulting"
        
        # Manufacturing
        manufacturing_keywords = ['manufacturing', 'automotive', 'industrial', 'aerospace']
        if any(keyword in company_lower for keyword in manufacturing_keywords):
            return "Manufacturing"
        
        # Media and entertainment
        media_keywords = ['media', 'entertainment', 'content', 'publishing', 'news']
        if any(keyword in company_lower for keyword in media_keywords):
            return "Media & Entertainment"
        
        # Default
        return "Business Services"
    
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
                f"Clearbit hourly rate limit ({self.rate_limit}) exceeded",
                "clearbit",
                retry_after=int(wait_time)
            )
        
        # Minimum delay between requests (to be respectful)
        min_delay = 1.0  # 1 second between requests
        if self.last_request_time > 0:
            elapsed = current_time - self.last_request_time
            if elapsed < min_delay:
                await asyncio.sleep(min_delay - elapsed)
    
    def _update_rate_limiting(self):
        """Update rate limiting counters"""
        self.last_request_time = time.time()
        self.requests_this_hour += 1
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test Clearbit API connection"""
        if not self.is_enabled():
            return {
                'success': False,
                'error': 'Clearbit not enabled or configured'
            }
        
        try:
            # Test with a known email (we'll use a test email)
            test_email = "test@clearbit.com"
            
            async with self:
                result = await self._fetch_person_data(test_email)
                
                return {
                    'success': True,
                    'message': 'Clearbit API connection successful',
                    'rate_limit': self.rate_limit,
                    'cost_per_request': self.cost_per_request
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
            'name': 'Clearbit',
            'description': 'Premium B2B contact and company data',
            'confidence_score': self.source_config.confidence_score,
            'cost_per_request': self.cost_per_request,
            'rate_limit_per_hour': self.rate_limit,
            'enabled': self.is_enabled(),
            'data_points': [
                'Full name',
                'Job title and seniority',
                'Company information',
                'Location (city, state, country)',
                'Social profiles (LinkedIn, Twitter, GitHub)',
                'Phone numbers',
                'Industry classification'
            ],
            'use_cases': [
                'Lead qualification',
                'Account enrichment',
                'Personalization data',
                'Market research'
            ]
        }