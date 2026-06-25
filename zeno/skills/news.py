"""
Zeno News Skill — fetches headlines from RSS feeds.
No external dependencies: uses stdlib urllib + xml.etree.
"""

import urllib.request
import xml.etree.ElementTree as ET
from zeno.skills.base import BaseSkill
from zeno.nlu.entity import Entities
from zeno.core.context import Context
from zeno.memory.store import get_store

_DEFAULT_FEED = "https://feeds.bbci.co.uk/news/rss.xml"
_MAX_HEADLINES = 3
_TIMEOUT = 6


class NewsSkill(BaseSkill):
    intents = ["news_query"]

    def handle(self, intent: str, entities: Entities, context: Context) -> str:
        store = get_store()
        feed_url = store.get("news.feed_url", _DEFAULT_FEED)

        try:
            req = urllib.request.Request(
                feed_url,
                headers={"User-Agent": "Zeno/1.0"},
            )
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                raw = resp.read()

            headlines = self._parse_headlines(raw)
            if not headlines:
                return self.say("Found the feed but no headlines. Maybe the world is quiet today.")

            parts = ["Here are the latest headlines:"]
            for i, h in enumerate(headlines, 1):
                parts.append(f"{i}. {h}")
            return self.say(" ".join(parts))

        except ET.ParseError:
            return self.say("Couldn't parse the news feed. Might be using alien formats.")
        except urllib.error.URLError:
            return self.say("Can't reach the news feed right now. Check your connection.")
        except Exception as e:
            return self.say(f"News check failed: {e}")

    def _parse_headlines(self, raw: bytes) -> list[str]:
        root = ET.fromstring(raw)
        headlines = []

        # RSS 2.0: /rss/channel/item/title
        # Atom: /feed/entry/title
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        for item in root.iterfind("channel/item/title"):
            if item.text:
                headlines.append(item.text.strip())
                if len(headlines) >= _MAX_HEADLINES:
                    break

        if not headlines:
            for entry in root.iterfind("atom:entry/atom:title", ns):
                if entry.text:
                    headlines.append(entry.text.strip())
                    if len(headlines) >= _MAX_HEADLINES:
                        break

        return headlines
