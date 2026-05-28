"""Enumeracoes do dominio."""

from enum import StrEnum


class EditionStatus(StrEnum):
    """Status de processamento de uma edicao do Diario Oficial."""

    PENDING = "pending"
    DOWNLOADING = "downloading"
    ANALYZING = "analyzing"
    PROCESSED = "processed"
    FAILED = "failed"


class OccurrenceType(StrEnum):
    """Tipo de ocorrencia encontrada no documento."""

    NOME = "nome"
    CARGO = "cargo"
    BOTH = "both"


class AnalysisModel(StrEnum):
    """Modelo de IA utilizado na analise."""

    GEMINI_25_FLASH = "gemini-2.5-flash"
    OPENROUTER_FREE = "openrouter-free"
    OCR_LOCAL = "ocr-local"
