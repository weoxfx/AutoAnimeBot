from decouple import config


class Var:
    __version__ = "v2.0"

    API_ID = config("API_ID", default=6, cast=int)
    API_HASH = config("API_HASH", default="eb06d4abfb49dc3eeb1aeb98ae0f581e")
    BOT_TOKEN = config("BOT_TOKEN", default=None)
    SESSION = config("SESSION", default=None)

    MONGO_SRV = config("MONGO_SRV", default=None)

    LOG_CHANNEL = config("LOG_CHANNEL", default=0, cast=int)
    OWNER = config("OWNER", default=0, cast=int)
