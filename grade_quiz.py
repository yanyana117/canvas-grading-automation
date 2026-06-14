"""Auto-grade a Canvas multiple-choice quiz and optionally upload scores.

For each student the script counts answered multiple-choice questions,
applies a late penalty based on submission time, and writes the score back
through the Canvas API.

Safety by design:
  * DRY_RUN is on by default, so every score is previewed before anything
    is uploaded. Set DRY_RUN=0 only after you have spot checked the preview.
  * Uploading a grade does not publish it. Posting grades to students stays
    a deliberate manual step in Canvas.

All identifiers and secrets come from environment variables. See .env.example.
"""
import math
import os
from datetime import datetime, timezone

import requests

import config

# Assignment deadline in UTC. 11:59 PM PDT equals 06:59 UTC the next day.
DEADLINE = datetime.fromisoformat(
    os.environ.get("DEADLINE_UTC", "2026-04-06T06:59:00+00:00")
)

# Question ids to skip, for example short-answer questions graded by hand.
# Provide as a comma separated list in SHORT_ANSWER_IDS, e.g. "1871787,1871890".
SHORT_ANSWER_IDS = {
    int(x) for x in os.environ.get("SHORT_ANSWER_IDS", "").split(",") if x.strip()
}
MAX_SCORE = int(os.environ.get("MAX_SCORE", "12"))
DRY_RUN = os.environ.get("DRY_RUN", "1") != "0"   # preview unless explicitly off

BASE = config.CANVAS_BASE_URL
COURSE_ID = config.require("COURSE_ID", config.COURSE_ID)
ASSIGNMENT_ID = config.require("ASSIGNMENT_ID", config.ASSIGNMENT_ID)
QUIZ_ID = config.require("QUIZ_ID", config.QUIZ_ID)
TOKEN = config.require("CANVAS_TOKEN", config.CANVAS_TOKEN)

HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


def get_all_submissions():
    """Return every quiz submission including its submission history."""
    result = []
    url = f"{BASE}/courses/{COURSE_ID}/quizzes/{QUIZ_ID}/submissions"
    params = {"include[]": ["submission", "submission_history"], "per_page": 100}
    while url:
        r = requests.get(url, headers=HEADERS, params=params)
        r.raise_for_status()
        result.extend(r.json().get("quiz_submissions", []))
        url = r.links.get("next", {}).get("url")
        params = {}
    return result


def get_user_names():
    """Map user_id to display name via the assignment submissions endpoint."""
    names = {}
    url = f"{BASE}/courses/{COURSE_ID}/assignments/{ASSIGNMENT_ID}/submissions"
    params = {"include[]": ["user"], "per_page": 100}
    while url:
        r = requests.get(url, headers=HEADERS, params=params)
        r.raise_for_status()
        for sub in r.json():
            uid = sub.get("user_id")
            names[uid] = sub.get("user", {}).get("name", f"ID:{uid}")
        url = r.links.get("next", {}).get("url")
        params = {}
    return names


def late_penalty(submitted_at_str):
    """Return (multiplier, comment) for a submission timestamp."""
    if not submitted_at_str:
        return 1.0, None
    submitted_at = datetime.fromisoformat(submitted_at_str.replace("Z", "+00:00"))
    if submitted_at <= DEADLINE:
        return 1.0, None
    hours = (submitted_at - DEADLINE).total_seconds() / 3600
    label = f"{hours / 24:.1f}-day late submission"
    if hours <= 24:
        return 0.9, f"{label}: 10% penalty."
    if hours <= 48:
        return 0.8, f"{label}: 20% penalty."
    return 0.0, f"{label}: 100% penalty (not accepted after 48 hours)."


def is_answered(item):
    """True if a quiz answer item has a real response."""
    if item.get("answer_id") is not None:
        return True
    answer_values = [v for k, v in item.items() if k.startswith("answer_")]
    if answer_values:
        return any(v == "1" for v in answer_values)
    return bool(item.get("text", "").strip())


def calculate_score(submission):
    user_id = submission.get("user_id")
    submitted_at = submission.get("submitted_at")
    history = submission.get("submission_history", [])
    if not submitted_at or not history:
        return user_id, 0, None

    data = history[-1].get("submission_data", []) or []
    mc_score = sum(
        1 for item in data
        if item.get("question_id") not in SHORT_ANSWER_IDS and is_answered(item)
    )
    multiplier, comment = late_penalty(submitted_at)
    final_score = math.floor(mc_score * multiplier * 100) / 100
    return user_id, final_score, comment


def post_grade(user_id, score, comment):
    url = f"{BASE}/courses/{COURSE_ID}/assignments/{ASSIGNMENT_ID}/submissions/{user_id}"
    payload = {"submission": {"posted_grade": score}}
    if comment:
        payload["comment"] = {"text_comment": comment}
    return requests.put(url, headers=HEADERS, json=payload).status_code


def main():
    mode = "DRY RUN (preview only)" if DRY_RUN else "LIVE (scores uploaded, not posted)"
    print("=" * 56)
    print(f"  Mode: {mode}")
    print("=" * 56 + "\n")

    names = get_user_names()
    submissions = get_all_submissions()
    print(f"Found {len(submissions)} submissions.\n")

    ok = failed = 0
    for sub in submissions:
        uid = sub.get("user_id")
        who = names.get(uid, f"ID:{uid}")
        try:
            _, score, comment = calculate_score(sub)
            line = f"{who}: {score}/{MAX_SCORE}" + (f" | {comment}" if comment else "")
            if DRY_RUN:
                print(f"[preview] {line}")
                ok += 1
            else:
                status = post_grade(uid, score, comment)
                if status in (200, 201):
                    print(f"ok  {line}")
                    ok += 1
                else:
                    print(f"err {who}: upload failed, status {status}")
                    failed += 1
        except Exception as exc:
            print(f"err {who}: {exc}")
            failed += 1

    print(f"\nDone. {ok} processed, {failed} failed.")
    if not DRY_RUN:
        print("Grades uploaded but NOT posted. Post manually in Canvas when ready.")


if __name__ == "__main__":
    main()
