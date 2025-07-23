"""
Esquemas de datos para el contenido narrativo en JSON
"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class ChoiceSchema(BaseModel):
    """Esquema para una opción de decisión"""
    id: str
    text: str
    next_fragment: str
    requirements: Optional[Dict[str, Any]] = Field(default_factory=dict)
    effects: Optional[Dict[str, Any]] = Field(default_factory=dict)
    hidden: bool = False
    hint: Optional[str] = None


class RewardSchema(BaseModel):
    """Esquema para recompensas de fragmento"""
    points: Optional[float] = 0
    items: Optional[List[str]] = Field(default_factory=list)
    achievements: Optional[List[str]] = Field(default_factory=list)
    lore_pieces: Optional[List[str]] = Field(default_factory=list)
    unlock_fragments: Optional[List[str]] = Field(default_factory=list)


class FragmentSchema(BaseModel):
    """Esquema para un fragmento narrativo completo"""
    id: str
    type: str = "story"  # story, decision, reward, checkpoint, ending
    
    # Contenido
    title: Optional[str] = None
    narrator_text: str  # Texto de Lucien
    atmosphere_text: Optional[str] = None  # Ambientación
    
    # Navegación
    next_fragment: Optional[str] = None
    choices: Optional[List[ChoiceSchema]] = Field(default_factory=list)
    
    # Recompensas y requisitos
    rewards: Optional[RewardSchema] = None
    requirements: Optional[Dict[str, Any]] = Field(default_factory=dict)
    vip_only: bool = False
    
    # Media
    image_url: Optional[str] = None
    audio_url: Optional[str] = None
    
    # Metadata
    chapter: int = 1
    scene: int = 1
    tags: Optional[List[str]] = Field(default_factory=list)
    is_hidden: bool = False
    unlock_hint: Optional[str] = None


class StorySchema(BaseModel):
    """Esquema para una historia completa"""
    id: str
    title: str
    description: str
    author: str = "Diana"
    version: str = "1.0.0"
    
    # Configuración
    starting_fragment: str
    chapters: Dict[int, Dict[str, Any]]  # {1: {title, description, fragments}}
    
    # Fragmentos
    fragments: Dict[str, FragmentSchema]
    
    # Metadata
    total_fragments: int
    total_decisions: int
    estimated_duration: str  # "2-3 horas"
    content_warnings: Optional[List[str]] = Field(default_factory=list)
    
    # Requisitos globales
    min_level: int = 1
    requires_vip: bool = False
    
    # Estadísticas
    created_at: datetime
    updated_at: datetime
  
