from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

router = Router()

@router.message(F.text == "🎒 Mochila")
async def handle_backpack_button(message: Message, session: AsyncSession):
    try:
        from backpack import mostrar_mochila_narrativa
        await mostrar_mochila_narrativa(message)
    except ImportError:
        await message.answer("🎒 **Mochila**\n\nFuncionalidad en desarrollo...")

@router.message(F.text == "💰 Billetera")
async def handle_wallet_button(message: Message, session: AsyncSession):
    await message.answer("💰 **Tu Billetera**\n\nFuncionalidad en desarrollo...")

@router.message(F.text == "🎯 Misiones")
async def handle_missions_button(message: Message, session: AsyncSession):
    from handlers.missions_handler import show_available_missions
    fake_callback = type("cb", (), {"from_user": message.from_user, "data": "misiones_disponibles", "message": message})
    await show_available_missions(fake_callback, session)

@router.message(F.text == "⚙️ Configuración")
async def handle_config_button(message: Message, session: AsyncSession):
    await message.answer("⚙️ **Configuración**\n\nOpciones de usuario...")

@router.message(F.text == "❓ Ayuda")
async def handle_help_button(message: Message, session: AsyncSession):
    await message.answer("❓ **Ayuda**\n\nGuía de uso del bot...")
