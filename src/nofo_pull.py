"""Download NIH Guide text for the funding opportunities (NOFOs) behind data science projects.

Laura Ellis · https://github.com/Laura-Ellis/nih-ds-taxonomy

Picks the NOFOs that account for --coverage (default 95%) of data science records, then saves each
NOFO's page from the NIH Guide as plain text. Safe to stop and rerun: pages already saved are skipped.

Run from the repo root:
    python -u src/nofo_pull.py
    python -u src/nofo_pull.py --coverage 0.9 --delay 2
    python -u src/nofo_pull.py --reparse     # re-extract Section I from saved pages

Outputs (data/raw/ is git-ignored):
    data/raw/nofo/text/<NOFO>.txt     full page text
    data/raw/nofo/section1/<NOFO>.txt Section I (the funding opportunity description) when it can be found
    data/raw/nofo/manifest.csv        one row per NOFO: url, status, characters, data science records
"""
import argparse
import csv
import html
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUT = ROOT / "data" / "raw" / "nofo"
GUIDE = "https://grants.nih.gov/grants/guide"
UA = "Mozilla/5.0 (research use; nih-ds-taxonomy; contact via github.com/Laura-Ellis)"
FIELDS = ["nofo", "url", "status", "chars", "section1_chars", "ds_records", "fetched_at"]


class Text(HTMLParser):
    """Visible text only, one block per line."""
    SKIP = {"script", "style", "noscript", "head"}
    BLOCK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "table", "section"}

    def __init__(self):
        super().__init__()
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        elif tag in self.BLOCK:
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip:
            self.skip -= 1
        elif tag in self.BLOCK:
            self.out.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)

    def text(self):
        t = html.unescape("".join(self.out))
        t = re.sub(r"[ \t\xa0]+", " ", t)
        return re.sub(r"\n\s*\n+", "\n\n", t).strip()


def urls(nofo: str) -> list[str]:
    n = nofo.upper()
    if n.startswith("RFA"):
        return [f"{GUIDE}/rfa-files/{n}.html"]
    if n.startswith("NOT"):
        return [f"{GUIDE}/notice-files/{n}.html"]
    if n.startswith(("PA", "PAR", "PAS")):
        return [f"{GUIDE}/pa-files/{n}.html"]
    return [f"{GUIDE}/pa-files/{n}.html", f"{GUIDE}/rfa-files/{n}.html"]


S1 = re.compile(r"Section\s+I\.\s+(?:Notice\s+of\s+)?Funding\s+Opportunity\s+Description(.*?)(?=Section\s+II\.)", re.S | re.I)


def section1(t: str) -> str:
    """Longest Section I block (the first match is usually the table of contents)."""
    blocks = [m.group(1).strip() for m in S1.finditer(t)]
    return max(blocks, key=len) if blocks else ""


def reparse() -> None:
    """Re-extract Section I from saved pages without downloading anything."""
    man = pd.read_csv(OUT / "manifest.csv").drop_duplicates("nofo", keep="last")
    for i, r in man[man.status == 200].iterrows():
        f = OUT / "text" / f"{r.nofo}.txt"
        if f.exists():
            s1 = section1(f.read_text(encoding="utf-8"))
            if s1:
                (OUT / "section1" / f"{r.nofo}.txt").write_text(s1, encoding="utf-8")
            man.loc[i, "section1_chars"] = len(s1)
    man.to_csv(OUT / "manifest.csv", index=False)
    ok = man[man.status == 200]
    print(f"Section I found for {ok.section1_chars.gt(0).sum():,} of {len(ok):,} saved NOFOs ({ok.section1_chars.gt(0).mean():.0%})")


def fetch(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, ""


def pick(coverage: float) -> pd.DataFrame:
    key = ["core_project_number", "subproject_id"]
    a = pd.read_parquet(PROCESSED / "exporter_applications.parquet", columns=key + ["nofo"])
    core = pd.read_parquet(PROCESSED / "exporter_core_projects_labeled.parquet", columns=key + ["ds_label"])
    a = a.merge(core, on=key, how="left")
    ds = a[a.ds_label.eq("Y") & a.nofo.notna() & a.nofo.astype(str).str.match(r"^(PA|PAR|PAS|RFA|NOT)-")]
    c = ds.nofo.astype(str).str.upper().value_counts().rename_axis("nofo").reset_index(name="ds_records")
    c["cum"] = c.ds_records.cumsum() / c.ds_records.sum()
    keep = c[c.cum.shift(fill_value=0) < coverage]
    print(f"{len(c):,} NIH Guide NOFOs behind data science records; {len(keep):,} cover {coverage:.0%}")
    return keep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--coverage", type=float, default=0.95)
    ap.add_argument("--delay", type=float, default=1.5, help="seconds between requests")
    ap.add_argument("--limit", type=int, default=0, help="stop after this many downloads (0 = no limit)")
    ap.add_argument("--reparse", action="store_true", help="re-extract Section I from saved pages; no downloads")
    args = ap.parse_args()
    if args.reparse:
        return reparse()

    for d in ("text", "section1"):
        (OUT / d).mkdir(parents=True, exist_ok=True)
    man_path = OUT / "manifest.csv"
    done = {}
    if man_path.exists():
        done = {r["nofo"]: r for r in csv.DictReader(man_path.open(encoding="utf-8"))}
    todo = pick(args.coverage)
    new = [r for r in todo.itertuples() if r.nofo not in done or done[r.nofo]["status"] not in ("200", "404")]
    print(f"{len(todo) - len(new):,} already saved; {len(new):,} to fetch (about {len(new) * (args.delay + 0.5) / 60:.0f} min)")

    write_header = not man_path.exists()
    with man_path.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, FIELDS)
        if write_header:
            w.writeheader()
        for i, r in enumerate(new, 1):
            status, page, url = 0, "", ""
            for url in urls(r.nofo):
                for attempt in range(3):
                    try:
                        status, page = fetch(url)
                        break
                    except Exception as e:  # network hiccup: wait and retry
                        print(f"  {r.nofo}: {e}; retrying")
                        time.sleep(5 * (attempt + 1))
                if status == 200:
                    break
                time.sleep(args.delay)
            t = s1 = ""
            if status == 200:
                p = Text()
                p.feed(page)
                t = p.text()
                s1 = section1(t)
                (OUT / "text" / f"{r.nofo}.txt").write_text(t, encoding="utf-8")
                if s1:
                    (OUT / "section1" / f"{r.nofo}.txt").write_text(s1, encoding="utf-8")
            w.writerow({"nofo": r.nofo, "url": url, "status": status, "chars": len(t), "section1_chars": len(s1),
                        "ds_records": r.ds_records, "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
            fh.flush()
            if i % 50 == 0 or i == len(new):
                print(f"[{datetime.now():%H:%M:%S}] {i:,}/{len(new):,} fetched", flush=True)
            if args.limit and i >= args.limit:
                break
            time.sleep(args.delay)

    m = pd.read_csv(man_path).drop_duplicates("nofo", keep="last")
    ok = m[m.status == 200]
    print(f"Saved {len(ok):,} of {len(m):,} NOFOs; {ok.section1_chars.gt(0).mean():.0%} with Section I found; "
          f"{(m.status == 404).sum():,} not found")


if __name__ == "__main__":
    sys.exit(main())
