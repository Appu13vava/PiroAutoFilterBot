from pyrogram import Client
from info import AUTH_CHANNELS
from database.users_chats_db import db


@Client.on_chat_join_request()
async def save_join_request(client, request):
    if request.chat.id not in [int(ch) for ch in AUTH_CHANNELS]:
        return

    await db.add_force_request(
        user_id=request.from_user.id,
        channel_id=request.chat.id
    )
