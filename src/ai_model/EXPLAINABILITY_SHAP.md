# Explainability with SHAP

Owner: Krishna Agrawal (23BIT0428) — branch `feature/student3`
Module: AI/ML

## Purpose

Each soil-moisture forecast must be explainable, both for the review viva and so
an extension officer can trust why a given irrigation plan was produced. SHAP
(SHapley Additive exPlanations) gives a per-forecast attribution over the input
features.

## Approach

- Use a SHAP explainer suited to sequence models (DeepExplainer / Gradient
  explainer on the trained LSTM, or KernelExplainer on a wrapped predict
  function as a model-agnostic fallback).
- Compute SHAP values on a held-out sample, not the training set.
- Aggregate two ways:
  - **Global:** mean absolute SHAP per feature, to show which drivers matter most
    across all fields (expected leaders: recent soil-moisture lags, ET0, forecast
    rainfall).
  - **Local:** a per-field, per-day attribution for a specific advisory, so a
    single recommendation can be explained ("today's longer run is driven mainly
    by high ET0 and low recent moisture").

## How it surfaces in the project

- A compact feature-importance figure for the report's results section.
- A short natural-language reason attached to an advisory, derived from the top
  local SHAP contributors — kept voice-safe (plain words, no jargon) so it can be
  spoken if needed.

## Honesty note

SHAP explains the model's behaviour, not ground truth. If a feature that should
not matter dominates the attribution, that is a signal to inspect for leakage or
a preprocessing error — consistent with the project's mandatory sanity-check
discipline.

## Open items

- [PERSONALIZE] Add the global importance figure once the model is trained.
- [PERSONALIZE] Pick one worked local example for the viva walkthrough.
