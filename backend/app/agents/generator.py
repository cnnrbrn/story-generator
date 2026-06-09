"""Generator agent: turns a topic into one structured story level via an LLM.

We build a Pydantic AI `Agent` bound to a model, a system prompt, and an output
schema (`StoryLevelOutput`). Calling it returns data already validated against
that schema.
"""

from pydantic_ai import Agent
from pydantic_ai.models import Model
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.providers.deepseek import DeepSeekProvider

from app.config import settings
from app.language.base import LanguageProfile, LevelRule
from app.language.spanish import SPANISH_PROFILE
from app.schemas.story import StoryLevelOutput


# Functions prefixed with "_" are a convention for "internal helper, not the public API".
def _build_model(model: str) -> Model:
    # Route by model id: claude-* → Anthropic, everything else → DeepSeek.
    if model.startswith("claude"):
        return AnthropicModel(
            model,
            provider=AnthropicProvider(api_key=settings.anthropic_api_key),
        )
    # DeepSeek speaks the OpenAI Chat Completions API, so we use the OpenAI chat
    # model class with the DeepSeek provider (sets the base URL + our API key).
    return OpenAIChatModel(
        model,
        provider=DeepSeekProvider(api_key=settings.deepseek_api_key),
    )


def _level_instructions(rule: LevelRule) -> str:
    # Build the level-specific rules from the profile data (see app/language).
    # `lines` is a list of strings we join at the end with newlines.
    lines = [f'You are writing the "{rule.label_en}" level.']
    if rule.has_sections:
        lines.append(
            "Produce: Spanish title, English title, English summary, a vocabulary "
            "list, a verbs list, the story in Spanish, and the grammar tracking list."
        )
        lines.append(
            "Keep the English summary to ONE short sentence conveying the gist — "
            "users should hear as little English as possible."
        )
    else:
        lines.append(
            "Output ONLY the Spanish title and the story in Spanish. Leave "
            "title_en, summary_en, vocab and verbs empty. Still produce the "
            "grammar tracking list of every verb in the story."
        )
    if rule.verb_section_min is not None:
        if rule.verb_section_min == rule.verb_section_max:
            lines.append(
                f"The verbs section must contain EXACTLY {rule.verb_section_min} verbs."
            )
        else:
            lines.append(
                f"The verbs section must contain between {rule.verb_section_min} "
                f"and {rule.verb_section_max} verbs."
            )
    if rule.has_sections and not rule.new_verbs_only and rule.verb_section_max is not None:
        n = rule.verb_section_max
        lines.append(
            f"#### THE MOST IMPORTANT RULE: ONLY {n} VERB FORMS IN THE WHOLE STORY ####\n"
            f"The entire story may contain at most {n} DISTINCT conjugated verb forms — "
            "no more, ever. This rule beats completeness: it is more important than "
            "telling the full story.\n"
            f"- Different conjugations of the same verb are DIFFERENT forms and each "
            "uses up one of your slots. 'tenía' and 'tenían' are two forms; 'era' and "
            "'eran' are two forms; 'lucharon' and 'luchó' are two forms. So pick ONE "
            "conjugation per verb and reuse that exact word everywhere.\n"
            f"- Before writing, CHOOSE your {n} verb forms. Then write the whole story "
            f"using ONLY those {n} words as verbs, repeating them often (as in the "
            "example, where 'había' recurs again and again).\n"
            f"- If a fact or detail would need a {n + 1}th verb form, DROP that detail. "
            "Leave it out. A shorter, simpler story with the right verb count is "
            "correct; a richer story with extra verbs is WRONG and will be rejected.\n"
            "- Every verb that appears anywhere in the story must also be in the verbs "
            "section. Do not introduce any other verbs."
        )
    if rule.new_verbs_only:
        lines.append(
            "In the verbs section, list only NEW verb forms not shown in earlier levels."
        )
    if rule.requires_subjunctive:
        lines.append("The story must include at least two subjunctive verbs.")
    if rule.min_story_verbs:
        lines.append(f"The story should contain at least {rule.min_story_verbs} verbs.")
    lines.append(
        "Every verb in the story must also appear in the grammar tracking list "
        "with its lemma, tense and mood. Use only commas and full stops; never "
        "use colons or em dashes."
    )
    # "\n".join(list) is like list.join("\n") in JS — glue the lines with newlines.
    return "\n".join(lines)


def _system_prompt(profile: LanguageProfile, rule: LevelRule) -> str:
    # f"..." is an f-string: a template literal. {expr} is interpolated.
    prompt = (
        f"You are an expert writer of {profile.name} history stories for language "
        "learners. Follow these guidelines exactly:\n\n"
        f"{profile.guidelines}\n\n"
        f"{_level_instructions(rule)}"
    )
    # Few-shot: if the profile has a worked example for this level, include it.
    # `.get(key)` returns None when the key is absent (advanced has no example).
    example = profile.examples.get(rule.key)
    if example:
        prompt += (
            f"\n\nEXAMPLE of a well-formed {rule.label_en} level. Match its "
            "structure, style, tone and rule-adherence. Adapt it to the requested "
            "topic; do not copy its sentences unless the topic is the same.\n\n"
            f"{example}"
        )
    return prompt


def _run_agent(
    profile: LanguageProfile, rule: LevelRule, user_prompt: str, model: str | None
) -> StoryLevelOutput:
    """Build the generator agent and run one prompt, returning the validated output."""
    # `a or b` returns b when a is falsy (None) — a common Python default pattern.
    agent = Agent(
        _build_model(model or settings.generator_model),
        output_type=StoryLevelOutput,  # force the model to return THIS shape
        system_prompt=_system_prompt(profile, rule),
    )
    # run_sync = the blocking call; `.output` is the validated StoryLevelOutput.
    return agent.run_sync(user_prompt).output


def generate_level(
    profile: LanguageProfile,
    level_key: str,
    topic: str,
    model: str | None = None,
    context: str | None = None,
) -> StoryLevelOutput:
    """Generate one story level from scratch. Returns a validated StoryLevelOutput.

    `model` defaults to settings.generator_model; the repair step reuses it.
    `context` (brief + sources + prior levels) is injected into the user prompt;
    the system prompt with the guidelines/rules is unchanged.
    """
    rule = profile.level(level_key)
    return _run_agent(profile, rule, _level_user_prompt(rule, topic, context), model)


def _level_user_prompt(rule: LevelRule, topic: str, context: str | None) -> str:
    """Build the user-facing prompt for an initial level generation."""
    prompt = f"Topic: {topic}\n"
    if context:
        prompt += f"\n{context}\n"
    prompt += (
        f"\nThe Spanish title (title_target) MUST be the topic exactly: {topic!r}. "
        "Set title_en to its English translation."
    )
    prompt += f"\nWrite the {rule.label_en} level now."
    return prompt


def generation_prompts(
    profile: LanguageProfile,
    level_key: str,
    topic: str,
    context: str | None = None,
) -> tuple[str, str]:
    """Return the exact (system_prompt, user_prompt) used to generate this level.

    Pure string-building (no LLM call), so endpoints can show the creator what
    was sent to the model.
    """
    rule = profile.level(level_key)
    return _system_prompt(profile, rule), _level_user_prompt(rule, topic, context)


def repair_level(
    profile: LanguageProfile,
    level_key: str,
    topic: str,
    previous: StoryLevelOutput,
    issues: list[str],
    model: str | None = None,
    context: str | None = None,
) -> StoryLevelOutput:
    """Regenerate a level, telling the model exactly what to fix.

    Sends the previous attempt and the concrete validator problems back to the
    same model so it can correct them while keeping what was already right.
    `context` (same brief/sources/prior levels) rides along so repairs stay grounded.
    """
    rule = profile.level(level_key)
    issue_text = "\n".join(f"- {i}" for i in issues)
    context_block = f"\n{context}\n" if context else ""
    prompt = (
        f"Topic: {topic}\n"
        f"{context_block}"
        f"Your previous attempt at the {rule.label_en} level had these problems:\n"
        f"{issue_text}\n\n"
        "Here is your previous attempt as JSON:\n"
        f"{previous.model_dump_json(indent=2)}\n\n"
        "Produce a corrected version that fixes ALL of the problems above while "
        "keeping everything that was already correct. Return the full level."
    )
    return _run_agent(profile, rule, prompt, model)


# Runs only when executed directly: `python -m app.agents.generator`
if __name__ == "__main__":
    level = generate_level(
        SPANISH_PROFILE, "just_starting", "Cerro Rico, the silver mountain of Potosi"
    )
    print("TITLE (es):", level.title_target)
    print("TITLE (en):", level.title_en)
    print("SUMMARY  :", level.summary_en)
    print("\nSTORY:\n", level.story_text)
    print("\nVERBS:")
    for v in level.verbs:
        print(f"  - {v.surface_form} ({v.lemma}, {v.tense}/{v.mood}) = {v.translation}")
        print(f"      e.g. {v.example_sentence_target}")
    # A list comprehension: [expr for x in items] — like items.map(x => expr).
    print("\nVOCAB:", [f"{x.word}={x.translation}" for x in level.vocab])
    print("GRAMMAR (tracking):", [f"{g.surface_form}->{g.lemma}" for g in level.grammar])
