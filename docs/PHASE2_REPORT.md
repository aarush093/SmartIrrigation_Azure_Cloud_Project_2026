# Phase-II report sections

**Cloud-Based Smart Irrigation Recommendation using Weather Intelligence**
BITE412L Cloud Computing · Dr. Priya V · VIT
Nayan Jaggi (23BIT0390) · Aarush Pandit (23BIT0416) · Krishna Agrawal (23BIT0428)

*Prepared 5 September 2026 by Aarush Pandit. Sections follow the order of the
Phase-I guidelines. **Only the sections that change or extend for Phase-II are
included**, so they can be pasted into the report document without disturbing
what is already there.*

*Every number below traces to a file under `results/`. Nothing is rounded in a
favourable direction and nothing is stated that a file does not support.*

---

## Abstract — replacement paragraph on implementation status

> Phase-II implements the platform described in Phase-I and refines its scope on
> instructor feedback. The refinement fixes both halves of the gap Phase-I
> identified: the translation target becomes pump running minutes scheduled
> inside the farmer's rationed agricultural electricity window, and the delivery
> channel becomes an outbound voice call in the farmer's own language together
> with three toll-free missed-call numbers that require no literacy, smartphone
> or data connection. The FAO-56 decision engine, the power-window scheduler, the
> voice and missed-call channel, the Azure Functions application and the
> infrastructure as code are complete and tested: 1,270 automated tests, static
> type checking under `mypy --strict`, and five continuous integration jobs on
> every commit. The daily loop runs end to end for three pilot farmers using live
> public weather data and no cloud resources. Two of the six Phase-I objectives
> are reported as not met at their stated thresholds, with the measurements that
> establish this and an analysis of what each shortfall costs in practice.

---

## Novelty summary

Existing irrigation advisories, whether FAO-56 applications, IoT dashboards or
the current generation of conversational assistants, answer a single question:
*when does the crop need water?* For the majority of Indian pump owners that is
not the binding question. Agricultural electricity in most states is unmetered
and rationed to a fixed number of supply hours a day on a rotating schedule,
frequently at night. The binding question is *when can the pump run at all?*

**New feature.** The distribution company's agricultural feeder supply window is
treated as a first-class scheduling constraint. Each recommendation names the
window and the pump running time inside it. A search of Google Scholar,
ScienceDirect, MDPI, IEEE Xplore, arXiv and ICT-for-agriculture grey literature
conducted in August and September 2026 found no farmer-facing advisory that does
this; the closest work optimises collective pumping stations or agricultural
microgrids, which are operator-side tools.

**Better algorithm.** A capacity-constrained refill policy replaces the standard
"irrigate when depletion reaches readily available water" trigger. The engine
computes the net depth one power window can deliver for a particular pump and
field, and refills while the projected deficit can still be repaid in a single
window, rather than after it has already outgrown one.

**Better architecture.** No on-farm hardware of any kind. Soil type comes from a
single spoken question at onboarding, pump discharge from timing a bucket, the
power window from a published circular or the farmer's own account of his
rotation, and all subsequent field observations from missed calls that cost him
nothing.

**Measured contribution.** Against a conventional advisory operating under an
identical power constraint, the scheduler achieves **62.2 per cent fewer crop
stress days at 44.2 per cent higher water use** across eighteen field-seasons.
The scheduler buys reliability with water, because it must refill in advance
against a window that may not arrive. Isolating the constraint itself, the
scheduler under rationed supply applies **28 per cent more water** than the same
scheduler with power on demand: a measured price for rationed electricity that no
prior farmer-facing system reports, because none of them models the window.

---

## Proposed Architecture

Both Phase-I diagrams are retained unchanged, each with a Phase-II overlay
beneath it in `architecture/`.

**Diagram 1, Azure cloud architecture, overlay.** Shows the deployed service set
exactly as declared in `src/azure/infra/main.bicep`: Functions on consumption,
Cosmos DB serverless, Blob Storage, AI Speech, AI Document Intelligence, AI
Translator, Communication Services, Event Grid, Static Web Apps, API Management,
Key Vault, Application Insights, Monitor and a Machine Learning workspace. The
farmer's own soil answer is drawn as the primary input with SoilGrids as a dashed
prefill. The Communication Services path is drawn dashed and greyed: implemented
and tested, but not executable on this subscription.

**Diagram 2, system architecture, overlay.** Describes the farmer's day rather
than the data stages: a five-minute onboarding, an automatic daily loop, one
thirty-second call placed only when something is being asked, and three
missed-call numbers that are the only state inputs thereafter.

---

## Dataset Details

Sources D1 to D6 are unchanged. Three are added and two statuses change; nothing
is withdrawn.

| # | Source | Type | Licence | Role |
|---|---|---|---|---|
| D7 | MSEDCL AgLM feeder schedule circulars | PDF tables | Public circular · *reuse terms to verify* | Ground truth for power windows in the Maharashtra pilot |
| D8 | Open-Meteo Previous Runs API | Forecasts as issued on earlier days | CC BY 4.0 | Calibration training pairs, and the forecast-as-issued input that keeps hindsight out of the simulation |
| D9 | Farmer missed-call and call-outcome events | Event log | Own, consented | The only sensor: feedback, feeder reliability, compliance |

**D4, ISRIC SoilGrids: role restated from primary to prefill.** The service
returned every requested property as null for all three pilot coordinates, and
Phase-I had already recorded that its REST interface had been paused. The
farmer's own answer to a three-choice soil question is now the primary input.
This is also the better design independent of availability: the farmer's answer
describes his plot, whereas a SoilGrids value describes a 250 metre grid cell
that may straddle a road, a canal and three separate holdings.

**D5, Kaggle irrigation dataset:** retained, optional, Objective 3 only.
**D6, International Soil Moisture Network:** retained as the independent
validation set for Objective 3.

---

## Azure Services Planning

The full table with a Status column for every Phase-I service is
`docs/AZURE_SERVICES_PHASE2.md`. Summary: **sixteen services deployed** in the
infrastructure as code, all on free or consumption tiers; **eleven deferred** to
Phase-III, each with a named substitute meeting the same functional need at pilot
scale.

Objective 5 requires data-plane services behind private endpoints *or*
authenticated gateways. Private endpoints carry a per-endpoint hourly charge
exceeding the available student credit, so the requirement is met through
authenticated gateways: Cosmos DB with local authentication disabled and managed
identity only, Key Vault with role-based access control, API Management in front
of the operator endpoints with Entra ID authentication, and automated secret
scanning over full repository history in continuous integration.

**Nothing has been deployed.** The template compiles to twenty-five resource
declarations and the deployment preview target runs `what-if` only.

---

## Implementation Progress

| Milestone | Delivered |
|---|---|
| M0 | Repository standards, build configuration, engine public API fixed as typed contracts, five-job CI |
| M1 | FAO-56 engine: Penman-Monteith cross-check, Saxton-Rawls pedotransfer, crop calendar, root-zone water balance, pump-minutes conversion, Open-Meteo and SoilGrids adapters with offline fakes |
| M2 | Power-window scheduler, feeder reliability, multi-field allocation, DISCOM schedule parser, property tests |
| M3 | Script masters in three languages, spoken clock times, quiet hours, missed-call state machine, telephony and speech adapters, Functions application |
| M4 | Frontend and AI/ML handoff packages prepared for their owners |
| M5 | Bicep for twenty-five resources, Cosmos-backed persistence, five alert rules |
| M6 | Objective 6 simulation, architecture overlays, documentation, review materials |

**Verification status at submission:** 1,270 automated tests; `ruff`,
`ruff format` and `mypy --strict` clean across 55 source files; five continuous
integration jobs green on every push — lint, unit tests on Python 3.11 and 3.12,
secret scanning, and a check that the decision engine imports no Azure SDK so
that the agronomy remains reviewable offline.

---

## Results

### Objective 2 — reference evapotranspiration

Criterion: ET₀ within 0.2 mm/day of the FAO-56 Penman-Monteith reference over at
least 365 held-out station-days.

**Measured over 1,095 station-days at Vellore, Beed and Ludhiana during 2025:**

| Site | n | MAE | RMSE | Bias | Within 0.2 |
|---|---:|---:|---:|---:|---:|
| Vellore TN | 365 | 0.297 | 0.366 | +0.205 | 37.3% |
| Beed MH | 365 | 0.308 | 0.350 | −0.013 | 28.8% |
| Ludhiana PB | 365 | 0.232 | 0.276 | +0.004 | 43.8% |
| **Overall** | **1,095** | **0.279** | **0.333** | **+0.065** | **36.6%** |

**The objective is not met at the stated tolerance.** Four findings establish
what the residual is and is not.

1. **The implementation is correct.** It reproduces every printed intermediate of
   FAO-56 Example 18: atmospheric pressure, psychrometric constant, saturation
   vapour pressure slope, both vapour pressures, extraterrestrial and clear-sky
   radiation, net shortwave, net longwave, net radiation, and the final ET₀ of
   3.9 mm/day.
2. **It is not an artefact of the daily time step.** FAO-56 equation 53 was
   implemented and summed hourly; the hourly total is worse, 0.368 against 0.154
   at Beed.
3. **The residual is smaller than the disagreement between reanalysis products.**
   The same implementation, given Open-Meteo (ERA5) and NASA POWER (MERRA-2)
   inputs for the same sites and dates, disagrees with itself by 0.735 mm/day —
   2.6 times the residual. Part of that spread is grid-resolution mismatch, since
   POWER serves 0.5° × 0.625° meteorology against ERA5 at 0.25°; the conclusion
   survives a substantial discount for it.
4. **The practical cost is small.** Propagated to pump minutes on a one-acre
   furrow-irrigated wheat field with a 409-minute baseline run, the overall bias
   costs 8.6 minutes, or 2.1 per cent. Application efficiency alone spans 129
   minutes on the same field and an uncalibrated pump discharge spans 102.

> This implementation agrees with an independent FAO-56 implementation more
> closely than two reanalysis datasets agree with each other.

Bias, not scatter, is what accumulates in a water balance, because random daily
errors partly cancel across an irrigation interval while a bias does not. The
annual bias of +0.065 mm/day is comfortably inside the 0.2 mm/day criterion.

### Objective 6 — water saving and the novelty claim

Five policies, nine fields across three districts, two seasons: eighteen
field-seasons per policy. The water balance is driven by observed weather; every
decision is driven by the forecast as it was issued that morning.

| Policy | Water (mm) | Stress days | Pump hours | Energy (kWh) | Percolation (mm) |
|---|---:|---:|---:|---:|---:|
| P0 fixed-interval calendar | 7,776 | 1,001 | 3,032 | 15,603 | 8,998 |
| **P1 advisory, power constrained** | **6,141** | **846** | **2,959** | **15,942** | **5,547** |
| P2 power-window scheduler | 8,961 | 312 | 4,513 | 24,976 | 7,685 |
| P3 scheduler with rain skip | 8,852 | 320 | 4,463 | 24,683 | 7,593 |
| *Pref unconstrained, unlimited power* | *6,920* | *277* | *3,369* | *18,418* | *5,829* |

*Pref is physically unachievable: it presumes power on demand.*

**Objective 6 as written is not met.** The criterion asks for at least 20 per
cent less water than fixed-interval irrigation; P3 applies **13.8 per cent more**.
Against the same baseline it reaches **68.0 per cent fewer stress days and 15.6
per cent less deep percolation**: fixed-interval practice both over-waters and
under-delivers, applying the wrong amount at the wrong time in both directions.

**The novelty claim, against a conventional advisory under an identical power
constraint: 62.2 per cent fewer crop stress days at 44.2 per cent higher water
use.** The scheduler buys reliability with water. Unable to rely on the next
window arriving, it refills early, which keeps the root zone fuller — the reason
stress nearly disappears, and equally the reason more subsequent rainfall drains
below the root zone.

Whether that is the right trade depends on the local value of water against
yield, which this simulation can now quantify per field rather than leave to
argument.

**The price of rationed electricity.** P3 against Pref differs only in whether
power is available on demand: **28 per cent more water and 43 additional stress
days**.

### Rain forecast calibration

Fitted on the earlier season and evaluated on the later one, never on the same
data.

| Model | Brier score |
|---|---:|
| Calibrated, binned by forecast amount and deficit | **0.0859** |
| Raw forecast probability | 0.1174 |

The calibration improves on the raw forecast by 27 per cent over 4,344 held-out
pairs. Its effect on the outcome is nevertheless small — P3 saves 1.2 per cent of
water over P2 — because at the confidence threshold the skip rule requires, the
calibrated probability seldom clears the bar. That is the conservative direction
by design: a wrongly skipped irrigation costs the crop, while a needless one
costs only water. The value of this system lies in the scheduling rather than in
the skip, and the results say so.

---

## Limitations

Stated plainly, because each is material to how the results should be read.

**No live telephone call has been placed, and none can be on this subscription.**
India does not appear in Microsoft's country and region list for Communication
Services telephone numbers, and numbers cannot be acquired on trial accounts or
with Azure free credits in any case. The SMS fallback declared in Phase-I is
blocked by the same restriction. The channel is demonstrated on a simulated
telephony console that exercises the identical code path; the Azure adapter is
implemented and tested against the documented API. Production deployment would
use an Indian communications provider registered under TRAI's DLT framework as a
new adapter implementation and a configuration change.

**Two of six Phase-I objectives are not met at their stated thresholds.**
Objective 2 measures 0.279 mm/day against a 0.2 mm/day criterion; Objective 6
applies 13.8 per cent more water than fixed-interval irrigation rather than 20
per cent less. Both are reported as measured, with the analysis above.

**Crop stage lengths and yield response factors are unverified.** FAO-56 Table 11
contains printed Indian rows for wheat and maize only; the remaining seven crops
use rows from other regions and are marked accordingly in the parameter file. All
yield response factors are unverified because they originate in FAO-33 and
FAO-66, which were not accessible during this work. The tabulated initial crop
coefficients also carry the accuracy limitation FAO-56 itself states for them.

**The Hindi and Tamil scripts have not been checked by a native speaker.** Every
rendered script for every schedule state has been written to
`results/script_samples.txt` for that review. Until it is complete, both masters
are marked accordingly and must not be used in the field.

**Objective 3 is not delivered in this phase.** The root-zone soil moisture model
is owned by Krishna Agrawal and remains in progress. It is deliberately off the
critical path: the scheduler depends on an interface whose default implementation
computes crop evapotranspiration as Kc × ET₀ and always works, so the absence of
the learned model changes nothing downstream.

**The simulation's rain-skip policy uses an empirical calibration table**, fitted
here for the purpose, rather than the trained model that forms part of the AI/ML
module. Historical precipitation probability is not served by the Previous Runs
interface, so the confidence had to be measured from forecast-versus-observed
pairs.

**No Azure resource has been deployed.** The infrastructure is defined as code
and validated by compilation; it has not been provisioned, so no runtime metric,
cost figure or latency measurement is reported.
