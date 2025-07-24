import random
from aiogram import Bot

lucien_mensajes = [
    "Sabías que los flamencos pueden dormir mientras están de pie? Lucien aprueba.",
    "Lucien dice: No te fíes de los patos, ellos siempre están tramando algo.",
    "Hoy es un gran día para acumular pistas, o para no hacer nada. Tú decides.",
    "Cada reacción cuenta, incluso la tuya, humano.",
    "Lucien quiere saber: ¿cuántos besitos has coleccionado hoy?",
    "Datos absurdos: Las vacas pueden subir escaleras pero no bajarlas.",
    "Lucien dice: Sigue reaccionando, el Diván te observa.",
    "A veces un besito abre más puertas que mil llaves.",
    "Lucien aprobó tu reacción con su sello de sarcasmo.",
    "¿Ya tomaste agua? Lucien está pendiente de ti."
]

user_last_message = {}

async def enviar_notificacion_gamificada(bot: Bot, user_id: int):
    mensaje = random.choice(lucien_mensajes)

    while user_last_message.get(user_id) == mensaje and len(lucien_mensajes) > 1:
        mensaje = random.choice(lucien_mensajes)

    user_last_message[user_id] = mensaje
    await bot.send_message(user_id, f"💬 {mensaje}")


async def send_narrative_notification(bot: Bot, user_id: int, notification_type: str, context: dict = None):
    """
    Envía notificaciones narrativas mejoradas
    
    Args:
        bot: Bot instance
        user_id: ID del usuario
        notification_type: Tipo de notificación ('new_hint', 'achievement', etc.)
        context: Contexto adicional con información específica
    """
    if context is None:
        context = {}
    
    if notification_type == "new_hint":
        pista_code = context.get('hint_code', 'Desconocida')
        origen = context.get('source', 'Sistema')
        
        mensajes = [
            f"🎩 Lucien: Una nueva pieza ha caído en tus manos... {pista_code}. No la pierdas.",
            f"🎩 Lucien: {pista_code} se ha revelado para ti. ¿Podrás entender su verdadero valor?",
            f"🎩 Lucien: Has desbloqueado algo nuevo. {pista_code}... interesante.",
            f"🎩 Lucien: El Diván susurra: {pista_code} es ahora tuyo.",
            f"🎩 Lucien: {pista_code} proviene de {origen}. ¿Accidente o destino?"
        ]
    elif notification_type == "achievement":
        achievement_name = context.get('achievement_name', 'Logro desconocido')
        mensajes = [
            f"🏆 Lucien: Has desbloqueado un logro: {achievement_name}. Diana está impresionada.",
            f"🏆 Lucien: {achievement_name}... un logro digno de reconocimiento.",
        ]
    else:
        # Fallback para compatibilidad con código anterior
        pista_code = str(notification_type)  # Asumir que es el código de pista
        origen = context.get('source', 'Sistema')
        mensajes = [
            f"🎩 Lucien: Una nueva pieza ha caído en tus manos... {pista_code}. No la pierdas.",
            f"🎩 Lucien: {pista_code} se ha revelado para ti. ¿Podrás entender su verdadero valor?",
        ]

    mensaje = random.choice(mensajes)
    await bot.send_message(user_id, mensaje)

# Función de compatibilidad para código existente
async def send_narrative_notification_legacy(bot: Bot, user_id: int, pista_code: str, origen: str = "Sistema"):
    """Función de compatibilidad para el código existente"""
    mensajes = [
        f"🎩 Lucien: Una nueva pieza ha caído en tus manos... {pista_code}. No la pierdas.",
        f"🎩 Lucien: {pista_code} se ha revelado para ti. ¿Podrás entender su verdadero valor?",
        f"🎩 Lucien: Has desbloqueado algo nuevo. {pista_code}... interesante.",
        f"🎩 Lucien: El Diván susurra: {pista_code} es ahora tuyo.",
        f"🎩 Lucien: {pista_code} proviene de {origen}. ¿Accidente o destino?"
    ]

    mensaje = random.choice(mensajes)
    await bot.send_message(user_id, mensaje)
