# Canvas Grading Automation

![tests](https://github.com/yanyana117/canvas-grading-automation/actions/workflows/tests.yml/badge.svg)

A small toolkit that automates a repetitive teaching workflow by integrating the **Canvas LMS REST API** and the **GitHub REST API**. It replaces hours of manual clicking with deterministic, reviewable scripts: it discovers submissions, computes deadline based late penalties, cross checks data sources to catch inconsistencies, and writes grades back to Canvas.

Built and used in a real Teaching Assistant role for a 90 student course, cutting grading turnaround from about 3 hours to under 5 minutes per assignment.

## Why it is built this way

Grading touches real student records, so the design is deliberately cautious:

- **Secrets only from the environment.** No token or course id is hardcoded. Configuration lives in environment variables (see `.env.example`).
- **Read only by default where it matters.** The GitHub client verifies the token carries no write capable scope and refuses to run otherwise, so it can never modify a student repository.
- **Preview before any write.** The quiz grader runs in `DRY_RUN` mode by default. You inspect every computed score before a single grade is uploaded.
- **Upload is not publish.** Uploading a grade to Canvas does not reveal it to students. Posting stays a manual step.
- **Tested grading logic.** The penalty brackets and lab-release detection are covered by unit tests (`pytest`) and run in CI on every push.
- **No student data in the repository.** Real rosters, grades, and reports are gitignored. Only a synthetic sample roster is included.

## Components

| File | What it does |
| --- | --- |
| `config.py` | Loads all settings from environment variables and fails fast when one is missing. |
| `canvas_client.py` | Authenticated Canvas session plus Link header pagination. |
| `github_client.py` | GitHub session with a read only scope guard and rate limit aware retry. |
| `find_missing_submissions.py` | Cross checks assignment submissions against quiz submissions and lists who is missing one. |
| `grade_quiz.py` | Scores a multiple choice quiz, applies a tiered late penalty, and uploads grades (dry run by default). |
| `fetch_github_late_times.py` | Reads each student's GitHub release publish time, selects the correct lab release while ignoring stray version numbers, and computes the late bracket. |

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env      # then edit .env with your own values
```

Use a Canvas token scoped to your TA permissions and a **read only** GitHub token.

## Usage

```bash
# Who submitted the assignment but not the quiz
python find_missing_submissions.py

# Preview quiz scores (no upload)
python grade_quiz.py

# Upload after you have checked the preview
DRY_RUN=0 python grade_quiz.py

# Compute lab late status from GitHub releases
python fetch_github_late_times.py
```

### Example dry-run output

`grade_quiz.py` previews every computed score before anything is written. A run looks like:

```text
$ python grade_quiz.py
DRY RUN — no grades will be uploaded. Set DRY_RUN=0 to write.
Deadline: 2026-04-06 06:59 UTC

  Sample Student One     12/12   on time
  Sample Student Two     11/12   -10%  (submitted 9.4h late)  -> 9.90
  Sample Student Three    0/12   missing quiz submission

3 students processed, 0 uploaded (dry run).
```

Re-running with `DRY_RUN=0` uploads the same scores to Canvas. Uploading does
not reveal grades to students; posting stays a manual step in Canvas.

## Notes

This is a portfolio version with all institutional identifiers and student data removed. The included `sample_data/roster.example.csv` is fictional. Bring your own credentials and course ids through `.env`.
