# Anime Request Bot

A Telegram bot that lets users search for any anime season and receive all episodes in Sub, Dub, or HSub at a chosen quality.

## How it works

1. User sends `/request <anime name>` in private chat
2. Bot searches Anilist and shows up to 6 matching results as buttons
3. User picks the anime → selects season number → picks type (Sub / Dub / HSub / All) → picks quality (480p / 720p / 1080p / All)
4. Bot searches Nyaa.si for all episodes matching the selection
5. Each episode is downloaded via aria2, then uploaded to Telegram with the caption:
   `Anime Name | Season N | Episode NN | Sub/Dub/HSub | Quality`

## Required environment variables

| Variable | Description |
|----------|-------------|
| `BOT_TOKEN` | Telegram bot token from @BotFather |
| `API_ID` | Telegram API ID from my.telegram.org |
| `API_HASH` | Telegram API hash from my.telegram.org |
| `OWNER` | Your Telegram numeric user ID |

## Optional environment variables

| Variable | Description |
|----------|-------------|
| `MONGO_SRV` | MongoDB SRV string — enables request logging |
| `LOG_CHANNEL` | Telegram channel ID for bot activity logs |
| `SESSION` | Telethon string session for user-account operations |

## Stack

- **Python 3.12** — core language
- **Telethon** — bot event handling
- **Pyrogram (pyrofork)** — large file uploads
- **Anilist GraphQL API** — anime search & metadata
- **Nyaa.si RSS** — torrent/magnet episode search
- **aria2** — download engine
- **MongoDB (motor)** — optional request tracking

## User preferences

- No watermarks on uploaded files
- Caption format: `Anime Name | Season N | Episode NN | Sub/Dub/HSub | Quality`
- Quality and type are user-selectable per request
