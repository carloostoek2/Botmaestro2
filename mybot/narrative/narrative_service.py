"""
Servicio principal de lógica de negocio para el sistema narrativo
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, Achievement, Mission, LorePiece
from .models import StoryFragment, UserNarrativeState, UserDecision, NarrativeMetrics
from .story_manager import StoryManager
from .schemas import FragmentSchema, ChoiceSchema
from .constants import NARRATIVE_POINTS, AUTO_SAVE_INTERVAL

logger = logging.getLogger(__name__)


class NarrativeService:
    """Servicio que maneja toda la lógica narrativa"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.story_manager = StoryManager()
    
    async def get_user_state(self, user_id: int) -> Optional[UserNarrativeState]:
        """Obtiene el estado narrativo de un usuario"""
        # REF: [narrative/models.py] UserNarrativeState
        return await self.session.get(UserNarrativeState, user_id)
    
    async def initialize_user_narrative(self, user_id: int) -> UserNarrativeState:
        """Inicializa el estado narrativo para un nuevo usuario"""
        state = UserNarrativeState(
            user_id=user_id,
            current_fragment_id=None,
            fragments_visited=[],
            story_flags={
                "first_time": True,
                "lucien_relationship": 0,
                "diana_relationship": 0,
                "secrets_discovered": 0
            },
            relationship_scores={
                "lucien": 0,
                "diana": 0
            }
        )
        self.session.add(state)
        await self.session.commit()
        return state
    
    async def start_story(self, user_id: int, story_id: str) -> Tuple[bool, str, Optional[FragmentSchema]]:
        """
        Inicia una nueva historia para el usuario
        Returns: (success, message, starting_fragment)
        """
        # Verificar que la historia existe
        story = self.story_manager.get_story(story_id)
        if not story:
            return False, "Historia no encontrada", None
        
        # Obtener o crear estado del usuario
        state = await self.get_user_state(user_id)
        if not state:
            state = await self.initialize_user_narrative(user_id)
        
        # Verificar acceso VIP si es necesario
        if story.requires_vip:
            user = await self.session.get(User, user_id)
            # REF: [database/models.py] User.role
            if user.role != "vip":
                return False, "Esta historia requiere suscripción VIP", None
        
        # Obtener fragmento inicial
        starting_fragment = self.story_manager.get_starting_fragment(story_id)
        if not starting_fragment:
            return False, "Error al cargar la historia", None
        
        # Actualizar estado del usuario
        state.active_story = story_id
        state.current_fragment_id = starting_fragment.id
        state.current_chapter = starting_fragment.chapter
        state.fragments_visited = [starting_fragment.id]
        state.story_completion_percent = 0.0
        
        # Marcar historia VIP como desbloqueada si corresponde
        if story_id == "vip":
            state.vip_story_unlocked = True
        
        await self.session.commit()
        
        # Registrar métrica
        await self._record_fragment_visit(starting_fragment.id)
        
        # Dar puntos por comenzar historia
        await self._give_narrative_points(user_id, NARRATIVE_POINTS["fragment_read"])
        
        return True, f"Historia '{story.title}' iniciada", starting_fragment
    
    async def get_current_fragment(self, user_id: int) -> Optional[FragmentSchema]:
        """Obtiene el fragmento actual del usuario"""
        state = await self.get_user_state(user_id)
        if not state or not state.current_fragment_id:
            return None
        
        return self.story_manager.get_fragment(state.active_story, state.current_fragment_id)
    
    async def make_choice(
        self, 
        user_id: int, 
        choice_id: str
    ) -> Tuple[bool, str, Optional[FragmentSchema]]:
        """
        Procesa una decisión del usuario
        Returns: (success, message, next_fragment)
        """
        state = await self.get_user_state(user_id)
        if not state:
            return False, "No tienes una historia activa", None
        
        # Obtener fragmento actual
        current_fragment = self.story_manager.get_fragment(
            state.active_story, 
            state.current_fragment_id
        )
        if not current_fragment:
            return False, "Error al cargar el fragmento actual", None
        
        # Validar la elección
        choice = self.story_manager.validate_choice(
            state.active_story,
            state.current_fragment_id,
            choice_id
        )
        if not choice:
            return False, "Opción no válida", None
        
        # Verificar requisitos de la elección
        user = await self.session.get(User, user_id)
        user_data = await self._get_user_data_for_requirements(user_id)
        can_choose, missing = self.story_manager.check_requirements(
            choice.requirements or {},
            user_data
        )
        
        if not can_choose:
            missing_text = "\n".join([f"• {req}" for req in missing])
            return False, f"No cumples los requisitos:\n{missing_text}", None
        
        # Obtener siguiente fragmento
        next_fragment = self.story_manager.get_fragment(
            state.active_story,
            choice.next_fragment
        )
        if not next_fragment:
            return False, "Error al cargar el siguiente fragmento", None
        
        # Registrar la decisión
        decision = UserDecision(
            user_id=user_id,
            fragment_id=state.current_fragment_id,
            choice_id=choice_id,
            choice_text=choice.text,
            chapter=current_fragment.chapter
        )
        
        # Aplicar efectos de la elección
        if choice.effects:
            await self._apply_choice_effects(user_id, choice.effects, decision)
        
        self.session.add(decision)
        
        # Actualizar estado del usuario
        state.current_fragment_id = next_fragment.id
        state.current_chapter = next_fragment.chapter
        if next_fragment.id not in state.fragments_visited:
            state.fragments_visited.append(next_fragment.id)
        state.total_decisions_made += 1
        state.last_interaction_at = datetime.utcnow()
        
        # Auto-save si es checkpoint
        if next_fragment.type == "checkpoint":
            await self._create_checkpoint(user_id, state)
        
        # Procesar recompensas del nuevo fragmento
        if next_fragment.rewards:
            await self._process_fragment_rewards(user_id, next_fragment)
        
        # Actualizar porcentaje de completitud
        state.story_completion_percent = self.story_manager.calculate_completion_percent(
            state.active_story,
            state.fragments_visited
        )
        
        await self.session.commit()
        
        # Métricas
        await self._record_fragment_visit(next_fragment.id)
        await self._record_choice_metric(state.current_fragment_id, choice_id)
        
        # Puntos por decisión
        await self._give_narrative_points(user_id, NARRATIVE_POINTS["decision_made"])
        
        return True, "Decisión registrada", next_fragment
    
    async def navigate_next(self, user_id: int) -> Tuple[bool, str, Optional[FragmentSchema]]:
        """Navega al siguiente fragmento (cuando no hay decisión)"""
        state = await self.get_user_state(user_id)
        if not state:
            return False, "No tienes una historia activa", None
        
        current_fragment = self.story_manager.get_fragment(
            state.active_story,
            state.current_fragment_id
        )
        
        if not current_fragment or not current_fragment.next_fragment:
            return False, "No hay siguiente fragmento", None
        
        next_fragment = self.story_manager.get_fragment(
            state.active_story,
            current_fragment.next_fragment
        )
        
        if not next_fragment:
            return False, "Error al cargar el siguiente fragmento", None
        
        # Verificar requisitos
        user_data = await self._get_user_data_for_requirements(user_id)
        can_access, missing = self.story_manager.check_requirements(
            next_fragment.requirements or {},
            user_data
        )
        
        if not can_access:
            missing_text = "\n".join([f"• {req}" for req in missing])
            return False, f"No cumples los requisitos:\n{missing_text}", None
        
        # Actualizar estado
        state.current_fragment_id = next_fragment.id
        state.current_chapter = next_fragment.chapter
        if next_fragment.id not in state.fragments_visited:
            state.fragments_visited.append(next_fragment.id)
        state.last_interaction_at = datetime.utcnow()
        
        # Procesar recompensas si las hay
        if next_fragment.rewards:
            await self._process_fragment_rewards(user_id, next_fragment)
        
        # Actualizar completitud
        state.story_completion_percent = self.story_manager.calculate_completion_percent(
            state.active_story,
            state.fragments_visited
        )
        
        await self.session.commit()
        
        # Métricas y puntos
        await self._record_fragment_visit(next_fragment.id)
        await self._give_narrative_points(user_id, NARRATIVE_POINTS["fragment_read"])
        
        return True, "Continuando historia", next_fragment
    
    async def go_back(self, user_id: int) -> Tuple[bool, str, Optional[FragmentSchema]]:
        """Retrocede al fragmento anterior"""
        state = await self.get_user_state(user_id)
        if not state or len(state.fragments_visited) <= 1:
            return False, "No puedes retroceder más", None
        
        # Encontrar el fragmento anterior en el historial
        current_index = state.fragments_visited.index(state.current_fragment_id)
        if current_index <= 0:
            return False, "Ya estás en el inicio", None
        
        previous_fragment_id = state.fragments_visited[current_index - 1]
        previous_fragment = self.story_manager.get_fragment(
            state.active_story,
            previous_fragment_id
        )
        
        if not previous_fragment:
            return False, "Error al cargar fragmento anterior", None
        
        # Actualizar estado (sin eliminar del historial)
        state.current_fragment_id = previous_fragment_id
        state.current_chapter = previous_fragment.chapter
        state.last_interaction_at = datetime.utcnow()
        
        await self.session.commit()
        
        return True, "Has retrocedido", previous_fragment
    
    async def get_user_history(
        self, 
        user_id: int,
        story_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Obtiene el historial de decisiones del usuario"""
        query = select(UserDecision).where(
            UserDecision.user_id == user_id
        ).order_by(UserDecision.made_at.desc())
        
        if story_id:
            # Filtrar por historia específica
            fragment_ids = list(self.story_manager._story_cache.get(story_id, {}).keys())
            query = query.where(UserDecision.fragment_id.in_(fragment_ids))
        
        query = query.limit(limit).offset(offset)
        result = await self.session.execute(query)
        decisions = result.scalars().all()
        
        history = []
        for decision in decisions:
            fragment = self.story_manager.get_fragment(
                story_id or "free",  # Asumir free si no se especifica
                decision.fragment_id
            )
            
            history.append({
                "fragment_title": fragment.title if fragment else "Desconocido",
                "choice_text": decision.choice_text,
                "made_at": decision.made_at,
                "chapter": decision.chapter,
                "points_gained": decision.points_gained,
                "items_gained": decision.items_gained
            })
        
        return history
    
    async def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Obtiene estadísticas narrativas del usuario"""
        state = await self.get_user_state(user_id)
        if not state:
            return {
                "has_started": False,
                "message": "Aún no has comenzado ninguna historia"
            }
        
        # Contar decisiones por historia
        decisions_query = select(UserDecision).where(
            UserDecision.user_id == user_id
        )
        result = await self.session.execute(decisions_query)
        all_decisions = result.scalars().all()
        
        # Calcular estadísticas
        total_points_from_narrative = sum(d.points_gained for d in all_decisions)
        unique_items = set()
        for d in all_decisions:
            if d.items_gained:
                unique_items.update(d.items_gained)
        
        # Encontrar finales alcanzados
        endings_reached = []
        for frag_id in state.fragments_visited:
            fragment = self.story_manager.get_fragment(state.active_story, frag_id)
            if fragment and fragment.type == "ending":
                endings_reached.append({
                    "title": fragment.title or "Final",
                    "chapter": fragment.chapter
                })
        
        return {
            "has_started": True,
            "active_story": state.active_story,
            "current_chapter": state.current_chapter,
            "completion_percent": state.story_completion_percent,
            "total_fragments_visited": len(state.fragments_visited),
            "total_decisions": state.total_decisions_made,
            "total_points_earned": total_points_from_narrative,
            "unique_items_found": len(unique_items),
            "endings_reached": endings_reached,
            "relationship_scores": state.relationship_scores,
            "time_played": (datetime.utcnow() - state.started_at).total_seconds() / 3600,  # horas
            "last_played": state.last_interaction_at
        }
    
    async def check_achievements(self, user_id: int) -> List[Achievement]:
        """Verifica y otorga logros narrativos"""
        state = await self.get_user_state(user_id)
        if not state:
            return []
        
        new_achievements = []
        
        # REF: [database/models.py] Achievement
        # Verificar logros por decisiones
        if state.total_decisions_made >= 10:
            achievement = await self._check_and_award_achievement(
                user_id, "narrative_10_decisions"
            )
            if achievement:
                new_achievements.append(achievement)
        
        if state.total_decisions_made >= 50:
            achievement = await self._check_and_award_achievement(
                user_id, "narrative_50_decisions"
            )
            if achievement:
                new_achievements.append(achievement)
        
        # Verificar logros por completitud
        if state.story_completion_percent >= 25:
            achievement = await self._check_and_award_achievement(
                user_id, "narrative_25_percent"
            )
            if achievement:
                new_achievements.append(achievement)
        
        if state.story_completion_percent >= 100:
            achievement = await self._check_and_award_achievement(
                user_id, f"narrative_complete_{state.active_story}"
            )
            if achievement:
                new_achievements.append(achievement)
        
        # Verificar logros por relaciones
        if state.relationship_scores.get("lucien", 0) >= 50:
            achievement = await self._check_and_award_achievement(
                user_id, "lucien_trusted"
            )
            if achievement:
                new_achievements.append(achievement)
        
        return new_achievements
    
    # Métodos privados auxiliares
    
    async def _get_user_data_for_requirements(self, user_id: int) -> Dict[str, Any]:
        """Obtiene datos del usuario necesarios para verificar requisitos"""
        user = await self.session.get(User, user_id)
        state = await self.get_user_state(user_id)
        
        # REF: [database/models.py] User, UserAchievement
        # Obtener logros del usuario
        from sqlalchemy import select
        from database.models import UserAchievement
        
        achievements_query = select(UserAchievement.achievement_id).where(
            UserAchievement.user_id == user_id
        )
        result = await self.session.execute(achievements_query)
        achievements = [a[0] for a in result.all()]
        
        # TODO: Integrar con sistema de mochila cuando esté disponible
        items = []  # Por ahora vacío
        
        return {
            "level": user.level if user else 1,
            "points": user.points if user else 0,
            "items": items,
            "achievements": achievements,
            "story_flags": state.story_flags if state else {}
        }
    
    async def _apply_choice_effects(
        self, 
        user_id: int,
        effects: Dict[str, Any],
        decision: UserDecision
    ) -> None:
        """Aplica los efectos de una elección"""
        state = await self.get_user_state(user_id)
        if not state:
            return
        
        # Aplicar cambios en relaciones
        if "relationships" in effects:
            for character, change in effects["relationships"].items():
                current = state.relationship_scores.get(character, 0)
                state.relationship_scores[character] = current + change
        
        # Aplicar flags de historia
        if "story_flags" in effects:
            state.story_flags.update(effects["story_flags"])
        
        # Registrar items ganados (para futura integración)
        if "items" in effects:
            decision.items_gained = effects["items"]
        
        # Registrar puntos ganados
        if "points" in effects:
            decision.points_gained = effects["points"]
            await self._give_narrative_points(user_id, effects["points"])
    
    async def _process_fragment_rewards(
        self,
        user_id: int,
        fragment: FragmentSchema
    ) -> None:
        """Procesa las recompensas de un fragmento"""
        if not fragment.rewards:
            return
        
        rewards = fragment.rewards
        
        # Dar puntos
        if hasattr(rewards, 'points') and rewards.points > 0:
            await self._give_narrative_points(user_id, rewards.points)
        
        # Otorgar logros
        if hasattr(rewards, 'achievements'):
            for achievement_id in rewards.achievements:
                await self._check_and_award_achievement(user_id, achievement_id)
        
        # REF: [database/models.py] LorePiece
        # Desbloquear pistas
        if hasattr(rewards, 'lore_pieces'):
            for lore_code in rewards.lore_pieces:
                await self._unlock_lore_piece(user_id, lore_code)
        
        # Desbloquear fragmentos ocultos
        if hasattr(rewards, 'unlock_fragments'):
            state = await self.get_user_state(user_id)
            if state:
                # Marcar fragmentos como descubiertos en story_flags
                if "discovered_fragments" not in state.story_flags:
                    state.story_flags["discovere
