import json
import os
import time
from collections import deque, defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "instance_data.json"), "r", encoding="utf-8") as f:
    data = json.load(f)

nodes = [int(v) for v in data["nodes"]]
s = int(data["source"])
t = int(data["sink"])
arcs = data["arcs"]

cap = {}
for a in arcs:
    i = int(a["from"])
    j = int(a["to"])
    cap[(i, j)] = float(a["capacity"])

def compute_min_cut(flow):
    eps = 1e-9
    adj = defaultdict(list)
    for (i, j), uij in cap.items():
        f_ij = flow[(i, j)]
        if uij - f_ij > eps:
            adj[i].append(j)
        if f_ij > eps:
            adj[j].append(i)

    reachable = {s}
    q = deque([s])
    while q:
        u = q.popleft()
        for v in adj[u]:
            if v not in reachable:
                reachable.add(v)
                q.append(v)

    cut_s = sorted(reachable)
    cut_t = sorted(v for v in nodes if v not in reachable)
    cut_value = 0.0
    for (i, j), uij in cap.items():
        if i in reachable and j not in reachable:
            cut_value += uij
    return cut_s, cut_t, float(cut_value)

def solve_with_gurobi():
    import gurobipy as gp
    from gurobipy import GRB

    m = gp.Model("max_flow")
    m.setParam("OutputFlag", 0)
    fvar = {}
    for (i, j), uij in cap.items():
        fvar[(i, j)] = m.addVar(lb=0.0, ub=uij, vtype=GRB.CONTINUOUS, name=f"f_{i}_{j}")
    m.setObjective(gp.quicksum(fvar[(s, j)] for (i, j) in cap.keys() if i == s), GRB.MAXIMIZE)
    for v in nodes:
        if v in (s, t):
            continue
        inflow = gp.quicksum(fvar[(i, v)] for (i, j) in cap.keys() if j == v)
        outflow = gp.quicksum(fvar[(v, j)] for (i, j) in cap.keys() if i == v)
        m.addConstr(inflow == outflow, name=f"flow_conservation_{v}")
    m.optimize()
    if m.status != GRB.OPTIMAL:
        raise RuntimeError(f"Gurobi ended with status {m.status}")
    flow = {(i, j): float(fvar[(i, j)].X) for (i, j) in cap.keys()}
    max_flow_value = float(sum(flow[(s, j)] for (i, j) in cap.keys() if i == s))
    return max_flow_value, flow, "gurobi_lp_max_flow", "Gurobi"

def solve_with_scipy():
    from scipy.optimize import linprog

    var_arcs = list(cap.keys())
    c = np.array([-1.0 if i == s else 0.0 for (i, j) in var_arcs], dtype=float)
    eq_rows = [v for v in nodes if v not in (s, t)]
    A_eq = np.zeros((len(eq_rows), len(var_arcs)), dtype=float)
    b_eq = np.zeros(len(eq_rows), dtype=float)
    for row, v in enumerate(eq_rows):
        for col, (i, j) in enumerate(var_arcs):
            if j == v:
                A_eq[row, col] += 1.0
            if i == v:
                A_eq[row, col] -= 1.0
    bounds = [(0.0, cap[arc]) for arc in var_arcs]
    result = linprog(c=c, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")
    if not result.success:
        raise RuntimeError(f"SciPy linprog failed: {result.message}")
    flow = {arc: float(result.x[idx]) for idx, arc in enumerate(var_arcs)}
    max_flow_value = float(sum(flow[(s, j)] for (i, j) in cap.keys() if i == s))
    return max_flow_value, flow, "scipy_highs_exact_lp_max_flow", "SciPy"

def write_solution(status, max_flow_value, flow, solve_method, solver_name, runtime_seconds):
    cut_s, cut_t, cut_value = compute_min_cut(flow)
    sol = {
        "status": status,
        "objective_value": float(max_flow_value),
        "objective_exact": float(max_flow_value),
        "max_flow_value": float(max_flow_value),
        "min_cut_value": float(cut_value),
        "min_cut_S": cut_s,
        "min_cut_T": cut_t,
        "flows": {f"{i}_{j}": float(flow[(i, j)]) for (i, j) in cap.keys()},
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
    max_flow_value, flow, solve_method, solver_name = solve_with_gurobi()
except Exception:
    max_flow_value, flow, solve_method, solver_name = solve_with_scipy()
runtime_seconds = time.time() - start
write_solution("optimal", max_flow_value, flow, solve_method, solver_name, runtime_seconds)
