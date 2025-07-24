"""
Menu creators for specific menu types.
Separated to avoid circular imports and improve maintainability.
"""
from __future__ import annotations
from typing import Tuple
from aiogram.types import InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User
try:
    from utils.keyboard_utils import (
        get_profile_keyboard,
        get_missions_keyboard,
        get_reward_keyboard,
        get_ranking_keyboard
    )
    from utils.message_utils import get_profile_message, get_ranking_message
except ImportError:
    # Fallback keyboards
    from keyboards.common import get_back_kb
    
    def get_profile_keyboard():
        return get_back_kb("main")
    
    def get_missions_keyboard(missions):
        return get_back_kb("main")
    
    def get_reward_keyboard(rewards, claimed_ids):
        return get_back_kb("main")
    
    def get_ranking_keyboard():
        return get_back_kb("main")
    
    async def get_profile_message(user, missions, session):
        return f"👤 **Perfil de {user.first_name or 'Usuario'}**\n\nPuntos: {user.points}\nNivel: {user.level}"
    
    async def get_ranking_message(users, viewer_id):
        return "🏆 **Ranking**\n\nFuncionalidad en desarrollo..."

from services.mission_service import MissionService
from services.reward_service import RewardService
from services.point_service import PointService
try:
    from keyboards.auction_kb import get_auction_main_kb
except ImportError:
    from keyboards.common import get_back_kb
    def get_auction_main_kb():
        return get_back_kb("main")

async def create_profile_menu(user_id: int, session: AsyncSession) -> Tuple[str, InlineKeyboardMarkup]:
    """Create the profile menu for a user."""
    user = await session.get(User, user_id)
    if not user:
        return (
            "❌ **Perfil No Encontrado**\n\n"
            "No se pudo cargar tu perfil. Usa /start para registrarte.",
            get_profile_keyboard()
        )
    
    mission_service = MissionService(session)
    active_missions = await mission_service.get_active_missions(user_id=user_id)
    
    profile_text = await get_profile_message(user, active_missions, session)
    return profile_text, get_profile_keyboard()

async def create_missions_menu(user_id: int, session: AsyncSession) -> Tuple[str, InlineKeyboardMarkup]:
    """Create the missions menu for a user."""
    mission_service = MissionService(session)
    active_missions = await mission_service.get_active_missions(user_id=user_id)
    
    if not active_missions:
        text = (
            "🎯 **Misiones Disponibles**\n\n"
            "No hay misiones activas en este momento.\n"
            "¡Mantente atento! Pronto habrá nuevos desafíos."
        )
    else:
        text = (
            "🎯 **Misiones Disponibles**\n\n"
            "Completa estas misiones para ganar puntos y desbloquear recompensas:"
        )
    
    return text, get_missions_keyboard(active_missions)

async def create_rewards_menu(user_id: int, session: AsyncSession) -> Tuple[str, InlineKeyboardMarkup]:
    """Create the rewards menu for a user."""
    reward_service = RewardService(session)
    user = await session.get(User, user_id)
    user_points = int(user.points) if user else 0
    
    available_rewards = await reward_service.get_available_rewards(user_points)
    claimed_ids = await reward_service.get_claimed_reward_ids(user_id)
    
    if not available_rewards:
        text = (
            "🎁 **Recompensas Disponibles**\n\n"
            "No hay recompensas disponibles con tus puntos actuales.\n"
            "¡Sigue participando para desbloquear más recompensas!"
        )
    else:
        text = (
            f"🎁 **Recompensas Disponibles**\n\n"
            f"Tienes **{user_points} puntos** para canjear.\n"
            f"Selecciona una recompensa para reclamarla:"
        )
    
    return text, get_reward_keyboard(available_rewards, set(claimed_ids))

async def create_auction_menu(user_id: int, session: AsyncSession) -> Tuple[str, InlineKeyboardMarkup]:
    """Create the auction menu for a user."""
    text = (
        "🏛️ **Subastas en Tiempo Real**\n\n"
        "Participa en subastas exclusivas y gana premios únicos.\n"
        "¡Usa tus puntos para pujar por increíbles recompensas!"
    )
    
    return text, get_auction_main_kb()

async def create_ranking_menu(user_id: int, session: AsyncSession) -> Tuple[str, InlineKeyboardMarkup]:
    """Create the ranking menu for a user."""
    point_service = PointService(session)
    top_users = await point_service.get_top_users(limit=10)
    
    ranking_text = await get_ranking_message(top_users, user_id)
    return ranking_text, get_ranking_keyboard()