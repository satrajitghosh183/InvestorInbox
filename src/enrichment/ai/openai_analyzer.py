"""
OpenAI-powered Email Analysis Engine
Uses GPT-4 for intelligent email signature parsing and relationship analysis
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import asyncio
import json
import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

try:
    import openai
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from core.models import Contact, Interaction, InteractionType, SentimentType, EmotionType
from core.exceptions import EnrichmentError, RateLimitError, AuthenticationError
from config.config_manager import get_config_manager

class OpenAIEmailAnalyzer:
    """
    OpenAI-powered email analysis for intelligent contact enrichment
    Provides:
    - Email signature parsing
    - Company extraction
    - Job title inference  
    - Relationship mapping
    - Communication pattern analysis
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config_manager = get_config_manager()
        self.ai_config = self.config_manager.get_ai_config('openai')
        
        if not OPENAI_AVAILABLE:
            self.logger.warning("OpenAI library not available - AI analysis disabled")
            self.enabled = False
            return
        
        if not self.ai_config or not self.ai_config.api_key:
            self.logger.warning("OpenAI not configured - AI analysis disabled")
            self.enabled = False
            return
        
        # Initialize OpenAI client
        self.client = AsyncOpenAI(api_key=self.ai_config.api_key)
        self.model = self.ai_config.model
        self.max_tokens = self.ai_config.max_tokens
        self.temperature = self.ai_config.temperature
        self.cost_per_1k_tokens = self.ai_config.cost_per_1k_tokens
        
        self.enabled = self.ai_config.enabled
        
        # Analysis prompts
        self._load_analysis_prompts()
        
        # Rate limiting
        self.requests_today = 0
        self.tokens_used_today = 0
        self.last_reset = datetime.now().date()
    
    def _load_analysis_prompts(self):
        """Load analysis prompts for different tasks"""
        self.prompts = {
            'signature_analysis': """
Analyze the following email signature and extract structured information. Return a JSON object with the following fields:
- name: Full name of the person
- job_title: Their job title/position
- company: Company name
- department: Department or division
- phone: Phone number(s)
- email: Email address(es)
- website: Company website
- location: Office location/address
- social_profiles: Any social media profiles mentioned

Email signature:
{signature}

Return only valid JSON, no other text.
""",
            
            'company_extraction': """
Analyze the following email content and extract company information. Look for:
- Company names mentioned
- Industry indicators
- Business context
- Company size indicators
- Technology stack mentions

Email content:
{content}

Return a JSON object with:
- primary_company: Main company discussed
- mentioned_companies: List of other companies mentioned
- industry_indicators: Industry clues found
- business_context: Type of business discussion
- technology_mentions: Technologies or tools mentioned

Return only valid JSON, no other text.
""",
            
            'relationship_analysis': """
Analyze the email communication pattern and determine the relationship type between the sender and recipient.

Email context:
Subject: {subject}
Content preview: {content}
Sender tone: {tone}
Previous interactions: {interaction_count}

Determine:
- relationship_type: colleague, client, vendor, partner, prospect, friend, family, other
- relationship_strength: weak, moderate, strong, very_strong
- communication_style: formal, informal, friendly, professional, urgent
- business_relevance: high, medium, low, none

Return only valid JSON, no other text.
""",
            
            'job_title_inference': """
Based on the email signature, content, and communication style, infer the person's likely job title and seniority level.

Available information:
- Email signature: {signature}
- Email content style: {content_style}
- Communication authority: {authority_level}
- Company context: {company}

Provide:
- inferred_title: Most likely job title
- seniority_level: entry, mid, senior, director, vp, c_suite
- confidence: 0.0 to 1.0
- reasoning: Brief explanation

Return only valid JSON, no other text.
""",
            
            'communication_patterns': """
Analyze the communication patterns from this email interaction:

Email details:
- Subject: {subject}
- Response time: {response_time}
- Email length: {length}
- Time sent: {send_time}
- Tone indicators: {tone}

Determine:
- response_urgency: immediate, normal, delayed, very_delayed
- engagement_level: high, medium, low
- preferred_communication_time: morning, afternoon, evening, weekend
- communication_preference: brief, detailed, formal, casual
- follow_up_likelihood: high, medium, low

Return only valid JSON, no other text.
"""
        }
    
    async def analyze_email_signature(self, signature: str) -> Dict[str, Any]:
        """
        Parse email signature using GPT-4 to extract structured information
        
        Args:
            signature: Email signature text
            
        Returns:
            Dictionary with extracted information
        """
        if not self.enabled or not signature.strip():
            return {}
        
        try:
            prompt = self.prompts['signature_analysis'].format(signature=signature)
            
            response = await self._make_openai_request(prompt)
            
            # Parse JSON response
            try:
                result = json.loads(response)
                return self._clean_signature_data(result)
            except json.JSONDecodeError:
                self.logger.warning("Failed to parse signature analysis JSON response")
                return {}
                
        except Exception as e:
            self.logger.error(f"Email signature analysis failed: {e}")
            return {}
    
    async def extract_company_information(self, email_content: str, subject: str = "") -> Dict[str, Any]:
        """
        Extract company and business context from email content
        
        Args:
            email_content: Email body text
            subject: Email subject line
            
        Returns:
            Dictionary with company information
        """
        if not self.enabled:
            return {}
        
        try:
            # Combine subject and content for analysis
            full_content = f"Subject: {subject}\n\n{email_content}" if subject else email_content
            
            # Limit content length to avoid token limits
            if len(full_content) > 2000:
                full_content = full_content[:2000] + "..."
            
            prompt = self.prompts['company_extraction'].format(content=full_content)
            
            response = await self._make_openai_request(prompt)
            
            try:
                result = json.loads(response)
                return self._clean_company_data(result)
            except json.JSONDecodeError:
                self.logger.warning("Failed to parse company extraction JSON response")
                return {}
                
        except Exception as e:
            self.logger.error(f"Company extraction failed: {e}")
            return {}
    
    async def analyze_relationship_type(self, 
                                      contact: Contact, 
                                      recent_interaction: Interaction) -> Dict[str, Any]:
        """
        Determine relationship type and strength based on communication patterns
        
        Args:
            contact: Contact object with interaction history
            recent_interaction: Most recent interaction to analyze
            
        Returns:
            Dictionary with relationship analysis
        """
        if not self.enabled:
            return {}
        
        try:
            # Analyze tone from email content
            tone = self._analyze_basic_tone(recent_interaction.content_preview)
            
            prompt = self.prompts['relationship_analysis'].format(
                subject=recent_interaction.subject,
                content=recent_interaction.content_preview[:500],  # Limit length
                tone=tone,
                interaction_count=contact.frequency
            )
            
            response = await self._make_openai_request(prompt)
            
            try:
                result = json.loads(response)
                return self._clean_relationship_data(result)
            except json.JSONDecodeError:
                self.logger.warning("Failed to parse relationship analysis JSON response")
                return {}
                
        except Exception as e:
            self.logger.error(f"Relationship analysis failed: {e}")
            return {}
    
    async def infer_job_title(self, 
                            signature: str = "", 
                            email_style: str = "",
                            company: str = "") -> Dict[str, Any]:
        """
        Infer job title and seniority from available information
        
        Args:
            signature: Email signature
            email_style: Communication style indicators
            company: Company name for context
            
        Returns:
            Dictionary with job title inference
        """
        if not self.enabled:
            return {}
        
        try:
            # Analyze authority level from signature and style
            authority_level = self._assess_authority_level(signature, email_style)
            
            prompt = self.prompts['job_title_inference'].format(
                signature=signature,
                content_style=email_style,
                authority_level=authority_level,
                company=company
            )
            
            response = await self._make_openai_request(prompt)
            
            try:
                result = json.loads(response)
                return self._clean_job_title_data(result)
            except json.JSONDecodeError:
                self.logger.warning("Failed to parse job title inference JSON response")
                return {}
                
        except Exception as e:
            self.logger.error(f"Job title inference failed: {e}")
            return {}
    
    async def analyze_communication_patterns(self, 
                                           interaction: Interaction,
                                           response_time_hours: Optional[float] = None) -> Dict[str, Any]:
        """
        Analyze communication patterns for insights
        
        Args:
            interaction: Interaction to analyze
            response_time_hours: Response time if available
            
        Returns:
            Dictionary with communication pattern insights
        """
        if not self.enabled:
            return {}
        
        try:
            # Determine tone indicators
            tone = self._analyze_basic_tone(interaction.content_preview)
            
            # Format response time
            response_time_str = "unknown"
            if response_time_hours is not None:
                if response_time_hours < 1:
                    response_time_str = "under 1 hour"
                elif response_time_hours < 24:
                    response_time_str = f"{response_time_hours:.1f} hours"
                else:
                    response_time_str = f"{response_time_hours/24:.1f} days"
            
            prompt = self.prompts['communication_patterns'].format(
                subject=interaction.subject,
                response_time=response_time_str,
                length=len(interaction.content_preview),
                send_time=interaction.timestamp.strftime("%A %H:%M"),
                tone=tone
            )
            
            response = await self._make_openai_request(prompt)
            
            try:
                result = json.loads(response)
                return self._clean_communication_data(result)
            except json.JSONDecodeError:
                self.logger.warning("Failed to parse communication patterns JSON response")
                return {}
                
        except Exception as e:
            self.logger.error(f"Communication pattern analysis failed: {e}")
            return {}
    
    async def batch_analyze_contacts(self, contacts: List[Contact]) -> Dict[str, Dict[str, Any]]:
        """
        Analyze multiple contacts in batch for efficiency
        
        Args:
            contacts: List of contacts to analyze
            
        Returns:
            Dictionary mapping contact emails to analysis results
        """
        if not self.enabled:
            return {}
        
        results = {}
        
        # Process in small batches to avoid rate limits
        batch_size = 5
        for i in range(0, len(contacts), batch_size):
            batch = contacts[i:i + batch_size]
            
            # Analyze each contact in the batch
            tasks = []
            for contact in batch:
                if contact.interactions:
                    # Use most recent interaction for analysis
                    recent_interaction = max(contact.interactions, key=lambda x: x.timestamp)
                    task = self._analyze_single_contact(contact, recent_interaction)
                    tasks.append((contact.email, task))
            
            # Execute batch
            for email, task in tasks:
                try:
                    result = await task
                    results[email] = result
                except Exception as e:
                    self.logger.error(f"Batch analysis failed for {email}: {e}")
                    results[email] = {}
            
            # Rate limiting delay between batches
            await asyncio.sleep(1)
        
        return results
    
    async def _analyze_single_contact(self, contact: Contact, interaction: Interaction) -> Dict[str, Any]:
        """Analyze a single contact comprehensively"""
        analysis = {}
        
        # Extract signature if available
        signature = self._extract_signature(interaction.content_preview)
        if signature:
            sig_analysis = await self.analyze_email_signature(signature)
            analysis['signature_analysis'] = sig_analysis
        
        # Analyze relationship
        rel_analysis = await self.analyze_relationship_type(contact, interaction)
        analysis['relationship_analysis'] = rel_analysis
        
        # Communication patterns
        comm_analysis = await self.analyze_communication_patterns(interaction)
        analysis['communication_patterns'] = comm_analysis
        
        return analysis
    
    async def _make_openai_request(self, prompt: str) -> str:
        """Make request to OpenAI API with error handling"""
        try:
            # Check rate limits
            await self._check_rate_limits()
            
            # Make API request
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert email analyst. Always return valid JSON responses."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )
            
            # Update usage tracking
            self._update_usage_tracking(response.usage.total_tokens if response.usage else 100)
            
            return response