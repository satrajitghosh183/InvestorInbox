# """
# Configuration settings for Email Enrichment System - Real Gmail Version
# """
# import os
# from pathlib import Path

# # Project paths
# PROJECT_ROOT = Path(__file__).parent.parent
# DATA_DIR = PROJECT_ROOT / "data"
# EXPORTS_DIR = PROJECT_ROOT / "exports"
# CONFIG_DIR = PROJECT_ROOT / "config"

# # Ensure directories exist
# DATA_DIR.mkdir(exist_ok=True)
# EXPORTS_DIR.mkdir(exist_ok=True)

# # Gmail API settings
# GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
# GMAIL_CREDENTIALS_FILE = CONFIG_DIR / "gmail_credentials.json"
# GMAIL_TOKEN_FILE = DATA_DIR / "gmail_token.json"

# # Email processing settings for real data
# MAX_EMAILS_TO_PROCESS = 1000  # Start with reasonable limit
# DAYS_BACK = 30  # Last 30 days for initial test

# # Enrichment settings - Start with simple domain-based enrichment
# ENABLE_ENRICHMENT = True
# ENRICHMENT_SOURCES = {
#     'clearbit': {
#         'enabled': False,  # Disable paid APIs for now
#         'api_key': os.getenv('CLEARBIT_API_KEY', ''),
#         'base_url': 'https://person.clearbit.com/v1/people/find'
#     },
#     'hunter': {
#         'enabled': False,  # Disable paid APIs for now
#         'api_key': os.getenv('HUNTER_API_KEY', ''),
#         'base_url': 'https://api.hunter.io/v2/email-finder'
#     },
#     'domain_inference': {
#         'enabled': True,  # Free domain-based enrichment
#     },
#     'mock': {
#         'enabled': False,  # Disable mock data for real run
#     }
# }

# # Export settings
# EXCEL_FILENAME_TEMPLATE = "gmail_contacts_enriched_{timestamp}.xlsx"
# DEFAULT_SHEET_NAME = "Gmail Contacts"

# # Real data settings
# DEMO_MODE = False  # Set to False for real data
# SHOW_PROGRESS_BARS = True
# COLORFUL_OUTPUT = True

# # Email filtering settings
# EXCLUDE_DOMAINS = [
#     'noreply.gmail.com',
#     'mail-noreply.google.com', 
#     'noreply.youtube.com',
#     'noreply.facebook.com',
#     'no-reply.uber.com',
#     'donotreply.com',
#     'mailer-daemon',
#     'postmaster'
# ]

# EXCLUDE_KEYWORDS = [
#     'noreply', 'no-reply', 'donotreply', 'mailer-daemon',
#     'postmaster', 'bounce', 'newsletter', 'notification',
#     'automated', 'system', 'robot', 'bot'
# ]

# # Contact quality thresholds
# MIN_EMAIL_FREQUENCY = 1  # Include all contacts for now
# MIN_NAME_LENGTH = 2      # Minimum characters in name
# REQUIRE_REAL_NAME = False  # Don't require real names initially



"""
Updated Configuration for Multi-Provider Email Enrichment System
Production-ready with environment variables, validation, and security
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
EXPORTS_DIR = PROJECT_ROOT / "exports"
LOGS_DIR = PROJECT_ROOT / "logs"
CACHE_DIR = DATA_DIR / "cache"
TOKENS_DIR = DATA_DIR / "tokens"

# Ensure directories exist
for directory in [DATA_DIR, EXPORTS_DIR, LOGS_DIR, CACHE_DIR, TOKENS_DIR]:
    directory.mkdir(exist_ok=True, parents=True)

class Environment(Enum):
    """Application environments"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"

@dataclass
class SecurityConfig:
    """Security configuration settings"""
    encrypt_tokens: bool = True
    token_encryption_key: Optional[str] = None
    max_failed_auth_attempts: int = 3
    auth_timeout_minutes: int = 60
    require_app_passwords: bool = True
    allowed_domains: List[str] = None
    
    def __post_init__(self):
        if self.allowed_domains is None:
            self.allowed_domains = []

@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""
    enable_rate_limiting: bool = True
    default_daily_limit: int = 10000
    default_hourly_limit: int = 1000
    default_minute_limit: int = 60
    rate_limit_storage: str = "memory"  # "memory" or "redis"
    redis_url: Optional[str] = None

@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_logging: bool = True
    log_file: Path = LOGS_DIR / "email_enrichment.log"
    max_file_size_mb: int = 100
    backup_count: int = 5
    console_logging: bool = True
    structured_logging: bool = False  # JSON format for production
    log_sensitive_data: bool = False

# Environment detection
ENVIRONMENT = Environment(os.getenv("ENVIRONMENT", "development"))
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
TESTING = ENVIRONMENT == Environment.TESTING

# Core application settings
APP_NAME = "Email Enrichment System"
APP_VERSION = "2.0.0"
API_VERSION = "v1"

# Configuration file paths
PROVIDERS_CONFIG_FILE = CONFIG_DIR / "providers_config.yaml"
MAIN_CONFIG_FILE = CONFIG_DIR / "config.yaml"

# Provider-specific configuration files
GMAIL_CREDENTIALS_FILE = CONFIG_DIR / "gmail_credentials.json"
OUTLOOK_CREDENTIALS_FILE = CONFIG_DIR / "outlook_credentials.json"

# Token storage
GMAIL_TOKEN_FILE = TOKENS_DIR / "gmail_token.json"
OUTLOOK_TOKEN_FILE = TOKENS_DIR / "outlook_token.json"

# Default processing settings
DEFAULT_DAYS_BACK = 30
DEFAULT_MAX_EMAILS = 1000
DEFAULT_MIN_FREQUENCY = 1
DEFAULT_BATCH_SIZE = 100

# Export settings
EXCEL_FILENAME_TEMPLATE = "enriched_contacts_{provider}_{timestamp}.xlsx"
CSV_FILENAME_TEMPLATE = "enriched_contacts_{provider}_{timestamp}.csv"
DEFAULT_SHEET_NAME = "Enriched Contacts"

# Cache settings
ENABLE_CACHING = True
CACHE_TTL_HOURS = 24
CACHE_MAX_SIZE_MB = 500

# Security settings
SECURITY_CONFIG = SecurityConfig(
    encrypt_tokens=ENVIRONMENT == Environment.PRODUCTION,
    token_encryption_key=os.getenv("TOKEN_ENCRYPTION_KEY"),
    max_failed_auth_attempts=int(os.getenv("MAX_AUTH_ATTEMPTS", "3")),
    auth_timeout_minutes=int(os.getenv("AUTH_TIMEOUT_MINUTES", "60")),
    require_app_passwords=True
)

# Rate limiting settings
RATE_LIMIT_CONFIG = RateLimitConfig(
    enable_rate_limiting=True,
    default_daily_limit=int(os.getenv("DEFAULT_DAILY_LIMIT", "10000")),
    default_hourly_limit=int(os.getenv("DEFAULT_HOURLY_LIMIT", "1000")),
    default_minute_limit=int(os.getenv("DEFAULT_MINUTE_LIMIT", "60")),
    rate_limit_storage=os.getenv("RATE_LIMIT_STORAGE", "memory"),
    redis_url=os.getenv("REDIS_URL")
)

# Logging settings
LOGGING_CONFIG = LoggingConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    file_logging=os.getenv("FILE_LOGGING", "true").lower() == "true",
    log_file=LOGS_DIR / os.getenv("LOG_FILE", "email_enrichment.log"),
    max_file_size_mb=int(os.getenv("LOG_MAX_SIZE_MB", "100")),
    backup_count=int(os.getenv("LOG_BACKUP_COUNT", "5")),
    console_logging=os.getenv("CONSOLE_LOGGING", "true").lower() == "true",
    structured_logging=ENVIRONMENT == Environment.PRODUCTION,
    log_sensitive_data=DEBUG and not ENVIRONMENT == Environment.PRODUCTION
)

# Email filtering settings
EXCLUDE_DOMAINS = [
    'noreply.gmail.com', 'mail-noreply.google.com', 
    'noreply.youtube.com', 'noreply.google.com',
    'noreply.outlook.com', 'noreply.microsoft.com',
    'no-reply.microsoft.com', 'noreply.yahoo.com',
    'no-reply.yahoo.com', 'noreply.icloud.com',
    'no-reply.apple.com', 'noreply.aol.com',
    'donotreply.com', 'mailer-daemon', 'postmaster'
]

EXCLUDE_KEYWORDS = [
    'noreply', 'no-reply', 'donotreply', 'mailer-daemon',
    'postmaster', 'bounce', 'newsletter', 'notification',
    'automated', 'system', 'robot', 'bot', 'auto-reply',
    'do-not-reply', 'no_reply', 'support+', 'help+',
    'security-noreply', 'accounts-noreply'
]

# Provider-specific settings
PROVIDER_SETTINGS = {
    'gmail': {
        'scopes': [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/userinfo.email'
        ],
        'batch_size': 100,
        'rate_limit_per_minute': 250,
        'concurrent_requests': 10
    },
    'outlook': {
        'scopes': [
            'https://graph.microsoft.com/Mail.Read',
            'https://graph.microsoft.com/User.Read',
            'https://graph.microsoft.com/Contacts.Read'
        ],
        'batch_size': 50,
        'rate_limit_per_minute': 60,
        'concurrent_requests': 5
    },
    'yahoo': {
        'imap_server': 'imap.mail.yahoo.com',
        'imap_port': 993,
        'batch_size': 25,
        'rate_limit_per_minute': 30,
        'concurrent_requests': 2
    },
    'icloud': {
        'imap_server': 'imap.mail.me.com',
        'imap_port': 993,
        'batch_size': 25,
        'rate_limit_per_minute': 20,
        'concurrent_requests': 2
    }
}

# Enrichment settings
ENRICHMENT_CONFIG = {
    'enable_enrichment': True,
    'max_concurrent_enrichments': 5,
    'enrichment_timeout': 30,
    'retry_failed_enrichments': True,
    'cache_enrichment_results': True,
    'sources': {
        'clearbit': {
            'enabled': bool(os.getenv('CLEARBIT_API_KEY')),
            'api_key': os.getenv('CLEARBIT_API_KEY'),
            'base_url': 'https://person.clearbit.com/v1/people/find',
            'timeout': 10,
            'rate_limit_per_minute': 600,
            'cost_per_request': 0.02
        },
        'hunter': {
            'enabled': bool(os.getenv('HUNTER_API_KEY')),
            'api_key': os.getenv('HUNTER_API_KEY'),
            'base_url': 'https://api.hunter.io/v2',
            'timeout': 10,
            'rate_limit_per_minute': 100,
            'cost_per_request': 0.01
        },
        'peopledatalabs': {
            'enabled': bool(os.getenv('PDL_API_KEY')),
            'api_key': os.getenv('PDL_API_KEY'),
            'base_url': 'https://api.peopledatalabs.com/v5',
            'timeout': 10,
            'rate_limit_per_minute': 1000,
            'cost_per_request': 0.01
        },
        'domain_inference': {
            'enabled': True,
            'timeout': 1,
            'confidence_score': 0.3
        },
        'mock_data': {
            'enabled': DEBUG or TESTING,
            'confidence_score': 0.5
        }
    }
}

# Database settings (for future use)
DATABASE_CONFIG = {
    'enabled': False,  # Currently using in-memory storage
    'type': os.getenv('DATABASE_TYPE', 'postgresql'),
    'host': os.getenv('DATABASE_HOST', 'localhost'),
    'port': int(os.getenv('DATABASE_PORT', '5432')),
    'name': os.getenv('DATABASE_NAME', 'email_enrichment'),
    'user': os.getenv('DATABASE_USER', 'postgres'),
    'password': os.getenv('DATABASE_PASSWORD', ''),
    'ssl_mode': os.getenv('DATABASE_SSL_MODE', 'prefer'),
    'pool_size': int(os.getenv('DATABASE_POOL_SIZE', '5')),
    'max_overflow': int(os.getenv('DATABASE_MAX_OVERFLOW', '10'))
}

# API settings (for future web interface)
API_CONFIG = {
    'enabled': False,  # Will be enabled in Phase 4
    'host': os.getenv('API_HOST', '0.0.0.0'),
    'port': int(os.getenv('API_PORT', '8000')),
    'workers': int(os.getenv('API_WORKERS', '1')),
    'cors_origins': os.getenv('CORS_ORIGINS', '*').split(','),
    'api_key_required': os.getenv('API_KEY_REQUIRED', 'false').lower() == 'true',
    'api_key': os.getenv('API_KEY'),
    'rate_limit_enabled': True,
    'rate_limit_per_minute': int(os.getenv('API_RATE_LIMIT', '100'))
}

# Monitoring and observability
MONITORING_CONFIG = {
    'enabled': ENVIRONMENT in [Environment.STAGING, Environment.PRODUCTION],
    'metrics_enabled': True,
    'health_check_enabled': True,
    'sentry_dsn': os.getenv('SENTRY_DSN'),
    'datadog_api_key': os.getenv('DATADOG_API_KEY'),
    'prometheus_enabled': False,
    'metrics_port': int(os.getenv('METRICS_PORT', '9090'))
}

# Feature flags
FEATURE_FLAGS = {
    'multi_provider_support': True,
    'real_time_sync': False,  # Future feature
    'ai_enrichment': False,   # Phase 3 feature
    'web_dashboard': False,   # Phase 4 feature
    'api_access': False,      # Phase 4 feature
    'webhook_support': False, # Phase 5 feature
    'advanced_analytics': False,  # Phase 5 feature
    'bulk_operations': True,
    'scheduled_jobs': False,  # Phase 6 feature
}

def load_config_file(config_file: Path) -> Dict[str, Any]:
    """Load configuration from YAML or JSON file"""
    if not config_file.exists():
        return {}
    
    try:
        with open(config_file, 'r') as f:
            if config_file.suffix.lower() in ['.yaml', '.yml']:
                return yaml.safe_load(f) or {}
            elif config_file.suffix.lower() == '.json':
                return json.load(f) or {}
            else:
                raise ValueError(f"Unsupported config file format: {config_file.suffix}")
    except Exception as e:
        print(f"Warning: Failed to load config file {config_file}: {e}")
        return {}

def load_provider_credentials(provider: str) -> Dict[str, Any]:
    """Load credentials for a specific provider"""
    cred_file = CONFIG_DIR / f"{provider}_credentials.json"
    
    if cred_file.exists():
        try:
            with open(cred_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load {provider} credentials: {e}")
    
    return {}

def get_env_vars_for_provider(provider: str) -> Dict[str, str]:
    """Get environment variables for a provider"""
    env_vars = {}
    
    if provider == 'outlook':
        env_vars = {
            'client_id': os.getenv('OUTLOOK_CLIENT_ID'),
            'client_secret': os.getenv('OUTLOOK_CLIENT_SECRET'),
            'tenant_id': os.getenv('OUTLOOK_TENANT_ID', 'common')
        }
    elif provider == 'yahoo':
        env_vars = {
            'email': os.getenv('YAHOO_EMAIL'),
            'password': os.getenv('YAHOO_APP_PASSWORD')
        }
    elif provider == 'icloud':
        env_vars = {
            'email': os.getenv('ICLOUD_EMAIL'),
            'app_password': os.getenv('ICLOUD_APP_PASSWORD')
        }
    elif provider == 'aol':
        env_vars = {
            'email': os.getenv('AOL_EMAIL'),
            'password': os.getenv('AOL_PASSWORD')
        }
    
    # Filter out None values
    return {k: v for k, v in env_vars.items() if v is not None}

def validate_configuration() -> List[str]:
    """Validate configuration and return list of issues"""
    issues = []
    
    # Check required directories
    for directory in [DATA_DIR, EXPORTS_DIR, LOGS_DIR]:
        if not directory.exists():
            issues.append(f"Required directory missing: {directory}")
    
    # Validate security settings
    if ENVIRONMENT == Environment.PRODUCTION:
        if SECURITY_CONFIG.encrypt_tokens and not SECURITY_CONFIG.token_encryption_key:
            issues.append("Token encryption key required in production")
        
        if DEBUG:
            issues.append("DEBUG should be False in production")
        
        if LOGGING_CONFIG.log_sensitive_data:
            issues.append("Sensitive data logging should be disabled in production")
    
    # Check provider credentials
    providers_configured = 0
    
    if GMAIL_CREDENTIALS_FILE.exists():
        providers_configured += 1
    else:
        issues.append("Gmail credentials file not found (optional)")
    
    outlook_creds = get_env_vars_for_provider('outlook')
    if outlook_creds.get('client_id') and outlook_creds.get('client_secret'):
        providers_configured += 1
    else:
        issues.append("Outlook credentials not configured (optional)")
    
    if providers_configured == 0:
        issues.append("No email providers configured - at least one provider is required")
    
    # Validate enrichment settings
    enabled_sources = [k for k, v in ENRICHMENT_CONFIG['sources'].items() if v.get('enabled')]
    if ENRICHMENT_CONFIG['enable_enrichment'] and not enabled_sources:
        issues.append("Enrichment enabled but no sources configured")
    
    return issues

def get_configuration_summary() -> Dict[str, Any]:
    """Get a summary of current configuration"""
    return {
        'environment': ENVIRONMENT.value,
        'debug': DEBUG,
        'app_version': APP_VERSION,
        'providers_configured': [
            provider for provider in ['gmail', 'outlook', 'yahoo', 'icloud'] 
            if (CONFIG_DIR / f"{provider}_credentials.json").exists() or 
               bool(get_env_vars_for_provider(provider))
        ],
        'enrichment_sources': [
            k for k, v in ENRICHMENT_CONFIG['sources'].items() 
            if v.get('enabled')
        ],
        'features_enabled': [
            k for k, v in FEATURE_FLAGS.items() if v
        ],
        'directories': {
            'config': str(CONFIG_DIR),
            'data': str(DATA_DIR),
            'exports': str(EXPORTS_DIR),
            'logs': str(LOGS_DIR)
        }
    }

# Load any additional configuration from files
_main_config = load_config_file(MAIN_CONFIG_FILE)
_providers_config = load_config_file(PROVIDERS_CONFIG_FILE)

# Override settings with file-based configuration
if _main_config:
    # Update global settings with values from config file
    globals().update(_main_config.get('global_settings', {}))

# Validate configuration on import
_config_issues = validate_configuration()
if _config_issues and not TESTING:
    print("Configuration Issues Found:")
    for issue in _config_issues:
        print(f"  - {issue}")
    if any("required" in issue.lower() for issue in _config_issues):
        print("\nSome issues are critical. Please fix them before running the application.")

# Export commonly used settings
__all__ = [
    'ENVIRONMENT', 'DEBUG', 'PROJECT_ROOT', 'CONFIG_DIR', 'DATA_DIR', 
    'EXPORTS_DIR', 'LOGS_DIR', 'GMAIL_CREDENTIALS_FILE', 'OUTLOOK_CREDENTIALS_FILE',
    'DEFAULT_DAYS_BACK', 'DEFAULT_MAX_EMAILS', 'ENRICHMENT_CONFIG',
    'SECURITY_CONFIG', 'RATE_LIMIT_CONFIG', 'LOGGING_CONFIG',
    'EXCLUDE_DOMAINS', 'EXCLUDE_KEYWORDS', 'PROVIDER_SETTINGS',
    'load_provider_credentials', 'get_env_vars_for_provider',
    'validate_configuration', 'get_configuration_summary'
]