"""Generate a story level and repair it until it passes the validators.

This ties the generator agent together with the deterministic checks: generate,
validate, and if there are problems, send them back to the same model to fix —
looping up to `max_attempts` times.
"""

from dataclasses import dataclass

from app.agents.generator import generate_level, repair_level
from app.language.base import LanguageProfile
from app.pipeline.validate import validate_level
from app.schemas.story import StoryLevelOutput


@dataclass
class GenerationResult:
    level: StoryLevelOutput
    issues: list[str]   # remaining problems after the loop ([] means fully valid)
    attempts: int       # how many model calls it took
    passed: bool        # True if the final level has no validator issues


def generate_validated_level(
    profile: LanguageProfile,
    level_key: str,
    topic: str,
    model: str | None = None,
    max_attempts: int = 5,
    context: str | None = None,
) -> GenerationResult:
    """Generate one level, then repair until it validates or attempts run out.

    `context` (brief + sources + prior saved levels) is passed through to both the
    initial generation and every repair so the model stays grounded and consistent.
    """
    rule = profile.level(level_key)

    level = generate_level(profile, level_key, topic, model=model, context=context)
    issues = validate_level(level, rule)
    attempts = 1

    while issues and attempts < max_attempts:
        level = repair_level(
            profile, level_key, topic, level, issues, model=model, context=context
        )
        issues = validate_level(level, rule)
        attempts += 1

    return GenerationResult(
        level=level, issues=issues, attempts=attempts, passed=not issues
    )
