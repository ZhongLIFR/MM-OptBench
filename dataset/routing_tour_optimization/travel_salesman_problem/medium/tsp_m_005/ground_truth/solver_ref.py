#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import math
import time
from itertools import combinations
from pathlib import Path

try:
    import gurobipy as gp
    from gurobipy import GRB
except Exception:
    gp = None
    GRB = None


def held_karp_solve(nodes: list[str], dist: dict, root: str):
    others = [n for n in nodes if n != root]
    m = len(others)
    dp = {}
    parent = {}

    for j in range(m):
        mask = 1 << j
        dp[(mask, j)] = float(dist[root][others[j]])
        parent[(mask, j)] = None

    for subset_size in range(2, m + 1):
        for comb in combinations(range(m), subset_size):
            mask = 0
            for j in comb:
                mask |= 1 << j
            for j in comb:
                prev_mask = mask ^ (1 << j)
                best_val = math.inf
                best_prev = None
                for k in comb:
                    if k == j:
                        continue
                    cand = dp[(prev_mask, k)] + float(dist[others[k]][others[j]])
                    if cand < best_val - 1e-12:
                        best_val = cand
                        best_prev = k
                dp[(mask, j)] = best_val
                parent[(mask, j)] = best_prev

    full_mask = (1 << m) - 1
    best_cost = math.inf
    end_j = None
    for j in range(m):
        cand = dp[(full_mask, j)] + float(dist[others[j]][root])
        if cand < best_cost - 1e-12:
            best_cost = cand
            end_j = j

    rev = []
    mask = full_mask
    j = end_j
    while j is not None:
        rev.append(others[j])
        prev = parent[(mask, j)]
        mask ^= 1 << j
        j = prev
    tour = [root] + rev[::-1] + [root]
    return best_cost, tour


def solve_with_gurobi(data: dict):
    if gp is None:
        return None

    nodes = data["sets"]["nodes"]
    root = data["root_city"]
    others = [n for n in nodes if n != root]
    dist = data["distance_matrix"]
    n = len(nodes)

    model = gp.Model("medium_tsp")
    model.Params.OutputFlag = 0
    model.Params.TimeLimit = 60

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


def solve_instance(data: dict) -> dict:
    nodes = data["sets"]["nodes"]
    root = data["root_city"]
    dist = data["distance_matrix"]

    gurobi_result = solve_with_gurobi(data)
    if gurobi_result is None:
        start = time.perf_counter()
        best_cost, best_tour = held_karp_solve(nodes, dist, root)
        runtime = time.perf_counter() - start
        solve_method = "held_karp_dynamic_programming_root_fixed"
    else:
        best_cost, best_tour, runtime = gurobi_result
        solve_method = "gurobi_mtz_tsp"

    selected_arcs = [(best_tour[k], best_tour[k + 1]) for k in range(len(best_tour) - 1)]
    visit_order = {best_tour[t]: t for t in range(len(best_tour) - 1)}
    return {
        "status": "optimal",
        "objective": round(best_cost, 4),
        "objective_exact": best_cost,
        "runtime_seconds": runtime,
        "tour": list(best_tour),
        "selected_arcs": selected_arcs,
        "visit_order": visit_order,
        "near_optimal_tour_flag": data["meta_parameters"].get("near_optimal_tour_flag", False),
        "solve_method": solve_method,
    }


def main() -> None:
    base = Path(__file__).resolve().parent
    data = json.loads((base / "instance_data.json").read_text(encoding="utf-8"))
    sol = solve_instance(data)
    (base / "solution_ref.json").write_text(json.dumps(sol, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
