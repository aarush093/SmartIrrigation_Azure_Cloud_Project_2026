# Presentation

Review presentation material for *Cloud-Based Smart Irrigation Recommendation using
Weather Intelligence* (BITE412L, Dr. Priya V).

---

## Contents

| File | Description | Status |
|---|---|---|
| `README.md` | This file | Complete |
| `Phase1_Review.pptx` | Phase-I review deck | To be added before the review |
| `Phase2_Review.pptx` | Phase-II review deck | Phase-II |
| `Final_Review.pptx` | Final review deck | Phase-III |
| `figures/` | Exported diagrams and charts used in the decks | Ongoing |

---

## Phase-I deck outline

The Phase-I review covers documentation and planning. Code is not required and
will not be presented.

| Slide | Content | Presented by |
|---|---|---|
| 1 | Title, cluster, SDG mapping, team with register numbers | Aarush Pandit |
| 2 | Problem statement — the three failures of current irrigation practice | Nayan Jaggi |
| 3 | Objectives with measurable acceptance criteria | Nayan Jaggi |
| 4 | Literature survey overview — 15 papers, venue and year distribution | Nayan Jaggi |
| 5 | Research gap, group 1 (papers 1–5): scheduling and decision support | Nayan Jaggi |
| 6 | Research gap, group 2 (papers 6–10): cloud, IoT and distributed learning | Aarush Pandit |
| 7 | Research gap, group 3 (papers 11–15): predictive modelling | Krishna Agrawal |
| 8 | Consolidated research gap — the single structural discontinuity | Aarush Pandit |
| 9 | Novelty summary | Aarush Pandit |
| 10 | **Diagram 1 — Azure Cloud Architecture** | Aarush Pandit |
| 11 | **Diagram 2 — Complete System Architecture** | Aarush Pandit |
| 12 | Dataset details — six sources, all free, all verified | Krishna Agrawal |
| 13 | Azure services planning | Aarush Pandit |
| 14 | Technology stack | Krishna Agrawal |
| 15 | GitHub repository — structure, branch workflow, commit history | Aarush Pandit |
| 16 | Individual contribution and planned module ownership | All three |
| 17 | Work completed, in progress, and planned for later phases | Aarush Pandit |

Each member presents their own contribution, as required for the viva component.

---

## Presentation guidelines

| Rule | Reason |
|---|---|
| **One idea per slide** | A slide carrying three arguments communicates none of them |
| **Diagrams at full width** | Both architecture diagrams get a slide each, uncropped |
| **No paragraphs on slides** | Short phrases on the slide; the sentences are spoken |
| **Cite on the slide** | Any figure or claim from a surveyed paper carries its reference number |
| **Number every slide** | So questions can be directed precisely during the viva |
| **Rehearse the handovers** | Three presenters means three transitions; they should not be improvised |

---

## Viva preparation

Each member should be prepared to answer, without notes:

**All members**
- Which five papers did you study, and what gap did *you* identify?
- Why Azure rather than another cloud platform?
- What is your individual contribution, and where is it in the commit history?

**Nayan Jaggi (23BIT0390)**
- Why is FAO-56 the correct physical baseline rather than a purely learned model?
- What does the human-in-the-loop element in paper 2 contribute, and how does our
  design preserve it?

**Aarush Pandit (23BIT0416)**
- Walk through Diagram 1 and explain the role of each Azure service.
- Why is the Redis cache keyed by weather grid cell rather than by field?
- How does the system function for a farmer with no soil moisture sensor?

**Krishna Agrawal (23BIT0428)**
- Why a residual correction model rather than end-to-end prediction?
- Why must the train/test split be chronological?
- What happens to accuracy when a sensor is unavailable, and why is that acceptable?

---

## Figure sources

Figures are exported from existing repository content rather than recreated, so
the deck cannot drift from the report:

| Figure | Source |
|---|---|
| Azure Cloud Architecture | [`../architecture/azure_cloud_architecture.png`](../architecture/) |
| Complete System Architecture | [`../architecture/system_architecture.png`](../architecture/) |
| Result charts (Phase-III) | [`../results/figures/`](../results/) |

---

*Phase-I: planning and documentation.*
