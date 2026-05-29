import re
import aiohttp
import feedparser
from libs.logger import LOGS

NYAA_RSS = "https://nyaa.si/?page=rss&q={query}&c=1_2&f=0"


class NyaaSearch:
    async def _fetch_rss(self, query: str) -> list:
        url = NYAA_RSS.format(query=query.replace(" ", "+"))
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                    content = await resp.text()
            feed = feedparser.parse(content)
            results = []
            for entry in feed.entries:
                magnet = getattr(entry, "nyaa_magneturi", "") or ""
                size = getattr(entry, "nyaa_size", "") or ""
                seeders = int(getattr(entry, "nyaa_seeders", 0) or 0)
                results.append({
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "magnet": magnet,
                    "size": size,
                    "seeders": seeders,
                })
            return results
        except Exception as e:
            LOGS.error(f"Nyaa fetch error: {e}")
            return []

    def extract_episode(self, title: str) -> int | None:
        patterns = [
            r"[\s\-_]+(\d{2,3})[\s\[\(]",
            r"[Ee][Pp]?[\s\._]*(\d+)",
            r"[Ss]\d+[Ee](\d+)",
            r"\[(\d{2,3})\]",
        ]
        for pattern in patterns:
            m = re.search(pattern, title)
            if m:
                return int(m.group(1))
        return None

    def detect_quality(self, title: str) -> str:
        for q in ["1080p", "720p", "480p", "360p"]:
            if q.lower() in title.lower():
                return q
        return "Unknown"

    def detect_type(self, title: str) -> str:
        tl = title.lower()
        if re.search(r"\b(dub|dubbed|english.?audio|eng.?dub)\b", tl):
            return "Dub"
        if re.search(r"\b(hardsub|hard.?sub|hsub)\b", tl):
            return "HSub"
        return "Sub"

    async def search_episodes(
        self,
        anime_title: str,
        quality: str,
        sub_type: str,
        alt_title: str = "",
    ) -> dict:
        queries = []
        base = anime_title

        if sub_type == "Dub":
            queries.append(f"{base} dub {quality}")
            queries.append(f"{base} dubbed {quality}")
            if alt_title:
                queries.append(f"{alt_title} dub {quality}")
        elif sub_type == "HSub":
            queries.append(f"{base} hardsub {quality}")
            queries.append(f"{base} {quality}")
            if alt_title:
                queries.append(f"{alt_title} hardsub {quality}")
        else:
            queries.append(f"{base} {quality}")
            if alt_title:
                queries.append(f"{alt_title} {quality}")

        all_results = []
        seen = set()
        for q in queries:
            results = await self._fetch_rss(q)
            for r in results:
                if r["magnet"] and r["magnet"] not in seen:
                    seen.add(r["magnet"])
                    all_results.append(r)

        episode_map = {}
        for r in all_results:
            ep = self.extract_episode(r["title"])
            if ep is None:
                continue
            q = self.detect_quality(r["title"])
            t = self.detect_type(r["title"])

            if quality != "All" and q != quality:
                continue
            if sub_type != "All" and t != sub_type:
                continue

            if ep not in episode_map:
                episode_map[ep] = []
            episode_map[ep].append({**r, "detected_quality": q, "detected_type": t})

        for ep in episode_map:
            episode_map[ep].sort(key=lambda x: x["seeders"], reverse=True)

        return episode_map

    async def search_single_episode(
        self,
        anime_title: str,
        episode: int,
        quality: str,
        sub_type: str,
        alt_title: str = "",
    ) -> dict | None:
        ep_str = f"{episode:02d}"
        queries = []

        if sub_type == "Dub":
            queries.append(f"{anime_title} - {ep_str} dub {quality}")
            queries.append(f"{anime_title} {ep_str} dub {quality}")
            if alt_title:
                queries.append(f"{alt_title} - {ep_str} dub {quality}")
        elif sub_type == "HSub":
            queries.append(f"{anime_title} - {ep_str} hardsub")
            queries.append(f"{anime_title} {ep_str} {quality}")
        else:
            queries.append(f"{anime_title} - {ep_str} {quality}")
            queries.append(f"{anime_title} {ep_str} {quality}")
            if alt_title:
                queries.append(f"{alt_title} - {ep_str} {quality}")

        for q in queries:
            results = await self._fetch_rss(q)
            for r in results:
                if not r["magnet"]:
                    continue
                ep_found = self.extract_episode(r["title"])
                if ep_found != episode:
                    continue
                t = self.detect_type(r["title"])
                detected_q = self.detect_quality(r["title"])
                if sub_type != "All" and t != sub_type:
                    continue
                if quality != "All" and detected_q != quality:
                    continue
                return {**r, "detected_quality": detected_q, "detected_type": t}
        return None
