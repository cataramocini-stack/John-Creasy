"""Value objects imutaveis do dominio."""

from dataclasses import dataclass
from typing import Self


@dataclass(frozen=True, slots=True)
class Nome:
    """Nome da pessoa a ser monitorada."""

    valor: str

    def __post_init__(self) -> None:
        if not self.valor or not self.valor.strip():
            raise ValueError("Nome nao pode ser vazio")

    def normalizado(self) -> str:
        """Retorna versao normalizada para comparacoes."""
        import unicodedata

        txt = unicodedata.normalize("NFKD", self.valor)
        txt = txt.encode("ascii", "ignore").decode("ascii")
        return txt.upper().strip()


@dataclass(frozen=True, slots=True)
class Cargo:
    """Cargo de interesse."""

    valor: str

    def __post_init__(self) -> None:
        if not self.valor or not self.valor.strip():
            raise ValueError("Cargo nao pode ser vazio")

    def normalizado(self) -> str:
        """Retorna versao normalizada para comparacoes."""
        import unicodedata

        txt = unicodedata.normalize("NFKD", self.valor)
        txt = txt.encode("ascii", "ignore").decode("ascii")
        return txt.upper().strip()


@dataclass(frozen=True, slots=True)
class HashSHA256:
    """Hash SHA-256 de um arquivo."""

    valor: str

    def __post_init__(self) -> None:
        if len(self.valor) != 64:
            raise ValueError("Hash SHA-256 invalido")

    @classmethod
    def from_bytes(cls, data: bytes) -> Self:
        import hashlib

        return cls(hashlib.sha256(data).hexdigest())
