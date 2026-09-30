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


def data_partial(data: dict, assign: Dict[str, str]) -> dict:
    jobs = list(assign.keys())
    return {
        "sets": {"jobs": jobs, "machines": data["sets"]["machines"]},
        "effective_processing_time": {j: data["effective_processing_time"][j] for j in jobs},
        "base_processing_time": {j: data["base_processing_time"][j] for j in jobs},
        "weights": {j: data["weights"][j] for j in jobs},
        "meta_parameters": data["meta_parameters"],
        "eligibility": {j: [assign[j]] for j in jobs},
    }


def exact_solve(data: dict, time_limit_seconds: float = 120.0) -> dict:
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

    def recurse(idx: int, assign: Dict[str, str], loads: Dict[str, int]) -> None:
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
        seen = set()
        for m in data["eligibility"][j]:
            sig = None
            if objective_type == "makespan" and machine_type == "P":
                sig = loads[m]
            elif objective_type != "makespan" and machine_type == "P":
                sig = tuple(sorted(assign_k for assign_k, mm in assign.items() if mm == m))
            if sig is not None and sig in seen:
                continue
            if sig is not None:
                seen.add(sig)

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
    makespan = max(machine_completion.values(), default=0)
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


def exact_completion_subset_dp(data: dict) -> dict:
    try:
        import numpy as np
        from numba import njit
    except Exception as exc:
        raise RuntimeError("NumPy/Numba are unavailable for subset DP fallback") from exc

    jobs = list(data["sets"]["jobs"])
    machines = list(data["sets"]["machines"])
    objective_type = data["meta_parameters"]["objective_type"]
    if objective_type == "makespan":
        raise RuntimeError("subset DP fallback is only for completion objectives")
    if len(jobs) > 18 or len(machines) != 4:
        raise RuntimeError("subset DP fallback is only enabled for 18-job/4-machine completion instances")

    n = len(jobs)
    full_mask = (1 << n) - 1
    job_index = {j: idx for idx, j in enumerate(jobs)}
    INF = 10**18

    @njit
    def subset_convolution(cost_a, cost_b, inf_val):
        n_states = len(cost_a)
        out = np.full(n_states, inf_val, dtype=np.int64)
        arg = np.zeros(n_states, dtype=np.int64)
        for mask in range(n_states):
            sub = mask
            best = inf_val
            best_sub = 0
            while True:
                va = cost_a[sub]
                vb = cost_b[mask ^ sub]
                if va < inf_val and vb < inf_val:
                    total = va + vb
                    if total < best:
                        best = total
                        best_sub = sub
                if sub == 0:
                    break
                sub = (sub - 1) & mask
            out[mask] = best
            arg[mask] = best_sub
        return out, arg

    def build_machine_cost(machine: str) -> "np.ndarray":
        eligible_jobs = [j for j in jobs if machine in data["eligibility"][j]]
        if objective_type == "total_completion":
            ordered = sorted(eligible_jobs, key=lambda j: (data["effective_processing_time"][j][machine], j))
        else:
            ordered = sorted(
                eligible_jobs,
                key=lambda j: (
                    data["effective_processing_time"][j][machine] / max(1, data["weights"][j]),
                    data["effective_processing_time"][j][machine],
                    j,
                ),
            )

        k = len(ordered)
        local_states = 1 << k
        total = [0] * local_states
        cost = [0] * local_states
        global_mask = [0] * local_states
        for local_mask in range(1, local_states):
            highest = local_mask.bit_length() - 1
            prev = local_mask ^ (1 << highest)
            j = ordered[highest]
            total[local_mask] = total[prev] + int(data["effective_processing_time"][j][machine])
            cost[local_mask] = cost[prev] + total[local_mask]
            global_mask[local_mask] = global_mask[prev] | (1 << job_index[j])

        arr = np.full(1 << n, INF, dtype=np.int64)
        arr[0] = 0
        for local_mask in range(1, local_states):
            arr[global_mask[local_mask]] = cost[local_mask]
        return arr

    start_clock = time.perf_counter()
    machine_costs = [build_machine_cost(m) for m in machines]
    best01, arg01 = subset_convolution(machine_costs[0], machine_costs[1], INF)
    best23, arg23 = subset_convolution(machine_costs[2], machine_costs[3], INF)

    best_total = INF
    best_mask01 = 0
    for mask in range(1 << n):
        rhs = best23[full_mask ^ mask]
        lhs = best01[mask]
        if lhs < INF and rhs < INF and lhs + rhs < best_total:
            best_total = lhs + rhs
            best_mask01 = mask

    if best_total >= INF:
        raise RuntimeError("subset DP failed to build a complete partition")

    mask23 = full_mask ^ best_mask01
    subset0 = int(arg01[best_mask01])
    subset1 = int(best_mask01 ^ subset0)
    subset2 = int(arg23[mask23])
    subset3 = int(mask23 ^ subset2)
    chosen_masks = [subset0, subset1, subset2, subset3]

    assignment: Dict[str, str] = {}
    for machine, subset in zip(machines, chosen_masks):
        for idx, j in enumerate(jobs):
            if subset & (1 << idx):
                assignment[j] = machine

    if set(assignment) != set(jobs):
        raise RuntimeError("subset DP produced an incomplete assignment")

    objective_value, schedule, machine_load = evaluate_assignment(assignment, data)
    return {
        "status": "optimal",
        "objective_type": objective_type,
        "objective": int(objective_value),
        "objective_exact": float(objective_value),
        "makespan": int(max(machine_load.values(), default=0)),
        "assignment": assignment,
        "machine_load": machine_load,
        "schedule": schedule,
        "solve_method": "exact_subset_dp_completion",
        "solver": infer_solver_label("exact_subset_dp_completion"),
        "runtime_seconds": float(time.perf_counter() - start_clock),
    }


def solve_makespan_with_scipy(data: dict, time_limit_seconds: float = 120.0) -> dict:
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
        "makespan": int(max(machine_load.values(), default=0)),
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
    w = data["weights"]
    objective_type = data["meta_parameters"]["objective_type"]

    if objective_type == "makespan":
        model = gp.Model("pms_medium_makespan_compact")
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
            "makespan": int(max(machine_load.values()) if machine_load else 0),
            "assignment": assignment,
            "machine_load": machine_load,
            "schedule": schedule,
            "solve_method": "gurobi_milp_assignment_load",
            "solver": infer_solver_label("gurobi_milp_assignment_load"),
            "runtime_seconds": float(model.Runtime),
        }

    horizon = sum(max(p[j].values()) for j in jobs)
    model = gp.Model("pms_medium_completion")
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


def solve_reference(data: dict, time_limit_seconds: float = 300.0) -> dict:
    objective_type = data["meta_parameters"]["objective_type"]
    jobs = data["sets"]["jobs"]
    machines = data["sets"]["machines"]
    subset_dp_eligible = (
        objective_type != "makespan"
        and len(jobs) <= 18
        and len(machines) == 4
    )
    try:
        gurobi_limit = min(time_limit_seconds, 20.0) if subset_dp_eligible else time_limit_seconds
        return solve_with_gurobi(data, time_limit_seconds=gurobi_limit)
    except Exception:
        if objective_type == "makespan":
            return solve_makespan_with_scipy(data, time_limit_seconds=max(120.0, 2 * time_limit_seconds))
        if subset_dp_eligible:
            try:
                return exact_completion_subset_dp(data)
            except Exception:
                return exact_solve(data, time_limit_seconds=max(300.0, 2 * time_limit_seconds))
        return exact_solve(data, time_limit_seconds=max(120.0, 2 * time_limit_seconds))


def main() -> None:
    gt_dir = Path(__file__).resolve().parent
    data = json.loads((gt_dir / "instance_data.json").read_text(encoding="utf-8"))
    sol = solve_reference(data, time_limit_seconds=300.0)
    (gt_dir / "solution_ref.json").write_text(json.dumps(sol, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
