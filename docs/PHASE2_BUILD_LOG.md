# Phase-II Build Log

Chronological engineering record for Phase-II of *Cloud-Based Smart Irrigation
Recommendation using Weather Intelligence* (BITE412L, Dr. Priya V).

Maintained by Aarush Pandit (23BIT0416) on `feature/student2`. One entry per
working session. Entries are append-only; superseded statements are marked as
superseded rather than deleted, so the reasoning trail survives review.

---

## 2026-09-02 — M0, orientation

### Documents read

`README.md`, `docs/README.md`, `docs/WORK_DISTRIBUTION.md`,
`architecture/azure_cloud_architecture.md`, `architecture/system_architecture.md`,
`dataset/README.md`, `src/README.md`, `src/backend/README.md`,
`src/azure/README.md`, `src/frontend/README.md`, `src/ai_model/README.md`,
`literature_survey/research_gap_23BIT0416.md`, `.gitignore`.

`docs/PHASE2_NOVELTY_AND_PLAN.md` — **not present in the repository.** See
Blocker B1 below. The understanding recorded in this entry is therefore drawn
from the Phase-II engineering brief and the committed Phase-I documents, and is
provisional until the plan document is available.

### Understanding of Phase-II, in ten lines

1. The system is a zero-hardware irrigation advisory: no soil moisture sensor,
   no field controller and no actuator is required for a field to receive advice.
2. A FAO-56 root-zone water balance is driven by Open-Meteo forecast data, which
   already publishes `et0_fao_evapotranspiration`, so ET0 is consumed rather than
   re-derived; an independent Penman-Monteith implementation exists only as a
   cross-check on that published value.
3. ISRIC SoilGrids supplies texture and bulk density for the 0-30 cm root zone,
   and a Saxton-Rawls pedotransfer function converts these into field capacity
   and wilting point, hence total and readily available water.
4. The balance yields a root-zone depletion in millimetres, which is converted
   into pump running minutes for the farmer's actual pump, characterised either
   by a bucket test or by a horsepower-and-head specification.
5. The novelty is scheduling: those minutes must fit inside the rationed
   agricultural electricity window that the farmer's feeder actually receives,
   taken from DISCOM schedule PDFs or from a declared day/night rotation.
6. Because the next window may not arrive before depletion exceeds readily
   available water, the scheduler refills early to the capacity of the current
   window, carrying the unmet depth forward rather than discarding it.
7. A forecast-skip rule suppresses irrigation when a calibrated rain probability
   indicates that forecast rainfall will cover the deficit; calibration, not the
   raw forecast probability, is what makes the rule safe to act on.
8. Delivery is an outbound voice call in the farmer's language, plus three
   missed-call numbers that serve as the field sensor: A water was given, B power
   did not arrive, C repeat today's plan. A missed call is free to the farmer and
   requires no literacy, no smartphone and no application.
9. An icon-only progressive web application exists for demonstrations and for
   literate family members; it renders what the backend decides and never
   computes a recommendation itself.
10. The decision path is deterministic end to end. No language model participates
    in it. Generative components are confined to rendering: script templating,
    Azure AI Speech for synthesis and Azure AI Translator for language coverage.

### Conflicts between the Phase-II brief and the committed Phase-I documents

Recorded for resolution before implementation begins. Each names the Phase-I text
it contradicts. None has been acted on.

**C1 — Delivery channel.** `README.md` Objective 4 and `system_architecture.md`
Stage 5 specify dashboard, push notification and SMS. The Phase-II brief makes an
outbound voice call and three missed-call numbers the primary channel, with the
PWA demonstration-only. Objective 4's acceptance criterion, end-to-end latency
under five minutes for 95% of recommendations, was written for push dispatch and
does not describe a placed telephone call.

**C2 — Frontend technology.** `README.md` Technology Stack and
`src/frontend/README.md` specify React 18, Vite, Tailwind CSS, Recharts and a
Vite PWA plugin, with a documented component tree. The Phase-II brief specifies a
no-build progressive web application in plain HTML, CSS and JavaScript. These are
mutually exclusive descriptions of the same folder.

**C3 — Machine learning in the decision path.** `README.md` Objective 3 requires
a soil-moisture forecast model achieving R-squared of at least 0.80 on a held-out
season. `src/ai_model/README.md` makes `prediction = FAO-56 baseline + learned
residual` the organising principle, and adds an LSTM trajectory model and a SHAP
justification generator. The Phase-II brief recasts the learned component as
forecast rain-probability calibration plus a policy simulation study, and states
that the decision path is deterministic. Under the Phase-II scope as briefed,
Objective 3 is not attempted, and the residual-correction model, the LSTM and the
SHAP generator are not built.

**C4 — Evapotranspiration acceptance criterion.** Objective 2 requires computed
ET0 within 0.2 mm/day of the FAO-56 Penman-Monteith reference on at least 365
held-out station-days. The Phase-II brief consumes Open-Meteo's published ET0 and
uses an own Penman-Monteith implementation only as a cross-check, so both the
quantity being validated and the station-day corpus that would validate it
change.

**C5 — Statement of novelty.** The Phase-I novelty is translation and delivery:
turning free forecast data into a specific instruction for an uninstrumented
field. The Phase-II novelty is scheduling irrigation inside a rationed
agricultural electricity window. No committed Phase-I document mentions
electricity rationing, DISCOM feeder schedules, power windows, pump running
minutes or the farmer's pump. This is the largest divergence in the set: it is an
addition to the project's contribution rather than a refinement of it, and the
literature survey and research gap analysis do not currently support it.

**C6 — Objective 6 baseline.** Objective 6 measures at least 20% water saving
against a fixed-interval baseline with no increase in modelled crop water stress
days. That baseline measures the forecast-driven contribution but is silent on
the power-window contribution, which is the Phase-II novelty. The simulation
study needs a policy set that isolates it.

**C7 — Azure service inventory.** `src/azure/README.md` and the `README.md`
Technology Stack commit to Data Factory, Azure SQL Database, Cache for Redis,
Service Bus, API Management, Notification Hubs, Virtual Network with private
endpoints, Front Door with WAF, and Azure Machine Learning. The Phase-II M5 Bicep
inventory is Storage, Cosmos DB serverless, Functions on consumption, Key Vault,
Application Insights, AI Speech, AI Document Intelligence, Communication Services
and Static Web App. Nine planned services are dropped. Objective 5 in particular
requires all data-plane services to sit behind private endpoints or authenticated
gateways, which the M5 inventory does not provide.

**C8 — Backend framework.** `src/backend/README.md` specifies a FastAPI service
fronted by API Management, with a documented folder tree under `backend/`. The
Phase-II brief specifies Azure Functions HTTP triggers on the Python v2
programming model, no FastAPI, no API Management, and a different layout:
`src/backend/irrigation_engine/` as a pure library plus `src/azure/functions/`.

**C9 — Teammate scope as declared in Phase-I.** `docs/WORK_DISTRIBUTION.md`
section 5 assigns Krishna Agrawal the feature pipeline, LSTM, residual model,
SHAP generator, Azure ML training jobs, model registry and retraining schedule;
the Phase-II brief narrows him to calibration and simulation. It assigns Nayan
Jaggi a React dashboard with offline cache and charts; the Phase-II brief gives
him a no-build PWA and voice script masters. Both teammates' recorded Phase-I
commitments shrink, and that record is a committed document visible to the
examiner.

**C10 — Language coverage.** `README.md` and `src/frontend/README.md` commit to
English, Hindi and Tamil. The Phase-II script masters are Hindi and English only,
with further languages generated later. One of the three demonstration farmers is
in Vellore, Tamil Nadu, so Tamil is on the demonstration path.

**C11 — Datasets D5 and D6.** `dataset/README.md` specifies the Kaggle Crop
Irrigation Scheduling dataset as the supervised label source and the
International Soil Moisture Network as the independent validation source. Neither
has a role in any Phase-II milestone. M6 adds D7, D8 and D9 but does not say
whether D5 and D6 are withdrawn, and `dataset/README.md` is Krishna's file under
the Phase-I authorship record.

**C12 — Blanket CSV rule in `.gitignore`.** The committed `.gitignore` ignores
`*.csv` everywhere and un-ignores only `docs/**/*.csv`. M2 requires a fixture CSV
under `tests/` for the feeder-schedule parser, and M4 and M6 require simulation
outputs as CSV in `results/`. Both would be silently excluded from commits.

### Blockers

**B1 — `docs/PHASE2_NOVELTY_AND_PLAN.md` is absent.** It is not in the working
tree, not on `main`, `develop`, `feature/student1`, `feature/student2` or
`feature/student3`, not anywhere in the repository history, and not present
elsewhere on the build machine. The brief names it as the authoritative
specification, and later milestones cite it by section: the scheduling policy is
Section 7, the simulation policy set is Section 12, the MSEDCL feeder schedule
URL is taken from it, and the pump worked example (wheat, one acre, 25 mm,
furrow, 5 HP at 30 m head, approximately 410 minutes) is stated in it. M1 onward
cannot be built to specification without it.

**B2 — Git identity is not the GitHub address.** `user.email` on this clone is
`aarush@example.com` and `user.name` is `Aarush`. Commits made with that address
do not attribute to the `aarush093` GitHub account and will not appear in the
contribution graph the review assesses. No commit has been made pending
correction.

### Repository state at start of session

Local `feature/student2` was 13 commits behind `origin/feature/student2`, and its
working tree was missing `dataset/`, `references/`, `results/`,
`src/frontend/README.md`, `src/ai_model/README.md` and three `literature_survey/`
files. Fast-forwarded to `db00d08`; the tree now matches the remote and Phase-I is
confirmed complete. No Phase-II code exists yet.

---

## 2026-09-02 — M0, conflict resolution and scaffolding

### Blockers cleared

**B1 resolved.** `docs/PHASE2_NOVELTY_AND_PLAN.md` was supplied and committed as
`7ab941c`. Sections 7 and 12 supply the scheduling policy and the four-policy
evaluation plan; Section 17, written in response to the orientation entry above,
rules on every conflict raised. The plan is the authority for all subsequent
work; where this log and the plan disagree, the plan wins.

**B2 resolved.** Workspace moved to a fresh clone at
`Projects/SmartIrrigation_Azure_Cloud_Project_2026`. The stale clone under
`AppData/Roaming/SPB_Data/` and the unversioned copies under `Downloads/` are
abandoned. Repository-level git identity set to `Aarush Pandit
<153858722+aarush093@users.noreply.github.com>`; verified on the first commit.

### Resolutions

The governing principle, from Section 17: Phase-I is a submitted and graded
record and is not rewritten. Phase-II is an addendum in which every Phase-I
objective, service, dataset and technology keeps its entry and receives a
Phase-II status. Per-conflict rulings:

| Ref | Ruling | Where it is recorded |
|---|---|---|
| C1 | Extension, not replacement. PWA replaces the dashboard, ACS SMS retained as text fallback, voice call and missed calls added as primary. Objective 4 criterion unchanged | Plan 17.2 |
| C2 | Frontend stays React 18, Vite, Tailwind, `vite-plugin-pwa` as declared; prepared in `handoff/student1_frontend/` | Plan 17.4 |
| C3 | Objective 3 retained, moved off the critical path behind a `MoistureForecaster` protocol with a `KcEt0Forecaster` fallback. Krishna delivers the LSTM in weeks 4 to 5; the calibration model is additional | Plan 17.2, 8 |
| C4 | Objective 2 criterion retained verbatim. The ET0 cross-check is an M1 deliverable | Plan 17.2 |
| C5 | Novelty is an extension of the Phase-I translation-and-delivery gap, not a new one. README gains a "Phase-II scope refinement" section; sources R1 to R8 go to `literature_survey/phase2_addendum.md` as supplementary, leaving the fifteen mandated papers untouched | Plan 17.1 |
| C6 | Objective 6 criterion retained. The Section 12 four-policy simulation is the objective, with fixed-interval calendar irrigation as the baseline | Plan 17.2 |
| C7 | No service dropped from the architecture. Bicep deploys the Section 17.3 core set; the remaining nine are declared with status "deferred to Phase-III" and a named substitute. Objective 5 met through authenticated gateways rather than private endpoints | Plan 17.3 |
| C8 | Backend stays FastAPI, hosted on Functions via `AsgiFunctionApp`, so the declared stack is what runs. Storage Queues replace Service Bus | Plan 17.4, 17.3 |
| C9 | No teammate scope shrinks. `docs/WORK_DISTRIBUTION.md` gains a Phase-II addendum table; the Phase-I table stays intact | Plan 17.5 |
| C10 | Tamil added as a third script master alongside Hindi and English, drafted here and tagged for native-speaker verification. Marathi, Telugu and Punjabi via Azure AI Translator later | Plan 17.4 |
| C11 | Nothing withdrawn. D5 marked "optional, Objective 3 only", D6 marked "validation set for Objective 3", D7 to D9 added | Plan 17.4, 11 |
| C12 | `.gitignore` gains negations for `results/**/*.csv`, `results/**/*.png` and `tests/fixtures/**/*.csv`; `data/raw/` stays ignored | Plan 17.6 |

### Amendments to the milestone brief, as instructed

1. M1 gains a `MoistureForecaster` protocol with `KcEt0Forecaster` as the default
   implementation, which Krishna's model will later satisfy.
2. M3 hosts a FastAPI application through `AsgiFunctionApp`; timer and queue
   triggers remain native Functions. Storage Queues, not Service Bus.
3. M4 ships `handoff/student1_frontend/` as a Vite, React and Tailwind project
   with `vite-plugin-pwa` and a Static Web Apps workflow file, and adds
   `train_soil_moisture.py` to `handoff/student3_ai_model/`.
4. M5 Bicep includes API Management (consumption) and an Azure Machine Learning
   workspace, and excludes Virtual Network, Front Door, SQL, Redis, Service Bus,
   Notification Hubs, Container Registry and App Service.
   `docs/AZURE_SERVICES_PHASE2.md` carries a Status column over all Phase-I
   services.
5. M6 edits to `README.md` are additive only; the Objectives table is untouched
   and a second "Phase-II acceptance mapping" table is added from Section 17.2.

### Verification items carried forward

Collected from the plan so they are not lost between milestones. Each becomes a
`# TODO [VERIFY]` at the point of use.

- Crop stage lengths for Indian varieties, per crop, from ICAR and state
  agricultural university packages of practice (plan Section 6, Section 15).
- Pump combined efficiency default of 0.5 and the head defaults, with a local
  pump dealer or Krishi Vigyan Kendra (Section 6).
- Azure AI Speech neural voice names for hi-IN, ta-IN, mr-IN, te-IN and pa-IN, at
  build time rather than from memory (Section 10, Section 15).
- ACS phone number availability for India and outbound PSTN rates (Section 15).
- TRAI TCCCPR 2018 position on consented transactional automated calls, before
  the pilot (Section 5.5).
- Reuse terms for the MSEDCL circular PDFs (Section 11, D7).
- IEEE citation metadata for R1, R2, R6, R9, R10, R11, R13, R14, R15 and R17
  (Section 16).
- Native-speaker check of every non-English script master (Section 17.4).

### M0 outcome

Scaffolding complete and verified. `ruff check`, `ruff format --check`,
`mypy --strict` and 29 unit tests pass locally and in CI, on Python 3.11 and
3.12, with the gitleaks secret scan and the engine-purity check green.

Three engineering decisions taken during the milestone, recorded because they
depart from the letter of the build brief:

1. **`pyyaml` is a fourth engine dependency.** The brief names numpy, pydantic
   and httpx only, but also mandates that every agronomic constant lives in
   `params/*.yaml` and every farmer-facing string in `scripts/*.yaml`. Reading
   YAML requires a YAML parser. `pyyaml` is small, pure-Python and ubiquitous, so
   it does not breach the dependency-light intent.
2. **mypy's `python_version` is not pinned to 3.11.** numpy 2.5 ships stubs using
   the Python 3.12 `type` statement, which mypy rejects when asked to target
   3.11, so pinning fails on a dependency rather than on project code. mypy now
   follows the interpreter, the CI lint job runs on 3.12, and 3.11 runtime
   support is proved by the pytest matrix instead. `ruff` still targets `py311`.
3. **`.gitattributes` added.** Not requested, but the team develops on Windows
   while CI runs on Linux, and without line-ending normalisation the first
   cross-platform edit produces a whole-file diff that hides the real change.

The engine is currently typed stubs raising `NotImplementedError`, each naming
its milestone and citing the FAO-56 equation or table it will implement. This is
deliberate: it fixes the public API before behaviour exists, so the scheduler,
the Functions layer and both teammate handoff packages can be written against a
contract that is already enforced by test.

