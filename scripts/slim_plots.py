#!/usr/bin/env python3
"""One-shot tool: turn raw Plotly exports into site-consistent static pages.

Two things happen to each export:
  1. An inlined plotly.js bundle (~4.3 MB) is swapped for the CDN build, which
     is shared and cached across pages.
  2. The page gets the site stylesheet, a breadcrumb, and the site background
     colour applied to both the page and the chart canvas.

Run it once per new export:  python3 scripts/slim_plots.py <src.html> <out-name>
"""

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "public" / "plots"

PLOTLY_CDN = "https://cdn.plot.ly/plotly-2.35.2.min.js"
BG = "#f0ece4"
PLOT_BG = "#f7f4ee"

HEAD_EXTRA = f"""<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" href="/favicon.png" type="image/png">
<link rel="stylesheet" href="/css/main.css">
<style>html,body{{background:{BG};}}</style>"""

# Plotly renders its own background into the SVG, so CSS alone is not enough --
# the canvas has to be relaid out once the chart exists.
RECOLOR = f"""<script>
(function () {{
  var tries = 0;
  function paint() {{
    var divs = document.querySelectorAll('.js-plotly-plot');
    if (!divs.length || !window.Plotly) {{
      if (tries++ < 60) setTimeout(paint, 100);
      return;
    }}
    divs.forEach(function (d) {{
      Plotly.relayout(d, {{paper_bgcolor: '{BG}', plot_bgcolor: '{PLOT_BG}'}});
    }});
  }}
  paint();
}})();
</script>"""


def crumb(title):
    return (
        f'<p class="crumb"><a href="/">Home</a> &rsaquo; {title}</p>'
    )


def strip_inline_plotly(src):
    """Replace an inlined plotly.js bundle with the CDN script tag."""
    pattern = re.compile(
        r'<script type="text/javascript">/\*\*\s*\n\* plotly\.js v[\d.]+.*?</script>',
        re.DOTALL,
    )
    new, n = pattern.subn(
        f'<script charset="utf-8" src="{PLOTLY_CDN}"></script>', src
    )
    return new, n


def inject_head(src):
    if "<head>" in src:
        return src.replace("<head>", "<head>\n" + HEAD_EXTRA, 1)
    if "<html>" in src:
        return src.replace("<html>", f"<html>\n<head>\n{HEAD_EXTRA}\n</head>", 1)
    return HEAD_EXTRA + src


def process(src_path, out_name, title):
    src = pathlib.Path(src_path).read_text(encoding="utf-8")
    before = len(src)

    src, swapped = strip_inline_plotly(src)
    src = inject_head(src)

    # Site background + breadcrumb on the body.
    src = re.sub(r"<body[^>]*>", '<body class="chart">', src, count=1)
    src = src.replace("<body class=\"chart\">", '<body class="chart">\n' + crumb(title), 1)

    if "</body>" in src:
        src = src.replace("</body>", RECOLOR + "\n</body>", 1)
    else:
        src += RECOLOR

    out = OUT_DIR / out_name
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(src, encoding="utf-8")
    print(
        f"{out.name}: {before / 1024 / 1024:.2f} MB -> {len(src) / 1024 / 1024:.2f} MB"
        f"{' (plotly.js -> CDN)' if swapped else ''}"
    )


PAGES = [
    ("sources/boston-food.html", "boston-food.html", "Boston food inspections"),
    ("sources/sunburst_dialogue_distribution.html", "dialogue-sunburst.html", "Dialogue distribution"),
    ("sources/interactive_dialogue_slider.html", "dialogue-slider.html", "Dialogue over time"),
    ("sources/violation_rate_chart copy.html", "violation-rate.html", "Violation rate"),
]


if __name__ == "__main__":
    if len(sys.argv) == 3:
        process(sys.argv[1], sys.argv[2], sys.argv[2].replace(".html", ""))
    else:
        for src, out, title in PAGES:
            process(ROOT / src, out, title)
