"""Figures for the Objective 6 results section.

Three figures, each answering one question a reviewer will ask:

  objective6_water_vs_stress.png   what does each policy cost, and what does it
                                   buy? The trade-off is the whole result, so it
                                   is drawn as a trade-off rather than as two
                                   separate bar charts.
  objective6_by_policy.png         the per-metric comparison, for the report
                                   table to point at.
  objective6_skip_threshold.png    how much the one tunable threshold in the
                                   system actually changes the outcome.

The physically unachievable reference policy is drawn hollow and labelled, so it
cannot be mistaken for something a farmer could do.

**Ponded fields are excluded**, matching the headline set in the simulation:
``params/crops.yaml`` states that a depletion-triggered balance is the wrong
model for paddy, so plotting rice alongside the rest would put a claim on a model
the project already disowns for that crop.
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RESULTS = Path("results")

LABELS = {
    "P0_calendar": "P0 calendar",
    "P1_advisory_constrained": "P1 advisory,\npower constrained",
    "P2_window": "P2 power-window\nscheduler",
    "P3_window_skip": "P3 scheduler\n+ rain skip",
    "Pref_unlimited_power": "Pref unlimited\npower (unachievable)",
}
# Label offsets in points, for the few markers that would otherwise collide.
OFFSETS = {
    "P2_window": (58, 14),
    "P3_window_skip": (-40, -28),
    "Pref_unlimited_power": (0, 20),
}
COLOURS = {
    "P0_calendar": "#94a3b8",
    "P1_advisory_constrained": "#f59e0b",
    "P2_window": "#60a5fa",
    "P3_window_skip": "#2563eb",
    "Pref_unlimited_power": "#cbd5e1",
}


def load(path: Path, *, include_ponded: bool = False) -> dict[str, dict[str, float]]:
    """Aggregate the per-field CSV into per-policy totals.

    Args:
        path: The per-field comparison CSV.
        include_ponded: Whether to include rice. False for every published
            figure; see the module docstring.

    Returns:
        Per-policy totals.
    """
    totals: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    with path.open(encoding="utf-8") as handle:
        rows = [r for r in csv.reader(handle) if r and not r[0].startswith("#")]
    header = rows[0]
    for row in rows[1:]:
        record = dict(zip(header, row, strict=False))
        if not include_ponded and record.get("ponded") == "True":
            continue
        policy = record["policy"]
        for key in ("water_mm", "stress_days", "pump_hours", "energy_kwh", "deep_percolation_mm"):
            totals[policy][key] += float(record[key])
    return totals


def skip_threshold(path: Path, out: Path) -> None:
    """How much the rain-skip confidence threshold changes the outcome.

    Drawn because the honest answer turned out to be "almost nothing", and a
    reader should be able to see that rather than take it on assertion.
    """
    with path.open(encoding="utf-8") as handle:
        rows = [r for r in csv.reader(handle) if r and not r[0].startswith("#")]
    header = rows[0]
    records = [dict(zip(header, r, strict=False)) for r in rows[1:]]
    thresholds = [float(r["min_confidence"]) for r in records]
    water = [float(r["water_mm"]) for r in records]
    stress = [int(r["stress_days"]) for r in records]
    skips = [int(r["rain_skips"]) for r in records]

    figure, axes = plt.subplots(figsize=(8, 5))
    axes.plot(thresholds, water, "o-", color=COLOURS["P3_window_skip"], label="Water applied (mm)")
    axes.set_xlabel("Rain-skip confidence threshold")
    axes.set_ylabel("Water applied, two seasons, six non-ponded fields (mm)")
    axes.set_xticks(thresholds)
    axes.grid(alpha=0.25)

    # Both axes start at zero. Autoscaled, an 87 mm spread over 5,700 mm fills
    # the panel and reads as a steep climb, which is the opposite of what the
    # data says. The flatness is the finding, so the axis must show it.
    axes.set_ylim(0, max(water) * 1.25)

    twin = axes.twinx()
    twin.plot(thresholds, skips, "s--", color="#f59e0b", label="Skip decisions issued")
    twin.set_ylabel("Skip decisions issued")
    twin.set_ylim(0, max(skips) * 1.25)

    for x, y, s in zip(thresholds, water, stress, strict=True):
        axes.annotate(
            f"{s} stress days", (x, y), textcoords="offset points",
            xytext=(0, 11), ha="center", fontsize=8,
        )

    lines = axes.get_lines() + twin.get_lines()
    axes.legend(lines, [ln.get_label() for ln in lines], loc="center left", fontsize=9)
    axes.margins(y=0.18)
    axes.set_title(
        "The skip threshold barely moves the outcome\n"
        "Nearly tripling the skips issued changes water use by under two percent",
        fontsize=11,
    )
    figure.tight_layout()
    figure.savefig(out, dpi=150)
    plt.close(figure)


def trade_off(totals: dict[str, dict[str, float]], out: Path) -> None:
    """Water applied against stress days. The result, in one picture."""
    figure, axes = plt.subplots(figsize=(8, 6))
    for policy, values in totals.items():
        unachievable = policy == "Pref_unlimited_power"
        axes.scatter(
            values["water_mm"], values["stress_days"],
            s=260, zorder=3,
            facecolor="none" if unachievable else COLOURS[policy],
            edgecolor=COLOURS[policy], linewidth=2.5,
        )
        # P2 and P3 land almost on top of each other, which is itself part of
        # the result: the rain skip changes little at this confidence
        # threshold. Their labels are offset in opposite directions so both
        # stay readable.
        offset = OFFSETS.get(policy, (0, 16))
        axes.annotate(
            LABELS[policy],
            (values["water_mm"], values["stress_days"]),
            textcoords="offset points", xytext=offset,
            ha="center", fontsize=9,
        )
    axes.set_xlabel("Water applied over two seasons, six non-ponded fields (mm)")
    axes.set_ylabel("Crop stress days (depletion above RAW)")
    axes.set_title(
        "What each policy costs and what it buys\n"
        "Lower is better on both axes. P3 is left of P0 and far below it;\n"
        "it is right of P1, and that gap is the trade.",
        fontsize=11,
    )
    # Room for the annotations, which sit outside the data range.
    axes.margins(x=0.22, y=0.14)
    axes.grid(alpha=0.25, zorder=0)
    figure.tight_layout()
    figure.savefig(out, dpi=150)
    plt.close(figure)


def per_metric(totals: dict[str, dict[str, float]], out: Path) -> None:
    """Each metric as its own panel, normalised to the P1 baseline."""
    metrics = [
        ("water_mm", "Water applied"),
        ("stress_days", "Stress days"),
        ("pump_hours", "Pump hours"),
        ("deep_percolation_mm", "Deep percolation"),
    ]
    order = ["P0_calendar", "P1_advisory_constrained", "P2_window", "P3_window_skip",
             "Pref_unlimited_power"]

    figure, axes_grid = plt.subplots(1, 4, figsize=(15, 4.5))
    for axes, (key, title) in zip(axes_grid, metrics, strict=True):
        base = totals["P1_advisory_constrained"][key] or 1.0
        values = [totals[p][key] / base * 100.0 for p in order]
        bars = axes.bar(
            range(len(order)), values,
            color=[COLOURS[p] for p in order],
            edgecolor="black", linewidth=0.6,
        )
        bars[order.index("Pref_unlimited_power")].set_hatch("///")
        axes.axhline(100, color="black", linewidth=0.8, linestyle="--")
        axes.set_title(title, fontsize=11)
        axes.set_xticks(range(len(order)))
        axes.set_xticklabels(["P0", "P1", "P2", "P3", "Pref"], fontsize=9)
        axes.set_ylabel("percent of P1 baseline" if key == "water_mm" else "")
        axes.grid(axis="y", alpha=0.25)
    figure.suptitle(
        "Relative to P1, a conventional advisory under the same power constraint "
        "(dashed line). Six non-ponded fields. Pref is hatched: unachievable.",
        fontsize=10,
    )
    figure.tight_layout()
    figure.savefig(out, dpi=150)
    plt.close(figure)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plot the Objective 6 results.")
    parser.add_argument("--results", type=Path, default=RESULTS)
    args = parser.parse_args(argv)

    totals = load(args.results / "objective6_policy_comparison.csv")
    trade_off(totals, args.results / "objective6_water_vs_stress.png")
    per_metric(totals, args.results / "objective6_by_policy.png")
    skip_threshold(
        args.results / "objective6_skip_threshold_sensitivity.csv",
        args.results / "objective6_skip_threshold.png",
    )
    print(f"wrote three figures to {args.results}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
