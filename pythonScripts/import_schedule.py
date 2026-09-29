"""Import an authorized ONE.UF schedule export without losing meeting data.

Accepts either a list of course objects or a list of ONE.UF response pages.
This tool never logs in to UF or stores a session cookie.
"""

import argparse
import json
import os
from pathlib import Path
import tempfile
from datetime import datetime


ROOT = Path(__file__).resolve().parent.parent
COURSES_DIR = ROOT / "courses"


def courses_from_export(payload):
    if not isinstance(payload, list):
        raise ValueError("Expected a JSON list of courses or ONE.UF response pages")

    courses = []
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("Every list item must be an object")
        if "COURSES" in item:
            if not isinstance(item["COURSES"], list):
                raise ValueError("COURSES must be a list")
            courses.extend(item["COURSES"])
        else:
            courses.append(item)
    return courses


def normalize_time(value):
    if not isinstance(value, str):
        raise ValueError("Meeting times must be strings")
    for fmt in ("%I:%M %p", "%H:%M"):
        try:
            return datetime.strptime(value.strip(), fmt).strftime("%H:%M")
        except ValueError:
            pass
    raise ValueError(f"Unrecognized meeting time: {value!r}")


def prepare_courses(payload):
    by_key = {}
    for course in courses_from_export(payload):
        if not isinstance(course, dict) or not course.get("code"):
            raise ValueError("Every course needs a code")
        if not isinstance(course.get("sections"), list):
            raise ValueError(f"{course['code']} needs a sections list")

        code = course["code"]
        course = dict(course)
        incoming_sections = course["sections"]
        course["codeWithSpace"] = course.get("codeWithSpace") or f"{code[:3]} {code[3:]}"
        key = (code, course.get("termInd", ""))
        existing = by_key.get(key)
        if existing is None:
            course["sections"] = []
            by_key[key] = course
            existing = course
        known_sections = {
            section.get("classNumber"): index
            for index, section in enumerate(existing["sections"])
        }

        for section in incoming_sections:
            if not isinstance(section, dict) or section.get("classNumber") is None:
                raise ValueError(f"{code} has a section without classNumber")
            section = dict(section)
            meetings = section.get("meetTimes") or []
            if not isinstance(meetings, list):
                raise ValueError(f"{code} section {section['classNumber']} has invalid meetTimes")
            section["meetTimes"] = []
            for meeting in meetings:
                if not isinstance(meeting, dict):
                    raise ValueError("Each meeting must be an object")
                meeting = dict(meeting)
                meeting["meetTimeBegin"] = normalize_time(meeting["meetTimeBegin"])
                meeting["meetTimeEnd"] = normalize_time(meeting["meetTimeEnd"])
                section["meetTimes"].append(meeting)
            section["courseCode"] = code
            if section["classNumber"] not in known_sections:
                existing["sections"].append(section)
                known_sections[section["classNumber"]] = len(existing["sections"]) - 1
            elif section["meetTimes"] and not existing["sections"][known_sections[section["classNumber"]]]["meetTimes"]:
                existing["sections"][known_sections[section["classNumber"]]] = section

    return sorted(by_key.values(), key=lambda course: (course["code"], course.get("name", "")))


def meeting_coverage(courses):
    in_person = [
        section
        for course in courses
        for section in course["sections"]
        if section.get("sectWeb") != "AD"
    ]
    timed = sum(bool(section["meetTimes"]) for section in in_person)
    return timed, len(in_person)


def import_export(source, year, term, minimum_coverage=1.0):
    with open(source, encoding="utf-8") as stream:
        courses = prepare_courses(json.load(stream))
    if not courses:
        raise ValueError("Export contains no courses")
    timed, total = meeting_coverage(courses)
    coverage = timed / total if total else 0
    if coverage < minimum_coverage:
        raise ValueError(
            f"Only {timed}/{total} in-person sections have meeting times "
            f"({coverage:.1%}); need at least {minimum_coverage:.1%}. "
            "Existing course files were left untouched."
        )

    COURSES_DIR.mkdir(exist_ok=True)
    destination = COURSES_DIR / f"UF_Imported_{year}_{term}_final.json"
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=COURSES_DIR, suffix=".tmp", delete=False
    ) as temporary:
        json.dump(courses, temporary, separators=(",", ":"))
        temporary_path = Path(temporary.name)
    try:
        os.replace(temporary_path, destination)
    finally:
        temporary_path.unlink(missing_ok=True)
    return destination, len(courses), timed, total


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Authorized JSON export")
    parser.add_argument("year", help="Two digit year, for example 26")
    parser.add_argument("term", choices=("spring", "summer", "fall"))
    parser.add_argument("--minimum-coverage", type=float, default=1.0)
    args = parser.parse_args()
    if not (len(args.year) == 2 and args.year.isdigit()):
        parser.error("year must be two digits")
    if not 0 < args.minimum_coverage <= 1:
        parser.error("minimum coverage must be greater than 0 and at most 1")
    try:
        destination, count, timed, total = import_export(
            args.source, args.year, args.term, args.minimum_coverage
        )
    except (OSError, ValueError, KeyError) as error:
        parser.error(str(error))
    print(f"Imported {count} courses to {destination} ({timed}/{total} in-person sections timed)")


if __name__ == "__main__":
    main()
