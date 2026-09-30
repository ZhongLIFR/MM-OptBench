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


TIME_LIMIT_SECONDS = 300.0


def normalize_objective(value: float):
    rounded = round(float(value))
    if abs(float(value) - rounded) <= 1e-6:
        return int(rounded)
    return float(value)


def package_solution(G, T, generation, commitment, startup, runtime: float, objective_value: float, solve_method: str) -> dict:
    period_total_generation = {t: round(sum(generation[g][t] for g in G), 6) for t in T}
    online_units_by_period = {t: [g for g in G if commitment[g][t] == 1] for t in T}
    startup_periods = {g: [t for t in T if startup[g][t] == 1] for g in G}
    return {
        "status": "optimal",
        "objective": normalize_objective(objective_value),
        "objective_exact": float(objective_value),
        "runtime_seconds": runtime,
        "generation": generation,
        "commitment": commitment,
        "startup": startup,
        "period_total_generation": period_total_generation,
        "online_units_by_period": online_units_by_period,
        "startup_periods": startup_periods,
        "solve_method": solve_method,
    }


def solve_with_gurobi(data: dict) -> dict | None:
    if gp is None:
        return None
    G = data["sets"]["generators"]
    T = data["sets"]["periods"]
    initial_status = data["initial_status"]
    initial_output = data["initial_output"]
    start = time.perf_counter()
    try:
        model = gp.Model("educ_hard")
        model.Params.OutputFlag = 0
        model.Params.TimeLimit = TIME_LIMIT_SECONDS
        model.Params.MIPGap = 0.0

        p = {(g, t): model.addVar(lb=0.0, ub=float(data["pmax"][g]), vtype=GRB.CONTINUOUS, name=f"p_{g}_{t}") for g in G for t in T}
        u = {(g, t): model.addVar(vtype=GRB.BINARY, name=f"u_{g}_{t}") for g in G for t in T}
        v = {(g, t): model.addVar(vtype=GRB.BINARY, name=f"v_{g}_{t}") for g in G for t in T}

        model.setObjective(
            gp.quicksum(
                float(data["cost"][g]) * p[g, t] + float(data["startup_cost"][g]) * v[g, t]
                for g in G for t in T
            ),
            GRB.MINIMIZE,
        )

        for t in T:
            model.addConstr(gp.quicksum(p[g, t] for g in G) == float(data["demand"][t]), name=f"demand_{t}")

        for g in G:
            for t in T:
                model.addConstr(p[g, t] >= float(data["pmin"][g]) * u[g, t], name=f"min_{g}_{t}")
                model.addConstr(p[g, t] <= float(data["pmax"][g]) * u[g, t], name=f"max_{g}_{t}")

        for g in G:
            for k, t in enumerate(T):
                prev_u = float(initial_status[g]) if k == 0 else u[g, T[k - 1]]
                model.addConstr(v[g, t] >= u[g, t] - prev_u, name=f"startup_{g}_{t}")

        for g in G:
            ru = float(data["ramp_up"][g])
            rd = float(data["ramp_down"][g])
            model.addConstr(p[g, T[0]] <= float(initial_output[g]) + ru, name=f"ramp_up_{g}_{T[0]}")
            model.addConstr(float(initial_output[g]) - p[g, T[0]] <= rd, name=f"ramp_down_{g}_{T[0]}")
            for k in range(1, len(T)):
                t = T[k]
                tm = T[k - 1]
                model.addConstr(p[g, t] - p[g, tm] <= ru, name=f"ramp_up_{g}_{t}")
                model.addConstr(p[g, tm] - p[g, t] <= rd, name=f"ramp_down_{g}_{t}")

        for g in G:
            UT = int(data["min_up"][g])
            if UT > 0:
                for k, t in enumerate(T):
                    if k + UT > len(T):
                        continue
                    model.addConstr(
                        gp.quicksum(u[g, T[kk]] for kk in range(k, k + UT)) >= float(UT) * v[g, t],
                        name=f"min_up_{g}_{t}",
                    )

        for g in G:
            DT = int(data["min_down"][g])
            if DT > 0:
                for k, t in enumerate(T):
                    if k + DT > len(T):
                        continue
                    expr = gp.LinExpr()
                    for kk in range(k, k + DT):
                        expr += -u[g, T[kk]]
                    if k == 0:
                        expr += float(DT) * u[g, t]
                        model.addConstr(expr >= -float(DT) * float(initial_status[g]), name=f"min_down_{g}_{t}")
                    else:
                        expr += -float(DT) * u[g, T[k - 1]]
                        expr += float(DT) * u[g, t]
                        model.addConstr(expr >= -float(DT), name=f"min_down_{g}_{t}")

        model.optimize()
        runtime = time.perf_counter() - start
        if model.Status != GRB.OPTIMAL:
            return None

        generation = {g: {t: round(float(p[g, t].X), 6) for t in T} for g in G}
        commitment = {g: {t: int(round(float(u[g, t].X))) for t in T} for g in G}
        startup = {g: {t: int(round(float(v[g, t].X))) for t in T} for g in G}
        return package_solution(G, T, generation, commitment, startup, runtime, float(model.ObjVal), "gurobi_milp_educ")
    except gp.GurobiError:
        return None


def solve_with_scipy(data: dict) -> dict:
    G = data["sets"]["generators"]
    T = data["sets"]["periods"]
    initial_status = data["initial_status"]
    initial_output = data["initial_output"]

    p_idx = {}
    u_idx = {}
    v_idx = {}
    idx = 0
    for g in G:
        for t in T:
            p_idx[(g, t)] = idx
            idx += 1
    for g in G:
        for t in T:
            u_idx[(g, t)] = idx
            idx += 1
    for g in G:
        for t in T:
            v_idx[(g, t)] = idx
            idx += 1
    n = idx

    c = np.zeros(n, dtype=float)
    lb = np.zeros(n, dtype=float)
    ub = np.full(n, np.inf, dtype=float)
    integrality = np.zeros(n, dtype=int)

    for g in G:
        for t in T:
            c[p_idx[(g, t)]] = float(data["cost"][g])
            ub[p_idx[(g, t)]] = float(data["pmax"][g])
            ub[u_idx[(g, t)]] = 1.0
            ub[v_idx[(g, t)]] = 1.0
            integrality[u_idx[(g, t)]] = 1
            integrality[v_idx[(g, t)]] = 1
            c[v_idx[(g, t)]] = float(data["startup_cost"][g])

    rows = []
    lower = []
    upper = []

    for t in T:
        row = np.zeros(n, dtype=float)
        for g in G:
            row[p_idx[(g, t)]] = 1.0
        d = float(data["demand"][t])
        rows.append(row); lower.append(d); upper.append(d)

    for g in G:
        for t in T:
            row = np.zeros(n, dtype=float)
            row[p_idx[(g, t)]] = 1.0
            row[u_idx[(g, t)]] = -float(data["pmin"][g])
            rows.append(row); lower.append(0.0); upper.append(np.inf)

            row = np.zeros(n, dtype=float)
            row[p_idx[(g, t)]] = 1.0
            row[u_idx[(g, t)]] = -float(data["pmax"][g])
            rows.append(row); lower.append(-np.inf); upper.append(0.0)

    for g in G:
        for k, t in enumerate(T):
            row = np.zeros(n, dtype=float)
            row[v_idx[(g, t)]] = 1.0
            row[u_idx[(g, t)]] = -1.0
            if k == 0:
                rhs = -float(initial_status[g])
            else:
                row[u_idx[(g, T[k-1])]] = 1.0
                rhs = 0.0
            rows.append(row); lower.append(rhs); upper.append(np.inf)

    for g in G:
        ru = float(data["ramp_up"][g]); rd = float(data["ramp_down"][g])
        row = np.zeros(n, dtype=float)
        row[p_idx[(g, T[0])]] = 1.0
        rows.append(row); lower.append(-np.inf); upper.append(float(initial_output[g]) + ru)

        row = np.zeros(n, dtype=float)
        row[p_idx[(g, T[0])]] = -1.0
        rows.append(row); lower.append(-np.inf); upper.append(rd - float(initial_output[g]))

        for k in range(1, len(T)):
            t = T[k]; tm = T[k-1]
            row = np.zeros(n, dtype=float)
            row[p_idx[(g, t)]] = 1.0
            row[p_idx[(g, tm)]] = -1.0
            rows.append(row); lower.append(-np.inf); upper.append(ru)

            row = np.zeros(n, dtype=float)
            row[p_idx[(g, tm)]] = 1.0
            row[p_idx[(g, t)]] = -1.0
            rows.append(row); lower.append(-np.inf); upper.append(rd)

    for g in G:
        UT = int(data["min_up"][g])
        if UT > 0:
            for k, t in enumerate(T):
                if k + UT > len(T):
                    continue
                row = np.zeros(n, dtype=float)
                for kk in range(k, k + UT):
                    row[u_idx[(g, T[kk])]] = 1.0
                row[v_idx[(g, t)]] = -float(UT)
                rows.append(row); lower.append(0.0); upper.append(np.inf)

    for g in G:
        DT = int(data["min_down"][g])
        if DT > 0:
            for k, t in enumerate(T):
                if k + DT > len(T):
                    continue
                row = np.zeros(n, dtype=float)
                for kk in range(k, k + DT):
                    row[u_idx[(g, T[kk])]] = -1.0
                if k == 0:
                    row[u_idx[(g, t)]] += float(DT)
                    rows.append(row); lower.append(-float(DT) * float(initial_status[g])); upper.append(np.inf)
                else:
                    row[u_idx[(g, T[k-1])]] += -float(DT)
                    row[u_idx[(g, t)]] += float(DT)
                    rows.append(row); lower.append(-float(DT)); upper.append(np.inf)

    constraints = LinearConstraint(np.array(rows), np.array(lower), np.array(upper))
    bounds = Bounds(lb, ub)

    start = time.perf_counter()
    res = milp(c=c, integrality=integrality, bounds=bounds, constraints=constraints)
    runtime = time.perf_counter() - start

    if res.status != 0 or res.x is None:
        return {
            "status": "infeasible_or_no_optimal_solution",
            "solver_status": int(res.status),
            "message": str(res.message),
            "runtime_seconds": runtime,
        }

    sol = res.x
    generation = {g: {t: round(float(sol[p_idx[(g, t)]]), 6) for t in T} for g in G}
    commitment = {g: {t: int(round(float(sol[u_idx[(g, t)]]))) for t in T} for g in G}
    startup = {g: {t: int(round(float(sol[v_idx[(g, t)]]))) for t in T} for g in G}
    return package_solution(G, T, generation, commitment, startup, runtime, float(res.fun), "scipy_milp_educ")


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
