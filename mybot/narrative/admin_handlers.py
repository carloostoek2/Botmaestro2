"""
Handlers administrativos para el sistema narrativo
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from utils.user_roles import is_admin
from utils.menu_manager import menu_manager
from .models import StoryFragment, UserNarrativeState, UserDecision, NarrativeMetrics
from .narrative_service import NarrativeService
from .keyboards import NarrativeKeyboards

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("narrative_admin"))
async def narrative_admin_command(message: Message, session: AsyncSession):
    """Comando de administración para el sistema narrativo"""
    if not await is_admin(message.from_user.id, session):
        await message.answer("⛔ Acceso denegado")
        return
    
    service = NarrativeService(session)
    
    # Estadísticas generales
    total_users_query = select(func.count(UserNarrativeState.user_id))
    total_users_result = await session.execute(total_users_query)
    total_users = total_users_result.scalar() or 0
    
    active_users_query = select(func.count(UserNarrativeState.user_id)).where(
        UserNarrativeState.current_fragment_id.isnot(None)
    )
    active_users_result = await session.execute(active_users_query)
    active_users = active_users_result.scalar() or 0
    
    text = (
        "🎭 **Panel Admin - Sistema Narrativo**\n\n"
        f"👥 **Usuarios Totales**: {total_users}\n"
        f"🎮 **Usuarios Activos**: {active_users}\n"
        f"📚 **Historias Cargadas**: {len(service.story_manager.stories)}\n\n"
        "Selecciona una acción:"
    )
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📊 Estadísticas", callback_data="nadmin_stats"),
        InlineKeyboardButton(text="👥 Usuarios", callback_data="nadmin_users")
    )
    builder.row(
        InlineKeyboardButton(text="📖 Historias", callback_data="nadmin_stories"),
        InlineKeyboardButton(text="🎭 Fragmentos", callback_data="nadmin_fragments")
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Recargar Historias", callback_data="nadmin_reload"),
        InlineKeyboardButton(text="🧪 Modo Test", callback_data="nadmin_test")
    )
    
    await menu_manager.show_menu(
        message,
        text,
        builder.as_markup(),
        session,
        menu_state="narrative_admin_main"
    )
