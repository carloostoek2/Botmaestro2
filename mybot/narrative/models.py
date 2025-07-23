"""
Modelos de base de datos para el sistema narrativo
"""
from sqlalchemy import (
    Column, Integer, String, BigInteger, DateTime, Boolean,
    JSON, Text, ForeignKey, Float, Enum, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.base import Base
import enum


class FragmentType(enum.Enum):
    """Tipos de fragmentos narrativos"""
    STORY = "story"          # Fragmento de historia normal
    DECISION = "decision"    # Punto de decisión
    REWARD = "reward"        # Fragmento que otorga recompensa
    CHECKPOINT = "checkpoint" # Punto de guardado automático
    ENDING = "ending"        # Final de rama narrativa


class StoryFragment(Base):
    """Fragmentos individuales de la narrativa"""
    __tablename__ = "story_fragments"
    
    id = Column(String, primary_key=True)  # ID único del fragmento
    story_id = Column(String, nullable=False)  # ID de la historia (free/vip)
    fragment_type = Column(Enum(FragmentType), default=FragmentType.STORY)
    
    # Contenido
    title = Column(String, nullable=True)
    narrator_text = Column(Text, nullable=False)  # Texto de Lucien
    atmosphere_text = Column(Text, nullable=True)  # Descripción ambiental
    
    # Decisiones (si es tipo DECISION)
    choices = Column(JSON, default=list)  # Lista de {id, text, next_fragment, requirements}
    
    # Navegación
    next_fragment = Column(String, nullable=True)  # Siguiente fragmento por defecto
    previous_fragment = Column(String, nullable=True)  # Para permitir retroceso
    
    # Recompensas y efectos
    rewards = Column(JSON, default=dict)  # {points: 10, items: [], achievements: []}
    effects = Column(JSON, default=dict)  # Efectos especiales o flags
    
    # Requisitos para acceder
    requirements = Column(JSON, default=dict)  # {level: 5, items: [], achievements: []}
    vip_only = Column(Boolean, default=False)
    
    # Media
    image_url = Column(String, nullable=True)
    audio_url = Column(String, nullable=True)
    
    # Metadata
    chapter = Column(Integer, default=1)
    scene = Column(Integer, default=1)
    is_hidden = Column(Boolean, default=False)  # Fragmento oculto/secreto
    unlock_hint = Column(Text, nullable=True)  # Pista para desbloquear
    
    # Control
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relaciones
    decisions = relationship("UserDecision", back_populates="fragment", lazy="selectin")
    
    # REF: [database/models.py] Achievement - Relación con logros
    unlocks_achievement_id = Column(String, ForeignKey("achievements.id"), nullable=True)
    achievement_link = relationship("Achievement", back_populates="story_fragments")


class UserNarrativeState(Base):
    """Estado narrativo actual de cada usuario"""
    __tablename__ = "user_narrative_states"
    
    user_id = Column(BigInteger, ForeignKey("users.id"), primary_key=True)
    current_fragment_id = Column(String, ForeignKey("story_fragments.id"), nullable=True)
    current_chapter = Column(Integer, default=1)
    
    # Progreso
    fragments_visited = Column(JSON, default=list)  # Lista de IDs visitados
    total_decisions_made = Column(Integer, default=0)
    story_completion_percent = Column(Float, default=0.0)
    
    # Estado de historias
    free_story_unlocked = Column(Boolean, default=True)
    vip_story_unlocked = Column(Boolean, default=False)
    active_story = Column(String, default="free")  # free/vip
    
    # Flags y variables narrativas
    story_flags = Column(JSON, default=dict)  # Variables de estado personalizadas
    relationship_scores = Column(JSON, default=dict)  # {lucien: 0, diana: 0}
    
    # Timestamps
    started_at = Column(DateTime, default=func.now())
    last_interaction_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime, nullable=True)
    
    # Relaciones
    user = relationship("User", back_populates="narrative_state")
    current_fragment = relationship("StoryFragment", foreign_keys=[current_fragment_id])
    decisions = relationship("UserDecision", back_populates="user_state", lazy="selectin")


class UserDecision(Base):
    """Registro de decisiones tomadas por usuarios"""
    __tablename__ = "user_decisions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    fragment_id = Column(String, ForeignKey("story_fragments.id"), nullable=False)
    choice_id = Column(String, nullable=False)  # ID de la opción elegida
    choice_text = Column(Text, nullable=False)  # Texto de la opción (para historial)
    
    # Contexto
    chapter = Column(Integer, nullable=False)
    made_at = Column(DateTime, default=func.now())
    
    # Efectos
    points_gained = Column(Float, default=0)
    items_gained = Column(JSON, default=list)
    flags_set = Column(JSON, default=dict)
    
    # Relaciones
    fragment = relationship("StoryFragment", back_populates="decisions")
    user_state = relationship("UserNarrativeState", back_populates="decisions")
    
    __table_args__ = (
        UniqueConstraint("user_id", "fragment_id", name="uix_user_fragment_decision"),
    )


class NarrativeMetrics(Base):
    """Métricas agregadas del sistema narrativo"""
    __tablename__ = "narrative_metrics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    fragment_id = Column(String, ForeignKey("story_fragments.id"), nullable=False)
    
    # Estadísticas
    times_visited = Column(Integer, default=0)
    choice_distribution = Column(JSON, default=dict)  # {choice_id: count}
    average_time_spent = Column(Float, default=0.0)
    skip_rate = Column(Float, default=0.0)
    
    # Popularidad
    rating_sum = Column(Integer, default=0)
    rating_count = Column(Integer, default=0)
    
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
