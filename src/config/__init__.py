# src/config/__init__.py
"""Configuration module"""

# Direct imports since everything is now in the same directory
from .config import *
from .config_manager import *

__all__ = [
    'PROJECT_ROOT', 'CONFIG_DIR', 'DATA_DIR', 'EXPORTS_DIR', 'LOGS_DIR',
    'ENRICHMENT_CONFIG', 'PROVIDER_SETTINGS', 'GMAIL_CREDENTIALS_FILE',
    'DEFAULT_DAYS_BACK', 'DEFAULT_MAX_EMAILS', 'EXCLUDE_DOMAINS', 'EXCLUDE_KEYWORDS',
    'get_config_manager', 'get_env_vars_for_provider', 'load_provider_credentials'
]