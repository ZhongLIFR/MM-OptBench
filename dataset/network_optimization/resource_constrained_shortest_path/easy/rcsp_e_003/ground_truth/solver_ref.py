#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "instance_data.json"), "r", encoding="utf-8") as f:
    data = json.load(f)

nodes = [int(x) for x in data["nodes"]]
source = int(data["source"])
sink = int(data["sink"])
resource_name = str(data["resource_name"])
resource_bound = float(data["resource_bound"])
arcs = [(int(a["from"]), int(a["to"])) for a in data["arcs"]]
cost = {(int(a["from"]), int(a["to"])): float(a["cost"]) for a in data["arcs"]}
resource = {(int(a["from"]), int(a["to"])): float(a["resource"]) for a in data["arcs"]}
graph = defaultdict(list)
for i, j in arcs:
    graph[i].append(j)


def normalize_number(value: float):
    rounded = round(float(value))
    if abs(float(value) - rounded) <= 1e-8:
        return int(rounded)
    return float(value)


def enumerate_simple_paths():
    paths = []

    def dfs(node: int, path: list[int], visited: set[int]) -> None:
        if node == sink:
            paths.append(path[:])
            return
        for nxt in graph[node]:
            if nxt in visited:
                continue
            visited.add(nxt)
            path.append(nxt)
            dfs(nxt, path, visited)
            path.pop()
            visited.remove(nxt)

    dfs(source, [source], {source})
    return paths


def evaluate_path(path: list[int]) -> dict:
    selected_arcs = []
    total_cost = 0.0
    total_resource = 0.0
    for u, v in zip(path, path[1:]):
        selected_arcs.append([u, v])
        total_cost += cost[(u, v)]
        total_resource += resource[(u, v)]
    return {
        "path": path,
        "selected_arcs": selected_arcs,
        "total_cost": normalize_number(total_cost),
        "total_resource": normalize_number(total_resource),
        "feasible": bool(total_resource <= resource_bound + 1e-8),
    }


def choose_best_by_enumeration() -> tuple[dict, list[dict]]:
    catalog = [evaluate_path(path) for path in enumerate_simple_paths()]
    feasible = [entry for entry in catalog if entry["feasible"]]
    if not feasible:
        raise RuntimeError("No feasible path exists.")
    feasible.sort(key=lambda item: (float(item["total_cost"]), float(item["total_resource"]), item["path"]))
    return feasible[0], catalog


def solve_with_gurobi() -> tuple[dict, list[dict], str, str]:
    import gurobipy as gp
    from gurobipy import GRB

    model = gp.Model("rcsp_easy")
    model.Params.OutputFlag = 0
    model.Params.TimeLimit = 30.0
    model.Params.MIPGap = 0.0

    x = {
        (i, j): model.addVar(vtype=GRB.BINARY, name=f"x_{i}_{j}")
        for (i, j) in arcs
    }

    model.setObjective(
        gp.quicksum(cost[(i, j)] * x[(i, j)] for (i, j) in arcs),
        GRB.MINIMIZE,
    )

    for node in nodes:
        outflow = gp.quicksum(x[(i, j)] for (i, j) in arcs if i == node)
        inflow = gp.quicksum(x[(i, j)] for (i, j) in arcs if j == node)
        rhs = 1 if node == source else -1 if node == sink else 0
        model.addConstr(outflow - inflow == rhs, name=f"balance_{node}")

    model.addConstr(
        gp.quicksum(resource[(i, j)] * x[(i, j)] for (i, j) in arcs) <= resource_bound,
        name="resource_bound",
    )

    model.optimize()
    if model.Status != GRB.OPTIMAL:
        raise RuntimeError(f"Gurobi ended with status {model.Status}")

    chosen = {(i, j): int(round(x[(i, j)].X)) for (i, j) in arcs}
    current = source
    path = [source]
    used = set()
    while current != sink:
        next_nodes = [j for (i, j), val in chosen.items() if i == current and val > 0]
        if len(next_nodes) != 1:
            raise RuntimeError("Unable to reconstruct a unique directed path from Gurobi output.")
        nxt = next_nodes[0]
        if (current, nxt) in used:
            raise RuntimeError("Cycle detected while reconstructing Gurobi solution.")
        used.add((current, nxt))
        path.append(nxt)
        current = nxt

    best, catalog = choose_best_by_enumeration()
    gurobi_cost = normalize_number(model.ObjVal)
    if abs(float(gurobi_cost) - float(best["total_cost"])) > 1e-8:
        raise RuntimeError("Gurobi objective does not match exact enumeration.")

    solution = {
        "path": path,
        "selected_arcs": [[u, v] for u, v in zip(path, path[1:])],
        "total_cost": gurobi_cost,
        "total_resource": normalize_number(sum(resource[(u, v)] for u, v in zip(path, path[1:]))),
    }
    return solution, catalog, "gurobi_mip_rcsp_single_resource", "Gurobi"


def solve_exactly_by_enumeration() -> tuple[dict, list[dict], str, str]:
    best, catalog = choose_best_by_enumeration()
    solution = {
        "path": best["path"],
        "selected_arcs": best["selected_arcs"],
        "total_cost": best["total_cost"],
        "total_resource": best["total_resource"],
    }
    return solution, catalog, "exact_simple_path_enumeration", "Enumeration"


def build_arc_selection(selected_arcs: list[list[int]]) -> dict:
    chosen = {tuple(arc) for arc in selected_arcs}
    return {
        f"{i}_{j}": int((i, j) in chosen)
        for (i, j) in arcs
    }


def write_solution(solution: dict, catalog: list[dict], solve_method: str, solver_name: str, runtime_seconds: float) -> None:
    payload = {
        "status": "optimal",
        "objective_value": normalize_number(solution["total_cost"]),
        "objective_exact": normalize_number(solution["total_cost"]),
        "optimal_path": solution["path"],
        "selected_arcs": solution["selected_arcs"],
        "arc_selection": build_arc_selection(solution["selected_arcs"]),
        "resource_name": resource_name,
        "resource_bound": normalize_number(resource_bound),
        "total_resource": normalize_number(solution["total_resource"]),
        "feasible_path_count": sum(1 for entry in catalog if entry["feasible"]),
        "path_count": len(catalog),
        "runtime_seconds": float(runtime_seconds),
        "solve_method": solve_method,
        "solver_used": solver_name,
        "solver": solver_name,
        "solver_policy": "gurobi_first_then_exact_path_enumeration",
    }
    with open(os.path.join(HERE, "solution_ref.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


start = time.time()
try:
    solution, catalog, solve_method, solver_name = solve_with_gurobi()
except Exception:
    solution, catalog, solve_method, solver_name = solve_exactly_by_enumeration()
runtime_seconds = time.time() - start
write_solution(solution, catalog, solve_method, solver_name, runtime_seconds)
