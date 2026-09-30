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


TIME_LIMIT_SECONDS = 240.0


def normalize_objective(value: float):
    rounded = round(float(value))
    if abs(float(value) - rounded) <= 1e-6:
        return int(rounded)
    return float(value)


def package_solution(generators, periods, generation, commitment, startup, shutdown, runtime: float, objective_value: float, solve_method: str) -> dict:
    return {
        "status": "optimal",
        "objective": normalize_objective(objective_value),
        "objective_exact": float(objective_value),
        "runtime_seconds": runtime,
        "generation": generation,
        "commitment": commitment,
        "startup": startup,
        "shutdown": shutdown,
        "period_total_generation": {
            t: round(sum(generation[g][t] for g in generators), 6)
            for t in periods
        },
        "solve_method": solve_method,
    }


def solve_with_gurobi(data: dict) -> dict | None:
    if gp is None:
        return None
    G = data["sets"]["generators"]
    T = data["sets"]["periods"]
    init_u = data["initial_status"]
    init_p = data["initial_output"]
    start = time.perf_counter()
    try:
        model = gp.Model("educ_medium")
        model.Params.OutputFlag = 0
        model.Params.TimeLimit = TIME_LIMIT_SECONDS
        model.Params.MIPGap = 0.0

        p = {(g, t): model.addVar(lb=0.0, ub=float(data["pmax"][g]), vtype=GRB.CONTINUOUS, name=f"p_{g}_{t}") for g in G for t in T}
        u = {(g, t): model.addVar(vtype=GRB.BINARY, name=f"u_{g}_{t}") for g in G for t in T}
        v = {(g, t): model.addVar(vtype=GRB.BINARY, name=f"v_{g}_{t}") for g in G for t in T}
        w = {(g, t): model.addVar(vtype=GRB.BINARY, name=f"w_{g}_{t}") for g in G for t in T}

        model.setObjective(
            gp.quicksum(
                float(data["cost"][g]) * p[g, t]
                + float(data["startup_cost"][g]) * v[g, t]
                + float(data["shutdown_cost"][g]) * w[g, t]
                for g in G for t in T
            ),
            GRB.MINIMIZE,
        )

        for t in T:
            model.addConstr(gp.quicksum(p[g, t] for g in G) == float(data["demand"][t]), name=f"demand_{t}")

        for g in G:
            pmin = float(data["pmin"][g])
            pmax = float(data["pmax"][g])
            for t in T:
                model.addConstr(p[g, t] >= pmin * u[g, t], name=f"min_{g}_{t}")
                model.addConstr(p[g, t] <= pmax * u[g, t], name=f"max_{g}_{t}")

        for g in G:
            for k, t in enumerate(T):
                if k == 0:
                    model.addConstr(u[g, t] - v[g, t] + w[g, t] == float(init_u[g]), name=f"transition_{g}_{t}")
                else:
                    model.addConstr(u[g, t] - u[g, T[k - 1]] - v[g, t] + w[g, t] == 0.0, name=f"transition_{g}_{t}")

        for g in G:
            ru = float(data["ramp_up"][g])
            rd = float(data["ramp_down"][g])
            for k, t in enumerate(T):
                if k == 0:
                    model.addConstr(p[g, t] <= float(init_p[g]) + ru, name=f"ramp_up_{g}_{t}")
                    model.addConstr(float(init_p[g]) - p[g, t] <= rd, name=f"ramp_down_{g}_{t}")
                else:
                    model.addConstr(p[g, t] - p[g, T[k - 1]] <= ru, name=f"ramp_up_{g}_{t}")
                    model.addConstr(p[g, T[k - 1]] - p[g, t] <= rd, name=f"ramp_down_{g}_{t}")

        for g in G:
            UT = int(data["min_up"][g])
            if UT > 1:
                for start_idx in range(len(T) - UT + 1):
                    model.addConstr(
                        gp.quicksum(u[g, T[j]] for j in range(start_idx, start_idx + UT)) >= float(UT) * v[g, T[start_idx]],
                        name=f"min_up_{g}_{start_idx}",
                    )

        for g in G:
            DT = int(data["min_down"][g])
            if DT > 1:
                for start_idx in range(len(T) - DT + 1):
                    model.addConstr(
                        gp.quicksum(u[g, T[j]] for j in range(start_idx, start_idx + DT)) <= float(DT) * (1.0 - w[g, T[start_idx]]),
                        name=f"min_down_{g}_{start_idx}",
                    )

        model.optimize()
        runtime = time.perf_counter() - start
        if model.Status != GRB.OPTIMAL:
            return None

        generation = {g: {t: round(float(p[g, t].X), 6) for t in T} for g in G}
        commitment = {g: {t: int(round(float(u[g, t].X))) for t in T} for g in G}
        startup = {g: {t: int(round(float(v[g, t].X))) for t in T} for g in G}
        shutdown = {g: {t: int(round(float(w[g, t].X))) for t in T} for g in G}
        return package_solution(G, T, generation, commitment, startup, shutdown, runtime, float(model.ObjVal), "gurobi_milp_educ")
    except gp.GurobiError:
        return None


def solve_with_scipy(data: dict) -> dict:
    G = data["sets"]["generators"]
    T = data["sets"]["periods"]
    init_u = data["initial_status"]
    init_p = data["initial_output"]

    p_idx, u_idx, v_idx, w_idx = {}, {}, {}, {}
    idx = 0
    for g in G:
        for t in T:
            p_idx[(g, t)] = idx; idx += 1
    for g in G:
        for t in T:
            u_idx[(g, t)] = idx; idx += 1
    for g in G:
        for t in T:
            v_idx[(g, t)] = idx; idx += 1
    for g in G:
        for t in T:
            w_idx[(g, t)] = idx; idx += 1
    n = idx

    c = np.zeros(n, dtype=float)
    lb = np.zeros(n, dtype=float)
    ub = np.full(n, np.inf, dtype=float)
    integrality = np.zeros(n, dtype=int)

    for g in G:
        for t in T:
            c[p_idx[(g,t)]] = float(data["cost"][g])
            c[v_idx[(g,t)]] = float(data["startup_cost"][g])
            c[w_idx[(g,t)]] = float(data["shutdown_cost"][g])
            ub[p_idx[(g,t)]] = float(data["pmax"][g])
            ub[u_idx[(g,t)]] = 1.0
            ub[v_idx[(g,t)]] = 1.0
            ub[w_idx[(g,t)]] = 1.0
            integrality[u_idx[(g,t)]] = 1
            integrality[v_idx[(g,t)]] = 1
            integrality[w_idx[(g,t)]] = 1

    rows, lower, upper = [], [], []

    for t in T:
        row = np.zeros(n, dtype=float)
        for g in G:
            row[p_idx[(g,t)]] = 1.0
        d = float(data["demand"][t])
        rows.append(row); lower.append(d); upper.append(d)

    for g in G:
        pmin = float(data["pmin"][g]); pmax = float(data["pmax"][g])
        for t in T:
            row = np.zeros(n, dtype=float)
            row[p_idx[(g,t)]] = 1.0
            row[u_idx[(g,t)]] = -pmin
            rows.append(row); lower.append(0.0); upper.append(np.inf)

            row = np.zeros(n, dtype=float)
            row[p_idx[(g,t)]] = 1.0
            row[u_idx[(g,t)]] = -pmax
            rows.append(row); lower.append(-np.inf); upper.append(0.0)

    for g in G:
        for k, t in enumerate(T):
            row = np.zeros(n, dtype=float)
            row[u_idx[(g,t)]] = 1.0
            row[v_idx[(g,t)]] = -1.0
            row[w_idx[(g,t)]] = 1.0
            if k == 0:
                rhs = float(init_u[g])
            else:
                row[u_idx[(g, T[k-1])]] = -1.0
                rhs = 0.0
            rows.append(row); lower.append(rhs); upper.append(rhs)

    for g in G:
        ru = float(data["ramp_up"][g]); rd = float(data["ramp_down"][g])
        for k, t in enumerate(T):
            row = np.zeros(n, dtype=float)
            row[p_idx[(g,t)]] = 1.0
            if k == 0:
                rhs = ru + float(init_p[g])
            else:
                row[p_idx[(g, T[k-1])]] = -1.0
                rhs = ru
            rows.append(row); lower.append(-np.inf); upper.append(rhs)

            row = np.zeros(n, dtype=float)
            row[p_idx[(g,t)]] = -1.0
            if k == 0:
                rhs = rd - float(init_p[g])
            else:
                row[p_idx[(g, T[k-1])]] = 1.0
                rhs = rd
            rows.append(row); lower.append(-np.inf); upper.append(rhs)

    for g in G:
        UT = int(data["min_up"][g])
        if UT > 1:
            for start in range(len(T) - UT + 1):
                row = np.zeros(n, dtype=float)
                row[v_idx[(g, T[start])]] = -float(UT)
                for j in range(start, start + UT):
                    row[u_idx[(g, T[j])]] = 1.0
                rows.append(row); lower.append(0.0); upper.append(np.inf)

    for g in G:
        DT = int(data["min_down"][g])
        if DT > 1:
            for start in range(len(T) - DT + 1):
                row = np.zeros(n, dtype=float)
                row[w_idx[(g, T[start])]] = float(DT)
                for j in range(start, start + DT):
                    row[u_idx[(g, T[j])]] = 1.0
                rows.append(row); lower.append(-np.inf); upper.append(float(DT))

    constraints = LinearConstraint(np.array(rows), np.array(lower), np.array(upper))
    bounds = Bounds(lb, ub)

    start_time = time.perf_counter()
    res = milp(c=c, integrality=integrality, bounds=bounds, constraints=constraints)
    runtime = time.perf_counter() - start_time

    if res.status != 0 or res.x is None:
        return {
            "status": "infeasible_or_no_optimal_solution",
            "solver_status": int(res.status),
            "message": str(res.message),
            "runtime_seconds": runtime,
        }

    x = res.x
    generation = {g: {t: round(float(x[p_idx[(g,t)]]), 6) for t in T} for g in G}
    commitment = {g: {t: int(round(float(x[u_idx[(g,t)]]))) for t in T} for g in G}
    startup = {g: {t: int(round(float(x[v_idx[(g,t)]]))) for t in T} for g in G}
    shutdown = {g: {t: int(round(float(x[w_idx[(g,t)]]))) for t in T} for g in G}
    return package_solution(G, T, generation, commitment, startup, shutdown, runtime, float(res.fun), "scipy_milp_educ")


def solve_instance(data: dict) -> dict:
    gurobi_solution = solve_with_gurobi(data)
    if gurobi_solution is not None:
        return gurobi_solution
    return solve_with_scipy(data)


def main() -> None:
    base = Path(__file__).resolve().parent
    data = json.loads((base / "instance_data.json").read_text(encoding="utf-8"))
    sol = solve_instance(data)
    (base / "solution_ref.json").write_text(json.dumps(sol, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
