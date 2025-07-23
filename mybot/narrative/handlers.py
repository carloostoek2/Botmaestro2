"""
Handlers principales del sistema narrativo
"""
import logging
from typing import Optional
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from utils.menu_manager import menu_manager
from utils.user_roles import is_vip_active
from utils.text_utils import sanitize_text
from database.models import User
from .narrative_service import NarrativeService
from .decorators import ensure_narrative_state, require_vip_for_story, track_narrative_action
from .keyboards import NarrativeKeyboards
from .constants import MESSAGE_TEMPLATES, CHARACTERS
from .schemas import FragmentSchema

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("historia"))
@ensure_narrative_state
async def narrative_command(message: Message, session: AsyncSession):
    """Comando principal para acceder al sistema narrativo"""
    user_id = message.from_user.id
    service = NarrativeService(session)
    
    # Verificar si tiene historia activa
    state = await service.get_user_state(user_id)
    has_active_story = state and state.current_fragment_id is not None
    
    # Verificar si es VIP
    is_vip = await is_vip_active(user_id, session)
    
    # Construir mensaje de bienvenida
    text = (
        f"{CHARACTERS['lucien']['emoji']} *Bienvenido al Reino de las Historias*\n\n"
        f"_{CHARACTERS['lucien']['name']} hace una reverencia elegante_\n\n"
        "Mi nombre es Lucien, seré tu guía en este viaje narrativo. "
        "Cada decisión que tomes moldeará tu destino y revelará los secretos "
        "que Diana ha tejido para ti.\n\n"
    )
    
    if has_active_story:
        text += f"📖 Veo que ya has comenzado tu viaje. ¿Deseas continuar donde lo dejaste?"
    else:
        text += "🌟 ¿Estás listo para comenzar tu primera aventura?"
    
    keyboard = NarrativeKeyboards.main_menu(has_active_story, is_vip)
    
    await menu_manager.show_menu(
        message,
        text,
        keyboard,
        session,
        menu_state="narrative_main",
        delete_origin_message=True
    )


@router.callback_query(F.data == "narrative_menu")
@ensure_narrative_state
async def narrative_menu(callback: CallbackQuery, session: AsyncSession):
    """Muestra el menú principal de narrativa"""
    user_id = callback.from_user.id
    service = NarrativeService(session)
    
    state = await service.get_user_state(user_id)
    has_active_story = state and state.current_fragment_id is not None
    is_vip = await is_vip_active(user_id, session)
    
    text = (
        f"{CHARACTERS['lucien']['emoji']} *Sistema Narrativo*\n\n"
        "¿Qué deseas hacer?"
    )
    
    keyboard = NarrativeKeyboards.main_menu(has_active_story, is_vip)
    
    await menu_manager.update_menu(
        callback,
        text,
        keyboard,
        session,
        menu_state="narrative_main"
    )
    await callback.answer()


@router.callback_query(F.data == "narrative_continue")
@ensure_narrative_state
@require_vip_for_story
@track_narrative_action("continue_story", 0)
async def continue_story(callback: CallbackQuery, session: AsyncSession):
    """Continúa la historia donde se quedó"""
    user_id = callback.from_user.id
    service = NarrativeService(session)
    
    fragment = await service.get_current_fragment(user_id)
    if not fragment:
        await callback.answer("No tienes una historia activa", show_alert=True)
        return
    
    # Construir y mostrar el fragmento
    await _display_fragment(callback, fragment, service, session)
    await callback.answer()


@router.callback_query(F.data == "narrative_new_story")
@ensure_narrative_state
async def new_story_menu(callback: CallbackQuery, session: AsyncSession):
    """Muestra el menú de selección de historia"""
    user_id = callback.from_user.id
    is_vip = await is_vip_active(user_id, session)
    
    text = (
        f"{CHARACTERS['diana']['emoji']} *Elige tu Historia*\n\n"
        "Cada camino revela diferentes secretos y desafíos. "
        "¿Cuál llamará tu atención?\n\n"
        "📚 *Historias Disponibles:*"
    )
    
    keyboard = NarrativeKeyboards.story_selection(is_vip)
    
    await menu_manager.update_menu(
        callback,
        text,
        keyboard,
        session,
        menu_state="narrative_story_selection"
    )
    await callback.answer()


@router.callback_query(F.data == "narrative_select_free")
@ensure_narrative_state
@track_narrative_action("start_free_story", 1.0)
async def select_free_story(callback: CallbackQuery, session: AsyncSession):
    """Inicia la historia gratuita"""
    user_id = callback.from_user.id
    service = NarrativeService(session)
    
    # Confirmar inicio
    state = await service.get_user_state(user_id)
    if state and state.current_fragment_id:
        # Ya tiene historia activa
        await callback.answer(
            "Ya tienes una historia en progreso. Úsala desde el menú principal.",
            show_alert=True
        )
        return
    
    # Iniciar historia
    success, message, fragment = await service.start_story(user_id, "free")
    
    if not success:
        await callback.answer(message, show_alert=True)
        return
    
    # Mostrar fragmento inicial
    await _display_fragment(callback, fragment, service, session)
    await callback.answer("¡Historia iniciada!")


@router.callback_query(F.data == "narrative_select_vip")
@ensure_narrative_state
@require_vip_for_story
@track_narrative_action("start_vip_story", 2.0)
async def select_vip_story(callback: CallbackQuery, session: AsyncSession):
    """Inicia la historia VIP"""
    user_id = callback.from_user.id
    service = NarrativeService(session)
    
    # Verificar VIP
    if not await is_vip_active(user_id, session):
        await callback.answer("Necesitas suscripción VIP activa", show_alert=True)
        return
    
    # Confirmar inicio
    state = await service.get_user_state(user_id)
    if state and state.current_fragment_id and state.active_story == "vip":
        await callback.answer("Ya estás en la historia VIP", show_alert=True)
        return
    
    # Iniciar historia VIP
    success, message, fragment = await service.start_story(user_id, "vip")
    
    if not success:
        await callback.answer(message, show_alert=True)
        return
    
    await _display_fragment(callback, fragment, service, session)
    await callback.answer("¡Historia VIP iniciada!")


@router.callback_query(F.data.startswith("narrative_choice_"))
@ensure_narrative_state
@require_vip_for_story
@track_narrative_action("make_choice", 1.0)
async def process_choice(callback: CallbackQuery, session: AsyncSession):
    """Procesa una elección del usuario"""
    user_id = callback.from_user.id
    choice_id = callback.data.split("_")[-1]
    
    service = NarrativeService(session)
    
    # Hacer la elección
    success, message, fragment = await service.make_choice(user_id, choice_id)
    
    if not success:
        # Mostrar requisitos faltantes
        if "requisitos" in message:
            keyboard = NarrativeKeyboards.locked_fragment(
                missing_requirements=message.split("\n")[1:],
                has_hint=False
            )
            await menu_manager.update_menu(
                callback,
                f"🔒 *Opción Bloqueada*\n\n{message}",
                keyboard,
                session,
                menu_state="narrative_locked"
            )
        else:
            await callback.answer(message, show_alert=True)
        return
    
    # Mostrar nuevo fragmento
    await _display_fragment(callback, fragment, service, session)
    
    # Verificar logros
    achievements = await service.check_achievements(user_id)
    if achievements:
        achievement_text = "\n".join([f"🏆 {a.name}" for a in achievements])
        await callback.answer(f"¡Nuevos logros!\n{achievement_text}", show_alert=True)
    else:
        await callback.answer()


@router.callback_query(F.data.startswith("narrative_next_"))
@ensure_narrative_state
@require_vip_for_story
@track_narrative_action("continue_fragment", 0.5)
async def next_fragment(callback: CallbackQuery, session: AsyncSession):
    """Avanza al siguiente fragmento"""
    user_id = callback.from_user.id
    service = NarrativeService(session)
    
    success, message, fragment = await service.navigate_next(user_id)
    
    if not success:
        await callback.answer(message, show_alert=True)
        return
    
    await _display_fragment(callback, fragment, service, session)
    await callback.answer()


@router.callback_query(F.data == "narrative_back")
@ensure_narrative_state
async def go_back(callback: CallbackQuery, session: AsyncSession):
    """Retrocede al fragmento anterior"""
    user_id = callback.from_user.id
    service = NarrativeService(session)
    
    success, message, fragment = await service.go_back(user_id)
    
    if not success:
        await callback.answer(message, show_alert=True)
        return
    
    await _display_fragment(callback, fragment, service, session)
    await callback.answer("Has retrocedido")


# Funciones auxiliares

async def _display_fragment(
    callback: CallbackQuery,
    fragment: Optional[FragmentSchema],
    service: NarrativeService,
    session: AsyncSession
) -> None:
    """Muestra un fragmento narrativo formateado"""
    if not fragment:
        await callback.answer("Error al cargar el fragmento", show_alert=True)
        return
    
    user_id = callback.from_user.id
    state = await service.get_user_state(user_id)
    
    # Construir texto del fragmento
    text = ""
    
    # Título si existe
    if fragment.title:
        text += f"*{fragment.title}*\n\n"
    
    # Prefijo del narrador
    text += MESSAGE_TEMPLATES["narrator_prefix"].format(character=CHARACTERS['lucien']['name'])
    text += f"{fragment.narrator_text}\n\n"
    
    # Atmósfera si existe
    if fragment.atmosphere_text:
        text += MESSAGE_TEMPLATES["atmosphere_prefix"].format(text=fragment.atmosphere_text)
    
    # Prefijo de decisión si aplica
    if fragment.type == "decision" and fragment.choices:
        text += MESSAGE_TEMPLATES["choice_prefix"]
    
    # Información de capítulo
    chapter_info = {
        "current": fragment.chapter,
        "total": 6  # TODO: Obtener del story manager
    }
    
    # Verificar si puede retroceder
    can_go_back = len(state.fragments_visited) > 1 if state else False
    
    # Generar teclado apropiado
    if fragment.type == "ending":
        # Es un final
        completion = state.story_completion_percent if state else 0
        keyboard = NarrativeKeyboards.story_ending(
            ending_type="default",
            completion_percent=completion,
            has_more_endings=completion < 100
        )
    else:
        # Fragmento normal
        keyboard = NarrativeKeyboards.story_fragment(
            fragment=fragment,
            can_go_back=can_go_back,
            chapter_info=chapter_info
        )
    
    # Actualizar menú
    await menu_manager.update_menu(
        callback,
        sanitize_text(text),
        keyboard,
        session,
        menu_state=f"narrative_fragment_{fragment.id}"
    )


# Función auxiliar eliminada - se usa la importada desde utils.user_roles
