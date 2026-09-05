# Farmer-facing script masters

Every string a farmer hears lives here, one YAML file per language:
`hi.yaml`, `en.yaml`, `ta.yaml`. Seeded in M3.

Marathi, Telugu and Punjabi are generated from these masters with Azure AI
Translator later, and **every non-English master is checked by a native speaker
before the pilot** (`TODO [VERIFY native speaker]`).

## Rules, from plan Section 5.5

1. **Never** say millimetres, evapotranspiration, depletion or percent soil
   moisture. Only minutes, clock times, "paani chahiye / nahi chahiye", and rain
   in familiar words.
2. One decision per call. One number per decision.
3. Every recommendation carries a one-line reason in plain words: "kal baarish
   hai", "khet sookha hai", "bijli raat ko hai".
4. Four cases must exist in every language: irrigate with a clock time; irrigate
   "when power comes" (used when feeder reliability is below 0.6); skip for rain;
   and the next-day "did you irrigate" question.

Tamil is a master rather than a translation because the Vellore pilot farmer is
on the demonstration path. See plan Section 17.4.
