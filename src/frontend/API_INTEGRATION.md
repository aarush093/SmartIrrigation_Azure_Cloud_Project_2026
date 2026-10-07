# Frontend ↔ Backend API Integration Contract

Owner: Nayan Jaggi (23BIT0390) — branch `feature/student1`
Module: Farmer Advisory Dashboard (React PWA on Azure Static Web Apps)

## Purpose

This document fixes the REST contract between the frontend dashboard and the
backend scheduler (Azure Functions, owned by Student B). It lets the frontend
be built against stable request/response shapes while the backend evolves, and
gives the review a clear picture of how the two modules communicate.

## Base URL and auth

- Base URL: the backend Function App endpoint, injected at build time via the
  `VITE_API_BASE` environment variable (configured in Azure Static Web Apps).
- Officer-facing routes require a Microsoft Entra ID bearer token; the dashboard
  attaches it as `Authorization: Bearer <token>`.
- Farmer interaction itself happens over voice call / missed call, not the
  dashboard — the dashboard is for extension officers who register and monitor
  farmers.

## Endpoints consumed by the dashboard

### 1. Register a farmer
`POST /api/farmers`

Request:
```json
{
  "name": "string",
  "phone": "+91XXXXXXXXXX",
  "village": "string",
  "declaredSoilTexture": "sandy | loam | clay | sandy-loam | clay-loam",
  "crop": "string",
  "sowingDate": "YYYY-MM-DD",
  "powerWindowStart": "HH:mm",
  "powerWindowEnd": "HH:mm"
}
```
Note: `declaredSoilTexture` is the primary input. SoilGrids is prefill only and
returned nulls at the pilot points, so the form must never block on it.

### 2. Today's advisory for a farmer
`GET /api/farmers/{id}/advisory`

Response:
```json
{
  "farmerId": "string",
  "date": "YYYY-MM-DD",
  "pumpMinutes": 0,
  "powerWindow": { "start": "HH:mm", "end": "HH:mm" },
  "rainSkip": false,
  "rootZoneDepletionMm": 0.0,
  "spokenAdvisoryText": "string"
}
```
`spokenAdvisoryText` contains clock times written as words (no digits), matching
the farmer-facing voice script convention.

### 3. Field history
`GET /api/farmers/{id}/history?days=14`

Returns a time series of root-zone depletion and water-given events for the
field-history chart.

### 4. Call log
`GET /api/farmers/{id}/calls`

Returns outbound voice-call status and missed-call responses per farmer.

## Error handling

- `400` — validation error; show inline field errors on the registration form.
- `401` — token expired; trigger Entra ID re-authentication.
- `5xx` — show a non-blocking retry banner; the dashboard is read-mostly and
  degrades gracefully.

## Open items

- [PERSONALIZE] Confirm the final Function App route prefix with Student B before
  wiring the live calls.
- [PERSONALIZE] Add response examples captured from the SimulatedTelephony demo
  path once the backend demo data is stable.
