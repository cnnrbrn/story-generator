"""Web research: plan angled searches, run them via Tavily, return real sources.

The researcher agent decides what to search (mainstream + anti-imperialist angles);
we run each query, dedupe by URL, then rank everything by Tavily's relevance score
and return the top `research_max_results`. The perspective tag still rides along on
each source but is no longer used to group the results.
"""

from tavily import TavilyClient

from app.agents.researcher import plan_queries
from app.config import settings
from app.schemas.source import SourceItem


def research_topic(
    topic: str,
    max_results_per_query: int = 3,
    model: str | None = None,
    max_results: int | None = None,
) -> list[SourceItem]:
    """Plan searches, run them, then return the top sources ranked by relevance.

    `max_results` caps the final list (defaults to settings.research_max_results).
    """
    cap = max_results if max_results is not None else settings.research_max_results
    plan = plan_queries(topic, model=model)
    client = TavilyClient(api_key=settings.tavily_api_key)

    # url -> (relevance score, source). Dedupe by URL, keeping the highest score.
    by_url: dict[str, tuple[float, SourceItem]] = {}
    for q in plan.queries:
        response = client.search(
            query=q.query, max_results=max_results_per_query, search_depth="basic"
        )
        for r in response.get("results", []):
            url = r.get("url", "")
            if not url:
                continue
            score = r.get("score", 0.0)
            if url not in by_url or score > by_url[url][0]:
                by_url[url] = (
                    score,
                    SourceItem(
                        title=r.get("title", ""),
                        url=url,
                        snippet=r.get("content", ""),
                        perspective=q.perspective,
                    ),
                )

    # Sort by score (highest first) and cap. `x[0]` is the score in each tuple.
    ranked = sorted(by_url.values(), key=lambda x: x[0], reverse=True)
    return [source for _, source in ranked[:cap]]


if __name__ == "__main__":
    sources = research_topic("the fall of Tenochtitlan")
    print(f"=== {len(sources)} sources (ranked) ===")
    for i, s in enumerate(sources, start=1):
        print(f"{i}. {s.title}")
        print(f"   {s.url}")
        print(f"   {s.snippet[:140]}...")
