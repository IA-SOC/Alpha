"""Import synthetic/anonymized cases and pre-enriched IoCs into SQLite."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.services.context_import import import_context  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iocs", type=Path, required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("data/context/context.sqlite3"),
    )
    args = parser.parse_args()
    try:
        counts = import_context(
            args.database, iocs_file=args.iocs, cases_file=args.cases
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(
        f"Imported {counts['iocs']} IoCs, {counts['cases']} cases and "
        f"{counts['case_iocs']} case-IoC links into {args.database}"
    )


if __name__ == "__main__":
    main()
