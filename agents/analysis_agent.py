from __future__ import annotations

from typing import Dict, List
import re
import html


class AnalysisAgent:
    """Produces a concise, readable summary from news items."""

    def summarize(self, query: str, items: List[Dict]) -> str:
        if not items:
            return f"No recent articles found for '{query}'. Try a different query."

        def clean_snippet(text: str, limit: int = 240) -> str:
            if not text:
                return ""
            # Remove HTML tags and unescape entities, collapse whitespace
            text = re.sub(r"<[^>]+>", " ", text)
            text = html.unescape(text)
            text = re.sub(r"\s+", " ", text).strip()
            if len(text) > limit:
                return text[:limit].rstrip() + "..."
            return text

        report_lines: List[str] = [f"What to expect for '{query}':"]

        # Descriptive bullets using snippets when available
        for item in items[:5]:
            title = (item.get("title") or "").strip()
            source = (item.get("source") or "source").strip()
            snippet = clean_snippet(item.get("snippet") or "")
            if snippet:
                report_lines.append(f"- {title} — {source}: {snippet}")
            else:
                report_lines.append(f"- {title} — {source}")

        # Append links at the end (no extra descriptions)
        urls = [it.get("url") or "" for it in items if it.get("url")]
        if urls:
            report_lines.append("\nLinks:")
            report_lines.extend(urls)

        report_lines.append("\nPlease verify details with the linked sources.")
        return "\n".join(report_lines)


