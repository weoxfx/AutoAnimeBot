import aiohttp
from libs.logger import LOGS

ANILIST_URL = "https://graphql.anilist.co"

SEARCH_QUERY = """
query ($search: String, $page: Int) {
  Page(page: $page, perPage: 6) {
    media(search: $search, type: ANIME, sort: SEARCH_MATCH) {
      id
      title { romaji english native }
      episodes
      status
      season
      seasonYear
      format
      coverImage { large }
      description(asHtml: false)
    }
  }
}
"""

ID_QUERY = """
query ($id: Int) {
  Media(id: $id, type: ANIME) {
    id
    title { romaji english native }
    episodes
    status
    season
    seasonYear
    format
    coverImage { large }
  }
}
"""


class AnilistClient:
    async def _post(self, query: str, variables: dict) -> dict:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                ANILIST_URL,
                json={"query": query, "variables": variables},
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status != 200:
                    LOGS.error(f"Anilist returned {resp.status}")
                    return {}
                return await resp.json()

    async def search(self, name: str) -> list:
        try:
            data = await self._post(SEARCH_QUERY, {"search": name, "page": 1})
            media_list = data.get("data", {}).get("Page", {}).get("media", [])
            return [self._format(m) for m in media_list]
        except Exception as e:
            LOGS.error(f"Anilist search error: {e}")
            return []

    async def get_by_id(self, anime_id: int) -> dict:
        try:
            data = await self._post(ID_QUERY, {"id": anime_id})
            media = data.get("data", {}).get("Media", {})
            return self._format(media) if media else {}
        except Exception as e:
            LOGS.error(f"Anilist get_by_id error: {e}")
            return {}

    def _format(self, media: dict) -> dict:
        titles = media.get("title", {})
        english = titles.get("english") or ""
        romaji = titles.get("romaji") or ""
        display = english if english else romaji
        year = media.get("seasonYear") or ""
        episodes = media.get("episodes") or "?"
        status = (media.get("status") or "").replace("_", " ").title()
        season = (media.get("season") or "").title()
        return {
            "id": media.get("id"),
            "display_title": display,
            "english": english,
            "romaji": romaji,
            "episodes": episodes,
            "status": status,
            "season": season,
            "year": year,
            "cover": (media.get("coverImage") or {}).get("large") or "",
            "label": f"{display} ({year}) — {episodes} eps",
        }
