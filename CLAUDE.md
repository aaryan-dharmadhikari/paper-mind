# PaperMind

Personal research mentor: ingest PDFs, build knowledge graphs, study with AI agents.

## Quick Start

```bash
cp .env.example .env   # Add your API key
./run.sh               # Dev server on :8080
docker compose up -d   # Docker on :4269
```

## Architecture

Single-user NiceGUI web app. No ORM, no heavyweight frameworks.

- **Pages** self-register via `@ui.page()` decorators, imported in `main.py` for side effects
- **DB** is synchronous SQLite with WAL mode. All queries in `db.py`. Schema auto-created by `init_db()`
- **LLM** calls are async via LiteLLM. `litellm.drop_params = True` for cross-provider compat
- **PDFs** are base64-encoded and sent directly to the LLM for parsing (no local text extraction)
- **Chat** stores messages as JSON in `chat_history`. Both agents share one conversation per paper

## Key Files

| File | What it does |
|------|-------------|
| `main.py` | NiceGUI entry, page imports, static files, DB init |
| `config.py` | Reads `.env`, exposes `LITELLM_MODEL`, `DB_PATH`, `UPLOAD_DIR` |
| `db.py` | Schema + all CRUD helpers. Migrations in `init_db()` |
| `llm.py` | System prompts, `parse_paper_with_llm()`, `stream_chat_response()`, `assess_knowledge()` |
| `pdf_processing.py` | Upload pipeline: save → dedup check → base64 → LLM parse → store |
| `pages/layout.py` | Shared `frame()` header/nav |
| `pages/chat.py` | Teach/Zealot agents, streaming, agent toggle, knowledge assessment |

## Adding a Page

1. Create `pages/my_page.py`
2. Define `@ui.page("/my-route") def my_page():`
3. Call `frame("Title")` at the top
4. Add `import pages.my_page  # noqa: F401` to `main.py`

## Gotchas

- `main.py` guard must be `if __name__ in {"__main__", "__mp_main__"}:` — NiceGUI uses multiprocessing for reload
- DB layer is sync, LLM layer is async. Don't `await` db calls
- Paper context is injected only into the first user message in chat history
- Concept names are normalized to lowercase for dedup
- `self_rating` column added via migration in `init_db()` — new columns need the same pattern
- Duplicate detection checks filename first (free), then LLM-parsed title (after parsing)

## Code Style

- Snake case everywhere. Private helpers prefixed with `_`
- Constants are `UPPER_CASE`
- Type hints on function signatures: `def get_paper(paper_id: int) -> dict | None:`
- NiceGUI styling via `.classes("tailwind classes")` and `.props("quasar props")`
- No linter/formatter configured. Keep it readable

## Commit Messages

Short imperative subject. No conventional commits prefix. Always include:

```
Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

## Config

All via `.env` (loaded by python-dotenv):

```
LITELLM_MODEL=openai/gpt-5-mini   # Any LiteLLM-supported model
OPENAI_API_KEY=sk-...              # Provider API key
NICEGUI_HOST=0.0.0.0               # Optional
NICEGUI_PORT=8080                  # Optional
DB_PATH=paper_mind.db              # Optional
```

## Data

- SQLite DB at `DB_PATH` (default: project root)
- PDFs in `uploads/`
- Docker volumes: `./uploads` and `./data`
- Daily backup via `backup.sh` to private repo `paper-mind-data`
