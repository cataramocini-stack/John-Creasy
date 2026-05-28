"""Analisador fallback usando PyMuPDF + fuzzy matching."""

import time
import unicodedata

import fitz
import structlog

from vgb.application.ports.ai_analyzer import AIAnalysisResult, AIOccurrence, PDFAnalyzer
from vgb.domain.entities import SearchTarget
from vgb.domain.enums import AnalysisModel, OccurrenceType

logger = structlog.get_logger()


class OcrAnalyzer(PDFAnalyzer):
    """Extrai texto com PyMuPDF e faz busca por substring com fuzzy matching."""

    def __init__(self, max_pages: int = 80) -> None:
        self._max_pages = max_pages

    async def analyze(self, pdf_bytes: bytes, target: SearchTarget) -> AIAnalysisResult:
        start = time.monotonic()
        logger.info("ocr.analyze.start")

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        try:
            nome_norm = target.nome.normalizado()
            cargo_norm = target.cargo.normalizado()
            occurrences: list[AIOccurrence] = []
            found = False

            limit = min(len(doc), self._max_pages)
            for page_num in range(limit):
                text = doc[page_num].get_text("text")
                text_norm = self._normalize(text)

                nome_hit = nome_norm in text_norm
                cargo_hit = cargo_norm in text_norm

                if nome_hit or cargo_hit:
                    found = True
                    occ_type = OccurrenceType.BOTH
                    if nome_hit and not cargo_hit:
                        occ_type = OccurrenceType.NOME
                    elif cargo_hit and not nome_hit:
                        occ_type = OccurrenceType.CARGO

                    idx = text_norm.find(nome_norm) if nome_hit else text_norm.find(cargo_norm)
                    ctx = text[max(0, idx - 100) : idx + 120] if idx >= 0 else text[:220]

                    occurrences.append(
                        AIOccurrence(
                            type=occ_type,
                            context=ctx.strip(),
                            page=page_num + 1,
                            confidence=0.5,
                        )
                    )
                    # Para no primeiro hit por pagina para evitar spam
                    break

            elapsed_ms = int((time.monotonic() - start) * 1000)
            logger.info("ocr.analyze.done", found=found, occurrences=len(occurrences), elapsed_ms=elapsed_ms)

            return AIAnalysisResult(
                found=found,
                occurrences=occurrences,
                raw_response="",
                model_used=AnalysisModel.OCR_LOCAL.value,
                confidence_score=0.5 if found else 0.0,
                processing_time_ms=elapsed_ms,
            )
        finally:
            doc.close()

    @staticmethod
    def _normalize(txt: str) -> str:
        txt = unicodedata.normalize("NFKD", txt)
        txt = txt.encode("ascii", "ignore").decode("ascii")
        return txt.upper().strip()
