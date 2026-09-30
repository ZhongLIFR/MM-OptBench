from __future__ import annotations

import base64
import json
import mimetypes
from pathlib import Path
from typing import Any

from .instances import ArtifactFile, BenchmarkInstance

RESPONSE_CONTRACT_FULLSOLVE_JSON = "fullsolve_json"
RESPONSE_CONTRACT_MINIMAL_SECTIONS = "minimal_sections"
RESPONSE_CONTRACT_EXTRACTION_JSON = "extraction_json"
INPUT_MODE_MULTIMODAL = "multimodal"
INPUT_MODE_ORACLE_READING = "oracle_reading"
INPUT_MODE_VERIFIED_EXTRACTION = "verified_extraction"

_PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"

FULL_SOLVE_SCHEMA = (_PROMPT_DIR / "fullsolve_json.txt").read_text(encoding="utf-8")

MINIMAL_SECTION_SPEC = (_PROMPT_DIR / "solve.txt").read_text(encoding="utf-8")

EXTRACTION_JSON_SCHEMA = (_PROMPT_DIR / "extraction.txt").read_text(encoding="utf-8")

SYSTEM_PROMPT = (_PROMPT_DIR / "system.txt").read_text(encoding="utf-8").rstrip("\n")


def build_instance_text(
    instance: BenchmarkInstance,
    *,
    include_canonical: bool = False,
    response_contract: str = RESPONSE_CONTRACT_MINIMAL_SECTIONS,
    input_mode: str = INPUT_MODE_MULTIMODAL,
    conditioning_payload: dict[str, Any] | None = None,
) -> str:
    task_input = instance.text("task_input.txt").strip()
    parts = [f"Case ID: {instance.instance_id}", ""]
    if input_mode == INPUT_MODE_MULTIMODAL:
        visuals = instance.visuals()
        if not visuals:
            raise ValueError(f"No visuals found for {instance.instance_key}.")
        parts.extend(
            [
                "You will receive a benchmark optimization instance via text plus one or more attached visuals.",
                "Use all provided modalities jointly, and treat the visuals as a primary source of instance-specific data.",
                _instance_task_description(response_contract, input_mode),
                "",
                "Task statement:",
                task_input,
                "",
                "Attached visuals in order:",
                *[f"- {artifact.name}" for artifact in visuals],
                "",
                "Output requirements:",
                _output_requirements(response_contract),
            ]
        )
    else:
        if conditioning_payload is None:
            conditioning_payload = build_oracle_conditioning_payload(instance)
        prompt_payload = build_conditioning_prompt_payload(conditioning_payload)
        structured_instance = prompt_payload.get("structured_instance")
        if not isinstance(structured_instance, dict):
            raise ValueError("Conditioning payload is missing a valid structured_instance object.")
        usage_notes = build_conditioning_usage_notes(structured_instance)
        if input_mode == INPUT_MODE_ORACLE_READING:
            source_description = "a verified ground-truth public-instance payload"
            source_label = "ground-truth public instance"
        elif input_mode == INPUT_MODE_VERIFIED_EXTRACTION:
            source_description = "a verified extracted public-instance payload"
            source_label = "verified extraction"
        else:
            source_description = "a verified structured public-instance payload"
            source_label = "verified public instance"
        parts.extend(
            [
                f"You will receive a benchmark optimization instance via the task statement plus {source_description}.",
                "Treat the supplied payload as authoritative public data for this case.",
                _instance_task_description(response_contract, input_mode),
                "",
                "Structured-payload usage rules:",
                *[f"- {note}" for note in usage_notes],
                "",
                f"Structured public-instance payload ({source_label}):",
                json.dumps(prompt_payload, ensure_ascii=False, indent=2, sort_keys=True),
                "",
                "Original benchmark wording for context only:",
                "Use it for objective/task phrasing only. If it duplicates, paraphrases, or conflicts with the structured payload, the structured payload wins.",
                task_input,
                "",
                "Output requirements:",
                _output_requirements(response_contract),
            ]
        )
    if include_canonical and instance.has_file("canonical_specification.txt"):
        parts.extend(
            [
                "",
                "Additional reference text supplied for ablation/debugging only:",
                instance.text("canonical_specification.txt").strip(),
            ]
        )
    return "\n".join(parts)


def build_instance_messages(
    instance: BenchmarkInstance,
    *,
    include_canonical: bool = False,
    response_contract: str = RESPONSE_CONTRACT_MINIMAL_SECTIONS,
    input_mode: str = INPUT_MODE_MULTIMODAL,
    conditioning_payload: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": build_instance_text(
                instance,
                include_canonical=include_canonical,
                response_contract=response_contract,
                input_mode=input_mode,
                conditioning_payload=conditioning_payload,
            ),
        }
    ]
    if input_mode == INPUT_MODE_MULTIMODAL:
        for visual in instance.visuals():
            content.append({"type": "image_url", "image_url": {"url": image_artifact_to_data_url(visual)}})
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": content},
    ]


def build_oracle_conditioning_payload(instance: BenchmarkInstance) -> dict[str, Any]:
    instance_data = instance.json("ground_truth/instance_data.json")
    return {
        "case_id": instance.instance_id,
        "problem_type": instance.problem,
        "extracted_data": {
            "structured_instance": instance_data,
            "assumptions": [],
            "uncertain_or_missing": [],
        },
    }


def build_verified_conditioning_payload(case_id: str, extraction_payload: dict[str, Any]) -> dict[str, Any]:
    extracted_data = extraction_payload.get("extracted_data")
    if not isinstance(extracted_data, dict):
        raise ValueError("Verified extraction payload is missing extracted_data.")
    structured_instance = extracted_data.get("structured_instance")
    if not isinstance(structured_instance, dict) or not structured_instance:
        raise ValueError("Verified extraction payload is missing extracted_data.structured_instance.")
    assumptions = extracted_data.get("assumptions")
    uncertain_or_missing = extracted_data.get("uncertain_or_missing")
    return {
        "case_id": str(extraction_payload.get("case_id") or case_id),
        "problem_type": str(extraction_payload.get("problem_type") or ""),
        "extracted_data": {
            "structured_instance": structured_instance,
            "assumptions": assumptions if isinstance(assumptions, list) else [],
            "uncertain_or_missing": uncertain_or_missing if isinstance(uncertain_or_missing, list) else [],
        },
    }


def compact_structured_instance_for_prompt(structured_instance: dict[str, Any]) -> dict[str, Any]:
    compact = json.loads(json.dumps(structured_instance, ensure_ascii=False))
    for key in (
        "visual_encoding",
        "visual_settings",
        "positions",
        "coordinates",
        "meta_parameters",
        "scenario_name",
        "graph_type",
        "variant",
        "difficulty",
        "family",
        "subtype",
        "demands",
    ):
        if key == "demands" and "net_supply_by_node_period" not in compact:
            continue
        compact.pop(key, None)
    if (
        "capacities_by_arc_period" in compact
        and "routing_costs_by_arc_period" in compact
        and isinstance(compact.get("indices"), dict)
        and isinstance(compact["indices"].get("arc_to_endpoints"), dict)
    ):
        compact.pop("arcs", None)
    return compact


def build_conditioning_prompt_payload(conditioning_payload: dict[str, Any]) -> dict[str, Any]:
    structured_instance = _extract_structured_instance(conditioning_payload)
    if not structured_instance:
        raise ValueError("Conditioning payload is missing extracted_data.structured_instance.")
    compact_instance = compact_structured_instance_for_prompt(structured_instance)
    extracted_data = conditioning_payload.get("extracted_data")
    assumptions: list[Any] = []
    uncertain_or_missing: list[Any] = []
    if isinstance(extracted_data, dict):
        raw_assumptions = extracted_data.get("assumptions")
        raw_uncertain = extracted_data.get("uncertain_or_missing")
        if isinstance(raw_assumptions, list):
            assumptions = raw_assumptions
        if isinstance(raw_uncertain, list):
            uncertain_or_missing = raw_uncertain
    prompt_payload: dict[str, Any] = {
        "problem_type": str(conditioning_payload.get("problem_type") or ""),
        "structured_instance": compact_instance,
    }
    semantic_conventions = build_conditioning_semantic_conventions(structured_instance)
    if semantic_conventions:
        prompt_payload["semantic_conventions"] = semantic_conventions
    if assumptions:
        prompt_payload["assumptions"] = assumptions
    if uncertain_or_missing:
        prompt_payload["uncertain_or_missing"] = uncertain_or_missing
    return prompt_payload


def build_conditioning_semantic_conventions(structured_instance: dict[str, Any]) -> dict[str, Any]:
    conventions: dict[str, Any] = {}
    indices = structured_instance.get("indices")
    if isinstance(indices, dict) and isinstance(indices.get("period_order"), list):
        conventions["ordered_indices"] = {
            "periods": [str(period) for period in indices["period_order"]],
            "labels_are_identifiers": True,
        }
    elif isinstance(structured_instance.get("periods"), list):
        conventions["ordered_indices"] = {
            "periods": [str(period) for period in structured_instance["periods"]],
            "labels_are_identifiers": True,
        }
    if "net_supply_by_node_period" in structured_instance:
        conventions["signed_balance_convention"] = {
            "positive": "net_supply",
            "negative": "net_demand",
            "preserve_signs_exactly": True,
            "canonical_balance_form": "outflow_minus_inflow_equals_net_supply_with_inventory_adjustments_if_present",
            "do_not_flip_equation_orientation": True,
            "positive_values_require_net_outflow": True,
            "negative_values_require_net_inflow": True,
        }
    if any(key in structured_instance for key in ("capacities_by_arc_period", "routing_costs_by_arc_period", "storage")):
        conventions["canonical_numeric_tables"] = {
            "use_machine_readable_tables_directly": True,
            "do_not_reparse_visual_label_strings_when_equivalent_numeric_fields_exist": True,
        }
    return conventions


def build_conditioning_usage_notes(structured_instance: dict[str, Any]) -> list[str]:
    notes = [
        "Use the machine-readable structured payload directly. Do not re-parse duplicated descriptive text when an equivalent numeric field is already present.",
        "Treat labels and IDs as opaque identifiers unless the payload explicitly assigns them a numeric meaning.",
    ]
    periods = structured_instance.get("periods")
    indices = structured_instance.get("indices")
    if isinstance(indices, dict) and isinstance(indices.get("period_order"), list):
        notes.append("Use the provided `indices.period_order` as the authoritative temporal order; do not infer order or predecessor periods by slicing label strings such as `t[:-1]`, `int(t[1]) - 1`, or similar label arithmetic.")
    elif isinstance(periods, list):
        notes.append("Use the provided `periods` list as the authoritative temporal order; do not infer order or predecessor periods by slicing label strings such as `t[:-1]`, `int(t[1]) - 1`, or similar label arithmetic.")
    if "net_supply_by_node_period" in structured_instance:
        notes.append("For signed node-balance tables such as `net_supply_by_node_period`, preserve the sign convention exactly: positive values mean net supply and negative values mean net demand.")
        notes.append("When translating signed balance tables into conservation constraints, do not flip the equation orientation; use the payload's convention directly.")
    if any(key in structured_instance for key in ("capacities_by_arc_period", "routing_costs_by_arc_period", "storage")):
        notes.append("If canonical per-index numeric tables are present, prefer those tables over alternate descriptive encodings or visual-label formats.")
    return notes


def _extract_structured_instance(payload: dict[str, Any]) -> dict[str, Any]:
    extracted_data = payload.get("extracted_data")
    if isinstance(extracted_data, dict) and isinstance(extracted_data.get("structured_instance"), dict):
        return extracted_data["structured_instance"]
    structured_instance = payload.get("structured_instance")
    if isinstance(structured_instance, dict):
        return structured_instance
    return {}


def image_artifact_to_data_url(artifact: ArtifactFile) -> str:
    if artifact.kind != "binary" or not isinstance(artifact.content, bytes):
        raise TypeError(f"Visual artifact is not binary bytes: {artifact.relative_path}")
    mime_type = mimetypes.guess_type(artifact.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(artifact.content).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _output_requirements(response_contract: str) -> str:
    if response_contract == RESPONSE_CONTRACT_MINIMAL_SECTIONS:
        return MINIMAL_SECTION_SPEC
    if response_contract == RESPONSE_CONTRACT_EXTRACTION_JSON:
        return EXTRACTION_JSON_SCHEMA
    if response_contract == RESPONSE_CONTRACT_FULLSOLVE_JSON:
        return FULL_SOLVE_SCHEMA
    raise ValueError(f"Unsupported response contract: {response_contract}")


def _instance_task_description(response_contract: str, input_mode: str) -> str:
    if response_contract == RESPONSE_CONTRACT_EXTRACTION_JSON:
        return "Your task is extraction only: recover the instance-specific structured data faithfully from the text and visuals."
    if input_mode == INPUT_MODE_ORACLE_READING:
        return "Your task is downstream solving only: use the verified public instance payload to formulate the model and write runnable Python code."
    if input_mode == INPUT_MODE_VERIFIED_EXTRACTION:
        return "Your task is downstream solving only: use the verified extracted public instance payload to formulate the model and write runnable Python code. Do not re-infer the instance from visuals."
    return "Your task is end-to-end full solving: understand the instance, formulate the model, and write runnable Python code."
