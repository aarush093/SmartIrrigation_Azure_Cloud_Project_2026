# CLAUDE.md — engineering standards for this repository

Working agreement for any session, human or agent, that touches this repository.
Read this before making a change. It is binding; where it conflicts with a
convention you would otherwise apply, this file wins.

**Project:** Cloud-Based Smart Irrigation Recommendation using Weather
Intelligence. BITE412L Cloud Computing, VIT, Dr. Priya V. Microsoft Azure only.

**The project title is fixed. Never change it.**

---

## 1. Authoritative documents

| Document | Role |
|---|---|
| `docs/PHASE2_NOVELTY_AND_PLAN.md` | The specification for Phase-II. Where this file and the plan disagree, the plan wins. Section 7 defines the scheduler policy, Section 12 the evaluation, Section 17 the reconciliation with Phase-I |
| `docs/PHASE2_BUILD_LOG.md` | Dated engineering record. Append an entry per session. Never rewrite a past entry; mark it superseded |
| Phase-I documents | `README.md`, `docs/WORK_DISTRIBUTION.md`, `architecture/*`, `dataset/README.md`, `literature_survey/*`, `references/README.md`, every `src/**/README.md` |

**Phase-I is a submitted and graded record. It is not rewritten.** Phase-II is
recorded as an addendum: every Phase-I objective, service, dataset and technology
keeps its entry and receives a Phase-II status. Changes are stated in an
addendum, never made by silent edit. Editing a Phase-I document beyond an
additive, clearly-marked Phase-II section requires the repository owner's
explicit approval.

---

## 2. Branch and commit discipline

This is graded on the GitHub contribution record, so it is not negotiable.

- **Work only on `feature/student2`.** Never commit to `main` or `develop`.
- **Never force-push.** Never rewrite published history.
- **Do not open pull requests from a session.** The repository owner opens
  `feature/student2 -> develop` pull requests from the GitHub web interface so
  the review trail is his.
- One logical change per commit. Conventional-commit style, imperative mood:
  `feat(engine): add Saxton-Rawls pedotransfer`,
  `test(scheduler): window length never exceeded`,
  `fix(pump): correct head term in discharge estimate`.
  Scopes in use: `engine`, `scheduler`, `telephony`, `speech`, `functions`,
  `infra`, `ci`, `docs`, `handoff`, `params`.
- Many small meaningful commits, not one large one. Commit at every point where
  the tree is coherent and the tests pass.
- At the end of every milestone: run the full test suite, commit, and print the
  commits made in that milestone.
- Git identity must be the GitHub noreply address, or the commits do not
  attribute to the account being graded:
  `Aarush Pandit <153858722+aarush093@users.noreply.github.com>`.

### Never commit

Secrets, `.env` files, keys, connection strings, downloaded datasets, DISCOM
PDFs, synthesised audio, `local.settings.json`. Add the pattern to `.gitignore`
before the file exists, not after. Simulation outputs under `results/` and test
fixtures under `tests/fixtures/` are deliberate exceptions and are versioned.

---

## 3. Teammate handoff rule

Two teammates own other modules and must commit their own files from their own
GitHub accounts, because per-member commit history is assessed.

| Student | Name | Register no. | GitHub | Branch | Owns |
|---|---|---|---|---|---|
| 1 | Nayan Jaggi | 23BIT0390 | `jaggs11` | `feature/student1` | Frontend: PWA, onboarding screen, voice script masters, card design, usability round |
| 3 | Krishna Agrawal | 23BIT0428 | `Krishnaaep` | `feature/student3` | AI/ML: soil-moisture model (Objective 3), forecast calibration model, simulation study |

Everything else — engine, scheduler, Azure Functions, ACS, Speech and Document
Intelligence adapters, Bicep, CI, documentation — belongs to Aarush Pandit
(23BIT0416) and goes on `feature/student2`.

**The rule.** Their files are still written here, because the system must run end
to end, but they are **never committed on `feature/student2`**. They are written
to:

- `handoff/student1_frontend/` — mirrors `src/frontend/`
- `handoff/student3_ai_model/` — mirrors `src/ai_model/`

`handoff/` is in `.gitignore`. For local end-to-end testing the Makefile copies
these into place at runtime; never git. Each handoff folder carries a
`HANDOFF_README.md` giving exact GitHub web-upload steps — branch name,
"Add file > Upload files", the commit message to paste, then the pull request to
`develop` — so the teammate needs to make no decisions.

---

## 4. Engineering standards

### Language and layout

- Python 3.11.
- `src/backend/irrigation_engine/` is a **pure, dependency-light library**:
  `numpy`, `pydantic`, `httpx`, `pyyaml` only. **No Azure imports anywhere in
  it.** It must stay importable and testable with no network and no cloud
  credentials. This is what makes the agronomy independently reviewable.
- Azure Functions live in `src/azure/functions/` on the Python v2 programming
  model and import the library. The FastAPI application is hosted through
  `AsgiFunctionApp`, so the Phase-I declared stack is what actually runs. Timer
  and queue triggers stay native Functions. Storage Queues, not Service Bus.
- Tests live under `tests/`, mirroring the package layout.

### Typing and style

- Type hints everywhere. Docstrings on every public function.
- `ruff` clean and `mypy --strict` clean. Both run in CI on every push.
- No bare `except`. No mutable default arguments. No `Any` without a comment
  saying why.

### Agronomic constants

**Every** agronomic constant — Kc, p, Zr, Ky, Ea, pedotransfer coefficients —
lives in `src/backend/irrigation_engine/params/*.yaml`, never inline in code.
Each carries a comment naming its source, for example `FAO-56 Table 12`,
`FAO-56 Table 22`, `Saxton and Rawls 2006`, `FAO Training Manual 4`.

**Anything not certain gets `# TODO [VERIFY]` and a conservative default. Never
invent a number silently.** A wrong constant that looks authoritative is worse
than an admitted gap: it survives review and fails in the field.

### Determinism

The decision path is deterministic end to end. **No language model anywhere in
it.** The only generative components are script templating, Azure AI Speech for
synthesis and Azure AI Translator for draft translation — all rendering, never
deciding. Identical inputs must produce identical outputs; this is enforced by
property test.

### Adapters

Every external call sits behind an interface with an offline fake:
`WeatherProvider`, `SoilProvider`, `TelephonyAdapter`, `SpeechAdapter`,
`ScheduleSource`, `MoistureForecaster`. Fakes are used in tests; real adapters
are selected by settings. ACS sits behind a feature flag and **must not be
needed for `make demo`**.

### Tests

- **No external network in unit tests.** Tests that hit Open-Meteo, SoilGrids or
  NASA POWER are marked `@pytest.mark.integration` and skipped by default.
- Known-answer tests cite their source in the test itself, for example the FAO-56
  example box number.
- The scheduler carries `hypothesis` property tests: scheduled minutes never
  exceed window length; depletion after a mandatory refill never exceeds RAW at
  the next window under the forecast; a skip happens only when calibrated rain
  covers the deficit; identical inputs give identical outputs.

### Farmer-facing strings

Live in `src/backend/irrigation_engine/scripts/{hi,en,ta}.yaml`. Other languages
are generated later with Azure AI Translator and checked by a native speaker.

**Never put millimetres, ET0, depletion, or percentages in a farmer-facing
string.** Only minutes, clock times, and rain in familiar words. One decision per
call, one number per decision, and a one-line reason in plain language. See plan
Section 5.5.

---

## 5. Standard commands

`make setup` install into a virtualenv · `make test` full suite ·
`make lint` ruff and mypy · `make demo` three-farmer end-to-end run with the
simulated telephony console · `make sim` policy simulation into `results/` ·
`make func-start` Functions host locally · `make deploy-plan` `az deployment
group what-if`, never an actual deployment.

---

## 6. Ask before doing

Permitted without asking: creating files under `src/backend`, `src/azure`,
`tests`, `docs`, `results`, `handoff`, `.github/workflows`; installing Python dev
dependencies into a virtualenv; running tests and linters; committing to
`feature/student2`; calling Open-Meteo, SoilGrids and NASA POWER for demo data.

**Ask first:** anything that costs money on Azure; provisioning ACS phone
numbers; deleting or rewriting Phase-I documents; changing the course-mandated
folder structure (`README.md`, `docs/`, `literature_survey/`, `architecture/`,
`dataset/`, `src/{frontend,backend,ai_model,azure}`, `results/`, `presentation/`,
`references/`); adding heavy dependencies; anything touching `main` or `develop`.

---

## 7. Quality bar

Everything here may be submitted for marks.

- Academic tone in documents. No filler.
- **No invented references, numbers or URLs.** If unsure whether something is
  true, write `TODO [VERIFY]` and move on.
- Prefer a smaller working system with tests over a larger untested one.
- Report outcomes faithfully. If a test fails, say so with the output. If a
  target is missed, report the shortfall rather than restating the target.
