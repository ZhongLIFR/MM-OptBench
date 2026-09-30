#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import math
import time
from pathlib import Path


HERE = Path(__file__).resolve().parent
DATA = json.loads((HERE / "instance_data.json").read_text(encoding="utf-8"))


def build_maps(data: dict) -> tuple[dict, dict]:
    activities = data["sets"]["activities"]
    preds = {a: [] for a in activities}
    succ = {a: [] for a in activities}
    for u, v in data["precedence_arcs"]:
        preds[v].append(u)
        succ[u].append(v)
    return preds, succ


def compute_usage(start_times: dict[str, int], data: dict) -> tuple[dict[str, dict[str, int]], list[str]]:
    resources = data["sets"]["resources"]
    real_activities = data["sets"]["real_activities"]
    duration = data["duration"]
    demand = data["resource_demand"]
    caps = data["resource_capacity"]
    makespan = max(start_times[a] + duration[a] for a in real_activities)

    usage = {}
    binding = set()
    for tau in range(makespan):
        row = {r: 0 for r in resources}
        active_any = False
        for act in real_activities:
            st = start_times[act]
            if st <= tau < st + duration[act]:
                active_any = True
                for r in resources:
                    row[r] += demand[act][r]
        if active_any:
            usage[str(tau)] = {r: int(row[r]) for r in resources}
            for r in resources:
                if row[r] == caps[r] and row[r] > 0:
                    binding.add(r)
    return usage, sorted(binding)


def build_solution_payload(start_times_real: dict[str, int], runtime_seconds: float, solve_method: str, solver_name: str) -> dict:
    duration = DATA["duration"]
    real_activities = DATA["sets"]["real_activities"]
    makespan = max(start_times_real[a] + duration[a] for a in real_activities)
    start_full = {"Start": 0, **{a: int(start_times_real[a]) for a in real_activities}, "End": int(makespan)}
    finish_full = {a: int(start_full[a] + duration[a]) for a in DATA["sets"]["activities"]}
    usage_by_time, binding_resources = compute_usage(start_times_real, DATA)
    schedule = [
        {
            "activity": a,
            "start": int(start_full[a]),
            "finish": int(finish_full[a]),
            "duration": int(duration[a]),
        }
        for a in sorted(real_activities, key=lambda x: (start_full[x], x))
    ]
    return {
        "status": "optimal",
        "objective": int(makespan),
        "objective_exact": float(makespan),
        "makespan": int(makespan),
        "activity_start_times": {k: int(v) for k, v in sorted(start_full.items())},
        "activity_finish_times": {k: int(v) for k, v in sorted(finish_full.items())},
        "schedule": schedule,
        "resource_usage_by_time": usage_by_time,
        "binding_resources": binding_resources,
        "binding_resource_count": len(binding_resources),
        "solve_method": solve_method,
        "solver": solver_name,
        "runtime_seconds": float(runtime_seconds),
    }


def solve_with_gurobi(data: dict, time_limit_seconds: float = 120.0) -> dict | None:
    try:
        import gurobipy as gp
        from gurobipy import GRB
    except Exception:
        return None

    real_activities = data["sets"]["real_activities"]
    resources = data["sets"]["resources"]
    preds, _ = build_maps(data)
    duration = data["duration"]
    demand = data["resource_demand"]
    caps = data["resource_capacity"]
    horizon = sum(duration[a] for a in real_activities)

    start_clock = time.perf_counter()
    try:
        model = gp.Model(f"{data['instance_id']}_rcpsp_hard")
        model.Params.OutputFlag = 0
        model.Params.TimeLimit = time_limit_seconds
        model.Params.MIPGap = 0.0

        x = {}
        for act in real_activities:
            for t in range(horizon - duration[act] + 1):
                x[(act, t)] = model.addVar(vtype=GRB.BINARY, name=f"x_{act}_{t}")
        cmax = model.addVar(vtype=GRB.INTEGER, lb=0, name="C_max")
        model.update()

        for act in real_activities:
            model.addConstr(
                gp.quicksum(x[(act, t)] for t in range(horizon - duration[act] + 1)) == 1,
                name=f"start_once_{act}",
            )

        for act in real_activities:
            for pred in preds[act]:
                if pred == "Start":
                    continue
                model.addConstr(
                    gp.quicksum(t * x[(act, t)] for t in range(horizon - duration[act] + 1))
                    >= gp.quicksum(t * x[(pred, t)] for t in range(horizon - duration[pred] + 1))
                    + duration[pred],
                    name=f"prec_{pred}_{act}",
                )

        for tau in range(horizon):
            for r in resources:
                expr = gp.LinExpr()
                for act in real_activities:
                    for t in range(max(0, tau - duration[act] + 1), tau + 1):
                        if t <= horizon - duration[act]:
                            expr += demand[act][r] * x[(act, t)]
                model.addConstr(expr <= caps[r], name=f"res_{r}_{tau}")

        for act in real_activities:
            model.addConstr(
                cmax >= gp.quicksum((t + duration[act]) * x[(act, t)] for t in range(horizon - duration[act] + 1)),
                name=f"cmax_{act}",
            )

        model.setObjective(cmax, GRB.MINIMIZE)
        model.optimize()

        if model.Status != GRB.OPTIMAL:
            return None

        start_times = {}
        for act in real_activities:
            for t in range(horizon - duration[act] + 1):
                if x[(act, t)].X > 0.5:
                    start_times[act] = int(t)
                    break
        return build_solution_payload(
            start_times_real=start_times,
            runtime_seconds=time.perf_counter() - start_clock,
            solve_method="gurobi_time_indexed_rcpsp_hard",
            solver_name="Gurobi",
        )
    except Exception:
        return None


def exact_priority_search(data: dict, time_limit_seconds: float = 480.0) -> dict:
    real_activities = data["sets"]["real_activities"]
    resources = data["sets"]["resources"]
    duration = data["duration"]
    demand = data["resource_demand"]
    caps = data["resource_capacity"]
    preds, succ = build_maps(data)

    tail = {}

    def tail_length(act: str) -> int:
        if act in tail:
            return tail[act]
        nexts = [n for n in succ[act] if n != "End"]
        val = duration[act] + (max(tail_length(n) for n in nexts) if nexts else 0)
        tail[act] = val
        return val

    for act in real_activities:
        tail_length(act)

    start_clock = time.perf_counter()
    best_makespan = math.inf
    best_start_times = None

    def lower_bound(remaining: set[str], finish_times: dict[str, int]) -> int:
        memo = {}

        def earliest_start(act: str) -> int:
            if act in memo:
                return memo[act]
            vals = []
            for p in preds[act]:
                if p == "Start":
                    continue
                if p in finish_times:
                    vals.append(finish_times[p])
                elif p in remaining:
                    vals.append(earliest_start(p) + duration[p])
            memo[act] = max(vals, default=0)
            return memo[act]

        lb = max(finish_times.values(), default=0)
        for act in remaining:
            lb = max(lb, earliest_start(act) + tail[act])
        return lb

    def recurse(scheduled: set[str], remaining: set[str], usage: dict[int, dict[str, int]], start_times: dict[str, int], finish_times: dict[str, int]) -> None:
        nonlocal best_makespan, best_start_times
        if time.perf_counter() - start_clock > time_limit_seconds:
            raise TimeoutError("Custom exact search exceeded time limit.")

        current_makespan = max(finish_times.values(), default=0)
        if current_makespan >= best_makespan:
            return
        if lower_bound(remaining, finish_times) >= best_makespan:
            return
        if not remaining:
            best_makespan = current_makespan
            best_start_times = dict(start_times)
            return

        eligible = []
        for act in sorted(remaining):
            if all(p == "Start" or p in scheduled for p in preds[act]):
                eligible.append(act)
        eligible.sort(key=lambda a: (-tail[a], -sum(demand[a][r] for r in resources), a))

        for act in eligible:
            est = max((finish_times[p] for p in preds[act] if p != "Start"), default=0)
            t = est
            while True:
                feasible = True
                for tau in range(t, t + duration[act]):
                    row = usage.get(tau)
                    for r in resources:
                        used = 0 if row is None else row.get(r, 0)
                        if used + demand[act][r] > caps[r]:
                            feasible = False
                            break
                    if not feasible:
                        break
                if feasible:
                    break
                t += 1
                if t >= best_makespan:
                    break
            if t >= best_makespan:
                continue

            new_usage = {tau: dict(vals) for tau, vals in usage.items()}
            for tau in range(t, t + duration[act]):
                if tau not in new_usage:
                    new_usage[tau] = {r: 0 for r in resources}
                for r in resources:
                    new_usage[tau][r] += demand[act][r]
            new_start_times = dict(start_times)
            new_finish_times = dict(finish_times)
            new_start_times[act] = t
            new_finish_times[act] = t + duration[act]
            recurse(scheduled | {act}, remaining - {act}, new_usage, new_start_times, new_finish_times)

    recurse(set(), set(real_activities), {}, {}, {})
    if best_start_times is None:
        raise RuntimeError("Custom exact search failed to find a feasible schedule.")
    return build_solution_payload(
        start_times_real=best_start_times,
        runtime_seconds=time.perf_counter() - start_clock,
        solve_method="custom_exact_priority_search_rcpsp_hard",
        solver_name="Custom exact B&B",
    )


def main() -> None:
    solution = solve_with_gurobi(DATA)
    if solution is None:
        solution = exact_priority_search(DATA)
    (HERE / "solution_ref.json").write_text(json.dumps(solution, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
