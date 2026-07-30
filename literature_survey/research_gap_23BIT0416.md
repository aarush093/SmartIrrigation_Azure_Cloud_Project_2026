# Research Gap Analysis — Papers 6 to 10

**Student:** Aarush Pandit
**Register Number:** 23BIT0416
**Project:** Cloud-Based Smart Irrigation Recommendation using Weather Intelligence
**Course:** BITE412L — Cloud Computing | **Instructor:** Dr. Priya V
**Thematic focus:** Cloud and IoT platform architecture, distributed and privacy-preserving learning, explainability

> This analysis reflects my own reading of the five papers assigned to me. Research
> gaps are not reproduced from the source papers.

---

## Paper 6 — Al Mashhadany et al. (2024), *Environmental Monitoring and Assessment*

**Citation:** Y. Al Mashhadany, H. R. Alsanad, M. A. Al-Askari, S. Algburi, and B. A. Taha, "Irrigation intelligence—enabling a cloud-based Internet of Things approach for enhanced water management in agriculture," *Environmental Monitoring and Assessment*, vol. 196, art. 438, May 2024. DOI: 10.1007/s10661-024-12606-1

The method here is a cloud-connected sensing and actuation stack: internet-connected instruments monitor weather, soil condition and crop health, the resulting stream is stored and analysed for daily fluctuation and longer-term trend, and a hybrid controller combining fuzzy logic with conventional PID governs pump behaviour, with smart cameras supplying visual context. Its strengths are that it closes the loop end to end, from field observation through to physical actuation, and that the hybrid controller extracts high efficiency from the pump rather than treating actuation as a solved detail; the emphasis on longitudinal analysis of stored data is also correct, since seasonal pattern is exactly what a single-reading threshold system cannot see.

Where it falls short is in temporal orientation. The system is reactive — it responds to the field as measured now — and contains no forecast-driven anticipation, so it cannot decline to irrigate because rain is expected in eighteen hours, which is the single most valuable decision a weather-aware system makes. Validation leans substantially on Simulink modelling rather than sustained field deployment. Most significantly for our purposes, "cloud" is used generically: no managed service is named for storage, identity, messaging or monitoring, so the architecture cannot be costed, secured or reproduced.

**Research gap.** A demonstrated cloud-connected control system exists with neither a predictive layer nor a reference architecture bound to concrete provider services.

**Possible improvement.** Invert the control philosophy — make the forecast the primary input and the sensor the correction — and specify every architectural box as a named Azure service so that the design is deployable rather than illustrative.

---

## Paper 7 — Bera, Dey, Mukherjee & De (2024), *IEEE Transactions on Consumer Electronics*

**Citation:** S. Bera, T. Dey, A. Mukherjee, and D. De, "FLAG: Federated learning for sustainable irrigation in Agriculture 5.0," *IEEE Transactions on Consumer Electronics*, vol. 70, no. 1, pp. 2303–2310, 2024.

This paper proposes federated learning for irrigation decision-making across a dew–edge–cloud hierarchy. Local LSTM and deep neural network models are trained on each farm and aggregated globally, raw data and user identity never leave the premises, gradient encryption defends against reconstruction from shared updates, and a dew-computing cache holds data temporarily when connectivity fails. Its advantages are real and well-argued: reported accuracy near ninety-nine per cent at roughly half the latency and energy consumption of a conventional edge–cloud arrangement, privacy protection designed in rather than appended, and a caching strategy that acknowledges what rural connectivity is actually like.

Where it falls short is in what it demands and what it ignores. Federated participation requires capable compute at every farm, which reintroduces the capital barrier that smart irrigation is supposed to remove; the evaluation rests on a limited dataset; and, most tellingly, the framework makes no use of public weather forecasts at all.

**Research gap.** The architecture that most carefully protects the farmer's private data is simultaneously the one that declines to exploit the free, openly available signal that would most improve its predictions.

**Possible improvement.** A hybrid split: forecast-derived features, which are public by construction and carry no privacy cost, are computed centrally and shared, while only farm-specific observations remain local. Privacy is preserved where it matters and the forecast advantage is recovered where it costs nothing.

---

## Paper 8 — Killeen, Lin, Li, Kiringa & Yeap (2025), *ACM Journal on Computing and Sustainable Societies*

**Citation:** P. Killeen, C. Lin, F. Li, I. Kiringa, and T. Yeap, "IoT-based smart farming architecture using federated learning: A nitrous oxide emission prediction use case," *ACM Journal on Computing and Sustainable Societies*, vol. 3, no. 2, art. 12, Feb. 2025. DOI: 10.1145/3723039

The contribution is an architecture rather than an application: a privacy-aware IoT smart-farming design combining federated learning with ensemble learning, demonstrated through nitrous oxide emission prediction driven by weather, soil and emission data. Its advantages are conceptual and I rate them highly. The authors argue that machine learning models can substitute for expensive sensing hardware, which reframes cost from an equipment problem into a modelling problem; they treat farmer privacy concern as a genuine adoption blocker rather than an inconvenience; and the architecture is described at a level of generality that permits transfer to other agricultural prediction tasks.

Where it falls short is that the demonstration is emissions, not irrigation, so the reader is left to assume transferability rather than shown it. Federated benefit only materialises once several farm silos participate, which is a cold-start problem the paper does not resolve, and no operating cost model accompanies the architecture.

**Research gap.** A well-specified privacy-aware farming architecture has never been instantiated for irrigation recommendation, nor bound to a commercial managed cloud with concrete service selections.

**Possible improvement.** Perform exactly that instantiation — retarget the architectural pattern at irrigation depth and timing — and resolve the cold-start problem by seeding the global model on public weather and soil data, so the first participating farm receives a useful recommendation on day one rather than after a cohort has assembled.

---

## Paper 9 — Manocha, Sood & Bhatia (2024), *Sustainable Computing: Informatics and Systems*

**Citation:** A. Manocha, S. K. Sood, and M. Bhatia, "IoT-digital twin-inspired smart irrigation approach for optimal water utilization," *Sustainable Computing: Informatics and Systems*, vol. 41, art. 100947, 2024. DOI: 10.1016/j.suscom.2023.100947

The approach constructs a digital twin of the irrigated field, driven by IoT sensing, and uses that virtual replica to optimise water utilisation predictively. Its advantages follow from what a twin is: irrigation strategies can be evaluated before water is committed, optimisation targets water utilisation explicitly rather than as a by-product of yield maximisation, and the twin carries state forward across the season so that cumulative effects are represented instead of forgotten between decisions.

Where it falls short is cost, in three currencies at once. Building and calibrating a twin per field is expensive in data, in compute and in expertise; the approach presumes dense instrumentation that a two-hectare holding will not have; and the ongoing synchronisation between twin and field is itself a continuous operational expense.

**Research gap.** The digital twin is a technique for well-capitalised agriculture, with no defined low-cost approximation that preserves the predictive benefit for everyone else.

**Possible improvement.** A deliberately reduced twin — a lightweight per-field state comprising a running water balance, crop stage and recent irrigation history, driven by forecast data and public soil characteristics rather than dense sensing. Most of the anticipatory value of a twin comes from carrying state forward, and that is cheap; the expense lies in fidelity this application does not need.

---

## Paper 10 — Martin et al. (2024), *IEEE Access*

**Citation:** R. J. Martin, R. Mittal, V. Malik, F. Jeribi, S. T. Siddiqui, and M. A. Hossain, "XAI-powered smart agriculture framework for enhancing food productivity and sustainability," *IEEE Access*, vol. 12, pp. 168412–168427, 2024. DOI: 10.1109/ACCESS.2024.3492973

This framework applies explainable AI to smart agriculture with the stated aim of improving productivity and sustainability, generating interpretable accounts of model outputs alongside the predictions themselves. Its advantage addresses the problem that most agricultural machine learning quietly avoids: a farmer who does not understand why a recommendation was made will not act against their own judgement to follow it, and explainability is the only mechanism that converts an accurate model into an adopted one. Publishing in a high-visibility open-access venue also means the approach is genuinely available to build on.

Where it falls short is specificity. The contribution operates at framework level rather than deployment level, irrigation is one candidate application among several rather than the object of the work, and the explanations are not validated with the people who would have to read them.

**Research gap.** Explainability has not been bound to the particular question an irrigating farmer asks — why today rather than tomorrow, and why this depth rather than more — so recommendations remain accurate but unjustified at the moment of use.

**Possible improvement.** Constrain explanation to the decision-relevant drivers and express it in the farmer's own terms: forecast rainfall, accumulated evapotranspiration since the last irrigation, current crop stage. A short sentence naming the two factors that decided the recommendation is worth more in the field than a complete attribution plot.

---

## Consolidated Gap Summary — Aarush Pandit (23BIT0416)

Across these five papers the pattern I keep meeting is that the computing is ahead of the agriculture. Papers 7 and 8 show that privacy-preserving distributed learning over farm data is a solved architectural problem; paper 9 shows that predictive state can be carried forward through a digital twin; paper 10 shows that model decisions can be made explicable; paper 6 shows that the whole path from sensor to pump can be closed through a cloud connection. Individually these are strong pieces of systems work. What none of them does is assemble the pieces around the actual irrigation question while respecting what a small farm actually has, which is a phone, unreliable connectivity, no soil sensors and no capital. Two omissions stand out. First, forecast data — free, public, globally available and privacy-neutral — is treated as peripheral by precisely the architectures that most need a cheap high-value input. Second, none of these systems is specified against a named managed-cloud service catalogue, so none can be costed, secured, monitored or reproduced by anyone other than its authors. My position is that the contribution worth making is not a novel learning algorithm but a fully specified, forecast-first cloud architecture in which every component is a named service with a defined purpose, every recommendation carries a one-line justification, and the sensing requirement is optional rather than assumed.

---

*Phase-I: planning and documentation.*
