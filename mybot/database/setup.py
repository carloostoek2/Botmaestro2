# database/setup.py
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from .base import Base
from utils.config import Config

logger = logging.getLogger(__name__)

_engine = None
_sessionmaker = None

TABLES_ORDER = [
    'users',
    'achievements',
    'story_fragments',
    'user_narrative_states',
    'user_decisions',
    'narrative_metrics',
    'rewards',
    'lore_pieces',
    'missions',
    'events',
    'raffles',
    'badges',
    'levels',
    'invite_tokens',
    'subscription_plans',
    'subscription_tokens',
    'tariffs',
    'config_entries',
    'bot_config',
    'channels',
    'pending_channel_requests',
    'challenges',
    'auctions',
    'trivias',
    'user_rewards',
    'user_achievements',
    'user_mission_entries',
    'raffle_entries',
    'user_badges',
    'vip_subscriptions',
    'user_stats',
    'tokens',
    'user_challenge_progress',
    'button_reactions',
    'bids',
    'auction_participants',
    'minigame_play',
    'user_lore_pieces',
    'trivia_questions',
    'trivia_attempts',
    'trivia_user_answers',
]

async def init_db():
    global _engine
    try:
        logger.info("Creando motor de base de datos...")
        if _engine is None:
            _engine = create_async_engine(
                Config.DATABASE_URL, 
                echo=False, 
                poolclass=NullPool
            )
        async with _engine.begin() as conn:
            logger.info("Creando tablas...")
            tables = [Base.metadata.tables[name] for name in TABLES_ORDER]
            await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=tables))
            logger.info("Tablas creadas exitosamente")
        return _engine
    except Exception as e:
        logger.critical(f"Error crítico en init_db: {str(e)}")
        raise

def get_session_factory():
    global _sessionmaker
    if _engine is None:
        raise RuntimeError("Database engine not initialized. Call init_db first.")
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(
            bind=_engine, 
            expire_on_commit=False,
            class_=AsyncSession
        )
    return _sessionmaker

async def get_session() -> AsyncSession:
    session_factory = get_session_factory()
    return session_factory()
