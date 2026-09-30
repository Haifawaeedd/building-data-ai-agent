"""Run deterministic answer-licensing cases without a database or model."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.answer_licensing import evaluate_answer_license


CASES_PATH = ROOT / "evaluation" / "answer_licensing" / "cases.json"


def run_cases(path=CASES_PATH):
    cases = json.loads(path.read_text(encoding="utf-8"))
    results = []
    for case in cases:
        expected = case["expected"]
        inputs = {
            key: value
            for key, value in case.items()
            if key not in {"name", "expected"}
        }
        actual = evaluate_answer_license(**inputs)["answer_license"]
        results.append({
            "name": case["name"],
            "expected": expected,
            "actual": actual,
            "passed": actual == expected,
        })
    passed = sum(item["passed"] for item in results)
    return {
        "cases": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "results": results,
    }


if __name__ == "__main__":
    report = run_cases()
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["failed"] == 0 else 1)
