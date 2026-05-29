import asyncio
import sys
from traceback import format_exc

from pyrogram import Client, utils
from telethon import TelegramClient
from telethon.errors import (
    AccessTokenExpiredError,
    AccessTokenInvalidError,
    ApiIdInvalidError,
    AuthKeyDuplicatedError,
)
from telethon.sessions import StringSession

from functions.config import Var
from libs.logger import LOGS, TelethonLogger


class Bot(TelegramClient):
    def __init__(self):
        utils.MIN_CHANNEL_ID = -1009147483647
        super().__init__(
            None,
            api_id=Var.API_ID,
            api_hash=Var.API_HASH,
            base_logger=TelethonLogger,
            connection_retries=10,
            retry_delay=5,
            auto_reconnect=True,
            flood_sleep_threshold=60,
        )
        self.pyro = Client(
            name="anime_bot",
            api_id=Var.API_ID,
            api_hash=Var.API_HASH,
            bot_token=Var.BOT_TOKEN,
            in_memory=True,
        )
        self.loop.run_until_complete(self._start())

    async def _start(self):
        LOGS.info("Starting bot...")
        try:
            await self.start(bot_token=Var.BOT_TOKEN)
            await self.pyro.start()
        except ApiIdInvalidError:
            LOGS.critical("API_ID / API_HASH mismatch!")
            sys.exit(1)
        except (AuthKeyDuplicatedError, EOFError):
            LOGS.critical("String session expired.")
            sys.exit(1)
        except (AccessTokenExpiredError, AccessTokenInvalidError):
            LOGS.critical("BOT_TOKEN invalid or expired.")
            sys.exit(1)
        me = await self.get_me()
        LOGS.info(f"Logged in as @{me.username}")

    async def send_progress_message(self, chat_id: int, text: str):
        return await self.send_message(chat_id, text)

    async def upload_file(
        self,
        chat_id: int,
        file_path: str,
        caption: str,
        progress_msg=None,
    ):
        if not self.pyro.is_connected:
            try:
                await self.pyro.connect()
            except Exception:
                await self.pyro.start()

        last_update = [0]

        async def progress(current, total):
            import time
            now = time.time()
            if now - last_update[0] < 8:
                return
            last_update[0] = now
            pct = (current / total) * 100
            bar_filled = int(pct / 5)
            bar = "●" * bar_filled + "○" * (20 - bar_filled)
            size_mb = total / (1024 * 1024)
            done_mb = current / (1024 * 1024)
            text = (
                f"**📤 Uploading...**\n\n"
                f"`[{bar}] {pct:.1f}%`\n"
                f"`{done_mb:.1f} / {size_mb:.1f} MB`"
            )
            try:
                if progress_msg:
                    await progress_msg.edit(text)
            except Exception:
                pass

        return await self.pyro.send_document(
            chat_id,
            file_path,
            caption=caption,
            force_document=True,
            progress=progress,
        )

    def run(self):
        self.run_until_disconnected()
