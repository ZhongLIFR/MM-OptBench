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
except Exception:
    gp = None
    GRB = None


def _package_solution(values, weights, capacities, x, runtime_seconds, solve_method):
    used = (weights.T @ x).astype(int)
    slacks = (capacities - used).astype(int)
    binding = [int(i + 1) for i, s in enumerate(slacks) if s == 0]
    objective = int(round(values @ x))
    return {
        "status": "optimal",
        "objective": objective,
        "objective_exact": objective,
        "selected_items": [int(i + 1) for i, val in enumerate(x) if val == 1],
        "decision_variables": {f"x_{i+1}": int(x[i]) for i in range(len(x))},
        "resource_usage": {f"R{r+1}": int(used[r]) for r in range(weights.shape[1])},
        "resource_limits": {f"R{r+1}": int(capacities[r]) for r in range(weights.shape[1])},
        "resource_slack": {f"R{r+1}": int(slacks[r]) for r in range(weights.shape[1])},
        "binding_constraints": binding,
        "binding_constraint_count": len(binding),
        "solve_method": solve_method,
        "runtime_seconds": runtime_seconds,
    }


def _solve_with_gurobi(values, weights, capacities):
    if gp is None:
        return None
    start = time.perf_counter()
    n, m = weights.shape
    model = gp.Model("mdkp")
    model.Params.OutputFlag = 0
    model.Params.TimeLimit = 30.0
    x = model.addVars(n, vtype=GRB.BINARY, name="x")
    model.setObjective(gp.quicksum(float(values[i]) * x[i] for i in range(n)), GRB.MAXIMIZE)
    for r in range(m):
        model.addConstr(gp.quicksum(float(weights[i, r]) * x[i] for i in range(n)) <= float(capacities[r]), name=f"cap_{r+1}")
    model.optimize()
    if model.Status != GRB.OPTIMAL:
        return None
    sol = np.array([int(round(x[i].X)) for i in range(n)], dtype=int)
    return _package_solution(values, weights, capacities, sol, time.perf_counter() - start, "gurobi_milp_mdkp")


def _solve_with_scipy(values, weights, capacities):
    start = time.perf_counter()
    n, m = weights.shape
    c = -values
    constraints = LinearConstraint(weights.T, lb=-np.inf * np.ones(m), ub=capacities)
    bounds = Bounds(lb=np.zeros(n), ub=np.ones(n))
    integrality = np.ones(n, dtype=int)
    res = milp(c=c, constraints=constraints, bounds=bounds, integrality=integrality, options={"time_limit": 30.0})
    if not res.success or res.x is None:
        return None
    x = np.rint(res.x).astype(int)
    return _package_solution(values, weights, capacities, x, time.perf_counter() - start, "scipy.optimize.milp")


def solve_instance(data: dict) -> dict:
    values = np.array(data["values"], dtype=float)
    weights = np.array(data["weights"], dtype=float)
    capacities = np.array(data["capacities"], dtype=float)
    gurobi_sol = _solve_with_gurobi(values, weights, capacities)
    if gurobi_sol is not None:
        return gurobi_sol
    scipy_sol = _solve_with_scipy(values, weights, capacities)
    if scipy_sol is not None:
        return scipy_sol
    return {
        "status": "infeasible_or_no_optimal_solution",
        "objective": None,
        "objective_exact": None,
        "runtime_seconds": None,
        "solve_method": "none",
    }


def main() -> None:
    base = Path(__file__).resolve().parent
    data = json.loads((base / "instance_data.json").read_text(encoding="utf-8"))
    sol = solve_instance(data)
    (base / "solution_ref.json").write_text(json.dumps(sol, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
