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
