"""Story endpoints: create a draft story from selected sources, and read it back."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.brief import brief_prompts, generate_brief
from app.agents.generator import generation_prompts
from app.db import crud
from app.db.session import get_db
from app.language.spanish import SPANISH_PROFILE
from app.pipeline.context import build_context
from app.pipeline.extract import extract_sources
from app.pipeline.generate import generate_validated_level
from app.pipeline.validate import validate_level
from app.schemas.brief import BriefSourceInput, StoryBrief
from app.schemas.source import SourceItem
from app.schemas.story import GrammarItem, StoryLevelOutput, VerbItem, VocabItem

# Level keys in difficulty order (defines which levels count as "prior").
LEVEL_ORDER = [rule.key for rule in SPANISH_PROFILE.levels]

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


class LevelOut(BaseModel):
    level: str
    title_target: str | None
    title_en: str | None
    summary_en: str | None
    story_text: str | None
    status: str
    version: int
    vocab: list[VocabItem]
    verbs: list[VerbItem]
    grammar: list[GrammarItem]


class StoryDetail(BaseModel):
    id: int
    topic_text: str
    language_code: str
    status: str
    brief: dict | None
    brief_prompt: dict | None
    sources: list[SourceOut]
    levels: list[LevelOut]


class PromptPreview(BaseModel):
    """The exact prompt sent to the model, for display in the UI."""

    system: str
    user: str


class BriefResponse(BaseModel):
    brief: StoryBrief
    prompt: PromptPreview


class GenerateLevelResponse(BaseModel):
    level: StoryLevelOutput  # the generated draft (not yet saved)
    issues: list[str]        # validator findings (advisory)
    passed: bool
    attempts: int
    prompt: PromptPreview


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

    levels: list[LevelOut] = []
    for lvl in crud.get_levels(db, story_id):
        levels.append(
            LevelOut(
                level=lvl.level,
                title_target=lvl.title_target,
                title_en=lvl.title_en,
                summary_en=lvl.summary_en,
                story_text=lvl.story_text,
                status=lvl.status,
                version=lvl.version,
                vocab=[
                    VocabItem(word=v.word, translation=v.translation)
                    for v in crud.get_vocab(db, lvl.id)
                ],
                verbs=[
                    VerbItem(
                        surface_form=vb.surface_form,
                        lemma=vb.lemma,
                        tense=vb.tense,
                        mood=vb.mood,
                        translation=vb.translation,
                        example_sentence_target=vb.example_sentence_target,
                        example_sentence_en=vb.example_sentence_en,
                    )
                    for vb in crud.get_verbs(db, lvl.id)
                ],
                grammar=[
                    GrammarItem(
                        surface_form=g.surface_form,
                        lemma=g.lemma,
                        tense=g.tense,
                        mood=g.mood,
                        translation=g.translation,
                    )
                    for g in crud.get_grammar(db, lvl.id)
                ],
            )
        )

    return StoryDetail(
        id=story.id,
        topic_text=story.topic_text,
        language_code=story.language_code,
        status=story.status,
        brief=story.brief,
        brief_prompt=story.brief_prompt,
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
        levels=levels,
    )


@router.post("/stories/{story_id}/brief", response_model=BriefResponse)
def create_brief(story_id: int, db: Session = Depends(get_db)) -> BriefResponse:
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
    system, user = brief_prompts(story.topic_text, brief_sources, pasted_text)
    prompt = {"system": system, "user": user}
    crud.save_brief(db, story, brief.model_dump(), prompt=prompt)
    return BriefResponse(brief=brief, prompt=PromptPreview(**prompt))


@router.post(
    "/stories/{story_id}/levels/{level_key}/generate",
    response_model=GenerateLevelResponse,
)
def generate_level(
    story_id: int, level_key: str, db: Session = Depends(get_db)
) -> GenerateLevelResponse:
    """Generate a draft for one level from the brief + sources + prior saved levels.

    Returns the draft and validator issues; does NOT persist (the creator edits and
    saves separately).
    """
    story = crud.get_story(db, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")
    if level_key not in LEVEL_ORDER:
        raise HTTPException(status_code=400, detail=f"Unknown level: {level_key}")
    if not story.brief:
        raise HTTPException(status_code=400, detail="Generate a brief first")

    sources = crud.get_sources(db, story_id)
    snippets = [
        (s.title or s.url or "", s.citation_text or "")
        for s in sources
        if s.type == "web"
    ]
    pasted_text = "\n\n".join(
        s.citation_text or "" for s in sources if s.type == "manual"
    )

    # Saved levels that come before this one in difficulty order.
    prior_keys = set(LEVEL_ORDER[: LEVEL_ORDER.index(level_key)])
    prior_levels: list[dict] = []
    for lvl in crud.get_levels(db, story_id):
        if lvl.level in prior_keys:
            prior_levels.append(
                {
                    "label": lvl.level,
                    "story_text": lvl.story_text or "",
                    "vocab_words": [v.word for v in crud.get_vocab(db, lvl.id)],
                    "example_sentences": [
                        vb.example_sentence_target for vb in crud.get_verbs(db, lvl.id)
                    ],
                }
            )

    context = build_context(
        brief=story.brief,
        level_key=level_key,
        snippets=snippets,
        pasted_text=pasted_text,
        prior_levels=prior_levels,
    )
    result = generate_validated_level(
        SPANISH_PROFILE, level_key, story.topic_text, context=context
    )
    # The Spanish title is the topic itself (entered in Spanish); enforce it.
    result.level.title_target = story.topic_text
    system, user = generation_prompts(
        SPANISH_PROFILE, level_key, story.topic_text, context
    )
    return GenerateLevelResponse(
        level=result.level,
        issues=result.issues,
        passed=result.passed,
        attempts=result.attempts,
        prompt=PromptPreview(system=system, user=user),
    )


class SaveLevelResponse(BaseModel):
    issues: list[str]  # validators re-run on the edited level (advisory)
    passed: bool


@router.put(
    "/stories/{story_id}/levels/{level_key}", response_model=SaveLevelResponse
)
def save_level(
    story_id: int,
    level_key: str,
    level: StoryLevelOutput,
    db: Session = Depends(get_db),
) -> SaveLevelResponse:
    """Save the creator's edited level; re-run validators and return advisory flags."""
    story = crud.get_story(db, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")
    if level_key not in LEVEL_ORDER:
        raise HTTPException(status_code=400, detail=f"Unknown level: {level_key}")

    crud.save_level(db, story_id, level_key, level)
    issues = validate_level(level, SPANISH_PROFILE.level(level_key))
    return SaveLevelResponse(issues=issues, passed=not issues)


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
