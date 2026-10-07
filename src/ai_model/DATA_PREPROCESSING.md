# Data Preprocessing Pipeline

Owner: Krishna Agrawal (23BIT0428) — branch `feature/student3`
Module: Soil-Moisture Forecasting (AI/ML)

## Inputs

| Source | Variables | Role |
|---|---|---|
| Open-Meteo | air temperature, humidity, wind, solar radiation, precipitation forecast | ET0 inputs + rain-skip signal |
| NASA POWER | historical daily weather | training history, backfill of gaps |
| ISRIC SoilGrids | soil texture class (prefill only) | suggestion; falls back to farmer-declared texture |
| Farmer-declared | soil texture, crop, sowing date, power window | primary soil input and crop-stage context |

SoilGrids returned nulls at all three pilot points, so the pipeline treats it as
an optional prefill and never fails when it is missing — farmer-declared texture
is authoritative.

## Steps

1. **Ingest & align** — pull daily records, align all sources to a single
   per-field daily index in local time.
2. **Gap handling** — forward-fill short gaps (≤2 days); for longer gaps,
   substitute NASA POWER climatology for the same day-of-year. Flag imputed rows
   so they can be excluded from evaluation.
3. **ET0 computation** — compute reference evapotranspiration with the FAO-56
   Penman-Monteith method. Crop coefficient (Kc) is read from FAO-56 tables by
   crop and growth stage derived from sowing date.
4. **Feature engineering** — lag features (soil moisture t-1..t-7), rolling means
   of ET0 and rainfall, crop-stage one-hot, and declared-texture one-hot.
5. **Scaling** — fit a standard scaler on the training split only; persist it so
   the same transform applies at inference. Never fit on validation/test.
6. **Windowing** — build sliding input windows for the LSTM (see
   `MODEL_EVALUATION.md` for window length and horizon).

## Leakage guards

- Any feature that depends on future information (e.g. tomorrow's realised
  rainfall) is excluded; only forecasted rainfall available at decision time is
  used, matching the no-hindsight constraint used in the irrigation simulation.
- Scaler and imputation statistics are fit on training data only.

## Outputs

- A per-field, per-day feature table written to Blob Storage as Parquet.
- A persisted scaler and feature schema versioned alongside the model.

## Open items

- [PERSONALIZE] Record the exact training date range once the dataset entry's
  blank fields (URL, size, record count, licence) are finalised.
- [PERSONALIZE] Confirm the pilot crops and their Kc stage boundaries used.
