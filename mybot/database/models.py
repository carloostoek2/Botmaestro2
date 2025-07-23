# database/models.py
from sqlalchemy import (
    Column,
    Integer,
    String,
    BigInteger,
    DateTime,
    Boolean,
    JSON,
    Text,
    ForeignKey,
    Float,
    UniqueConstraint,
    Enum,
)
from sqlalchemy.orm import relationship
from uuid import uuid4
from sqlalchemy.sql import func
from sqlalchemy.future import select
import enum
from .base import Base
from sqlalchemy import Column, BigInteger, String, Float, Integer, JSON, DateTime
from sqlalchemy.orm import relationship, declared_attr



class AuctionStatus(enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    ENDED = "ended"
    CANCELLED = "cancelled"



class User(Base):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True, unique=True)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    points = Column(Float, default=0)
    level = Column(Integer, default=1)
    achievements = Column(JSON, default={})
    missions_completed = Column(JSON, default={})
    last_daily_mission_reset = Column(DateTime, default=func.now())
    last_weekly_mission_reset = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    role = Column(String, default="free")
    vip_expires_at = Column(DateTime, nullable=True)
    last_reminder_sent_at = Column(DateTime, nullable=True)
    menu_state = Column(String, default="root")
    is_admin = Column(Boolean, default=False) # New column for admin status

    @declared_attr
    def narrative_state(cls):
        from .narrative_models import UserNarrativeState
        return relationship(
            UserNarrativeState,
            back_populates="user",
            uselist=False,
            lazy="selectin",
            cascade="all, delete-orphan"
        )


class Reward(Base):
    """Rewards unlocked by reaching a number of points."""

    __tablename__ = "rewards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=True)
    required_points = Column(Integer, nullable=False)
    reward_type = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())


class UserReward(Base):
    """Stores claimed rewards per user."""

    __tablename__ = "user_rewards"

    user_id = Column(BigInteger, ForeignKey("users.id"), primary_key=True)
    reward_id = Column(Integer, ForeignKey("rewards.id"), primary_key=True)
    claimed_at = Column(DateTime, default=func.now())


class Achievement(Base):
    __tablename__ = "achievements"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    condition_type = Column(String, nullable=False)
    condition_value = Column(Integer, nullable=False)
    reward_text = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())

    story_fragments = relationship(
        "StoryFragment",
        foreign_keys="StoryFragment.unlocks_achievement_id",
        back_populates="achievement_link",
        lazy="selectin"  # Añadido para evitar problemas de carga
    )


class UserAchievement(Base):
    __tablename__ = "user_achievements"
    user_id = Column(BigInteger, ForeignKey("users.id"), primary_key=True)
    achievement_id = Column(String, ForeignKey("achievements.id"), primary_key=True)
    unlocked_at = Column(DateTime, default=func.now())
    __table_args__ = (UniqueConstraint("user_id", "achievement_id", name="uix_user_achievements"),)


class Mission(Base):
    __tablename__ = "missions"
    id = Column(String, primary_key=True, unique=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    reward_points = Column(Integer, default=0)
    type = Column(String, default="one_time")
    target_value = Column(Integer, default=1)
    duration_days = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    requires_action = Column(Boolean, default=False)
    action_data = Column(JSON, nullable=True)
    # Código de pista que se desbloquea al completar esta misión
    unlocks_lore_piece_code = Column(
        String, 
        ForeignKey('lore_pieces.code_name', ondelete='SET NULL'),  # Cambiado para referencia correcta
        nullable=True,
        index=True
    )

    # Relación con LorePiece
    @declared_attr
    def lore_piece(cls):
        return relationship(
            "LorePiece",
            foreign_keys=[cls.unlocks_lore_piece_code],
            primaryjoin="Mission.unlocks_lore_piece_code == LorePiece.code_name"
        )
    created_at = Column(DateTime, default=func.now())


class UserMissionEntry(Base):
    """Consolidated mission progress and completion per user."""

    __tablename__ = "user_mission_entries"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"))
    mission_id = Column(String, ForeignKey("missions.id"))
    progress_value = Column(Integer, default=0, nullable=False)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (UniqueConstraint("user_id", "mission_id", name="uix_user_mission_entry"),)

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    multiplier = Column(Integer, default=1)  # e.g., 2 for double points
    is_active = Column(Boolean, default=True)
    start_time = Column(DateTime, default=func.now())
    end_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())


class Raffle(Base):
    __tablename__ = "raffles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    prize = Column(String, nullable=True)
    winner_id = Column(BigInteger, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    ended_at = Column(DateTime, nullable=True)


class RaffleEntry(Base):
    __tablename__ = "raffle_entries"
    raffle_id = Column(Integer, ForeignKey("raffles.id"), primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), primary_key=True)
    created_at = Column(DateTime, default=func.now())


class Badge(Base):
    __tablename__ = "badges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    icon = Column(String, nullable=True)
    condition_type = Column(String, nullable=False)
    condition_value = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())


class UserBadge(Base):
    __tablename__ = "user_badges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    badge_id = Column(Integer, ForeignKey("badges.id"), nullable=False)
    awarded_at = Column(DateTime, default=func.now())

    __table_args__ = (UniqueConstraint("user_id", "badge_id", name="uix_user_badges"),)


class Level(Base):
    __tablename__ = "levels"

    level_id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    min_points = Column(Integer, nullable=False)
    reward = Column(String, nullable=True)
    # Código de pista desbloqueada al alcanzar este nivel
    unlocks_lore_piece_code = Column(String, nullable=True)


class VipSubscription(Base):
    __tablename__ = "vip_subscriptions"
    user_id = Column(BigInteger, primary_key=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())


class UserStats(Base):
    """Activity and progression stats per user (points stored in User)."""

    __tablename__ = "user_stats"
    user_id = Column(BigInteger, ForeignKey("users.id"), primary_key=True)
    last_activity_at = Column(DateTime, default=func.now())
    last_checkin_at = Column(DateTime, nullable=True)
    last_daily_gift_at = Column(DateTime, nullable=True)
    last_notified_points = Column(Float, default=0)
    messages_sent = Column(Integer, default=0)
    checkin_streak = Column(Integer, default=0)
    # Track last time the user used the free roulette spin
    last_roulette_at = Column(DateTime, nullable=True)


class InviteToken(Base):
    __tablename__ = "invite_tokens"
    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(String, unique=True, nullable=False)
    created_by = Column(BigInteger, nullable=False)
    used_by = Column(BigInteger, nullable=True)
    created_at = Column(DateTime, default=func.now())
    used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"
    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(String, unique=True, nullable=True)
    name = Column(String, nullable=False)
    price = Column(Integer, nullable=False)
    duration_days = Column(Integer, nullable=False)
    status = Column(String, default="available")
    created_by = Column(BigInteger, nullable=False)
    used_by = Column(BigInteger, nullable=True)
    created_at = Column(DateTime, default=func.now())
    used_at = Column(DateTime, nullable=True)


class SubscriptionToken(Base):
    __tablename__ = "subscription_tokens"
    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(String, unique=True, nullable=False)
    plan_id = Column(Integer, nullable=False)
    created_by = Column(BigInteger, nullable=False)
    used_by = Column(BigInteger, nullable=True)
    created_at = Column(DateTime, default=func.now())
    used_at = Column(DateTime, nullable=True)


class Token(Base):
    """VIP activation tokens linked to tariffs."""

    __tablename__ = "tokens"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    token_string = Column(String, unique=True)
    tariff_id = Column(Integer, ForeignKey("tariffs.id"))
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    generated_at = Column(DateTime, default=func.now())
    activated_at = Column(DateTime, nullable=True)
    is_used = Column(Boolean, default=False)


class Tariff(Base):
    __tablename__ = "tariffs"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    duration_days = Column(Integer)
    price = Column(Integer)


class ConfigEntry(Base):
    __tablename__ = "config_entries"
    key = Column(String, primary_key=True)
    value = Column(String, nullable=True)


class BotConfig(Base):
    __tablename__ = "bot_config"
    id = Column(Integer, primary_key=True, autoincrement=True)
    free_channel_wait_time_minutes = Column(Integer, default=0)


class Channel(Base):
    __tablename__ = "channels"
    id = Column(BigInteger, primary_key=True)  # Telegram chat ID
    title = Column(String, nullable=True)
    # --- NUEVAS COLUMNAS ---
    reactions = Column(JSON, default=list)  # Guarda una lista de strings (ej. ["👍", "❤️", "😂"])
    reaction_points = Column(JSON, default=dict)  # Guarda un diccionario {emoji: puntos} (ej. {"👍": 0.5, "❤️": 1.0})
    # --- FIN NUEVAS COLUMNAS ---


class PendingChannelRequest(Base):
    __tablename__ = "pending_channel_requests"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    chat_id = Column(BigInteger, nullable=False)
    request_timestamp = Column(DateTime, default=func.now())
    approved = Column(Boolean, default=False)


class Challenge(Base):
    __tablename__ = "challenges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # daily, weekly, monthly
    goal_type = Column(String, nullable=False)  # messages, reactions, checkins
    goal_value = Column(Integer, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)


class UserChallengeProgress(Base):
    __tablename__ = "user_challenge_progress"

    user_id = Column(BigInteger, ForeignKey("users.id"), primary_key=True)
    challenge_id = Column(Integer, ForeignKey("challenges.id"), primary_key=True)
    current_value = Column(Integer, default=0)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)


class ButtonReaction(Base):
    """Stores reactions made on interactive channel posts."""

    __tablename__ = "button_reactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(BigInteger, nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    reaction_type = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())


# NEW AUCTION SYSTEM MODELS
class Auction(Base):
    """Real-time auction system."""
    
    __tablename__ = "auctions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    prize_description = Column(Text, nullable=False)
    initial_price = Column(Integer, nullable=False)  # Starting bid amount in points
    current_highest_bid = Column(Integer, default=0)
    highest_bidder_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    winner_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    status = Column(Enum(AuctionStatus), default=AuctionStatus.PENDING)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    created_by = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=func.now())
    ended_at = Column(DateTime, nullable=True)
    
    # Auction settings
    min_bid_increment = Column(Integer, default=10)  # Minimum increment for new bids
    max_participants = Column(Integer, nullable=True)  # Optional participant limit
    auto_extend_minutes = Column(Integer, default=5)  # Auto-extend if bid in last X minutes


class Bid(Base):
    """Individual bids in auctions."""
    
    __tablename__ = "bids"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    auction_id = Column(Integer, ForeignKey("auctions.id"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    amount = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=func.now())
    is_winning = Column(Boolean, default=False)  # Track if this is currently the winning bid
    
    __table_args__ = (
        UniqueConstraint("auction_id", "user_id", "amount", name="uix_auction_user_bid"),
    )


class AuctionParticipant(Base):
    """Track users participating in auctions for notifications."""
    
    __tablename__ = "auction_participants"
    
    auction_id = Column(Integer, ForeignKey("auctions.id"), primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), primary_key=True)
    joined_at = Column(DateTime, default=func.now())
    notifications_enabled = Column(Boolean, default=True)
    last_notified_at = Column(DateTime, nullable=True)


class MiniGamePlay(Base):
    """Record usage of minigames such as roulette or challenges."""

    __tablename__ = "minigame_play"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    game_type = Column(String, nullable=False)
    used_at = Column(DateTime, default=func.now())
    is_free = Column(Boolean, default=False)
    cost_points = Column(Float, default=0)


class LorePiece(Base):
    """Discrete lore or clue piece that users can unlock."""

    __tablename__ = "lore_pieces"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code_name = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    content_type = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String, nullable=True)
    is_main_story = Column(Boolean, default=False)
    unlock_condition_type = Column(String, nullable=True)
    unlock_condition_value = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)


class UserLorePiece(Base):
    """Mapping of unlocked lore pieces per user."""

    __tablename__ = "user_lore_pieces"

    user_id = Column(BigInteger, ForeignKey("users.id"), primary_key=True)
    lore_piece_id = Column(Integer, ForeignKey("lore_pieces.id"), primary_key=True)
    unlocked_at = Column(DateTime, default=func.now())
    context = Column(JSON, nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "lore_piece_id", name="uix_user_lore_pieces"),
    )



# Funciones para manejar el estado del menú del usuario
async def get_user_menu_state(session, user_id: int) -> str:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user and user.menu_state:
        return user.menu_state
    return "root"


async def set_user_menu_state(session, user_id: int, state: str):
    user = await session.get(User, user_id)
    if user:
        user.menu_state = state
        await session.commit()
        await session.refresh(user)

class Trivia(Base):
    __tablename__ = "trivias"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    reward_points = Column(Integer, default=10)
    unlocks_lore_piece_code = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())


class TriviaQuestion(Base):
    __tablename__ = "trivia_questions"

    id = Column(Integer, primary_key=True)
    trivia_id = Column(Integer, ForeignKey("trivias.id"), nullable=False)
    question_text = Column(Text, nullable=False)
    question_type = Column(Enum("multiple_choice", "open_ended", "visual", name="question_types"))
    options = Column(JSON, nullable=True)  # {"A": "Opción 1", "B": "Opción 2"}
    correct_answer = Column(String, nullable=False)
    media_type = Column(String, nullable=True)  # image, video, none
    media_path = Column(String, nullable=True)
    order = Column(Integer, default=0)


class TriviaAttempt(Base):
    __tablename__ = "trivia_attempts"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    trivia_id = Column(Integer, ForeignKey("trivias.id"), nullable=False)
    score = Column(Integer, default=0)
    completed_at = Column(DateTime, default=func.now())




class TriviaUserAnswer(Base):
    __tablename__ = "trivia_user_answers"

    id = Column(Integer, primary_key=True)
    attempt_id = Column(Integer, ForeignKey("trivia_attempts.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("trivia_questions.id"), nullable=False)
    user_answer = Column(Text, nullable=True)
    is_correct = Column(Boolean, default=False)
