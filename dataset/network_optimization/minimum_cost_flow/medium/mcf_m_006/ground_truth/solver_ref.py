import json
import os
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "instance_data.json"), "r", encoding="utf-8") as f:
    data = json.load(f)

nodes = data["nodes"]
supply = {int(k): float(v) for k, v in data["supply"].items()}
arcs = data["arcs"]

def solve_with_gurobi():
    import gurobipy as gp
    from gurobipy import GRB

    m = gp.Model("minimum_cost_flow")
    m.Params.OutputFlag = 0

    x = {}
    for a in arcs:
        i, j = int(a["from"]), int(a["to"])
        x[(i, j)] = m.addVar(lb=0.0, ub=float(a["capacity"]), vtype=GRB.CONTINUOUS, name=f"x_{i}_{j}")

    for i in nodes:
        i = int(i)
        outflow = gp.quicksum(x[(int(a["from"]), int(a["to"]))] for a in arcs if int(a["from"]) == i)
        inflow = gp.quicksum(x[(int(a["from"]), int(a["to"]))] for a in arcs if int(a["to"]) == i)
        m.addConstr(outflow - inflow == supply[i], name=f"flow_{i}")

    m.setObjective(
        gp.quicksum(float(a["cost"]) * x[(int(a["from"]), int(a["to"]))] for a in arcs),
        GRB.MINIMIZE,
    )
    m.optimize()
    if m.Status != GRB.OPTIMAL:
        raise RuntimeError(f"Gurobi ended with status {m.Status}")

    flows = {
        (int(a["from"]), int(a["to"])): float(x[(int(a["from"]), int(a["to"]))].X)
        for a in arcs
    }
    return float(m.ObjVal), flows, "gurobi_lp_mcf", "Gurobi"

def solve_with_scipy():
    from scipy.optimize import linprog

    var_arcs = [(int(a["from"]), int(a["to"])) for a in arcs]
    c = np.array([float(a["cost"]) for a in arcs], dtype=float)
    A_eq = np.zeros((len(nodes), len(var_arcs)), dtype=float)
    b_eq = np.array([supply[int(i)] for i in nodes], dtype=float)

    for row, i in enumerate(nodes):
        i = int(i)
        for col, (u, v) in enumerate(var_arcs):
            if u == i:
                A_eq[row, col] += 1.0
            if v == i:
                A_eq[row, col] -= 1.0

    bounds = [(0.0, float(a["capacity"])) for a in arcs]
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
        "flows": {f"{int(a['from'])}_{int(a['to'])}": float(flows.get((int(a["from"]), int(a["to"])), 0.0)) for a in arcs},
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
