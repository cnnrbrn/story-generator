"""Fetch full page text for selected source URLs via Tavily Extract.

Search only gives us short snippets; to ground the brief we extract the real page
content for the URLs the creator selected. Per-URL failures are skipped (the caller
falls back to the stored snippet), and each page is truncated to a char budget so a
few long articles don't blow the model's context window.
"""

from tavily import TavilyClient

from app.config import settings


def extract_sources(urls: list[str]) -> dict[str, str]:
    """Return {url: extracted_text} for the URLs Tavily could fetch.

    URLs that fail extraction are simply absent from the result.
    """
    if not urls:
        return {}

    client = TavilyClient(api_key=settings.tavily_api_key)
    budget = settings.extract_char_budget

    # Tavily accepts a list of URLs; successful pages come back under "results".
    # "advanced" strips more page boilerplate (nav/markup) than "basic" for ~2x the
    # credit cost — negligible at our scale (a handful of URLs per brief).
    response = client.extract(urls, extract_depth="advanced")

    out: dict[str, str] = {}
    for r in response.get("results", []):
        url = r.get("url", "")
        content = (r.get("raw_content") or "").strip()
        if url and content:
            out[url] = content[:budget]
    return out


if __name__ == "__main__":
    sample = ["https://en.wikipedia.org/wiki/The_Broken_Spears"]
    result = extract_sources(sample)
    for url, text in result.items():
        print(f"=== {url} ({len(text)} chars) ===")
        print(text[:500], "...\n")
    missing = [u for u in sample if u not in result]
    if missing:
        print("FAILED to extract:", missing)
