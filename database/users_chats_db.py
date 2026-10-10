import motor.motor_asyncio

from info import (
    DATABASE_NAME, DATABASE_URI, IMDB, IMDB_TEMPLATE,
    MELCOW_NEW_USERS, P_TTI_SHOW_OFF, SINGLE_BUTTON,
    SPELL_CHECK_REPLY, PROTECT_CONTENT, AUTO_DELETE,
    AUTO_FFILTER, MAX_BTN
)


class Database:

    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.col = self.db.users
        self.grp = self.db.groups

        # Force join requests
        self.force_requests = self.db.force_requests

        # Pending files awaiting a join request
        self.pending_force_files = self.db.pending_force_files

    # ---------------- FORCE JOIN REQUESTS ----------------

    async def add_force_request(self, user_id, channel_id):
        await self.force_requests.update_one(
            {
                "user_id": int(user_id),
                "channel_id": int(channel_id)
            },
            {
                "$set": {
                    "user_id": int(user_id),
                    "channel_id": int(channel_id)
                }
            },
            upsert=True
        )

    async def has_force_request(self, user_id, channel_id=None):
        """Check whether a user has a saved request, optionally for one channel."""
        query = {"user_id": int(user_id)}
        if channel_id is not None:
            query["channel_id"] = int(channel_id)
        return await self.force_requests.find_one(query) is not None

    async def has_force_request_for_channel(self, user_id, channel_id):
        # Telegram channel IDs may be configured as strings in info.py.
        # Normalize both IDs so requests are tracked per user AND per channel.
        return await self.force_requests.find_one({
            "user_id": int(user_id),
            "channel_id": int(channel_id)
        }) is not None

    async def remove_force_request(self, user_id, channel_id):
        await self.force_requests.delete_one({
            "user_id": int(user_id),
            "channel_id": int(channel_id)
        })

    # ---------------- PENDING FILES ----------------

    async def save_pending_force_file(
        self, user_id, channel_id, file_id, protect=False
    ):
        await self.pending_force_files.update_one(
            {
                "user_id": int(user_id),
                "channel_id": int(channel_id)
            },
            {
                "$set": {
                    "user_id": int(user_id),
                    "channel_id": int(channel_id),
                    "file_id": file_id,
                    "protect": bool(protect)
                }
            },
            upsert=True
        )

    async def save_pending_force_search(self, user_id, channel_id, search_query):
        await self.pending_force_files.update_one(
            {"user_id": int(user_id), "channel_id": int(channel_id)},
            {"$set": {
                "user_id": int(user_id),
                "channel_id": int(channel_id),
                "search_query": str(search_query),
            }, "$unset": {"file_id": "", "protect": ""}},
            upsert=True
        )

    async def get_pending_force_file(self, user_id, channel_id):
        return await self.pending_force_files.find_one({
            "user_id": int(user_id),
            "channel_id": int(channel_id)
        })

    async def remove_pending_force_file(self, user_id, channel_id=None):
        """Remove the pending item for this user, optionally for one channel only."""
        query = {"user_id": int(user_id)}
        if channel_id is not None:
            query["channel_id"] = int(channel_id)
        await self.pending_force_files.delete_many(query)

    # ---------------- USERS ----------------

    def new_user(self, id, name):
        return dict(
            id=id,
            name=name,
            ban_status=dict(
                is_banned=False,
                ban_reason=""
            )
        )

    async def add_user(self, id, name):
        user = self.new_user(id, name)
        await self.col.insert_one(user)

    async def is_user_exist(self, id):
        user = await self.col.find_one({"id": int(id)})
        return bool(user)

    async def total_users_count(self):
        return await self.col.count_documents({})

    async def remove_ban(self, id):
        ban_status = dict(
            is_banned=False,
            ban_reason=""
        )
        await self.col.update_one(
            {"id": id},
            {"$set": {"ban_status": ban_status}}
        )

    async def ban_user(self, user_id, ban_reason="No Reason"):
        ban_status = dict(
            is_banned=True,
            ban_reason=ban_reason
        )
        await self.col.update_one(
            {"id": user_id},
            {"$set": {"ban_status": ban_status}}
        )

    async def get_ban_status(self, id):
        default = dict(
            is_banned=False,
            ban_reason=""
        )
        user = await self.col.find_one({"id": int(id)})
        if not user:
            return default
        return user.get("ban_status", default)

    async def get_all_users(self):
        return self.col.find({})

    async def delete_user(self, user_id):
        await self.col.delete_many({"id": int(user_id)})

    async def get_banned(self):
        users = self.col.find({"ban_status.is_banned": True})
        chats = self.grp.find({"chat_status.is_disabled": True})
        b_chats = [chat["id"] async for chat in chats]
        b_users = [user["id"] async for user in users]
        return b_users, b_chats

    # ---------------- GROUPS ----------------

    def new_group(self, id, title):
        return dict(
            id=id,
            title=title,
            chat_status=dict(
                is_disabled=False,
                reason=""
            )
        )

    async def add_chat(self, chat, title):
        group = self.new_group(chat, title)
        await self.grp.insert_one(group)

    async def get_chat(self, chat):
        chat = await self.grp.find_one({"id": int(chat)})
        return False if not chat else chat.get("chat_status")

    async def re_enable_chat(self, id):
        chat_status = dict(
            is_disabled=False,
            reason=""
        )
        await self.grp.update_one(
            {"id": int(id)},
            {"$set": {"chat_status": chat_status}}
        )

    async def update_settings(self, id, settings):
        # Persist settings even if this group has not yet been inserted into
        # the groups collection (upsert prevents silent loss of the toggle).
        group_id = int(id)
        await self.grp.update_one(
            {"id": group_id},
            {
                "$set": {"settings": settings},
                "$setOnInsert": {
                    "id": group_id,
                    "title": "Unknown",
                    "chat_status": {"is_disabled": False, "reason": ""}
                }
            },
            upsert=True
        )

    async def get_settings(self, id):
        default = {
            "button": SINGLE_BUTTON,
            "botpm": P_TTI_SHOW_OFF,
            "file_secure": PROTECT_CONTENT,
            "imdb": IMDB,
            "spell_check": SPELL_CHECK_REPLY,
            "welcome": MELCOW_NEW_USERS,
            "auto_delete": AUTO_DELETE,
            "auto_ffilter": AUTO_FFILTER,
            "max_btn": MAX_BTN,
            "template": IMDB_TEMPLATE
        }
        chat = await self.grp.find_one({"id": int(id)})
        # Merge defaults with saved values so older/incomplete MongoDB
        # documents still receive the current spell_check default.
        saved = chat.get("settings", {}) if chat else {}
        if not isinstance(saved, dict):
            saved = {}
        return {**default, **saved}

    async def disable_chat(self, chat, reason="No Reason"):
        chat_status = dict(
            is_disabled=True,
            reason=reason
        )
        await self.grp.update_one(
            {"id": int(chat)},
            {"$set": {"chat_status": chat_status}}
        )

    async def total_chat_count(self):
        return await self.grp.count_documents({})

    async def get_all_chats(self):
        return self.grp.find({})

    # ---------------- DATABASE ----------------

    async def get_db_size(self):
        return (await self.db.command("dbstats"))["dataSize"]


db = Database(DATABASE_URI, DATABASE_NAME)
