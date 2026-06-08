# Plan: Story Generator for Language-Learning Videos

## Context

We are building a greenfield content-generation app. A content creator enters a historical topic (e.g. "the fall of Tenochtitlan") and the system produces a complete story in the target language at **4 difficulty levels** (Just Starting, Beginner, Intermediate, Advanced), each with a rigid section structure, plus a full list of sources.

Latin-American Spanish ships first; the architecture must accommodate **Brazilian Portuguese** and **Zulu** later without rework. The hard part is not "call an LLM" — it is enforcing the detailed editorial rules (exact verb counts per level, no repeated example sentences across levels, cross-level vocab de-dup, audio-safe punctuation, a *subtle* anti-imperialist tone), and doing so reliably by **cross-checking one model's output with a second/third model** plus deterministic validators. Output is **text scripts only** (audio/video are out of scope). The creator **reviews, edits, and can regenerate** any level/section before publishing.

### Decisions locked with the user
- **Sources:** Both auto web-research and creator-uploaded PDFs/docs/links. A final source list is always produced.
- **Tracking:** Track the **conjugated surface form** (e.g. `era`, `murieron`, `mueren`), not the root. Hard de-dup rules apply **within a story** across its 4 levels; across the whole library we keep a **global ledger** to steer *variety* (don't open every Just-Starting story with `era`) — reuse across stories is allowed, it is a soft preference, not a ban.
- **Output:** Text scripts + sources only.
- **Workflow:** Draft → human review/edit → regenerate level or section → publish.

## Execution approach (how we build)

**Backend + setup first. Small, single-purpose, approval-gated steps — one increment at a time, stop for review before the next.** No large multi-file dumps. Confirmed setup choices: **uv** for Python, **local Postgres + pgvector via docker-compose** for dev (deploy to Neon later through `DATABASE_URL`), default providers **OpenAI + DeepSeek** (both OpenAI-compatible, both cheap; keys `OPENAI_API_KEY`, `DEEPSEEK_API_KEY`).

### Step 1 (done): bare backend scaffold — no DB
- `backend/` with `pyproject.toml` (uv), Python 3.12.
- Minimal FastAPI app exposing `GET /health`.
- `backend/Dockerfile` (uv-based) and `docker-compose.yml` with **only the `api` service** for now.
- `.env.example` (placeholders for `OPENAI_API_KEY`, `DEEPSEEK_API_KEY`; `DATABASE_URL`/`REDIS_URL` for later).
- A `.gitignore`.
- Verify: `docker compose up` serves `/health`.

### Next steps (later, each approved separately)
- Postgres+pgvector service + SQLAlchemy/Alembic + connection.
- Full schema + first migration.
- Model registry (per-role model resolution from env/`models.yaml`).
- `LanguageProfile` for `es-LA` + seeded guidelines system prompt.
- Generation pipeline, validators, critics, tracking, research, frontend.

## High-level architecture

```
Next.js frontend ──HTTP──> FastAPI ──enqueue──> Async worker (ARQ)
                              │                      │
                              ▼                      ▼
                      Neon Postgres          Generation pipeline
                      (+ pgvector)           (Pydantic AI agents, cheap models)
```

- **Backend:** FastAPI (Python).
- **DB:** Neon Postgres with the **`pgvector` extension** for document RAG — **no separate vector database**. Verb/vocab tracking is exact/relational, not semantic, so it lives in normal tables.
- **LLM orchestration:** **Pydantic AI** — model-agnostic, so we run cheap models and assign a *different* model to each role (researcher / generator / critic-1 / critic-2). Typed structured outputs match the rigid section schema.
- **Long-running work:** multi-stage pipeline runs in a **background worker (ARQ, Redis-backed)**, not in the request. Frontend tracks progress via polling/SSE.
- **Packaging:** **Docker** — one backend image for API + worker.

## Model selection & providers

Cost-first and configurable — no hardcoded flagship model.

- **Per-role model config.** Each role (`researcher`, `generator`, `critic_1`, `critic_2`) is `{provider, model, params}`. Defaults from env; overridable per story; recorded on the story (`model_config` jsonb) and every `generation_runs` row.
- **Cheap by default, Claude optional.** Default to inexpensive models (e.g. small/flash-tier for generation; *different* cheap models from *different* providers for the two critics — that's what gives real cross-model independence). Claude is selectable, not default.
- **Provider abstraction via Pydantic AI** — OpenAI, Gemini, Mistral, Groq, Anthropic, plus any OpenAI-compatible base URL (OpenRouter, DeepSeek, Together, local Ollama/vLLM).
- **API keys in env vars.** A `models.yaml` lists selectable models, provider, and cost tier.
- **Why cheap is safe:** deterministic validators + repair loop + independent critic catch the rule violations weaker models make.

## Data model (Neon Postgres, SQLAlchemy + Alembic)

- **`languages`** — `code` (e.g. `es-LA`), `name`, `profile_key`, `active`.
- **`stories`** — `id`, `topic_text`, `language_code`, `status` (`draft|researching|generating|review|published|failed`), `model_config` (jsonb), `created_by`, timestamps.
- **`story_levels`** — `id`, `story_id`, `level`, `title_target`, `title_en`, `summary_en`, `story_text`, `status`, `version`.
- **`vocabulary_entries`** — `story_level_id`, `word`, `translation`, `position`.
- **`verb_entries`** — `story_level_id`, `surface_form`, `lemma`, `tense`, `mood`, `translation`, `example_sentence_target`, `example_sentence_en`, `position`.
- **`grammar_entries`** — `story_level_id`, `surface_form`, `lemma`, `tense`, `mood`, `translation` (superset of verbs section).
- **`sources`** — `story_id`, `type` (`web|upload|manual`), `title`, `author`, `url`, `citation_text`, `retrieved_at`.
- **`source_documents`** — `story_id`, `filename`, `mime`, `storage_ref`, `extracted_text`, `status`.
- **`document_chunks`** — `source_document_id`, `chunk_index`, `content`, `embedding vector(N)` (pgvector).
- **`verb_ledger`** — `language_code`, `surface_form`, `lemma`, `tense`, `mood`, `level`, `usage_count`, `last_used_at`. (`vocab_ledger` mirror.)
- **`generation_runs`** — `story_level_id`, `stage`, `model`, `iteration`, `raw_output` (jsonb), `validation_results` (jsonb), `critic_results` (jsonb), `created_at`.

## Generation pipeline (the core)

Orchestrated in the worker; each stage writes to `generation_runs`.

1. **Research** — researcher agent + provider-neutral search tool; ingest uploaded docs (chunk+embed large ones into pgvector). Collect `sources` with citations.
2. **Brief / fact-sheet** — shared, source-grounded outline: key facts (each tied to a source), the emotional/anti-imperialist angle, the recurring spine/refrain.
3. **Sequential level generation** — **Just Starting → Beginner → Intermediate → Advanced in order** (de-dup is cumulative). Each level call gets: the brief, prior level's story, **accumulated constraint state** (verbs/surface-forms/tenses + exact example sentences already used; vocab introduced), and **global variety hints**. Output is a typed per-level structure.
4. **Validate** (deterministic, pure Python — hard gates).
5. **Critique** (independent LLM(s) — rubric scoring).
6. **Repair loop** — deterministic failures regenerate with violations fed back; critic findings attached as flags.
7. **Human review** — drafts with inline validator/critic flags; edit text or regenerate level/section; edits re-run validators.
8. **Finalize** — assemble source list, update ledgers, publish.

The static guidelines + active `LanguageProfile` are a stable system-prompt prefix; enable **prompt caching where the provider supports it**.

## Multi-LLM verification design

**Deterministic validators** (code, language-agnostic, `app/pipeline/validate.py`):
- Verb-section counts: Just Starting **exactly 3**; Beginner **≤ 6**; Intermediate **≤ 10**; Advanced **≥ 15 with ≥ 1 subjunctive**.
- Every verb/vocab **example sentence appears verbatim** in that level's `story_text`.
- **No example sentence repeats** across levels of the same story.
- **No vocab word repeats** across prior levels.
- Intermediate+ verbs section introduces **only new surface forms** vs prior levels.
- Every verb in the story appears in `grammar_entries`.
- **Audio-safe punctuation:** reject `—` and `:`; allow only commas, periods, `-`.
- **Section structure per level:** Advanced = target title + story only; Intermediate/Advanced headings in target language.

**LLM critics** (each a *different, cheaper* model from a *different provider* than the generator). Structured per-criterion scores + feedback:
- **Anti-imperialist tone** present **but not heavy-handed/preachy** (both directions).
- Emotional engagement; tragedy/injustice surfaced.
- **Historical accuracy** vs the brief's cited facts.
- **Level-appropriate complexity** (simple for JS/Beginner; connectors like `sin embargo`, `a pesar de` for Int/Adv).
- **Natural read-aloud** quality.
- **Translation accuracy** (target ↔ English).
- **Cognate check** — vocab excludes obvious cognates.

Deterministic gates are blocking; critic findings surface to the reviewer as flags. Critic prompts/rubric live in the `LanguageProfile`.

## Verb / vocab tracking design

- **Unit = conjugated surface form** mapped to `(lemma, tense, mood)` for grammar. `murieron` ≠ `mueren` though both are `morir`.
- **Within a story (hard):** the validator rules above.
- **Across the library (soft):** `verb_ledger`/`vocab_ledger` track usage count + recency per `(language, surface_form, level)`; over-used forms become "prefer fresh alternatives" hints. Reuse allowed, monotony discouraged.
- **Lemma/POS verification:** trust the model's structured grammar output; for `es`/`pt` optionally cross-check with spaCy via an optional `lemmatizer` hook. Zulu relies on LLM output + second-LLM cross-check.

## Sources & RAG

- **Web research:** provider-neutral search tool (Tavily/Brave) as a Pydantic AI tool. Results → `sources` (`type=web`).
- **Uploads/links:** PDFs/docs extracted; large ones chunked + embedded into `document_chunks`; links fetched server-side. → `source_documents` + `sources` (`type=upload`).
- **Embeddings (configurable, cost-aware):** default to a free **local multilingual embedding model** (e.g. `multilingual-e5` via sentence-transformers); hosted embeddings a swap-in option. pgvector dimension follows the chosen model.
- **Final source list:** aggregated, editable, exported with the scripts.

## Multi-language extensibility

A **`LanguageProfile`** (`app/language/base.py`, impl `spanish.py`; later `portuguese.py`, `zulu.py`) encapsulates everything language-specific: level/section definitions, verb-count rules, prompt templates + guidelines text, critic rubric + cognate rules, optional `lemmatizer` hook. Zulu (agglutinative, noun classes) becomes "write a new profile," not a re-architecture.

## Frontend (Next.js)

- **New story:** topic + language select + optional uploads/links.
- **Dashboard:** stories list with status.
- **Progress view:** live pipeline status (poll/SSE).
- **Review workspace:** 4 level tabs; inline editing; inline validator/critic flags; regenerate level/section.
- **Sources panel:** aggregated, editable.
- **Export/publish.**

## Repository structure

```
backend/
  app/
    main.py
    routers/        stories.py documents.py generation.py languages.py models.py
    pipeline/       orchestrator.py research.py brief.py generate_level.py
                    validate.py critique.py
    agents/         generator.py critic.py researcher.py   (Pydantic AI)
    models/         registry.py        (per-role model resolution)
    language/       base.py spanish.py
    db/             models.py session.py  + alembic/
    workers/        tasks.py   (ARQ)
  models.yaml
  Dockerfile
  pyproject.toml
frontend/           (Next.js app router)
docker-compose.yml  (api, worker, redis; Neon is remote)
.env.example
```

## Docker & deployment

- **`backend/Dockerfile`** — one image for API (`uvicorn`) and worker (`arq`), different command.
- **`docker-compose.yml`** — `api`, `worker`, `redis`; Neon remote via `DATABASE_URL`. Local embedding model baked in.
- **Config via env**; `.env.example` documents keys; secrets never committed.

## Build phases

1. **Foundation:** scaffold, Docker/compose, Neon + Alembic, FastAPI skeleton, model registry, `LanguageProfile` for `es-LA`, seeded guidelines.
2. **Generation core:** brief + sequential 4-level generation with typed output; golden test against the Cerro Rico example.
3. **Verification layer:** deterministic validators + repair loop; independent critic + flags; `generation_runs` audit.
4. **Tracking:** verb/vocab ledgers + variety hints.
5. **Research & sources:** search agent, uploads + pgvector RAG, final source list.
6. **Frontend:** new-story, progress, review/edit/regenerate, sources, export.
7. **Hardening + extensibility:** prompt caching, retries, stub a second `LanguageProfile`.

## Verification / testing

- **Golden test:** reproduce the Cerro Rico story; assert all deterministic rules pass.
- **Validator unit tests:** one per rule.
- **Pipeline integration test:** fresh topic end-to-end; assert 4 levels, sources, audit rows.
- **Critic smoke test:** preachy story → tone critic flags "heavy-handed."
- **Manual:** generate via UI, review flags, edit + regenerate, publish, confirm source list.

## Open considerations (not blocking)
- Object storage for uploads (S3/R2 vs Neon large objects) — decide at phase 5.
- Auth: deferred until multi-user is needed; **Python/FastAPI** concern (e.g. `fastapi-users` / JWT), not Better Auth (TypeScript/frontend-only).
- Cost/usage tracking via `generation_runs` (model + tokens per call).
- Frontend model-picker UX with sensible defaults.
