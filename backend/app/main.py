from fastapi import FastAPI

app = FastAPI(title="Story Generator API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe. Returns 200 with a simple status payload."""
    return {"status": "ok"}
