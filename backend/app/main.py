from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import research

app = FastAPI(title="Story Generator API", version="0.1.0")

# Allow the Vite dev server (frontend) to call the API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(research.router)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe. Returns 200 with a simple status payload."""
    return {"status": "ok"}
