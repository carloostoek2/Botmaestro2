"""
Teclados inline para el sistema narrativo
"""
from typing import List, Optional, Dict, Any
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .schemas import ChoiceSchema, FragmentSchema
from .constants import MAX_CHOICES_PER_FRAGMENT, BACK_BUTTON_ENABLED


class NarrativeKeyboards:
    """Generador de teclados para narrativa"""
    
    @staticmethod
    def main_menu(has_active_story: bool = False, is_vip: bool = False) -> InlineKeyboardMarkup:
        """Menú principal de narrativa"""
        builder = InlineKeyboardBuilder()
        
        if has_active_story:
            builder.row(
                InlineKeyboardButton(
                    text="📖 Continuar Historia",
                    callback_data="narrative_continue"
                )
            )
        
        builder.row(
            InlineKeyboardButton(
                text="🆕 Nueva Historia",
                callback_data="narrative_new_story"
            )
        )
        
        builder.row(
            InlineKeyboardButton(
                text="📚 Mis Historias",
                callback_data="narrative_my_stories"
            ),
            InlineKeyboardButton(
                text="🏆 Logros",
                callback_data="narrative_achievements"
            )
        )
        
        builder.row(
            InlineKeyboardButton(
                text="📜 Historial",
                callback_data="narrative_history"
            ),
            InlineKeyboardButton(
                text="📊 Estadísticas", 
                callback_data="narrative_stats"
            )
        )
        
        if not is_vip:
            builder.row(
                InlineKeyboardButton(
                    text="⭐ Desbloquear Historia VIP",
                    callback_data="narrative_vip_info"
                )
            )
        
        builder.row(
            InlineKeyboardButton(
                text="🔙 Menú Principal",
                callback_data="main_menu"
            )
        )
        
        return builder.as_markup()
    
    @staticmethod
    def story_selection(has_vip_access: bool = False) -> InlineKeyboardMarkup:
        """Selección de historia para comenzar"""
        builder = InlineKeyboardBuilder()
        
        builder.row(
            InlineKeyboardButton(
                text="🌙 Historia Gratuita: El Despertar",
                callback_data="narrative_select_free"
            )
        )
        
        if has_vip_access:
            builder.row(
                InlineKeyboardButton(
                    text="💎 Historia VIP: Secretos de Diana",
                    callback_data="narrative_select_vip"
                )
            )
        else:
            builder.row(
                InlineKeyboardButton(
                    text="🔒 Historia VIP (Bloqueada)",
                    callback_data="narrative_vip_locked"
                )
            )
        
        builder.row(
            InlineKeyboardButton(
                text="🔙 Atrás",
                callback_data="narrative_menu"
            )
        )
        
        return builder.as_markup()
    
    @staticmethod
    def story_fragment(
        fragment: FragmentSchema,
        can_go_back: bool = False,
        chapter_info: Optional[Dict[str, Any]] = None
    ) -> InlineKeyboardMarkup:
        """Teclado para un fragmento de historia"""
        builder = InlineKeyboardBuilder()
        
        # Si es un punto de decisión, mostrar opciones
        if fragment.type == "decision" and fragment.choices:
            for i, choice in enumerate(fragment.choices[:MAX_CHOICES_PER_FRAGMENT]):
                # Formato: narrative_choice_{choice_id}
                builder.row(
                    InlineKeyboardButton(
                        text=f"{i+1}. {choice.text}",
                        callback_data=f"narrative_choice_{choice.id}"
                    )
                )
        
        # Si tiene siguiente fragmento automático
        elif fragment.next_fragment:
            builder.row(
                InlineKeyboardButton(
                    text="➡️ Continuar",
                    callback_data=f"narrative_next_{fragment.next_fragment}"
                )
            )
        
        # Botones de navegación
        nav_buttons = []
        
        if BACK_BUTTON_ENABLED and can_go_back:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="◀️ Atrás",
                    callback_data="narrative_back"
                )
            )
        
        nav_buttons.append(
            InlineKeyboardButton(
                text="📑 Menú",
                callback_data="narrative_menu"
            )
        )
        
        if chapter_info:
            nav_buttons.append(
                InlineKeyboardButton(
                    text=f"📍 Cap. {chapter_info.get('current', '?')}",
                    callback_data="narrative_chapter_info"
                )
            )
        
        if nav_buttons:
            builder.row(*nav_buttons)
        
        return builder.as_markup()
    
    @staticmethod
    def locked_fragment(
        missing_requirements: List[str],
        has_hint: bool = False
    ) -> InlineKeyboardMarkup:
        """Teclado para fragmento bloqueado"""
        builder = InlineKeyboardBuilder()
        
        if has_hint:
            builder.row(
                InlineKeyboardButton(
                    text="💡 Ver Pista",
                    callback_data="narrative_show_hint"
                )
            )
        
        builder.row(
            InlineKeyboardButton(
                text="📋 Ver Requisitos",
                callback_data="narrative_show_requirements"
            )
        )
        
        builder.row(
            InlineKeyboardButton(
                text="🔙 Volver",
                callback_data="narrative_back"
            ),
            InlineKeyboardButton(
                text="🏠 Menú Principal",
                callback_data="main_menu"
            )
        )
        
        return builder.as_markup()
    
    @staticmethod
    def story_ending(
        ending_type: str,
        completion_percent: float,
        has_more_endings: bool = True
    ) -> InlineKeyboardMarkup:
        """Teclado para final de historia"""
        builder = InlineKeyboardBuilder()
        
        if has_more_endings:
            builder.row(
                InlineKeyboardButton(
                    text="🔄 Explorar Otro Camino",
                    callback_data="narrative_restart_chapter"
                )
            )
        
        builder.row(
            InlineKeyboardButton(
                text="📊 Ver Estadísticas",
                callback_data="narrative_ending_stats"
            ),
            InlineKeyboardButton(
                text="🏆 Compartir Logro",
                callback_data="narrative_share_ending"
            )
        )
        
        if completion_percent < 100:
            builder.row(
                InlineKeyboardButton(
                    text=f"🗺️ Mapa de Historia ({completion_percent:.0f}% completo)",
                    callback_data="narrative_story_map"
                )
            )
        
        builder.row(
            InlineKeyboardButton(
                text="📚 Volver a Historias",
                callback_data="narrative_my_stories"
            ),
            InlineKeyboardButton(
                text="🏠 Menú Principal",
                callback_data="main_menu"
            )
        )
        
        return builder.as_markup()
    
    @staticmethod
    def history_navigation(
        page: int,
        total_pages: int,
        story_id: str
    ) -> InlineKeyboardMarkup:
        """Navegación para historial de decisiones"""
        builder = InlineKeyboardBuilder()
        
        nav_buttons = []
        
        if page > 1:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="⬅️",
                    callback_data=f"narrative_history_page_{story_id}_{page-1}"
                )
            )
        
        nav_buttons.append(
            InlineKeyboardButton(
                text=f"{page}/{total_pages}",
                callback_data="narrative_history_info"
            )
        )
        
        if page < total_pages:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="➡️",
                    callback_data=f"narrative_history_page_{story_id}_{page+1}"
                )
            )
        
        if nav_buttons:
            builder.row(*nav_buttons)
        
        builder.row(
            InlineKeyboardButton(
                text="📊 Estadísticas Completas",
                callback_data=f"narrative_story_stats_{story_id}"
            )
        )
        
        builder.row(
            InlineKeyboardButton(
                text="🔙 Atrás",
                callback_data="narrative_menu"
            )
        )
        
        return builder.as_markup()
    
    @staticmethod
    def admin_fragment_actions(fragment_id: str, story_id: str) -> InlineKeyboardMarkup:
        """Acciones de administrador para un fragmento"""
        builder = InlineKeyboardBuilder()
        
        builder.row(
            InlineKeyboardButton(
                text="✏️ Editar",
                callback_data=f"narrative_admin_edit_{story_id}_{fragment_id}"
            ),
            InlineKeyboardButton(
                text="📊 Stats",
                callback_data=f"narrative_admin_stats_{story_id}_{fragment_id}"
            )
        )
        
        builder.row(
            InlineKeyboardButton(
                text="🔀 Probar Caminos",
                callback_data=f"narrative_admin_test_{story_id}_{fragment_id}"
            ),
            InlineKeyboardButton(
                text="👥 Ver Usuarios",
                callback_data=f"narrative_admin_users_{story_id}_{fragment_id}"
            )
        )
        
        builder.row(
            InlineKeyboardButton(
                text="🔙 Panel Admin",
                callback_data="admin_narrative_menu"
            )
        )
        
        return builder.as_markup()
      
