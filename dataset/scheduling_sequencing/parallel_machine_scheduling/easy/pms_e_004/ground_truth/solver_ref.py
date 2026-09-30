#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
import math
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


def schedule_order(machine_jobs: List[str], data: dict, machine: str, objective_type: str) -> List[str]:
    if objective_type == "total_completion":
        return sorted(machine_jobs, key=lambda j: (data["effective_processing_time"][j][machine], j))
    if objective_type == "weighted_completion":
        return sorted(
            machine_jobs,
            key=lambda j: (
                data["effective_processing_time"][j][machine] / max(1, data["weights"][j]),
                data["effective_processing_time"][j][machine],
                j,
            ),
        )
    return sorted(machine_jobs, key=lambda j: (-data["effective_processing_time"][j][machine], j))


def evaluate_assignment(assign: Dict[str, str], data: dict) -> Tuple[int, List[dict], dict]:
    jobs = data["sets"]["jobs"]
    machines = data["sets"]["machines"]
    objective_type = data["meta_parameters"]["objective_type"]

    machine_jobs: Dict[str, List[str]] = {m: [] for m in machines}
    for j in jobs:
        machine_jobs[assign[j]].append(j)

    schedule = []
    machine_completion = {}
    machine_load = {}
    total_completion = 0
    weighted_completion = 0

    for m in machines:
        ordered = schedule_order(machine_jobs[m], data, m, objective_type)
        t = 0
        for j in ordered:
            p = data["effective_processing_time"][j][m]
            rec = {
                "job": j,
                "machine": m,
                "start": int(t),
                "finish": int(t + p),
                "duration": int(p),
                "base_duration": int(data["base_processing_time"][j]),
                "weight": int(data["weights"][j]),
            }
            schedule.append(rec)
            t += p
            total_completion += t
            weighted_completion += data["weights"][j] * t
        machine_completion[m] = int(t)
        machine_load[m] = int(t)

    schedule.sort(key=lambda r: (r["machine"], r["start"], r["job"]))
    makespan = max(machine_completion.values()) if machine_completion else 0
    objective_value = {
        "makespan": makespan,
        "total_completion": total_completion,
        "weighted_completion": weighted_completion,
    }[objective_type]
    return int(objective_value), schedule, machine_load


def lower_bound_makespan(loads: Dict[str, int], remaining_jobs: List[str], data: dict) -> int:
    total_min = sum(min(data["effective_processing_time"][j][m] for m in data["eligibility"][j]) for j in remaining_jobs)
    avg_bound = math.ceil((sum(loads.values()) + total_min) / len(loads)) if loads else 0
    job_bound = max((min(data["effective_processing_time"][j][m] for m in data["eligibility"][j]) for j in remaining_jobs), default=0)
    return max(max(loads.values(), default=0), avg_bound, job_bound)


def exact_solve(data: dict, time_limit_seconds: float = 20.0) -> dict:
    jobs = list(data["sets"]["jobs"])
    machines = list(data["sets"]["machines"])
    objective_type = data["meta_parameters"]["objective_type"]
    machine_type = data["meta_parameters"]["machine_type"]

    def job_sort_key(j: str):
        pmin = min(data["effective_processing_time"][j][m] for m in data["eligibility"][j])
        return (len(data["eligibility"][j]), -pmin, -data["weights"][j], j)

    search_jobs = sorted(jobs, key=job_sort_key)
    start_clock = time.perf_counter()
    best_obj = math.inf
    best_assign: Dict[str, str] | None = None

    def recurse(idx: int, assign: Dict[str, str], loads: Dict[str, int]):
        nonlocal best_obj, best_assign
        if time.perf_counter() - start_clock > time_limit_seconds:
            raise TimeoutError("Exact search exceeded time limit")

        if idx == len(search_jobs):
            obj, _, _ = evaluate_assignment(assign, data)
            if obj < best_obj:
                best_obj = obj
                best_assign = dict(assign)
            return

        remaining = search_jobs[idx:]
        if objective_type == "makespan":
            lb = lower_bound_makespan(loads, remaining, data)
            if lb >= best_obj:
                return
        else:
            partial_obj, _, _ = evaluate_assignment({j: assign[j] for j in assign}, data_partial(data, assign))
            if partial_obj >= best_obj:
                return

        j = search_jobs[idx]
        for m in data["eligibility"][j]:
            assign[j] = m
            old = loads[m]
            loads[m] = old + data["effective_processing_time"][j][m]
            recurse(idx + 1, assign, loads)
            loads[m] = old
            del assign[j]

    recurse(0, {}, {m: 0 for m in machines})
    if best_assign is None:
        raise RuntimeError("No feasible solution found")

    objective_value, schedule, machine_load = evaluate_assignment(best_assign, data)
    machine_completion = {m: 0 for m in machines}
    for rec in schedule:
        machine_completion[rec["machine"]] = rec["finish"]
    makespan = max(machine_completion.values())

    return {
        "status": "optimal",
        "objective_type": objective_type,
        "objective": int(objective_value),
        "objective_exact": float(objective_value),
        "makespan": int(makespan),
        "assignment": {j: best_assign[j] for j in jobs},
        "machine_load": machine_load,
        "schedule": schedule,
        "solve_method": "exact_branch_and_bound_assignment",
        "solver": infer_solver_label("exact_branch_and_bound_assignment"),
        "runtime_seconds": float(time.perf_counter() - start_clock),
    }


def solve_with_gurobi(data: dict, time_limit_seconds: float = 30.0) -> dict:
    try:
        import gurobipy as gp
        from gurobipy import GRB
    except Exception as exc:
        raise RuntimeError("gurobipy is unavailable") from exc

    jobs = list(data["sets"]["jobs"])
    machines = list(data["sets"]["machines"])
    objective_type = data["meta_parameters"]["objective_type"]
    eligibility = data["eligibility"]
    p = data["effective_processing_time"]
    w = data["weights"]

    if objective_type == "makespan":
        model = gp.Model("pms_easy_makespan")
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
            "objective_type": objective_type,
            "objective": int(objective_value),
            "objective_exact": float(model.ObjVal),
            "makespan": int(max(machine_load.values()) if machine_load else 0),
            "assignment": assignment,
            "machine_load": machine_load,
            "schedule": schedule,
            "solve_method": "gurobi_milp_assignment_load",
            "solver": infer_solver_label("gurobi_milp_assignment_load"),
            "runtime_seconds": float(model.Runtime),
        }

    horizon = sum(max(p[j].values()) for j in jobs)
    model = gp.Model("pms_easy_completion")
    model.Params.OutputFlag = 0
    model.Params.TimeLimit = time_limit_seconds
    model.Params.MIPGap = 0.0

    x = {(j, m): model.addVar(vtype=GRB.BINARY, name=f"x_{j}_{m}") for j in jobs for m in eligibility[j]}
    S = {j: model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"S_{j}") for j in jobs}
    C = {j: model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"C_{j}") for j in jobs}
    y = {}
    for i_idx in range(len(jobs)):
        for j_idx in range(i_idx + 1, len(jobs)):
            i = jobs[i_idx]
            j = jobs[j_idx]
            for m in set(eligibility[i]).intersection(eligibility[j]):
                y[(i, j, m)] = model.addVar(vtype=GRB.BINARY, name=f"y_{i}_{j}_{m}")

    model.update()

    for j in jobs:
        model.addConstr(gp.quicksum(x[(j, m)] for m in eligibility[j]) == 1, name=f"assign_{j}")
        model.addConstr(C[j] == S[j] + gp.quicksum(p[j][m] * x[(j, m)] for m in eligibility[j]), name=f"completion_{j}")

    for i_idx in range(len(jobs)):
        for j_idx in range(i_idx + 1, len(jobs)):
            i = jobs[i_idx]
            j = jobs[j_idx]
            common = set(eligibility[i]).intersection(eligibility[j])
            for m in common:
                ym = y[(i, j, m)]
                model.addConstr(S[i] + p[i][m] <= S[j] + horizon * (3 - x[(i, m)] - x[(j, m)] - ym), name=f"ord1_{i}_{j}_{m}")
                model.addConstr(S[j] + p[j][m] <= S[i] + horizon * (2 - x[(i, m)] - x[(j, m)] + ym), name=f"ord2_{i}_{j}_{m}")

    if objective_type == "total_completion":
        model.setObjective(gp.quicksum(C[j] for j in jobs), GRB.MINIMIZE)
    else:
        model.setObjective(gp.quicksum(w[j] * C[j] for j in jobs), GRB.MINIMIZE)

    model.optimize()
    if model.Status != GRB.OPTIMAL:
        raise RuntimeError(f"Gurobi failed to prove optimality for {data['instance_id']}")

    assignment = {j: max(eligibility[j], key=lambda m: x[(j, m)].X) for j in jobs}
    schedule = []
    machine_load = {m: 0 for m in machines}
    for j in jobs:
        m = assignment[j]
        st = int(round(S[j].X))
        ft = int(round(C[j].X))
        dur = int(p[j][m])
        machine_load[m] = max(machine_load[m], ft)
        schedule.append(
            {
                "job": j,
                "machine": m,
                "start": st,
                "finish": ft,
                "duration": dur,
                "base_duration": int(data["base_processing_time"][j]),
                "weight": int(data["weights"][j]),
            }
        )
    schedule.sort(key=lambda r: (r["machine"], r["start"], r["job"]))
    makespan = max((row["finish"] for row in schedule), default=0)

    return {
        "status": "optimal",
        "objective_type": objective_type,
        "objective": int(round(model.ObjVal)),
        "objective_exact": float(model.ObjVal),
        "makespan": int(makespan),
        "assignment": assignment,
        "machine_load": {k: int(v) for k, v in machine_load.items()},
        "schedule": schedule,
        "solve_method": "gurobi_milp_disjunctive",
        "solver": infer_solver_label("gurobi_milp_disjunctive"),
        "runtime_seconds": float(model.Runtime),
    }


def solve_reference(data: dict, time_limit_seconds: float = 30.0) -> dict:
    try:
        return solve_with_gurobi(data, time_limit_seconds=time_limit_seconds)
    except Exception:
        return exact_solve(data, time_limit_seconds=time_limit_seconds)


def data_partial(data: dict, assign: Dict[str, str]) -> dict:
    jobs = list(assign.keys())
    new = {
        "sets": {"jobs": jobs, "machines": data["sets"]["machines"]},
        "effective_processing_time": {j: data["effective_processing_time"][j] for j in jobs},
        "base_processing_time": {j: data["base_processing_time"][j] for j in jobs},
        "weights": {j: data["weights"][j] for j in jobs},
        "meta_parameters": data["meta_parameters"],
    }
    # Turn the partial assignment into singleton eligibility so evaluate_assignment uses it directly.
    new["eligibility"] = {j: [assign[j]] for j in jobs}
    return new


def main():
    gt_dir = Path(__file__).resolve().parent
    data = json.loads((gt_dir / "instance_data.json").read_text(encoding="utf-8"))
    sol = solve_reference(data, time_limit_seconds=30.0)
    (gt_dir / "solution_ref.json").write_text(json.dumps(sol, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
