"""The browser call console: what a reviewer is actually shown.

Renders the calls the simulated telephony placed, and offers the buttons a
farmer's phone would otherwise provide: keypress 1 and 2, and the three
missed-call numbers A, B and C.

It is a single self-contained HTML file with no build step and no network
dependency, because it has to open reliably on a projector in a room with bad
wifi.
"""

from __future__ import annotations

import datetime as dt
import html
import json

from irrigation_engine.telephony import SimulatedTelephony

__all__ = ["render_console"]

_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Call console &mdash; {date}</title>
<style>
  :root {{
    --bg: #0f1115; --panel: #171a21; --line: #262b36;
    --ink: #e8eaf0; --muted: #9aa3b2;
    --water: #3b82f6; --power: #f59e0b; --ear: #10b981;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 24px; background: var(--bg); color: var(--ink);
    font: 15px/1.55 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  }}
  h1 {{ font-size: 20px; margin: 0 0 4px; }}
  .sub {{ color: var(--muted); margin-bottom: 24px; font-size: 13px; }}
  .call {{
    background: var(--panel); border: 1px solid var(--line);
    border-radius: 10px; padding: 16px 18px; margin-bottom: 14px;
  }}
  .to {{ font-size: 13px; color: var(--muted); margin-bottom: 8px; }}
  .script {{ font-size: 17px; line-height: 1.7; }}
  .row {{ display: flex; gap: 10px; flex-wrap: wrap; margin-top: 14px; }}
  button {{
    border: 1px solid var(--line); background: #1e2330; color: var(--ink);
    border-radius: 8px; padding: 10px 14px; font-size: 14px; cursor: pointer;
  }}
  button:hover {{ border-color: #3a4152; }}
  .a {{ border-left: 4px solid var(--water); }}
  .b {{ border-left: 4px solid var(--power); }}
  .c {{ border-left: 4px solid var(--ear); }}
  .log {{
    margin-top: 28px; background: var(--panel); border: 1px solid var(--line);
    border-radius: 10px; padding: 16px 18px;
  }}
  .log h2 {{ font-size: 14px; margin: 0 0 10px; color: var(--muted);
             text-transform: uppercase; letter-spacing: .06em; }}
  .entry {{ font-family: ui-monospace, "Cascadia Code", Consolas, monospace;
            font-size: 13px; padding: 4px 0; border-bottom: 1px solid var(--line); }}
  .empty {{ color: var(--muted); font-style: italic; }}
  .note {{ color: var(--muted); font-size: 12px; margin-top: 22px; max-width: 62ch; }}
</style>
</head>
<body>
<h1>Call console</h1>
<div class="sub">
  Simulated telephony for {date}. No call here is real and no number is
  provisioned. The buttons stand in for the farmer&rsquo;s phone.
</div>

{calls}

<div class="log">
  <h2>Missed calls received</h2>
  <div id="log"><div class="empty">Nothing yet. Press a button above.</div></div>
</div>

<div class="note">
  A missed call costs the farmer nothing: the platform rejects it without
  answering, so the call never connects and is never billed. The fact of the
  call is the whole message. If the handler is slow to reject, the call simply
  rings out and the event is still recorded &mdash; timing does not change what
  it means.
</div>

<script>
const CALLS = {payload};
const log = document.getElementById('log');
let first = true;

function record(label, number) {{
  if (first) {{ log.innerHTML = ''; first = false; }}
  const when = new Date().toLocaleTimeString();
  const entry = document.createElement('div');
  entry.className = 'entry';
  entry.textContent = when + '   ' + label + '   -> ' + number;
  log.prepend(entry);
}}
</script>
</body>
</html>
"""

_CALL_BLOCK = """<div class="call">
  <div class="to">to {phone}{audio}</div>
  <div class="script">{script}</div>
  <div class="row">
    <button class="a" onclick="record('missed call A: paani de diya', '{phone}')">
      A &mdash; water given
    </button>
    <button class="b" onclick="record('missed call B: bijli nahi aayi', '{phone}')">
      B &mdash; power did not come
    </button>
    <button class="c" onclick="record('missed call C: repeat today', '{phone}')">
      C &mdash; repeat today
    </button>
    <button onclick="record('keypress 1 (yes)', '{phone}')">Press 1 &mdash; yes</button>
    <button onclick="record('keypress 2 (no)', '{phone}')">Press 2 &mdash; no</button>
  </div>
</div>"""


def render_console(telephony: SimulatedTelephony, today: dt.date) -> str:
    """Render the console for the calls a simulated run placed.

    Args:
        telephony: The adapter that recorded the run.
        today: The planning date, shown in the heading.

    Returns:
        A complete, self-contained HTML document.
    """
    if telephony.placed:
        blocks = "\n".join(
            _CALL_BLOCK.format(
                phone=html.escape(call.phone),
                script=html.escape(call.text),
                audio=" &middot; audio cached" if call.audio_url else "",
            )
            for call in telephony.placed
        )
    else:
        blocks = (
            '<div class="call"><div class="empty">No calls were placed. '
            "Every field was left to WAIT, so nothing was asked of anyone."
            "</div></div>"
        )

    payload = json.dumps(
        [{"phone": call.phone, "text": call.text} for call in telephony.placed],
        ensure_ascii=False,
    )
    return _TEMPLATE.format(date=today.isoformat(), calls=blocks, payload=payload)
