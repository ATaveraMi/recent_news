from __future__ import annotations

from typing import Dict, List
from urllib.parse import quote_plus
from urllib.request import urlopen, Request
import xml.etree.ElementTree as ET
import logging

logger = logging.getLogger(__name__)


class DataAgent:
    """Retrieves recent news from multiple public RSS sources."""

    def __init__(self, user_agent: str = "Reportero/1.0 (+https://localhost)"):
        self.user_agent = user_agent

    def _http_get(self, url: str) -> bytes:
        req = Request(url, headers={"User-Agent": f"Mozilla/5.0 {self.user_agent}"})
        with urlopen(req, timeout=10) as resp:
            return resp.read()

    def _parse_rss(self, content: bytes, source_name: str) -> List[Dict]:
        items: List[Dict] = []
        try:
            root = ET.fromstring(content)
        except ET.ParseError:
            return items

        # RSS: <rss><channel><item>...</item></channel></rss>
        channel = root.find("channel")
        if channel is not None:
            for item in channel.findall("item"):
                title_elem = item.find("title")
                link_elem = item.find("link")
                desc_elem = item.find("description")
                title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""
                link = link_elem.text.strip() if link_elem is not None and link_elem.text else ""
                description = desc_elem.text.strip() if desc_elem is not None and desc_elem.text else ""
                if title and link:
                    items.append({"title": title, "url": link, "snippet": description, "source": source_name})
            return items

        # Atom: <feed><entry>...</entry></feed>
        for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
            title_elem = entry.find("{http://www.w3.org/2005/Atom}title")
            link_elem = entry.find("{http://www.w3.org/2005/Atom}link")
            summary_elem = entry.find("{http://www.w3.org/2005/Atom}summary")
            href = link_elem.get("href") if link_elem is not None else ""
            title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""
            summary = summary_elem.text.strip() if summary_elem is not None and summary_elem.text else ""
            if title and href:
                items.append({"title": title, "url": href, "snippet": summary, "source": source_name})
        return items

    def _search_google_news(self, query: str) -> List[Dict]:
        url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
        try:
            content = self._http_get(url)
            return self._parse_rss(content, "Google News")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Google News fetch failed: %s", exc)
            return []

    def _search_bing_news(self, query: str) -> List[Dict]:
        url = f"https://www.bing.com/news/search?q={quote_plus(query)}&format=rss"
        try:
            content = self._http_get(url)
            return self._parse_rss(content, "Bing News")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Bing News fetch failed: %s", exc)
            return []

    def search_news(self, query: str, max_items: int = 6) -> List[Dict]:
        """Return up to max_items news items aggregated from two sources."""
        seen: set = set()
        combined: List[Dict] = []
        for item in self._search_google_news(query) + self._search_bing_news(query):
            key = item.get("url") or item.get("title")
            if key and key not in seen:
                seen.add(key)
                combined.append(item)
            if len(combined) >= max_items:
                break
        return combined


