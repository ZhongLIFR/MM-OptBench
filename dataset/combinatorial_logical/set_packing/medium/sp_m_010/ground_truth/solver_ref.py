#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp


def summarize_solution(weights: np.ndarray, incidence: np.ndarray, x: np.ndarray, groups: list[str], items: list[str], method: str, runtime_seconds: float) -> dict:
    selected = [groups[i] for i, val in enumerate(x.tolist()) if val == 1]
    objective = int(round(float(np.dot(weights, x))))
    usage = incidence @ x
    binding = [items[i] for i, val in enumerate(usage.tolist()) if int(round(val)) == 1]
    return {
        "status": "optimal",
        "is_feasible": True,
        "objective_value": objective,
        "objective_exact": objective,
        "selected_groups": selected,
        "selected_group_count": len(selected),
        "binding_constraints_count": len(binding),
        "binding_items": binding,
        "solve_method": method,
        "runtime_seconds": round(runtime_seconds, 6),
    }


def build_milp(weights: np.ndarray, incidence: np.ndarray):
    m, n = incidence.shape
    c = -weights.astype(float)
    A = incidence.astype(float)
    lb = -np.inf * np.ones(m)
    ub = np.ones(m)
    constraints = LinearConstraint(A, lb=lb, ub=ub)
    bounds = Bounds(lb=np.zeros(n), ub=np.ones(n))
    integrality = np.ones(n, dtype=int)
    return c, constraints, bounds, integrality


def solve_with_gurobi(data: dict) -> dict | None:
    try:
        import gurobipy as gp
        from gurobipy import GRB
    except Exception:
        return None

    weights = np.array(data["weights"], dtype=float)
    incidence = np.array(data["incidence_matrix"], dtype=float)
    groups = data["sets"]["candidate_groups"]
    items = data["sets"]["items"]
    m, n = incidence.shape
    start = time.time()
    try:
        model = gp.Model("set_packing")
        model.Params.OutputFlag = 0
        x = model.addVars(n, vtype=GRB.BINARY, name="x")
        for i in range(m):
            model.addConstr(gp.quicksum(float(incidence[i, j]) * x[j] for j in range(n)) <= 1.0, name=f"pack_{i}")
        model.setObjective(gp.quicksum(float(weights[j]) * x[j] for j in range(n)), GRB.MAXIMIZE)
        model.optimize()
        runtime = time.time() - start
        if model.Status == GRB.OPTIMAL:
            sol = np.array([int(round(x[j].X)) for j in range(n)], dtype=int)
            return summarize_solution(weights, incidence, sol, groups, items, "gurobi_milp_set_packing", runtime)
        if model.Status == GRB.INFEASIBLE:
            return {"status": "infeasible", "is_feasible": False, "solve_method": "gurobi_milp_set_packing", "runtime_seconds": round(runtime, 6)}
    except Exception:
        return None
    return None


def solve_with_scipy(data: dict) -> dict:
    start = time.time()
    weights = np.array(data["weights"], dtype=float)
    incidence = np.array(data["incidence_matrix"], dtype=float)
    groups = data["sets"]["candidate_groups"]
    items = data["sets"]["items"]
    c, constraints, bounds, integrality = build_milp(weights, incidence)
    res = milp(c=c, constraints=constraints, bounds=bounds, integrality=integrality, options={"time_limit": 30.0})
    runtime = time.time() - start
    if not res.success or res.x is None:
        return {"status": "infeasible", "is_feasible": False, "solve_method": "scipy.optimize.milp", "runtime_seconds": round(runtime, 6)}
    x = np.rint(res.x).astype(int)
    return summarize_solution(weights, incidence, x, groups, items, "scipy.optimize.milp", runtime)


def solve_instance(data: dict) -> dict:
    gurobi_result = solve_with_gurobi(data)
    if gurobi_result is not None and gurobi_result.get("status") == "optimal":
        return gurobi_result
    scipy_result = solve_with_scipy(data)
    if scipy_result.get("status") == "optimal":
        return scipy_result
    if gurobi_result is not None:
        return gurobi_result
    return scipy_result


def main() -> None:
    base = Path(__file__).resolve().parent
    data = json.loads((base / "instance_data.json").read_text(encoding="utf-8"))
    sol = solve_instance(data)
    (base / "solution_ref.json").write_text(json.dumps(sol, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
