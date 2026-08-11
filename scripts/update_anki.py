#!/usr/bin/env python3
"""Pull review history from Anki, rebuild the heatmap page, and push.

Runs unattended from launchd (see launchd/com.alishali.anki-sync.plist), so it
has to be quiet when Anki simply isn't running and loud when something is
actually wrong. Everything it does goes to logs/update.log.

Replaces the old update_anki_data.py + auto_push.sh pair, which silently stopped
committing in Sep 2025 and left the deployed site stuck on 2025 data.
"""

import datetime as dt
import json
import pathlib
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "public" / "anki_data.json"
LOG = ROOT / "logs" / "update.log"
ANKI_CONNECT = "http://127.0.0.1:8765"
GIT = "/usr/bin/git"
MAX_LOG_BYTES = 1_000_000


def log(msg):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    if LOG.exists() and LOG.stat().st_size > MAX_LOG_BYTES:
        tail = LOG.read_text(errors="replace")[-MAX_LOG_BYTES // 2:]
        LOG.write_text(tail)
    line = f"{dt.datetime.now().isoformat(timespec='seconds')}  {msg}\n"
    LOG.open("a").write(line)
    print(line, end="")


def git(*args, check=True):
    return subprocess.run(
        [GIT, *args], cwd=ROOT, check=check, capture_output=True, text=True
    )


def fetch_reviews():
    payload = json.dumps(
        {"action": "getNumCardsReviewedByDay", "version": 6}
    ).encode()
    req = urllib.request.Request(
        ANKI_CONNECT, data=payload, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.load(resp)
    if result.get("error"):
        raise RuntimeError(f"AnkiConnect error: {result['error']}")
    return result["result"]


def load_existing():
    try:
        return json.loads(DATA.read_text())
    except Exception:
        return []


def main():
    try:
        fresh = fetch_reviews()
    except (urllib.error.URLError, OSError) as e:
        # Anki closed / AnkiConnect not listening. Normal, not an error.
        log(f"skip: Anki unreachable ({e})")
        return 0
    except Exception as e:
        log(f"ERROR: fetch failed: {e}")
        return 1

    existing = load_existing()

    if not fresh:
        log("skip: AnkiConnect returned no rows")
        return 0

    # Guard against a half-initialised Anki profile wiping real history.
    if len(fresh) < len(existing) * 0.9:
        log(
            f"ERROR: refusing to shrink history "
            f"({len(existing)} days on disk, {len(fresh)} from Anki)"
        )
        return 1

    if fresh == existing:
        log(f"no change ({len(fresh)} days, latest {fresh[0][0]})")
        return 0

    DATA.write_text(json.dumps(fresh))
    log(f"updated data: {len(fresh)} days, latest {fresh[0][0]} = {fresh[0][1]}")

    sys.path.insert(0, str(ROOT / "scripts"))
    import build_anki

    page, size = build_anki.build()
    log(f"rebuilt {page.relative_to(ROOT)} ({size / 1024:.0f} KB)")

    dirty = git("status", "--porcelain").stdout.splitlines()
    ours = {"public/anki_data.json", "public/anki/index.html"}
    unrelated = [l for l in dirty if l[3:].strip().strip('"') not in ours]
    if unrelated:
        log(f"stopping before commit: unrelated changes present: {unrelated}")
        return 0

    git("add", "public/anki_data.json", "public/anki/index.html")
    git("commit", "-m", f"Anki data through {fresh[0][0]}")
    push = git("push", check=False)
    if push.returncode != 0:
        log(f"ERROR: push failed: {push.stderr.strip()}")
        return 1

    log("pushed; Vercel will redeploy")
    return 0


if __name__ == "__main__":
    sys.exit(main())
