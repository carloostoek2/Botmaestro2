#!/usr/bin/env python3
"""
Script para inicializar la base de datos con las tablas narrativas
"""
import asyncio
import sys
import os

# Agregar el directorio del proyecto al path
sys.path.insert(0, '/app/mybot')

async def init_narrative_db():
    """Inicializa la base de datos incluyendo las tablas narrativas"""
    try:
        # Importar todos los modelos
        from database.base import Base
        import database.models
        import narrative.models
        
        print("✅ Modelos importados correctamente")
        
        # Configurar la base de datos
        from database.setup import init_db
        engine = await init_db()
        
        print("✅ Base de datos inicializada correctamente")
        
        # Verificar que las tablas se crearon
        async with engine.begin() as conn:
            from sqlalchemy import text
            result = await conn.execute(text('SELECT name FROM sqlite_master WHERE type="table"'))
            tables = [row[0] for row in result.fetchall()]
            
        print(f"✅ Tablas creadas: {sorted(tables)}")
        
        # Verificar tablas narrativas específicamente
        narrative_tables = ['story_fragments', 'user_narrative_states', 'user_decisions', 'narrative_metrics']
        missing_tables = [t for t in narrative_tables if t not in tables]
        
        if missing_tables:
            print(f"❌ Tablas narrativas faltantes: {missing_tables}")
        else:
            print("✅ Todas las tablas narrativas están presentes")
            
        return engine
        
    except Exception as e:
        print(f"❌ Error inicializando base de datos: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    asyncio.run(init_narrative_db())