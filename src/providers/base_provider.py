"""
Abstract base class for email providers
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging

from core.models import Contact, EmailProvider, ProviderStatus
from core.exceptions import ProviderError

@dataclass
class ProviderConfig:
    provider_type: EmailProvider
    credentials: Dict[str, Any]
    settings: Dict[str, Any]
    rate_limits: Dict[str, int]
    timeout: int = 30
    max_retries: int = 3

class BaseEmailProvider(ABC):
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.provider_type = config.provider_type
        self.logger = logging.getLogger(f"{__name__}.{self.provider_type.value}")
        self.is_authenticated = False
        self.api_calls_today = 0
        self.rate_limit_remaining = config.rate_limits.get('daily', 10000)
    
    @abstractmethod
    async def authenticate(self) -> bool:
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        pass
    
    @abstractmethod
    async def get_account_info(self) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    async def extract_contacts(self, days_back: int = 30, max_emails: int = 1000, account_id: Optional[str] = None) -> List[Contact]:
        pass
    
    def get_status(self) -> ProviderStatus:
        return ProviderStatus(
            provider=self.provider_type,
            is_connected=self.is_authenticated
        )
    
    def _increment_api_call(self):
        self.api_calls_today += 1
        self.rate_limit_remaining = max(0, self.rate_limit_remaining - 1)
    
    async def validate_config(self) -> bool:
        return True
    
    def _get_required_credentials(self) -> List[str]:
        return []
