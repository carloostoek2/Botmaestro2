from aiogram import Router, F
from aiogram.types import Message
from utils.message_safety import safe_answer, safe_edit, safe_send_message, safe_edit_message_text
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import Command
from sqlalchemy.future import select
from database.setup import get_session
from database.models import UserLorePiece, LorePiece
from database.hint_combination import HintCombination
try:
    from narrativa import desbloquear_pista
except ImportError:
    # Fallback function
    async def desbloquear_pista(bot, user_id, pista_code):
        await bot.send_message(user_id, f"🎩 Has desbloqueado: {pista_code}")

router = Router()

class CombinationFSM(StatesGroup):
    waiting_for_hint_codes = State()

@router.message(Command("combinar_pistas"))
async def iniciar_combinacion(message: Message, state: FSMContext):
    await safe_answer(message, "Ingrese los códigos de las pistas que desea combinar separados por coma. Ejemplo: 2,4,7")
    await state.set_state(CombinationFSM.waiting_for_hint_codes)

@router.message(CombinationFSM.waiting_for_hint_codes)
async def procesar_combinacion(message: Message, state: FSMContext):
    session_factory = await get_session()
    async with session_factory() as session:
        user_id = message.from_user.id
        user_input = message.text.replace(" ", "")
        user_hints = sorted(user_input.split(","))
    
        result = await session.execute(select(HintCombination))
        combinaciones = result.scalars().all()
    
        for combinacion in combinaciones:
            pistas_requeridas = sorted(combinacion.required_hints.split(","))
            if user_hints == pistas_requeridas:
                await desbloquear_pista(bot=message.bot, user_id=user_id, pista_code=combinacion.reward_code)
                await safe_answer(message, "\u00a1Combinaci\u00f3n correcta! Has desbloqueado una nueva pista.")
                await state.clear()
                return
    
        await safe_answer(message, "Combinaci\u00f3n incorrecta. Verifica tus pistas e intenta nuevamente.")
        await state.clear()
