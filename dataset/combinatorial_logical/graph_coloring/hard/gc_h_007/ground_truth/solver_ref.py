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


def build_decision_milp(n: int, edges: list[list[int]], k: int, precolored: dict[int, int] | None = None):
    precolored = precolored or {}
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

    for v, cfix in precolored.items():
        row = np.zeros(vars_count, dtype=float)
        row[vidx(int(v), int(cfix))] = 1.0
        rows.append(row)
        lb.append(1.0)
        ub.append(1.0)

    A = np.vstack(rows) if rows else np.zeros((0, vars_count), dtype=float)
    cvec = np.zeros(vars_count, dtype=float)
    bounds = Bounds(lb=np.zeros(vars_count), ub=np.ones(vars_count))
    integrality = np.ones(vars_count, dtype=int)
    constraints = LinearConstraint(A, lb=np.array(lb, dtype=float), ub=np.array(ub, dtype=float))
    return cvec, constraints, bounds, integrality


def build_opt_milp(n: int, edges: list[list[int]], kmax: int, weights: list[int] | None = None, precolored: dict[int, int] | None = None):
    weights = weights or [1] * kmax
    precolored = precolored or {}
    x_vars = n * kmax
    total_vars = x_vars + kmax
    rows = []
    lb = []
    ub = []

    def xidx(v: int, color: int) -> int:
        return (v - 1) * kmax + (color - 1)

    def yidx(color: int) -> int:
        return x_vars + (color - 1)

    for v in range(1, n + 1):
        row = np.zeros(total_vars, dtype=float)
        for c in range(1, kmax + 1):
            row[xidx(v, c)] = 1.0
        rows.append(row)
        lb.append(1.0)
        ub.append(1.0)

    for u, v in edges:
        for c in range(1, kmax + 1):
            row = np.zeros(total_vars, dtype=float)
            row[xidx(int(u), c)] = 1.0
            row[xidx(int(v), c)] = 1.0
            rows.append(row)
            lb.append(-np.inf)
            ub.append(1.0)

    for v in range(1, n + 1):
        for c in range(1, kmax + 1):
            row = np.zeros(total_vars, dtype=float)
            row[xidx(v, c)] = 1.0
            row[yidx(c)] = -1.0
            rows.append(row)
            lb.append(-np.inf)
            ub.append(0.0)

    for v, cfix in precolored.items():
        row = np.zeros(total_vars, dtype=float)
        row[xidx(int(v), int(cfix))] = 1.0
        rows.append(row)
        lb.append(1.0)
        ub.append(1.0)

    A = np.vstack(rows) if rows else np.zeros((0, total_vars), dtype=float)
    cvec = np.zeros(total_vars, dtype=float)
    for c in range(1, kmax + 1):
        cvec[yidx(c)] = float(weights[c - 1])
    bounds = Bounds(lb=np.zeros(total_vars), ub=np.ones(total_vars))
    integrality = np.ones(total_vars, dtype=int)
    constraints = LinearConstraint(A, lb=np.array(lb, dtype=float), ub=np.array(ub, dtype=float))
    return cvec, constraints, bounds, integrality


def solve_decision_gurobi(data: dict):
    if gp is None:
        return None
    n = int(data["meta_parameters"]["number_of_vertices"])
    k = int(data["meta_parameters"]["number_of_colors_available"])
    edges = [(int(u), int(v)) for u, v in data["edges"]]
    precolored = {int(v): int(c) for v, c in data.get("precolored_vertices", {}).items()}
    start = time.perf_counter()
    model = gp.Model("graph_coloring_decision")
    model.Params.OutputFlag = 0
    model.Params.TimeLimit = 120.0
    x = model.addVars(range(1, n + 1), range(1, k + 1), vtype=GRB.BINARY, name="x")
    for v in range(1, n + 1):
        model.addConstr(gp.quicksum(x[v, c] for c in range(1, k + 1)) == 1)
    for u, v in edges:
        for c in range(1, k + 1):
            model.addConstr(x[u, c] + x[v, c] <= 1)
    for v, cfix in precolored.items():
        model.addConstr(x[v, cfix] == 1)
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


def solve_optimization_gurobi(data: dict):
    if gp is None:
        return None
    n = int(data["meta_parameters"]["number_of_vertices"])
    kmax = int(data["meta_parameters"]["color_upper_bound"])
    edges = [(int(u), int(v)) for u, v in data["edges"]]
    weights = [int(w) for w in data.get("color_weights", [1] * kmax)]
    start = time.perf_counter()
    model = gp.Model("graph_coloring_optimization")
    model.Params.OutputFlag = 0
    model.Params.TimeLimit = 150.0
    x = model.addVars(range(1, n + 1), range(1, kmax + 1), vtype=GRB.BINARY, name="x")
    y = model.addVars(range(1, kmax + 1), vtype=GRB.BINARY, name="y")
    for v in range(1, n + 1):
        model.addConstr(gp.quicksum(x[v, c] for c in range(1, kmax + 1)) == 1)
    for u, v in edges:
        for c in range(1, kmax + 1):
            model.addConstr(x[u, c] + x[v, c] <= 1)
    for v in range(1, n + 1):
        for c in range(1, kmax + 1):
            model.addConstr(x[v, c] <= y[c])
    model.setObjective(gp.quicksum(weights[c - 1] * y[c] for c in range(1, kmax + 1)), GRB.MINIMIZE)
    model.optimize()
    runtime = round(time.perf_counter() - start, 6)
    if model.Status == GRB.OPTIMAL:
        assignment = {}
        for v in range(1, n + 1):
            chosen = [c for c in range(1, kmax + 1) if x[v, c].X > 0.5]
            if len(chosen) != 1:
                return None
            assignment[str(v)] = int(chosen[0])
        used = [c for c in range(1, kmax + 1) if y[c].X > 0.5]
        objective = round(float(model.ObjVal), 6)
        return {
            "status": "optimal",
            "chromatic_number": int(data["meta_parameters"]["chromatic_number"]),
            "number_of_used_colors": int(len(used)),
            "used_colors": used,
            "objective_value": objective,
            "objective_exact": objective,
            "color_assignment": assignment,
            "solve_method": "gurobi_milp_graph_coloring_optimization",
            "runtime_seconds": runtime,
        }
    if model.Status in {GRB.INFEASIBLE, GRB.INF_OR_UNBD}:
        return {
            "status": "infeasible",
            "chromatic_number": int(data["meta_parameters"]["chromatic_number"]),
            "objective_value": None,
            "objective_exact": None,
            "solve_method": "gurobi_milp_graph_coloring_optimization",
            "runtime_seconds": runtime,
        }
    return None


def solve_decision(data: dict) -> dict:
    n = int(data["meta_parameters"]["number_of_vertices"])
    k = int(data["meta_parameters"]["number_of_colors_available"])
    edges = data["edges"]
    precolored = {int(v): int(c) for v, c in data.get("precolored_vertices", {}).items()}
    gurobi_sol = solve_decision_gurobi(data)
    if gurobi_sol is not None:
        return gurobi_sol
    start = time.perf_counter()
    cvec, constraints, bounds, integrality = build_decision_milp(n, edges, k, precolored)
    res = milp(c=cvec, constraints=constraints, bounds=bounds, integrality=integrality, options={"time_limit": 30.0})
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


def solve_optimization(data: dict) -> dict:
    n = int(data["meta_parameters"]["number_of_vertices"])
    kmax = int(data["meta_parameters"]["color_upper_bound"])
    edges = data["edges"]
    precolored = {int(v): int(c) for v, c in data.get("precolored_vertices", {}).items()}
    weights = data.get("color_weights", [1] * kmax)
    gurobi_sol = solve_optimization_gurobi(data)
    if gurobi_sol is not None:
        return gurobi_sol
    start = time.perf_counter()
    cvec, constraints, bounds, integrality = build_opt_milp(n, edges, kmax, weights, precolored)
    res = milp(c=cvec, constraints=constraints, bounds=bounds, integrality=integrality, options={"time_limit": 60.0})
    runtime = round(time.perf_counter() - start, 6)
    if not res.success or res.x is None:
        return {
            "status": "infeasible",
            "objective_value": None,
            "objective_exact": None,
            "solve_method": "scipy_milp_graph_coloring_optimization",
            "runtime_seconds": runtime,
        }
    x_vars = n * kmax
    x = np.rint(res.x[:x_vars]).astype(int)
    y = np.rint(res.x[x_vars:]).astype(int)
    assignment = {}
    for v in range(1, n + 1):
        block = x[(v - 1) * kmax : v * kmax]
        colors = np.where(block == 1)[0]
        if len(colors) != 1:
            return {
                "status": "infeasible",
                "objective_value": None,
                "objective_exact": None,
                "solve_method": "scipy_milp_graph_coloring_optimization",
                "runtime_seconds": runtime,
            }
        assignment[str(v)] = int(colors[0] + 1)
    used = [int(i + 1) for i, val in enumerate(y) if val == 1]
    objective = float(round(float(np.dot(y, np.array(weights, dtype=float))), 6))
    return {
        "status": "optimal",
        "chromatic_number": int(data["meta_parameters"]["chromatic_number"]),
        "number_of_used_colors": int(sum(y)),
        "used_colors": used,
        "objective_value": objective,
        "objective_exact": objective,
        "color_assignment": assignment,
        "solve_method": "scipy_milp_graph_coloring_optimization",
        "runtime_seconds": runtime,
    }


def main() -> None:
    base = Path(__file__).resolve().parent
    data = json.loads((base / "instance_data.json").read_text(encoding="utf-8"))
    variant = data["task_variant"]
    if variant in {"decision", "precolored_decision"}:
        sol = solve_decision(data)
    else:
        sol = solve_optimization(data)
    (base / "solution_ref.json").write_text(json.dumps(sol, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
