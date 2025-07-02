"""
Advanced Contact Scoring Engine
Comprehensive contact intelligence using multiple factors and AI analysis
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import math
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from core.models import Contact, ContactScore, Interaction, InteractionType, SentimentType, EmotionType, RelationshipStage
from config.config_manager import get_config_manager

@dataclass
class ScoringWeights:
    """Weights for different scoring factors"""
    interaction_frequency: float = 0.25
    response_rate: float = 0.20
    recency: float = 0.15
    sentiment: float = 0.15
    company_importance: float = 0.10
    title_seniority: float = 0.10
    meeting_engagement: float = 0.05

class ContactScoringEngine:
    """
    Advanced contact scoring engine that evaluates contacts across multiple dimensions
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config_manager = get_config_manager()
        self.scoring_config = self.config_manager.get_contact_intelligence_config().get('scoring', {})
        
        # Load scoring weights from config
        self.weights = self._load_scoring_weights()
        
        # Company importance mappings
        self.company_importance_scores = {
            # Big Tech
            'google': 0.95, 'apple': 0.95, 'microsoft': 0.95, 'amazon': 0.95, 'meta': 0.95,
            'netflix': 0.90, 'tesla': 0.90, 'nvidia': 0.90, 'salesforce': 0.85,
            
            # Major Banks & Finance
            'goldman sachs': 0.90, 'jp morgan': 0.90, 'blackrock': 0.85, 'visa': 0.85,
            
            # Consulting
            'mckinsey': 0.90, 'bain': 0.85, 'bcg': 0.85, 'deloitte': 0.80,
            
            # Other Fortune 500
            'coca cola': 0.80, 'walmart': 0.75, 'exxon': 0.75,
            
            # Startups and unicorns
            'uber': 0.80, 'airbnb': 0.80, 'stripe': 0.85, 'spacex': 0.90
        }
        
        # Job title seniority scores
        self.title_seniority_scores = {
            # C-Suite
            'ceo': 1.0, 'cto': 0.95, 'cfo': 0.95, 'coo': 0.90, 'chief': 0.90,
            'founder': 1.0, 'co-founder': 0.95, 'president': 0.95,
            
            # VP Level
            'vp': 0.85, 'vice president': 0.85, 'svp': 0.90, 'evp': 0.90,
            
            # Director Level
            'director': 0.75, 'head of': 0.75, 'principal': 0.70,
            
            # Manager Level
            'manager': 0.60, 'senior manager': 0.65, 'lead': 0.65,
            
            # Senior Individual Contributors
            'senior': 0.55, 'sr': 0.55, 'staff': 0.60, 'principal engineer': 0.70,
            
            # Regular Individual Contributors
            'engineer': 0.45, 'analyst': 0.45, 'specialist': 0.45, 'coordinator': 0.40
        }
    
    def _load_scoring_weights(self) -> ScoringWeights:
        """Load scoring weights from configuration"""
        weights_config = self.scoring_config.get('weights', {})
        
        return ScoringWeights(
            interaction_frequency=weights_config.get('frequency', 0.25),
            response_rate=weights_config.get('response_rate', 0.20),
            recency=weights_config.get('recency', 0.15),
            sentiment=weights_config.get('sentiment', 0.15),
            company_importance=weights_config.get('company', 0.10),
            title_seniority=weights_config.get('title_seniority', 0.10),
            meeting_engagement=weights_config.get('meetings', 0.05)
        )
    
    def calculate_comprehensive_score(self, contact: Contact) -> ContactScore:
        """
        Calculate comprehensive contact score across all dimensions
        
        Args:
            contact: Contact to score
            
        Returns:
            ContactScore with detailed scoring breakdown
        """
        try:
            score = ContactScore()
            
            # Calculate individual scoring components
            interaction_score = self._calculate_interaction_score(contact)
            response_score = self._calculate_response_rate_score(contact)
            recency_score = self._calculate_recency_score(contact)
            sentiment_score = self._calculate_sentiment_score(contact)
            company_score = self._calculate_company_importance_score(contact)
            title_score = self._calculate_title_seniority_score(contact)
            engagement_score = self._calculate_engagement_score(contact)
            
            # Calculate weighted overall score
            score.overall_score = (
                interaction_score * self.weights.interaction_frequency +
                response_score * self.weights.response_rate +
                recency_score * self.weights.recency +
                sentiment_score * self.weights.sentiment +
                company_score * self.weights.company_importance +
                title_score * self.weights.title_seniority +
                engagement_score * self.weights.meeting_engagement
            )
            
            # Set individual component scores
            score.relationship_strength = contact.calculate_relationship_strength()
            score.engagement_score = engagement_score
            score.importance_score = max(company_score, title_score)
            score.response_likelihood = response_score
            
            # Calculate additional metrics
            score.influence_score = self._calculate_influence_score(contact)
            score.deal_potential = self._calculate_deal_potential(contact)
            
            # Set scoring factors for transparency
            score.scoring_factors = {
                'interaction_frequency': interaction_score,
                'response_rate': response_score,
                'recency': recency_score,
                'sentiment': sentiment_score,
                'company_importance': company_score,
                'title_seniority': title_score,
                'engagement': engagement_score,
                'total_interactions': contact.frequency,
                'days_since_last_contact': (datetime.now() - contact.last_seen).days,
                'has_meetings': contact.meeting_count > 0,
                'bidirectional_communication': contact.sent_to > 0 and contact.received_from > 0
            }
            
            # Set communication patterns
            comm_patterns = self._analyze_communication_patterns(contact)
            score.average_sentiment = comm_patterns.get('avg_sentiment', 0.0)
            score.sentiment_trend = comm_patterns.get('sentiment_trend', 'neutral')
            score.response_rate = response_score
            score.average_response_time = comm_patterns.get('avg_response_time', 0.0)
            score.best_contact_time = comm_patterns.get('best_contact_time', '')
            score.preferred_communication = comm_patterns.get('preferred_communication', 'email')
            
            # Set AI analysis results if available
            if contact.ai_analysis and contact.ai_analysis.sentiment_history:
                score.dominant_emotion = self._get_dominant_emotion(contact)
            
            score.last_calculated = datetime.now()
            
            return score
            
        except Exception as e:
            self.logger.error(f"Error calculating contact score for {contact.email}: {e}")
            return ContactScore()
    
    def _calculate_interaction_score(self, contact: Contact) -> float:
        """Calculate score based on interaction frequency"""
        if contact.frequency == 0:
            return 0.0
        
        # Use logarithmic scaling to prevent outliers from dominating
        # Score approaches 1.0 as interactions increase
        base_score = math.log(contact.frequency + 1) / math.log(26)  # Log base chosen for nice scaling
        
        # Cap at 1.0
        return min(base_score, 1.0)
    
    def _calculate_response_rate_score(self, contact: Contact) -> float:
        """Calculate score based on email response patterns"""
        if contact.sent_to == 0:
            return 0.5  # Neutral score if no outbound emails
        
        # Basic response rate
        response_rate = contact.received_from / contact.sent_to
        
        # Bonus for bidirectional communication
        if contact.received_from > 0 and contact.sent_to > 0:
            balance_bonus = min(contact.sent_to, contact.received_from) / max(contact.sent_to, contact.received_from)
            response_rate = min(response_rate + (balance_bonus * 0.2), 1.0)
        
        return min(response_rate, 1.0)
    
    def _calculate_recency_score(self, contact: Contact) -> float:
        """Calculate score based on recency of last interaction"""
        days_since_last = (datetime.now() - contact.last_seen).days
        
        # Exponential decay function
        if days_since_last <= 1:
            return 1.0
        elif days_since_last <= 7:
            return 0.9
        elif days_since_last <= 30:
            return 0.7
        elif days_since_last <= 90:
            return 0.5
        elif days_since_last <= 180:
            return 0.3
        else:
            return 0.1
    
    def _calculate_sentiment_score(self, contact: Contact) -> float:
        """Calculate score based on sentiment analysis of interactions"""
        if not contact.interactions:
            return 0.5  # Neutral score
        
        sentiment_scores = []
        
        for interaction in contact.interactions:
            if interaction.sentiment == SentimentType.POSITIVE:
                sentiment_scores.append(interaction.sentiment_score)
            elif interaction.sentiment == SentimentType.NEGATIVE:
                sentiment_scores.append(-interaction.sentiment_score)
            else:
                sentiment_scores.append(0.0)
        
        if not sentiment_scores:
            return 0.5
        
        # Calculate average sentiment with recent bias
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
    
    def _calculate_company_importance_score(self, contact: Contact) -> float:
        """Calculate score based on company importance"""
        if not contact.company:
            return 0.3  # Default score for unknown company
        
        company_lower = contact.company.lower()
        
        # Check for direct matches
        for company, score in self.company_importance_scores.items():
            if company in company_lower:
                return score
        
        # Check for partial matches or indicators
        if any(indicator in company_lower for indicator in ['google', 'microsoft', 'amazon', 'apple']):
            return 0.9
        elif any(indicator in company_lower for indicator in ['bank', 'capital', 'ventures']):
            return 0.7
        elif any(indicator in company_lower for indicator in ['consulting', 'advisory']):
            return 0.75
        elif any(indicator in company_lower for indicator in ['university', 'edu']):
            return 0.6
        elif any(indicator in company_lower for indicator in ['startup', 'inc', 'llc']):
            return 0.5
        else:
            return 0.4  # Default for other companies
    
    def _calculate_title_seniority_score(self, contact: Contact) -> float:
        """Calculate score based on job title seniority"""
        if not contact.job_title:
            return 0.4  # Default score for unknown title
        
        title_lower = contact.job_title.lower()
        
        # Check for direct matches
        for title_keyword, score in self.title_seniority_scores.items():
            if title_keyword in title_lower:
                return score
        
        # Default scoring based on common patterns
        if any(exec in title_lower for exec in ['executive', 'owner', 'partner']):
            return 0.8
        elif any(mgr in title_lower for mgr in ['management', 'supervisor']):
            return 0.6
        elif any(tech in title_lower for tech in ['developer', 'engineer', 'architect']):
            return 0.5
        else:
            return 0.4
    
    def _calculate_engagement_score(self, contact: Contact) -> float:
        """Calculate score based on meeting and call engagement"""
        total_meetings = contact.meeting_count + contact.call_count
        
        if total_meetings == 0:
            return 0.0
        
        # Score based on meeting frequency relative to email interactions
        if contact.frequency > 0:
            meeting_ratio = total_meetings / contact.frequency
            # Normalize and cap at 1.0
            return min(meeting_ratio * 2.0, 1.0)
        else:
            # If no email interactions but has meetings, give decent score
            return min(total_meetings / 5.0, 1.0)
    
    def _calculate_influence_score(self, contact: Contact) -> float:
        """Calculate influence score based on multiple factors"""
        factors = []
        
        # Company influence
        company_score = self._calculate_company_importance_score(contact)
        factors.append(company_score * 0.4)
        
        # Title influence
        title_score = self._calculate_title_seniority_score(contact)
        factors.append(title_score * 0.3)
        
        # Network influence (based on social profiles)
        network_score = 0.0
        if contact.social_profiles:
            # LinkedIn presence
            linkedin_profile = contact.get_social_profile('linkedin')
            if linkedin_profile:
                network_score += 0.3
            
            # Twitter presence
            twitter_profile = contact.get_social_profile('twitter')
            if twitter_profile and hasattr(twitter_profile, 'followers'):
                if twitter_profile.followers > 10000:
                    network_score += 0.3
                elif twitter_profile.followers > 1000:
                    network_score += 0.2
                else:
                    network_score += 0.1
            
            # GitHub presence (for tech roles)
            github_profile = contact.get_social_profile('github')
            if github_profile:
                network_score += 0.2
        
        factors.append(network_score * 0.2)
        
        # Communication influence (how quickly they respond, meeting frequency)
        comm_influence = 0.0
        if contact.interactions:
            # Quick responders get higher influence scores
            recent_interactions = sorted(contact.interactions, key=lambda x: x.timestamp, reverse=True)[:5]
            response_times = []
            
            for i in range(len(recent_interactions) - 1):
                current = recent_interactions[i]
                previous = recent_interactions[i + 1]
                
                if (current.direction == "inbound" and previous.direction == "outbound" and
                    current.timestamp > previous.timestamp):
                    response_time = (current.timestamp - previous.timestamp).total_seconds() / 3600
                    response_times.append(response_time)
            
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
                if avg_response_time < 2:  # Less than 2 hours
                    comm_influence = 0.8
                elif avg_response_time < 24:  # Less than 1 day
                    comm_influence = 0.6
                elif avg_response_time < 72:  # Less than 3 days
                    comm_influence = 0.4
                else:
                    comm_influence = 0.2
        
        factors.append(comm_influence * 0.1)
        
        return sum(factors)
    
    def _calculate_deal_potential(self, contact: Contact) -> float:
        """Calculate potential for business deals"""
        potential_factors = []
        
        # Industry factor
        high_value_industries = [
            'technology', 'finance', 'consulting', 'healthcare', 'energy'
        ]
        
        if contact.industry:
            industry_lower = contact.industry.lower()
            if any(ind in industry_lower for ind in high_value_industries):
                potential_factors.append(0.8)
            else:
                potential_factors.append(0.5)
        else:
            potential_factors.append(0.5)
        
        # Company size factor (inferred from domain patterns)
        company_size_score = 0.5
        if contact.company:
            company_lower = contact.company.lower()
            # Fortune 500 companies
            if any(big_co in company_lower for big_co in ['microsoft', 'google', 'amazon', 'apple']):
                company_size_score = 0.9
            # Mid-size tech companies
            elif any(tech_co in company_lower for tech_co in ['startup', 'solutions', 'technologies']):
                company_size_score = 0.7
            # Small businesses
            elif any(small_co in company_lower for small_co in ['consulting', 'services', 'group']):
                company_size_score = 0.6
        
        potential_factors.append(company_size_score)
        
        # Decision maker factor
        decision_maker_score = self._calculate_title_seniority_score(contact)
        potential_factors.append(decision_maker_score)
        
        # Engagement history factor
        if contact.frequency > 10:
            engagement_factor = 0.8
        elif contact.frequency > 5:
            engagement_factor = 0.6
        elif contact.frequency > 1:
            engagement_factor = 0.4
        else:
            engagement_factor = 0.2
        
        potential_factors.append(engagement_factor)
        
        return sum(potential_factors) / len(potential_factors)
    
    def _analyze_communication_patterns(self, contact: Contact) -> Dict[str, Any]:
        """Analyze communication patterns for insights"""
        patterns = {
            'avg_sentiment': 0.0,
            'sentiment_trend': 'neutral',
            'avg_response_time': 0.0,
            'best_contact_time': '',
            'preferred_communication': 'email'
        }
        
        if not contact.interactions:
            return patterns
        
        # Sentiment analysis
        sentiment_scores = []
        for interaction in contact.interactions:
            if interaction.sentiment != SentimentType.NEUTRAL:
                score = interaction.sentiment_score if interaction.sentiment == SentimentType.POSITIVE else -interaction.sentiment_score
                sentiment_scores.append(score)
        
        if sentiment_scores:
            patterns['avg_sentiment'] = sum(sentiment_scores) / len(sentiment_scores)
            
            # Sentiment trend (compare recent vs older interactions)
            if len(sentiment_scores) >= 4:
                recent_avg = sum(sentiment_scores[-2:]) / 2
                older_avg = sum(sentiment_scores[:-2]) / len(sentiment_scores[:-2])
                
                if recent_avg > older_avg + 0.1:
                    patterns['sentiment_trend'] = 'improving'
                elif recent_avg < older_avg - 0.1:
                    patterns['sentiment_trend'] = 'declining'
                else:
                    patterns['sentiment_trend'] = 'stable'
        
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
            hour_counts = {}
            for hour in interaction_hours:
                hour_counts[hour] = hour_counts.get(hour, 0) + 1
            
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
    
    def _get_dominant_emotion(self, contact: Contact) -> EmotionType:
        """Get dominant emotion from AI analysis"""
        if not contact.ai_analysis or not contact.ai_analysis.emotion_patterns:
            return EmotionType.NEUTRAL
        
        emotion_patterns = contact.ai_analysis.emotion_patterns
        
        # Find emotion with highest average score
        max_emotion = EmotionType.NEUTRAL
        max_score = 0.0
        
        for emotion, score in emotion_patterns.items():
            if isinstance(emotion, EmotionType) and score > max_score:
                max_emotion = emotion
                max_score = score
        
        return max_emotion
    
    def score_contacts_batch(self, contacts: List[Contact]) -> Dict[str, ContactScore]:
        """Score multiple contacts efficiently"""
        scores = {}
        
        for contact in contacts:
            try:
                scores[contact.email] = self.calculate_comprehensive_score(contact)
            except Exception as e:
                self.logger.error(f"Failed to score contact {contact.email}: {e}")
                scores[contact.email] = ContactScore()
        
        return scores
    
    def rank_contacts_by_score(self, contacts: List[Contact], 
                              score_type: str = 'overall') -> List[Tuple[Contact, float]]:
        """
        Rank contacts by specified score type
        
        Args:
            contacts: List of contacts to rank
            score_type: Type of score to use for ranking
                       ('overall', 'importance', 'engagement', 'response_likelihood')
        
        Returns:
            List of (contact, score) tuples sorted by score descending
        """
        scored_contacts = []
        
        for contact in contacts:
            score = self.calculate_comprehensive_score(contact)
            
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
            else:
                score_value = score.overall_score
            
            scored_contacts.append((contact, score_value))
        
        # Sort by score descending
        scored_contacts.sort(key=lambda x: x[1], reverse=True)
        
        return scored_contacts
    
    def get_top_contacts(self, contacts: List[Contact], 
                        count: int = 10, 
                        score_type: str = 'overall') -> List[Contact]:
        """Get top N contacts by specified score"""
        ranked_contacts = self.rank_contacts_by_score(contacts, score_type)
        return [contact for contact, score in ranked_contacts[:count]]
    
    def generate_scoring_insights(self, contacts: List[Contact]) -> Dict[str, Any]:
        """Generate insights about contact scoring patterns"""
        if not contacts:
            return {}
        
        scores = [self.calculate_comprehensive_score(contact) for contact in contacts]
        
        # Calculate statistics
        overall_scores = [score.overall_score for score in scores]
        avg_score = sum(overall_scores) / len(overall_scores)
        
        # Score distribution
        high_value = sum(1 for score in overall_scores if score >= 0.8)
        medium_value = sum(1 for score in overall_scores if 0.5 <= score < 0.8)
        low_value = sum(1 for score in overall_scores if score < 0.5)
        
        # Company distribution
        company_scores = {}
        for contact, score in zip(contacts, scores):
            if contact.company:
                if contact.company not in company_scores:
                    company_scores[contact.company] = []
                company_scores[contact.company].append(score.overall_score)
        
        top_companies = sorted(
            [(company, sum(scores)/len(scores)) for company, scores in company_scores.items()],
            key=lambda x: x[1], reverse=True
        )[:10]
        
        # Response rate patterns
        response_rates = [score.response_rate for score in scores if score.response_rate > 0]
        avg_response_rate = sum(response_rates) / len(response_rates) if response_rates else 0
        
        return {
            'total_contacts': len(contacts),
            'average_score': avg_score,
            'score_distribution': {
                'high_value': high_value,
                'medium_value': medium_value,
                'low_value': low_value
            },
            'top_companies': top_companies,
            'average_response_rate': avg_response_rate,
            'scoring_weights': {
                'interaction_frequency': self.weights.interaction_frequency,
                'response_rate': self.weights.response_rate,
                'recency': self.weights.recency,
                'sentiment': self.weights.sentiment,
                'company_importance': self.weights.company_importance,
                'title_seniority': self.weights.title_seniority,
                'meeting_engagement': self.weights.meeting_engagement
            }
        }
    
    def update_scoring_weights(self, new_weights: Dict[str, float]):
        """Update scoring weights"""
        for weight_name, value in new_weights.items():
            if hasattr(self.weights, weight_name):
                setattr(self.weights, weight_name, value)
        
        self.logger.info(f"Updated scoring weights: {new_weights}")
    
    def get_scoring_explanation(self, contact: Contact) -> Dict[str, Any]:
        """Get detailed explanation of how a contact was scored"""
        score = self.calculate_comprehensive_score(contact)
        
        return {
            'contact_email': contact.email,
            'overall_score': score.overall_score,
            'component_scores': score.scoring_factors,
            'scoring_weights': {
                'interaction_frequency': self.weights.interaction_frequency,
                'response_rate': self.weights.response_rate,
                'recency': self.weights.recency,
                'sentiment': self.weights.sentiment,
                'company_importance': self.weights.company_importance,
                'title_seniority': self.weights.title_seniority,
                'meeting_engagement': self.weights.meeting_engagement
            },
            'key_insights': [
                f"Has {contact.frequency} total interactions",
                f"Last contact {(datetime.now() - contact.last_seen).days} days ago",
                f"Response rate: {score.response_rate:.1%}",
                f"Company importance: {score.scoring_factors.get('company_importance', 0):.2f}",
                f"Title seniority: {score.scoring_factors.get('title_seniority', 0):.2f}"
            ]
        }