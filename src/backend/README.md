# Backend

**Owner:** Aarush Pandit (23BIT0416)
**Branch:** `feature/student2`
**Status:** Phase-I — no code. Implementation begins in Phase-II.

---

## Purpose

The backend owns the decision. It ingests external data, computes the FAO-56
physical baseline, calls the machine learning endpoint for the learned correction,
applies the decision rule, and dispatches the result.

Everything else in the system either feeds it or renders what it produces.

---

## What will be built here (Phase-II)

| Component | Description | Azure Service |
|---|---|---|
| **Ingest Function** | Timer-triggered. Pulls forecast, reanalysis and soil data; checks the Redis cache before any upstream call; computes engineered features; writes to Cosmos DB and Blob Storage | Azure Functions (timer trigger) |
| **FAO-56 module** | Reference evapotranspiration by Penman–Monteith, root-zone water balance, field capacity and wilting point from soil texture via pedotransfer function | Library code inside the backend |
| **Recommendation engine** | Timer-triggered. Reads field state and crop master data, computes the physical baseline, calls the ML endpoint, applies the decision rule, generates the justification, persists and dispatches | Azure Functions (timer trigger) |
| **Notification dispatch** | Queue-triggered. Consumes Service Bus messages and fans out to push and SMS | Azure Functions (queue trigger) |
| **REST API** | Field registration, recommendation retrieval, history, farmer action recording | FastAPI, fronted by API Management |
| **Data access layer** | Cosmos DB and SQL Database repositories, Redis cache client | Library code |

---

## Technology

| Item | Choice | Reason |
|---|---|---|
| Language | Python 3.11 | Shares a language with the ML pipeline, so the FAO-56 module and feature engineering live in one codebase and cannot drift apart |
| API framework | FastAPI | Async, automatic OpenAPI generation for API Management import, Pydantic validation built in |
| Serverless | Azure Functions Python worker | Consumption billing means a field costs nothing on days it is not processed |
| Validation | Pydantic | Request and response schemas enforced at the boundary |
| Testing | pytest | Unit tests for the FAO-56 module are the acceptance evidence for Objective 2 |

---

## Planned structure

```
backend/
├── README.md
├── requirements.txt
├── host.json
├── api/
│   ├── main.py
│   ├── routers/
│   │   ├── fields.py
│   │   ├── recommendations.py
│   │   └── actions.py
│   └── schemas/
│       └── models.py
├── functions/
│   ├── ingest/
│   ├── recommend/
│   └── notify/
├── core/
│   ├── fao56.py              # Reference ET and water balance
│   ├── pedotransfer.py       # Field capacity and wilting point from texture
│   ├── decision_rule.py      # Irrigate or wait, and depth
│   └── justification.py      # Two-factor plain-language explanation
├── data/
│   ├── openmeteo_client.py
│   ├── nasapower_client.py
│   ├── soilgrids_client.py
│   ├── cosmos_repository.py
│   ├── sql_repository.py
│   └── redis_cache.py
└── tests/
    ├── test_fao56.py
    ├── test_decision_rule.py
    └── test_clients.py
```

---

## The decision rule, stated precisely

This is the core logic and will be implemented in `core/decision_rule.py`:

```
Given:
  D    = current root-zone depletion (mm)
  TAW  = total available water in the root zone (mm)
  p    = crop-specific allowable depletion fraction
  RAW  = readily available water = p × TAW
  ETc  = forecast crop evapotranspiration per day (mm)
  P    = forecast effective rainfall per day (mm)
  H    = forecast horizon (days)

For each day d in 1..H:
    D(d) = D(d-1) + ETc(d) - P(d)      bounded at 0 ≤ D ≤ TAW

Let d* = the first day where D(d) > RAW

If d* does not exist within H:
    decision = WAIT
    validity  = H days
Else if d* == 1:
    decision = IRRIGATE today
    depth    = D(0) + ETc(1) - P(1)     restore to field capacity
    validity = 24 hours
Else:
    decision = WAIT
    next check on day d* - 1
    validity = min(d* - 1, forecast confidence horizon) days
```

The ML residual correction adjusts `D(d)` before the threshold test; it does not
replace this structure. **The physics bounds the model's error.**

---

## Interfaces this component owns

| Consumer | Interface |
|---|---|
| Frontend | REST API via API Management — the recommendation object contract documented in `src/frontend/README.md` |
| ML model | HTTPS call to the Azure ML managed endpoint, versioned request/response |
| Notification dispatch | Service Bus message, so a notification failure never loses a recommendation |
| Database | Repository classes; no raw SQL or Cosmos queries outside `data/` |

---

## Non-negotiable rules

1. **No secrets in code.** All credentials from Azure Key Vault via managed
   identity. Local development uses `.env`, which is gitignored.
2. **Persist before dispatch.** The recommendation is written to Cosmos DB and SQL
   Database *before* the Service Bus message is sent, so a dispatch failure cannot
   lose it.
3. **Check the cache before the upstream call.** Every Open-Meteo request goes
   through Redis keyed by grid cell. This is what keeps the platform inside the
   free API quota.
4. **The same feature code at training and inference.** Feature engineering lives
   in one module, imported by both the ingest Function and the ML training
   pipeline.
5. **Every recommendation carries a model version.** Untraceable advice is not
   defensible at review.

---

*Phase-I: planning and documentation. No code has been written.*
