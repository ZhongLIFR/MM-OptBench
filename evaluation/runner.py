from __future__ import annotations

import datetime as dt
import json
import os
import re
import ssl
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Iterable

from .diagnosis import diagnose_extraction_result, diagnose_instance_result
from .instances import BenchmarkInstance
from .prompts import (
    INPUT_MODE_MULTIMODAL,
    RESPONSE_CONTRACT_EXTRACTION_JSON,
    RESPONSE_CONTRACT_FULLSOLVE_JSON,
    RESPONSE_CONTRACT_MINIMAL_SECTIONS,
    build_instance_messages,
)
from .scoring import make_json_safe, strip_response_wrappers

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_API_KEY_ENV = "OPENAI_API_KEY"
MAX_API_COMPLETION_TOKENS = 32768


def run_instance(
    instance: BenchmarkInstance,
    *,
    model: str,
    base_url: str = DEFAULT_BASE_URL,
    api_key: str | None = None,
    api_key_env: str = DEFAULT_API_KEY_ENV,
    include_canonical: bool = False,
    response_contract: str = RESPONSE_CONTRACT_MINIMAL_SECTIONS,
    input_mode: str = INPUT_MODE_MULTIMODAL,
    conditioning_payload: dict[str, Any] | None = None,
    temperature: float = 0.0,
    max_tokens: int = MAX_API_COMPLETION_TOKENS,
    verify_ssl: bool = True,
    output_root: str | Path = "output/mmopt_runs",
    dry_run: bool = False,
    python_cmd: str = sys.executable,
    timeout_seconds: int = 1800,
    tolerance: float = 1e-6,
) -> tuple[Path, dict[str, Any]]:
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = create_output_dir(
        output_root,
        f"{timestamp}_{instance.instance_id}_{sanitize_name(model)}_{sanitize_name(response_contract)}",
    )
    messages = build_instance_messages(
        instance,
        include_canonical=include_canonical,
        response_contract=response_contract,
        input_mode=input_mode,
        conditioning_payload=conditioning_payload,
    )
    request_payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        _completion_token_limit_field(base_url): max_tokens,
    }
    save_json(output_dir / "request.json", request_payload)
    metadata = {
        **instance.metadata(),
        "model_requested": model,
        "response_contract": response_contract,
        "input_mode": input_mode,
        "include_canonical": include_canonical,
        "dry_run": dry_run,
    }
    if dry_run:
        metadata["assistant_json_valid"] = False
        save_json(output_dir / "metadata.json", metadata)
        return output_dir, metadata
    key = api_key or os.environ.get(api_key_env)
    if not key:
        raise RuntimeError(f"Missing API key. Pass api_key or set {api_key_env}.")
    response = chat_completion(
        base_url=base_url,
        api_key=key,
        payload=request_payload,
        verify_ssl=verify_ssl,
    )
    save_json(output_dir / "response.json", response)
    assistant_text = extract_assistant_text(response)
    (output_dir / "assistant.txt").write_text(assistant_text, encoding="utf-8")
    assistant_payload = parse_assistant_payload(assistant_text, response_contract)
    if assistant_payload is not None:
        save_json(output_dir / "assistant.json", assistant_payload)
    metadata["assistant_json_valid"] = assistant_payload is not None
    metadata["model_returned"] = response.get("model")
    metadata["finish_reason"] = extract_finish_reason(response)
    metadata["completion_tokens"] = extract_completion_tokens(response)
    provider_failure = classify_provider_empty_content(response) if assistant_payload is None else None
    if provider_failure is not None:
        diagnosis = {
            "case_id": instance.instance_id,
            "instance_id": instance.instance_id,
            "primary_failure_stage": "response_schema_error",
            "summary": "The provider returned no assistant text despite nonzero completion tokens.",
            **provider_failure,
        }
        metadata.update(provider_failure)
    elif response_contract == RESPONSE_CONTRACT_EXTRACTION_JSON:
        diagnosis = diagnose_extraction_result(instance, assistant_payload, tolerance=tolerance)
    else:
        diagnosis = diagnose_instance_result(
            instance,
            assistant_payload,
            response_contract=response_contract,
            python_cmd=python_cmd,
            timeout_seconds=timeout_seconds,
            tolerance=tolerance,
        )
    save_json(output_dir / "diagnosis.json", diagnosis)
    metadata["diagnosis_primary_failure_stage"] = diagnosis.get("primary_failure_stage")
    save_json(output_dir / "metadata.json", metadata)
    return output_dir, metadata


def evaluate(
    instances: Iterable[BenchmarkInstance],
    *,
    models: list[str],
    base_url: str = DEFAULT_BASE_URL,
    api_key: str | None = None,
    api_key_env: str = DEFAULT_API_KEY_ENV,
    include_canonical: bool = False,
    response_contract: str = RESPONSE_CONTRACT_MINIMAL_SECTIONS,
    input_mode: str = INPUT_MODE_MULTIMODAL,
    temperature: float = 0.0,
    max_tokens: int = MAX_API_COMPLETION_TOKENS,
    verify_ssl: bool = True,
    output_dir: str | Path = "output/mmopt_eval",
    run_output_dir: str | Path = "output/mmopt_runs",
    dry_run: bool = False,
    python_cmd: str = sys.executable,
    timeout_seconds: int = 1800,
    tolerance: float = 1e-6,
) -> Path:
    instance_tuple = tuple(instances)
    if not instance_tuple:
        raise ValueError("No instances selected for evaluation.")
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    family_tag = instance_tuple[0].family if len({instance.family for instance in instance_tuple}) == 1 else "mixed"
    model_tag = "multi" if len(models) != 1 else sanitize_name(models[0])
    eval_dir = create_output_dir(
        output_dir, f"{timestamp}_{family_tag}_{model_tag}_{sanitize_name(response_contract)}"
    )
    config = {
        "eval_mode": input_mode,
        "instance_count": len(instance_tuple),
        "instance_keys": [instance.instance_key for instance in instance_tuple],
        "models": models,
        "response_contract": response_contract,
        "input_mode": input_mode,
        "include_canonical": include_canonical,
        "dry_run": dry_run,
        "instance_origin_counts": _origin_counts(instance_tuple),
    }
    save_json(eval_dir / "config.json", config)
    records: list[dict[str, Any]] = []
    for model in models:
        for instance in instance_tuple:
            run_dir, metadata = run_instance(
                instance,
                model=model,
                base_url=base_url,
                api_key=api_key,
                api_key_env=api_key_env,
                include_canonical=include_canonical,
                response_contract=response_contract,
                input_mode=input_mode,
                temperature=temperature,
                max_tokens=max_tokens,
                verify_ssl=verify_ssl,
                output_root=run_output_dir,
                dry_run=dry_run,
                python_cmd=python_cmd,
                timeout_seconds=timeout_seconds,
                tolerance=tolerance,
            )
            record = {
                **instance.metadata(),
                "model": model,
                "run_dir": str(run_dir),
                "eval_mode": input_mode,
                "response_contract": response_contract,
                "assistant_json_valid": metadata.get("assistant_json_valid", False),
                "diagnosis_primary_failure_stage": metadata.get("diagnosis_primary_failure_stage"),
            }
            records.append(record)
            with (eval_dir / "manifest.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    save_json(eval_dir / "summary.json", summarize_records(records))
    (eval_dir / "summary.md").write_text(build_summary_markdown(eval_dir.name, records), encoding="utf-8")
    return eval_dir


def chat_completion(*, base_url: str, api_key: str, payload: dict[str, Any], verify_ssl: bool = True) -> dict[str, Any]:
    url = base_url.rstrip("/") + "/chat/completions"
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        method="POST",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        data=data,
    )
    context = None if verify_ssl else ssl._create_unverified_context()
    last_error: BaseException | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=600, context=context) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            last_error = RuntimeError(f"HTTP {exc.code} for {url}\n{body}")
            if exc.code not in {408, 409, 425, 429, 500, 502, 503, 504}:
                break
        except urllib.error.URLError as exc:
            last_error = RuntimeError(f"Network error for {url}: {exc}")
        if attempt < 2:
            time.sleep(min(8, 2**attempt))
    assert last_error is not None
    raise last_error


def _completion_token_limit_field(base_url: str) -> str:
    """Return the token-limit field expected by the target chat-completions endpoint."""
    normalized = base_url.rstrip("/").lower()
    if normalized == "https://api.openai.com/v1":
        return "max_completion_tokens"
    return "max_tokens"


def parse_assistant_payload(text: str, response_contract: str) -> dict[str, Any] | None:
    if response_contract == RESPONSE_CONTRACT_MINIMAL_SECTIONS:
        parsed = parse_minimal_sections(text)
        if parsed is not None:
            return parsed
    if response_contract in {RESPONSE_CONTRACT_FULLSOLVE_JSON, RESPONSE_CONTRACT_EXTRACTION_JSON}:
        parsed = parse_json_payload(text)
        if parsed is not None:
            return parsed
    if response_contract == RESPONSE_CONTRACT_FULLSOLVE_JSON:
        return parse_minimal_sections(text)
    if response_contract == RESPONSE_CONTRACT_MINIMAL_SECTIONS:
        return parse_json_payload(text)
    if response_contract == RESPONSE_CONTRACT_EXTRACTION_JSON:
        return None
    raise ValueError(f"Unsupported response contract: {response_contract}")


def parse_minimal_sections(text: str) -> dict[str, Any] | None:
    stripped = strip_response_wrappers(text)
    if not stripped:
        return None
    pattern = re.compile(
        r"ASSUMPTIONS\s*(?P<assumptions>.*?)\s*MATHEMATICAL_MODEL\s*(?P<model>.*?)\s*PYTHON_CODE\s*(?P<code>.*)",
        re.DOTALL | re.IGNORECASE,
    )
    match = pattern.search(stripped)
    if not match:
        return None
    assumptions_text = match.group("assumptions").strip()
    model_block = match.group("model").strip()
    code_block = match.group("code").strip()
    code_match = re.search(r"```(?:python)?\s*(?P<code>.*?)```", code_block, flags=re.DOTALL | re.IGNORECASE)
    if code_match:
        code_block = code_match.group("code").strip()
    if assumptions_text.upper() == "NONE":
        assumptions: list[str] = []
    else:
        assumptions = [line.strip().lstrip("- ").strip() for line in assumptions_text.splitlines() if line.strip()]
    if not model_block or not code_block:
        return None
    return {
        "assumptions": assumptions,
        "math_model_markdown": model_block,
        "solver_code_python": code_block,
    }


def parse_json_payload(text: str) -> dict[str, Any] | None:
    stripped = strip_response_wrappers(text)
    if not stripped:
        return None
    candidates = [stripped]
    fenced_match = re.search(r"```json\s*(\{.*\})\s*```", stripped, flags=re.DOTALL | re.IGNORECASE)
    if fenced_match:
        candidates.append(fenced_match.group(1).strip())
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidates.append(stripped[start : end + 1].strip())
    seen: set[str] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def extract_assistant_text(response: dict[str, Any]) -> str:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        return extract_responses_output_text(response)
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        return extract_responses_output_text(response)
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "text":
                parts.append(str(item.get("text", "")))
        text = "\n".join(parts).strip()
        if text:
            return text
    return extract_responses_output_text(response)


def extract_responses_output_text(response: dict[str, Any]) -> str:
    parts: list[str] = []
    top_level_text = response.get("output_text")
    if isinstance(top_level_text, str) and top_level_text.strip():
        parts.append(top_level_text.strip())
    output = response.get("output")
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            item_type = str(item.get("type") or "")
            if item_type in {"output_text", "text"}:
                direct_text = item.get("text") or item.get("content")
                if isinstance(direct_text, str) and direct_text.strip():
                    parts.append(direct_text.strip())
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for chunk in content:
                if not isinstance(chunk, dict):
                    continue
                chunk_type = str(chunk.get("type") or "")
                if chunk_type not in {"output_text", "text", "input_text"}:
                    continue
                chunk_text = chunk.get("text") or chunk.get("content")
                if isinstance(chunk_text, str) and chunk_text.strip():
                    parts.append(chunk_text.strip())
    return "\n".join(parts).strip()


def extract_finish_reason(response: dict[str, Any]) -> str | None:
    choices = response.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        finish_reason = choices[0].get("finish_reason")
        return str(finish_reason) if finish_reason is not None else None
    status = response.get("status")
    return str(status) if isinstance(status, str) else None


def extract_completion_tokens(response: dict[str, Any]) -> int | None:
    usage = response.get("usage")
    if not isinstance(usage, dict):
        return None
    completion_tokens = usage.get("completion_tokens")
    if isinstance(completion_tokens, int):
        return completion_tokens
    output_tokens = usage.get("output_tokens")
    return int(output_tokens) if isinstance(output_tokens, int) else None


def classify_provider_empty_content(response: dict[str, Any]) -> dict[str, Any] | None:
    completion_tokens = extract_completion_tokens(response)
    if not isinstance(completion_tokens, int) or completion_tokens <= 0:
        return None
    assistant_text = extract_assistant_text(response).strip()
    if assistant_text:
        return None
    choices = response.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        if isinstance(message, dict) and message.get("content") is None:
            return {
                "schema_failure_subtype": "provider_empty_content",
                "schema_failure_hints": [
                    "provider returned completion tokens but assistant message.content was null",
                    f"completion_tokens={completion_tokens}",
                ],
            }
    output = response.get("output")
    if isinstance(output, list) and not output:
        return {
            "schema_failure_subtype": "provider_empty_content",
            "schema_failure_hints": [
                "provider returned output tokens but the responses-style output array was empty",
                f"completion_tokens={completion_tokens}",
            ],
        }
    return None


def create_output_dir(root: str | Path, name: str) -> Path:
    root = Path(root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    # Atomic allocation keeps concurrent runs and same-second retries separate.
    return Path(tempfile.mkdtemp(prefix=f"{name}_", dir=root))


def save_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(make_json_safe(value), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def summarize_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "record_count": len(records),
        "assistant_json_valid_count": sum(1 for record in records if record.get("assistant_json_valid")),
        "instance_count": len({record.get("instance_key") for record in records}),
        "model_count": len({record.get("model") for record in records}),
        "mode_counts": _record_counts(records, "eval_mode"),
        "failure_stage_counts": _record_counts(records, "diagnosis_primary_failure_stage"),
    }


def build_summary_markdown(name: str, records: list[dict[str, Any]]) -> str:
    summary = summarize_records(records)
    return (
        f"# {name}\n\n"
        f"- Records: {summary['record_count']}\n"
        f"- Instances: {summary['instance_count']}\n"
        f"- Models: {summary['model_count']}\n"
        f"- Parsed assistant payloads: {summary['assistant_json_valid_count']}\n"
        f"- Modes: {json.dumps(summary['mode_counts'], ensure_ascii=False, sort_keys=True)}\n"
    )


def sanitize_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_") or "unnamed"


def _origin_counts(instances: tuple[BenchmarkInstance, ...]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for instance in instances:
        counts[instance.origin] = counts.get(instance.origin, 0) + 1
    return counts


def _record_counts(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        value = record.get(key)
        label = "none" if value is None else str(value)
        counts[label] = counts.get(label, 0) + 1
    return counts


def _finish_reason(response: dict[str, Any]) -> Any:
    return extract_finish_reason(response)
