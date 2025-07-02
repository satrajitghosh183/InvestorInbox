"""
Custom exceptions for the email enrichment system
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class EmailEnrichmentException(Exception):
    def __init__(self, message: str, provider: str = None):
        self.message = message
        self.provider = provider
        super().__init__(self.message)

class AuthenticationError(EmailEnrichmentException):
    pass

class ProviderError(EmailEnrichmentException):
    pass

class RateLimitError(EmailEnrichmentException):
    pass

class ValidationError(EmailEnrichmentException):
    pass

class EnrichmentError(EmailEnrichmentException):
    pass

class ExportError(EmailEnrichmentException):
    def __init__(self, message: str, export_format: str = None, file_path: str = None):
        super().__init__(message)
        self.export_format = export_format
        self.file_path = file_path

class ConfigurationError(EmailEnrichmentException):
    pass
