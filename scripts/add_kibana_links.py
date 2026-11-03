"""Add a link to the Kibana logs to every failed case in a planemo JUnit report.

planemo writes its own JUnit XML, so the pytest hook in tests/conftest.py never sees
these tests. This walks the report instead and appends the same "Elasticsearch logs"
section to each failure, taking the window a tool's job actually ran in from the
matching --test_output_json report that planemo writes alongside the XML.

Run it after fix_junit_xml.py, which is what makes the report parseable in the first
place. Like the pytest hook, it is a no-op when KIBANA_URL is unset.
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from xml.sax.saxutils import escape, unescape

from kibana import SECTION_NAME, log_section

TESTCASE = re.compile(r"<testcase\b([^>]*)>(.*?)</testcase>", re.DOTALL)
ATTRIBUTE = re.compile(r'([\w.:-]+)="([^"]*)"')
# planemo wraps the failure details in CDATA, so the section goes in just before it ends
CDATA_END = re.compile(r"\]\]></(failure|error)>")
ELEMENT_END = re.compile(r"</(failure|error)>")


def _epoch(timestamp):
    """Parse a Galaxy API timestamp, which is UTC but carries no timezone marker."""
    if not timestamp:
        return None
    try:
        moment = datetime.fromisoformat(timestamp.rstrip("Z"))
    except ValueError:
        return None
    return moment.replace(tzinfo=timezone.utc).timestamp()


def _windows_by_test(json_path):
    """Map each test in planemo's JSON report to the window its job ran in.

    Tests that never produced a job, because the tool failed to start at all, are
    left out and fall back to the window of the whole planemo run.
    """
    try:
        with open(json_path, "r", encoding="utf-8") as handle:
            report = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Could not read job times from {json_path}: {exc}", file=sys.stderr)
        return {}

    windows = {}
    for test in report.get("tests", []):
        data = test.get("data") or {}
        job = data.get("job") or {}
        start = _epoch(job.get("create_time"))
        end = _epoch(job.get("update_time"))
        if start is None or end is None:
            continue

        job_ids = [job["id"]] if job.get("id") else []
        windows[(str(test.get("id")), str(data.get("test_index")))] = (start, end, job_ids)
    return windows


def _attributes(raw):
    return {name: unescape(value) for name, value in ATTRIBUTE.findall(raw)}


def _insert(body, section):
    """Put the section inside the failure element, keeping the rest of it untouched."""
    text = f"\n{SECTION_NAME}\n{section}\n"

    match = CDATA_END.search(body)
    if match:
        return body[: match.start()] + text + body[match.start() :]

    match = ELEMENT_END.search(body)
    if match:
        return body[: match.start()] + escape(text) + body[match.start() :]

    return body


def add_links(xml_path, json_path, run_window):
    with open(xml_path, "r", encoding="utf-8") as handle:
        original = handle.read()

    windows = _windows_by_test(json_path)
    linked = 0

    def rewrite(match):
        nonlocal linked
        raw_attributes, body = match.group(1), match.group(2)
        if SECTION_NAME in body:
            # Already annotated, so a second pass over the same report leaves it alone
            return match.group(0)
        if not CDATA_END.search(body) and not ELEMENT_END.search(body):
            return match.group(0)

        attributes = _attributes(raw_attributes)
        name = attributes.get("classname", "")
        key = (name, attributes.get("name", ""))
        start, end, job_ids = windows.get(key, run_window + ([],))

        section = log_section(start, end, job_ids)
        if not section:
            return match.group(0)

        linked += 1
        print(f"{name}\n{section}\n")
        return f"<testcase{raw_attributes}>{_insert(body, section)}</testcase>"

    updated = TESTCASE.sub(rewrite, original)
    if not linked:
        return

    with open(xml_path, "w", encoding="utf-8") as handle:
        handle.write(updated)
    print(f"Added Kibana links to {linked} failed test(s) in {xml_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("xml_paths", nargs="+", help="planemo JUnit report(s) to annotate")
    parser.add_argument(
        "--run-start",
        type=float,
        help="epoch seconds the planemo run started, used for tests with no job",
    )
    parser.add_argument(
        "--run-end",
        type=float,
        help="epoch seconds the planemo run finished, used for tests with no job",
    )
    args = parser.parse_args()

    if not os.getenv("KIBANA_URL"):
        print("KIBANA_URL is not set, leaving the reports alone.")
        sys.exit(0)

    now = time.time()
    fallback = (args.run_start or now, args.run_end or now)

    for path in args.xml_paths:
        if not os.path.isfile(path):
            print(f"No such report: {path}", file=sys.stderr)
            continue
        add_links(path, os.path.splitext(path)[0] + ".json", fallback)
