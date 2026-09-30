#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
import time


def infer_solver_label(method: str | None) -> str | None:
    if not method:
        return None
    method_lower = method.lower()
    if "gurobi" in method_lower:
        return "Gurobi"
    if "scipy" in method_lower:
        return "SciPy"
    return method


def greedy_schedule(data: dict) -> dict:
    jobs = data["sets"]["jobs"]
    machines = data["sets"]["machines"]
    operations = data["sets"]["operations"]
    machine_assignment = data["machine_assignment"]
    processing_time = data["processing_time"]

    job_ready = {j: 0 for j in jobs}
    mach_ready = {m: 0 for m in machines}
    schedule = []
    levels = len(operations[jobs[0]])
    for level in range(levels):
        avail = []
        for j in jobs:
            op = operations[j][level]
            m = machine_assignment[j][op]
            d = int(processing_time[j][op])
            est = max(job_ready[j], mach_ready[m])
            avail.append((est, -d, j, op, m, d))
        avail.sort()
        for _, _, j, op, m, d in avail:
            st = max(job_ready[j], mach_ready[m])
            ft = st + d
            schedule.append({"job": j, "operation": op, "machine": m, "start": st, "finish": ft, "duration": d})
            job_ready[j] = ft
            mach_ready[m] = ft
    makespan = max(r["finish"] for r in schedule)
    return {"makespan": int(makespan), "schedule": schedule}


def solve_with_gurobi(data: dict, time_limit_seconds: float = 8.0) -> dict:
    try:
        import gurobipy as gp
        from gurobipy import GRB
    except Exception as exc:
        raise RuntimeError("gurobipy is required to generate hard-level JSS instances") from exc

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

    model = gp.Model(f"{data['instance_id']}_generator")
    model.Params.OutputFlag = 0
    model.Params.TimeLimit = time_limit_seconds
    model.Params.MIPGap = 0.0
    model.Params.MIPFocus = 1
    model.Params.Presolve = 2
    model.Params.Cuts = 1
    model.Params.Heuristics = 0.2

    s = model.addVars(op_keys, vtype=GRB.CONTINUOUS, lb=0.0, name="s")
    cmax = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name="Cmax")

    y = {}
    for m, ops in machine_ops.items():
        for i in range(len(ops)):
            for j in range(i + 1, len(ops)):
                a = ops[i]
                b = ops[j]
                y[(a, b)] = model.addVar(vtype=GRB.BINARY, name=f"y_{a[0]}_{a[1]}__{b[0]}_{b[1]}")

    model.setObjective(cmax, GRB.MINIMIZE)

    for j in jobs:
        job_ops = operations[j]
        for idx in range(len(job_ops) - 1):
            op_a = (j, job_ops[idx])
            op_b = (j, job_ops[idx + 1])
            model.addConstr(s[op_b] >= s[op_a] + durations[op_a], name=f"prec_{j}_{idx+1}")

    for m, ops in machine_ops.items():
        for i in range(len(ops)):
            for j in range(i + 1, len(ops)):
                a = ops[i]
                b = ops[j]
                z = y[(a, b)]
                model.addConstr(s[a] + durations[a] <= s[b] + horizon * (1 - z), name=f"mach1_{m}_{i}_{j}")
                model.addConstr(s[b] + durations[b] <= s[a] + horizon * z, name=f"mach2_{m}_{i}_{j}")

    for key in op_keys:
        model.addConstr(cmax >= s[key] + durations[key], name=f"mk_{key[0]}_{key[1]}")

    heur = greedy_schedule(data)
    cmax.UB = heur["makespan"]
    for rec in heur["schedule"]:
        s[(rec["job"], rec["operation"])].Start = rec["start"]
    cmax.Start = heur["makespan"]

    start_clock = time.perf_counter()
    model.optimize()

    if model.Status != GRB.OPTIMAL:
        raise RuntimeError(f"Gurobi failed to solve {data['instance_id']} to optimality within {time_limit_seconds} seconds")

    detailed = []
    for j, op in op_keys:
        st = int(round(s[(j, op)].X))
        dur = durations[(j, op)]
        detailed.append({
            "job": j,
            "operation": op,
            "machine": machine_of[(j, op)],
            "start": st,
            "finish": st + dur,
            "duration": dur,
        })
    detailed.sort(key=lambda x: (x["machine"], x["start"], x["job"], x["operation"]))

    machine_orders = {}
    binding_machines = []
    for m in machines:
        rows = [r for r in detailed if r["machine"] == m]
        rows.sort(key=lambda x: (x["start"], x["finish"], x["job"], x["operation"]))
        machine_orders[m] = [f"{r['job']}-{r['operation']}" for r in rows]
        if any(rows[t + 1]["start"] == rows[t]["finish"] for t in range(len(rows) - 1)):
            binding_machines.append(m)

    objective = int(round(cmax.X))
    result = {
        "status": "optimal",
        "objective": objective,
        "objective_exact": float(cmax.X),
        "makespan": objective,
        "schedule": detailed,
        "solve_method": "gurobi_disjunctive_milp",
        "runtime_seconds": float(model.Runtime),
        "solver": infer_solver_label("gurobi_disjunctive_milp"),
        "binding_machines": binding_machines,
        "machine_orders": machine_orders,
    }
    _ = time.perf_counter() - start_clock
    return result


def solve_with_scipy(data: dict, time_limit_seconds: float = 30.0) -> dict:
    try:
        import numpy as np
        from scipy.optimize import Bounds, LinearConstraint, milp
    except Exception as exc:
        raise RuntimeError("SciPy MILP fallback is unavailable") from exc

    jobs = data["sets"]["jobs"]
    operations = data["sets"]["operations"]
    machine_assignment = data["machine_assignment"]
    processing_time = data["processing_time"]
    machines = data["sets"]["machines"]

    op_keys = [(j, op) for j in jobs for op in operations[j]]
    durations = {(j, op): int(processing_time[j][op]) for j, op in op_keys}
    machine_of = {(j, op): machine_assignment[j][op] for j, op in op_keys}
    horizon = float(sum(durations.values()))

    machine_ops = {m: [] for m in machines}
    for key in op_keys:
        machine_ops[machine_of[key]].append(key)

    op_index = {key: idx for idx, key in enumerate(op_keys)}
    pair_keys = []
    for m in machines:
        ops = machine_ops[m]
        for i in range(len(ops)):
            for j in range(i + 1, len(ops)):
                pair_keys.append((ops[i], ops[j]))

    n_starts = len(op_keys)
    cmax_idx = n_starts
    y_offset = cmax_idx + 1
    num_vars = y_offset + len(pair_keys)

    c = np.zeros(num_vars, dtype=float)
    c[cmax_idx] = 1.0
    integrality = np.zeros(num_vars, dtype=int)
    if pair_keys:
        integrality[y_offset:] = 1

    lb = np.zeros(num_vars, dtype=float)
    ub = np.full(num_vars, np.inf, dtype=float)
    if pair_keys:
        ub[y_offset:] = 1.0

    rows = []
    lower = []
    upper = []

    for j in jobs:
        job_ops = operations[j]
        for idx in range(len(job_ops) - 1):
            a = (j, job_ops[idx])
            b = (j, job_ops[idx + 1])
            row = np.zeros(num_vars, dtype=float)
            row[op_index[b]] = 1.0
            row[op_index[a]] = -1.0
            rows.append(row)
            lower.append(float(durations[a]))
            upper.append(np.inf)

    for pair_idx, (a, b) in enumerate(pair_keys):
        y_idx = y_offset + pair_idx

        row1 = np.zeros(num_vars, dtype=float)
        row1[op_index[b]] = 1.0
        row1[op_index[a]] = -1.0
        row1[y_idx] = horizon
        rows.append(row1)
        lower.append(float(durations[a]))
        upper.append(np.inf)

        row2 = np.zeros(num_vars, dtype=float)
        row2[op_index[a]] = 1.0
        row2[op_index[b]] = -1.0
        row2[y_idx] = -horizon
        rows.append(row2)
        lower.append(float(durations[b] - horizon))
        upper.append(np.inf)

    for key in op_keys:
        row = np.zeros(num_vars, dtype=float)
        row[cmax_idx] = 1.0
        row[op_index[key]] = -1.0
        rows.append(row)
        lower.append(float(durations[key]))
        upper.append(np.inf)

    constraints = LinearConstraint(np.vstack(rows), np.array(lower, dtype=float), np.array(upper, dtype=float))

    start_clock = time.perf_counter()
    result = milp(
        c=c,
        integrality=integrality,
        bounds=Bounds(lb, ub),
        constraints=constraints,
        options={"time_limit": float(time_limit_seconds)},
    )
    runtime = time.perf_counter() - start_clock
    if not result.success or result.x is None:
        raise RuntimeError(f"SciPy MILP failed to solve {data['instance_id']} to optimality")

    x = result.x
    detailed = []
    for j, op in op_keys:
        st = int(round(float(x[op_index[(j, op)]])))
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
    detailed.sort(key=lambda rec: (rec["machine"], rec["start"], rec["job"], rec["operation"]))

    machine_orders = {}
    binding_machines = []
    for m in machines:
        rows_m = [r for r in detailed if r["machine"] == m]
        rows_m.sort(key=lambda rec: (rec["start"], rec["finish"], rec["job"], rec["operation"]))
        machine_orders[m] = [f"{r['job']}-{r['operation']}" for r in rows_m]
        if any(rows_m[t + 1]["start"] == rows_m[t]["finish"] for t in range(len(rows_m) - 1)):
            binding_machines.append(m)

    objective = int(round(float(x[cmax_idx])))
    return {
        "status": "optimal",
        "objective": objective,
        "objective_exact": float(x[cmax_idx]),
        "makespan": objective,
        "schedule": detailed,
        "solve_method": "scipy_milp_jssp",
        "runtime_seconds": float(runtime),
        "solver": infer_solver_label("scipy_milp_jssp"),
        "binding_machines": binding_machines,
        "machine_orders": machine_orders,
    }


def solve_reference(data: dict, time_limit_seconds: float = 30.0) -> dict:
    try:
        return solve_with_gurobi(data, time_limit_seconds=time_limit_seconds)
    except Exception:
        return solve_with_scipy(data, time_limit_seconds=time_limit_seconds)


def main():
    gt_dir = Path(__file__).resolve().parent
    data = json.loads((gt_dir / "instance_data.json").read_text(encoding="utf-8"))
    sol = solve_reference(data, time_limit_seconds=30.0)
    (gt_dir / "solution_ref.json").write_text(json.dumps(sol, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
