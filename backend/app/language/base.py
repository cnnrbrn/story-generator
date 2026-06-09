"""LanguageProfile: everything language-specific the pipeline needs, in one place.

Isolating these rules is what lets us add Brazilian Portuguese and Zulu later by
writing a new profile rather than changing the pipeline.
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class LevelRule:
    key: str                      # e.g. "just_starting"
    label_en: str                 # e.g. "Just Starting"
    # Displayed *script* sections (vocab + verbs list + english title/summary).
    # False at advanced, which records only the target-language title + story.
    # NB: the internal grammar verb-tracking list is produced for every level regardless.
    has_sections: bool
    # Intermediate and Advanced localise section headings into the target language.
    headings_localized: bool
    # Count rule for the displayed "verbs from the story" list. None when there's no section.
    verb_section_min: int | None
    verb_section_max: int | None
    # Intermediate: the verbs section lists only forms not shown in earlier levels.
    new_verbs_only: bool
    # Advanced: the story must include at least one subjunctive verb.
    requires_subjunctive: bool
    # Advanced: rough floor on how many verbs the story itself should contain.
    min_story_verbs: int | None


@dataclass(frozen=True)
class LanguageProfile:
    code: str                     # e.g. "es-LA"
    name: str                     # e.g. "Latin American Spanish"
    profile_key: str              # matches Language.profile_key, e.g. "spanish"
    guidelines: str               # full system-prompt guidelines text
    levels: list[LevelRule]
    # Optional per-level worked examples (level key -> example text) for few-shot prompting.
    # A field with a mutable default must use default_factory on a (frozen) dataclass.
    examples: dict[str, str] = field(default_factory=dict)

    def level(self, key: str) -> LevelRule:
        for rule in self.levels:
            if rule.key == key:
                return rule
        raise KeyError(f"Unknown level: {key}")


def load_guidelines(filename: str) -> str:
    """Read a guidelines markdown file from app/language/guidelines/."""
    path = Path(__file__).parent / "guidelines" / filename
    return path.read_text(encoding="utf-8")


def load_example(relpath: str) -> str:
    """Read an example file from app/language/examples/ (e.g. 'es/beginner.md')."""
    path = Path(__file__).parent / "examples" / relpath
    return path.read_text(encoding="utf-8")
