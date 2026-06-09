"""Pydantic schemas for the structured output the generator must return per level.

These are validation / LLM-output models (Pydantic) — distinct from the SQLAlchemy
table models in app/db/models.py. The generator is forced to return data in this shape.
"""

from enum import Enum

from pydantic import BaseModel, Field


class Level(str, Enum):
    just_starting = "just_starting"
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class VocabItem(BaseModel):
    word: str
    translation: str


class VerbItem(BaseModel):
    # Conjugated form exactly as it appears in the story, e.g. "murieron" (the unit we track).
    surface_form: str
    # Dictionary form, e.g. "morir".
    lemma: str
    tense: str
    mood: str
    translation: str
    # Example sentence taken verbatim from the story (validated against story_text).
    example_sentence_target: str
    example_sentence_en: str


class GrammarItem(BaseModel):
    surface_form: str
    lemma: str
    tense: str
    mood: str
    translation: str


class StoryLevelOutput(BaseModel):
    """Everything the model returns for a single difficulty level."""

    level: Level
    title_target: str
    title_en: str | None = None      # omitted at advanced
    summary_en: str | None = None    # omitted at advanced
    story_text: str
    # Displayed script sections — empty at advanced (which shows only title + story).
    vocab: list[VocabItem] = Field(default_factory=list)
    verbs: list[VerbItem] = Field(default_factory=list)
    # Internal verb-tracking list ("La gramática de la historia - no para grabar").
    # NOT part of the recorded script. Produced for EVERY level, including advanced.
    grammar: list[GrammarItem] = Field(default_factory=list)
