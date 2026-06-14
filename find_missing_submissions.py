"""Find students who submitted the assignment but are missing the quiz.

Reads two Canvas list endpoints, compares the user ids, and prints the
gap. This script is read only: it never writes anything back to Canvas.
"""
import config
from canvas_client import make_session, get_pages


def main():
    base = config.CANVAS_BASE_URL
    course = config.require("COURSE_ID", config.COURSE_ID)
    assignment = config.require("ASSIGNMENT_ID", config.ASSIGNMENT_ID)
    quiz = config.require("QUIZ_ID", config.QUIZ_ID)
    session = make_session()

    print("Fetching assignment submissions ...")
    students = {}
    url = f"{base}/courses/{course}/assignments/{assignment}/submissions"
    for page in get_pages(session, url, {"include[]": ["user"]}):
        for sub in page:
            uid = sub.get("user_id")
            students[uid] = sub.get("user", {}).get("name", f"ID:{uid}")

    print("Fetching quiz submissions ...")
    quiz_takers = set()
    url = f"{base}/courses/{course}/quizzes/{quiz}/submissions"
    for page in get_pages(session, url):
        for qs in page.get("quiz_submissions", []):
            quiz_takers.add(qs.get("user_id"))

    missing = {uid: name for uid, name in students.items()
               if uid not in quiz_takers}

    print(f"\n{len(students)} students in the assignment, "
          f"{len(quiz_takers)} took the quiz.")
    print(f"Missing the quiz ({len(missing)}):")
    for uid, name in missing.items():
        print(f"  {name} (user_id={uid})")


if __name__ == "__main__":
    main()
