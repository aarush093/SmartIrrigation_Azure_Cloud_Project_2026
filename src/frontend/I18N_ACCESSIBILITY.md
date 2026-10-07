# Multilingual & Zero-Literacy Support Plan

Owner: Nayan Jaggi (23BIT0390) — branch `feature/student1`
Module: Farmer Advisory Dashboard + voice-playback preview

## Why this matters

The project's core delivery channel is an outbound voice call, built so a farmer
needs no literacy and no smartphone. The frontend must respect that: the
dashboard is an officer tool, but any farmer-facing string it previews must be
playable as speech in the farmer's language, not just readable on screen.

## Language scope

- Primary: Hindi (voice + on-screen officer labels).
- Secondary: English (officer dashboard default).
- [PERSONALIZE] Add one regional language for the pilot district once the pilot
  location is confirmed.

Language resources live in `src/frontend/locales/<lang>.json` as flat key/value
maps. No string is hardcoded in components.

## Voice-safe string rules

Every farmer-facing string previewed in the dashboard follows the same rules the
voice script uses:

- Clock times are written as words, never digits (e.g. "six in the morning",
  not "6:00"). This keeps the text-to-speech output natural and unambiguous.
- Quantities are spoken in rounded, everyday terms (e.g. "about twenty minutes"),
  not decimals.
- No abbreviations or units that do not read aloud cleanly.

A small lint check (`scripts/check-voice-strings`) flags any farmer-facing key
that contains a digit so it is caught before it reaches the voice channel.

## Accessibility (officer dashboard)

- All interactive elements are keyboard reachable and have visible focus states.
- Colour is never the sole carrier of meaning — the rain-skip flag and advisory
  status also use an icon and a text label.
- Minimum contrast ratio 4.5:1 for body text (WCAG AA).
- The PWA works offline for the last-loaded farmer list, so officers in
  low-connectivity villages can still read the most recent advisory.

## Open items

- [PERSONALIZE] Record the Hindi text-to-speech voice sample via Azure Speech
  Service and link it here.
- [PERSONALIZE] Confirm the pilot regional language and add its locale file.
