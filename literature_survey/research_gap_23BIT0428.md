# Research Gap Analysis — Papers 11 to 15

**Student:** Krishna Agrawal
**Register Number:** 23BIT0428
**Project:** Cloud-Based Smart Irrigation Recommendation using Weather Intelligence
**Course:** BITE412L — Cloud Computing | **Instructor:** Dr. Priya V
**Thematic focus:** Soil-moisture prediction, evapotranspiration estimation and crop water requirement modelling

> This analysis reflects my own reading of the five papers assigned to me. Research
> gaps are not reproduced from the source papers.

---

## Paper 11 — Wang, Shi, Hu, Hu, Song & Wang (2024), *Hydrology and Earth System Sciences*

**Citation:** Y. Wang, L. Shi, Y. Hu, X. Hu, W. Song, and L. Wang, "A comprehensive study of deep learning for soil moisture prediction," *Hydrology and Earth System Sciences*, vol. 28, pp. 917–943, Feb. 2024. DOI: 10.5194/hess-28-917-2024

| Aspect | Assessment |
|---|---|
| **Existing method** | Systematic comparison of ten deep network structures for soil-moisture prediction — three basic feature extractors and seven hybrids, six of the latter applied to this task for the first time — evaluated across soil textures and depths, with SHAP attribution and t-SNE embedding used to interpret model behaviour. |
| **Advantages** | The most controlled architectural comparison currently available in this area. It establishes that LSTM's temporal modelling suits the task, quantifies the additional gain from feature attention and adversarial training, and explains those gains rather than merely reporting them. In-situ observations from thirty International Soil Moisture Network sites give genuine textural and depth diversity. Computational cost is reported alongside accuracy, which most comparison papers omit. |
| **Limitations** | The framing is hydrological, so the analysis terminates at prediction and never reaches a management action. The larger hybrid structures carry heavy computational cost. Evaluation is site-based rather than farm-based, and the sites are instrumented research locations, not working fields. |
| **Research gap** | The paper produces skilful soil-moisture forecasts and reusable design principles, but provides no transformation from a predicted moisture trajectory into an irrigation depth and timing — which is the only output a cultivator can act on. |
| **Possible improvement** | Append a decision layer that converts the predicted trajectory into an intervention: given a forecast crossing of the crop's allowable depletion threshold, compute the volume required to restore the root zone to field capacity, and schedule it before the crossing rather than after. Use the architectural findings as a cost filter, selecting the lightest structure whose accuracy loss is agronomically immaterial rather than the most accurate structure available. |

---

## Paper 12 — Li, Zhang, Li & Zhu (2024), *Water* (MDPI)

**Citation:** X. Li, Z. Zhang, Q. Li, and J. Zhu, "Enhancing soil moisture forecasting accuracy with REDF-LSTM: Integrating residual en-decoding and feature attention mechanisms," *Water*, vol. 16, no. 10, art. 1376, May 2024. DOI: 10.3390/w16101376

| Aspect | Assessment |
|---|---|
| **Existing method** | REDF-LSTM, combining residual learning encoder–decoder LSTM layers with a feedforward attention mechanism — reported as the first pairing of these two components for soil-moisture prediction. Inputs are multivariate: land-surface features, atmospheric conditions and static environmental variables, with soil moisture modelled at 10, 25, 50 and 100 cm. |
| **Advantages** | Reported average improvement of approximately 13% in R² over conventional LSTM, with corresponding gains in RMSE and bias. The attention mechanism localises which drivers dominate a given prediction, supplying interpretability without a separate explanation stage. Multi-depth modelling is agronomically appropriate, since root water uptake is not confined to the surface layer. |
| **Limitations** | Computational cost is roughly an order of magnitude above a plain LSTM. The evaluation is entirely offline: no inference latency, no serving cost, no deployment. Accuracy is reported on curated reanalysis-style inputs rather than on the incomplete, noisy feature sets a real deployment would face. |
| **Research gap** | A 13% accuracy gain purchased at ten times the compute is not self-evidently worthwhile, and the paper never tests it under the cost and latency budget of a farm-scale service. |
| **Possible improvement** | Conduct an explicit accuracy-per-unit-cost evaluation across candidate architectures on identical inputs, and restrict the feature set to variables obtainable free from a public forecast API. If a lighter model on freely available features reaches within a small margin of REDF-LSTM, that model is the correct engineering choice regardless of which one wins the leaderboard. |

---

## Paper 13 — Wang, Corzo, Lü, Zhou, Mao, Zhu, Duarte, Liu & Su (2024), *Agricultural Water Management*

**Citation:** X. Wang, G. Corzo, H. Lü, S. Zhou, K. Mao, Y. Zhu, S. Duarte, M. Liu, and J. Su, "Sub-seasonal soil moisture anomaly forecasting using combinations of deep learning, based on the reanalysis soil moisture records," *Agricultural Water Management*, vol. 295, art. 108772, Apr. 2024.

| Aspect | Assessment |
|---|---|
| **Existing method** | Combination of multiple deep-learning modules — a hybrid model and a committee-machine framework — with noise-assisted series decomposition, applied to sub-seasonal soil-moisture anomaly and drought-index hindcasting over the Huai River basin using long-term ERA5-Land reanalysis records. |
| **Advantages** | Forecast skill does not deteriorate as lead time lengthens, which is unusual and directly useful for planning horizons beyond a few days. Series decomposition measurably strengthens the committee machine. Exploiting soil-moisture memory is a physically motivated choice rather than an arbitrary architectural one, and the long reanalysis record permits robust validation. |
| **Limitations** | Basin-scale operation on reanalysis data rather than field measurement; the spatial resolution is far coarser than a single holding. Outputs are drought indices, not irrigation quantities. Regionally specific to one basin, with transferability untested. |
| **Research gap** | Genuine sub-seasonal predictive skill exists but is never translated downward to field-level irrigation advice, so a real planning-horizon advantage goes unused by the people who would benefit from it. |
| **Possible improvement** | A two-horizon design: short-range forecast data for the immediate irrigate-or-wait decision, and sub-seasonal anomaly signals of this kind for a seasonal water-budget outlook presented separately on the dashboard. Downscaling from basin to field can be handled by bias-correcting the coarse anomaly against whatever local observation is available, rather than attempting full spatial disaggregation. |

---

## Paper 14 — Katimbo et al. (2023), *Smart Agricultural Technology*

**Citation:** A. Katimbo, D. R. Rudnick, J. Zhang, Y. Ge, K. C. DeJonge, T. E. Franz, Y. Shi, W. Liang, X. Qiao, D. M. Heeren, I. Kabenge, H. N. Nakabuye, and J. Duan, "Evaluation of artificial intelligence algorithms with sensor data assimilation in estimating crop evapotranspiration and crop water stress index for irrigation water management," *Smart Agricultural Technology*, vol. 4, art. 100176, Aug. 2023. DOI: 10.1016/j.atech.2023.100176

| Aspect | Assessment |
|---|---|
| **Existing method** | Evaluation of several artificial intelligence algorithms combined with sensor data assimilation to estimate crop evapotranspiration and the crop water stress index for irrigation water management, benchmarked against established estimation practice. |
| **Advantages** | Estimates are tied to management variables rather than stopping at a physical quantity: crop evapotranspiration and the stress index are both directly interpretable as irrigation triggers. Data assimilation improves estimate quality over standalone modelling. The multi-algorithm comparison prevents a single-method result from being over-generalised. |
| **Limitations** | Dependence on canopy-temperature instrumentation, typically infrared thermometry, which few smallholdings possess. Site-specific calibration is required. Sensor faults propagate directly into the estimate, and the paper does not specify a degradation path when instrumentation fails. |
| **Research gap** | The quality of the method is gated on expensive sensing, and no fallback is defined for fields with no sensors at all — which describes most of the intended user base for a smart irrigation service. |
| **Possible improvement** | A tiered estimator: where canopy sensing exists, assimilate it as the paper describes; where it does not, reconstruct reference evapotranspiration from forecast temperature, humidity, wind and radiation using the FAO-56 formulation and apply crop coefficients by growth stage. The service then degrades in accuracy rather than failing outright, and sensor investment becomes an upgrade path instead of a precondition. |

---

## Paper 15 — Mokhtar et al. (2023), *Water Resources Management*

**Citation:** A. Mokhtar, N. Al-Ansari, W. El-Ssawy, R. Graf, P. Aghelpour, H. He, S. M. Hafez, and M. Abuarab, "Prediction of irrigation water requirements for green beans-based machine learning algorithm models in arid region," *Water Resources Management*, vol. 37, pp. 1557–1580, 2023. DOI: 10.1007/s11269-023-03443-x

| Aspect | Assessment |
|---|---|
| **Existing method** | Machine-learning models trained to predict irrigation water requirement for green beans under arid conditions, with several algorithm families benchmarked against each other on field experimental data. |
| **Advantages** | The target variable is the one a farmer must actually decide — the water requirement itself — rather than an intermediate physical quantity requiring further conversion. Validation rests on field experiment rather than simulation, which is a stronger evidential basis. The arid-region setting is directly relevant to water-scarce Indian districts. |
| **Limitations** | One crop, one agro-climatic zone, and a limited sample size. No forecast input, so the model cannot anticipate rainfall and will recommend irrigation on the eve of a storm. The model is static, with no retraining, versioning or drift-monitoring path defined. |
| **Research gap** | Crop- and region-specific models of this kind do not transfer, and no mechanism exists by which such a model is retrained and re-served for other crops or districts at scale. |
| **Possible improvement** | Treat the crop-specific model as a configurable artefact rather than a fixed result: a common feature schema, per-crop model versions stored and served from a managed registry, and scheduled retraining as new season data arrives. Adding forecast rainfall as an input feature would additionally remove the most damaging failure mode, which is recommending water immediately before it falls free. |

---

## Consolidated Gap Summary — Krishna Agrawal (23BIT0428)

My five papers are all, in different ways, about prediction quality, and taken together they show that prediction quality is no longer the binding constraint. Paper 11 compares ten architectures rigorously and paper 12 improves on the strongest of them by a further thirteen per cent; paper 13 demonstrates forecast skill that survives extended lead times; paper 14 converts physical estimates into management-relevant indices; paper 15 predicts the water requirement itself against field experimental data. The models work. What fails is everything around them. Papers 11 and 13 stop before the decision, producing moisture trajectories and drought indices that no cultivator can act on directly. Papers 12 and 14 achieve their accuracy through resources — an order of magnitude more compute, or canopy-temperature instrumentation — that the intended beneficiary does not have. Paper 15 predicts the right quantity but for one crop in one zone, with no rainfall foresight and no route to being retrained or reused elsewhere. The consistent gap I see is the absence of an operational pathway: from prediction to an irrigation depth and time, from research-grade inputs to freely available forecast features, and from a fixed model artefact to a versioned model that is retrained and served as conditions change. My view is that the project's contribution on the modelling side should be judged not by whether it beats these papers on accuracy — it will not — but by whether it delivers comparable decisions from inputs that cost nothing and degrade gracefully when sensing is absent.

---

*Phase-I: planning and documentation.*
