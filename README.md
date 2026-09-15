# Frontend

**Owner:** Nayan Jaggi (23BIT0390)
**Branch:** `feature/student1`
**Status:** Phase-II implementation.

---

## What this is

The farmer-facing progressive web application, plus the operator onboarding
screen.

**The primary user cannot read.** That single constraint decides almost every
choice below. It is also why the PWA is not the main channel: the daily
recommendation reaches the farmer as a **voice call**, and this application
exists for demonstrations, for extension workers, and for literate family
members who want to see the same thing on a screen.

---

## The three-tile screen

| Tile | Shows | Why it is drawn that way |
|---|---|---|
| 💧 Pump | Minutes, with a start and stop time | The minutes are the largest thing on the screen, readable at arm's length in sunlight |
| ⚡ Power | The supply window as an arc on a 24-hour ring | A ring, not a bar, because a night window crosses midnight and would otherwise break into two disconnected pieces |
| 🌧️ Rain | A drop that fills in proportion to the chance of rain | Never a percentage. "80%" means little without literacy or numeracy; a four-fifths full drop says the same thing |

**Tapping any tile plays the same words the voice call speaks**, using the audio
URL `/today` returns. That is the fallback for a farmer who can work a phone but
cannot read the labels.

A SKIP shows a crossed-out drop rather than zero minutes, because "do not water
today" is a different instruction from "water for no time", and a zero would
read as a broken screen.

---

## Design rules

1. **The decision is legible without scrolling** on a small screen.
2. **No text is load-bearing.** Every value is carried by an icon, a number or a
   position. Words are a secondary aid.
3. **No percentages, no millimetres, no technical units** anywhere a farmer can
   see them. The backend enforces the same rule on the spoken scripts and has a
   test for it.
4. **No blocking spinner on the home screen.** With no network, show the cached
   recommendation and say plainly that it is older information.
5. **Large touch targets.** Calloused hands, a cracked screen, standing in a
   field.
6. **Colour is never the only signal.** Roughly one man in twelve has some
   colour blindness.

---

## Onboarding

Operator-facing, so ordinary form layout and words are fine here. About five
minutes. Every field is something establishable standing in the field with no
instrument beyond a bucket and a watch.

Two parts deserve attention:

**The soil question.** Three choices with icons and a spoken cue: sandy, loamy,
clayey. This is the **primary soil input for the whole system**. ISRIC SoilGrids
only prefills it, and has repeatedly returned nothing at all for the pilot
points. A farmer knows his own soil, and his answer describes *his plot* rather
than a 250 m grid pixel that may straddle a road, a canal and three holdings.

**The bucket test.** Visually emphasised and placed before the nameplate fields,
because it removes the largest single source of error in the running time the
farmer is eventually told. Timing a bucket needs no assumption about pump
efficiency or head; a nameplate estimate needs both.

Warnings returned by `/onboard` are shown, never swallowed. The operator is
still standing in the field and can fix the thing being warned about.

---

## Technology

React 18, Vite, Tailwind CSS, `vite-plugin-pwa`, deployed to Azure Static Web
Apps. Exactly the stack declared in the Phase-I technology stack table.

```
frontend/
├── index.html
├── package.json
├── vite.config.js          service worker and runtime caching
├── tailwind.config.js
├── public/
│   ├── manifest.json
│   └── icons/              app icons, and the missed-call card icons
└── src/
    ├── main.jsx
    ├── App.jsx
    ├── api.js              the two backend calls
    ├── i18n.js             interface labels for hi, en, ta
    ├── pages/
    │   ├── Home.jsx        the three-tile screen
    │   ├── Bucket.jsx      seven-day water balance
    │   └── Onboard.jsx     operator onboarding
    └── components/
        ├── PumpTile.jsx
        ├── PowerRing.jsx
        ├── RainDrop.jsx
        └── LanguageSwitch.jsx
```

---

## Interface contract

Fixed at design time so frontend and backend can be built in parallel. **Do not
rename a field on one side only**: the screen will silently show nothing.

`GET /today?field_id=...`

```json
{
  "field_id": "farmer-000001-f1",
  "date": "2026-09-04",
  "decision": "irrigate | skip | wait",
  "reason_code": "stress_imminent",
  "minutes": 409.4,
  "start_time": "2026-09-04T22:00:00+05:30",
  "stop_time": "2026-09-05T04:45:00+05:30",
  "window_start": "2026-09-04T22:00:00+05:30",
  "window_end": "2026-09-05T06:00:00+05:30",
  "script_text": "...",
  "audio_url": "https://.../abc123.mp3"
}
```

`start_time` is **null** when the feeder is unreliable. That is not an error: it
means no clock time can be promised, and the screen should show the power query
instead of a time, exactly as the voice call says "when the power comes".

**The frontend never computes a recommendation.** It renders what it is given.
If a number looks wrong, that is a backend question.

---

## Running locally

```bash
npm install
npm run dev
```

Set `VITE_API_BASE` if the API is not at `/api`.

---

## Still to do

- App icons at 192 and 512 pixels, and the three missed-call card icons. See
  `public/icons/README.md`, which specifies them.
- Native-speaker check of the Hindi and Tamil interface labels in `i18n.js`.
  They are marked `TODO [VERIFY native speaker]` and must not go to the pilot
  unchecked.
- The usability round: five to ten farmers or family members, per plan
  Section 12.
