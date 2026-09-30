from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Any

from .instances import BenchmarkInstance
from .prompts import (
    RESPONSE_CONTRACT_EXTRACTION_JSON,
    RESPONSE_CONTRACT_FULLSOLVE_JSON,
    RESPONSE_CONTRACT_MINIMAL_SECTIONS,
)
from .scoring import (
    build_primary_diagnosis,
    build_secondary_failure_signals,
    check_schema,
    compare_extracted_instance,
    compare_solution_to_ground_truth,
    effective_numeric_tolerance,
    extract_structured_instance,
    has_top_level_solve_function,
    infer_problem_type,
    make_json_safe,
    normalize_solver_code,
    parse_stdout_object,
    validate_output_against_instance,
)


def diagnose_instance_result(
    instance: BenchmarkInstance,
    assistant_payload: dict[str, Any] | None,
    *,
    response_contract: str = RESPONSE_CONTRACT_MINIMAL_SECTIONS,
    python_cmd: str = sys.executable,
    timeout_seconds: int = 1800,
    tolerance: float = 1e-6,
) -> dict[str, Any]:
    if assistant_payload is None:
        return {
            "case_id": instance.instance_id,
            "instance_id": instance.instance_id,
            "primary_failure_stage": "response_schema_error",
            "summary": "No parsed assistant payload.",
        }
    schema_report = check_schema(assistant_payload, response_contract)
    if not schema_report.get("required_keys_present", False):
        return {
            "case_id": instance.instance_id,
            "instance_id": instance.instance_id,
            "assistant_json_valid": True,
            "schema_report": schema_report,
            "primary_failure_stage": "response_schema_error",
            "summary": "The response is missing required top-level keys.",
        }
    code = assistant_payload.get("solver_code_python")
    if not isinstance(code, str) or not code.strip():
        return {
            "case_id": instance.instance_id,
            "instance_id": instance.instance_id,
            "assistant_json_valid": True,
            "schema_report": schema_report,
            "primary_failure_stage": "response_content_error",
            "summary": "No solver code found.",
        }
    execution = execute_solver_code(code, python_cmd=python_cmd, timeout_seconds=timeout_seconds)
    result: dict[str, Any] = {
        "case_id": instance.instance_id,
        "instance_id": instance.instance_id,
        "assistant_json_valid": True,
        "schema_report": schema_report,
        "execution": execution,
    }
    try:
        ground_truth_instance = instance.json("ground_truth/instance_data.json")
        ground_truth_solution = instance.json("ground_truth/solution_ref.json")
    except Exception as exc:
        result["primary_failure_stage"] = "ground_truth_missing"
        result["summary"] = str(exc)
        return result

    problem_type = str(assistant_payload.get("problem_type") or instance.problem or "")
    inferred_problem_type = infer_problem_type(
        ground_truth_instance=ground_truth_instance,
        assistant_json=assistant_payload,
    )
    if inferred_problem_type and not problem_type:
        problem_type = inferred_problem_type
    if not problem_type:
        problem_type = instance.problem
    result["problem_type"] = problem_type
    result["effective_numeric_tolerance"] = effective_numeric_tolerance(problem_type, tolerance)

    executed_output = normalize_solution_aliases(execution.get("parsed_output"))
    if executed_output is None:
        executed_output = normalize_solution_aliases(execution.get("result"))
    extracted_instance = extract_structured_instance(assistant_payload)
    reading_report = (
        compare_extracted_instance(extracted_instance, ground_truth_instance, tolerance)
        if extracted_instance
        else None
    )
    predicted_validation = (
        validate_output_against_instance(problem_type, executed_output, extracted_instance, tolerance)
        if extracted_instance
        else None
    )
    ground_truth_validation = compare_solution_to_ground_truth(
        problem_type,
        executed_output,
        ground_truth_solution,
        ground_truth_instance,
        tolerance,
    )
    primary_stage, summary = build_primary_diagnosis(
        schema_report=schema_report,
        reading_report=reading_report,
        execution_report=execution,
        predicted_validation=predicted_validation,
        ground_truth_validation=ground_truth_validation,
    )
    result.update(
        {
            "reading_report": reading_report,
            "predicted_validation": predicted_validation,
            "ground_truth_validation": ground_truth_validation,
            "primary_failure_stage": primary_stage,
            "secondary_failure_signals": build_secondary_failure_signals(
                primary_stage=primary_stage,
                reading_report=reading_report,
                execution_report=execution,
                predicted_validation=predicted_validation,
                ground_truth_validation=ground_truth_validation,
            ),
            "summary": summary,
        }
    )
    return result


def diagnose_extraction_result(
    instance: BenchmarkInstance,
    assistant_payload: dict[str, Any] | None,
    *,
    tolerance: float = 1e-6,
) -> dict[str, Any]:
    if assistant_payload is None:
        return {
            "case_id": instance.instance_id,
            "instance_id": instance.instance_id,
            "primary_failure_stage": "response_schema_error",
            "summary": "No parsed extraction payload.",
        }
    schema_report = check_schema(assistant_payload, RESPONSE_CONTRACT_EXTRACTION_JSON)
    extracted_instance = extract_structured_instance(assistant_payload)
    try:
        truth = instance.json("ground_truth/instance_data.json")
    except Exception as exc:
        return {
            "case_id": instance.instance_id,
            "instance_id": instance.instance_id,
            "primary_failure_stage": "ground_truth_missing",
            "summary": str(exc),
        }
    reading_report = compare_extracted_instance(extracted_instance, truth, tolerance)
    if not schema_report.get("required_keys_present", False):
        primary_stage = "response_schema_error"
        summary = "The response is missing required top-level extraction keys."
    elif not extracted_instance:
        primary_stage = "reading_error"
        summary = "No extracted_data.structured_instance found."
    elif reading_report.get("major_mismatch"):
        primary_stage = "reading_error"
        summary = "The extracted instance data differs materially from the benchmark ground truth."
    else:
        primary_stage = "success"
        summary = "The extracted instance data matches the benchmark ground truth at the configured comparison granularity."
    return {
        "case_id": instance.instance_id,
        "instance_id": instance.instance_id,
        "assistant_json_valid": True,
        "schema_report": schema_report,
        "structured_instance_available": bool(extracted_instance),
        "reading_report": reading_report,
        "primary_failure_stage": primary_stage,
        "summary": summary,
    }


def execute_solver_code(code: str, *, python_cmd: str = sys.executable, timeout_seconds: int = 1800) -> dict[str, Any]:
    normalized_code = normalize_solver_code(code)
    with tempfile.TemporaryDirectory(prefix="mmopt_solver_") as tmp:
        tmp_path = Path(tmp)
        module_path = tmp_path / "solver.py"
        module_path.write_text(normalized_code, encoding="utf-8")
        runner_path: Path | None = None
        command = [python_cmd, str(module_path)]
        execution_mode = "direct_script"
        if has_top_level_solve_function(normalized_code):
            runner_path = tmp_path / "harness.py"
            runner_path.write_text(_solve_harness(module_path), encoding="utf-8")
            command = [python_cmd, str(runner_path)]
            execution_mode = "solve_harness"
        try:
            completed = subprocess.run(
                command,
                cwd=tmp_path,
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else exc.stdout
            stderr = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else exc.stderr
            return {
                "ok": False,
                "script_path": str(module_path),
                "runner_path": str(runner_path) if runner_path is not None else None,
                "execution_mode": execution_mode,
                "returncode": None,
                "timed_out": True,
                "stdout": stdout or "",
                "stderr": stderr or f"Execution timed out after {timeout_seconds} seconds.",
                "parsed_output": None,
                "result": None,
            }
    stdout = completed.stdout.strip()
    parsed = parse_stdout_object(stdout)
    parsed = make_json_safe(parsed)
    return {
        "ok": completed.returncode == 0 and parsed is not None,
        "script_path": str(module_path),
        "runner_path": str(runner_path) if runner_path is not None else None,
        "execution_mode": execution_mode,
        "returncode": completed.returncode,
        "timed_out": False,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "parsed_output": parsed,
        "result": parsed,
    }


def normalize_solution_aliases(output: Any) -> Any:
    if not isinstance(output, dict):
        return output
    normalized = make_json_safe(output)
    if not isinstance(normalized, dict):
        return normalized
    solution = normalized.get("solution")
    if isinstance(solution, dict):
        for key, value in solution.items():
            normalized.setdefault(key, value)
    alias_groups = (
        ("objective_value", "objective", "objective_exact", "total_cost", "cost", "value", "makespan"),
        ("selected_items", "items", "chosen_items", "selected"),
        ("assignment", "assignments", "decision_variables"),
        ("flows", "flow", "arc_flows"),
        ("path", "route", "selected_arcs"),
    )
    for canonical, *aliases in alias_groups:
        if canonical in normalized:
            continue
        for alias in aliases:
            if alias in normalized:
                normalized[canonical] = normalized[alias]
                break
    return normalized


def _solve_harness(module_path: Path) -> str:
    return (
        textwrap.dedent(
            f"""
            import importlib.util
            import json
            from pathlib import Path

            def _make_json_safe(value):
                if isinstance(value, dict):
                    converted = {{}}
                    for key, item in value.items():
                        if isinstance(key, (str, int, float, bool)) or key is None:
                            safe_key = key
                        elif isinstance(key, (tuple, list)):
                            safe_key = "_".join(str(part) for part in key)
                        else:
                            safe_key = str(key)
                        converted[safe_key] = _make_json_safe(item)
                    return converted
                if isinstance(value, (list, tuple)):
                    return [_make_json_safe(item) for item in value]
                if isinstance(value, set):
                    return [_make_json_safe(item) for item in sorted(value, key=lambda item: str(item))]
                if hasattr(value, "item") and not isinstance(value, (str, bytes, bytearray)):
                    try:
                        return _make_json_safe(value.item())
                    except Exception:
                        pass
                return value

            module_path = Path({str(module_path)!r})
            spec = importlib.util.spec_from_file_location("mmopt_generated_solver", module_path)
            if spec is None or spec.loader is None:
                raise RuntimeError(f"Failed to load generated solver module: {{module_path}}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            solve = getattr(module, "solve", None)
            if solve is None or not callable(solve):
                raise AttributeError("Generated code must define a callable solve() function.")

            result = solve()
            if not isinstance(result, dict):
                raise TypeError("solve() must return a dict.")

            print(json.dumps(_make_json_safe(result), ensure_ascii=False))
            """
        ).strip()
        + "\n"
    )


def compare_solution(predicted: Any, truth: Any, *, tolerance: float = 1e-6) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    _compare(predicted, truth, "", tolerance, findings)
    mismatches = [finding for finding in findings if not finding["match"]]
    return {
        "matches": not mismatches,
        "checked_count": len(findings),
        "mismatch_count": len(mismatches),
        "mismatches": mismatches[:50],
    }


def _compare(predicted: Any, truth: Any, path: str, tolerance: float, findings: list[dict[str, Any]]) -> None:
    if isinstance(truth, dict):
        if not isinstance(predicted, dict):
            findings.append({"path": path, "match": False, "type": "type", "predicted": type(predicted).__name__, "truth": "dict"})
            return
        for key, truth_value in truth.items():
            key_path = f"{path}.{key}" if path else str(key)
            if key not in predicted:
                findings.append({"path": key_path, "match": False, "type": "missing_key"})
                continue
            _compare(predicted[key], truth_value, key_path, tolerance, findings)
        return
    if isinstance(truth, list):
        if not isinstance(predicted, list):
            findings.append({"path": path, "match": False, "type": "type", "predicted": type(predicted).__name__, "truth": "list"})
            return
        if len(predicted) != len(truth):
            findings.append({"path": path, "match": False, "type": "length", "predicted": len(predicted), "truth": len(truth)})
            return
        for index, truth_value in enumerate(truth):
            _compare(predicted[index], truth_value, f"{path}[{index}]", tolerance, findings)
        return
    if isinstance(truth, (int, float)) and isinstance(predicted, (int, float)):
        diff = abs(float(predicted) - float(truth))
        findings.append({"path": path, "match": diff <= tolerance, "type": "number", "abs_diff": diff})
        return
    findings.append({"path": path, "match": predicted == truth, "type": "exact", "predicted": predicted, "truth": truth})
