"""Latin American Spanish (es-LA) language profile.

The grammar list is internal verb-tracking ("no para grabar") — produced for every
level including advanced, but never part of the recorded script.

Verb-section counts are encoded from the guidelines. Note two deliberate readings:
- Intermediate's verbs *section* lists only NEW forms (3-4); the cumulative total
  (up to ~10) lives in the grammar tracking list, not the displayed section.
- Advanced records only the Spanish title + story (no displayed sections). Its
  "15+ verbs incl. subjunctive" rule is checked against the grammar tracking list.
"""

from app.language.base import (
    LanguageProfile,
    LevelRule,
    load_example,
    load_guidelines,
)

SPANISH_PROFILE = LanguageProfile(
    code="es-LA",
    name="Latin American Spanish",
    profile_key="spanish",
    guidelines=load_guidelines("es.md"),
    levels=[
        LevelRule(
            key="just_starting",
            label_en="Just Starting",
            has_sections=True,
            headings_localized=False,
            verb_section_min=3,
            verb_section_max=3,  # strict: exactly 3
            new_verbs_only=False,
            requires_subjunctive=False,
            min_story_verbs=None,
        ),
        LevelRule(
            key="beginner",
            label_en="Beginner",
            has_sections=True,
            headings_localized=False,
            verb_section_min=5,  # the same 3 + 2-3 new
            verb_section_max=6,
            new_verbs_only=False,
            requires_subjunctive=False,
            min_story_verbs=None,
        ),
        LevelRule(
            key="intermediate",
            label_en="Intermediate",
            has_sections=True,
            headings_localized=True,
            verb_section_min=3,  # only NEW forms shown (3-4)
            verb_section_max=4,
            new_verbs_only=True,
            requires_subjunctive=False,
            min_story_verbs=None,
        ),
        LevelRule(
            key="advanced",
            label_en="Advanced",
            has_sections=False,  # title + story only
            headings_localized=True,
            verb_section_min=None,
            verb_section_max=None,
            new_verbs_only=False,
            requires_subjunctive=True,
            min_story_verbs=15,
        ),
    ],
    examples={
        "just_starting": load_example("es/just_starting.md"),
        "beginner": load_example("es/beginner.md"),
        "intermediate": load_example("es/intermediate.md"),
        # No advanced example provided yet.
    },
)
