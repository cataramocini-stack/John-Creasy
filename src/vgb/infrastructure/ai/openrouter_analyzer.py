"""Analisador usando OpenRouter (fallback gratuito)."""

import base64
import json
import time
from typing import Any

import structlog
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from vgb.application.ports.ai_analyzer import AIAnalysisResult, AIOccurrence, PDFAnalyzer
from vgb.domain.entities import SearchTarget
from vgb.domain.enums import ActType, AnalysisModel, OccurrenceType
from vgb.domain.exceptions import AnaliseIndisponivelError
from vgb.infrastructure.config import Settings

logger = structlog.get_logger()


class _OccurrenceSchema(BaseModel):
    type: str = Field(description="Um de: NOME, CARGO, BOTH")
    context: str = Field(
        description="Resumo conciso do ato em linguagem natural. Maximo 300 caracteres. "
        "Exemplo: 'Gabriel de Oliveira foi nomeado para o cargo de Apoio de Saneamento.'"
    )
    page: int | None = Field(description="Numero da pagina, se identificavel", default=None)
    confidence: float = Field(description="Confianca de 0.0 a 1.0")
    act_type: str = Field(description="Um de: NOMEACAO, EXONERACAO, DESIGNACAO, LICENCA, OUTRO")


class _ResultSchema(BaseModel):
    found: bool = Field(description="True se encontrou o nome ou cargo em contexto relevante")
    occurrences: list[_OccurrenceSchema] = Field(default_factory=list)


class OpenRouterAnalyzer(PDFAnalyzer):
    """Analisa PDFs via OpenRouter usando modelos gratuitos compatíveis com OpenAI."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        if not settings.openrouter_api_key:
            raise AnaliseIndisponivelError("OpenRouter API key nao configurada")

        self._client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.openrouter_api_key.get_secret_value(),
        )
        self._model = "deepseek/deepseek-v4-flash:free"

    async def analyze(self, pdf_bytes: bytes, target: SearchTarget) -> AIAnalysisResult:
        start = time.monotonic()
        logger.info("openrouter.analyze.start", nome=target.nome.valor, cargo=target.cargo.valor)

        try:
            b64 = base64.standard_b64encode(pdf_bytes).decode("ascii")
            messages: list[dict[str, Any]] = [
                {
                    "role": "system",
                    "content": (
                        "Voce e um assistente juridico especializado em Diarios Oficiais municipais. "
                        "Analise o PDF fornecido e retorne um JSON valido."
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": self._build_prompt(target),
                        },
                        {
                            "type": "file",
                            "file": {
                                "filename": "diario.pdf",
                                "data": b64,
                            },
                        },
                    ],
                },
            ]

            response = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,  # type: ignore[arg-type]
                temperature=0.1,
                max_tokens=2048,
            )

            raw_text = response.choices[0].message.content or "{}"
            # OpenRouter pode retornar markdown codeblock
            raw_text = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            parsed = json.loads(raw_text)
            result = _ResultSchema.model_validate(parsed)

            occurrences = [
                AIOccurrence(
                    type=(
                        OccurrenceType(o.type.lower())
                        if o.type.lower() in {e.value for e in OccurrenceType}
                        else OccurrenceType.NOME
                    ),
                    context=o.context,
                    page=o.page,
                    confidence=max(0.0, min(1.0, o.confidence)),
                    act_type=(
                        ActType(o.act_type.lower())
                        if o.act_type.lower() in {e.value for e in ActType}
                        else ActType.OUTRO
                    ),
                )
                for o in result.occurrences
            ]

            elapsed_ms = int((time.monotonic() - start) * 1000)
            logger.info(
                "openrouter.analyze.done",
                found=result.found,
                occurrences=len(occurrences),
                elapsed_ms=elapsed_ms,
            )

            return AIAnalysisResult(
                found=result.found,
                occurrences=occurrences,
                raw_response=raw_text,
                model_used=AnalysisModel.OPENROUTER_FREE.value,
                confidence_score=max((o.confidence for o in occurrences), default=0.0),
                processing_time_ms=elapsed_ms,
            )
        except Exception as exc:
            logger.error("openrouter.analyze.error", error=str(exc))
            raise AnaliseIndisponivelError(f"OpenRouter falhou: {exc}") from exc

    def _build_prompt(self, target: SearchTarget) -> str:
        return (
            f"Analise este Diario Oficial e verifique se ha atos relevantes.\n\n"
            f"Nome a buscar: {target.nome.valor}\n"
            f"Cargo de interesse: {target.cargo.valor}\n\n"
            f"Instrucoes:\n"
            f"- act_type: NOMEACAO (nomear/nomeia-se), EXONERACAO (exonerar/exonera-se), "
            f"DESIGNACAO (designar/designa-se), LICENCA (licenca/afastamento), OUTRO (apenas se nao encaixar).\n"
            f"- context: em vez de trecho exato, gere um resumo conciso em portugues explicando "
            f"o que aconteceu com a pessoa/cargo. Exemplo: 'Gabriel de Oliveira foi nomeado para "
            f"o cargo de Agente de Apoio de Saneamento mediante portaria nº 123/2026.' "
            f"Maximo 300 caracteres.\n"
            f"- Retorne JSON com: found (bool), occurrences (array com type, context, page, confidence, act_type). "
            f"'found' deve ser true apenas para atos administrativos."
        )
