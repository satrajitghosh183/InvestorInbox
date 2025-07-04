# src/enrichment/__init__.py
"""
Enrichment module initialization - Fixed version
"""

# Import basic classes that don't have complex dependencies
try:
    # Import the main enrichment classes
    from .enrichment import ContactEnricher, EnrichmentResult, EnrichmentCache
    ENRICHMENT_AVAILABLE = True
    
except ImportError as e:
    # Create fallback classes if imports fail
    print(f"⚠️ Full enrichment module not available: {e}")
    
    class EnrichmentCache:
        def __init__(self, ttl_hours=24):
            self.cache = {}
        def get(self, email): return None
        def set(self, email, data): pass
        def clear(self): pass
        def size(self): return 0
    
    class EnrichmentResult:
        def __init__(self, success=False, **kwargs):
            self.success = success
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    class ContactEnricher:
        def __init__(self):
            self.logger = None
            self.cache = EnrichmentCache()
        
        async def enrich_contacts(self, contacts):
            """Fallback enrichment - just returns contacts unchanged"""
            print(f"⚠️ Using fallback enrichment for {len(contacts)} contacts")
            return contacts
        
        async def cleanup(self):
            pass
        
        def get_statistics(self):
            return {"sources_available": 0, "cache_size": 0}
    
    ENRICHMENT_AVAILABLE = False

# Export the main classes
__all__ = [
    'ContactEnricher',
    'EnrichmentResult', 
    'EnrichmentCache',
    'ENRICHMENT_AVAILABLE'
]