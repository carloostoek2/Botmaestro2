"""
Módulo de Narrativa Profunda para DianaBot
Gestiona historias ramificadas, decisiones y progresión narrativa
"""
from __future__ import annotations

try:
    from .handlers import router as narrative_router
    from .models import StoryFragment, UserNarrativeState, UserDecision
    from .narrative_service import NarrativeService
    from .story_manager import StoryManager
    
    __all__ = [
        'narrative_router',
        'StoryFragment',
        'UserNarrativeState', 
        'UserDecision',
        'NarrativeService',
        'StoryManager'
    ]
except ImportError as e:
    import logging
    logging.getLogger(__name__).warning(f"Error importing narrative components: {e}")
    
    # Fallback exports
    narrative_router = None
    StoryFragment = None
    UserNarrativeState = None
    UserDecision = None
    NarrativeService = None
    StoryManager = None
    
    __all__ = []