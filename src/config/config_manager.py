
"""
Simplified Configuration Manager for Email Enrichment System
Handles basic configuration loading without complex auto-discovery
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

class ConfigManager:
    """
    Simplified configuration manager
    """
    
    def __init__(self, config_dir: str = "config"):
        self.logger = logging.getLogger(__name__)
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        # Basic configurations
        self._provider_configs = {}
        self._enrichment_config = {}
        
        self._load_basic_configs()
    
    def _load_basic_configs(self):
        """Load basic configuration"""
        try:
            # Check for Gmail credentials
            gmail_creds = self.config_dir / "gmail_credentials.json"
            if gmail_creds.exists():
                self._provider_configs['gmail'] = {
                    'enabled': True,
                    'credentials_file': str(gmail_creds)
                }
            
            # Check for other Gmail credential files
            for cred_file in self.config_dir.glob("gmail_*_credentials.json"):
                email = self._extract_email_from_filename(cred_file.name)
                if email:
                    self._provider_configs[f'gmail_{email}'] = {
                        'enabled': True,
                        'email': email,
                        'credentials_file': str(cred_file)
                    }
            
            # Check environment variables for other providers
            if os.getenv('OUTLOOK_CLIENT_ID') and os.getenv('OUTLOOK_CLIENT_SECRET'):
                self._provider_configs['outlook'] = {
                    'enabled': True,
                    'client_id': os.getenv('OUTLOOK_CLIENT_ID'),
                    'client_secret': os.getenv('OUTLOOK_CLIENT_SECRET'),
                    'tenant_id': os.getenv('OUTLOOK_TENANT_ID', 'common')
                }
            
            if os.getenv('YAHOO_EMAIL') and os.getenv('YAHOO_APP_PASSWORD'):
                self._provider_configs['yahoo'] = {
                    'enabled': True,
                    'email': os.getenv('YAHOO_EMAIL'),
                    'app_password': os.getenv('YAHOO_APP_PASSWORD')
                }
            
            if os.getenv('ICLOUD_EMAIL') and os.getenv('ICLOUD_APP_PASSWORD'):
                self._provider_configs['icloud'] = {
                    'enabled': True,
                    'email': os.getenv('ICLOUD_EMAIL'),
                    'app_password': os.getenv('ICLOUD_APP_PASSWORD')
                }
            
            # Basic enrichment config
            self._enrichment_config = {
                'sources': {
                    'clearbit': {
                        'enabled': bool(os.getenv('CLEARBIT_API_KEY')),
                        'api_key': os.getenv('CLEARBIT_API_KEY', ''),
                        'confidence_score': 0.9
                    },
                    'hunter': {
                        'enabled': bool(os.getenv('HUNTER_API_KEY')),
                        'api_key': os.getenv('HUNTER_API_KEY', ''),
                        'confidence_score': 0.7
                    },
                    'peopledatalabs': {
                        'enabled': bool(os.getenv('PDL_API_KEY')),
                        'api_key': os.getenv('PDL_API_KEY', ''),
                        'confidence_score': 0.85
                    },
                    'domain_inference': {
                        'enabled': True,
                        'confidence_score': 0.6
                    },
                    'mock_data': {
                        'enabled': True,
                        'confidence_score': 0.8
                    }
                },
                'ai': {
                    'openai': {
                        'enabled': bool(os.getenv('OPENAI_API_KEY')),
                        'api_key': os.getenv('OPENAI_API_KEY', ''),
                        'model': 'gpt-4'
                    }
                },
                'performance': {
                    'max_concurrent_enrichments': 5,
                    'daily_budget': 100.0,
                    'max_cost_per_contact': 1.0
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to load configurations: {e}")
    
    def _extract_email_from_filename(self, filename: str) -> Optional[str]:
        """Extract email from credential filename"""
        import re
        # Pattern: gmail_email@domain.com_credentials.json
        pattern = r'gmail_([^_]+@[^_]+)_credentials\.json'
        match = re.match(pattern, filename)
        return match.group(1) if match else None
    
    def get_provider_configs(self) -> Dict[str, Any]:
        """Get all provider configurations"""
        return self._provider_configs
    
    def get_enrichment_config(self) -> Dict[str, Any]:
        """Get enrichment configuration"""
        return self._enrichment_config
    
    def get_source_config(self, source_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific enrichment source"""
        return self._enrichment_config.get('sources', {}).get(source_name)
    
    def is_source_enabled(self, source_name: str) -> bool:
        """Check if an enrichment source is enabled"""
        source_config = self.get_source_config(source_name)
        return source_config.get('enabled', False) if source_config else False
    
    def get_ai_config(self, ai_provider: str) -> Optional[Dict[str, Any]]:
        """Get AI configuration for a specific provider"""
        return self._enrichment_config.get('ai', {}).get(ai_provider)
    
    def is_ai_enabled(self, ai_provider: str) -> bool:
        """Check if an AI provider is enabled"""
        ai_config = self.get_ai_config(ai_provider)
        return ai_config.get('enabled', False) if ai_config else False
    
    def get_performance_config(self) -> Dict[str, Any]:
        """Get performance configuration"""
        return self._enrichment_config.get('performance', {})
    
    def get_huggingface_config(self) -> Dict[str, Any]:
        """Get Hugging Face configuration"""
        return {
            'enabled': True,
            'use_local_models': True,
            'cache_dir': 'data/models',
            'device': 'cpu'
        }
    
    def get_contact_intelligence_config(self) -> Dict[str, Any]:
        """Get contact intelligence configuration"""
        return {
            'scoring': {
                'enabled': True,
                'factors': ['interaction_frequency', 'email_response_rate']
            }
        }
    
    def get_location_services_config(self) -> Dict[str, Any]:
        """Get location services configuration"""
        return {
            'ip_geolocation': {
                'enabled': False,
                'provider': 'ipapi'
            }
        }
    
    # Mock methods for compatibility
    @property
    def performance_config(self):
        """Mock performance config object"""
        class MockPerformanceConfig:
            def __init__(self, config_dict):
                self.max_concurrent_enrichments = config_dict.get('max_concurrent_enrichments', 5)
                self.daily_budget = config_dict.get('daily_budget', 100.0)
                self.max_cost_per_contact = config_dict.get('max_cost_per_contact', 1.0)
        
        return MockPerformanceConfig(self.get_performance_config())


# Global configuration manager instance
_config_manager = None

def get_config_manager() -> ConfigManager:
    """Get the global configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager

def reset_config_manager():
    """Reset the global configuration manager (useful for testing)"""
    global _config_manager
    _config_manager = None