"""Schemas for the story brief: the shared narrative plan + per-level scope.

The brief is the "what to say" produced from the sources, edited by the creator,
and later fed into per-level generation. It is stored as JSON on stories.brief.
"""

from pydantic import BaseModel


class LevelScopes(BaseModel):
    """How much of the story each difficulty level covers / emphasizes."""

    just_starting: str
    beginner: str
    intermediate: str
    advanced: str


class StoryBrief(BaseModel):
    overview: str  # the shared narrative: key facts, grounded in the sources
    angle: str     # the anti-imperialist / emotional framing to carry through
    spine: str     # the recurring refrain / throughline tying the levels together
    levels: LevelScopes


class BriefSourceInput(BaseModel):
    """One source's content fed into brief generation (extracted text or snippet)."""

    title: str = ""
    url: str = ""
    content: str
