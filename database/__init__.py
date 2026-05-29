import sys
from traceback import format_exc

from functions.config import Var
from libs.logger import LOGS


class DataBase:
    def __init__(self):
        self.client = None
        self.requests_db = None
        self.users_db = None

        if not Var.MONGO_SRV:
            LOGS.warning("MONGO_SRV not set — running without database (requests won't be tracked).")
            return

        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            LOGS.info("Connecting to MongoDB...")
            self.client = AsyncIOMotorClient(Var.MONGO_SRV)
            self.requests_db = self.client["AnimeBot"]["requests"]
            self.users_db = self.client["AnimeBot"]["users"]
            LOGS.info("MongoDB connected.")
        except Exception:
            LOGS.error(format_exc())
            LOGS.critical("MongoDB connection failed. Running without database.")

    async def add_user(self, user_id: int):
        if not self.users_db:
            return
        try:
            await self.users_db.update_one(
                {"_id": user_id}, {"$set": {"_id": user_id}}, upsert=True
            )
        except Exception:
            pass

    async def log_request(self, user_id: int, anime: str, season: int, sub_type: str, quality: str):
        if not self.requests_db:
            return
        try:
            import datetime
            await self.requests_db.insert_one({
                "user_id": user_id,
                "anime": anime,
                "season": season,
                "type": sub_type,
                "quality": quality,
                "at": datetime.datetime.utcnow(),
            })
        except Exception:
            pass

    async def get_all_users(self) -> list:
        if not self.users_db:
            return []
        try:
            data = await self.users_db.find().to_list(length=None)
            return [d["_id"] for d in data]
        except Exception:
            return []
