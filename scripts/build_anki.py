#!/usr/bin/env python3
"""Render public/anki/index.html from public/anki_data.json.

Produces a static, dependency-free calendar heatmap as inline SVG. The previous
version of this page shipped a ~4.6 MB Plotly bundle per request; this one is
~100 KB of markup with no client-side JavaScript at all.
"""

import datetime as dt
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "public" / "anki_data.json"
OUT = ROOT / "public" / "anki" / "index.html"

# Known bad readings from the raw AnkiConnect history.
FIXUPS = {"2024-10-17": 196}

CELL = 11
GAP = 3
STEP = CELL + GAP
LABEL_W = 26
MONTH_H = 15
YEAR_H = 30
GRID_H = 7 * STEP

EMPTY = "#e3ddd0"
# Light -> dark, matching the original "anki blues" ramp.
LEVELS = ["#cfe6ff", "#93c0ff", "#4b8bf5", "#1450d8", "#03308f"]

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def load_counts():
    raw = json.loads(DATA.read_text())
    counts = {}
    for date, value in raw:
        counts[date] = FIXUPS.get(date, value)
    return counts


def thresholds(values):
    """Quantile cut points, so a handful of 300-card days don't flatten the rest."""
    ordered = sorted(v for v in values if v > 0)
    if not ordered:
        return [1, 2, 3, 4]

    def q(p):
        return ordered[min(len(ordered) - 1, int(p * len(ordered)))]

    cuts = [q(0.25), q(0.50), q(0.75), q(0.90)]
    # Keep the ramp strictly increasing even on small / lumpy datasets.
    out = []
    for c in cuts:
        floor = out[-1] + 1 if out else 1
        out.append(max(c, floor))
    return out


def level(count, cuts):
    if count <= 0:
        return -1
    for i, cut in enumerate(cuts):
        if count <= cut:
            return i
    return len(cuts)


def week_index(day, year_start):
    """Column for a date, where columns start on Sunday."""
    offset = (year_start.weekday() + 1) % 7  # weekday of Jan 1, Sunday=0
    return (day.timetuple().tm_yday - 1 + offset) // 7


def year_svg(year, counts, cuts, today):
    start = dt.date(year, 1, 1)
    end = min(dt.date(year, 12, 31), today)
    weeks = week_index(dt.date(year, 12, 31), start) + 1
    width = LABEL_W + weeks * STEP
    height = MONTH_H + GRID_H

    parts = []

    # Month labels, positioned at the column holding the 1st of each month.
    for m in range(12):
        first = dt.date(year, m + 1, 1)
        x = LABEL_W + week_index(first, start) * STEP
        parts.append(
            f'<text class="mon" x="{x}" y="{MONTH_H - 4}">{MONTHS[m]}</text>'
        )

    # Weekday labels (Mon / Wed / Fri only, like GitHub).
    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        y = MONTH_H + row * STEP + CELL - 1
        parts.append(f'<text class="dow" x="0" y="{y}">{name}</text>')

    day = start
    while day <= end:
        col = week_index(day, start)
        row = (day.weekday() + 1) % 7
        x = LABEL_W + col * STEP
        y = MONTH_H + row * STEP
        iso = day.isoformat()
        count = counts.get(iso, 0)
        lv = level(count, cuts)
        fill = EMPTY if lv < 0 else LEVELS[lv]
        label = f"{iso}: {count} review{'' if count == 1 else 's'}"
        # <title> alone is not enough: Safari does not render tooltips for it.
        # data-t drives the JS tooltip; <title> stays for screen readers.
        parts.append(
            f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" '
            f'fill="{fill}" data-t="{label}"><title>{label}</title></rect>'
        )
        day += dt.timedelta(days=1)

    return (
        f'<div class="year">'
        f"<h2>{year}</h2>"
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'role="img" aria-label="Anki reviews in {year}">{"".join(parts)}</svg>'
        f"</div>"
    )


def legend():
    swatches = "".join(
        f'<span class="sw" style="background:{c}"></span>'
        for c in [EMPTY] + LEVELS
    )
    return f'<p class="legend">Less {swatches} More</p>'


def build():
    counts = load_counts()
    if not counts:
        raise SystemExit("anki_data.json is empty; refusing to build")

    cuts = thresholds(counts.values())
    today = dt.date.today()
    years = sorted({int(d[:4]) for d in counts}, reverse=True)

    body = "\n".join(year_svg(y, counts, cuts, today) for y in years)

    page = f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="icon" href="/favicon.png" type="image/png">
    <link rel="stylesheet" href="/css/main.css">
    <style>
      .year {{ margin: 0 0 1.75em; }}
      .year h2 {{ font-size: 20px; font-weight: bold; margin: 0 0 0.35em; }}
      .year svg {{ max-width: 100%; height: auto; display: block; }}
      .year text.mon, .year text.dow {{ font-size: 10px; fill: var(--muted); }}
      .year rect {{ cursor: default; }}
      .legend {{ font-size: 14px; color: var(--muted); }}
      .sw {{ display: inline-block; width: 11px; height: 11px; border-radius: 2px; margin: 0 2px; vertical-align: -1px; }}
      #tip {{
        position: fixed; z-index: 20; display: none; pointer-events: none;
        background: #1a1a1a; color: #fff; font-size: 13px; line-height: 1.3;
        padding: 4px 8px; border-radius: 4px; white-space: nowrap;
      }}
    </style>
    <title>Anki &middot; Alisha Li</title>
  </head>
  <body class="page">
    <p class="crumb"><a href="/">Home</a> &rsaquo; Anki</p>
    <p class="lede">
      <a href="https://apps.ankiweb.net/" target="_blank">Anki</a> is a spaced
      repetition flashcard software. Below is a heatmap of my reviews.
    </p>
    {body}
    {legend()}
    <div id="tip"></div>
    <script>
      // Safari ignores SVG <title> tooltips, so draw our own.
      (function () {{
        var tip = document.getElementById('tip');
        document.addEventListener('mouseover', function (e) {{
          var t = e.target.getAttribute && e.target.getAttribute('data-t');
          if (!t) return;
          tip.textContent = t;
          tip.style.display = 'block';
        }});
        document.addEventListener('mousemove', function (e) {{
          if (tip.style.display !== 'block') return;
          var w = tip.offsetWidth;
          tip.style.left = Math.min(e.clientX + 12, window.innerWidth - w - 8) + 'px';
          tip.style.top = (e.clientY - tip.offsetHeight - 10) + 'px';
        }});
        document.addEventListener('mouseout', function (e) {{
          if (e.target.getAttribute && e.target.getAttribute('data-t')) {{
            tip.style.display = 'none';
          }}
        }});
      }})();
    </script>
  </body>
</html>
"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page)
    return OUT, len(page)


if __name__ == "__main__":
    path, size = build()
    print(f"wrote {path} ({size / 1024:.0f} KB)")
