# Azure services, Phase-II

Every service named in the Phase-I planning table, with its Phase-II status, the
tier used, and what it actually does in this project.

**Phase-I is a submitted record and is not rewritten.** No service is removed
from the plan; each keeps its entry and receives a status. Where one is deferred,
a substitute meeting the same functional need at pilot scale is named. Plan
Section 17.3.

Everything marked Deployed is defined in `src/azure/infra/main.bicep`, which
compiles cleanly to 25 resource declarations. **Nothing has been deployed.**
`make deploy-plan` previews; `make deploy` is for the repository owner.

---

## Deployed in Phase-II

| Service | Tier | What it does here |
|---|---|---|
| **Azure Functions** | Y1 Consumption, Python 3.11 | The whole backend. `daily_plan` plans and calls hourly for the farmers due that hour; `acs_events` receives missed calls; `onboard` and `today` are the FastAPI routes, mounted through `AsgiFunctionApp` so the Phase-I declared stack is literally what runs. `keep_warm` raises the share of calls rejected inside the ring window and is comfort, not correctness. |
| **Azure Cosmos DB** | Serverless, continuous backup | Five containers: `farmers`, `fields`, `feeder_windows`, `schedules`, `events`. The `events` container is where idempotency is really enforced: the deduplication key is the document id, so a replayed missed call fails on the uniqueness constraint rather than on a set in process memory. Local authentication is disabled; the Functions identity holds the data-plane role. |
| **Azure Blob Storage** | Standard_LRS | Four containers. `raw` holds API responses as fetched, for reproducibility. `discom-pdfs` holds circulars fed to Document Intelligence and is never committed to git. `tts-cache` holds synthesised audio keyed by script hash, so each distinct utterance is synthesised once for the whole pilot. `deadletter` receives Event Grid failures, so a missed call is never lost silently. |
| **Azure AI Speech** | F0 (free) | Neural text to speech in the farmer's language. The blob cache is what makes F0 sufficient: the same script recurs for days, and a farmer replaying today's message hears the same file. |
| **Azure AI Document Intelligence** | F0 (free), 500 pages/month | `prebuilt-layout` table extraction from DISCOM feeder schedule circulars into `feeder_windows`. Circulars are parsed once when published, so the free allowance is far more than enough. |
| **Azure AI Translator** | F0 (free) | Drafts new language masters from the Hindi and English ones. Every draft is checked by a native speaker before use, so volume is negligible. |
| **Azure Communication Services** | Standard, **no phone number** | Deployed to show the integration is real: the Event Grid system topic and the missed-call subscription hang off it. **No number can be attached** — see the limitation below. |
| **Azure Event Grid** | Included | System topic on the Communication Services resource, subscribed to `IncomingCall`, delivering to `acs_events`. Retry is deliberately generous and dead-lettered; see below. |
| **Azure Static Web Apps** | Free | Hosts the icon-only PWA. 100 GB a month, which a three-tile page will not approach. Pointed at the frontend once Nayan Jaggi's pull request lands. |
| **Azure API Management** | Consumption | The authenticated gateway in front of the operator endpoints. Pay per call, no instance charge, scales to zero. |
| **Microsoft Entra ID** | Included | Authentication on the operator screen only. The farmer-facing channel is a phone call and has no login anywhere in it; his identity is his phone number, verified by the missed call itself. |
| **Azure Key Vault** | Standard, RBAC | Speech key, Document Intelligence key, ACS connection string. App settings reference them; no secret is ever valued in configuration. |
| **Application Insights** | Included with Log Analytics | Custom events for every scheduler decision, carrying reason code, window, minutes and carry-over, so any decision can be reconstructed after the fact. |
| **Azure Monitor / Log Analytics** | PerGB2018, capped 0.1 GB/day | Five alert rules, below. The daily cap is a hard stop, so a runaway log loop cannot spend the student credit. |
| **Azure Machine Learning** | Basic, **no compute** | Model registration and versioning for the Objective 3 and calibration models. Training runs locally; a compute instance would spend credit while idle. |
| **GitHub Actions** | Free for public repositories | Five CI jobs on every push: ruff, `mypy --strict`, pytest on 3.11 and 3.12, gitleaks, and the check that the engine imports no Azure SDK. |

---

## Deferred to Phase-III, with a substitute named

None of these is abandoned. Each is deferred on cost or time grounds with
something meeting the same functional need at pilot scale.

| Service | Why deferred | Substitute in Phase-II |
|---|---|---|
| **Azure Data Factory** | An orchestration tier for three farmers is cost without benefit | Functions timer trigger orchestrates the daily loop |
| **Azure SQL Database** | A second datastore doubles the operational surface for no gain at this scale | Cosmos DB holds all state; a relational audit store is added when a reporting requirement actually needs one |
| **Azure Cache for Redis** | No tier is free, and the cache would hold a few dozen forecasts | Forecast responses cached in Blob with a TTL; soil is fetched once per field for the life of the project |
| **Azure Service Bus** | A namespace charge for a queue that carries one message per farmer per day | Azure Storage Queues, which the Functions consumption plan includes |
| **Azure Notification Hubs** | The farmer channel is voice; push presumes a smartphone the target user does not have | Web push from the PWA service worker, for the operator and literate family members |
| **Virtual Network and private endpoints** | Private endpoints carry a per-hour charge per endpoint, which exceeds the entire remaining student credit | Objective 5 met through **authenticated gateways** instead: API Management with Entra ID on operator endpoints, Cosmos DB with local auth disabled and managed identity only, Key Vault with RBAC |
| **Azure Front Door with WAF** | No free tier; a WAF in front of a three-tile static page protects little | Static Web Apps includes managed TLS and a global CDN |
| **Azure Container Registry** | Nothing is containerised | Functions deploys from a package |
| **Azure App Service** | The consumption plan is sufficient, and the reason it is sufficient is established in the feasibility note | Functions on consumption |
| **Azure Backup** | A separate vault for a serverless database that already backs itself up | Cosmos DB continuous backup, 7-day tier, set in the Bicep |
| **Power BI** | A licence cost for figures that belong in the report anyway | Matplotlib figures committed under `results/` |

---

## The limitation that is not a deferral

**No phone number can be provisioned on this subscription, and this is not a
cost decision.**

Two independent blockers, either one decisive:

1. India does not appear in the country and region list for Communication
   Services telephone numbers.
2. Numbers cannot be acquired on trial accounts or with Azure free credits, and
   availability is restricted to subscriptions with a billing address in a
   supported region.

ACS **SMS** is documented as supporting United States numbers only, so the
Phase-I text fallback is blocked by the same restriction.

The system is unaffected because the adapter interface was built for exactly
this risk, which plan Section 15 recorded before it was confirmed.
`SimulatedTelephony` runs the complete daily loop with no phone number, no ACS
resource and no credit spend, and that is the demonstration path permanently.
`AcsCallAutomationTelephony` remains written and tested as the evidence the
integration was designed correctly. Full detail in
`docs/ACS_MISSED_CALL_FEASIBILITY.md` section 5.

---

## Two settings that deliberately depart from Microsoft's guidance

**Event Grid retry.** Microsoft recommends two delivery attempts and a
one-minute time to live for `IncomingCall`, because in an answer-the-call design
a late event is useless. This design never answers, so a late event is still a
valid field observation and may be the only one that field produces that day.
The subscription uses a 12-hour TTL, 30 attempts, and a dead-letter container.
Reasoning in the feasibility note, Decision 2.

**Consumption plan for an incoming-call webhook.** Microsoft advises against it
because a cold start can consume the 30-second ring window. That warning targets
applications that must answer. Here a missed rejection means the call rings out
on its own and the Event Grid event still arrives, so nothing is lost. Decision 1.

---

## The five alert rules

Objective 5 requires at least five configured Azure Monitor alert rules. Each is
named for the failure it watches, because an alert whose purpose is not obvious
gets muted rather than fixed.

| Alert | Watches for | Why it matters |
|---|---|---|
| `ingest-failure` | Weather or soil fetch errors | Objective 1 requires 99 percent ingestion success over 30 days |
| `scheduler-failure` | Exceptions in `daily_plan` | A farmer received no decision at all that day |
| `call-failure-rate` | Outbound calls not answered | The advice was computed and never reached anyone |
| `missedcall-webhook-errors` | Failures in `acs_events` | **The most serious of the five.** Missed calls are the only sensor this system has; losing them is silent data loss |
| `cosmos-throttling` | HTTP 429 from Cosmos | Serverless throughput exceeded |

---

## Deployment status

*Added 5 September 2026.*

**The infrastructure is a compiled and validated deliverable. It has not been
deployed, and will not be in Phase-II.**

| | |
|---|---|
| `src/azure/infra/main.bicep` | Compiles cleanly to **25 resource declarations**, verified with Bicep CLI v0.46.1 |
| Alert rules | **5**, generated from a `copy` loop: `ingest-failure`, `scheduler-failure`, `call-failure-rate`, `missedcall-webhook-errors`, `cosmos-throttling` |
| `make deploy-plan` | Ready. Runs `az deployment group what-if`, previews only, spends nothing |
| `make deploy` | Ready. One command, once a subscription exists |
| Deployed | **Nothing.** No Azure resource has been created and no credit has been spent |

**Why no live deployment.** Azure for Students is disabled in VIT's managed
tenant and self-signup is not permitted, so no subscription is available to this
project. The blocker is an institutional tenant policy, not a technical or
budgetary one: every resource in the template is on a free or consumption tier,
and the template targets a resource group rather than a subscription, so it
deploys with a single command the moment a subscription exists.

**What this costs the evidence.** Every claim in this document about *what the
template declares* is verified by compilation. Every claim about *runtime* — cost,
latency, alert firing, the ingestion availability figure Objective 1 asks for —
is not, and is marked `TODO [VERIFY]` rather than estimated. The distinction is
stated here so a reader does not have to infer which is which.

Azure CLI 2.90.0 and Bicep 0.46.1 are installed on the build machine, and
`az login` was attempted; it authenticated but returned no subscriptions, which
is what confirmed the tenant restriction rather than a configuration error.

---

## Cost

Every resource is on a free or consumption tier. At pilot scale, three farmers
with one call a day each, the expected steady-state cost is dominated by
Cosmos DB serverless request units and Functions executions, both of which sit
inside the Azure for Students free grant. The Log Analytics daily cap of
0.1 GB is the one hard stop configured, and it exists so that a logging mistake
cannot quietly consume the credit.

`TODO [VERIFY]` actual monthly cost against the portal after the first
deployment, and record it here. A stated cost with a number behind it is worth
more at review than a claim that it is cheap. Per the deployment status above,
this cannot be closed in Phase-II: it needs a subscription this project does not
have.
