"""Render a StoryLevelOutput into the final, recordable script text.

The structured data (separate fields) is formatted here into the layout the
guidelines require. Section headings localise into the target language at
intermediate/advanced (rule.headings_localized).

NOTE: the heading strings below are Spanish-specific. When we add Portuguese/Zulu
they should move into the LanguageProfile; kept here for now while es-LA is the
only language.
"""

from app.language.base import LevelRule
from app.schemas.story import GrammarItem, StoryLevelOutput, VerbItem

_HEADINGS = {
    False: {  # Just Starting / Beginner — English headings
        "vocab": "Vocabulary from the story",
        "verbs": "Verbs from the story",
        "story": "Now, the story",
    },
    True: {  # Intermediate (+) — target-language headings
        "vocab": "Vocabulario de la historia",
        "verbs": "Verbos de la historia",
        "story": "Ahora, la historia",
    },
}
_GRAMMAR_HEADING = "La gramática de la historia (no para grabar)"


def _render_verb(v: VerbItem) -> str:
    # "verb. translation. <Spanish example> <English example>"
    return (
        f"{v.surface_form}. {v.translation}. "
        f"{v.example_sentence_target} {v.example_sentence_en}"
    )


def _render_grammar(g: GrammarItem) -> str:
    # "verb - translation - tense mood (lemma)"
    return f"{g.surface_form} - {g.translation} - {g.tense} {g.mood} ({g.lemma})"


def render_level(level: StoryLevelOutput, rule: LevelRule) -> str:
    parts: list[str] = [level.title_target]

    # Advanced: only the target-language title + the story.
    if not rule.has_sections:
        parts += ["", level.story_text]
        return "\n".join(parts)

    h = _HEADINGS[rule.headings_localized]

    if level.title_en:
        parts.append(level.title_en)
    if level.summary_en:
        parts += ["", level.summary_en]

    if level.vocab:
        parts += ["", h["vocab"]]
        parts += [f"{item.word} - {item.translation}" for item in level.vocab]

    if level.verbs:
        parts += ["", h["verbs"]]
        parts += [_render_verb(v) for v in level.verbs]

    parts += ["", h["story"], level.story_text]

    if level.grammar:
        parts += ["", _GRAMMAR_HEADING]
        parts += [_render_grammar(g) for g in level.grammar]

    return "\n".join(parts)
