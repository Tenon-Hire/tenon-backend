from __future__ import annotations

import argparse


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Initialize timestamped code-quality run directories and optionally copy artifacts."
    )
    parser.add_argument(
        "--phase",
        required=True,
        help="Phase name. Supported: performance, loc, file-structure, testing-coverage, documentation.",
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Run date folder name in YYYY-MM-DD (defaults to current local date).",
    )
    parser.add_argument(
        "--label",
        default=None,
        help="Optional run label appended to the date (slug-safe).",
    )
    parser.add_argument(
        "--artifact",
        action="append",
        default=[],
        help="Artifact file or directory path to copy into this run (repeatable).",
    )
    parser.add_argument(
        "--artifact-glob",
        action="append",
        default=[],
        help="Glob (repo-root relative) to copy matching artifacts (repeatable).",
    )
    return parser.parse_args()
