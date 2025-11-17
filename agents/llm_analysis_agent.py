from __future__ import annotations

from typing import Dict, List
from pydantic import BaseModel, Field
from pydantic_ai import Agent, models


class NewsReport(BaseModel):
    summary: str = Field(..., description="Resumen claro y útil (2–5 párrafos) con contexto, riesgos y señales.")
    links: List[str] = Field(default_factory=list, description="Lista de URLs en orden de relevancia (sin duplicados).")


class LLMAnalysisAgent:
    """
    Agente de análisis impulsado por LLM vía pydantic-ai.
    Siempre usa un modelo LLM para generar el reporte tipado (NewsReport).
    Requiere OPENAI_API_KEY en el entorno.
    """

    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.agent = Agent(
            model=models.openai(model_name),
            system_prompt=(
                "Eres un analista financiero. Dado un conjunto de artículos recientes, "
                "redacta un informe conciso y útil (2–5 párrafos) con contexto, riesgos, "
                "señales a observar y catalizadores probables. Al final, no repitas títulos; "
                "incluye solo la lista de URLs en 'links' (sin duplicados)."
            ),
        )

    def _to_bullets(self, items: List[Dict]) -> str:
        lines: List[str] = []
        for it in items[:6]:
            title = (it.get("title") or "").strip()
            source = (it.get("source") or "").strip()
            snippet = (it.get("snippet") or "").strip()
            url = (it.get("url") or "").strip()
            if title:
                lines.append(f"- {title} — {source}\n  {snippet}\n  {url}")
        return "\n".join(lines)

    def summarize(self, query: str, items: List[Dict]) -> str:
        if not items:
            return f"No se encontraron artículos recientes para '{query}'."
        prompt = (
            f"Tema: {query}\n\n"
            f"Artículos (título — fuente, snippet, url):\n{self._to_bullets(items)}\n\n"
            "Devuelve un NewsReport pydantic con 'summary' bien redactado y 'links' "
            "solo con las URLs (sin duplicados)."
        )
        result = self.agent.run_sync(prompt, result_type=NewsReport)
        report = result.data
        output_lines: List[str] = [report.summary.strip()]
        links = [u for u in (report.links or []) if u]
        if links:
            output_lines.append("\nLinks:")
            output_lines.extend(links)
        output_lines.append("\nVerifica detalles en las fuentes.")
        return "\n".join(output_lines)


