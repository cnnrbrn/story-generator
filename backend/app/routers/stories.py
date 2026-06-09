"""Story endpoints: create a draft story from selected sources, and read it back."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import crud
from app.db.session import get_db
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
