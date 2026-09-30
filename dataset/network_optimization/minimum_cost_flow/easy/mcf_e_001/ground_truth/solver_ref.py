#!/usr/bin/env python3
import json
import os
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "instance_data.json"), "r", encoding="utf-8") as f:
    data = json.load(f)

nodes = [int(x) for x in data["nodes"]]
supply = {int(k): float(v) for k, v in data["supply"].items()}
arcs = [(int(a["from"]), int(a["to"])) for a in data["arcs"]]
cap = {(int(a["from"]), int(a["to"])): float(a["capacity"]) for a in data["arcs"]}
cost = {(int(a["from"]), int(a["to"])): float(a["cost"]) for a in data["arcs"]}

def solve_with_gurobi():
    import gurobipy as gp
    from gurobipy import GRB

    m = gp.Model("minimum_cost_flow")
    m.setParam("OutputFlag", 0)

    x = {
        (i, j): m.addVar(lb=0.0, ub=cap[(i, j)], vtype=GRB.CONTINUOUS, name=f"x_{i}_{j}")
        for (i, j) in arcs
    }
    m.setObjective(gp.quicksum(cost[(i, j)] * x[(i, j)] for (i, j) in arcs), GRB.MINIMIZE)
    for i in nodes:
        outflow = gp.quicksum(x[(u, v)] for (u, v) in arcs if u == i)
        inflow = gp.quicksum(x[(u, v)] for (u, v) in arcs if v == i)
        m.addConstr(outflow - inflow == supply[i], name=f"balance_{i}")
    m.optimize()
    if m.Status != GRB.OPTIMAL:
        raise RuntimeError(f"Gurobi ended with status {m.Status}")
    flows = {(i, j): float(x[(i, j)].X) for (i, j) in arcs}
    return float(m.ObjVal), flows, "gurobi_lp_mcf", "Gurobi"

def solve_with_scipy():
    from scipy.optimize import linprog

    var_arcs = list(arcs)
    c = np.array([cost[a] for a in var_arcs], dtype=float)
    A_eq = np.zeros((len(nodes), len(var_arcs)), dtype=float)
    b_eq = np.array([supply[i] for i in nodes], dtype=float)

    for row, i in enumerate(nodes):
        for col, (u, v) in enumerate(var_arcs):
            if u == i:
                A_eq[row, col] += 1.0
            if v == i:
                A_eq[row, col] -= 1.0

    bounds = [(0.0, cap[a]) for a in var_arcs]
    result = linprog(c=c, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")
    if not result.success:
        raise RuntimeError(f"SciPy linprog failed: {result.message}")

    flows = {arc: float(result.x[idx]) for idx, arc in enumerate(var_arcs)}
    return float(result.fun), flows, "scipy_highs_exact_lp_mcf", "SciPy"

def write_solution(status, objective_value, flows, solve_method, solver_name, runtime_seconds):
    sol = {
        "status": status,
        "objective_value": float(objective_value),
        "objective_exact": float(objective_value),
        "flows": {f"{i}_{j}": float(flows.get((i, j), 0.0)) for (i, j) in arcs},
        "runtime_seconds": float(runtime_seconds),
        "solve_method": solve_method,
        "solver_used": solver_name,
        "solver": solver_name,
        "solver_policy": "gurobi_first_then_exact_scipy_linprog",
    }
    with open(os.path.join(HERE, "solution_ref.json"), "w", encoding="utf-8") as f:
        json.dump(sol, f, indent=2)

start = time.time()
try:
    objective_value, flows, solve_method, solver_name = solve_with_gurobi()
except Exception:
    objective_value, flows, solve_method, solver_name = solve_with_scipy()
runtime_seconds = time.time() - start
write_solution("optimal", objective_value, flows, solve_method, solver_name, runtime_seconds)
