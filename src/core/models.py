

"""
Enhanced Core models for the email enrichment system
Phase 2-4: Premium APIs + AI + NLP Features + Multiple Account Support
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import dataclass, field
from datetime import datetime,timezone
from typing import List, Optional, Dict, Any, Union
from enum import Enum
import uuid
import json

class EmailProvider(Enum):
    GMAIL = "gmail"
    OUTLOOK = "outlook"
    YAHOO = "yahoo"
    IMAP = "imap"
    ICLOUD = "icloud"
    OTHER = "other"
    
    @classmethod
    def from_email_domain(cls, email: str) -> 'EmailProvider':
        """Determine provider from email domain"""
        domain = email.split('@')[1].lower() if '@' in email else ''
        
        if 'gmail.com' in domain:
            return cls.GMAIL
        elif 'outlook.com' in domain or 'hotmail.com' in domain or 'live.com' in domain:
            return cls.OUTLOOK
        elif 'yahoo.com' in domain:
            return cls.YAHOO
        elif 'icloud.com' in domain or 'me.com' in domain:
            return cls.ICLOUD
        else:
            return cls.OTHER

@dataclass
class ProviderAccount:
    """Represents a specific email account for a provider"""
    provider: EmailProvider
    email: str
    account_id: str = ""
    display_name: str = ""
    credential_file: str = ""
    is_active: bool = True
    last_sync: Optional[datetime] = None
    contacts_extracted: int = 0
    last_error: str = ""
    
    def __post_init__(self):
        if not self.account_id:
            self.account_id = f"{self.provider.value}_{self.email}"
        if not self.display_name:
            self.display_name = f"{self.provider.value.title()} ({self.email})"

class ContactType(Enum):
    PERSONAL = "personal"
    BUSINESS = "business"
    BIG_TECH = "big_tech"
    ACADEMIC = "academic"
    GOVERNMENT = "government"
    NONPROFIT = "nonprofit"
    STARTUP = "startup"
    ENTERPRISE = "enterprise"
    UNKNOWN = "unknown"

class InteractionType(Enum):
    SENT = "sent"
    RECEIVED = "received"
    CC = "cc"
    BCC = "bcc"
    MEETING = "meeting"
    CALL = "call"
    SOCIAL = "social"

class EnrichmentSource(Enum):
    CLEARBIT = "clearbit"
    PEOPLEDATALABS = "peopledatalabs"
    HUNTER = "hunter"
    ZOOMINFO = "zoominfo"
    APOLLO = "apollo"
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    GITHUB = "github"
    DOMAIN_INFERENCE = "domain_inference"
    AI_ANALYSIS = "ai_analysis"
    MOCK_DATA = "mock_data"
    MANUAL = "manual"

class SentimentType(Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"

class EmotionType(Enum):
    JOY = "joy"
    ANGER = "anger"
    FEAR = "fear"
    SURPRISE = "surprise"
    SADNESS = "sadness"
    DISGUST = "disgust"
    NEUTRAL = "neutral"

class RelationshipStage(Enum):
    NEW = "new"
    WARM = "warm"
    ENGAGED = "engaged"
    ACTIVE = "active"
    DORMANT = "dormant"
    LOST = "lost"

@dataclass
class SocialProfile:
    """Social media profile information"""
    platform: str = ""
    url: str = ""
    username: str = ""
    followers: int = 0
    verified: bool = False
    last_updated: datetime = field(default_factory=datetime.now)

@dataclass
class ContactScore:
    """Contact scoring and intelligence metrics"""
    overall_score: float = 0.0
    relationship_strength: float = 0.0
    engagement_score: float = 0.0
    importance_score: float = 0.0
    response_likelihood: float = 0.0
    deal_potential: float = 0.0
    influence_score: float = 0.0
    
    # Sentiment analysis
    average_sentiment: float = 0.0
    sentiment_trend: str = "neutral"
    dominant_emotion: EmotionType = EmotionType.NEUTRAL
    
    # Communication patterns
    response_rate: float = 0.0
    average_response_time: float = 0.0  # hours
    best_contact_time: str = ""
    preferred_communication: str = ""
    
    # Scoring factors
    scoring_factors: Dict[str, float] = field(default_factory=dict)
    last_calculated: datetime = field(default_factory=datetime.now)

@dataclass
class EnrichmentMetadata:
    """Metadata about enrichment process"""
    sources_used: List[EnrichmentSource] = field(default_factory=list)
    total_cost: float = 0.0
    processing_time: float = 0.0
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    api_calls_made: int = 0
    last_enriched: datetime = field(default_factory=datetime.now)
    enrichment_version: str = "2.0"

@dataclass
class AIAnalysis:
    """AI-powered analysis results"""
    email_signature_analysis: Dict[str, Any] = field(default_factory=dict)
    communication_style: str = ""
    relationship_type: str = ""
    industry_classification: str = ""
    seniority_level: str = ""
    
    # NLP Analysis
    sentiment_history: List[Dict[str, Any]] = field(default_factory=list)
    emotion_patterns: Dict[str, float] = field(default_factory=dict)
    email_categories: List[str] = field(default_factory=list)
    extracted_entities: List[Dict[str, Any]] = field(default_factory=list)
    
    # Smart inference
    gender: str = ""
    age_range: str = ""
    estimated_income: str = ""
    personality_traits: List[str] = field(default_factory=list)
    interests: List[str] = field(default_factory=list)
    
    # Analysis metadata
    analysis_confidence: float = 0.0
    models_used: List[str] = field(default_factory=list)
    last_analyzed: datetime = field(default_factory=datetime.now)

@dataclass
class Interaction:
    """Enhanced interaction record"""
    type: InteractionType
    timestamp: datetime
    subject: str = ""
    message_id: str = ""
    direction: str = ""  # inbound/outbound
    
    # Account tracking
    source_account: str = ""  # Which account this interaction came from
    
    # Enhanced interaction data
    content_preview: str = ""
    attachment_count: int = 0
    urgency_level: str = "normal"
    
    # AI Analysis
    sentiment: SentimentType = SentimentType.NEUTRAL
    sentiment_score: float = 0.0
    emotions: Dict[EmotionType, float] = field(default_factory=dict)
    category: str = ""
    extracted_topics: List[str] = field(default_factory=list)
    
    # Response tracking
    requires_response: bool = False
    response_deadline: Optional[datetime] = None
    was_responded: bool = False
    response_time: Optional[float] = None  # hours

@dataclass
class Contact:
    """Enhanced Contact model with AI and enrichment features + Multiple Account Support"""
    
    # Basic Information
    email: str = ""
    name: str = ""
    first_name: str = ""
    last_name: str = ""
    provider: EmailProvider = EmailProvider.OTHER
    contact_type: ContactType = ContactType.UNKNOWN
    
    # Account tracking
    source_accounts: List[str] = field(default_factory=list)  # Which accounts this contact appears in
    primary_source_account: str = ""  # Primary account for this contact
    
    # Contact Details
    phone_numbers: List[str] = field(default_factory=list)
    alternative_emails: List[str] = field(default_factory=list)
    location: str = ""
    timezone: str = ""
    
    # Professional Information
    job_title: str = ""
    company: str = ""
    company_size: str = ""
    industry: str = ""
    department: str = ""
    seniority_level: str = ""
    
    # Financial Information
    estimated_net_worth: str = ""
    estimated_income: str = ""
    company_revenue: str = ""
    
    # Social Profiles
    social_profiles: List[SocialProfile] = field(default_factory=list)
    linkedin_url: str = ""
    twitter_handle: str = ""
    github_username: str = ""
    
    # Interaction Data - Global
    frequency: int = 0
    sent_to: int = 0
    received_from: int = 0
    cc_count: int = 0
    bcc_count: int = 0
    meeting_count: int = 0
    call_count: int = 0
    
    # Account-specific interaction stats
    account_stats: Dict[str, Dict[str, int]] = field(default_factory=dict)
    
    # Timestamps
    # first_seen: datetime = field(default_factory=datetime.now)
    # last_seen: datetime = field(default_factory=datetime.now)
    first_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen:  datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_contacted: Optional[datetime] = None
    last_response: Optional[datetime] = None
    
    # Enhanced Features
    interactions: List[Interaction] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""
    
    # AI and Scoring
    contact_score: ContactScore = field(default_factory=ContactScore)
    ai_analysis: AIAnalysis = field(default_factory=AIAnalysis)
    relationship_stage: RelationshipStage = RelationshipStage.NEW
    
    # Enrichment Metadata
    enrichment_metadata: EnrichmentMetadata = field(default_factory=EnrichmentMetadata)
    data_sources: List[str] = field(default_factory=list)
    confidence: float = 0.0
    is_verified: bool = False
    
    # Computed Properties
    domain: str = field(init=False)
    provider_contact_id: str = ""
    account_id: str = ""
    
    def __post_init__(self):
        """Initialize computed fields"""
        if self.email and '@' in self.email:
            self.domain = self.email.split('@')[1]
            # Auto-detect provider from email
            self.provider = EmailProvider.from_email_domain(self.email)
        
        # Parse name if provided
        if self.name and not (self.first_name and self.last_name):
            name_parts = self.name.split()
            if len(name_parts) >= 2:
                self.first_name = name_parts[0]
                self.last_name = " ".join(name_parts[1:])
            elif len(name_parts) == 1:
                self.first_name = name_parts[0]
        
        # Initialize contact score if not provided
        if not hasattr(self.contact_score, 'last_calculated'):
            self.contact_score = ContactScore()
    
    def add_source_account(self, account_id: str):
        """Add a source account for this contact"""
        if account_id not in self.source_accounts:
            self.source_accounts.append(account_id)
            self.account_stats[account_id] = {
                'frequency': 0, 'sent_to': 0, 'received_from': 0,
                'cc_count': 0, 'bcc_count': 0, 'meeting_count': 0, 'call_count': 0
            }
        
        if not self.primary_source_account:
            self.primary_source_account = account_id
    
    def add_interaction(self, interaction: Interaction):
        """Add an interaction and update statistics"""
        self.interactions.append(interaction)
        self.frequency += 1
        
        # Update global stats
        if interaction.type == InteractionType.SENT:
            self.sent_to += 1
        elif interaction.type == InteractionType.RECEIVED:
            self.received_from += 1
        elif interaction.type == InteractionType.CC:
            self.cc_count += 1
        elif interaction.type == InteractionType.BCC:
            self.bcc_count += 1
        elif interaction.type == InteractionType.MEETING:
            self.meeting_count += 1
        elif interaction.type == InteractionType.CALL:
            self.call_count += 1
        
        # Update account-specific stats
        if interaction.source_account:
            if interaction.source_account not in self.account_stats:
                self.account_stats[interaction.source_account] = {
                    'frequency': 0, 'sent_to': 0, 'received_from': 0,
                    'cc_count': 0, 'bcc_count': 0, 'meeting_count': 0, 'call_count': 0
                }
            
            self.account_stats[interaction.source_account]['frequency'] += 1
            
            if interaction.type == InteractionType.SENT:
                self.account_stats[interaction.source_account]['sent_to'] += 1
            elif interaction.type == InteractionType.RECEIVED:
                self.account_stats[interaction.source_account]['received_from'] += 1
            elif interaction.type == InteractionType.CC:
                self.account_stats[interaction.source_account]['cc_count'] += 1
            elif interaction.type == InteractionType.BCC:
                self.account_stats[interaction.source_account]['bcc_count'] += 1
            elif interaction.type == InteractionType.MEETING:
                self.account_stats[interaction.source_account]['meeting_count'] += 1
            elif interaction.type == InteractionType.CALL:
                self.account_stats[interaction.source_account]['call_count'] += 1
        
        # Update timestamps
        self.last_seen = max(self.last_seen, interaction.timestamp)
        
        if interaction.direction == "outbound":
            self.last_contacted = interaction.timestamp
        elif interaction.direction == "inbound":
            self.last_response = interaction.timestamp
    
    def get_account_stats(self, account_id: str) -> Dict[str, int]:
        """Get interaction statistics for a specific account"""
        return self.account_stats.get(account_id, {
            'frequency': 0, 'sent_to': 0, 'received_from': 0,
            'cc_count': 0, 'bcc_count': 0, 'meeting_count': 0, 'call_count': 0
        })
    
    def calculate_relationship_strength(self, account_id: str = None) -> float:
        """Calculate relationship strength, optionally for a specific account"""
        if account_id and account_id in self.account_stats:
            stats = self.account_stats[account_id]
            frequency = stats['frequency']
            sent_to = stats['sent_to']
            received_from = stats['received_from']
            meeting_count = stats['meeting_count']
            call_count = stats['call_count']
        else:
            frequency = self.frequency
            sent_to = self.sent_to
            received_from = self.received_from
            meeting_count = self.meeting_count
            call_count = self.call_count
        
        if frequency == 0:
            return 0.0
        
        # Base interaction score (0-0.4)
        base_score = min(frequency / 25.0, 0.4)
        
        # Bidirectional communication bonus (0-0.3)
        if sent_to > 0 and received_from > 0:
            balance = min(sent_to, received_from) / max(sent_to, received_from)
            bidirectional_bonus = balance * 0.3
        else:
            bidirectional_bonus = 0.0
        
        # Recency bonus (0-0.2)
        # days_since_last = (datetime.now() - self.last_seen).days
        days_since_last = (datetime.now(timezone.utc) - self.last_seen).days
        if days_since_last <= 7:
            recency_bonus = 0.2
        elif days_since_last <= 30:
            recency_bonus = 0.15
        elif days_since_last <= 90:
            recency_bonus = 0.1
        else:
            recency_bonus = 0.05
        
        # Meeting/call bonus (0-0.1)
        meeting_bonus = min((meeting_count + call_count) / 10.0, 0.1)
        
        total_score = base_score + bidirectional_bonus + recency_bonus + meeting_bonus
        return min(total_score, 1.0)
    
    def add_social_profile(self, platform: str, url: str, username: str = "", **kwargs):
        """Add a social media profile"""
        profile = SocialProfile(
            platform=platform,
            url=url,
            username=username,
            **kwargs
        )
        self.social_profiles.append(profile)
    
    def get_social_profile(self, platform: str) -> Optional[SocialProfile]:
        """Get social profile by platform"""
        for profile in self.social_profiles:
            if profile.platform.lower() == platform.lower():
                return profile
        return None
    
    def update_ai_analysis(self, analysis_data: Dict[str, Any]):
        """Update AI analysis data"""
        for field_name, value in analysis_data.items():
            if hasattr(self.ai_analysis, field_name):
                setattr(self.ai_analysis, field_name, value)
        
        self.ai_analysis.last_analyzed = datetime.now()
    
    def calculate_contact_score(self) -> ContactScore:
        """Calculate comprehensive contact score"""
        score = ContactScore()
        
        # Relationship strength (0-1)
        score.relationship_strength = self.calculate_relationship_strength()
        
        # Engagement score based on interaction variety
        interaction_types = len(set(i.type for i in self.interactions))
        score.engagement_score = min(interaction_types / 4.0, 1.0)  # Max 4 types
        
        # Response likelihood based on historical data
        if self.sent_to > 0:
            score.response_likelihood = self.received_from / self.sent_to
        else:
            score.response_likelihood = 0.5  # Neutral if no data
        
        # Importance based on company, title, and enrichment data
        importance_factors = []
        
        if self.company:
            # Big tech companies get higher importance
            big_tech = ['google', 'apple', 'microsoft', 'amazon', 'meta', 'netflix']
            if any(company in self.company.lower() for company in big_tech):
                importance_factors.append(0.9)
            else:
                importance_factors.append(0.7)
        
        if self.job_title:
            # Executive titles get higher importance
            exec_terms = ['ceo', 'cto', 'cfo', 'founder', 'president', 'vp', 'director']
            if any(term in self.job_title.lower() for term in exec_terms):
                importance_factors.append(0.9)
            elif any(term in self.job_title.lower() for term in ['senior', 'principal', 'lead']):
                importance_factors.append(0.7)
            elif 'manager' in self.job_title.lower():
                importance_factors.append(0.6)
            else:
                importance_factors.append(0.5)
        
        score.importance_score = sum(importance_factors) / len(importance_factors) if importance_factors else 0.5
        
        # Overall score (weighted average)
        weights = {
            'relationship_strength': 0.4,
            'engagement_score': 0.2,
            'response_likelihood': 0.2,
            'importance_score': 0.2
        }
        
        score.overall_score = (
            score.relationship_strength * weights['relationship_strength'] +
            score.engagement_score * weights['engagement_score'] +
            score.response_likelihood * weights['response_likelihood'] +
            score.importance_score * weights['importance_score']
        )
        
        # Update scoring factors for transparency
        score.scoring_factors = {
            'total_interactions': self.frequency,
            'bidirectional_communication': bool(self.sent_to > 0 and self.received_from > 0),
            'days_since_last_contact': (datetime.now() - self.last_seen).days,
            'meeting_calls': self.meeting_count + self.call_count,
            'company_importance': self.company in ['Google', 'Apple', 'Microsoft', 'Amazon'] if self.company else False,
            'executive_title': any(term in self.job_title.lower() for term in ['ceo', 'cto', 'cfo', 'founder']) if self.job_title else False
        }
        
        score.last_calculated = datetime.now()
        self.contact_score = score
        return score
    
    def get_communication_insights(self) -> Dict[str, Any]:
        """Get communication pattern insights"""
        if not self.interactions:
            return {}
        
        # Response time analysis
        response_times = []
        for i in range(len(self.interactions) - 1):
            current = self.interactions[i]
            next_interaction = self.interactions[i + 1]
            
            if (current.direction == "outbound" and 
                next_interaction.direction == "inbound" and
                next_interaction.timestamp > current.timestamp):
                
                response_time = (next_interaction.timestamp - current.timestamp).total_seconds() / 3600
                response_times.append(response_time)
        
        # Sentiment analysis
        sentiments = [i.sentiment for i in self.interactions if i.sentiment != SentimentType.NEUTRAL]
        positive_count = sum(1 for s in sentiments if s == SentimentType.POSITIVE)
        negative_count = sum(1 for s in sentiments if s == SentimentType.NEGATIVE)
        
        # Time pattern analysis
        interaction_hours = [i.timestamp.hour for i in self.interactions]
        hour_counts = {}
        for hour in interaction_hours:
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
        
        best_hour = max(hour_counts.items(), key=lambda x: x[1])[0] if hour_counts else 9
        
        return {
            'average_response_time_hours': sum(response_times) / len(response_times) if response_times else None,
            'response_rate': len(response_times) / max(self.sent_to, 1),
            'sentiment_ratio': positive_count / max(len(sentiments), 1) if sentiments else 0.5,
            'best_contact_hour': best_hour,
            'total_interactions': len(self.interactions),
            'interaction_frequency_days': (self.last_seen - self.first_seen).days / max(len(self.interactions), 1)
        }
    
    def update_enrichment_data(self, 
                             data: Dict[str, Any], 
                             source: EnrichmentSource, 
                             confidence: float,
                             cost: float = 0.0):
        """Update contact with enrichment data"""
        
        # Update basic fields
        for field_name, value in data.items():
            if value and hasattr(self, field_name):
                setattr(self, field_name, value)
        
        # Update enrichment metadata
        if source not in self.enrichment_metadata.sources_used:
            self.enrichment_metadata.sources_used.append(source)
        
        self.enrichment_metadata.total_cost += cost
        self.enrichment_metadata.confidence_scores[source.value] = confidence
        self.enrichment_metadata.api_calls_made += 1
        self.enrichment_metadata.last_enriched = datetime.now()
        
        # Update overall confidence (weighted average)
        total_confidence = sum(self.enrichment_metadata.confidence_scores.values())
        source_count = len(self.enrichment_metadata.confidence_scores)
        self.confidence = total_confidence / source_count if source_count > 0 else 0.0
        
        # Add data source if not already present
        source_name = source.value
        if source_name not in self.data_sources:
            self.data_sources.append(source_name)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert contact to dictionary for export"""
        return {
            'email': self.email,
            'name': self.name,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone_numbers': self.phone_numbers,
            'location': self.location,
            'timezone': self.timezone,
            'job_title': self.job_title,
            'company': self.company,
            'industry': self.industry,
            'estimated_net_worth': self.estimated_net_worth,
            'linkedin_url': self.linkedin_url,
            'twitter_handle': self.twitter_handle,
            'github_username': self.github_username,
            'frequency': self.frequency,
            'sent_to': self.sent_to,
            'received_from': self.received_from,
            'relationship_strength': self.calculate_relationship_strength(),
            'contact_score': self.contact_score.overall_score,
            'confidence': self.confidence,
            'data_sources': ', '.join(self.data_sources),
            'source_accounts': ', '.join(self.source_accounts),
            'primary_source_account': self.primary_source_account,
            'tags': ', '.join(self.tags),
            'first_seen': self.first_seen.isoformat(),
            'last_seen': self.last_seen.isoformat(),
            'enrichment_cost': self.enrichment_metadata.total_cost,
            'is_verified': self.is_verified
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Contact':
        """Create contact from dictionary"""
        contact = cls()
        
        # Basic fields
        for field in ['email', 'name', 'first_name', 'last_name', 'location', 
                     'job_title', 'company', 'industry', 'estimated_net_worth',
                     'linkedin_url', 'twitter_handle', 'github_username']:
            if field in data and data[field]:
                setattr(contact, field, data[field])
        
        # Lists and complex fields
        if 'phone_numbers' in data:
            contact.phone_numbers = data['phone_numbers'] if isinstance(data['phone_numbers'], list) else [data['phone_numbers']]
        
        if 'tags' in data:
            contact.tags = data['tags'] if isinstance(data['tags'], list) else data['tags'].split(', ')
        
        if 'data_sources' in data:
            contact.data_sources = data['data_sources'] if isinstance(data['data_sources'], list) else data['data_sources'].split(', ')
        
        if 'source_accounts' in data:
            contact.source_accounts = data['source_accounts'] if isinstance(data['source_accounts'], list) else data['source_accounts'].split(', ')
        
        if 'primary_source_account' in data:
            contact.primary_source_account = data['primary_source_account']
        
        # Numerical fields
        for field in ['frequency', 'sent_to', 'received_from', 'confidence']:
            if field in data and data[field] is not None:
                setattr(contact, field, float(data[field]) if field == 'confidence' else int(data[field]))
        
        # Timestamps
        for field in ['first_seen', 'last_seen']:
            if field in data and data[field]:
                if isinstance(data[field], str):
                    setattr(contact, field, datetime.fromisoformat(data[field]))
                elif isinstance(data[field], datetime):
                    setattr(contact, field, data[field])
        
        return contact

@dataclass
class EnrichmentResult:
    """Result of an enrichment operation"""
    success: bool
    contact: Contact
    source: EnrichmentSource
    data_added: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    cost: float = 0.0
    processing_time: float = 0.0
    error_message: str = ""
    api_calls_used: int = 0

@dataclass
class ProviderStatus:
    """Enhanced provider status with enrichment info and multiple accounts"""
    provider: EmailProvider
    accounts: List[ProviderAccount] = field(default_factory=list)
    is_connected: bool = False
    last_sync: Optional[datetime] = None
    api_calls_today: int = 0
    rate_limit_remaining: int = 0
    error_message: str = ""
    
    # Enrichment status
    enrichment_enabled: bool = False
    enrichment_sources: List[EnrichmentSource] = field(default_factory=list)
    daily_enrichment_budget: float = 0.0
    daily_enrichment_spent: float = 0.0
    
    def add_account(self, account: ProviderAccount):
        """Add an account to this provider"""
        existing_emails = [acc.email for acc in self.accounts]
        if account.email not in existing_emails:
            self.accounts.append(account)
    
    def get_account_by_email(self, email: str) -> Optional[ProviderAccount]:
        """Get account by email address"""
        for account in self.accounts:
            if account.email.lower() == email.lower():
                return account
        return None
    
    def get_active_accounts(self) -> List[ProviderAccount]:
        """Get all active accounts for this provider"""
        return [account for account in self.accounts if account.is_active]
    
    def remove_account(self, email: str) -> bool:
        """Remove account by email"""
        for i, account in enumerate(self.accounts):
            if account.email.lower() == email.lower():
                del self.accounts[i]
                return True
        return False

@dataclass
class CampaignContact:
    """Contact within a campaign context"""
    contact: Contact
    campaign_id: str
    status: str = "pending"  # pending, contacted, responded, converted, bounced
    contacted_at: Optional[datetime] = None
    response_at: Optional[datetime] = None
    campaign_score: float = 0.0
    personalization_data: Dict[str, Any] = field(default_factory=dict)
    
@dataclass
class NetworkAnalysis:
    """Network analysis results for contacts"""
    contact_id: str
    mutual_connections: List[str] = field(default_factory=list)
    influence_score: float = 0.0
    network_reach: int = 0
    common_interests: List[str] = field(default_factory=list)
    introduction_paths: List[List[str]] = field(default_factory=list)
    network_clusters: List[str] = field(default_factory=list)

# Utility functions for model operations

def merge_contacts(primary: Contact, secondary: Contact) -> Contact:
    """Merge two contact records, keeping the best data from each"""
    merged = Contact()
    
    # Take non-empty values, preferring primary
    for field in ['email', 'name', 'first_name', 'last_name', 'location', 
                 'job_title', 'company', 'industry', 'estimated_net_worth']:
        primary_val = getattr(primary, field, "")
        secondary_val = getattr(secondary, field, "")
        
        if primary_val:
            setattr(merged, field, primary_val)
        elif secondary_val:
            setattr(merged, field, secondary_val)
    
    # Merge source accounts
    merged.source_accounts = list(set(primary.source_accounts + secondary.source_accounts))
    merged.primary_source_account = primary.primary_source_account or secondary.primary_source_account
    
    # Merge account stats
    merged.account_stats = {}
    for account_id in merged.source_accounts:
        primary_stats = primary.account_stats.get(account_id, {})
        secondary_stats = secondary.account_stats.get(account_id, {})
        
        merged_stats = {}
        for stat_key in ['frequency', 'sent_to', 'received_from', 'cc_count', 'bcc_count', 'meeting_count', 'call_count']:
            merged_stats[stat_key] = primary_stats.get(stat_key, 0) + secondary_stats.get(stat_key, 0)
        
        merged.account_stats[account_id] = merged_stats
    
    # Merge lists
    merged.phone_numbers = list(set(primary.phone_numbers + secondary.phone_numbers))
    merged.alternative_emails = list(set(primary.alternative_emails + secondary.alternative_emails))
    merged.tags = list(set(primary.tags + secondary.tags))
    merged.data_sources = list(set(primary.data_sources + secondary.data_sources))
    
    # Combine interactions
    merged.interactions = primary.interactions + secondary.interactions
    merged.interactions.sort(key=lambda x: x.timestamp)
    
    # Sum numerical fields
    merged.frequency = primary.frequency + secondary.frequency
    merged.sent_to = primary.sent_to + secondary.sent_to
    merged.received_from = primary.received_from + secondary.received_from
    
    # Take better timestamps
    merged.first_seen = min(primary.first_seen, secondary.first_seen)
    merged.last_seen = max(primary.last_seen, secondary.last_seen)
    
    # Take higher confidence
    merged.confidence = max(primary.confidence, secondary.confidence)
    
    return merged

def calculate_similarity_score(contact1: Contact, contact2: Contact) -> float:
    """Calculate similarity score between two contacts (0-1)"""
    score = 0.0
    factors = 0
    
    # Email similarity (exact match only)
    if contact1.email.lower() == contact2.email.lower():
        score += 1.0
        factors += 1
    
    # Name similarity
    if contact1.name and contact2.name:
        name1_words = set(contact1.name.lower().split())
        name2_words = set(contact2.name.lower().split())
        if name1_words & name2_words:  # Any common words
            score += len(name1_words & name2_words) / len(name1_words | name2_words)
        factors += 1
    
    # Company similarity
    if contact1.company and contact2.company:
        if contact1.company.lower() == contact2.company.lower():
            score += 1.0
        factors += 1
    
    # Domain similarity
    if contact1.domain and contact2.domain:
        if contact1.domain.lower() == contact2.domain.lower():
            score += 0.8
        factors += 1
    
    return score / factors if factors > 0 else 0.0

def validate_email_format(email: str) -> bool:
    """Validate email format"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def extract_email_from_credential_filename(filename: str) -> Optional[str]:
    """Extract email from credential filename"""
    # Expected format: {provider}_{email}_credentials.json
    try:
        # Remove extension
        name_without_ext = filename.replace('.json', '')
        
        # Split by underscores
        parts = name_without_ext.split('_')
        
        # Find the email part (contains @)
        for part in parts:
            if '@' in part and validate_email_format(part):
                return part
        
        return None
    except Exception:
        return None

def generate_account_id(provider: EmailProvider, email: str) -> str:
    """Generate a unique account ID"""
    return f"{provider.value}_{email.lower()}"

def parse_provider_account_string(provider_accounts_str: str) -> Dict[str, List[str]]:
    """
    Parse provider account string from CLI
    
    Args:
        provider_accounts_str: String like "gmail=john@example.com,jane@gmail.com outlook=jane@company.com"
    
    Returns:
        Dict mapping provider to list of emails
    """
    result = {}
    
    try:
        # Split by spaces to get provider=emails pairs
        pairs = provider_accounts_str.split()
        
        for pair in pairs:
            if '=' not in pair:
                continue
            
            provider, emails_str = pair.split('=', 1)
            provider = provider.lower().strip()
            
            if emails_str.lower() == 'all':
                result[provider] = ['all']
            else:
                emails = [email.strip() for email in emails_str.split(',')]
                # Validate emails
                valid_emails = [email for email in emails if validate_email_format(email)]
                if valid_emails:
                    result[provider] = valid_emails
    
    except Exception as e:
        # Return empty dict on parsing error
        return {}
    
    return result