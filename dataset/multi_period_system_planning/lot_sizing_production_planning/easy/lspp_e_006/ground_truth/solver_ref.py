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


def build_index_maps(products, periods):
    x_idx = {}
    i_idx = {}
    y_idx = {}
    idx = 0
    for p in products:
        for t in periods:
            x_idx[(p, t)] = idx
            idx += 1
    for p in products:
        for t in periods:
            i_idx[(p, t)] = idx
            idx += 1
    for p in products:
        for t in periods:
            y_idx[(p, t)] = idx
            idx += 1
    return x_idx, i_idx, y_idx, idx


def package_solution(data: dict, products, periods, production, inventory, setup, runtime: float, objective_value: float, solve_method: str) -> dict:
    capacity_usage = {
        t: int(sum(production[p][t] for p in products))
        for t in periods
    }
    return {
        "status": "optimal",
        "objective": normalize_objective(objective_value),
        "objective_exact": float(objective_value),
        "runtime_seconds": runtime,
        "production": production,
        "inventory": inventory,
        "setup": setup,
        "capacity_usage": capacity_usage,
        "capacity_binding_periods": [
            t for t in periods
            if data["capacity"] is not None and abs(capacity_usage[t] - int(data["capacity"][t])) <= 1e-6
        ],
        "solve_method": solve_method,
    }


def solve_with_gurobi(data: dict) -> dict | None:
    if gp is None:
        return None
    products = data["sets"]["products"]
    periods = data["sets"]["periods"]
    start = time.perf_counter()
    try:
        model = gp.Model("lspp")
        model.Params.OutputFlag = 0
        model.Params.TimeLimit = TIME_LIMIT_SECONDS
        model.Params.MIPGap = 0.0

        x = {(p, t): model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"x_{p}_{t}") for p in products for t in periods}
        inv = {(p, t): model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"I_{p}_{t}") for p in products for t in periods}
        y = {(p, t): model.addVar(lb=0.0, ub=1.0, vtype=GRB.BINARY, name=f"y_{p}_{t}") for p in products for t in periods}

        model.setObjective(
            gp.quicksum(
                float(data["production_cost"][p][t]) * x[p, t]
                + float(data["holding_cost"][p][t]) * inv[p, t]
                + float(data["setup_cost"][p][t]) * y[p, t]
                for p in products
                for t in periods
            ),
            GRB.MINIMIZE,
        )

        for p in products:
            for k, t in enumerate(periods):
                lhs = x[p, t] - inv[p, t]
                rhs = float(data["demand"][p][t])
                if k == 0:
                    rhs -= float(data["initial_inventory"][p])
                else:
                    lhs += inv[p, periods[k - 1]]
                model.addConstr(lhs == rhs, name=f"balance_{p}_{t}")

        for p in products:
            M = float(data["big_m"][p])
            for t in periods:
                model.addConstr(x[p, t] <= M * y[p, t], name=f"setup_{p}_{t}")

        if data["capacity"] is not None:
            for t in periods:
                model.addConstr(
                    gp.quicksum(x[p, t] for p in products) <= float(data["capacity"][t]),
                    name=f"cap_{t}",
                )

        model.optimize()
        runtime = time.perf_counter() - start
        if model.Status != GRB.OPTIMAL:
            return None

        production = {p: {t: int(round(x[p, t].X)) for t in periods} for p in products}
        inventory = {p: {t: int(round(inv[p, t].X)) for t in periods} for p in products}
        setup = {p: {t: int(round(y[p, t].X)) for t in periods} for p in products}
        return package_solution(
            data,
            products,
            periods,
            production,
            inventory,
            setup,
            runtime,
            model.ObjVal,
            "gurobi_milp_lspp",
        )
    except Exception:
        return None


def solve_instance(data: dict) -> dict:
    products = data["sets"]["products"]
    periods = data["sets"]["periods"]

    gurobi_solution = solve_with_gurobi(data)
    if gurobi_solution is not None:
        return gurobi_solution

    x_idx, i_idx, y_idx, n = build_index_maps(products, periods)

    c = np.zeros(n, dtype=float)
    lb = np.zeros(n, dtype=float)
    ub = np.full(n, np.inf, dtype=float)
    integrality = np.zeros(n, dtype=int)

    for p in products:
        for t in periods:
            c[x_idx[(p, t)]] = float(data["production_cost"][p][t])
            c[i_idx[(p, t)]] = float(data["holding_cost"][p][t])
            c[y_idx[(p, t)]] = float(data["setup_cost"][p][t])
            ub[y_idx[(p, t)]] = 1.0
            integrality[y_idx[(p, t)]] = 1

    rows = []
    lower = []
    upper = []

    for p in products:
        for k, t in enumerate(periods):
            row = np.zeros(n, dtype=float)
            row[x_idx[(p, t)]] = 1.0
            row[i_idx[(p, t)]] = -1.0
            rhs = float(data["demand"][p][t])
            if k == 0:
                rhs -= float(data["initial_inventory"][p])
            else:
                row[i_idx[(p, periods[k - 1])]] = 1.0
            rows.append(row)
            lower.append(rhs)
            upper.append(rhs)

    for p in products:
        M = float(data["big_m"][p])
        for t in periods:
            row = np.zeros(n, dtype=float)
            row[x_idx[(p, t)]] = 1.0
            row[y_idx[(p, t)]] = -M
            rows.append(row)
            lower.append(-np.inf)
            upper.append(0.0)

    if data["capacity"] is not None:
        for t in periods:
            row = np.zeros(n, dtype=float)
            for p in products:
                row[x_idx[(p, t)]] = 1.0
            rows.append(row)
            lower.append(-np.inf)
            upper.append(float(data["capacity"][t]))

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
    production = {
        p: {t: int(round(sol[x_idx[(p, t)]])) for t in periods}
        for p in products
    }
    inventory = {
        p: {t: int(round(sol[i_idx[(p, t)]])) for t in periods}
        for p in products
    }
    setup = {
        p: {t: int(round(sol[y_idx[(p, t)]])) for t in periods}
        for p in products
    }
    result = package_solution(
        data,
        products,
        periods,
        production,
        inventory,
        setup,
        runtime,
        float(res.fun),
        "scipy_milp_highs_exact",
    )
    result["solver_status"] = int(res.status)
    return result


def main() -> None:
    base = Path(__file__).resolve().parent
    data = json.loads((base / "instance_data.json").read_text(encoding="utf-8"))
    sol = solve_instance(data)
    (base / "solution_ref.json").write_text(json.dumps(sol, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
