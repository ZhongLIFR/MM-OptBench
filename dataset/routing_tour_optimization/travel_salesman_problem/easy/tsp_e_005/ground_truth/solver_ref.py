#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import math
import time
from itertools import permutations
from pathlib import Path

try:
    import gurobipy as gp
    from gurobipy import GRB
except Exception:
    gp = None
    GRB = None


def canonical_tours(root: str, others: list[str]):
    for perm in permutations(others):
        if perm[0] < perm[-1]:
            yield (root,) + perm + (root,)


def tour_cost(tour: tuple[str, ...], dist: dict) -> float:
    return sum(float(dist[tour[k]][tour[k + 1]]) for k in range(len(tour) - 1))


def solve_with_gurobi(data: dict):
    if gp is None:
        return None

    nodes = data["sets"]["nodes"]
    root = data["root_city"]
    others = [n for n in nodes if n != root]
    dist = data["distance_matrix"]
    n = len(nodes)

    model = gp.Model("easy_tsp")
    model.Params.OutputFlag = 0
    model.Params.TimeLimit = 30

    x = {(i, j): model.addVar(vtype=GRB.BINARY, name=f"x_{i}_{j}") for i in nodes for j in nodes if i != j}
    u = {i: model.addVar(lb=1.0, ub=n - 1, vtype=GRB.CONTINUOUS, name=f"u_{i}") for i in others}

    model.setObjective(gp.quicksum(float(dist[i][j]) * x[i, j] for i in nodes for j in nodes if i != j), GRB.MINIMIZE)

    for i in nodes:
        model.addConstr(gp.quicksum(x[i, j] for j in nodes if i != j) == 1)
        model.addConstr(gp.quicksum(x[j, i] for j in nodes if i != j) == 1)

    for i in others:
        for j in others:
            if i != j:
                model.addConstr(u[i] - u[j] + n * x[i, j] <= n - 1)

    start = time.perf_counter()
    model.optimize()
    runtime = time.perf_counter() - start

    if model.Status != GRB.OPTIMAL:
        return None

    succ = {}
    for (i, j), var in x.items():
        if var.X > 0.5:
            succ[i] = j

    tour = [root]
    current = root
    while True:
        nxt = succ[current]
        tour.append(nxt)
        if nxt == root:
            break
        current = nxt

    return float(model.ObjVal), tour, runtime


def enumerate_tour_landscape(data: dict):
    nodes = data["sets"]["nodes"]
    root = data["root_city"]
    others = [n for n in nodes if n != root]
    dist = data["distance_matrix"]

    best_tour = None
    best_cost = math.inf
    all_costs = []
    for tour in canonical_tours(root, others):
        c = tour_cost(tour, dist)
        all_costs.append((tour, c))
        if c < best_cost - 1e-12:
            best_cost = c
            best_tour = tour

    tol = 1e-9
    threshold = best_cost * 1.05 + tol
    optimal_tours = [tour for tour, c in all_costs if abs(c - best_cost) <= tol]
    near_tours = [tour for tour, c in all_costs if c <= threshold]
    return best_cost, best_tour, len(optimal_tours) == 1, len(optimal_tours), len(near_tours) >= 2, len(near_tours)


def solve_instance(data: dict) -> dict:
    start = time.perf_counter()
    gurobi_result = solve_with_gurobi(data)
    solve_runtime = time.perf_counter() - start

    if gurobi_result is None:
        landscape_start = time.perf_counter()
        best_cost, best_tour, unique_optimal, num_optimal, near_flag, num_near = enumerate_tour_landscape(data)
        runtime = time.perf_counter() - landscape_start
        solve_method = "exact_enumeration_root_fixed"
    else:
        best_cost, best_tour, runtime = gurobi_result
        _, _, unique_optimal, num_optimal, near_flag, num_near = enumerate_tour_landscape(data)
        solve_method = "gurobi_mtz_tsp"

    selected_arcs = [(best_tour[k], best_tour[k + 1]) for k in range(len(best_tour) - 1)]
    visit_order = {best_tour[t]: t for t in range(len(best_tour) - 1)}
    return {
        "status": "optimal",
        "objective": round(best_cost, 4),
        "objective_exact": best_cost,
        "runtime_seconds": runtime if gurobi_result is None else runtime,
        "tour": list(best_tour),
        "selected_arcs": selected_arcs,
        "visit_order": visit_order,
        "unique_optimal_flag": unique_optimal,
        "near_optimal_tour_flag": near_flag,
        "num_optimal_tours": num_optimal,
        "num_tours_within_5pct": num_near,
        "solve_method": solve_method,
    }


def main() -> None:
    base = Path(__file__).resolve().parent
    data = json.loads((base / "instance_data.json").read_text(encoding="utf-8"))
    sol = solve_instance(data)
    (base / "solution_ref.json").write_text(json.dumps(sol, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
