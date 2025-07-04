"""
IP Geolocation and Demographics Service
Location-based enrichment using IP addresses and other signals
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import asyncio
import aiohttp
import logging
import re
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from pathlib import Path

from core.models import Contact
from core.exceptions import EnrichmentError, RateLimitError
from config.config_manager import get_config_manager

class IPGeolocationService:
    """
    IP-based geolocation and demographics service
    Provides location enrichment using multiple data sources:
    - IP geolocation APIs
    - Email header analysis
    - Phone number location lookup
    - Timezone inference
    - Address validation
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config_manager = get_config_manager()
        self.location_config = self.config_manager.get_location_services_config()
        
        # Provider configurations
        self.ip_geolocation_config = self.location_config.get('ip_geolocation', {})
        self.phone_lookup_config = self.location_config.get('phone_lookup', {})
        self.timezone_config = self.location_config.get('timezone_inference', {})
        self.address_config = self.location_config.get('address_validation', {})
        
        # Session for HTTP requests
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Load country and city databases
        self._load_location_databases()
    
    def _load_location_databases(self):
        """Load location reference databases"""
        # Country codes and names
        self.country_codes = {
            'US': 'United States', 'CA': 'Canada', 'GB': 'United Kingdom',
            'DE': 'Germany', 'FR': 'France', 'IT': 'Italy', 'ES': 'Spain',
            'NL': 'Netherlands', 'SE': 'Sweden', 'NO': 'Norway', 'DK': 'Denmark',
            'FI': 'Finland', 'AU': 'Australia', 'NZ': 'New Zealand', 'JP': 'Japan',
            'KR': 'South Korea', 'CN': 'China', 'IN': 'India', 'SG': 'Singapore',
            'HK': 'Hong Kong', 'IL': 'Israel', 'AE': 'United Arab Emirates',
            'CH': 'Switzerland', 'AT': 'Austria', 'BE': 'Belgium', 'LU': 'Luxembourg'
        }
        
        # Major cities and their countries
        self.major_cities = {
            'New York': 'US', 'Los Angeles': 'US', 'Chicago': 'US', 'Houston': 'US',
            'Phoenix': 'US', 'Philadelphia': 'US', 'San Antonio': 'US', 'San Diego': 'US',
            'Dallas': 'US', 'San Jose': 'US', 'Austin': 'US', 'Jacksonville': 'US',
            'San Francisco': 'US', 'Columbus': 'US', 'Indianapolis': 'US', 'Fort Worth': 'US',
            'Charlotte': 'US', 'Seattle': 'US', 'Denver': 'US', 'Washington': 'US',
            'Boston': 'US', 'El Paso': 'US', 'Nashville': 'US', 'Detroit': 'US',
            'Oklahoma City': 'US', 'Portland': 'US', 'Las Vegas': 'US', 'Memphis': 'US',
            'Louisville': 'US', 'Baltimore': 'US', 'Milwaukee': 'US', 'Albuquerque': 'US',
            'Tucson': 'US', 'Fresno': 'US', 'Sacramento': 'US', 'Atlanta': 'US',
            'Miami': 'US', 'Tampa': 'US', 'Orlando': 'US', 'Minneapolis': 'US',
            'Toronto': 'CA', 'Montreal': 'CA', 'Vancouver': 'CA', 'Calgary': 'CA',
            'Ottawa': 'CA', 'Edmonton': 'CA', 'Mississauga': 'CA', 'Winnipeg': 'CA',
            'London': 'GB', 'Birmingham': 'GB', 'Manchester': 'GB', 'Glasgow': 'GB',
            'Liverpool': 'GB', 'Leeds': 'GB', 'Sheffield': 'GB', 'Edinburgh': 'GB',
            'Bristol': 'GB', 'Cardiff': 'GB', 'Belfast': 'GB', 'Leicester': 'GB',
            'Berlin': 'DE', 'Hamburg': 'DE', 'Munich': 'DE', 'Cologne': 'DE',
            'Frankfurt': 'DE', 'Stuttgart': 'DE', 'Düsseldorf': 'DE', 'Dortmund': 'DE',
            'Paris': 'FR', 'Marseille': 'FR', 'Lyon': 'FR', 'Toulouse': 'FR',
            'Nice': 'FR', 'Nantes': 'FR', 'Strasbourg': 'FR', 'Montpellier': 'FR',
            'Tokyo': 'JP', 'Osaka': 'JP', 'Yokohama': 'JP', 'Nagoya': 'JP',
            'Sydney': 'AU', 'Melbourne': 'AU', 'Brisbane': 'AU', 'Perth': 'AU',
            'Singapore': 'SG', 'Hong Kong': 'HK', 'Seoul': 'KR', 'Beijing': 'CN',
            'Shanghai': 'CN', 'Mumbai': 'IN', 'Delhi': 'IN', 'Bangalore': 'IN'
        }
        
        # Timezone mappings
        self.timezone_mappings = {
            'PST': 'America/Los_Angeles', 'PDT': 'America/Los_Angeles',
            'MST': 'America/Denver', 'MDT': 'America/Denver',
            'CST': 'America/Chicago', 'CDT': 'America/Chicago',
            'EST': 'America/New_York', 'EDT': 'America/New_York',
            'GMT': 'Europe/London', 'BST': 'Europe/London',
            'CET': 'Europe/Paris', 'CEST': 'Europe/Paris',
            'JST': 'Asia/Tokyo', 'KST': 'Asia/Seoul',
            'IST': 'Asia/Kolkata', 'CST': 'Asia/Shanghai'
        }
    
    async def __aenter__(self):
        """Async context manager entry"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={'User-Agent': 'EmailEnrichment/2.0'}
            )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def enrich_location_from_ip(self, ip_address: str) -> Dict[str, Any]:
        """
        Enrich location information from IP address
        
        Args:
            ip_address: IP address to geolocate
            
        Returns:
            Dictionary with location information
        """
        if not self._is_valid_ip(ip_address):
            return {}
        
        # Skip private/local IP addresses
        if self._is_private_ip(ip_address):
            return {'location_type': 'private', 'note': 'Private IP address'}
        
        try:
            # Try multiple IP geolocation providers
            location_data = None
            
            # 1. Try IP-API (free tier)
            if not location_data:
                location_data = await self._geolocate_with_ipapi(ip_address)
            
            # 2. Try IPStack (if configured)
            if not location_data and self.ip_geolocation_config.get('api_key'):
                location_data = await self._geolocate_with_ipstack(ip_address)
            
            # 3. Fallback to basic geographic inference
            if not location_data:
                location_data = self._basic_ip_location_inference(ip_address)
            
            return location_data or {}
            
        except Exception as e:
            self.logger.error(f"IP geolocation failed for {ip_address}: {e}")
            return {}
    
    async def _geolocate_with_ipapi(self, ip_address: str) -> Optional[Dict[str, Any]]:
        """Geolocate using IP-API service (free tier)"""
        if not self.session:
            return None
        
        url = f"http://ip-api.com/json/{ip_address}"
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get('status') == 'success':
                        return self._process_ipapi_response(data)
                
        except Exception as e:
            self.logger.warning(f"IP-API geolocation failed: {e}")
        
        return None
    
    async def _geolocate_with_ipstack(self, ip_address: str) -> Optional[Dict[str, Any]]:
        """Geolocate using IPStack service (premium)"""
        if not self.session:
            return None
        
        api_key = self.ip_geolocation_config.get('api_key')
        if not api_key:
            return None
        
        url = f"http://api.ipstack.com/{ip_address}"
        params = {'access_key': api_key}
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if not data.get('error'):
                        return self._process_ipstack_response(data)
                
        except Exception as e:
            self.logger.warning(f"IPStack geolocation failed: {e}")
        
        return None
    
    def _process_ipapi_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process IP-API response"""
        result = {}
        
        # Location information
        location_parts = []
        if data.get('city'):
            location_parts.append(data['city'])
            result['city'] = data['city']
        
        if data.get('regionName'):
            location_parts.append(data['regionName'])
            result['region'] = data['regionName']
        
        if data.get('country'):
            location_parts.append(data['country'])
            result['country'] = data['country']
        
        if location_parts:
            result['location'] = ', '.join(location_parts)
        
        # Coordinates
        if data.get('lat') and data.get('lon'):
            result['latitude'] = data['lat']
            result['longitude'] = data['lon']
            result['coordinates'] = f"{data['lat']}, {data['lon']}"
        
        # Timezone
        if data.get('timezone'):
            result['timezone'] = data['timezone']
        
        # ISP and organization
        if data.get('isp'):
            result['isp'] = data['isp']
        
        if data.get('org'):
            result['organization'] = data['org']
        
        # Country and region codes
        if data.get('countryCode'):
            result['country_code'] = data['countryCode']
        
        if data.get('region'):
            result['region_code'] = data['region']
        
        # ZIP code
        if data.get('zip'):
            result['postal_code'] = data['zip']
        
        result['geolocation_source'] = 'IP-API'
        result['geolocation_confidence'] = 0.7
        
        return result
    
    def _process_ipstack_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process IPStack response"""
        result = {}
        
        # Location information
        location_parts = []
        if data.get('city'):
            location_parts.append(data['city'])
            result['city'] = data['city']
        
        if data.get('region_name'):
            location_parts.append(data['region_name'])
            result['region'] = data['region_name']
        
        if data.get('country_name'):
            location_parts.append(data['country_name'])
            result['country'] = data['country_name']
        
        if location_parts:
            result['location'] = ', '.join(location_parts)
        
        # Coordinates
        if data.get('latitude') and data.get('longitude'):
            result['latitude'] = data['latitude']
            result['longitude'] = data['longitude']
            result['coordinates'] = f"{data['latitude']}, {data['longitude']}"
        
        # Timezone
        if data.get('time_zone', {}).get('id'):
            result['timezone'] = data['time_zone']['id']
        
        # Connection information
        if data.get('connection'):
            conn = data['connection']
            if conn.get('isp'):
                result['isp'] = conn['isp']
        
        # Country and region codes
        if data.get('country_code'):
            result['country_code'] = data['country_code']
        
        if data.get('region_code'):
            result['region_code'] = data['region_code']
        
        # ZIP code
        if data.get('zip'):
            result['postal_code'] = data['zip']
        
        result['geolocation_source'] = 'IPStack'
        result['geolocation_confidence'] = 0.85
        
        return result
    
    def _basic_ip_location_inference(self, ip_address: str) -> Dict[str, Any]:
        """Basic IP location inference using IP ranges"""
        # This is a very simplified approach
        # In production, you'd use a proper GeoIP database
        
        octets = ip_address.split('.')
        if len(octets) != 4:
            return {}
        
        try:
            first_octet = int(octets[0])
            second_octet = int(octets[1])
            
            # Very basic regional inference
            if first_octet in range(8, 15):  # Some US ranges
                return {
                    'country': 'United States',
                    'country_code': 'US',
                    'location': 'United States',
                    'geolocation_source': 'Basic Inference',
                    'geolocation_confidence': 0.3
                }
            elif first_octet in range(80, 95):  # Some European ranges
                return {
                    'country': 'Europe',
                    'location': 'Europe',
                    'geolocation_source': 'Basic Inference',
                    'geolocation_confidence': 0.2
                }
            
        except ValueError:
            pass
        
        return {}
    
    async def enrich_location_from_phone(self, phone_number: str) -> Dict[str, Any]:
        """
        Enrich location information from phone number
        
        Args:
            phone_number: Phone number to analyze
            
        Returns:
            Dictionary with location information
        """
        if not phone_number:
            return {}
        
        # Clean phone number
        cleaned_phone = re.sub(r'[^\d+]', '', phone_number)
        
        try:
            # Basic country code inference
            country_info = self._infer_country_from_phone(cleaned_phone)
            
            # If we have a premium phone lookup service configured
            if self.phone_lookup_config.get('enabled') and self.phone_lookup_config.get('api_key'):
                premium_info = await self._lookup_phone_premium(cleaned_phone)
                if premium_info:
                    country_info.update(premium_info)
            
            return country_info
            
        except Exception as e:
            self.logger.error(f"Phone location enrichment failed for {phone_number}: {e}")
            return {}
    
    def _infer_country_from_phone(self, phone_number: str) -> Dict[str, Any]:
        """Infer country from phone number country code"""
        country_codes_phone = {
            '+1': ('United States/Canada', 'US'),
            '+44': ('United Kingdom', 'GB'),
            '+49': ('Germany', 'DE'),
            '+33': ('France', 'FR'),
            '+39': ('Italy', 'IT'),
            '+34': ('Spain', 'ES'),
            '+31': ('Netherlands', 'NL'),
            '+46': ('Sweden', 'SE'),
            '+47': ('Norway', 'NO'),
            '+45': ('Denmark', 'DK'),
            '+358': ('Finland', 'FI'),
            '+61': ('Australia', 'AU'),
            '+64': ('New Zealand', 'NZ'),
            '+81': ('Japan', 'JP'),
            '+82': ('South Korea', 'KR'),
            '+86': ('China', 'CN'),
            '+91': ('India', 'IN'),
            '+65': ('Singapore', 'SG'),
            '+852': ('Hong Kong', 'HK'),
            '+972': ('Israel', 'IL'),
            '+971': ('UAE', 'AE'),
            '+41': ('Switzerland', 'CH'),
            '+43': ('Austria', 'AT')
        }
        
        for code, (country, country_code) in country_codes_phone.items():
            if phone_number.startswith(code):
                return {
                    'country': country,
                    'country_code': country_code,
                    'phone_country_code': code,
                    'location_source': 'Phone Number Analysis',
                    'location_confidence': 0.8
                }
        
        return {}
    
    async def _lookup_phone_premium(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Premium phone number lookup (placeholder for Numverify or similar)"""
        # This would integrate with a service like Numverify
        # For now, return None as it's not implemented
        return None
    
    async def infer_timezone_from_email_headers(self, email_headers: Dict[str, str]) -> Dict[str, Any]:
        """
        Infer timezone from email headers
        
        Args:
            email_headers: Email headers dictionary
            
        Returns:
            Dictionary with timezone information
        """
        timezone_info = {}
        
        try:
            # Look for timezone information in various headers
            date_header = email_headers.get('Date', '')
            received_headers = [v for k, v in email_headers.items() if k.lower() == 'received']
            
            # Parse timezone from Date header
            if date_header:
                tz_match = re.search(r'([+-]\d{4}|[A-Z]{3,4})', date_header)
                if tz_match:
                    tz_string = tz_match.group(1)
                    timezone_info.update(self._parse_timezone_string(tz_string))
            
            # Parse timezone from Received headers
            for received in received_headers:
                tz_match = re.search(r'([+-]\d{4}|[A-Z]{3,4})', received)
                if tz_match:
                    tz_string = tz_match.group(1)
                    tz_info = self._parse_timezone_string(tz_string)
                    if tz_info:
                        timezone_info.update(tz_info)
                        break
            
            return timezone_info
            
        except Exception as e:
            self.logger.error(f"Timezone inference from email headers failed: {e}")
            return {}
    
    def _parse_timezone_string(self, tz_string: str) -> Dict[str, Any]:
        """Parse timezone string and return timezone information"""
        result = {}
        
        # Handle offset format (+0000, -0500, etc.)
        if re.match(r'[+-]\d{4}', tz_string):
            sign = 1 if tz_string[0] == '+' else -1
            hours = int(tz_string[1:3])
            minutes = int(tz_string[3:5])
            offset_hours = sign * (hours + minutes / 60)
            
            result['timezone_offset'] = tz_string
            result['timezone_offset_hours'] = offset_hours
            
            # Infer likely timezone
            if offset_hours == -8:
                result['likely_timezone'] = 'America/Los_Angeles'
                result['likely_location'] = 'US West Coast'
            elif offset_hours == -5:
                result['likely_timezone'] = 'America/New_York'
                result['likely_location'] = 'US East Coast'
            elif offset_hours == 0:
                result['likely_timezone'] = 'Europe/London'
                result['likely_location'] = 'UK/GMT'
            elif offset_hours == 1:
                result['likely_timezone'] = 'Europe/Paris'
                result['likely_location'] = 'Central Europe'
            elif offset_hours == 9:
                result['likely_timezone'] = 'Asia/Tokyo'
                result['likely_location'] = 'Japan'
        
        # Handle timezone abbreviations
        elif tz_string in self.timezone_mappings:
            result['timezone_abbreviation'] = tz_string
            result['timezone'] = self.timezone_mappings[tz_string]
            
            # Infer location from timezone
            tz = self.timezone_mappings[tz_string]
            if 'America/Los_Angeles' in tz:
                result['likely_location'] = 'US West Coast'
            elif 'America/New_York' in tz:
                result['likely_location'] = 'US East Coast'
            elif 'Europe' in tz:
                result['likely_location'] = 'Europe'
            elif 'Asia' in tz:
                result['likely_location'] = 'Asia'
        
        if result:
            result['timezone_source'] = 'Email Headers'
            result['timezone_confidence'] = 0.6
        
        return result
    
    async def validate_address(self, address: str) -> Dict[str, Any]:
        """
        Validate and standardize address
        
        Args:
            address: Address string to validate
            
        Returns:
            Dictionary with validation results
        """
        if not address:
            return {}
        
        try:
            # Basic address parsing
            address_info = self._parse_address_components(address)
            
            # If Google Maps API is configured, use it for validation
            if self.address_config.get('enabled') and self.address_config.get('api_key'):
                google_info = await self._validate_with_google_maps(address)
                if google_info:
                    address_info.update(google_info)
            
            return address_info
            
        except Exception as e:
            self.logger.error(f"Address validation failed for {address}: {e}")
            return {}
    
    def _parse_address_components(self, address: str) -> Dict[str, Any]:
        """Parse address into components"""
        result = {'original_address': address}
        
        # Extract country
        for country_name, country_code in self.country_codes.items():
            if country_name.lower() in address.lower():
                result['country'] = country_name
                result['country_code'] = country_code
                break
        
        # Extract known cities
        for city_name, city_country in self.major_cities.items():
            if city_name.lower() in address.lower():
                result['city'] = city_name
                if not result.get('country_code'):
                    result['country_code'] = city_country
                    result['country'] = self.country_codes.get(city_country, city_country)
                break
        
        # Extract postal codes (basic patterns)
        postal_patterns = {
            'US': r'\b\d{5}(-\d{4})?\b',
            'CA': r'\b[A-Z]\d[A-Z]\s?\d[A-Z]\d\b',
            'GB': r'\b[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}\b',
            'DE': r'\b\d{5}\b'
        }
        
        for country, pattern in postal_patterns.items():
            match = re.search(pattern, address, re.IGNORECASE)
            if match:
                result['postal_code'] = match.group(0)
                if not result.get('country_code'):
                    result['country_code'] = country
                break
        
        result['address_source'] = 'Basic Parsing'
        result['address_confidence'] = 0.5
        
        return result
    
    async def _validate_with_google_maps(self, address: str) -> Optional[Dict[str, Any]]:
        """Validate address using Google Maps Geocoding API"""
        # Placeholder for Google Maps integration
        # Would require Google Maps API key and implementation
        return None
    
    def _is_valid_ip(self, ip_address: str) -> bool:
        """Check if IP address is valid"""
        try:
            octets = ip_address.split('.')
            if len(octets) != 4:
                return False
            
            for octet in octets:
                if not (0 <= int(octet) <= 255):
                    return False
            
            return True
        except:
            return False
    
    def _is_private_ip(self, ip_address: str) -> bool:
        """Check if IP address is private/local"""
        try:
            octets = [int(x) for x in ip_address.split('.')]
            
            # Private IP ranges
            if octets[0] == 10:
                return True
            elif octets[0] == 172 and 16 <= octets[1] <= 31:
                return True
            elif octets[0] == 192 and octets[1] == 168:
                return True
            elif octets[0] == 127:  # Localhost
                return True
            
            return False
        except:
            return False
    
    async def enrich_contact_location(self, contact: Contact, 
                                    ip_address: Optional[str] = None,
                                    email_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Comprehensive location enrichment for a contact
        
        Args:
            contact: Contact to enrich
            ip_address: IP address if available
            email_headers: Email headers if available
            
        Returns:
            Dictionary with enriched location data
        """
        enrichment_data = {}
        
        try:
            # 1. IP-based geolocation
            if ip_address:
                ip_location = await self.enrich_location_from_ip(ip_address)
                if ip_location:
                    enrichment_data.update(ip_location)
            
            # 2. Phone-based location
            if contact.phone_numbers:
                for phone in contact.phone_numbers:
                    phone_location = await self.enrich_location_from_phone(phone)
                    if phone_location:
                        # Merge phone location data
                        for key, value in phone_location.items():
                            if key not in enrichment_data:
                                enrichment_data[key] = value
            
            # 3. Timezone inference from email headers
            if email_headers:
                timezone_info = await self.infer_timezone_from_email_headers(email_headers)
                if timezone_info:
                    enrichment_data.update(timezone_info)
            
            # 4. Address validation if location exists
            if contact.location:
                address_info = await self.validate_address(contact.location)
                if address_info:
                    # Merge address validation results
                    for key, value in address_info.items():
                        if key not in enrichment_data:
                            enrichment_data[key] = value
            
            # 5. Consolidate location information
            if enrichment_data:
                enrichment_data = self._consolidate_location_data(enrichment_data)
            
            return enrichment_data
            
        except Exception as e:
            self.logger.error(f"Contact location enrichment failed: {e}")
            return {}
    
    def _consolidate_location_data(self, location_data: Dict[str, Any]) -> Dict[str, Any]:
        """Consolidate location data from multiple sources"""
        consolidated = location_data.copy()
        
        # Create a unified location string if we have components
        location_parts = []
        
        if location_data.get('city'):
            location_parts.append(location_data['city'])
        
        if location_data.get('region') or location_data.get('state'):
            region = location_data.get('region') or location_data.get('state')
            location_parts.append(region)
        
        if location_data.get('country'):
            location_parts.append(location_data['country'])
        
        if location_parts and not location_data.get('location'):
            consolidated['unified_location'] = ', '.join(location_parts)
        
        # Determine overall confidence
        confidence_scores = []
        for key, value in location_data.items():
            if key.endswith('_confidence'):
                confidence_scores.append(value)
        
        if confidence_scores:
            consolidated['overall_location_confidence'] = sum(confidence_scores) / len(confidence_scores)
        
        # Add enrichment metadata
        consolidated['location_enrichment_timestamp'] = datetime.now(timezone.utc).isoformat()
        consolidated['location_sources_used'] = [
            source for source in [
                location_data.get('geolocation_source'),
                location_data.get('location_source'),
                location_data.get('timezone_source'),
                location_data.get('address_source')
            ] if source
        ]
        
        return consolidated
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get information about the location service"""
        return {
            'name': 'IP Geolocation & Demographics Service',
            'description': 'Location enrichment using IP addresses and demographic data',
            'features': [
                'IP geolocation',
                'Phone number country detection',
                'Timezone inference from email headers',
                'Address validation and parsing',
                'Multi-source location consolidation'
            ],
            'providers': {
                'ip_geolocation': {
                    'enabled': self.ip_geolocation_config.get('enabled', True),
                    'provider': self.ip_geolocation_config.get('provider', 'ipapi'),
                    'has_api_key': bool(self.ip_geolocation_config.get('api_key'))
                },
                'phone_lookup': {
                    'enabled': self.phone_lookup_config.get('enabled', False),
                    'has_api_key': bool(self.phone_lookup_config.get('api_key'))
                },
                'address_validation': {
                    'enabled': self.address_config.get('enabled', False),
                    'provider': self.address_config.get('provider', 'google_maps'),
                    'has_api_key': bool(self.address_config.get('api_key'))
                }
            },
            'data_sources': [
                'IP-API (free tier)',
                'IPStack (premium)',
                'Phone number country codes',
                'Email header timezone analysis',
                'Geographic databases'
            ]
        }