"""
Hugging Face NLP Analysis Engine
Advanced NLP capabilities using pre-trained transformers for:
- Sentiment analysis
- Emotion detection  
- Email classification
- Named entity recognition
- Text similarity
- Data validation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

try:
    from transformers import (
        AutoTokenizer, AutoModelForSequenceClassification,
        AutoModelForTokenClassification, pipeline,
        DistilBertTokenizer, DistilBertForSequenceClassification
    )
    from sentence_transformers import SentenceTransformer
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

from core.models import Contact, Interaction, SentimentType, EmotionType
from core.exceptions import EnrichmentError
from config.config_manager import get_config_manager

class HuggingFaceNLPEngine:
    """
    Hugging Face NLP engine for advanced contact intelligence
    Provides offline NLP capabilities using pre-trained models
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config_manager = get_config_manager()
        self.hf_config = self.config_manager.get_huggingface_config()
        
        if not TRANSFORMERS_AVAILABLE:
            self.logger.warning("Transformers library not available - NLP analysis disabled")
            self.enabled = False
            return
        
        self.enabled = self.hf_config.get('enabled', True)
        self.use_local_models = self.hf_config.get('use_local_models', True)
        self.cache_dir = Path(self.hf_config.get('cache_dir', 'data/models'))
        self.device = self.hf_config.get('device', 'cpu')
        
        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Model configurations
        self.model_configs = {
            'sentiment': {
                'model_name': 'distilbert-base-uncased-finetuned-sst-2-english',
                'enabled': self.hf_config.get('sentiment_analysis', {}).get('enabled', True),
                'confidence_threshold': self.hf_config.get('sentiment_analysis', {}).get('confidence_threshold', 0.7)
            },
            'emotion': {
                'model_name': 'j-hartmann/emotion-english-distilroberta-base',
                'enabled': self.hf_config.get('emotion_detection', {}).get('enabled', True),
                'confidence_threshold': self.hf_config.get('emotion_detection', {}).get('confidence_threshold', 0.6)
            },
            'classification': {
                'model_name': 'microsoft/DialoGPT-medium',
                'enabled': self.hf_config.get('email_classification', {}).get('enabled', True),
                'categories': self.hf_config.get('email_classification', {}).get('categories', [
                    'business_proposal', 'follow_up', 'complaint', 'inquiry', 'networking'
                ])
            },
            'ner': {
                'model_name': 'dbmdz/bert-large-cased-finetuned-conll03-english',
                'enabled': self.hf_config.get('named_entity_recognition', {}).get('enabled', True),
                'entities': self.hf_config.get('named_entity_recognition', {}).get('entities', 
                                            ['PERSON', 'ORG', 'GPE', 'MONEY', 'DATE'])
            },
            'similarity': {
                'model_name': 'sentence-transformers/all-MiniLM-L6-v2',
                'enabled': self.hf_config.get('text_similarity', {}).get('enabled', True),
                'threshold': self.hf_config.get('text_similarity', {}).get('similarity_threshold', 0.8)
            },
            'zero_shot': {
                'model_name': 'facebook/bart-large-mnli',
                'enabled': self.hf_config.get('contact_categorization', {}).get('enabled', True),
                'categories': self.hf_config.get('contact_categorization', {}).get('categories', [
                    'prospect', 'customer', 'vendor', 'partner', 'competitor', 'colleague'
                ])
            }
        }
        
        # Loaded models
        self.models = {}
        self.pipelines = {}
        
        # Initialize models
        if self.enabled:
            asyncio.create_task(self._initialize_models())
    
    async def _initialize_models(self):
        """Initialize NLP models asynchronously"""
        try:
            self.logger.info("Initializing Hugging Face NLP models...")
            
            # Initialize sentiment analysis
            if self.model_configs['sentiment']['enabled']:
                await self._load_sentiment_model()
            
            # Initialize emotion detection
            if self.model_configs['emotion']['enabled']:
                await self._load_emotion_model()
            
            # Initialize NER
            if self.model_configs['ner']['enabled']:
                await self._load_ner_model()
            
            # Initialize text similarity
            if self.model_configs['similarity']['enabled']:
                await self._load_similarity_model()
            
            # Initialize zero-shot classification
            if self.model_configs['zero_shot']['enabled']:
                await self._load_zero_shot_model()
            
            self.logger.info("NLP models initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize NLP models: {e}")
            self.enabled = False
    
    async def _load_sentiment_model(self):
        """Load sentiment analysis model"""
        try:
            model_name = self.model_configs['sentiment']['model_name']
            
            self.pipelines['sentiment'] = pipeline(
                "sentiment-analysis",
                model=model_name,
                tokenizer=model_name,
                device=0 if self.device == 'cuda' and torch.cuda.is_available() else -1,
                # cache_dir=self.cache_dir
            )
            
            self.logger.info("Sentiment analysis model loaded")
            
        except Exception as e:
            self.logger.error(f"Failed to load sentiment model: {e}")
            self.model_configs['sentiment']['enabled'] = False
    
    async def _load_emotion_model(self):
        """Load emotion detection model"""
        try:
            model_name = self.model_configs['emotion']['model_name']
            
            self.pipelines['emotion'] = pipeline(
                "text-classification",
                model=model_name,
                tokenizer=model_name,
                device=0 if self.device == 'cuda' and torch.cuda.is_available() else -1,
                # cache_dir=self.cache_dir
            )
            
            self.logger.info("Emotion detection model loaded")
            
        except Exception as e:
            self.logger.error(f"Failed to load emotion model: {e}")
            self.model_configs['emotion']['enabled'] = False
    
    async def _load_ner_model(self):
        """Load Named Entity Recognition model"""
        try:
            model_name = self.model_configs['ner']['model_name']
            
            self.pipelines['ner'] = pipeline(
                "ner",
                model=model_name,
                tokenizer=model_name,
                device=0 if self.device == 'cuda' and torch.cuda.is_available() else -1,
                # cache_dir=self.cache_dir,
                aggregation_strategy="simple"
            )
            
            self.logger.info("NER model loaded")
            
        except Exception as e:
            self.logger.error(f"Failed to load NER model: {e}")
            self.model_configs['ner']['enabled'] = False
    
    async def _load_similarity_model(self):
        """Load text similarity model"""
        try:
            model_name = self.model_configs['similarity']['model_name']
            
            self.models['similarity'] = SentenceTransformer(
                model_name,
                cache_folder=self.cache_dir
            )
            
            # Move to appropriate device
            if self.device == 'cuda' and torch.cuda.is_available():
                self.models['similarity'] = self.models['similarity'].to('cuda')
            
            self.logger.info("Text similarity model loaded")
            
        except Exception as e:
            self.logger.error(f"Failed to load similarity model: {e}")
            self.model_configs['similarity']['enabled'] = False
    
    async def _load_zero_shot_model(self):
        """Load zero-shot classification model"""
        try:
            model_name = self.model_configs['zero_shot']['model_name']
            
            self.pipelines['zero_shot'] = pipeline(
                "zero-shot-classification",
                model=model_name,
                device=0 if self.device == 'cuda' and torch.cuda.is_available() else -1,
                # cache_dir=self.cache_dir
            )
            
            self.logger.info("Zero-shot classification model loaded")
            
        except Exception as e:
            self.logger.error(f"Failed to load zero-shot model: {e}")
            self.model_configs['zero_shot']['enabled'] = False
    
    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of text using DistilBERT
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with sentiment analysis results
        """
        if not self.enabled or 'sentiment' not in self.pipelines:
            return {}
        
        try:
            # Limit text length to avoid memory issues
            text = text[:512] if len(text) > 512 else text
            
            if not text.strip():
                return {}
            
            # Run sentiment analysis
            result = self.pipelines['sentiment'](text)
            
            if result and len(result) > 0:
                prediction = result[0]
                
                # Map LABEL to our sentiment types
                label_mapping = {
                    'POSITIVE': SentimentType.POSITIVE,
                    'NEGATIVE': SentimentType.NEGATIVE,
                    'NEUTRAL': SentimentType.NEUTRAL
                }
                
                sentiment = label_mapping.get(prediction['label'], SentimentType.NEUTRAL)
                confidence = prediction['score']
                
                # Only return result if confidence is above threshold
                if confidence >= self.model_configs['sentiment']['confidence_threshold']:
                    return {
                        'sentiment': sentiment,
                        'confidence': confidence,
                        'raw_prediction': prediction
                    }
            
            return {}
            
        except Exception as e:
            self.logger.error(f"Sentiment analysis failed: {e}")
            return {}
    
    async def detect_emotions(self, text: str) -> Dict[str, Any]:
        """
        Detect emotions in text using RoBERTa
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with emotion detection results
        """
        if not self.enabled or 'emotion' not in self.pipelines:
            return {}
        
        try:
            # Limit text length
            text = text[:512] if len(text) > 512 else text
            
            if not text.strip():
                return {}
            
            # Run emotion detection
            results = self.pipelines['emotion'](text)
            
            if results:
                # Convert results to emotion mapping
                emotion_scores = {}
                dominant_emotion = None
                max_score = 0
                
                for result in results:
                    emotion_label = result['label'].lower()
                    score = result['score']
                    
                    # Map to our emotion types
                    emotion_mapping = {
                        'joy': EmotionType.JOY,
                        'anger': EmotionType.ANGER,
                        'fear': EmotionType.FEAR,
                        'surprise': EmotionType.SURPRISE,
                        'sadness': EmotionType.SADNESS,
                        'disgust': EmotionType.DISGUST
                    }
                    
                    if emotion_label in emotion_mapping:
                        emotion_type = emotion_mapping[emotion_label]
                        emotion_scores[emotion_type] = score
                        
                        if score > max_score:
                            max_score = score
                            dominant_emotion = emotion_type
                
                # Only return if confidence is above threshold
                if max_score >= self.model_configs['emotion']['confidence_threshold']:
                    return {
                        'dominant_emotion': dominant_emotion,
                        'emotion_scores': emotion_scores,
                        'confidence': max_score,
                        'raw_results': results
                    }
            
            return {}
            
        except Exception as e:
            self.logger.error(f"Emotion detection failed: {e}")
            return {}
    
    async def classify_email_content(self, subject: str, content: str) -> Dict[str, Any]:
        """
        Classify email content into categories
        
        Args:
            subject: Email subject line
            content: Email content
            
        Returns:
            Dictionary with classification results
        """
        if not self.enabled or 'zero_shot' not in self.pipelines:
            return {}
        
        try:
            # Combine subject and content
            full_text = f"Subject: {subject}\n\n{content}"
            
            # Limit text length
            full_text = full_text[:1024] if len(full_text) > 1024 else full_text
            
            if not full_text.strip():
                return {}
            
            # Get categories from config
            categories = self.model_configs['classification']['categories']
            
            # Run zero-shot classification
            result = self.pipelines['zero_shot'](full_text, categories)
            
            if result:
                return {
                    'primary_category': result['labels'][0],
                    'confidence': result['scores'][0],
                    'all_categories': dict(zip(result['labels'], result['scores'])),
                    'raw_result': result
                }
            
            return {}
            
        except Exception as e:
            self.logger.error(f"Email classification failed: {e}")
            return {}
    
    async def extract_named_entities(self, text: str) -> Dict[str, Any]:
        """
        Extract named entities from text using BERT NER
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with extracted entities
        """
        if not self.enabled or 'ner' not in self.pipelines:
            return {}
        
        try:
            # Limit text length
            text = text[:512] if len(text) > 512 else text
            
            if not text.strip():
                return {}
            
            # Run NER
            entities = self.pipelines['ner'](text)
            
            if entities:
                # Group entities by type
                entity_groups = {}
                for entity in entities:
                    entity_type = entity['entity_group']
                    entity_text = entity['word']
                    confidence = entity['score']
                    
                    # Only include entities we're configured to extract
                    if entity_type in self.model_configs['ner']['entities']:
                        if entity_type not in entity_groups:
                            entity_groups[entity_type] = []
                        
                        entity_groups[entity_type].append({
                            'text': entity_text,
                            'confidence': confidence,
                            'start': entity.get('start'),
                            'end': entity.get('end')
                        })
                
                return {
                    'entities_by_type': entity_groups,
                    'total_entities': len(entities),
                    'raw_entities': entities
                }
            
            return {}
            
        except Exception as e:
            self.logger.error(f"Named entity extraction failed: {e}")
            return {}
    
    async def calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate semantic similarity between two texts
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score between 0 and 1
        """
        if not self.enabled or 'similarity' not in self.models:
            return 0.0
        
        try:
            if not text1.strip() or not text2.strip():
                return 0.0
            
            # Generate embeddings
            embeddings = self.models['similarity'].encode([text1, text2])
            
            # Calculate cosine similarity
            from sklearn.metrics.pairwise import cosine_similarity
            similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
            
            return float(similarity)
            
        except Exception as e:
            self.logger.error(f"Text similarity calculation failed: {e}")
            return 0.0
    
    async def categorize_contact(self, contact: Contact, interaction_sample: str = "") -> Dict[str, Any]:
        """
        Categorize a contact using zero-shot classification
        
        Args:
            contact: Contact to categorize
            interaction_sample: Sample interaction text for context
            
        Returns:
            Dictionary with categorization results
        """
        if not self.enabled or 'zero_shot' not in self.pipelines:
            return {}
        
        try:
            # Build context for classification
            context_parts = []
            
            if contact.company:
                context_parts.append(f"Company: {contact.company}")
            
            if contact.job_title:
                context_parts.append(f"Job Title: {contact.job_title}")
            
            if contact.industry:
                context_parts.append(f"Industry: {contact.industry}")
            
            if interaction_sample:
                context_parts.append(f"Communication: {interaction_sample[:200]}")
            
            context = ". ".join(context_parts)
            
            if not context.strip():
                return {}
            
            # Get categories from config
            categories = self.model_configs['zero_shot']['categories']
            
            # Run classification
            result = self.pipelines['zero_shot'](context, categories)
            
            if result:
                return {
                    'primary_category': result['labels'][0],
                    'confidence': result['scores'][0],
                    'all_categories': dict(zip(result['labels'], result['scores'])),
                    'context_used': context
                }
            
            return {}
            
        except Exception as e:
            self.logger.error(f"Contact categorization failed: {e}")
            return {}
    
    async def validate_email_coherence(self, name: str, email: str) -> Dict[str, Any]:
        """
        Validate if name and email are coherent using text similarity
        
        Args:
            name: Person's name
            email: Email address
            
        Returns:
            Dictionary with validation results
        """
        if not self.enabled or 'similarity' not in self.models:
            return {'coherent': True, 'confidence': 0.5}  # Default to coherent
        
        try:
            if not name or not email:
                return {'coherent': True, 'confidence': 0.5}
            
            # Extract name from email local part
            email_local = email.split('@')[0].lower()
            
            # Clean email local part (remove numbers, dots, etc.)
            import re
            cleaned_email_local = re.sub(r'[^a-zA-Z]', ' ', email_local)
            
            # Calculate similarity between name and cleaned email
            similarity = await self.calculate_text_similarity(name.lower(), cleaned_email_local)
            
            # Determine coherence threshold
            threshold = 0.3  # Adjust based on testing
            coherent = similarity >= threshold
            
            return {
                'coherent': coherent,
                'confidence': similarity,
                'similarity_score': similarity,
                'threshold': threshold
            }
            
        except Exception as e:
            self.logger.error(f"Email coherence validation failed: {e}")
            return {'coherent': True, 'confidence': 0.5}
    
    async def detect_spam_promotional(self, subject: str, content: str) -> Dict[str, Any]:
        """
        Detect if email is spam or promotional using classification
        
        Args:
            subject: Email subject
            content: Email content
            
        Returns:
            Dictionary with spam/promotional detection results
        """
        if not self.enabled or 'zero_shot' not in self.pipelines:
            return {'is_spam': False, 'is_promotional': False, 'confidence': 0.5}
        
        try:
            # Combine subject and content
            full_text = f"Subject: {subject}\n\n{content[:500]}"  # Limit content
            
            if not full_text.strip():
                return {'is_spam': False, 'is_promotional': False, 'confidence': 0.5}
            
            # Classification categories
            categories = ['personal communication', 'business communication', 'promotional email', 'spam']
            
            # Run classification
            result = self.pipelines['zero_shot'](full_text, categories)
            
            if result:
                scores = dict(zip(result['labels'], result['scores']))
                
                is_promotional = scores.get('promotional email', 0) > 0.6
                is_spam = scores.get('spam', 0) > 0.7
                
                return {
                    'is_spam': is_spam,
                    'is_promotional': is_promotional,
                    'confidence': max(scores.get('promotional email', 0), scores.get('spam', 0)),
                    'category_scores': scores
                }
            
            return {'is_spam': False, 'is_promotional': False, 'confidence': 0.5}
            
        except Exception as e:
            self.logger.error(f"Spam/promotional detection failed: {e}")
            return {'is_spam': False, 'is_promotional': False, 'confidence': 0.5}
    
    async def detect_language(self, text: str) -> Dict[str, Any]:
        """
        Detect language of text (basic implementation)
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with language detection results
        """
        # This is a simplified implementation
        # In production, you might want to use a dedicated language detection model
        
        try:
            if not text.strip():
                return {'language': 'unknown', 'confidence': 0.0}
            
            # Simple heuristics for common languages
            text_lower = text.lower()
            
            # English indicators
            english_words = ['the', 'and', 'is', 'in', 'to', 'of', 'a', 'that', 'it', 'with']
            english_score = sum(1 for word in english_words if word in text_lower) / len(english_words)
            
            # Spanish indicators
            spanish_words = ['el', 'la', 'de', 'que', 'y', 'en', 'un', 'es', 'se', 'no']
            spanish_score = sum(1 for word in spanish_words if word in text_lower) / len(spanish_words)
            
            # French indicators
            french_words = ['le', 'de', 'et', 'à', 'un', 'il', 'être', 'et', 'en', 'avoir']
            french_score = sum(1 for word in french_words if word in text_lower) / len(french_words)
            
            # Determine language
            scores = {
                'english': english_score,
                'spanish': spanish_score,
                'french': french_score
            }
            
            detected_language = max(scores, key=scores.get)
            confidence = scores[detected_language]
            
            # Default to English if confidence is low
            if confidence < 0.1:
                detected_language = 'english'
                confidence = 0.5
            
            return {
                'language': detected_language,
                'confidence': confidence,
                'all_scores': scores
            }
            
        except Exception as e:
            self.logger.error(f"Language detection failed: {e}")
            return {'language': 'english', 'confidence': 0.5}
    
    async def analyze_communication_intelligence(self, interactions: List[Interaction]) -> Dict[str, Any]:
        """
        Analyze communication patterns for intelligence insights
        
        Args:
            interactions: List of interactions to analyze
            
        Returns:
            Dictionary with communication intelligence
        """
        if not interactions:
            return {}
        
        try:
            # Analyze sentiment trends
            sentiment_scores = []
            emotion_patterns = {}
            categories = []
            
            for interaction in interactions[-10:]:  # Last 10 interactions
                # Analyze sentiment
                if interaction.content_preview:
                    sentiment_result = await self.analyze_sentiment(interaction.content_preview)
                    if sentiment_result:
                        sentiment_scores.append(sentiment_result['confidence'] if sentiment_result['sentiment'] == SentimentType.POSITIVE else -sentiment_result['confidence'])
                    
                    # Analyze emotions
                    emotion_result = await self.detect_emotions(interaction.content_preview)
                    if emotion_result:
                        dominant_emotion = emotion_result['dominant_emotion']
                        if dominant_emotion not in emotion_patterns:
                            emotion_patterns[dominant_emotion] = 0
                        emotion_patterns[dominant_emotion] += 1
                    
                    # Classify email
                    classification_result = await self.classify_email_content(
                        interaction.subject, 
                        interaction.content_preview
                    )
                    if classification_result:
                        categories.append(classification_result['primary_category'])
            
            # Calculate trends
            sentiment_trend = "stable"
            if len(sentiment_scores) >= 3:
                recent_avg = sum(sentiment_scores[-3:]) / 3
                older_avg = sum(sentiment_scores[:-3]) / max(len(sentiment_scores) - 3, 1) if len(sentiment_scores) > 3 else recent_avg
                
                if recent_avg > older_avg + 0.1:
                    sentiment_trend = "improving"
                elif recent_avg < older_avg - 0.1:
                    sentiment_trend = "declining"
            
            # Determine relationship lifecycle stage
            lifecycle_stage = "active"
            if not interactions:
                lifecycle_stage = "new"
            else:
                days_since_last = (datetime.now() - interactions[-1].timestamp).days
                if days_since_last > 90:
                    lifecycle_stage = "dormant"
                elif days_since_last > 30:
                    lifecycle_stage = "cooling"
                elif len(sentiment_scores) > 0 and sum(sentiment_scores) / len(sentiment_scores) > 0.3:
                    lifecycle_stage = "engaged"
            
            return {
                'sentiment_trend': sentiment_trend,
                'average_sentiment': sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0,
                'dominant_emotions': emotion_patterns,
                'common_categories': list(set(categories)),
                'lifecycle_stage': lifecycle_stage,
                'total_interactions_analyzed': len(interactions),
                'communication_frequency': len(interactions) / max((datetime.now() - interactions[0].timestamp).days, 1) if interactions else 0
            }
            
        except Exception as e:
            self.logger.error(f"Communication intelligence analysis failed: {e}")
            return {}
    
    async def batch_analyze_interactions(self, interactions: List[Interaction]) -> Dict[str, Dict[str, Any]]:
        """
        Analyze multiple interactions in batch for efficiency
        
        Args:
            interactions: List of interactions to analyze
            
        Returns:
            Dictionary mapping interaction IDs to analysis results
        """
        results = {}
        
        # Process in batches to avoid memory issues
        batch_size = 10
        for i in range(0, len(interactions), batch_size):
            batch = interactions[i:i + batch_size]
            
            for interaction in batch:
                try:
                    analysis = {}
                    
                    if interaction.content_preview:
                        # Sentiment analysis
                        sentiment_result = await self.analyze_sentiment(interaction.content_preview)
                        if sentiment_result:
                            analysis['sentiment'] = sentiment_result
                        
                        # Emotion detection
                        emotion_result = await self.detect_emotions(interaction.content_preview)
                        if emotion_result:
                            analysis['emotions'] = emotion_result
                        
                        # Email classification
                        classification_result = await self.classify_email_content(
                            interaction.subject, 
                            interaction.content_preview
                        )
                        if classification_result:
                            analysis['classification'] = classification_result
                        
                        # Named entity recognition
                        ner_result = await self.extract_named_entities(interaction.content_preview)
                        if ner_result:
                            analysis['entities'] = ner_result
                    
                    results[interaction.message_id] = analysis
                    
                except Exception as e:
                    self.logger.error(f"Batch analysis failed for interaction {interaction.message_id}: {e}")
                    results[interaction.message_id] = {}
            
            # Small delay between batches
            await asyncio.sleep(0.1)
        
        return results
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about loaded models"""
        model_status = {}
        
        for model_type, config in self.model_configs.items():
            model_status[model_type] = {
                'enabled': config['enabled'],
                'model_name': config['model_name'],
                'loaded': model_type in self.pipelines or model_type in self.models
            }
        
        return {
            'enabled': self.enabled,
            'device': self.device,
            'cache_dir': str(self.cache_dir),
            'models': model_status,
            'transformers_available': TRANSFORMERS_AVAILABLE
        }
    
    async def test_models(self) -> Dict[str, Any]:
        """Test all loaded models with sample inputs"""
        if not self.enabled:
            return {'success': False, 'error': 'NLP engine not enabled'}
        
        test_results = {}
        sample_text = "Hello, this is a test message for our business meeting."
        
        # Test sentiment analysis
        if 'sentiment' in self.pipelines:
            try:
                result = await self.analyze_sentiment(sample_text)
                test_results['sentiment'] = {'success': bool(result), 'result': result}
            except Exception as e:
                test_results['sentiment'] = {'success': False, 'error': str(e)}
        
        # Test emotion detection
        if 'emotion' in self.pipelines:
            try:
                result = await self.detect_emotions(sample_text)
                test_results['emotion'] = {'success': bool(result), 'result': result}
            except Exception as e:
                test_results['emotion'] = {'success': False, 'error': str(e)}
        
        # Test NER
        if 'ner' in self.pipelines:
            try:
                result = await self.extract_named_entities(sample_text)
                test_results['ner'] = {'success': bool(result), 'result': result}
            except Exception as e:
                test_results['ner'] = {'success': False, 'error': str(e)}
        
        # Test text similarity
        if 'similarity' in self.models:
            try:
                result = await self.calculate_text_similarity(sample_text, "Hi, this is a test for our business meeting.")
                test_results['similarity'] = {'success': result > 0, 'similarity_score': result}
            except Exception as e:
                test_results['similarity'] = {'success': False, 'error': str(e)}
        
        return test_results
    
    def is_available(self) -> bool:
        """Check if NLP engine is available and functional"""
        return TRANSFORMERS_AVAILABLE and self.enabled and len(self.pipelines) > 0