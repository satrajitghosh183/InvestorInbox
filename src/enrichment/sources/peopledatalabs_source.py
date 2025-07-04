"""
People Data Labs API Integration
Comprehensive B2B people and company data
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

class PeopleDataLabsSource:
    """
    People Data Labs enrichment source
    Provides comprehensive people data including:
    - Personal and work emails
    - Phone numbers
    - Professional history
    - Education information
    - Social profiles
    - Location data
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config_manager = get_config_manager()
        self.source_config = self.config_manager.get_source_config('peopledatalabs')
        
        if not self.source_config:
            raise EnrichmentError("People Data Labs configuration not found")
        
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
                    'X-Api-Key': self.api_key,
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
        """Check if PDL source is enabled and configured"""
        return (self.source_config.enabled and 
                bool(self.api_key) and 
                self.api_key.strip() != "")
    
    async def enrich_contact(self, contact: Contact) -> EnrichmentResult:
        """
        Enrich a contact using People Data Labs Person Enrichment API
        
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
                source=EnrichmentSource.PEOPLEDATALABS,
                error_message="People Data Labs not enabled or configured"
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
                    source=EnrichmentSource.PEOPLEDATALABS,
                    error_message="No data found for email",
                    cost=self.cost_per_request,
                    processing_time=time.time() - start_time,
                    api_calls_used=1
                )
            
            # Process the enrichment data
            processed_data = self._process_pdl_response(enrichment_data)
            
            # Update contact with enriched data
            contact.update_enrichment_data(
                data=processed_data,
                source=EnrichmentSource.PEOPLEDATALABS,
                confidence=self.source_config.confidence_score,
                cost=self.cost_per_request
            )
            
            processing_time = time.time() - start_time
            
            self.logger.info(f"Successfully enriched {contact.email} with People Data Labs")
            
            return EnrichmentResult(
                success=True,
                contact=contact,
                source=EnrichmentSource.PEOPLEDATALABS,
                data_added=processed_data,
                confidence=self.source_config.confidence_score,
                cost=self.cost_per_request,
                processing_time=processing_time,
                api_calls_used=1
            )
            
        except RateLimitError as e:
            self.logger.warning(f"PDL rate limit hit: {e}")
            return EnrichmentResult(
                success=False,
                contact=contact,
                source=EnrichmentSource.PEOPLEDATALABS,
                error_message=f"Rate limit exceeded: {e}",
                processing_time=time.time() - start_time
            )
            
        except AuthenticationError as e:
            self.logger.error(f"PDL authentication failed: {e}")
            return EnrichmentResult(
                success=False,
                contact=contact,
                source=EnrichmentSource.PEOPLEDATALABS,
                error_message=f"Authentication failed: {e}",
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            self.logger.error(f"PDL enrichment failed for {contact.email}: {e}")
            return EnrichmentResult(
                success=False,
                contact=contact,
                source=EnrichmentSource.PEOPLEDATALABS,
                error_message=str(e),
                processing_time=time.time() - start_time
            )
    
    async def _fetch_person_data(self, email: str) -> Optional[Dict[str, Any]]:
        """Fetch person data from PDL Person Enrichment API"""
        if not self.session:
            raise EnrichmentError("Session not initialized")
        
        url = f"{self.base_url}/person/enrich"
        
        params = {
            'email': email,
            'pretty': 'true'
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                self._update_rate_limiting()
                
                if response.status == 200:
                    data = await response.json()
                    
                    # Check if we got actual data
                    if data.get('status') == 200 and data.get('data'):
                        return data['data']
                    else:
                        self.logger.debug(f"No PDL data found for {email}")
                        return None
                
                elif response.status == 404:
                    # Person not found - not an error
                    self.logger.debug(f"No PDL data found for {email}")
                    return None
                
                elif response.status == 401:
                    raise AuthenticationError("Invalid People Data Labs API key", "peopledatalabs")
                
                elif response.status == 402:
                    raise EnrichmentError("PDL quota exceeded")
                
                elif response.status == 429:
                    # Rate limit exceeded
                    retry_after = int(response.headers.get('Retry-After', 3600))
                    raise RateLimitError(
                        "People Data Labs rate limit exceeded",
                        "peopledatalabs",
                        retry_after=retry_after
                    )
                
                else:
                    error_text = await response.text()
                    raise EnrichmentError(f"PDL API error {response.status}: {error_text}")
                    
        except aiohttp.ClientError as e:
            raise EnrichmentError(f"Network error calling PDL: {e}")
    
    def _process_pdl_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process PDL API response into standardized format"""
        result = {}
        
        # Basic person information
        if data.get('full_name'):
            result['name'] = data['full_name']
            
            # Split name into first and last
            name_parts = data['full_name'].split()
            if len(name_parts) >= 2:
                result['first_name'] = name_parts[0]
                result['last_name'] = ' '.join(name_parts[1:])
        
        # Alternative approach using first_name and last_name fields
        if not result.get('name'):
            first_name = data.get('first_name', '')
            last_name = data.get('last_name', '')
            if first_name or last_name:
                result['name'] = f"{first_name} {last_name}".strip()
                result['first_name'] = first_name
                result['last_name'] = last_name
        
        # Location information
        if data.get('location_names') and isinstance(data['location_names'], list):
            # Take the first location as primary
            result['location'] = data['location_names'][0]
        elif data.get('location_name'):
            result['location'] = data['location_name']
        
        # Location details
        if data.get('location_country'):
            result['country'] = data['location_country']
        if data.get('location_region'):
            result['region'] = data['location_region']
        if data.get('location_locality'):
            result['city'] = data['location_locality']
        
        # Job information
        if data.get('job_title'):
            result['job_title'] = data['job_title']
        
        if data.get('job_company_name'):
            result['company'] = data['job_company_name']
        
        if data.get('job_title_levels') and isinstance(data['job_title_levels'], list):
            # Map PDL seniority levels to our standard levels
            pdl_levels = data['job_title_levels']
            if 'owner' in pdl_levels or 'c_suite' in pdl_levels:
                result['seniority_level'] = 'Executive'
            elif 'director' in pdl_levels or 'vp' in pdl_levels:
                result['seniority_level'] = 'Director'
            elif 'manager' in pdl_levels:
                result['seniority_level'] = 'Manager'
            elif 'senior' in pdl_levels:
                result['seniority_level'] = 'Senior'
            else:
                result['seniority_level'] = 'Individual Contributor'
        
        # Experience and career info
        if data.get('inferred_years_experience'):
            result['years_experience'] = data['inferred_years_experience']
        
        if data.get('industry'):
            result['industry'] = data['industry']
        
        # Contact information
        phone_numbers = []
        if data.get('phone_numbers') and isinstance(data['phone_numbers'], list):
            phone_numbers = data['phone_numbers']
        elif data.get('mobile_phone'):
            phone_numbers.append(data['mobile_phone'])
        
        if phone_numbers:
            result['phone_numbers'] = phone_numbers
        
        # Email information
        emails = []
        if data.get('personal_emails') and isinstance(data['personal_emails'], list):
            emails.extend(data['personal_emails'])
        if data.get('work_emails') and isinstance(data['work_emails'], list):
            emails.extend(data['work_emails'])
        
        if emails:
            # Remove the primary email and add others as alternatives
            primary_email = data.get('emails', [{}])[0].get('address', '') if data.get('emails') else ''
            alternative_emails = [email for email in emails if email != primary_email]
            if alternative_emails:
                result['alternative_emails'] = alternative_emails
        
        # Social profiles
        social_profiles = []
        
        if data.get('linkedin_url'):
            linkedin_username = data['linkedin_url'].split('/')[-1] if data['linkedin_url'] else ''
            result['linkedin_url'] = data['linkedin_url']
            social_profiles.append({
                'platform': 'linkedin',
                'url': data['linkedin_url'],
                'username': linkedin_username
            })
        
        if data.get('twitter_url'):
            twitter_username = data['twitter_url'].split('/')[-1] if data['twitter_url'] else ''
            result['twitter_handle'] = twitter_username
            social_profiles.append({
                'platform': 'twitter',
                'url': data['twitter_url'],
                'username': twitter_username
            })
        
        if data.get('github_url'):
            github_username = data['github_url'].split('/')[-1] if data['github_url'] else ''
            result['github_username'] = github_username
            social_profiles.append({
                'platform': 'github',
                'url': data['github_url'],
                'username': github_username
            })
        
        if data.get('facebook_url'):
            social_profiles.append({
                'platform': 'facebook',
                'url': data['facebook_url'],
                'username': data['facebook_url'].split('/')[-1] if data['facebook_url'] else ''
            })
        
        if social_profiles:
            result['social_profiles'] = social_profiles
        
        # Education information
        if data.get('education') and isinstance(data['education'], list):
            education_list = []
            for edu in data['education']:
                education_info = {}
                if edu.get('school', {}).get('name'):
                    education_info['institution'] = edu['school']['name']
                if edu.get('degrees'):
                    education_info['degree'] = ', '.join(edu['degrees'])
                if edu.get('majors'):
                    education_info['major'] = ', '.join(edu['majors'])
                if edu.get('end_date'):
                    education_info['graduation_year'] = edu['end_date']
                
                if education_info:
                    education_list.append(education_info)
            
            if education_list:
                result['education'] = education_list
                
                # Use most recent education for primary fields
                latest_edu = education_list[0] if education_list else {}
                if latest_edu.get('institution'):
                    result['education_institution'] = latest_edu['institution']
                if latest_edu.get('degree'):
                    result['education_degree'] = latest_edu['degree']
        
        # Work experience
        if data.get('experience') and isinstance(data['experience'], list):
            experience_list = []
            for exp in data['experience']:
                experience_info = {}
                if exp.get('company', {}).get('name'):
                    experience_info['company'] = exp['company']['name']
                if exp.get('title'):
                    experience_info['title'] = exp['title']
                if exp.get('start_date'):
                    experience_info['start_date'] = exp['start_date']
                if exp.get('end_date'):
                    experience_info['end_date'] = exp['end_date']
                if exp.get('summary'):
                    experience_info['description'] = exp['summary']
                
                if experience_info:
                    experience_list.append(experience_info)
            
            if experience_list:
                result['work_experience'] = experience_list
        
        # Skills and interests
        if data.get('skills') and isinstance(data['skills'], list):
            result['skills'] = data['skills']
        
        if data.get('interests') and isinstance(data['interests'], list):
            result['interests'] = data['interests']
        
        # Demographics
        if data.get('gender'):
            result['gender'] = data['gender']
        
        if data.get('birth_year'):
            result['birth_year'] = data['birth_year']
            # Calculate age range
            current_year = datetime.now().year
            age = current_year - data['birth_year']
            result['age_range'] = f"{age-2}-{age+2}"  # Give a range for privacy
        
        # Estimate net worth based on PDL data
        result['estimated_net_worth'] = self._estimate_net_worth_from_pdl(data)
        
        # Calculate confidence score based on data completeness
        confidence_factors = []
        if result.get('name'):
            confidence_factors.append(0.2)
        if result.get('job_title'):
            confidence_factors.append(0.2)
        if result.get('company'):
            confidence_factors.append(0.2)
        if result.get('location'):
            confidence_factors.append(0.1)
        if result.get('linkedin_url'):
            confidence_factors.append(0.1)
        if result.get('phone_numbers'):
            confidence_factors.append(0.1)
        if result.get('years_experience'):
            confidence_factors.append(0.1)
        
        result['data_confidence'] = sum(confidence_factors)
        
        # Add raw data for reference
        result['_raw_pdl_data'] = data
        
        return result
    
    def _estimate_net_worth_from_pdl(self, data: Dict[str, Any]) -> str:
        """Estimate net worth based on PDL professional data"""
        score = 0
        
        # Job title analysis
        job_title = data.get('job_title', '').lower()
        if any(exec in job_title for exec in ['ceo', 'founder', 'president', 'chief']):
            score += 4
        elif any(senior in job_title for senior in ['vp', 'director', 'head']):
            score += 3
        elif 'senior' in job_title or 'principal' in job_title:
            score += 2
        elif 'manager' in job_title:
            score += 1
        
        # Seniority levels
        title_levels = data.get('job_title_levels', [])
        if 'owner' in title_levels or 'c_suite' in title_levels:
            score += 3
        elif 'director' in title_levels or 'vp' in title_levels:
            score += 2
        elif 'manager' in title_levels:
            score += 1
        
        # Experience factor
        years_exp = data.get('inferred_years_experience', 0)
        if years_exp > 15:
            score += 2
        elif years_exp > 10:
            score += 1.5
        elif years_exp > 5:
            score += 1
        
        # Company factor (if available)
        company = data.get('job_company_name', '').lower()
        if any(big_tech in company for big_tech in ['google', 'apple', 'microsoft', 'amazon', 'meta']):
            score += 2
        elif 'unicorn' in company or any(unicorn in company for unicorn in ['uber', 'airbnb', 'stripe']):
            score += 1.5
        
        # Education factor
        education = data.get('education', [])
        if education:
            for edu in education:
                school = edu.get('school', {}).get('name', '').lower()
                if any(ivy in school for ivy in ['harvard', 'stanford', 'mit', 'yale', 'princeton']):
                    score += 1
                    break
        
        # Location factor
        location = data.get('location_name', '').lower()
        if any(expensive_city in location for expensive_city in ['san francisco', 'new york', 'london', 'zurich']):
            score += 1
        elif any(tech_hub in location for tech_hub in ['seattle', 'boston', 'austin', 'singapore']):
            score += 0.5
        
        # Convert score to net worth range
        if score >= 8:
            return "$5M - $10M+"
        elif score >= 6:
            return "$2.5M - $5M"
        elif score >= 5:
            return "$1M - $2.5M"
        elif score >= 4:
            return "$500K - $1M"
        elif score >= 3:
            return "$250K - $500K"
        elif score >= 2:
            return "$150K - $300K"
        else:
            return "$100K - $200K"
    
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
                f"PDL hourly rate limit ({self.rate_limit}) exceeded",
                "peopledatalabs",
                retry_after=int(wait_time)
            )
        
        # Minimum delay between requests
        min_delay = 0.1  # 100ms between requests
        if self.last_request_time > 0:
            elapsed = current_time - self.last_request_time
            if elapsed < min_delay:
                await asyncio.sleep(min_delay - elapsed)
    
    def _update_rate_limiting(self):
        """Update rate limiting counters"""
        self.last_request_time = time.time()
        self.requests_this_hour += 1
    
    async def search_contacts(self, search_criteria: Dict[str, Any], max_results: int = 100) -> List[Dict[str, Any]]:
        """
        Search for contacts using PDL Person Search API
        
        Args:
            search_criteria: Search parameters (company, title, location, etc.)
            max_results: Maximum number of results to return
            
        Returns:
            List of contact data dictionaries
        """
        if not self.is_enabled():
            raise EnrichmentError("People Data Labs not enabled or configured")
        
        if not self.session:
            raise EnrichmentError("Session not initialized")
        
        url = f"{self.base_url}/person/search"
        
        # Build search query
        query_parts = []
        
        if search_criteria.get('company'):
            query_parts.append(f"job_company_name:\"{search_criteria['company']}\"")
        
        if search_criteria.get('title'):
            query_parts.append(f"job_title:\"{search_criteria['title']}\"")
        
        if search_criteria.get('location'):
            query_parts.append(f"location_name:\"{search_criteria['location']}\"")
        
        if search_criteria.get('industry'):
            query_parts.append(f"industry:\"{search_criteria['industry']}\"")
        
        if search_criteria.get('seniority'):
            query_parts.append(f"job_title_levels:\"{search_criteria['seniority']}\"")
        
        if not query_parts:
            raise EnrichmentError("No search criteria provided")
        
        params = {
            'sql': f"SELECT * FROM person WHERE {' AND '.join(query_parts)}",
            'size': min(max_results, 100),  # PDL limits to 100 per request
            'pretty': 'true'
        }
        
        try:
            await self._check_rate_limits()
            
            async with self.session.get(url, params=params) as response:
                self._update_rate_limiting()
                
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get('status') == 200 and data.get('data'):
                        return data['data']
                    else:
                        return []
                
                elif response.status == 401:
                    raise AuthenticationError("Invalid People Data Labs API key", "peopledatalabs")
                
                elif response.status == 429:
                    retry_after = int(response.headers.get('Retry-After', 3600))
                    raise RateLimitError(
                        "People Data Labs rate limit exceeded",
                        "peopledatalabs",
                        retry_after=retry_after
                    )
                
                else:
                    error_text = await response.text()
                    raise EnrichmentError(f"PDL Search API error {response.status}: {error_text}")
                    
        except aiohttp.ClientError as e:
            raise EnrichmentError(f"Network error calling PDL Search: {e}")
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test PDL API connection"""
        if not self.is_enabled():
            return {
                'success': False,
                'error': 'People Data Labs not enabled or configured'
            }
        
        try:
            # Test with a simple search query
            async with self:
                url = f"{self.base_url}/person/search"
                params = {
                    'sql': 'SELECT * FROM person WHERE job_company_name="Google" LIMIT 1',
                    'pretty': 'true'
                }
                
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        return {
                            'success': True,
                            'message': 'People Data Labs API connection successful',
                            'rate_limit': self.rate_limit,
                            'cost_per_request': self.cost_per_request
                        }
                    else:
                        error_text = await response.text()
                        return {
                            'success': False,
                            'error': f"API test failed: {response.status} - {error_text}"
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
            'name': 'People Data Labs',
            'description': 'Comprehensive B2B people and company data',
            'confidence_score': self.source_config.confidence_score,
            'cost_per_request': self.cost_per_request,
            'rate_limit_per_hour': self.rate_limit,
            'enabled': self.is_enabled(),
            'data_points': [
                'Full name and demographics',
                'Job title and seniority',
                'Company and industry',
                'Location data',
                'Contact information (email, phone)',
                'Social profiles (LinkedIn, Twitter, GitHub)',
                'Education history',
                'Work experience',
                'Skills and interests'
            ],
            'use_cases': [
                'Lead generation',
                'Contact enrichment',
                'Market research',
                'Talent sourcing',
                'Sales intelligence'
            ],
            'data_sources': '1.5+ billion person profiles',
            'coverage': 'Global with strong US/EU coverage'
        }