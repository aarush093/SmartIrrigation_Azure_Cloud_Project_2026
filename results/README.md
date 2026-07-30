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
