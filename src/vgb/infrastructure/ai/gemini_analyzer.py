"""Analisador usando Google Gemini 2.5 Flash (multimodal)."""

import time

import structlog
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from vgb.application.ports.ai_analyzer import AIAnalysisResult, AIOccurrence, PDFAnalyzer
from vgb.domain.entities import SearchTarget
from vgb.domain.enums import ActType, AnalysisModel, OccurrenceType
from vgb.domain.exceptions import AnaliseIndisponivelError
from vgb.infrastructure.config import Settings

logger = structlog.get_logger()


class _OccurrenceSchema(BaseModel):
    type: str = Field(description="Um de: NOME, CARGO, BOTH")
    context: str = Field(description="Trecho exato do documento com ate 200 caracteres")
    page: int | None = Field(description="Numero da pagina, se identificavel", default=None)
    confidence: float = Field(description="Confianca de 0.0 a 1.0")
    act_type: str = Field(description="Um de: NOMEACAO, EXONERACAO, DESIGNACAO, LICENCA, OUTRO")


class _ResultSchema(BaseModel):
    found: bool = Field(description="True se encontrou o nome ou cargo em contexto relevante")
    occurrences: list[_OccurrenceSchema] = Field(default_factory=list)


class GeminiAnalyzer(PDFAnalyzer):
    """Analisa PDFs usando Google Gemini multimodal com structured output."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        if not settings.gemini_api_key:
            raise AnaliseIndisponivelError("Gemini API key nao configurada")

        self._client = genai.Client(api_key=settings.gemini_api_key.get_secret_value())

    async def analyze(self, pdf_bytes: bytes, target: SearchTarget) -> AIAnalysisResult:
        start = time.monotonic()
        logger.info("gemini.analyze.start", nome=target.nome.valor, cargo=target.cargo.valor)

        try:
            prompt = self._build_prompt(target)
            response = await self._client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=types.Content(
                    parts=[
                        types.Part.from_text(text=prompt),
                        types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                    ]
                ),
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=_ResultSchema,
                    temperature=0.1,
                    max_output_tokens=2048,
                ),
            )

            raw_text = response.text or "{}"
            result = _ResultSchema.model_validate_json(raw_text)

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
                "gemini.analyze.done",
                found=result.found,
                occurrences=len(occurrences),
                elapsed_ms=elapsed_ms,
            )

            return AIAnalysisResult(
                found=result.found,
                occurrences=occurrences,
                raw_response=raw_text,
                model_used=AnalysisModel.GEMINI_25_FLASH.value,
                confidence_score=max((o.confidence for o in occurrences), default=0.0),
                processing_time_ms=elapsed_ms,
            )
        except Exception as exc:
            logger.error("gemini.analyze.error", error=str(exc))
            raise AnaliseIndisponivelError(f"Gemini falhou: {exc}") from exc

    def _build_prompt(self, target: SearchTarget) -> str:
        return (
            "Voce e um assistente juridico especializado em Diarios Oficiais municipais. "
            "Analise este Diario Oficial e verifique se ha atos de nomeacao, exoneracao, "
            "designacao, licenca ou outras referencias relevantes.\n\n"
            f"Nome a buscar: {target.nome.valor}\n"
            f"Cargo de interesse: {target.cargo.valor}\n\n"
            "Instrucoes:\n"
            "- 'found' deve ser true APENAS se o nome ou cargo aparecem em contexto administrativo "
            "  relevante (ex: nomeacao, exoneracao, designacao, portaria), NAO em listas de presenca "
            "  ou simples mencoes.\n"
            "- Para cada ocorrencia, forneca o trecho exato (context), pagina (page) e tipo de ato (act_type).\n"
            "- confidence deve refletir a certeza de que se trata de um ato administrativo relevante.\n"
            "- Retorne JSON valido seguindo o schema fornecido."
        )
