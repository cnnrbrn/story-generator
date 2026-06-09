"""Database read/write helpers for stories and their sources.

Plain functions that take a Session (from app.db.session.get_db) and the data to
persist. Endpoints call these so the SQL lives in one place, not in the routers.
"""

from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import (
    GrammarEntry,
    Source,
    Story,
    StoryLevel,
    VerbEntry,
    VocabularyEntry,
)
from app.schemas.source import SourceItem
from app.schemas.story import StoryLevelOutput


def create_story(
    db: Session,
    *,
    topic: str,
    language_code: str,
    sources: list[SourceItem],
    pasted_text: str,
) -> Story:
    """Create a draft Story plus its source rows (web selections + pasted text)."""
    story = Story(topic_text=topic, language_code=language_code, status="draft")
    db.add(story)
    db.flush()  # assigns story.id without committing yet

    now = datetime.now(timezone.utc)
    for s in sources:
        db.add(
            Source(
                story_id=story.id,
                type="web",
                title=s.title or None,
                url=s.url,
                citation_text=s.snippet or None,  # the snippet is our citation text
                retrieved_at=now,
            )
        )
    # Freeform pasted content is stored as a single "manual" source.
    if pasted_text.strip():
        db.add(
            Source(
                story_id=story.id,
                type="manual",
                title="Pasted content",
                citation_text=pasted_text,
            )
        )

    db.commit()
    db.refresh(story)
    return story


def get_story(db: Session, story_id: int) -> Story | None:
    """Fetch a single story by id (or None)."""
    return db.get(Story, story_id)


def save_brief(
    db: Session, story: Story, brief: dict, prompt: dict | None = None
) -> Story:
    """Store (or overwrite) the brief JSON on a story.

    `prompt` is the {system, user} that generated it; passed on generation, omitted
    on a human edit (so the original generation prompt is preserved).
    """
    story.brief = brief
    if prompt is not None:
        story.brief_prompt = prompt
    db.commit()
    db.refresh(story)
    return story


def get_sources(db: Session, story_id: int) -> list[Source]:
    """All sources for a story, oldest first."""
    return list(
        db.scalars(
            select(Source).where(Source.story_id == story_id).order_by(Source.id)
        ).all()
    )


def get_levels(db: Session, story_id: int) -> list[StoryLevel]:
    """All saved levels for a story, in creation order."""
    return list(
        db.scalars(
            select(StoryLevel)
            .where(StoryLevel.story_id == story_id)
            .order_by(StoryLevel.id)
        ).all()
    )


def get_vocab(db: Session, story_level_id: int) -> list[VocabularyEntry]:
    return list(
        db.scalars(
            select(VocabularyEntry)
            .where(VocabularyEntry.story_level_id == story_level_id)
            .order_by(VocabularyEntry.position)
        ).all()
    )


def get_verbs(db: Session, story_level_id: int) -> list[VerbEntry]:
    return list(
        db.scalars(
            select(VerbEntry)
            .where(VerbEntry.story_level_id == story_level_id)
            .order_by(VerbEntry.position)
        ).all()
    )


def get_grammar(db: Session, story_level_id: int) -> list[GrammarEntry]:
    return list(
        db.scalars(
            select(GrammarEntry).where(GrammarEntry.story_level_id == story_level_id)
        ).all()
    )


def save_level(
    db: Session, story_id: int, level_key: str, output: StoryLevelOutput
) -> StoryLevel:
    """Upsert a story level and replace its vocab/verb/grammar entries.

    Re-saving the same level bumps its version and clears the old child rows first.
    """
    lvl = db.scalar(
        select(StoryLevel).where(
            StoryLevel.story_id == story_id, StoryLevel.level == level_key
        )
    )
    if lvl is None:
        lvl = StoryLevel(story_id=story_id, level=level_key, version=1)
        db.add(lvl)
    else:
        lvl.version += 1
        for model in (VocabularyEntry, VerbEntry, GrammarEntry):
            db.execute(delete(model).where(model.story_level_id == lvl.id))

    lvl.title_target = output.title_target
    lvl.title_en = output.title_en
    lvl.summary_en = output.summary_en
    lvl.story_text = output.story_text
    lvl.status = "saved"
    db.flush()  # ensure lvl.id is available for the child rows

    for i, v in enumerate(output.vocab):
        db.add(
            VocabularyEntry(
                story_level_id=lvl.id,
                word=v.word,
                translation=v.translation,
                position=i,
            )
        )
    for i, vb in enumerate(output.verbs):
        db.add(
            VerbEntry(
                story_level_id=lvl.id,
                surface_form=vb.surface_form,
                lemma=vb.lemma,
                tense=vb.tense,
                mood=vb.mood,
                translation=vb.translation,
                example_sentence_target=vb.example_sentence_target,
                example_sentence_en=vb.example_sentence_en,
                position=i,
            )
        )
    for g in output.grammar:
        db.add(
            GrammarEntry(
                story_level_id=lvl.id,
                surface_form=g.surface_form,
                lemma=g.lemma,
                tense=g.tense,
                mood=g.mood,
                translation=g.translation,
            )
        )

    db.commit()
    db.refresh(lvl)
    return lvl
