#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds
from scipy.sparse import lil_matrix

try:
    import gurobipy as gp
    from gurobipy import GRB
except Exception:
    gp = None
    GRB = None


def solve_with_gurobi(data: dict):
    if gp is None:
        return None

    nodes = list(data["sets"]["nodes"])
    root = nodes[0]
    others = [n for n in nodes if n != root]
    dist = data["distance_matrix"]
    n = len(nodes)

    model = gp.Model("hard_tsp")
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


def solve_with_scipy(data: dict) -> dict:
    nodes = list(data["sets"]["nodes"])
    dist = data["distance_matrix"]
    n = len(nodes)
    arcs = [(i, j) for i in range(n) for j in range(n) if i != j]
    cost = np.array([float(dist[nodes[i]][nodes[j]]) for i, j in arcs], dtype=float)
    m = len(arcs)
    arc_index = {a: k for k, a in enumerate(arcs)}

    deg = lil_matrix((2 * n, m), dtype=float)
    rhs = np.ones(2 * n, dtype=float)
    for i in range(n):
        for j in range(n):
            if i != j:
                deg[i, arc_index[(i, j)]] = 1.0
                deg[n + j, arc_index[(i, j)]] = 1.0

    constraints = [LinearConstraint(deg.tocsr(), rhs, rhs)]
    integrality = np.ones(m, dtype=int)
    bounds = Bounds(np.zeros(m), np.ones(m))

    def extract_cycles(x: np.ndarray):
        succ = {i: None for i in range(n)}
        for (i, j), val in zip(arcs, x):
            if val > 0.5:
                succ[i] = j
        seen = set()
        cycles = []
        for start in range(n):
            if start in seen:
                continue
            cur = start
            path = []
            while cur is not None and cur not in path:
                path.append(cur)
                seen.add(cur)
                cur = succ[cur]
            if cur in path:
                cyc = path[path.index(cur):]
                cycles.append(cyc)
        return cycles

    start = time.perf_counter()
    cut_rounds = 0
    while True:
        res = milp(c=cost, integrality=integrality, bounds=bounds, constraints=constraints)
        if res.status != 0 or res.x is None:
            runtime = time.perf_counter() - start
            return {"status": "infeasible_or_no_optimal_solution", "runtime_seconds": runtime}
        cycles = extract_cycles(res.x)
        if len(cycles) == 1 and len(cycles[0]) == n:
            break
        rows = []
        lbs = []
        ubs = []
        for cyc in cycles:
            if len(cyc) == n:
                continue
            row = np.zeros(m, dtype=float)
            for i in cyc:
                for j in cyc:
                    if i != j:
                        row[arc_index[(i, j)]] = 1.0
            rows.append(row)
            lbs.append(-np.inf)
            ubs.append(len(cyc) - 1)
        if rows:
            constraints.append(LinearConstraint(np.array(rows), np.array(lbs), np.array(ubs)))
        cut_rounds += 1
        if cut_rounds > 100:
            runtime = time.perf_counter() - start
            return {"status": "solver_cut_limit_reached", "runtime_seconds": runtime}

    runtime = time.perf_counter() - start
    x = res.x
    chosen = [(nodes[i], nodes[j]) for (i, j), val in zip(arcs, x) if val > 0.5]
    succ_name = {i: j for i, j in chosen}
    root = nodes[0]
    tour = [root]
    current = root
    visited = {root}
    while True:
        nxt = succ_name[current]
        tour.append(nxt)
        if nxt == root:
            break
        if nxt in visited:
            break
        visited.add(nxt)
        current = nxt
    visit_order = {tour[k]: k for k in range(len(tour) - 1)}

    # approximate near-opt signal using edge-exchange perturbations around optimum
    best_cost = float(res.fun)
    alt_costs = []
    for a_idx in range(len(tour) - 3):
        for b_idx in range(a_idx + 2, len(tour) - 1):
            if a_idx == 0 and b_idx == len(tour) - 2:
                continue
            candidate = tour[:-1]
            candidate[a_idx + 1:b_idx + 1] = reversed(candidate[a_idx + 1:b_idx + 1])
            cand_tour = candidate + [candidate[0]]
            c = 0.0
            for k in range(len(cand_tour) - 1):
                c += float(dist[cand_tour[k]][cand_tour[k + 1]])
            alt_costs.append(c)
    near_threshold = best_cost * 1.05 + 1e-9
    num_near = 1 + sum(1 for c in alt_costs if c <= near_threshold)

    return {
        "status": "optimal",
        "objective": round(best_cost, 4),
        "objective_exact": best_cost,
        "runtime_seconds": runtime,
        "tour": tour,
        "selected_arcs": chosen,
        "visit_order": visit_order,
        "near_optimal_tour_flag": num_near >= 2,
        "num_tours_within_5pct_proxy": num_near,
        "cut_rounds": cut_rounds,
        "solve_method": "scipy_milp_iterative_subtour_cuts",
    }


def solve_instance(data: dict) -> dict:
    gurobi_result = solve_with_gurobi(data)
    if gurobi_result is not None:
        best_cost, tour, runtime = gurobi_result
        selected_arcs = [(tour[k], tour[k + 1]) for k in range(len(tour) - 1)]
        visit_order = {tour[k]: k for k in range(len(tour) - 1)}

        alt_costs = []
        for a_idx in range(len(tour) - 3):
            for b_idx in range(a_idx + 2, len(tour) - 1):
                if a_idx == 0 and b_idx == len(tour) - 2:
                    continue
                candidate = tour[:-1]
                candidate[a_idx + 1:b_idx + 1] = reversed(candidate[a_idx + 1:b_idx + 1])
                cand_tour = candidate + [candidate[0]]
                c = 0.0
                dist = data["distance_matrix"]
                for k in range(len(cand_tour) - 1):
                    c += float(dist[cand_tour[k]][cand_tour[k + 1]])
                alt_costs.append(c)
        near_threshold = best_cost * 1.05 + 1e-9
        num_near = 1 + sum(1 for c in alt_costs if c <= near_threshold)

        return {
            "status": "optimal",
            "objective": round(best_cost, 4),
            "objective_exact": best_cost,
            "runtime_seconds": runtime,
            "tour": tour,
            "selected_arcs": selected_arcs,
            "visit_order": visit_order,
            "near_optimal_tour_flag": num_near >= 2,
            "num_tours_within_5pct_proxy": num_near,
            "solve_method": "gurobi_mtz_tsp",
        }

    return solve_with_scipy(data)


def main() -> None:
    base = Path(__file__).resolve().parent
    data = json.loads((base / "instance_data.json").read_text(encoding="utf-8"))
    sol = solve_instance(data)
    (base / "solution_ref.json").write_text(json.dumps(sol, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
