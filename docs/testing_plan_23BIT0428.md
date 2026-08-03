> \# Testing Plan for Phase-I Scope
>
> Prepared by: Krishna Agrawal (23BIT0428)
>
> \## Scope
>
> Phase-I is documentation and planning so this file defines what will be tested once implementation begins, along with the checks already applied to Phase-I artefacts.
>
> \## Checks completed in Phase-I
>
> | Item | Check applied | Result |
> |---|---|---|
> | Literature survey citations | DOI or publisher record confirmed for all 15 papers | Passed |
> | Paper distribution | 5 papers per student, no overlap | Passed |
> | Architecture diagrams | Both diagrams render and all six required elements present | Passed |
> | Repository structure | Every folder contains a README or placeholder | Passed |
>
> \## Planned test levels for later phases
>
> 1. Unit: feature engineering functions, water balance calculation, input validation
> 2. Integration: weather API ingestion through to stored recommendation
> 3. Model: accuracy thresholds enforced before any model is promoted
> 4. Security: authentication and role checks on every protected endpoint
> 5. Load: recommendation generation for a batch of plots within the scheduling window
>
> \## Tooling
>
> pytest for unit and integration tests, with Azure Monitor used to observe behaviour in the deployed environment.
>
> Status: Phase-I. Test cases to be written in Phase-II.

---
