import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "examples" / "sprint3"
EXPECTATIONS = json.loads((ROOT / "expectations.json").read_text(encoding="utf-8"))


def load_case(name):
    return json.loads((ROOT / EXPECTATIONS[name]["file"]).read_text(encoding="utf-8"))
