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


TIME_LIMIT_SECONDS = 180.0


def normalize_objective(value: float):
    rounded = round(float(value))
    if abs(float(value) - rounded) <= 1e-6:
        return int(rounded)
    return float(value)


def package_solution(data: dict, generators, periods, generation, commitment, startup, runtime: float, objective_value: float, solve_method: str) -> dict:
    period_total_generation = {
        t: round(sum(generation[g][t] for g in generators), 6)
        for t in periods
    }
    online_units_by_period = {
        t: [g for g in generators if commitment[g][t] == 1]
        for t in periods
    }
    startup_periods = {
        g: [t for t in periods if startup[g][t] == 1]
        for g in generators
    }
    binding_capacity_periods = {
        g: [t for t in periods if commitment[g][t] == 1 and abs(generation[g][t] - float(data["pmax"][g])) <= 1e-6]
        for g in generators
    }
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
        "binding_capacity_periods": binding_capacity_periods,
        "solve_method": solve_method,
    }


def solve_with_gurobi(data: dict) -> dict | None:
    if gp is None:
        return None
    generators = data["sets"]["generators"]
    periods = data["sets"]["periods"]
    initial_status = data["initial_status"]
    start = time.perf_counter()
    try:
        model = gp.Model("educ_easy")
        model.Params.OutputFlag = 0
        model.Params.TimeLimit = TIME_LIMIT_SECONDS
        model.Params.MIPGap = 0.0

        p = {(g, t): model.addVar(lb=0.0, ub=float(data["pmax"][g]), vtype=GRB.CONTINUOUS, name=f"p_{g}_{t}") for g in generators for t in periods}
        u = {(g, t): model.addVar(vtype=GRB.BINARY, name=f"u_{g}_{t}") for g in generators for t in periods}
        v = {(g, t): model.addVar(vtype=GRB.BINARY, name=f"v_{g}_{t}") for g in generators for t in periods}

        model.setObjective(
            gp.quicksum(
                float(data["cost"][g]) * p[g, t] + float(data["startup_cost"][g]) * v[g, t]
                for g in generators for t in periods
            ),
            GRB.MINIMIZE,
        )

        for t in periods:
            model.addConstr(gp.quicksum(p[g, t] for g in generators) == float(data["demand"][t]), name=f"demand_{t}")
        for g in generators:
            for t in periods:
                model.addConstr(p[g, t] >= float(data["pmin"][g]) * u[g, t], name=f"min_{g}_{t}")
                model.addConstr(p[g, t] <= float(data["pmax"][g]) * u[g, t], name=f"max_{g}_{t}")
        for g in generators:
            for k, t in enumerate(periods):
                prev_u = float(initial_status[g]) if k == 0 else u[g, periods[k - 1]]
                model.addConstr(v[g, t] >= u[g, t] - prev_u, name=f"startup_{g}_{t}")

        model.optimize()
        runtime = time.perf_counter() - start
        if model.Status != GRB.OPTIMAL:
            return None

        generation = {
            g: {t: round(float(p[g, t].X), 6) for t in periods}
            for g in generators
        }
        commitment = {
            g: {t: int(round(float(u[g, t].X))) for t in periods}
            for g in generators
        }
        startup = {
            g: {t: int(round(float(v[g, t].X))) for t in periods}
            for g in generators
        }
        return package_solution(
            data,
            generators,
            periods,
            generation,
            commitment,
            startup,
            runtime,
            float(model.ObjVal),
            "gurobi_milp_educ",
        )
    except gp.GurobiError:
        return None


def solve_with_scipy(data: dict) -> dict:
    generators = data["sets"]["generators"]
    periods = data["sets"]["periods"]
    initial_status = data["initial_status"]

    p_idx = {}
    u_idx = {}
    v_idx = {}
    idx = 0
    for g in generators:
        for t in periods:
            p_idx[(g, t)] = idx
            idx += 1
    for g in generators:
        for t in periods:
            u_idx[(g, t)] = idx
            idx += 1
    for g in generators:
        for t in periods:
            v_idx[(g, t)] = idx
            idx += 1
    n = idx

    c = np.zeros(n, dtype=float)
    lb = np.zeros(n, dtype=float)
    ub = np.full(n, np.inf, dtype=float)
    integrality = np.zeros(n, dtype=int)

    for g in generators:
        for t in periods:
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

    for t in periods:
        row = np.zeros(n, dtype=float)
        for g in generators:
            row[p_idx[(g, t)]] = 1.0
        d = float(data["demand"][t])
        rows.append(row)
        lower.append(d)
        upper.append(d)

    for g in generators:
        for t in periods:
            row = np.zeros(n, dtype=float)
            row[p_idx[(g, t)]] = 1.0
            row[u_idx[(g, t)]] = -float(data["pmin"][g])
            rows.append(row)
            lower.append(0.0)
            upper.append(np.inf)

    for g in generators:
        for t in periods:
            row = np.zeros(n, dtype=float)
            row[p_idx[(g, t)]] = 1.0
            row[u_idx[(g, t)]] = -float(data["pmax"][g])
            rows.append(row)
            lower.append(-np.inf)
            upper.append(0.0)

    for g in generators:
        for k, t in enumerate(periods):
            row = np.zeros(n, dtype=float)
            row[v_idx[(g, t)]] = 1.0
            row[u_idx[(g, t)]] = -1.0
            if k == 0:
                rhs = -float(initial_status[g])
            else:
                row[u_idx[(g, periods[k - 1])]] = 1.0
                rhs = 0.0
            rows.append(row)
            lower.append(rhs)
            upper.append(np.inf)

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
    generation = {
        g: {t: round(float(sol[p_idx[(g, t)]]), 6) for t in periods}
        for g in generators
    }
    commitment = {
        g: {t: int(round(float(sol[u_idx[(g, t)]]))) for t in periods}
        for g in generators
    }
    startup = {
        g: {t: int(round(float(sol[v_idx[(g, t)]]))) for t in periods}
        for g in generators
    }
    return package_solution(
        data,
        generators,
        periods,
        generation,
        commitment,
        startup,
        runtime,
        float(res.fun),
        "scipy_milp_educ",
    )


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
