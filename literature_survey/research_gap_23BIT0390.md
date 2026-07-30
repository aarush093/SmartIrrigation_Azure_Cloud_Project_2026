# Research Gap Analysis — Papers 1 to 5

**Student:** Nayan Jaggi
**Register Number:** 23BIT0390
**Project:** Cloud-Based Smart Irrigation Recommendation using Weather Intelligence
**Course:** BITE412L — Cloud Computing | **Instructor:** Dr. Priya V
**Thematic focus:** Irrigation scheduling, decision-support systems and forecast-driven planning

> This analysis reflects my own reading of the five papers assigned to me. Research
> gaps are not reproduced from the source papers.

---

## Paper 1 — Umutoni & Samadi (2024), *Agricultural Water Management*

**Citation:** L. Umutoni and V. Samadi, "Application of machine learning approaches in supporting irrigation decision making: A review," *Agricultural Water Management*, vol. 294, art. 108710, Apr. 2024. DOI: 10.1016/j.agwat.2024.108710

**Existing method.** The authors conduct a structured review of sixteen studies in which machine learning is used to predict crop water need and to drive irrigation scheduling decisions. Each study is characterised by its input feature set, its algorithm family and its demonstrated applicability outside laboratory conditions. The review positions machine learning against two older traditions: deterministic calculation such as FAO-56 and process-based crop modelling.

**Advantages.** The paper is valuable precisely because it does not advocate a single algorithm. It reports comparative accuracy and water conservation relative to fixed-interval and threshold-triggered irrigation, which is the correct baseline against which any new system should be judged. It also treats adoption as a technical question rather than a social afterthought, examining whether the reviewed models could survive field conditions.

**Limitations.** Being a review, it establishes no common benchmark; the sixteen studies differ in crop, region, sensing density and evaluation metric, so their reported accuracies are not strictly comparable. No new experimental result is contributed, and the field-scale emphasis means very large or very small holdings are under-represented.

**Research gap.** The authors themselves conclude that progress is constrained by limited data availability, by constraints on data sharing between growers, by the absence of uncertainty quantification in reported models, and by the need for physics-informed learning. None of these four constraints is addressed by a shared data layer that many farms could contribute to and draw from.

**Possible improvement.** A hosted platform that accumulates weather, soil and irrigation-outcome records across many participating fields would directly relieve the data-scarcity constraint the review identifies. Coupling that store with models that return a prediction interval rather than a single number, and that respect a physical water-balance constraint, would answer the uncertainty and physics-informed recommendations simultaneously.

---

## Paper 2 — Conde, Guzmán & Athelly (2024), *Computers and Electronics in Agriculture*

**Citation:** G. Conde, S. M. Guzmán, and A. Athelly, "Adaptive and predictive decision support system for irrigation scheduling: An approach integrating humans in the control loop," *Computers and Electronics in Agriculture*, vol. 217, art. 108640, 2024.

**Existing method.** A decision-support algorithm is constructed from control theory, combining a feedback path with a feedforward path so that modelling, state estimation, prediction and control operate together. Its distinguishing feature is that human intervention is treated as part of the control loop rather than as noise to be eliminated. Soil moisture, rainfall, temperature and irrigation records are fused with weather forecasts to produce timing and depth instructions.

**Advantages.** The output is prescriptive, not descriptive — the manager is told when and how much, which is the form in which an irrigation decision is actually taken. The reported potential of roughly thirty per cent water saving in seepage-irrigated conditions is substantial, and maintaining soil moisture within a controlled band reduces both leaching and runoff.

**Limitations.** The formulation is tied to one irrigation method at one research site, and the control-oriented soil-moisture model would require re-identification elsewhere. The design assumes a manager who acts on instructions promptly; delayed or partial compliance degrades the loop. Architecturally it is a single-site tool with no provision for serving multiple independent farms.

**Research gap.** A control strategy that demonstrably saves water on one instrumented site has no path to replication, because there is no multi-tenant, cloud-hosted realisation in which the same logic could be instantiated per field with per-field parameters.

**Possible improvement.** The control logic should be separated from the site: parameters describing soil, crop and irrigation method become per-field configuration held in a database, while the estimation and control routines run as shared, stateless cloud functions. Human intervention then re-enters the loop through a dashboard confirmation rather than through direct operator presence at the site.

---

## Paper 3 — Jamal et al. (2023), *Water Resources Research*

**Citation:** A. Jamal, X. Cai, X. Qiao, L. Garcia, J. Wang, A. Amori, and H. Yang, "Real-time irrigation scheduling based on weather forecasts, field observations, and human-machine interactions," *Water Resources Research*, vol. 59, no. 12, art. e2023WR035810, Dec. 2023. DOI: 10.1029/2023WR035810

**Existing method.** The authors build a real-time irrigation scheduling tool that unites three components normally treated separately: simulation–optimisation to search for a good schedule, data assimilation to keep the modelled field state aligned with observation, and human–computer interaction so that the grower's judgement enters the schedule. Probabilistic weather forecasts are converted into weighted scenarios rather than reduced to one deterministic sequence.

**Advantages.** Handling forecast uncertainty as a distribution of scenarios is methodologically stronger than scheduling on a single forecast, since it allows the schedule to hedge against a rainfall event that may or may not occur. Assimilation prevents the simulated soil-moisture and canopy state from drifting away from reality across a season, which is the usual failure mode of long-horizon crop simulation.

**Limitations.** Simulation–optimisation over multiple weather scenarios is computationally expensive, and the interaction design presumes a user who has been trained on the tool. Validation covers a small number of fields, so the transferability of the calibration is untested.

**Research gap.** Uncertainty-aware scheduling remains a research instrument. There is no service form in which the probabilistic reasoning executes remotely and the grower receives one short, plain-language instruction without needing to understand the scenarios behind it.

**Possible improvement.** The scenario ensemble should be evaluated in the cloud on a schedule, with only the resulting recommendation and a confidence indicator delivered to the farmer. The human-in-the-loop element can then be preserved cheaply as an accept-or-override action recorded against the recommendation, which additionally produces the labelled feedback needed to improve the model over time.

---

## Paper 4 — Abd El Baki, Fujimaki, Tokumoto & Saito (2024), *Frontiers in Agronomy*

**Citation:** H. M. Abd El Baki, H. Fujimaki, I. Tokumoto, and T. Saito, "Optimization of irrigation scheduling using crop–water simulation, water pricing, and quantitative weather forecasts," *Frontiers in Agronomy*, vol. 6, art. 1376231, 2024. DOI: 10.3389/fagro.2024.1376231

**Existing method.** Irrigation scheduling is optimised by coupling a crop–water simulation with the price of water and with quantitative weather forecasts, so that the objective function is economic return rather than yield alone. The formulation therefore asks not merely whether irrigation is agronomically justified, but whether it is worth its cost given what the forecast implies.

**Advantages.** Introducing water pricing is an important corrective; in most irrigation research water is treated as free, which is untrue wherever it is metered, pumped with paid electricity or rationed. The work also quantifies how the availability and quality of forecast information alter the optimal decision, which is directly relevant to this project's premise.

**Limitations.** The study is simulation-based, with no farmer-facing delivery mechanism and no field trial of the resulting schedules. Sensitivity to forecast error is a structural risk that grows with the horizon, and the parameterisation of the crop–water model requires specialist knowledge that a cultivator will not possess.

**Research gap.** Economic optimisation of irrigation is effectively unavailable to smallholders, not because the mathematics is unavailable but because no accessible interface or automated pipeline exposes it.

**Possible improvement.** A simplified cost term — pumping energy or tariff per unit volume — can be entered once as a field property and applied automatically, allowing the recommendation to be expressed in both volume and approximate cost. Forecast-error sensitivity should be reported to the user as a shorter or longer valid horizon rather than concealed inside the model.

---

## Paper 5 — Mohamed Naziq et al. (2024), *Water Supply*

**Citation:** S. Mohamed Naziq, N. K. Sathyamoorthy, Ga. Dheebakaran, S. Pazhanivelan, and N. Vadivel, "Coupled weather and crop simulation modeling for smart irrigation planning: A review," *Water Supply*, vol. 24, no. 8, pp. 2844–2865, Aug. 2024. DOI: 10.2166/ws.2024.170

**Existing method.** This is a review of crop simulation models coupled with weather forecast data for irrigation planning. Its most useful contribution is a taxonomy: scheduling approaches are classified as evapotranspiration and water-balance based, soil-moisture status based, plant-water-status based, or driven by simulation model output. Publication trends from 2000 to 2023 are used to establish where research effort has concentrated.

**Advantages.** The review confirms the evapotranspiration and water-balance approach, grounded in FAO-56, as the dominant and defensible baseline, which gives this project a justified starting point rather than an arbitrary one. It identifies specifically where forecast integration improves planning quality, and its Indian agro-climatic framing makes the findings locally applicable.

**Limitations.** No implementation or validation accompanies the review. The crop simulation models discussed demand extensive calibration inputs — soil hydraulic properties, cultivar coefficients, management histories — that most farms cannot supply, which quietly limits the practical reach of the conclusions.

**Research gap.** Forecast and crop-model coupling is described almost entirely as offline, desktop-scale modelling work. It has not been re-expressed as a hosted service that ingests forecasts automatically and returns an advisory without human modelling effort in between.

**Possible improvement.** The FAO-56 water-balance calculation is light enough to run as a scheduled cloud job for thousands of fields, using forecast evapotranspiration drivers and default crop coefficients selected by crop and growth stage. Machine learning should then correct the residual between that physical baseline and observed conditions, rather than replacing the physics outright.

---

## Consolidated Gap Summary — Nayan Jaggi (23BIT0390)

Reading these five papers together, my conclusion is that the scheduling problem has largely been solved as an optimisation exercise and left unsolved as a delivery problem. Papers 2 and 3 both produce genuinely prescriptive schedules, and paper 4 adds an economic dimension that most of the literature ignores, yet each remains bound to a single instrumented site, a trained operator and a specialist parameterisation. The two reviews explain why this persists: paper 5 shows that forecast–crop-model coupling is still practised as desktop modelling, and paper 1 identifies data scarcity, restricted data sharing and absent uncertainty quantification as the standing constraints. What none of the five provides is a scheduling method that survives the transition from a research site to an ordinary field, where soil parameters are unknown, sensors are absent and the person receiving the recommendation has no interest in the model behind it. My assessment is that the missing element is not a better algorithm but a hosted layer that computes a physically grounded water balance from freely available forecast data, corrects it with learning as observations accumulate, and returns a single instruction with an honest indication of how far ahead it can be trusted.

---

*Phase-I: planning and documentation.*
