> \# AI Model Plan for the Irrigation Recommendation Engine
>
> Owner: Krishna Agrawal (23BIT0428), AI and Machine Learning module
>
> \## Objective of the module
>
> Produce a per plot irrigation recommendation consisting of an irrigate or hold decision and, where irrigation is advised, an estimated water depth in millimetres.
>
> \## Inputs
>
> Forecast weather features: temperature, humidity, wind speed, rainfall probability.
> Historical weather aggregates for the same location.
> Soil attributes: texture class, field capacity, wilting point.
> Crop attributes: crop type, growth stage, coefficient values.
>
> \## Modelling approach
>
> Two stage design. A gradient boosted classifier decides whether irrigation is needed in the next scheduling window. A regressor then estimates the water depth for the positive cases only. Training this way avoids forcing the regressor to fit a large block of zero valued targets.
>
> \## Baseline for comparison
>
> A reference evapotranspiration water balance calculation serves as the non learned baseline. Any learned model must beat it on held out data before it is deployed.
>
> \## Evaluation metrics
>
> Classifier: precision, recall and F1 on the irrigate class.
> Regressor: mean absolute error in millimetres of water.
> Operational: water saved against the baseline schedule.
>
> \## Azure integration
>
> Training and experiment tracking in Azure Machine Learning. The registered model is served behind a managed online endpoint and called by Azure Functions.
>
> Status: Phase-I planning. No implementation in this phase.
