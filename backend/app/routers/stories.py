"""Story endpoints: create a draft story from selected sources, and read it back."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.brief import generate_brief
from app.db import crud
from app.db.session import get_db
from app.pipeline.extract import extract_sources
from app.schemas.brief import BriefSourceInput, StoryBrief
from app.schemas.source import SourceItem

router = APIRouter(prefix="/api", tags=["stories"])


class CreateStoryRequest(BaseModel):
    topic: str
    language_code: str = "es-LA"
    sources: list[SourceItem] = []
    pasted_text: str = ""


class CreateStoryResponse(BaseModel):
    id: int


class SourceOut(BaseModel):
    id: int
    type: str
    title: str | None
    url: str | None
    citation_text: str | None


class StoryDetail(BaseModel):
    id: int
    topic_text: str
    language_code: str
    status: str
    brief: dict | None
    sources: list[SourceOut]


@router.post("/stories", response_model=CreateStoryResponse)
def create_story(req: CreateStoryRequest, db: Session = Depends(get_db)) -> CreateStoryResponse:
    """Persist a draft Story with its selected web sources + pasted content."""
    story = crud.create_story(
        db,
        topic=req.topic,
        language_code=req.language_code,
        sources=req.sources,
        pasted_text=req.pasted_text,
    )
    return CreateStoryResponse(id=story.id)


@router.get("/stories/{story_id}", response_model=StoryDetail)
def get_story(story_id: int, db: Session = Depends(get_db)) -> StoryDetail:
    """Return a story with its brief and sources (for reopening a draft)."""
    story = crud.get_story(db, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")
    sources = crud.get_sources(db, story_id)
    return StoryDetail(
        id=story.id,
        topic_text=story.topic_text,
        language_code=story.language_code,
        status=story.status,
        brief=story.brief,
        sources=[
            SourceOut(
                id=s.id,
                type=s.type,
                title=s.title,
                url=s.url,
                citation_text=s.citation_text,
            )
            for s in sources
        ],
    )


@router.post("/stories/{story_id}/brief", response_model=StoryBrief)
def create_brief(story_id: int, db: Session = Depends(get_db)) -> StoryBrief:
    """Extract the selected sources' full text and synthesize a brief; persist it."""
    story = crud.get_story(db, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")

    sources = crud.get_sources(db, story_id)

    # Web sources get their full page text via Tavily Extract (snippet as fallback);
    # the single "manual" source is the creator's pasted content.
    web = [s for s in sources if s.type == "web" and s.url]
    extracted = extract_sources([s.url for s in web])  # type: ignore[arg-type]
    brief_sources = [
        BriefSourceInput(
            title=s.title or "",
            url=s.url or "",
            content=extracted.get(s.url or "") or (s.citation_text or ""),
        )
        for s in web
    ]
    pasted_text = "\n\n".join(
        s.citation_text or "" for s in sources if s.type == "manual"
    )

    brief = generate_brief(story.topic_text, brief_sources, pasted_text)
    crud.save_brief(db, story, brief.model_dump())
    return brief


@router.put("/stories/{story_id}/brief", response_model=StoryBrief)
def update_brief(
    story_id: int, brief: StoryBrief, db: Session = Depends(get_db)
) -> StoryBrief:
    """Save the creator's edited brief."""
    story = crud.get_story(db, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")
    crud.save_brief(db, story, brief.model_dump())
    return brief
