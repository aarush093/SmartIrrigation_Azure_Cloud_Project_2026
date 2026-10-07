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
---

## 2026-09-03 — Objective 2 closed, and the crops verification corrected

### The crops verification was wrong, and the correction was itself wrong

Recorded in full because a correction that introduces an error is exactly the
kind of thing that otherwise survives into a report.

FAO-56 Table 12 prints `Kc_ini` on the **group header row**; an individual crop
row leaves that cell **blank** unless it overrides the group value. That
structure was misread on 3 September 2026, with two consequences:

1. Cotton's blank cell was read as a printed 0.30, and its correct seeded value
   of 0.35 was "corrected" to it. **The seeded value was right.** Cotton inherits
   the Fibre Crops header value of 0.35. Reverted.
2. Groundnut's blank cell was reported as unresolvable "because of the footnote
   markers". It is not unresolvable; it inherits the Legumes header value of 0.4.
   That field now flips to verified.

Confirmed group header values, read from the page:

| Group | Kc_ini | Crops here inheriting it |
|---|---|---|
| a. Small Vegetables | 0.7 | onion (dry) |
| b. Vegetables - Solanaceae | 0.6 | tomato |
| e. Legumes | 0.4 | groundnut, chickpea |
| g. Fibre Crops | 0.35 | cotton |
| i. Cereals | 0.3 | maize (grain) |

Rice (1.05), sugarcane (0.40) and winter wheat (0.4 frozen / 0.7 non-frozen)
print their own values and do not inherit.

A test now pins these group values, so the same misreading cannot recur silently.

### Two Kc_end choices corrected

**Tomato, 0.70 to 0.90.** The chapter's rule is that a frequently irrigated,
fresh-harvested crop keeps a wet topsoil and takes the **higher** value, while a
crop left to senesce and dry in the field takes the lower one. The previous
comment stated the rule inverted and selected 0.70 on that basis. Indian
fresh-market tomato is picked over several harvests and stays irrigated, so
**0.90**, which is also the conservative direction consistent with the
lower-bound convention adopted for Zr.

**Wheat, 0.25 to 0.40.** Footnote 10 gives the higher value to hand-harvested
crops, and smallholder rabi wheat in the pilot districts frequently is, so
**0.40**. The previous comment quoted footnote 10 correctly and then justified
0.25 using footnote 11, which belongs to maize. The two footnotes are now
distinguished explicitly in the file header.

Maize (0.35) and rice (0.60) were already correct and their reasoning already
matched the printed footnotes.

### Table 11 does contain Indian rows

The previous header note claimed it had none. It has two, both directly usable,
and both now replace borrowed non-Indian rows:

| Crop | L_ini | L_dev | L_mid | L_late | Total | Planted | Region |
|---|---:|---:|---:|---:|---:|---|---|
| Barley/Oats/Wheat | 15 | 25 | 50 | 30 | 120 | November | Central India |
| Maize (grain) | 20 | 35 | 40 | 30 | 125 | October | India (dry, cool) |

Wheat's previous 30/45/40/30 came from a Mediterranean row and maize's 25/40/45/30
from an arid-climate row. Both crops' `stage_days` now flip to verified, and a
test asserts that **only** these two crops may claim verified stage lengths.

Chick pea is confirmed absent from Table 11 entirely, so the existing note there
was correct. Every other crop keeps its non-Indian row with the region named and
stays unverified.

FAO-56 itself says Table 11 values "are useful only as a general guide and for
comparison purposes" and recommends local observation of plant stage development
wherever possible. That caveat is recorded in the file even for the two verified
Indian rows.

### A limitation now stated on every Kc_ini

FAO-56 Chapter 6: "The values for Kc ini in Table 12 are only approximations and
should only be used for estimating ETc during preliminary or planning studies."
More accurate estimates come from the chapter's wetting-frequency method, which
accounts for wetting interval, evaporative demand and the size of each wetting
event.

That method is not implemented. Kc_ini therefore carries a known accuracy
limitation on every crop, worst during the initial stage when the canopy is
sparse and soil evaporation dominates. Recorded in the parameter file header as a
Phase-III item.

---

### Objective 2: the book is closed

The final experiment asked whether the 0.279 mm/day residual is a difference in
*method* or a difference in the *input dataset*. Our own Penman-Monteith was run
twice over the same year and the same three sites, once on Open-Meteo (ERA5)
inputs and once on NASA POWER (MERRA-2) inputs, against Open-Meteo's published
ET0. `tests/validation/et0_input_dataset.py`, 1,095 station-days.

| Series | n | MAE | RMSE | Bias | Dry (Nov-May) | Wet (Jun-Oct) |
|---|---:|---:|---:|---:|---:|---:|
| A. our PM on Open-Meteo inputs vs published | 1095 | 0.279 | 0.333 | +0.065 | -0.082 | +0.270 |
| B. our PM on NASA POWER inputs vs published | 1095 | 0.672 | 0.873 | -0.032 | +0.052 | -0.149 |
| C. our PM: POWER inputs vs Open-Meteo inputs | 1095 | **0.735** | 0.929 | -0.098 | +0.134 | -0.419 |

**The answer is the input dataset, decisively.**

Series C is the finding. Our own identical implementation, fed two different
reanalysis products, disagrees **with itself** by 0.735 mm/day MAE. That is
**2.6 times larger** than the 0.279 mm/day residual against Open-Meteo's
independent FAO-56 implementation on shared inputs.

The residual is therefore not a defect in anything this project built. It is
smaller than the intrinsic disagreement between the reanalysis products that feed
it. Put the other way round: **this implementation agrees with an independent
FAO-56 implementation more closely than two reanalysis datasets agree with each
other.**

The seasonal reversal reproduces on POWER inputs too, with the sign flipped
(POWER runs high in the dry season and low in the monsoon relative to
Open-Meteo), which is again a property of the input products rather than of the
method.

Objective 2 is reported as a measured uncertainty budget, resting on three
established facts:

1. The implementation is **verified correct** against every printed intermediate
   of FAO-56 Example 18.
2. The residual is **not** an hourly-versus-daily artefact; the hourly sum is
   worse (0.368 against 0.154 at Beed).
3. The residual is **smaller than the disagreement between reanalysis products**,
   so no further accuracy is available from anything under this project's
   control.
4. At this residual, ET0 costs at most 37 minutes of a 409-minute run, while
   application efficiency spans 129 and pump discharge 102. ET0 is not the
   limiting factor in pump-minute accuracy.

**No further ET0 investigation. The question is not reopened.**
---

## 2026-09-03 — M3, call orchestrator, missed-call state machine and speech

516 tests, `ruff`, `ruff format` and `mypy --strict` clean across 52 source
files, all five CI jobs green. 199 of those tests are new.

### Item 1 first: the missed-call mechanism was verified before anything was built on it

Full write-up in `docs/ACS_MISSED_CALL_FEASIBILITY.md`. It works: Event Grid
delivers `Microsoft.Communication.IncomingCall` on ring, `data.from` and
`data.to` carry the phone numbers **before** any answer, and `Reject` is a
documented pre-call action in the Python SDK that prevents the call connecting at
all. The three-number vocabulary is implementable as designed.

**A correction to my own reasoning, recorded because it matters.** The first
draft of that document treated Microsoft's 30-second cold-start warning as a
binding constraint and recommended buying always-on compute. That was wrong. The
warning targets applications that must *answer* the call. This design never
answers: the success state for a missed call is that the call does not connect.
On a cold start the `Reject` misses the window, the call rings out, and the Event
Grid event still arrives and is still recorded. Both paths capture the reading.
Buying warm compute for a flow that never answers would have been indefensible at
review, and correctly so.

Four decisions follow, all recorded in that document:

1. **Consumption plan**, one Functions app, `function_app.py` at the deployment
   root. Cheaper and more defensible.
2. **Retry generously and dead-letter**, which reverses Microsoft's guidance for
   `IncomingCall`. They advise two attempts and a one-minute TTL because a late
   event is useless when you must answer. Here a late event is still a valid
   field observation and may be the only one that field produces that day, so the
   subscription gets a TTL in hours, the default attempt count, and a dead-letter
   destination in Blob Storage.
3. **A keep-warm timer as comfort, not correctness.** Removing it changes the
   share of calls rejected inside the ring window, never whether an event is
   recorded, and
   `tests/test_events.py::TestIdempotency::test_timing_within_the_day_does_not_change_the_outcome`
   is the test that holds that line.
4. **Confirmation is carried on the next call**, not on a new one: "kal aapne
   bataya tha ki paani de diya". Zero marginal cost, and it gives the farmer a
   chance to correct us if we logged the wrong thing.

### The operational day, found by a test rather than by inspection

The deduplication key was originally the caller, the number called and the IST
**calendar** date. A test that replayed an event ninety minutes later failed, and
the failure was not the test's fault.

A Maharashtra night feeder runs 22:00 to 06:00. A farmer who irrigates on that
window and rings at 00:30 to confirm is reporting the same irrigation as one who
rings at 23:30, but the two calls fall on different calendar dates. The second
would have been accepted as a fresh event and credited the water balance a second
time, silently under-irrigating the field for the rest of the interval.

The key now uses an **operational date** that rolls over at 06:00 IST, after
every night window in the pilot districts closes. `deduplication_key` also accepts
an explicit day, which is exact where the handler already knows which schedule
the event refers to. Both are tested.

### What the farmer actually hears

Start time and stop time, never a raw duration. "Run the pump for 409 minutes" is
useless: he cannot convert it and he will be asleep. The stop time rounds to five
minutes and **always downward**, so a truncated run is never overrun and the pump
is never asked to draw power that has gone.

Quiet hours are 07:00 to 21:00 IST, tested exhaustively across all 24 possible
window-opening hours. A 06:00 window gets its call the previous evening and the
script says "tomorrow morning" rather than "today".

A call happens for IRRIGATE and SKIP and never for WAIT. Enforced by a raise, not
merely documented: a farmer called on days when nothing is asked of him stops
listening on the days when something is.

### The accessibility guarantee

`tests/test_scripts.py::TestNoTechnicalUnitsLeak` renders nine schedule states
across three languages and asserts that nothing a farmer hears contains a
technical unit, a percent sign or a decimal number, in English or in the target
language. It also walks every string in every master, so a case added later
cannot smuggle one in through a branch the rendering tests do not exercise.

**The accessibility claim in the report rests on that class**, which is why it is
more thorough than its length suggests.

It also caught something the eye missed. Three reason lines asserted a day, "so
water it today", while the capacity branch schedules into the *next* window, which
is usually tomorrow. The script would have told the farmer to water today and then
instructed him for tomorrow morning, two sentences apart. All three lines are now
day-agnostic in all three languages, and a test holds that.

### Two bugs the demo exposed

**It planned from midnight rather than from the planning instant.** A window that
had already opened was therefore offered as today's, and the call announced
"tomorrow morning" about a window that had closed hours earlier. Fixed by passing
the planning instant to both the window enumeration and the call timing.

**Windows console encoding.** The scripts are Hindi and Tamil; a Windows console
defaults to a codepage that cannot encode either and crashes on the first print.
`stdout` is now reconfigured to UTF-8 in the demo entry point.

### SoilGrids: the adapter is right, the data is absent

All three pilot points returned every property null with a 200 status. The
adapter's unit divisors were confirmed correct against the API's own
`unit_measure.mapped_units` field: cg/cm3 for bulk density, g/kg for texture,
dg/kg for organic carbon, exactly as coded.

The error message was misleading, naming whichever property came first in
iteration order rather than saying that the point has no data at all. Those are
different failures deserving different responses, and the message now
distinguishes them. `dataset/README.md` already warned that the ISRIC REST API is
intermittently unavailable, so the demo falls back to a medium loam and degrades
rather than failing in front of a reviewer.

`TODO [VERIFY]` whether the three pilot coordinates genuinely lack SoilGrids
coverage or whether the service was degraded on the day, before the pilot.

### Deviations and deferrals

- `azure-functions` and `fastapi` are now dev dependencies. Without them the
  Functions app and the FastAPI routes were the one part of the codebase nothing
  verified. A narrow mypy override exempts only the untyped SDK decorators; the
  function bodies are fully checked.
- The Cosmos-backed parts of `daily_plan`, `today` and the farmer lookup are
  stubs pending the M5 bindings. The planning logic they will call is complete
  and tested.
- Azure AI Speech voice names carry `TODO [VERIFY]`: they must be confirmed
  against the current voice list at build time, since Microsoft retires names and
  a retired one fails at synthesis rather than at deployment.
- All three non-English masters carry `TODO [VERIFY native speaker]` and must not
  reach the field until checked, for register as much as for grammar.
---

## 2026-09-05 — Script wording, soil inversion, crop correction, and M4

1,264 tests, `ruff`, `ruff format` and `mypy --strict` clean across 54 source
files.

### The Hindi in the M3 report was mangled in transit, not in the data

Settled at the byte level rather than by assertion. `बिजली` is
U+092C 093F 091C 0932 0940, complete, and the sentence carries all seven of its
spaces. The corruption happened somewhere in the copy-paste path between the
terminal and the message.

That could not have been established from console output, which is the point.
`make script-samples` now writes every rendered script to
`results/script_samples.txt` in UTF-8, and `tests/test_script_vocabulary.py`
checks the wording at the data level where a display cannot interfere:

- **every rendered token must appear in a vocabulary derived from the master
  itself**, so a concatenation of two words is not in it;
- **no token may be a strict prefix of a longer vocabulary word**, which is what
  distinguishes truncation from a merely unknown token;
- no two adjacent tokens may be identical;
- exhaustively across every hour and quarter, in all three languages.

The vocabulary is derived rather than listed, so it cannot drift out of date
when a line is reworded.

### No digit now reaches a farmer

Clock times as digits were the wrong output for this user on two counts: a
farmer who cannot read does not know whether `6:00` is morning or evening, and a
text-to-speech voice handed a numeral renders it unpredictably. This is the
single most important string the system produces and it carried the most
ambiguity.

`speak_time` and `speak_duration` now render every time and duration in words
with its part of day. Hindi uses its irregular half-hour forms, `डेढ़` for 1:30
and `ढाई` for 2:30, rather than `साढ़े एक`; getting that wrong would break
nothing and would mark the script immediately as machine-written to any Hindi
speaker. Whether a language uses quarter forms at all is declared in the master
rather than inferred from which words happen to be listed, which is what let
Tamil use its regular construction throughout.

The report's claim tightens from "no technical units" to **no digits at all**,
across ASCII, Devanagari and Tamil numerals. That is simpler, stronger, and
checkable in a second at a viva.

**The change introduced a bug of its own, caught by generating the sample file.**
The sentence frame still named the period while the spoken time also carried it,
so English read "tonight power is from ten o'clock at night" and Tamil produced
a visibly doubled word, "இன்று இரவு இரவு". The frame now names only the day.
A general test asserts no token is ever repeated adjacently, in any language, in
any schedule state.

### SoilGrids demoted from primary to prefill

It returned every property null for all three pilot points, and Phase-I had
already recorded that its REST API was paused. A zero-hardware claim cannot rest
on a source that returns nothing.

**The farmer's declared soil texture is now the primary input.** Onboarding asks
one question with three icon choices, `reti`, `domat`, `chikni`, each with a
spoken cue an extension worker can read aloud. SoilGrids prefills the answer
where it responds; where it does not, the answer stands and nothing fails.

This is a better design and not a workaround, for a reason unrelated to
availability: a farmer knows his own soil, and his answer describes **his plot**,
while a SoilGrids value describes a 250 m pixel that may straddle a road, a canal
and three holdings. On half a hectare the farmer is the better instrument.

`resolve_soil` returns the source alongside the profile. A `FALLBACK` source is
never used silently: the demo prints a warning and the operator screen surfaces
it, because a depth computed from a guessed soil can be wrong by a factor of two
and the operator is the only person able to go and ask.

`params/soil_texture_classes.yaml` carries `verified: false` and
`TODO [VERIFY]` on the USDA centroids, under the same discipline as the FAO-56
constants.

### The Vellore demo farmer was growing the wrong crop

Wheat is a rabi crop sown in November, and Vellore is not a wheat district. A
September wheat field in Tamil Nadu would have undermined everything correct
behind it in front of an agriculture-literate reviewer.

It is now **groundnut**, genuinely grown there, in the seeded crop set, and
mid-season in early September from a mid-June kharif sowing. Every sowing date
across the three farmers is now chosen so the crop is at a plausible **stage** on
the demonstration date rather than merely inside its growing period, and the
season and sowing window for each is named in a comment so the choice is visibly
deliberate.

### M4: both handoff packages are ready

Nothing under `handoff/` is committed here; `handoff/` is gitignored and only
`docs/HANDOFF_STATUS.md` and the Makefile change are on this branch.

**Frontend, for Nayan.** Vite, React 18, Tailwind, `vite-plugin-pwa`, and the
Static Web Apps workflow placed inside the package so the deployment workflow
arrives in his own pull request. Three-tile home screen, seven-day bucket,
operator onboarding including the new soil question and the bucket-test fields,
language switch, and a specification for the three missed-call card icons.

The power window is drawn as an arc on a 24-hour **ring** rather than a bar,
because a night window crosses midnight and on a bar becomes two disconnected
pieces at opposite ends. Rain is a **filling drop** rather than a percentage,
since no percentage may reach a farmer.

**AI/ML, for Krishna.** `train_soil_moisture.py` for Objective 3 alongside the
two calibration scripts. `simulate_policies.py` is written rather than
scaffolded and imports the engine rather than reimplementing the water balance,
so the four-policy comparison cannot drift away from the system it evaluates.
The other three are scaffolded with the feature list, the chronological split
rule and the reporting contract fixed, so the result is comparable and honest
whatever architecture he chooses.

Each `HANDOFF_README.md` gives the exact web-upload steps and a ready-to-paste
pull request description.

`make sim` prefers `src/ai_model/simulate_policies.py` once he commits it and
falls back to the handoff copy until then, so Objective 6 is runnable now rather
than blocked on his upload.

### Carried forward

- `results/script_samples.txt` awaits a native speaker. Until then both
  non-English masters stay `TODO [VERIFY native speaker]` and the report says so.
- The Tamil time construction is deliberately the regular
  "`{hour}` மணி `{minutes}` நிமிடம்" form rather than the colloquial
  contractions, because a contraction that is wrong is worse than one that is
  merely formal. A native speaker should decide whether to contract it.
- `params/soil_texture_classes.yaml` centroids and the class-typical bulk
  densities both need checking against printed sources.

---

## 2026-09-05 — Phase-II closing entry

1,270 tests. `ruff`, `ruff format` and `mypy --strict` clean across 55 source
files. Five CI jobs green. Bicep compiles to 25 resource declarations. Nothing
deployed, no Azure credit spent.

### What Phase-II delivered

| Milestone | Outcome |
|---|---|
| M0 | Standards, build config, engine API fixed as typed contracts before behaviour existed, five-job CI |
| M1 | FAO-56 engine, verified against Example 18 on every printed intermediate |
| M2 | Power-window scheduler with hypothesis property tests, DISCOM parser |
| M3 | Three script masters, spoken clock times, missed-call state machine, Functions app |
| M4 | Both teammate handoff packages, prepared and gitignored |
| M5 | Bicep for 25 resources on free tiers, Cosmos-backed persistence, five alert rules |
| M6 | Objective 6 simulation, architecture overlays, README, viva notes, report draft |

### The three headline numbers

1. **Objective 2 is not met**, at 0.279 mm/day against 0.2. The implementation is
   verified correct, and the residual is smaller than the 0.735 mm/day
   disagreement between two reanalysis products fed to that same implementation.
2. **Objective 6 is not met** on water: P3 applies 9.8 percent less than
   fixed-interval, against a 20 percent criterion. The direction is right and the
   magnitude is not. It reaches 84.8 percent fewer stress days on the same
   comparison, so the second half of the criterion is met with a wide margin.
   *(Superseded figures: an earlier run reported 13.8 percent more water and 68.0
   percent fewer stress days. See the entry of 5 September 2026 on the carry-over
   double count.)*
3. **The novelty claim holds on its own terms**: against a conventional advisory
   under an identical power constraint, 83.3 percent fewer stress days at 29.4
   percent higher water use. The scheduler buys reliability with water.
   *(Superseded: 62.2 percent and 44.2 percent, from the same uncorrected run.)*

### Every deviation from the brief, across all milestones

Recorded in one place so none has to be rediscovered at review.

| # | Deviation | Reason | Approved |
|---|---|---|---|
| 1 | `pyyaml` as a fourth engine dependency | The brief's own mandate that constants and scripts live in YAML requires a YAML parser | Yes |
| 2 | mypy `python_version` unpinned | numpy 2.5 stubs use 3.12 syntax; pinning fails on a dependency, not our code. 3.11 support proved by the CI matrix instead | Yes |
| 3 | `.gitattributes` added | Team on Windows, CI on Linux; without it the first cross-platform edit is a whole-file diff | Yes |
| 4 | `required_pump_minutes` split from `pump_minutes` | The 720-minute ceiling would have made the plan's own 45 mm case uncomputable, and the scheduler needs the true requirement to carry a remainder forward | Yes |
| 5 | `minutes_for_discharge` added | The scheduler holds a discharge as a number; faking a `BucketTest` would read as though one had been performed | Yes |
| 6 | `Field` renamed `IrrigatedField` | `Field` is pydantic's own, and shadowing it in a module using `Field(...)` throughout is a trap | Yes |
| 7 | `src/azure` on the import path rather than a package | mypy could not resolve it both ways | Yes |
| 8 | `tzdata` added, Windows only | `zoneinfo` cannot resolve `Asia/Kolkata` on Windows, and IST-aware windows are load-bearing | Yes |
| 9 | `azure-functions` and `fastapi` as dev dependencies | Without them the Functions app was the one part of the codebase nothing type-checked | Yes |
| 10 | Objective 6 policy set expanded from four to five | An unconstrained trigger is not a baseline anyone can execute; P1 is what a farmer using an existing advisory actually experiences | Yes |
| 11 | Empirical rain calibration written here | `precipitation_probability` is null for every historical date, so the confidence had to be measured rather than read. The trained model remains Krishna's deliverable | Within scope |

### Every defect found during Phase-II, and how

None of these was found by inspection. Recording the mechanism matters more than
recording the fix.

| Defect | Found by | Consequence had it shipped |
|---|---|---|
| Saxton-Rawls density adjustment was a no-op, ratio identically 1.0 | Hand-tracing three bulk densities | An adjustment that appears in code and review while doing nothing |
| Validation harness used `wind_speed_10m_max` where FAO-56 takes the mean | Running the Objective 2 validation | MAE 0.972 instead of 0.279; the engine would have looked wrong |
| Deduplication keyed on the calendar date | A test replaying an event 90 minutes later | A farmer ringing at 00:30 about a 22:00–06:00 window credits the balance twice, silently under-irrigating for the rest of the interval |
| Demo planned from midnight | Reading the demo output | A call announcing "tomorrow morning" about a window that closed hours earlier |
| Sentence frame repeated the part of day | Generating the script sample file | English "tonight … ten o'clock at night"; Tamil a visibly doubled word |
| Three reason lines said "water today" | A guard test written after spotting it | The script tells him to water today, then instructs him for tomorrow morning, two sentences apart |
| Honorific hardcoded as Marathi "kaka" | Review | Every farmer addressed as a Marathi speaker regardless of district |
| Cotton Kc_ini "corrected" from a correct 0.35 to a wrong 0.30 | Re-reading Table 12's group-header structure | A wrong agronomic constant introduced *by* a correction |
| Phantom carry-over in the simulation | Investigating why P2 used 64 percent more water than P1 | Double-counted deficit driving steady over-irrigation, inflating the headline |
| P0 applying a need-based depth | Reading the policy specification against the code | A flattered baseline making every other policy look worse |
| `hash()` used for the farmer id | mypy and review | A different farmer id after every process restart |

### Open `TODO [VERIFY]` items

Grouped by who can close them.

**Needs a printed source**

- Indian crop stage lengths for the seven crops without an FAO-56 Table 11 Indian
  row: rice, cotton, sugarcane, groundnut, tomato, onion, chickpea. ICAR or state
  package-of-practice.
- All nine Ky values, from FAO-33 and FAO-66. Ky is not in FAO-56.
- Groundnut Kc_ini, unresolved from the page.
- Saxton and Rawls equations 3 to 5, for the density adjustment.
- USDA texture-triangle class centroids and class-typical bulk densities in
  `params/soil_texture_classes.yaml`.
- Local area-unit conversions: bigha, guntha, cent vary by district.
- IEEE citation metadata for R1, R2, R6, R9, R10, R11, R13, R14, R15, R17.

**Needs a native speaker**

- Every line of the Hindi and Tamil masters, for register as much as grammar.
- The honorific in each: whether "kaka", "bhai" or "ji" suits the Hindi pilot
  districts, and "anna", "aiya" or "saar" the Tamil one.
- Whether the Tamil time construction should use colloquial contractions rather
  than the regular form used here.
- `results/script_samples.txt` exists for exactly this review.

**Needs a deployment or a pilot**

- Actual monthly Azure cost against the portal.
- Azure AI Speech neural voice names, confirmed at build time.
- Whether a rejected inbound call accrues any charge, on whichever provider a
  pilot uses.
- TRAI TCCCPR 2018 position on consented transactional automated calls.
- MSEDCL circular reuse terms.
- Observed share of inbound calls receiving an instant reject versus ringing out.
- Whether the three pilot coordinates genuinely lack SoilGrids coverage or the
  service was degraded that day.
- The Vellore monsoon ET₀ bias of +0.413, still unexplained.

### What is not done

- Objective 3, the soil-moisture model. Krishna Agrawal's module, off the
  critical path by design.
- The trained rain calibration model. The empirical table stands in.
- Both teammates' code is prepared but must be committed by them.
- No Azure resource is deployed; no runtime, cost or latency figure exists.
- No live phone call has ever been placed, and none can be on this subscription.

---

## 2026-09-05 (second entry) — the carry-over double count

Phase-II was reported as closed earlier today. It was not. The Objective 6 table
contained a result that could not be right, and the framing built on it — "the
scheduler buys reliability with water" — was resting on a defect.

1,280 tests, `ruff`, `ruff format` and `mypy --strict` clean across 56 source
files.

### What was wrong with the table

P2 applied **2,041 mm more water than Pref**, the physically unachievable policy
with power on demand, with **1,856 mm more deep percolation** and **35 more
stress days**. Ninety-one percent of the excess water drained straight past the
root zone.

Nothing should apply more water than the unconstrained policy unless it is
over-filling the root zone. A policy that applies more than the ideal, wastes
almost all of the excess, and still stresses the crop more often is not making a
trade. That signature was in the published table and nobody, including me, read
it.

### The defect

`plan_day` computed

    required = state.depletion_mm + state.carry_over_mm

while the water balance was stepped with `applied = schedule.delivered_mm`. After
a truncated run the undelivered depth is **already inside the depletion**, so
adding carry-over on top asked the pump for the same water twice.

Worked through: depletion 40 mm, window capacity 25 mm. Apply 25, carry-over 15.
The balance steps to 40 − 25 + 5 mm ETc = 20 mm, and that 20 already contains the
15 that was never delivered. The next morning the requirement became 20 + 15 = 35
against a true deficit of 20, and 15 mm percolated. Every truncated run, all
season.

**This was in the engine, not only in the simulation.** A real farmer would have
been told to over-irrigate the morning after every window that ran short. It
would have reached the field.

It is the same class as the phantom carry-over fixed on 5 September in the
earlier entry. That fix addressed the branch where *nothing was applied*; the
identical double count survived in the branch where something was. Fixing one
instance of a class and not looking for the others is the actual lesson here.

### Diagnostic, before the fix

P2 run twice over identical data, nothing else changed:

| P2 arm | Water (mm) | Percolation (mm) | Stress days | Pump hours |
|---|---:|---:|---:|---:|
| `required = depletion + carry_over` | 8,961 | 7,685 | 312 | 4,513 |
| `required = depletion` | 7,493 | 6,233 | 341 | 3,704 |
| *Pref, unlimited power (reference)* | *6,920* | *5,829* | *277* | *3,369* |

The double count was **1,467 mm of water and 1,452 mm of deep percolation**. Of
the water it added, 99 percent drained below the root zone, which is what the
hypothesis predicted and is why the excess was almost pure waste rather than
insurance.

### What was changed

**Engine.** `required = state.depletion_mm`. `FieldState.carry_over_mm` is
**removed**, not merely ignored: an input that must always be zero is the same
trap a second time. `Schedule.carry_over_mm` stays, because carry-over is a real
thing — it is what the call script tells the farmer about tomorrow — but it is an
output, not an accounting quantity the balance needs. Both docstrings now say so.

**Event credit.** `StateChange.credit_mm` is documented as
`Schedule.delivered_mm`, never `required_mm`, since that is the half of the loop
that makes the depletion correct. The Functions handler was passing a hardcoded
`0.0`, so a farmer's confirmation credited nothing at all; it now reads the
stored schedule for the **operational** day, so a night run confirmed at 00:30 is
credited against the right plan. Five tests in `tests/test_planned_depth.py`.

**Simulation.** Requirement is depletion alone. A second defect fixed in the same
loop: when the forecast was unavailable the policy branch did `day += 1;
continue`, skipping the balance step entirely, so that day's ETc and rain never
reached the depletion. It now falls through to the balance step with no
irrigation, and `run_policy` asserts that every simulated day steps the balance
exactly once under every policy.

**A standing check, so this cannot recur silently.** `_sanity_check` warns on
every run when a constrained policy applies materially more water than Pref with
more than 75 percent of the excess draining below the root zone. That is the
signature that was sitting in the published table.

**Regression test.** `tests/scheduler/test_truncated_run_accounting.py`, ten
tests, drives a real `WaterBalance` rather than a stub, because the scheduler in
isolation was self-consistent and the balance in isolation was correct against
FAO-56 equation 85. Only stepping one into the other exposes the double count.
Verified to fail against the old requirement, at three of five truncation
degrees.

### Rice is out of the headline

Three of the nine simulated fields are rice, including the largest.
`params/crops.yaml` already records that a depletion-triggered balance is the
wrong model for ponded paddy and that a paddy mode is a Phase-III item, so the
headline now uses the **six non-ponded fields** and the all-nine figure is
printed beside every claim.

The rice rows are the argument for their own exclusion: the unachievable Pref
applies the *most* water of any policy on rice, and fixed-interval practice the
least. No irrigation model should produce that ranking. Rice takes p = 0.20, so
RAW is small and the trigger fires almost continuously.

### Corrected results, six non-ponded fields, two seasons

| Policy | Water (mm) | Stress days | Pump hours | Energy (kWh) | Percolation (mm) |
|---|---:|---:|---:|---:|---:|
| P0 calendar | 6,362 | 631 | 2,424 | 12,202 | 7,605 |
| **P1 advisory, power constrained** | **4,435** | **576** | **2,141** | **10,895** | **4,212** |
| P2 power-window scheduler | 5,873 | 95 | 2,919 | 15,492 | 4,992 |
| **P3 scheduler + rain skip** | **5,740** | **96** | **2,854** | **15,136** | **4,859** |
| *Pref unlimited power* | *5,048* | *116* | *2,475* | *12,910* | *4,431* |

### Before and after, on the claims that were published

| Claim | Reported this morning | Corrected |
|---|---|---|
| Objective 6, P3 vs P0, water | 13.8 percent **more** | **9.8 percent less** |
| Objective 6, P3 vs P0, stress days | 68.0 percent fewer | 84.8 percent fewer |
| Novelty, P3 vs P1, water | 44.2 percent more | 29.4 percent more |
| Novelty, P3 vs P1, stress days | 62.2 percent fewer | 83.3 percent fewer |
| Price of rationed power, P3 vs Pref | 28 percent more water, 43 more stress days | 13.7 percent more water, 20 **fewer** stress days |

Objective 6 is **still not met**: 9.8 percent against a 20 percent criterion. The
direction is now right and the magnitude is not, which is a different and more
defensible position than a result that contradicted itself. The second half of
the criterion, no increase in stress days, is met with a wide margin.

The framing rule applied again on the corrected numbers puts the result in the
same branch as before — P3 better than P1 on stress days, worse on water — so the
headline wording stands, but it now stands on numbers that survive a physical
sanity check. The evidence for that: P3 sits *below* the unachievable Pref on
stress days, 96 against 116, at 13.7 percent more water, with 62 percent of the
excess draining rather than 99 percent.

**Pref needs restating.** It bounds what unlimited power buys, not what perfect
agronomy would. It waits for depletion to reach RAW before acting, while P3's
capacity-limit branch refills before the deficit outgrows one window, which is
why P3 reaches fewer stress days than it does. Calling it "ideal" was loose.

### The rain-skip threshold

A single threshold is a single point, so all four were run. `rain_skip.
min_confidence` is now a parameter in `scheduling.yaml`, and `RainForecast` takes
it, which is what made the sweep possible.

| Threshold | Water (mm) | Stress days | Skips issued | Percolation (mm) |
|---:|---:|---:|---:|---:|
| 0.5 | 5,745 | 98 | 316 | 4,864 |
| 0.6 | 5,745 | 98 | 261 | 4,864 |
| **0.7 (deployed)** | **5,740** | **96** | **242** | **4,859** |
| 0.8 | 5,827 | 96 | 113 | 4,946 |

Nearly tripling the skips issued changes water use by 87 mm out of 5,750, under 2
percent. The power-window scheduling accounts for 1,305 mm against the same
baseline. **The value is in the scheduling, not the skip**, and this is now
evidence rather than assertion.

Two features of that table are stated in `results/README.md` rather than left for
a reviewer to find. 0.5 and 0.6 give identical water despite 55 more skips,
because the rain check runs before the need check in `plan_day`, so a skip is
issued whenever rain covers a deficit including deficits too small to act on —
**the skip count overstates avoided irrigations**. And 0.8 uses *more* water than
0.7, which is the rule working: a higher bar refuses more skips.

No threshold was chosen to improve the headline. 0.7 stays, on the asymmetry
argument, and a pilot with a measured local cost of water should pick its own
point from the curve.

### Everything updated

`results/objective6_policy_comparison.csv` (now carrying `ponded` and
`rain_skips` columns), `results/objective6_skip_threshold_sensitivity.csv` (new),
all three figures including `objective6_skip_threshold.png` (new),
`results/README.md`, the README acceptance table, `docs/PHASE2_REPORT.md`,
`docs/REVIEW2_VIVA_NOTES.md` and the closing entry above. Superseded figures are
marked superseded in place rather than deleted.

The viva notes gained a section on what to say if the change in numbers is
raised. The answer is that a number surviving a physical sanity check is worth
more than one that was never checked, and that the check is now automatic.

### Carried forward

- The Vellore monsoon ET₀ bias of +0.413 is still unexplained.
- A ponded-paddy mode remains a Phase-III item, and until it exists no claim in
  this project covers rice.
- The pre-existing lint findings in `handoff/student3_ai_model/` are Krishna
  Agrawal's to clear when he commits the package; `handoff/` is gitignored and
  outside CI.

---

## 2026-09-05 (third entry) — deployment abandoned, and a recipe that never ran

Two findings, one of which explains the other.

### Azure for Students is not available to this project

The deployment was attempted properly, not skipped. Azure CLI 2.90.0 and Bicep
0.46.1 were installed on the build machine and `az login` was run. It
authenticated and then returned `No subscriptions found`.

**Azure for Students is disabled in VIT's managed tenant and self-signup is not
permitted.** There is no subscription to deploy into, and no way to obtain one
from inside the institution's tenant. The blocker is an institutional policy: not
technical, since the template compiles and targets a resource group rather than a
subscription, and not budgetary, since every resource is on a free or consumption
tier.

**Phase-II therefore ships the infrastructure as a compiled, validated
deliverable and stops there.** Verified today with Bicep CLI v0.46.1:

- `src/azure/infra/main.bicep` compiles to **25 resource declarations**
- **5 alert rules**, generated from a `copy` loop over the `alerts` variable:
  `ingest-failure`, `scheduler-failure`, `call-failure-rate`,
  `missedcall-webhook-errors`, `cosmos-throttling`
- `make deploy-plan` and `make deploy` are both ready and correct
- **Nothing is deployed. No Azure credit has been spent, at any point in
  Phase-II.**

What this costs the project is worth stating rather than glossing. Every claim
about *what the template declares* is verified by compilation. Every claim about
*runtime* — monthly cost, latency, whether an alert actually fires, and the
30-day ingestion availability figure Objective 1 asks for — is not, and stays
`TODO [VERIFY]` rather than being estimated. The cost TODO in
`docs/AZURE_SERVICES_PHASE2.md` is now marked as unclosable in Phase-II, so it
does not read as merely undone.

### The deploy recipes had never been runnable

Found while preparing to run `make deploy-plan`. Both recipes carried literal
backslash-n sequences where line continuations were intended:

    az deployment group what-if \n\t\t--resource-group ... \n\t\t--template-file ...

The shell sees an escaped `n`, which collapses to a bare `n`, so the command
would have been `az deployment group what-if n --resource-group ...`. Neither
`deploy-plan` nor `deploy` could ever have worked.

**Why it survived until now: `make` is not installed on this machine.** Every
target in this Makefile has been exercised by calling the underlying command
directly, so the recipes themselves were never parsed. A Makefile whose recipes
are never run is documentation that looks like automation, and the two failed
differently here — the documentation was right and the automation was broken.

Both recipes are now single lines, matching the other multi-argument recipes in
the file, and verified with `make -n` after installing GNU Make 4.4.1. The
`AZURE_RESOURCE_GROUP` guard now names an example value, because that error
message is the only place the variable is documented.

The same defect class was fixed once before, in the `sim` recipe on
3 September. Fixing one instance and not sweeping the file for the rest is the
same mistake as the carry-over double count earlier today, in a different file.
`Makefile` now contains exactly one literal backslash-n, inside an `awk` format
string where it belongs, and that was checked rather than assumed.

### Also in this pass

`results/script_samples.html` and `make script-html`. A terminal cannot be
trusted with Devanagari or Tamil, so the native-speaker review that both
non-English masters are blocked on now has a page that renders correctly on a
phone: one card per schedule case, the English gloss above its Hindi and Tamil so
the reviewer can see the intent before judging the wording, explicit font stacks
and extra leading for the combining marks, and no external requests so it opens
with no data connection. Verified in a browser rather than asserted.

### Carried forward

- Objective 1's availability criterion cannot be measured without a deployment
  and is not claimed.
- Both non-English masters remain `TODO [VERIFY native speaker]`.
- `make` should be treated as a required tool for this repository; the README's
  How to Run section assumes it and the build machine did not have it.
