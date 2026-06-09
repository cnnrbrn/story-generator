"""Deterministic validators — pure Python, no LLM, no cost.

Each check appends a human-readable problem to a shared `issues` list. An empty
list means the level passed every check here. These are the hard gates that keep
cheap models honest. (Cross-level checks — e.g. no repeated example sentences
across levels — come later, once we generate the 4 levels in sequence.)
"""

from app.language.base import LevelRule
from app.schemas.story import StoryLevelOutput

# Characters the audio rules forbid (colon, em dash).
_BANNED_PUNCTUATION = [":", "—"]


def validate_level(level: StoryLevelOutput, rule: LevelRule) -> list[str]:
    """Run every single-level check. Returns a list of problems ([] means OK)."""
    issues: list[str] = []
    _check_vocab_present(level, rule, issues)
    _check_verb_count(level, rule, issues)
    _check_story_verb_diversity(level, rule, issues)
    _check_examples_verbatim(level, issues)
    _check_verbs_in_grammar(level, issues)
    _check_punctuation(level, issues)
    return issues


def _check_vocab_present(
    level: StoryLevelOutput, rule: LevelRule, issues: list[str]
) -> None:
    # Levels with sections must include a vocabulary list; advanced has none.
    if rule.has_sections and not level.vocab:
        issues.append(f"{rule.label_en} is missing its vocabulary section.")


def _check_story_verb_diversity(
    level: StoryLevelOutput, rule: LevelRule, issues: list[str]
) -> None:
    # Just Starting / Beginner must list ALL the story's verbs, so the story itself
    # cannot contain more distinct verbs than the section allows. (Intermediate shows
    # only new verbs, and advanced has no section, so this rule does not apply there.)
    if not (rule.has_sections and not rule.new_verbs_only):
        return
    if rule.verb_section_max is None:
        return
    # grammar tracks every verb in the story; count distinct conjugated forms.
    distinct_forms = {g.surface_form for g in level.grammar}
    if len(distinct_forms) > rule.verb_section_max:
        issues.append(
            f"Story uses {len(distinct_forms)} distinct verbs, but {rule.label_en} "
            f"allows at most {rule.verb_section_max} (every story verb must appear in "
            "the verbs section)."
        )


def _check_verb_count(level: StoryLevelOutput, rule: LevelRule, issues: list[str]) -> None:
    # Advanced has no verbs section (min/max are None there).
    if rule.verb_section_min is None or rule.verb_section_max is None:
        if level.verbs:
            issues.append("Advanced level should have an empty verbs section.")
        return
    # After this guard the type checker knows both bounds are plain ints.
    n = len(level.verbs)
    # Chained comparison: Python lets you write a <= x <= b directly.
    if not (rule.verb_section_min <= n <= rule.verb_section_max):
        issues.append(
            f"Verbs section has {n} verbs; expected "
            f"{rule.verb_section_min}-{rule.verb_section_max}."
        )


def _check_examples_verbatim(level: StoryLevelOutput, issues: list[str]) -> None:
    for v in level.verbs:
        # `in` on a string is a substring test (≈ story_text.includes(...)).
        if v.example_sentence_target not in level.story_text:
            issues.append(
                f"Example for '{v.surface_form}' is not verbatim in the story: "
                f"{v.example_sentence_target!r}"  # !r shows the repr (quoted) form
            )


def _check_verbs_in_grammar(level: StoryLevelOutput, issues: list[str]) -> None:
    # A set comprehension — like new Set(level.grammar.map(g => g.surface_form)).
    grammar_forms = {g.surface_form for g in level.grammar}
    for v in level.verbs:
        if v.surface_form not in grammar_forms:
            issues.append(f"Verb '{v.surface_form}' is missing from the grammar list.")


def _check_punctuation(level: StoryLevelOutput, issues: list[str]) -> None:
    # A dict (≈ a JS object): field name -> its text. .items() yields (key, value) pairs.
    fields = {
        "title_target": level.title_target,
        "summary_en": level.summary_en,
        "story_text": level.story_text,
    }
    for name, text in fields.items():
        if not text:  # skip None / empty (e.g. summary is empty at advanced)
            continue
        for ch in _BANNED_PUNCTUATION:
            if ch in text:
                issues.append(f"Field '{name}' contains banned character {ch!r}.")
