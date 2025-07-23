"""
Decoradores para verificaciones comunes en el sistema narrativo
"""
import functools
from typing import Callable, Any
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from utils.user_roles import is_vip_active
from .models import UserNarrativeState


def ensure_narrative_state(func: Callable) -> Callable:
    """Asegura que el usuario tenga un estado narrativo inicializado"""
    @functools.wraps(func)
    async def wrapper(event: Any, session: AsyncSession, *args, **kwargs):
        # Determinar user_id según el tipo de evento
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
        else:
            return await func(event, session, *args, **kwargs)
        
        # Verificar y crear estado si no existe
        state = await session.get(UserNarrativeState, user_id)
        if not state:
            # REF: [narrative/story_manager.py] get_starting_fragment
            state = UserNarrativeState(
                user_id=user_id,
                current_fragment_id=None,  # Se establecerá al iniciar historia
                current_chapter=1,
                fragments_visited=[],
                story_flags={
                    "first_time": True,
                    "lucien_relationship": 0,
                    "diana_relationship": 0
                }
            )
            session.add(state)
            await session.commit()
        
        return await func(event, session, *args, **kwargs)
    
    return wrapper


def require_vip_for_story(func: Callable) -> Callable:
    """Requiere VIP activo para historias VIP"""
    @functools.wraps(func)
    async def wrapper(event: Any, session: AsyncSession, *args, **kwargs):
        # Obtener user_id
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
        else:
            return await func(event, session, *args, **kwargs)
        
        # Verificar si está intentando acceder a historia VIP
        state = await session.get(UserNarrativeState, user_id)
        if state and state.active_story == "vip":
            # REF: [utils/user_roles.py] is_vip_active
            if not await is_vip_active(user_id, session):
                if isinstance(event, CallbackQuery):
                    await event.answer(
                        "🔒 Esta historia requiere suscripción VIP activa",
                        show_alert=True
                    )
                    return
                else:
                    await event.answer(
                        "🔒 Esta historia requiere suscripción VIP activa\n\n"
                        "Usa /vip para más información."
                    )
                    return
        
        return await func(event, session, *args, **kwargs)
    
    return wrapper


def track_narrative_action(action_type: str, points: float = 0):
    """Registra acciones narrativas para estadísticas"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(event: Any, session: AsyncSession, *args, **kwargs):
            result = await func(event, session, *args, **kwargs)
            
            # Registrar acción después de ejecutar
            if isinstance(event, (Message, CallbackQuery)):
                user_id = event.from_user.id
                
                # Aquí podrías registrar métricas, dar puntos, etc.
                # Por ahora solo logueamos
                from logging import getLogger
                logger = getLogger(__name__)
                logger.info(f"Narrative action: {action_type} by user {user_id}")
                
                # REF: [database/models.py] User - Dar puntos si corresponde
                if points > 0:
                    user = await session.get(User, user_id)
                    if user:
                        user.points += points
                        await session.commit()
            
            return result
        
        return wrapper
    return decorator
  
