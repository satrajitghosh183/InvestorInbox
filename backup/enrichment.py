
import os
import re
import time
import random
from typing import List, Dict, Optional
import requests
from tqdm import tqdm
import colorama
from colorama import Fore, Style

from config.config import ENRICHMENT_SOURCES, DEMO_MODE

class ContactEnricher:
    """Enriches contact data using various sources"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Email-Enrichment-Demo/1.0'
        })
        
        # Mock data for demo purposes
        self.mock_locations = [
            "San Francisco, CA", "New York, NY", "London, UK", "Toronto, Canada",
            "Austin, TX", "Seattle, WA", "Boston, MA", "Chicago, IL", "Los Angeles, CA",
            "Berlin, Germany", "Amsterdam, Netherlands", "Sydney, Australia", "Tokyo, Japan",
            "Singapore", "Hong Kong", "Tel Aviv, Israel", "Stockholm, Sweden", "Zurich, Switzerland"
        ]
        
        self.mock_net_worth_ranges = [
            "$50K - $100K", "$100K - $250K", "$250K - $500K", "$500K - $1M",
            "$1M - $2.5M", "$2.5M - $5M", "$5M - $10M", "$10M+"
        ]
        
        self.job_title_patterns = {
            'executive': ['ceo', 'cto', 'cfo', 'president', 'vp', 'director', 'head of'],
            'senior': ['senior', 'principal', 'lead', 'architect', 'manager'],
            'mid': ['engineer', 'developer', 'analyst', 'specialist', 'coordinator'],
            'junior': ['junior', 'associate', 'assistant', 'intern', 'trainee']
        }
    
    def enrich_contacts(self, contacts: List) -> List:
        """Enrich a list of contacts with location and net worth data"""
        if not contacts:
            return contacts
        
        print(f"{Fore.CYAN}🔍 Enriching {len(contacts)} contacts...{Style.RESET_ALL}")
        
        if DEMO_MODE:
            # Use progress bar for demo
            contact_iterator = tqdm(contacts, desc="Enriching contacts", unit="contact")
        else:
            contact_iterator = contacts
        
        enriched_contacts = []
        
        for contact in contact_iterator:
            enriched_contact = self._enrich_single_contact(contact)
            enriched_contacts.append(enriched_contact)
            
            # Small delay for demo effect
            if DEMO_MODE:
                time.sleep(0.1)
        
        # Calculate enrichment stats
        total = len(enriched_contacts)
        with_location = sum(1 for c in enriched_contacts if c.location)
        with_net_worth = sum(1 for c in enriched_contacts if c.estimated_net_worth)
        
        print(f"{Fore.GREEN}✅ Enrichment complete!{Style.RESET_ALL}")
        print(f"• Contacts with location: {with_location}/{total} ({with_location/total*100:.1f}%)")
        print(f"• Contacts with net worth estimate: {with_net_worth}/{total} ({with_net_worth/total*100:.1f}%)")
        
        return enriched_contacts
    
    def _enrich_single_contact(self, contact) -> object:
        """Enrich a single contact with available data sources"""
        
        # Try different enrichment methods in order of preference
        enrichment_data = None
        
        # 1. Try Clearbit (if enabled and API key available)
        if ENRICHMENT_SOURCES['clearbit']['enabled']:
            enrichment_data = self._enrich_with_clearbit(contact.email)
            if enrichment_data:
                contact.data_source = "Clearbit"
                contact.confidence = 0.9
        
        # 2. Try Hunter.io (if enabled)
        if not enrichment_data and ENRICHMENT_SOURCES['hunter']['enabled']:
            enrichment_data = self._enrich_with_hunter(contact.email)
            if enrichment_data:
                contact.data_source = "Hunter.io"
                contact.confidence = 0.7
        
        # 3. Use mock data for demo
        if not enrichment_data and ENRICHMENT_SOURCES['mock']['enabled']:
            enrichment_data = self._enrich_with_mock_data(contact.email, contact.name)
            if enrichment_data:
                contact.data_source = "Demo Data"
                contact.confidence = 0.5
        
        # 4. Fallback to domain-based inference
        if not enrichment_data:
            enrichment_data = self._enrich_with_domain_inference(contact.email)
            contact.data_source = "Domain Inference"
            contact.confidence = 0.3
        
        # Apply enrichment data
        if enrichment_data:
            contact.location = enrichment_data.get('location', '')
            contact.estimated_net_worth = enrichment_data.get('net_worth', '')
        
        return contact
    
    def _enrich_with_clearbit(self, email: str) -> Optional[Dict]:
        """Enrich using Clearbit API"""
        api_key = ENRICHMENT_SOURCES['clearbit']['api_key']
        if not api_key:
            return None
        
        try:
            url = f"{ENRICHMENT_SOURCES['clearbit']['base_url']}?email={email}"
            
            response = self.session.get(
                url,
                auth=(api_key, ''),
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                location = ""
                if data.get('location'):
                    city = data['location'].get('city', '')
                    state = data['location'].get('state', '')
                    country = data['location'].get('country', '')
                    location = f"{city}, {state}, {country}".strip(', ')
                
                # Estimate net worth based on role and company
                net_worth = self._estimate_net_worth_from_clearbit(data)
                
                return {
                    'location': location,
                    'net_worth': net_worth
                }
            
        except Exception as e:
            print(f"{Fore.YELLOW}⚠️ Clearbit API error for {email}: {e}{Style.RESET_ALL}")
        
        return None
    
    def _enrich_with_hunter(self, email: str) -> Optional[Dict]:
        """Enrich using Hunter.io API"""
        api_key = ENRICHMENT_SOURCES['hunter']['api_key']
        if not api_key:
            return None
        
        try:
            # Hunter.io has different endpoint structure
            domain = email.split('@')[1]
            url = f"{ENRICHMENT_SOURCES['hunter']['base_url']}?domain={domain}&api_key={api_key}"
            
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                # Process Hunter.io response format
                # This is a simplified implementation
                return {
                    'location': 'Location from Hunter',
                    'net_worth': '$100K - $250K'
                }
            
        except Exception as e:
            print(f"{Fore.YELLOW}⚠️ Hunter.io API error for {email}: {e}{Style.RESET_ALL}")
        
        return None
    
    def _enrich_with_mock_data(self, email: str, name: str) -> Dict:
        """Generate realistic mock data for demo purposes"""
        
        # Use email/name hash for consistent results
        seed = hash(email) % 1000
        random.seed(seed)
        
        # Generate location
        location = random.choice(self.mock_locations)
        
        # Generate net worth based on email domain and name patterns
        net_worth = self._estimate_net_worth_from_email(email, name)
        
        return {
            'location': location,
            'net_worth': net_worth
        }
    
    def _enrich_with_domain_inference(self, email: str) -> Dict:
        """Infer data from email domain"""
        domain = email.split('@')[1].lower()
        
        # Common domain locations
        domain_locations = {
            'gmail.com': 'Global',
            'yahoo.com': 'Global',
            'hotmail.com': 'Global',
            'outlook.com': 'Global',
            'apple.com': 'Cupertino, CA',
            'google.com': 'Mountain View, CA',
            'microsoft.com': 'Redmond, WA',
            'amazon.com': 'Seattle, WA',
            'facebook.com': 'Menlo Park, CA',
            'netflix.com': 'Los Gatos, CA',
            'salesforce.com': 'San Francisco, CA',
            'uber.com': 'San Francisco, CA',
            'airbnb.com': 'San Francisco, CA',
            'tesla.com': 'Austin, TX',
        }
        
        location = domain_locations.get(domain, 'Unknown')
        
        # Basic net worth estimation
        if domain in ['apple.com', 'google.com', 'microsoft.com', 'amazon.com', 'facebook.com']:
            net_worth = '$250K - $500K'  # Big tech assumption
        elif domain.endswith('.edu'):
            net_worth = '$50K - $100K'  # Academic assumption
        elif domain.endswith('.gov'):
            net_worth = '$75K - $150K'  # Government assumption
        else:
            net_worth = '$100K - $250K'  # Default assumption
        
        return {
            'location': location,
            'net_worth': net_worth
        }
    
    def _estimate_net_worth_from_email(self, email: str, name: str) -> str:
        """Estimate net worth based on email patterns and name"""
        
        # Get domain characteristics
        domain = email.split('@')[1].lower()
        local_part = email.split('@')[0].lower()
        
        # Check for executive indicators
        executive_indicators = ['ceo', 'cto', 'cfo', 'founder', 'president', 'vp']
        senior_indicators = ['director', 'head', 'lead', 'senior', 'principal']
        
        name_lower = name.lower() if name else ''
        
        # Score based on various factors
        score = 0
        
        # Domain scoring
        if domain in ['apple.com', 'google.com', 'microsoft.com', 'amazon.com', 'meta.com']:
            score += 3  # Big tech
        elif domain.endswith('.edu'):
            score -= 1  # Academic
        elif len(domain.split('.')) == 2 and not domain.endswith(('.com', '.org', '.net')):
            score += 1  # Custom domain might indicate business owner
        
        # Email pattern scoring
        if any(indicator in local_part for indicator in executive_indicators):
            score += 3
        elif any(indicator in local_part for indicator in senior_indicators):
            score += 2
        
        # Name pattern scoring
        if any(indicator in name_lower for indicator in executive_indicators):
            score += 3
        elif any(indicator in name_lower for indicator in senior_indicators):
            score += 2
        
        # Convert score to net worth range
        if score >= 5:
            return random.choice(['$1M - $2.5M', '$2.5M - $5M', '$5M - $10M'])
        elif score >= 3:
            return random.choice(['$500K - $1M', '$1M - $2.5M'])
        elif score >= 1:
            return random.choice(['$250K - $500K', '$500K - $1M'])
        elif score >= 0:
            return random.choice(['$100K - $250K', '$250K - $500K'])
        else:
            return random.choice(['$50K - $100K', '$100K - $250K'])
    
    def _estimate_net_worth_from_clearbit(self, data: Dict) -> str:
        """Estimate net worth from Clearbit data"""
        
        # This would use actual Clearbit data structure
        # For now, return a reasonable estimate
        
        employment = data.get('employment', {})
        title = employment.get('title', '').lower()
        
        if any(exec_term in title for exec_term in ['ceo', 'founder', 'president']):
            return '$1M - $2.5M'
        elif any(senior_term in title for senior_term in ['vp', 'director', 'head']):
            return '$500K - $1M'
        elif any(mid_term in title for mid_term in ['manager', 'senior', 'lead']):
            return '$250K - $500K'
        else:
            return '$100K - $250K'

# Demo function
def demo_enrichment():
    """Demo the enrichment functionality"""
    print(f"{Fore.MAGENTA}🚀 Contact Enrichment Demo{Style.RESET_ALL}")
    print("=" * 40)
    
    # Create some sample contacts for demo
    from gmail_extractor import Contact
    
    sample_contacts = [
        Contact("John Smith", "john.smith@google.com"),
        Contact("Sarah Johnson", "sarah.j@microsoft.com"),
        Contact("", "founder@startup.com"),
        Contact("Mike Chen", "mike.chen@university.edu"),
        Contact("Lisa Rodriguez", "l.rodriguez@salesforce.com")
    ]
    
    enricher = ContactEnricher()
    enriched = enricher.enrich_contacts(sample_contacts)
    
    print(f"\n{Fore.CYAN}📋 Enrichment Results:{Style.RESET_ALL}")
    for contact in enriched:
        print(f"• {contact.name} ({contact.email})")
        print(f"  Location: {contact.location}")
        print(f"  Net Worth: {contact.estimated_net_worth}")
        print(f"  Source: {contact.data_source} (Confidence: {contact.confidence:.1f})")
        print()

if __name__ == "__main__":
    demo_enrichment()