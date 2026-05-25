"""Testes do dominio puro."""

import pytest

from vgb.domain.entities import Edition, SearchTarget
from vgb.domain.enums import EditionStatus
from vgb.domain.value_objects import Cargo, HashSHA256, Nome


class TestNome:
    def test_normalizacao(self) -> None:
        nome = Nome("João Silva")
        assert nome.normalizado() == "JOAO SILVA"

    def test_vazio_lanca_erro(self) -> None:
        with pytest.raises(ValueError):
            Nome("")


class TestHashSHA256:
    def test_from_bytes(self) -> None:
        h = HashSHA256.from_bytes(b"hello")
        assert len(h.valor) == 64

    def test_hash_invalido(self) -> None:
        with pytest.raises(ValueError):
            HashSHA256("curto")


class TestEdition:
    def test_criacao(self) -> None:
        ed = Edition.from_scrape(url="http://x.pdf", title="DO")
        assert ed.status == EditionStatus.PENDING

    def test_marcar_downloaded(self) -> None:
        ed = Edition.from_scrape(url="http://x.pdf", title="DO")
        ed.mark_downloaded(b"pdfdata")
        assert ed.status == EditionStatus.ANALYZING
        assert ed.size_bytes == 7
        assert ed.hash is not None


class TestSearchTarget:
    def test_match_nome(self) -> None:
        target = SearchTarget(nome=Nome("Maria"), cargo=Cargo("Engenheiro"))
        assert target.matches_nome("NOMEIA MARIA SILVA")
        assert not target.matches_cargo("NOMEIA MARIA SILVA")

    def test_match_cargo(self) -> None:
        target = SearchTarget(nome=Nome("Maria"), cargo=Cargo("Engenheiro"))
        assert target.matches_cargo("CARGO DE ENGENHEIRO")
