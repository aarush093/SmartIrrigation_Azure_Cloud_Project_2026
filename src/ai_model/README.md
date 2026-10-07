# AI / Machine Learning

**Owner:** Krishna Agrawal (23BIT0428)
**Branch:** `feature/student3`
**Status:** Phase-I — no code. Implementation begins in Phase-II.

---

## Purpose

The learned component of the system. Two models are trained here:

1. A **soil-moisture forecaster** predicting root-zone moisture one to seven days
   ahead from freely available weather and soil features.
2. A **residual correction model** predicting the difference between the FAO-56
   physical baseline and observed conditions for a given soil and crop.

Plus the **justification generator**, which identifies the two features that most
influenced a given decision.

---

## Design principle: physics first, learning second

The models do **not** replace the FAO-56 water balance. They correct it.

```
prediction = FAO-56 physical baseline  +  learned residual
```

This matters for three reasons:

| Reason | Consequence |
|---|---|
| **Error is bounded by physics** | The model cannot produce an agronomically absurd result, because the baseline constrains it |
| **No cold-start problem** | A brand-new field with zero history still gets the physical baseline on day one; the residual simply starts at zero |
| **Interpretability comes free** | The residual is small and explainable, unlike a black-box end-to-end prediction |

This directly addresses the gap identified in the research gap analysis for papers
11 and 13: prediction that never becomes a decision.

---

## Constraint: free inputs only

Models are trained on features obtainable at zero cost from public APIs. **No
feature that requires a soil moisture sensor may appear in the baseline model.**
Sensor data, where available, is assimilated as an optional correction in a
separate tier.

This is what makes the sensor-optional claim in the project's novelty summary real
rather than aspirational.

---

## What will be built here (Phase-II)

| Component | Description |
|---|---|
| **Feature pipeline** | Daily aggregation, FAO-56 ET₀ drivers, cumulative deficit, antecedent rainfall windows, crop coefficient by growth stage, soil-derived field capacity and wilting point |
| **Baseline models** | Random Forest and XGBoost on tabular features, as the accuracy-per-cost reference |
| **Sequence model** | LSTM for the one-to-seven-day soil-moisture trajectory |
| **Residual model** | Regression of the observed-minus-baseline residual on soil, crop and weather features |
| **Justification generator** | SHAP values reduced to the top two contributing features, mapped to plain-language templates |
| **Evaluation harness** | Chronological split by season, R², RMSE, and the irrigate/wait classification metrics that actually matter |
| **Training pipeline** | Azure ML jobs with a registered container image, model registration and versioning |
| **Retraining schedule** | Periodic retraining consuming accumulated farmer outcomes |

---

## Technology

| Item | Choice | Reason |
|---|---|---|
| Core | Python 3.11, pandas, NumPy | Shared language with the backend, so feature code is imported not reimplemented |
| Classical ML | scikit-learn, XGBoost | Strong tabular baselines; fast to train and cheap to serve |
| Deep learning | TensorFlow with Keras (LSTM) | Established for soil-moisture sequence modelling per the surveyed literature |
| Explainability | SHAP | Feature attribution reduced to the two dominant drivers |
| Tracking | MLflow via Azure Machine Learning | Every run recorded; every model versioned and registered |
| Serving | Azure ML managed endpoint | Versioned rollout without managing container infrastructure |

---

## Planned structure

```
ai_model/
├── README.md
├── requirements.txt
├── conda.yaml
├── features/
│   ├── engineering.py        # Shared with backend — single source of truth
│   └── schema.py             # Feature contract, enforced at train and serve
├── models/
│   ├── baseline_rf.py
│   ├── baseline_xgb.py
│   ├── lstm_soil_moisture.py
│   └── residual_correction.py
├── explain/
│   └── justification.py      # SHAP → top-2 features → plain language
├── training/
│   ├── train.py
│   ├── evaluate.py
│   └── azureml_job.yml
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   ├── 02_feature_analysis.ipynb
│   └── 03_model_comparison.ipynb
└── tests/
    ├── test_features.py
    └── test_residual.py
```

---

## Evaluation protocol

| Rule | Reason |
|---|---|
| **Chronological split by season — never random** | A random split leaks future weather into training and inflates every metric. This is the single most common error in the surveyed literature's weaker papers |
| **Report accuracy *and* compute cost** | Following paper 11's example. A 13% accuracy gain at 10× compute (paper 12) may not be the right engineering choice for a farm-scale service |
| **Validate against real observations, not only reanalysis** | The International Soil Moisture Network provides in-situ ground truth; validating a model only against another model proves nothing |
| **Optimise the decision, not the number** | Report irrigate/wait classification accuracy and depth error within agronomic tolerance alongside R² and RMSE. A model that minimises RMSE while getting the irrigate/wait call wrong is useless |

### Objective 3 acceptance criterion

R² ≥ 0.80 and RMSE within the defined tolerance on a held-out season, using only
freely available features.

---

## Justification generation

The output is a sentence, not a plot. SHAP values are computed for the decision,
the top two contributing features are selected, and each maps to a template:

| Dominant feature | Template fragment |
|---|---|
| Cumulative ET since last irrigation | "high evaporative demand since your last irrigation" |
| Forecast rainfall | "rainfall expected in the next {n} days" |
| Absence of forecast rainfall | "no rainfall forecast for {n} days" |
| Crop growth stage | "your crop is at {stage}, when water matters most" |
| Soil water holding capacity | "your soil holds water for a shorter period" |

Two fragments are joined into one sentence. This addresses the gap identified in
paper 10: explainability that is not bound to the farmer's actual question.

---

*Phase-I: planning and documentation. No code has been written and no data has
been downloaded.*
