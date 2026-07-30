# Source Code

Source code for *Cloud-Based Smart Irrigation Recommendation using Weather
Intelligence* (BITE412L, Dr. Priya V).

---

## ⚠️ Phase-I Status

> **This folder is intentionally empty of code.**
> Phase-I is planning and documentation; code implementation is **not** required at
> this stage. Each subfolder carries a README describing what will be built there
> in Phase-II and Phase-III, who owns it, and how it connects to the rest of the
> system.

---

## Subfolder structure

```
src/
├── README.md          # This file
├── frontend/          # React dashboard and PWA          — Nayan Jaggi (23BIT0390)
├── backend/           # FastAPI service and Azure Functions — Aarush Pandit (23BIT0416)
├── ai_model/          # ML pipeline and models           — Krishna Agrawal (23BIT0428)
└── azure/             # Infrastructure as code (Bicep)   — Aarush Pandit (23BIT0416)
```

| Subfolder | Contents | Owner | Phase |
|---|---|---|---|
| [`frontend/`](frontend/) | React 18 dashboard, PWA configuration, offline cache, multilingual UI, charts | Nayan Jaggi (23BIT0390) | Phase-II |
| [`backend/`](backend/) | FastAPI service, Azure Functions (ingest, recommendation engine, notification dispatch), FAO-56 module, database access layer | Aarush Pandit (23BIT0416) | Phase-II |
| [`ai_model/`](ai_model/) | Feature engineering, soil-moisture forecasting model, residual correction model, SHAP justification generator, training and evaluation scripts | Krishna Agrawal (23BIT0428) | Phase-II |
| [`azure/`](azure/) | Bicep infrastructure templates, Azure Function configuration, deployment scripts, Data Factory pipeline definitions | Aarush Pandit (23BIT0416) | Phase-II |

---

## How the components connect

```
   frontend/  ──HTTPS──▶  API Management  ──▶  backend/
                                                  │
                                    ┌─────────────┼─────────────┐
                                    ▼             ▼             ▼
                              Cosmos DB      SQL Database   ai_model/
                             (field state)  (master, audit)  (ML endpoint)
                                    ▲
                                    │
                          azure/ provisions all of the above
```

- **`frontend/`** never talks to a database directly. Every request goes through
  API Management to the backend, which enforces authorisation.
- **`backend/`** owns the FAO-56 physical baseline and the decision rule. It calls
  the ML endpoint for the learned component but does not train models.
- **`ai_model/`** owns training, registration and serving. It publishes a versioned
  model; the backend consumes it by version.
- **`azure/`** provisions every resource. **No resource is created by hand in the
  portal** — if it is not in Bicep, it does not exist.

---

## Development conventions (Phase-II onward)

| Convention | Rule |
|---|---|
| **Language** | Python 3.11 for backend and ML; JavaScript/JSX for frontend |
| **Formatting** | `ruff` for Python; Prettier for JavaScript |
| **Secrets** | Never committed. All secrets live in Azure Key Vault and are accessed via managed identity. Local development uses a `.env` file listed in `.gitignore` |
| **Branching** | Work only on your own `feature/studentN` branch. No direct commits to `main` |
| **Commits** | Small and descriptive. "Add FAO-56 ET₀ calculation with unit tests" not "update" |
| **Tests** | `pytest` for Python. Every module ships with unit tests before its PR is merged |
| **Feature parity** | The feature engineering used at training time and at inference time must come from the **same code path**, to prevent train/serve skew |

---

## Why the folder is empty rather than stubbed

Placeholder code that does nothing is worse than no code: it has to be deleted
later, it confuses reviewers about what is implemented, and it invites merge
conflicts. Every subfolder therefore carries documentation of intent instead, so
the plan is legible without pretending the implementation exists.

---

*Phase-I: planning and documentation.*
