# Results

Experimental results for *Cloud-Based Smart Irrigation Recommendation using Weather
Intelligence* (BITE412L, Dr. Priya V).

---

## ⚠️ Phase-I Status

> **This folder is intentionally empty.**
> No experiments have been run, no models trained and no data processed. Results
> are produced in Phase-III, after implementation. Populating this folder now with
> placeholder numbers would misrepresent the project's state.

---

## What will be recorded here (Phase-III)

Results are organised around the six project objectives, because each objective
carries a measurable acceptance criterion and each therefore needs evidence.

| Objective | Evidence to be produced | Planned artefact |
|---|---|---|
| **1 — Data ingestion** | Ingestion success rate over a rolling 30-day window; data freshness per field | `ingestion_reliability.md`, Azure Monitor export |
| **2 — FAO-56 computation** | Agreement between the implemented ET₀ and the FAO-56 Penman–Monteith reference across ≥ 365 station-days | `fao56_validation.md`, scatter and residual plots |
| **3 — Soil-moisture model** | R², RMSE and bias on a held-out season; comparison across architectures; accuracy-per-compute-cost | `model_comparison.md`, `learning_curves.png` |
| **4 — Delivery latency** | End-to-end latency distribution from generation to notification dispatch | `latency_analysis.md`, Application Insights export |
| **5 — Security and observability** | Secret-scan report, private endpoint verification, alert rule configuration | `security_audit.md` |
| **6 — Water saving** | Applied water and modelled crop water stress days, recommendation engine versus fixed-interval baseline, over ≥ 1 historical season | `water_saving_simulation.md`, comparison charts |

---

## Planned structure

```
results/
├── README.md
├── objective1_ingestion/
├── objective2_fao56/
├── objective3_model/
│   ├── model_comparison.md
│   ├── confusion_matrix.png
│   └── learning_curves.png
├── objective4_latency/
├── objective5_security/
├── objective6_water_saving/
│   ├── water_saving_simulation.md
│   └── baseline_vs_recommended.png
└── figures/
```

---

## Reporting standards

These rules exist so the results are defensible at review rather than merely
favourable.

1. **Report the metric that matters, not only the flattering one.** For this
   project the decisive metrics are irrigate/wait classification accuracy and
   depth error within agronomic tolerance. R² on a soil-moisture value is
   secondary — no farmer reads it.
2. **Always report the baseline alongside the result.** A water saving figure with
   no stated baseline is meaningless.
3. **Chronological splits only.** Any result produced from a random train/test
   split on time-series data is invalid and will not be reported.
4. **Report compute cost alongside accuracy.** Following the practice of paper 11
   in the literature survey.
5. **Negative results are recorded, not discarded.** If a model underperforms its
   baseline, that is a finding and it belongs here.
6. **Every figure carries its generating script.** No chart appears without the
   code that produced it.

---

## Relationship to the presentation

Figures in [`../presentation/`](../presentation/) are drawn from this folder rather
than regenerated separately, so the numbers in the slides and the numbers in the
report cannot diverge.

---

*Phase-I: planning and documentation. Results begin in Phase-III.*

---

# Phase-II results

Added by Aarush Pandit (23BIT0416). The Phase-I content above is unchanged.

Each file is produced by a harness under `tests/validation/`, marked
`integration` and excluded from CI, run on demand through the Makefile.

| File | Produced by | Question it answers |
|---|---|---|
| `objective2_et0_crosscheck.csv` | `make validate` | Does our FAO-56 ET0 agree with an independent implementation to within 0.2 mm/day over at least 365 station-days? |
| `objective2_hourly_hypothesis.csv` | `make validate-hourly` | Is the residual explained by Open-Meteo integrating hourly while we compute from daily aggregates? |
| `objective2_input_datasets.csv` | `make validate-inputs` | Is the residual a difference of method, or a difference of input dataset? |
| `objective2_sensitivity.csv` | `make sensitivity` | What does the measured ET0 error cost the farmer, in pump minutes? |

## Objective 2, stated in full

**Criterion.** Computed ET0 within 0.2 mm/day of the FAO-56 Penman-Monteith
reference on at least 365 held-out station-days.

**Measured.** Over 1,095 station-days at Vellore, Beed and Ludhiana during 2025,
mean absolute error against Open-Meteo's published `et0_fao_evapotranspiration`
is **0.279 mm/day**, with an annual bias of **+0.065 mm/day**. The station-day
count is met three times over; the tolerance is not. The tolerance was not
widened.

Four findings put that number in context.

**1. The implementation is verified correct.** It reproduces every printed
intermediate of FAO-56 Example 18, "Determination of ETo with daily data" (Uccle,
50 deg 48 min N, 6 July): P, gamma, Delta, e0(Tmax), e0(Tmin), es, ea, Ra, Rso,
Rns, Rnl, Rn, and the final ETo of 3.9 mm/day. Correctness of the implementation
and agreement with another provider are different questions, and only the first
is under this project's control.

**2. The residual is not an hourly-versus-daily artefact.** FAO-56 equation 53
was implemented and summed over 24 hours for a month at Beed. The hourly sum is
*worse* than the daily aggregate, MAE 0.368 against 0.154. The hypothesis is
dead.

**3. The residual is smaller than the disagreement between reanalysis products.**
Our own identical implementation, run on Open-Meteo (ERA5) inputs and on NASA
POWER (MERRA-2) inputs over the same year and sites, disagrees **with itself** by
**0.735 mm/day** MAE, which is 2.6 times the 0.279 residual.

> This implementation agrees with an independent FAO-56 implementation more
> closely than two reanalysis datasets agree with each other.

*Caveat, stated so it cannot be sprung at review.* The two products are on
different spatial grids. NASA POWER serves meteorology at 0.5 deg by 0.625 deg
and solar at 1 deg by 1 deg; the Open-Meteo archive serves ERA5 at 0.25 deg and
ERA5-Land at 0.1 deg. Part of the 0.735 mm/day is therefore grid-cell mismatch
rather than pure dataset disagreement, since the two "sites" are not exactly the
same patch of ground. **The conclusion holds regardless**: even a substantial
discount for grid mismatch leaves the spread above our 0.279 mm/day residual, so
the residual remains smaller than the intrinsic uncertainty of the input data.

**4. At this residual, ET0 is not the limiting factor in what the farmer is
told.** Propagated to pump minutes on the worked example field (wheat mid-season,
one acre, furrow, 380.2 L/min, seven-day interval, 409-minute baseline run):

| Error term | ETc over 7 days | Extra pump time | Share of the run |
|---|---:|---:|---:|
| Overall bias +0.065 mm/day | 0.52 mm | 8.6 min | 2.1% |
| Vellore bias +0.205 mm/day | 1.65 mm | 27.0 min | 6.6% |
| MAE 0.279, fully correlated | 2.25 mm | 36.8 min | 9.0% |
| MAE 0.279, independent across days | 0.85 mm | 13.9 min | 3.4% |
| *Application efficiency, Ea 0.55 vs 0.75* | | *129.0 min* | *31.5%* |
| *Pump discharge 20 percent low, no bucket test* | | *102.3 min* | *25.0%* |

Application efficiency alone spans 3.5 times the largest ET0 error term. This is
why the bucket test at onboarding matters more to the farmer than closing the
last fraction of a millimetre of ET0 agreement.

Bias, not scatter, is what accumulates in a water balance: random daily errors
partly cancel across an irrigation interval, a bias does not. The annual bias of
+0.065 mm/day is comfortably inside the 0.2 mm/day criterion.

**The error is seasonal.** The bias reverses sign between the dry season and the
monsoon at all three sites, which is why the annual figure is small. Vellore's
+0.205 annual bias is almost entirely a monsoon effect, +0.413 from June to
October against +0.054 from November to May. The signature is humidity and cloud,
where daily aggregation of RHmax, RHmin and the Rs/Rso cloudiness ratio departs
most from an hourly treatment.

Objective 2 is reported as a measured uncertainty budget rather than as a passed
or failed threshold.

---

## Objective 6, and the novelty claim

Produced by `make sim`. Nine fields across three districts, three crops each,
over two seasons (2024 and 2025): 18 field-seasons per policy.

| File | Contents |
|---|---|
| `objective6_policy_comparison.csv` | Per policy, per field, per season, with a `ponded` column |
| `objective6_skip_threshold_sensitivity.csv` | P3 at four rain-skip confidence thresholds |
| `objective6_water_vs_stress.png` | The trade-off, in one picture |
| `objective6_by_policy.png` | Each metric relative to the P1 baseline |
| `objective6_skip_threshold.png` | How little the skip threshold changes the outcome |

### Method, and the three things that would have invalidated it

**The baseline was corrected before the run.** An unconstrained FAO-56 trigger
assumes the pump can run whenever the crop wants water, which is impossible on a
rationed feeder. Beating it is not this project's claim and losing to it would
mean nothing. The baseline is **P1**: a correct agronomic instruction that the
farmer can only execute when the power happens to arrive, which is what a farmer
using any existing advisory app actually experiences.

**No hindsight.** The water balance is driven by observed archive weather, but
every decision is driven by the forecast **as it was issued that morning**, from
the Open-Meteo Previous Runs API, which reaches back beyond both simulated
seasons. Had the skip rule read the archive it would have been skipping on rain
it already knew had fallen, and the whole result would be worthless.

**Rice is reported but excluded from the headline.** `params/crops.yaml` records
for rice that "a ponded-paddy mode is a Phase-III item": a depletion-triggered
balance is the wrong model for a crop that is deliberately kept ponded. Three of
the nine fields are rice, including the largest in the set, so including them
would let a model the project itself disowns for that crop dominate every
number. The headline set is therefore the **six non-ponded fields**, and the
all-nine figure is printed beside every claim. The rice rows are below, and they
are visibly incoherent — P0 uses the least water and the unachievable Pref the
most — which is the evidence that the exclusion is right rather than convenient.

### Defects found and fixed

Four, across two runs. Each inflated the scheduler's apparent water use, so the
uncorrected result would have been a worse one reported honestly rather than a
better one reported dishonestly. That does not make it acceptable.

1. **Phantom carry-over.** When the scheduler planned into a window on a later
   day, the simulation recorded the shortfall of that unperformed run as
   carry-over, and the next day added it to a depletion that already contained
   the same shortfall.
2. **A flattered baseline.** P0 was applying a need-based depth, which is not
   what "fixed interval, fixed depth" means. Traditional practice is "when the
   power comes on my day, run the pump until it goes off", so P0 now applies
   whatever one full window delivers, regardless of need.
3. **Carry-over double-counted against depletion.** The same class as (1), in the
   branch (1) did not reach. `plan_day` computed the requirement as
   `depletion + carry_over`, while the balance was stepped with the depth
   actually *delivered*, so the undelivered part of a truncated run sat in the
   depletion **and** was added on top of it the next morning. This was in the
   **engine**, not only the simulation: a real farmer would have been told to
   over-irrigate the morning after every truncated run.

   Measured directly, by running P2 twice over identical data with nothing else
   changed:

   | P2 arm | Water (mm) | Deep percolation (mm) | Stress days |
   |---|---:|---:|---:|
   | `required = depletion + carry_over` | 8,961 | 7,685 | 312 |
   | `required = depletion` | 7,493 | 6,233 | 341 |
   | *Pref, unlimited power (reference)* | *6,920* | *5,829* | *277* |

   The double count was **1,467 mm of water and 1,452 mm of deep percolation**:
   99 percent of the water it added drained straight past the root zone, because
   the root zone could not hold it. The signature — a constrained policy applying
   far more than the unconstrained one, with nearly all the excess percolating —
   is now checked on every run and printed as a warning, so this cannot recur
   silently. `tests/scheduler/test_truncated_run_accounting.py` pins the
   invariant in the engine.

4. **A skipped balance step.** When the forecast was unavailable the policy loop
   advanced the day without stepping the water balance at all, so that day's ETc
   and rain never reached the depletion and the next morning planned from a stale
   root zone. The loop now falls through to the balance step with no irrigation,
   and asserts that every simulated day steps the balance exactly once under
   every policy.

### Results

Totals over 12 field-seasons: **six non-ponded fields, two seasons.**

| Policy | Water (mm) | Stress days | Pump hours | Energy (kWh) | Deep percolation (mm) |
|---|---:|---:|---:|---:|---:|
| P0 calendar | 6,362 | 631 | 2,424 | 12,202 | 7,605 |
| **P1 advisory, power constrained** | **4,435** | **576** | **2,141** | **10,895** | **4,212** |
| P2 power-window scheduler | 5,873 | 95 | 2,919 | 15,492 | 4,992 |
| **P3 scheduler + rain skip** | **5,740** | **96** | **2,854** | **15,136** | **4,859** |
| *Pref unlimited power* | *5,048* | *116* | *2,475* | *12,910* | *4,431* |

*Pref is **physically unachievable**: it assumes power on demand. It is a bound
on power availability, **not** an agronomic optimum — it waits until depletion
reaches RAW before acting, which is why P3, whose capacity-limit branch refills
earlier, reaches fewer stress days than it does.*

All nine fields including rice, for completeness:

| Policy | Water (mm) | Stress days | Pump hours | Energy (kWh) | Deep percolation (mm) |
|---|---:|---:|---:|---:|---:|
| P0 calendar | 7,776 | 1,001 | 3,032 | 15,603 | 8,998 |
| P1 advisory, power constrained | 6,141 | 846 | 2,959 | 15,942 | 5,547 |
| P2 power-window scheduler | 7,493 | 341 | 3,704 | 20,380 | 6,233 |
| P3 scheduler + rain skip | 7,261 | 361 | 3,582 | 19,617 | 6,016 |
| *Pref unlimited power* | *6,920* | *277* | *3,369* | *18,418* | *5,829* |

Rice alone, three fields, **not used for any claim**:

| Policy | Water (mm) | Stress days | Deep percolation (mm) |
|---|---:|---:|---:|
| P0 calendar | 1,414 | 370 | 1,393 |
| P1 advisory, power constrained | 1,706 | 270 | 1,336 |
| P2 power-window scheduler | 1,621 | 246 | 1,241 |
| P3 scheduler + rain skip | 1,522 | 265 | 1,156 |
| *Pref unlimited power* | *1,872* | *161* | *1,398* |

Read that table as a warning rather than a result. The unachievable ideal applies
the *most* water and fixed-interval practice the least, which is not a ranking any
irrigation model should produce. Rice takes p = 0.20, so RAW is small and the
trigger fires almost continuously; the depletion model is simply the wrong
instrument for a ponded field, exactly as `crops.yaml` says.

### Objective 6 as written: NOT MET

The criterion is at least 20 percent less water than fixed-interval irrigation,
with no increase in stress days.

**P3 applies 9.8 percent less water than P0.** The direction is right and the
magnitude is not: 9.8 against 20. The objective is not met and the number is
reported as measured. On all nine fields including rice it is 6.6 percent less.

On the other metrics against the same baseline, P3 reaches **84.8 percent fewer
stress days** and **36.1 percent less deep percolation** (63.9 percent fewer
stress days across all nine). The second half of the criterion — no increase in
stress days — is met with a large margin.

Fixed-interval practice both over-waters and under-delivers: P0 has the highest
percolation of any policy *and* the most stress days, because a fixed depth on a
fixed interval is the wrong amount at the wrong time in both directions.

### The novelty claim: P3 versus P1

This is the comparison the contribution rests on, and both policies operate under
exactly the same power constraint.

| Metric | P3 | P1 | Change |
|---|---:|---:|---:|
| Water applied | 5,740 mm | 4,435 mm | **+29.4%** |
| Stress days | 96 | 576 | **−83.3%** |
| Deep percolation | 4,859 mm | 4,212 mm | +15.4% |
| Pump hours | 2,854 | 2,141 | +33.3% |

All nine fields including rice: +18.3 percent water, −57.3 percent stress days.

**Headline: 83 percent fewer crop stress days than a conventional advisory under
the same power constraint, at 29 percent higher water use.**

The scheduler buys reliability with water, and the mechanism is visible in the
policy itself. Because it cannot rely on the next window arriving, it refills
early, and the capacity-limit branch fires while the deficit can still be repaid
in one window. That keeps the root zone fuller, which is why stress nearly
disappears, and also why more of the rain that follows drains below it.

This is a real trade, not a defect. The evidence that it is a trade rather than
over-application is that P3 now sits **below** the unachievable Pref on stress
days (96 against 116) while applying only 13.7 percent more water, and that 62
percent of that excess — not 99 percent — reaches the root zone rather than
draining past it. Before the carry-over fix neither of those was true, and the
same words would have been a cover story for a defect.

The 38 percent that still drains has a mechanism worth naming: refilling early
leaves the root zone fuller, so monsoon rain arriving afterwards finds less
storage to occupy and passes below it. **The water cost of window scheduling is
paid mostly as wet-season deep percolation**, not as extra transpiration, which
is what the 62 to 68 percent share tracked by the sanity check is measuring. In a
district where the aquifer is recharged by that percolation the cost is smaller
than the water figure suggests; where it is not, it is exactly as large.

Whether it is the right trade depends on what water costs relative to yield in a
given district, which is a question the simulation can now quantify per field
rather than one that has to be argued.

### The price of rationed electricity

P3 against Pref isolates the cost of the constraint itself, since the two differ
only in whether power is available on demand:

**13.7 percent more water than the same scheduler with power on demand.** That is
the measured price a smallholder pays for a rationed feeder, and it is a number
this project can produce because it models the constraint explicitly. No advisory
in the related-work map (plan Section 3) reports it, because none of them models
the window at all.

P3 reaches *fewer* stress days than Pref (96 against 116) rather than more, which
is not a paradox: Pref waits for depletion to reach RAW before irrigating, while
P3's capacity-limit branch refills before the deficit outgrows one window. Pref
bounds what unlimited power buys, not what perfect agronomy would.

### Rain calibration

Fitted on the earlier season and scored on the later one; never on the same data,
which would report memorisation rather than skill.

| Model | Brier score |
|---|---:|
| Calibrated (empirical, binned by forecast amount and deficit) | **0.0859** |
| Raw forecast probability | 0.1174 |

The calibration is **better than the raw forecast**, by 27 percent on Brier
score, over 4,344 held-out pairs.

#### How much the threshold matters: almost nothing

A single threshold is a single point, so all four were run. Six non-ponded
fields, two seasons, everything else unchanged:

| Confidence threshold | Water (mm) | Stress days | Skips issued | Deep percolation (mm) |
|---:|---:|---:|---:|---:|
| 0.5 | 5,745 | 98 | 316 | 4,864 |
| 0.6 | 5,745 | 98 | 261 | 4,864 |
| **0.7 (deployed)** | **5,740** | **96** | **242** | **4,859** |
| 0.8 | 5,827 | 96 | 113 | 4,946 |

Nearly tripling the number of skips issued, from 113 to 316, changes water use by
**87 mm out of 5,750, under 2 percent**, and stress days by two. Compare that
with the 1,305 mm the power-window scheduling itself accounts for against P1.
**The skip rule is not where this system's value lies. The power-window
scheduling is**, and the sensitivity table is the evidence rather than the
assertion.

Two things in that table are worth stating plainly rather than leaving for a
reviewer to notice:

- **0.5 and 0.6 give identical water, stress and percolation** despite 55 more
  skips. Those extra skips fall on days the scheduler would not have irrigated
  anyway. The rain check runs before the need check in `plan_day`, so a skip is
  issued whenever rain covers a deficit, including deficits too small to act on.
  **The skip count therefore overstates avoided irrigations**, and only the water
  column measures what the rule actually saved.
- **0.8 uses more water than 0.7**, which is the rule working as intended: a
  higher bar refuses more skips, so more irrigations go ahead.

The deployed value stays at 0.7, in `params/scheduling.yaml` under
`rain_skip.min_confidence`. It is not chosen because it wins — nothing in this
table wins — but because the asymmetry is real: a wrongly skipped irrigation
costs the crop a whole interval, since the next window may be days away, while a
needless one costs only water. A pilot with a measured cost of water in a
particular district should pick its own point from this curve.

`precipitation_probability` is null for every historical date in the Previous
Runs API, which is why the confidence had to be measured from
forecast-versus-observed pairs rather than read from a stored value. That is
precisely the gap the calibration model exists to fill. The trained model is
Krishna Agrawal's deliverable and should beat this empirical table; the
comparison is its acceptance criterion.
