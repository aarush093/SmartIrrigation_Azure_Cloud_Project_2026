# Dashboard Component Inventory

Owner: Nayan Jaggi (23BIT0390) — branch `feature/student1`
Module: Farmer Advisory Dashboard (React + Vite PWA)

## Screen map

| Screen | Route | Purpose |
|---|---|---|
| Onboarding | `/` | Officer sign-in via Entra ID; short intro to the advisory system |
| Farmer registration | `/farmers/new` | Capture farmer profile, declared soil texture, crop, sowing date, power window |
| Farmer list | `/farmers` | Searchable list of registered farmers with today's advisory status |
| Advisory detail | `/farmers/:id` | Today's pump minutes mapped to the power window, rain-skip flag, spoken advisory preview |
| Field history | `/farmers/:id/history` | Root-zone depletion trend and water-given events |
| Call log | `/farmers/:id/calls` | Outbound voice-call status and missed-call responses |

## Component breakdown

- `AppShell` — top bar, navigation, offline indicator.
- `FarmerForm` — registration form with inline validation; soil-texture select
  with SoilGrids prefill shown as a non-blocking suggestion.
- `AdvisoryCard` — pump minutes, power-window band, rain-skip badge (icon + text,
  not colour alone), and a "play spoken advisory" preview button.
- `PowerWindowBar` — horizontal band showing the rationed supply window with the
  recommended pump run placed inside it.
- `DepletionChart` — line chart of root-zone depletion over time.
- `CallTimeline` — vertical timeline of call attempts and responses.
- `OfflineBanner` — shows when the PWA is serving cached data.

## State and data

- Server state via a thin fetch wrapper around the endpoints in
  `API_INTEGRATION.md`; no global store needed beyond the current farmer.
- Auth token held in memory for the session; refreshed on `401`.

## Open items

- [PERSONALIZE] Replace placeholder copy in `AppShell` and `Onboarding` with the
  final project title and team credits before the review.
- [PERSONALIZE] Wire `DepletionChart` to the `/history` endpoint once backend
  demo data is available.
