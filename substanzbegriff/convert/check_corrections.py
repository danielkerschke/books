"""Check a corrections JSON file against the current reader HTML.

    python check_corrections.py corrections/<name>.json

Each entry: {"file": "kapitel-4.html", "old": "...", "new": "..."}.
Entries are applied in order (as render.py does). Every "old" must occur exactly
once in the file at the moment it is applied. Afterwards IDs must be unique.
"""
import json, re, sys, collections
from pathlib import Path

READER = Path(__file__).resolve().parent.parent / "reader"
entries = json.load(open(sys.argv[1], encoding="utf-8"))
texts = {}
problems = []
for i, e in enumerate(entries):
    f = e["file"]
    if f not in texts:
        texts[f] = (READER / f).read_text(encoding="utf-8")
    n = texts[f].count(e["old"])
    if n != 1:
        problems.append(f"#{i} {f}: 'old' occurs {n} times: {e['old'][:90]!r}")
        continue
    texts[f] = texts[f].replace(e["old"], e["new"])
for f, t in texts.items():
    ids = collections.Counter(re.findall(r'\bid="([^"]+)"', t))
    dup = [k for k, v in ids.items() if v > 1]
    if dup:
        problems.append(f"{f}: duplicate ids after corrections: {dup}")
    for m in re.finditer(r'href="#([^"]+)"', t):
        if m.group(1) not in ids:
            problems.append(f"{f}: link to missing anchor #{m.group(1)}")
print(f"{len(entries)} corrections checked, {len(problems)} problems")
for p in problems:
    print("  ", p)
sys.exit(1 if problems else 0)
