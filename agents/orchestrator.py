from __future__ import annotations

from typing import Dict, List, Optional
import os
import smtplib
from email.message import EmailMessage
import asyncio

from .data_agent import DataAgent
from .analysis_agent import AnalysisAgent


class Orchestrator:
    """Coordinates the workflow: retrieve → analyze → optionally email."""

    def __init__(self, data_agent: DataAgent, analysis_agent: AnalysisAgent):
        self.data_agent = data_agent
        self.analysis_agent = analysis_agent

    async def run_workflow(self, query: str, email_to: Optional[str] = None) -> Dict:
        items = await asyncio.to_thread(self.data_agent.search_news, query, 6)
        summary = self.analysis_agent.summarize(query, items)
        sources_out: List[Dict] = [
            {"title": it.get("title", ""), "url": it.get("url", ""), "source": it.get("source", "")}
            for it in items
        ]

        emailed = False
        if email_to:
            subject = f"News summary: {query}"
            body = summary
            await asyncio.to_thread(self._send_email, email_to, subject, body)
            emailed = True

        return {
            "query": query,
            "status": "workflow completed",
            "summary": summary,
            "sources": sources_out,
            "emailed": emailed,
        }

    def _send_email(self, to_address: str, subject: str, body: str) -> None:
        host = os.getenv("SMTP_HOST")
        port = int(os.getenv("SMTP_PORT", "587"))
        user = os.getenv("SMTP_USER")
        password = os.getenv("SMTP_PASSWORD")
        from_address = os.getenv("SMTP_FROM", user or "")
        starttls = os.getenv("SMTP_STARTTLS", "true").lower() in ("1", "true", "yes", "on")

        if not host or not user or not password:
            raise RuntimeError("SMTP config missing. Set SMTP_HOST, SMTP_USER, SMTP_PASSWORD in .env")

        msg = EmailMessage()
        msg["From"] = from_address or user
        msg["To"] = to_address
        msg["Subject"] = subject
        msg.set_content(body)

        with smtplib.SMTP(host, port, timeout=15) as server:
            if starttls:
                server.starttls()
            server.login(user, password)
            server.send_message(msg)


