#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
import time
from typing import Dict, List, Tuple


def infer_solver_label(method: str | None) -> str | None:
    if not method:
        return None
    method_lower = method.lower()
    if "gurobi" in method_lower:
        return "Gurobi"
    if "scipy" in method_lower:
        return "SciPy"
    if "subset_dp" in method_lower:
        return "Custom exact subset DP"
    if "branch_and_bound" in method_lower:
        return "Custom exact B&B"
    return method


def evaluate_assignment(assign: Dict[str, str], data: dict) -> Tuple[int, List[dict], dict]:
    jobs = data["sets"]["jobs"]
    machines = data["sets"]["machines"]
    machine_jobs: Dict[str, List[str]] = {m: [] for m in machines}
    for j in jobs:
        machine_jobs[assign[j]].append(j)

    schedule = []
    machine_load = {}
    for m in machines:
        ordered = sorted(machine_jobs[m], key=lambda j: (-data["effective_processing_time"][j][m], j))
        t = 0
        for j in ordered:
            p = int(data["effective_processing_time"][j][m])
            schedule.append(
                {
                    "job": j,
                    "machine": m,
                    "start": int(t),
                    "finish": int(t + p),
                    "duration": int(p),
                    "base_duration": int(data["base_processing_time"][j]),
                    "weight": 1,
                }
            )
            t += p
        machine_load[m] = int(t)

    schedule.sort(key=lambda r: (r["machine"], r["start"], r["job"]))
    makespan = max(machine_load.values(), default=0)
    return int(makespan), schedule, machine_load


def solve_makespan_with_scipy(data: dict, time_limit_seconds: float = 180.0) -> dict:
    try:
        import numpy as np
        from scipy.optimize import Bounds, LinearConstraint, milp
    except Exception as exc:
        raise RuntimeError("SciPy MILP is unavailable") from exc

    jobs = list(data["sets"]["jobs"])
    machines = list(data["sets"]["machines"])
    eligibility = data["eligibility"]
    p = data["effective_processing_time"]

    assign_keys = [(j, m) for j in jobs for m in eligibility[j]]
    n_assign = len(assign_keys)
    c = np.zeros(n_assign + 1)
    c[-1] = 1.0
    integrality = np.zeros(n_assign + 1, dtype=int)
    integrality[:n_assign] = 1
    bounds = Bounds(np.zeros(n_assign + 1), np.array([1.0] * n_assign + [np.inf]))

    A_eq = []
    b_eq = []
    for j in jobs:
        row = np.zeros(n_assign + 1)
        for idx, (jj, _) in enumerate(assign_keys):
            if jj == j:
                row[idx] = 1.0
        A_eq.append(row)
        b_eq.append(1.0)

    A_ub = []
    b_ub = []
    for m in machines:
        row = np.zeros(n_assign + 1)
        for idx, (j, mm) in enumerate(assign_keys):
            if mm == m:
                row[idx] = float(p[j][m])
        row[-1] = -1.0
        A_ub.append(row)
        b_ub.append(0.0)

    start_clock = time.perf_counter()
    constraints = [
        LinearConstraint(np.asarray(A_eq), np.asarray(b_eq), np.asarray(b_eq)),
        LinearConstraint(np.asarray(A_ub), -np.inf * np.ones(len(A_ub)), np.asarray(b_ub)),
    ]
    res = milp(c=c, constraints=constraints, integrality=integrality, bounds=bounds, options={"time_limit": float(time_limit_seconds)})
    if not res.success:
        raise RuntimeError(f"SciPy MILP failed: {res.message}")

    assignment = {}
    for idx, (j, m) in enumerate(assign_keys):
        if res.x[idx] > 0.5:
            assignment[j] = m
    if set(assignment) != set(jobs):
        raise RuntimeError("SciPy MILP returned incomplete assignment")

    objective_value, schedule, machine_load = evaluate_assignment(assignment, data)
    return {
        "status": "optimal",
        "objective_type": "makespan",
        "objective": int(objective_value),
        "objective_exact": float(objective_value),
        "makespan": int(objective_value),
        "assignment": assignment,
        "machine_load": machine_load,
        "schedule": schedule,
        "solve_method": "scipy_milp_assignment_load",
        "solver": infer_solver_label("scipy_milp_assignment_load"),
        "runtime_seconds": float(time.perf_counter() - start_clock),
    }


def solve_with_gurobi(data: dict, time_limit_seconds: float = 60.0) -> dict:
    try:
        import gurobipy as gp
        from gurobipy import GRB
    except Exception as exc:
        raise RuntimeError("gurobipy is unavailable") from exc

    jobs = list(data["sets"]["jobs"])
    machines = list(data["sets"]["machines"])
    eligibility = data["eligibility"]
    p = data["effective_processing_time"]

    model = gp.Model("pms_hard_makespan_compact")
    model.Params.OutputFlag = 0
    model.Params.TimeLimit = time_limit_seconds
    model.Params.MIPGap = 0.0

    x = {(j, m): model.addVar(vtype=GRB.BINARY, name=f"x_{j}_{m}") for j in jobs for m in eligibility[j]}
    cmax = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="Cmax")
    model.update()

    for j in jobs:
        model.addConstr(gp.quicksum(x[(j, m)] for m in eligibility[j]) == 1, name=f"assign_{j}")
    for m in machines:
        assignable_jobs = [j for j in jobs if m in eligibility[j]]
        model.addConstr(
            gp.quicksum(p[j][m] * x[(j, m)] for j in assignable_jobs) <= cmax,
            name=f"load_{m}",
        )

    model.setObjective(cmax, GRB.MINIMIZE)
    model.optimize()
    if model.Status != GRB.OPTIMAL:
        raise RuntimeError(f"Gurobi failed to prove optimality for {data['instance_id']}")

    assignment = {j: max(eligibility[j], key=lambda m: x[(j, m)].X) for j in jobs}
    objective_value, schedule, machine_load = evaluate_assignment(assignment, data)
    return {
        "status": "optimal",
        "objective_type": "makespan",
        "objective": int(objective_value),
        "objective_exact": float(model.ObjVal),
        "makespan": int(objective_value),
        "assignment": assignment,
        "machine_load": machine_load,
        "schedule": schedule,
        "solve_method": "gurobi_milp_assignment_load",
        "solver": infer_solver_label("gurobi_milp_assignment_load"),
        "runtime_seconds": float(model.Runtime),
    }


def solve_reference(data: dict, time_limit_seconds: float = 300.0) -> dict:
    try:
        return solve_with_gurobi(data, time_limit_seconds=time_limit_seconds)
    except Exception:
        return solve_makespan_with_scipy(data, time_limit_seconds=max(180.0, 2 * time_limit_seconds))


def main() -> None:
    gt_dir = Path(__file__).resolve().parent
    data = json.loads((gt_dir / "instance_data.json").read_text(encoding="utf-8"))
    sol = solve_reference(data, time_limit_seconds=300.0)
    (gt_dir / "solution_ref.json").write_text(json.dumps(sol, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
