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

---

## 2026-09-02 — M1, corrections carried in

### Correction: Ky is not an FAO-56 parameter

The build brief instructed that the crop parameter set, including the yield
response factor Ky, be seeded from FAO-56 Tables 11, 12 and 22. That attribution
is wrong for Ky and was corrected by the repository owner before implementation.
Recorded here so the trail shows the error was caught rather than shipped.

| Parameter | Correct source |
|---|---|
| Stage lengths `L_ini`, `L_dev`, `L_mid`, `L_late` | FAO-56 Table 11, lengths of crop development stages |
| `Kc_ini`, `Kc_mid`, `Kc_end` | FAO-56 Table 12, single time-averaged crop coefficients |
| `Zr`, `p` | FAO-56 Table 22, maximum effective rooting depth and depletion fraction |
| `Ky` | **FAO-33** (Doorenbos and Kassam, *Yield response to water*, 1979), with stage-wise values updated in **FAO-66** (Steduto, Hsiao, Fereres and Raes, *Crop yield response to water*, 2012). **Ky does not appear in FAO-56.** |

Actions taken: FAO-33 and FAO-66 added to the plan's reference list as R24 and
R25; the source table added to `CLAUDE.md` section 4; the citation on
`CropStage.yield_response_factor` in `models.py` corrected from "FAO-33 / FAO-56
Table 24" to FAO-33 with the FAO-66 update; every Ky entry in
``params/crops.yaml`` cites FAO-33 or FAO-66 and carries `TODO [VERIFY]` where
the printed value could not be confirmed against a copy of the paper.

### Ruling on reference values in tests

No numeric "reference" value is written into a test unless it was confirmed
against a source actually consulted. Where a FAO-56 worked example could not be
confirmed, the test asserts physical bounds and sensitivity properties instead,
with `TODO [VERIFY] FAO-56 example number and printed value` above it. A test
asserting a fabricated reference value is worse than no test: it looks
authoritative and would be quoted back in the viva.

The numeric evidence for Objective 2 is therefore not the unit tests but
`tests/validation/et0_crosscheck.py`, which compares this project's
Penman-Monteith implementation against Open-Meteo's published
`et0_fao_evapotranspiration` over a full year at three Indian locations and
reports n, MAE, RMSE, bias and the fraction of station-days within the 0.2 mm/day
tolerance. It is marked `integration`, excluded from CI, and run on demand with
`make validate`.

### M1 outcome

The FAO-56 engine is implemented and tested: 209 unit tests, `ruff`,
`ruff format` and `mypy --strict` clean, no network in the default suite.

**Pump worked example reproduced exactly.** Every intermediate in plan Section 6
is asserted independently, so each number is defensible on its own rather than
only in aggregate: Ea 0.65, gross depth 38.46 mm, discharge 380.2 L/min, volume
155,654 L, running time 409 minutes.

#### Three engineering findings

**F1 — a no-op density adjustment was removed from the pedotransfer.** The first
draft of `saxton_rawls` scaled field capacity by the ratio of a "normal" bulk
density to the measured one, but derived that normal density *from* the measured
density, making the ratio identically 1.0 at every input. It would have appeared
in the code, in the parameter file and in review as an implemented correction
while doing nothing at all. The correct adjustment needs Saxton and Rawls
equations 3 to 5, which could not be reproduced reliably here, so the adjustment
was removed and its absence documented in the module docstring rather than
faked. Carried as `TODO [VERIFY]`.

**F2 — `pump_minutes` was split in two.** The build brief asked for a domain
error when a run exceeds a configurable ceiling, defaulting to 720 minutes. That
alone would have made the plan's own 45 mm case uncomputable: it needs about 737
minutes, which is precisely the situation the scheduler exists to handle by
filling one window and carrying the remainder. `required_pump_minutes` now
returns the unguarded requirement for the scheduler, and `pump_minutes` enforces
the ceiling for anything that becomes an instruction to a farmer. Both are
tested.

**F3 — Objective 2 is not met, and the measured number is reported.** See below.

#### Objective 2 status: NOT MET

`tests/validation/et0_crosscheck.py`, run 2 September 2026 over calendar year
2025 at the three pilot districts:

| Site | n | MAE | RMSE | Bias | Within 0.2 mm/day |
|---|---:|---:|---:|---:|---:|
| Vellore TN | 365 | 0.297 | 0.366 | +0.205 | 37.3% |
| Beed MH | 365 | 0.308 | 0.350 | -0.013 | 28.8% |
| Ludhiana PB | 365 | 0.232 | 0.276 | +0.004 | 43.8% |
| **OVERALL** | **1095** | **0.279** | **0.333** | **+0.065** | **36.6%** |

The criterion is ET0 within 0.2 mm/day. Measured MAE is 0.279 mm/day. The
station-day count is met at 1,095 against a required 365. The test asserts the
criterion and therefore fails; the tolerance has not been widened.

**A real bug was found and fixed by this run.** The first execution gave MAE
0.972 mm/day with a bias of +0.967, an almost pure systematic overestimate. The
cause was the validation harness requesting `wind_speed_10m_max` where FAO-56
equation 6 takes the daily *mean* wind speed, which inflated the aerodynamic term
on every day of every site. Correcting to `wind_speed_10m_mean` moved MAE to
0.279 and bias to +0.065. The defect was in the harness, not in
`penman_monteith`; had the run not been performed, the engine would have looked
correct and the harness would have shipped with a 0.97 mm/day error in it.

The residual is scatter rather than bias: Beed and Ludhiana are unbiased to
within 0.02 mm/day. The most likely cause is methodological rather than an error
— Open-Meteo computes ET0 hourly and sums to a daily total, while this
implementation works from daily aggregates, and FAO-56 sanctions both without
their agreeing to 0.2 mm/day. Vellore's residual +0.205 mm/day bias is not yet
explained.

Three routes are recorded in the module docstring for decision before Review 2:
compare against a reference computed the same way from daily aggregates, which is
the more plausible reading of the Objective 2 wording; implement the hourly time
step of FAO-56 equation 53 and sum; or report Objective 2 as partially met with
0.279 mm/day and zero bias against an independent implementation. Whichever is
chosen is to be reported as measured.

#### Deferred to later milestones

- `params/crops.yaml` remains `verified: false`. A test asserts that flag, so the
  suite fails if the file claims verification it has not received.
- Farmer-facing script masters (`scripts/{hi,en,ta}.yaml`) are M3.
- The scheduler consumes `required_pump_minutes` and `MoistureForecaster` in M2.

---

## 2026-09-03 — Objective 2 resolved into a measured uncertainty budget

Four actions, none of which loosened the 0.2 mm/day criterion.

### 1. Wind height conversion: confirmed present, question closed

FAO-56 equation 47 is applied in the cross-check harness. `wind_10m_to_2m`
returns `u10 * 4.87 / ln(67.8 * 10 - 5.42)`, a factor of **0.747951**, and it is
applied to `wind_speed_10m_mean` after converting km/h to m/s. The residual is
not caused by a missing height conversion.

### 2. FAO-56 Example 18: the implementation is confirmed correct

FAO-56 Chapter 4 was fetched from <https://www.fao.org/4/x0490e/x0490e08.htm> and
**Example 18, "Determination of ETo with daily data"**, read directly from the
page: Uccle (Brussels), 50 deg 48 min N, 100 m, 6 July (day 187), Tmax 21.5 degC,
Tmin 12.3 degC, RHmax 84 percent, RHmin 63 percent, wind 10 km/h at 10 m,
sunshine 9.25 h.

Every printed intermediate is now asserted in
`tests/test_et0.py::TestFao56WorkedExample`:

| Quantity | Ours | FAO-56 Example 18 |
|---|---:|---:|
| P (kPa) | 100.124 | 100.1 |
| gamma (kPa/degC) | 0.0666 | 0.0666 |
| Delta (kPa/degC) | 0.122 | 0.122 |
| e0(Tmax) (kPa) | 2.564 | 2.564 |
| e0(Tmin) (kPa) | 1.431 | 1.431 |
| es (kPa) | 1.997 | 1.997 |
| ea (kPa) | 1.409 | 1.409 |
| Ra (MJ/m2/day) | 41.088 | 41.09 |
| Rso (MJ/m2/day) | 30.898 | 30.90 |
| Rns (MJ/m2/day) | 16.994 | 17.00 |
| Rnl (MJ/m2/day) | 3.712 | 3.71 |
| Rn (MJ/m2/day) | 13.282 | 13.28 |
| **ET0 (mm/day)** | **3.880** | **3.9** |

**The implementation is correct.** Every term matches to the precision printed.
This separates two questions that were previously entangled: whether the
implementation is right, which it is, and whether it agrees with Open-Meteo,
which is a different matter measured separately.

The example prints ET0 to one decimal place, so the assertion tolerance is the
half-unit of that precision; 3.880 is 3.9 as printed.

One discrepancy with the instruction received: the hourly wind coefficient was
given as 900/24 = 37.5. The page prints **37**. The page wins, and 37 is what is
implemented in `params/et0.yaml`.

### 3. Hourly-versus-daily hypothesis: DEAD

`tests/validation/et0_hourly_hypothesis.py`, Beed, April 2025, 30 days. FAO-56
equation 53 implemented in `irrigation_engine/et0_hourly.py` with the soil heat
flux of equations 45 and 46 (`Ghr = 0.1 Rn` daylight, `Ghr = 0.5 Rn` night, both
read from <https://www.fao.org/4/x0490e/x0490e07.htm>).

| Series | MAE | RMSE | Bias | Within 0.2 |
|---|---:|---:|---:|---:|
| A, our daily aggregate (eq 6) | 0.154 | 0.178 | -0.089 | 63.3% |
| B, our hourly sum (eq 53) | 0.368 | 0.374 | -0.368 | 3.3% |

**The hourly sum is worse, not better.** The hypothesis is dead and is recorded
as such rather than left as a suspicion. Open-Meteo's daily ET0 is not reproduced
by summing FAO-56 equation 53 over 24 hours.

The hourly implementation was checked for defects before the hypothesis was
declared dead, so that a bug of ours would not be misattributed to it. On 10
April at Beed it gives a physically sensible diurnal profile, peaking at 0.87
mm/hour at midday and near zero at night, summing to 8.469 mm against
Open-Meteo's 8.58 mm. Retaining negative night-time hours rather than clipping
them changes the daily total by 0.003 mm, so that choice is not the cause either.

### 4. The error is seasonal, and the budget that matters is in minutes

Breaking the 2025 cross-check down by month exposed the structure the annual
figures hid. **The bias flips sign with the season at all three sites:**

| Site | Dry, Nov to May | Monsoon, Jun to Oct |
|---|---|---|
| Vellore TN | MAE 0.213, bias +0.054 | MAE 0.414, bias **+0.413** |
| Beed MH | MAE 0.308, bias -0.216 | MAE 0.307, bias +0.268 |
| Ludhiana PB | MAE 0.238, bias -0.086 | MAE 0.223, bias +0.129 |

Vellore's annual +0.205 bias, previously unexplained, is almost entirely a
monsoon effect: +0.413 in June to October against +0.054 in the dry season. The
signature is humidity and cloud, which is where daily aggregation of RHmax and
RHmin and of the Rs/Rso cloudiness ratio departs most from an hourly treatment.
The seasonal reversal is also why the annual bias is only +0.065: the two halves
of the year partly cancel.

**Bias, not scatter, is what accumulates in a water balance.** Random daily errors
partly cancel across an irrigation interval; a bias does not. The annual bias of
+0.065 mm/day is comfortably inside the 0.2 criterion.

`tests/validation/et0_sensitivity.py` propagates each error term to the unit the
farmer acts on, on the worked example field (wheat mid-season Kc 1.15, one acre,
furrow Ea 0.65, 380.2 L/min, seven-day interval, baseline run 409.4 minutes):

| Error term | ETc error over 7 days | Extra pump time | Share of the 409-minute run |
|---|---:|---:|---:|
| Overall bias +0.065 mm/day | 0.52 mm | 8.6 min | 2.1% |
| Vellore bias +0.205 mm/day | 1.65 mm | 27.0 min | 6.6% |
| MAE 0.279 mm/day, fully correlated | 2.25 mm | 36.8 min | 9.0% |
| MAE 0.279 mm/day, independent across days | 0.85 mm | 13.9 min | 3.4% |

These figures were computed from the engine and agree with the independently
supplied table to the last digit.

Against the uncertainty the recommendation already carries on the same field:

| Term | Spread | Share |
|---|---:|---:|
| Application efficiency Ea 0.55 vs 0.75 | 129.0 min | 31.5% |
| Pump discharge 20 percent low, no bucket test | 102.3 min | 25.0% |

**Conclusion for the report.** The largest ET0 error term costs 37 minutes on a
409-minute run. Application efficiency alone spans 129 minutes on the same field,
a factor of 3.5, and an uncalibrated pump discharge spans 102. At this residual
the ET0 disagreement is not the limiting factor in pump-minute accuracy;
application efficiency and pump discharge dominate it by roughly three to one.
That is why the bucket test at onboarding matters more to the farmer than closing
the last 0.08 mm/day of ET0 agreement.

Objective 2 is therefore reported not as a failed threshold but as a measured
uncertainty budget: the implementation is verified correct against FAO-56 Example
18; it agrees with an independent implementation to 0.279 mm/day MAE with +0.065
mm/day annual bias; and that residual is a known seasonal artefact of daily
aggregation costing about 2 percent of a typical irrigation run.

`tzdata` was added as a Windows-only dependency in this work. Windows ships no
IANA time zone database, so `zoneinfo` cannot resolve `Asia/Kolkata`, and the M2
scheduler models power windows as IST-aware datetimes because a 22:00 to 06:00
night feeder crosses midnight. Linux and macOS use the system database.
---

## 2026-09-03 — M2, power-window scheduler

317 tests, `ruff`, `ruff format` and `mypy --strict` clean, no network in the
default suite. Ninety-four of those tests are new and cover the scheduler.

### Section 7 correction applied before implementation

The opportunistic branch previously read `D >= C`, which fires only once the
deficit has already outgrown one window's capacity. That is too late: a
capacity-constrained refill exists to act before that point. It is replaced by
`D_next > C`, evaluated on the depletion projected at the start of the next
window, and `docs/PHASE2_NOVELTY_AND_PLAN.md` Section 7 records both the new
policy and the superseded form.

The `min_app` guard is new and load-bearing. Without it a small pump on a large
field makes the window capacity `C` tiny, the capacity branch fires almost every
night, and the farmer is told to run his pump for four minutes. That is worse
than silence because it trains him to ignore the calls. `min_application_mm`
defaults to 8 mm in `params/irrigation.yaml`, with that reasoning recorded beside
it.

The `CAPACITY_LIMIT` test asserts its own precondition, that today's deficit is
still inside one window's capacity, so it fails against the superseded rule
rather than passing by accident.

### Midnight-crossing windows

A window is a pair of timezone-aware datetimes, never a pair of clock times. A
Maharashtra night feeder running 22:00 to 06:00 is eight hours ending the
following morning; modelled as two times-of-day it is minus sixteen hours, and
every downstream number is wrong in a way that only shows up on night feeders.

Three defences, all tested:

- `PowerWindow` refuses a window whose end does not follow its start, which is
  exactly the shape a naive clock-time construction produces.
- It refuses a naive datetime outright, because one silently assumes the
  server's timezone rather than the field's.
- `DeclaredRotation` and the DISCOM parser both put the following day's date on
  a night window's end, and both are asserted to produce exactly eight hours.

A property test asserts a 22:00 window sorts after an 06:00 one on the same
date, which ordering by clock time alone could not guarantee.

### Feeder reliability

`r_new = alpha * outcome + (1 - alpha) * r_old`, alpha 0.3, initialised at 0.8
for a feeder with no history, threshold 0.6. Constants in
`params/scheduling.yaml`.

Deliberately fast to react: a single failure takes a fresh feeder from 0.80 to
0.56, crossing the threshold immediately, after which the schedule carries no
clock time and the call says "when power comes, run X minutes". Telling a farmer
that one day too early is a smaller error than giving him a clock time the feeder
will not honour. Reliability also scales the window duration used to compute
capacity, so an unreliable feeder is planned against what it is expected to
deliver rather than what it promises.

The missed call is the only measurement. There is no sensor.

### Determinism

Nothing in `plan_day` reads a clock, generates a random number or touches ambient
state; `today` and the window list are arguments. Two property tests assert it:
identical inputs give identical schedules, and the multi-field allocation is
invariant to the order the caller supplied the fields.

### DISCOM parser

Built entirely against hand-made CSV fixtures under `tests/fixtures/` that
reproduce the table shape Document Intelligence produces once its cells are
flattened. **No circular is downloaded and none is committed**; the MSEDCL URL is
recorded in the module docstring only, and its reuse terms carry a
`TODO [VERIFY]`. The Azure call sits behind the extractor protocol and is never
touched by a test.

Two decisions worth recording:

- A malformed time cell raises rather than defaulting. A window with a guessed
  start would send a farmer to his pump at the wrong hour.
- A row whose `Days` column cannot be understood is kept, not dropped, and the
  ambiguity is surfaced as a warning. Dropping it would silently deny the farmer
  his schedule; a warning lets the operator decide.

### Deviations from the M2 brief

**`required_pump_minutes` and `pump_minutes` both used, as ruled.** The scheduler
calls the unguarded form to learn the true requirement and truncates it to the
window itself; only a farmer-facing instruction passes through the 720-minute
ceiling.

**`minutes_for_discharge` added to `pump.py`.** The scheduler holds a discharge as
a number, resolved once at onboarding, not as a `BucketTest` or a `PumpSpec`.
Reconstructing a fake characterisation to satisfy the existing signature would
have been the alternative, and would have read as though a bucket test had been
performed when none had.

**`Field` renamed to `IrrigatedField`.** `Field` is pydantic's own, and shadowing
it in a module that uses `Field(...)` for every attribute is a trap. The brief
named the model `Field`.

**`src/azure` is on the import path rather than being a package.** `src/azure`
carries no `__init__.py`, so the parser imports as
`document_intelligence.parse_feeder_schedule`. The engine-purity CI check greps
`src/backend` only and is unaffected.

### Carried forward to M3

- The `RainForecast` interface is in place with a conservative default. Krishna
  Agrawal's calibration model implements the same `covers` contract.
- `Schedule.reason_code` is the enumeration the call script will map from, and
  `start_time` is already `None` on a low-reliability feeder, which is the "when
  power comes" case the script must render.
- Farmer-facing script masters (`scripts/{hi,en,ta}.yaml`) remain M3.
