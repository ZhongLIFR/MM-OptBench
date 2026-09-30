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


def load_instance(base: Path) -> dict:
    return json.loads((base / "ground_truth" / "instance_data.json").read_text(encoding="utf-8"))


def normalize_objective(value: float):
    rounded = round(float(value))
    if abs(float(value) - rounded) <= 1e-6:
        return int(rounded)
    return float(value)


def clean_float(value: float) -> float:
    return 0.0 if abs(value) < 1e-9 else float(round(value, 6))


def build_availability(data: dict) -> dict[tuple[str, str, str], int]:
    availability = {}
    for worker in data["sets"]["workers"]:
        for day in data["sets"]["days"]:
            code = data["availability_code"][worker][day]
            allowed_shifts = set(data["availability_legend"][code])
            for shift in data["sets"]["shifts"]:
                availability[(worker, day, shift)] = int(shift in allowed_shifts)
    return availability


def package_solution(data: dict, assignments: dict, runtime: float, objective_value: float, solve_method: str) -> dict:
    workers = data["sets"]["workers"]
    days = data["sets"]["days"]
    shifts = data["sets"]["shifts"]
    assignment_by_day = {
        day: {
            shift: [worker for worker in workers if assignments[(worker, day, shift)] == 1]
            for shift in shifts
        }
        for day in days
    }
    worker_schedule = {
        worker: {
            day: next((shift for shift in shifts if assignments[(worker, day, shift)] == 1), "OFF")
            for day in days
        }
        for worker in workers
    }
    worker_total_assignments = {
        worker: int(sum(assignments[(worker, day, shift)] for day in days for shift in shifts))
        for worker in workers
    }
    coverage_realized = {
        day: {
            shift: int(sum(assignments[(worker, day, shift)] for worker in workers))
            for shift in shifts
        }
        for day in days
    }
    total_assignment_cost = sum(
        float(data["shift_cost"][worker][shift]) * assignments[(worker, day, shift)]
        for worker in workers
        for day in days
        for shift in shifts
    )
    return {
        "status": "optimal",
        "objective": normalize_objective(objective_value),
        "objective_exact": float(objective_value),
        "runtime_seconds": runtime,
        "assignment_cost": clean_float(total_assignment_cost),
        "assignments_by_day": assignment_by_day,
        "coverage_realized": coverage_realized,
        "worker_schedule": worker_schedule,
        "worker_total_assignments": worker_total_assignments,
        "solve_method": solve_method,
    }


def solve_with_gurobi(data: dict) -> dict | None:
    if gp is None:
        return None
    workers = data["sets"]["workers"]
    days = data["sets"]["days"]
    shifts = data["sets"]["shifts"]
    availability = build_availability(data)
    start = time.perf_counter()
    try:
        model = gp.Model("wpss_easy")
        model.Params.OutputFlag = 0
        model.Params.TimeLimit = TIME_LIMIT_SECONDS
        model.Params.MIPGap = 0.0

        x = {
            (worker, day, shift): model.addVar(vtype=GRB.BINARY, name=f"x_{worker}_{day}_{shift}")
            for worker in workers
            for day in days
            for shift in shifts
        }

        model.setObjective(
            gp.quicksum(
                float(data["shift_cost"][worker][shift]) * x[worker, day, shift]
                for worker in workers
                for day in days
                for shift in shifts
            ),
            GRB.MINIMIZE,
        )

        for day in days:
            for shift in shifts:
                model.addConstr(
                    gp.quicksum(x[worker, day, shift] for worker in workers) >= float(data["demand"][day][shift]),
                    name=f"coverage_{day}_{shift}",
                )

        for worker in workers:
            for day in days:
                model.addConstr(
                    gp.quicksum(x[worker, day, shift] for shift in shifts) <= 1.0,
                    name=f"one_shift_{worker}_{day}",
                )
                for shift in shifts:
                    model.addConstr(
                        x[worker, day, shift] <= float(availability[(worker, day, shift)]),
                        name=f"availability_{worker}_{day}_{shift}",
                    )

        model.optimize()
        runtime = time.perf_counter() - start
        if model.Status != GRB.OPTIMAL:
            return None

        assignments = {
            (worker, day, shift): int(round(float(x[worker, day, shift].X)))
            for worker in workers
            for day in days
            for shift in shifts
        }
        return package_solution(data, assignments, runtime, float(model.ObjVal), "gurobi_milp_wpss_easy")
    except Exception:
        return None


def solve_with_scipy(data: dict) -> dict:
    workers = data["sets"]["workers"]
    days = data["sets"]["days"]
    shifts = data["sets"]["shifts"]
    availability = build_availability(data)

    x_idx = {}
    idx = 0
    for worker in workers:
        for day in days:
            for shift in shifts:
                x_idx[(worker, day, shift)] = idx
                idx += 1
    n = idx

    c = np.zeros(n, dtype=float)
    lb = np.zeros(n, dtype=float)
    ub = np.ones(n, dtype=float)
    integrality = np.ones(n, dtype=int)

    for worker in workers:
        for day in days:
            for shift in shifts:
                c[x_idx[(worker, day, shift)]] = float(data["shift_cost"][worker][shift])

    rows = []
    lower = []
    upper = []

    for day in days:
        for shift in shifts:
            row = np.zeros(n, dtype=float)
            for worker in workers:
                row[x_idx[(worker, day, shift)]] = 1.0
            rows.append(row)
            lower.append(float(data["demand"][day][shift]))
            upper.append(np.inf)

    for worker in workers:
        for day in days:
            row = np.zeros(n, dtype=float)
            for shift in shifts:
                row[x_idx[(worker, day, shift)]] = 1.0
            rows.append(row)
            lower.append(-np.inf)
            upper.append(1.0)

    for worker in workers:
        for day in days:
            for shift in shifts:
                row = np.zeros(n, dtype=float)
                row[x_idx[(worker, day, shift)]] = 1.0
                rows.append(row)
                lower.append(-np.inf)
                upper.append(float(availability[(worker, day, shift)]))

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

    assignments = {
        (worker, day, shift): int(round(float(res.x[x_idx[(worker, day, shift)]])))
        for worker in workers
        for day in days
        for shift in shifts
    }
    return package_solution(data, assignments, runtime, float(res.fun), "scipy_milp_wpss_easy")


def solve_instance(base: Path) -> dict:
    data = load_instance(base)
    gurobi_solution = solve_with_gurobi(data)
    if gurobi_solution is not None:
        return gurobi_solution
    return solve_with_scipy(data)


def main() -> None:
    base = Path(__file__).resolve().parents[1]
    result = solve_instance(base)
    out_path = base / "ground_truth" / "solution_ref.json"
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
