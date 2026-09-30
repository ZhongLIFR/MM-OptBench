#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
from heapq import heappop, heappush
from itertools import product

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE_PATH = os.path.join(HERE, "instance_data.json")
SOLUTION_PATH = os.path.join(HERE, "solution_ref.json")


def arc_id_key(arc_id: str) -> tuple[int, str]:
    if arc_id.startswith("e") and arc_id[1:].isdigit():
        return (int(arc_id[1:]), arc_id)
    return (10**9, arc_id)


def normalize_number(value: float):
    rounded = round(float(value))
    if abs(float(value) - rounded) <= 1e-8:
        return int(rounded)
    return float(round(float(value), 8))


with open(INSTANCE_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

nodes = [int(x) for x in data["nodes"]]
source = int(data["source"])
sink = int(data["sink"])
required_flow = int(data["required_flow"])
arcs = data["arcs"]
arc_ids = [str(arc["id"]) for arc in arcs]
capacity = {str(arc["id"]): float(arc["capacity"]) for arc in arcs}
fixed_cost = {str(arc["id"]): float(arc["fixed_cost"]) for arc in arcs}
variable_cost = {str(arc["id"]): float(arc["variable_cost"]) for arc in arcs}
arc_lookup = {
    str(arc["id"]): {
        "from": int(arc["from"]),
        "to": int(arc["to"]),
        "capacity": float(arc["capacity"]),
        "fixed_cost": float(arc["fixed_cost"]),
        "variable_cost": float(arc["variable_cost"]),
    }
    for arc in arcs
}


def installation_indicator(installed_arc_ids: list[str]) -> dict[str, int]:
    installed_set = set(installed_arc_ids)
    return {arc_id: int(arc_id in installed_set) for arc_id in arc_ids}


def dense_flow_dict(flow_by_id: dict[str, float]) -> dict[str, float | int]:
    return {arc_id: normalize_number(flow_by_id.get(arc_id, 0.0)) for arc_id in arc_ids}


def sparse_flow_dict(flow_by_id: dict[str, float]) -> dict[str, float | int]:
    return {
        arc_id: normalize_number(value)
        for arc_id, value in dense_flow_dict(flow_by_id).items()
        if float(value) > 1e-8
    }


def used_arc_ids(flow_by_id: dict[str, float]) -> list[str]:
    return sorted(
        [arc_id for arc_id, value in flow_by_id.items() if float(value) > 1e-8],
        key=arc_id_key,
    )


def binding_capacity_arcs(flow_by_id: dict[str, float]) -> list[str]:
    return sorted(
        [
            arc_id
            for arc_id, value in flow_by_id.items()
            if float(value) > 1e-8 and abs(float(value) - capacity[arc_id]) <= 1e-8
        ],
        key=arc_id_key,
    )


def min_cost_flow_on_installed(installed_arc_ids: set[str]) -> tuple[float, dict[str, float]] | None:
    selected = [arc for arc in arcs if str(arc["id"]) in installed_arc_ids]
    if not selected:
        return None

    used_nodes = sorted({int(arc["from"]) for arc in selected} | {int(arc["to"]) for arc in selected})
    if source not in used_nodes or sink not in used_nodes:
        return None

    node_to_idx = {node: idx for idx, node in enumerate(used_nodes)}
    graph: list[list[list[object]]] = [[] for _ in used_nodes]

    def add_edge(u: int, v: int, cap: float, cost: float, arc_id: str) -> None:
        graph[u].append([v, float(cap), float(cost), len(graph[v]), arc_id, True])
        graph[v].append([u, 0.0, -float(cost), len(graph[u]) - 1, arc_id, False])

    for arc in selected:
        add_edge(
            node_to_idx[int(arc["from"])],
            node_to_idx[int(arc["to"])],
            float(arc["capacity"]),
            float(arc["variable_cost"]),
            str(arc["id"]),
        )

    source_idx = node_to_idx[source]
    sink_idx = node_to_idx[sink]
    potentials = [0.0] * len(used_nodes)
    total_sent = 0.0
    total_variable_cost = 0.0
    flow_by_id = {str(arc["id"]): 0.0 for arc in selected}

    while total_sent + 1e-8 < required_flow:
        dist = [10**18] * len(used_nodes)
        prev: list[tuple[int, int] | None] = [None] * len(used_nodes)
        dist[source_idx] = 0.0
        pq: list[tuple[float, int]] = [(0.0, source_idx)]

        while pq:
            current_dist, u = heappop(pq)
            if current_dist != dist[u]:
                continue
            for edge_index, edge in enumerate(graph[u]):
                v, cap, cost, _rev, _arc_id, _is_forward = edge
                if float(cap) <= 1e-8:
                    continue
                candidate = current_dist + float(cost) + potentials[u] - potentials[int(v)]
                if candidate + 1e-12 < dist[int(v)]:
                    dist[int(v)] = candidate
                    prev[int(v)] = (u, edge_index)
                    heappush(pq, (candidate, int(v)))

        if dist[sink_idx] >= 10**18:
            return None

        for idx, value in enumerate(dist):
            if value < 10**18:
                potentials[idx] += float(value)

        augment = float(required_flow) - total_sent
        v = sink_idx
        while v != source_idx:
            if prev[v] is None:
                return None
            u, edge_index = prev[v]
            augment = min(augment, float(graph[u][edge_index][1]))
            v = u

        v = sink_idx
        while v != source_idx:
            u, edge_index = prev[v]
            edge = graph[u][edge_index]
            reverse_index = int(edge[3])
            graph[u][edge_index][1] = float(graph[u][edge_index][1]) - augment
            graph[v][reverse_index][1] = float(graph[v][reverse_index][1]) + augment
            arc_id = str(edge[4])
            if bool(edge[5]):
                flow_by_id[arc_id] += augment
            else:
                flow_by_id[arc_id] -= augment
            total_variable_cost += augment * float(edge[2])
            v = u

        total_sent += augment

    return total_variable_cost, {arc_id: value for arc_id, value in flow_by_id.items() if value > 1e-8}


def decompose_paths(flow_by_id: dict[str, float]) -> list[dict[str, object]]:
    residual = {arc_id: float(value) for arc_id, value in flow_by_id.items() if float(value) > 1e-8}
    outgoing: dict[int, list[str]] = {}
    for arc_id in residual:
        outgoing.setdefault(int(arc_lookup[arc_id]["from"]), []).append(arc_id)
    for node in outgoing:
        outgoing[node] = sorted(outgoing[node], key=arc_id_key)

    def dfs(node: int, current_path: list[str], visited: set[str]) -> list[str] | None:
        if node == sink:
            return current_path[:]
        for arc_id in outgoing.get(node, []):
            if residual.get(arc_id, 0.0) <= 1e-8 or arc_id in visited:
                continue
            visited.add(arc_id)
            current_path.append(arc_id)
            result = dfs(int(arc_lookup[arc_id]["to"]), current_path, visited)
            if result is not None:
                return result
            current_path.pop()
            visited.remove(arc_id)
        return None

    paths: list[dict[str, object]] = []
    while True:
        found = dfs(source, [], set())
        if not found:
            break
        path_flow = min(residual[arc_id] for arc_id in found)
        for arc_id in found:
            residual[arc_id] -= path_flow
        node_path = [source]
        for arc_id in found:
            node_path.append(int(arc_lookup[arc_id]["to"]))
        paths.append(
            {
                "path_nodes": node_path,
                "path_arc_ids": found,
                "flow": normalize_number(path_flow),
            }
        )
    return paths


def build_solution_payload(
    installed_arc_ids: list[str],
    flow_by_id: dict[str, float],
    solve_method: str,
    solver_name: str,
    verification_method: str,
    fallback_used: bool,
    optimality_proof: str,
) -> dict[str, object]:
    installed_arc_ids = sorted(installed_arc_ids, key=arc_id_key)
    dense_flow = {arc_id: float(flow_by_id.get(arc_id, 0.0)) for arc_id in arc_ids}
    fixed_total = sum(fixed_cost[arc_id] for arc_id in installed_arc_ids)
    variable_total = sum(variable_cost[arc_id] * dense_flow[arc_id] for arc_id in arc_ids)
    objective = fixed_total + variable_total
    used_ids = used_arc_ids(dense_flow)
    path_decomposition = decompose_paths(dense_flow)

    return {
        "status": "optimal",
        "objective_value": normalize_number(objective),
        "objective_exact": normalize_number(objective),
        "fixed_cost_total": normalize_number(fixed_total),
        "variable_cost_total": normalize_number(variable_total),
        "installed_arc_ids": installed_arc_ids,
        "installation_indicator": installation_indicator(installed_arc_ids),
        "arc_flow_by_id": dense_flow_dict(dense_flow),
        "arc_flows": sparse_flow_dict(dense_flow),
        "used_arc_ids": used_ids,
        "binding_capacity_arcs": binding_capacity_arcs(dense_flow),
        "path_decomposition": path_decomposition,
        "runtime_seconds": None,
        "solve_method": solve_method,
        "solver_used": solver_name,
        "solver": solver_name,
        "solver_policy": "gurobi_first_then_exact_installation_enumeration",
        "verification_method": verification_method,
        "fallback_used": bool(fallback_used),
        "optimality_proof": optimality_proof,
    }


def solve_with_gurobi() -> tuple[list[str], dict[str, float]]:
    import gurobipy as gp
    from gurobipy import GRB

    model = gp.Model("cnd_easy")
    model.Params.OutputFlag = 0
    model.Params.TimeLimit = 30.0
    model.Params.MIPGap = 0.0

    y = {
        arc_id: model.addVar(vtype=GRB.BINARY, name=f"y_{arc_id}")
        for arc_id in arc_ids
    }
    x = {
        arc_id: model.addVar(lb=0.0, ub=capacity[arc_id], vtype=GRB.CONTINUOUS, name=f"x_{arc_id}")
        for arc_id in arc_ids
    }

    model.setObjective(
        gp.quicksum(fixed_cost[arc_id] * y[arc_id] for arc_id in arc_ids)
        + gp.quicksum(variable_cost[arc_id] * x[arc_id] for arc_id in arc_ids),
        GRB.MINIMIZE,
    )

    for node in nodes:
        outflow = gp.quicksum(x[arc_id] for arc_id in arc_ids if int(arc_lookup[arc_id]["from"]) == node)
        inflow = gp.quicksum(x[arc_id] for arc_id in arc_ids if int(arc_lookup[arc_id]["to"]) == node)
        rhs = float(required_flow if node == source else -required_flow if node == sink else 0)
        model.addConstr(outflow - inflow == rhs, name=f"balance_{node}")

    for arc_id in arc_ids:
        model.addConstr(x[arc_id] <= capacity[arc_id] * y[arc_id], name=f"caplink_{arc_id}")

    model.optimize()
    if model.Status != GRB.OPTIMAL:
        raise RuntimeError(f"Gurobi ended with status {model.Status}")

    installed_arc_ids = sorted(
        [arc_id for arc_id in arc_ids if float(y[arc_id].X) > 0.5],
        key=arc_id_key,
    )
    flow_by_id = {arc_id: float(x[arc_id].X) for arc_id in arc_ids}
    return installed_arc_ids, flow_by_id


def solve_exactly_by_enumeration() -> dict[str, object]:
    best_payload: dict[str, object] | None = None
    best_objective: float | None = None

    for install_bits in product([0, 1], repeat=len(arc_ids)):
        installed = sorted(
            [arc_ids[idx] for idx, bit in enumerate(install_bits) if bit == 1],
            key=arc_id_key,
        )
        flow_result = min_cost_flow_on_installed(set(installed))
        if flow_result is None:
            continue
        variable_total, sparse_flow = flow_result
        dense_flow = {arc_id: float(sparse_flow.get(arc_id, 0.0)) for arc_id in arc_ids}
        fixed_total = sum(fixed_cost[arc_id] for arc_id in installed)
        objective = fixed_total + variable_total
        if best_objective is None or objective + 1e-8 < best_objective:
            best_objective = objective
            best_payload = build_solution_payload(
                installed_arc_ids=installed,
                flow_by_id=dense_flow,
                solve_method="exact_installation_enumeration",
                solver_name="Enumeration",
                verification_method="self_certified_by_global_installation_enumeration",
                fallback_used=True,
                optimality_proof="global_enumeration_over_all_installation_subsets",
            )

    if best_payload is None:
        raise RuntimeError("No feasible installation pattern found.")
    return best_payload


def write_solution(solution: dict[str, object]) -> None:
    with open(SOLUTION_PATH, "w", encoding="utf-8") as f:
        json.dump(solution, f, indent=2)
        f.write("\n")


def main() -> None:
    start = time.time()
    gurobi_error = None
    primary_solution = None

    try:
        installed_arc_ids, flow_by_id = solve_with_gurobi()
        primary_solution = build_solution_payload(
            installed_arc_ids=installed_arc_ids,
            flow_by_id=flow_by_id,
            solve_method="gurobi_mip_cnd_single_commodity",
            solver_name="Gurobi",
            verification_method="pending_exact_verification",
            fallback_used=False,
            optimality_proof="gurobi_optimal_mip_solution",
        )
    except Exception as exc:
        gurobi_error = str(exc)

    exact_solution = solve_exactly_by_enumeration()

    if primary_solution is not None:
        if abs(float(primary_solution["objective_value"]) - float(exact_solution["objective_value"])) > 1e-8:
            final_solution = exact_solution
            final_solution["solve_method"] = "exact_installation_enumeration_after_gurobi_mismatch"
            final_solution["verification_method"] = "objective_mismatch_triggered_exact_fallback"
            final_solution["gurobi_error"] = "objective mismatch with exact enumeration"
        else:
            final_solution = primary_solution
            final_solution["objective_exact"] = exact_solution["objective_exact"]
            final_solution["verification_method"] = "exact_installation_enumeration"
            final_solution["optimality_proof"] = (
                "gurobi_optimal_mip_solution_verified_against_global_installation_enumeration"
            )
    else:
        final_solution = exact_solution
        if gurobi_error is not None:
            final_solution["gurobi_error"] = gurobi_error

    final_solution["runtime_seconds"] = normalize_number(time.time() - start)
    write_solution(final_solution)


if __name__ == "__main__":
    main()
