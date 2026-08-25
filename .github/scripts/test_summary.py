#!/usr/bin/env python3
"""Render a JUnit XML report into a human-readable test statistics table.

Usage: python test_summary.py <junit_xml_path> [group_title]

Writes a markdown table to $GITHUB_STEP_SUMMARY when running inside GitHub
Actions, and always prints it to stdout (so it is visible in the job log too).

Output format:

    ### 🧪 Test report — math

    | Test                        | Result   | Time |
    |-----------------------------|----------|------|
    | test_read_sigma_from_header | ✅ passed | 0.01s|
    ...
    **Total: 23 passed, 0 failed, 0 errors, 0 skipped in 0.24s**
"""

from __future__ import annotations

import os
import sys
import xml.etree.ElementTree as ET


def short_name(classname: str, name: str) -> str:
    """tests.test_loaders_math + test_x -> test_loaders_math::test_x"""
    module = classname.rsplit(".", 1)[-1] if classname else ""
    return f"{module}::{name}" if module else name


def main(xml_path: str, group_title: str = "") -> int:
    tree = ET.parse(xml_path)
    suite = tree.getroot()
    if not suite.tag.endswith("testsuite"):
        suite = suite.find(".//testsuite")

    rows = []
    counts = {"passed": 0, "failed": 0, "error": 0, "skipped": 0}
    for case in suite.iter("testcase"):
        name = short_name(case.get("classname", ""), case.get("name", ""))
        elapsed = float(case.get("time", 0.0))
        failure = case.find("failure")
        error = case.find("error")
        skipped = case.find("skipped")
        if error is not None:
            status, icon = "error", "💥"
            counts["error"] += 1
        elif failure is not None:
            status, icon = "FAILED", "❌"
            counts["failed"] += 1
        elif skipped is not None:
            status, icon = "skipped", "⏭️"
            counts["skipped"] += 1
        else:
            status, icon = "passed", "✅"
            counts["passed"] += 1
        detail = ""
        for node in (failure, error, skipped):
            if node is not None:
                msg = (node.get("message") or "").splitlines()
                detail = f" — {msg[0]}" if msg else ""
                break
        rows.append(f"| `{name}` | {icon} {status}{detail} | {elapsed:.2f}s |")

    total_time = float(suite.get("time", 0.0))
    header = [
        "| Test | Result | Time |",
        "|------|--------|------|",
    ] + rows
    total = (f"**Total: {counts['passed']} passed, {counts['failed']} failed,"
             f" {counts['error']} errors, {counts['skipped']} skipped"
             f" in {total_time:.2f}s**")
    title = f"### 🧪 Test report — {group_title}\n\n" if group_title else ""
    report = title + "\n".join(header + ["", total]) + "\n"

    print(report)
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_file:
        with open(summary_file, "a", encoding="utf-8") as fh:
            fh.write(report)
    return 0 if (counts["failed"] == 0 and counts["error"] == 0) else 1


if __name__ == "__main__":
    title_arg = sys.argv[2] if len(sys.argv) > 2 else ""
    sys.exit(main(sys.argv[1], title_arg))
