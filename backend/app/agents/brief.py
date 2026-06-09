"""Brief agent: turn source content into a shared narrative brief + per-level scope.

Reads the extracted text of the selected sources (plus any pasted content) and
produces a StoryBrief: one overview/angle/spine shared across the whole story, and
a short scope note per difficulty level. This is the "what to say" the creator
edits before any Spanish is generated.
"""

from pydantic_ai import Agent

# Reuse the DeepSeek model builder from the generator (same provider + key).
from app.agents.generator import _build_model
from app.config import settings
from app.schemas.brief import BriefSourceInput, StoryBrief

_SYSTEM_PROMPT = (
    "You plan a short historical story that will be told to language learners at "
    "four difficulty levels (Just Starting, Beginner, Intermediate, Advanced). You "
    "produce a BRIEF — the plan for what to say — NOT the story itself, and you write "
    "the brief in English.\n\n"
    "Ground everything strictly in the provided sources and pasted content; do not "
    "invent facts. Carry a subtle anti-imperialist, Indigenous-centered perspective: "
    "surface injustice and the human cost honestly, but do not be heavy-handed or "
    "preachy.\n\n"
    "Produce:\n"
    "- overview: the shared narrative — the key facts, people, places and events that "
    "matter, in a few tight paragraphs.\n"
    "- angle: the emotional and anti-imperialist framing to carry through every level.\n"
    "- spine: a single recurring image or refrain that ties the levels together.\n"
    "- levels: a short scope note for each level describing how much of the story it "
    "covers and what to emphasize. Difficulty rises across levels:\n"
    "  - just_starting: the simplest possible frame — a few concrete facts only.\n"
    "  - beginner: a little more of the arc, still simple and concrete.\n"
    "  - intermediate: cause and effect, more actors and context.\n"
    "  - advanced: the full account, including consequences and nuance."
)


def _build_user_prompt(
    topic: str, sources: list[BriefSourceInput], pasted_text: str
) -> str:
    parts = [f"Topic: {topic}\n"]
    for i, s in enumerate(sources, start=1):
        header = s.title or s.url or f"Source {i}"
        parts.append(f"--- SOURCE {i}: {header} ({s.url}) ---\n{s.content}\n")
    if pasted_text.strip():
        parts.append(f"--- PASTED CONTENT (creator-provided) ---\n{pasted_text}\n")
    parts.append("\nWrite the brief now.")
    return "\n".join(parts)


def generate_brief(
    topic: str,
    sources: list[BriefSourceInput],
    pasted_text: str = "",
    model: str | None = None,
) -> StoryBrief:
    """Synthesize a StoryBrief from the topic, source content and pasted text."""
    agent = Agent(
        _build_model(model or settings.generator_model),
        output_type=StoryBrief,
        system_prompt=_SYSTEM_PROMPT,
    )
    return agent.run_sync(_build_user_prompt(topic, sources, pasted_text)).output


if __name__ == "__main__":
    from app.pipeline.extract import extract_sources

    topic = "the fall of Tenochtitlan"
    url = "https://en.wikipedia.org/wiki/The_Broken_Spears"
    extracted = extract_sources([url])
    srcs = [BriefSourceInput(title="The Broken Spears", url=url, content=extracted[url])]
    brief = generate_brief(topic, srcs)
    print("OVERVIEW:\n", brief.overview, "\n")
    print("ANGLE:\n", brief.angle, "\n")
    print("SPINE:\n", brief.spine, "\n")
    print("LEVELS:")
    for key in ("just_starting", "beginner", "intermediate", "advanced"):
        print(f"  [{key}] {getattr(brief.levels, key)}")
