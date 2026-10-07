# AI / ML handoff — Krishna Agrawal (23BIT0428)

Everything in this folder is **yours**. It was prepared so the system could be
tested end to end, but it must be committed by you, from your own GitHub
account, on your own branch, because per-student commit history is graded.

**Do not ask Aarush to commit these files.** If he commits them, they count as
his contribution and not yours.

---

## What to do, step by step

### 1. Go to the repository on GitHub

<https://github.com/aarush093/SmartIrrigation_Azure_Cloud_Project_2026>

### 2. Switch to your branch

Branch dropdown → **`feature/student3`**. If it is not listed, type
`feature/student3` and choose "Create branch: feature/student3 from main".

### 3. Upload the files

**Add file** → **Upload files**. Drag in the contents of this folder, keeping
the structure. **Do not upload this file** (`HANDOFF_README.md`).

### 4. Commit directly to `feature/student3`

Title:

```
feat(ai_model): add soil-moisture model, forecast calibration and policy simulation
```

Description:

```
Adds the three learned and analytical components for Phase-II.

train_soil_moisture.py trains the Objective 3 root-zone soil-moisture
forecaster, one to seven days ahead, on free public features only. Split
is chronological by season, never random, so no future information leaks
into training. Reports R-squared and RMSE per horizon against the 0.80
target, with an ISMN validation hook for independent in-situ comparison.

build_calibration_dataset.py assembles training pairs from Open-Meteo
Previous Runs against the Historical Archive for the three pilot
districts, with NASA POWER as an independent check.

train_calibration.py fits a monotone calibrated classifier giving the
probability that observed rain over the horizon actually covers a given
deficit, and reports Brier score and a reliability diagram against the
raw forecast probability.

simulate_policies.py runs the five-policy comparison from Section 12 of
the plan over two seasons and writes the tables and figures to results/.
```

### 5. Open a pull request

**Base** `develop`, **compare** `feature/student3`.

Title: `Phase-II AI/ML: soil-moisture model, forecast calibration and policy simulation`

Description:

```
Implements the AI/ML scope for Phase-II.

The soil-moisture forecaster is Objective 3, retained from Phase-I. It sits
behind the engine's MoistureForecaster protocol, so if it misses the 0.80
R-squared target the scheduler falls back to Kc x forecast ET0 with no
change anywhere else. That is a deliberate design choice: the learned model
is never on the critical path.

The forecast calibration model is what makes the skip rule safe. The
scheduler must know how much to trust "80 percent chance of 20 mm" before it
tells a farmer not to irrigate, and a wrong skip costs him a whole irrigation
interval because the next power window may be days away.

The policy simulation is Objective 6: five policies over two seasons across
three districts, reporting water applied, stress days, pump hours, estimated
energy and deep percolation.
```

**Do not merge it yourself.** Aarush or Nayan reviews it first.

---

## What is in here

| File | What it does | Which objective |
|---|---|---|
| `train_soil_moisture.py` | Root-zone soil moisture, 1 to 7 days ahead | **Objective 3** |
| `build_calibration_dataset.py` | Forecast-versus-observed training pairs | Feeds the skip rule |
| `train_calibration.py` | Calibrated rain probability, Brier score, reliability diagram | Feeds the skip rule |
| `simulate_policies.py` | Five-policy comparison over two seasons | **Objective 6** |
| `plot_results.py` | The three Objective 6 figures | **Objective 6** |
| `diagnose_carry_over.py` | One-variable diagnostic that confirmed the carry-over defect | Evidence for the report |
| `notebooks/exploration.ipynb` | Data exploration and the figures for the report | — |
| `requirements.txt` | Dependencies, kept separate from the engine's | — |

> **Updated 5 September 2026 — upload the current copies, not an older download.**
> A carry-over accounting defect was found after the first Objective 6 run and
> fixed in both the engine and `simulate_policies.py`. `plot_results.py` and
> `diagnose_carry_over.py` changed or were added with it, and the published
> results were regenerated. Uploading a stale copy would put the superseded
> numbers back into the repository. The defect, the diagnostic and the
> before-and-after are in `docs/PHASE2_BUILD_LOG.md` under 5 September 2026, and
> the corrected results are in `results/README.md`.

---

## Four things that matter more than the model accuracy

**1. Never split randomly.** Every split in every script is chronological, by
season. A random split lets tomorrow's weather train the model that predicts
tomorrow, and the resulting R-squared will look excellent and mean nothing. The
scripts enforce this; do not add a `train_test_split(shuffle=True)` anywhere.

**2. Report the number you get.** If the soil-moisture model reaches R² of 0.62,
the report says 0.62 and explains why the fallback keeps the system working.
That is a far stronger position at review than a suspiciously round 0.80. This
project has already reported one objective as not met, with the measurement
behind it, and it strengthened the work rather than weakening it.

**3. Your model is not on the critical path, by design.** The scheduler talks to
a `MoistureForecaster` protocol with a `KcEt0Forecaster` default that always
works. Implement the same two methods — `name` and `forecast_etc(weather,
stages)` — and the engine will use yours instead. There is already a test
asserting a substitute implementation satisfies the protocol.

**4. A wrong skip is expensive.** The calibration model tells the scheduler
whether to trust a rain forecast. If it is over-confident the farmer is told not
to irrigate, the rain does not come, and the next power window may be three days
away. Prefer under-confidence: a needless irrigation costs water, a wrongly
skipped one costs the crop.

---

## Using the engine

The engine is a normal installable package and you should use it rather than
reimplementing anything:

```bash
pip install -e .          # from the repository root
```

```python
from irrigation_engine import (
    WaterBalance, crop_calendar, saxton_rawls, total_available_water,
    OpenMeteoProvider, resolve_soil,
)
from irrigation_engine.scheduler import plan_day, DeclaredRotation
```

`simulate_policies.py` already does this. The FAO-56 water balance, the crop
calendar and the power-window scheduler are all tested; please do not write a
second copy of any of them, or the two will drift and the simulation will stop
describing the system it is meant to be evaluating.

---

## Data sources

| Source | Use |
|---|---|
| Open-Meteo Historical Archive | Two seasons of weather for the simulation, and observed rainfall for calibration |
| Open-Meteo Previous Runs | Forecasts as they were issued, the other half of each calibration pair |
| NASA POWER | Independent check on both |
| ISMN | In-situ validation for Objective 3, where a station is near enough |

No API keys are needed for the first three. **Nothing downloaded goes into git**:
`data/raw/` is already in `.gitignore`. Only the outputs in `results/` are
committed.
