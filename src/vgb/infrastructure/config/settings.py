"""Configuracao tipada do aplicativo."""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Todas as configuracoes sao carregadas de variaveis de ambiente."""

    model_config = SettingsConfigDict(
        env_prefix="VGB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Alvos de busca
    nome_busca: str = Field(..., min_length=2, description="Nome da pessoa a monitorar")
    cargo_busca: str = Field(..., min_length=2, description="Cargo de interesse")

    # Notificacoes
    telegram_token: SecretStr
    telegram_chat_id: str

    # IA (opcionais — fallback para OCR local se ausentes)
    gemini_api_key: SecretStr | None = None
    openrouter_api_key: SecretStr | None = None

    # Fonte de documentos
    diario_url: str = Field(..., min_length=10, description="URL da pagina do diario oficial")
    diario_base_url: str = Field(..., min_length=10, description="URL base do diario oficial")

    # Limites
    max_pdfs_per_run: int = Field(default=8, ge=1, le=50)
    max_pdf_size_mb: int = Field(default=25, ge=1, le=100)
    max_pages_to_analyze: int = Field(default=80, ge=1, le=500)

    # Concorrencia
    http_workers: int = Field(default=4, ge=1, le=16)

    # Banco de dados
    database_url: str = Field(default="sqlite+aiosqlite:///vgb.db")

    # Logging
    log_level: str = Field(default="INFO")
    log_json: bool = Field(default=False)
