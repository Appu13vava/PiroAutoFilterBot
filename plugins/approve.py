import logging
from pyrogram import Client
from info import AUTH_CHANNELS
from database.users_chats_db import db

logger = logging.getLogger(__name__)

logger.info("Force join-request plugin loaded")

@Client.on_chat_join_request()
async def save_join_request(client, request):
    logger.info(
        "JOIN REQUEST RECEIVED: user=%s channel=%s",
        request.from_user.id,
        request.chat.id
    )

    try:
        channel_id = int(request.chat.id)
        user_id = int(request.from_user.id)
        configured_channels = {int(ch) for ch in AUTH_CHANNELS}

        if channel_id not in configured_channels:
            logger.warning("Join request channel is not in AUTH_CHANNELS: %s", channel_id)
            return

        await db.add_force_request(
            user_id=user_id,
            channel_id=channel_id
        )

        logger.info(
            "Force join request saved: user=%s channel=%s",
            user_id,
            channel_id
        )

    except Exception:
        logger.exception("Failed to save force join request")
