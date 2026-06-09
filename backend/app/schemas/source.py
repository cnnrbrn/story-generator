"""Pydantic schemas for research: planned search queries and the sources found."""

from pydantic import BaseModel


class SourceItem(BaseModel):
    title: str
    url: str
    snippet: str = ""              # short excerpt, used as the citation text
    perspective: str = "mainstream"  # "mainstream" or "anti_imperialist"


class SearchQuery(BaseModel):
    query: str
    # "mainstream" = factual baseline; "anti_imperialist" = Indigenous/decolonial angle.
    perspective: str


class ResearchPlan(BaseModel):
    """The set of searches the researcher decided to run for a topic."""

    queries: list[SearchQuery]
