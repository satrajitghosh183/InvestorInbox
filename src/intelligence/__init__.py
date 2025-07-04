"""
Contact Intelligence Package
Advanced contact scoring and analysis capabilities
"""

try:
    from .contact_scorer import EnhancedContactScoringEngine
    __all__ = ['EnhancedContactScoringEngine']
except ImportError as e:
    print(f"⚠️ EnhancedContactScoringEngine not available: {e}")
    __all__ = []