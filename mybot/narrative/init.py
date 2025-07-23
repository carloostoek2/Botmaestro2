"""
Módulo de Narrativa Profunda para DianaBot
Gestiona historias ramificadas, decisiones y progresión narrativa
"""

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
