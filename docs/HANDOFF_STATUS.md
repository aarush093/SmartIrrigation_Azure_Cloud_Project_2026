# Teammate handoff status

**Date:** 5 September 2026
**Prepared by:** Aarush Pandit (23BIT0416)

Two modules are owned by other students and must be committed by them, from
their own GitHub accounts, on their own branches. Per-student commit history and
pull requests are assessed individually, so a file committed by the wrong person
counts for the wrong person.

The code has been written here so the system runs end to end, but **nothing
under `handoff/` is committed on `feature/student2`**. `handoff/` is in
`.gitignore`, and that is deliberate rather than incidental.

---

## Status

| Package | Owner | Branch | Target folder | Ready |
|---|---|---|---|---|
| `handoff/student1_frontend/` | Nayan Jaggi (23BIT0390) | `feature/student1` | `src/frontend/` | Yes |
| `handoff/student3_ai_model/` | Krishna Agrawal (23BIT0428) | `feature/student3` | `src/ai_model/` | Yes |

Each package contains a `HANDOFF_README.md` with the exact steps: which branch,
"Add file → Upload files", the commit message to paste, and the pull request
description. Neither teammate has to make a decision or run a command.

---

## What Aarush must do manually

The handoff folders cannot be pushed from this branch, so they have to reach the
other two some other way.

1. **Send Nayan `handoff/student1_frontend/`** — zip it, or share the folder.
   Tell him to read `HANDOFF_README.md` first and **not** to upload that file.
2. **Send Krishna `handoff/student3_ai_model/`** — same.
3. Confirm each opens a pull request into `develop`, not `main`.
4. **Review their pull requests.** Course expectation is at least one review of
   another member's PR per sprint, from each of us. Reviewing theirs is as much
   part of the grade as raising your own.

---

## What is in each package

### Frontend, Nayan

React 18, Vite, Tailwind, `vite-plugin-pwa`, Azure Static Web Apps workflow.
Exactly the Phase-I declared stack.

- Three-tile home screen: pump minutes with a start time, the power window as an
  arc on a 24-hour ring, rain as a filling drop. Every tile speaks when tapped.
- Seven-day water balance drawn as a filling bucket.
- Operator onboarding form matching the `onboard` API, including the three-way
  soil texture question and the bucket-test fields.
- Language switch for Hindi, English and Tamil.
- A specification for the three missed-call card icons, in
  `public/icons/README.md`.

**Still needed from him:** the icon PNG files, a native-speaker check of the
Hindi and Tamil interface labels, and the usability round.

### AI/ML, Krishna

- `train_soil_moisture.py` — **Objective 3**, retained from Phase-I. Scaffolded
  with the feature list, the chronological split rule and the reporting contract
  fixed, so the result is comparable and honest whatever architecture he picks.
- `build_calibration_dataset.py` — Open-Meteo Previous Runs against the
  Historical Archive, with NASA POWER as an independent check.
- `train_calibration.py` — the calibrated rain probability the skip rule needs,
  with monotone constraints specified and Brier score against the raw forecast
  as the acceptance criterion.
- `simulate_policies.py` — **Objective 6**, the four-policy comparison from plan
  Section 12. **This one is written, not scaffolded**, and imports the engine
  rather than reimplementing the water balance.

**Still needed from him:** the three models, and the report of whatever numbers
they produce.

---

## Two things worth saying plainly to both

**Report the number you get.** This project has already reported Objective 2 as
not met at its stated tolerance, with 1,095 station-days of measurement behind
the figure and a sensitivity analysis showing why it does not matter much in
practice. That was a stronger position at review than a passed threshold with
nothing behind it would have been. The same applies to Objective 3.

**Do not reimplement the engine.** The FAO-56 water balance, the crop calendar,
the pedotransfer and the power-window scheduler are installable
(`pip install -e .`) and tested. A second copy will drift, and then the
simulation stops describing the system it is meant to be evaluating.

---

## Running the whole system locally before they upload

```bash
make sync-handoff    # copies both packages into src/, never into git
make demo            # the daily loop for the three pilot farmers
make sim             # falls back to the handoff copy if src/ai_model is absent
```

`make sync-handoff` prints a reminder that the copied files belong to someone
else. `make sim` prefers `src/ai_model/simulate_policies.py` once Krishna has
committed it, and falls back to the handoff copy until then, so Objective 6 is
runnable now rather than blocked on his upload.
