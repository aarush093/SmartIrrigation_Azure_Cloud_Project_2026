# Azure Functions app

Python v2 programming model. **This directory is the deployment root**, because
the v2 model discovers triggers by importing `function_app.py` from the root of
the deployed package.

## Why the layout is this way

The course mandates the top-level folder structure, so `src/azure/functions/`
cannot be moved to the repository root. Instead this directory *is* what gets
deployed, and the engine travels with it as an installed dependency rather than
as a sibling folder:

```
src/azure/functions/          <- deployment root; `func` is pointed here
├── function_app.py           <- v2 trigger discovery starts here
├── api.py                    <- the FastAPI app, mounted by AsgiFunctionApp
├── host.json
├── requirements.txt
└── local.settings.example.json
```

At publish time the engine is built as a wheel from `src/backend` and installed
into the package, so `import irrigation_engine` resolves with no path
manipulation at runtime, and the adapters from `src/azure/adapters/` are copied
alongside. The course-mandated folders are not disturbed to achieve this.

## Hosting: consumption plan

Decided in `docs/ACS_MISSED_CALL_FEASIBILITY.md`, Decision 1.

Microsoft advises against a consumption plan for incoming-call webhooks, because
a cold start can consume the 30-second ring window. **That advice targets
applications that must answer the call.** This one never answers: the success
state for a missed call is that the call is not connected. If a cold start means
the `Reject` misses the window, the call rings out on its own and the Event Grid
event still arrives and is still recorded. Nothing is lost, so the always-on
cost is not justified and would not be defensible at review.

`keep_warm` raises the share of calls that receive an instant `Reject`. It is
**comfort, not correctness**, and
`tests/test_events.py::TestIdempotency::test_timing_within_the_day_does_not_change_the_outcome`
is the test that holds that line: the same event is worth the same whether it
arrives during the ring or a minute later.

## Event Grid subscription settings

Deliberately the **opposite** of Microsoft's default advice for `IncomingCall`,
for the same reason. Microsoft suggests two delivery attempts and a one-minute
TTL because in an answer-the-call design a late event is useless. Here a late
event is still a valid field observation, and may be the only one that field
produces that day.

| Setting | Value | Why |
|---|---|---|
| Event Time to Live | hours, not 1 minute | A late reading is still a reading |
| Max delivery attempts | default, not 2 | Dropping fast would discard data to save nothing |
| Dead-letter destination | Blob Storage container | Nothing is lost silently |
| Advanced filter | `data.to.PhoneNumber.Value` in the provisioned numbers | Microsoft warns that an unfiltered subscription can produce duplicate events and infinite loops |

## Triggers

| Trigger | Type | Purpose |
|---|---|---|
| `daily_plan` | Timer, hourly | Plans and calls for farmers whose call is due this hour. Hourly rather than daily because call time depends on each farmer's own power window and on quiet hours |
| `keep_warm` | Timer, 5 minutes | Comfort only; never correctness |
| `acs_events` | HTTP POST | Event Grid webhook: subscription validation, then `IncomingCall` |
| `onboard` | HTTP POST, via FastAPI | Register a farmer and field |
| `today` | HTTP GET, via FastAPI | The day's schedule, for the PWA |
| `health` | HTTP GET, via FastAPI | Liveness |

## Running locally

```bash
cp local.settings.example.json local.settings.json    # then fill in the blanks
make func-start
```

`local.settings.json` is gitignored and must never be committed.

**Every Azure integration is behind a feature flag and defaults to off**, so the
host starts and every route answers with no ACS resource, no Speech key and no
provisioned phone number. `make demo` does not use this app at all: it drives
the same engine through the simulated telephony console.
