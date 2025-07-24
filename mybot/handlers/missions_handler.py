from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from services.mission_service import MissionService
from database.models import User
import logging

logger = logging.getLogger(__name__)

router = Router()

@router.callback_query(F.data == "misiones_disponibles")
async def show_available_missions(callback: CallbackQuery, session: AsyncSession):
    """Muestra la lista de misiones disponibles para el usuario."""
    try:
        await callback.answer("Cargando misiones...", show_alert=False)

        mission_service = MissionService(session)
        missions = await mission_service.get_active_missions(user_id=callback.from_user.id)

        if not missions:
            missions_text = "No hay misiones disponibles actualmente."
        else:
            user = await session.get(User, callback.from_user.id)
            missions_text = "Aquí están tus misiones actuales:\n\n"
            for m in missions:
                completed, _ = await mission_service.check_mission_completion_status(user, m)
                status = "✅" if completed else "❌"
                missions_text += f"• {m.name} ({m.reward_points} pts) {status}\n"

        await callback.message.edit_text(missions_text)
    except Exception as e:
        logger.error(f"Error showing missions: {e}")
        await callback.message.edit_text("❌ Error al cargar las misiones. Intenta nuevamente.")
