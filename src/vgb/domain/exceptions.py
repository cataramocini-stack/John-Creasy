"""Excecoes do dominio."""


class DomainError(Exception):
    """Erro base do dominio."""

    pass


class PDFInvalidoError(DomainError):
    """PDF corrompido ou ilegivel."""

    pass


class AnaliseIndisponivelError(DomainError):
    """Nenhum servico de analise (IA ou OCR) disponivel."""

    pass


class LimiteTamanhoExcedidoError(DomainError):
    """PDF excede o tamanho maximo permitido."""

    pass
