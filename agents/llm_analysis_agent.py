from __future__ import annotations

from typing import Dict, List
from pydantic import BaseModel, Field
from openai import OpenAI
import json


class NewsReport(BaseModel):
    summary: str = Field(..., description="Resumen claro y útil (2–5 párrafos) con contexto, riesgos y señales.")
    links: List[str] = Field(default_factory=list, description="Lista de URLs en orden de relevancia (sin duplicados).")


class LLMAnalysisAgent:
    """
    Agente de análisis impulsado por LLM usando OpenAI Python SDK.
    Siempre usa un modelo LLM para generar el reporte tipado (NewsReport).
    Requiere OPENAI_API_KEY en el entorno.
    """

    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.client = OpenAI()
        self.model_name = model_name

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
        system_prompt = (
            "Eres un analista financiero. Dado un conjunto de artículos recientes, "
            "redacta un informe conciso y útil (2–5 párrafos) con contexto, riesgos, "
            "señales a observar y catalizadores probables. Al final, no repitas títulos; "
            "devuelve solo un JSON con 'summary' (string) y 'links' (array de URLs)."
        )
        user_prompt = (
            f"Tema: {query}\n\n"
            f"Artículos (título — fuente, snippet, url):\n{self._to_bullets(items)}\n\n"
            "Responde exclusivamente en formato JSON válido con las claves:\n"
            '{ "summary": string, "links": string[] }'
        )
        resp = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )
        content = resp.choices[0].message.content or "{}"
        try:
            data = json.loads(content)
            report = NewsReport.model_validate(data)
        except Exception:
            # fallback: wrap raw text
            report = NewsReport(summary=content, links=[it.get("url", "") for it in items if it.get("url")])

        output_lines: List[str] = [report.summary.strip()]
        links = [u for u in (report.links or []) if u]
        if links:
            output_lines.append("\nLinks:")
            output_lines.extend(links)
        output_lines.append("\nVerifica detalles en las fuentes.")
        return "\n".join(output_lines)


