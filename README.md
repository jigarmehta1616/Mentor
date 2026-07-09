# Mentor — an adaptive learning agent

You tell Mentor a topic and your level. It builds a **personalized learning path**
over a prerequisite graph, then **teaches interactively**: explains a concept,
quizzes you, **diagnoses exactly what you misunderstood**, re-teaches that specific
gap at a depth you choose, cites current resources, and uses **spaced repetition
(SM‑2)** to resurface weak spots in later sessions. It remembers you across sessions.

It's a genuine **agentic system** — planning, tool use, stateful memory, and
self‑correction — built as an explicit **LangGraph** state machine, not a prompt.
Runs end‑to‑end **with zero API keys and no database** (mock LLM + in‑memory backend).

---

## Why it's interesting

- **Agent as a state machine.** `scheduler → planner → teacher → quizzer → grader → diagnoser → adapter`, with a conditional self‑correction loop — typed state, explicit edges.
- **Deterministic where it must be.** The LLM *explains and diagnoses*; the SM‑2 scheduling math is pure, tested code (`memory/srs.py`). Grading returns a validated `{quality, misconception}`.
- **Bounded context.** The agent never sends unbounded history to the model — a sliding window of `W` turns + a running summary keeps token cost **O(W)**, constant in session length.
- **Measured, not asserted.** An **evaluation harness** simulates a learner and shows adaptive teaching beats a static syllabus (numbers below).
- **Complexity is an acceptance criterion.** Every hot path has a one‑line complexity comment and meets a documented bound (table below).

---

## The agent (LangGraph)

```mermaid
flowchart TD
    START([turn]) -->|answer present| grader
    START -->|no answer| scheduler
    scheduler --> planner
    planner -->|topic complete| DONE([end])
    planner -->|next concept| teacher
    teacher --> quizzer
    quizzer --> PRESENT([teach + quiz])
    grader -->|quality &lt; 3| diagnoser
    grader -->|quality &gt;= 3| adapter
    diagnoser --> adapter
    adapter --> planner
```

- **scheduler** surfaces items **due for review first** (indexed query).
- **planner** builds the path by **topological sort** over the prerequisite DAG (cycle‑checked) and advances to the next unlearned concept.
- **teacher** explains at the chosen level with cited resources; on a wrong answer it **re‑teaches the diagnosed sub‑point**, not the same text.
- **grader → diagnoser → adapter** is the self‑correction loop: score `0..5`, identify the misconception, then run the deterministic SM‑2 update and decide **re‑teach vs advance**.

State is bounded: `{ user_id, topic, path, current_concept, explain_level, window[≤W], running_summary, last_quiz, last_grade, diagnosis }`.

---

## Quick start

### Zero keys, zero infra (mock LLM + in‑memory store)

```bash
# backend
cd backend
pip install -e ".[dev]"
DATABASE_URL="memory://" LLM_PROVIDER="mock" uvicorn app.main:app --port 8000

# frontend (separate terminal)
cd frontend
npm install
npm run dev            # http://localhost:5173
```

Open the app, pick a topic, and start learning. A wrong quiz answer triggers a
**targeted re‑explanation**; mastered concepts come back as **due reviews** later.

### With Postgres

```bash
docker compose up -d                 # Postgres on :5432, schema auto-applied
cd backend && python -m app.db.migrate   # apply schema + seed topic DAGs
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/mentor" \
  LLM_PROVIDER="mock" uvicorn app.main:app --port 8000
```

Set `LLM_PROVIDER=anthropic` (+ `ANTHROPIC_API_KEY`) or `openai` to use a real model.

---

## Adaptive vs. static — evaluation

`python -m app.eval.harness` simulates a learner (per‑concept skill, answers graded
by the **real** grader) and compares the full adaptive agent against a static,
teach‑once syllabus:

| Topic | Arm | Mastery | Mean quiz quality |
|---|---|---|---|
| neural‑networks | static | 0 / 10 (0%) | 1.8 |
| neural‑networks | **adaptive** | **10 / 10 (100%)** | **3.4** |
| sql | static | 1 / 9 (11%) | 1.67 |
| sql | **adaptive** | **9 / 9 (100%)** | **3.44** |

Adaptive re‑teaching of diagnosed gaps lifts mastery by **+89–100 percentage points**
in simulation. (Numbers are illustrative — mock learner + mock grader — but the
harness plugs a real LLM learner in unchanged.)

---

## Performance & Complexity (acceptance criteria)

| Operation | Bound | How |
|---|---|---|
| Fetch **due** review items | **O(log n + k)** | B‑tree index **`idx_due (user_id, next_review)`**; `WHERE next_review <= now ORDER BY next_review LIMIT k`. Never a full scan. |
| **SM‑2 update** | **O(1)** | Pure arithmetic on EF / interval / repetitions (`memory/srs.py`). |
| **Path generation** | **O(V + E)** | Kahn's topological sort + explicit cycle detection (`memory/graph_utils.py`). |
| **Prerequisite check** | **O(indegree)** | Adjacency map lookup; no graph rebuilds. |
| **Load agent context** | **O(W)**, constant in session length | Sliding window + running summary (`memory/context.py`), folded incrementally (amortized O(1)). |
| **Quiz history / progress** | **O(log n + page)** | Indexed + paginated; no `SELECT *` of full history. |
| **Mastery lookup** | **O(log n)** | Primary key `(user_id, concept_id)`. |
| **Resource fetch** | **O(1)** amortized | Bounded LRU + TTL cache; `web_search` only on miss. |
| DB access | **No N+1** | Path concepts and edges batch‑fetched in one query each. |

Space: bounded LLM context (window + summary) ⇒ constant token footprint per request;
only compact SM‑2 state on the hot path; streamed responses; paginated lists;
LRU+TTL‑bounded cache.

---

## API

| Method | Route | Purpose |
|---|---|---|
| `POST` | `/sessions` | Start a session → due reviews + first concept (teach + quiz). |
| `POST` | `/sessions/{id}/turn` | One agent step (teach/quiz/diagnose/adapt), **streamed (SSE)**. `{answer?, level?}`. |
| `GET` | `/paths/{user_id}?topic=` | Ordered path + per‑concept status. |
| `GET` | `/reviews/{user_id}` | Items due now (the O(log n + k) query). |
| `GET` | `/progress/{user_id}?topic=` | Mastery per concept + paginated quiz history. |
| `GET` | `/health` | Status + active LLM provider. |

---

## Tech stack

- **Backend:** Python 3.11+, FastAPI, **LangGraph**, SQLAlchemy 2.0 / psycopg 3, PostgreSQL. Typed throughout (`mypy --strict` clean).
- **Frontend:** React + Vite + TypeScript (strict) + Tailwind, streaming chat UI.
- **LLM:** provider abstraction — `mock` (default, offline) | `anthropic` (`claude-opus-4-8`, adaptive thinking) | `openai`.

## Layout

```
backend/app
├── agent/        LangGraph: state, nodes, tools, repo protocol
├── memory/       srs.py (SM-2), graph_utils.py (topo sort), context.py (window+summary)
├── llm/          provider abstraction (mock | anthropic | openai)
├── api/          engine + sessions/paths/reviews/progress routers
├── db/           models, schema.sql, SqlRepo
├── eval/         adaptive-vs-static harness
└── seed/         seeded topic DAGs
frontend/src      chat panel, level switcher, path sidebar, due badge, dashboard
```

## Tests & CI

```bash
cd backend && pytest              # 38 tests: SRS, graph utils, context bounding, agent, API, eval
ruff check app tests && mypy app  # lint + strict typecheck
cd frontend && npm run typecheck && npm run build
```

GitHub Actions runs backend lint/typecheck/tests + frontend typecheck/build on every push.

---

## What's proven to work

- A **personalized path** is generated by topological sort over a prerequisite DAG.
- A **wrong quiz answer** triggers a **targeted** re‑explanation of the misunderstood sub‑point (verified in `tests/test_agent_graph.py` and `tests/test_api.py`).
- A **due review** surfaces first in a later session (spaced repetition).
- Adaptive teaching **measurably beats** a static syllabus (`tests/test_eval.py`).
