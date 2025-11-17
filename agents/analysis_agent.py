from __future__ import annotations

from typing import Dict, List


class AnalysisAgent:
    """Produces a concise, readable summary from news items."""

    def summarize(self, query: str, items: List[Dict]) -> str:
        if not items:
            return f"No recent articles found for '{query}'. Try a different query."

        lines = [f"Recent developments for '{query}':"]
        for i, item in enumerate(items[:5], start=1):
            title = (item.get("title") or "").strip()
            url = (item.get("url") or "").strip()
            source = item.get("source") or "source"
            if title and url:
                lines.append(f"{i}. {title} — {source}\n   {url}")
        lines.append("\nPlease verify details with the linked sources.")
        return "\n".join(lines)


