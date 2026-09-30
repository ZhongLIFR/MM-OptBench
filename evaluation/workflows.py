from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any, Iterable

from .benchmarks import ArtifactBenchmark, Benchmark, parse_instance_key
from .diagnosis import diagnose_extraction_result, diagnose_instance_result
from .instances import BenchmarkInstance
from .prompts import (
    INPUT_MODE_MULTIMODAL,
    INPUT_MODE_ORACLE_READING,
    INPUT_MODE_VERIFIED_EXTRACTION,
    RESPONSE_CONTRACT_EXTRACTION_JSON,
    RESPONSE_CONTRACT_MINIMAL_SECTIONS,
    build_verified_conditioning_payload,
)
from .runner import (
    DEFAULT_API_KEY_ENV,
    DEFAULT_BASE_URL,
    MAX_API_COMPLETION_TOKENS,
    build_summary_markdown,
    classify_provider_empty_content,
    create_output_dir,
    extract_assistant_text,
    parse_assistant_payload,
    run_instance,
    sanitize_name,
    save_json,
    summarize_records,
)

EVAL_MODE_MULTIMODAL = "multimodal"
EVAL_MODE_ORACLE_READING = "oracle_reading"
EVAL_MODE_VERIFIED_EXTRACTION = "verified_extraction"
EVAL_MODE_TWO_STAGE = "two_stage"


def run_experiment(
    instances: Iterable[BenchmarkInstance],
    *,
    models: list[str],
    mode: str = EVAL_MODE_MULTIMODAL,
    base_url: str = DEFAULT_BASE_URL,
    api_key: str | None = None,
    api_key_env: str = DEFAULT_API_KEY_ENV,
    include_canonical: bool = False,
    response_contract: str = RESPONSE_CONTRACT_MINIMAL_SECTIONS,
    temperature: float = 0.0,
    max_tokens: int = MAX_API_COMPLETION_TOKENS,
    stage1_max_tokens: int = MAX_API_COMPLETION_TOKENS,
    stage2_max_tokens: int = MAX_API_COMPLETION_TOKENS,
    extraction_max_tokens: int = MAX_API_COMPLETION_TOKENS,
    downstream_max_tokens: int = MAX_API_COMPLETION_TOKENS,
    verify_ssl: bool = True,
    output_dir: str | Path = "output/mmopt_eval",
    run_output_dir: str | Path = "output/mmopt_runs",
    dry_run: bool = False,
    python_cmd: str = sys.executable,
    timeout_seconds: int = 1800,
    tolerance: float = 1e-6,
    resume_eval_dir: str | Path | None = None,
) -> Path:
    eval_mode = mode
    instance_tuple = tuple(instances)
    if not instance_tuple:
        raise ValueError("No instances selected for evaluation.")
    eval_dir = Path(resume_eval_dir).expanduser().resolve() if resume_eval_dir else _new_eval_dir(output_dir, instance_tuple, models, eval_mode)
    eval_dir.mkdir(parents=True, exist_ok=True)
    existing_records = _read_manifest(eval_dir / "manifest.jsonl") if resume_eval_dir else []
    completed = _completed_record_map(existing_records)
    config = _build_config(
        instance_tuple,
        models,
        eval_mode=eval_mode,
        response_contract=response_contract,
        include_canonical=include_canonical,
        dry_run=dry_run,
        base_url=base_url,
        api_key_env=api_key_env,
        temperature=temperature,
        max_tokens=max_tokens,
        stage1_max_tokens=stage1_max_tokens,
        stage2_max_tokens=stage2_max_tokens,
        extraction_max_tokens=extraction_max_tokens,
        downstream_max_tokens=downstream_max_tokens,
        verify_ssl=verify_ssl,
        output_dir=output_dir,
        run_output_dir=run_output_dir,
        python_cmd=python_cmd,
        timeout_seconds=timeout_seconds,
        tolerance=tolerance,
    )
    save_json(eval_dir / "config.json", config)
    records = list(existing_records)
    for model in models:
        for instance in instance_tuple:
            if eval_mode == EVAL_MODE_MULTIMODAL:
                record_key = (model, instance.instance_key, EVAL_MODE_MULTIMODAL, "solve")
                if record_key in completed:
                    continue
                run_dir, metadata = run_instance(
                    instance,
                    model=model,
                    base_url=base_url,
                    api_key=api_key,
                    api_key_env=api_key_env,
                    include_canonical=include_canonical,
                    response_contract=response_contract,
                    input_mode=INPUT_MODE_MULTIMODAL,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    verify_ssl=verify_ssl,
                    output_root=run_output_dir,
                    dry_run=dry_run,
                    python_cmd=python_cmd,
                    timeout_seconds=timeout_seconds,
                    tolerance=tolerance,
                )
                records.append(_record(instance, model, run_dir, metadata, eval_mode=eval_mode, stage="solve"))
                completed[record_key] = records[-1]
            elif eval_mode == EVAL_MODE_ORACLE_READING:
                record_key = (model, instance.instance_key, EVAL_MODE_ORACLE_READING, "oracle_solve")
                if record_key in completed:
                    continue
                run_dir, metadata = run_instance(
                    instance,
                    model=model,
                    base_url=base_url,
                    api_key=api_key,
                    api_key_env=api_key_env,
                    include_canonical=include_canonical,
                    response_contract=response_contract,
                    input_mode=INPUT_MODE_ORACLE_READING,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    verify_ssl=verify_ssl,
                    output_root=run_output_dir,
                    dry_run=dry_run,
                    python_cmd=python_cmd,
                    timeout_seconds=timeout_seconds,
                    tolerance=tolerance,
                )
                records.append(_record(instance, model, run_dir, metadata, eval_mode=eval_mode, stage="oracle_solve"))
                completed[record_key] = records[-1]
            elif eval_mode == EVAL_MODE_VERIFIED_EXTRACTION:
                new_records = _run_verified_extraction(
                    instance,
                    model,
                    base_url=base_url,
                    api_key=api_key,
                    api_key_env=api_key_env,
                    include_canonical=include_canonical,
                    temperature=temperature,
                    extraction_max_tokens=extraction_max_tokens,
                    downstream_max_tokens=downstream_max_tokens,
                    verify_ssl=verify_ssl,
                    run_output_dir=run_output_dir,
                    dry_run=dry_run,
                    python_cmd=python_cmd,
                    timeout_seconds=timeout_seconds,
                    tolerance=tolerance,
                    completed=completed,
                )
                records.extend(new_records)
                completed.update(_completed_record_map(new_records))
            elif eval_mode == EVAL_MODE_TWO_STAGE:
                new_records = _run_two_stage(
                    instance,
                    model,
                    base_url=base_url,
                    api_key=api_key,
                    api_key_env=api_key_env,
                    include_canonical=include_canonical,
                    response_contract=response_contract,
                    temperature=temperature,
                    stage1_max_tokens=stage1_max_tokens,
                    stage2_max_tokens=stage2_max_tokens,
                    verify_ssl=verify_ssl,
                    run_output_dir=run_output_dir,
                    dry_run=dry_run,
                    python_cmd=python_cmd,
                    timeout_seconds=timeout_seconds,
                    tolerance=tolerance,
                    completed=completed,
                )
                records.extend(new_records)
                completed.update(_completed_record_map(new_records))
            else:
                raise ValueError(f"Unsupported eval mode: {eval_mode}")
            _rewrite_outputs(eval_dir, records)
    _rewrite_outputs(eval_dir, records)
    return eval_dir


def resume_eval_dir(
    eval_dir: str | Path,
    *,
    run_output_dir: str | Path | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    api_key_env: str | None = None,
    verify_ssl: bool | None = None,
    dry_run: bool | None = None,
    python_cmd: str | None = None,
    timeout_seconds: int | None = None,
    tolerance: float | None = None,
) -> Path:
    path = Path(eval_dir).expanduser().resolve()
    config = _read_json(path / "config.json")
    instances = _instances_from_config(config)
    return run_experiment(
        instances,
        models=[str(model) for model in config["models"]],
        mode=str(config.get("eval_mode", EVAL_MODE_MULTIMODAL)),
        base_url=base_url if base_url is not None else str(config.get("base_url", DEFAULT_BASE_URL)),
        api_key=api_key,
        api_key_env=api_key_env if api_key_env is not None else str(config.get("api_key_env", DEFAULT_API_KEY_ENV)),
        include_canonical=bool(config.get("include_canonical", False)),
        response_contract=str(config.get("response_contract", RESPONSE_CONTRACT_MINIMAL_SECTIONS)),
        temperature=float(config.get("temperature", 0.0)),
        max_tokens=int(config.get("max_tokens", MAX_API_COMPLETION_TOKENS)),
        stage1_max_tokens=int(config.get("stage1_max_tokens", MAX_API_COMPLETION_TOKENS)),
        stage2_max_tokens=int(config.get("stage2_max_tokens", MAX_API_COMPLETION_TOKENS)),
        extraction_max_tokens=int(config.get("extraction_max_tokens", MAX_API_COMPLETION_TOKENS)),
        downstream_max_tokens=int(config.get("downstream_max_tokens", MAX_API_COMPLETION_TOKENS)),
        verify_ssl=verify_ssl if verify_ssl is not None else bool(config.get("verify_ssl", True)),
        output_dir=path.parent,
        run_output_dir=run_output_dir if run_output_dir is not None else config.get("run_output_dir", "output/mmopt_runs"),
        dry_run=dry_run if dry_run is not None else bool(config.get("dry_run", False)),
        python_cmd=python_cmd if python_cmd is not None else str(config.get("python_cmd", sys.executable)),
        timeout_seconds=timeout_seconds if timeout_seconds is not None else int(config.get("timeout_seconds", 1800)),
        tolerance=tolerance if tolerance is not None else float(config.get("tolerance", 1e-6)),
        resume_eval_dir=path,
    )


def grade_instance_response(instance: BenchmarkInstance, target: str | Path, *, tolerance: float = 1e-6) -> dict[str, Any]:
    payload, response_contract = _load_assistant_payload(target)
    if response_contract == RESPONSE_CONTRACT_EXTRACTION_JSON:
        return diagnose_extraction_result(instance, payload, tolerance=tolerance)
    return diagnose_instance_result(instance, payload, response_contract=response_contract, tolerance=tolerance)


def diagnose_instance_target(
    instance: BenchmarkInstance,
    target: str | Path,
    *,
    python_cmd: str = sys.executable,
    timeout_seconds: int = 1800,
    tolerance: float = 1e-6,
) -> dict[str, Any]:
    payload, response_contract = _load_assistant_payload(target)
    provider_failure = _provider_empty_diagnosis(instance, target, response_contract)
    if payload is None and provider_failure is not None:
        return provider_failure
    if response_contract == RESPONSE_CONTRACT_EXTRACTION_JSON:
        return diagnose_extraction_result(instance, payload, tolerance=tolerance)
    return diagnose_instance_result(
        instance,
        payload,
        response_contract=response_contract,
        python_cmd=python_cmd,
        timeout_seconds=timeout_seconds,
        tolerance=tolerance,
    )


def diagnose_extraction_target(instance: BenchmarkInstance, target: str | Path, *, tolerance: float = 1e-6) -> dict[str, Any]:
    payload, _ = _load_assistant_payload(target, response_contract=RESPONSE_CONTRACT_EXTRACTION_JSON)
    provider_failure = _provider_empty_diagnosis(instance, target, RESPONSE_CONTRACT_EXTRACTION_JSON)
    if payload is None and provider_failure is not None:
        return provider_failure
    return diagnose_extraction_result(instance, payload, tolerance=tolerance)


def load_instance(instance: str | None = None, instance_dir: str | Path | None = None) -> BenchmarkInstance:
    if instance_dir is not None:
        return ArtifactBenchmark().instances(instance_dir=instance_dir)[0]
    if instance is None:
        raise ValueError("Either instance or instance_dir is required.")
    return Benchmark().instance(instance)


def _run_verified_extraction(
    instance: BenchmarkInstance,
    model: str,
    *,
    base_url: str,
    api_key: str | None,
    api_key_env: str,
    include_canonical: bool,
    temperature: float,
    extraction_max_tokens: int,
    downstream_max_tokens: int,
    verify_ssl: bool,
    run_output_dir: str | Path,
    dry_run: bool,
    python_cmd: str,
    timeout_seconds: int,
    tolerance: float,
    completed: dict[tuple[str, str, str, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    extraction_key = (model, instance.instance_key, EVAL_MODE_VERIFIED_EXTRACTION, "extraction")
    extraction_record = completed.get(extraction_key)
    if extraction_record is None:
        run_dir, metadata = run_instance(
            instance,
            model=model,
            base_url=base_url,
            api_key=api_key,
            api_key_env=api_key_env,
            include_canonical=include_canonical,
            response_contract=RESPONSE_CONTRACT_EXTRACTION_JSON,
            input_mode=INPUT_MODE_MULTIMODAL,
            temperature=temperature,
            max_tokens=extraction_max_tokens,
            verify_ssl=verify_ssl,
            output_root=run_output_dir,
            dry_run=dry_run,
            python_cmd=python_cmd,
            timeout_seconds=timeout_seconds,
            tolerance=tolerance,
        )
        extraction_record = _record(instance, model, run_dir, metadata, eval_mode=EVAL_MODE_VERIFIED_EXTRACTION, stage="extraction")
        records.append(extraction_record)
    downstream_key = (model, instance.instance_key, EVAL_MODE_VERIFIED_EXTRACTION, "verified_solve")
    if downstream_key not in completed:
        extraction_passed = extraction_record is not None and _record_succeeded(extraction_record)
        if extraction_passed and not dry_run:
            try:
                extraction_payload = _load_verified_extraction_payload(extraction_record)
                conditioning_payload = build_verified_conditioning_payload(instance.instance_id, extraction_payload)
            except Exception as exc:
                records.append(
                    {
                        **instance.metadata(),
                        "model": model,
                        "run_dir": None,
                        "eval_mode": EVAL_MODE_VERIFIED_EXTRACTION,
                        "stage": "verified_solve",
                        "skipped": True,
                        "skip_reason": f"verified_payload_unavailable: {exc}",
                        "assistant_json_valid": False,
                        "diagnosis_primary_failure_stage": "skipped",
                    }
                )
            else:
                run_dir, metadata = run_instance(
                    instance,
                    model=model,
                    base_url=base_url,
                    api_key=api_key,
                    api_key_env=api_key_env,
                    include_canonical=include_canonical,
                    response_contract=RESPONSE_CONTRACT_MINIMAL_SECTIONS,
                    input_mode=INPUT_MODE_VERIFIED_EXTRACTION,
                    conditioning_payload=conditioning_payload,
                    temperature=temperature,
                    max_tokens=downstream_max_tokens,
                    verify_ssl=verify_ssl,
                    output_root=run_output_dir,
                    dry_run=False,
                    python_cmd=python_cmd,
                    timeout_seconds=timeout_seconds,
                    tolerance=tolerance,
                )
                records.append(_record(instance, model, run_dir, metadata, eval_mode=EVAL_MODE_VERIFIED_EXTRACTION, stage="verified_solve"))
        else:
            records.append(
                {
                    **instance.metadata(),
                    "model": model,
                    "run_dir": None,
                    "eval_mode": EVAL_MODE_VERIFIED_EXTRACTION,
                    "stage": "verified_solve",
                    "skipped": True,
                    "skip_reason": "dry_run_or_extraction_failed",
                    "assistant_json_valid": False,
                    "diagnosis_primary_failure_stage": "skipped",
                }
            )
    return records


def _run_two_stage(
    instance: BenchmarkInstance,
    model: str,
    *,
    base_url: str,
    api_key: str | None,
    api_key_env: str,
    include_canonical: bool,
    response_contract: str,
    temperature: float,
    stage1_max_tokens: int,
    stage2_max_tokens: int,
    verify_ssl: bool,
    run_output_dir: str | Path,
    dry_run: bool,
    python_cmd: str,
    timeout_seconds: int,
    tolerance: float,
    completed: dict[tuple[str, str, str, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    stage1_key = (model, instance.instance_key, EVAL_MODE_TWO_STAGE, "stage1_solve")
    stage1_record = completed.get(stage1_key)
    if stage1_record is None:
        run_dir, metadata = run_instance(
            instance,
            model=model,
            base_url=base_url,
            api_key=api_key,
            api_key_env=api_key_env,
            include_canonical=include_canonical,
            response_contract=response_contract,
            input_mode=INPUT_MODE_MULTIMODAL,
            temperature=temperature,
            max_tokens=stage1_max_tokens,
            verify_ssl=verify_ssl,
            output_root=run_output_dir,
            dry_run=dry_run,
            python_cmd=python_cmd,
            timeout_seconds=timeout_seconds,
            tolerance=tolerance,
        )
        stage1_record = _record(instance, model, run_dir, metadata, eval_mode=EVAL_MODE_TWO_STAGE, stage="stage1_solve")
        records.append(stage1_record)
    stage2_key = (model, instance.instance_key, EVAL_MODE_TWO_STAGE, "stage2_extraction")
    if stage2_key not in completed:
        needs_stage2 = dry_run or not _record_succeeded(stage1_record)
        if needs_stage2:
            run_dir, metadata = run_instance(
                instance,
                model=model,
                base_url=base_url,
                api_key=api_key,
                api_key_env=api_key_env,
                include_canonical=include_canonical,
                response_contract=RESPONSE_CONTRACT_EXTRACTION_JSON,
                input_mode=INPUT_MODE_MULTIMODAL,
                temperature=temperature,
                max_tokens=stage2_max_tokens,
                verify_ssl=verify_ssl,
                output_root=run_output_dir,
                dry_run=dry_run,
                python_cmd=python_cmd,
                timeout_seconds=timeout_seconds,
                tolerance=tolerance,
            )
            records.append(_record(instance, model, run_dir, metadata, eval_mode=EVAL_MODE_TWO_STAGE, stage="stage2_extraction"))
        else:
            records.append(
                {
                    **instance.metadata(),
                    "model": model,
                    "run_dir": None,
                    "eval_mode": EVAL_MODE_TWO_STAGE,
                    "stage": "stage2_extraction",
                    "skipped": True,
                    "skip_reason": "stage1_passed",
                    "assistant_json_valid": False,
                    "diagnosis_primary_failure_stage": "skipped",
                }
            )
    return records


def _record(
    instance: BenchmarkInstance,
    model: str,
    run_dir: Path,
    metadata: dict[str, Any],
    *,
    eval_mode: str,
    stage: str,
) -> dict[str, Any]:
    return {
        **instance.metadata(),
        "model": model,
        "run_dir": str(run_dir),
        "eval_mode": eval_mode,
        "stage": stage,
        "response_contract": metadata.get("response_contract"),
        "input_mode": metadata.get("input_mode"),
        "assistant_json_valid": metadata.get("assistant_json_valid", False),
        "diagnosis_primary_failure_stage": metadata.get("diagnosis_primary_failure_stage"),
    }


def _new_eval_dir(output_dir: str | Path, instances: tuple[BenchmarkInstance, ...], models: list[str], eval_mode: str) -> Path:
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    family_tag = instances[0].family if len({instance.family for instance in instances}) == 1 else "mixed"
    model_tag = "multi" if len(models) != 1 else sanitize_name(models[0])
    return create_output_dir(output_dir, f"{timestamp}_{family_tag}_{model_tag}_{sanitize_name(eval_mode)}")


def _build_config(
    instances: tuple[BenchmarkInstance, ...],
    models: list[str],
    *,
    eval_mode: str,
    response_contract: str,
    include_canonical: bool,
    dry_run: bool,
    base_url: str,
    api_key_env: str,
    temperature: float,
    max_tokens: int,
    stage1_max_tokens: int,
    stage2_max_tokens: int,
    extraction_max_tokens: int,
    downstream_max_tokens: int,
    verify_ssl: bool,
    output_dir: str | Path,
    run_output_dir: str | Path,
    python_cmd: str,
    timeout_seconds: int,
    tolerance: float,
) -> dict[str, Any]:
    config = {
        "eval_mode": eval_mode,
        "instance_count": len(instances),
        "instance_keys": [instance.instance_key for instance in instances],
        "models": models,
        "response_contract": response_contract,
        "include_canonical": include_canonical,
        "dry_run": dry_run,
        "base_url": base_url,
        "api_key_env": api_key_env,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stage1_max_tokens": stage1_max_tokens,
        "stage2_max_tokens": stage2_max_tokens,
        "extraction_max_tokens": extraction_max_tokens,
        "downstream_max_tokens": downstream_max_tokens,
        "verify_ssl": verify_ssl,
        "output_dir": str(Path(output_dir).expanduser().resolve()),
        "run_output_dir": str(Path(run_output_dir).expanduser().resolve()),
        "python_cmd": python_cmd,
        "timeout_seconds": timeout_seconds,
        "tolerance": tolerance,
        "instance_origin_counts": _origin_counts(instances),
    }
    local_instance_dirs = {
        instance.instance_key: str(Path(instance.source_dir).expanduser().resolve())
        for instance in instances
        if instance.origin == "local" and instance.source_dir is not None
    }
    if local_instance_dirs:
        config["local_instance_dirs"] = local_instance_dirs
    return config


def _origin_counts(instances: tuple[BenchmarkInstance, ...]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for instance in instances:
        counts[instance.origin] = counts.get(instance.origin, 0) + 1
    return counts


def _rewrite_outputs(eval_dir: Path, records: list[dict[str, Any]]) -> None:
    manifest = eval_dir / "manifest.jsonl"
    with manifest.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    save_json(eval_dir / "summary.json", summarize_records(records))
    (eval_dir / "summary.md").write_text(build_summary_markdown(eval_dir.name, records), encoding="utf-8")


def _read_manifest(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


def _completed_record_keys(records: list[dict[str, Any]]) -> set[tuple[str, str, str, str]]:
    return set(_completed_record_map(records))


def _completed_record_map(records: list[dict[str, Any]]) -> dict[tuple[str, str, str, str], dict[str, Any]]:
    return {
        (
            str(record.get("model")),
            str(record.get("instance_key")),
            str(record.get("eval_mode")),
            str(record.get("stage", "solve")),
        ): record
        for record in records
    }


def _record_succeeded(record: dict[str, Any] | None) -> bool:
    if record is None:
        return False
    stage = record.get("diagnosis_primary_failure_stage")
    return stage in {None, "success"}


def _load_verified_extraction_payload(record: dict[str, Any]) -> dict[str, Any]:
    run_dir = record.get("run_dir")
    if not run_dir:
        raise ValueError("Verified extraction record has no run_dir.")
    payload, response_contract = _load_assistant_payload(run_dir, response_contract=RESPONSE_CONTRACT_EXTRACTION_JSON)
    if response_contract != RESPONSE_CONTRACT_EXTRACTION_JSON or not isinstance(payload, dict):
        raise ValueError("Verified extraction payload is unavailable or malformed.")
    return payload


def _provider_empty_diagnosis(
    instance: BenchmarkInstance,
    target: str | Path,
    response_contract: str,
) -> dict[str, Any] | None:
    response = _load_response_json(target)
    if response is None:
        return None
    provider_failure = classify_provider_empty_content(response)
    if provider_failure is None:
        return None
    return {
        "case_id": instance.instance_id,
        "instance_id": instance.instance_id,
        "response_contract": response_contract,
        "assistant_json_valid": False,
        "primary_failure_stage": "response_schema_error",
        "summary": "The provider returned no assistant text despite nonzero completion tokens.",
        **provider_failure,
    }


def _instances_from_config(config: dict[str, Any]) -> tuple[BenchmarkInstance, ...]:
    if "instance_keys" in config:
        benchmark = Benchmark()
        local_dirs = config.get("local_instance_dirs", {})
        local_count = int(config.get("instance_origin_counts", {}).get("local", 0))
        if local_count > len(local_dirs):
            family_dir = config.get("family_dir")
            if not family_dir:
                raise ValueError("Cannot restore local instances: config.json has no source directories.")
            local_instances = ArtifactBenchmark().instances(
                family_dir=family_dir,
                difficulty=config.get("difficulty"),
                problem=config.get("problem"),
                max_instances=config.get("limit"),
            )
            local_dirs = {instance.instance_key: instance.source_dir for instance in local_instances}
        instances: list[BenchmarkInstance] = []
        for key_value in config["instance_keys"]:
            key = str(key_value)
            if key in local_dirs:
                family, problem, difficulty, _ = parse_instance_key(key)
                instance = ArtifactBenchmark().instance_from_dir(
                    local_dirs[key], family=family, problem=problem, difficulty=difficulty
                )
                if instance.instance_key != key:
                    raise ValueError(f"Local instance path no longer matches {key}.")
                instances.append(instance)
            elif local_count and not config.get("local_instance_dirs"):
                raise ValueError(f"Cannot restore local instance source: {key}.")
            else:
                instances.append(benchmark.instance(key))
        return tuple(instances)
    family_dir = config.get("family_dir")
    if family_dir:
        return ArtifactBenchmark().instances(
            family_dir=family_dir,
            difficulty=config.get("difficulty"),
            problem=config.get("problem"),
            max_instances=config.get("limit"),
        )
    raise ValueError("Cannot infer instances from config.json.")


def _load_assistant_payload(
    target: str | Path,
    *,
    response_contract: str | None = None,
) -> tuple[dict[str, Any] | None, str]:
    path = Path(target).expanduser().resolve()
    if path.is_dir():
        metadata = _read_json(path / "metadata.json") if (path / "metadata.json").is_file() else {}
        contract = response_contract or str(metadata.get("response_contract", RESPONSE_CONTRACT_MINIMAL_SECTIONS))
        if (path / "assistant.json").is_file():
            return _read_json(path / "assistant.json"), contract
        if (path / "assistant.txt").is_file():
            return parse_assistant_payload((path / "assistant.txt").read_text(encoding="utf-8"), contract), contract
        if (path / "response.json").is_file():
            response = _read_json(path / "response.json")
            return parse_assistant_payload(extract_assistant_text(response), contract), contract
        return None, contract
    if path.name == "response.json":
        response = _read_json(path)
        contract = response_contract or RESPONSE_CONTRACT_MINIMAL_SECTIONS
        return parse_assistant_payload(extract_assistant_text(response), contract), contract
    if path.suffix == ".json":
        payload = _read_json(path)
        return payload if isinstance(payload, dict) else None, response_contract or RESPONSE_CONTRACT_MINIMAL_SECTIONS
    text = path.read_text(encoding="utf-8")
    contract = response_contract or RESPONSE_CONTRACT_MINIMAL_SECTIONS
    return parse_assistant_payload(text, contract), contract


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_response_json(target: str | Path) -> dict[str, Any] | None:
    path = Path(target).expanduser().resolve()
    candidate = path / "response.json" if path.is_dir() else path
    if not candidate.is_file() or candidate.name != "response.json":
        return None
    payload = json.loads(candidate.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None
