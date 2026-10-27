
import argparse
import json
import subprocess
from pathlib import Path


def audit(root: Path):
    result = subprocess.run(
        ["git", "-C", str(root), "log", "--format=%aN", "--numstat", "--no-merges"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        return {
            "history_available": False,
            "authors": {},
            "team_review_required": True,
            "note": "Run inside the real Git checkout; a source ZIP has no history.",
        }
    authors, author = {}, None
    for line in result.stdout.splitlines():
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) == 3:
            if author is not None and Path(parts[2]).suffix in {
                ".py",
                ".ts",
                ".tsx",
                ".js",
                ".jsx",
                ".mjs",
            }:
                authors[author].add(parts[2])
        else:
            author = line
            authors.setdefault(author, set())
    return {
        "history_available": True,
        "authors": {name: sorted(files) for name, files in authors.items()},
        "team_review_required": True,
        "note": (
            "Match Git identities to the team; check PRs and AI records manually. "
            "File changes alone do not prove authorship or completion."
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(".."))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(audit(args.root), stream, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
