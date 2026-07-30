# Frontend

**Owner:** Nayan Jaggi (23BIT0390)
**Branch:** `feature/student1`
**Status:** Phase-I — no code. Implementation begins in Phase-II.

---

## Purpose

The farmer-facing interface. This is where the recommendation produced by the
backend becomes something a cultivator can read, understand and act on.

The design constraint that shapes everything here: **the user may be on a slow
connection, an old Android device, or no connection at all.** The interface is
built for that case first and enhanced upward, not the reverse.

---

## What will be built here (Phase-II)

| Component | Description |
|---|---|
| **Field registration** | Capture the four facts the farmer must supply: crop, sowing date, field area and irrigation method. Location is captured from the device or entered manually |
| **Recommendation card** | The primary screen. Shows the decision (irrigate or wait), the depth in millimetres and litres, the plain-language justification, and the validity horizon |
| **Water balance chart** | Recharts visualisation of root-zone moisture against field capacity and the allowable depletion threshold, with forecast projection |
| **Irrigation history** | Record of past recommendations, farmer actions and volumes applied |
| **Action controls** | Accept, override with reason, log volume actually applied |
| **Offline shell** | Service worker caching the last recommendation so it remains readable with no network |
| **Language switcher** | English, Hindi and Tamil |
| **Officer view** | Aggregate view across fields for agricultural officers (role-gated) |

---

## Technology

| Item | Choice | Reason |
|---|---|---|
| Framework | React 18 with Vite | Fast build, wide familiarity, first-class PWA tooling |
| Styling | Tailwind CSS | Utility-first, small production bundle |
| Charts | Recharts | Composable React charting; adequate for time-series water balance |
| PWA | Vite PWA plugin with service worker | Offline shell and cached last recommendation |
| Hosting | Azure Static Web Apps | Global CDN, integrated authentication with Microsoft Entra ID, free tier sufficient |
| Auth | Microsoft Entra ID via Static Web Apps built-in auth | Token acquisition without a custom auth implementation |

---

## Planned structure

```
frontend/
├── README.md
├── package.json
├── vite.config.js
├── public/
│   ├── manifest.json
│   └── icons/
└── src/
    ├── main.jsx
    ├── App.jsx
    ├── components/
    │   ├── RecommendationCard.jsx
    │   ├── WaterBalanceChart.jsx
    │   ├── FieldRegistrationForm.jsx
    │   ├── IrrigationHistory.jsx
    │   └── LanguageSwitcher.jsx
    ├── pages/
    │   ├── Dashboard.jsx
    │   ├── FieldDetail.jsx
    │   └── OfficerView.jsx
    ├── services/
    │   └── api.js
    ├── hooks/
    │   └── useOfflineCache.js
    └── i18n/
        ├── en.json
        ├── hi.json
        └── ta.json
```

---

## Interface contract with the backend

The frontend consumes the recommendation object through Azure API Management. The
shape is fixed at design time so frontend and backend can be built in parallel:

```json
{
  "fieldId": "string",
  "generatedAt": "ISO-8601 timestamp",
  "decision": "IRRIGATE | WAIT",
  "depthMm": 18.0,
  "volumeLitres": 18000,
  "justification": "High evaporative demand since your last irrigation, and no rainfall forecast for four days.",
  "validUntil": "ISO-8601 timestamp",
  "confidence": "HIGH | MEDIUM | LOW",
  "modelVersion": "string"
}
```

The frontend **never** computes the recommendation. It renders what it is given.

---

## Design rules

1. **The decision must be legible without scrolling.** Irrigate or wait, and how
   much, above the fold on a small screen.
2. **The justification is not optional.** If the backend returns an empty
   justification, that is a bug, and the UI surfaces it as a degraded state rather
   than hiding it.
3. **Show the validity horizon.** Advice built on a forecast expires; the interface
   says when.
4. **No blocking spinners on the primary screen.** If the network is unavailable,
   show the cached recommendation with a clear "last updated" timestamp.
5. **Accessible defaults.** Large tap targets, high contrast, no reliance on colour
   alone to convey the decision.

---

*Phase-I: planning and documentation. No code has been written.*
