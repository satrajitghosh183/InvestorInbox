"""
Production-Ready Enhanced Contact Scoring Engine
Integrates all APIs, AI components, and social media data with robust fallbacks
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
import math
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict

from core.models import Contact, ContactScore, Interaction, InteractionType, SentimentType, EmotionType, RelationshipStage
from config.config_manager import get_config_manager

# AI Components with fallbacks
try:
    from enrichment.ai.huggingface_nlp import HuggingFaceNLPEngine
    HUGGINGFACE_AVAILABLE = True
except ImportError:
    HUGGINGFACE_AVAILABLE = False

try:
    from enrichment.ai.openai_analyzer import OpenAIEmailAnalyzer
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Enrichment services
try:
    from enrichment.sources.clearbit_source import ClearbitEnrichmentSource
    CLEARBIT_AVAILABLE = True
except ImportError:
    CLEARBIT_AVAILABLE = False

try:
    from enrichment.sources.hunter_source import HunterIOSource
    HUNTER_AVAILABLE = True
except ImportError:
    HUNTER_AVAILABLE = False

try:
    from enrichment.sources.peopledatalabs_source import PeopleDataLabsSource
    PDL_AVAILABLE = True
except ImportError:
    PDL_AVAILABLE = False

# Add this at the top of the file to handle missing dependencies gracefully
try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("⚠️ Transformers not available - using basic scoring only")

@dataclass
class ScoringWeights:
    """Enhanced scoring weights that include social media and AI factors"""
    # Traditional factors (reduced to make room for new ones)
    interaction_frequency: float = 0.18      # Reduced from 0.25
    response_rate: float = 0.16             # Reduced from 0.20
    recency: float = 0.12                   # Reduced from 0.15
    sentiment: float = 0.12                 # Reduced from 0.15
    
    # Professional factors
    company_importance: float = 0.10        # Same
    title_seniority: float = 0.10          # Same
    
    # NEW: Social media and network factors
    social_influence: float = 0.08          # LinkedIn, Twitter followers/connections
    network_quality: float = 0.06          # Quality of social profiles
    content_engagement: float = 0.04       # Social media activity level
    
    # Enhanced engagement
    meeting_engagement: float = 0.04       # Meetings, calls, video conferences

class EnhancedContactScoringEngine:
    """
    Production-ready contact scoring engine with full API integration and fallbacks
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config_manager = get_config_manager()
        
        # Initialize AI engines
        self.nlp_engine = None
        self.openai_analyzer = None
        self._init_ai_engines()
        
        # Initialize enrichment sources
        self.clearbit_source = None
        self.hunter_source = None
        self.pdl_source = None
        self._init_enrichment_sources()
        
        # Load scoring weights from config
        self.weights = self._load_scoring_weights()
        
        # Enhanced company importance mappings
        self.company_importance_scores = self._load_company_mappings()
        
        # Enhanced job title seniority scores
        self.title_seniority_scores = self._load_title_mappings()
        
        # Social media scoring factors
        self.social_scoring_factors = self._load_social_scoring_factors()
        
        # Industry importance mappings
        self.industry_importance = self._load_industry_mappings()
        
        self.logger.info(f"Enhanced Contact Scorer initialized with:")
        self.logger.info(f"  - HuggingFace NLP: {'✅' if self.nlp_engine else '❌'}")
        self.logger.info(f"  - OpenAI Analysis: {'✅' if self.openai_analyzer else '❌'}")
        self.logger.info(f"  - Clearbit: {'✅' if self.clearbit_source else '❌'}")
        self.logger.info(f"  - Hunter.io: {'✅' if self.hunter_source else '❌'}")
        self.logger.info(f"  - People Data Labs: {'✅' if self.pdl_source else '❌'}")
        
        # Then in the __init__ method, add:
        if not TRANSFORMERS_AVAILABLE:
            self.logger.warning("AI components not available - using basic scoring")
            self.nlp_engine = None
            self.openai_analyzer = None
    
    def _init_ai_engines(self):
        """Initialize AI engines with fallback handling"""
        # Initialize HuggingFace NLP
        if HUGGINGFACE_AVAILABLE:
            try:
                self.nlp_engine = HuggingFaceNLPEngine()
                if not self.nlp_engine.enabled:
                    self.logger.warning("HuggingFace NLP engine disabled")
                    self.nlp_engine = None
            except Exception as e:
                self.logger.warning(f"Failed to initialize HuggingFace NLP: {e}")
                self.nlp_engine = None
        
        # Initialize OpenAI analyzer
        if OPENAI_AVAILABLE and os.getenv('OPENAI_API_KEY'):
            try:
                self.openai_analyzer = OpenAIEmailAnalyzer()
                if not self.openai_analyzer.enabled:
                    self.logger.warning("OpenAI analyzer disabled")
                    self.openai_analyzer = None
            except Exception as e:
                self.logger.warning(f"Failed to initialize OpenAI analyzer: {e}")
                self.openai_analyzer = None
    
    def _init_enrichment_sources(self):
        """Initialize enrichment sources with fallback handling"""
        # Initialize Clearbit
        if CLEARBIT_AVAILABLE and os.getenv('CLEARBIT_API_KEY'):
            try:
                self.clearbit_source = ClearbitEnrichmentSource()
                if not self.clearbit_source.is_enabled():
                    self.clearbit_source = None
            except Exception as e:
                self.logger.warning(f"Failed to initialize Clearbit: {e}")
                self.clearbit_source = None
        
        # Initialize Hunter.io
        if HUNTER_AVAILABLE and os.getenv('HUNTER_API_KEY'):
            try:
                self.hunter_source = HunterIOSource()
                if not self.hunter_source.is_enabled():
                    self.hunter_source = None
            except Exception as e:
                self.logger.warning(f"Failed to initialize Hunter.io: {e}")
                self.hunter_source = None
        
        # Initialize People Data Labs
        if PDL_AVAILABLE and os.getenv('PDL_API_KEY'):
            try:
                self.pdl_source = PeopleDataLabsSource()
                if not self.pdl_source.is_enabled():
                    self.pdl_source = None
            except Exception as e:
                self.logger.warning(f"Failed to initialize People Data Labs: {e}")
                self.pdl_source = None
    
    def _load_scoring_weights(self) -> ScoringWeights:
        """Load scoring weights from configuration with fallbacks"""
        try:
            scoring_config = self.config_manager.get_contact_intelligence_config().get('scoring', {})
            weights_config = scoring_config.get('weights', {})
            
            return ScoringWeights(
                interaction_frequency=weights_config.get('interaction_frequency', 0.18),
                response_rate=weights_config.get('response_rate', 0.16),
                recency=weights_config.get('recency', 0.12),
                sentiment=weights_config.get('sentiment', 0.12),
                company_importance=weights_config.get('company_importance', 0.10),
                title_seniority=weights_config.get('title_seniority', 0.10),
                social_influence=weights_config.get('social_influence', 0.08),
                network_quality=weights_config.get('network_quality', 0.06),
                content_engagement=weights_config.get('content_engagement', 0.04),
                meeting_engagement=weights_config.get('meeting_engagement', 0.04)
            )
        except Exception as e:
            self.logger.warning(f"Failed to load scoring weights from config: {e}")
            return ScoringWeights()  # Use defaults
    
    def _load_company_mappings(self) -> Dict[str, float]:
        """Load enhanced company importance mappings"""
        return {
            # Tier 1: FAANG + Top Tech (0.95-1.0)
            'google': 1.0, 'alphabet': 1.0, 'apple': 0.98, 'microsoft': 0.98,
            'amazon': 0.97, 'meta': 0.96, 'facebook': 0.96, 'netflix': 0.95,
            'tesla': 0.95, 'nvidia': 0.95, 'openai': 0.95, 'anthropic': 0.94,
            
            # Tier 2: Major Tech Companies (0.85-0.94)
            'salesforce': 0.92, 'adobe': 0.90, 'oracle': 0.89, 'sap': 0.88,
            'servicenow': 0.87, 'snowflake': 0.87, 'palantir': 0.86,
            'uber': 0.85, 'airbnb': 0.85, 'stripe': 0.90, 'spacex': 0.92,
            
            # Tier 3: Investment Banks & Finance (0.85-0.95)
            'goldman sachs': 0.95, 'morgan stanley': 0.93, 'jp morgan': 0.92,
            'blackrock': 0.90, 'citadel': 0.89, 'bridgewater': 0.88,
            'blackstone': 0.87, 'kkr': 0.85, 'carlyle': 0.85,
            
            # Tier 4: Top Consulting (0.85-0.92)
            'mckinsey': 0.92, 'bain': 0.90, 'bcg': 0.90, 'boston consulting': 0.90,
            'deloitte': 0.85, 'pwc': 0.84, 'ey': 0.83, 'kpmg': 0.82,
            
            # Tier 5: Other Fortune 100 (0.70-0.85)
            'berkshire hathaway': 0.85, 'jp morgan chase': 0.84,
            'bank of america': 0.82, 'wells fargo': 0.80,
            'walmart': 0.78, 'exxon': 0.75, 'chevron': 0.75,
            
            # Tier 6: Unicorn Startups (0.75-0.85)
            'bytedance': 0.85, 'spacex': 0.92, 'stripe': 0.90,
            'klarna': 0.80, 'revolut': 0.78, 'canva': 0.77,
            
            # Tier 7: Notable Tech Companies (0.65-0.80)
            'shopify': 0.80, 'zoom': 0.78, 'slack': 0.77, 'atlassian': 0.76,
            'spotify': 0.75, 'dropbox': 0.72, 'box': 0.70, 'twilio': 0.75,
            
            # Tier 8: Traditional Large Corps (0.60-0.75)
            'ibm': 0.72, 'intel': 0.75, 'cisco': 0.74, 'hp': 0.65,
            'dell': 0.67, 'general electric': 0.70, 'general motors': 0.68,
            
            # Default scoring for unknown companies
            'startup': 0.55, 'consulting': 0.60, 'agency': 0.50,
            'university': 0.65, 'government': 0.60, 'nonprofit': 0.50
        }
    
    def _load_title_mappings(self) -> Dict[str, float]:
        """Load enhanced job title seniority mappings"""
        return {
            # C-Suite & Founders (0.95-1.0)
            'ceo': 1.0, 'chief executive officer': 1.0, 'founder': 1.0,
            'co-founder': 0.98, 'cofounder': 0.98, 'president': 0.97,
            'chairman': 0.96, 'owner': 0.95, 'managing partner': 0.95,
            
            # C-Level Executives (0.90-0.95)
            'cto': 0.94, 'chief technology officer': 0.94,
            'cfo': 0.93, 'chief financial officer': 0.93,
            'coo': 0.92, 'chief operating officer': 0.92,
            'cmo': 0.91, 'chief marketing officer': 0.91,
            'cpo': 0.90, 'chief product officer': 0.90,
            'ciso': 0.90, 'chief information security officer': 0.90,
            
            # VP Level (0.80-0.89)
            'vp': 0.85, 'vice president': 0.85, 'svp': 0.88,
            'senior vice president': 0.88, 'evp': 0.87,
            'executive vice president': 0.87,
            
            # Director Level (0.70-0.82)
            'director': 0.78, 'senior director': 0.82, 'executive director': 0.80,
            'managing director': 0.85, 'head of': 0.75, 'chief of staff': 0.75,
            
            # Principal/Distinguished Level (0.65-0.75)
            'principal': 0.72, 'distinguished': 0.74, 'fellow': 0.73,
            'principal engineer': 0.75, 'principal scientist': 0.74,
            'distinguished engineer': 0.76, 'technical fellow': 0.75,
            
            # Manager Level (0.55-0.70)
            'manager': 0.62, 'senior manager': 0.68, 'group manager': 0.70,
            'program manager': 0.65, 'product manager': 0.67,
            'engineering manager': 0.68, 'team lead': 0.60, 'lead': 0.60,
            
            # Senior Individual Contributors (0.50-0.65)
            'senior': 0.58, 'sr': 0.58, 'staff': 0.62, 'senior staff': 0.65,
            'principal consultant': 0.65, 'senior consultant': 0.60,
            'architect': 0.65, 'senior architect': 0.68,
            
            # Regular Individual Contributors (0.40-0.55)
            'engineer': 0.50, 'developer': 0.48, 'software engineer': 0.50,
            'data scientist': 0.55, 'analyst': 0.45, 'consultant': 0.50,
            'designer': 0.48, 'researcher': 0.52, 'scientist': 0.54,
            
            # Junior/Entry Level (0.30-0.45)
            'junior': 0.35, 'jr': 0.35, 'associate': 0.40, 'assistant': 0.38,
            'coordinator': 0.42, 'specialist': 0.45, 'intern': 0.30,
            'trainee': 0.32, 'entry level': 0.35
        }
    
    def _load_social_scoring_factors(self) -> Dict[str, Dict[str, float]]:
        """Load social media scoring factors"""
        return {
            'linkedin': {
                'base_score': 0.3,  # Having LinkedIn profile
                'connection_multipliers': {
                    500: 1.0,    # 500+ connections = baseline
                    1000: 1.2,   # 1000+ connections = 20% bonus
                    5000: 1.5,   # 5000+ connections = 50% bonus
                    10000: 1.8   # 10k+ connections = 80% bonus
                },
                'premium_bonus': 0.1,  # LinkedIn Premium indicator
                'activity_bonus': 0.2   # Recent posts/activity
            },
            'twitter': {
                'base_score': 0.2,  # Having Twitter profile
                'follower_multipliers': {
                    1000: 1.0,     # 1k+ followers = baseline
                    10000: 1.3,    # 10k+ followers = 30% bonus
                    100000: 1.6,   # 100k+ followers = 60% bonus
                    1000000: 2.0   # 1M+ followers = 100% bonus
                },
                'verified_bonus': 0.3,  # Verified account
                'engagement_bonus': 0.15  # High engagement rate
            },
            'github': {
                'base_score': 0.25,  # Having GitHub (for tech roles)
                'repo_multipliers': {
                    10: 1.0,     # 10+ repos = baseline
                    50: 1.2,     # 50+ repos = 20% bonus
                    100: 1.4     # 100+ repos = 40% bonus
                },
                'star_multipliers': {
                    100: 1.1,    # 100+ stars = 10% bonus
                    1000: 1.3,   # 1k+ stars = 30% bonus
                    10000: 1.6   # 10k+ stars = 60% bonus
                },
                'contribution_bonus': 0.2  # Regular contributions
            },
            'personal_website': {
                'base_score': 0.15,  # Having personal website/blog
                'domain_authority_bonus': 0.1,  # High domain authority
                'content_quality_bonus': 0.1   # Quality content
            }
        }
    
    def _load_industry_mappings(self) -> Dict[str, float]:
        """Load industry importance mappings"""
        return {
            # High-value industries
            'technology': 0.95, 'software': 0.95, 'artificial intelligence': 1.0,
            'machine learning': 0.98, 'blockchain': 0.90, 'cryptocurrency': 0.85,
            'fintech': 0.92, 'biotech': 0.88, 'medtech': 0.85,
            
            # Finance & Investment
            'investment banking': 0.95, 'private equity': 0.92, 'venture capital': 0.90,
            'hedge fund': 0.88, 'asset management': 0.85, 'banking': 0.80,
            
            # Consulting
            'management consulting': 0.90, 'strategy consulting': 0.88,
            'technology consulting': 0.85, 'consulting': 0.75,
            
            # Healthcare & Life Sciences
            'pharmaceuticals': 0.85, 'biotechnology': 0.88, 'medical devices': 0.82,
            'healthcare': 0.75, 'life sciences': 0.80,
            
            # Traditional Industries
            'energy': 0.70, 'oil and gas': 0.68, 'manufacturing': 0.65,
            'automotive': 0.70, 'aerospace': 0.75, 'defense': 0.72,
            
            # Media & Entertainment
            'media': 0.68, 'entertainment': 0.65, 'gaming': 0.75,
            'streaming': 0.78, 'social media': 0.80,
            
            # Other
            'education': 0.60, 'government': 0.55, 'nonprofit': 0.45,
            'retail': 0.55, 'real estate': 0.60, 'legal': 0.70
        }
    
    async def calculate_comprehensive_score(self, contact: Contact) -> ContactScore:
        """
        Calculate comprehensive contact score with full AI and API integration
        """
        try:
            score = ContactScore()
            
            # 1. Traditional scoring components
            interaction_score = self._calculate_interaction_score(contact)
            response_score = self._calculate_response_rate_score(contact)
            recency_score = self._calculate_recency_score(contact)
            company_score = await self._calculate_enhanced_company_score(contact)
            title_score = await self._calculate_enhanced_title_score(contact)
            
            # 2. AI-enhanced sentiment scoring
            sentiment_score = await self._calculate_ai_sentiment_score(contact)
            
            # 3. NEW: Social media and network scoring
            social_influence_score = await self._calculate_social_influence_score(contact)
            network_quality_score = await self._calculate_network_quality_score(contact)
            content_engagement_score = await self._calculate_content_engagement_score(contact)
            
            # 4. Enhanced engagement scoring
            meeting_score = self._calculate_enhanced_meeting_score(contact)
            
            # 5. Calculate weighted overall score
            score.overall_score = (
                interaction_score * self.weights.interaction_frequency +
                response_score * self.weights.response_rate +
                recency_score * self.weights.recency +
                sentiment_score * self.weights.sentiment +
                company_score * self.weights.company_importance +
                title_score * self.weights.title_seniority +
                social_influence_score * self.weights.social_influence +
                network_quality_score * self.weights.network_quality +
                content_engagement_score * self.weights.content_engagement +
                meeting_score * self.weights.meeting_engagement
            )
            
            # 6. Set individual component scores
            score.relationship_strength = contact.calculate_relationship_strength()
            score.engagement_score = meeting_score
            score.importance_score = max(company_score, title_score, social_influence_score)
            score.response_likelihood = response_score
            score.influence_score = await self._calculate_comprehensive_influence_score(contact)
            score.deal_potential = await self._calculate_enhanced_deal_potential(contact)
            
            # 7. Enhanced communication patterns with AI
            comm_patterns = await self._analyze_ai_communication_patterns(contact)
            score.average_sentiment = comm_patterns.get('avg_sentiment', 0.0)
            score.sentiment_trend = comm_patterns.get('sentiment_trend', 'neutral')
            score.response_rate = response_score
            score.average_response_time = comm_patterns.get('avg_response_time', 0.0)
            score.best_contact_time = comm_patterns.get('best_contact_time', '')
            score.preferred_communication = comm_patterns.get('preferred_communication', 'email')
            
            # 8. Set dominant emotion from AI analysis
            if contact.ai_analysis and contact.ai_analysis.emotion_patterns:
                score.dominant_emotion = self._get_dominant_emotion(contact)
            
            # 9. Detailed scoring factors for transparency
            score.scoring_factors = {
                'interaction_frequency': interaction_score,
                'response_rate': response_score,
                'recency': recency_score,
                'sentiment': sentiment_score,
                'company_importance': company_score,
                'title_seniority': title_score,
                'social_influence': social_influence_score,
                'network_quality': network_quality_score,
                'content_engagement': content_engagement_score,
                'meeting_engagement': meeting_score,
                'total_interactions': contact.frequency,
                'days_since_last_contact': (datetime.now() - contact.last_seen).days,
                'has_meetings': contact.meeting_count > 0,
                'bidirectional_communication': contact.sent_to > 0 and contact.received_from > 0,
                'has_social_profiles': len(contact.social_profiles) > 0,
                'linkedin_connections': self._get_linkedin_connections(contact),
                'twitter_followers': self._get_twitter_followers(contact),
                'ai_sentiment_available': sentiment_score > 0.5,
                'enrichment_sources': len(contact.data_sources)
            }
            
            score.last_calculated = datetime.now()
            
            return score
            
        except Exception as e:
            self.logger.error(f"Error calculating enhanced contact score for {contact.email}: {e}")
            # Return basic score as fallback
            return self._calculate_basic_fallback_score(contact)
    
    # Traditional scoring methods (enhanced)
    def _calculate_interaction_score(self, contact: Contact) -> float:
        """Enhanced interaction scoring with email type weighting"""
        if contact.frequency == 0:
            return 0.0
        
        # Base logarithmic scaling
        base_score = math.log(contact.frequency + 1) / math.log(26)
        
        # Bonus for email variety (sent, received, CC, meetings)
        variety_bonus = 0.0
        if contact.sent_to > 0:
            variety_bonus += 0.1
        if contact.received_from > 0:
            variety_bonus += 0.1
        if contact.cc_count > 0:
            variety_bonus += 0.05
        if contact.meeting_count > 0:
            variety_bonus += 0.15  # Meetings are high value
        
        return min(base_score + variety_bonus, 1.0)
    
    def _calculate_response_rate_score(self, contact: Contact) -> float:
        """Enhanced response rate with response time consideration"""
        if contact.sent_to == 0:
            return 0.5  # Neutral score if no outbound emails
        
        # Basic response rate
        response_rate = contact.received_from / contact.sent_to
        
        # Response time bonus (if available from interactions)
        response_time_bonus = 0.0
        if hasattr(contact, 'interactions') and contact.interactions:
            avg_response_time = self._calculate_average_response_time(contact.interactions)
            if avg_response_time:
                # Quick responses get bonus (within 24 hours = max bonus)
                if avg_response_time <= 24:
                    response_time_bonus = 0.2 * (1 - avg_response_time / 24)
        
        # Bidirectional communication bonus
        balance_bonus = 0.0
        if contact.received_from > 0 and contact.sent_to > 0:
            balance = min(contact.sent_to, contact.received_from) / max(contact.sent_to, contact.received_from)
            balance_bonus = balance * 0.1
        
        total_score = response_rate + response_time_bonus + balance_bonus
        return min(total_score, 1.0)
    
    def _calculate_recency_score(self, contact: Contact) -> float:
        """Enhanced recency scoring with interaction pattern analysis"""
        days_since_last = (datetime.now() - contact.last_seen).days
        
        # Base recency score
        if days_since_last <= 1:
            base_score = 1.0
        elif days_since_last <= 7:
            base_score = 0.9
        elif days_since_last <= 30:
            base_score = 0.7
        elif days_since_last <= 90:
            base_score = 0.5
        elif days_since_last <= 180:
            base_score = 0.3
        else:
            base_score = 0.1
        
        # Consistency bonus - regular communication pattern
        consistency_bonus = 0.0
        if hasattr(contact, 'interactions') and len(contact.interactions) >= 3:
            # Calculate communication frequency consistency
            time_gaps = []
            sorted_interactions = sorted(contact.interactions, key=lambda x: x.timestamp)
            for i in range(1, len(sorted_interactions)):
                gap = (sorted_interactions[i].timestamp - sorted_interactions[i-1].timestamp).days
                time_gaps.append(gap)
            
            if time_gaps:
                # Lower variance in gaps = more consistent = bonus
                avg_gap = sum(time_gaps) / len(time_gaps)
                variance = sum((gap - avg_gap) ** 2 for gap in time_gaps) / len(time_gaps)
                consistency_bonus = max(0, 0.1 - variance / 1000)  # Normalize variance
        
        return min(base_score + consistency_bonus, 1.0)
    
    async def _calculate_enhanced_company_score(self, contact: Contact) -> float:
        """Enhanced company scoring with API enrichment and industry factors"""
        if not contact.company:
            # Try to get company from enrichment data
            company = self._get_enriched_company(contact)
            if not company:
                return 0.3  # Default for unknown company
        else:
            company = contact.company
        
        company_lower = company.lower()
        
        # 1. Direct company lookup
        for company_key, score in self.company_importance_scores.items():
            if company_key in company_lower:
                # Add industry bonus
                industry_bonus = self._get_industry_bonus(contact)
                return min(score + industry_bonus, 1.0)
        
        # 2. Pattern-based scoring for unlisted companies
        pattern_score = self._calculate_company_pattern_score(company_lower)
        
        # 3. Size estimation from enrichment data
        size_bonus = await self._estimate_company_size_bonus(contact, company)
        
        # 4. Industry importance
        industry_bonus = self._get_industry_bonus(contact)
        
        final_score = pattern_score + size_bonus + industry_bonus
        return min(final_score, 1.0)
    
    async def _calculate_enhanced_title_score(self, contact: Contact) -> float:
        """Enhanced title scoring with AI analysis and LinkedIn data"""
        # Get title from multiple sources
        titles = []
        if contact.job_title:
            titles.append(contact.job_title)
        
        # Get from enrichment data
        enriched_title = self._get_enriched_title(contact)
        if enriched_title:
            titles.append(enriched_title)
        
        # Get from LinkedIn if available
        linkedin_title = self._get_linkedin_title(contact)
        if linkedin_title:
            titles.append(linkedin_title)
        
        if not titles:
            return 0.4  # Default for unknown title
        
        # Score all titles and take the highest
        title_scores = []
        for title in titles:
            score = self._score_individual_title(title.lower())
            title_scores.append(score)
        
        base_score = max(title_scores) if title_scores else 0.4
        
        # AI enhancement - use OpenAI to analyze title context
        ai_bonus = 0.0
        if self.openai_analyzer and contact.interactions:
            try:
                # Use AI to infer seniority from email signature/content
                sample_interaction = contact.interactions[0] if contact.interactions else None
                if sample_interaction:
                    ai_analysis = await self.openai_analyzer.infer_job_title(
                        signature=sample_interaction.content_preview,
                        email_style="professional",
                        company=contact.company or ""
                    )
                    if ai_analysis.get('seniority_level'):
                        ai_confidence = ai_analysis.get('confidence', 0.0)
                        ai_bonus = ai_confidence * 0.1  # Up to 10% bonus from AI
            except Exception as e:
                self.logger.debug(f"AI title analysis failed: {e}")
        
        return min(base_score + ai_bonus, 1.0)
    
    async def _calculate_ai_sentiment_score(self, contact: Contact) -> float:
        """AI-enhanced sentiment scoring using HuggingFace and interaction analysis"""
        if not contact.interactions:
            return 0.5  # Neutral default
        
        sentiment_scores = []
        
        # 1. Use HuggingFace NLP for advanced sentiment analysis
        if self.nlp_engine:
            try:
                for interaction in contact.interactions[-10:]:  # Last 10 interactions
                    if interaction.content_preview:
                        sentiment_result = await self.nlp_engine.analyze_sentiment(
                            interaction.content_preview
                        )
                        if sentiment_result and sentiment_result.get('confidence', 0) > 0.7:
                            sentiment_type = sentiment_result['sentiment']
                            confidence = sentiment_result['confidence']
                            
                            if sentiment_type == SentimentType.POSITIVE:
                                sentiment_scores.append(confidence)
                            elif sentiment_type == SentimentType.NEGATIVE:
                                sentiment_scores.append(-confidence)
                            else:
                                sentiment_scores.append(0.0)
            except Exception as e:
                self.logger.debug(f"HuggingFace sentiment analysis failed: {e}")
        
        # 2. Fallback to basic sentiment analysis
        if not sentiment_scores:
            sentiment_scores = self._calculate_basic_sentiment_scores(contact.interactions)
        
        # 3. Calculate weighted average with recency bias
        if sentiment_scores:
            weighted_scores = []
            total_weight = 0
            
            for i, score in enumerate(sentiment_scores):
                # Recent interactions get higher weight
                weight = 1.0 + (i / len(sentiment_scores)) * 0.5
                weighted_scores.append(score * weight)
                total_weight += weight
            
            avg_sentiment = sum(weighted_scores) / total_weight
            
            # Convert to 0-1 scale
            return max(0.0, min(1.0, (avg_sentiment + 1.0) / 2.0))
        
        return 0.5  # Neutral default
    
    async def _calculate_social_influence_score(self, contact: Contact) -> float:
        """Calculate social media influence score"""
        if not contact.social_profiles:
            return 0.0
        
        total_influence = 0.0
        max_possible = 0.0
        
        # LinkedIn scoring
        linkedin_profile = contact.get_social_profile('linkedin')
        if linkedin_profile:
            linkedin_score = self._score_linkedin_profile(linkedin_profile, contact)
            total_influence += linkedin_score
            max_possible += 1.0
        
        # Twitter scoring
        twitter_profile = contact.get_social_profile('twitter')
        if twitter_profile:
            twitter_score = self._score_twitter_profile(twitter_profile)
            total_influence += twitter_score
            max_possible += 0.8  # Twitter less valuable than LinkedIn for B2B
        
        # GitHub scoring (for tech roles)
        github_profile = contact.get_social_profile('github')
        if github_profile and self._is_tech_role(contact):
            github_score = self._score_github_profile(github_profile)
            total_influence += github_score
            max_possible += 0.6
        
        # Personal website/blog
        website = self._get_personal_website(contact)
        if website:
            website_score = self._score_personal_website(website)
            total_influence += website_score
            max_possible += 0.4
        
        # Normalize to 0-1 scale
        if max_possible > 0:
            return min(total_influence / max_possible, 1.0)
        
        return 0.0
    
    async def _calculate_network_quality_score(self, contact: Contact) -> float:
        """Calculate network quality based on connections and mutual contacts"""
        network_score = 0.0
        
        # LinkedIn network quality
        linkedin_profile = contact.get_social_profile('linkedin')
        if linkedin_profile:
            # Connection count quality
            connections = self._get_linkedin_connections(contact)
            if connections:
                if connections >= 500:
                    network_score += 0.3
                if connections >= 1000:
                    network_score += 0.2
                if connections >= 5000:
                    network_score += 0.2
            
            # Industry relevance (if we can determine it)
            if self._is_industry_relevant_profile(linkedin_profile, contact):
                network_score += 0.2
        
        # Mutual connections (would require LinkedIn API)
        # For now, estimate based on company and industry
        mutual_estimate = self._estimate_mutual_connections(contact)
        network_score += mutual_estimate * 0.3
        
        return min(network_score, 1.0)
    
    async def _calculate_content_engagement_score(self, contact: Contact) -> float:
        """Calculate content engagement score from social media activity"""
        engagement_score = 0.0
        
        # Twitter engagement
        twitter_profile = contact.get_social_profile('twitter')
        if twitter_profile:
            # High follower count suggests good content
            followers = self._get_twitter_followers(contact)
            if followers:
                if followers >= 1000:
                    engagement_score += 0.2
                if followers >= 10000:
                    engagement_score += 0.3
                if followers >= 100000:
                    engagement_score += 0.2
        
        # LinkedIn content indicators
        linkedin_profile = contact.get_social_profile('linkedin')
        if linkedin_profile:
            # Premium account suggests active user
            if self._has_linkedin_premium_indicators(linkedin_profile):
                engagement_score += 0.2
            
            # Industry thought leadership indicators
            if self._has_thought_leadership_indicators(contact):
                engagement_score += 0.3
        
        return min(engagement_score, 1.0)
    
    def _calculate_enhanced_meeting_score(self, contact: Contact) -> float:
        """Enhanced meeting engagement scoring"""
        total_meetings = contact.meeting_count + contact.call_count
        
        if total_meetings == 0:
            return 0.0
        
        # Base meeting score
        if contact.frequency > 0:
            meeting_ratio = total_meetings / contact.frequency
            base_score = min(meeting_ratio * 2.0, 1.0)
        else:
            base_score = min(total_meetings / 5.0, 1.0)
        
        # Meeting frequency bonus
        frequency_bonus = 0.0
        if total_meetings >= 5:
            frequency_bonus = 0.2
        elif total_meetings >= 10:
            frequency_bonus = 0.3
        
        # Recent meeting bonus
        recent_bonus = 0.0
        if hasattr(contact, 'interactions'):
            recent_meetings = [i for i in contact.interactions 
                             if i.type in [InteractionType.MEETING, InteractionType.CALL]
                             and (datetime.now() - i.timestamp).days <= 30]
            if recent_meetings:
                recent_bonus = 0.1
        
        return min(base_score + frequency_bonus + recent_bonus, 1.0)
    
    async def _calculate_comprehensive_influence_score(self, contact: Contact) -> float:
        """Calculate comprehensive influence score combining all factors"""
        influence_factors = []
        
        # 1. Company influence (40%)
        company_score = await self._calculate_enhanced_company_score(contact)
        influence_factors.append(company_score * 0.4)
        
        # 2. Title influence (30%)
        title_score = await self._calculate_enhanced_title_score(contact)
        influence_factors.append(title_score * 0.3)
        
        # 3. Social media influence (20%)
        social_score = await self._calculate_social_influence_score(contact)
        influence_factors.append(social_score * 0.2)
        
        # 4. Network influence (10%)
        network_score = await self._calculate_network_quality_score(contact)
        influence_factors.append(network_score * 0.1)
        
        return sum(influence_factors)
    
    async def _calculate_enhanced_deal_potential(self, contact: Contact) -> float:
        """Enhanced deal potential calculation with AI insights"""
        potential_factors = []
        
        # 1. Industry factor (25%)
        industry_score = self._get_industry_deal_potential(contact)
        potential_factors.append(industry_score * 0.25)
        
        # 2. Company size factor (25%)
        company_size_score = await self._get_company_size_deal_potential(contact)
        potential_factors.append(company_size_score * 0.25)
        
        # 3. Decision maker factor (20%)
        decision_maker_score = await self._calculate_enhanced_title_score(contact)
        potential_factors.append(decision_maker_score * 0.20)
        
        # 4. Engagement history factor (15%)
        engagement_score = self._calculate_engagement_deal_potential(contact)
        potential_factors.append(engagement_score * 0.15)
        
        # 5. AI-analyzed communication intent (10%)
        intent_score = await self._analyze_communication_intent(contact)
        potential_factors.append(intent_score * 0.10)
        
        # 6. Network warmth factor (5%)
        warmth_score = self._calculate_network_warmth(contact)
        potential_factors.append(warmth_score * 0.05)
        
        return sum(potential_factors)
    
    async def _analyze_ai_communication_patterns(self, contact: Contact) -> Dict[str, Any]:
        """Enhanced communication pattern analysis with AI"""
        patterns = {
            'avg_sentiment': 0.0,
            'sentiment_trend': 'neutral',
            'avg_response_time': 0.0,
            'best_contact_time': '',
            'preferred_communication': 'email',
            'communication_style': 'unknown',
            'urgency_level': 'normal',
            'business_relevance': 'medium'
        }
        
        if not contact.interactions:
            return patterns
        
        # 1. AI-enhanced sentiment analysis
        if self.nlp_engine:
            try:
                sentiment_results = []
                for interaction in contact.interactions[-10:]:
                    if interaction.content_preview:
                        result = await self.nlp_engine.analyze_sentiment(interaction.content_preview)
                        if result:
                            sentiment_results.append(result)
                
                if sentiment_results:
                    avg_sentiment = sum(r.get('confidence', 0) * (1 if r.get('sentiment') == SentimentType.POSITIVE else -1) 
                                      for r in sentiment_results) / len(sentiment_results)
                    patterns['avg_sentiment'] = (avg_sentiment + 1) / 2  # Normalize to 0-1
                    
                    # Sentiment trend
                    if len(sentiment_results) >= 4:
                        recent_avg = sum(r.get('confidence', 0) for r in sentiment_results[-2:]) / 2
                        older_avg = sum(r.get('confidence', 0) for r in sentiment_results[:-2]) / len(sentiment_results[:-2])
                        
                        if recent_avg > older_avg + 0.1:
                            patterns['sentiment_trend'] = 'improving'
                        elif recent_avg < older_avg - 0.1:
                            patterns['sentiment_trend'] = 'declining'
                        else:
                            patterns['sentiment_trend'] = 'stable'
            except Exception as e:
                self.logger.debug(f"AI sentiment analysis failed: {e}")
        
        # 2. Communication style analysis with OpenAI
        if self.openai_analyzer and contact.interactions:
            try:
                sample_interaction = contact.interactions[-1]
                style_analysis = await self.openai_analyzer.analyze_communication_patterns(
                    sample_interaction,
                    self._calculate_average_response_time(contact.interactions)
                )
                if style_analysis:
                    patterns.update(style_analysis)
            except Exception as e:
                self.logger.debug(f"OpenAI communication analysis failed: {e}")
        
        # 3. Fallback to basic analysis
        patterns.update(self._calculate_basic_communication_patterns(contact))
        
        return patterns
    
    # Helper methods for social media scoring
    def _score_linkedin_profile(self, profile, contact: Contact) -> float:
        """Score LinkedIn profile comprehensively"""
        score = self.social_scoring_factors['linkedin']['base_score']  # 0.3 base
        
        # Connection count bonus
        connections = self._get_linkedin_connections(contact)
        if connections:
            for threshold, multiplier in self.social_scoring_factors['linkedin']['connection_multipliers'].items():
                if connections >= threshold:
                    score *= multiplier
        
        # Premium indicators
        if self._has_linkedin_premium_indicators(profile):
            score += self.social_scoring_factors['linkedin']['premium_bonus']
        
        # Recent activity indicators
        if self._has_linkedin_activity_indicators(profile):
            score += self.social_scoring_factors['linkedin']['activity_bonus']
        
        return min(score, 1.0)
    
    def _score_twitter_profile(self, profile) -> float:
        """Score Twitter profile"""
        score = self.social_scoring_factors['twitter']['base_score']  # 0.2 base
        
        # Follower count bonus
        followers = getattr(profile, 'followers', 0)
        if followers:
            for threshold, multiplier in self.social_scoring_factors['twitter']['follower_multipliers'].items():
                if followers >= threshold:
                    score *= multiplier
        
        # Verified account bonus
        if getattr(profile, 'verified', False):
            score += self.social_scoring_factors['twitter']['verified_bonus']
        
        # High engagement indicators
        if self._has_high_twitter_engagement(profile):
            score += self.social_scoring_factors['twitter']['engagement_bonus']
        
        return min(score, 1.0)
    
    def _score_github_profile(self, profile) -> float:
        """Score GitHub profile (for tech roles)"""
        score = self.social_scoring_factors['github']['base_score']  # 0.25 base
        
        # Repository count (estimated from profile data)
        repos = self._estimate_github_repos(profile)
        if repos:
            for threshold, multiplier in self.social_scoring_factors['github']['repo_multipliers'].items():
                if repos >= threshold:
                    score *= multiplier
        
        # Stars/popularity (estimated)
        stars = self._estimate_github_stars(profile)
        if stars:
            for threshold, multiplier in self.social_scoring_factors['github']['star_multipliers'].items():
                if stars >= threshold:
                    score *= multiplier
        
        # Regular contributions
        if self._has_regular_github_contributions(profile):
            score += self.social_scoring_factors['github']['contribution_bonus']
        
        return min(score, 1.0)
    
    def _score_personal_website(self, website: str) -> float:
        """Score personal website/blog"""
        score = self.social_scoring_factors['personal_website']['base_score']  # 0.15 base
        
        # Domain authority indicators (basic heuristics)
        if self._has_custom_domain(website):
            score += 0.05
        
        if self._has_professional_content_indicators(website):
            score += self.social_scoring_factors['personal_website']['content_quality_bonus']
        
        return min(score, 1.0)
    
    # Enhanced enrichment data extraction
    def _get_enriched_company(self, contact: Contact) -> Optional[str]:
        """Get company from enrichment data"""
        # Check enrichment_data attribute
        if hasattr(contact, 'enrichment_data') and contact.enrichment_data:
            return contact.enrichment_data.get('company')
        
        # Check data sources
        for source in contact.data_sources:
            if 'clearbit' in source.lower():
                # Try to extract from Clearbit data
                return self._extract_clearbit_company(contact)
            elif 'hunter' in source.lower():
                return self._extract_hunter_company(contact)
            elif 'peopledatalabs' in source.lower() or 'pdl' in source.lower():
                return self._extract_pdl_company(contact)
        
        return None
    
    def _get_enriched_title(self, contact: Contact) -> Optional[str]:
        """Get job title from enrichment data"""
        if hasattr(contact, 'enrichment_data') and contact.enrichment_data:
            return contact.enrichment_data.get('job_title')
        return None
    
    def _get_linkedin_title(self, contact: Contact) -> Optional[str]:
        """Get job title from LinkedIn profile"""
        linkedin_profile = contact.get_social_profile('linkedin')
        if linkedin_profile and hasattr(linkedin_profile, 'job_title'):
            return linkedin_profile.job_title
        return None
    
    def _get_linkedin_connections(self, contact: Contact) -> Optional[int]:
        """Get LinkedIn connection count"""
        linkedin_profile = contact.get_social_profile('linkedin')
        if linkedin_profile:
            # Try to get from profile data
            if hasattr(linkedin_profile, 'connections'):
                return linkedin_profile.connections
            # Try to estimate from enrichment data
            return self._estimate_linkedin_connections(contact)
        return None
    
    def _get_twitter_followers(self, contact: Contact) -> Optional[int]:
        """Get Twitter follower count"""
        twitter_profile = contact.get_social_profile('twitter')
        if twitter_profile and hasattr(twitter_profile, 'followers'):
            return twitter_profile.followers
        return None
    
    # Industry and company analysis helpers
    def _get_industry_bonus(self, contact: Contact) -> float:
        """Get industry importance bonus"""
        industry = contact.industry or self._get_enriched_industry(contact)
        if not industry:
            return 0.0
        
        industry_lower = industry.lower()
        for industry_key, importance in self.industry_importance.items():
            if industry_key in industry_lower:
                return (importance - 0.5) * 0.2  # Convert to bonus (max 0.1)
        
        return 0.0
    
    def _calculate_company_pattern_score(self, company_lower: str) -> float:
        """Calculate company score based on patterns"""
        # Tech company indicators
        tech_indicators = ['tech', 'software', 'digital', 'ai', 'data', 'cloud', 'cyber']
        if any(indicator in company_lower for indicator in tech_indicators):
            return 0.75
        
        # Finance indicators
        finance_indicators = ['bank', 'capital', 'investment', 'fund', 'trading', 'financial']
        if any(indicator in company_lower for indicator in finance_indicators):
            return 0.70
        
        # Consulting indicators
        consulting_indicators = ['consulting', 'advisory', 'strategy']
        if any(indicator in company_lower for indicator in consulting_indicators):
            return 0.68
        
        # Healthcare indicators
        health_indicators = ['health', 'medical', 'pharma', 'bio', 'hospital']
        if any(indicator in company_lower for indicator in health_indicators):
            return 0.65
        
        # Startup indicators
        startup_indicators = ['startup', 'inc', 'llc', 'ltd']
        if any(indicator in company_lower for indicator in startup_indicators):
            return 0.55
        
        return 0.50  # Default for unknown patterns
    
    async def _estimate_company_size_bonus(self, contact: Contact, company: str) -> float:
        """Estimate company size bonus from enrichment data"""
        # Check enrichment data for employee count
        if hasattr(contact, 'enrichment_data') and contact.enrichment_data:
            employee_count = contact.enrichment_data.get('employee_count')
            if employee_count:
                return self._employee_count_to_bonus(employee_count)
        
        # Use domain analysis as fallback
        domain = contact.domain
        if domain:
            # Well-known large company domains
            if any(big_domain in domain for big_domain in ['.com', '.org', '.net']) and len(domain.split('.')) == 2:
                return 0.1  # Established domain structure
        
        return 0.0
    
    def _employee_count_to_bonus(self, employee_count) -> float:
        """Convert employee count to size bonus"""
        try:
            if isinstance(employee_count, str):
                # Extract number from string like "1000-5000"
                numbers = re.findall(r'\d+', employee_count)
                if numbers:
                    employee_count = int(numbers[-1])  # Use upper bound
                else:
                    return 0.0
            
            if employee_count >= 10000:
                return 0.15  # Large enterprise
            elif employee_count >= 1000:
                return 0.10  # Medium enterprise
            elif employee_count >= 100:
                return 0.05  # Small-medium business
            else:
                return 0.0   # Small business/startup
                
        except (ValueError, TypeError):
            return 0.0
    
    # Fallback scoring methods
    def _calculate_basic_fallback_score(self, contact: Contact) -> ContactScore:
        """Calculate basic fallback score when AI/API fails"""
        score = ContactScore()
        
        # Use traditional scoring only
        interaction_score = self._calculate_interaction_score(contact)
        response_score = self._calculate_response_rate_score(contact)
        recency_score = self._calculate_recency_score(contact)
        
        # Basic company/title scoring
        company_score = 0.4
        if contact.company:
            company_lower = contact.company.lower()
            if any(big_tech in company_lower for big_tech in ['google', 'apple', 'microsoft', 'amazon']):
                company_score = 0.9
            elif 'university' in company_lower or '.edu' in company_lower:
                company_score = 0.6
        
        title_score = 0.4
        if contact.job_title:
            title_lower = contact.job_title.lower()
            if any(exec_term in title_lower for exec_term in ['ceo', 'cto', 'founder', 'vp']):
                title_score = 0.9
            elif 'manager' in title_lower or 'director' in title_lower:
                title_score = 0.7
        
        # Simple weighted average
        score.overall_score = (
            interaction_score * 0.30 +
            response_score * 0.25 +
            recency_score * 0.20 +
            company_score * 0.15 +
            title_score * 0.10
        )
        
        score.relationship_strength = contact.calculate_relationship_strength()
        score.engagement_score = 0.5
        score.importance_score = max(company_score, title_score)
        score.response_likelihood = response_score
        score.last_calculated = datetime.now()
        
        return score
    
    def _calculate_basic_sentiment_scores(self, interactions: List[Interaction]) -> List[float]:
        """Basic sentiment analysis fallback"""
        sentiment_scores = []
        
        positive_keywords = ['thank', 'great', 'excellent', 'good', 'pleased', 'happy', 'wonderful']
        negative_keywords = ['sorry', 'problem', 'issue', 'concern', 'disappointed', 'frustrated']
        
        for interaction in interactions:
            if interaction.content_preview:
                content_lower = interaction.content_preview.lower()
                
                positive_count = sum(1 for word in positive_keywords if word in content_lower)
                negative_count = sum(1 for word in negative_keywords if word in content_lower)
                
                if positive_count > negative_count:
                    sentiment_scores.append(0.7)
                elif negative_count > positive_count:
                    sentiment_scores.append(-0.7)
                else:
                    sentiment_scores.append(0.0)
        
        return sentiment_scores
    
    def _calculate_basic_communication_patterns(self, contact: Contact) -> Dict[str, Any]:
        """Basic communication pattern analysis fallback"""
        patterns = {}
        
        if not contact.interactions:
            return patterns
        
        # Response time analysis
        response_times = []
        sorted_interactions = sorted(contact.interactions, key=lambda x: x.timestamp)
        
        for i in range(len(sorted_interactions) - 1):
            current = sorted_interactions[i]
            next_interaction = sorted_interactions[i + 1]
            
            if (current.direction == "outbound" and 
                next_interaction.direction == "inbound" and
                next_interaction.timestamp > current.timestamp):
                
                response_time = (next_interaction.timestamp - current.timestamp).total_seconds() / 3600
                response_times.append(response_time)
        
        if response_times:
            patterns['avg_response_time'] = sum(response_times) / len(response_times)
        
        # Best contact time analysis
        interaction_hours = [interaction.timestamp.hour for interaction in contact.interactions]
        if interaction_hours:
            hour_counts = defaultdict(int)
            for hour in interaction_hours:
                hour_counts[hour] += 1
            
            best_hour = max(hour_counts.items(), key=lambda x: x[1])[0]
            
            if 6 <= best_hour < 12:
                patterns['best_contact_time'] = 'morning'
            elif 12 <= best_hour < 17:
                patterns['best_contact_time'] = 'afternoon'
            elif 17 <= best_hour < 20:
                patterns['best_contact_time'] = 'evening'
            else:
                patterns['best_contact_time'] = 'off-hours'
        
        # Communication preference
        if contact.meeting_count > contact.frequency * 0.3:
            patterns['preferred_communication'] = 'meetings'
        elif contact.call_count > contact.frequency * 0.2:
            patterns['preferred_communication'] = 'calls'
        else:
            patterns['preferred_communication'] = 'email'
        
        return patterns
    
    # Utility methods for detailed analysis
    def _calculate_average_response_time(self, interactions: List[Interaction]) -> Optional[float]:
        """Calculate average response time in hours"""
        response_times = []
        sorted_interactions = sorted(interactions, key=lambda x: x.timestamp)
        
        for i in range(len(sorted_interactions) - 1):
            current = sorted_interactions[i]
            next_interaction = sorted_interactions[i + 1]
            
            if (current.direction == "outbound" and 
                next_interaction.direction == "inbound" and
                next_interaction.timestamp > current.timestamp):
                
                response_time = (next_interaction.timestamp - current.timestamp).total_seconds() / 3600
                response_times.append(response_time)
        
        return sum(response_times) / len(response_times) if response_times else None
    
    def _get_dominant_emotion(self, contact: Contact) -> EmotionType:
        """Get dominant emotion from AI analysis"""
        if not contact.ai_analysis or not contact.ai_analysis.emotion_patterns:
            return EmotionType.NEUTRAL
        
        emotion_patterns = contact.ai_analysis.emotion_patterns
        
        max_emotion = EmotionType.NEUTRAL
        max_score = 0.0
        
        for emotion, score in emotion_patterns.items():
            if isinstance(emotion, EmotionType) and score > max_score:
                max_emotion = emotion
                max_score = score
        
        return max_emotion
    
    def _score_individual_title(self, title_lower: str) -> float:
        """Score individual job title"""
        for title_keyword, score in self.title_seniority_scores.items():
            if title_keyword in title_lower:
                return score
        
        # Pattern-based fallback scoring
        if any(exec in title_lower for exec in ['executive', 'owner', 'partner']):
            return 0.8
        elif any(mgr in title_lower for mgr in ['management', 'supervisor']):
            return 0.6
        elif any(tech in title_lower for tech in ['developer', 'engineer', 'architect']):
            return 0.5
        else:
            return 0.4
    
    # Additional helper methods for social media analysis
    def _is_tech_role(self, contact: Contact) -> bool:
        """Check if contact has a tech role"""
        if contact.job_title:
            tech_keywords = ['engineer', 'developer', 'architect', 'programmer', 'tech', 'software']
            return any(keyword in contact.job_title.lower() for keyword in tech_keywords)
        return False
    
    def _get_personal_website(self, contact: Contact) -> Optional[str]:
        """Extract personal website from contact data"""
        # Check enrichment data
        if hasattr(contact, 'enrichment_data') and contact.enrichment_data:
            return contact.enrichment_data.get('website')
        return None
    
    def _has_linkedin_premium_indicators(self, profile) -> bool:
        """Check for LinkedIn premium indicators"""
        # This would be enhanced with actual LinkedIn data
        return False
    
    def _has_linkedin_activity_indicators(self, profile) -> bool:
        """Check for LinkedIn activity indicators"""
        # This would be enhanced with actual LinkedIn data
        return False
    
    def _has_high_twitter_engagement(self, profile) -> bool:
        """Check for high Twitter engagement"""
        # Basic heuristic: followers vs following ratio
        followers = getattr(profile, 'followers', 0)
        following = getattr(profile, 'following', 0)
        
        if followers > 0 and following > 0:
            ratio = followers / following
            return ratio > 2.0  # More followers than following
        
        return False
    
    def _estimate_github_repos(self, profile) -> int:
        """Estimate GitHub repository count"""
        # This would need actual GitHub API integration
        # For now, return conservative estimate
        return 0
    
    def _estimate_github_stars(self, profile) -> int:
        """Estimate GitHub stars count"""
        # This would need actual GitHub API integration
        return 0
    
    def _has_regular_github_contributions(self, profile) -> bool:
        """Check for regular GitHub contributions"""
        # This would need actual GitHub API integration
        return False
    
    def _has_custom_domain(self, website: str) -> bool:
        """Check if website has custom domain"""
        common_platforms = ['wordpress.com', 'blogspot.com', 'wix.com', 'squarespace.com']
        return not any(platform in website.lower() for platform in common_platforms)
    
    def _has_professional_content_indicators(self, website: str) -> bool:
        """Check for professional content indicators"""
        # This would need web scraping or content analysis
        # For now, use domain heuristics
        professional_indicators = ['blog', 'portfolio', 'consulting', 'about']
        return any(indicator in website.lower() for indicator in professional_indicators)
    
    def _is_industry_relevant_profile(self, profile, contact: Contact) -> bool:
        """Check if LinkedIn profile is industry relevant"""
        # This would be enhanced with actual LinkedIn industry data
        return True  # Conservative default
    
    def _estimate_mutual_connections(self, contact: Contact) -> float:
        """Estimate mutual connections based on company and industry"""
        score = 0.0
        
        # Same company = higher mutual connection probability
        if contact.company:
            company_lower = contact.company.lower()
            if any(big_tech in company_lower for big_tech in ['google', 'apple', 'microsoft', 'amazon']):
                score += 0.8  # High probability of mutual connections
            elif any(consulting in company_lower for consulting in ['mckinsey', 'bain', 'bcg']):
                score += 0.7
            else:
                score += 0.3
        
        # Industry factor
        if contact.industry:
            industry_lower = contact.industry.lower()
            if 'technology' in industry_lower or 'software' in industry_lower:
                score += 0.2  # Tech has more connected networks
        
        return min(score, 1.0)
    
    def _has_thought_leadership_indicators(self, contact: Contact) -> bool:
        """Check for thought leadership indicators"""
        # Check if person has speaking engagements, publications, etc.
        # This would be enhanced with actual data
        
        # Basic heuristics
        if contact.job_title:
            title_lower = contact.job_title.lower()
            leadership_titles = ['head of', 'chief', 'vp', 'director', 'principal', 'lead']
            return any(title in title_lower for title in leadership_titles)
        
        return False
    
    def _estimate_linkedin_connections(self, contact: Contact) -> Optional[int]:
        """Estimate LinkedIn connections from available data"""
        # Estimate based on job title and company
        base_connections = 100
        
        if contact.job_title:
            title_lower = contact.job_title.lower()
            if any(exec in title_lower for exec in ['ceo', 'cto', 'founder', 'vp']):
                base_connections = 2000
            elif any(senior in title_lower for senior in ['director', 'head of', 'principal']):
                base_connections = 1000
            elif 'manager' in title_lower or 'lead' in title_lower:
                base_connections = 500
        
        # Company size factor
        if contact.company:
            company_lower = contact.company.lower()
            if any(big_tech in company_lower for big_tech in ['google', 'apple', 'microsoft']):
                base_connections *= 2
        
        return base_connections
    
    def _get_enriched_industry(self, contact: Contact) -> Optional[str]:
        """Get industry from enrichment data"""
        if hasattr(contact, 'enrichment_data') and contact.enrichment_data:
            return contact.enrichment_data.get('industry')
        return None
    
    def _extract_clearbit_company(self, contact: Contact) -> Optional[str]:
        """Extract company from Clearbit enrichment data"""
        # This would parse Clearbit-specific data structure
        if hasattr(contact, 'enrichment_data'):
            return contact.enrichment_data.get('company')
        return None
    
    def _extract_hunter_company(self, contact: Contact) -> Optional[str]:
        """Extract company from Hunter.io enrichment data"""
        if hasattr(contact, 'enrichment_data'):
            return contact.enrichment_data.get('company')
        return None
    
    def _extract_pdl_company(self, contact: Contact) -> Optional[str]:
        """Extract company from People Data Labs enrichment data"""
        if hasattr(contact, 'enrichment_data'):
            return contact.enrichment_data.get('company')
        return None
    
    def _get_industry_deal_potential(self, contact: Contact) -> float:
        """Get deal potential based on industry"""
        industry = contact.industry or self._get_enriched_industry(contact)
        if not industry:
            return 0.5
        
        industry_lower = industry.lower()
        
        # High-value industries for deals
        if any(tech in industry_lower for tech in ['technology', 'software', 'saas', 'fintech']):
            return 0.9
        elif any(finance in industry_lower for finance in ['finance', 'banking', 'investment']):
            return 0.85
        elif 'consulting' in industry_lower:
            return 0.8
        elif any(health in industry_lower for health in ['healthcare', 'biotech', 'medical']):
            return 0.75
        else:
            return 0.6
    
    async def _get_company_size_deal_potential(self, contact: Contact) -> float:
        """Get deal potential based on company size"""
        # Check enrichment data for company size indicators
        if hasattr(contact, 'enrichment_data') and contact.enrichment_data:
            employee_count = contact.enrichment_data.get('employee_count')
            revenue = contact.enrichment_data.get('company_revenue')
            
            if employee_count:
                if isinstance(employee_count, str) and 'thousand' in employee_count.lower():
                    return 0.95  # Very large company
                elif isinstance(employee_count, int):
                    if employee_count >= 10000:
                        return 0.9
                    elif employee_count >= 1000:
                        return 0.8
                    elif employee_count >= 100:
                        return 0.6
                    else:
                        return 0.4
            
            if revenue:
                # Parse revenue strings like "$1B+", "$100M-$500M"
                if 'billion' in str(revenue).lower() or 'b' in str(revenue).lower():
                    return 0.9
                elif 'million' in str(revenue).lower() or 'm' in str(revenue).lower():
                    return 0.7
                else:
                    return 0.5
        
        # Fallback based on company name recognition
        if contact.company:
            company_score = await self._calculate_enhanced_company_score(contact)
            return company_score * 0.8  # Convert company importance to deal potential
        
        return 0.5
    
    def _calculate_engagement_deal_potential(self, contact: Contact) -> float:
        """Calculate deal potential based on engagement history"""
        if contact.frequency == 0:
            return 0.0
        
        # High interaction frequency suggests interest
        frequency_score = min(contact.frequency / 20.0, 1.0)
        
        # Bidirectional communication is crucial for deals
        bidirectional_bonus = 0.0
        if contact.sent_to > 0 and contact.received_from > 0:
            response_ratio = min(contact.received_from / contact.sent_to, 1.0)
            bidirectional_bonus = response_ratio * 0.3
        
        # Meeting engagement is highest indicator
        meeting_bonus = 0.0
        total_meetings = contact.meeting_count + contact.call_count
        if total_meetings > 0:
            meeting_bonus = min(total_meetings / 5.0, 0.4)
        
        # Recent engagement matters
        recency_bonus = 0.0
        days_since_last = (datetime.now() - contact.last_seen).days
        if days_since_last <= 7:
            recency_bonus = 0.2
        elif days_since_last <= 30:
            recency_bonus = 0.1
        
        total_score = frequency_score + bidirectional_bonus + meeting_bonus + recency_bonus
        return min(total_score, 1.0)
    
    async def _analyze_communication_intent(self, contact: Contact) -> float:
        """Analyze communication intent using AI"""
        if not contact.interactions:
            return 0.5
        
        # Use OpenAI to analyze business intent in communications
        if self.openai_analyzer:
            try:
                # Analyze recent interactions for business intent
                recent_interactions = contact.interactions[-5:]  # Last 5 interactions
                
                intent_scores = []
                for interaction in recent_interactions:
                    if interaction.content_preview:
                        # Use OpenAI to classify business intent
                        company_analysis = await self.openai_analyzer.extract_company_information(
                            interaction.content_preview,
                            interaction.subject
                        )
                        
                        if company_analysis and company_analysis.get('business_context'):
                            business_context = company_analysis['business_context']
                            
                            # Score business intent
                            if 'proposal' in business_context.lower():
                                intent_scores.append(0.9)
                            elif 'meeting' in business_context.lower():
                                intent_scores.append(0.8)
                            elif 'partnership' in business_context.lower():
                                intent_scores.append(0.7)
                            elif 'project' in business_context.lower():
                                intent_scores.append(0.6)
                            else:
                                intent_scores.append(0.4)
                
                if intent_scores:
                    return sum(intent_scores) / len(intent_scores)
                    
            except Exception as e:
                self.logger.debug(f"AI intent analysis failed: {e}")
        
        # Fallback: basic keyword analysis
        intent_keywords = {
            'high': ['proposal', 'contract', 'deal', 'partnership', 'project', 'opportunity'],
            'medium': ['meeting', 'discussion', 'collaboration', 'interested', 'explore'],
            'low': ['follow up', 'checking in', 'hello', 'introduction']
        }
        
        intent_scores = []
        for interaction in contact.interactions[-5:]:
            if interaction.content_preview:
                content_lower = interaction.content_preview.lower()
                
                if any(keyword in content_lower for keyword in intent_keywords['high']):
                    intent_scores.append(0.8)
                elif any(keyword in content_lower for keyword in intent_keywords['medium']):
                    intent_scores.append(0.6)
                elif any(keyword in content_lower for keyword in intent_keywords['low']):
                    intent_scores.append(0.4)
                else:
                    intent_scores.append(0.5)
        
        return sum(intent_scores) / len(intent_scores) if intent_scores else 0.5
    
    def _calculate_network_warmth(self, contact: Contact) -> float:
        """Calculate network warmth factor"""
        warmth_score = 0.0
        
        # Mutual connections (estimated)
        mutual_estimate = self._estimate_mutual_connections(contact)
        warmth_score += mutual_estimate * 0.4
        
        # Introduction path length (estimated)
        # Shorter paths = warmer connections
        if contact.company:
            # Same company connections are warmest
            warmth_score += 0.3
        
        # Social media connections
        if contact.social_profiles:
            # Having social profiles suggests more open to networking
            warmth_score += 0.3
        
        return min(warmth_score, 1.0)
    
    # Batch processing methods
    async def score_contacts_batch(self, contacts: List[Contact]) -> Dict[str, ContactScore]:
        """Score multiple contacts efficiently with progress reporting"""
        scores = {}
        total_contacts = len(contacts)
        
        self.logger.info(f"Starting batch scoring for {total_contacts} contacts")
        
        # Process in batches to manage memory and API rate limits
        batch_size = 10
        successful_scores = 0
        
        for i in range(0, total_contacts, batch_size):
            batch = contacts[i:i + batch_size]
            batch_start = i + 1
            batch_end = min(i + batch_size, total_contacts)
            
            self.logger.info(f"Processing contacts {batch_start}-{batch_end} of {total_contacts}")
            
            for contact in batch:
                try:
                    score = await self.calculate_comprehensive_score(contact)
                    scores[contact.email] = score
                    successful_scores += 1
                    
                    # Update contact with calculated score
                    contact.contact_score = score
                    
                except Exception as e:
                    self.logger.error(f"Failed to score contact {contact.email}: {e}")
                    # Add fallback score
                    scores[contact.email] = self._calculate_basic_fallback_score(contact)
            
            # Small delay between batches to respect rate limits
            if i + batch_size < total_contacts:
                await asyncio.sleep(0.5)
        
        success_rate = (successful_scores / total_contacts) * 100 if total_contacts > 0 else 0
        self.logger.info(f"Batch scoring completed: {successful_scores}/{total_contacts} contacts scored successfully ({success_rate:.1f}%)")
        
        return scores
    
    def rank_contacts_by_score(self, contacts: List[Contact], 
                              score_type: str = 'overall') -> List[Tuple[Contact, float]]:
        """
        Rank contacts by specified score type with enhanced options
        """
        scored_contacts = []
        
        for contact in contacts:
            if not hasattr(contact, 'contact_score') or not contact.contact_score:
                # Calculate score if not available
                contact.contact_score = asyncio.run(self.calculate_comprehensive_score(contact))
            
            score = contact.contact_score
            
            if score_type == 'overall':
                score_value = score.overall_score
            elif score_type == 'importance':
                score_value = score.importance_score
            elif score_type == 'engagement':
                score_value = score.engagement_score
            elif score_type == 'response_likelihood':
                score_value = score.response_likelihood
            elif score_type == 'deal_potential':
                score_value = score.deal_potential
            elif score_type == 'influence':
                score_value = score.influence_score
            elif score_type == 'social_influence':
                score_value = score.scoring_factors.get('social_influence', 0.0)
            elif score_type == 'relationship_strength':
                score_value = score.relationship_strength
            else:
                score_value = score.overall_score
            
            scored_contacts.append((contact, score_value))
        
        # Sort by score descending
        scored_contacts.sort(key=lambda x: x[1], reverse=True)
        
        return scored_contacts
    
    def get_top_contacts(self, contacts: List[Contact], 
                        count: int = 10, 
                        score_type: str = 'overall') -> List[Contact]:
        """Get top N contacts by specified score with enhanced filtering"""
        ranked_contacts = self.rank_contacts_by_score(contacts, score_type)
        return [contact for contact, score in ranked_contacts[:count]]
    
    def generate_enhanced_scoring_insights(self, contacts: List[Contact]) -> Dict[str, Any]:
        """Generate comprehensive insights about contact scoring patterns"""
        if not contacts:
            return {}
        
        # Calculate scores for all contacts
        scores = [contact.contact_score if hasattr(contact, 'contact_score') and contact.contact_score 
                 else asyncio.run(self.calculate_comprehensive_score(contact)) for contact in contacts]
        
        # Overall statistics
        overall_scores = [score.overall_score for score in scores]
        avg_score = sum(overall_scores) / len(overall_scores)
        
        # Score distribution
        high_value = sum(1 for score in overall_scores if score >= 0.8)
        medium_value = sum(1 for score in overall_scores if 0.5 <= score < 0.8)
        low_value = sum(1 for score in overall_scores if score < 0.5)
        
        # Social media coverage
        with_linkedin = sum(1 for contact in contacts if contact.get_social_profile('linkedin'))
        with_twitter = sum(1 for contact in contacts if contact.get_social_profile('twitter'))
        with_github = sum(1 for contact in contacts if contact.get_social_profile('github'))
        
        # AI analysis coverage
        ai_sentiment_available = sum(1 for score in scores if score.scoring_factors.get('ai_sentiment_available', False))
        enrichment_coverage = sum(1 for contact in contacts if contact.data_sources)
        
        # Industry distribution
        industry_distribution = defaultdict(int)
        for contact in contacts:
            industry = contact.industry or self._get_enriched_industry(contact) or 'Unknown'
            industry_distribution[industry] += 1
        
        # Company analysis
        company_scores = defaultdict(list)
        for contact, score in zip(contacts, scores):
            if contact.company:
                company_scores[contact.company].append(score.overall_score)
        
        top_companies = sorted(
            [(company, sum(scores)/len(scores), len(scores)) 
             for company, scores in company_scores.items()],
            key=lambda x: (x[1], x[2]), reverse=True
        )[:10]
        
        # Response rate analysis
        response_rates = [score.response_rate for score in scores if score.response_rate > 0]
        avg_response_rate = sum(response_rates) / len(response_rates) if response_rates else 0
        
        # Deal potential analysis
        deal_potentials = [score.deal_potential for score in scores]
        avg_deal_potential = sum(deal_potentials) / len(deal_potentials)
        high_deal_potential = sum(1 for dp in deal_potentials if dp >= 0.7)
        
        return {
            'total_contacts': len(contacts),
            'average_score': avg_score,
            'score_distribution': {
                'high_value': high_value,
                'medium_value': medium_value,
                'low_value': low_value
            },
            'social_media_coverage': {
                'linkedin': with_linkedin,
                'twitter': with_twitter,
                'github': with_github,
                'total_with_social': len([c for c in contacts if c.social_profiles])
            },
            'ai_analysis_coverage': {
                'sentiment_analysis': ai_sentiment_available,
                'enrichment_coverage': enrichment_coverage,
                'ai_engines_available': {
                    'huggingface': self.nlp_engine is not None,
                    'openai': self.openai_analyzer is not None
                }
            },
            'industry_distribution': dict(industry_distribution),
            'top_companies': top_companies,
            'response_metrics': {
                'average_response_rate': avg_response_rate,
                'contacts_with_responses': len([c for c in contacts if c.received_from > 0])
            },
            'deal_potential_analysis': {
                'average_deal_potential': avg_deal_potential,
                'high_potential_contacts': high_deal_potential,
                'percentage_high_potential': (high_deal_potential / len(contacts)) * 100
            },
            'enrichment_sources': {
                'clearbit_available': self.clearbit_source is not None,
                'hunter_available': self.hunter_source is not None,
                'pdl_available': self.pdl_source is not None
            },
            'scoring_weights': {
                'interaction_frequency': self.weights.interaction_frequency,
                'response_rate': self.weights.response_rate,
                'recency': self.weights.recency,
                'sentiment': self.weights.sentiment,
                'company_importance': self.weights.company_importance,
                'title_seniority': self.weights.title_seniority,
                'social_influence': self.weights.social_influence,
                'network_quality': self.weights.network_quality,
                'content_engagement': self.weights.content_engagement,
                'meeting_engagement': self.weights.meeting_engagement
            }
        }
    
    def update_scoring_weights(self, new_weights: Dict[str, float]):
        """Update scoring weights and validate they sum to ~1.0"""
        total_weight = sum(new_weights.values())
        if abs(total_weight - 1.0) > 0.1:
            self.logger.warning(f"Scoring weights sum to {total_weight:.2f}, not 1.0. Normalizing...")
            # Normalize weights
            new_weights = {k: v / total_weight for k, v in new_weights.items()}
        
        for weight_name, value in new_weights.items():
            if hasattr(self.weights, weight_name):
                setattr(self.weights, weight_name, value)
        
        self.logger.info(f"Updated scoring weights: {new_weights}")
    
    def get_scoring_explanation(self, contact: Contact) -> Dict[str, Any]:
        """Get detailed explanation of how a contact was scored"""
        if not hasattr(contact, 'contact_score') or not contact.contact_score:
            contact.contact_score = asyncio.run(self.calculate_comprehensive_score(contact))
        
        score = contact.contact_score
        
        return {
            'contact_email': contact.email,
            'contact_name': contact.name,
            'overall_score': score.overall_score,
            'component_scores': {
                'interaction_frequency': score.scoring_factors.get('interaction_frequency', 0),
                'response_rate': score.scoring_factors.get('response_rate', 0),
                'recency': score.scoring_factors.get('recency', 0),
                'sentiment': score.scoring_factors.get('sentiment', 0),
                'company_importance': score.scoring_factors.get('company_importance', 0),
                'title_seniority': score.scoring_factors.get('title_seniority', 0),
                'social_influence': score.scoring_factors.get('social_influence', 0),
                'network_quality': score.scoring_factors.get('network_quality', 0),
                'content_engagement': score.scoring_factors.get('content_engagement', 0),
                'meeting_engagement': score.scoring_factors.get('meeting_engagement', 0)
            },
            'scoring_weights': {
                'interaction_frequency': self.weights.interaction_frequency,
                'response_rate': self.weights.response_rate,
                'recency': self.weights.recency,
                'sentiment': self.weights.sentiment,
                'company_importance': self.weights.company_importance,
                'title_seniority': self.weights.title_seniority,
                'social_influence': self.weights.social_influence,
                'network_quality': self.weights.network_quality,
                'content_engagement': self.weights.content_engagement,
                'meeting_engagement': self.weights.meeting_engagement
            },
            'key_insights': [
                f"Total interactions: {contact.frequency}",
                f"Last contact: {(datetime.now() - contact.last_seen).days} days ago",
                f"Response rate: {score.response_rate:.1%}",
                f"Company: {contact.company or 'Unknown'}",
                f"Job title: {contact.job_title or 'Unknown'}",
                f"Social profiles: {len(contact.social_profiles)} found",
                f"Data sources: {len(contact.data_sources)} enrichment sources",
                f"LinkedIn connections: {score.scoring_factors.get('linkedin_connections', 'Unknown')}",
                f"AI sentiment available: {'Yes' if score.scoring_factors.get('ai_sentiment_available') else 'No'}",
                f"Deal potential: {score.deal_potential:.1%}",
                f"Influence score: {score.influence_score:.1%}"
            ],
            'recommendations': self._get_scoring_recommendations(contact, score)
        }
    
    def _get_scoring_recommendations(self, contact: Contact, score: ContactScore) -> List[str]:
        """Get recommendations for improving contact score"""
        recommendations = []
        
        # Low interaction frequency
        if score.scoring_factors.get('interaction_frequency', 0) < 0.3:
            recommendations.append("Increase interaction frequency to build stronger relationship")
        
        # Poor response rate
        if score.response_rate < 0.4:
            recommendations.append("Focus on more engaging communication to improve response rate")
        
        # No recent contact
        days_since_last = score.scoring_factors.get('days_since_last_contact', 0)
        if days_since_last > 90:
            recommendations.append("Re-engage with recent follow-up to improve recency score")
        
        # No meetings
        if not score.scoring_factors.get('has_meetings', False):
            recommendations.append("Schedule a meeting or call to increase engagement score")
        
        # No social profiles
        if len(contact.social_profiles) == 0:
            recommendations.append("Find and connect on LinkedIn to improve social influence score")
        
        # Low enrichment
        if len(contact.data_sources) < 2:
            recommendations.append("Enrich contact data with additional API sources")
        
        # High potential but low engagement
        if score.deal_potential > 0.7 and score.engagement_score < 0.5:
            recommendations.append("This is a high-potential contact - prioritize deeper engagement")
        
        return recommendations


# Factory function for easy initialization
def create_enhanced_contact_scorer() -> EnhancedContactScoringEngine:
    """Create and return an enhanced contact scoring engine"""
    return EnhancedContactScoringEngine()