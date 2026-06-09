"""Database table definitions (SQLAlchemy models).

Each class here maps to one table; each ``mapped_column`` is a column.
Alembic reads these models to autogenerate migrations.

Deferred to the RAG step: ``document_chunks`` (needs a pgvector column whose size
depends on the chosen embedding model) and enabling the pgvector extension.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Language(Base):
    __tablename__ = "languages"

    # Short code used everywhere to identify the language, e.g. "es-LA". Primary key.
    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    # Human-readable name, e.g. "Latin American Spanish".
    name: Mapped[str] = mapped_column(String(100))
    # Which LanguageProfile implementation handles this language, e.g. "spanish".
    profile_key: Mapped[str] = mapped_column(String(50))
    # Whether this language is currently offered to creators.
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Story(Base):
    __tablename__ = "stories"

    # Auto-incrementing integer primary key.
    id: Mapped[int] = mapped_column(primary_key=True)
    # The historical topic the creator entered (free text, can be long → Text).
    topic_text: Mapped[str] = mapped_column(Text)
    # Foreign key: this value must match an existing languages.code row.
    language_code: Mapped[str] = mapped_column(ForeignKey("languages.code"))
    # Pipeline status; defaults to "draft" if not set on insert.
    status: Mapped[str] = mapped_column(String(20), default="draft")
    # Chosen models per role, stored as JSON. Nullable until generation is configured.
    # (Named model_settings, not model_config — Pydantic reserves "model_config".)
    model_settings: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # The shared narrative brief + per-level scope (StoryBrief), as JSON.
    # Nullable until the brief has been generated.
    brief: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Who created it (no auth yet, so nullable for now).
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Timestamps filled in by the database itself.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class StoryLevel(Base):
    __tablename__ = "story_levels"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Parent story this level belongs to.
    story_id: Mapped[int] = mapped_column(ForeignKey("stories.id"))
    # One of: just_starting | beginner | intermediate | advanced.
    level: Mapped[str] = mapped_column(String(20))
    # Title in the target language (e.g. Spanish). Filled in as the level is generated.
    title_target: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # English title.
    title_en: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # English summary of the story.
    summary_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    # The story itself, in the target language.
    story_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    # Bumped each time this level is regenerated.
    version: Mapped[int] = mapped_column(default=1)


class VocabularyEntry(Base):
    __tablename__ = "vocabulary_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    story_level_id: Mapped[int] = mapped_column(ForeignKey("story_levels.id"))
    word: Mapped[str] = mapped_column(String(100))
    translation: Mapped[str] = mapped_column(String(200))
    # Order of the word within the vocabulary list.
    position: Mapped[int] = mapped_column(default=0)


class VerbEntry(Base):
    """A verb shown in a level's 'Verbs from the story' section."""

    __tablename__ = "verb_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    story_level_id: Mapped[int] = mapped_column(ForeignKey("story_levels.id"))
    # The conjugated form as it appears, e.g. "murieron" (this is the unit we track).
    surface_form: Mapped[str] = mapped_column(String(100))
    # The dictionary form, e.g. "morir".
    lemma: Mapped[str] = mapped_column(String(100))
    tense: Mapped[str] = mapped_column(String(50))
    mood: Mapped[str] = mapped_column(String(50))
    translation: Mapped[str] = mapped_column(String(200))
    # Example sentence taken verbatim from the story (validated against story_text).
    example_sentence_target: Mapped[str] = mapped_column(Text)
    example_sentence_en: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column(default=0)


class GrammarEntry(Base):
    """Full end-of-story grammar list (a superset of the verbs section)."""

    __tablename__ = "grammar_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    story_level_id: Mapped[int] = mapped_column(ForeignKey("story_levels.id"))
    surface_form: Mapped[str] = mapped_column(String(100))
    lemma: Mapped[str] = mapped_column(String(100))
    tense: Mapped[str] = mapped_column(String(50))
    mood: Mapped[str] = mapped_column(String(50))
    translation: Mapped[str] = mapped_column(String(200))


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    story_id: Mapped[int] = mapped_column(ForeignKey("stories.id"))
    # web | upload | manual
    type: Mapped[str] = mapped_column(String(20))
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    author: Mapped[str | None] = mapped_column(String(300), nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    citation_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    retrieved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class SourceDocument(Base):
    """An uploaded file (PDF/doc) the creator provided as source material."""

    __tablename__ = "source_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    story_id: Mapped[int] = mapped_column(ForeignKey("stories.id"))
    filename: Mapped[str] = mapped_column(String(500))
    mime: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Where the raw file is stored (object storage key / path); decided at the RAG step.
    storage_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")


class VerbLedger(Base):
    """Global usage counter per conjugated form, to steer cross-story variety."""

    __tablename__ = "verb_ledger"

    id: Mapped[int] = mapped_column(primary_key=True)
    language_code: Mapped[str] = mapped_column(ForeignKey("languages.code"))
    surface_form: Mapped[str] = mapped_column(String(100))
    lemma: Mapped[str] = mapped_column(String(100))
    tense: Mapped[str] = mapped_column(String(50))
    mood: Mapped[str] = mapped_column(String(50))
    level: Mapped[str] = mapped_column(String(20))
    usage_count: Mapped[int] = mapped_column(default=0)
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class VocabLedger(Base):
    """Global usage counter per vocabulary word, mirror of VerbLedger."""

    __tablename__ = "vocab_ledger"

    id: Mapped[int] = mapped_column(primary_key=True)
    language_code: Mapped[str] = mapped_column(ForeignKey("languages.code"))
    word: Mapped[str] = mapped_column(String(100))
    level: Mapped[str] = mapped_column(String(20))
    usage_count: Mapped[int] = mapped_column(default=0)
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class GenerationRun(Base):
    """Audit trail of every model call + validation/critique result in the pipeline."""

    __tablename__ = "generation_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Nullable: research/brief stages aren't tied to a specific level.
    story_level_id: Mapped[int | None] = mapped_column(
        ForeignKey("story_levels.id"), nullable=True
    )
    stage: Mapped[str] = mapped_column(String(50))
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    iteration: Mapped[int] = mapped_column(default=0)
    raw_output: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    validation_results: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    critic_results: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
