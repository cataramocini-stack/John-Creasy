"""Implementacoes concretas dos repositorios."""

from collections.abc import Sequence

from sqlalchemy import desc, select
from sqlalchemy.orm import selectinload

from vgb.application.ports.repository import AnalysisRepository, EditionRepository
from vgb.domain.entities import Analysis, Edition, Occurrence
from vgb.domain.enums import ActType, AnalysisModel, EditionStatus, OccurrenceType
from vgb.domain.value_objects import HashSHA256
from vgb.infrastructure.storage.database import Database
from vgb.infrastructure.storage.models import AnalysisORM, EditionORM, OccurrenceORM


def _edition_to_domain(orm: EditionORM) -> Edition:
    return Edition(
        id=orm.id,
        url=orm.url,
        title=orm.title,
        published_at=orm.published_at,
        hash=HashSHA256(orm.hash_sha256) if orm.hash_sha256 else None,
        size_bytes=orm.size_bytes,
        status=EditionStatus(orm.status),
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def _edition_to_orm(domain: Edition) -> EditionORM:
    return EditionORM(
        id=domain.id,
        url=domain.url,
        title=domain.title,
        published_at=domain.published_at,
        hash_sha256=domain.hash.valor if domain.hash else None,
        size_bytes=domain.size_bytes,
        status=domain.status.value,
        created_at=domain.created_at,
        updated_at=domain.updated_at,
    )


def _occurrence_to_domain(orm: OccurrenceORM) -> Occurrence:
    return Occurrence(
        id=orm.id,
        analysis_id=orm.analysis_id,
        type=OccurrenceType(orm.type),
        context_snippet=orm.context_snippet,
        page_hint=orm.page_hint,
        confidence=orm.confidence,
        act_type=ActType(orm.act_type),
        created_at=orm.created_at,
    )


def _analysis_to_domain(orm: AnalysisORM) -> Analysis:
    return Analysis(
        id=orm.id,
        edition_id=orm.edition_id,
        model_used=AnalysisModel(orm.model_used),
        raw_response=orm.raw_response,
        structured_result=orm.structured_result,
        confidence_score=orm.confidence_score,
        processing_time_ms=orm.processing_time_ms,
        created_at=orm.created_at,
        occurrences=[_occurrence_to_domain(o) for o in orm.occurrences],
    )


class SqlAlchemyEditionRepository(EditionRepository):
    def __init__(self, db: Database) -> None:
        self._db = db

    async def get_by_hash(self, hash_: HashSHA256) -> Edition | None:
        async with self._db.session_factory() as session:
            result = await session.execute(select(EditionORM).where(EditionORM.hash_sha256 == hash_.valor))
            orm = result.scalar_one_or_none()
            return _edition_to_domain(orm) if orm else None

    async def get_by_url(self, url: str) -> Edition | None:
        async with self._db.session_factory() as session:
            result = await session.execute(select(EditionORM).where(EditionORM.url == url))
            orm = result.scalar_one_or_none()
            return _edition_to_domain(orm) if orm else None

    async def save(self, edition: Edition) -> Edition:
        async with self._db.session_factory() as session:
            if edition.id is None:
                orm = _edition_to_orm(edition)
                session.add(orm)
                await session.commit()
                await session.refresh(orm)
                edition.id = orm.id
            else:
                existing = await session.get(EditionORM, edition.id)
                if existing:
                    existing.url = edition.url
                    existing.title = edition.title
                    existing.published_at = edition.published_at
                    existing.hash_sha256 = edition.hash.valor if edition.hash else None
                    existing.size_bytes = edition.size_bytes
                    existing.status = edition.status.value
                    existing.updated_at = edition.updated_at
                    await session.commit()
            return edition

    async def list_recent(self, limit: int = 20) -> Sequence[Edition]:
        async with self._db.session_factory() as session:
            result = await session.execute(select(EditionORM).order_by(desc(EditionORM.created_at)).limit(limit))
            return [_edition_to_domain(orm) for orm in result.scalars().all()]


class SqlAlchemyAnalysisRepository(AnalysisRepository):
    def __init__(self, db: Database) -> None:
        self._db = db

    async def save(self, analysis: Analysis) -> Analysis:
        async with self._db.session_factory() as session:
            if analysis.id is None:
                orm = AnalysisORM(
                    edition_id=analysis.edition_id,
                    model_used=analysis.model_used.value,
                    raw_response=analysis.raw_response,
                    structured_result=analysis.structured_result,
                    confidence_score=analysis.confidence_score,
                    processing_time_ms=analysis.processing_time_ms,
                )
                session.add(orm)
                await session.commit()
                await session.refresh(orm)
                analysis.id = orm.id

                for occ in analysis.occurrences:
                    occ_orm = OccurrenceORM(
                        analysis_id=orm.id,
                        type=occ.type.value,
                        context_snippet=occ.context_snippet,
                        page_hint=occ.page_hint,
                        confidence=occ.confidence,
                        act_type=occ.act_type.value,
                    )
                    session.add(occ_orm)
                await session.commit()
            return analysis

    async def get_by_edition(self, edition_id: int) -> Analysis | None:
        async with self._db.session_factory() as session:
            result = await session.execute(
                select(AnalysisORM)
                .where(AnalysisORM.edition_id == edition_id)
                .options(selectinload(AnalysisORM.occurrences))
            )
            orm = result.scalar_one_or_none()
            return _analysis_to_domain(orm) if orm else None
