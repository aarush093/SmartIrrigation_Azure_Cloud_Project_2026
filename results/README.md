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
