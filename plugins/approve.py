"""Track force-channel join requests without delivering a file early.

A user must send a join request to each configured force channel. The next
movie click then presents a request link for another channel. Once all
configured channels have a saved request (or the user has joined), the normal
/start handler delivers the requested movie.
"""
import logging
from pyrogram import Client
from info import AUTH_CHANNELS
from database.users_chats_db import db

logger = logging.getLogger(__name__)
logger.info("Force join-request tracker loaded")


@Client.on_chat_join_request()
async def save_join_request(client, request):
    user_id = int(request.from_user.id)
    channel_id = int(request.chat.id)

    try:
        configured_channels = {int(ch) for ch in AUTH_CHANNELS}
        if channel_id not in configured_channels:
            return

        # Store each request by user AND channel. Duplicate requests do not
        # count as requests to other channels.
        await db.add_force_request(user_id=user_id, channel_id=channel_id)
        logger.info("Saved force join request: user=%s channel=%s", user_id, channel_id)

        # Do not send the pending movie here. The user should click the movie
        # link again so the bot can select a different unrequested channel.
        try:
            await client.send_message(
                chat_id=user_id,
                text=(
                    "✅ Join request received!\n\n"
                    "ഇനി movie link വീണ്ടും click ചെയ്യൂ. അടുത്ത channel-ലേക്ക് "
                    "request അയക്കാം. എല്ലാ 4 channel-ലേക്കും request അയച്ചാൽ "
                    "movie നേരിട്ട് ലഭിക്കും."
                ),
            )
        except Exception:
            logger.debug("Could not notify user %s after join request", user_id, exc_info=True)
    except Exception:
        logger.exception("Failed to record force join request for user=%s channel=%s", user_id, channel_id)
