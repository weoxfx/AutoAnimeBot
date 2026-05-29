import logging

from functions.config import Var

logging.basicConfig(
    format="%(asctime)s || %(name)s [%(levelname)s] : %(message)s",
    handlers=[
        logging.FileHandler("AnimeRequestBot.log", mode="w", encoding="utf-8"),
        logging.StreamHandler(),
    ],
    level=logging.INFO,
    datefmt="%m/%d/%Y, %H:%M:%S",
)

LOGS = logging.getLogger("AnimeRequestBot")
TelethonLogger = logging.getLogger("Telethon")
TelethonLogger.setLevel(logging.WARNING)

LOGS.info(
    f"\n"
    f"    ╔══════════════════════════════════════╗\n"
    f"    ║       Anime Request Bot  {Var.__version__}        ║\n"
    f"    ║   Sub | Dub | HSub — Any Quality    ║\n"
    f"    ╚══════════════════════════════════════╝\n"
)
