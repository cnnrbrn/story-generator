"""Researcher: plans angled web searches for a topic.

A small LLM step turns the topic into a set of search queries, each tagged by
perspective: a couple of mainstream queries for the factual baseline, and several
that deliberately surface Indigenous / decolonial / anti-imperialist sources.
"""

from pydantic_ai import Agent

# Reuse the DeepSeek model builder from the generator (same provider + key).
from app.agents.generator import _build_model
from app.config import settings
from app.schemas.source import ResearchPlan

_SYSTEM_PROMPT = (
    "You plan web searches to research a historical topic for an anti-imperialist "
    "history story aimed at language learners. Produce 5 to 6 search queries:\n"
    "- 1 or 2 tagged perspective='mainstream' for the factual baseline (dates, "
    "events, key figures).\n"
    "- 3 or 4 tagged perspective='anti_imperialist' that deliberately surface "
    "Indigenous, decolonial and anti-imperialist perspectives, naming relevant "
    "decolonial works or authors where useful (for example Eduardo Galeano, "
    "Miguel Leon-Portilla, Matthew Restall, Camilla Townsend).\n"
    "Make each query specific and likely to return strong sources."
)


def plan_queries(topic: str, model: str | None = None) -> ResearchPlan:
    """Ask the model for a set of perspective-tagged search queries."""
    agent = Agent(
        _build_model(model or settings.generator_model),
        output_type=ResearchPlan,
        system_prompt=_SYSTEM_PROMPT,
    )
    return agent.run_sync(f"Topic: {topic}").output
