import logging
from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from info import AUTH_CHANNELS, CUSTOM_FILE_CAPTION
from database.users_chats_db import db
from database.ia_filterdb import get_file_details
from utils import get_size
from search_link import send_search_results

logger = logging.getLogger(__name__)
logger.info("Force join-request plugin loaded")


@Client.on_chat_join_request()
async def save_join_request(client, request):
    user_id = int(request.from_user.id)
    channel_id = int(request.chat.id)

    logger.info(
        "JOIN REQUEST RECEIVED: user=%s channel=%s",
        user_id,
        channel_id
    )

    try:
        if channel_id not in {int(ch) for ch in AUTH_CHANNELS}:
            return

        await db.add_force_request(
            user_id=user_id,
            channel_id=channel_id
        )

        pending = await db.get_pending_force_file(user_id, channel_id)

        if not pending:
            logger.info(
                "No pending file/search for user=%s channel=%s",
                user_id,
                channel_id
            )
            return

        if pending.get("search_query"):
            await send_search_results(client, user_id, pending["search_query"])
            await db.remove_pending_force_file(user_id)
            logger.info("Pending search results sent: user=%s query=%s", user_id, pending["search_query"])
            return

        file_id = pending.get("file_id")
        if not file_id:
            await db.remove_pending_force_file(user_id)
            return
        details = await get_file_details(file_id)

        if not details:
            logger.warning("Pending file not found: %s", file_id)
            await db.remove_pending_force_file(user_id)
            return

        media = details[0]
        size = get_size(media.file_size)
        caption = media.caption or media.file_name or " "

        if CUSTOM_FILE_CAPTION:
            try:
                caption = CUSTOM_FILE_CAPTION.format(
                    file_name=media.file_name or "",
                    file_size=size or "",
                    file_caption=media.caption or ""
                )
            except Exception:
                logger.exception("Could not format pending file caption")

        await client.send_cached_media(
            chat_id=user_id,
            file_id=file_id,
            caption=caption,
            protect_content=bool(pending.get("protect", False)),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "⚔️ മലയാളം മൂവീസ് ⚔️",
                    url="https://t.me/+lav5Yo5CPjZmNzY1"
                )]
            ])
        )

        await db.remove_pending_force_file(user_id)

        logger.info(
            "Pending file sent automatically: user=%s channel=%s",
            user_id,
            channel_id
        )

    except Exception:
        logger.exception("Failed to process force join request")
