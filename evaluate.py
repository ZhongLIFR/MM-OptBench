from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from scoring import compare_solution_to_ground_truth, make_json_safe, normalize_solution_aliases


DATASET = Path(__file__).resolve().parent / "dataset"


def load_dataset(root: Path) -> dict[str, Path]:
    instances = {}
    for path in sorted(root.glob("*/*/*/*/ground_truth/instance_data.json")):
        instance = path.parent.parent
        if instance.name in instances:
            raise ValueError(f"Duplicate instance ID: {instance.name}")
        instances[instance.name] = instance
    if not instances:
        raise ValueError(f"No instances found in {root}")
    return instances


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def evaluate_instance(instance: Path, solution: Any, tolerance: float = 1e-6) -> dict[str, Any]:
    data = read_json(instance / "ground_truth/instance_data.json")
    reference = read_json(instance / "ground_truth/solution_ref.json")
    problem = instance.parent.parent.name
    try:
        result = compare_solution_to_ground_truth(
            problem, normalize_solution_aliases(solution), reference, data, tolerance
        )
    except (ValueError, TypeError, KeyError, IndexError, OverflowError) as error:
        result = {"correct": False, "reason": f"Invalid solution: {error}"}
    return {"instance_id": instance.name, **make_json_safe(result)}


def read_predictions(path: Path, instances: dict[str, Path]) -> list[tuple[str, Any]]:
    records = []
    seen = set()
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Line {line_number}: {error.msg}") from error
            if not isinstance(record, dict) or "instance_id" not in record or "solution" not in record:
                raise ValueError(f"Line {line_number}: expected instance_id and solution")
            instance_id = record["instance_id"]
            if not isinstance(instance_id, str) or instance_id not in instances:
                raise ValueError(f"Line {line_number}: unknown instance ID {instance_id!r}")
            if instance_id in seen:
                raise ValueError(f"Line {line_number}: duplicate instance ID {instance_id}")
            seen.add(instance_id)
            records.append((instance_id, record["solution"]))
    if not records:
        raise ValueError("The predictions file contains no records")
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Score saved MM-OptBench solution dictionaries.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--solution", type=Path, help="A solution JSON file for one instance")
    mode.add_argument("--predictions", type=Path, help="JSONL records with instance_id and solution")
    parser.add_argument("--instance", help="Instance ID for --solution, for example ba_e_008")
    parser.add_argument("--dataset", type=Path, default=DATASET, help="Dataset root directory")
    parser.add_argument("--tolerance", type=float, default=1e-6)
    args = parser.parse_args()
    if bool(args.solution) != bool(args.instance):
        parser.error("--solution and --instance must be used together")
    if not math.isfinite(args.tolerance) or args.tolerance < 0:
        parser.error("--tolerance must be finite and nonnegative")
    try:
        instances = load_dataset(args.dataset)
        if args.solution:
            if args.instance not in instances:
                raise ValueError(f"Unknown instance ID: {args.instance}")
            result = evaluate_instance(instances[args.instance], read_json(args.solution), args.tolerance)
        else:
            records = read_predictions(args.predictions, instances)
            results = [evaluate_instance(instances[key], value, args.tolerance) for key, value in records]
            correct = sum(item["correct"] is True for item in results)
            result = {
                "total_instances": len(instances),
                "evaluated": len(results),
                "correct": correct,
                "accuracy": correct / len(results),
                "results": results,
            }
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
    except (OSError, UnicodeError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
