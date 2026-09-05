"""Render ``results/script_samples.txt`` as a page a native speaker can read.

A terminal cannot be trusted with Devanagari or Tamil: fonts fall back, glyphs
combine wrongly, and a reviewer cannot tell a data problem from a rendering one.
The samples file is written in UTF-8 for exactly that reason, and this turns it
into a page that a phone browser will render correctly and that can be handed to
someone who reads the language but not the code.

The design follows from who reads it. Every case is one card, each language block
is separated, and the English gloss sits beside its Hindi and Tamil so a reviewer
who does not know what the line is supposed to mean can see the intent before
judging the wording. Type is large because this will be read on a phone held at
arm's length, and the review questions are at the top because a reviewer asked
"is this alright?" gives a less useful answer than one asked three specific
questions.

Run with ``make script-html`` after ``make script-samples``.
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

__all__ = ["Case", "build_page", "main", "parse_samples"]

RESULTS = Path("results")

#: Language code to what a reviewer should see it called.
LANGUAGES: dict[str, tuple[str, str]] = {
    "en": ("English", "Reference. What the line is supposed to mean."),
    "hi": ("हिन्दी · Hindi", "Needs a native speaker."),
    "ta": ("தமிழ் · Tamil", "Needs a native speaker."),
}

_CASE = re.compile(r"^CASE\s+(\d+):\s*(.+)$")
_SITUATION = re.compile(r"^\s*Situation:\s*(.+)$")
_LINE = re.compile(r"^\s*\[(\w{2})\]\s*(.+)$")


@dataclass
class Case:
    """One schedule situation and the script it produces in each language."""

    number: str
    title: str
    situation: str = ""
    scripts: dict[str, str] = field(default_factory=dict)


def parse_samples(text: str) -> list[Case]:
    """Pull the cases out of the samples file.

    Args:
        text: Contents of ``results/script_samples.txt``.

    Returns:
        The cases, in file order.
    """
    cases: list[Case] = []
    for raw in text.splitlines():
        case_match = _CASE.match(raw)
        if case_match:
            cases.append(Case(number=case_match.group(1), title=case_match.group(2).strip()))
            continue
        if not cases:
            continue
        situation = _SITUATION.match(raw)
        if situation:
            cases[-1].situation = situation.group(1).strip()
            continue
        line = _LINE.match(raw)
        if line:
            cases[-1].scripts[line.group(1)] = line.group(2).strip()
    return cases


def _card(case: Case) -> str:
    """One case as a card, English first so the intent is read before the wording."""
    blocks = []
    for code, (name, note) in LANGUAGES.items():
        script = case.scripts.get(code)
        if script is None:
            continue
        blocks.append(
            f'      <div class="lang lang-{code}">\n'
            f'        <div class="lang-head"><span class="lang-name">{html.escape(name)}</span>'
            f'<span class="lang-note">{html.escape(note)}</span></div>\n'
            f'        <p class="script" lang="{code}">{html.escape(script)}</p>\n'
            f"      </div>"
        )
    situation = (
        f'      <p class="situation">{html.escape(case.situation)}</p>\n' if case.situation else ""
    )
    return (
        f'    <section class="case">\n'
        f'      <h2><span class="num">{html.escape(case.number)}</span>'
        f"{html.escape(case.title)}</h2>\n"
        f"{situation}" + "\n".join(blocks) + "\n    </section>"
    )


def build_page(cases: list[Case]) -> str:
    """Assemble the whole page.

    Args:
        cases: Parsed cases.

    Returns:
        A self-contained HTML document. No external requests: a reviewer may
        open this on a phone with no data, and a stylesheet that fails to load
        would leave the scripts unreadable.
    """
    cards = "\n".join(_card(case) for case in cases)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Farmer script samples for review</title>
<style>
  :root {{
    --bg: #f7f7f5; --card: #ffffff; --ink: #1b1b1a; --muted: #5d5d57;
    --line: #e2e0da; --accent: #1f6f3f; --warn-bg: #fff6e0; --warn-line: #e0b34a;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #16161a; --card: #1f1f24; --ink: #edece8; --muted: #a4a29a;
      --line: #33333a; --accent: #6fcf97; --warn-bg: #2e2717; --warn-line: #7a6224;
    }}
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 1.1rem 1rem 4rem;
    background: var(--bg); color: var(--ink);
    font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
    font-size: 18px; line-height: 1.65;
    max-width: 46rem; margin-inline: auto;
  }}
  h1 {{ font-size: 1.5rem; line-height: 1.3; margin: 0 0 .3rem; }}
  .sub {{ color: var(--muted); margin: 0 0 1.3rem; font-size: .95rem; }}
  .ask {{
    background: var(--warn-bg); border: 1px solid var(--warn-line);
    border-radius: 10px; padding: 1rem 1.1rem; margin-bottom: 1.6rem;
  }}
  .ask p {{ margin: 0 0 .6rem; font-weight: 600; }}
  .ask ol {{ margin: 0; padding-left: 1.3rem; }}
  .ask li {{ margin-bottom: .45rem; }}
  .case {{
    background: var(--card); border: 1px solid var(--line);
    border-radius: 12px; padding: 1rem 1.1rem 1.2rem; margin-bottom: 1.15rem;
  }}
  .case h2 {{
    font-size: 1.06rem; line-height: 1.4; margin: 0 0 .35rem;
    display: flex; gap: .6rem; align-items: baseline;
  }}
  .num {{
    flex: none; background: var(--accent); color: #fff;
    border-radius: 6px; padding: .05rem .5rem;
    font-size: .82rem; font-weight: 700;
  }}
  .situation {{
    margin: 0 0 .9rem; color: var(--muted);
    font-size: .88rem; border-left: 3px solid var(--line); padding-left: .7rem;
  }}
  .lang {{ padding: .55rem 0; border-top: 1px solid var(--line); }}
  .lang:first-of-type {{ border-top: none; }}
  .lang-head {{
    display: flex; flex-wrap: wrap; gap: .5rem; align-items: baseline;
    margin-bottom: .2rem;
  }}
  .lang-name {{ font-weight: 700; font-size: .9rem; }}
  .lang-note {{ color: var(--muted); font-size: .78rem; }}
  .script {{ margin: 0; font-size: 1.12rem; line-height: 1.75; }}
  /* The two scripts under review get the explicit stacks and a little more
     leading, because Devanagari matras and Tamil combining marks are what a
     reviewer is being asked to look at. */
  .lang-en .script {{ color: var(--muted); font-size: 1.02rem; }}
  .lang-hi .script {{
    font-family: "Noto Sans Devanagari", "Nirmala UI", "Mangal", sans-serif;
    line-height: 1.95;
  }}
  .lang-ta .script {{
    font-family: "Noto Sans Tamil", "Nirmala UI", "Latha", sans-serif;
    line-height: 1.95;
  }}
  footer {{ color: var(--muted); font-size: .85rem; margin-top: 2rem; }}
</style>
</head>
<body>
  <h1>Farmer script samples</h1>
  <p class="sub">Every line below is what a farmer <strong>hears</strong> on the
  phone. Nothing is read; there are no digits anywhere, because a non-reader
  cannot tell whether &ldquo;6:00&rdquo; means morning or evening.</p>

  <div class="ask">
    <p>Ye scripts abhi verify nahi hue hain. Padhne wale se poochhna hai:</p>
    <ol>
      <li>Kya ye natural lagta hai?</li>
      <li>Kya koi shabd galat hai?</li>
      <li>Kya ek kisan bina padhe, sirf sunkar samajh lega?</li>
    </ol>
  </div>

{cards}

  <footer>Generated from <code>results/script_samples.txt</code> by
  <code>make script-html</code>. Until a native speaker has read this, the Hindi
  and Tamil masters stay marked <code>TODO [VERIFY native speaker]</code> and the
  report says so.</footer>
</body>
</html>
"""


def main(argv: list[str] | None = None) -> int:
    """Render the samples file to HTML.

    Args:
        argv: Command line arguments, or None to read ``sys.argv``.

    Returns:
        Process exit status.
    """
    parser = argparse.ArgumentParser(description="Render the script samples as HTML.")
    parser.add_argument("--samples", type=Path, default=RESULTS / "script_samples.txt")
    parser.add_argument("--out", type=Path, default=RESULTS / "script_samples.html")
    args = parser.parse_args(argv)

    if not args.samples.exists():
        print(f"{args.samples} not found; run `make script-samples` first", file=sys.stderr)
        return 1

    cases = parse_samples(args.samples.read_text(encoding="utf-8"))
    if not cases:
        print(f"no cases found in {args.samples}", file=sys.stderr)
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(build_page(cases), encoding="utf-8")
    languages = sorted({code for case in cases for code in case.scripts})
    print(f"wrote {args.out}: {len(cases)} cases, languages {', '.join(languages)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
