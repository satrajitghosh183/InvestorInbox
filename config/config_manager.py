"""
Configuration Manager for Enhanced Email Enrichment System
Handles loading and validation of enrichment configurations
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

@dataclass
class EnrichmentSourceConfig:
    """Configuration for an enrichment source"""
    enabled: bool = False
    api_key: str = ""
    base_url: str = ""
    cost_per_request: float = 0.0
    rate_limit: int = 100
    confidence_score: float = 0.5
    priority: int = 5
    fields: List[str] = field(default_factory=list)
    timeout: int = 30
    max_retries: int = 3

@dataclass
class AIConfig:
    """Configuration for AI services"""
    enabled: bool = False
    api_key: str = ""
    model: str = ""
    cost_per_1k_tokens: float = 0.0
    max_tokens: int = 1000
    temperature: float = 0.1
    confidence_score: float = 0.9
    rate_limit: int = 1000

@dataclass
class PerformanceConfig:
    """Performance and optimization settings"""
    max_concurrent_enrichments: int = 5
    cache_ttl_hours: int = 24
    enable_caching: bool = True
    batch_size: int = 50
    retry_attempts: int = 3
    retry_delay: float = 1.0
    timeout: int = 30
    
    # Rate limiting
    per_minute: int = 100
    per_hour: int = 3000
    per_day: int = 50000
    
    # Cost controls
    daily_budget: float = 50.0
    max_cost_per_contact: float = 1.0
    alert_threshold: float = 0.8

class ConfigManager:
    """Manages configuration loading and validation"""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.logger = logging.getLogger(__name__)
        
        # Default config paths
        self.config_dir = Path("src/config")
        self.config_path = config_path or self.config_dir / "enrichment_config.yaml"
        self.secrets_path = self.config_dir / "secrets.json"
        
        # Loaded configurations
        self.config: Dict[str, Any] = {}
        self.enrichment_sources: Dict[str, EnrichmentSourceConfig] = {}
        self.ai_config: Dict[str, AIConfig] = {}
        self.performance_config: PerformanceConfig = PerformanceConfig()
        
        # Load configurations
        self._load_configurations()
    
    def _load_configurations(self):
        """Load all configuration files"""
        try:
            # Load main config
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    self.config = yaml.safe_load(f)
                self.logger.info(f"Loaded configuration from {self.config_path}")
            else:
                self.logger.warning(f"Config file not found: {self.config_path}")
                self.config = self._get_default_config()
            
            # Load secrets if available
            self._load_secrets()
            
            # Parse configurations
            self._parse_enrichment_sources()
            self._parse_ai_config()
            self._parse_performance_config()
            
            # Validate configurations
            self._validate_configurations()
            
        except Exception as e:
            self.logger.error(f"Failed to load configurations: {e}")
            raise
    
    def _load_secrets(self):
        """Load API keys and secrets from separate file"""
        try:
            if self.secrets_path.exists():
                with open(self.secrets_path, 'r') as f:
                    secrets = json.load(f)
                
                # Merge secrets into config
                for source_name, source_config in self.config.get('sources', {}).items():
                    if source_name in secrets:
                        source_config['api_key'] = secrets[source_name].get('api_key', '')
                
                # AI services secrets
                ai_services = self.config.get('ai_services', {})
                if 'openai' in ai_services and 'openai' in secrets:
                    ai_services['openai']['api_key'] = secrets['openai'].get('api_key', '')
                
                self.logger.info("Loaded API secrets")
            else:
                self.logger.info("No secrets file found - using environment variables")
                self._load_from_environment()
                
        except Exception as e:
            self.logger.warning(f"Failed to load secrets: {e}")
    
    def _load_from_environment(self):
        """Load API keys from environment variables"""
        env_mappings = {
            'CLEARBIT_API_KEY': ('sources', 'clearbit', 'api_key'),
            'PEOPLEDATALABS_API_KEY': ('sources', 'peopledatalabs', 'api_key'),
            'HUNTER_API_KEY': ('sources', 'hunter', 'api_key'),
            'ZOOMINFO_API_KEY': ('sources', 'zoominfo', 'api_key'),
            'APOLLO_API_KEY': ('sources', 'apollo', 'api_key'),
            'OPENAI_API_KEY': ('ai_services', 'openai', 'api_key'),
            'TWITTER_BEARER_TOKEN': ('social_networks', 'twitter', 'bearer_token'),
            'GITHUB_TOKEN': ('social_networks', 'github', 'api_token'),
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value:
                # Navigate to the config location
                current = self.config
                for key in config_path[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]
                current[config_path[-1]] = value
                self.logger.info(f"Loaded {env_var} from environment")
    
    def _parse_enrichment_sources(self):
        """Parse enrichment source configurations"""
        sources_config = self.config.get('sources', {})
        
        for source_name, source_data in sources_config.items():
            self.enrichment_sources[source_name] = EnrichmentSourceConfig(
                enabled=source_data.get('enabled', False),
                api_key=source_data.get('api_key', ''),
                base_url=source_data.get('base_url', ''),
                cost_per_request=source_data.get('cost_per_request', 0.0),
                rate_limit=source_data.get('rate_limit', 100),
                confidence_score=source_data.get('confidence_score', 0.5),
                priority=source_data.get('priority', 5),
                fields=source_data.get('fields', []),
                timeout=source_data.get('timeout', 30),
                max_retries=source_data.get('max_retries', 3)
            )
    
    def _parse_ai_config(self):
        """Parse AI service configurations"""
        ai_services = self.config.get('ai_services', {})
        
        for service_name, service_data in ai_services.items():
            if isinstance(service_data, dict) and 'api_key' in service_data:
                self.ai_config[service_name] = AIConfig(
                    enabled=service_data.get('enabled', False),
                    api_key=service_data.get('api_key', ''),
                    model=service_data.get('model', ''),
                    cost_per_1k_tokens=service_data.get('cost_per_1k_tokens', 0.0),
                    max_tokens=service_data.get('max_tokens', 1000),
                    temperature=service_data.get('temperature', 0.1),
                    confidence_score=service_data.get('confidence_score', 0.9),
                    rate_limit=service_data.get('rate_limit', 1000)
                )
    
    def _parse_performance_config(self):
        """Parse performance configuration"""
        perf_config = self.config.get('performance', {})
        
        self.performance_config = PerformanceConfig(
            max_concurrent_enrichments=perf_config.get('max_concurrent_enrichments', 5),
            cache_ttl_hours=perf_config.get('cache_ttl_hours', 24),
            enable_caching=perf_config.get('enable_caching', True),
            batch_size=perf_config.get('batch_size', 50),
            retry_attempts=perf_config.get('retry_attempts', 3),
            retry_delay=perf_config.get('retry_delay', 1.0),
            timeout=perf_config.get('timeout', 30)
        )
        
        # Rate limiting
        rate_limiting = perf_config.get('rate_limiting', {})
        if rate_limiting.get('enabled', True):
            self.performance_config.per_minute = rate_limiting.get('per_minute', 100)
            self.performance_config.per_hour = rate_limiting.get('per_hour', 3000)
            self.performance_config.per_day = rate_limiting.get('per_day', 50000)
        
        # Cost controls
        cost_controls = perf_config.get('cost_controls', {})
        self.performance_config.daily_budget = cost_controls.get('daily_budget', 50.0)
        self.performance_config.max_cost_per_contact = cost_controls.get('max_cost_per_contact', 1.0)
        self.performance_config.alert_threshold = cost_controls.get('alert_threshold', 0.8)
    
    def _validate_configurations(self):
        """Validate loaded configurations"""
        # Check for enabled sources with missing API keys
        enabled_sources = [name for name, config in self.enrichment_sources.items() 
                          if config.enabled and not config.api_key and name not in ['domain_inference', 'mock_data']]
        
        if enabled_sources:
            self.logger.warning(f"Enabled sources missing API keys: {enabled_sources}")
        
        # Check AI configurations
        enabled_ai = [name for name, config in self.ai_config.items() 
                     if config.enabled and not config.api_key]
        
        if enabled_ai:
            self.logger.warning(f"Enabled AI services missing API keys: {enabled_ai}")
        
        # Validate performance settings
        if self.performance_config.max_concurrent_enrichments > 20:
            self.logger.warning("High concurrent enrichments may cause rate limiting")
        
        if self.performance_config.daily_budget <= 0:
            self.logger.warning("Daily budget is 0 - enrichment may be limited")
    
    def get_enabled_sources(self) -> List[str]:
        """Get list of enabled enrichment sources"""
        return [name for name, config in self.enrichment_sources.items() if config.enabled]
    
    def get_source_config(self, source_name: str) -> Optional[EnrichmentSourceConfig]:
        """Get configuration for a specific source"""
        return self.enrichment_sources.get(source_name)
    
    def get_ai_config(self, service_name: str) -> Optional[AIConfig]:
        """Get AI service configuration"""
        return self.ai_config.get(service_name)
    
    def is_source_enabled(self, source_name: str) -> bool:
        """Check if a source is enabled and configured"""
        config = self.get_source_config(source_name)
        if not config:
            return False
        
        return config.enabled and (config.api_key or source_name in ['domain_inference', 'mock_data'])
    
    def is_ai_enabled(self, service_name: str) -> bool:
        """Check if an AI service is enabled and configured"""
        config = self.get_ai_config(service_name)
        if not config:
            return False
        
        return config.enabled and config.api_key
    
    def get_huggingface_config(self) -> Dict[str, Any]:
        """Get Hugging Face configuration"""
        return self.config.get('huggingface', {})
    
    def get_social_networks_config(self) -> Dict[str, Any]:
        """Get social networks configuration"""
        return self.config.get('social_networks', {})
    
    def get_location_services_config(self) -> Dict[str, Any]:
        """Get location services configuration"""
        return self.config.get('location_services', {})
    
    def get_contact_intelligence_config(self) -> Dict[str, Any]:
        """Get contact intelligence configuration"""
        return self.config.get('contact_intelligence', {})
    
    def get_data_quality_config(self) -> Dict[str, Any]:
        """Get data quality configuration"""
        return self.config.get('data_quality', {})
    
    def update_source_config(self, source_name: str, updates: Dict[str, Any]):
        """Update configuration for a source"""
        if source_name in self.enrichment_sources:
            config = self.enrichment_sources[source_name]
            for key, value in updates.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            
            # Also update the main config
            if 'sources' not in self.config:
                self.config['sources'] = {}
            if source_name not in self.config['sources']:
                self.config['sources'][source_name] = {}
            
            self.config['sources'][source_name].update(updates)
    
    def save_config(self, path: Optional[Path] = None):
        """Save current configuration to file"""
        save_path = path or self.config_path
        
        try:
            with open(save_path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False, indent=2)
            self.logger.info(f"Configuration saved to {save_path}")
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")
            raise
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration if no config file exists"""
        return {
            'sources': {
                'domain_inference': {
                    'enabled': True,
                    'confidence_score': 0.6,
                    'priority': 4
                },
                'mock_data': {
                    'enabled': True,
                    'confidence_score': 0.8,
                    'priority': 5
                }
            },
            'performance': {
                'max_concurrent_enrichments': 5,
                'cache_ttl_hours': 24,
                'enable_caching': True,
                'batch_size': 50,
                'rate_limiting': {
                    'enabled': True,
                    'per_minute': 100,
                    'per_hour': 1000,
                    'per_day': 10000
                },
                'cost_controls': {
                    'daily_budget': 10.0,
                    'max_cost_per_contact': 0.50,
                    'alert_threshold': 0.8
                }
            },
            'data_quality': {
                'min_confidence_score': 0.5,
                'require_email_validation': True,
                'exclude_generic_emails': True
            },
            'logging': {
                'level': 'INFO',
                'enrichment_stats': True,
                'cost_tracking': True
            }
        }
    
    def get_cost_summary(self) -> Dict[str, float]:
        """Get cost estimates for enabled sources"""
        costs = {}
        
        for source_name, config in self.enrichment_sources.items():
            if config.enabled and config.cost_per_request > 0:
                costs[source_name] = config.cost_per_request
        
        for service_name, config in self.ai_config.items():
            if config.enabled and config.cost_per_1k_tokens > 0:
                # Estimate cost for average enrichment (500 tokens)
                estimated_cost = (config.cost_per_1k_tokens * 500) / 1000
                costs[f"{service_name}_ai"] = estimated_cost
        
        return costs
    
    def estimate_enrichment_cost(self, contact_count: int) -> Dict[str, Any]:
        """Estimate total cost for enriching contacts"""
        source_costs = self.get_cost_summary()
        
        # Calculate per-contact cost
        per_contact_cost = sum(source_costs.values())
        total_cost = per_contact_cost * contact_count
        
        # Check against budget
        budget_available = self.performance_config.daily_budget
        within_budget = total_cost <= budget_available
        
        return {
            'per_contact_cost': per_contact_cost,
            'total_estimated_cost': total_cost,
            'daily_budget': budget_available,
            'within_budget': within_budget,
            'contacts_affordable': int(budget_available / per_contact_cost) if per_contact_cost > 0 else contact_count,
            'source_breakdown': source_costs
        }
    
    def __str__(self):
        enabled_sources = self.get_enabled_sources()
        return f"ConfigManager(sources={len(enabled_sources)}, enabled={enabled_sources})"

# Global configuration manager instance
_config_manager = None

def get_config_manager() -> ConfigManager:
    """Get global configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager

def reload_config():
    """Reload configuration from files"""
    global _config_manager
    _config_manager = ConfigManager()