"""Database read/write helpers for stories and their sources.

Plain functions that take a Session (from app.db.session.get_db) and the data to
persist. Endpoints call these so the SQL lives in one place, not in the routers.
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Source, Story
from app.schemas.source import SourceItem


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


def get_sources(db: Session, story_id: int) -> list[Source]:
    """All sources for a story, oldest first."""
    return list(
        db.scalars(
            select(Source).where(Source.story_id == story_id).order_by(Source.id)
        ).all()
    )
