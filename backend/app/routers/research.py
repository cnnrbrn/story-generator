"""Research endpoint: take a topic, return perspective-tagged web sources.

Thin HTTP wrapper around `app.pipeline.research.research_topic`. The pipeline call
is synchronous and takes ~10-20s (it plans queries with an LLM, then hits Tavily);
defining the handler with `def` (not `async def`) lets FastAPI run it in a threadpool
so the event loop isn't blocked.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.pipeline.research import research_topic
from app.schemas.source import SourceItem

router = APIRouter(prefix="/api", tags=["research"])


class ResearchRequest(BaseModel):
    topic: str


class ResearchResponse(BaseModel):
    topic: str
    sources: list[SourceItem]


@router.post("/research", response_model=ResearchResponse)
def research(req: ResearchRequest) -> ResearchResponse:
    """Plan angled searches for `topic` and return deduped, tagged sources."""
    sources = research_topic(req.topic)
    return ResearchResponse(topic=req.topic, sources=sources)
