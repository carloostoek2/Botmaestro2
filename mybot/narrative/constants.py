"""
Constantes del sistema narrativo
"""

# Personajes principales
CHARACTERS = {
    "lucien": {
        "name": "Lucien",
        "title": "El Mayordomo",
        "emoji": "🕴️",
        "color": "#8B4513"  # Saddle Brown
    },
    "diana": {
        "name": "Diana",
        "title": "La Creadora",
        "emoji": "🌸",
        "color": "#FF69B4"  # Hot Pink
    }
}

# Límites del sistema
MAX_CHOICES_PER_FRAGMENT = 6
MAX_FRAGMENT_LENGTH = 4000  # Caracteres
MAX_ACTIVE_STORIES = 2  # Free + VIP

# Configuración de navegación
BACK_BUTTON_ENABLED = True
SAVE_CHECKPOINTS = True
AUTO_SAVE_INTERVAL = 5  # Fragmentos

# Efectos y transiciones
TRANSITION_EFFECTS = {
    "fade": "Desvanecer",
    "slide": "Deslizar",
    "instant": "Instantáneo"
}

# Plantillas de mensaje
MESSAGE_TEMPLATES = {
    "narrator_prefix": "🕯️ *{character} susurra:*\n\n",
    "atmosphere_prefix": "_🌙 {text}_\n\n",
    "choice_prefix": "¿Qué decides?\n\n",
    "reward_prefix": "✨ *Has obtenido:*\n",
    "locked_fragment": "🔒 *Este fragmento está bloqueado*\n\n{hint}",
    "story_complete": "🏆 *Has completado esta rama narrativa*\n\nCompletitud: {percent}%",
}

# Configuración de caché
CACHE_TTL = 3600  # 1 hora
PRELOAD_FRAGMENTS = 3  # Precargar próximos N fragmentos

# Puntos por acciones narrativas
NARRATIVE_POINTS = {
    "fragment_read": 0.5,
    "decision_made": 1.0,
    "chapter_complete": 5.0,
    "story_complete": 25.0,
    "hidden_found": 10.0
}

# Estados de narrativa para el menú
NARRATIVE_MENU_STATES = {
    "narrative_main": "Menú Principal Narrativo",
    "narrative_story": "Historia Activa",
    "narrative_decision": "Punto de Decisión",
    "narrative_history": "Historial de Decisiones",
    "narrative_achievements": "Logros Narrativos"
}
