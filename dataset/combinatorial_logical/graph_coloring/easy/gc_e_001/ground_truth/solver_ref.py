#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

try:
    import gurobipy as gp
    from gurobipy import GRB
except Exception:  # pragma: no cover - fallback path when Gurobi is unavailable
    gp = None
    GRB = None


def build_milp_feasibility(n: int, edges: list[list[int]], k: int):
    vars_count = n * k
    rows = []
    lb = []
    ub = []

    def vidx(v: int, color: int) -> int:
        return (v - 1) * k + (color - 1)

    for v in range(1, n + 1):
        row = np.zeros(vars_count, dtype=float)
        for c in range(1, k + 1):
            row[vidx(v, c)] = 1.0
        rows.append(row)
        lb.append(1.0)
        ub.append(1.0)

    for u, v in edges:
        for c in range(1, k + 1):
            row = np.zeros(vars_count, dtype=float)
            row[vidx(int(u), c)] = 1.0
            row[vidx(int(v), c)] = 1.0
            rows.append(row)
            lb.append(-np.inf)
            ub.append(1.0)

    A = np.vstack(rows) if rows else np.zeros((0, vars_count), dtype=float)
    c = np.zeros(vars_count, dtype=float)
    bounds = Bounds(lb=np.zeros(vars_count), ub=np.ones(vars_count))
    integrality = np.ones(vars_count, dtype=int)
    constraints = LinearConstraint(A, lb=np.array(lb, dtype=float), ub=np.array(ub, dtype=float))
    return c, constraints, bounds, integrality


def solve_with_gurobi(data: dict):
    if gp is None:
        return None
    n = int(data["meta_parameters"]["number_of_vertices"])
    k = int(data["meta_parameters"]["number_of_colors"])
    edges = [(int(u), int(v)) for u, v in data["edges"]]
    start = time.perf_counter()
    model = gp.Model("graph_coloring_easy")
    model.Params.OutputFlag = 0
    model.Params.TimeLimit = 30.0
    x = model.addVars(range(1, n + 1), range(1, k + 1), vtype=GRB.BINARY, name="x")
    for v in range(1, n + 1):
        model.addConstr(gp.quicksum(x[v, c] for c in range(1, k + 1)) == 1)
    for u, v in edges:
        for c in range(1, k + 1):
            model.addConstr(x[u, c] + x[v, c] <= 1)
    model.setObjective(0.0, GRB.MINIMIZE)
    model.optimize()
    runtime = round(time.perf_counter() - start, 6)
    if model.Status == GRB.OPTIMAL:
        assignment = {}
        for v in range(1, n + 1):
            chosen = [c for c in range(1, k + 1) if x[v, c].X > 0.5]
            if len(chosen) != 1:
                return None
            assignment[str(v)] = int(chosen[0])
        return {
            "status": "feasible",
            "is_k_colorable": True,
            "number_of_colors_available": k,
            "chromatic_number": int(data["meta_parameters"]["chromatic_number"]),
            "color_assignment": assignment,
            "solve_method": "gurobi_milp_graph_coloring_decision",
            "runtime_seconds": runtime,
        }
    if model.Status in {GRB.INFEASIBLE, GRB.INF_OR_UNBD}:
        return {
            "status": "infeasible",
            "is_k_colorable": False,
            "number_of_colors_available": k,
            "chromatic_number": int(data["meta_parameters"]["chromatic_number"]),
            "solve_method": "gurobi_milp_graph_coloring_decision",
            "runtime_seconds": runtime,
        }
    return None


def solve_instance(data: dict) -> dict:
    n = int(data["meta_parameters"]["number_of_vertices"])
    k = int(data["meta_parameters"]["number_of_colors"])
    edges = data["edges"]
    gurobi_sol = solve_with_gurobi(data)
    if gurobi_sol is not None:
        return gurobi_sol

    start = time.perf_counter()
    c, constraints, bounds, integrality = build_milp_feasibility(n, edges, k)
    res = milp(c=c, constraints=constraints, bounds=bounds, integrality=integrality, options={"time_limit": 30.0})
    runtime = round(time.perf_counter() - start, 6)
    if not res.success or res.x is None:
        return {
            "status": "infeasible",
            "is_k_colorable": False,
            "number_of_colors_available": k,
            "chromatic_number": int(data["meta_parameters"]["chromatic_number"]),
            "solve_method": "scipy_milp_graph_coloring_decision",
            "runtime_seconds": runtime,
        }

    x = np.rint(res.x).astype(int)
    assignment = {}
    for v in range(1, n + 1):
        block = x[(v - 1) * k : v * k]
        colors = np.where(block == 1)[0]
        if len(colors) != 1:
            return {
                "status": "infeasible",
                "is_k_colorable": False,
                "number_of_colors_available": k,
                "chromatic_number": int(data["meta_parameters"]["chromatic_number"]),
                "solve_method": "scipy_milp_graph_coloring_decision",
                "runtime_seconds": runtime,
            }
        assignment[str(v)] = int(colors[0] + 1)
    return {
        "status": "feasible",
        "is_k_colorable": True,
        "number_of_colors_available": k,
        "chromatic_number": int(data["meta_parameters"]["chromatic_number"]),
        "color_assignment": assignment,
        "solve_method": "scipy_milp_graph_coloring_decision",
        "runtime_seconds": runtime,
    }


def main() -> None:
    base = Path(__file__).resolve().parent
    data = json.loads((base / "instance_data.json").read_text(encoding="utf-8"))
    sol = solve_instance(data)
    (base / "solution_ref.json").write_text(json.dumps(sol, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
