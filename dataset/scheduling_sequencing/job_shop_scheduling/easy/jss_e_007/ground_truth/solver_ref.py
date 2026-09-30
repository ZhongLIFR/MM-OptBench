#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
import math
import time
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class Operation:
    job: str
    op: str
    machine: str
    duration: int
    index_in_job: int


def infer_solver_label(method: str | None) -> str | None:
    if not method:
        return None
    method_lower = method.lower()
    if "gurobi" in method_lower:
        return "Gurobi"
    if "scipy" in method_lower:
        return "SciPy"
    if "branch_and_bound" in method_lower:
        return "Custom exact B&B"
    return method


def operations_from_data(data: dict) -> Tuple[List[Operation], Dict[str, List[Operation]], Dict[str, List[Operation]]]:
    jobs = data["sets"]["jobs"]
    machines = data["sets"]["machines"]
    ops_by_job: Dict[str, List[Operation]] = {j: [] for j in jobs}
    ops_by_machine: Dict[str, List[Operation]] = {m: [] for m in machines}
    flat: List[Operation] = []
    for j in jobs:
        for idx, op in enumerate(data["sets"]["operations"][j], start=1):
            rec = Operation(j, op, data["machine_assignment"][j][op], int(data["processing_time"][j][op]), idx)
            ops_by_job[j].append(rec)
            ops_by_machine[rec.machine].append(rec)
            flat.append(rec)
    return flat, ops_by_job, ops_by_machine


def lower_bound(job_ready: dict, machine_ready: dict, next_index: dict, ops_by_job: dict, ops_by_machine: dict) -> int:
    lb = 0
    for j, ops in ops_by_job.items():
        rem = sum(op.duration for op in ops[next_index[j]:])
        lb = max(lb, job_ready[j] + rem)
    for m, ops in ops_by_machine.items():
        rem = 0
        for op in ops:
            if next_index[op.job] <= op.index_in_job - 1:
                rem += op.duration
        lb = max(lb, machine_ready[m] + rem)
    return lb


def solve_with_gurobi(data: dict, time_limit_seconds: float = 30.0) -> dict | None:
    try:
        import gurobipy as gp
        from gurobipy import GRB
    except Exception:
        return None

    jobs = data["sets"]["jobs"]
    operations = data["sets"]["operations"]
    machine_assignment = data["machine_assignment"]
    processing_time = data["processing_time"]
    machines = data["sets"]["machines"]

    op_keys = [(j, op) for j in jobs for op in operations[j]]
    durations = {(j, op): int(processing_time[j][op]) for j, op in op_keys}
    machine_of = {(j, op): machine_assignment[j][op] for j, op in op_keys}
    horizon = sum(durations.values())

    machine_ops = {m: [] for m in machines}
    for key in op_keys:
        machine_ops[machine_of[key]].append(key)

    order_pairs = []
    for m in machines:
        ops = machine_ops[m]
        for i in range(len(ops)):
            for j in range(i + 1, len(ops)):
                order_pairs.append((ops[i], ops[j]))

    start_clock = time.perf_counter()
    try:
        model = gp.Model(f"{data['instance_id']}_generator")
        model.Params.OutputFlag = 0
        model.Params.TimeLimit = time_limit_seconds
        model.Params.MIPGap = 0.0

        s = {key: model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"s_{key[0]}_{key[1]}") for key in op_keys}
        cmax = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="C_max")
        y = {
            (a, b): model.addVar(vtype=GRB.BINARY, name=f"y_{a[0]}_{a[1]}__{b[0]}_{b[1]}")
            for a, b in order_pairs
        }

        for j in jobs:
            ops = operations[j]
            for idx in range(len(ops) - 1):
                cur = (j, ops[idx])
                nxt = (j, ops[idx + 1])
                model.addConstr(s[nxt] >= s[cur] + durations[cur], name=f"prec_{j}_{idx + 1}")

        for a, b in order_pairs:
            model.addConstr(
                s[a] + durations[a] <= s[b] + horizon * (1 - y[(a, b)]),
                name=f"disj1_{a[0]}_{a[1]}_{b[0]}_{b[1]}",
            )
            model.addConstr(
                s[b] + durations[b] <= s[a] + horizon * y[(a, b)],
                name=f"disj2_{a[0]}_{a[1]}_{b[0]}_{b[1]}",
            )

        for key in op_keys:
            model.addConstr(cmax >= s[key] + durations[key], name=f"cmax_{key[0]}_{key[1]}")

        model.setObjective(cmax, GRB.MINIMIZE)
        model.optimize()

        if model.Status != GRB.OPTIMAL:
            return None

        detailed = []
        for j, op in op_keys:
            st = int(round(s[(j, op)].X))
            dur = durations[(j, op)]
            detailed.append(
                {
                    "job": j,
                    "operation": op,
                    "machine": machine_of[(j, op)],
                    "start": st,
                    "finish": st + dur,
                    "duration": dur,
                }
            )
        detailed.sort(key=lambda x: (x["machine"], x["start"], x["job"], x["operation"]))

        binding_machines = []
        machine_orders = {}
        for m in machines:
            rows = [r for r in detailed if r["machine"] == m]
            rows.sort(key=lambda x: (x["start"], x["finish"], x["job"], x["operation"]))
            machine_orders[m] = [f"{r['job']}-{r['operation']}" for r in rows]
            if any(rows[t + 1]["start"] == rows[t]["finish"] for t in range(len(rows) - 1)):
                binding_machines.append(m)

        objective = int(round(cmax.X))
        return {
            "status": "optimal",
            "objective": objective,
            "objective_exact": float(cmax.X),
            "makespan": objective,
            "schedule": detailed,
            "solve_method": "gurobi_disjunctive_milp",
            "solver": infer_solver_label("gurobi_disjunctive_milp"),
            "runtime_seconds": float(model.Runtime),
            "binding_machines": binding_machines,
            "machine_orders": machine_orders,
        }
    finally:
        _ = time.perf_counter() - start_clock


def solve_jobshop_exact(data: dict, time_limit_seconds: float = 20.0) -> dict:
    flat_ops, ops_by_job, ops_by_machine = operations_from_data(data)
    jobs = data["sets"]["jobs"]
    machines = data["sets"]["machines"]
    total_ops = len(flat_ops)

    best_obj = math.inf
    best_schedule = None
    start_time = time.perf_counter()

    def recurse(next_index: dict, job_ready: dict, machine_ready: dict, sched: dict):
        nonlocal best_obj, best_schedule
        if time.perf_counter() - start_time > time_limit_seconds:
            raise TimeoutError("Exact search exceeded time limit")
        if len(sched) == total_ops:
            cmax = max((st + op.duration) for op_key, st in sched.items() for op in [op_lookup[op_key]])
            if cmax < best_obj:
                best_obj = cmax
                best_schedule = dict(sched)
            return
        lb = lower_bound(job_ready, machine_ready, next_index, ops_by_job, ops_by_machine)
        if lb >= best_obj:
            return
        available = []
        for j in jobs:
            idx = next_index[j]
            if idx < len(ops_by_job[j]):
                op = ops_by_job[j][idx]
                est = max(job_ready[j], machine_ready[op.machine])
                available.append((est, -op.duration, op.machine, j, op))
        available.sort()
        for _, _, _, _, op in available:
            est = max(job_ready[op.job], machine_ready[op.machine])
            finish = est + op.duration
            if finish >= best_obj:
                continue
            next2 = dict(next_index)
            jr2 = dict(job_ready)
            mr2 = dict(machine_ready)
            sched2 = dict(sched)
            next2[op.job] += 1
            jr2[op.job] = finish
            mr2[op.machine] = finish
            sched2[(op.job, op.op)] = est
            recurse(next2, jr2, mr2, sched2)

    op_lookup = {(op.job, op.op): op for op in flat_ops}
    recurse(
        {j: 0 for j in jobs},
        {j: 0 for j in jobs},
        {m: 0 for m in machines},
        {},
    )
    if best_schedule is None:
        raise RuntimeError("No feasible schedule found")

    detailed = []
    for op in flat_ops:
        st = best_schedule[(op.job, op.op)]
        detailed.append({
            "job": op.job,
            "operation": op.op,
            "machine": op.machine,
            "start": st,
            "finish": st + op.duration,
            "duration": op.duration,
        })
    detailed.sort(key=lambda x: (x["machine"], x["start"], x["job"], x["operation"]))
    runtime = time.perf_counter() - start_time
    binding_machines = []
    machine_orders = {}
    for m in machines:
        rows = [r for r in detailed if r["machine"] == m]
        rows.sort(key=lambda x: (x["start"], x["finish"], x["job"], x["operation"]))
        machine_orders[m] = [f"{r['job']}-{r['operation']}" for r in rows]
        if any(rows[t + 1]["start"] == rows[t]["finish"] for t in range(len(rows) - 1)):
            binding_machines.append(m)
    return {
        "status": "optimal",
        "objective": int(best_obj),
        "objective_exact": float(best_obj),
        "makespan": int(best_obj),
        "schedule": detailed,
        "solve_method": "exact_branch_and_bound",
        "solver": infer_solver_label("exact_branch_and_bound"),
        "runtime_seconds": float(runtime),
        "binding_machines": binding_machines,
        "machine_orders": machine_orders,
    }


def solve_reference(data: dict, time_limit_seconds: float = 30.0) -> dict:
    gurobi_solution = solve_with_gurobi(data, time_limit_seconds=time_limit_seconds)
    if gurobi_solution is not None:
        return gurobi_solution
    return solve_jobshop_exact(data, time_limit_seconds=time_limit_seconds)


def main():
    gt_dir = Path(__file__).resolve().parent
    data = json.loads((gt_dir / "instance_data.json").read_text(encoding="utf-8"))
    sol = solve_reference(data, time_limit_seconds=30.0)
    (gt_dir / "solution_ref.json").write_text(json.dumps(sol, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
