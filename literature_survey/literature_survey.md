# Literature Survey — 15 Papers

**Project:** Cloud-Based Smart Irrigation Recommendation using Weather Intelligence
**Course:** BITE412L — Cloud Computing | **Instructor:** Dr. Priya V

---

## 1. Scope

Irrigation consumes the largest share of global freshwater withdrawals, and the
decision of *when* and *how much* to irrigate remains, for most cultivators, an
experience-driven judgement rather than a measured one. The fifteen studies
surveyed here were selected to trace a single line of enquiry: how far has the
research community moved from threshold-triggered watering towards forecast-aware,
data-driven irrigation recommendation, and what prevents those methods from
reaching a farmer's phone?

The survey is organised along three axes:

1. **Papers 1–5** — irrigation scheduling and decision-support systems, including
   the incorporation of quantitative weather forecasts and crop-water simulation
   into the scheduling loop.
2. **Papers 6–10** — the computing substrate: cloud and IoT platform architectures,
   distributed and privacy-preserving learning across farms, digital-twin
   modelling, and explainability of agricultural recommendations.
3. **Papers 11–15** — the predictive core: soil-moisture forecasting using deep
   learning, evapotranspiration and crop water stress estimation, and direct
   modelling of crop water requirement.

Read together, the three groups expose a consistent discontinuity. Predictive
accuracy is mature. Platform engineering is mature. Yet the two rarely meet inside
one deployable, low-cost service that a smallholder can act on, and almost none of
the surveyed systems is specified against a named managed-cloud service catalogue.

---

## 2. Paper allocation

| Student | Register Number | Papers |
|---|---|---|
| Nayan Jaggi | 23BIT0390 | 1–5 |
| Aarush Pandit | 23BIT0416 | 6–10 |
| Krishna Agrawal | 23BIT0428 | 11–15 |

---

## 3. Citations

### Papers 1–5 — Nayan Jaggi (23BIT0390)

**[1]** L. Umutoni and V. Samadi, "Application of machine learning approaches in supporting irrigation decision making: A review," *Agricultural Water Management*, vol. 294, art. 108710, Apr. 2024. DOI: [10.1016/j.agwat.2024.108710](https://doi.org/10.1016/j.agwat.2024.108710)

**[2]** G. Conde, S. M. Guzmán, and A. Athelly, "Adaptive and predictive decision support system for irrigation scheduling: An approach integrating humans in the control loop," *Computers and Electronics in Agriculture*, vol. 217, art. 108640, 2024. [Publisher record](https://www.sciencedirect.com/science/article/abs/pii/S0168169924000310)

**[3]** A. Jamal, X. Cai, X. Qiao, L. Garcia, J. Wang, A. Amori, and H. Yang, "Real-time irrigation scheduling based on weather forecasts, field observations, and human-machine interactions," *Water Resources Research*, vol. 59, no. 12, art. e2023WR035810, Dec. 2023. DOI: [10.1029/2023WR035810](https://doi.org/10.1029/2023WR035810)

**[4]** H. M. Abd El Baki, H. Fujimaki, I. Tokumoto, and T. Saito, "Optimization of irrigation scheduling using crop–water simulation, water pricing, and quantitative weather forecasts," *Frontiers in Agronomy*, vol. 6, art. 1376231, 2024. DOI: [10.3389/fagro.2024.1376231](https://doi.org/10.3389/fagro.2024.1376231)

**[5]** S. Mohamed Naziq, N. K. Sathyamoorthy, Ga. Dheebakaran, S. Pazhanivelan, and N. Vadivel, "Coupled weather and crop simulation modeling for smart irrigation planning: A review," *Water Supply*, vol. 24, no. 8, pp. 2844–2865, Aug. 2024. DOI: [10.2166/ws.2024.170](https://doi.org/10.2166/ws.2024.170)

### Papers 6–10 — Aarush Pandit (23BIT0416)

**[6]** Y. Al Mashhadany, H. R. Alsanad, M. A. Al-Askari, S. Algburi, and B. A. Taha, "Irrigation intelligence—enabling a cloud-based Internet of Things approach for enhanced water management in agriculture," *Environmental Monitoring and Assessment*, vol. 196, art. 438, May 2024. DOI: [10.1007/s10661-024-12606-1](https://doi.org/10.1007/s10661-024-12606-1)

**[7]** S. Bera, T. Dey, A. Mukherjee, and D. De, "FLAG: Federated learning for sustainable irrigation in Agriculture 5.0," *IEEE Transactions on Consumer Electronics*, vol. 70, no. 1, pp. 2303–2310, 2024. [IEEE Xplore record](https://ieeexplore.ieee.org/document/10445480/)

**[8]** P. Killeen, C. Lin, F. Li, I. Kiringa, and T. Yeap, "IoT-based smart farming architecture using federated learning: A nitrous oxide emission prediction use case," *ACM Journal on Computing and Sustainable Societies*, vol. 3, no. 2, pp. 1-38, Jun. 2025. DOI: [10.1145/3723039](https://doi.org/10.1145/3723039)

**[9]** A. Manocha, S. K. Sood, and M. Bhatia, "IoT-digital twin-inspired smart irrigation approach for optimal water utilization," *Sustainable Computing: Informatics and Systems*, vol. 41, art. 100947, 2024. DOI: [10.1016/j.suscom.2023.100947](https://doi.org/10.1016/j.suscom.2023.100947)

**[10]** R. J. Martin, R. Mittal, V. Malik, F. Jeribi, S. T. Siddiqui, M. A. Hossain, and S. L. Swapna, "XAI-powered smart agriculture framework for enhancing food productivity and sustainability," *IEEE Access*, vol. 12, pp. 168412–168427, 2024. DOI: [10.1109/ACCESS.2024.3492973](https://doi.org/10.1109/ACCESS.2024.3492973)

### Papers 11–15 — Krishna Agrawal (23BIT0428)

**[11]** Y. Wang, L. Shi, Y. Hu, X. Hu, W. Song, and L. Wang, "A comprehensive study of deep learning for soil moisture prediction," *Hydrology and Earth System Sciences*, vol. 28, pp. 917–943, Feb. 2024. DOI: [10.5194/hess-28-917-2024](https://doi.org/10.5194/hess-28-917-2024)

**[12]** X. Li, Z. Zhang, Q. Li, and J. Zhu, "Enhancing soil moisture forecasting accuracy with REDF-LSTM: Integrating residual en-decoding and feature attention mechanisms," *Water*, vol. 16, no. 10, art. 1376, May 2024. DOI: [10.3390/w16101376](https://doi.org/10.3390/w16101376)

**[13]** X. Wang, G. Corzo, H. Lü, S. Zhou, K. Mao, Y. Zhu, S. Duarte, M. Liu, and J. Su, "Sub-seasonal soil moisture anomaly forecasting using combinations of deep learning, based on the reanalysis soil moisture records," *Agricultural Water Management*, vol. 295, art. 108772, Apr. 2024. [Publisher record](https://ideas.repec.org/a/eee/agiwat/v295y2024ics0378377424001070.html)

**[14]** A. Katimbo, D. R. Rudnick, J. Zhang, Y. Ge, K. C. DeJonge, T. E. Franz, Y. Shi, W. Liang, X. Qiao, D. M. Heeren, I. Kabenge, H. N. Nakabuye, and J. Duan, "Evaluation of artificial intelligence algorithms with sensor data assimilation in estimating crop evapotranspiration and crop water stress index for irrigation water management," *Smart Agricultural Technology*, vol. 4, art. 100176, Aug. 2023. DOI: [10.1016/j.atech.2023.100176](https://doi.org/10.1016/j.atech.2023.100176)

**[15]** A. Mokhtar, N. Al-Ansari, W. El-Ssawy, R. Graf, P. Aghelpour, H. He, S. M. Hafez, and M. Abuarab, "Prediction of irrigation water requirements for green beans-based machine learning algorithm models in arid region," *Water Resources Management*, vol. 37, pp. 1557–1580, 2023. DOI: [10.1007/s11269-023-03443-x](https://doi.org/10.1007/s11269-023-03443-x)

---

## 4. Survey Table

| # | Paper | Method | Dataset | Advantages | Limitations | Research Gap |
|---|---|---|---|---|---|---|
| 1 | Umutoni & Samadi, 2024, *Agricultural Water Management* | Systematic review of 16 studies applying ML to irrigation scheduling prediction; compares input features, algorithm families and real-world applicability | No primary dataset; synthesises input variables and data sources across the 16 reviewed field-scale studies | Consolidates algorithm selection guidance; contrasts ML accuracy and water conservation against fixed and threshold-based scheduling; assesses adoption barriers at field scale | Review only, so no common benchmark; reviewed studies heterogeneous in crop, scale and instrumentation | Restricted data availability, data-sharing constraints, absent uncertainty quantification and the need for physics-informed ML — none addressed by a shared cloud data layer serving many farms |
| 2 | Conde, Guzmán & Athelly, 2024, *Computers and Electronics in Agriculture* | Control-theoretic feedback-plus-feedforward decision support with human intervention inside the control loop | Field data from a seepage-irrigation case study — soil moisture, rainfall, temperature, irrigation records — with weather forecasts | Prescriptive instructions on timing and depth; ~30% water saving potential in seepage-irrigated crops; control-oriented soil-moisture estimation reduces leaching and runoff | One irrigation method at one research site; depends on manager compliance; single-tenant, not architected for multi-farm deployment | The human-in-the-loop control logic has no cloud-native, multi-tenant realisation, so the demonstrated saving cannot be replicated across farms |
| 3 | Jamal et al., 2023, *Water Resources Research* | Real-time scheduling tool integrating simulation–optimisation, data assimilation and human–computer interaction; probabilistic forecasts drive weighted scenarios | Field observations from two study fields, assimilated soil-moisture and LAI estimates, probabilistic weather forecasts | Handles forecast uncertainty through probability-weighted scenarios; assimilation keeps state current; farmer feedback is architecturally part of the loop | Computationally demanding; assumes a trained user; demonstrated on few fields | Uncertainty-aware scheduling exists only as a research tool; no lightweight service in which the probabilistic reasoning runs remotely and the farmer receives one plain-language instruction |
| 4 | Abd El Baki et al., 2024, *Frontiers in Agronomy* | Scheduling optimisation coupling crop–water simulation with water pricing and quantitative weather forecasts | Simulation driven by meteorological forecast series and crop–water model parameters | Introduces water economics explicitly; quantifies how forecast information changes the optimal decision | Simulation only; no farmer-facing delivery; forecast-error sensitivity; specialist parameterisation | Economic optimisation of irrigation is inaccessible to smallholders because no usable interface or automated pipeline exposes it |
| 5 | Mohamed Naziq et al., 2024, *Water Supply* | Review of crop simulation models coupled with weather forecast data; classifies scheduling into ET–water balance, soil-moisture, plant-status and model-output approaches | Scopus literature corpus, 2000–2023 | Establishes FAO-56 ET–water balance as the defensible baseline; maps where forecast integration improves planning; Indian agro-climatic relevance | Review only; the crop models require calibration inputs most farms cannot supply | Forecast–crop-model coupling is described as offline desktop modelling, not re-expressed as a hosted service that ingests forecasts automatically |
| 6 | Al Mashhadany et al., 2024, *Environmental Monitoring and Assessment* | Cloud-connected IoT monitoring with a hybrid fuzzy-logic plus PID pump controller and smart cameras | Sensor streams from the authors' instrumented environment plus control-system simulation | Closes the loop from sensing to actuation; high pump efficiency; longitudinal trend analysis from continuous cloud storage | Reactive not predictive; validation leans on simulation; no forecast-driven scheduling; "cloud" is generic with no named services | Cloud-connected control without a forecast-driven ML layer, and no reference architecture mapped to a provider's storage, identity, notification and monitoring services |
| 7 | Bera et al., 2024, *IEEE Transactions on Consumer Electronics* | Federated learning over a dew–edge–cloud hierarchy with LSTM and DNN local models, gradient encryption and dew caching | Irrigation-related sensor time series for local and global training | ~99% accuracy at ~50% lower latency and energy than conventional edge–cloud; privacy by design; caching tolerates intermittent connectivity | Requires capable per-farm hardware; limited dataset; no use of public weather forecasts | Privacy-preserving distributed learning is not combined with free forecast data, so the architecture protecting farmer data declines the signal that would most improve it |
| 8 | Killeen et al., 2025, *ACM Journal on Computing and Sustainable Societies* | Privacy-aware IoT smart-farming architecture combining federated with ensemble learning; N₂O emission prediction use case | Weather, soil and N₂O emission data from the study site | ML models substituting for costly sensing lowers the capital barrier; treats privacy as a real adoption blocker; transferable architecture | Use case is emissions not irrigation; needs several farm silos; no cost model | A well-specified privacy-aware architecture never instantiated for irrigation recommendation nor bound to a commercial managed cloud |
| 9 | Manocha, Sood & Bhatia, 2024, *Sustainable Computing: Informatics and Systems* | IoT and digital-twin approach; a virtual field replica supports predictive optimisation of water utilisation | Sensor-derived field data driving the twin | What-if evaluation before water is committed; optimises water utilisation explicitly; twin retains seasonal state | Twin construction and calibration expensive in data, compute and expertise; presumes dense instrumentation | Digital twins are out of reach for smallholders; no low-cost approximation retains the predictive benefit using forecast and public soil data |
| 10 | Martin et al., 2024, *IEEE Access* | Explainable-AI smart agriculture framework applying interpretability to agricultural model outputs | Agricultural datasets for model training and explanation generation | Addresses trust, the practical obstacle to acting on a machine recommendation; explanations intelligible to non-specialists | Framework-level not deployment-level; irrigation is one application among several; explanations unvalidated with farmers | Explainability is not bound to the farmer's actual question — why today, why this depth — leaving recommendations accurate but unjustified at point of use |
| 11 | Wang, Shi et al., 2024, *Hydrology and Earth System Sciences* | Comparison of ten deep architectures (3 extractors, 7 hybrids, 6 novel to the task) with SHAP and t-SNE interpretability across textures and depths | In-situ observations from 30 International Soil Moisture Network sites | Most controlled architectural comparison available; establishes LSTM suitability; explains FA-LSTM and GAN-LSTM gains; reports compute cost alongside accuracy | Hydrological framing stops at prediction; large hybrids computationally heavy; site-based not farm-based | No transformation from a predicted moisture trajectory into an irrigation depth and timing |
| 12 | Li et al., 2024, *Water* (MDPI) | REDF-LSTM: residual encoder–decoder LSTM with feedforward attention; first pairing of these components for soil moisture | Multivariate land-surface, atmospheric and static environmental series; soil moisture at 10/25/50/100 cm | ~13% R² improvement over conventional LSTM with RMSE and bias gains; attention localises dominant drivers; multi-depth modelling is agronomically appropriate | ~10× the compute of a plain LSTM; entirely offline evaluation; curated inputs unlike deployment conditions | Accuracy gains untested under the cost and latency budget of a farm-scale cloud service |
| 13 | Wang, Corzo et al., 2024, *Agricultural Water Management* | Hybrid deep-learning and committee-machine framework with noise-assisted series decomposition for sub-seasonal soil-moisture anomaly hindcasting | Long-term ERA5-Land reanalysis records, Huai River basin | Skill does not degrade as lead time increases; decomposition strengthens the committee machine; exploits soil-moisture memory; long record permits robust validation | Basin scale on reanalysis, far coarser than a holding; outputs drought indices not irrigation quantities; regionally specific | Sub-seasonal skill is never translated to field-level irrigation advice, so a real planning-horizon advantage goes unused |
| 14 | Katimbo et al., 2023, *Smart Agricultural Technology* | AI algorithms with sensor data assimilation estimating crop evapotranspiration and crop water stress index | Field sensor and canopy-temperature measurements | Ties ET and stress directly to management variables; assimilation improves estimate quality; multi-algorithm comparison | Requires canopy-temperature instrumentation few smallholdings have; site-specific calibration; sensor faults propagate | Method quality gated on expensive sensing, with no fallback reconstructing ET and stress from forecast and public data for sensor-free farms |
| 15 | Mokhtar et al., 2023, *Water Resources Management* | ML models predicting irrigation water requirement for green beans in an arid region, benchmarked across algorithm families | Field experimental data, green bean cultivation, arid region | Predicts the quantity the farmer must decide; validated on field experiment not simulation; arid-region relevance | One crop, one zone, limited sample; no forecast input so cannot anticipate rainfall; static model with no retraining path | Crop- and region-specific models do not transfer, and no mechanism retrains, versions and serves them at scale |

---

## 5. Observations

Three deficiencies recur and jointly define this project's opening.

1. **Predictive strength and decision usefulness are separated.** Papers 11–14
   forecast soil moisture and evapotranspiration to a high standard but stop short
   of stating an irrigation depth and time, while papers 2–4 make decisions but on
   single sites with heavy calibration.
2. **Forecast information is treated as an optional refinement.** Systems that
   protect privacy (paper 7) or scale well (papers 8, 9) do not consume the free,
   globally available forecast data that most improves the recommendation.
3. **No surveyed system specifies a deployable managed-cloud architecture** —
   storage, processing, identity, notification and monitoring bound to named
   services — which is precisely what a project graded on cloud computing must
   supply.

---

## 6. Individual gap analyses

| Student | File |
|---|---|
| Nayan Jaggi (23BIT0390) | [`research_gap_23BIT0390.md`](research_gap_23BIT0390.md) |
| Aarush Pandit (23BIT0416) | [`research_gap_23BIT0416.md`](research_gap_23BIT0416.md) |
| Krishna Agrawal (23BIT0428) | [`research_gap_23BIT0428.md`](research_gap_23BIT0428.md) |

---

*Phase-I: planning and documentation.*
