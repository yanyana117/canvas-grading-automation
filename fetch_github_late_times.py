"""Compute lab late status from GitHub release publish times.

For every netid in the roster this finds the student's lab repository,
selects the release that genuinely denotes the target lab (ignoring stray
version numbers), reads its publish time, and converts that into an on time
or late bracket. Writes late_times.csv next to the roster.

Read only: the GitHub token is checked to ensure it carries no write scope
before any request is made. All config comes from environment variables.
"""
import csv
import os
import re
import sys
import time
from datetime import datetime, timezone, timedelta

import config
from github_client import make_session, assert_read_only, gh_get, GITHUB_API

ROSTER = os.environ.get("ROSTER", "sample_data/roster.example.csv")
OUT = os.environ.get("LATE_OUT", "late_times.csv")
LAB_NUMBER = int(os.environ.get("LAB_NUMBER", "4"))

# Deadline in UTC. 11:59 PM PDT equals 06:59 UTC the next day.
DEADLINE_UTC = datetime.fromisoformat(
    os.environ.get("DEADLINE_UTC", "2026-05-04T06:59:00+00:00")
)
PT = timezone(timedelta(hours=-7))  # PDT


def is_strong_lab_marker(text, n):
    """True only if text genuinely denotes lab number n.

    Accepts forms such as ``lab4``, ``lab-4``, ``lab_4``, ``L4`` and a
    bare major version ``v4`` / ``4.0``. Rejects stray digits inside
    things like ``v1.0.4`` or ``v1.4`` so a patch number is never mistaken
    for the lab number.
    """
    t = text.strip().lower()
    if not t:
        return False
    if re.search(rf"lab[\s_\-]*0*{n}(\b|[^0-9]|$)", t):
        return not re.search(rf"lab[\s_\-]*0*{n}[0-9]", t)
    if re.search(rf"l{n}(\b|v|[^0-9]|$)", t):
        return True
    return bool(re.match(rf"v?\.?\s*0*{n}(\.|_|\b|$)", t))


def pick_lab_release(releases, n):
    """Pick the earliest release that strongly denotes lab n.

    Taking the earliest avoids penalizing a later fix re-publish. If none
    qualify, flag NEEDS_REVIEW with all tags for a human to adjudicate.
    """
    strong = [
        rel for rel in releases
        if is_strong_lab_marker(rel.get("tag_name") or "", n)
        or is_strong_lab_marker(rel.get("name") or "", n)
    ]
    if not strong:
        tags = "|".join((r.get("tag_name") or r.get("name") or "?") for r in releases)
        return None, "NEEDS_REVIEW:" + tags
    strong.sort(key=lambda r: r.get("published_at") or "")
    chosen = strong[0]
    note = chosen.get("tag_name") or chosen.get("name") or ""
    if len(strong) > 1:
        others = ",".join(
            (r.get("tag_name") or "?") + "@" + (r.get("published_at") or "?")
            for r in strong[1:]
        )
        note += f" (MULTI, others: {others})"
    return chosen, note


def late_bracket(hours_late):
    if hours_late <= 0:
        return "ontime"
    if hours_late <= 24:
        return "-10%"
    if hours_late <= 48:
        return "-20%"
    return "REJECTED"


def main():
    session = make_session()
    assert_read_only(session)

    rows = []
    with open(ROSTER, newline="") as f:
        for r in csv.DictReader(f):
            nid = (r.get("netid") or "").strip()
            if nid:
                rows.append((r.get("student_name", "").strip(), nid))

    out = []
    for i, (name, nid) in enumerate(rows, 1):
        repo = config.REPO_PREFIX + nid
        url = f"{GITHUB_API}/repos/{config.GITHUB_ORG}/{repo}/releases?per_page=100"
        status, data = gh_get(session, url)

        if status == 404:
            out.append([name, nid, "NO_REPO_OR_NO_ACCESS", "", "", "", ""])
        elif status == 200 and isinstance(data, list) and data:
            rel, note = pick_lab_release(data, LAB_NUMBER)
            if rel is None:
                out.append([name, nid, "NEEDS_REVIEW", "", "", str(len(data)), note])
            else:
                pub = datetime.fromisoformat(
                    (rel.get("published_at") or "").replace("Z", "+00:00")
                )
                pdt = pub.astimezone(PT).strftime("%Y-%m-%d %H:%M PDT")
                hours_late = (pub - DEADLINE_UTC).total_seconds() / 3600.0
                out.append([name, nid, pdt, f"{hours_late:.1f}",
                            late_bracket(hours_late), str(len(data)), note])
        elif status == 200:
            out.append([name, nid, "NO_RELEASES", "", "", "0", ""])
        else:
            msg = data.get("message", "") if isinstance(data, dict) else ""
            out.append([name, nid, f"ERROR_{status}", "", "", "", msg])

        print(f"[{i:2d}/{len(rows)}] {nid:<12} {out[-1][2]}")
        time.sleep(0.2)  # be polite to the API

    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["student_name", "netid", "published_at_PDT", "hours_late",
                    "late_label", "num_releases", "release_tag_or_note"])
        w.writerows(out)
    print(f"\nWrote {OUT} ({len(out)} rows)")


if __name__ == "__main__":
    main()
