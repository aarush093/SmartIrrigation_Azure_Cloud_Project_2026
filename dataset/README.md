# Dataset Details

Data sources for *Cloud-Based Smart Irrigation Recommendation using Weather
Intelligence* (BITE412L, Dr. Priya V).

Six sources are used. All are public and free at the volumes this project
requires. Each was verified against its official documentation.

---

## Summary

| # | Source | Type | Licence | Role |
|---|---|---|---|---|
| D1 | Open-Meteo Forecast API | Weather forecast, 16-day hourly | CC BY 4.0 | Primary decision driver |
| D2 | Open-Meteo Historical Archive | ERA5 / ERA5-Land reanalysis | CC BY 4.0 | Model training corpus |
| D3 | NASA POWER Daily API | Agroclimatology, 300+ parameters | CC BY 4.0 | ET drivers and cross-validation |
| D4 | ISRIC SoilGrids 2.0 | Global soil properties at 250 m | CC BY 4.0 | Field capacity and wilting point |
| D5 | Crop Irrigation Scheduling (Kaggle) | Labelled tabular, 6 attributes | To be confirmed | Supervised training labels |
| D6 | International Soil Moisture Network | In-situ soil moisture | Per contributing network | Independent validation |

**No API keys are required for D1 to D4, and none is stored in this repository.**

---

## D1 — Open-Meteo Forecast API

| Field | Detail |
|---|---|
| **Dataset name** | Open-Meteo Weather Forecast API |
| **Source** | Open-Meteo, aggregating national weather services including ECMWF, NOAA GFS/HRRR, DWD ICON, Météo-France ARPEGE/AROME, JMA, KMA, KNMI and DMI |
| **URL** | <https://open-meteo.com/> · <https://open-meteo.com/en/docs> |
| **Size** | Streaming API, no bulk download. One JSON response for one field, hourly, 16 days, 12 variables is of the order of tens of kilobytes. Projected storage for 1,000 fields at daily retrieval is a few gigabytes per year before compression |
| **Number of records** | Variable. A 16-day hourly request yields 384 timestamps per variable per field |
| **Number of features** | 30+ weather models exposed. The 10 core variables used are temperature at 2 m, relative humidity, dew point, precipitation, precipitation probability, wind speed at 10 m, surface pressure, cloud cover, shortwave solar radiation and reference evapotranspiration |
| **Data type** | Structured numeric time series, JSON over HTTP GET; CSV and XLSX also available |
| **Licence** | Data under **CC BY 4.0** with attribution required; server codebase under AGPLv3. No API key, no sign-up. Free for non-commercial use up to 10,000 daily API calls |
| **Purpose of use** | The primary decision driver — forecast evaporative demand and predicted rainfall determine whether irrigation proceeds or is deferred, and over what horizon the recommendation stays valid |
| **Preprocessing required** | Timezone normalisation to IST; unit harmonisation; aggregation of hourly series to daily ET₀ and rainfall totals; forward-fill of short gaps with a configured maximum gap length; caching per grid cell to stay within the free call quota; retry with exponential backoff and fallback to the last cached forecast on failure |

---

## D2 — Open-Meteo Historical Weather API

| Field | Detail |
|---|---|
| **Dataset name** | Open-Meteo Historical Weather API (`/v1/archive`) |
| **Source** | ECMWF reanalysis served through Open-Meteo: ERA5 at 0.25° from 1940, ERA5-Land at 0.1° from 1950, ECMWF IFS at 9 km from 2017 |
| **URL** | <https://open-meteo.com/en/docs/historical-weather-api> |
| **Size** | Query-dependent. A 10-year daily series for one location across 10 variables is a few megabytes of CSV; the planned training corpus is projected in the low gigabytes |
| **Number of records** | Continuous hourly and daily records; a 10-year daily extraction yields approximately 3,650 rows per location per variable |
| **Number of features** | The same variable set as D1, permitting identical feature engineering for training and inference — a deliberate choice to prevent train/serve skew |
| **Data type** | Structured numeric time series, JSON and CSV |
| **Licence** | **CC BY 4.0** |
| **Purpose of use** | The multi-year training corpus for the soil-moisture and residual-correction models, and the archived weather sequences for the Objective 6 water-saving simulation |
| **Preprocessing required** | Batched date-range extraction rather than day-by-day calls; alignment to the same daily aggregation logic as D1; **chronological train/validation/test split by season — never a random split, which would leak future information**; outlier screening; derivation of cumulative-deficit and antecedent-rainfall features |

---

## D3 — NASA POWER Daily Agroclimatology

| Field | Detail |
|---|---|
| **Dataset name** | NASA POWER (Prediction Of Worldwide Energy Resources) Daily API, Agroclimatology (`AG`) community |
| **Source** | NASA Langley Research Center, Earth Science Division |
| **URL** | <https://power.larc.nasa.gov/> · <https://power.larc.nasa.gov/docs/services/api/temporal/daily/> |
| **Size** | Query-dependent; analysis-ready responses per point per date range |
| **Number of records** | Continuous daily records: radiation from 1984 to present, meteorology from 1981 to present |
| **Number of features** | 300+ parameters catalogued. The 8 used are T2M, T2M_MAX, T2M_MIN, T2MDEW, RH2M, WS2M, PRECTOTCORR and ALLSKY_SFC_SW_DWN — all standard FAO-56 Penman–Monteith inputs |
| **Data type** | Structured numeric time series, JSON, CSV and ASCII |
| **Licence** | **CC BY 4.0**, free and open access, no API key |
| **Purpose of use** | Independent cross-check on the ERA5-derived training features, and fallback ET driver where Open-Meteo coverage is degraded. POWER's agroclimatology parameters are formatted specifically for crop-model input |
| **Preprocessing required** | Respect the native resolution of 0.5° × 0.625° for meteorology and 1° × 1° for solar — requesting finer risks repeated identical-cell calls and rate limiting. Account for the two-to-three-month latency before climate-quality products replace near-real-time values, so **POWER is used for training and validation, not live daily inference**. Unit conversion and daily alignment with D1 and D2 |

---

## D4 — ISRIC SoilGrids 2.0

| Field | Detail |
|---|---|
| **Dataset name** | SoilGrids 2.0 (SoilGrids250m) |
| **Source** | ISRIC — World Soil Information, Wageningen |
| **URL** | <https://soilgrids.org/> · <https://www.isric.org/explore/soilgrids> · Reference: Poggio et al., *SOIL*, 7, 217–240, 2021, DOI 10.5194/soil-7-217-2021 |
| **Size** | Global raster coverage at 250 m. Project usage is point extraction per field, so stored volume is one soil profile record per field of a few hundred bytes |
| **Number of records** | Global 250 m grid. Underlying models were fitted on approximately 240,000 soil profile observations comprising over 920,000 observed soil layers |
| **Number of features** | Soil properties at six standard depth intervals (0–5, 5–15, 15–30, 30–60, 60–100, 100–200 cm): pH, soil organic carbon, bulk density, coarse fragments, sand, silt, clay, cation exchange capacity, total nitrogen, plus organic carbon density and stock. This project uses **5 features — sand, silt, clay, bulk density and organic carbon — across the 3 depth intervals covering the 0–30 cm root zone** |
| **Data type** | Geospatial raster (GeoTIFF, VRT, WCS), reduced to tabular point extractions |
| **Licence** | **CC BY 4.0** |
| **Purpose of use** | Supplies the soil texture and bulk density needed to estimate field capacity, permanent wilting point and total available water for the root zone — the parameters that convert an evapotranspiration deficit into an irrigation depth. **This is what allows the system to work on an uninstrumented field.** |
| **Preprocessing required** | Point extraction at field centroid; depth-weighted averaging across the 0–30 cm root zone; application of a published pedotransfer function to derive field capacity and wilting point from texture and bulk density; unit rescaling per SoilGrids conventions |

> **Operational note.** The ISRIC REST API has been reported as temporarily paused.
> The ingestion design must therefore support bulk raster download or WCS as a
> fallback path, and must cache the extracted profile permanently per field —
> soil properties are static, so one successful retrieval per field is sufficient
> for the life of the project.

---

## D5 — Crop Irrigation Scheduling dataset (Kaggle)

| Field | Detail |
|---|---|
| **Dataset name** | Crop Irrigation Scheduling dataset, Kaggle open agricultural repository |
| **Source** | Kaggle. Used as the training corpus in the IEEE study at <https://ieeexplore.ieee.org/document/10296736/> |
| **URL** | *To be completed — exact Kaggle dataset URL* |
| **Size** | *To be completed from the Kaggle dataset page* |
| **Number of records** | *To be completed from the Kaggle dataset page* |
| **Number of features** | **6 attributes, confirmed from the published study:** Crop Type, Crop Days, Soil Moisture, Temperature, Humidity, and Irrigation as the binary target |
| **Data type** | Tabular CSV, mixed categorical and numeric |
| **Licence** | *To be confirmed from the Kaggle licence field before use* |
| **Purpose of use** | Provides the labelled irrigate/do-not-irrigate target needed to train and benchmark the classification component, since forecast and reanalysis sources supply features but no ground-truth irrigation decision |
| **Preprocessing required** | Categorical encoding of crop type; class-balance check on the irrigation label with resampling or class weighting if skewed; feature scaling; chronological split if a time index exists, otherwise stratified k-fold; explicit schema mapping onto the platform's feature names to keep training and serving consistent |

> **Outstanding action.** Four fields remain to be completed from the Kaggle
> dataset page. They are deliberately left blank rather than estimated. If the
> licence does not permit academic use, an alternative open irrigation-labelled
> dataset will be substituted and this entry rewritten.

---

## D6 — International Soil Moisture Network

| Field | Detail |
|---|---|
| **Dataset name** | International Soil Moisture Network (ISMN) |
| **Source** | ISMN, hosted at TU Wien, aggregating in-situ soil moisture networks worldwide. Used as the in-situ validation source in Wang et al., *HESS*, 28, 917–943, 2024 |
| **URL** | <https://ismn.earth/> |
| **Size** | Network-dependent. Project usage is a small subset of stations for validation only |
| **Number of records** | Continuous in-situ time series per station. The reference study drew observations from 30 sites across differing soil textures and depths |
| **Number of features** | Volumetric soil moisture at multiple depths, with accompanying soil temperature and quality flags |
| **Data type** | Structured numeric time series with quality-control flags |
| **Licence** | Registration required; licence terms vary by contributing network and are confirmed per network before use |
| **Purpose of use** | Independent validation that the soil-moisture model, trained on reanalysis and forecast features, tracks real measured soil moisture. Without this, Objective 3 would be validated only against another model's output |
| **Preprocessing required** | Station selection by climate and texture similarity to the target region; application of quality flags with rejection of flagged observations; depth matching to the modelled root zone; temporal resampling to daily; timezone alignment |

---

## Combined preprocessing pipeline (Phase-II)

```
Raw ingestion (D1–D4)
        │
        ├─ Timezone normalisation to IST
        ├─ Unit harmonisation across sources
        ├─ Hourly → daily aggregation (ET₀ drivers, rainfall totals)
        │
Feature engineering
        │
        ├─ FAO-56 reference evapotranspiration
        ├─ Cumulative water deficit since last irrigation
        ├─ Antecedent rainfall windows (1, 3, 7 days)
        ├─ Crop coefficient by growth stage
        ├─ Field capacity and wilting point via pedotransfer function (D4)
        │
Split and train
        │
        ├─ Chronological split by season (never random)
        ├─ Train on D2 + D5, validate on held-out season
        └─ Independent validation against D6
```

---

## Attribution requirements

Because D1 to D4 are all CC BY 4.0, the deployed application and the project report
must carry attribution:

- Weather data by **Open-Meteo.com** (CC BY 4.0)
- Meteorological and solar data from the **NASA POWER Project**
- Soil property data from **ISRIC — World Soil Information, SoilGrids**

Attribution text will appear in the dashboard footer and in the report's
references section.

---

*Phase-I: planning and documentation. No data has been downloaded or processed at
this stage.*
