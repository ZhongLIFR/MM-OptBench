from __future__ import annotations

import ast
import copy
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

RESPONSE_CONTRACT_FULLSOLVE_JSON = "fullsolve_json"
RESPONSE_CONTRACT_MINIMAL_SECTIONS = "minimal_sections"
RESPONSE_CONTRACT_EXTRACTION_JSON = "extraction_json"
REQUIRED_TOP_LEVEL_KEYS = ["case_id", "problem_type", "extracted_data", "mathematical_model", "math_model_markdown", "solving_approach", "solver_code_python", "validation_checks"]
MINIMAL_REQUIRED_KEYS = ["math_model_markdown", "solver_code_python"]
EXTRACTION_REQUIRED_KEYS = ["case_id", "problem_type", "extracted_data"]


def strip_response_wrappers(text: str) -> str:
    stripped = text.strip()
    for token in ("<|begin_of_box|>", "<|end_of_box|>", "<|begin_of_text|>", "<|end_of_text|>"):
        stripped = stripped.replace(token, "")
    return stripped.strip()


def check_schema(assistant_json: dict[str, Any], response_contract: str) -> dict[str, Any]:
    if response_contract == RESPONSE_CONTRACT_FULLSOLVE_JSON:
        required_keys = REQUIRED_TOP_LEVEL_KEYS
        allowed_keys = set(required_keys)
    elif response_contract == RESPONSE_CONTRACT_MINIMAL_SECTIONS:
        required_keys = MINIMAL_REQUIRED_KEYS
        allowed_keys = set(required_keys) | {"assumptions"}
    elif response_contract == RESPONSE_CONTRACT_EXTRACTION_JSON:
        required_keys = EXTRACTION_REQUIRED_KEYS
        allowed_keys = set(required_keys)
    else:
        required_keys = REQUIRED_TOP_LEVEL_KEYS
        allowed_keys = set(required_keys)
    missing = [key for key in required_keys if key not in assistant_json]
    extra = [key for key in assistant_json if key not in allowed_keys]
    return {
        "response_contract": response_contract,
        "required_keys_present": not missing,
        "missing_required_keys": missing,
        "extra_top_level_keys": extra,
    }


def to_number(value: Any) -> float | None:
    if isinstance(value, (int, float, str)):
        try:
            number = float(value)
        except (ValueError, OverflowError):
            return None
        return number if math.isfinite(number) else None
    return None


def has_nonfinite_number(value: Any) -> bool:
    if isinstance(value, dict):
        return any(has_nonfinite_number(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(has_nonfinite_number(item) for item in value)
    if isinstance(value, (int, float, str)):
        try:
            return not math.isfinite(float(value))
        except ValueError:
            return False
        except OverflowError:
            return True
    return False


def infer_case_subfamily(case_dir: Path | None) -> str:
    if case_dir is None:
        return ""
    try:
        return case_dir.parent.parent.name
    except IndexError:
        return ""


def infer_problem_type(
    *,
    case_dir: Path | None = None,
    ground_truth_instance: dict[str, Any] | None = None,
    assistant_json: dict[str, Any] | None = None,
) -> str:
    primary_candidates: list[Any] = []
    fallback_candidates: list[Any] = []
    if isinstance(ground_truth_instance, dict):
        primary_candidates.extend(
            [
                ground_truth_instance.get("problem_type"),
                ground_truth_instance.get("variant"),
            ]
        )
        fallback_candidates.append(ground_truth_instance.get("variant_type"))
    if isinstance(assistant_json, dict):
        primary_candidates.extend(
            [
                assistant_json.get("problem_type"),
                assistant_json.get("detected_problem_type"),
            ]
        )
        extracted = assistant_json.get("extracted_data")
        if isinstance(extracted, dict):
            structured = extracted.get("structured_instance")
            if isinstance(structured, dict):
                primary_candidates.extend(
                    [
                        structured.get("problem_type"),
                        structured.get("variant"),
                    ]
                )
                fallback_candidates.append(structured.get("variant_type"))
    for candidate in primary_candidates:
        text = str(candidate).strip() if candidate is not None else ""
        if text and text.lower() != "null":
            return text
    subfamily = infer_case_subfamily(case_dir)
    if subfamily:
        return subfamily
    for candidate in fallback_candidates:
        text = str(candidate).strip() if candidate is not None else ""
        if text and text.lower() != "null":
            return text
    return ""


def normalize_edge(edge: Any) -> tuple[int, int] | None:
    if isinstance(edge, (list, tuple)) and len(edge) == 2:
        try:
            a = int(edge[0])
            b = int(edge[1])
        except (TypeError, ValueError):
            return None
        return tuple(sorted((a, b)))
    return None


def derive_edges_from_adjacency_matrix(instance: dict[str, Any]) -> set[tuple[int, int]]:
    matrix = instance.get("adjacency_matrix")
    if not isinstance(matrix, list):
        return set()
    vertices = None
    if isinstance(instance.get("vertex_ids"), list):
        vertices = instance.get("vertex_ids")
    elif isinstance(instance.get("vertices"), list):
        vertices = instance.get("vertices")
    elif isinstance(instance.get("sets"), dict) and isinstance(instance["sets"].get("vertices"), list):
        vertices = instance["sets"]["vertices"]
    elif isinstance(instance.get("num_vertices"), int):
        vertices = list(range(1, instance["num_vertices"] + 1))
    elif isinstance(instance.get("n_vertices"), int):
        vertices = list(range(1, instance["n_vertices"] + 1))
    if not isinstance(vertices, list):
        n = len(matrix)
        vertices = list(range(1, n + 1))

    edges: set[tuple[int, int]] = set()
    for i, row in enumerate(matrix):
        if not isinstance(row, list):
            continue
        for j, cell in enumerate(row):
            if j <= i:
                continue
            if to_number(cell) == 1:
                try:
                    edges.add(tuple(sorted((int(vertices[i]), int(vertices[j])))))
                except (IndexError, TypeError, ValueError):
                    continue
    return edges


def extract_edge_set(instance: dict[str, Any]) -> set[tuple[int, int]]:
    edges = instance.get("edges")
    edge_set: set[tuple[int, int]] = set()
    if isinstance(edges, list):
        for edge in edges:
            normalized = normalize_edge(edge)
            if normalized is not None:
                edge_set.add(normalized)
    if edge_set:
        return edge_set
    return derive_edges_from_adjacency_matrix(instance)


def extract_arc_map(instance: dict[str, Any]) -> dict[tuple[int, int], float | None]:
    arc_map: dict[tuple[int, int], float | None] = {}
    arcs = instance.get("arcs")
    if not isinstance(arcs, list):
        return arc_map
    for arc in arcs:
        if not isinstance(arc, dict):
            continue
        try:
            key = (int(arc["from"]), int(arc["to"]))
        except (KeyError, TypeError, ValueError):
            continue
        arc_map[key] = to_number(arc.get("capacity"))
    return arc_map


def extract_group_map(instance: dict[str, Any]) -> dict[str, dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    subsets = instance.get("subsets")
    if isinstance(subsets, dict):
        for gid, payload in subsets.items():
            if not isinstance(payload, dict):
                continue
            elements = payload.get("elements", [])
            if not isinstance(elements, list):
                continue
            groups[str(gid)] = {
                "elements": tuple(sorted(str(x) for x in elements)),
                "weight": to_number(payload.get("weight")),
            }
        if groups:
            return groups

    raw_groups = instance.get("groups")
    if isinstance(raw_groups, list):
        for payload in raw_groups:
            if not isinstance(payload, dict):
                continue
            gid = payload.get("id")
            elements = payload.get("items") or payload.get("elements")
            if gid is None or not isinstance(elements, list):
                continue
            groups[str(gid)] = {
                "elements": tuple(sorted(str(x) for x in elements)),
                "weight": to_number(payload.get("value") if "value" in payload else payload.get("weight")),
            }
    return groups


def extract_named_list(instance: dict[str, Any], key: str) -> list[Any]:
    if isinstance(instance.get(key), list):
        return instance[key]
    if isinstance(instance.get("sets"), dict) and isinstance(instance["sets"].get(key), list):
        return instance["sets"][key]
    return []


def unwrap_solution_dict(output: Any) -> dict[str, Any] | None:
    if not isinstance(output, dict):
        return None
    solution = output.get("solution")
    if isinstance(solution, dict):
        return solution
    return output


def extract_reported_objective(payload: dict[str, Any] | None, keys: tuple[str, ...]) -> float | None:
    if not isinstance(payload, dict):
        return None
    for key in keys:
        if key in payload:
            value = to_number(payload.get(key))
            if value is not None:
                return value
    return None


def normalize_partition_nodes(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple, set)):
        return []
    normalized: list[str] = []
    for item in value:
        numeric = to_number(item)
        if numeric is not None and float(numeric).is_integer():
            normalized.append(str(int(numeric)))
        elif numeric is not None:
            normalized.append(str(float(numeric)))
        else:
            normalized.append(str(item))
    return normalized


def extract_max_flow_value(payload: dict[str, Any] | None) -> float | None:
    return extract_reported_objective(
        payload,
        (
            "max_flow",
            "maximum_flow",
            "maximum_flow_value",
            "max_flow_value",
            "flow_value",
            "objective_exact",
            "objective_value",
            "minimum_cut_value",
            "cut_value",
        ),
    )


def extract_max_flow_cut_partition(payload: dict[str, Any] | None) -> dict[str, list[str]]:
    if not isinstance(payload, dict):
        return {"S": [], "T": []}
    for key in ("min_cut", "minimum_cut", "minimum_cut_partition", "min_cut_partition", "min_cut_set"):
        raw = payload.get(key)
        if isinstance(raw, dict) and not any(name in raw for name in ("S", "T", "source_side", "sink_side", "source_partition", "sink_partition")):
            raw = raw.get("partition", raw)
        if isinstance(raw, (list, tuple)) and len(raw) == 2 and all(isinstance(side, (list, tuple, set)) for side in raw):
            return {"S": normalize_partition_nodes(raw[0]), "T": normalize_partition_nodes(raw[1])}
        if not isinstance(raw, dict):
            continue
        source_side = normalize_partition_nodes(
            raw.get("S")
            if "S" in raw
            else raw.get("source_side")
            if "source_side" in raw
            else raw.get("source_partition")
        )
        sink_side = normalize_partition_nodes(
            raw.get("T")
            if "T" in raw
            else raw.get("sink_side")
            if "sink_side" in raw
            else raw.get("sink_partition")
        )
        if source_side or sink_side:
            return {"S": source_side, "T": sink_side}
    source_side = normalize_partition_nodes(
        payload.get("min_cut_S")
        if "min_cut_S" in payload
        else payload.get("minimum_cut_S")
        if "minimum_cut_S" in payload
        else payload.get("cut_S")
        if "cut_S" in payload
        else payload.get("min_cut_set_S")
        if "min_cut_set_S" in payload
        else payload.get("source_side")
    )
    sink_side = normalize_partition_nodes(
        payload.get("min_cut_T")
        if "min_cut_T" in payload
        else payload.get("minimum_cut_T")
        if "minimum_cut_T" in payload
        else payload.get("cut_T")
        if "cut_T" in payload
        else payload.get("min_cut_set_T")
        if "min_cut_set_T" in payload
        else payload.get("sink_side")
    )
    return {"S": source_side, "T": sink_side}


def extract_max_flow_arc_mapping(payload: dict[str, Any] | None, errors: list[str] | None = None) -> dict[tuple[int, int], float]:
    if not isinstance(payload, dict):
        return {}
    errors = errors if errors is not None else []
    arc_flows: dict[tuple[int, int], float] = {}

    def add_flow(endpoint: Any, value: Any) -> None:
        numeric = to_number(value)
        parsed = parse_numeric_mapping_key(endpoint, arity=2)
        numbers = [to_number(part) for part in parsed] if parsed is not None else []
        if (numeric is None or len(numbers) != 2
                or any(number is None or not number.is_integer() for number in numbers)):
            errors.append(f"Invalid arc-flow entry {endpoint}:{value}")
            return
        arc = (int(numbers[0]), int(numbers[1]))
        if arc in arc_flows:
            errors.append(f"Duplicate arc-flow entry {arc}")
        arc_flows[arc] = numeric

    for key in (
        "arc_flows",
        "arc_flow",
        "flow_on_arc",
        "flow_on_arcs",
        "optimal_flow",
        "optimal_flows",
        "optimal_arc_flows",
        "optimal_flow_on_arcs",
        "flows",
        "flow",
        "flow_dict",
    ):
        if key not in payload:
            continue
        raw = payload.get(key)
        if raw is None or raw == {} or raw == []:
            continue
        if isinstance(raw, list):
            for item in raw:
                if not isinstance(item, dict):
                    errors.append(f"Invalid arc-flow record {item}")
                    continue
                add_flow((item.get("from"), item.get("to")), item.get("flow") if "flow" in item else item.get("value"))
        elif isinstance(raw, dict) and raw and any(isinstance(value, dict) for value in raw.values()):
            for raw_u, inner in raw.items():
                if not isinstance(inner, dict):
                    errors.append(f"Invalid arc-flow row {raw_u}")
                    continue
                for raw_v, flow_value in inner.items():
                    add_flow((raw_u, raw_v), flow_value)
        elif isinstance(raw, dict):
            for raw_key, flow_value in raw.items():
                add_flow(raw_key, flow_value)
        else:
            errors.append(f"Invalid arc-flow mapping {key}")
        return arc_flows
    return arc_flows


def extract_named_selection(payload: dict[str, Any] | None, keys: tuple[str, ...]) -> list[str]:
    if not isinstance(payload, dict):
        return []
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return [str(item) for item in value]
        if isinstance(value, dict):
            selected = [str(name) for name, flag in value.items() if flag]
            if selected:
                return selected
    return []


def parse_numeric_mapping_key(
    key: Any,
    *,
    arity: int,
) -> tuple[Any, ...] | None:
    if isinstance(key, tuple) and len(key) == arity:
        return tuple(key)
    if isinstance(key, list) and len(key) == arity:
        return tuple(key)
    text = str(key).strip()
    if not text:
        return None
    text = text.strip("()[]")
    normalized = text.replace(" ", "")
    for separator in ("->", "@", "_", ","):
        parts = normalized.split(separator)
        if len(parts) != arity:
            continue
        parsed: list[Any] = []
        ok = True
        for part in parts:
            if part == "":
                ok = False
                break
            try:
                parsed.append(int(part))
            except ValueError:
                parsed.append(part)
        if ok:
            return tuple(parsed)
    return None


def normalize_arc_key_text(
    raw_key: Any,
    *,
    instance_arc_ids: set[str] | None = None,
) -> str | None:
    text = str(raw_key).strip()
    if not text:
        return None
    if instance_arc_ids and text in instance_arc_ids:
        return text
    candidates = [text]
    trimmed = text.strip("()[]{}")
    if trimmed != text:
        candidates.append(trimmed)
    prefix_variants = (
        "flow_",
        "flows_",
        "flowvalues_",
        "flow_values_",
        "arcflow_",
        "arc_flow_",
        "arcflows_",
        "arc_flows_",
        "optimalflow_",
        "optimal_flow_",
        "flowsolution_",
        "flow_solution_",
        "shipment_",
        "shipments_",
        "x_",
        "f_",
        "arc_",
        "edge_",
    )
    seen: set[str] = set()
    queue = [candidate.replace(" ", "") for candidate in candidates]
    while queue:
        candidate = queue.pop(0)
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        if instance_arc_ids and candidate in instance_arc_ids:
            return candidate
        lowered = candidate.lower()
        for prefix in prefix_variants:
            if lowered.startswith(prefix):
                queue.append(candidate[len(prefix) :])
    return text.replace(" ", "")


def extract_arc_value_mapping(
    payload: dict[str, Any] | None,
    *,
    instance_arc_ids: set[str] | None = None,
    endpoint_to_arc_id: dict[tuple[int, int], str] | None = None,
    keys: tuple[str, ...] = (
        "arc_flows",
        "arc_flow",
        "flows",
        "flow",
        "flow_values",
        "flow_by_arc",
        "flow_solution",
        "optimal_flow",
        "optimal_arc_flow",
        "arc_flow_by_id",
        "shipment",
        "shipments",
        "installation",
        "installation_indicator",
    ),
) -> dict[str, float]:
    if not isinstance(payload, dict):
        return {}
    arc_ids = {str(item) for item in instance_arc_ids} if instance_arc_ids is not None else set()
    endpoint_lookup = endpoint_to_arc_id or {}
    result: dict[str, float] = {}
    for key in keys:
        raw = payload.get(key)
        if isinstance(raw, dict):
            for raw_key, raw_value in raw.items():
                value = to_number(raw_value)
                if value is None:
                    continue
                arc_id: str | None = None
                text_key = normalize_arc_key_text(raw_key, instance_arc_ids=arc_ids) or str(raw_key)
                if text_key in arc_ids:
                    arc_id = text_key
                else:
                    parsed = parse_numeric_mapping_key(raw_key, arity=2)
                    if parsed is not None:
                        try:
                            endpoint_key = (int(parsed[0]), int(parsed[1]))
                        except (TypeError, ValueError):
                            endpoint_key = None
                        if endpoint_key is not None:
                            arc_id = endpoint_lookup.get(endpoint_key)
                if arc_id is not None:
                    result[arc_id] = float(value)
            if result:
                return result
        if isinstance(raw, list):
            for item in raw:
                if not isinstance(item, dict):
                    continue
                value = to_number(item.get("flow") or item.get("value") or item.get("quantity"))
                if value is None:
                    continue
                arc_id: str | None = None
                if item.get("id") is not None:
                    text_id = str(item["id"])
                    if not arc_ids or text_id in arc_ids:
                        arc_id = text_id
                if arc_id is None:
                    try:
                        endpoint_key = (int(item["from"]), int(item["to"]))
                    except (KeyError, TypeError, ValueError):
                        endpoint_key = None
                    if endpoint_key is not None:
                        arc_id = endpoint_lookup.get(endpoint_key)
                if arc_id is not None:
                    result[arc_id] = float(value)
            if result:
                return result
    return result


def transpose_arc_period_mapping(raw: dict[str, Any]) -> dict[str, dict[str, float]]:
    if not isinstance(raw, dict):
        return {}
    if raw and all(isinstance(value, dict) for value in raw.values()):
        first_key = next(iter(raw))
        first_value = raw[first_key]
        if isinstance(first_value, dict) and all(isinstance(k, str) and k.startswith("t") for k in raw.keys()):
            return {
                str(period): {
                    str(arc_id): float(value)
                    for arc_id, value in arc_map.items()
                    if to_number(value) is not None
                }
                for period, arc_map in raw.items()
                if isinstance(arc_map, dict)
            }
        transposed: dict[str, dict[str, float]] = {}
        for arc_id, period_map in raw.items():
            if not isinstance(period_map, dict):
                continue
            for period, value in period_map.items():
                numeric = to_number(value)
                if numeric is None:
                    continue
                transposed.setdefault(str(period), {})[str(arc_id)] = float(numeric)
        return transposed
    return {}


def normalize_arc_identifier(
    raw_key: Any,
    *,
    instance_arc_ids: set[str],
    endpoint_to_arc_id: dict[tuple[int, int], str],
) -> str | None:
    text_key = str(raw_key).strip()
    if not text_key:
        return None
    if text_key in instance_arc_ids:
        return text_key
    parsed = parse_numeric_mapping_key(text_key, arity=2)
    if parsed is not None:
        try:
            endpoint = (int(parsed[0]), int(parsed[1]))
        except (TypeError, ValueError):
            endpoint = None
        if endpoint is not None and endpoint in endpoint_to_arc_id:
            return endpoint_to_arc_id[endpoint]
    return None


def parse_arc_period_key(
    raw_key: Any,
    *,
    periods: list[str],
    instance_arc_ids: set[str],
    endpoint_to_arc_id: dict[tuple[int, int], str],
) -> tuple[str, str] | None:
    text_key = str(raw_key).strip()
    if not text_key:
        return None
    for period in sorted({str(x) for x in periods}, key=len, reverse=True):
        for separator in ("@", "_"):
            suffix = f"{separator}{period}"
            if not text_key.endswith(suffix):
                continue
            arc_part = text_key[: -len(suffix)]
            arc_id = normalize_arc_identifier(
                arc_part,
                instance_arc_ids=instance_arc_ids,
                endpoint_to_arc_id=endpoint_to_arc_id,
            )
            if arc_id is not None:
                return arc_id, period
    return None


def extract_arc_period_flow_mapping(
    payload: dict[str, Any] | None,
    *,
    periods: list[str],
    instance_arc_ids: set[str],
    endpoint_to_arc_id: dict[tuple[int, int], str],
) -> dict[str, dict[str, float]]:
    if not isinstance(payload, dict):
        return {}
    for key in (
        "flows_by_period",
        "flow_by_period",
        "arc_flows_by_period",
        "arc_flows",
        "flows",
        "flow",
        "flow_solution",
        "optimal_flow",
        "optimal_flow_on_arcs",
    ):
        raw = payload.get(key)
        if not isinstance(raw, dict):
            continue
        mapping = transpose_arc_period_mapping(raw)
        if mapping:
            normalized: dict[str, dict[str, float]] = {}
            for period, arc_map in mapping.items():
                for raw_arc_id, value in arc_map.items():
                    arc_id = normalize_arc_identifier(
                        raw_arc_id,
                        instance_arc_ids=instance_arc_ids,
                        endpoint_to_arc_id=endpoint_to_arc_id,
                    )
                    if arc_id is None:
                        continue
                    normalized.setdefault(str(period), {})[arc_id] = float(value)
            if normalized:
                return normalized
        flat_mapping: dict[str, dict[str, float]] = {}
        for raw_key, raw_value in raw.items():
            numeric = to_number(raw_value)
            if numeric is None:
                continue
            parsed = parse_arc_period_key(
                raw_key,
                periods=periods,
                instance_arc_ids=instance_arc_ids,
                endpoint_to_arc_id=endpoint_to_arc_id,
            )
            if parsed is None:
                continue
            arc_id, period = parsed
            flat_mapping.setdefault(period, {})[arc_id] = float(numeric)
        if flat_mapping:
            return flat_mapping
    return {}


def parse_inventory_node_period_key(
    raw_key: Any,
    *,
    periods: list[str],
    storage_nodes: set[str],
) -> tuple[str, str] | None:
    text_key = str(raw_key).strip()
    if not text_key:
        return None
    stripped = text_key
    if stripped.startswith("I"):
        stripped = stripped[1:]
    stripped = stripped.lstrip("_")
    for period in sorted({str(x) for x in periods}, key=len, reverse=True):
        for separator in ("@", "_"):
            suffix = f"{separator}{period}"
            if not stripped.endswith(suffix):
                continue
            node_part = stripped[: -len(suffix)].strip("_")
            if node_part in storage_nodes:
                return node_part, period
        bare_suffix = period[1:] if period.startswith("t") else period
        suffix = f"_{bare_suffix}"
        if stripped.endswith(suffix):
            node_part = stripped[: -len(suffix)].strip("_")
            if node_part in storage_nodes:
                return node_part, period
    return None


def extract_inventory_by_node_period(
    payload: dict[str, Any] | None,
    storage_nodes: list[str],
    *,
    periods: list[str],
) -> dict[str, dict[str, float]]:
    if not isinstance(payload, dict):
        return {}
    storage_node_set = {str(x) for x in storage_nodes}
    period_set = {str(x) for x in periods}
    for key in (
        "inventory_by_node",
        "inventory_by_period",
        "inventory_levels_by_node",
        "inventory_levels",
        "inventory_solution",
        "inventory",
    ):
        raw = payload.get(key)
        if not isinstance(raw, dict):
            continue
        if raw and all(isinstance(value, dict) for value in raw.values()) and all(str(period) in period_set for period in raw.keys()):
            transposed: dict[str, dict[str, float]] = {}
            for period, node_map in raw.items():
                if not isinstance(node_map, dict):
                    continue
                for node, value in node_map.items():
                    numeric = to_number(value)
                    if numeric is None:
                        continue
                    node_name = str(node)
                    if storage_node_set and node_name not in storage_node_set:
                        continue
                    transposed.setdefault(node_name, {})[str(period)] = float(numeric)
            if transposed:
                return transposed
        result: dict[str, dict[str, float]] = {}
        for node, period_map in raw.items():
            if isinstance(period_map, dict):
                parsed = {
                    str(period): float(value)
                    for period, value in period_map.items()
                    if to_number(value) is not None
                    for value in [to_number(value)]
                }
                if parsed:
                    result[str(node)] = parsed
        if result:
            return result
        if len(storage_nodes) == 1:
            parsed_single = {
                str(period): float(value)
                for period, value in raw.items()
                if to_number(value) is not None and str(period) in {str(x) for x in periods}
                for value in [to_number(value)]
            }
            if parsed_single:
                return {storage_nodes[0]: parsed_single}
        flat_result: dict[str, dict[str, float]] = {}
        for raw_key, raw_value in raw.items():
            numeric = to_number(raw_value)
            if numeric is None:
                continue
            parsed = parse_inventory_node_period_key(
                raw_key,
                periods=periods,
                storage_nodes=storage_node_set,
            )
            if parsed is None:
                continue
            node, period = parsed
            flat_result.setdefault(node, {})[period] = float(numeric)
        if flat_result:
            return flat_result
    prefixed_result: dict[str, dict[str, float]] = {}
    for raw_key, raw_value in payload.items():
        if not isinstance(raw_key, str) or not raw_key.startswith("inventory_at_node_"):
            continue
        if not isinstance(raw_value, dict):
            continue
        node = raw_key[len("inventory_at_node_") :].strip()
        if not node:
            continue
        if storage_node_set and node not in storage_node_set:
            continue
        parsed = {
            str(period): float(value)
            for period, value in raw_value.items()
            if to_number(value) is not None and str(period) in period_set
            for value in [to_number(value)]
        }
        if parsed:
            prefixed_result[node] = parsed
    if prefixed_result:
        return prefixed_result
    return {}


def transpose_named_period_mapping(
    raw: dict[str, Any],
    *,
    entity_names: set[str],
    periods: list[str],
) -> dict[str, dict[str, float]]:
    if not isinstance(raw, dict):
        return {}
    period_set = {str(period) for period in periods}
    if raw and all(isinstance(value, dict) for value in raw.values()):
        if all(str(key) in period_set for key in raw.keys()):
            transposed: dict[str, dict[str, float]] = {}
            for period, entity_map in raw.items():
                if not isinstance(entity_map, dict):
                    continue
                for entity, value in entity_map.items():
                    numeric = to_number(value)
                    if numeric is None:
                        continue
                    entity_name = str(entity)
                    if entity_names and entity_name not in entity_names:
                        continue
                    transposed.setdefault(entity_name, {})[str(period)] = float(numeric)
            return transposed
        normalized: dict[str, dict[str, float]] = {}
        for entity, period_map in raw.items():
            entity_name = str(entity)
            if entity_names and entity_name not in entity_names:
                continue
            if not isinstance(period_map, dict):
                continue
            parsed = {
                str(period): float(numeric)
                for period, raw_value in period_map.items()
                for numeric in [to_number(raw_value)]
                if numeric is not None and str(period) in period_set
            }
            if parsed:
                normalized[entity_name] = parsed
        return normalized
    return {}


def parse_named_entity_period_key(
    raw_key: Any,
    *,
    entity_names: set[str],
    periods: list[str],
    prefixes: tuple[str, ...] = (),
) -> tuple[str, str] | None:
    text = str(raw_key).strip()
    if not text:
        return None
    candidates = [text.strip("()[]{}")]
    seen: set[str] = set()
    while candidates:
        candidate = candidates.pop(0).strip()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        lowered = candidate.lower()
        for prefix in prefixes:
            prefix_lower = prefix.lower()
            if lowered.startswith(prefix_lower):
                trimmed = candidate[len(prefix) :].lstrip("_")
                if trimmed and trimmed not in seen:
                    candidates.append(trimmed)
        for period in sorted({str(period) for period in periods}, key=len, reverse=True):
            for separator in ("@", "_", ":"):
                suffix = f"{separator}{period}"
                if candidate.endswith(suffix):
                    entity_name = candidate[: -len(suffix)].strip("_")
                    if entity_name in entity_names:
                        return entity_name, period
            bare_suffix = f"_{period[1:]}" if period.startswith("t") else ""
            if bare_suffix and candidate.endswith(bare_suffix):
                entity_name = candidate[: -len(bare_suffix)].strip("_")
                if entity_name in entity_names:
                    return entity_name, period
    return None


def extract_named_period_matrix(
    payload: dict[str, Any] | None,
    *,
    keys: tuple[str, ...],
    entity_names: list[str],
    periods: list[str],
    prefixes: tuple[str, ...] = (),
) -> dict[str, dict[str, float]]:
    if not isinstance(payload, dict):
        return {}
    entity_set = {str(entity) for entity in entity_names}
    for key in keys:
        raw = payload.get(key)
        if not isinstance(raw, dict):
            continue
        if len(entity_names) == 1 and all(str(period) in {str(p) for p in periods} for period in raw.keys()):
            entity_name = str(entity_names[0])
            singleton = {
                entity_name: {
                    str(period): float(numeric)
                    for period, raw_value in raw.items()
                    for numeric in [to_number(raw_value)]
                    if numeric is not None
                }
            }
            if singleton[entity_name]:
                return singleton
        structured = transpose_named_period_mapping(raw, entity_names=entity_set, periods=periods)
        if structured:
            return structured
        flat_result: dict[str, dict[str, float]] = {}
        for raw_key, raw_value in raw.items():
            numeric = to_number(raw_value)
            if numeric is None:
                continue
            parsed = parse_named_entity_period_key(
                raw_key,
                entity_names=entity_set,
                periods=periods,
                prefixes=prefixes,
            )
            if parsed is None:
                continue
            entity_name, period = parsed
            flat_result.setdefault(entity_name, {})[period] = float(numeric)
        if flat_result:
            return flat_result
    return {}


def normalize_categorical_label(value: Any, *, allowed_labels: set[str] | None = None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if allowed_labels is None:
        return text
    if text in allowed_labels:
        return text
    upper = text.upper()
    if upper in allowed_labels:
        return upper
    title = text.title()
    if title in allowed_labels:
        return title
    return None


def transpose_named_period_label_mapping(
    raw: Any,
    *,
    entity_names: set[str],
    periods: list[str],
    allowed_labels: set[str] | None = None,
) -> dict[str, dict[str, str]]:
    if not isinstance(raw, dict):
        return {}
    period_set = {str(period) for period in periods}
    if raw and all(isinstance(value, dict) for value in raw.values()):
        if all(str(key) in period_set for key in raw.keys()):
            transposed: dict[str, dict[str, str]] = {}
            for period, entity_map in raw.items():
                if not isinstance(entity_map, dict):
                    continue
                for entity, value in entity_map.items():
                    entity_name = str(entity)
                    if entity_names and entity_name not in entity_names:
                        continue
                    normalized_label = normalize_categorical_label(value, allowed_labels=allowed_labels)
                    if normalized_label is None:
                        continue
                    transposed.setdefault(entity_name, {})[str(period)] = normalized_label
            return transposed
        normalized: dict[str, dict[str, str]] = {}
        for entity, period_map in raw.items():
            entity_name = str(entity)
            if entity_names and entity_name not in entity_names:
                continue
            if not isinstance(period_map, dict):
                continue
            parsed: dict[str, str] = {}
            for period, raw_value in period_map.items():
                period_name = str(period)
                if period_name not in period_set:
                    continue
                normalized_label = normalize_categorical_label(raw_value, allowed_labels=allowed_labels)
                if normalized_label is None:
                    continue
                parsed[period_name] = normalized_label
            if parsed:
                normalized[entity_name] = parsed
        return normalized
    return {}


def extract_named_period_label_matrix(
    payload: dict[str, Any] | None,
    *,
    keys: tuple[str, ...],
    entity_names: list[str],
    periods: list[str],
    prefixes: tuple[str, ...] = (),
    allowed_labels: set[str] | None = None,
) -> dict[str, dict[str, str]]:
    if not isinstance(payload, dict):
        return {}
    entity_set = {str(entity) for entity in entity_names}
    for key in keys:
        raw = payload.get(key)
        if not isinstance(raw, dict):
            continue
        structured = transpose_named_period_label_mapping(
            raw,
            entity_names=entity_set,
            periods=periods,
            allowed_labels=allowed_labels,
        )
        if structured:
            return structured
        flat_result: dict[str, dict[str, str]] = {}
        for raw_key, raw_value in raw.items():
            normalized_label = normalize_categorical_label(raw_value, allowed_labels=allowed_labels)
            if normalized_label is None:
                continue
            parsed = parse_named_entity_period_key(
                raw_key,
                entity_names=entity_set,
                periods=periods,
                prefixes=prefixes,
            )
            if parsed is None:
                continue
            entity_name, period = parsed
            flat_result.setdefault(entity_name, {})[period] = normalized_label
        if flat_result:
            return flat_result
    return {}


def extract_period_indicator_mapping(
    payload: dict[str, Any] | None,
    *,
    periods: list[str],
    indicator_keys: tuple[str, ...],
    list_keys: tuple[str, ...] = (),
    prefixes: tuple[str, ...] = (),
) -> dict[str, int]:
    if not isinstance(payload, dict):
        return {}
    period_set = {str(period) for period in periods}

    def parse_period_key(raw_key: Any) -> str | None:
        text = str(raw_key).strip()
        if not text:
            return None
        candidates = [text.strip("()[]{}")]
        seen: set[str] = set()
        prefix_lowers = {prefix.lower() for prefix in prefixes}
        while candidates:
            candidate = candidates.pop(0).strip()
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            if candidate in period_set:
                return candidate
            lowered = candidate.lower()
            for prefix in prefixes:
                prefix_lower = prefix.lower()
                if lowered.startswith(prefix_lower):
                    trimmed = candidate[len(prefix) :].lstrip("_:@")
                    if trimmed and trimmed not in seen:
                        candidates.append(trimmed)
            for period in sorted(period_set, key=len, reverse=True):
                for separator in ("@", "_", ":"):
                    suffix = f"{separator}{period}"
                    if candidate.endswith(suffix):
                        prefix_part = candidate[: -len(suffix)].strip("_").lower()
                        if not prefix_lowers or prefix_part in prefix_lowers:
                            return period
                bare_suffix = f"_{period[1:]}" if period.startswith("t") else ""
                if bare_suffix and candidate.endswith(bare_suffix):
                    prefix_part = candidate[: -len(bare_suffix)].strip("_").lower()
                    if not prefix_lowers or prefix_part in prefix_lowers:
                        return period
        return None

    for key in indicator_keys:
        raw = payload.get(key)
        if not isinstance(raw, dict):
            continue
        result: dict[str, int] = {}
        for raw_period, raw_value in raw.items():
            period_name = parse_period_key(raw_period)
            if period_name is None:
                continue
            numeric = to_number(raw_value)
            if numeric is None:
                continue
            result[period_name] = 1 if numeric > 0.5 else 0
        if result:
            return result
    for key in list_keys:
        raw = payload.get(key)
        if not isinstance(raw, list):
            continue
        result = {str(period): 0 for period in periods}
        for item in raw:
            period_name = str(item)
            if period_name in period_set:
                result[period_name] = 1
        if any(result.values()):
            return result
    return {}


def extract_vehicle_period_indicator_mapping(
    payload: dict[str, Any] | None,
    *,
    vehicles: list[str],
    periods: list[str],
) -> dict[str, dict[str, int]]:
    if not isinstance(payload, dict):
        return {}
    vehicle_set = {str(vehicle) for vehicle in vehicles}
    period_set = {str(period) for period in periods}
    for key in ("dispatch_by_vehicle_period", "vehicle_dispatch", "dispatch_indicator_by_vehicle_period"):
        raw = payload.get(key)
        if not isinstance(raw, dict):
            continue
        result: dict[str, dict[str, int]] = {}
        for vehicle, period_map in raw.items():
            vehicle_name = str(vehicle)
            if vehicle_set and vehicle_name not in vehicle_set:
                continue
            if not isinstance(period_map, dict):
                continue
            parsed = {}
            for period, raw_value in period_map.items():
                period_name = str(period)
                if period_name not in period_set:
                    continue
                numeric = to_number(raw_value)
                if numeric is None:
                    continue
                parsed[period_name] = 1 if numeric > 0.5 else 0
            if parsed:
                result[vehicle_name] = parsed
        if result:
            return result
    raw_used = payload.get("used_vehicles_by_period")
    if isinstance(raw_used, dict):
        result = {str(vehicle): {} for vehicle in vehicles}
        for period, vehicle_list in raw_used.items():
            period_name = str(period)
            if period_name not in period_set or not isinstance(vehicle_list, list):
                continue
            used_set = {str(vehicle) for vehicle in vehicle_list}
            for vehicle in vehicles:
                result.setdefault(str(vehicle), {})[period_name] = 1 if str(vehicle) in used_set else 0
        if any(any(period_map.values()) for period_map in result.values()):
            return result
    return {}


def route_path_to_arcs(path: list[Any]) -> list[tuple[str, str]]:
    if not isinstance(path, list) or len(path) < 2:
        return []
    normalized = [str(node) for node in path]
    return [(normalized[idx], normalized[idx + 1]) for idx in range(len(normalized) - 1)]


def parse_route_arc_item(item: Any, *, nodes: set[str] | None = None) -> tuple[str, str] | None:
    if isinstance(item, (list, tuple)) and len(item) == 2:
        return (str(item[0]), str(item[1]))
    if not isinstance(item, str):
        return None
    token = item.strip()
    if not token:
        return None
    for sep in ("->", "→"):
        if sep in token:
            left, right = token.split(sep, 1)
            left = left.strip()
            right = right.strip()
            if left and right:
                return (left, right)
    if nodes:
        for left in sorted(nodes, key=len, reverse=True):
            prefix = f"{left}_"
            if token.startswith(prefix):
                right = token[len(prefix) :].strip()
                if right in nodes:
                    return (left, right)
    return None


def coerce_route_sequence_to_arcs(path: list[Any], *, nodes: set[str] | None = None) -> list[tuple[str, str]]:
    if not isinstance(path, list) or not path:
        return []
    parsed_arcs: list[tuple[str, str]] = []
    for item in path:
        parsed = parse_route_arc_item(item, nodes=nodes)
        if parsed is None:
            parsed_arcs = []
            break
        parsed_arcs.append(parsed)
    if parsed_arcs:
        return parsed_arcs
    return route_path_to_arcs(path)


def extract_period_route_arcs(
    payload: dict[str, Any] | None,
    *,
    periods: list[str],
    vehicles: list[str],
    nodes: list[str] | None = None,
) -> dict[str, dict[str, list[tuple[str, str]]]]:
    if not isinstance(payload, dict):
        return {}
    period_set = {str(period) for period in periods}
    normalized_vehicles = [str(vehicle) for vehicle in vehicles]
    default_vehicle = normalized_vehicles[0] if normalized_vehicles else "V1"
    node_set = {str(node) for node in nodes} if nodes else None

    def parse_arc_map(raw: Any, *, vehicle_scoped: bool) -> dict[str, dict[str, list[tuple[str, str]]]]:
        if not isinstance(raw, dict):
            return {}
        result: dict[str, dict[str, list[tuple[str, str]]]] = {}
        if vehicle_scoped:
            for vehicle, period_map in raw.items():
                if not isinstance(period_map, dict):
                    continue
                vehicle_name = str(vehicle)
                for period, arc_list in period_map.items():
                    period_name = str(period)
                    if period_name not in period_set or not isinstance(arc_list, list):
                        continue
                    arcs: list[tuple[str, str]] = []
                    for item in arc_list:
                        parsed = parse_route_arc_item(item, nodes=node_set)
                        if parsed is not None:
                            arcs.append(parsed)
                    result.setdefault(vehicle_name, {})[period_name] = arcs
        else:
            result = {default_vehicle: {}}
            for period, arc_list in raw.items():
                period_name = str(period)
                if period_name not in period_set or not isinstance(arc_list, list):
                    continue
                arcs: list[tuple[str, str]] = []
                for item in arc_list:
                    parsed = parse_route_arc_item(item, nodes=node_set)
                    if parsed is not None:
                        arcs.append(parsed)
                result[default_vehicle][period_name] = arcs
            if not result[default_vehicle]:
                return {}
        return result

    for key in ("route_arcs_by_vehicle_period", "routing_arcs_by_vehicle_period", "routes_by_vehicle_period"):
        parsed = parse_arc_map(payload.get(key), vehicle_scoped=True)
        if parsed:
            return parsed

    for key in ("route_arcs_by_period", "routing_arcs_by_period"):
        parsed = parse_arc_map(payload.get(key), vehicle_scoped=False)
        if parsed:
            return parsed

    def parse_path_map(raw: Any, *, vehicle_scoped: bool) -> dict[str, dict[str, list[tuple[str, str]]]]:
        if not isinstance(raw, dict):
            return {}
        result: dict[str, dict[str, list[tuple[str, str]]]] = {}
        if vehicle_scoped:
            for vehicle, period_map in raw.items():
                if not isinstance(period_map, dict):
                    continue
                vehicle_name = str(vehicle)
                for period, path in period_map.items():
                    period_name = str(period)
                    if period_name not in period_set or not isinstance(path, list):
                        continue
                    result.setdefault(vehicle_name, {})[period_name] = coerce_route_sequence_to_arcs(path, nodes=node_set)
        else:
            result = {default_vehicle: {}}
            for period, path in raw.items():
                period_name = str(period)
                if period_name not in period_set or not isinstance(path, list):
                    continue
                result[default_vehicle][period_name] = coerce_route_sequence_to_arcs(path, nodes=node_set)
            if not result[default_vehicle]:
                return {}
        return result

    for key in ("route_by_vehicle_period", "routing_by_vehicle_period", "routes_by_vehicle_period"):
        parsed = parse_path_map(payload.get(key), vehicle_scoped=True)
        if parsed:
            return parsed

    for key in ("route_by_period", "routing", "routes"):
        parsed = parse_path_map(payload.get(key), vehicle_scoped=False)
        if parsed:
            return parsed

    return {}


def normalize_route_path(value: Any) -> list[str]:
    if isinstance(value, dict):
        for key in ("route", "tour", "path", "stops", "sequence", "visit_sequence"):
            path = normalize_route_path(value.get(key))
            if path:
                return path
        return []
    if isinstance(value, tuple):
        value = list(value)
    if not isinstance(value, list):
        return []
    route: list[str] = []
    for item in value:
        if isinstance(item, (str, int, float)):
            route.append(str(item))
        else:
            return []
    return route


def parse_named_arc_record(
    item: Any,
    *,
    nodes: set[str] | None = None,
) -> tuple[str, str, str | None] | None:
    if isinstance(item, dict):
        tail = item.get("from") if "from" in item else item.get("tail", item.get("source"))
        head = item.get("to") if "to" in item else item.get("head", item.get("target"))
        vehicle = item.get("vehicle_id") if "vehicle_id" in item else item.get("vehicle")
        if tail is not None and head is not None:
            return (str(tail), str(head), str(vehicle) if vehicle is not None else None)
        return None
    if isinstance(item, (list, tuple)) and len(item) >= 2:
        vehicle = str(item[2]) if len(item) >= 3 else None
        return (str(item[0]), str(item[1]), vehicle)
    parsed = parse_route_arc_item(item, nodes=nodes)
    if parsed is not None:
        return (parsed[0], parsed[1], None)
    return None


def extract_named_arc_records(
    payload: dict[str, Any] | None,
    *,
    keys: tuple[str, ...],
    nodes: set[str] | None = None,
) -> list[tuple[str, str, str | None]]:
    if not isinstance(payload, dict):
        return []
    for key in keys:
        raw = payload.get(key)
        if not isinstance(raw, list):
            continue
        arcs: list[tuple[str, str, str | None]] = []
        for item in raw:
            parsed = parse_named_arc_record(item, nodes=nodes)
            if parsed is not None:
                arcs.append(parsed)
        if arcs:
            return arcs
    return []


def rotate_cycle_to_root(route: list[str], root: str | None) -> list[str]:
    if not route or not root:
        return route
    cycle = route[:-1] if len(route) >= 2 and route[0] == route[-1] else list(route)
    if root not in cycle:
        return route
    index = cycle.index(root)
    rotated = cycle[index:] + cycle[:index]
    return rotated + [rotated[0]]


def rebuild_route_from_arcs(arcs: list[tuple[str, str]], *, root: str | None = None) -> list[str]:
    if not arcs:
        return []
    successor: dict[str, str] = {}
    indegree: Counter[str] = Counter()
    for tail, head in arcs:
        if tail in successor and successor[tail] != head:
            return []
        successor[tail] = head
        indegree[head] += 1
    if root and root in successor:
        start = root
    else:
        starts = [node for node in successor if indegree[node] == 0]
        start = starts[0] if starts else arcs[0][0]
    route = [start]
    seen_edges = 0
    while route[-1] in successor and seen_edges < len(arcs):
        nxt = successor[route[-1]]
        route.append(nxt)
        seen_edges += 1
        if root and nxt == root:
            break
        if nxt in route[:-1]:
            break
    return route


def derive_route_from_visit_order(payload: dict[str, Any] | None, *, root: str | None = None) -> list[str]:
    if not isinstance(payload, dict):
        return []
    raw_visit_order = payload.get("visit_order")
    if not isinstance(raw_visit_order, dict):
        return []
    pairs: list[tuple[float, str]] = []
    for node, order in raw_visit_order.items():
        numeric = to_number(order)
        if numeric is None:
            return []
        pairs.append((float(numeric), str(node)))
    if not pairs:
        return []
    ordered = [node for _, node in sorted(pairs)]
    if root and root not in ordered:
        ordered.insert(0, root)
    if ordered and ordered[-1] != ordered[0]:
        ordered.append(ordered[0])
    return ordered


def extract_routes_and_vehicle_ids(
    payload: dict[str, Any] | None,
    *,
    depot: str | None = None,
    nodes: list[str] | None = None,
) -> tuple[list[list[str]], list[str]]:
    if not isinstance(payload, dict):
        return [], []
    node_set = {str(node) for node in nodes} if nodes else None
    raw_routes = payload.get("routes")
    if isinstance(raw_routes, dict):
        vehicle_ids: list[str] = []
        routes: list[list[str]] = []
        for vehicle, raw_path in raw_routes.items():
            path = normalize_route_path(raw_path)
            if path:
                vehicle_ids.append(str(vehicle))
                routes.append(path)
        if routes:
            return routes, vehicle_ids
    if isinstance(raw_routes, list):
        if raw_routes and all(isinstance(item, dict) for item in raw_routes):
            vehicle_ids = []
            routes = []
            for item in raw_routes:
                path = normalize_route_path(item)
                if not path:
                    continue
                vehicle = item.get("vehicle_id") if "vehicle_id" in item else item.get("vehicle")
                vehicle_ids.append(str(vehicle) if vehicle is not None else "")
                routes.append(path)
            if routes:
                return routes, vehicle_ids
        if raw_routes and all(isinstance(item, list) for item in raw_routes):
            routes = [path for item in raw_routes if (path := normalize_route_path(item))]
            if routes:
                raw_ids = payload.get("route_vehicle_ids")
                vehicle_ids = [str(item) for item in raw_ids] if isinstance(raw_ids, list) else []
                return routes, vehicle_ids
        path = normalize_route_path(raw_routes)
        if path:
            raw_ids = payload.get("route_vehicle_ids")
            vehicle_ids = [str(item) for item in raw_ids] if isinstance(raw_ids, list) else []
            return [path], vehicle_ids
    raw_vehicles = payload.get("vehicles")
    if isinstance(raw_vehicles, list) and raw_vehicles and all(isinstance(item, dict) for item in raw_vehicles):
        vehicle_ids = []
        routes = []
        for item in raw_vehicles:
            path = normalize_route_path(item)
            if not path:
                raw_customers = item.get("customers") if isinstance(item.get("customers"), list) else item.get("stops")
                if isinstance(raw_customers, list) and all(isinstance(node, (str, int, float)) for node in raw_customers):
                    path = [str(node) for node in raw_customers]
            if not path:
                continue
            vehicle = (
                item.get("vehicle_id")
                if "vehicle_id" in item
                else item.get("vehicle", item.get("id", item.get("name", item.get("type"))))
            )
            vehicle_ids.append(str(vehicle) if vehicle is not None else "")
            routes.append(path)
        if routes:
            return routes, vehicle_ids
    for key in ("tour", "route", "path", "optimal_path"):
        path = normalize_route_path(payload.get(key))
        if path:
            return [path], []
    derived = derive_route_from_visit_order(payload, root=depot)
    if derived:
        return [derived], []
    arc_records = extract_named_arc_records(payload, keys=("active_arcs", "selected_arcs"), nodes=node_set)
    if arc_records:
        by_vehicle: dict[str, list[tuple[str, str]]] = {}
        for tail, head, vehicle in arc_records:
            by_vehicle.setdefault(vehicle or "__default__", []).append((tail, head))
        vehicle_ids = [vehicle for vehicle in by_vehicle if vehicle != "__default__"]
        routes: list[list[str]] = []
        for vehicle, arcs in by_vehicle.items():
            route = rebuild_route_from_arcs(arcs, root=depot)
            if route:
                routes.append(route)
        return routes, vehicle_ids
    return [], []


def canonicalize_tsptw_route(route: list[Any], *, depot: str, nodes: list[str] | None = None) -> list[str]:
    if not route:
        return []
    lowered_depot = depot.strip().lower()
    known_nodes = {str(node).strip() for node in (nodes or [])}
    canonical: list[str] = []
    for raw_node in route:
        text = str(raw_node).strip()
        lowered = text.lower()
        is_depot_alias = False
        if lowered == lowered_depot:
            is_depot_alias = True
        elif lowered in {"depot", "start", "end", "origin", "source", "sink", "return"}:
            is_depot_alias = True
        elif re.fullmatch(r"(?:depot|d)(?:[_\-\s]?(?:start|end|origin|source|sink|return))?", lowered):
            is_depot_alias = True
        elif lowered == "0" and "0" not in known_nodes and depot != "0":
            is_depot_alias = True
        canonical_node = depot if is_depot_alias else text
        if not canonical or canonical_node != canonical[-1]:
            canonical.append(canonical_node)
    return canonical


def simplify_alphanumeric_token(value: Any) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "", str(value)).upper()


def canonicalize_hfvrp_route(route: list[Any], *, depot: str, nodes: list[str] | None = None) -> list[str]:
    if not route:
        return []
    known_nodes = [str(node) for node in (nodes or [])]
    known_node_map = {str(node).strip().lower(): str(node) for node in known_nodes}
    canonical: list[str] = []
    for raw_node in route:
        text = str(raw_node).strip()
        if not text:
            continue
        lowered = text.lower()
        canonical_node = known_node_map.get(lowered)
        if canonical_node is None:
            is_depot_alias = False
            if lowered == depot.strip().lower():
                is_depot_alias = True
            elif lowered in {"depot", "d", "start", "end", "origin", "source", "sink", "return"}:
                is_depot_alias = True
            elif re.fullmatch(r"(?:depot|d)(?:[_\-\s]?(?:start|end|origin|source|sink|return))?", lowered):
                is_depot_alias = True
            elif lowered == "0" and "0" not in known_node_map and depot != "0":
                is_depot_alias = True
            if is_depot_alias:
                canonical_node = depot
        if canonical_node is None:
            numeric = to_number(text)
            if numeric is not None and abs(float(numeric) - round(float(numeric))) <= 1e-9:
                index = int(round(float(numeric)))
                if 0 <= index < len(known_nodes):
                    canonical_node = known_nodes[index]
        if canonical_node is None:
            canonical_node = text
        if not canonical or canonical_node != canonical[-1]:
            canonical.append(canonical_node)
    if canonical and depot not in canonical:
        canonical = [depot] + canonical + [depot]
    return canonical


def resolve_hfvrp_vehicle_type_alias(raw_value: Any, known_types: list[str]) -> str | None:
    if raw_value is None:
        return None
    text = str(raw_value).strip()
    if not text:
        return None
    if text in known_types:
        return text
    simplified = simplify_alphanumeric_token(text)
    matches = [type_id for type_id in known_types if simplify_alphanumeric_token(type_id) == simplified]
    if len(matches) == 1:
        return matches[0]
    return None


def infer_hfvrp_vehicle_type_from_label(
    label: Any,
    *,
    known_types: list[str],
    vehicle_parameters: dict[str, Any],
) -> str | None:
    resolved = resolve_hfvrp_vehicle_type_alias(label, known_types)
    if resolved is not None:
        return resolved
    simplified_label = simplify_alphanumeric_token(label)
    for vehicle_id, payload in vehicle_parameters.items():
        if simplify_alphanumeric_token(vehicle_id) == simplified_label and isinstance(payload, dict):
            resolved_type = resolve_hfvrp_vehicle_type_alias(payload.get("type_id"), known_types)
            if resolved_type is not None:
                return resolved_type
    prefix_matches = [
        type_id
        for type_id in known_types
        if simplified_label.startswith(simplify_alphanumeric_token(type_id))
    ]
    if len(prefix_matches) == 1:
        return prefix_matches[0]
    return None


def normalize_hfvrp_vehicle_assignments(
    raw_vehicle_ids: list[str],
    raw_vehicle_types: list[str | None],
    *,
    route_count: int,
    vehicle_parameters: dict[str, Any],
    vehicle_type_parameters: dict[str, Any],
) -> tuple[list[str | None], list[str | None]]:
    known_types = list(vehicle_type_parameters.keys())
    type_to_vehicles: dict[str, list[str]] = {}
    for vehicle_id, payload in vehicle_parameters.items():
        if not isinstance(payload, dict):
            continue
        type_id = resolve_hfvrp_vehicle_type_alias(payload.get("type_id"), known_types)
        if type_id is not None:
            type_to_vehicles.setdefault(type_id, []).append(str(vehicle_id))
    simplified_vehicle_map: dict[str, list[str]] = {}
    for vehicle_id in vehicle_parameters:
        simplified_vehicle_map.setdefault(simplify_alphanumeric_token(vehicle_id), []).append(str(vehicle_id))

    normalized_ids: list[str | None] = [None] * route_count
    normalized_types: list[str | None] = [None] * route_count
    raw_aliases: list[str | None] = [None] * route_count

    for index in range(route_count):
        if index < len(raw_vehicle_types):
            normalized_types[index] = resolve_hfvrp_vehicle_type_alias(raw_vehicle_types[index], known_types)
        if index < len(raw_vehicle_ids):
            alias = str(raw_vehicle_ids[index]).strip()
            if alias:
                raw_aliases[index] = alias
                if alias in vehicle_parameters:
                    normalized_ids[index] = alias
                else:
                    matches = simplified_vehicle_map.get(simplify_alphanumeric_token(alias), [])
                    if len(matches) == 1:
                        normalized_ids[index] = matches[0]
        if normalized_ids[index] is not None and normalized_types[index] is None:
            payload = vehicle_parameters.get(normalized_ids[index])
            if isinstance(payload, dict):
                normalized_types[index] = resolve_hfvrp_vehicle_type_alias(payload.get("type_id"), known_types)
        if normalized_types[index] is None and raw_aliases[index] is not None:
            normalized_types[index] = infer_hfvrp_vehicle_type_from_label(
                raw_aliases[index],
                known_types=known_types,
                vehicle_parameters=vehicle_parameters,
            )

    for type_id, vehicles in type_to_vehicles.items():
        type_indices = [index for index in range(route_count) if normalized_types[index] == type_id and raw_aliases[index] is not None]
        unresolved = [index for index in range(route_count) if normalized_ids[index] is None and normalized_types[index] == type_id]
        if not type_indices and not unresolved:
            continue
        numeric_suffixes: dict[int, int] = {}
        type_prefix = simplify_alphanumeric_token(type_id)
        suffix_parse_ok = True
        for index in type_indices:
            alias = raw_aliases[index]
            if alias is None:
                suffix_parse_ok = False
                break
            simplified_alias = simplify_alphanumeric_token(alias)
            if not simplified_alias.startswith(type_prefix):
                suffix_parse_ok = False
                break
            suffix = simplified_alias[len(type_prefix):]
            if not suffix.isdigit():
                suffix_parse_ok = False
                break
            numeric_suffixes[index] = int(suffix)
        if suffix_parse_ok and len(set(numeric_suffixes.values())) == len(numeric_suffixes):
            values = list(numeric_suffixes.values())
            zero_based = all(0 <= value < len(vehicles) for value in values)
            one_based = all(1 <= value <= len(vehicles) for value in values)
            if zero_based ^ one_based:
                for index, value in numeric_suffixes.items():
                    normalized_ids[index] = vehicles[value] if zero_based else vehicles[value - 1]

        remaining = [index for index in unresolved if normalized_ids[index] is None]
        if remaining:
            available_vehicles = [vehicle_id for vehicle_id in vehicles if vehicle_id not in {vid for vid in normalized_ids if vid}]
            if len(remaining) <= len(available_vehicles):
                for index, vehicle_id in zip(remaining, available_vehicles):
                    normalized_ids[index] = vehicle_id

    for index in range(route_count):
        if normalized_ids[index] is not None and normalized_types[index] is None:
            payload = vehicle_parameters.get(normalized_ids[index])
            if isinstance(payload, dict):
                normalized_types[index] = resolve_hfvrp_vehicle_type_alias(payload.get("type_id"), known_types)

    return normalized_ids, normalized_types


def compute_route_cost_from_matrix(route: list[str], matrix: dict[str, Any]) -> float | None:
    if not route or not isinstance(matrix, dict) or len(route) < 2:
        return None
    total = 0.0
    for tail, head in zip(route, route[1:]):
        row = matrix.get(tail)
        if not isinstance(row, dict):
            return None
        value = to_number(row.get(head))
        if value is None:
            return None
        total += float(value)
    return total


def extract_selected_arc_set(payload: dict[str, Any] | None) -> set[tuple[int, int]]:
    if not isinstance(payload, dict):
        return set()
    selected: set[tuple[int, int]] = set()
    raw_selected = payload.get("selected_arcs")
    if isinstance(raw_selected, list):
        for item in raw_selected:
            parsed = parse_numeric_mapping_key(item, arity=2)
            if parsed is None:
                continue
            try:
                selected.add((int(parsed[0]), int(parsed[1])))
            except (TypeError, ValueError):
                continue
    if isinstance(raw_selected, dict):
        for key, flag in raw_selected.items():
            numeric = to_number(flag)
            if numeric is None or numeric <= 0.5:
                continue
            parsed = parse_numeric_mapping_key(key, arity=2)
            if parsed is None:
                continue
            try:
                selected.add((int(parsed[0]), int(parsed[1])))
            except (TypeError, ValueError):
                continue
    raw_binary = payload.get("arc_selection")
    if isinstance(raw_binary, dict):
        for key, flag in raw_binary.items():
            numeric = to_number(flag)
            if numeric is None or numeric <= 0.5:
                continue
            parsed = parse_numeric_mapping_key(key, arity=2)
            if parsed is None:
                continue
            try:
                selected.add((int(parsed[0]), int(parsed[1])))
            except (TypeError, ValueError):
                continue
    return selected


def extract_single_assignment_target(value: Any) -> str | None:
    if isinstance(value, dict):
        for key in (
            "assigned_site",
            "assigned_facility",
            "assigned_agent",
            "assigned_route",
            "assigned_to",
            "site",
            "facility",
            "agent",
            "route",
            "target",
        ):
            if key in value:
                return str(value[key])
        return None
    if isinstance(value, (list, tuple)) and len(value) == 1:
        return str(value[0])
    if isinstance(value, (str, int, float)):
        return str(value)
    return None


def extract_assignment_mapping(
    payload: dict[str, Any] | None,
    *,
    source_entities: list[str] | tuple[str, ...] | set[str] | None = None,
    target_entities: list[str] | tuple[str, ...] | set[str] | None = None,
) -> dict[str, str]:
    if not isinstance(payload, dict):
        return {}
    source_set = {str(item) for item in source_entities} if source_entities is not None else set()
    target_set = {str(item) for item in target_entities} if target_entities is not None else set()
    for key in (
        "assignments",
        "assignment",
        "matching",
        "customer_assignments",
        "task_assignments",
        "demand_assignments",
        "assignment_map",
    ):
        raw = payload.get(key)
        if not isinstance(raw, dict):
            continue
        direct_hits = sum(1 for name in raw.keys() if str(name) in source_set)
        inverse_hits = sum(1 for name in raw.keys() if str(name) in target_set)
        mapping: dict[str, str] = {}
        if direct_hits >= inverse_hits:
            for src, value in raw.items():
                target = extract_single_assignment_target(value)
                if target is not None:
                    mapping[str(src)] = target
            if mapping:
                return mapping
        inverse_mapping: dict[str, str] = {}
        for tgt, value in raw.items():
            tgt_name = str(tgt)
            if isinstance(value, list):
                for src in value:
                    inverse_mapping[str(src)] = tgt_name
            elif isinstance(value, dict):
                for inner_key, inner_value in value.items():
                    if inner_value:
                        inverse_mapping[str(inner_key)] = tgt_name
            else:
                src = extract_single_assignment_target(value)
                if src is not None:
                    inverse_mapping[src] = tgt_name
        if inverse_mapping:
            return inverse_mapping
    return {}


def normalize_sign(value: Any) -> str:
    if isinstance(value, (int, float)):
        if abs(float(value) - 1.0) <= 1e-9:
            return "+"
        if abs(float(value) + 1.0) <= 1e-9:
            return "-"
    text = str(value).strip()
    if text in {"+", "＋", "positive", "pos"}:
        return "+"
    if text in {"-", "−", "－", "negative", "neg"}:
        return "-"
    return text


def normalize_literal(literal: Any) -> tuple[str, str] | None:
    if isinstance(literal, dict):
        variable = literal.get("variable") or literal.get("var") or literal.get("name")
        sign = normalize_sign(literal.get("sign", "+"))
    elif isinstance(literal, (list, tuple)) and len(literal) == 2:
        variable = literal[0]
        sign = normalize_sign(literal[1])
    else:
        return None
    if variable is None:
        return None
    return (str(variable), sign)


def extract_clause_set(instance: dict[str, Any]) -> set[tuple[tuple[str, str], ...]]:
    clause_set: set[tuple[tuple[str, str], ...]] = set()
    for key in ("clauses", "CNF_clauses"):
        clauses = instance.get(key)
        if not isinstance(clauses, list):
            continue
        for clause in clauses:
            if not isinstance(clause, dict):
                continue
            literals = clause.get("literals")
            normalized: list[tuple[str, str]] = []
            if isinstance(literals, list):
                normalized = sorted(
                    literal for literal in (normalize_literal(item) for item in literals) if literal is not None
                )
            else:
                pos_vars = clause.get("pos")
                neg_vars = clause.get("neg")
                if isinstance(pos_vars, list):
                    normalized.extend((str(var), "+") for var in pos_vars)
                if isinstance(neg_vars, list):
                    normalized.extend((str(var), "-") for var in neg_vars)
                normalized = sorted(normalized)
            if normalized:
                clause_set.add(tuple(normalized))
    return clause_set


def implication_to_clause(source: str, target: str) -> tuple[tuple[str, str], ...]:
    return tuple(sorted(((str(source), "-"), (str(target), "+"))))


def extract_implication_set(instance: dict[str, Any]) -> set[tuple[str, str]]:
    implication_set: set[tuple[str, str]] = set()
    for key in ("implications", "implication_rows"):
        implications = instance.get(key)
        if not isinstance(implications, list):
            continue
        for item in implications:
            if not isinstance(item, dict):
                continue
            source = item.get("if_variable")
            target = item.get("then_variable")
            if source is None or target is None:
                literals = item.get("literals")
                if isinstance(literals, list):
                    normalized = [literal for literal in (normalize_literal(x) for x in literals) if literal is not None]
                    neg_vars = [var for var, sign in normalized if sign == "-"]
                    pos_vars = [var for var, sign in normalized if sign == "+"]
                    if len(neg_vars) == 1 and len(pos_vars) == 1:
                        source, target = neg_vars[0], pos_vars[0]
                elif isinstance(item.get("neg"), list) and isinstance(item.get("pos"), list):
                    neg_vars = [str(x) for x in item["neg"]]
                    pos_vars = [str(x) for x in item["pos"]]
                    if len(neg_vars) == 1 and len(pos_vars) == 1:
                        source, target = neg_vars[0], pos_vars[0]
            if source is None or target is None:
                continue
            implication_set.add((str(source), str(target)))
    return implication_set


def extract_at_most_one_groups(instance: dict[str, Any]) -> set[tuple[str, ...]]:
    result: set[tuple[str, ...]] = set()
    for key in ("at_most_one_groups", "at_most_one_rows", "pairwise_exclusions"):
        groups = instance.get(key)
        if not isinstance(groups, list):
            continue
        for item in groups:
            if not isinstance(item, dict):
                continue
            variables = None
            if isinstance(item.get("variables"), list):
                variables = item["variables"]
            elif isinstance(item.get("neg"), list):
                variables = item["neg"]
            else:
                literals = item.get("literals")
                if isinstance(literals, list):
                    normalized = [literal for literal in (normalize_literal(x) for x in literals) if literal is not None]
                    neg_vars = [var for var, sign in normalized if sign == "-"]
                    if neg_vars:
                        variables = neg_vars
            if not isinstance(variables, list):
                continue
            result.add(tuple(sorted(str(var) for var in variables)))
    return result


def extract_logical_constraint_clause_set(instance: dict[str, Any]) -> set[tuple[tuple[str, str], ...]]:
    clause_set = set(extract_clause_set(instance))
    for source, target in extract_implication_set(instance):
        clause_set.add(implication_to_clause(source, target))
    for group in extract_at_most_one_groups(instance):
        variables = list(group)
        for i in range(len(variables)):
            for j in range(i + 1, len(variables)):
                clause_set.add(tuple(sorted(((variables[i], "-"), (variables[j], "-")))))
    return clause_set


def extract_cardinality_constraints(instance: dict[str, Any]) -> set[tuple[int, tuple[str, ...]]]:
    result: set[tuple[int, tuple[str, ...]]] = set()
    for key in ("cardinality_constraints", "cardinality_rows"):
        constraints = instance.get(key)
        if not isinstance(constraints, list):
            continue
        for item in constraints:
            if not isinstance(item, dict):
                continue
            variables = None
            if isinstance(item.get("variables"), list):
                variables = item["variables"]
            elif isinstance(item.get("pos"), list):
                variables = item["pos"]
            else:
                literals = item.get("literals")
                if isinstance(literals, list):
                    normalized = [literal for literal in (normalize_literal(x) for x in literals) if literal is not None]
                    pos_vars = [var for var, sign in normalized if sign == "+"]
                    if pos_vars:
                        variables = pos_vars
            if not isinstance(variables, list):
                continue
            rhs = item.get("rhs")
            if rhs is None:
                rhs = item.get("upper_bound", item.get("bound"))
            try:
                rhs_int = int(rhs)
            except (TypeError, ValueError):
                continue
            result.add((rhs_int, tuple(sorted(str(var) for var in variables))))
    return result


def extract_mdkp_item_profiles(instance: dict[str, Any]) -> dict[str, dict[str, Any]]:
    items = extract_named_list(instance, "items")
    if isinstance(items, list) and items and all(isinstance(item, dict) for item in items):
        profiles: dict[str, dict[str, Any]] = {}
        for idx, item in enumerate(items, start=1):
            item_id = item.get("id") or item.get("item") or item.get("name") or idx
            item_key = str(item_id)
            match = re.search(r"(\d+)$", item_key)
            if match:
                item_key = str(int(match.group(1)))
            resources = item.get("resources") or item.get("weights")
            if isinstance(resources, dict):
                ordered_keys = sorted(resources.keys())
                weight_tuple = tuple(to_number(resources[key]) for key in ordered_keys)
            elif isinstance(resources, list):
                weight_tuple = tuple(to_number(x) for x in resources)
            else:
                continue
            profiles[item_key] = {
                "value": to_number(item.get("value") if "value" in item else item.get("profit")),
                "weights": weight_tuple,
            }
        if profiles:
            return profiles
    values = instance.get("values")
    weights = instance.get("weights")
    if not isinstance(items, list) or not isinstance(values, list) or not isinstance(weights, list):
        return {}
    if not (len(items) == len(values) == len(weights)):
        return {}
    profiles: dict[str, dict[str, Any]] = {}
    for item, value, weight_row in zip(items, values, weights):
        if not isinstance(weight_row, list):
            continue
        profiles[str(item)] = {
            "value": to_number(value),
            "weights": tuple(to_number(x) for x in weight_row),
        }
    return profiles


def extract_capacity_map(instance: dict[str, Any]) -> dict[str, float | None]:
    for key in ("resource_limits", "resource_capacities", "resource_capacity", "capacities"):
        raw = instance.get(key)
        if isinstance(raw, dict):
            return {str(resource): to_number(capacity) for resource, capacity in raw.items()}
    renewable_resources = instance.get("renewable_resources")
    if isinstance(renewable_resources, list):
        capacities: dict[str, float | None] = {}
        for resource in renewable_resources:
            if not isinstance(resource, dict):
                continue
            resource_id = resource.get("id") or resource.get("resource") or resource.get("name")
            if resource_id is None:
                continue
            capacities[str(resource_id)] = to_number(resource.get("capacity"))
        if capacities:
            return capacities
    resources_payload = instance.get("resources")
    if isinstance(resources_payload, list):
        capacities: dict[str, float | None] = {}
        for resource in resources_payload:
            if not isinstance(resource, dict):
                continue
            resource_id = resource.get("id") or resource.get("resource") or resource.get("name")
            if resource_id is None:
                continue
            capacities[str(resource_id)] = to_number(resource.get("capacity"))
        if capacities:
            return capacities
    capacities = instance.get("capacities")
    if not isinstance(capacities, list):
        return {}
    resources = extract_named_list(instance, "resources")
    if resources and len(resources) == len(capacities):
        return {str(resource): to_number(capacity) for resource, capacity in zip(resources, capacities)}
    return {f"R{i + 1}": to_number(capacity) for i, capacity in enumerate(capacities)}


def natural_label_sort_key(value: Any) -> tuple[Any, ...]:
    text = str(value)
    parts = re.split(r"(\d+)", text)
    key: list[tuple[int, Any]] = []
    for part in parts:
        if not part:
            continue
        if part.isdigit():
            key.append((0, int(part)))
        else:
            key.append((1, part.lower()))
    return tuple(key)


def extract_first_text_field(record: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = record.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def extract_first_numeric_field(record: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    for key in keys:
        value = to_number(record.get(key))
        if value is not None:
            return float(value)
    return None


def normalize_named_numeric_mapping(raw: Any) -> dict[str, float]:
    if not isinstance(raw, dict):
        return {}
    normalized: dict[str, float] = {}
    for key, value in raw.items():
        numeric = to_number(value)
        if numeric is not None:
            normalized[str(key)] = float(numeric)
    return normalized


def normalize_nested_numeric_mapping(raw: Any) -> dict[str, dict[str, float]]:
    if not isinstance(raw, dict):
        return {}
    normalized: dict[str, dict[str, float]] = {}
    for outer_key, inner in raw.items():
        if not isinstance(inner, dict):
            continue
        parsed = normalize_named_numeric_mapping(inner)
        if parsed:
            normalized[str(outer_key)] = parsed
    return normalized


def normalize_nested_string_mapping(raw: Any) -> dict[str, dict[str, str]]:
    if not isinstance(raw, dict):
        return {}
    normalized: dict[str, dict[str, str]] = {}
    for outer_key, inner in raw.items():
        if not isinstance(inner, dict):
            continue
        parsed: dict[str, str] = {}
        for inner_key, value in inner.items():
            if value is None:
                continue
            text = str(value).strip()
            if text:
                parsed[str(inner_key)] = text
        if parsed:
            normalized[str(outer_key)] = parsed
    return normalized


def extract_scheduling_precedence_arc_set(instance: dict[str, Any]) -> set[tuple[str, str]]:
    raw = instance.get("precedence_arcs")
    if not isinstance(raw, list):
        raw = instance.get("precedence_relations")
    if not isinstance(raw, list):
        return set()
    arcs: set[tuple[str, str]] = set()
    for item in raw:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            arcs.add((str(item[0]), str(item[1])))
        elif isinstance(item, dict):
            tail = item.get("from") if "from" in item else item.get("tail", item.get("source"))
            head = item.get("to") if "to" in item else item.get("head", item.get("target"))
            if tail is not None and head is not None:
                arcs.add((str(tail), str(head)))
    return arcs


def extract_job_shop_operation_profiles(instance: dict[str, Any]) -> dict[str, dict[str, Any]]:
    profiles: dict[str, dict[str, Any]] = {}
    jobs_payload = instance.get("jobs")
    if isinstance(jobs_payload, list):
        for job_payload in jobs_payload:
            if not isinstance(job_payload, dict):
                continue
            job_id = (
                job_payload.get("id")
                or job_payload.get("job")
                or job_payload.get("job_id")
                or job_payload.get("name")
            )
            operations = job_payload.get("operations")
            if job_id is None or not isinstance(operations, list):
                continue
            for index, operation in enumerate(operations, start=1):
                if not isinstance(operation, dict):
                    continue
                raw_operation_id = (
                    operation.get("operation")
                    or operation.get("operation_id")
                    or operation.get("op")
                    or operation.get("id")
                    or f"O{index}"
                )
                operation_id = str(raw_operation_id)
                if operation_id.startswith(f"{job_id}-"):
                    profile_key = operation_id
                else:
                    profile_key = f"{job_id}-{operation_id}"
                profiles[profile_key] = {
                    "machine": extract_first_text_field(operation, ("machine", "machine_id", "resource")),
                    "duration": normalize_routing_numeric(
                        extract_first_numeric_field(operation, ("duration", "processing_time", "proc_time"))
                    ),
                }
        if profiles:
            return profiles
    operation_records = instance.get("operation_records")
    if isinstance(operation_records, list):
        for item in operation_records:
            if not isinstance(item, dict):
                continue
            job = extract_first_text_field(item, ("job", "job_id"))
            operation = extract_first_text_field(item, ("operation", "operation_id", "op"))
            machine = extract_first_text_field(item, ("machine", "machine_id", "resource"))
            duration = extract_first_numeric_field(item, ("duration", "processing_time", "proc_time"))
            if job is None or operation is None:
                continue
            profiles[f"{job}-{operation}"] = {
                "machine": machine,
                "duration": normalize_routing_numeric(duration),
            }
        if profiles:
            return profiles
    machine_assignment = instance.get("machine_assignment") if isinstance(instance.get("machine_assignment"), dict) else {}
    processing_time = instance.get("processing_time") if isinstance(instance.get("processing_time"), dict) else {}
    for job, op_map in machine_assignment.items():
        if not isinstance(op_map, dict):
            continue
        for operation, machine in op_map.items():
            duration = None
            if isinstance(processing_time.get(job), dict):
                duration = to_number(processing_time[job].get(operation))
            profiles[f"{job}-{operation}"] = {
                "machine": str(machine),
                "duration": normalize_routing_numeric(duration),
            }
    return profiles


def extract_parallel_machine_job_profiles(instance: dict[str, Any]) -> dict[str, dict[str, Any]]:
    jobs_payload = instance.get("jobs")
    if isinstance(jobs_payload, list):
        profiles: dict[str, dict[str, Any]] = {}
        machine_list = [str(x) for x in instance.get("machines", [])] if isinstance(instance.get("machines"), list) else []
        saw_parallel_machine_shape = False
        for job_payload in jobs_payload:
            if not isinstance(job_payload, dict):
                continue
            if isinstance(job_payload.get("operations"), list):
                continue
            job_id = job_payload.get("id") or job_payload.get("job")
            if job_id is None:
                continue
            eligible = job_payload.get("eligible_machines")
            eligible_machines = (
                tuple(sorted(str(machine) for machine in eligible))
                if isinstance(eligible, list)
                else tuple(machine_list)
            )
            durations_map = None
            for key in ("effective_processing_time", "effective_durations", "processing_time_by_machine"):
                raw = job_payload.get(key)
                if isinstance(raw, dict):
                    durations_map = raw
                    break
            duration_tuple = tuple()
            if isinstance(durations_map, dict):
                saw_parallel_machine_shape = True
                duration_tuple = tuple(
                    (str(machine), normalize_routing_numeric(duration))
                    for machine, duration in sorted(durations_map.items(), key=lambda item: natural_label_sort_key(item[0]))
                )
            else:
                duration = extract_first_numeric_field(job_payload, ("processing_time", "duration", "base_duration"))
                if duration is not None and eligible_machines:
                    saw_parallel_machine_shape = True
                    duration_tuple = tuple((machine, normalize_routing_numeric(duration)) for machine in eligible_machines)
            profiles[str(job_id)] = {
                "eligible_machines": eligible_machines,
                "durations": duration_tuple,
            }
        if profiles and saw_parallel_machine_shape:
            return profiles
    jobs = [str(x) for x in extract_named_list(instance, "jobs")]
    if not jobs:
        jobs = sorted(
            {str(key) for key in (instance.get("eligibility") or {}).keys()}
            | {str(key) for key in (instance.get("effective_processing_time") or {}).keys()},
            key=natural_label_sort_key,
        )
    eligibility = instance.get("eligibility") if isinstance(instance.get("eligibility"), dict) else {}
    effective_processing_time = (
        instance.get("effective_processing_time") if isinstance(instance.get("effective_processing_time"), dict) else {}
    )
    scalar_processing_times = {}
    for key in ("processing_times", "processing_time", "base_processing_time"):
        raw = instance.get(key)
        if isinstance(raw, dict):
            scalar_processing_times = raw
            break
    profiles: dict[str, dict[str, Any]] = {}
    for job in jobs:
        eligible = eligibility.get(job)
        eligible_machines = (
            tuple(sorted(str(machine) for machine in eligible))
            if isinstance(eligible, list)
            else tuple()
        )
        durations = effective_processing_time.get(job)
        duration_tuple = tuple()
        if isinstance(durations, dict):
            duration_tuple = tuple(
                (str(machine), normalize_routing_numeric(duration))
                for machine, duration in sorted(durations.items(), key=lambda item: natural_label_sort_key(item[0]))
            )
        elif job in scalar_processing_times and eligible_machines:
            duration = to_number(scalar_processing_times.get(job))
            if duration is not None:
                duration_tuple = tuple((machine, normalize_routing_numeric(duration)) for machine in eligible_machines)
        if eligible_machines or duration_tuple:
            profiles[job] = {
                "eligible_machines": eligible_machines,
                "durations": duration_tuple,
            }
    return profiles


def extract_rcpsp_activity_profiles(instance: dict[str, Any]) -> dict[str, dict[str, Any]]:
    activities_payload = instance.get("activities")
    if isinstance(activities_payload, list):
        profiles: dict[str, dict[str, Any]] = {}
        for activity_payload in activities_payload:
            if not isinstance(activity_payload, dict):
                continue
            activity_id = activity_payload.get("id") or activity_payload.get("activity") or activity_payload.get("name")
            if activity_id is None:
                continue
            demand_payload = activity_payload.get("resource_demand")
            demand_tuple = tuple()
            if isinstance(demand_payload, dict):
                demand_tuple = tuple(
                    (str(resource), normalize_routing_numeric(value))
                    for resource, value in sorted(demand_payload.items(), key=lambda item: natural_label_sort_key(item[0]))
                )
            profiles[str(activity_id)] = {
                "duration": normalize_routing_numeric(activity_payload.get("duration")),
                "resource_demand": demand_tuple,
            }
        if profiles:
            return profiles
    activities = [str(x) for x in extract_named_list(instance, "activities")]
    if not activities:
        activities = sorted((str(key) for key in (instance.get("duration") or {}).keys()), key=natural_label_sort_key)
    durations = instance.get("duration") if isinstance(instance.get("duration"), dict) else {}
    resource_demand = instance.get("resource_demand") if isinstance(instance.get("resource_demand"), dict) else {}
    profiles: dict[str, dict[str, Any]] = {}
    for activity in activities:
        demand_payload = resource_demand.get(activity)
        demand_tuple = tuple()
        if isinstance(demand_payload, dict):
            demand_tuple = tuple(
                (str(resource), normalize_routing_numeric(value))
                for resource, value in sorted(demand_payload.items(), key=lambda item: natural_label_sort_key(item[0]))
            )
        profiles[activity] = {
            "duration": normalize_routing_numeric(durations.get(activity)),
            "resource_demand": demand_tuple,
        }
    return profiles


def extract_flow_shop_stage_machine_profiles(instance: dict[str, Any]) -> dict[str, dict[str, Any]]:
    stages_payload = instance.get("stages")
    if isinstance(stages_payload, list) and stages_payload and all(isinstance(stage, dict) for stage in stages_payload):
        profiles: dict[str, dict[str, Any]] = {}
        for stage in stages_payload:
            stage_id = stage.get("id") or stage.get("stage") or stage.get("name")
            machines = stage.get("machines") or stage.get("machine_ids")
            if stage_id is None or not isinstance(machines, list):
                continue
            profiles[str(stage_id)] = {"machines": tuple(sorted(str(machine) for machine in machines))}
        if profiles:
            return profiles
    sets_payload = instance.get("sets") if isinstance(instance.get("sets"), dict) else {}
    machines_by_stage = sets_payload.get("machines_by_stage") if isinstance(sets_payload.get("machines_by_stage"), dict) else {}
    profiles: dict[str, dict[str, Any]] = {}
    for stage, machines in machines_by_stage.items():
        if not isinstance(machines, list):
            continue
        profiles[str(stage)] = {"machines": tuple(sorted(str(machine) for machine in machines))}
    return profiles


def extract_flow_shop_job_stage_profiles(instance: dict[str, Any]) -> dict[str, dict[str, Any]]:
    sets_payload = instance.get("sets") if isinstance(instance.get("sets"), dict) else {}
    stage_hint_present = bool(
        (isinstance(instance.get("common_stage_order"), list) and instance.get("common_stage_order"))
        or (isinstance(instance.get("stages"), list) and instance.get("stages"))
        or (isinstance(sets_payload.get("machines_by_stage"), dict) and sets_payload.get("machines_by_stage"))
    )
    jobs_payload = instance.get("jobs")
    if isinstance(jobs_payload, list) and jobs_payload and all(isinstance(job, dict) for job in jobs_payload):
        profiles: dict[str, dict[str, Any]] = {}
        for job_payload in jobs_payload:
            job_id = job_payload.get("id") or job_payload.get("job")
            if job_id is None:
                continue
            stage_map = None
            for key in ("processing_time", "processing_times", "stage_processing_times", "processing_time_by_stage"):
                raw = job_payload.get(key)
                if isinstance(raw, dict):
                    stage_map = raw
                    break
            if isinstance(stage_map, dict):
                for stage, duration in stage_map.items():
                    profiles[f"{job_id}@{stage}"] = {"duration": normalize_routing_numeric(duration)}
                continue
            operations = job_payload.get("operations")
            if isinstance(operations, list):
                for operation in operations:
                    if not isinstance(operation, dict):
                        continue
                    stage = operation.get("stage") or operation.get("stage_id") or operation.get("operation")
                    if stage is None or (not stage_hint_present and operation.get("stage") is None and operation.get("stage_id") is None):
                        continue
                    duration = extract_first_numeric_field(operation, ("duration", "processing_time", "proc_time"))
                    profiles[f"{job_id}@{stage}"] = {"duration": normalize_routing_numeric(duration)}
        if profiles and stage_hint_present:
            return profiles
    if not stage_hint_present:
        return {}
    processing_time = {}
    for key in ("processing_time", "processing_times", "stage_processing_times", "processing_time_by_stage"):
        raw = instance.get(key)
        if isinstance(raw, dict):
            processing_time = raw
            break
    profiles: dict[str, dict[str, Any]] = {}
    for job, stage_map in processing_time.items():
        if not isinstance(stage_map, dict):
            continue
        for stage, duration in stage_map.items():
            profiles[f"{job}@{stage}"] = {"duration": normalize_routing_numeric(duration)}
    return profiles


def normalize_routing_numeric(value: Any) -> int | float | None:
    numeric = to_number(value)
    if numeric is None:
        return None
    numeric = float(numeric)
    if abs(numeric - round(numeric)) <= 1e-9:
        return int(round(numeric))
    return round(numeric, 6)


def extract_coordinate_pair(value: Any) -> tuple[float, float] | None:
    if isinstance(value, dict):
        x = to_number(value.get("x"))
        y = to_number(value.get("y"))
        if x is not None and y is not None:
            return (round(float(x), 6), round(float(y), 6))
        nested = value.get("coordinates") or value.get("coords")
        if nested is not None:
            return extract_coordinate_pair(nested)
        return None
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        x = to_number(value[0])
        y = to_number(value[1])
        if x is not None and y is not None:
            return (round(float(x), 6), round(float(y), 6))
    return None


def normalize_routing_node_id(node_id: Any, *, depot_like: bool = False) -> str:
    if depot_like:
        return "__DEPOT__"
    return str(node_id)


def looks_like_routing_depot_id(node_id: Any) -> bool:
    text = str(node_id).strip().lower()
    return text in {"depot", "d", "start", "origin", "source"}


def extract_routing_time_window(value: Any) -> tuple[int | float, int | float] | None:
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        open_time = normalize_routing_numeric(value[0])
        close_time = normalize_routing_numeric(value[1])
        if open_time is not None and close_time is not None:
            return (open_time, close_time)
        return None
    if not isinstance(value, dict):
        return None
    window = value.get("time_window") or value.get("timeWindow")
    if isinstance(window, (list, tuple)) and len(window) >= 2:
        open_time = normalize_routing_numeric(window[0])
        close_time = normalize_routing_numeric(window[1])
        if open_time is not None and close_time is not None:
            return (open_time, close_time)
    start = (
        value.get("ready_time")
        if value.get("ready_time") is not None
        else value.get("readyTime")
        if value.get("readyTime") is not None
        else value.get("window_start")
        if value.get("window_start") is not None
        else value.get("windowStart")
        if value.get("windowStart") is not None
        else value.get("open_time")
        if value.get("open_time") is not None
        else value.get("openTime")
    )
    end = (
        value.get("due_date")
        if value.get("due_date") is not None
        else value.get("dueDate")
        if value.get("dueDate") is not None
        else value.get("window_end")
        if value.get("window_end") is not None
        else value.get("windowEnd")
        if value.get("windowEnd") is not None
        else value.get("close_time")
        if value.get("close_time") is not None
        else value.get("closeTime")
    )
    open_time = normalize_routing_numeric(start)
    close_time = normalize_routing_numeric(end)
    if open_time is not None and close_time is not None:
        return (open_time, close_time)
    return None


def looks_like_routing_depot_payload(node_id: Any, payload: Any) -> bool:
    if looks_like_routing_depot_id(node_id):
        return True
    if not isinstance(payload, dict):
        return False
    if payload.get("is_depot") is True:
        return True
    node_type = str(
        payload.get("type")
        or payload.get("node_type")
        or payload.get("nodeType")
        or payload.get("role")
        or ""
    ).strip().lower()
    return node_type == "depot"


def extract_routing_node_profiles(instance: dict[str, Any]) -> dict[str, dict[str, Any]]:
    profiles: dict[str, dict[str, Any]] = {}

    def add_profile(
        node_id: Any,
        *,
        coords: Any = None,
        demand: Any = None,
        time_window: Any = None,
        service_time: Any = None,
        depot_like: bool = False,
    ) -> None:
        key = normalize_routing_node_id(node_id, depot_like=depot_like)
        profile: dict[str, Any] = {}
        coord_pair = extract_coordinate_pair(coords)
        if coord_pair is not None:
            profile["coords"] = coord_pair
        demand_value = normalize_routing_numeric(demand)
        if demand_value is not None:
            profile["demand"] = demand_value
        normalized_time_window = extract_routing_time_window(time_window)
        if normalized_time_window is not None:
            profile["time_window"] = normalized_time_window
        service_value = normalize_routing_numeric(service_time)
        if service_value is not None:
            profile["service_time"] = service_value
        profiles[key] = profile

    if isinstance(instance.get("cities"), list):
        for city in instance["cities"]:
            if not isinstance(city, dict):
                continue
            city_id = city.get("id") or city.get("node_id") or city.get("name") or city.get("label")
            if city_id is None:
                continue
            add_profile(city_id, coords=city)
        if profiles:
            return profiles

    if isinstance(instance.get("cities"), dict):
        for city_id, payload in instance["cities"].items():
            if isinstance(payload, dict):
                add_profile(city_id, coords=payload.get("coordinates") or payload.get("coords") or payload)
            else:
                add_profile(city_id)
        if profiles:
            return profiles

    if isinstance(instance.get("nodes"), list) and all(isinstance(node, dict) for node in instance["nodes"]):
        for node in instance["nodes"]:
            node_id = node.get("id") or node.get("node_id") or node.get("name") or node.get("label")
            if node_id is None:
                continue
            add_profile(
                node_id,
                coords=node,
                demand=node.get("demand"),
                time_window=node,
                service_time=node.get("service_time"),
                depot_like=looks_like_routing_depot_payload(node_id, node),
            )
        if profiles:
            return profiles

    if isinstance(instance.get("nodes"), dict):
        for raw_node_id, payload in instance["nodes"].items():
            if isinstance(payload, dict):
                add_profile(
                    raw_node_id,
                    coords=payload,
                    demand=payload.get("demand"),
                    time_window=payload,
                    service_time=payload.get("service_time"),
                    depot_like=looks_like_routing_depot_payload(raw_node_id, payload),
                )
            else:
                add_profile(raw_node_id, depot_like=looks_like_routing_depot_id(raw_node_id))
        if profiles:
            return profiles

    depot_payload = instance.get("depot")
    customers_payload = instance.get("customers")
    if isinstance(depot_payload, dict) and isinstance(customers_payload, list):
        depot_id = depot_payload.get("id") or depot_payload.get("node_id") or depot_payload.get("name") or "Depot"
        add_profile(
            depot_id,
            coords=depot_payload,
            demand=depot_payload.get("demand"),
            time_window=depot_payload,
            service_time=depot_payload.get("service_time"),
            depot_like=True,
        )
        for customer in customers_payload:
            if not isinstance(customer, dict):
                continue
            customer_id = customer.get("id") or customer.get("node_id") or customer.get("name") or customer.get("label")
            if customer_id is None:
                continue
            add_profile(
                customer_id,
                coords=customer,
                demand=customer.get("demand"),
                time_window=customer,
                service_time=customer.get("service_time"),
            )
        if profiles:
            return profiles

    if isinstance(customers_payload, dict):
        depot_id = str(instance.get("depot") or "Depot")
        add_profile(depot_id, depot_like=True)
        for customer_id, payload in customers_payload.items():
            if isinstance(payload, dict):
                add_profile(
                    customer_id,
                    coords=payload,
                    demand=payload.get("demand"),
                    time_window=payload,
                    service_time=payload.get("service_time"),
                )
            else:
                add_profile(customer_id)
        if profiles:
            return profiles

    coordinates = instance.get("coordinates")
    if isinstance(coordinates, dict):
        depot_id = instance.get("depot")
        customer_ids = {str(x) for x in extract_named_list(instance, "customers")}
        node_ids = [str(x) for x in extract_named_list(instance, "nodes")] or sorted(str(x) for x in coordinates.keys())
        demands = instance.get("demands") if isinstance(instance.get("demands"), dict) else {}
        time_windows = instance.get("time_windows") if isinstance(instance.get("time_windows"), dict) else {}
        service_times = instance.get("service_times") if isinstance(instance.get("service_times"), dict) else {}
        for node_id in node_ids:
            add_profile(
                node_id,
                coords=coordinates.get(node_id),
                demand=demands.get(node_id),
                time_window=time_windows.get(node_id),
                service_time=service_times.get(node_id),
                depot_like=depot_id is not None and str(node_id) == str(depot_id),
            )
        if profiles:
            return profiles

    return profiles


def extract_routing_vehicle_type_profiles(instance: dict[str, Any]) -> dict[str, dict[str, Any]]:
    profiles: dict[str, dict[str, Any]] = {}
    fleet_categories = instance.get("fleet_categories")
    if isinstance(fleet_categories, list):
        for category in fleet_categories:
            if not isinstance(category, dict):
                continue
            type_id = category.get("type") or category.get("type_id") or category.get("id")
            if type_id is None:
                continue
            profiles[str(type_id)] = {
                "available_count": normalize_routing_numeric(category.get("count", category.get("available_count"))),
                "capacity": normalize_routing_numeric(category.get("capacity")),
                "fixed_activation_cost": normalize_routing_numeric(
                    category.get("fixed_activation_cost", category.get("fixed_cost"))
                ),
                "distance_multiplier": normalize_routing_numeric(category.get("distance_multiplier")),
            }
        if profiles:
            return profiles

    vehicle_type_parameters = instance.get("vehicle_type_parameters")
    if isinstance(vehicle_type_parameters, dict):
        type_to_vehicles = instance.get("type_to_vehicles") if isinstance(instance.get("type_to_vehicles"), dict) else {}
        for type_id, payload in vehicle_type_parameters.items():
            if not isinstance(payload, dict):
                continue
            available_count = payload.get("available_count")
            if available_count is None and isinstance(type_to_vehicles.get(type_id), list):
                available_count = len(type_to_vehicles[type_id])
            profiles[str(type_id)] = {
                "available_count": normalize_routing_numeric(available_count),
                "capacity": normalize_routing_numeric(payload.get("capacity")),
                "fixed_activation_cost": normalize_routing_numeric(payload.get("fixed_activation_cost")),
                "distance_multiplier": normalize_routing_numeric(payload.get("distance_multiplier")),
            }
        if profiles:
            return profiles

    return profiles


def extract_routing_fleet_scalars(instance: dict[str, Any]) -> dict[str, float | None]:
    fleet_payload = instance.get("fleet")
    if isinstance(fleet_payload, dict):
        scalars: dict[str, float | None] = {}
        if fleet_payload.get("num_vehicles") is not None:
            scalars["num_vehicles"] = to_number(fleet_payload.get("num_vehicles"))
        if fleet_payload.get("vehicle_capacity") is not None:
            scalars["vehicle_capacity"] = to_number(fleet_payload.get("vehicle_capacity"))
        elif fleet_payload.get("capacity") is not None:
            scalars["vehicle_capacity"] = to_number(fleet_payload.get("capacity"))
        if scalars:
            return scalars
    fleet_parameters = instance.get("fleet_parameters")
    if isinstance(fleet_parameters, dict):
        scalars: dict[str, float | None] = {}
        if fleet_parameters.get("num_vehicles") is not None:
            scalars["num_vehicles"] = to_number(fleet_parameters.get("num_vehicles"))
        if fleet_parameters.get("vehicle_capacity") is not None:
            scalars["vehicle_capacity"] = to_number(fleet_parameters.get("vehicle_capacity"))
        if scalars:
            return scalars
    if instance.get("vehicle_capacity") is None:
        return {}
    scalars = {"vehicle_capacity": to_number(instance.get("vehicle_capacity"))}
    vehicles = extract_named_list(instance, "vehicles")
    if vehicles:
        scalars["num_vehicles"] = float(len(vehicles))
    return scalars


def normalize_temporal_network_role(
    role: Any,
    node_id: Any,
    *,
    source_ids: set[str],
    sink_ids: set[str],
    storage_ids: set[str],
) -> str:
    node_key = str(node_id)
    role_text = str(role).strip().lower() if role is not None else ""
    if node_key in source_ids or "source" in role_text:
        return "source"
    if node_key in sink_ids or "sink" in role_text:
        return "sink"
    if node_key in storage_ids or any(token in role_text for token in ("storage", "warehouse", "inventory")):
        return "storage"
    return "regular"


def normalize_temporal_value_vector(raw: Any, periods: list[str]) -> tuple[int | float, ...] | None:
    if isinstance(raw, dict):
        ordered_periods = periods or sorted(str(key) for key in raw.keys())
        values: list[int | float] = []
        for period in ordered_periods:
            value = raw.get(period)
            if value is None:
                value = raw.get(str(period))
            normalized = normalize_routing_numeric(value)
            values.append(0 if normalized is None else normalized)
        return tuple(values)
    if isinstance(raw, (list, tuple)):
        values = []
        for value in raw:
            normalized = normalize_routing_numeric(value)
            values.append(0 if normalized is None else normalized)
        return tuple(values)
    if raw is None:
        return tuple(0 for _ in periods) if periods else None
    normalized = normalize_routing_numeric(raw)
    if normalized is None:
        return None
    return (normalized,)


def extract_temporal_network_node_profiles(instance: dict[str, Any]) -> dict[str, dict[str, Any]]:
    nodes_payload = instance.get("nodes")
    node_data_payload = instance.get("node_data")
    has_temporal_network_signal = bool(
        instance.get("net_supply_by_node_period")
        or instance.get("storage")
        or instance.get("node_roles")
        or instance.get("source") is not None
        or instance.get("sink") is not None
        or instance.get("storage_nodes")
        or instance.get("time_periods") is not None
    )
    if not has_temporal_network_signal and isinstance(nodes_payload, list):
        has_temporal_network_signal = any(
            isinstance(node, dict)
            and any(key in node for key in ("net_supply_demand", "storage_capacity", "holding_costs", "role"))
            for node in nodes_payload
        )
    if not has_temporal_network_signal and isinstance(node_data_payload, dict):
        has_temporal_network_signal = any(
            isinstance(node, dict)
            and any(key in node for key in ("net_supply_demand", "net_supply", "storage_capacity", "holding_costs", "role"))
            for node in node_data_payload.values()
        )
    if not has_temporal_network_signal and isinstance(instance.get("arcs"), list):
        has_temporal_network_signal = any(
            isinstance(arc, dict) and any(key in arc for key in ("period_data", "time_period_data"))
            for arc in instance["arcs"]
        )
    if not has_temporal_network_signal:
        return {}

    periods = [str(period) for period in extract_named_list(instance, "periods")]
    if not periods and isinstance(instance.get("periods"), list):
        periods = [str(period) for period in instance.get("periods", [])]

    source_ids = {str(instance["source"])} if instance.get("source") is not None else set()
    sink_ids = {str(instance["sink"])} if instance.get("sink") is not None else set()
    storage_ids = {str(node) for node in instance.get("storage_nodes", [])} if isinstance(instance.get("storage_nodes"), list) else set()

    node_roles = instance.get("node_roles") if isinstance(instance.get("node_roles"), dict) else {}
    net_supply = normalize_nested_numeric_mapping(instance.get("net_supply_by_node_period"))
    storage_payload = instance.get("storage") if isinstance(instance.get("storage"), dict) else {}

    node_records: dict[str, dict[str, Any]] = {}
    node_ids: set[str] = set()
    if isinstance(nodes_payload, list):
        for node in nodes_payload:
            if isinstance(node, dict):
                node_id = node.get("id") or node.get("node_id") or node.get("name") or node.get("label")
                if node_id is None:
                    continue
                node_key = str(node_id)
                node_ids.add(node_key)
                node_records[node_key] = node
            else:
                node_ids.add(str(node))
    elif isinstance(nodes_payload, dict):
        for raw_node_id, payload in nodes_payload.items():
            node_key = str(raw_node_id)
            node_ids.add(node_key)
            if isinstance(payload, dict):
                node_records[node_key] = payload
    if isinstance(node_data_payload, dict):
        for raw_node_id, payload in node_data_payload.items():
            node_key = str(raw_node_id)
            node_ids.add(node_key)
            if isinstance(payload, dict):
                node_records[node_key] = payload

    node_ids |= set(str(node_id) for node_id in node_roles.keys())
    node_ids |= set(str(node_id) for node_id in net_supply.keys())
    node_ids |= set(str(node_id) for node_id in storage_payload.keys())
    node_ids |= source_ids | sink_ids | storage_ids

    profiles: dict[str, dict[str, Any]] = {}
    for node_id in sorted(node_ids, key=lambda value: (to_number(value) is None, to_number(value) if to_number(value) is not None else str(value))):
        node_record = node_records.get(node_id, {})
        raw_role = node_record.get("role") if isinstance(node_record, dict) else None
        if raw_role is None:
            raw_role = node_roles.get(node_id)

        storage_record = storage_payload.get(node_id) if isinstance(storage_payload.get(node_id), dict) else None
        if storage_record is None and isinstance(node_record, dict) and any(
            key in node_record for key in ("storage_capacity", "holding_costs", "holding_cost_by_period")
        ):
            storage_record = node_record

        semantic_role = normalize_temporal_network_role(
            raw_role,
            node_id,
            source_ids=source_ids,
            sink_ids=sink_ids,
            storage_ids=storage_ids,
        )
        profile: dict[str, Any] = {"role": semantic_role}

        supply_raw = node_record.get("net_supply_demand") if isinstance(node_record, dict) else None
        if supply_raw is None and isinstance(node_record, dict):
            supply_raw = node_record.get("net_supply")
        if supply_raw is None:
            supply_raw = net_supply.get(node_id)
        supply_vector = normalize_temporal_value_vector(supply_raw, periods)
        if supply_vector is not None:
            profile["net_supply_demand"] = supply_vector

        storage_capacity = None
        holding_costs_raw = None
        if isinstance(storage_record, dict):
            storage_capacity = storage_record.get("storage_capacity")
            if storage_capacity is None:
                storage_capacity = storage_record.get("capacity")
            holding_costs_raw = storage_record.get("holding_costs")
            if holding_costs_raw is None:
                holding_costs_raw = storage_record.get("holding_cost_by_period")
        storage_capacity_value = normalize_routing_numeric(storage_capacity)
        if storage_capacity_value is not None:
            profile["storage_capacity"] = storage_capacity_value
        holding_costs = normalize_temporal_value_vector(holding_costs_raw, periods)
        if holding_costs is not None and (storage_record is not None or semantic_role == "storage"):
            profile["holding_costs"] = holding_costs

        profiles[node_id] = profile

    return profiles


def compare_profile_maps(
    pred: dict[str, dict[str, Any]],
    truth: dict[str, dict[str, Any]],
    tolerance: float,
    *,
    label: str,
) -> dict[str, Any]:
    pred_keys = set(pred)
    truth_keys = set(truth)
    mismatches = []
    for key in sorted(pred_keys & truth_keys):
        pred_payload = pred[key]
        truth_payload = truth[key]
        value_match = (
            pred_payload.get("value") == truth_payload.get("value")
            if pred_payload.get("value") is None or truth_payload.get("value") is None
            else abs(float(pred_payload["value"]) - float(truth_payload["value"])) <= tolerance
        )
        weights_match = pred_payload.get("weights") == truth_payload.get("weights")
        if not value_match or not weights_match:
            mismatches.append({"id": key, "predicted": pred_payload, "ground_truth": truth_payload})
    return {
        "label": label,
        "predicted_count": len(pred_keys),
        "ground_truth_count": len(truth_keys),
        "missing_sample": sorted(list(truth_keys - pred_keys))[:10],
        "extra_sample": sorted(list(pred_keys - truth_keys))[:10],
        "mismatch_sample": mismatches[:10],
        "exact_match": pred_keys == truth_keys and not mismatches,
    }


def compare_record_maps(
    pred: dict[str, dict[str, Any]],
    truth: dict[str, dict[str, Any]],
    *,
    label: str,
) -> dict[str, Any]:
    pred_keys = set(pred)
    truth_keys = set(truth)
    mismatches = []
    for key in sorted(pred_keys & truth_keys):
        if pred.get(key) != truth.get(key):
            mismatches.append({"id": key, "predicted": pred.get(key), "ground_truth": truth.get(key)})
    return {
        "label": label,
        "predicted_count": len(pred_keys),
        "ground_truth_count": len(truth_keys),
        "missing_sample": sorted(list(truth_keys - pred_keys))[:10],
        "extra_sample": sorted(list(pred_keys - truth_keys))[:10],
        "mismatch_sample": mismatches[:10],
        "exact_match": pred_keys == truth_keys and not mismatches,
    }


def compare_number_maps(
    pred: dict[str, float | None],
    truth: dict[str, float | None],
    tolerance: float,
    *,
    label: str,
) -> dict[str, Any]:
    pred_keys = set(pred)
    truth_keys = set(truth)
    mismatches = []
    for key in sorted(pred_keys & truth_keys):
        p = pred.get(key)
        t = truth.get(key)
        if p is None or t is None:
            if p != t:
                mismatches.append({"id": key, "predicted": p, "ground_truth": t})
        elif abs(p - t) > tolerance:
            mismatches.append({"id": key, "predicted": p, "ground_truth": t})
    return {
        "label": label,
        "predicted_count": len(pred_keys),
        "ground_truth_count": len(truth_keys),
        "missing_sample": sorted(list(truth_keys - pred_keys))[:10],
        "extra_sample": sorted(list(pred_keys - truth_keys))[:10],
        "mismatch_sample": mismatches[:10],
        "exact_match": pred_keys == truth_keys and not mismatches,
    }


def summarize_instance_counts(instance: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    if isinstance(instance.get("variables"), list):
        counts["variables"] = len(instance["variables"])
    if isinstance(instance.get("nodes"), list):
        counts["nodes"] = len(instance["nodes"])
    elif isinstance(instance.get("cities"), list):
        counts["nodes"] = len(instance["cities"])
    if isinstance(instance.get("vertex_ids"), list):
        counts["vertices"] = len(instance["vertex_ids"])
    elif isinstance(instance.get("vertices"), list):
        counts["vertices"] = len(instance["vertices"])
    elif isinstance(instance.get("num_vertices"), int):
        counts["vertices"] = int(instance["num_vertices"])
    elif isinstance(instance.get("n_vertices"), int):
        counts["vertices"] = int(instance["n_vertices"])
    elif isinstance(instance.get("number_of_vertices"), int):
        counts["vertices"] = int(instance["number_of_vertices"])
    if isinstance(instance.get("sets"), dict):
        sets = instance["sets"]
        for key in (
            "vertices",
            "colors",
            "items",
            "candidate_groups",
            "variables",
            "clauses",
            "resources",
            "jobs",
            "machines",
            "operations",
            "stages",
            "activities",
            "real_activities",
            "nodes",
            "customers",
            "vehicles",
            "vehicle_types",
            "drivers",
            "routes",
            "agents",
            "tasks",
            "elements",
            "candidate_subsets",
            "F",
            "C",
            "I",
            "J",
            "E",
            "S",
        ):
            if isinstance(sets.get(key), list):
                counts[key] = len(sets[key])
    if isinstance(instance.get("job_routes"), dict):
        counts.setdefault("jobs", len(instance["job_routes"]))
    if isinstance(instance.get("machine_assignment"), dict):
        counts.setdefault("jobs", len(instance["machine_assignment"]))
    sets_payload = instance.get("sets") if isinstance(instance.get("sets"), dict) else {}
    operations_payload = sets_payload.get("operations")
    if isinstance(operations_payload, dict):
        counts.setdefault(
            "operations",
            sum(len(operations) for operations in operations_payload.values() if isinstance(operations, list)),
        )
    if isinstance(instance.get("machine_speed"), dict):
        counts.setdefault("machines", len(instance["machine_speed"]))
    if isinstance(instance.get("duration"), dict):
        counts.setdefault("activities", len(instance["duration"]))
    if isinstance(instance.get("jobs"), list):
        counts.setdefault("jobs", len(instance["jobs"]))
        if instance["jobs"] and all(isinstance(job, dict) for job in instance["jobs"]):
            total_operations = 0
            for job in instance["jobs"]:
                operations = job.get("operations")
                if isinstance(operations, list):
                    total_operations += len(operations)
            if total_operations:
                counts.setdefault("operations", total_operations)
    if isinstance(instance.get("machines"), list):
        counts.setdefault("machines", len(instance["machines"]))
    if isinstance(instance.get("stages"), list):
        counts.setdefault("stages", len(instance["stages"]))
    if isinstance(instance.get("activities"), list):
        counts.setdefault("activities", len(instance["activities"]))
        if instance["activities"] and all(isinstance(activity, dict) for activity in instance["activities"]):
            real_activity_count = 0
            for activity in instance["activities"]:
                activity_id = str(activity.get("id") or activity.get("activity") or activity.get("name") or "")
                if activity_id and activity_id not in {"Start", "End"}:
                    real_activity_count += 1
            if real_activity_count:
                counts.setdefault("real_activities", real_activity_count)
    if isinstance(instance.get("renewable_resources"), list):
        counts.setdefault("resources", len(instance["renewable_resources"]))
    elif isinstance(instance.get("resources"), list):
        counts.setdefault("resources", len(instance["resources"]))
    precedence_arcs = extract_scheduling_precedence_arc_set(instance)
    if precedence_arcs:
        counts["precedence_arcs"] = len(precedence_arcs)
    if isinstance(instance.get("customers"), list):
        counts["customers"] = len(instance["customers"])
        if isinstance(instance.get("depot"), dict) and "nodes" not in counts:
            counts["nodes"] = len(instance["customers"]) + 1
    if isinstance(instance.get("facilities"), list):
        counts["facilities"] = len(instance["facilities"])
    if isinstance(instance.get("facility"), dict):
        counts["facilities"] = len(instance["facility"])
    if isinstance(instance.get("customer"), dict):
        counts["customers"] = len(instance["customer"])
    if isinstance(instance.get("demand_points"), list):
        counts["customers"] = len(instance["demand_points"])
        counts.setdefault("I", len(instance["demand_points"]))
    if isinstance(instance.get("candidate_sites"), dict):
        counts["facilities"] = len(instance["candidate_sites"])
        counts.setdefault("J", len(instance["candidate_sites"]))
    if isinstance(instance.get("candidate_sites"), list):
        counts["facilities"] = len(instance["candidate_sites"])
        counts.setdefault("J", len(instance["candidate_sites"]))
    if isinstance(instance.get("demand_points"), dict):
        counts["customers"] = len(instance["demand_points"])
        counts.setdefault("I", len(instance["demand_points"]))
    if isinstance(instance.get("candidate_subsets"), dict):
        counts["candidate_subsets"] = len(instance["candidate_subsets"])
    if isinstance(instance.get("vehicles"), list):
        counts["vehicles"] = len(instance["vehicles"])
    if isinstance(instance.get("vehicle_types"), list):
        counts["vehicle_types"] = len(instance["vehicle_types"])
    fleet_categories = instance.get("fleet_categories")
    if isinstance(fleet_categories, list):
        counts["vehicle_types"] = len(fleet_categories)
        available_total = 0
        have_available_total = False
        for category in fleet_categories:
            if not isinstance(category, dict):
                continue
            available = normalize_routing_numeric(category.get("count", category.get("available_count")))
            if isinstance(available, int):
                available_total += available
                have_available_total = True
        if have_available_total:
            counts["vehicles"] = available_total
    if isinstance(instance.get("colors"), list):
        counts["colors"] = len(instance["colors"])
    elif isinstance(instance.get("available_colors"), list):
        counts["colors"] = len(instance["available_colors"])
    elif isinstance(instance.get("num_colors"), int):
        counts["colors"] = int(instance["num_colors"])
    elif isinstance(instance.get("n_colors"), int):
        counts["colors"] = int(instance["n_colors"])
    elif isinstance(instance.get("number_of_colors"), int):
        counts["colors"] = int(instance["number_of_colors"])
    elif isinstance(instance.get("max_colors"), int):
        counts["colors"] = int(instance["max_colors"])
    if isinstance(instance.get("items"), list):
        counts["items"] = len(instance["items"])
    if isinstance(instance.get("groups"), list):
        counts["groups"] = len(instance["groups"])
    if isinstance(instance.get("subsets"), dict):
        counts["subsets"] = len(instance["subsets"])
    if isinstance(instance.get("clauses"), list):
        counts["clauses"] = len(instance["clauses"])
    elif isinstance(instance.get("CNF_clauses"), list):
        counts["clauses"] = len(instance["CNF_clauses"])
    if isinstance(instance.get("implications"), list):
        counts["implications"] = len(instance["implications"])
    elif isinstance(instance.get("implication_rows"), list):
        counts["implications"] = len(instance["implication_rows"])
    if isinstance(instance.get("at_most_one_groups"), list):
        counts["at_most_one_groups"] = len(instance["at_most_one_groups"])
    elif isinstance(instance.get("at_most_one_rows"), list):
        counts["at_most_one_groups"] = len(instance["at_most_one_rows"])
    elif isinstance(instance.get("pairwise_exclusions"), list):
        counts["at_most_one_groups"] = len(instance["pairwise_exclusions"])
    if isinstance(instance.get("cardinality_constraints"), list):
        counts["cardinality_constraints"] = len(instance["cardinality_constraints"])
    elif isinstance(instance.get("cardinality_rows"), list):
        counts["cardinality_constraints"] = len(instance["cardinality_rows"])
    if isinstance(instance.get("resource_limits"), dict):
        counts["resources"] = len(instance["resource_limits"])
    elif isinstance(instance.get("resource_capacities"), dict):
        counts["resources"] = len(instance["resource_capacities"])
    routing_nodes = extract_routing_node_profiles(instance)
    if routing_nodes and "nodes" not in counts:
        counts["nodes"] = len(routing_nodes)
    if routing_nodes and "customers" not in counts:
        counts["customers"] = sum(1 for node_id in routing_nodes if node_id != "__DEPOT__")
    routing_vehicle_types = extract_routing_vehicle_type_profiles(instance)
    if routing_vehicle_types and "vehicle_types" not in counts:
        counts["vehicle_types"] = len(routing_vehicle_types)
    routing_fleet = extract_routing_fleet_scalars(instance)
    if routing_fleet.get("num_vehicles") is not None and "vehicles" not in counts:
        vehicle_count = normalize_routing_numeric(routing_fleet.get("num_vehicles"))
        if isinstance(vehicle_count, int):
            counts["vehicles"] = vehicle_count
    edge_set = extract_edge_set(instance)
    if edge_set:
        counts["edges"] = len(edge_set)
    arc_map = extract_arc_map(instance)
    if arc_map:
        counts["arcs"] = len(arc_map)
    return counts


def normalize_xy_pair(value: Any) -> list[float | int] | None:
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        x = to_number(value[0])
        y = to_number(value[1])
        if x is not None and y is not None:
            return [x, y]
    if isinstance(value, dict):
        x = to_number(value.get("x"))
        y = to_number(value.get("y"))
        if x is not None and y is not None:
            return [x, y]
    return None


def extract_location_facility_profiles(instance: dict[str, Any]) -> dict[str, dict[str, Any]]:
    profiles: dict[str, dict[str, Any]] = {}
    payload = instance.get("facility")
    if isinstance(payload, dict):
        for fid, record in payload.items():
            if not isinstance(record, dict):
                continue
            profile: dict[str, Any] = {}
            xy = normalize_xy_pair(record.get("xy"))
            if xy is not None:
                profile["xy"] = xy
            open_cost = normalize_routing_numeric(record.get("open_cost"))
            if open_cost is None:
                open_cost = normalize_routing_numeric(record.get("opening_cost"))
            if open_cost is not None:
                profile["open_cost"] = open_cost
            radius = normalize_routing_numeric(record.get("radius"))
            if radius is None:
                radius = normalize_routing_numeric(record.get("coverage_radius"))
            if radius is not None:
                profile["radius"] = radius
            profiles[str(fid)] = profile
        return profiles

    payload = instance.get("facilities")
    if isinstance(payload, list):
        for record in payload:
            if not isinstance(record, dict):
                continue
            fid = record.get("id") or record.get("facility_id") or record.get("name")
            if fid is None:
                continue
            profile = {}
            xy = normalize_xy_pair(record)
            if xy is None:
                xy = normalize_xy_pair(record.get("xy"))
            if xy is not None:
                profile["xy"] = xy
            open_cost = normalize_routing_numeric(record.get("open_cost"))
            if open_cost is None:
                open_cost = normalize_routing_numeric(record.get("opening_cost"))
            if open_cost is not None:
                profile["open_cost"] = open_cost
            radius = normalize_routing_numeric(record.get("radius"))
            if radius is None:
                radius = normalize_routing_numeric(record.get("coverage_radius"))
            if radius is not None:
                profile["radius"] = radius
            profiles[str(fid)] = profile
        if profiles:
            return profiles

    payload = instance.get("candidate_sites")
    if isinstance(payload, dict):
        for sid, record in payload.items():
            profile = {}
            if isinstance(record, dict):
                xy = normalize_xy_pair(record.get("xy"))
                if xy is None:
                    xy = normalize_xy_pair(record)
                if xy is not None:
                    profile["xy"] = xy
            profiles[str(sid)] = profile
        return profiles

    if isinstance(payload, list):
        for record in payload:
            if not isinstance(record, dict):
                continue
            sid = record.get("id") or record.get("site_id") or record.get("facility_id") or record.get("name")
            if sid is None:
                continue
            profile = {}
            xy = normalize_xy_pair(record)
            if xy is None:
                xy = normalize_xy_pair(record.get("xy"))
            if xy is not None:
                profile["xy"] = xy
            profiles[str(sid)] = profile
    return profiles


def extract_location_customer_profiles(instance: dict[str, Any]) -> dict[str, dict[str, Any]]:
    profiles: dict[str, dict[str, Any]] = {}
    payload = instance.get("customer")
    if isinstance(payload, dict):
        for cid, record in payload.items():
            if not isinstance(record, dict):
                continue
            profile: dict[str, Any] = {}
            xy = normalize_xy_pair(record.get("xy"))
            if xy is not None:
                profile["xy"] = xy
            demand = normalize_routing_numeric(record.get("demand"))
            if demand is not None:
                profile["demand"] = demand
            profiles[str(cid)] = profile
        return profiles

    payload = instance.get("customers")
    if isinstance(payload, list):
        for record in payload:
            if not isinstance(record, dict):
                continue
            cid = record.get("id") or record.get("customer_id") or record.get("name")
            if cid is None:
                continue
            profile = {}
            xy = normalize_xy_pair(record)
            if xy is None:
                xy = normalize_xy_pair(record.get("xy"))
            if xy is not None:
                profile["xy"] = xy
            demand = normalize_routing_numeric(record.get("demand"))
            if demand is not None:
                profile["demand"] = demand
            profiles[str(cid)] = profile
        if profiles:
            return profiles

    payload = instance.get("demand_points")
    if isinstance(payload, dict):
        for did, record in payload.items():
            profile = {}
            if isinstance(record, dict):
                xy = normalize_xy_pair(record.get("xy"))
                if xy is None:
                    xy = normalize_xy_pair(record)
                if xy is not None:
                    profile["xy"] = xy
                demand = normalize_routing_numeric(record.get("demand"))
                if demand is not None:
                    profile["demand"] = demand
            profiles[str(did)] = profile
        return profiles

    if isinstance(payload, list):
        for record in payload:
            if not isinstance(record, dict):
                continue
            did = record.get("id") or record.get("demand_id") or record.get("customer_id") or record.get("name")
            if did is None:
                continue
            profile = {}
            xy = normalize_xy_pair(record)
            if xy is None:
                xy = normalize_xy_pair(record.get("xy"))
            if xy is not None:
                profile["xy"] = xy
            demand = normalize_routing_numeric(record.get("demand"))
            if demand is not None:
                profile["demand"] = demand
            profiles[str(did)] = profile
    return profiles


def extract_location_agent_profiles(instance: dict[str, Any]) -> dict[str, dict[str, Any]]:
    sets_payload = instance.get("sets") if isinstance(instance.get("sets"), dict) else {}
    agent_ids: list[Any] = []
    for key in ("agents", "drivers"):
        if isinstance(sets_payload.get(key), list):
            agent_ids = sets_payload[key]
            break
    capacities = instance.get("agent_capacities") if isinstance(instance.get("agent_capacities"), dict) else {}
    roles = instance.get("agent_roles") if isinstance(instance.get("agent_roles"), dict) else {}
    profiles: dict[str, dict[str, Any]] = {}
    for raw_agent in agent_ids:
        agent = str(raw_agent)
        profile: dict[str, Any] = {}
        capacity = normalize_routing_numeric(capacities.get(agent))
        if capacity is not None:
            profile["capacity"] = capacity
        role = roles.get(agent)
        if role is not None:
            profile["role"] = role
        profiles[agent] = profile
    return profiles


def extract_location_subset_profiles(instance: dict[str, Any]) -> dict[str, dict[str, Any]]:
    payload = instance.get("candidate_subsets")
    if not isinstance(payload, dict):
        return {}
    profiles: dict[str, dict[str, Any]] = {}
    for sid, record in payload.items():
        if not isinstance(record, dict):
            continue
        profile: dict[str, Any] = {}
        covered = record.get("covered_elements")
        if isinstance(covered, list):
            profile["covered_elements"] = list(covered)
        cost = normalize_routing_numeric(record.get("cost"))
        if cost is not None:
            profile["cost"] = cost
        cardinality = normalize_routing_numeric(record.get("cardinality"))
        if cardinality is not None:
            profile["cardinality"] = cardinality
        profiles[str(sid)] = profile
    return profiles


def extract_location_group_profiles(instance: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    payload = instance.get(key)
    if not isinstance(payload, dict):
        return {}
    groups: dict[str, dict[str, Any]] = {}
    for gid, members in payload.items():
        if isinstance(members, list):
            groups[str(gid)] = {"elements": list(members)}
    return groups


def extract_flat_numeric_matrix(instance: dict[str, Any], key: str) -> dict[str, float | None]:
    payload = instance.get(key)
    if not isinstance(payload, dict):
        if key != "distance_matrix":
            return {}
        facility_profiles = extract_location_facility_profiles(instance)
        customer_profiles = extract_location_customer_profiles(instance)
        if not facility_profiles or not customer_profiles:
            return {}
        metric = str(instance.get("distance_metric") or "").strip().lower()
        round_digits = 2 if "euclidean" in metric else 6
        matrix: dict[str, float | None] = {}
        for customer_id, customer in customer_profiles.items():
            cxy = customer.get("xy")
            if not isinstance(cxy, list) or len(cxy) < 2:
                continue
            cx = to_number(cxy[0])
            cy = to_number(cxy[1])
            if cx is None or cy is None:
                continue
            for facility_id, facility in facility_profiles.items():
                fxy = facility.get("xy")
                if not isinstance(fxy, list) or len(fxy) < 2:
                    continue
                fx = to_number(fxy[0])
                fy = to_number(fxy[1])
                if fx is None or fy is None:
                    continue
                dist = math.sqrt((float(cx) - float(fx)) ** 2 + (float(cy) - float(fy)) ** 2)
                matrix[f"{customer_id}->{facility_id}"] = round(dist, round_digits)
        return matrix
    matrix: dict[str, float | None] = {}
    for row_key, row_payload in payload.items():
        if not isinstance(row_payload, dict):
            continue
        for col_key, value in row_payload.items():
            matrix[f"{row_key}->{col_key}"] = to_number(value)
    return matrix


def extract_flat_scalar_map(instance: dict[str, Any], key: str) -> dict[str, float | None]:
    payload = instance.get(key)
    if not isinstance(payload, dict):
        if key != "demand_weights":
            return {}
        payload = instance.get("demand_points")
        if isinstance(payload, dict):
            derived: dict[str, float | None] = {}
            for demand_id, record in payload.items():
                if not isinstance(record, dict):
                    continue
                value = record.get("weight")
                if value is None:
                    value = record.get("demand_weight")
                if value is None:
                    value = record.get("demand")
                numeric = to_number(value)
                if numeric is not None:
                    derived[str(demand_id)] = numeric
            return derived
        if isinstance(payload, list):
            derived = {}
            for record in payload:
                if not isinstance(record, dict):
                    continue
                demand_id = record.get("id") or record.get("demand_id") or record.get("customer_id") or record.get("name")
                if demand_id is None:
                    continue
                value = record.get("weight")
                if value is None:
                    value = record.get("demand_weight")
                if value is None:
                    value = record.get("demand")
                numeric = to_number(value)
                if numeric is not None:
                    derived[str(demand_id)] = numeric
            return derived
        return {}
    return {str(map_key): to_number(value) for map_key, value in payload.items()}


def compare_entity_sets(pred: set[Any], truth: set[Any], label: str) -> dict[str, Any]:
    missing = sorted(list(truth - pred))
    extra = sorted(list(pred - truth))
    overlap = len(pred & truth)
    truth_size = len(truth)
    recall = (overlap / truth_size) if truth_size else None
    return {
        "label": label,
        "predicted_count": len(pred),
        "ground_truth_count": len(truth),
        "overlap_count": overlap,
        "recall_against_ground_truth": recall,
        "missing_sample": missing[:10],
        "extra_sample": extra[:10],
        "exact_match": pred == truth,
    }


def compare_arc_maps(pred: dict[tuple[int, int], float | None], truth: dict[tuple[int, int], float | None], tolerance: float) -> dict[str, Any]:
    pred_keys = set(pred)
    truth_keys = set(truth)
    shared = pred_keys & truth_keys
    capacity_mismatches = []
    for key in sorted(shared):
        p = pred.get(key)
        t = truth.get(key)
        if p is None or t is None:
            if p != t:
                capacity_mismatches.append({"arc": key, "predicted_capacity": p, "ground_truth_capacity": t})
        elif abs(p - t) > tolerance:
            capacity_mismatches.append({"arc": key, "predicted_capacity": p, "ground_truth_capacity": t})
    return {
        "label": "arcs",
        "predicted_count": len(pred_keys),
        "ground_truth_count": len(truth_keys),
        "missing_sample": sorted(list(truth_keys - pred_keys))[:10],
        "extra_sample": sorted(list(pred_keys - truth_keys))[:10],
        "capacity_mismatch_sample": capacity_mismatches[:10],
        "exact_match": pred_keys == truth_keys and not capacity_mismatches,
    }


def compare_group_maps(
    pred: dict[str, dict[str, Any]],
    truth: dict[str, dict[str, Any]],
    tolerance: float,
    *,
    label: str = "groups",
) -> dict[str, Any]:
    pred_keys = set(pred)
    truth_keys = set(truth)
    mismatches = []
    for gid in sorted(pred_keys & truth_keys):
        pred_payload = pred[gid]
        truth_payload = truth[gid]
        pred_weight = pred_payload.get("weight")
        truth_weight = truth_payload.get("weight")
        weights_match = (
            pred_weight == truth_weight
            if pred_weight is None or truth_weight is None
            else abs(pred_weight - truth_weight) <= tolerance
        )
        if pred_payload.get("elements") != truth_payload.get("elements") or not weights_match:
            mismatches.append(
                {
                    "group": gid,
                    "predicted": pred_payload,
                    "ground_truth": truth_payload,
                }
            )
    return {
        "label": label,
        "predicted_count": len(pred_keys),
        "ground_truth_count": len(truth_keys),
        "missing_sample": sorted(list(truth_keys - pred_keys))[:10],
        "extra_sample": sorted(list(pred_keys - truth_keys))[:10],
        "mismatch_sample": mismatches[:10],
        "exact_match": pred_keys == truth_keys and not mismatches,
    }


def planning_field(instance: dict[str, Any], keys: tuple[str, ...], default: Any = None) -> Any:
    for key in keys:
        if key in instance:
            return instance[key]
    for key in keys:
        matches = [value for name, value in instance.items() if str(name).casefold() == key.casefold()]
        if len(matches) == 1:
            return matches[0]
    return default


def planning_named_records(raw: Any) -> dict[str, dict[str, Any]]:
    if isinstance(raw, dict) and raw and all(isinstance(record, dict) for record in raw.values()):
        return {str(key): record for key, record in raw.items()}
    if not isinstance(raw, list) or not raw or not all(isinstance(record, dict) for record in raw):
        return {}
    result = {}
    for record in raw:
        identifier = planning_field(record, ("id", "generator_id", "worker_id", "product_id", "period_id", "shift_id", "period", "day", "name"))
        if identifier is None or str(identifier) in result:
            return {}
        result[str(identifier)] = record
    return result


def extract_planning_numeric_field(
    instance: dict[str, Any],
    keys: tuple[str, ...],
    rows: list[str],
    columns: list[str] | None = None,
) -> dict[str, float | None]:
    raw = planning_field(instance, keys)
    if raw is None and isinstance(instance.get("parameters"), dict):
        return extract_planning_numeric_field(instance["parameters"], keys, rows, columns)
    if keys[0] == "initial_status":
        def status_number(value: Any) -> Any:
            if isinstance(value, str) and value.lower().strip() in {"on", "off"}:
                return int(value.lower().strip() == "on")
            return value
        raw = {key: status_number(value) for key, value in raw.items()} if isinstance(raw, dict) else status_number(raw)
    if columns is None:
        if isinstance(raw, list) and (records := planning_named_records(raw)):
            raw = {name: planning_field(record, keys + ("value",)) for name, record in records.items()}
        if isinstance(raw, dict):
            return {str(key): to_number(value) for key, value in raw.items()}
        if isinstance(raw, list) and len(raw) == len(rows):
            return {row: to_number(value) for row, value in zip(rows, raw)}
        number = to_number(raw)
        return {row: number for row in rows} if number is not None else {}
    # Reuse the solution parser's support for transposed and flattened matrices.
    if isinstance(raw, dict):
        nested = planning_field(raw, keys)
        if isinstance(nested, (dict, list)):
            raw = nested
    matrix = extract_named_period_matrix({"value": raw}, keys=("value",), entity_names=rows, periods=columns)
    if isinstance(raw, list) and len(raw) == len(rows):
        raw = dict(zip(rows, raw))
    if isinstance(raw, dict):
        for row in rows:
            value = raw.get(row)
            if isinstance(value, list) and len(value) == len(columns):
                matrix[row] = dict(zip(columns, value))
            elif to_number(value) is not None:
                matrix[row] = {column: value for column in columns}
    elif to_number(raw) is not None:
        matrix = {row: {column: raw for column in columns} for row in rows}
    return {f"{row}/{column}": to_number(value) for row, values in matrix.items() for column, value in values.items()}


def compare_multi_period_extraction(
    predicted: dict[str, Any], truth: dict[str, Any], tolerance: float
) -> list[dict[str, Any]]:
    variant = str(truth.get("variant") or truth.get("problem_type") or truth.get("scenario") or "")
    sets = truth.get("sets") if isinstance(truth.get("sets"), dict) else {}
    fields: list[tuple[tuple[str, ...], list[str], list[str] | None]] = []
    dimensions: dict[str, tuple[str, ...]] = {}
    if "energy_dispatch_unit_commitment" in variant or ("pmin" in truth and "startup_cost" in truth):
        dimensions = {"generators": ("generators", "units"), "periods": ("periods", "time_periods")}
        generators = [str(value) for value in sets.get("generators", [])]
        periods = [str(value) for value in sets.get("periods", [])]
        fields.append((("demand", "demands", "load", "demand_mw"), periods, None))
        for keys in (
            ("cost", "generation_cost", "variable_cost", "marginal_cost_per_mwh", "marginal_cost", "cost_per_mwh"), ("startup_cost", "startup_costs"),
            ("shutdown_cost", "shutdown_costs"), ("pmin", "p_min", "min_output", "min_output_mw", "min_capacity"),
            ("pmax", "p_max", "max_output", "max_output_mw", "max_capacity"), ("ramp_up", "ramp_up_limit", "ramp_up_mw_per_period"),
            ("ramp_down", "ramp_down_limit", "ramp_down_mw_per_period"), ("min_up", "min_up_time", "min_up_time_periods"),
            ("min_down", "min_down_time", "min_down_time_periods"), ("initial_status", "initial_commitment"),
            ("initial_output", "initial_generation", "initial_output_mw"),
        ):
            if keys[0] in truth:
                fields.append((keys, generators, None))
    elif "lot_sizing_production_planning" in variant or ("production_cost" in truth and "setup_cost" in truth):
        dimensions = {"products": ("products",), "periods": ("periods", "time_periods")}
        products = [str(value) for value in sets.get("products", [])]
        periods = [str(value) for value in sets.get("periods", [])]
        for keys in (("demand", "demands"), ("production_cost", "production_costs", "unit_production_cost", "prod_cost"),
                     ("holding_cost", "holding_costs", "hold_cost"), ("setup_cost", "setup_costs")):
            fields.append((keys, products, periods))
        fields.extend([(("initial_inventory", "initial_stock"), products, None),
                       (("capacity", "capacities", "production_capacity", "capacity_by_period"), periods, None)])
    elif "workforce_planning_shift_scheduling" in variant or ("shift_cost" in truth and "availability_code" in truth):
        dimensions = {"workers": ("workers", "employees"), "days": ("days", "periods", "planning_days", "planning_horizon_days"), "shifts": ("shifts", "shift_types")}
        workers = [str(value) for value in sets.get("workers", [])]
        days = [str(value) for value in sets.get("days", [])]
        shifts = [str(value) for value in sets.get("shifts", [])]
        fields.extend([(("demand", "demands", "staffing_requirements", "shift_staffing_requirements", "shift_requirements", "shift_demand", "required_staff_by_day_shift"), days, shifts),
                       (("shift_cost", "shift_costs", "assignment_cost", "cost_per_shift", "worker_costs", "worker_shift_costs", "cost", "costs"), workers, shifts)])
        for keys in (("regular_shift_limit", "regular_shift_cap"), ("overtime_cost", "overtime_cost_per_extra_shift"),
                     ("max_night_shifts",), ("max_consecutive_days", "max_consecutive_working_days")):
            if keys[0] in truth:
                fields.append((keys, workers, None))
    if not fields:
        return []
    predicted = dict(predicted)
    missing = object()
    availability_keys = ("availability_code", "availability_by_day", "availability", "worker_availability", "worker_daily_availability")
    record_fields = [keys for keys, _, _ in fields] + [availability_keys]
    if isinstance(predicted.get("planning_horizon"), dict):
        for name, value in predicted["planning_horizon"].items():
            predicted.setdefault(name, value)
    for name, aliases in dimensions.items():
        raw = planning_field(predicted, aliases)
        records = planning_named_records(raw)
        if not records and name == "generators":
            records = planning_named_records(planning_field(predicted, ("generator_data",)))
        if not records:
            continue
        if not isinstance(raw, list) or any(isinstance(value, dict) for value in raw):
            predicted[name] = list(records)
        if name == "workers":
            records = {identifier: dict(record) for identifier, record in records.items()}
            for record in records.values():
                if planning_field(record, fields[1][0], missing) is missing:
                    costs = {shift: planning_field(record, (f"cost_{shift}",), missing) for shift in shifts}
                    costs = {shift: value for shift, value in costs.items() if value is not missing}
                    if costs:
                        record["shift_cost"] = costs
        for keys in record_fields:
            if planning_field(predicted, keys, missing) is not missing:
                continue
            values = {str(identifier): value for identifier, record in records.items()
                      for value in [planning_field(record, keys, missing)] if value is not missing}
            if values:
                predicted[keys[0]] = values
    if "generators" in dimensions:
        capacity = predicted.get("capacity", {})
        if isinstance(capacity, dict):
            for name, keys in (("pmin", ("min", "minimum")), ("pmax", ("max", "maximum"))):
                values = {str(g): planning_field(value, keys) for g, value in capacity.items() if isinstance(value, dict)}
                aliases = next(field_keys for field_keys, _, _ in fields if field_keys[0] == name)
                if values and planning_field(predicted, aliases, missing) is missing:
                    predicted[name] = values
        if planning_field(predicted, ("initial_output", "initial_generation", "initial_output_mw"), missing) is missing:
            status = extract_planning_numeric_field(predicted, ("initial_status", "initial_commitment"), generators)
            # An explicitly off generator has zero initial output; do not infer on-unit output.
            predicted["initial_output"] = {g: 0.0 for g, value in status.items() if value == 0}
    if "products" in dimensions and planning_field(predicted, ("initial_inventory", "initial_stock"), missing) is missing:
        # Released lot-sizing task wording defines zero initial inventory, independent of visual data.
        predicted["initial_inventory"] = {product: 0.0 for product in products}
    if "availability_legend" not in predicted:
        legend = planning_field(predicted, ("availability_code_allowed_shifts", "availability_code_to_allowed_shifts", "availability_codes"))
        if isinstance(legend, dict):
            predicted["availability_legend"] = legend
    if "availability_code" not in predicted:
        predicted["availability_code"] = planning_field(predicted, availability_keys)
    reports = []
    pred_sets = predicted.get("sets") if isinstance(predicted.get("sets"), dict) else predicted
    for name, aliases in dimensions.items():
        values = next((pred_sets[key] for key in aliases if key in pred_sets), None)
        if isinstance(values, dict):
            values = list(values)
        if isinstance(values, list):
            reports.append(compare_entity_sets(set(map(str, values)), set(map(str, sets.get(name, []))), f"planning_{name}"))
    for keys, rows, columns in fields:
        def axis_order(names: list[str]) -> list[str]:
            for name, aliases in dimensions.items():
                if list(map(str, sets.get(name, []))) == names:
                    values = next((pred_sets[key] for key in aliases if key in pred_sets), None)
                    if isinstance(values, list):
                        return list(map(str, values))
            return names
        reports.append(compare_number_maps(
            extract_planning_numeric_field(predicted, keys, axis_order(rows), axis_order(columns) if columns is not None else None),
            extract_planning_numeric_field(truth, keys, rows, columns), tolerance, label=f"planning_{keys[0]}",
        ))
    if "workers" in dimensions:
        def binary_flag(value: Any) -> int | None:
            return None if has_nonfinite_number(value) else to_binary(value)

        def availability(instance: dict[str, Any]) -> dict[str, float | None]:
            raw = instance.get("availability_code", instance.get("availability", {}))
            legend = instance.get("availability_legend", {})
            result = {}
            for worker in workers:
                for day in days:
                    value = (raw.get(worker) or {}).get(day) if isinstance(raw, dict) and isinstance(raw.get(worker), dict) else None
                    if isinstance(value, str):
                        code = value.upper().strip()
                        allowed = legend.get(value) if isinstance(legend, dict) else None
                        if not isinstance(allowed, list):
                            allowed = [] if code == "OFF" else list(code) if code in {"D", "E", "N", "DE", "DN", "EN", "DEN"} else None
                    else:
                        allowed = value
                    for shift in shifts:
                        if isinstance(allowed, list):
                            numeric = float(shift in allowed)
                        elif isinstance(allowed, dict):
                            numeric = binary_flag(allowed.get(shift))
                        else:
                            numeric = None
                        result[f"{worker}/{day}/{shift}"] = numeric
            return result
        reports.append(compare_number_maps(availability(predicted), availability(truth), tolerance, label="planning_availability"))
        # Flags are textual rules, not a requirement to copy presentation metadata.
        if "constraint_flags" in predicted:
            flags = predicted.get("constraint_flags")
            truth_flags = truth.get("constraint_flags", {})
            pred_flags = {str(key): binary_flag(value) for key, value in flags.items()} if isinstance(flags, dict) else {}
            reports.append(compare_number_maps(pred_flags, {key: binary_flag(value) for key, value in truth_flags.items()}, tolerance, label="planning_constraint_flags"))
    return reports


def compare_extracted_instance(pred_instance: dict[str, Any], truth_instance: dict[str, Any], tolerance: float) -> dict[str, Any]:
    counts_pred = summarize_instance_counts(pred_instance)
    counts_truth = summarize_instance_counts(truth_instance)
    logical_constraint_like = any(
        isinstance(instance.get(key), list) and instance.get(key)
        for instance in (pred_instance, truth_instance)
        for key in ("clauses", "implications", "at_most_one_groups", "cardinality_constraints")
    )
    count_mismatches = []
    for key in sorted(set(counts_pred) | set(counts_truth)):
        if logical_constraint_like and key in {"clauses", "implications", "at_most_one_groups"}:
            continue
        if counts_pred.get(key) != counts_truth.get(key):
            count_mismatches.append(
                {
                    "field": key,
                    "predicted": counts_pred.get(key),
                    "ground_truth": counts_truth.get(key),
                }
            )

    entity_reports = compare_multi_period_extraction(pred_instance, truth_instance, tolerance)
    pred_edges = extract_edge_set(pred_instance)
    truth_edges = extract_edge_set(truth_instance)
    if pred_edges or truth_edges:
        entity_reports.append(compare_entity_sets(pred_edges, truth_edges, "edges"))

    pred_arcs = extract_arc_map(pred_instance)
    truth_arcs = extract_arc_map(truth_instance)
    if pred_arcs or truth_arcs:
        entity_reports.append(compare_arc_maps(pred_arcs, truth_arcs, tolerance))

    pred_temporal_network_nodes = extract_temporal_network_node_profiles(pred_instance)
    truth_temporal_network_nodes = extract_temporal_network_node_profiles(truth_instance)
    if pred_temporal_network_nodes or truth_temporal_network_nodes:
        entity_reports.append(
            compare_record_maps(
                pred_temporal_network_nodes,
                truth_temporal_network_nodes,
                label="temporal_network_nodes",
            )
        )

    pred_groups = extract_group_map(pred_instance)
    truth_groups = extract_group_map(truth_instance)
    if pred_groups or truth_groups:
        entity_reports.append(compare_group_maps(pred_groups, truth_groups, tolerance))

    if logical_constraint_like:
        pred_logical_clauses = extract_logical_constraint_clause_set(pred_instance)
        truth_logical_clauses = extract_logical_constraint_clause_set(truth_instance)
        if pred_logical_clauses or truth_logical_clauses:
            entity_reports.append(
                compare_entity_sets(pred_logical_clauses, truth_logical_clauses, "logical_constraint_clauses")
            )
    else:
        pred_clauses = extract_clause_set(pred_instance)
        truth_clauses = extract_clause_set(truth_instance)
        if pred_clauses or truth_clauses:
            entity_reports.append(compare_entity_sets(pred_clauses, truth_clauses, "clauses"))

        pred_implications = extract_implication_set(pred_instance)
        truth_implications = extract_implication_set(truth_instance)
        if pred_implications or truth_implications:
            entity_reports.append(compare_entity_sets(pred_implications, truth_implications, "implications"))

        pred_amo = extract_at_most_one_groups(pred_instance)
        truth_amo = extract_at_most_one_groups(truth_instance)
        if pred_amo or truth_amo:
            entity_reports.append(compare_entity_sets(pred_amo, truth_amo, "at_most_one_groups"))

    pred_cardinality = extract_cardinality_constraints(pred_instance)
    truth_cardinality = extract_cardinality_constraints(truth_instance)
    if pred_cardinality or truth_cardinality:
        entity_reports.append(compare_entity_sets(pred_cardinality, truth_cardinality, "cardinality_constraints"))

    pred_item_profiles = extract_mdkp_item_profiles(pred_instance)
    truth_item_profiles = extract_mdkp_item_profiles(truth_instance)
    if pred_item_profiles or truth_item_profiles:
        entity_reports.append(
            compare_profile_maps(pred_item_profiles, truth_item_profiles, tolerance, label="mdkp_item_profiles")
        )

    pred_capacities = extract_capacity_map(pred_instance)
    truth_capacities = extract_capacity_map(truth_instance)
    if pred_capacities or truth_capacities:
        entity_reports.append(compare_number_maps(pred_capacities, truth_capacities, tolerance, label="capacities"))

    pred_location_facilities = extract_location_facility_profiles(pred_instance)
    truth_location_facilities = extract_location_facility_profiles(truth_instance)
    if pred_location_facilities or truth_location_facilities:
        entity_reports.append(
            compare_record_maps(pred_location_facilities, truth_location_facilities, label="location_facilities")
        )

    pred_location_customers = extract_location_customer_profiles(pred_instance)
    truth_location_customers = extract_location_customer_profiles(truth_instance)
    if pred_location_customers or truth_location_customers:
        entity_reports.append(
            compare_record_maps(pred_location_customers, truth_location_customers, label="location_customers")
        )

    pred_location_agents = extract_location_agent_profiles(pred_instance)
    truth_location_agents = extract_location_agent_profiles(truth_instance)
    if pred_location_agents or truth_location_agents:
        entity_reports.append(compare_record_maps(pred_location_agents, truth_location_agents, label="location_agents"))

    pred_location_subsets = extract_location_subset_profiles(pred_instance)
    truth_location_subsets = extract_location_subset_profiles(truth_instance)
    if pred_location_subsets or truth_location_subsets:
        entity_reports.append(
            compare_record_maps(pred_location_subsets, truth_location_subsets, label="location_candidate_subsets")
        )

    for key, label in (
        ("feasible_assignments", "feasible_assignments"),
        ("task_feasible_agents", "task_feasible_agents"),
        ("element_to_subsets", "element_to_subsets"),
    ):
        pred_groups = extract_location_group_profiles(pred_instance, key)
        truth_groups = extract_location_group_profiles(truth_instance, key)
        if pred_groups or truth_groups:
            entity_reports.append(compare_group_maps(pred_groups, truth_groups, tolerance, label=label))

    for key, label in (
        ("cost_matrix", "cost_matrix"),
        ("resource_matrix", "resource_matrix"),
        ("assignment_cost_per_unit_demand", "assignment_cost_per_unit_demand"),
        ("distance_matrix", "distance_matrix"),
        ("incidence_matrix", "incidence_matrix"),
    ):
        pred_matrix = extract_flat_numeric_matrix(pred_instance, key)
        truth_matrix = extract_flat_numeric_matrix(truth_instance, key)
        if pred_matrix or truth_matrix:
            entity_reports.append(compare_number_maps(pred_matrix, truth_matrix, tolerance, label=label))

    for key, label in (
        ("subset_costs", "subset_costs"),
        ("agent_capacities", "agent_capacities"),
        ("demand_weights", "demand_weights"),
    ):
        pred_map = extract_flat_scalar_map(pred_instance, key)
        truth_map = extract_flat_scalar_map(truth_instance, key)
        if pred_map or truth_map:
            entity_reports.append(compare_number_maps(pred_map, truth_map, tolerance, label=label))

    pred_routing_nodes = extract_routing_node_profiles(pred_instance)
    truth_routing_nodes = extract_routing_node_profiles(truth_instance)
    if pred_routing_nodes or truth_routing_nodes:
        entity_reports.append(compare_record_maps(pred_routing_nodes, truth_routing_nodes, label="routing_nodes"))

    pred_routing_vehicle_types = extract_routing_vehicle_type_profiles(pred_instance)
    truth_routing_vehicle_types = extract_routing_vehicle_type_profiles(truth_instance)
    if pred_routing_vehicle_types or truth_routing_vehicle_types:
        entity_reports.append(
            compare_record_maps(
                pred_routing_vehicle_types,
                truth_routing_vehicle_types,
                label="routing_vehicle_types",
            )
        )

    pred_routing_fleet = extract_routing_fleet_scalars(pred_instance)
    truth_routing_fleet = extract_routing_fleet_scalars(truth_instance)
    if pred_routing_fleet or truth_routing_fleet:
        entity_reports.append(compare_number_maps(pred_routing_fleet, truth_routing_fleet, tolerance, label="routing_fleet"))

    pred_precedence_arcs = extract_scheduling_precedence_arc_set(pred_instance)
    truth_precedence_arcs = extract_scheduling_precedence_arc_set(truth_instance)
    if pred_precedence_arcs or truth_precedence_arcs:
        entity_reports.append(compare_entity_sets(pred_precedence_arcs, truth_precedence_arcs, "precedence_arcs"))

    pred_job_shop_profiles = extract_job_shop_operation_profiles(pred_instance)
    truth_job_shop_profiles = extract_job_shop_operation_profiles(truth_instance)
    if pred_job_shop_profiles or truth_job_shop_profiles:
        entity_reports.append(compare_record_maps(pred_job_shop_profiles, truth_job_shop_profiles, label="job_shop_operations"))

    pred_parallel_machine_profiles = extract_parallel_machine_job_profiles(pred_instance)
    truth_parallel_machine_profiles = extract_parallel_machine_job_profiles(truth_instance)
    if pred_parallel_machine_profiles or truth_parallel_machine_profiles:
        entity_reports.append(
            compare_record_maps(
                pred_parallel_machine_profiles,
                truth_parallel_machine_profiles,
                label="parallel_machine_jobs",
            )
        )

    pred_rcpsp_profiles = extract_rcpsp_activity_profiles(pred_instance)
    truth_rcpsp_profiles = extract_rcpsp_activity_profiles(truth_instance)
    if pred_rcpsp_profiles or truth_rcpsp_profiles:
        entity_reports.append(compare_record_maps(pred_rcpsp_profiles, truth_rcpsp_profiles, label="rcpsp_activities"))

    pred_flow_stage_profiles = extract_flow_shop_stage_machine_profiles(pred_instance)
    truth_flow_stage_profiles = extract_flow_shop_stage_machine_profiles(truth_instance)
    if pred_flow_stage_profiles or truth_flow_stage_profiles:
        entity_reports.append(
            compare_record_maps(
                pred_flow_stage_profiles,
                truth_flow_stage_profiles,
                label="flow_shop_stage_machines",
            )
        )

    pred_flow_job_stage_profiles = extract_flow_shop_job_stage_profiles(pred_instance)
    truth_flow_job_stage_profiles = extract_flow_shop_job_stage_profiles(truth_instance)
    if pred_flow_job_stage_profiles or truth_flow_job_stage_profiles:
        entity_reports.append(
            compare_record_maps(
                pred_flow_job_stage_profiles,
                truth_flow_job_stage_profiles,
                label="flow_shop_job_stage_durations",
            )
        )

    major_mismatch = bool(count_mismatches)
    if not major_mismatch:
        for report in entity_reports:
            if not report.get("exact_match", False):
                major_mismatch = True
                break

    return {
        "predicted_summary": counts_pred,
        "ground_truth_summary": counts_truth,
        "count_mismatches": count_mismatches,
        "entity_reports": entity_reports,
        "major_mismatch": major_mismatch,
    }


def extract_structured_instance(assistant_json: dict[str, Any]) -> dict[str, Any]:
    extracted_data = assistant_json.get("extracted_data")
    if not isinstance(extracted_data, dict):
        return {}
    structured_instance = extracted_data.get("structured_instance")
    if isinstance(structured_instance, dict):
        return structured_instance
    return {}

def parse_stdout_object(text: str) -> Any:
    stripped = text.strip()
    if not stripped:
        return None

    candidates = [stripped]
    lines = [line.strip() for line in stripped.splitlines() if line.strip()]
    if lines:
        candidates.append(lines[-1])
        candidates.extend(reversed(lines[:-1]))

    seen: set[str] = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            try:
                return ast.literal_eval(candidate)
            except Exception:
                continue
    return None


def normalize_solver_code(code: str) -> str:
    stripped = strip_response_wrappers(code).strip()
    fenced_match = re.fullmatch(r"```(?:python)?\s*(?P<code>.*?)\s*```", stripped, flags=re.DOTALL | re.IGNORECASE)
    if fenced_match:
        return fenced_match.group("code").strip()
    cleaned_lines = []
    for line in stripped.splitlines():
        marker = line.strip().lower()
        if marker in {"```", "```python"}:
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip()


def has_top_level_solve_function(code: str) -> bool:
    return re.search(r"(?m)^\s*def\s+solve\s*\(", code) is not None


def make_json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        converted: dict[Any, Any] = {}
        for key, item in value.items():
            if isinstance(key, (str, int, float, bool)) or key is None:
                safe_key: Any = key
            elif isinstance(key, (tuple, list)):
                safe_key = "_".join(str(part) for part in key)
            else:
                safe_key = str(key)
            converted[safe_key] = make_json_safe(item)
        return converted
    if isinstance(value, (list, tuple)):
        return [make_json_safe(item) for item in value]
    if isinstance(value, set):
        return [make_json_safe(item) for item in sorted(value, key=lambda item: str(item))]
    if hasattr(value, "item") and not isinstance(value, (str, bytes, bytearray)):
        try:
            return make_json_safe(value.item())
        except Exception:
            pass
    return value

def normalize_status(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"optimal", "success", "feasible"}:
        return text
    if "infeasible" in text:
        return "infeasible"
    return text


def to_binary(value: Any) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        rounded = int(round(float(value)))
        if abs(float(value) - rounded) <= 1e-9 and rounded in {0, 1}:
            return rounded
        return None
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "t", "yes"}:
            return 1
        if lowered in {"0", "false", "f", "no"}:
            return 0
    return None


def extract_boolean_assignment(output: Any, instance: dict[str, Any]) -> dict[str, int]:
    if not isinstance(output, dict):
        return {}
    solution = output.get("solution") if isinstance(output.get("solution"), dict) else None
    candidates = []
    for container in (output, solution or {}):
        if isinstance(container.get("assignment"), dict):
            candidates.append(container.get("assignment"))
        if isinstance(container.get("decision_variables"), dict):
            candidates.append(container.get("decision_variables"))
    for candidate in candidates:
        assignment = {}
        for key, value in candidate.items():
            binary = to_binary(value)
            if binary is None:
                continue
            assignment[str(key)] = binary
        if assignment:
            return assignment

    variables = [str(x) for x in extract_named_list(instance, "variables")]
    assignment: dict[str, int] = {}
    true_like = None
    false_like = None
    if isinstance(output.get("true_variables"), list):
        true_like = [str(x) for x in output["true_variables"]]
    elif solution and isinstance(solution.get("true_variables"), list):
        true_like = [str(x) for x in solution["true_variables"]]
    if isinstance(output.get("false_variables"), list):
        false_like = [str(x) for x in output["false_variables"]]
    elif solution and isinstance(solution.get("false_variables"), list):
        false_like = [str(x) for x in solution["false_variables"]]

    if true_like is not None or false_like is not None:
        true_set = set(true_like or [])
        false_set = set(false_like or [])
        for variable in variables:
            if variable in true_set:
                assignment[variable] = 1
            elif variable in false_set:
                assignment[variable] = 0
        if assignment:
            return assignment
    for container in (output, solution or {}):
        flat_assignment: dict[str, int] = {}
        for variable in variables:
            if variable not in container:
                continue
            binary = to_binary(container.get(variable))
            if binary is None:
                continue
            flat_assignment[variable] = binary
        if flat_assignment:
            return flat_assignment
    return {}


def extract_selected_items_from_output(output: Any) -> list[int]:
    if not isinstance(output, dict):
        return []
    solution = output.get("solution") if isinstance(output.get("solution"), dict) else None
    for container in (output, solution or {}):
        selected_items = container.get("selected_items")
        if isinstance(selected_items, list):
            result = []
            for item in selected_items:
                try:
                    result.append(int(item))
                except (TypeError, ValueError):
                    continue
            if result:
                return sorted(result)
    for container in (output, solution or {}):
        decision_variables = container.get("decision_variables")
        if not isinstance(decision_variables, dict):
            continue
        result = []
        for key, value in decision_variables.items():
            binary = to_binary(value)
            if binary != 1:
                continue
            match = re.search(r"(\d+)$", str(key))
            if match:
                result.append(int(match.group(1)))
        if result:
            return sorted(result)
    return []


def validate_graph_coloring_output(output: Any, instance: dict[str, Any], tolerance: float = 1e-6) -> dict[str, Any]:
    if not isinstance(output, dict):
        return {"parse_ok": False, "feasible_under_instance": False, "details": "stdout is not a dict"}
    if has_nonfinite_number(output):
        return {"parse_ok": False, "feasible_under_instance": False, "details": "Non-finite numeric output"}
    payload = unwrap_solution_dict(output) or output
    status = normalize_status(payload.get("status", output.get("status")))
    coloring = payload.get("coloring") or payload.get("color_assignment")
    if coloring is None:
        coloring = output.get("coloring") or output.get("color_assignment") or output.get("solution") or {}
    vertices = extract_named_list(instance, "vertices") or instance.get("vertex_ids") or []
    if not vertices:
        count = instance.get("num_vertices", instance.get("n_vertices"))
        if isinstance(count, int) and count >= 0:
            vertices = list(range(1, count + 1))
        elif isinstance(instance.get("adjacency_matrix"), list):
            vertices = list(range(1, len(instance["adjacency_matrix"]) + 1))
    if isinstance(coloring, list):
        coloring = {str(vertices[i]) if i < len(vertices) else f"extra_{i}": value for i, value in enumerate(coloring)}
    elif not isinstance(coloring, dict):
        coloring = {}
    edges = extract_edge_set(instance)
    if not vertices:
        vertices = sorted({vertex for edge in edges for vertex in edge})
    expected = {int(vertex) for vertex in vertices}
    colors_available = extract_named_list(instance, "colors")
    allowed = set(int(x) for x in colors_available) if colors_available else None
    valid = True
    messages: list[str] = []
    assignment: dict[int, int] = {}
    for key, value in coloring.items():
        vertex_number, color_number = to_number(key), to_number(value)
        if (isinstance(key, bool) or isinstance(value, bool) or vertex_number is None or color_number is None
                or not vertex_number.is_integer() or not color_number.is_integer()):
            valid = False
            messages.append(f"Invalid coloring entry {key}:{value}")
            continue
        vertex, color = int(vertex_number), int(color_number)
        if vertex in assignment:
            valid = False
            messages.append(f"Duplicate vertex {vertex}")
        assignment[vertex] = color
        if allowed is not None and color not in allowed:
            valid = False
            messages.append(f"Color {color} for vertex {vertex} is not allowed")
    if set(assignment) != expected or not expected:
        valid = False
        messages.append(f"Vertex coverage mismatch: missing={sorted(expected - set(assignment))}, extra={sorted(set(assignment) - expected)}")
    for u, v in sorted(edges):
        if u in assignment and v in assignment and assignment[u] == assignment[v]:
            valid = False
            messages.append(f"Adjacent vertices {u} and {v} share the same color")
    for vertex, color in (instance.get("precolored_vertices") or {}).items():
        if assignment.get(int(vertex)) != int(color):
            valid = False
            messages.append(f"Precolored vertex {vertex} must have color {color}")

    used_colors = set(assignment.values())
    objective_value = float(len(used_colors))
    if instance.get("task_variant") == "weighted_min_colors" or instance.get("objective_type") == "weighted_min_colors":
        weights = instance.get("color_weights", [])
        objective_value = 0.0
        for color in used_colors:
            weight = to_number(weights[color - 1]) if isinstance(weights, list) and 1 <= color <= len(weights) else None
            if weight is None:
                valid = False
                messages.append(f"Missing weight for color {color}")
            else:
                objective_value += weight
    if instance.get("task_variant") in {"min_colors", "weighted_min_colors"} or instance.get("objective_type") in {"min_colors", "weighted_min_colors"}:
        for key in ("objective_exact", "objective_value", "objective", "total_cost"):
            if payload.get(key) is not None and (to_number(payload[key]) is None or abs(float(payload[key]) - objective_value) > tolerance):
                valid = False
                messages.append(f"Reported {key} does not match computed objective {objective_value}")
    return {
        "parse_ok": True,
        "status": status,
        "feasible_under_instance": valid and status != "infeasible",
        "used_colors_count": len(used_colors),
        "objective_value": objective_value,
        "details": messages[:10],
    }


def validate_max_flow_output(output: Any, instance: dict[str, Any], tolerance: float) -> dict[str, Any]:
    payload = unwrap_solution_dict(output)
    if payload is None:
        return {"parse_ok": False, "feasible_under_instance": False, "details": "stdout is not a dict"}
    if has_nonfinite_number(output):
        return {"parse_ok": False, "feasible_under_instance": False, "details": "Non-finite numeric output"}
    arc_map = extract_arc_map(instance)
    source_number = to_number(instance.get("source"))
    sink_number = to_number(instance.get("sink"))
    if source_number is None or sink_number is None or not source_number.is_integer() or not sink_number.is_integer():
        return {"parse_ok": True, "feasible_under_instance": False, "details": "Instance is missing source or sink"}
    source, sink = int(source_number), int(sink_number)
    max_flow = extract_max_flow_value(payload)
    messages: list[str] = []
    arc_flows = extract_max_flow_arc_mapping(payload, messages)
    cut = extract_max_flow_cut_partition(payload)
    node_ids = {int(node.get("id") if isinstance(node, dict) else node) for node in instance.get("nodes", [])}
    node_ids |= {u for u, _ in arc_map} | {v for _, v in arc_map} | {source, sink}
    if max_flow is None or max_flow < -tolerance:
        messages.append("Missing or invalid maximum-flow value")
    if not arc_flows:
        messages.append("Arc flow map is required")
    # Dense flow matrices may explicitly give zero on non-edges of this graph.
    unknown_arcs = {arc for arc, value in arc_flows.items() if arc not in arc_map
                    and (abs(value) > tolerance or not set(arc) <= node_ids)}
    if unknown_arcs:
        messages.append(f"Unknown arcs in flow map: {sorted(unknown_arcs)}")
    for key, capacity in arc_map.items():
        flow_value = arc_flows.get(key, 0.0)
        if capacity is None or flow_value - capacity > tolerance:
            messages.append(f"Arc {key} exceeds or lacks capacity: flow={flow_value}, cap={capacity}")
        if flow_value < -tolerance:
            messages.append(f"Arc {key} has negative flow {flow_value}")
    for node in sorted(node_ids):
        inflow = sum(arc_flows.get((u, v), 0.0) for (u, v) in arc_map if v == node)
        outflow = sum(arc_flows.get((u, v), 0.0) for (u, v) in arc_map if u == node)
        target = max_flow if node == source else -max_flow if node == sink and max_flow is not None else 0.0
        if target is not None and abs(outflow - inflow - target) > tolerance:
            messages.append(f"Flow balance violated at node {node}: out-in={outflow - inflow}, target={target}")

    # A certificate is mathematical, not tied to the reference solver's chosen cut.
    source_side, sink_side = set(cut["S"]), set(cut["T"])
    if (source_side & sink_side or source_side | sink_side != {str(node) for node in node_ids}
            or str(source) not in source_side or str(sink) not in sink_side
            or len(source_side) != len(cut["S"]) or len(sink_side) != len(cut["T"])):
        messages.append("Cut must partition all nodes, with source in S and sink in T")
    cut_capacity = sum(capacity for (u, v), capacity in arc_map.items()
                       if str(u) in source_side and str(v) in sink_side and capacity is not None)
    if max_flow is not None and abs(cut_capacity - max_flow) > tolerance:
        messages.append(f"Cut capacity {cut_capacity} does not match flow value {max_flow}")
    for key in ("min_cut_value", "minimum_cut_value", "cut_value", "objective_exact", "objective_value", "max_flow", "maximum_flow", "maximum_flow_value", "max_flow_value", "flow_value"):
        if payload.get(key) is not None and (to_number(payload[key]) is None or max_flow is None or abs(float(payload[key]) - max_flow) > tolerance):
            messages.append(f"Reported {key} does not match flow value {max_flow}")
    if normalize_status(payload.get("status")) == "infeasible":
        messages.append("Reported infeasible despite a requested flow certificate")
    return {
        "parse_ok": True,
        "feasible_under_instance": not messages,
        "status": normalize_status(payload.get("status")),
        "objective_value": max_flow,
        "cut_capacity": cut_capacity,
        "details": messages[:10],
        "min_cut": cut,
        "arc_flows": arc_flows,
    }


def validate_capacitated_network_design_output(output: Any, instance: dict[str, Any], tolerance: float) -> dict[str, Any]:
    payload = unwrap_solution_dict(output)
    if payload is None:
        return {"parse_ok": False, "feasible_under_instance": False, "details": "stdout is not a dict"}
    arcs = instance.get("arcs")
    if not isinstance(arcs, list):
        return {"parse_ok": True, "feasible_under_instance": False, "details": "instance is missing arcs"}
    arc_ids = {str(arc.get("id")) for arc in arcs if isinstance(arc, dict) and arc.get("id") is not None}
    endpoint_to_arc = {
        (int(arc["from"]), int(arc["to"])): str(arc["id"])
        for arc in arcs
        if isinstance(arc, dict) and arc.get("id") is not None and arc.get("from") is not None and arc.get("to") is not None
    }
    flow_map = extract_arc_value_mapping(
        payload,
        instance_arc_ids=arc_ids,
        endpoint_to_arc_id=endpoint_to_arc,
        keys=("arc_flow_by_id", "arc_flows", "arc_flow", "flow", "flows"),
    )
    install_map = extract_arc_value_mapping(
        payload,
        instance_arc_ids=arc_ids,
        endpoint_to_arc_id=endpoint_to_arc,
        keys=("installation_indicator", "installation", "installed_arcs", "arc_installed"),
    )
    installed_ids = set(extract_named_selection(payload, ("installed_arc_ids", "used_arc_ids", "open_arcs")))
    messages: list[str] = []
    feasible = True
    balances = ((instance.get("demands") or {}).get("node_balance")) or {}
    capacities = instance.get("capacities") or {}
    fixed_costs = instance.get("fixed_costs") or {}
    variable_costs = instance.get("variable_costs") or {}
    node_ids = [int(node) for node in instance.get("nodes", [])]
    if not node_ids:
        node_ids = sorted({int(arc["from"]) for arc in arcs if isinstance(arc, dict)} | {int(arc["to"]) for arc in arcs if isinstance(arc, dict)})
    for arc in arcs:
        if not isinstance(arc, dict):
            continue
        arc_id = str(arc["id"])
        flow = float(flow_map.get(arc_id, 0.0))
        installed = bool(install_map.get(arc_id, 0.0) > 0.5 or arc_id in installed_ids or flow > tolerance)
        capacity = to_number(capacities.get(arc_id) if isinstance(capacities, dict) else arc.get("capacity"))
        if capacity is not None and flow - capacity > tolerance:
            feasible = False
            messages.append(f"Arc {arc_id} exceeds capacity: flow={flow}, cap={capacity}")
        if flow < -tolerance:
            feasible = False
            messages.append(f"Arc {arc_id} has negative flow {flow}")
        if not installed and flow > tolerance:
            feasible = False
            messages.append(f"Arc {arc_id} carries positive flow without being installed")
    for node in node_ids:
        inflow = 0.0
        outflow = 0.0
        for arc in arcs:
            if not isinstance(arc, dict):
                continue
            arc_id = str(arc["id"])
            flow = float(flow_map.get(arc_id, 0.0))
            if int(arc["to"]) == node:
                inflow += flow
            if int(arc["from"]) == node:
                outflow += flow
        target = to_number((balances or {}).get(str(node)))
        if target is None:
            target = to_number((balances or {}).get(node))
        if target is None:
            target = 0.0
        if abs(outflow - inflow - target) > tolerance:
            feasible = False
            messages.append(f"Flow balance violated at node {node}: out-in={outflow - inflow}, target={target}")
    objective_value = 0.0
    for arc in arcs:
        if not isinstance(arc, dict):
            continue
        arc_id = str(arc["id"])
        flow = float(flow_map.get(arc_id, 0.0))
        installed = bool(install_map.get(arc_id, 0.0) > 0.5 or arc_id in installed_ids or flow > tolerance)
        fixed = to_number(fixed_costs.get(arc_id))
        variable = to_number(variable_costs.get(arc_id))
        if fixed is not None and installed:
            objective_value += fixed
        if variable is not None:
            objective_value += variable * flow
    reported_objective = extract_reported_objective(payload, ("objective_exact", "objective", "objective_value", "total_cost"))
    if reported_objective is not None and abs(reported_objective - objective_value) > tolerance:
        feasible = False
        messages.append(f"Reported objective {reported_objective} does not match computed objective {objective_value}")
    return {
        "parse_ok": True,
        "feasible_under_instance": feasible,
        "status": normalize_status(payload.get("status")),
        "objective_value": reported_objective if reported_objective is not None else objective_value,
        "details": messages[:10],
        "arc_flows": flow_map,
    }


def validate_minimum_cost_flow_output(output: Any, instance: dict[str, Any], tolerance: float) -> dict[str, Any]:
    payload = unwrap_solution_dict(output)
    if payload is None:
        return {"parse_ok": False, "feasible_under_instance": False, "details": "stdout is not a dict"}
    if has_nonfinite_number(output):
        return {"parse_ok": False, "feasible_under_instance": False, "details": "Non-finite numeric output"}
    arcs = instance.get("arcs")
    supply = instance.get("supply")
    if not isinstance(arcs, list) or not isinstance(supply, dict):
        return {"parse_ok": True, "feasible_under_instance": False, "details": "instance is missing arcs or supply"}
    endpoint_to_arc = {
        (int(arc["from"]), int(arc["to"])): f"{int(arc['from'])}_{int(arc['to'])}"
        for arc in arcs
        if isinstance(arc, dict) and arc.get("from") is not None and arc.get("to") is not None
    }
    flow_map = extract_arc_value_mapping(
        payload,
        instance_arc_ids=set(endpoint_to_arc.values()),
        endpoint_to_arc_id=endpoint_to_arc,
        keys=("flows", "arc_flows", "flow"),
    )
    feasible = True
    messages: list[str] = []
    objective_value = 0.0
    node_ids = sorted({int(node) for node in supply.keys()} | {int(arc["from"]) for arc in arcs if isinstance(arc, dict)} | {int(arc["to"]) for arc in arcs if isinstance(arc, dict)})
    for arc in arcs:
        if not isinstance(arc, dict):
            continue
        arc_id = f"{int(arc['from'])}_{int(arc['to'])}"
        flow = float(flow_map.get(arc_id, 0.0))
        capacity = to_number(arc.get("capacity"))
        cost = to_number(arc.get("cost"))
        if capacity is not None and flow - capacity > tolerance:
            feasible = False
            messages.append(f"Arc {arc_id} exceeds capacity: flow={flow}, cap={capacity}")
        if flow < -tolerance:
            feasible = False
            messages.append(f"Arc {arc_id} has negative flow {flow}")
        if cost is not None:
            objective_value += cost * flow
    for node in node_ids:
        inflow = 0.0
        outflow = 0.0
        for arc in arcs:
            if not isinstance(arc, dict):
                continue
            arc_id = f"{int(arc['from'])}_{int(arc['to'])}"
            flow = float(flow_map.get(arc_id, 0.0))
            if int(arc["to"]) == node:
                inflow += flow
            if int(arc["from"]) == node:
                outflow += flow
        target = to_number(supply.get(str(node)))
        if target is None:
            target = to_number(supply.get(node))
        if target is None:
            target = 0.0
        if abs(outflow - inflow - target) > tolerance:
            feasible = False
            messages.append(f"Flow balance violated at node {node}: out-in={outflow - inflow}, target={target}")
    reported_objective = extract_reported_objective(payload, ("objective_exact", "objective", "objective_value", "total_cost"))
    if reported_objective is not None and abs(reported_objective - objective_value) > tolerance:
        feasible = False
        messages.append(f"Reported objective {reported_objective} does not match computed objective {objective_value}")
    return {
        "parse_ok": True,
        "feasible_under_instance": feasible,
        "status": normalize_status(payload.get("status")),
        "objective_value": reported_objective if reported_objective is not None else objective_value,
        "details": messages[:10],
        "arc_flows": flow_map,
    }


def validate_resource_constrained_shortest_path_output(output: Any, instance: dict[str, Any], tolerance: float) -> dict[str, Any]:
    payload = unwrap_solution_dict(output)
    if payload is None:
        return {"parse_ok": False, "feasible_under_instance": False, "details": "stdout is not a dict"}
    arcs = instance.get("arcs")
    if not isinstance(arcs, list):
        return {"parse_ok": True, "feasible_under_instance": False, "details": "instance is missing arcs"}
    source = instance.get("source")
    sink = instance.get("sink")
    resource_bound = to_number(instance.get("resource_bound"))
    path = payload.get("optimal_path") or payload.get("path")
    selected_arcs = extract_selected_arc_set(payload)
    if not selected_arcs and isinstance(path, list) and len(path) >= 2:
        parsed_arc_sequence: list[tuple[int, int]] = []
        for item in path:
            parsed = parse_numeric_mapping_key(item, arity=2)
            if parsed is None:
                parsed_arc_sequence = []
                break
            try:
                parsed_arc_sequence.append((int(parsed[0]), int(parsed[1])))
            except (TypeError, ValueError):
                parsed_arc_sequence = []
                break
        if parsed_arc_sequence:
            selected_arcs = set(parsed_arc_sequence)
    if not selected_arcs and isinstance(path, list) and len(path) >= 2:
        try:
            selected_arcs = {(int(path[i]), int(path[i + 1])) for i in range(len(path) - 1)}
        except (TypeError, ValueError):
            selected_arcs = set()
    feasible = True
    messages: list[str] = []
    objective_value = 0.0
    resource_used = 0.0
    incoming = Counter()
    outgoing = Counter()
    arc_lookup = {(int(arc["from"]), int(arc["to"])): arc for arc in arcs if isinstance(arc, dict)}
    for arc_key in selected_arcs:
        arc = arc_lookup.get(arc_key)
        if arc is None:
            feasible = False
            messages.append(f"Unknown selected arc {arc_key}")
            continue
        outgoing[arc_key[0]] += 1
        incoming[arc_key[1]] += 1
        objective_value += float(to_number(arc.get("cost")) or 0.0)
        resource_used += float(to_number(arc.get("resource")) or 0.0)
    node_ids = sorted({int(arc["from"]) for arc in arcs if isinstance(arc, dict)} | {int(arc["to"]) for arc in arcs if isinstance(arc, dict)})
    if source is not None and outgoing[int(source)] != 1:
        feasible = False
        messages.append(f"Source {source} must have exactly one outgoing selected arc")
    if sink is not None and incoming[int(sink)] != 1:
        feasible = False
        messages.append(f"Sink {sink} must have exactly one incoming selected arc")
    for node in node_ids:
        if node in {source, sink}:
            continue
        if incoming[node] != outgoing[node]:
            feasible = False
            messages.append(f"Path continuity violated at node {node}: in={incoming[node]} out={outgoing[node]}")
        if incoming[node] > 1 or outgoing[node] > 1:
            feasible = False
            messages.append(f"Node {node} is used multiple times")
    if resource_bound is not None and resource_used - resource_bound > tolerance:
        feasible = False
        messages.append(f"Resource bound exceeded: used={resource_used}, bound={resource_bound}")
    reported_objective = extract_reported_objective(payload, ("objective_exact", "objective", "objective_value", "path_cost"))
    if reported_objective is not None and abs(reported_objective - objective_value) > tolerance:
        feasible = False
        messages.append(f"Reported objective {reported_objective} does not match computed objective {objective_value}")
    return {
        "parse_ok": True,
        "feasible_under_instance": feasible,
        "status": normalize_status(payload.get("status")),
        "objective_value": reported_objective if reported_objective is not None else objective_value,
        "details": messages[:10],
        "selected_arcs": sorted(selected_arcs),
    }


def validate_time_expanded_multi_period_network_flow_output(output: Any, instance: dict[str, Any], tolerance: float) -> dict[str, Any]:
    payload = unwrap_solution_dict(output)
    if payload is None:
        return {"parse_ok": False, "feasible_under_instance": False, "details": "stdout is not a dict"}
    periods = [str(p) for p in extract_named_list(instance, "periods")] or [str(p) for p in instance.get("periods", [])]
    arc_endpoints = ((instance.get("indices") or {}).get("arc_to_endpoints")) or {}
    instance_arc_ids = {str(x) for x in instance.get("arc_ids", [])}
    endpoint_to_arc_id: dict[tuple[int, int], str] = {}
    for arc_id, endpoints in arc_endpoints.items():
        if isinstance(endpoints, list) and len(endpoints) == 2:
            try:
                endpoint_to_arc_id[(int(endpoints[0]), int(endpoints[1]))] = str(arc_id)
            except (TypeError, ValueError):
                continue
    capacities = instance.get("capacities_by_arc_period") or {}
    routing_costs = instance.get("routing_costs_by_arc_period") or {}
    net_supply = instance.get("net_supply_by_node_period") or {}
    storage_nodes = [str(x) for x in instance.get("storage_nodes", [])]
    storage = instance.get("storage") or {}
    flows_by_period = extract_arc_period_flow_mapping(
        payload,
        periods=periods,
        instance_arc_ids=instance_arc_ids,
        endpoint_to_arc_id=endpoint_to_arc_id,
    )
    inventory = extract_inventory_by_node_period(payload, storage_nodes, periods=periods)
    if not periods or not isinstance(arc_endpoints, dict):
        return {"parse_ok": True, "feasible_under_instance": False, "details": "instance is missing periods or arc endpoints"}
    feasible = True
    messages: list[str] = []
    objective_value = 0.0
    node_ids = sorted({int(node) for node in instance.get("nodes", [])})
    for period in periods:
        period_flows = flows_by_period.get(period, {})
        for arc_id, endpoints in arc_endpoints.items():
            if not isinstance(endpoints, list) or len(endpoints) != 2:
                continue
            flow = float(to_number(period_flows.get(str(arc_id))) or 0.0)
            cap = to_number(((capacities.get(str(arc_id)) or {}).get(period)) if isinstance(capacities, dict) else None)
            cost = to_number(((routing_costs.get(str(arc_id)) or {}).get(period)) if isinstance(routing_costs, dict) else None)
            if cap is not None and flow - cap > tolerance:
                feasible = False
                messages.append(f"Arc {arc_id}@{period} exceeds capacity: flow={flow}, cap={cap}")
            if flow < -tolerance:
                feasible = False
                messages.append(f"Arc {arc_id}@{period} has negative flow {flow}")
            if cost is not None:
                objective_value += cost * flow
        for node in node_ids:
            inflow = 0.0
            outflow = 0.0
            for arc_id, endpoints in arc_endpoints.items():
                if not isinstance(endpoints, list) or len(endpoints) != 2:
                    continue
                u, v = int(endpoints[0]), int(endpoints[1])
                flow = float(to_number(period_flows.get(str(arc_id))) or 0.0)
                if v == node:
                    inflow += flow
                if u == node:
                    outflow += flow
            target = to_number(((net_supply.get(str(node)) or {}).get(period)) if isinstance(net_supply, dict) else None)
            if target is None and isinstance(net_supply, dict):
                target = to_number((net_supply.get(node) or {}).get(period))
            if target is None:
                target = 0.0
            if str(node) in storage_nodes:
                store_payload = storage.get(str(node)) if isinstance(storage, dict) else None
                if not isinstance(store_payload, dict):
                    store_payload = storage.get(node) if isinstance(storage, dict) else None
                initial = float(to_number(store_payload.get("initial_inventory")) or 0.0) if isinstance(store_payload, dict) else 0.0
                prev_period = periods[periods.index(period) - 1] if periods.index(period) > 0 else None
                prev_inventory = initial if prev_period is None else float(to_number((inventory.get(str(node)) or {}).get(prev_period)) or 0.0)
                curr_inventory = float(to_number((inventory.get(str(node)) or {}).get(period)) or 0.0)
                if isinstance(store_payload, dict):
                    cap = to_number(store_payload.get("capacity"))
                    if cap is not None and curr_inventory - cap > tolerance:
                        feasible = False
                        messages.append(f"Inventory capacity exceeded at node {node}@{period}: inv={curr_inventory}, cap={cap}")
                    holding = to_number((store_payload.get("holding_cost_by_period") or {}).get(period))
                    if holding is not None:
                        objective_value += holding * curr_inventory
                balance_target = target + prev_inventory - curr_inventory
            else:
                balance_target = target
            if abs(outflow - inflow - balance_target) > tolerance:
                feasible = False
                messages.append(f"Flow balance violated at node {node}@{period}: out-in={outflow - inflow}, target={balance_target}")
    reported_objective = extract_reported_objective(payload, ("objective_exact", "objective", "objective_value", "total_cost"))
    if reported_objective is not None and abs(reported_objective - objective_value) > tolerance:
        feasible = False
        messages.append(f"Reported objective {reported_objective} does not match computed objective {objective_value}")
    return {
        "parse_ok": True,
        "feasible_under_instance": feasible,
        "status": normalize_status(payload.get("status")),
        "objective_value": reported_objective if reported_objective is not None else objective_value,
        "details": messages[:10],
        "flows_by_period": flows_by_period,
    }


def validate_logical_constraint_satisfaction_output(output: Any, instance: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(output, dict):
        return {"parse_ok": False, "feasible_under_instance": False, "details": "stdout is not a dict"}
    status = normalize_status(output.get("status"))
    assignment = extract_boolean_assignment(output, instance)
    variables = [str(x) for x in extract_named_list(instance, "variables")]
    messages = []
    feasible = True
    for variable in variables:
        if variable not in assignment:
            feasible = False
            messages.append(f"Missing assignment for {variable}")
    for clause in instance.get("clauses", []):
        if not isinstance(clause, dict) or not isinstance(clause.get("literals"), list):
            continue
        clause_satisfied = False
        for literal in clause["literals"]:
            normalized = normalize_literal(literal)
            if normalized is None:
                continue
            variable, sign = normalized
            value = assignment.get(variable)
            if value is None:
                continue
            if (sign == "+" and value == 1) or (sign == "-" and value == 0):
                clause_satisfied = True
                break
        if not clause_satisfied:
            feasible = False
            messages.append(f"Clause {clause.get('name', '?')} is not satisfied")
    for implication in instance.get("implications", []):
        if not isinstance(implication, dict):
            continue
        source = str(implication.get("if_variable"))
        target = str(implication.get("then_variable"))
        if assignment.get(source) == 1 and assignment.get(target) != 1:
            feasible = False
            messages.append(f"Implication {implication.get('name', '?')} violated: {source} -> {target}")
    for group in instance.get("at_most_one_groups", []):
        if not isinstance(group, dict) or not isinstance(group.get("variables"), list):
            continue
        total = sum(assignment.get(str(variable), 0) for variable in group["variables"])
        if total > 1:
            feasible = False
            messages.append(f"At-most-one group {group.get('name', '?')} has {total} true variables")
    for constraint in instance.get("cardinality_constraints", []):
        if not isinstance(constraint, dict) or not isinstance(constraint.get("variables"), list):
            continue
        rhs = to_number(constraint.get("rhs"))
        if rhs is None:
            continue
        total = sum(assignment.get(str(variable), 0) for variable in constraint["variables"])
        if total - rhs > 1e-9:
            feasible = False
            messages.append(f"Cardinality row {constraint.get('name', '?')} exceeds rhs {rhs}")
    if status == "infeasible":
        feasible = False
    return {
        "parse_ok": True,
        "feasible_under_instance": feasible and bool(assignment),
        "status": status,
        "details": messages[:10],
        "assigned_variable_count": len(assignment),
    }


def validate_multi_dim_knapsack_output(output: Any, instance: dict[str, Any], tolerance: float) -> dict[str, Any]:
    if not isinstance(output, dict):
        return {"parse_ok": False, "feasible_under_instance": False, "details": "stdout is not a dict"}
    status = normalize_status(output.get("status"))
    selected_items = extract_selected_items_from_output(output)
    items = extract_named_list(instance, "items")
    values = instance.get("values")
    weights = instance.get("weights")
    capacities = instance.get("capacities")
    if not isinstance(items, list) or not isinstance(values, list) or not isinstance(weights, list) or not isinstance(capacities, list):
        return {"parse_ok": True, "feasible_under_instance": False, "details": "instance is missing values, weights, or capacities"}
    index_map = {}
    for i, item in enumerate(items):
        try:
            index_map[int(item)] = i
        except (TypeError, ValueError):
            continue
    usage = [0.0 for _ in capacities]
    total_value = 0.0
    feasible = True
    messages = []
    for item in selected_items:
        if item not in index_map:
            feasible = False
            messages.append(f"Unknown item {item}")
            continue
        idx = index_map[item]
        total_value += float(to_number(values[idx]) or 0.0)
        row = weights[idx]
        if not isinstance(row, list):
            feasible = False
            messages.append(f"Missing weight row for item {item}")
            continue
        for dim, weight in enumerate(row):
            usage[dim] += float(to_number(weight) or 0.0)
    for dim, capacity in enumerate(capacities):
        cap = float(to_number(capacity) or 0.0)
        if usage[dim] - cap > tolerance:
            feasible = False
            messages.append(f"Capacity exceeded on dimension {dim + 1}: usage={usage[dim]}, cap={cap}")
    reported_objective = None
    for key in ("objective_exact", "objective", "objective_value", "total_value"):
        if key in output:
            reported_objective = to_number(output.get(key))
            break
    if reported_objective is None and isinstance(output.get("solution"), dict):
        for key in ("objective_exact", "objective", "objective_value", "total_value"):
            if key in output["solution"]:
                reported_objective = to_number(output["solution"].get(key))
                break
    if reported_objective is not None and abs(reported_objective - total_value) > tolerance:
        feasible = False
        messages.append(f"Reported objective {reported_objective} does not match computed objective {total_value}")
    return {
        "parse_ok": True,
        "feasible_under_instance": feasible,
        "status": status,
        "objective_value": reported_objective if reported_objective is not None else total_value,
        "selected_items": selected_items,
        "resource_usage": usage,
        "details": messages[:10],
    }


def validate_set_packing_output(output: Any, instance: dict[str, Any], tolerance: float) -> dict[str, Any]:
    if not isinstance(output, dict):
        return {"parse_ok": False, "feasible_under_instance": False, "details": "stdout is not a dict"}
    group_map = extract_group_map(instance)
    selected = output.get("selected_groups", [])
    if not isinstance(selected, list):
        return {"parse_ok": True, "feasible_under_instance": False, "details": "selected_groups is not a list"}
    selected = [str(x) for x in selected]
    item_counts: dict[str, int] = {}
    messages = []
    feasible = True
    total = 0.0
    for gid in selected:
        payload = group_map.get(gid)
        if payload is None:
            feasible = False
            messages.append(f"Unknown group {gid}")
            continue
        if payload.get("weight") is not None:
            total += float(payload["weight"])
        for item in payload.get("elements", ()):
            item_counts[item] = item_counts.get(item, 0) + 1
            if item_counts[item] > 1:
                feasible = False
                messages.append(f"Item {item} appears in more than one selected group")
    reported_total = to_number(output.get("total_value") if "total_value" in output else output.get("objective_value"))
    if reported_total is not None and abs(reported_total - total) > tolerance:
        feasible = False
        messages.append(f"Reported total {reported_total} does not match computed total {total}")
    return {
        "parse_ok": True,
        "feasible_under_instance": feasible,
        "status": normalize_status(output.get("status")),
        "objective_value": reported_total if reported_total is not None else total,
        "details": messages[:10],
    }


def validate_bipartite_assignment_output(output: Any, instance: dict[str, Any], tolerance: float) -> dict[str, Any]:
    payload = unwrap_solution_dict(output)
    if payload is None:
        return {"parse_ok": False, "feasible_under_instance": False, "details": "stdout is not a dict"}
    cost_matrix = instance.get("cost_matrix")
    if not isinstance(cost_matrix, dict):
        return {"parse_ok": True, "feasible_under_instance": False, "details": "instance is missing cost_matrix"}
    rows = [str(x) for x in extract_named_list(instance, "drivers")] or [str(x) for x in extract_named_list(instance, "left")] or [str(x) for x in cost_matrix.keys()]
    cols = [str(x) for x in extract_named_list(instance, "routes")] or [str(x) for x in extract_named_list(instance, "right")]
    if not cols:
        col_names: set[str] = set()
        for row in cost_matrix.values():
            if isinstance(row, dict):
                col_names.update(str(key) for key in row.keys())
        cols = sorted(col_names)
    assignments = extract_assignment_mapping(payload, source_entities=rows, target_entities=cols)
    feasible = True
    messages: list[str] = []
    used_cols: set[str] = set()
    total_cost = 0.0
    feasible_assignments = instance.get("feasible_assignments")
    requirement = instance.get("matching_requirement")
    required_side = requirement.get("required_side") if isinstance(requirement, dict) else None
    is_matching = instance.get("variant_type") == "matching"
    if is_matching and required_side not in {"drivers", "routes", "left", "right"}:
        feasible = False
        messages.append("Matching instance has an unsupported required_side")
    require_rows = not is_matching or required_side in {"drivers", "left"}
    require_cols = not is_matching or required_side in {"routes", "right"}
    if require_rows:
        for row in rows:
            if row not in assignments:
                feasible = False
                messages.append(f"Missing assignment for {row}")
    for row, col in assignments.items():
        if row not in rows or col not in cols:
            feasible = False
            messages.append(f"Unknown assignment endpoint {row}->{col}")
            continue
        if col in used_cols:
            feasible = False
            messages.append(f"Column {col} assigned more than once")
        used_cols.add(col)
        allowed = feasible_assignments.get(row) if isinstance(feasible_assignments, dict) else None
        if isinstance(allowed, list) and col not in [str(x) for x in allowed]:
            feasible = False
            messages.append(f"Assignment {row}->{col} is infeasible")
        row_costs = cost_matrix.get(row)
        if not isinstance(row_costs, dict):
            feasible = False
            messages.append(f"Missing cost row for {row}")
            continue
        cost = to_number(row_costs.get(col))
        if cost is None:
            feasible = False
            messages.append(f"Missing cost for {row}->{col}")
            continue
        total_cost += cost
    if require_cols and used_cols != set(cols):
        feasible = False
        messages.append(f"Missing assignments for columns {sorted(set(cols) - used_cols)}")
    reported_cost = extract_reported_objective(payload, ("objective_exact", "objective", "objective_value", "total_cost", "total_value"))
    if reported_cost is not None and abs(reported_cost - total_cost) > tolerance:
        feasible = False
        messages.append(f"Reported objective {reported_cost} does not match computed objective {total_cost}")
    return {
        "parse_ok": True,
        "feasible_under_instance": feasible,
        "status": normalize_status(payload.get("status")),
        "objective_value": reported_cost if reported_cost is not None else total_cost,
        "assignments": assignments,
        "details": messages[:10],
    }


def validate_facility_location_output(output: Any, instance: dict[str, Any], tolerance: float) -> dict[str, Any]:
    payload = unwrap_solution_dict(output)
    if payload is None:
        return {"parse_ok": False, "feasible_under_instance": False, "details": "stdout is not a dict"}
    facilities = instance.get("facility")
    customers = instance.get("customer")
    if not isinstance(facilities, dict) or not isinstance(customers, dict):
        return {"parse_ok": True, "feasible_under_instance": False, "details": "instance is missing facility or customer data"}
    facility_names = [str(x) for x in extract_named_list(instance, "F")] or [str(key) for key in facilities.keys()]
    customer_names = [str(x) for x in extract_named_list(instance, "C")] or [str(key) for key in customers.keys()]
    assignments = extract_assignment_mapping(payload, source_entities=customer_names, target_entities=facility_names)
    open_facilities = extract_named_selection(payload, ("open_facilities", "open_sites", "selected_sites", "opened_facilities"))
    if not open_facilities:
        open_facilities = sorted({dst for dst in assignments.values()})
    open_set = set(open_facilities)
    feasible = True
    messages: list[str] = []
    usage = {name: 0.0 for name in facility_names}
    assignment_cost_total = 0.0
    feasible_assignments = instance.get("feasible_assignments")
    per_unit_cost = instance.get("assignment_cost_per_unit_demand")
    for customer in customer_names:
        assigned = assignments.get(customer)
        if assigned is None:
            feasible = False
            messages.append(f"Missing assignment for {customer}")
            continue
        if assigned not in open_set:
            feasible = False
            messages.append(f"{customer} assigned to unopened facility {assigned}")
        allowed = feasible_assignments.get(customer) if isinstance(feasible_assignments, dict) else None
        if isinstance(allowed, list) and assigned not in [str(x) for x in allowed]:
            feasible = False
            messages.append(f"Assignment {customer}->{assigned} is infeasible")
        demand = 1.0
        customer_payload = customers.get(customer)
        if isinstance(customer_payload, dict):
            demand = float(to_number(customer_payload.get("demand")) or 1.0)
        usage[assigned] = usage.get(assigned, 0.0) + demand
        unit = None
        if isinstance(per_unit_cost, dict):
            row = per_unit_cost.get(customer)
            if isinstance(row, dict):
                unit = to_number(row.get(assigned))
        if unit is None:
            feasible = False
            messages.append(f"Missing assignment cost for {customer}->{assigned}")
            continue
        assignment_cost_total += demand * unit
    opening_cost_total = 0.0
    for facility in open_set:
        facility_payload = facilities.get(facility)
        if not isinstance(facility_payload, dict):
            feasible = False
            messages.append(f"Unknown facility {facility}")
            continue
        opening_cost_total += float(to_number(facility_payload.get("open_cost")) or 0.0)
        capacity = to_number(facility_payload.get("capacity"))
        if capacity is not None and usage.get(facility, 0.0) - capacity > tolerance:
            feasible = False
            messages.append(f"Capacity exceeded at {facility}: load={usage.get(facility, 0.0)} cap={capacity}")
    objective_value = opening_cost_total + assignment_cost_total
    reported_objective = extract_reported_objective(payload, ("objective_exact", "objective", "objective_value", "total_cost", "total_value"))
    if reported_objective is not None and abs(reported_objective - objective_value) > tolerance:
        feasible = False
        messages.append(f"Reported objective {reported_objective} does not match computed objective {objective_value}")
    return {
        "parse_ok": True,
        "feasible_under_instance": feasible,
        "status": normalize_status(payload.get("status")),
        "objective_value": reported_objective if reported_objective is not None else objective_value,
        "assignments": assignments,
        "open_facilities": sorted(open_set),
        "details": messages[:10],
    }


def validate_generalized_assignment_output(output: Any, instance: dict[str, Any], tolerance: float) -> dict[str, Any]:
    payload = unwrap_solution_dict(output)
    if payload is None:
        return {"parse_ok": False, "feasible_under_instance": False, "details": "stdout is not a dict"}
    agents = [str(x) for x in extract_named_list(instance, "agents")]
    tasks = [str(x) for x in extract_named_list(instance, "tasks")]
    if not agents:
        agents = [str(key) for key in (instance.get("agent_capacities") or {}).keys()]
    if not tasks:
        tasks = [str(key) for key in (instance.get("task_feasible_agents") or {}).keys()]
    assignments = extract_assignment_mapping(payload, source_entities=tasks, target_entities=agents)
    feasible = True
    messages: list[str] = []
    loads = {agent: 0.0 for agent in agents}
    capacities = instance.get("agent_capacities") or {}
    task_feasible_agents = instance.get("task_feasible_agents") or {}
    cost_matrix = instance.get("cost_matrix") or {}
    resource_matrix = instance.get("resource_matrix") or {}
    objective_value = 0.0
    for task in tasks:
        agent = assignments.get(task)
        if agent is None:
            feasible = False
            messages.append(f"Missing assignment for {task}")
            continue
        allowed = task_feasible_agents.get(task)
        if isinstance(allowed, list) and agent not in [str(x) for x in allowed]:
            feasible = False
            messages.append(f"Assignment {task}->{agent} is infeasible")
        cost_row = cost_matrix.get(agent)
        res_row = resource_matrix.get(agent)
        if not isinstance(cost_row, dict) or not isinstance(res_row, dict):
            feasible = False
            messages.append(f"Missing cost/resource row for agent {agent}")
            continue
        cost = to_number(cost_row.get(task))
        usage = to_number(res_row.get(task))
        if cost is None or usage is None:
            feasible = False
            messages.append(f"Missing cost/resource for {task}->{agent}")
            continue
        objective_value += cost
        loads[agent] = loads.get(agent, 0.0) + usage
    for agent in agents:
        capacity = to_number(capacities.get(agent)) if isinstance(capacities, dict) else None
        if capacity is not None and loads.get(agent, 0.0) - capacity > tolerance:
            feasible = False
            messages.append(f"Capacity exceeded at {agent}: load={loads.get(agent, 0.0)} cap={capacity}")
    reported_objective = extract_reported_objective(payload, ("objective_exact", "objective", "objective_value", "total_cost", "total_value"))
    if reported_objective is not None and abs(reported_objective - objective_value) > tolerance:
        feasible = False
        messages.append(f"Reported objective {reported_objective} does not match computed objective {objective_value}")
    return {
        "parse_ok": True,
        "feasible_under_instance": feasible,
        "status": normalize_status(payload.get("status")),
        "objective_value": reported_objective if reported_objective is not None else objective_value,
        "assignments": assignments,
        "agent_loads": loads,
        "details": messages[:10],
    }


def validate_p_median_center_output(output: Any, instance: dict[str, Any], tolerance: float) -> dict[str, Any]:
    payload = unwrap_solution_dict(output)
    if payload is None:
        return {"parse_ok": False, "feasible_under_instance": False, "details": "stdout is not a dict"}
    candidate_sites = instance.get("candidate_sites")
    demand_points = instance.get("demand_points")
    distance_matrix = instance.get("distance_matrix")
    if not isinstance(candidate_sites, dict) or not isinstance(demand_points, dict) or not isinstance(distance_matrix, dict):
        return {"parse_ok": True, "feasible_under_instance": False, "details": "instance is missing site, demand, or distance data"}
    site_names = [str(x) for x in extract_named_list(instance, "J")] or [str(key) for key in candidate_sites.keys()]
    demand_names = [str(x) for x in extract_named_list(instance, "I")] or [str(key) for key in demand_points.keys()]
    assignments = extract_assignment_mapping(payload, source_entities=demand_names, target_entities=site_names)
    open_sites = extract_named_selection(payload, ("open_sites", "selected_sites", "open_facilities"))
    if not open_sites:
        open_sites = sorted({dst for dst in assignments.values()})
    open_set = set(open_sites)
    p_value = int(to_number(instance.get("p_value")) or len(open_set))
    feasible = True
    messages: list[str] = []
    weighted_total = 0.0
    max_distance = 0.0
    demand_weights = instance.get("demand_weights") if isinstance(instance.get("demand_weights"), dict) else {}
    for demand in demand_names:
        site = assignments.get(demand)
        if site is None:
            feasible = False
            messages.append(f"Missing assignment for {demand}")
            continue
        if site not in open_set:
            feasible = False
            messages.append(f"{demand} assigned to unopened site {site}")
        row = distance_matrix.get(demand)
        if not isinstance(row, dict):
            feasible = False
            messages.append(f"Missing distance row for {demand}")
            continue
        distance = to_number(row.get(site))
        if distance is None:
            feasible = False
            messages.append(f"Missing distance for {demand}->{site}")
            continue
        weight = float(to_number(demand_weights.get(demand)) or 1.0)
        weighted_total += weight * distance
        if distance > max_distance:
            max_distance = distance
    if len(open_set) != p_value:
        feasible = False
        messages.append(f"Selected {len(open_set)} sites, expected {p_value}")
    variant_type = str(instance.get("variant_type") or "")
    objective_value = max_distance if "center" in variant_type else weighted_total
    reported_objective = extract_reported_objective(
        payload,
        ("objective_exact", "objective", "objective_value", "total_weighted_distance", "total_distance", "max_assignment_distance"),
    )
    if reported_objective is not None and abs(reported_objective - objective_value) > tolerance:
        feasible = False
        messages.append(f"Reported objective {reported_objective} does not match computed objective {objective_value}")
    return {
        "parse_ok": True,
        "feasible_under_instance": feasible,
        "status": normalize_status(payload.get("status")),
        "objective_value": reported_objective if reported_objective is not None else objective_value,
        "assignments": assignments,
        "open_sites": sorted(open_set),
        "details": messages[:10],
    }


def validate_set_covering_partitioning_output(output: Any, instance: dict[str, Any], tolerance: float) -> dict[str, Any]:
    payload = unwrap_solution_dict(output)
    if payload is None:
        return {"parse_ok": False, "feasible_under_instance": False, "details": "stdout is not a dict"}
    subsets = instance.get("candidate_subsets")
    if not isinstance(subsets, dict):
        return {"parse_ok": True, "feasible_under_instance": False, "details": "instance is missing candidate_subsets"}
    selected = extract_named_selection(payload, ("selected_subsets", "selected_sets", "selected_groups"))
    feasible = True
    messages: list[str] = []
    element_counts: dict[str, int] = {}
    objective_value = 0.0
    for subset in selected:
        subset_payload = subsets.get(subset)
        if not isinstance(subset_payload, dict):
            feasible = False
            messages.append(f"Unknown subset {subset}")
            continue
        objective_value += float(to_number(subset_payload.get("cost")) or 0.0)
        covered = subset_payload.get("covered_elements")
        if not isinstance(covered, list):
            feasible = False
            messages.append(f"Subset {subset} is missing covered elements")
            continue
        for element in covered:
            element_name = str(element)
            element_counts[element_name] = element_counts.get(element_name, 0) + 1
    elements = [str(x) for x in extract_named_list(instance, "E")] or sorted({str(element) for payload in subsets.values() if isinstance(payload, dict) for element in payload.get("covered_elements", [])})
    variant_type = str(instance.get("variant_type") or "set_covering")
    for element in elements:
        count = element_counts.get(element, 0)
        if "partition" in variant_type:
            if count != 1:
                feasible = False
                messages.append(f"Element {element} is covered {count} times, expected exactly once")
        elif count < 1:
            feasible = False
            messages.append(f"Element {element} is not covered")
    reported_objective = extract_reported_objective(payload, ("objective_exact", "objective", "objective_value", "total_cost", "total_value"))
    if reported_objective is not None and abs(reported_objective - objective_value) > tolerance:
        feasible = False
        messages.append(f"Reported objective {reported_objective} does not match computed objective {objective_value}")
    return {
        "parse_ok": True,
        "feasible_under_instance": feasible,
        "status": normalize_status(payload.get("status")),
        "objective_value": reported_objective if reported_objective is not None else objective_value,
        "selected_subsets": selected,
        "details": messages[:10],
    }


def validate_traveling_salesman_problem_output(output: Any, instance: dict[str, Any], tolerance: float) -> dict[str, Any]:
    payload = unwrap_solution_dict(output)
    if payload is None:
        return {"parse_ok": False, "feasible_under_instance": False, "details": "stdout is not a dict"}
    nodes = [str(x) for x in extract_named_list(instance, "nodes")] or sorted(str(x) for x in (instance.get("coordinates") or {}).keys())
    root = str(instance.get("root_city") or instance.get("depot") or (nodes[0] if nodes else ""))
    distance_matrix = instance.get("distance_matrix") if isinstance(instance.get("distance_matrix"), dict) else {}
    routes, _ = extract_routes_and_vehicle_ids(payload, depot=root, nodes=nodes)
    route = rotate_cycle_to_root(routes[0], root) if routes else []
    if route and route[-1] != route[0]:
        route = route + [route[0]]
    customers = [node for node in nodes if node != root]
    feasible = True
    messages: list[str] = []
    if not route:
        feasible = False
        messages.append("No tour or selected arcs were found in stdout")
    else:
        if route[0] != root:
            feasible = False
            messages.append(f"Tour must start at {root}, got {route[0]}")
        if route[-1] != root:
            feasible = False
            messages.append(f"Tour must end at {root}, got {route[-1]}")
        visited = route[1:-1]
        if Counter(visited) != Counter(customers):
            feasible = False
            messages.append(f"Visited customers {visited} do not match expected {customers}")
        if any(node == root for node in visited):
            feasible = False
            messages.append("Depot/root appears inside the interior of the tour")
    computed_objective = compute_route_cost_from_matrix(route, distance_matrix)
    effective_tolerance = max(tolerance, 1e-3)
    reported_objective = extract_reported_objective(payload, ("objective_exact", "objective", "objective_value", "total_cost", "total_distance"))
    if reported_objective is not None and computed_objective is not None and abs(reported_objective - computed_objective) > effective_tolerance:
        feasible = False
        messages.append(f"Reported objective {reported_objective} does not match computed objective {computed_objective}")
    return {
        "parse_ok": True,
        "feasible_under_instance": feasible,
        "status": normalize_status(payload.get("status")),
        "objective_value": reported_objective if reported_objective is not None else computed_objective,
        "route": route,
        "details": messages[:10],
    }


def validate_travel_salesman_problem_output(output: Any, instance: dict[str, Any], tolerance: float) -> dict[str, Any]:
    return validate_traveling_salesman_problem_output(output, instance, tolerance)


def validate_tsp_with_time_windows_output(output: Any, instance: dict[str, Any], tolerance: float) -> dict[str, Any]:
    payload = unwrap_solution_dict(output)
    if payload is None:
        return {"parse_ok": False, "feasible_under_instance": False, "details": "stdout is not a dict"}
    sets_payload = instance.get("sets") if isinstance(instance.get("sets"), dict) else {}
    nodes = [str(x) for x in sets_payload.get("nodes", [])] or sorted(str(x) for x in (instance.get("coordinates") or {}).keys())
    customers = [str(x) for x in sets_payload.get("customers", [])] or [node for node in nodes if node != str(instance.get("depot") or "Depot")]
    depot = str(instance.get("depot") or (nodes[0] if nodes else "Depot"))
    travel_time_matrix = instance.get("travel_time_matrix") if isinstance(instance.get("travel_time_matrix"), dict) else {}
    service_times = instance.get("service_times") if isinstance(instance.get("service_times"), dict) else {}
    time_windows = instance.get("time_windows") if isinstance(instance.get("time_windows"), dict) else {}
    routes, _ = extract_routes_and_vehicle_ids(payload, depot=depot, nodes=nodes)
    canonical_routes = [canonicalize_tsptw_route(route, depot=depot, nodes=nodes) for route in routes]
    route = rotate_cycle_to_root(canonical_routes[0], depot) if canonical_routes else []
    if route and route[-1] != depot:
        route = route + [depot]
    feasible = True
    messages: list[str] = []
    if not route:
        feasible = False
        messages.append("No tour or selected arcs were found in stdout")
    else:
        visited = route[1:-1]
        if route[0] != depot or route[-1] != depot:
            feasible = False
            messages.append(f"Tour must start and end at {depot}")
        if Counter(visited) != Counter(customers):
            feasible = False
            messages.append(f"Visited customers {visited} do not match expected {customers}")
    current_time = float(to_number((time_windows.get(depot) or [0.0])[0]) or 0.0)
    computed_objective = 0.0 if route else None
    if route:
        for tail, head in zip(route, route[1:]):
            travel_time = to_number((travel_time_matrix.get(tail) or {}).get(head))
            if travel_time is None:
                feasible = False
                messages.append(f"Missing travel time for arc {tail}->{head}")
                computed_objective = None
                break
            computed_objective += float(travel_time)
            arrival = current_time + float(to_number(service_times.get(tail)) or 0.0) + float(travel_time)
            window = time_windows.get(head)
            if isinstance(window, list) and len(window) >= 2:
                open_time = float(to_number(window[0]) or 0.0)
                close_time = float(to_number(window[1]) or 0.0)
                if arrival - close_time > max(tolerance, 1e-3):
                    feasible = False
                    messages.append(f"Arrival at {head} violates time window: arrival={arrival}, close={close_time}")
                current_time = max(arrival, open_time)
            else:
                current_time = arrival
    effective_tolerance = max(tolerance, 1e-2)
    reported_objective = extract_reported_objective(payload, ("objective_exact", "objective", "objective_value", "total_cost", "total_distance", "total_travel_time"))
    if reported_objective is not None and computed_objective is not None and abs(reported_objective - computed_objective) > effective_tolerance:
        feasible = False
        messages.append(f"Reported objective {reported_objective} does not match computed objective {computed_objective}")
    return {
        "parse_ok": True,
        "feasible_under_instance": feasible,
        "status": normalize_status(payload.get("status")),
        "objective_value": reported_objective if reported_objective is not None else computed_objective,
        "route": route,
        "details": messages[:10],
    }


def validate_vehicle_routing_problem_output(output: Any, instance: dict[str, Any], tolerance: float) -> dict[str, Any]:
    payload = unwrap_solution_dict(output)
    if payload is None:
        return {"parse_ok": False, "feasible_under_instance": False, "details": "stdout is not a dict"}
    sets_payload = instance.get("sets") if isinstance(instance.get("sets"), dict) else {}
    depot = str(instance.get("depot") or "Depot")
    customers = [str(x) for x in sets_payload.get("customers", [])]
    nodes = [str(x) for x in sets_payload.get("nodes", [])] or [depot] + customers
    demands = instance.get("demands") if isinstance(instance.get("demands"), dict) else {}
    distance_matrix = instance.get("distance_matrix") if isinstance(instance.get("distance_matrix"), dict) else {}
    vehicle_capacity = to_number(instance.get("vehicle_capacity"))
    routes, route_vehicle_ids = extract_routes_and_vehicle_ids(payload, depot=depot, nodes=nodes)
    feasible = True
    messages: list[str] = []
    if not routes:
        feasible = False
        messages.append("No routes or active arcs were found in stdout")
    visited_customers: list[str] = []
    computed_objective = 0.0
    computed_route_loads: list[float] = []
    normalized_routes: list[list[str]] = []
    for route in routes:
        if depot in route:
            route = rotate_cycle_to_root(route, depot)
        if route and route[-1] != depot:
            route = route + [depot]
        normalized_routes.append(route)
        if not route or route[0] != depot or route[-1] != depot:
            feasible = False
            messages.append(f"Malformed route {route}; each route must start/end at {depot}")
            continue
        customers_on_route = route[1:-1]
        if any(node == depot for node in customers_on_route):
            feasible = False
            messages.append(f"Depot appears inside route {route}")
        visited_customers.extend(customers_on_route)
        route_load = sum(float(to_number(demands.get(customer)) or 0.0) for customer in customers_on_route)
        computed_route_loads.append(route_load)
        if vehicle_capacity is not None and route_load - float(vehicle_capacity) > max(tolerance, 1e-6):
            feasible = False
            messages.append(f"Route load {route_load} exceeds vehicle capacity {vehicle_capacity}")
        route_cost = compute_route_cost_from_matrix(route, distance_matrix)
        if route_cost is None:
            feasible = False
            messages.append(f"Could not compute distance for route {route}")
        else:
            computed_objective += route_cost
    if Counter(visited_customers) != Counter(customers):
        feasible = False
        messages.append(f"Visited customers {visited_customers} do not match expected {customers}")
    reported_route_loads = payload.get("route_loads")
    if isinstance(reported_route_loads, list) and len(reported_route_loads) == len(computed_route_loads):
        for index, (reported, computed) in enumerate(zip(reported_route_loads, computed_route_loads), start=1):
            numeric = to_number(reported)
            if numeric is not None and abs(float(numeric) - computed) > max(tolerance, 1e-6):
                feasible = False
                messages.append(f"Route {index} reported load {numeric} does not match computed load {computed}")
    effective_tolerance = max(tolerance, 1e-3)
    reported_objective = extract_reported_objective(payload, ("objective_exact", "objective", "objective_value", "total_cost", "total_distance"))
    if reported_objective is not None and abs(reported_objective - computed_objective) > effective_tolerance:
        feasible = False
        messages.append(f"Reported objective {reported_objective} does not match computed objective {computed_objective}")
    return {
        "parse_ok": True,
        "feasible_under_instance": feasible,
        "status": normalize_status(payload.get("status")),
        "objective_value": reported_objective if reported_objective is not None else computed_objective,
        "routes": normalized_routes,
        "route_vehicle_ids": route_vehicle_ids,
        "route_loads": computed_route_loads,
        "details": messages[:10],
    }


def validate_heterogeneous_fleet_vrp_output(output: Any, instance: dict[str, Any], tolerance: float) -> dict[str, Any]:
    payload = unwrap_solution_dict(output)
    if payload is None:
        return {"parse_ok": False, "feasible_under_instance": False, "details": "stdout is not a dict"}
    sets_payload = instance.get("sets") if isinstance(instance.get("sets"), dict) else {}
    depot = str(instance.get("depot") or "Depot")
    customers = [str(x) for x in sets_payload.get("customers", [])]
    nodes = [str(x) for x in sets_payload.get("nodes", [])] or [depot] + customers
    demands = instance.get("demands") if isinstance(instance.get("demands"), dict) else {}
    vehicle_parameters = instance.get("vehicle_parameters") if isinstance(instance.get("vehicle_parameters"), dict) else {}
    vehicle_type_parameters = instance.get("vehicle_type_parameters") if isinstance(instance.get("vehicle_type_parameters"), dict) else {}
    travel_cost_by_type = instance.get("travel_cost_matrix_by_vehicle_type") if isinstance(instance.get("travel_cost_matrix_by_vehicle_type"), dict) else {}
    routes, raw_route_vehicle_ids = extract_routes_and_vehicle_ids(payload, depot=depot, nodes=nodes)
    routes = [canonicalize_hfvrp_route(route, depot=depot, nodes=nodes) for route in routes]
    raw_route_vehicle_types = [str(x) for x in payload.get("route_vehicle_types", [])] if isinstance(payload.get("route_vehicle_types"), list) else []
    route_vehicle_ids, route_vehicle_types = normalize_hfvrp_vehicle_assignments(
        raw_route_vehicle_ids,
        raw_route_vehicle_types,
        route_count=len(routes),
        vehicle_parameters=vehicle_parameters,
        vehicle_type_parameters=vehicle_type_parameters,
    )
    reported_route_costs = payload.get("route_total_costs") if isinstance(payload.get("route_total_costs"), list) else []
    feasible = True
    messages: list[str] = []
    if not routes:
        feasible = False
        messages.append("No routes or active arcs were found in stdout")
    visited_customers: list[str] = []
    computed_objective = 0.0
    normalized_routes: list[list[str]] = []
    derived_vehicle_types: list[str | None] = []
    vehicle_use_counter: Counter[str] = Counter()
    type_use_counter: Counter[str] = Counter()
    for index, route in enumerate(routes):
        if depot in route:
            route = rotate_cycle_to_root(route, depot)
        if route and route[-1] != depot:
            route = route + [depot]
        normalized_routes.append(route)
        if not route or route[0] != depot or route[-1] != depot:
            feasible = False
            messages.append(f"Malformed route {route}; each route must start/end at {depot}")
            continue
        vehicle_id = route_vehicle_ids[index] if index < len(route_vehicle_ids) else None
        vehicle_type = route_vehicle_types[index] if index < len(route_vehicle_types) else None
        if index < len(raw_route_vehicle_types) and resolve_hfvrp_vehicle_type_alias(raw_route_vehicle_types[index], list(vehicle_type_parameters)) is None:
            feasible = False
            messages.append(f"Unknown vehicle type for route {index + 1}")
        vehicle_record = vehicle_parameters.get(vehicle_id)
        if not isinstance(vehicle_record, dict) or vehicle_type not in vehicle_type_parameters:
            feasible = False
            messages.append(f"Route {index + 1} has no valid vehicle assignment")
        elif resolve_hfvrp_vehicle_type_alias(vehicle_record.get("type_id"), list(vehicle_type_parameters)) != vehicle_type:
            feasible = False
            messages.append(f"Vehicle {vehicle_id} does not have type {vehicle_type}")
        if vehicle_type is None and vehicle_id is not None and isinstance(vehicle_parameters.get(vehicle_id), dict):
            vehicle_type = str(vehicle_parameters[vehicle_id].get("type_id") or "")
        if vehicle_type == "":
            vehicle_type = None
        derived_vehicle_types.append(vehicle_type)
        if vehicle_id is not None:
            vehicle_use_counter[vehicle_id] += 1
        if vehicle_type is not None:
            type_use_counter[vehicle_type] += 1
        customers_on_route = route[1:-1]
        if any(node == depot for node in customers_on_route):
            feasible = False
            messages.append(f"Depot appears inside route {route}")
        visited_customers.extend(customers_on_route)
        route_load = sum(float(to_number(demands.get(customer)) or 0.0) for customer in customers_on_route)
        capacity = None
        if vehicle_id is not None and isinstance(vehicle_parameters.get(vehicle_id), dict):
            capacity = to_number(vehicle_parameters[vehicle_id].get("capacity"))
        if capacity is None and vehicle_type is not None and isinstance(vehicle_type_parameters.get(vehicle_type), dict):
            capacity = to_number(vehicle_type_parameters[vehicle_type].get("capacity"))
        if capacity is None:
            feasible = False
            messages.append(f"Missing vehicle capacity for route {index + 1}")
        elif route_load - float(capacity) > max(tolerance, 1e-6):
            feasible = False
            messages.append(f"Route load {route_load} exceeds capacity {capacity} for route {index + 1}")
        computed_route_cost = None
        if vehicle_type is not None and isinstance(travel_cost_by_type.get(vehicle_type), dict):
            variable_cost = compute_route_cost_from_matrix(route, travel_cost_by_type[vehicle_type])
            if variable_cost is not None:
                fixed_cost = None
                if vehicle_id is not None and isinstance(vehicle_parameters.get(vehicle_id), dict):
                    fixed_cost = to_number(vehicle_parameters[vehicle_id].get("fixed_activation_cost"))
                if fixed_cost is None and isinstance(vehicle_type_parameters.get(vehicle_type), dict):
                    fixed_cost = to_number(vehicle_type_parameters[vehicle_type].get("fixed_activation_cost"))
                if fixed_cost is not None:
                    computed_route_cost = variable_cost + float(fixed_cost)
        if computed_route_cost is None:
            feasible = False
            messages.append(f"Could not compute route cost for route {index + 1}")
        else:
            computed_objective += computed_route_cost
            if index < len(reported_route_costs):
                reported_cost = to_number(reported_route_costs[index])
                if reported_cost is None or abs(reported_cost - computed_route_cost) > max(tolerance, 1e-3):
                    feasible = False
                    messages.append(f"Route {index + 1} reported cost does not match its computed cost")
    if Counter(visited_customers) != Counter(customers):
        feasible = False
        messages.append(f"Visited customers {visited_customers} do not match expected {customers}")
    for vehicle_id, count in vehicle_use_counter.items():
        if count > 1:
            feasible = False
            messages.append(f"Vehicle {vehicle_id} is assigned to {count} routes")
    for vehicle_type, count in type_use_counter.items():
        available = None
        if isinstance(vehicle_type_parameters.get(vehicle_type), dict):
            available = to_number(vehicle_type_parameters[vehicle_type].get("available_count"))
        if available is not None and count > int(available):
            feasible = False
            messages.append(f"Vehicle type {vehicle_type} uses {count} routes but only {available} are available")
    effective_tolerance = max(tolerance, 1e-3)
    reported_objective = extract_reported_objective(payload, ("objective_exact", "objective", "objective_value", "total_cost", "objective_from_routes"))
    if reported_objective is not None and abs(reported_objective - computed_objective) > effective_tolerance:
        feasible = False
        messages.append(f"Reported objective {reported_objective} does not match computed objective {computed_objective}")
    return {
        "parse_ok": True,
        "feasible_under_instance": feasible,
        "status": normalize_status(payload.get("status")),
        "objective_value": reported_objective if reported_objective is not None else computed_objective,
        "routes": normalized_routes,
        "route_vehicle_ids": route_vehicle_ids,
        "route_vehicle_types": derived_vehicle_types,
        "details": messages[:10],
    }


def validate_job_shop_scheduling_output(output: Any, instance: dict[str, Any], tolerance: float) -> dict[str, Any]:
    payload = unwrap_solution_dict(output)
    if payload is None:
        return {"parse_ok": False, "feasible_under_instance": False, "details": "stdout is not a dict"}
    sets_payload = instance.get("sets") if isinstance(instance.get("sets"), dict) else {}
    jobs = [str(x) for x in sets_payload.get("jobs", [])]
    machine_assignment = instance.get("machine_assignment") if isinstance(instance.get("machine_assignment"), dict) else {}
    processing_time = instance.get("processing_time") if isinstance(instance.get("processing_time"), dict) else {}
    if not jobs:
        jobs = sorted(
            {str(key) for key in machine_assignment.keys()} | {str(key) for key in processing_time.keys()},
            key=natural_label_sort_key,
        )
    operations_payload = sets_payload.get("operations")
    operations_by_job: dict[str, list[str]] = {}
    if isinstance(operations_payload, dict):
        for job, operations in operations_payload.items():
            if isinstance(operations, list):
                operations_by_job[str(job)] = [str(operation) for operation in operations]
    elif isinstance(operations_payload, list):
        shared_operations = [str(x) for x in operations_payload]
        for job in jobs:
            operations_by_job[job] = list(shared_operations)
    def normalize_job_shop_operation_label(job: str, operation: str | None) -> str | None:
        if operation is None:
            return None
        text = str(operation).strip()
        if not text:
            return None
        known_operations = operations_by_job.get(job) or []
        if text in known_operations:
            return text
        compact = text
        for separator in ("_", "-"):
            prefix = f"{job}{separator}"
            if compact.startswith(prefix):
                compact = compact[len(prefix):]
                break
        prefixed = f"O{compact}"
        if prefixed in known_operations:
            return prefixed
        if compact in known_operations:
            return compact
        return text

    schedule_records: dict[tuple[str, str], dict[str, Any]] = {}
    raw_schedule = None
    for key in ("schedule", "schedule_by_job", "job_schedule", "operations"):
        candidate = payload.get(key)
        if isinstance(candidate, (list, dict)):
            raw_schedule = candidate
            break
    if isinstance(raw_schedule, list):
        for item in raw_schedule:
            if not isinstance(item, dict):
                continue
            job = extract_first_text_field(item, ("job", "job_id"))
            operation = normalize_job_shop_operation_label(
                str(job),
                extract_first_text_field(item, ("operation", "operation_id", "op")),
            ) if job is not None else None
            if job is None or operation is None:
                continue
            schedule_records[(job, operation)] = {
                "machine": extract_first_text_field(item, ("machine", "machine_id", "resource")),
                "start": extract_first_numeric_field(item, ("start", "start_time", "begin")),
                "finish": extract_first_numeric_field(item, ("finish", "completion", "completion_time", "end", "end_time")),
                "duration": extract_first_numeric_field(item, ("duration", "processing_time", "proc_time")),
            }
    elif isinstance(raw_schedule, dict):
        for schedule_key, operation_map in raw_schedule.items():
            if isinstance(operation_map, list):
                job = str(schedule_key)
                for item in operation_map:
                    if not isinstance(item, dict):
                        continue
                    normalized_operation = normalize_job_shop_operation_label(
                        job,
                        extract_first_text_field(item, ("operation", "operation_id", "op")),
                    )
                    if normalized_operation is None:
                        continue
                    schedule_records[(job, normalized_operation)] = {
                        "machine": extract_first_text_field(item, ("machine", "machine_id", "resource")),
                        "start": extract_first_numeric_field(item, ("start", "start_time", "begin")),
                        "finish": extract_first_numeric_field(item, ("finish", "completion", "completion_time", "end", "end_time")),
                        "duration": extract_first_numeric_field(item, ("duration", "processing_time", "proc_time")),
                    }
                continue
            if not isinstance(operation_map, dict):
                continue
            leaf_job = extract_first_text_field(operation_map, ("job", "job_id"))
            leaf_operation = normalize_job_shop_operation_label(
                str(leaf_job),
                extract_first_text_field(operation_map, ("operation", "operation_id", "op")) or str(schedule_key),
            ) if leaf_job is not None else None
            if leaf_job is not None and leaf_operation is not None:
                schedule_records[(str(leaf_job), str(leaf_operation))] = {
                    "machine": extract_first_text_field(operation_map, ("machine", "machine_id", "resource")),
                    "start": extract_first_numeric_field(operation_map, ("start", "start_time", "begin")),
                    "finish": extract_first_numeric_field(operation_map, ("finish", "completion", "completion_time", "end", "end_time")),
                    "duration": extract_first_numeric_field(operation_map, ("duration", "processing_time", "proc_time")),
                }
                continue
            job = str(schedule_key)
            for operation, item in operation_map.items():
                if not isinstance(item, dict):
                    continue
                normalized_operation = normalize_job_shop_operation_label(job, str(operation))
                if normalized_operation is None:
                    continue
                schedule_records[(job, normalized_operation)] = {
                    "machine": extract_first_text_field(item, ("machine", "machine_id", "resource")),
                    "start": extract_first_numeric_field(item, ("start", "start_time", "begin")),
                    "finish": extract_first_numeric_field(item, ("finish", "completion", "completion_time", "end", "end_time")),
                    "duration": extract_first_numeric_field(item, ("duration", "processing_time", "proc_time")),
                }
    start_times: dict[str, dict[str, float]] = {}
    for key in ("start_time", "start_times", "operation_start_times", "operation_starts"):
        start_times = normalize_nested_numeric_mapping(payload.get(key))
        if start_times:
            break
    finish_times: dict[str, dict[str, float]] = {}
    for key in ("finish_time", "finish_times", "completion_time", "completion_times", "operation_finish_times"):
        finish_times = normalize_nested_numeric_mapping(payload.get(key))
        if finish_times:
            break
    predicted_machine_assignment: dict[str, dict[str, str]] = {}
    for key in ("machine_assignment", "assignment", "operation_machine_assignment"):
        predicted_machine_assignment = normalize_nested_string_mapping(payload.get(key))
        if predicted_machine_assignment:
            break
    feasible = True
    messages: list[str] = []
    machine_intervals: dict[str, list[tuple[float, float, str, str]]] = {}
    job_timelines: dict[str, list[tuple[str, float, float]]] = {}
    computed_makespan = 0.0
    expected_pairs = 0
    for job in jobs:
        required_machines = machine_assignment.get(job) if isinstance(machine_assignment.get(job), dict) else {}
        required_durations = processing_time.get(job) if isinstance(processing_time.get(job), dict) else {}
        ordered_operations = operations_by_job.get(job) or sorted(
            {str(key) for key in required_machines.keys()} | {str(key) for key in required_durations.keys()},
            key=natural_label_sort_key,
        )
        for operation in ordered_operations:
            expected_pairs += 1
            record = dict(schedule_records.get((job, operation), {}))
            start = record.get("start")
            if start is None:
                start = (start_times.get(job) or {}).get(operation)
            finish = record.get("finish")
            if finish is None:
                finish = (finish_times.get(job) or {}).get(operation)
            machine = record.get("machine") or (predicted_machine_assignment.get(job) or {}).get(operation)
            required_machine = str(required_machines.get(operation)) if operation in required_machines else None
            duration_expected = to_number(required_durations.get(operation)) if operation in required_durations else None
            if machine is None:
                machine = required_machine
            duration = record.get("duration")
            if duration is None and start is not None and finish is not None:
                duration = float(finish) - float(start)
            if finish is None and start is not None and duration_expected is not None:
                finish = float(start) + float(duration_expected)
            if start is None and finish is not None and duration_expected is not None:
                start = float(finish) - float(duration_expected)
            if start is None or finish is None:
                feasible = False
                messages.append(f"Missing start/finish for {job}-{operation}")
                continue
            if start < -max(tolerance, 1e-6):
                feasible = False
                messages.append(f"Negative start time for {job}-{operation}: {start}")
            if finish + max(tolerance, 1e-6) < start:
                feasible = False
                messages.append(f"Finish precedes start for {job}-{operation}: start={start} finish={finish}")
            if required_machine is not None and machine is not None and str(machine) != required_machine:
                feasible = False
                messages.append(f"{job}-{operation} assigned to {machine}, expected {required_machine}")
            actual_duration = float(finish) - float(start)
            if duration_expected is not None and abs(actual_duration - float(duration_expected)) > max(tolerance, 1e-6):
                feasible = False
                messages.append(
                    f"{job}-{operation} duration {actual_duration} does not match expected {duration_expected}"
                )
            if machine is not None:
                machine_intervals.setdefault(str(machine), []).append((float(start), float(finish), job, operation))
            job_timelines.setdefault(job, []).append((operation, float(start), float(finish)))
            if finish > computed_makespan:
                computed_makespan = float(finish)
    if expected_pairs == 0:
        feasible = False
        messages.append("instance is missing operation definitions")
    for job, entries in job_timelines.items():
        order_lookup = {
            operation: index for index, operation in enumerate(operations_by_job.get(job, []))
        } if operations_by_job.get(job) else {}
        ordered_entries = sorted(
            entries,
            key=lambda item: (0, order_lookup[item[0]]) if item[0] in order_lookup else (1, natural_label_sort_key(item[0])),
        )
        for (_, _, prev_finish), (operation, start, _) in zip(ordered_entries, ordered_entries[1:]):
            if prev_finish - start > max(tolerance, 1e-6):
                feasible = False
                messages.append(f"Job precedence violated at {job}-{operation}: previous finish={prev_finish}, start={start}")
    for machine, intervals in machine_intervals.items():
        ordered = sorted(intervals, key=lambda item: (item[0], item[1], natural_label_sort_key(item[2]), natural_label_sort_key(item[3])))
        for (_, prev_finish, prev_job, prev_operation), (start, finish, job, operation) in zip(ordered, ordered[1:]):
            if prev_finish - start > max(tolerance, 1e-6):
                feasible = False
                messages.append(
                    f"Machine overlap on {machine}: {prev_job}-{prev_operation} finish={prev_finish} overlaps {job}-{operation} start={start}"
                )
    reported_objective = extract_reported_objective(
        payload,
        ("objective_exact", "objective", "objective_value", "makespan", "total_makespan"),
    )
    if reported_objective is not None and abs(float(reported_objective) - computed_makespan) > max(tolerance, 1e-6):
        feasible = False
        messages.append(f"Reported objective {reported_objective} does not match computed makespan {computed_makespan}")
    return {
        "parse_ok": True,
        "feasible_under_instance": feasible,
        "status": normalize_status(payload.get("status")),
        "objective_value": reported_objective if reported_objective is not None else computed_makespan,
        "scheduled_operations": sum(len(entries) for entries in job_timelines.values()),
        "details": messages[:10],
    }


def validate_parallel_machine_scheduling_output(output: Any, instance: dict[str, Any], tolerance: float) -> dict[str, Any]:
    payload = unwrap_solution_dict(output)
    if payload is None:
        return {"parse_ok": False, "feasible_under_instance": False, "details": "stdout is not a dict"}
    sets_payload = instance.get("sets") if isinstance(instance.get("sets"), dict) else {}
    jobs = [str(x) for x in sets_payload.get("jobs", [])]
    machines = [str(x) for x in sets_payload.get("machines", [])]
    if not jobs:
        jobs = sorted(
            {str(key) for key in (instance.get("effective_processing_time") or {}).keys()}
            | {str(key) for key in (instance.get("eligibility") or {}).keys()},
            key=natural_label_sort_key,
        )
    if not machines:
        machines = sorted(
            {str(key) for key in (instance.get("machine_speed") or {}).keys()}
            | {
                str(machine)
                for durations in (instance.get("effective_processing_time") or {}).values()
                if isinstance(durations, dict)
                for machine in durations.keys()
            },
            key=natural_label_sort_key,
        )
    eligibility = instance.get("eligibility") if isinstance(instance.get("eligibility"), dict) else {}
    effective_processing_time = (
        instance.get("effective_processing_time") if isinstance(instance.get("effective_processing_time"), dict) else {}
    )
    meta_parameters = instance.get("meta_parameters") if isinstance(instance.get("meta_parameters"), dict) else {}
    objective_type = instance.get("objective_type", meta_parameters.get("objective_type", "makespan"))
    weights = instance.get("weights") if isinstance(instance.get("weights"), dict) else {}
    assignment = extract_assignment_mapping(payload, source_entities=jobs, target_entities=machines)
    schedule_records: dict[str, dict[str, Any]] = {}
    raw_schedule = payload.get("schedule")
    if isinstance(raw_schedule, list):
        for item in raw_schedule:
            if not isinstance(item, dict):
                continue
            job = extract_first_text_field(item, ("job", "job_id"))
            if job is None:
                continue
            schedule_records[job] = {
                "machine": extract_first_text_field(item, ("machine", "machine_id", "resource")),
                "start": extract_first_numeric_field(item, ("start", "start_time", "begin")),
                "finish": extract_first_numeric_field(item, ("finish", "completion", "completion_time", "end", "end_time")),
                "duration": extract_first_numeric_field(item, ("duration", "processing_time", "proc_time")),
            }
    elif isinstance(raw_schedule, dict):
        for job, item in raw_schedule.items():
            if not isinstance(item, dict):
                continue
            schedule_records[str(job)] = {
                "machine": extract_first_text_field(item, ("machine", "machine_id", "resource")),
                "start": extract_first_numeric_field(item, ("start", "start_time", "begin")),
                "finish": extract_first_numeric_field(item, ("finish", "completion", "completion_time", "end", "end_time")),
                "duration": extract_first_numeric_field(item, ("duration", "processing_time", "proc_time")),
            }
    machine_schedule_payload = payload.get("machine_schedules") if isinstance(payload.get("machine_schedules"), dict) else payload.get("schedule_by_machine")
    if isinstance(machine_schedule_payload, dict):
        for machine, items in machine_schedule_payload.items():
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                job = extract_first_text_field(item, ("job", "job_id"))
                if job is None:
                    continue
                schedule_records[job] = {
                    "machine": str(machine),
                    "start": extract_first_numeric_field(item, ("start", "start_time", "begin")),
                    "finish": extract_first_numeric_field(item, ("finish", "completion", "completion_time", "end", "end_time")),
                    "duration": extract_first_numeric_field(item, ("duration", "processing_time", "proc_time")),
                }
    start_times = {}
    for key in ("start_time", "start_times", "job_start_times"):
        start_times = normalize_named_numeric_mapping(payload.get(key))
        if start_times:
            break
    finish_times = {}
    for key in ("finish_time", "finish_times", "completion_time", "completion_times", "job_finish_times"):
        finish_times = normalize_named_numeric_mapping(payload.get(key))
        if finish_times:
            break
    feasible = True
    messages: list[str] = []
    machine_intervals: dict[str, list[tuple[float, float, str]]] = {}
    deferred_jobs_by_machine: dict[str, list[tuple[str, float]]] = {}
    computed_machine_loads: dict[str, float] = {machine: 0.0 for machine in machines}
    computed_makespan = 0.0
    visited_jobs: list[str] = []
    for job in jobs:
        record = dict(schedule_records.get(job, {}))
        machine = record.get("machine") or assignment.get(job)
        start = record.get("start")
        if start is None:
            start = start_times.get(job)
        finish = record.get("finish")
        if finish is None:
            finish = finish_times.get(job)
        allowed_machines = eligibility.get(job)
        expected_duration = None
        if machine is not None and isinstance(effective_processing_time.get(job), dict):
            expected_duration = to_number(effective_processing_time[job].get(str(machine)))
        duration = record.get("duration")
        if duration is None and start is not None and finish is not None:
            duration = float(finish) - float(start)
        if finish is None and start is not None and expected_duration is not None:
            finish = float(start) + float(expected_duration)
        if start is None and finish is not None and expected_duration is not None:
            start = float(finish) - float(expected_duration)
        if machine is None:
            feasible = False
            messages.append(f"Missing machine assignment for {job}")
            continue
        visited_jobs.append(job)
        if str(machine) not in machines or expected_duration is None:
            feasible = False
            messages.append(f"Unknown machine or processing time for {job}@{machine}")
            continue
        if isinstance(allowed_machines, list) and str(machine) not in [str(item) for item in allowed_machines]:
            feasible = False
            messages.append(f"Job {job} assigned to ineligible machine {machine}")
        if start is None or finish is None:
            if objective_type != "makespan":
                feasible = False
                messages.append(f"Missing schedule times for {job} under {objective_type}")
                continue
            deferred_jobs_by_machine.setdefault(str(machine), []).append((job, float(expected_duration)))
            computed_machine_loads[str(machine)] = computed_machine_loads.get(str(machine), 0.0) + float(expected_duration)
            continue
        if start < -max(tolerance, 1e-6):
            feasible = False
            messages.append(f"Negative start time for {job}: {start}")
        if finish + max(tolerance, 1e-6) < start:
            feasible = False
            messages.append(f"Finish precedes start for {job}: start={start} finish={finish}")
        actual_duration = float(finish) - float(start)
        if expected_duration is not None and abs(actual_duration - float(expected_duration)) > max(tolerance, 1e-6):
            feasible = False
            messages.append(f"{job} duration {actual_duration} does not match expected {expected_duration}")
        machine_intervals.setdefault(str(machine), []).append((float(start), float(finish), job))
        computed_machine_loads[str(machine)] = computed_machine_loads.get(str(machine), 0.0) + actual_duration
        if finish > computed_makespan:
            computed_makespan = float(finish)
    for machine, entries in deferred_jobs_by_machine.items():
        cursor = max((finish for _, finish, _ in machine_intervals.get(machine, [])), default=0.0)
        for job, duration in sorted(entries, key=lambda item: natural_label_sort_key(item[0])):
            start = float(cursor)
            finish = start + float(duration)
            machine_intervals.setdefault(machine, []).append((start, finish, job))
            cursor = finish
            if finish > computed_makespan:
                computed_makespan = float(finish)
    if Counter(visited_jobs) != Counter(jobs):
        feasible = False
        messages.append(f"Scheduled jobs {visited_jobs} do not match expected {jobs}")
    for machine, intervals in machine_intervals.items():
        ordered = sorted(intervals, key=lambda item: (item[0], item[1], natural_label_sort_key(item[2])))
        for (_, prev_finish, prev_job), (start, _, job) in zip(ordered, ordered[1:]):
            if prev_finish - start > max(tolerance, 1e-6):
                feasible = False
                messages.append(
                    f"Machine overlap on {machine}: {prev_job} finish={prev_finish} overlaps {job} start={start}"
                )
    completion_times = {job: finish for intervals in machine_intervals.values() for _, finish, job in intervals}
    objective_keys = ("objective_exact", "objective", "objective_value")
    if objective_type == "makespan":
        computed_objective = computed_makespan
        objective_keys += ("makespan", "total_makespan")
    elif objective_type == "total_completion":
        computed_objective = sum(completion_times.values())
        # The shared normalizer can synthesize objective_value from makespan.
        objective_keys = ("total_completion", "total_completion_time", "sum_completion_times") + objective_keys
    elif objective_type == "weighted_completion":
        computed_objective = 0.0
        for job, finish in completion_times.items():
            weight = to_number(weights.get(job))
            if weight is None:
                feasible = False
                messages.append(f"Missing completion weight for {job}")
                continue
            computed_objective += weight * finish
        objective_keys = ("weighted_completion", "total_weighted_completion", "weighted_completion_time") + objective_keys
    else:
        feasible = False
        computed_objective = computed_makespan
        messages.append(f"Unsupported objective type {objective_type}")
    reported_objective = extract_reported_objective(payload, objective_keys)
    if reported_objective is not None and abs(float(reported_objective) - computed_objective) > max(tolerance, 1e-6):
        feasible = False
        messages.append(f"Reported objective {reported_objective} does not match computed {objective_type} {computed_objective}")
    return {
        "parse_ok": True,
        "feasible_under_instance": feasible,
        "status": normalize_status(payload.get("status")),
        "objective_value": reported_objective if reported_objective is not None else computed_objective,
        "assignments": {job: (schedule_records.get(job) or {}).get("machine") or assignment.get(job) for job in jobs},
        "machine_loads": computed_machine_loads,
        "details": messages[:10],
    }


def validate_rcpsp_output(output: Any, instance: dict[str, Any], tolerance: float) -> dict[str, Any]:
    payload = unwrap_solution_dict(output)
    if payload is None:
        return {"parse_ok": False, "feasible_under_instance": False, "details": "stdout is not a dict"}
    sets_payload = instance.get("sets") if isinstance(instance.get("sets"), dict) else {}
    activities = [str(x) for x in sets_payload.get("activities", [])]
    real_activities = [str(x) for x in sets_payload.get("real_activities", [])]
    resources = [str(x) for x in sets_payload.get("resources", [])]
    if not activities:
        activities = sorted((str(key) for key in (instance.get("duration") or {}).keys()), key=natural_label_sort_key)
    durations = instance.get("duration") if isinstance(instance.get("duration"), dict) else {}
    resource_capacity = instance.get("resource_capacity") if isinstance(instance.get("resource_capacity"), dict) else {}
    resource_demand = instance.get("resource_demand") if isinstance(instance.get("resource_demand"), dict) else {}
    precedence_arcs = list(extract_scheduling_precedence_arc_set(instance))
    start_times = {}
    for key in ("activity_start_times", "start_time", "start_times", "activity_starts", "schedule"):
        start_times = normalize_named_numeric_mapping(payload.get(key))
        if start_times:
            break
    finish_times = {}
    for key in ("activity_finish_times", "finish_time", "finish_times", "completion_time", "completion_times"):
        finish_times = normalize_named_numeric_mapping(payload.get(key))
        if finish_times:
            break
    raw_schedule = payload.get("schedule")
    if isinstance(raw_schedule, list):
        for item in raw_schedule:
            if not isinstance(item, dict):
                continue
            activity = extract_first_text_field(item, ("activity", "activity_id", "job", "task"))
            if activity is None:
                continue
            start = extract_first_numeric_field(item, ("start", "start_time", "begin"))
            finish = extract_first_numeric_field(item, ("finish", "completion", "completion_time", "end", "end_time"))
            if start is not None:
                start_times.setdefault(activity, float(start))
            if finish is not None:
                finish_times.setdefault(activity, float(finish))
    feasible = True
    messages: list[str] = []
    normalized_schedule: dict[str, tuple[float, float]] = {}
    for activity in activities:
        duration = to_number(durations.get(activity))
        start = start_times.get(activity)
        finish = finish_times.get(activity)
        if activity == "Start" and start is None:
            start = 0.0
        if duration is None:
            feasible = False
            messages.append(f"Missing duration for {activity}")
            continue
        if finish is None and start is not None:
            finish = float(start) + float(duration)
        if start is None and finish is not None:
            start = float(finish) - float(duration)
        if activity == "End" and start is None:
            continue
        if start is None or finish is None:
            feasible = False
            messages.append(f"Missing start/finish for {activity}")
            continue
        if start < -max(tolerance, 1e-6):
            feasible = False
            messages.append(f"Negative start time for {activity}: {start}")
        if abs((float(finish) - float(start)) - float(duration)) > max(tolerance, 1e-6):
            feasible = False
            messages.append(
                f"{activity} duration {float(finish) - float(start)} does not match expected {duration}"
            )
        normalized_schedule[activity] = (float(start), float(finish))
    computed_makespan = max((finish for _, finish in normalized_schedule.values()), default=0.0)
    for tail, head in precedence_arcs:
        if tail == "End":
            continue
        tail_window = normalized_schedule.get(tail)
        if tail_window is None:
            feasible = False
            messages.append(f"Missing predecessor timing for {tail}")
            continue
        tail_finish = tail_window[1]
        if head == "End":
            if computed_makespan + max(tolerance, 1e-6) < tail_finish:
                feasible = False
                messages.append(f"End occurs before predecessor {tail} finishes")
            continue
        head_window = normalized_schedule.get(head)
        if head_window is None:
            feasible = False
            messages.append(f"Missing successor timing for {head}")
            continue
        if tail_finish - head_window[0] > max(tolerance, 1e-6):
            feasible = False
            messages.append(f"Precedence violated for {tail}->{head}: {tail_finish} > {head_window[0]}")
    horizon = int(computed_makespan + 1)
    resource_names = resources or sorted(resource_capacity.keys(), key=natural_label_sort_key)
    active_activities = real_activities or [activity for activity in activities if activity not in {"Start", "End"}]
    for period in range(max(horizon, 1)):
        for resource in resource_names:
            usage = 0.0
            for activity in active_activities:
                window = normalized_schedule.get(activity)
                if window is None:
                    continue
                start, finish = window
                if start < period + 1 - max(tolerance, 1e-6) and finish > period + max(tolerance, 1e-6):
                    usage += float(to_number((resource_demand.get(activity) or {}).get(resource)) or 0.0)
            capacity = to_number(resource_capacity.get(resource))
            if capacity is not None and usage - float(capacity) > max(tolerance, 1e-6):
                feasible = False
                messages.append(f"Resource {resource} exceeds capacity at time {period}: usage={usage} cap={capacity}")
    reported_objective = extract_reported_objective(
        payload,
        ("objective_exact", "objective", "objective_value", "makespan", "total_makespan"),
    )
    if reported_objective is not None and abs(float(reported_objective) - computed_makespan) > max(tolerance, 1e-6):
        feasible = False
        messages.append(f"Reported objective {reported_objective} does not match computed makespan {computed_makespan}")
    return {
        "parse_ok": True,
        "feasible_under_instance": feasible,
        "status": normalize_status(payload.get("status")),
        "objective_value": reported_objective if reported_objective is not None else computed_makespan,
        "activity_start_times": {activity: times[0] for activity, times in normalized_schedule.items()},
        "details": messages[:10],
    }


def validate_flexible_hybrid_flow_shop_scheduling_output(
    output: Any,
    instance: dict[str, Any],
    tolerance: float,
) -> dict[str, Any]:
    payload = unwrap_solution_dict(output)
    if payload is None:
        return {"parse_ok": False, "feasible_under_instance": False, "details": "stdout is not a dict"}
    sets_payload = instance.get("sets") if isinstance(instance.get("sets"), dict) else {}
    jobs = [str(x) for x in sets_payload.get("jobs", [])]
    stages = [str(x) for x in sets_payload.get("stages", [])]
    if isinstance(instance.get("common_stage_order"), list):
        stages = [str(x) for x in instance["common_stage_order"]]
    machines_by_stage = sets_payload.get("machines_by_stage") if isinstance(sets_payload.get("machines_by_stage"), dict) else {}
    processing_time = instance.get("processing_time") if isinstance(instance.get("processing_time"), dict) else {}
    if not jobs:
        jobs = sorted((str(key) for key in processing_time.keys()), key=natural_label_sort_key)
    if not stages:
        stages = sorted(
            {str(stage) for stage_map in processing_time.values() if isinstance(stage_map, dict) for stage in stage_map.keys()},
            key=natural_label_sort_key,
        )
    schedule_records: dict[tuple[str, str], dict[str, Any]] = {}
    raw_schedule = payload.get("schedule")
    if isinstance(raw_schedule, list):
        for item in raw_schedule:
            if not isinstance(item, dict):
                continue
            job = extract_first_text_field(item, ("job", "job_id"))
            stage = extract_first_text_field(item, ("stage", "stage_id", "operation"))
            if job is None or stage is None:
                continue
            schedule_records[(job, stage)] = {
                "machine": extract_first_text_field(item, ("machine", "machine_id", "resource")),
                "start": extract_first_numeric_field(item, ("start", "start_time", "begin")),
                "finish": extract_first_numeric_field(item, ("finish", "completion", "completion_time", "end", "end_time")),
                "duration": extract_first_numeric_field(item, ("duration", "processing_time", "proc_time")),
            }
    elif isinstance(raw_schedule, dict):
        for job, stage_map in raw_schedule.items():
            if not isinstance(stage_map, dict):
                continue
            for stage, item in stage_map.items():
                if not isinstance(item, dict):
                    continue
                schedule_records[(str(job), str(stage))] = {
                    "machine": extract_first_text_field(item, ("machine", "machine_id", "resource")),
                    "start": extract_first_numeric_field(item, ("start", "start_time", "begin")),
                    "finish": extract_first_numeric_field(item, ("finish", "completion", "completion_time", "end", "end_time")),
                    "duration": extract_first_numeric_field(item, ("duration", "processing_time", "proc_time")),
                }
    machine_assignment = {}
    for key in ("machine_assignment", "assignment"):
        machine_assignment = normalize_nested_string_mapping(payload.get(key))
        if machine_assignment:
            break
    start_times = {}
    for key in ("start_time", "start_times"):
        start_times = normalize_nested_numeric_mapping(payload.get(key))
        if start_times:
            break
    finish_times = {}
    for key in ("completion_time", "completion_times", "finish_time", "finish_times"):
        finish_times = normalize_nested_numeric_mapping(payload.get(key))
        if finish_times:
            break
    feasible = True
    messages: list[str] = []
    machine_intervals: dict[str, list[tuple[float, float, str, str]]] = {}
    stage_intervals: dict[str, list[tuple[float, float, str]]] = {}
    job_stage_windows: dict[str, list[tuple[str, float, float]]] = {}
    computed_makespan = 0.0
    normalized_machine_assignment: dict[str, dict[str, str]] = {}
    for job in jobs:
        duration_map = processing_time.get(job) if isinstance(processing_time.get(job), dict) else {}
        for stage in stages:
            record = dict(schedule_records.get((job, stage), {}))
            machine = record.get("machine") or (machine_assignment.get(job) or {}).get(stage)
            start = record.get("start")
            if start is None:
                start = (start_times.get(job) or {}).get(stage)
            finish = record.get("finish")
            if finish is None:
                finish = (finish_times.get(job) or {}).get(stage)
            duration_expected = to_number(duration_map.get(stage)) if stage in duration_map else None
            duration = record.get("duration")
            if duration is None and start is not None and finish is not None:
                duration = float(finish) - float(start)
            if finish is None and start is not None and duration_expected is not None:
                finish = float(start) + float(duration_expected)
            if start is None and finish is not None and duration_expected is not None:
                start = float(finish) - float(duration_expected)
            if start is None or finish is None:
                feasible = False
                messages.append(f"Missing start/finish for {job}@{stage}")
                continue
            if start < -max(tolerance, 1e-6) or finish < start - max(tolerance, 1e-6):
                feasible = False
                messages.append(f"Invalid time interval for {job}@{stage}: start={start}, finish={finish}")
            stage_machines = machines_by_stage.get(stage)
            if machine is None and isinstance(stage_machines, list) and len(stage_machines) == 1:
                machine = str(stage_machines[0])
            if machine is not None and isinstance(stage_machines, list) and stage_machines and str(machine) not in [str(item) for item in stage_machines]:
                machine_index = to_number(machine)
                if machine_index is not None:
                    machine_position = int(machine_index)
                    if abs(float(machine_index) - machine_position) <= max(tolerance, 1e-6):
                        if 0 <= machine_position < len(stage_machines):
                            machine = str(stage_machines[machine_position])
                        elif 1 <= machine_position <= len(stage_machines):
                            machine = str(stage_machines[machine_position - 1])
            if machine is None and (not isinstance(stage_machines, list) or not stage_machines):
                feasible = False
                messages.append(f"Missing machine assignment for {job}@{stage}")
                continue
            if machine is not None and isinstance(stage_machines, list) and str(machine) not in [str(item) for item in stage_machines]:
                feasible = False
                messages.append(f"{job}@{stage} assigned to invalid machine {machine}")
            actual_duration = float(finish) - float(start)
            if duration_expected is not None and abs(actual_duration - float(duration_expected)) > max(tolerance, 1e-6):
                feasible = False
                messages.append(f"{job}@{stage} duration {actual_duration} does not match expected {duration_expected}")
            if machine is not None:
                normalized_machine_assignment.setdefault(job, {})[stage] = str(machine)
                machine_intervals.setdefault(str(machine), []).append((float(start), float(finish), job, stage))
            stage_intervals.setdefault(stage, []).append((float(start), float(finish), job))
            job_stage_windows.setdefault(job, []).append((stage, float(start), float(finish)))
            if finish > computed_makespan:
                computed_makespan = float(finish)
    for job, entries in job_stage_windows.items():
        order_lookup = {stage: index for index, stage in enumerate(stages)}
        ordered_entries = sorted(entries, key=lambda item: order_lookup.get(item[0], 10**6))
        for (_, _, prev_finish), (stage, start, _) in zip(ordered_entries, ordered_entries[1:]):
            if prev_finish - start > max(tolerance, 1e-6):
                feasible = False
                messages.append(f"Stage precedence violated for {job}@{stage}: previous finish={prev_finish}, start={start}")
    for machine, intervals in machine_intervals.items():
        ordered = sorted(intervals, key=lambda item: (item[0], item[1], natural_label_sort_key(item[2]), natural_label_sort_key(item[3])))
        for (_, prev_finish, prev_job, prev_stage), (start, _, job, stage) in zip(ordered, ordered[1:]):
            if prev_finish - start > max(tolerance, 1e-6):
                feasible = False
                messages.append(
                    f"Machine overlap on {machine}: {prev_job}@{prev_stage} finish={prev_finish} overlaps {job}@{stage} start={start}"
                )
    for stage, intervals in stage_intervals.items():
        stage_machines = machines_by_stage.get(stage)
        if not isinstance(stage_machines, list) or not stage_machines:
            continue
        assigned_count = sum(stage in assignment for assignment in normalized_machine_assignment.values())
        if 0 < assigned_count < len(intervals):
            feasible = False
            messages.append(f"Incomplete machine assignment on {stage}: provide all or none of the stage assignments")
            continue
        capacity = len(stage_machines)
        # Half-open intervals allow a machine to be reused at the finishing instant.
        epsilon = max(tolerance, 1e-6)
        events = []
        for start, finish, _ in intervals:
            if finish - start > epsilon:
                events.extend(((start, 1), (finish - epsilon, -1)))
        concurrent = 0
        for _, change in sorted(events):
            concurrent += change
            if concurrent > capacity:
                feasible = False
                messages.append(
                    f"Stage capacity exceeded on {stage}: concurrent_jobs={concurrent} machines={capacity}"
                )
                break
    reported_objective = extract_reported_objective(
        payload,
        ("objective_exact", "objective", "objective_value", "optimal_makespan", "makespan", "total_makespan"),
    )
    if reported_objective is not None and abs(float(reported_objective) - computed_makespan) > max(tolerance, 1e-6):
        feasible = False
        messages.append(f"Reported objective {reported_objective} does not match computed makespan {computed_makespan}")
    return {
        "parse_ok": True,
        "feasible_under_instance": feasible,
        "status": normalize_status(payload.get("status")),
        "objective_value": reported_objective if reported_objective is not None else computed_makespan,
        "machine_assignment": {job: normalized_machine_assignment.get(job, {}) for job in jobs},
        "details": messages[:10],
    }


def validate_energy_dispatch_unit_commitment_output(output: Any, instance: dict[str, Any], tolerance: float) -> dict[str, Any]:
    payload = unwrap_solution_dict(output)
    if payload is None:
        return {"parse_ok": False, "feasible_under_instance": False, "details": "stdout is not a dict"}
    sets_payload = instance.get("sets") if isinstance(instance.get("sets"), dict) else {}
    generators = [str(x) for x in sets_payload.get("generators", [])]
    periods = [str(x) for x in sets_payload.get("periods", [])]
    demand = instance.get("demand") if isinstance(instance.get("demand"), dict) else {}
    cost = instance.get("cost") if isinstance(instance.get("cost"), dict) else {}
    startup_cost = instance.get("startup_cost") if isinstance(instance.get("startup_cost"), dict) else {}
    shutdown_cost = instance.get("shutdown_cost") if isinstance(instance.get("shutdown_cost"), dict) else {}
    pmin = instance.get("pmin") if isinstance(instance.get("pmin"), dict) else {}
    pmax = instance.get("pmax") if isinstance(instance.get("pmax"), dict) else {}
    initial_status = instance.get("initial_status") if isinstance(instance.get("initial_status"), dict) else {}
    initial_output = instance.get("initial_output") if isinstance(instance.get("initial_output"), dict) else {}
    ramp_up = instance.get("ramp_up") if isinstance(instance.get("ramp_up"), dict) else {}
    ramp_down = instance.get("ramp_down") if isinstance(instance.get("ramp_down"), dict) else {}
    min_up = instance.get("min_up") if isinstance(instance.get("min_up"), dict) else {}
    min_down = instance.get("min_down") if isinstance(instance.get("min_down"), dict) else {}
    if not generators or not periods or not demand:
        return {"parse_ok": True, "feasible_under_instance": False, "details": "instance is missing generators, periods, or demand"}

    generation = extract_named_period_matrix(
        payload,
        keys=("generation", "dispatch", "power_output", "output", "outputs", "generation_schedule", "production", "production_schedule"),
        entity_names=generators,
        periods=periods,
        prefixes=("generation", "dispatch", "power", "power_output", "output", "outputs", "production", "prod", "p"),
    )
    commitment = extract_named_period_matrix(
        payload,
        keys=("commitment", "on_status", "unit_status", "online_status", "status_by_generator", "statuses"),
        entity_names=generators,
        periods=periods,
        prefixes=("commitment", "on_status", "unit_status", "online_status", "status", "statuses", "u"),
    )
    startup = extract_named_period_matrix(
        payload,
        keys=("startup", "startups", "startup_indicator", "startup_status", "start_indicator"),
        entity_names=generators,
        periods=periods,
        prefixes=("startup", "startups", "start_indicator", "z"),
    )
    shutdown = extract_named_period_matrix(
        payload,
        keys=("shutdown", "shutdowns", "shutdown_indicator", "shutdown_status", "stop_indicator"),
        entity_names=generators,
        periods=periods,
        prefixes=("shutdown", "shutdowns", "stop_indicator", "w"),
    )
    online_units_by_period = payload.get("online_units_by_period")
    if not commitment and isinstance(online_units_by_period, dict):
        rebuilt_commitment: dict[str, dict[str, float]] = {generator: {} for generator in generators}
        for period, generator_list in online_units_by_period.items():
            if str(period) not in periods or not isinstance(generator_list, list):
                continue
            generator_set = {str(item) for item in generator_list}
            for generator in generators:
                rebuilt_commitment[generator][str(period)] = 1.0 if generator in generator_set else 0.0
        if any(period_map for period_map in rebuilt_commitment.values()):
            commitment = rebuilt_commitment
    startup_periods = payload.get("startup_periods")
    if not startup and isinstance(startup_periods, dict):
        rebuilt_startup: dict[str, dict[str, float]] = {generator: {} for generator in generators}
        for generator, generator_periods in startup_periods.items():
            if str(generator) not in rebuilt_startup or not isinstance(generator_periods, list):
                continue
            period_set = {str(period) for period in generator_periods}
            for period in periods:
                rebuilt_startup[str(generator)][period] = 1.0 if period in period_set else 0.0
        if any(period_map for period_map in rebuilt_startup.values()):
            startup = rebuilt_startup

    if not generation or not commitment:
        return {
            "parse_ok": True,
            "feasible_under_instance": False,
            "details": "solution is missing generation or commitment matrices",
        }

    feasible = True
    messages: list[str] = []
    objective_value = 0.0
    normalized_commitment: dict[str, dict[str, int]] = {}
    inferred_startup: dict[str, dict[str, int]] = {}
    inferred_shutdown: dict[str, dict[str, int]] = {}
    for generator in generators:
        normalized_commitment[generator] = {}
        inferred_startup[generator] = {}
        inferred_shutdown[generator] = {}
        previous_commitment = int(round(to_number(initial_status.get(generator)) or 0.0))
        previous_output = float(to_number(initial_output.get(generator)) or 0.0)
        generator_cost = float(to_number(cost.get(generator)) or 0.0)
        generator_startup_cost = float(to_number(startup_cost.get(generator)) or 0.0)
        generator_shutdown_cost = float(to_number(shutdown_cost.get(generator)) or 0.0)
        generator_min = float(to_number(pmin.get(generator)) or 0.0)
        generator_max = float(to_number(pmax.get(generator)) or 0.0)
        generator_ramp_up = to_number(ramp_up.get(generator)) if ramp_up else None
        generator_ramp_down = to_number(ramp_down.get(generator)) if ramp_down else None
        for period in periods:
            generation_numeric = to_number((generation.get(generator) or {}).get(period))
            commitment_numeric = to_number((commitment.get(generator) or {}).get(period))
            if generation_numeric is None or commitment_numeric is None:
                feasible = False
                messages.append(f"Missing or non-finite generation/commitment for {generator}@{period}")
            generation_value = float(generation_numeric) if generation_numeric is not None else 0.0
            commitment_value = 1 if commitment_numeric is not None and commitment_numeric > 0.5 else 0
            if commitment_numeric is not None and abs(commitment_numeric - commitment_value) > tolerance:
                feasible = False
                messages.append(f"Non-binary commitment for {generator}@{period}: {commitment_numeric}")
            normalized_commitment[generator][period] = commitment_value
            if generation_value < -tolerance:
                feasible = False
                messages.append(f"Negative generation for {generator}@{period}: {generation_value}")
            if generation_value + tolerance < generator_min * commitment_value:
                feasible = False
                messages.append(
                    f"Generation below pmin for {generator}@{period}: generation={generation_value}, pmin={generator_min}, commitment={commitment_value}"
                )
            if generation_value - generator_max * commitment_value > tolerance:
                feasible = False
                messages.append(
                    f"Generation above pmax for {generator}@{period}: generation={generation_value}, pmax={generator_max}, commitment={commitment_value}"
                )
            inferred_start = 1 if commitment_value == 1 and previous_commitment == 0 else 0
            inferred_stop = 1 if commitment_value == 0 and previous_commitment == 1 else 0
            inferred_startup[generator][period] = inferred_start
            inferred_shutdown[generator][period] = inferred_stop
            for transition_name, transition, inferred in (
                ("Startup", startup, inferred_start), ("Shutdown", shutdown, inferred_stop)
            ):
                if not transition:
                    continue
                transition_value = to_number((transition.get(generator) or {}).get(period, 0.0))
                if transition_value is None or abs(transition_value - inferred) > tolerance:
                    feasible = False
                    messages.append(
                        f"{transition_name} inconsistency for {generator}@{period}: reported={transition_value}, inferred={inferred}"
                    )
            if generator_ramp_up is not None and generation_value - previous_output - generator_ramp_up > tolerance:
                feasible = False
                messages.append(
                    f"Ramp-up violated for {generator}@{period}: current={generation_value}, previous={previous_output}, limit={generator_ramp_up}"
                )
            if generator_ramp_down is not None and previous_output - generation_value - generator_ramp_down > tolerance:
                feasible = False
                messages.append(
                    f"Ramp-down violated for {generator}@{period}: current={generation_value}, previous={previous_output}, limit={generator_ramp_down}"
                )
            objective_value += (
                generator_cost * generation_value
                + generator_startup_cost * inferred_start
                + generator_shutdown_cost * inferred_stop
            )
            previous_commitment = commitment_value
            previous_output = generation_value

        required_up = int(to_number(min_up.get(generator)) or 0.0) if min_up else 0
        if required_up > 1:
            for index, period in enumerate(periods):
                if inferred_startup[generator].get(period, 0) != 1:
                    continue
                horizon = periods[index : min(len(periods), index + required_up)]
                if any(normalized_commitment[generator].get(candidate, 0) != 1 for candidate in horizon):
                    feasible = False
                    messages.append(f"Minimum up-time violated for {generator} starting at {period}")
                    break
        required_down = int(to_number(min_down.get(generator)) or 0.0) if min_down else 0
        if required_down > 1:
            previous_commitment = int(round(to_number(initial_status.get(generator)) or 0.0))
            for index, period in enumerate(periods):
                current_commitment = normalized_commitment[generator].get(period, 0)
                if previous_commitment == 1 and current_commitment == 0:
                    horizon = periods[index : min(len(periods), index + required_down)]
                    if any(normalized_commitment[generator].get(candidate, 0) != 0 for candidate in horizon):
                        feasible = False
                        messages.append(f"Minimum down-time violated for {generator} shutting down at {period}")
                        break
                previous_commitment = current_commitment

    for period in periods:
        period_total = sum(float(to_number((generation.get(generator) or {}).get(period)) or 0.0) for generator in generators)
        target = float(to_number(demand.get(period)) or 0.0)
        if abs(period_total - target) > tolerance:
            feasible = False
            messages.append(f"Demand balance violated at {period}: generation={period_total}, demand={target}")

    reported_objective = extract_reported_objective(payload, ("objective_exact", "objective", "objective_value", "total_cost"))
    if reported_objective is not None and abs(reported_objective - objective_value) > tolerance:
        feasible = False
        messages.append(f"Reported objective {reported_objective} does not match computed objective {objective_value}")

    return {
        "parse_ok": True,
        "feasible_under_instance": feasible,
        "status": normalize_status(payload.get("status")),
        "objective_value": reported_objective if reported_objective is not None else objective_value,
        "generation": generation,
        "commitment": normalized_commitment,
        "startup": inferred_startup,
        "shutdown": inferred_shutdown,
        "details": messages[:10],
    }


def validate_inventory_routing_problem_output(output: Any, instance: dict[str, Any], tolerance: float) -> dict[str, Any]:
    payload = unwrap_solution_dict(output)
    if payload is None:
        return {"parse_ok": False, "feasible_under_instance": False, "details": "stdout is not a dict"}
    sets_payload = instance.get("sets") if isinstance(instance.get("sets"), dict) else {}
    periods = [str(x) for x in sets_payload.get("periods", [])]
    customers = [str(x) for x in sets_payload.get("customers", [])]
    nodes = [str(x) for x in sets_payload.get("nodes", [])]
    vehicles = [str(x) for x in sets_payload.get("vehicles", [])]
    if not periods or not customers:
        return {"parse_ok": True, "feasible_under_instance": False, "details": "instance is missing periods or customers"}
    demands = instance.get("demands") if isinstance(instance.get("demands"), dict) else {}
    initial_inventory = instance.get("initial_inventory") if isinstance(instance.get("initial_inventory"), dict) else {}
    inventory_capacity = instance.get("inventory_capacity") if isinstance(instance.get("inventory_capacity"), dict) else {}
    holding_cost = instance.get("holding_cost") if isinstance(instance.get("holding_cost"), dict) else {}
    distance_matrix = instance.get("distance_matrix") if isinstance(instance.get("distance_matrix"), dict) else {}
    fixed_dispatch_cost = float(to_number(instance.get("fixed_dispatch_cost")) or 0.0)
    fixed_dispatch_cost_by_vehicle = (
        instance.get("fixed_dispatch_cost_by_vehicle") if isinstance(instance.get("fixed_dispatch_cost_by_vehicle"), dict) else {}
    )
    default_vehicle_capacity = to_number(instance.get("vehicle_capacity"))
    vehicle_capacity_by_vehicle = (
        instance.get("vehicle_capacity_by_vehicle") if isinstance(instance.get("vehicle_capacity_by_vehicle"), dict) else {}
    )
    vehicle_names = [str(vehicle) for vehicle in vehicles] or ["V1"]
    default_vehicle = vehicle_names[0]
    route_node_set = {str(node) for node in nodes} if nodes else set()
    route_node_set.add("Depot")
    route_node_set.update(customers)

    deliveries = extract_named_period_matrix(
        payload,
        keys=("deliveries", "delivery", "shipment", "shipments", "delivered_quantity"),
        entity_names=customers,
        periods=periods,
        prefixes=("deliveries", "delivery", "shipment", "shipments", "x", "y"),
    )
    ending_inventory = extract_named_period_matrix(
        payload,
        keys=(
            "ending_inventory",
            "inventory_end",
            "ending_inventory_by_customer",
            "inventory_levels",
            "inventory",
            "end_inventory",
            "end_inventories",
            "end_inventory_by_customer",
            "end_inventories_by_customer",
        ),
        entity_names=customers,
        periods=periods,
        prefixes=("ending_inventory", "inventory_end", "inventory", "end_inventory", "end_inventories", "I"),
    )
    dispatch_by_period = extract_period_indicator_mapping(
        payload,
        periods=periods,
        indicator_keys=("dispatch_by_period", "dispatch_indicator_by_period", "dispatches", "vehicle_dispatch"),
        list_keys=("dispatch_periods",),
        prefixes=("dispatch", "dispatches", "vehicle_dispatch", "y"),
    )
    dispatch_by_vehicle_period = extract_vehicle_period_indicator_mapping(payload, vehicles=vehicles, periods=periods)
    route_arcs = extract_period_route_arcs(payload, periods=periods, vehicles=vehicles, nodes=nodes)
    raw_plan = payload.get("plan")
    if isinstance(raw_plan, dict):
        fallback_deliveries = {customer: {} for customer in customers}
        fallback_ending_inventory = {customer: {} for customer in customers}
        fallback_dispatch_by_period: dict[str, int] = {}
        fallback_dispatch_by_vehicle_period: dict[str, dict[str, int]] = {default_vehicle: {}}
        fallback_route_arcs: dict[str, dict[str, list[tuple[str, str]]]] = {default_vehicle: {}}
        for period in periods:
            period_payload = raw_plan.get(period)
            if not isinstance(period_payload, dict):
                continue
            raw_deliveries = period_payload.get("deliveries")
            if isinstance(raw_deliveries, dict):
                for customer in customers:
                    numeric = to_number(raw_deliveries.get(customer))
                    if numeric is not None:
                        fallback_deliveries[customer][period] = float(numeric)
            raw_inventory = period_payload.get("end_inventory")
            if isinstance(raw_inventory, dict):
                for customer in customers:
                    numeric = to_number(raw_inventory.get(customer))
                    if numeric is not None:
                        fallback_ending_inventory[customer][period] = float(numeric)
            dispatch_numeric = to_number(period_payload.get("dispatch"))
            if dispatch_numeric is not None:
                dispatch_indicator = 1 if dispatch_numeric > 0.5 else 0
            else:
                dispatch_indicator = 1 if isinstance(period_payload.get("route_order"), list) and period_payload.get("route_order") else 0
                if dispatch_indicator == 0:
                    delivered_total = sum(
                        float(to_number((fallback_deliveries.get(customer) or {}).get(period)) or 0.0) for customer in customers
                    )
                    dispatch_indicator = 1 if delivered_total > tolerance else 0
            fallback_dispatch_by_period[period] = dispatch_indicator
            fallback_dispatch_by_vehicle_period[default_vehicle][period] = dispatch_indicator

            arcs: list[tuple[str, str]] = []
            raw_used_arcs = period_payload.get("used_arcs")
            if isinstance(raw_used_arcs, dict):
                for arc_token, arc_value in raw_used_arcs.items():
                    numeric = to_number(arc_value)
                    if numeric is not None and numeric <= 0.5:
                        continue
                    parsed = parse_route_arc_item(str(arc_token), nodes=route_node_set)
                    if parsed is not None:
                        arcs.append(parsed)
            elif isinstance(raw_used_arcs, list):
                for item in raw_used_arcs:
                    parsed = parse_route_arc_item(item, nodes=route_node_set)
                    if parsed is not None:
                        arcs.append(parsed)
            if not arcs:
                route_order = period_payload.get("route_order")
                if isinstance(route_order, list) and route_order:
                    route_path = ["Depot"] + [str(node) for node in route_order] + ["Depot"]
                    arcs = coerce_route_sequence_to_arcs(route_path, nodes=route_node_set)
            if arcs:
                fallback_route_arcs[default_vehicle][period] = arcs

        if not deliveries and any(period_map for period_map in fallback_deliveries.values()):
            deliveries = {customer: period_map for customer, period_map in fallback_deliveries.items() if period_map}
        if not ending_inventory and any(period_map for period_map in fallback_ending_inventory.values()):
            ending_inventory = {customer: period_map for customer, period_map in fallback_ending_inventory.items() if period_map}
        if not dispatch_by_period and fallback_dispatch_by_period:
            dispatch_by_period = fallback_dispatch_by_period
        if not dispatch_by_vehicle_period and fallback_dispatch_by_vehicle_period.get(default_vehicle):
            dispatch_by_vehicle_period = fallback_dispatch_by_vehicle_period
        if not route_arcs and fallback_route_arcs.get(default_vehicle):
            route_arcs = fallback_route_arcs
    if route_arcs:
        cleaned_route_arcs: dict[str, dict[str, list[tuple[str, str]]]] = {}
        for vehicle, period_map in route_arcs.items():
            if not isinstance(period_map, dict):
                continue
            for period, arcs in period_map.items():
                if not isinstance(arcs, list):
                    continue
                filtered = [(str(tail), str(head)) for tail, head in arcs if str(tail) != str(head)]
                if filtered:
                    cleaned_route_arcs.setdefault(str(vehicle), {})[str(period)] = filtered
        route_arcs = cleaned_route_arcs
    if not deliveries:
        return {"parse_ok": True, "feasible_under_instance": False, "details": "solution is missing deliveries"}

    feasible = True
    messages: list[str] = []
    objective_value = 0.0
    if not dispatch_by_vehicle_period:
        if dispatch_by_period:
            dispatch_by_vehicle_period = {
                default_vehicle: {period: dispatch_by_period.get(period, 0) for period in periods}
            }
        else:
            inferred = {period: 0 for period in periods}
            for period in periods:
                delivered = sum(float(to_number((deliveries.get(customer) or {}).get(period)) or 0.0) for customer in customers)
                if delivered > tolerance:
                    inferred[period] = 1
            dispatch_by_vehicle_period = {default_vehicle: inferred}

    visited_customers_by_period: dict[str, set[str]] = {period: set() for period in periods}
    for vehicle, period_map in route_arcs.items():
        for period, arcs in period_map.items():
            if not isinstance(arcs, list):
                continue
            previous_head = None
            for index, arc in enumerate(arcs):
                if not isinstance(arc, tuple) or len(arc) != 2:
                    feasible = False
                    messages.append(f"Malformed route arc for {vehicle}@{period}: {arc}")
                    continue
                tail, head = str(arc[0]), str(arc[1])
                if nodes and (tail not in nodes or head not in nodes):
                    feasible = False
                    messages.append(f"Unknown route arc for {vehicle}@{period}: {tail}->{head}")
                if tail != "Depot":
                    visited_customers_by_period.setdefault(period, set()).add(tail)
                if head != "Depot":
                    visited_customers_by_period.setdefault(period, set()).add(head)
                if index == 0 and tail != "Depot":
                    feasible = False
                    messages.append(f"Route for {vehicle}@{period} does not start at Depot")
                previous_head = head if previous_head is None else previous_head
                if index > 0:
                    prior_head = str(arcs[index - 1][1])
                    if tail != prior_head:
                        feasible = False
                        messages.append(f"Route continuity violated for {vehicle}@{period}: {prior_head}!={tail}")
                objective_value += float(to_number((distance_matrix.get(tail) or {}).get(head)) or 0.0)
            if arcs and str(arcs[-1][1]) != "Depot":
                feasible = False
                messages.append(f"Route for {vehicle}@{period} does not end at Depot")

    computed_inventory: dict[str, dict[str, float]] = {customer: {} for customer in customers}
    for customer in customers:
        previous_inventory = float(to_number(initial_inventory.get(customer)) or 0.0)
        capacity = to_number(inventory_capacity.get(customer)) if inventory_capacity else None
        customer_holding_cost = float(to_number(holding_cost.get(customer)) or 0.0)
        for period in periods:
            delivery_value = float(to_number((deliveries.get(customer) or {}).get(period)) or 0.0)
            demand_value = float(to_number((demands.get(customer) or {}).get(period)) or 0.0)
            if delivery_value < -tolerance:
                feasible = False
                messages.append(f"Negative delivery for {customer}@{period}: {delivery_value}")
            current_inventory = previous_inventory + delivery_value - demand_value
            computed_inventory[customer][period] = current_inventory
            if current_inventory < -tolerance:
                feasible = False
                messages.append(f"Negative ending inventory for {customer}@{period}: {current_inventory}")
            if capacity is not None and current_inventory - capacity > tolerance:
                feasible = False
                messages.append(f"Inventory capacity exceeded for {customer}@{period}: inv={current_inventory}, cap={capacity}")
            if ending_inventory:
                reported_inventory = to_number((ending_inventory.get(customer) or {}).get(period))
                if reported_inventory is not None and abs(reported_inventory - current_inventory) > tolerance:
                    feasible = False
                    messages.append(
                        f"Inventory recursion mismatch for {customer}@{period}: reported={reported_inventory}, computed={current_inventory}"
                    )
            objective_value += customer_holding_cost * max(current_inventory, 0.0)
            if route_arcs and delivery_value > tolerance and customer not in visited_customers_by_period.get(period, set()):
                feasible = False
                messages.append(f"Positive delivery without route visit for {customer}@{period}")
            previous_inventory = current_inventory

    for period in periods:
        used_vehicle_count = 0
        period_capacity = 0.0
        for vehicle in vehicle_names:
            indicator = 0
            if vehicle in dispatch_by_vehicle_period:
                indicator = dispatch_by_vehicle_period[vehicle].get(period, 0)
            if indicator > 0:
                used_vehicle_count += 1
                period_capacity += float(
                    to_number(vehicle_capacity_by_vehicle.get(vehicle))
                    if vehicle_capacity_by_vehicle and to_number(vehicle_capacity_by_vehicle.get(vehicle)) is not None
                    else default_vehicle_capacity
                    or 0.0
                )
                objective_value += float(to_number(fixed_dispatch_cost_by_vehicle.get(vehicle)) or fixed_dispatch_cost)
        period_delivery_total = sum(float(to_number((deliveries.get(customer) or {}).get(period)) or 0.0) for customer in customers)
        if used_vehicle_count == 0 and period_delivery_total > tolerance:
            feasible = False
            messages.append(f"Positive delivery but no dispatched vehicle at {period}")
        if used_vehicle_count > 0 and period_capacity > 0 and period_delivery_total - period_capacity > tolerance:
            feasible = False
            messages.append(f"Vehicle capacity exceeded at {period}: delivered={period_delivery_total}, cap={period_capacity}")
        if route_arcs:
            routed_vehicle_count = sum(1 for vehicle in vehicle_names if route_arcs.get(vehicle, {}).get(period))
            if routed_vehicle_count != used_vehicle_count:
                feasible = False
                messages.append(
                    f"Dispatch/route mismatch at {period}: dispatched={used_vehicle_count}, routed={routed_vehicle_count}"
                )

    reported_objective = extract_reported_objective(payload, ("objective_exact", "objective", "objective_value", "total_cost"))
    if reported_objective is not None and abs(reported_objective - objective_value) > max(tolerance, 1e-2):
        feasible = False
        messages.append(f"Reported objective {reported_objective} does not match computed objective {objective_value}")

    return {
        "parse_ok": True,
        "feasible_under_instance": feasible,
        "status": normalize_status(payload.get("status")),
        "objective_value": reported_objective if reported_objective is not None else objective_value,
        "deliveries": deliveries,
        "ending_inventory": computed_inventory,
        "details": messages[:10],
    }


def validate_lot_sizing_production_planning_output(output: Any, instance: dict[str, Any], tolerance: float) -> dict[str, Any]:
    payload = unwrap_solution_dict(output)
    if payload is None:
        return {"parse_ok": False, "feasible_under_instance": False, "details": "stdout is not a dict"}
    sets_payload = instance.get("sets") if isinstance(instance.get("sets"), dict) else {}
    products = [str(x) for x in sets_payload.get("products", [])]
    periods = [str(x) for x in sets_payload.get("periods", [])]
    if not products or not periods:
        return {"parse_ok": True, "feasible_under_instance": False, "details": "instance is missing products or periods"}
    demand = instance.get("demand") if isinstance(instance.get("demand"), dict) else {}
    production_cost = instance.get("production_cost") if isinstance(instance.get("production_cost"), dict) else {}
    holding_cost = instance.get("holding_cost") if isinstance(instance.get("holding_cost"), dict) else {}
    setup_cost = instance.get("setup_cost") if isinstance(instance.get("setup_cost"), dict) else {}
    initial_inventory = instance.get("initial_inventory") if isinstance(instance.get("initial_inventory"), dict) else {}
    capacity = instance.get("capacity") if isinstance(instance.get("capacity"), dict) else {}
    big_m = instance.get("big_m") if isinstance(instance.get("big_m"), dict) else {}

    production = extract_named_period_matrix(
        payload,
        keys=("production", "production_plan", "production_quantity", "production_schedule"),
        entity_names=products,
        periods=periods,
        prefixes=("production", "prod", "x"),
    )
    inventory = extract_named_period_matrix(
        payload,
        keys=("inventory", "ending_inventory", "inventory_levels", "inventory_end"),
        entity_names=products,
        periods=periods,
        prefixes=("inventory", "ending_inventory", "inv", "I"),
    )
    setup = extract_named_period_matrix(
        payload,
        keys=("setup", "setup_indicator", "setup_status", "setup_binary"),
        entity_names=products,
        periods=periods,
        prefixes=("setup", "setup_indicator", "y", "z"),
    )
    if not production:
        return {"parse_ok": True, "feasible_under_instance": False, "details": "solution is missing production"}

    feasible = True
    messages: list[str] = []
    objective_value = 0.0
    computed_inventory: dict[str, dict[str, float]] = {product: {} for product in products}
    computed_setup: dict[str, dict[str, int]] = {product: {} for product in products}
    capacity_usage: dict[str, float] = {period: 0.0 for period in periods}

    for product in products:
        previous_inventory = float(to_number(initial_inventory.get(product)) or 0.0)
        product_big_m = float(to_number(big_m.get(product)) or 0.0)
        for period in periods:
            production_value = float(to_number((production.get(product) or {}).get(period)) or 0.0)
            if production_value < -tolerance:
                feasible = False
                messages.append(f"Negative production for {product}@{period}: {production_value}")
            demand_value = float(to_number((demand.get(product) or {}).get(period)) or 0.0)
            current_inventory = previous_inventory + production_value - demand_value
            computed_inventory[product][period] = current_inventory
            if current_inventory < -tolerance:
                feasible = False
                messages.append(f"Negative inventory for {product}@{period}: {current_inventory}")
            reported_inventory = to_number((inventory.get(product) or {}).get(period))
            if reported_inventory is not None and abs(float(reported_inventory) - current_inventory) > tolerance:
                feasible = False
                messages.append(
                    f"Inventory recursion mismatch for {product}@{period}: reported={reported_inventory}, computed={current_inventory}"
                )
            inferred_setup = 1 if production_value > tolerance else 0
            computed_setup[product][period] = inferred_setup
            reported_setup = to_number((setup.get(product) or {}).get(period))
            if reported_setup is not None and int(round(float(reported_setup))) != inferred_setup:
                feasible = False
                messages.append(
                    f"Setup mismatch for {product}@{period}: reported={reported_setup}, inferred={inferred_setup}"
                )
            if product_big_m > 0.0 and production_value - product_big_m * inferred_setup > tolerance:
                feasible = False
                messages.append(
                    f"Big-M setup linkage violated for {product}@{period}: production={production_value}, big_m={product_big_m}, setup={inferred_setup}"
                )
            objective_value += production_value * float(to_number((production_cost.get(product) or {}).get(period)) or 0.0)
            objective_value += max(current_inventory, 0.0) * float(to_number((holding_cost.get(product) or {}).get(period)) or 0.0)
            objective_value += inferred_setup * float(to_number((setup_cost.get(product) or {}).get(period)) or 0.0)
            capacity_usage[period] += production_value
            previous_inventory = current_inventory

    for period in periods:
        period_capacity = to_number(capacity.get(period))
        if period_capacity is not None and capacity_usage.get(period, 0.0) - float(period_capacity) > tolerance:
            feasible = False
            messages.append(
                f"Capacity exceeded at {period}: usage={capacity_usage.get(period, 0.0)}, cap={float(period_capacity)}"
            )

    reported_objective = extract_reported_objective(payload, ("objective_exact", "objective", "objective_value", "total_cost"))
    effective_tolerance = max(tolerance, 1e-2)
    if reported_objective is not None and abs(float(reported_objective) - objective_value) > effective_tolerance:
        feasible = False
        messages.append(f"Reported objective {reported_objective} does not match computed objective {objective_value}")

    return {
        "parse_ok": True,
        "feasible_under_instance": feasible,
        "status": normalize_status(payload.get("status")),
        "objective_value": reported_objective if reported_objective is not None else objective_value,
        "production": production,
        "inventory": computed_inventory,
        "setup": computed_setup,
        "capacity_usage": capacity_usage,
        "details": messages[:10],
    }


def validate_workforce_planning_shift_scheduling_output(output: Any, instance: dict[str, Any], tolerance: float) -> dict[str, Any]:
    payload = unwrap_solution_dict(output)
    if payload is None:
        return {"parse_ok": False, "feasible_under_instance": False, "details": "stdout is not a dict"}
    sets_payload = instance.get("sets") if isinstance(instance.get("sets"), dict) else {}
    workers = [str(x) for x in sets_payload.get("workers", [])]
    days = [str(x) for x in sets_payload.get("days", [])]
    shifts = [str(x) for x in sets_payload.get("shifts", [])]
    if not workers or not days or not shifts:
        return {"parse_ok": True, "feasible_under_instance": False, "details": "instance is missing workers, days, or shifts"}
    allowed_shift_labels = set(shifts) | {"OFF", "REST", "NONE", "-"}

    def normalize_shift_label(raw_value: Any) -> str | None:
        normalized = normalize_categorical_label(raw_value, allowed_labels=allowed_shift_labels)
        if normalized in {"REST", "NONE", "-"}:
            return "OFF"
        return normalized

    worker_schedule = extract_named_period_label_matrix(
        payload,
        keys=("worker_schedule", "schedule", "schedule_by_worker", "assignment"),
        entity_names=workers,
        periods=days,
        prefixes=("worker_schedule", "schedule", "assignment", "shift"),
        allowed_labels=allowed_shift_labels,
    )
    if not worker_schedule:
        assignment_by_day = payload.get("assignments_by_day")
        if not isinstance(assignment_by_day, dict):
            assignment_by_day = payload.get("assignments")
        if isinstance(assignment_by_day, dict):
            rebuilt: dict[str, dict[str, str]] = {worker: {} for worker in workers}
            for day, shift_map in assignment_by_day.items():
                day_name = str(day)
                if day_name not in days or not isinstance(shift_map, dict):
                    continue
                for shift, assigned_workers in shift_map.items():
                    shift_name = normalize_shift_label(shift)
                    if shift_name is None or shift_name == "OFF" or not isinstance(assigned_workers, list):
                        continue
                    for worker in assigned_workers:
                        worker_name = str(worker)
                        if worker_name in rebuilt:
                            rebuilt[worker_name][day_name] = shift_name
            if any(schedule for schedule in rebuilt.values()):
                worker_schedule = rebuilt
    if not worker_schedule:
        return {"parse_ok": True, "feasible_under_instance": False, "details": "solution is missing worker schedule"}

    availability_code = instance.get("availability_code") if isinstance(instance.get("availability_code"), dict) else {}
    availability_legend = instance.get("availability_legend") if isinstance(instance.get("availability_legend"), dict) else {}
    demand = instance.get("demand") if isinstance(instance.get("demand"), dict) else {}
    shift_cost = instance.get("shift_cost") if isinstance(instance.get("shift_cost"), dict) else {}
    regular_shift_limit = instance.get("regular_shift_limit") if isinstance(instance.get("regular_shift_limit"), dict) else {}
    overtime_cost = instance.get("overtime_cost") if isinstance(instance.get("overtime_cost"), dict) else {}
    max_night_shifts = instance.get("max_night_shifts") if isinstance(instance.get("max_night_shifts"), dict) else {}
    max_consecutive_days = instance.get("max_consecutive_days") if isinstance(instance.get("max_consecutive_days"), dict) else {}
    constraint_flags = instance.get("constraint_flags") if isinstance(instance.get("constraint_flags"), dict) else {}

    feasible = True
    messages: list[str] = []
    objective_value = 0.0
    assignment_cost = 0.0
    overtime_total = 0.0
    coverage_realized: dict[str, dict[str, int]] = {day: {shift: 0 for shift in shifts} for day in days}
    worker_total_assignments: dict[str, int] = {worker: 0 for worker in workers}
    worker_night_assignments: dict[str, int] = {worker: 0 for worker in workers}

    for worker in workers:
        assigned_run = 0
        max_run = int(to_number(max_consecutive_days.get(worker)) or 0.0) if max_consecutive_days else 0
        for day in days:
            shift_name = normalize_shift_label((worker_schedule.get(worker) or {}).get(day)) or "OFF"
            if shift_name == "OFF":
                assigned_today = 0
            else:
                assigned_today = 1
                availability_token = str((availability_code.get(worker) or {}).get(day, "OFF"))
                allowed_shifts = availability_legend.get(availability_token, [])
                if shift_name not in [str(item) for item in allowed_shifts]:
                    feasible = False
                    messages.append(f"Availability violated for {worker}@{day}: assigned={shift_name}, code={availability_token}")
                coverage_realized[day][shift_name] += 1
                worker_total_assignments[worker] += 1
                if shift_name == "N":
                    worker_night_assignments[worker] += 1
                shift_cost_value = float(to_number((shift_cost.get(worker) or {}).get(shift_name)) or 0.0)
                assignment_cost += shift_cost_value
                objective_value += shift_cost_value
            if assigned_today:
                assigned_run += 1
            else:
                assigned_run = 0
            if constraint_flags.get("consecutive") and max_run > 0 and assigned_run > max_run:
                feasible = False
                messages.append(f"Max consecutive days violated for {worker} at {day}: run={assigned_run}, limit={max_run}")

    for day in days:
        for shift in shifts:
            required = int(to_number((demand.get(day) or {}).get(shift)) or 0.0)
            realized = coverage_realized.get(day, {}).get(shift, 0)
            if realized < required:
                feasible = False
                messages.append(f"Coverage shortfall at {day}/{shift}: realized={realized}, demand={required}")

    if constraint_flags.get("night_limit"):
        for worker in workers:
            limit = to_number(max_night_shifts.get(worker))
            if limit is not None and worker_night_assignments.get(worker, 0) - int(limit) > 0:
                feasible = False
                messages.append(
                    f"Night-shift limit violated for {worker}: assigned={worker_night_assignments.get(worker, 0)}, limit={int(limit)}"
                )

    for worker in workers:
        limit = to_number(regular_shift_limit.get(worker))
        if limit is None:
            continue
        overtime_units = max(0, worker_total_assignments.get(worker, 0) - int(limit))
        overtime_cost_value = float(to_number(overtime_cost.get(worker)) or 0.0)
        overtime_total += overtime_units * overtime_cost_value
        objective_value += overtime_units * overtime_cost_value

    reported_objective = extract_reported_objective(
        payload,
        ("objective_exact", "objective", "objective_value", "total_cost", "assignment_cost"),
    )
    effective_tolerance = max(tolerance, 1e-2)
    if reported_objective is not None and abs(float(reported_objective) - objective_value) > effective_tolerance:
        feasible = False
        messages.append(f"Reported objective {reported_objective} does not match computed objective {objective_value}")

    return {
        "parse_ok": True,
        "feasible_under_instance": feasible,
        "status": normalize_status(payload.get("status")),
        "objective_value": reported_objective if reported_objective is not None else objective_value,
        "assignment_cost": assignment_cost,
        "overtime_cost": overtime_total,
        "worker_schedule": {
            worker: {day: normalize_shift_label((worker_schedule.get(worker) or {}).get(day)) or "OFF" for day in days}
            for worker in workers
        },
        "coverage_realized": coverage_realized,
        "worker_total_assignments": worker_total_assignments,
        "details": messages[:10],
    }


def effective_numeric_tolerance(problem_type: str, base_tolerance: float) -> float:
    lowered = problem_type.lower()
    if (
        "facility_location" in lowered
        or "facility location" in lowered
        or "p_median_center" in lowered
        or "p-median" in lowered
        or "p_median" in lowered
        or "p_center" in lowered
        or "p-center" in lowered
    ):
        return max(base_tolerance, 1e-3)
    return base_tolerance


def validate_output_against_instance(problem_type: str, output: Any, instance: dict[str, Any], tolerance: float) -> dict[str, Any]:
    tolerance = effective_numeric_tolerance(problem_type, tolerance)
    lowered = problem_type.lower()
    if has_nonfinite_number(output):
        return {"parse_ok": False, "feasible_under_instance": False, "details": "Non-finite numeric output"}
    if "color" in lowered:
        return validate_graph_coloring_output(output, instance, tolerance)
    if "lot_sizing_production_planning" in lowered or "lot sizing" in lowered:
        return validate_lot_sizing_production_planning_output(output, instance, tolerance)
    if "workforce_planning_shift_scheduling" in lowered or "shift scheduling" in lowered:
        return validate_workforce_planning_shift_scheduling_output(output, instance, tolerance)
    if "energy_dispatch_unit_commitment" in lowered or "unit_commitment" in lowered:
        return validate_energy_dispatch_unit_commitment_output(output, instance, tolerance)
    if "inventory_routing_problem" in lowered or "inventory routing" in lowered:
        return validate_inventory_routing_problem_output(output, instance, tolerance)
    if "job_shop_scheduling" in lowered or "job shop" in lowered or "jssp" in lowered:
        return validate_job_shop_scheduling_output(output, instance, tolerance)
    if "parallel_machine_scheduling" in lowered or "parallel machine" in lowered:
        return validate_parallel_machine_scheduling_output(output, instance, tolerance)
    if "rcpsp" in lowered or "resource_constrained_project_scheduling" in lowered:
        return validate_rcpsp_output(output, instance, tolerance)
    if "flexible_hybrid_flow-shop_scheduling" in lowered or "flexible_hybrid_flow_shop_scheduling" in lowered or "hybrid flow-shop" in lowered:
        return validate_flexible_hybrid_flow_shop_scheduling_output(output, instance, tolerance)
    if "capacitated_network_design" in lowered or "network_design" in lowered:
        return validate_capacitated_network_design_output(output, instance, tolerance)
    if "minimum_cost_flow" in lowered:
        return validate_minimum_cost_flow_output(output, instance, tolerance)
    if "resource_constrained_shortest_path" in lowered or "rcsp" in lowered:
        return validate_resource_constrained_shortest_path_output(output, instance, tolerance)
    if "time_expanded_multi_period_network_flow" in lowered or "time-expanded_multi-period_network_flow" in lowered:
        return validate_time_expanded_multi_period_network_flow_output(output, instance, tolerance)
    if "flow" in lowered:
        return validate_max_flow_output(output, instance, tolerance)
    if "bipartite_assignment" in lowered or "bipartite assignment" in lowered or lowered == "assignment" or "matching" in lowered:
        return validate_bipartite_assignment_output(output, instance, tolerance)
    if "facility_location" in lowered or "facility location" in lowered:
        return validate_facility_location_output(output, instance, tolerance)
    if "generalized_assignment_problem" in lowered or "generalized assignment" in lowered:
        return validate_generalized_assignment_output(output, instance, tolerance)
    if "p_median_center" in lowered or "p-median" in lowered or "p_median" in lowered or "p_center" in lowered or "p-center" in lowered:
        return validate_p_median_center_output(output, instance, tolerance)
    if "heterogeneous_fleet_vrp" in lowered or "heterogeneous fleet" in lowered:
        return validate_heterogeneous_fleet_vrp_output(output, instance, tolerance)
    if "vehicle_routing_problem" in lowered or "vehicle routing" in lowered:
        return validate_vehicle_routing_problem_output(output, instance, tolerance)
    if "tsp_with_time_windows" in lowered or "traveling_salesman_problem_with_time_windows" in lowered or "time windows" in lowered:
        return validate_tsp_with_time_windows_output(output, instance, tolerance)
    if "traveling_salesman_problem" in lowered or "travel_salesman_problem" in lowered or "salesman problem" in lowered:
        return validate_traveling_salesman_problem_output(output, instance, tolerance)
    if "logical_constraint" in lowered or "logical constraint" in lowered or "satisfaction" in lowered:
        return validate_logical_constraint_satisfaction_output(output, instance)
    if "knapsack" in lowered:
        return validate_multi_dim_knapsack_output(output, instance, tolerance)
    if "set_covering_partitioning" in lowered or "set covering" in lowered or "set partitioning" in lowered:
        return validate_set_covering_partitioning_output(output, instance, tolerance)
    if "set_packing" in lowered or "set packing" in lowered:
        return validate_set_packing_output(output, instance, tolerance)
    return {"parse_ok": output is not None, "feasible_under_instance": None, "details": "No validator for this problem type"}


def compare_solution_to_ground_truth(
    problem_type: str,
    output: Any,
    solution_ref: dict[str, Any],
    instance: dict[str, Any],
    tolerance: float,
) -> dict[str, Any]:
    tolerance = effective_numeric_tolerance(problem_type, tolerance)
    lowered = problem_type.lower()
    if output is None or not isinstance(output, dict):
        return {"correct": False, "reason": "stdout is missing or not a dict"}
    if has_nonfinite_number(output):
        return {"correct": False, "reason": "Non-finite numeric output"}
    if "color" in lowered:
        validation = validate_graph_coloring_output(output, instance, tolerance)
        status = validation.get("status")
        gt_status = normalize_status(solution_ref.get("status"))
        if gt_status == "infeasible":
            return {"correct": status == gt_status, "reason": f"status={status} gt={gt_status}"}
        if gt_status == "optimal":
            gt_value = to_number(solution_ref.get("objective_value") if "objective_value" in solution_ref else solution_ref.get("chromatic_number"))
            objective_value = validation.get("objective_value")
            correct = validation.get("feasible_under_instance") is True and objective_value is not None and gt_value is not None and abs(float(objective_value) - float(gt_value)) <= tolerance
            return {"correct": correct, "reason": f"objective={objective_value} gt={gt_value}", "validation": validation}
        return {
            "correct": validation.get("feasible_under_instance") is True,
            "reason": f"status={status} gt={gt_status} feasible={validation.get('feasible_under_instance')}",
        }
    if "lot_sizing_production_planning" in lowered or "lot sizing" in lowered:
        validation = validate_lot_sizing_production_planning_output(output, instance, tolerance)
        gt_objective = extract_reported_objective(solution_ref, ("objective_exact", "objective", "objective_value", "total_cost"))
        predicted_objective = validation.get("objective_value")
        effective_tolerance = max(tolerance, 1e-2)
        correct = (
            validation.get("feasible_under_instance") is True
            and gt_objective is not None
            and predicted_objective is not None
            and abs(float(predicted_objective) - float(gt_objective)) <= effective_tolerance
        )
        return {
            "correct": correct,
            "reason": f"objective={predicted_objective} gt={gt_objective} capacity_usage={validation.get('capacity_usage')}",
        }
    if "workforce_planning_shift_scheduling" in lowered or "shift scheduling" in lowered:
        validation = validate_workforce_planning_shift_scheduling_output(output, instance, tolerance)
        gt_objective = extract_reported_objective(solution_ref, ("objective_exact", "objective", "objective_value", "total_cost"))
        predicted_objective = validation.get("objective_value")
        effective_tolerance = max(tolerance, 1e-2)
        correct = (
            validation.get("feasible_under_instance") is True
            and gt_objective is not None
            and predicted_objective is not None
            and abs(float(predicted_objective) - float(gt_objective)) <= effective_tolerance
        )
        return {
            "correct": correct,
            "reason": f"objective={predicted_objective} gt={gt_objective} coverage={validation.get('coverage_realized')}",
        }
    if "energy_dispatch_unit_commitment" in lowered or "unit_commitment" in lowered:
        validation = validate_energy_dispatch_unit_commitment_output(output, instance, tolerance)
        gt_objective = extract_reported_objective(solution_ref, ("objective_exact", "objective", "objective_value", "total_cost"))
        predicted_objective = validation.get("objective_value")
        correct = (
            validation.get("feasible_under_instance") is True
            and gt_objective is not None
            and predicted_objective is not None
            and abs(float(predicted_objective) - float(gt_objective)) <= tolerance
        )
        return {
            "correct": correct,
            "reason": f"objective={predicted_objective} gt={gt_objective} status={validation.get('status')}",
        }
    if "inventory_routing_problem" in lowered or "inventory routing" in lowered:
        validation = validate_inventory_routing_problem_output(output, instance, tolerance)
        gt_objective = extract_reported_objective(solution_ref, ("objective_exact", "objective", "objective_value", "total_cost"))
        predicted_objective = validation.get("objective_value")
        effective_tolerance = max(tolerance, 1e-2)
        correct = (
            validation.get("feasible_under_instance") is True
            and gt_objective is not None
            and predicted_objective is not None
            and abs(float(predicted_objective) - float(gt_objective)) <= effective_tolerance
        )
        return {
            "correct": correct,
            "reason": f"objective={predicted_objective} gt={gt_objective} deliveries={validation.get('deliveries')}",
        }
    if "job_shop_scheduling" in lowered or "job shop" in lowered or "jssp" in lowered:
        validation = validate_job_shop_scheduling_output(output, instance, tolerance)
        gt_objective = extract_reported_objective(
            solution_ref,
            ("objective_exact", "objective", "objective_value", "makespan", "total_makespan"),
        )
        predicted_objective = validation.get("objective_value")
        correct = (
            validation.get("feasible_under_instance") is True
            and gt_objective is not None
            and predicted_objective is not None
            and abs(float(predicted_objective) - float(gt_objective)) <= max(tolerance, 1e-6)
        )
        return {
            "correct": correct,
            "reason": f"objective={predicted_objective} gt={gt_objective} scheduled_operations={validation.get('scheduled_operations')}",
        }
    if "parallel_machine_scheduling" in lowered or "parallel machine" in lowered:
        validation = validate_parallel_machine_scheduling_output(output, instance, tolerance)
        gt_objective = extract_reported_objective(
            solution_ref,
            ("objective_exact", "objective", "objective_value", "makespan", "total_makespan"),
        )
        predicted_objective = validation.get("objective_value")
        correct = (
            validation.get("feasible_under_instance") is True
            and gt_objective is not None
            and predicted_objective is not None
            and abs(float(predicted_objective) - float(gt_objective)) <= max(tolerance, 1e-6)
        )
        return {
            "correct": correct,
            "reason": f"objective={predicted_objective} gt={gt_objective} assignments={validation.get('assignments')}",
        }
    if "rcpsp" in lowered or "resource_constrained_project_scheduling" in lowered:
        validation = validate_rcpsp_output(output, instance, tolerance)
        gt_objective = extract_reported_objective(
            solution_ref,
            ("objective_exact", "objective", "objective_value", "makespan", "total_makespan"),
        )
        predicted_objective = validation.get("objective_value")
        correct = (
            validation.get("feasible_under_instance") is True
            and gt_objective is not None
            and predicted_objective is not None
            and abs(float(predicted_objective) - float(gt_objective)) <= max(tolerance, 1e-6)
        )
        return {
            "correct": correct,
            "reason": f"objective={predicted_objective} gt={gt_objective} starts={validation.get('activity_start_times')}",
        }
    if "flexible_hybrid_flow-shop_scheduling" in lowered or "flexible_hybrid_flow_shop_scheduling" in lowered or "hybrid flow-shop" in lowered:
        validation = validate_flexible_hybrid_flow_shop_scheduling_output(output, instance, tolerance)
        gt_objective = extract_reported_objective(
            solution_ref,
            ("objective_exact", "objective", "objective_value", "optimal_makespan", "makespan", "total_makespan"),
        )
        predicted_objective = validation.get("objective_value")
        correct = (
            validation.get("feasible_under_instance") is True
            and gt_objective is not None
            and predicted_objective is not None
            and abs(float(predicted_objective) - float(gt_objective)) <= max(tolerance, 1e-6)
        )
        return {
            "correct": correct,
            "reason": f"objective={predicted_objective} gt={gt_objective} machine_assignment={validation.get('machine_assignment')}",
        }
    if "capacitated_network_design" in lowered or "network_design" in lowered:
        validation = validate_capacitated_network_design_output(output, instance, tolerance)
        gt_objective = to_number(solution_ref.get("objective_exact") if "objective_exact" in solution_ref else solution_ref.get("objective_value"))
        predicted_objective = validation.get("objective_value")
        correct = (
            validation.get("feasible_under_instance") is True
            and gt_objective is not None
            and predicted_objective is not None
            and abs(float(predicted_objective) - float(gt_objective)) <= tolerance
        )
        return {
            "correct": correct,
            "reason": f"objective={predicted_objective} gt={gt_objective} flows={validation.get('arc_flows')}",
        }
    if "minimum_cost_flow" in lowered:
        validation = validate_minimum_cost_flow_output(output, instance, tolerance)
        gt_objective = to_number(solution_ref.get("objective_exact") if "objective_exact" in solution_ref else solution_ref.get("objective_value"))
        predicted_objective = validation.get("objective_value")
        correct = (
            validation.get("feasible_under_instance") is True
            and gt_objective is not None
            and predicted_objective is not None
            and abs(float(predicted_objective) - float(gt_objective)) <= tolerance
        )
        return {
            "correct": correct,
            "reason": f"objective={predicted_objective} gt={gt_objective} flows={validation.get('arc_flows')}",
        }
    if "resource_constrained_shortest_path" in lowered or "rcsp" in lowered:
        validation = validate_resource_constrained_shortest_path_output(output, instance, tolerance)
        gt_objective = to_number(solution_ref.get("objective_exact") if "objective_exact" in solution_ref else solution_ref.get("objective_value"))
        predicted_objective = validation.get("objective_value")
        correct = (
            validation.get("feasible_under_instance") is True
            and gt_objective is not None
            and predicted_objective is not None
            and abs(float(predicted_objective) - float(gt_objective)) <= tolerance
        )
        return {
            "correct": correct,
            "reason": f"objective={predicted_objective} gt={gt_objective} arcs={validation.get('selected_arcs')}",
        }
    if "time_expanded_multi_period_network_flow" in lowered or "time-expanded_multi-period_network_flow" in lowered:
        validation = validate_time_expanded_multi_period_network_flow_output(output, instance, tolerance)
        gt_objective = to_number(solution_ref.get("objective_exact") if "objective_exact" in solution_ref else solution_ref.get("objective_value"))
        predicted_objective = validation.get("objective_value")
        correct = (
            validation.get("feasible_under_instance") is True
            and gt_objective is not None
            and predicted_objective is not None
            and abs(float(predicted_objective) - float(gt_objective)) <= tolerance
        )
        return {
            "correct": correct,
            "reason": f"objective={predicted_objective} gt={gt_objective}",
        }
    if "flow" in lowered:
        payload = unwrap_solution_dict(output)
        validation = validate_max_flow_output(output, instance, tolerance)
        max_flow = validation.get("objective_value")
        cut = extract_max_flow_cut_partition(payload)
        gt_max_flow = to_number(solution_ref.get("max_flow_value") if "max_flow_value" in solution_ref else solution_ref.get("objective_value"))
        correct = (
            validation.get("feasible_under_instance") is True
            and max_flow is not None
            and gt_max_flow is not None
            and abs(max_flow - float(gt_max_flow)) <= tolerance
        )
        return {
            "correct": correct,
            "reason": f"max_flow={max_flow} gt={gt_max_flow} cutS={cut.get('S')} cutT={cut.get('T')} feasible={validation.get('feasible_under_instance')}",
            "validation": validation,
        }
    if "logical_constraint" in lowered or "logical constraint" in lowered or "satisfaction" in lowered:
        validation = validate_logical_constraint_satisfaction_output(output, instance)
        gt_status = normalize_status(solution_ref.get("status"))
        correct = (gt_status == "feasible" and validation.get("feasible_under_instance") is True) or (
            gt_status == "infeasible" and normalize_status(output.get("status")) == "infeasible"
        )
        return {
            "correct": correct,
            "reason": f"gt_status={gt_status} feasible_under_instance={validation.get('feasible_under_instance')}",
        }
    if "bipartite_assignment" in lowered or "bipartite assignment" in lowered or lowered == "assignment" or "matching" in lowered:
        validation = validate_bipartite_assignment_output(output, instance, tolerance)
        gt_objective = to_number(solution_ref.get("objective_exact") if "objective_exact" in solution_ref else solution_ref.get("objective_value"))
        predicted_objective = validation.get("objective_value")
        correct = (
            validation.get("feasible_under_instance") is True
            and gt_objective is not None
            and predicted_objective is not None
            and abs(float(predicted_objective) - float(gt_objective)) <= tolerance
        )
        return {
            "correct": correct,
            "reason": f"objective={predicted_objective} gt={gt_objective} assignments={validation.get('assignments')}",
        }
    if "facility_location" in lowered or "facility location" in lowered:
        validation = validate_facility_location_output(output, instance, tolerance)
        gt_objective = to_number(solution_ref.get("objective_exact") if "objective_exact" in solution_ref else solution_ref.get("objective_value"))
        predicted_objective = validation.get("objective_value")
        correct = (
            validation.get("feasible_under_instance") is True
            and gt_objective is not None
            and predicted_objective is not None
            and abs(float(predicted_objective) - float(gt_objective)) <= tolerance
        )
        return {
            "correct": correct,
            "reason": f"objective={predicted_objective} gt={gt_objective} open={validation.get('open_facilities')}",
        }
    if "generalized_assignment_problem" in lowered or "generalized assignment" in lowered:
        validation = validate_generalized_assignment_output(output, instance, tolerance)
        gt_objective = to_number(solution_ref.get("objective_exact") if "objective_exact" in solution_ref else solution_ref.get("objective_value"))
        predicted_objective = validation.get("objective_value")
        correct = (
            validation.get("feasible_under_instance") is True
            and gt_objective is not None
            and predicted_objective is not None
            and abs(float(predicted_objective) - float(gt_objective)) <= tolerance
        )
        return {
            "correct": correct,
            "reason": f"objective={predicted_objective} gt={gt_objective} loads={validation.get('agent_loads')}",
        }
    if "p_median_center" in lowered or "p-median" in lowered or "p_median" in lowered or "p_center" in lowered or "p-center" in lowered:
        validation = validate_p_median_center_output(output, instance, tolerance)
        gt_objective = to_number(solution_ref.get("objective_exact") if "objective_exact" in solution_ref else solution_ref.get("objective_value"))
        predicted_objective = validation.get("objective_value")
        correct = (
            validation.get("feasible_under_instance") is True
            and gt_objective is not None
            and predicted_objective is not None
            and abs(float(predicted_objective) - float(gt_objective)) <= tolerance
        )
        return {
            "correct": correct,
            "reason": f"objective={predicted_objective} gt={gt_objective} open={validation.get('open_sites')}",
        }
    if "heterogeneous_fleet_vrp" in lowered or "heterogeneous fleet" in lowered:
        validation = validate_heterogeneous_fleet_vrp_output(output, instance, tolerance)
        gt_objective = extract_reported_objective(solution_ref, ("objective_exact", "objective", "objective_value", "total_cost", "objective_from_routes"))
        predicted_objective = validation.get("objective_value")
        effective_tolerance = max(tolerance, 1e-3)
        correct = (
            validation.get("feasible_under_instance") is True
            and gt_objective is not None
            and predicted_objective is not None
            and abs(float(predicted_objective) - float(gt_objective)) <= effective_tolerance
        )
        return {
            "correct": correct,
            "reason": f"objective={predicted_objective} gt={gt_objective} routes={validation.get('routes')}",
        }
    if "vehicle_routing_problem" in lowered or "vehicle routing" in lowered:
        validation = validate_vehicle_routing_problem_output(output, instance, tolerance)
        gt_objective = extract_reported_objective(solution_ref, ("objective_exact", "objective", "objective_value", "total_cost"))
        predicted_objective = validation.get("objective_value")
        effective_tolerance = max(tolerance, 1e-3)
        correct = (
            validation.get("feasible_under_instance") is True
            and gt_objective is not None
            and predicted_objective is not None
            and abs(float(predicted_objective) - float(gt_objective)) <= effective_tolerance
        )
        return {
            "correct": correct,
            "reason": f"objective={predicted_objective} gt={gt_objective} routes={validation.get('routes')}",
        }
    if "tsp_with_time_windows" in lowered or "traveling_salesman_problem_with_time_windows" in lowered or "time windows" in lowered:
        validation = validate_tsp_with_time_windows_output(output, instance, tolerance)
        gt_objective = extract_reported_objective(solution_ref, ("objective_exact", "objective", "objective_value", "total_cost", "total_distance", "total_travel_time"))
        predicted_objective = validation.get("objective_value")
        effective_tolerance = max(tolerance, 1e-2)
        correct = (
            validation.get("feasible_under_instance") is True
            and gt_objective is not None
            and predicted_objective is not None
            and abs(float(predicted_objective) - float(gt_objective)) <= effective_tolerance
        )
        return {
            "correct": correct,
            "reason": f"objective={predicted_objective} gt={gt_objective} route={validation.get('route')}",
        }
    if "traveling_salesman_problem" in lowered or "travel_salesman_problem" in lowered or "salesman problem" in lowered:
        validation = validate_traveling_salesman_problem_output(output, instance, tolerance)
        gt_objective = extract_reported_objective(solution_ref, ("objective_exact", "objective", "objective_value", "total_cost", "total_distance"))
        predicted_objective = validation.get("objective_value")
        effective_tolerance = max(tolerance, 1e-3)
        correct = (
            validation.get("feasible_under_instance") is True
            and gt_objective is not None
            and predicted_objective is not None
            and abs(float(predicted_objective) - float(gt_objective)) <= effective_tolerance
        )
        return {
            "correct": correct,
            "reason": f"objective={predicted_objective} gt={gt_objective} route={validation.get('route')}",
        }
    if "knapsack" in lowered:
        validation = validate_multi_dim_knapsack_output(output, instance, tolerance)
        gt_objective = to_number(solution_ref.get("objective_exact") if "objective_exact" in solution_ref else solution_ref.get("objective"))
        predicted_objective = validation.get("objective_value")
        correct = (
            validation.get("feasible_under_instance") is True
            and gt_objective is not None
            and predicted_objective is not None
            and abs(float(predicted_objective) - float(gt_objective)) <= tolerance
        )
        return {
            "correct": correct,
            "reason": f"objective={predicted_objective} gt={gt_objective} selected_items={validation.get('selected_items')}",
        }
    if "set_covering_partitioning" in lowered or "set covering" in lowered or "set partitioning" in lowered:
        validation = validate_set_covering_partitioning_output(output, instance, tolerance)
        gt_objective = to_number(solution_ref.get("objective_exact") if "objective_exact" in solution_ref else solution_ref.get("objective_value"))
        predicted_objective = validation.get("objective_value")
        correct = (
            validation.get("feasible_under_instance") is True
            and gt_objective is not None
            and predicted_objective is not None
            and abs(float(predicted_objective) - float(gt_objective)) <= tolerance
        )
        return {
            "correct": correct,
            "reason": f"objective={predicted_objective} gt={gt_objective} selected={validation.get('selected_subsets')}",
        }
    if "set_packing" in lowered or "set packing" in lowered:
        validation = validate_set_packing_output(output, instance, tolerance)
        total = validation.get("objective_value")
        correct = (
            validation.get("feasible_under_instance") is True
            and total is not None
            and abs(total - float(solution_ref.get("objective_value"))) <= tolerance
        )
        return {
            "correct": correct,
            "reason": f"value={total} gt={solution_ref.get('objective_value')} selected={output.get('selected_groups')}",
        }
    return {
        "correct": False,
        "reason": "No ground-truth comparator for this problem type",
        "unsupported_problem_type": True,
    }


def classify_code_failure(stderr: str) -> str:
    lowered = stderr.lower()
    if "modulenotfounderror" in lowered or "importerror" in lowered:
        return "coding_dependency_error"
    if "syntaxerror" in lowered:
        return "coding_syntax_error"
    return "coding_runtime_error"


def build_primary_diagnosis(
    *,
    schema_report: dict[str, Any],
    reading_report: dict[str, Any] | None,
    execution_report: dict[str, Any] | None,
    predicted_validation: dict[str, Any] | None,
    ground_truth_validation: dict[str, Any] | None,
) -> tuple[str, str]:
    if not schema_report.get("required_keys_present", False):
        return "response_schema_error", "The response is missing required top-level keys."
    if execution_report is None:
        return "response_content_error", "No solver code was available to execute."
    if execution_report.get("timed_out"):
        return "coding_runtime_error", execution_report.get("stderr", "Code execution timed out.")
    if execution_report.get("returncode") not in (0, None):
        return classify_code_failure(execution_report.get("stderr", "")), execution_report.get("stderr", "Code execution failed.")
    if execution_report.get("parsed_output") is None:
        return "code_output_format_error", "The generated code ran but did not print parseable JSON-like output."
    if ground_truth_validation and ground_truth_validation.get("unsupported_problem_type"):
        return "missing_ground_truth_validator", ground_truth_validation.get("reason", "No ground-truth comparator is available for this problem type.")
    if ground_truth_validation and ground_truth_validation.get("correct"):
        return "success", "The generated code executed successfully and matched ground truth."
    if reading_report and reading_report.get("major_mismatch"):
        return "reading_error", "The extracted instance data differs materially from the benchmark ground truth."
    if predicted_validation and predicted_validation.get("feasible_under_instance") is False:
        return "coding_or_algorithm_error", "The generated code output is inconsistent even with the model's own extracted instance."
    return "modeling_or_solving_error", "The extracted data looks plausible, but the executed solution does not match ground truth."


def build_secondary_failure_signals(
    *,
    primary_stage: str,
    reading_report: dict[str, Any] | None,
    execution_report: dict[str, Any] | None,
    predicted_validation: dict[str, Any] | None,
    ground_truth_validation: dict[str, Any] | None,
) -> list[str]:
    signals: list[str] = []
    if reading_report and reading_report.get("major_mismatch") and primary_stage != "reading_error":
        signals.append("reading_error")
    if execution_report is not None:
        if execution_report.get("timed_out"):
            signals.append("coding_runtime_error")
        elif execution_report.get("returncode") not in (0, None):
            signal = classify_code_failure(execution_report.get("stderr", ""))
            if signal != primary_stage:
                signals.append(signal)
        elif execution_report.get("parsed_output") is None and primary_stage != "code_output_format_error":
            signals.append("code_output_format_error")
    if predicted_validation and predicted_validation.get("feasible_under_instance") is False and primary_stage != "coding_or_algorithm_error":
        signals.append("coding_or_algorithm_error")
    if ground_truth_validation and ground_truth_validation.get("unsupported_problem_type"):
        if primary_stage != "missing_ground_truth_validator":
            signals.append("missing_ground_truth_validator")
    elif ground_truth_validation and not ground_truth_validation.get("correct", False) and primary_stage != "success":
        signals.append("solution_incorrect")
    deduped = []
    for item in signals:
        if item not in deduped:
                deduped.append(item)
    return deduped
