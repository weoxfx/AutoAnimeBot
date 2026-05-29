import asyncio
import os
import shutil
from traceback import format_exc

from telethon import Button, events

from core.bot import Bot
from database import DataBase
from libs.anilist import AnilistClient
from libs.ariawarp import Torrent
from libs.logger import LOGS
from libs.nyaa import NyaaSearch
from functions.config import Var

bot = Bot()
db = DataBase()
anilist = AnilistClient()
nyaa = NyaaSearch()
torrent = Torrent()

user_states: dict = {}

QUALITIES = ["480p", "720p", "1080p", "All"]
TYPES = ["Sub", "Dub", "HSub", "All"]
SEASONS = list(range(1, 9))


class _Reporter:
    def __init__(self, msg, name: str):
        self.msg = msg
        self.file_name = name

    def get_buttons(self):
        return None


def make_caption(title: str, season: int, episode: int, sub_type: str, quality: str) -> str:
    return f"{title} | Season {season} | Episode {episode:02d} | {sub_type} | {quality}"


def state(uid: int) -> dict:
    if uid not in user_states:
        user_states[uid] = {}
    return user_states[uid]


def clear_state(uid: int):
    user_states.pop(uid, None)


async def _safe_edit(msg, text, **kwargs):
    try:
        await msg.edit(text, **kwargs)
    except Exception:
        pass


@bot.on(events.NewMessage(pattern=r"^/start$", func=lambda e: e.is_private))
async def _start(event):
    await db.add_user(event.sender_id)
    await event.reply(
        "**🎌 Anime Request Bot**\n\n"
        "Send `/request <anime name>` to search and get all episodes.\n\n"
        "**Examples:**\n"
        "`/request Attack on Titan`\n"
        "`/request Naruto Shippuden`\n"
        "`/request One Piece`\n\n"
        "You'll choose the **season**, **type** (Sub / Dub / HSub) and **quality** (480p / 720p / 1080p).",
    )


@bot.on(events.NewMessage(pattern=r"^/request (.+)", func=lambda e: e.is_private))
async def _request(event):
    uid = event.sender_id
    await db.add_user(uid)

    if state(uid).get("processing"):
        return await event.reply("⏳ You already have a download in progress. Please wait.")

    query = event.pattern_match.group(1).strip()
    msg = await event.reply(f"🔍 Searching for **{query}**...")

    results = await anilist.search(query)
    if not results:
        return await msg.edit("❌ No anime found. Try a different name.")

    user_states[uid] = {"step": "select_anime"}

    buttons = []
    for r in results[:6]:
        label = r["label"][:50]
        buttons.append([Button.inline(label, data=f"sa_{r['id']}")])
    buttons.append([Button.inline("❌ Cancel", data="cancel")])

    await msg.edit(
        f"**Search results for:** `{query}`\n\nPick the correct anime:",
        buttons=buttons,
    )


@bot.on(events.CallbackQuery(pattern=r"^sa_(\d+)$"))
async def _select_anime(event):
    uid = event.sender_id
    s = state(uid)
    if s.get("step") != "select_anime":
        return await event.answer("Start a new search with /request", alert=True)

    anime_id = int(event.pattern_match.group(1))
    await event.answer()
    msg = await event.get_message()
    await _safe_edit(msg, "⏳ Fetching anime info...")

    anime = await anilist.get_by_id(anime_id)
    if not anime:
        return await _safe_edit(msg, "❌ Could not fetch anime info. Try /request again.")

    s["anime"] = anime
    s["step"] = "select_season"

    buttons = []
    row = []
    for n in SEASONS:
        row.append(Button.inline(f"S{n}", data=f"ss_{n}"))
        if len(row) == 4:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([Button.inline("❌ Cancel", data="cancel")])

    await _safe_edit(
        msg,
        f"**{anime['display_title']}** ({anime['year']})\n"
        f"Episodes: `{anime['episodes']}`  •  Status: `{anime['status']}`\n\n"
        f"Select **season number** (used in the caption):",
        buttons=buttons,
    )


@bot.on(events.CallbackQuery(pattern=r"^ss_(\d+)$"))
async def _select_season(event):
    uid = event.sender_id
    s = state(uid)
    if s.get("step") != "select_season":
        return await event.answer("Start over with /request", alert=True)

    s["season"] = int(event.pattern_match.group(1))
    s["step"] = "select_type"
    await event.answer()
    msg = await event.get_message()

    buttons = [[Button.inline(t, data=f"st_{t.lower()}") for t in TYPES]]
    buttons.append([Button.inline("❌ Cancel", data="cancel")])

    await _safe_edit(
        msg,
        f"**{s['anime']['display_title']}** — Season {s['season']}\n\n"
        f"Select the **type**:",
        buttons=buttons,
    )


@bot.on(events.CallbackQuery(pattern=r"^st_(.+)$"))
async def _select_type(event):
    uid = event.sender_id
    s = state(uid)
    if s.get("step") != "select_type":
        return await event.answer("Start over with /request", alert=True)

    raw = event.pattern_match.group(1)
    type_map = {"sub": "Sub", "dub": "Dub", "hsub": "HSub", "all": "All"}
    s["sub_type"] = type_map.get(raw, "Sub")
    s["step"] = "select_quality"
    await event.answer()
    msg = await event.get_message()

    buttons = [[Button.inline(q, data=f"sq_{q.lower()}") for q in QUALITIES]]
    buttons.append([Button.inline("❌ Cancel", data="cancel")])

    await _safe_edit(
        msg,
        f"**{s['anime']['display_title']}** — Season {s['season']} — {s['sub_type']}\n\n"
        f"Select the **quality**:",
        buttons=buttons,
    )


@bot.on(events.CallbackQuery(pattern=r"^sq_(.+)$"))
async def _select_quality(event):
    uid = event.sender_id
    s = state(uid)
    if s.get("step") != "select_quality":
        return await event.answer("Start over with /request", alert=True)

    raw = event.pattern_match.group(1)
    quality_map = {"480p": "480p", "720p": "720p", "1080p": "1080p", "all": "All"}
    s["quality"] = quality_map.get(raw, "720p")
    s["step"] = "confirm"
    await event.answer()
    msg = await event.get_message()

    anime = s["anime"]
    sample_cap = make_caption(anime["display_title"], s["season"], 1, s["sub_type"], s["quality"])
    buttons = [
        [Button.inline("✅ Start Download", data="confirm_start")],
        [Button.inline("❌ Cancel", data="cancel")],
    ]

    await _safe_edit(
        msg,
        f"**Ready to download!**\n\n"
        f"🎌 **Anime:** {anime['display_title']}\n"
        f"📅 **Year:** {anime['year']}\n"
        f"🔢 **Season:** {s['season']}\n"
        f"📺 **Episodes:** {anime['episodes']}\n"
        f"🎙 **Type:** {s['sub_type']}\n"
        f"🎞 **Quality:** {s['quality']}\n\n"
        f"**Sample caption:**\n`{sample_cap}`",
        buttons=buttons,
    )


@bot.on(events.CallbackQuery(data="confirm_start"))
async def _confirm_start(event):
    uid = event.sender_id
    s = state(uid)
    if s.get("step") != "confirm":
        return await event.answer("Start over with /request", alert=True)
    if s.get("processing"):
        return await event.answer("Already processing!", alert=True)

    await event.answer()
    s["processing"] = True
    s["step"] = "processing"
    msg = await event.get_message()

    asyncio.create_task(_run_download(uid, msg))


@bot.on(events.CallbackQuery(data="cancel"))
async def _cancel(event):
    uid = event.sender_id
    if state(uid).get("processing"):
        return await event.answer("Download in progress, cannot cancel.", alert=True)
    clear_state(uid)
    await event.answer("Cancelled.")
    msg = await event.get_message()
    await _safe_edit(msg, "❌ Cancelled. Use /request to start again.")


async def _run_download(uid: int, status_msg):
    s = user_states.get(uid, {})
    anime = s["anime"]
    season = s["season"]
    sub_type = s["sub_type"]
    quality = s["quality"]
    chat_id = status_msg.chat_id

    title = anime["display_title"]
    romaji = anime["romaji"]
    english = anime["english"]
    total_eps = anime["episodes"]
    alt_title = romaji if romaji != title else english

    download_dir = f"./downloads/{uid}/"
    os.makedirs(download_dir, exist_ok=True)

    try:
        await _safe_edit(
            status_msg,
            f"🔍 **Searching Nyaa.si** for episodes...\n\n"
            f"**{title}** | {sub_type} | {quality}\n"
            f"_(May take a moment for large libraries)_",
        )

        episode_map = await nyaa.search_episodes(title, quality, sub_type, alt_title=alt_title)

        if not episode_map and romaji and romaji != title:
            episode_map = await nyaa.search_episodes(romaji, quality, sub_type, alt_title=english)

        found_eps = sorted(episode_map.keys()) if episode_map else []

        if isinstance(total_eps, int):
            all_eps = list(range(1, total_eps + 1))
        else:
            all_eps = found_eps or list(range(1, 13))

        if not found_eps:
            await _safe_edit(
                status_msg,
                f"❌ **No episodes found** on Nyaa.si for:\n\n"
                f"**{title}** | {sub_type} | {quality}\n\n"
                f"Try a different type or quality. Some anime may not be on Nyaa.si.",
            )
            clear_state(uid)
            return

        await _safe_edit(
            status_msg,
            f"✅ Found **{len(found_eps)} episodes** — starting download & upload...\n\n"
            f"**{title}** | {sub_type} | {quality}",
        )

        await db.log_request(uid, title, season, sub_type, quality)

        success_count = 0
        fail_count = 0

        for ep_num in all_eps:
            if ep_num in episode_map:
                result = episode_map[ep_num][0]
            else:
                result = await nyaa.search_single_episode(
                    title, ep_num, quality, sub_type, alt_title=alt_title
                )
                if not result and romaji != title:
                    result = await nyaa.search_single_episode(
                        romaji, ep_num, quality, sub_type, alt_title=english
                    )

            if not result:
                await bot.send_message(
                    chat_id,
                    f"⚠️ **Episode {ep_num:02d}** — not found on Nyaa.si, skipping.",
                )
                fail_count += 1
                continue

            detected_type = result.get("detected_type", sub_type)
            detected_quality = result.get("detected_quality", quality)

            ep_dir = os.path.join(download_dir, f"ep{ep_num:03d}")
            os.makedirs(ep_dir, exist_ok=True)

            dl_msg = await bot.send_message(
                chat_id,
                f"**📥 Downloading Episode {ep_num:02d}**\n"
                f"`{result['title'][:80]}`\n"
                f"Size: `{result['size']}`  •  Seeders: `{result['seeders']}`",
            )

            try:
                reporter = _Reporter(dl_msg, result["title"])
                await torrent.download_magnet(result["magnet"], ep_dir, reporter)

                video_file = _find_video(ep_dir)
                if not video_file:
                    await dl_msg.edit(
                        f"⚠️ **Episode {ep_num:02d}** — download finished but no video file found."
                    )
                    fail_count += 1
                    shutil.rmtree(ep_dir, ignore_errors=True)
                    continue

                caption = make_caption(title, season, ep_num, detected_type, detected_quality)

                await dl_msg.edit(
                    f"**📤 Uploading Episode {ep_num:02d}**\n"
                    f"`{os.path.basename(video_file)}`"
                )

                await bot.upload_file(
                    chat_id=chat_id,
                    file_path=video_file,
                    caption=caption,
                    progress_msg=dl_msg,
                )

                await dl_msg.delete()
                success_count += 1

            except Exception:
                LOGS.error(f"Error on ep {ep_num}: {format_exc()}")
                try:
                    await dl_msg.edit(
                        f"❌ **Episode {ep_num:02d}** — error during download/upload.\n"
                        f"`{format_exc()[-300:]}`"
                    )
                except Exception:
                    pass
                fail_count += 1
            finally:
                shutil.rmtree(ep_dir, ignore_errors=True)

        summary = (
            f"✅ **All Done!**\n\n"
            f"🎌 **{title}** — Season {season}\n"
            f"🎙 Type: `{sub_type}` | 🎞 Quality: `{quality}`\n\n"
            f"✅ Uploaded: **{success_count}** episodes\n"
            f"❌ Skipped: **{fail_count}** episodes"
        )
        await bot.send_message(chat_id, summary)

        if Var.LOG_CHANNEL:
            try:
                await bot.send_message(Var.LOG_CHANNEL, f"[Done] User {uid}\n{summary}")
            except Exception:
                pass

    except Exception:
        LOGS.error(format_exc())
        try:
            await bot.send_message(
                chat_id,
                f"❌ Unexpected error:\n`{format_exc()[-400:]}`",
            )
        except Exception:
            pass
    finally:
        shutil.rmtree(download_dir, ignore_errors=True)
        clear_state(uid)


def _find_video(directory: str) -> str | None:
    extensions = {".mkv", ".mp4", ".avi", ".webm", ".m4v"}
    best = None
    best_size = 0
    for root, _, files in os.walk(directory):
        for f in files:
            if os.path.splitext(f)[1].lower() in extensions:
                path = os.path.join(root, f)
                size = os.path.getsize(path)
                if size > best_size:
                    best_size = size
                    best = path
    return best


bot.run()
