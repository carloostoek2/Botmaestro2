"""
Gestor de historias y contenido narrativo
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from .schemas import StorySchema, FragmentSchema, ChoiceSchema
from .constants import MAX_CHOICES_PER_FRAGMENT, NARRATIVE_POINTS

logger = logging.getLogger(__name__)


class StoryManager:
    """Gestiona la carga y acceso a historias desde JSON"""
    
    def __init__(self, data_path: Path = None):
        self.data_path = data_path or Path(__file__).parent / "data"
        self.stories: Dict[str, StorySchema] = {}
        self._story_cache: Dict[str, Dict[str, FragmentSchema]] = {}
        self._load_stories()
    
    def _load_stories(self) -> None:
        """Carga todas las historias disponibles desde JSON"""
        story_files = {
            "free": "story_free.json",
            "vip": "story_vip.json"
        }
        
        for story_id, filename in story_files.items():
            filepath = self.data_path / filename
            if filepath.exists():
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        story = StorySchema(**data)
                        self.stories[story_id] = story
                        
                        # Cache de fragmentos para acceso rápido
                        self._story_cache[story_id] = {
                            frag_id: FragmentSchema(**frag_data)
                            for frag_id, frag_data in data['fragments'].items()
                        }
                        
                        logger.info(f"Historia '{story_id}' cargada: {story.total_fragments} fragmentos")
                except Exception as e:
                    logger.error(f"Error cargando historia {filename}: {e}")
            else:
                logger.warning(f"Archivo de historia no encontrado: {filepath}")
    
    def get_story(self, story_id: str) -> Optional[StorySchema]:
        """Obtiene una historia completa"""
        return self.stories.get(story_id)
    
    def get_fragment(self, story_id: str, fragment_id: str) -> Optional[FragmentSchema]:
        """Obtiene un fragmento específico"""
        if story_id in self._story_cache:
            return self._story_cache[story_id].get(fragment_id)
        return None
    
    def get_starting_fragment(self, story_id: str) -> Optional[FragmentSchema]:
        """Obtiene el fragmento inicial de una historia"""
        story = self.get_story(story_id)
        if story:
            return self.get_fragment(story_id, story.starting_fragment)
        return None
    
    def get_chapter_fragments(self, story_id: str, chapter: int) -> List[FragmentSchema]:
        """Obtiene todos los fragmentos de un capítulo"""
        fragments = []
        if story_id in self._story_cache:
            for frag_id, fragment in self._story_cache[story_id].items():
                if fragment.chapter == chapter:
                    fragments.append(fragment)
        return sorted(fragments, key=lambda f: f.scene)
    
    def validate_choice(self, story_id: str, fragment_id: str, choice_id: str) -> Optional[ChoiceSchema]:
        """Valida que una elección existe en un fragmento"""
        fragment = self.get_fragment(story_id, fragment_id)
        if fragment and fragment.choices:
            for choice in fragment.choices:
                if choice.id == choice_id:
                    return choice
        return None
    
    def check_requirements(self, requirements: Dict[str, Any], user_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Verifica si un usuario cumple los requisitos
        Retorna (cumple_requisitos, lista_de_faltantes)
        """
        missing = []
        
        # REF: [database/models.py] User - Verificar nivel
        if "level" in requirements and user_data.get("level", 1) < requirements["level"]:
            missing.append(f"Nivel {requirements['level']}")
        
        # REF: [database/models.py] User - Verificar puntos
        if "points" in requirements and user_data.get("points", 0) < requirements["points"]:
            missing.append(f"{requirements['points']} besitos")
        
        # Verificar items (mochila)
        if "items" in requirements:
            user_items = user_data.get("items", [])
            for item in requirements["items"]:
                if item not in user_items:
                    missing.append(f"Item: {item}")
        
        # REF: [database/models.py] Achievement - Verificar logros
        if "achievements" in requirements:
            user_achievements = user_data.get("achievements", [])
            for achievement in requirements["achievements"]:
                if achievement not in user_achievements:
                    missing.append(f"Logro: {achievement}")
        
        # Verificar flags narrativos
        if "story_flags" in requirements:
            user_flags = user_data.get("story_flags", {})
            for flag, value in requirements["story_flags"].items():
                if user_flags.get(flag) != value:
                    missing.append(f"Decisión previa requerida")
                    
        return len(missing) == 0, missing
    
    def calculate_completion_percent(self, story_id: str, visited_fragments: List[str]) -> float:
        """Calcula el porcentaje de completitud de una historia"""
        story = self.get_story(story_id)
        if not story:
            return 0.0
        
        # Contar solo fragmentos principales (no ocultos)
        main_fragments = [
            frag_id for frag_id, frag in self._story_cache[story_id].items()
            if not frag.is_hidden
        ]
        
        if not main_fragments:
            return 0.0
        
        visited_main = [f for f in visited_fragments if f in main_fragments]
        return round((len(visited_main) / len(main_fragments)) * 100, 1)
    
    def get_fragment_stats(self, story_id: str, fragment_id: str) -> Dict[str, Any]:
        """Obtiene estadísticas de un fragmento (para admin)"""
        fragment = self.get_fragment(story_id, fragment_id)
        if not fragment:
            return {}
        
        return {
            "id": fragment_id,
            "type": fragment.type,
            "chapter": fragment.chapter,
            "scene": fragment.scene,
            "has_choices": bool(fragment.choices),
            "num_choices": len(fragment.choices) if fragment.choices else 0,
            "has_rewards": bool(fragment.rewards),
            "is_hidden": fragment.is_hidden,
            "requires_vip": fragment.vip_only
        }
    
    def search_fragments(self, story_id: str, query: str) -> List[FragmentSchema]:
        """Busca fragmentos por texto (para debug/admin)"""
        results = []
        query_lower = query.lower()
        
        if story_id in self._story_cache:
            for fragment in self._story_cache[story_id].values():
                if (query_lower in fragment.narrator_text.lower() or
                    (fragment.title and query_lower in fragment.title.lower()) or
                    (fragment.atmosphere_text and query_lower in fragment.atmosphere_text.lower())):
                    results.append(fragment)
        
        return results
    
    def get_next_fragments(self, story_id: str, fragment_id: str, depth: int = 3) -> Dict[str, List[str]]:
        """
        Obtiene un árbol de posibles siguientes fragmentos
        Útil para precarga y visualización de rutas
        """
        paths = {}
        visited = set()
        
        def explore(current_id: str, path: List[str], remaining_depth: int):
            if remaining_depth <= 0 or current_id in visited:
                return
            
            visited.add(current_id)
            fragment = self.get_fragment(story_id, current_id)
            if not fragment:
                return
            
            # Explorar siguiente por defecto
            if fragment.next_fragment:
                new_path = path + [fragment.next_fragment]
                paths[fragment.next_fragment] = new_path
                explore(fragment.next_fragment, new_path, remaining_depth - 1)
            
            # Explorar opciones
            if fragment.choices:
                for choice in fragment.choices:
                    if choice.next_fragment:
                        new_path = path + [choice.next_fragment]
                        paths[choice.next_fragment] = new_path
                        explore(choice.next_fragment, new_path, remaining_depth - 1)
        
        explore(fragment_id, [], depth)
        return paths
