#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import math
import time
from pathlib import Path

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp


def summarize_solution(variables: list[str], x: np.ndarray, method: str, runtime_seconds: float) -> dict:
    return {
        "status": "feasible",
        "is_feasible": True,
        "assignment": {var: int(val) for var, val in zip(variables, x.tolist())},
        "true_variables": [var for var, val in zip(variables, x.tolist()) if val == 1],
        "false_variables": [var for var, val in zip(variables, x.tolist()) if val == 0],
        "solve_method": method,
        "runtime_seconds": round(runtime_seconds, 6),
    }


def build_model_arrays(data: dict):
    variables = data["sets"]["variables"]
    n = len(variables)
    index = {v: i for i, v in enumerate(variables)}
    A_rows = []
    lb = []
    ub = []

    for clause in data["clauses"]:
        row = [0.0] * n
        neg_count = 0
        for lit in clause["literals"]:
            j = index[lit["variable"]]
            if lit["sign"] == "+":
                row[j] += 1.0
            else:
                row[j] -= 1.0
                neg_count += 1
        A_rows.append(row)
        lb.append(1.0 - neg_count)
        ub.append(math.inf)

    for imp in data["implications"]:
        row = [0.0] * n
        row[index[imp["if_variable"]]] = 1.0
        row[index[imp["then_variable"]]] = -1.0
        A_rows.append(row)
        lb.append(-math.inf)
        ub.append(0.0)

    for group in data["at_most_one_groups"]:
        row = [0.0] * n
        for var in group["variables"]:
            row[index[var]] = 1.0
        A_rows.append(row)
        lb.append(-math.inf)
        ub.append(1.0)

    for con in data["cardinality_constraints"]:
        row = [0.0] * n
        for var in con["variables"]:
            row[index[var]] = 1.0
        A_rows.append(row)
        lb.append(-math.inf)
        ub.append(float(con["rhs"]))
    A = np.array(A_rows, dtype=float)
    constraints = LinearConstraint(A, lb=np.array(lb, dtype=float), ub=np.array(ub, dtype=float))
    bounds = Bounds(lb=np.zeros(n), ub=np.ones(n))
    integrality = np.ones(n, dtype=int)
    return variables, index, constraints, bounds, integrality


def solve_with_gurobi(data: dict) -> dict | None:
    try:
        import gurobipy as gp
        from gurobipy import GRB
    except Exception:
        return None

    variables = data["sets"]["variables"]
    n = len(variables)
    index = {v: i for i, v in enumerate(variables)}
    start = time.time()
    try:
        model = gp.Model("lcsm")
        model.Params.OutputFlag = 0
        x = model.addVars(n, vtype=GRB.BINARY, name="x")

        for clause in data["clauses"]:
            expr = gp.LinExpr()
            rhs_shift = 0.0
            for lit in clause["literals"]:
                j = index[lit["variable"]]
                if lit["sign"] == "+":
                    expr += x[j]
                else:
                    expr += -x[j]
                    rhs_shift -= 1.0
            model.addConstr(expr >= 1.0 + rhs_shift, name=clause["name"])

        for imp in data["implications"]:
            u = index[imp["if_variable"]]
            v = index[imp["then_variable"]]
            model.addConstr(x[u] - x[v] <= 0.0, name=imp["name"])

        for group in data["at_most_one_groups"]:
            model.addConstr(gp.quicksum(x[index[var]] for var in group["variables"]) <= 1.0, name=group["name"])

        for con in data["cardinality_constraints"]:
            model.addConstr(gp.quicksum(x[index[var]] for var in con["variables"]) <= float(con["rhs"]), name=con["name"])

        model.setObjective(gp.quicksum((j + 1) * x[j] for j in range(n)), GRB.MINIMIZE)
        model.optimize()
        runtime = time.time() - start
        if model.Status == GRB.OPTIMAL:
            sol = np.array([int(round(x[j].X)) for j in range(n)], dtype=int)
            return summarize_solution(variables, sol, "gurobi_milp_lcsm", runtime)
        if model.Status == GRB.INFEASIBLE:
            return {"status": "infeasible", "is_feasible": False, "solve_method": "gurobi_milp_lcsm", "runtime_seconds": round(runtime, 6)}
    except Exception:
        return None
    return None


def solve_with_scipy(data: dict) -> dict:
    variables, _, constraints, bounds, integrality = build_model_arrays(data)
    start = time.time()
    c = np.array([i + 1 for i in range(len(variables))], dtype=float)
    res = milp(c=c, constraints=constraints, bounds=bounds, integrality=integrality, options={"time_limit": 60.0})
    runtime = time.time() - start
    if not res.success or res.x is None:
        return {"status": "infeasible", "is_feasible": False, "solve_method": "scipy.optimize.milp", "runtime_seconds": round(runtime, 6)}
    x = np.rint(res.x).astype(int)
    return summarize_solution(variables, x, "scipy.optimize.milp", runtime)


def solve_instance(data: dict) -> dict:
    gurobi_result = solve_with_gurobi(data)
    if gurobi_result is not None and gurobi_result.get("is_feasible", False):
        return gurobi_result
    scipy_result = solve_with_scipy(data)
    if scipy_result.get("is_feasible", False):
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
