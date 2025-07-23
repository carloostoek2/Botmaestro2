from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .config import ADMIN_IDS, VIP_CHANNEL_ID
from database.models import User, VipSubscription
import os
import time
from typing import Dict, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

DEFAULT_VIP_MULTIPLIER = int(os.environ.get("VIP_POINTS_MULTIPLIER", "2"))

# Cache user roles for a short time to avoid repeated API calls
_ROLE_CACHE: Dict[int, Tuple[str, float]] = {}


async def is_admin(user_id: int, session: AsyncSession | None = None) -> bool:
    """Check if the user is an admin with session support."""
    # Primero verificar en la lista estática de admins
    if user_id in ADMIN_IDS:
        return True
    
    # Si tenemos sesión, verificar en la base de datos
    if session:
        try:
            result = await session.execute(
                select(User.is_admin).where(User.id == user_id)
            )
            return result.scalar_one_or_none() or False
        except Exception as e:
            logger.error(f"Error checking admin status in DB: {e}")
    
    return False



async def is_vip_member(bot: Bot, user_id: int, session: AsyncSession | None = None) -> bool:
    """Check if the user should be considered a VIP."""
    from services.config_service import ConfigService

    # First check database subscription status
    if session:
        try:
            # Check if user has active VIP subscription in database
            user = await session.get(User, user_id)
            if user and user.role == "vip":
                # Check if subscription is still valid
                if user.vip_expires_at is None or user.vip_expires_at > datetime.utcnow():
                    logger.debug(f"User {user_id} is VIP via database record")
                    return True
                else:
                    # Subscription expired, update role
                    user.role = "free"
                    await session.commit()
                    logger.info(f"User {user_id} VIP subscription expired, updated to free")
            
            # Also check VipSubscription table
            stmt = select(VipSubscription).where(VipSubscription.user_id == user_id)
            result = await session.execute(stmt)
            subscription = result.scalar_one_or_none()
            if subscription:
                if subscription.expires_at is None or subscription.expires_at > datetime.utcnow():
                    logger.debug(f"User {user_id} is VIP via subscription table")
                    return True
                else:
                    logger.debug(f"User {user_id} subscription expired")
        except Exception as e:
            logger.error(f"Error checking VIP status in database for user {user_id}: {e}")

    # Fallback to channel membership check
    vip_channel_id = VIP_CHANNEL_ID
    if session:
        try:
            config_service = ConfigService(session)
            stored_vip_id = await config_service.get_vip_channel_id()
            if stored_vip_id is not None:
                vip_channel_id = stored_vip_id
        except Exception as e:
            logger.error(f"Error getting VIP channel ID from config: {e}")

    if not vip_channel_id:
        logger.debug(f"No VIP channel configured, user {user_id} is not VIP")
        return False

    try:
        member = await bot.get_chat_member(vip_channel_id, user_id)
        is_member = member.status in {"member", "administrator", "creator"}
        logger.debug(f"User {user_id} channel membership check: {is_member} (status: {member.status})")
        return is_member
    except Exception as e:
        logger.warning(f"Error checking channel membership for user {user_id}: {e}")
        return False


async def get_points_multiplier(bot: Bot, user_id: int, session: AsyncSession | None = None) -> int:
    """Return VIP multiplier for the user."""
    if await is_vip_member(bot, user_id, session=session):
        return DEFAULT_VIP_MULTIPLIER
    return 1


# Backwards compatibility
is_vip = is_vip_member


async def is_vip_active(user_id: int, session: AsyncSession) -> bool:
    """Check if user has active VIP status - simplified version for narrative system"""
    try:
        user = await session.get(User, user_id)
        if user and user.role == "vip":
            # Check if subscription is still valid
            if user.vip_expires_at is None or user.vip_expires_at > datetime.utcnow():
                return True
        return False
    except Exception as e:
        logger.error(f"Error checking VIP status for user {user_id}: {e}")
        return False


async def get_user_role(
    bot: Bot, user_id: int, session: AsyncSession | None = None
) -> str:
    """Return the role for the given user (admin, vip or free)."""
    now = time.time()
    cached = _ROLE_CACHE.get(user_id)
    
    # Use cache only for non-admin users and only for 2 minutes
    if cached and now < cached[1] and not await is_admin(user_id, session):
        logger.debug(f"Using cached role for user {user_id}: {cached[0]}")
        return cached[0]

    # Check admin first (highest priority)
    if await is_admin(user_id, session):
        role = "admin"
        _ROLE_CACHE[user_id] = (role, now + 120)  # cache for 2 minutes
        logger.debug(f"User {user_id} is admin")
        return role
    
    # Check VIP status
    try:
        if await is_vip_member(bot, user_id, session=session):
            role = "vip"
            logger.debug(f"User {user_id} is VIP")
        else:
            role = "free"
            logger.debug(f"User {user_id} is free user")
    except Exception as e:
        logger.error(f"Error determining user role for {user_id}: {e}")
        role = "free"

    _ROLE_CACHE[user_id] = (role, now + 120)  # cache for 2 minutes
    return role


def clear_role_cache(user_id: int = None):
    """Clear role cache for a specific user or all users."""
    if user_id:
        _ROLE_CACHE.pop(user_id, None)
        logger.debug(f"Cleared role cache for user {user_id}")
    else:
        _ROLE_CACHE.clear()
        logger.debug("Cleared all role cache")