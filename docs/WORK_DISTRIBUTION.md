# Work Distribution

**Project:** Cloud-Based Smart Irrigation Recommendation using Weather Intelligence
**Course:** BITE412L — Cloud Computing
**Instructor:** Dr. Priya V
**Team size:** 3

---

## 1. Team Members

| Student | Register Number | Name | GitHub Branch |
|---|---|---|---|
| Student 1 | 23BIT0390 | Nayan Jaggi | `feature/student1` |
| Student 2 | 23BIT0416 | Aarush Pandit | `feature/student2` |
| Student 3 | 23BIT0428 | Krishna Agrawal | `feature/student3` |

---

## 2. Literature Survey Allocation

Per the Phase-I guidelines for a team of three, the fifteen papers are divided
into three sets of five. Each member independently studied their own five papers
and wrote the corresponding research gap analysis.

| Student | Register Number | Papers | Thematic cluster | Gap analysis file |
|---|---|---|---|---|
| Nayan Jaggi | 23BIT0390 | 1–5 | Irrigation scheduling, decision-support systems, forecast-driven planning | [`research_gap_23BIT0390.md`](../literature_survey/research_gap_23BIT0390.md) |
| Aarush Pandit | 23BIT0416 | 6–10 | Cloud and IoT platform architecture, distributed and privacy-preserving learning, explainability | [`research_gap_23BIT0416.md`](../literature_survey/research_gap_23BIT0416.md) |
| Krishna Agrawal | 23BIT0428 | 11–15 | Soil-moisture prediction, evapotranspiration estimation, crop water requirement modelling | [`research_gap_23BIT0428.md`](../literature_survey/research_gap_23BIT0428.md) |

---

## 3. Phase-I Contribution Matrix

| Activity | Nayan Jaggi (23BIT0390) | Aarush Pandit (23BIT0416) | Krishna Agrawal (23BIT0428) |
|---|:---:|:---:|:---:|
| Literature survey — 5 papers each | ✓ | ✓ | ✓ |
| Research gap analysis — 5 papers each | ✓ | ✓ | ✓ |
| Survey table entries for own papers | ✓ | ✓ | ✓ |
| Consolidated research gap synthesis | ✓ | ✓ | ✓ |
| Problem statement and objectives | ✓ | ✓ | ✓ |
| Novelty summary | — | ✓ | ✓ |
| Azure cloud architecture (Diagram 1) | — | ✓ | — |
| Complete system architecture (Diagram 2) | ✓ | ✓ | — |
| Dataset identification and specification | ✓ | — | ✓ |
| Azure services planning table | — | ✓ | — |
| Technology stack | — | ✓ | ✓ |
| GitHub repository setup and branch configuration | — | ✓ | — |
| Repository documentation files | ✓ | ✓ | ✓ |
| Document compilation and formatting | — | ✓ | — |

---

## 4. Individual Phase-I Responsibilities in Detail

### 4.1 Nayan Jaggi — 23BIT0390

- Studied papers 1–5, covering irrigation scheduling, decision-support systems and
  forecast-driven planning.
- Authored the research gap analysis for those five papers, covering existing
  methods, advantages, limitations, research gap and possible improvement for each,
  with a consolidated summary.
- Completed rows 1–5 of the literature survey table.
- Contributed to the problem statement and project objectives.
- Contributed to the definition of the end-to-end system workflow represented in
  Diagram 2.
- Contributed to identification and specification of the weather and soil datasets.
- Authored `literature_survey/README.md`, `literature_survey/literature_survey.md`
  and `results/README.md`, and `src/frontend/README.md` for the module he will own.

### 4.2 Aarush Pandit — 23BIT0416

- Studied papers 6–10, covering cloud and IoT platform architecture, distributed
  and privacy-preserving learning and explainability.
- Authored the research gap analysis for those five papers with a consolidated
  summary.
- Completed rows 6–10 of the literature survey table.
- Designed both mandatory architecture diagrams.
- Authored the Azure services planning table and the technology stack.
- Contributed to the novelty summary.
- Created and configured the GitHub repository, branch structure and collaborator
  access.
- Compiled and formatted the Phase-I project report.
- Authored the root `README.md`, `docs/README.md`, this file,
  `architecture/*` and `src/backend/README.md`, `src/azure/README.md`,
  `src/README.md`, `presentation/README.md`.

### 4.3 Krishna Agrawal — 23BIT0428

- Studied papers 11–15, covering soil-moisture prediction, evapotranspiration
  estimation and crop water requirement modelling.
- Authored the research gap analysis for those five papers with a consolidated
  summary.
- Completed rows 11–15 of the literature survey table.
- Contributed to the novelty summary and the technology stack.
- Led specification of the machine learning datasets, preprocessing requirements
  and validation sources.
- Authored `dataset/README.md`, `references/README.md` and
  `src/ai_model/README.md` for the module he will own.

---

## 5. Planned Module Ownership — Phase-II and Phase-III

Per the contribution matrix in the Phase-I guidelines, the following activities are
owned by one member each. All other activities remain shared.

| Module | Owner | Scope |
|---|---|---|
| **Frontend Development** | Nayan Jaggi (23BIT0390) | React dashboard, PWA configuration and offline cache, multilingual interface, water-balance and forecast charts, field registration UI |
| **Backend Development** | Aarush Pandit (23BIT0416) | FastAPI service, Azure Functions (ingestion, recommendation engine, notification dispatch), FAO-56 water balance module, API Management configuration |
| **Database Integration** | Aarush Pandit (23BIT0416) | Azure SQL schema and migrations, Cosmos DB container design and partitioning, Redis caching strategy |
| **AI / Machine Learning** | Krishna Agrawal (23BIT0428) | Feature engineering pipeline, soil-moisture forecasting model, residual correction model, SHAP justification generator, Azure ML training jobs, model registry and retraining schedule |

### Shared across all three members

| Activity | Notes |
|---|---|
| Azure Cloud Services | Each member provisions and configures the services their module depends on |
| Testing | Each member writes unit tests for their own module; integration testing is joint |
| Documentation | Each member maintains the documentation for their own module |
| Presentation | Slides prepared jointly; each member presents their own contribution at review |
| GitHub Commits | Each member commits to their own feature branch throughout the project |

---

## 6. Git Branch Workflow

```
                    main
                      │
                   develop
        ┌─────────────┼─────────────┐
        │             │             │
feature/student1  feature/student2  feature/student3
   (Nayan)          (Aarush)         (Krishna)
```

**Rules**

1. `main` holds the final stable version. **No member commits directly to `main`.**
2. `develop` is the integration branch; all feature work merges here first.
3. Each member works only on their own `feature/studentN` branch.
4. Every merge into `develop` goes through a Pull Request reviewed by at least one
   other member.
5. Merge conflicts are resolved on the feature branch before the PR is approved.
6. `develop` merges into `main` only after the integrated state has been tested.
7. Each stable release is tagged, for example `v0.1-Phase1-planning`.

**Standard sequence**

```bash
git clone https://github.com/aarush093/SmartIrrigation_Azure_Cloud_Project_2026.git
cd SmartIrrigation_Azure_Cloud_Project_2026
git checkout feature/studentN
# ... implement assigned module ...
git add .
git commit -m "Descriptive message"
git push origin feature/studentN
# Open PR: feature/studentN -> develop
# Team review -> resolve comments -> merge
```

---

## 7. Expected GitHub Activity per Member

As set out in the Phase-I guidelines, each student is expected to demonstrate:

- Approximately 20–30 meaningful commits over the project
- At least 2 Pull Requests
- Participation in code review on teammates' Pull Requests
- Regular weekly commits rather than a single bulk upload
- Continuous documentation updates alongside code

---

*Phase-I: planning and documentation. Code implementation is not required at this
stage.*

---

# Phase-II Work Distribution

*Added 5 September 2026 by Aarush Pandit (23BIT0416). **The Phase-I tables above
are a submitted record and are unchanged.** No member's scope shrinks from what
Phase-I declared; plan Section 17.5.*

## 8. Phase-II Module Ownership

| Module | Nayan Jaggi (23BIT0390) | Aarush Pandit (23BIT0416) | Krishna Agrawal (23BIT0428) |
|---|:---:|:---:|:---:|
| Frontend: icon-only PWA, onboarding screen, laminated card design | **Owner** | Review | Review |
| Backend: FAO-56 engine, pump-minutes conversion, power-window scheduler | Review | **Owner** | Review |
| Voice channel: script masters, missed-call state machine, telephony and speech adapters | Contributor | **Owner** | Review |
| Azure: Functions, Cosmos DB, Blob, ACS, AI Speech, Document Intelligence, Key Vault, Monitor, Bicep, CI | Contributor | **Owner** | Contributor |
| AI/ML: soil-moisture model (Objective 3), forecast calibration, policy simulation | Review | Contributor | **Owner** |
| Testing | Contributor | Contributor | Contributor |
| Documentation and presentation | Contributor | Contributor | Contributor |

## 9. Delivered so far

### Aarush Pandit (23BIT0416) — backend, channel, Azure, CI

Milestones M0 to M6 complete on `feature/student2`. **1,270 tests**, `ruff` and
`mypy --strict` clean, five CI jobs green on every push.

| Area | Delivered |
|---|---|
| Engine | FAO-56 ET₀ (verified against Example 18 on every printed intermediate), Saxton-Rawls pedotransfer, crop calendar, root-zone water balance, pump-minutes conversion, Open-Meteo and SoilGrids adapters with offline fakes |
| Scheduler | Section 7 policy with the corrected capacity branch, feeder reliability, multi-field allocation, DISCOM schedule parser, hypothesis property tests |
| Channel | Script masters in Hindi, English and Tamil; spoken clock times with no digits; quiet hours; missed-call state machine with database-enforced idempotency; simulated and ACS telephony; Speech adapter |
| Azure | Functions app on the Python v2 model with FastAPI mounted, Cosmos store, Bicep for 25 resources on free tiers, five alert rules |
| Evidence | Objective 2 uncertainty budget over 1,095 station-days; Objective 6 five-policy simulation over 18 field-seasons; rain calibration beating the raw forecast |
| Docs | Phase-II plan, build log, ACS feasibility, Azure services, handoff status, results, viva notes, report draft |

### Nayan Jaggi (23BIT0390) — frontend

**Prepared and waiting for him to commit from his own account.** The package is
complete in `handoff/student1_frontend/`, which is gitignored so that it is not
committed on the wrong branch and credited to the wrong person.

| Prepared | Still his to do |
|---|---|
| Vite + React 18 + Tailwind + `vite-plugin-pwa` project | Upload to `feature/student1`, open the PR to `develop` |
| Three-tile home screen, seven-day bucket, onboarding form | App icons at 192 and 512 px |
| Language switch, service worker, Static Web Apps workflow | The three missed-call card icons, specified in `public/icons/README.md` |
| Interface contract fixed against the backend | Native-speaker check of the Hindi and Tamil labels |
| | The usability round, five to ten participants |

### Krishna Agrawal (23BIT0428) — AI/ML

**Prepared and waiting for him to commit from his own account**, in
`handoff/student3_ai_model/`.

| Prepared | Still his to do |
|---|---|
| `simulate_policies.py`, **written and run**: the Objective 6 result comes from it | `train_soil_moisture.py`: Objective 3, R² ≥ 0.80 |
| `forecast_source.py` and `rain_calibration.py`, written and run | `train_calibration.py`: a trained model that beats the empirical table |
| `train_*.py` scaffolds with the feature list, split rule and reporting contract fixed | `build_calibration_dataset.py` |
| | Upload to `feature/student3`, open the PR to `develop` |

The empirical rain calibration already in place scores **0.0859** on Brier
against the raw forecast's **0.1174**. That is the number his trained model
should beat, and beating it is its acceptance criterion.

## 10. Why the other two students' code is not on this branch

Per-student commit history and pull requests are assessed individually. A file
committed by the wrong person counts for the wrong person, so `handoff/` is in
`.gitignore` and only the Makefile change and `docs/HANDOFF_STATUS.md` are on
`feature/student2`. Each package carries a `HANDOFF_README.md` with the exact
GitHub web-upload steps and a ready-to-paste pull request description, so neither
teammate has to make a decision or run a command.

## 11. Expected GitHub activity, as at 5 September 2026

| Member | Commits | Pull requests | Reviews |
|---|---|---|---|
| Nayan Jaggi | Phase-I complete | Phase-I complete; Phase-II PR pending upload | Pending on `feature/student2` |
| Aarush Pandit | Phase-I plus 40+ in Phase-II | PR #7 open, `feature/student2 → develop` | Pending on the other two |
| Krishna Agrawal | Phase-I complete | Phase-I complete; Phase-II PR pending upload | Pending on `feature/student2` |
