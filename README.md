# alishali.info

A static site. No server, no build step, no framework. Vercel serves `public/`
straight off the CDN.

```
public/                  everything that gets deployed
  index.html             home
  anki/index.html        Anki heatmap (generated, do not hand-edit)
  anki_data.json         review history (generated)
  resume/index.html      resume (hand-written)
  alisha-li-resume.pdf   the PDF the resume page links to
  plots/                 chart pages
  css/main.css           the whole stylesheet
scripts/          local tooling, never deployed
sources/          raw Plotly/htmlwidget exports (local only, gitignored)
old/              the retired Flask app, kept for reference (gitignored)
```

## Anki sync

Anki's review history reaches the site like this:

```
Anki (AnkiConnect on :8765)
  -> scripts/update_anki.py     fetch, sanity-check, write public/anki_data.json
  -> scripts/build_anki.py      render public/anki/index.html
  -> git commit + push          Vercel redeploys automatically
```

`scripts/update_anki.py` runs from a launchd agent at 09:00, 13:00, 17:00 and
21:00. Four attempts a day, because AnkiConnect only answers while Anki is
actually open. It does nothing on the runs where Anki is closed, and it refuses
to overwrite the history with a set that is more than 10% shorter than what is
already on disk.

Install or reinstall the agent (also removes the old cron entry):

```bash
./scripts/install-sync.sh
```

Useful commands:

```bash
launchctl list | grep anki-sync                 # is it loaded, what did it exit with
launchctl kickstart -k gui/$UID/com.alishali.anki-sync   # run it right now
tail -f logs/update.log                         # what it did and why
```

Every run writes a line to `logs/update.log`, including the boring ones
("skip: Anki unreachable"). Silence in that file means the agent is not running,
which is the failure the old cron + `auto_push.sh` setup had no way to show.

## Updating the resume

`/resume` is hand-written HTML, not generated from the PDF. When the PDF
changes, do both halves:

```bash
cp "path/to/new.pdf" public/alisha-li-resume.pdf
# then edit public/resume/index.html to match
```

The page is unlisted: nothing on the site links to it, same as the chart pages.
Text extraction from the PDF, if you want a starting point for the edits:

```bash
gs -q -dNOPAUSE -dBATCH -sDEVICE=txtwrite -sOutputFile=- resume.pdf
```

## Adding a chart page

Export from Plotly or R as a standalone HTML file into `sources/`, then:

```bash
python3 scripts/slim_plots.py sources/my-chart.html my-chart.html
```

That swaps any inlined `plotly.js` bundle (~4.3 MB) for the CDN build, applies
the site stylesheet and background, and adds a breadcrumb. Add the file to the
`PAGES` list in `scripts/slim_plots.py` so it gets regenerated next time.

## Local preview

```bash
python3 -m http.server 8099 --directory public
```
