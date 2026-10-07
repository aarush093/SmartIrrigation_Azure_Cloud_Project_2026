# Model & Evaluation Plan — Soil-Moisture Forecasting

Owner: Krishna Agrawal (23BIT0428) — branch `feature/student3`
Module: AI/ML

## Model

- **Architecture:** LSTM for multi-day soil-moisture forecasting.
- **Input window:** 7 days of engineered features (see `DATA_PREPROCESSING.md`).
- **Forecast horizon:** 3 days ahead, so the scheduler can plan pump minutes
  before the farmer's rationed power window.
- **Target:** root-zone soil moisture, from which the scheduler derives depletion
  and the required irrigation depth.

## Why the forecast feeds the scheduler

The scheduler converts FAO-56 root-zone depletion into pump running minutes that
fit inside the rationed electricity window. A short-horizon forecast lets it plan
ahead instead of reacting only to today's state, and lets the rain-skip policy
avoid irrigating before forecast rainfall — without using hindsight.

## Train / validation / test split

- Chronological split (no shuffling) to respect the time series: earliest block
  for training, middle for validation, most recent for test.
- Imputed rows (flagged in preprocessing) are excluded from the metrics.

## Metrics

| Metric | Why |
|---|---|
| MAE (mm) | primary accuracy on soil moisture |
| RMSE (mm) | penalises large misses that would mislead the scheduler |
| Bias (mean error) | checks for systematic over/under-prediction |
| Skill vs persistence | forecast must beat a "tomorrow = today" baseline to be worth using |

A naive persistence baseline is reported alongside the LSTM so the model's value
is measured honestly, not in isolation.

## Validation principle

Physical sanity checks are mandatory. A forecast that drives the scheduler must
never produce an irrigation plan that uses more water than an unlimited-power
reference policy — if it does, that is an impossible result and signals a bug,
not a better model.

## Open items

- [PERSONALIZE] Fill in realised metric values after the first full training run.
- [PERSONALIZE] Add a learning-curve plot to `results/` once training is logged.
