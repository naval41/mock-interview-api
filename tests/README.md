# Tests & Evals — mock-interview-api

Two layers, both centered on the **premature phase-transition** behavior
(incident: `candidate_interview_id 60abce19-b7b8-4a5e-99eb-27941b9c25c8`, where
the bot abandoned coding problem 1 after ~189s of a 25-min phase).

## Layout

```
tests/
├── conftest.py                # hermetic env defaults (no real DB/secrets)
├── support/builders.py        # real InterviewContext/PlannerField builders
├── unit/                      # Layer 1 — deterministic guard tests
│   ├── test_phase_transition_guard.py
│   └── test_llm_initiated_transition.py
└── eval/                      # Layer 2 — decision eval
    ├── harness.py             # types, scoring, metrics (model-agnostic)
    ├── dataset.py             # labeled cases (incl. golden regressions)
    ├── reference_decider.py   # rule-based baseline / quality bar
    ├── test_transition_eval.py# deterministic harness+dataset+metric tests
    └── run_llm_eval.py        # LIVE Gemini eval (marker: llm_live)
```

## Markers

| Marker     | Runs in build gate? | What it is |
|------------|---------------------|------------|
| `unit`     | ✅ yes              | Pure guard logic. No network, no secrets. |
| `eval`     | ✅ yes              | Harness/dataset/metric correctness (deterministic). |
| `llm_live` | ❌ no (opt-in)      | Calls the real Gemini model (paid, networked). |

The default pytest config (`pyproject.toml`) runs `-m "not llm_live"`, so the
build gate is hermetic and deterministic.

## Running

```bash
# Deterministic suite (what the image build runs):
pytest

# Live Gemini eval — on demand or scheduled, not in the build:
GOOGLE_API_KEY=... pytest -m llm_live
# or as a script with a printed report + confusion matrix:
GOOGLE_API_KEY=... python -m tests.eval.run_llm_eval
```

## Metrics that matter (Layer 2)

- **`false_transition_rate`** — inferred transitions on `NO_CALL` cases. This is
  the original bug; target **0**.
- **`stuck_candidate_recall`** — of explicit "let's move on / I'm stuck" cases,
  how many were honored with `candidate_ready`. A miss traps a stuck candidate
  and steals time from the next problem; target **1.0**.

## Build gate (Dockerfile)

The image build runs the deterministic suite in a dedicated `test` stage; the
`runtime` stage copies from it, so **a failing test fails the image build**.
Add this between the `builder` and `runtime` stages, and point `runtime`'s
`COPY --from=` at `test`:

```dockerfile
FROM base AS test
ENV PATH="/opt/venv/bin:$PATH" PYTHONPATH="/app" ENV="test"
COPY --from=builder /opt/venv /opt/venv
COPY pyproject.toml ./
COPY app ./app
COPY config ./config
COPY tests ./tests
RUN DATABASE_URL="postgresql+asyncpg://test:test@localhost:5432/test" \
    JWT_SECRET_KEY="test-secret-not-used" \
    pytest

FROM base AS runtime
# ...
COPY --from=test /opt/venv /opt/venv    # was: --from=builder
```

## Extending the dataset from production

New labeled cases can be harvested from real sessions:
- **Negatives** (should have been `NO_CALL`): CloudWatch shows
  `initiated by: llm` transitions with a non-`candidate_ready` reason and low
  `elapsed_seconds` on a coding phase; pull the surrounding `Transcript` rows.
- **Positives** (`candidate_ready`): transcript-search candidate utterances like
  "move on / I'm stuck / skip / I'm done".

Append them to `tests/eval/dataset.py`. Golden incident cases must never regress.
