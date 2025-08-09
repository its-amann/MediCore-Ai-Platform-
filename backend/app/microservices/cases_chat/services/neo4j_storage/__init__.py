"""
Neo4j Storage Service for Cases Chat
Provides both unified and legacy storage implementations
"""

from .unified_cases_chat_storage import UnifiedCasesChatStorage
from .cases_chat_storage import CasesChatStorage  # Legacy async
from .cases_chat_storage_sync import CasesChatStorageSync  # Legacy sync

# Factory function to get storage instance
def get_storage_instance(use_unified: bool = True, driver=None):
    """
    Get storage instance based on configuration
    
    Args:
        use_unified: Whether to use unified storage (recommended)
        driver: Neo4j driver instance (required for unified storage)
        
    Returns:
        Storage instance
    """
    if use_unified:
        if driver is None:
            from app.api.dependencies.database import get_sync_driver
            driver = get_sync_driver()
        
        return UnifiedCasesChatStorage(driver)
    else:
        # Legacy implementation
        from app.core.config import settings
        return CasesChatStorage(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password
        )


__all__ = [
    'UnifiedCasesChatStorage',
    'CasesChatStorage',
    'CasesChatStorageSync',
    'get_storage_instance'
]