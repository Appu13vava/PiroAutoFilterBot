from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database.ia_filterdb import get_search_results
from utils import get_settings, get_size

async def send_search_results(client, user_id, query):
    query = (query or "").replace("_", " ").strip()
    if not query:
        await client.send_message(user_id, "Please provide a movie name to search.")
        return

    files, _offset, total = await get_search_results(
        chat_id=user_id, query=query.lower(), offset=0, filter=True
    )
    if not files:
        await client.send_message(user_id, f"❌ No files found for: {query}")
        return

    settings = await get_settings(user_id)
    prefix = "filep" if settings.get("file_secure") else "file"
    buttons = [[InlineKeyboardButton(f"🎬 {query} — {total} results", callback_data="pages")]]
    if settings.get("button"):
        buttons.extend([[InlineKeyboardButton(
            f"🔖 {get_size(item.file_size)}  {item.file_name}",
            callback_data=f"{prefix}#{item.file_id}"
        )] for item in files])
    else:
        buttons.extend([[
            InlineKeyboardButton(item.file_name or "File", callback_data=f"{prefix}#{item.file_id}"),
            InlineKeyboardButton(get_size(item.file_size), callback_data=f"{prefix}#{item.file_id}")
        ] for item in files])

    await client.send_message(
        user_id, f"🔎 Search results for **{query}**\n📁 Found: {total}",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
