"""Assemble the per-level generation context: brief + snippets + pasted + prior levels.

This string is injected into the generator's user prompt (the system prompt with the
guidelines/rules is unchanged). The brief is the content contract; web snippets are a
light factual anchor; pasted content is included in full (it's the creator's deliberate
input); prior saved levels steer cross-level continuity and de-dup.
"""


def build_context(
    *,
    brief: dict,
    level_key: str,
    snippets: list[tuple[str, str]],
    pasted_text: str,
    prior_levels: list[dict],
) -> str:
    lines: list[str] = ["=== BRIEF ==="]
    lines.append(f"Overview: {brief.get('overview', '')}")
    lines.append(f"Angle: {brief.get('angle', '')}")
    lines.append(f"Spine: {brief.get('spine', '')}")
    scope = (brief.get("levels") or {}).get(level_key, "")
    lines.append(f"Scope for THIS level: {scope}")

    if snippets:
        lines.append("\n=== SOURCE SNIPPETS (factual anchor) ===")
        for title, snippet in snippets:
            lines.append(f"- {title}: {snippet}")

    if pasted_text.strip():
        lines.append("\n=== PASTED CONTENT (creator-provided; use specifics from it) ===")
        lines.append(pasted_text.strip())

    if prior_levels:
        lines.append(
            "\n=== PRIOR LEVELS (already written — keep continuity; do NOT reuse "
            "their vocabulary words or example sentences) ==="
        )
        for pl in prior_levels:
            lines.append(f"--- {pl['label']} ---")
            lines.append(f"Story: {pl['story_text']}")
            if pl["vocab_words"]:
                lines.append("Vocab already used: " + ", ".join(pl["vocab_words"]))
            if pl["example_sentences"]:
                lines.append(
                    "Example sentences already used: "
                    + " | ".join(pl["example_sentences"])
                )

    return "\n".join(lines)
