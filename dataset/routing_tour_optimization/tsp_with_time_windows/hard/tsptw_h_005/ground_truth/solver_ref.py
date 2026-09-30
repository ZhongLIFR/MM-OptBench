#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import math
import time
from pathlib import Path

try:
    import gurobipy as gp
    from gurobipy import GRB
except Exception:
    gp = None
    GRB = None


def solve_exact_tsptw(data: dict) -> dict:
    if gp is None:
        return {"status": "solver_unavailable"}
    nodes = data["sets"]["nodes"]
    depot = data["depot"]
    customers = data["sets"]["customers"]
    dist = data["travel_time_matrix"]
    service = data["service_times"]
    tw = data["time_windows"]
    big_m = data["meta_parameters"]["big_m"]

    model = gp.Model("tsptw_hard_ref")
    model.Params.OutputFlag = 0
    model.Params.TimeLimit = 120.0
    model.Params.MIPGap = 0.0

    x = {(i, j): model.addVar(vtype=GRB.BINARY, name=f"x_{i}_{j}") for i in nodes for j in nodes if i != j}
    t = {i: model.addVar(lb=0.0, ub=tw[i][1], vtype=GRB.CONTINUOUS, name=f"t_{i}") for i in nodes}

    model.setObjective(gp.quicksum(dist[i][j] * x[i, j] for (i, j) in x), GRB.MINIMIZE)

    for i in nodes:
        model.addConstr(gp.quicksum(x[i, j] for j in nodes if j != i) == 1, name=f"out_{i}")
        model.addConstr(gp.quicksum(x[j, i] for j in nodes if j != i) == 1, name=f"in_{i}")

    model.addConstr(t[depot] == 0.0, name="depot_start")
    for i in customers:
        model.addConstr(t[i] >= tw[i][0], name=f"tw_lb_{i}")
        model.addConstr(t[i] <= tw[i][1], name=f"tw_ub_{i}")
        model.addConstr(t[i] >= dist[depot][i] - big_m * (1 - x[depot, i]), name=f"dep_arc_{i}")

    for i in customers:
        for j in customers:
            if i == j:
                continue
            model.addConstr(t[j] >= t[i] + service[i] + dist[i][j] - big_m * (1 - x[i, j]), name=f"time_{i}_{j}")

    model.optimize()
    if model.Status != GRB.OPTIMAL:
        return {"status": "infeasible_or_not_optimal", "gurobi_status": int(model.Status)}

    succ = {}
    for (i, j), var in x.items():
        if var.X > 0.5:
            succ[i] = j

    tour = [depot]
    cur = depot
    seen = {depot}
    while True:
        nxt = succ[cur]
        tour.append(nxt)
        if nxt == depot:
            break
        if nxt in seen:
            raise RuntimeError("Cycle reconstruction failed")
        seen.add(nxt)
        cur = nxt

    starts = {depot: 0.0}
    arrivals = {depot: 0.0}
    waits = {depot: 0.0}
    current_time = 0.0
    for idx in range(1, len(tour) - 1):
        prev = tour[idx - 1]
        node = tour[idx]
        arr = current_time + dist[prev][node]
        st = round(t[node].X, 2)
        arrivals[node] = round(arr, 2)
        starts[node] = st
        waits[node] = round(max(0.0, st - arr), 2)
        current_time = st + service[node]
    arrivals["Depot_return"] = round(current_time + dist[tour[-2]][depot], 2)

    selected_arcs = [[tour[k], tour[k + 1]] for k in range(len(tour) - 1)]
    visit_order = {tour[k]: k for k in range(len(tour) - 1)}
    binding_nodes = []
    for node in customers:
        a_i, b_i = tw[node]
        if abs(starts[node] - a_i) <= 1e-6 or abs(starts[node] - b_i) <= 1e-6:
            binding_nodes.append(node)

    return {
        "status": "optimal",
        "objective": round(model.ObjVal, 2),
        "objective_exact": round(float(model.ObjVal), 2),
        "runtime_seconds": round(model.Runtime, 4),
        "tour": tour,
        "selected_arcs": selected_arcs,
        "service_start_times": starts,
        "arrival_times": arrivals,
        "waiting_times": waits,
        "visit_order": visit_order,
        "binding_time_window_nodes": binding_nodes,
        "solve_method": "gurobi_milp_exact"
    }


def solve_with_fallback_branch_and_bound(data: dict) -> dict:
    nodes = data["sets"]["nodes"]
    depot = data["depot"]
    customers = data["sets"]["customers"]
    dist = data["travel_time_matrix"]
    service = data["service_times"]
    tw = data["time_windows"]

    start = time.perf_counter()
    best_cost = math.inf
    best_tour = None

    min_out = {i: min(dist[i][j] for j in nodes if j != i) for i in nodes}
    to_depot = {i: dist[i][depot] for i in nodes}

    def dfs(cur: str, current_time: float, cost_so_far: float, remaining: set[str], partial_tour: list[str]) -> None:
        nonlocal best_cost, best_tour

        if not remaining:
            total_cost = cost_so_far + dist[cur][depot]
            if total_cost < best_cost - 1e-9:
                best_cost = total_cost
                best_tour = partial_tour + [depot]
            return

        for k in remaining:
            earliest_arrival = current_time + dist[cur][k]
            earliest_start = max(earliest_arrival, tw[k][0])
            if earliest_start > tw[k][1] + 1e-9:
                return

        lower_bound = cost_so_far + to_depot[cur] + sum(min_out[k] for k in remaining)
        if lower_bound >= best_cost - 1e-9:
            return

        candidates = []
        for nxt in remaining:
            arrival = current_time + dist[cur][nxt]
            start_time = max(arrival, tw[nxt][0])
            if start_time <= tw[nxt][1] + 1e-9:
                candidates.append((tw[nxt][1], start_time, nxt))
        candidates.sort()

        for _, start_time, nxt in candidates:
            dfs(
                nxt,
                start_time + service[nxt],
                cost_so_far + dist[cur][nxt],
                remaining - {nxt},
                partial_tour + [nxt],
            )

    dfs(depot, 0.0, 0.0, set(customers), [depot])

    if best_tour is None:
        return {"status": "infeasible"}

    starts = {depot: 0.0}
    arrivals = {depot: 0.0}
    waits = {depot: 0.0}
    current_time = 0.0
    for idx in range(1, len(best_tour) - 1):
        prev = best_tour[idx - 1]
        node = best_tour[idx]
        arrival = current_time + dist[prev][node]
        start_time = max(arrival, tw[node][0])
        arrivals[node] = round(arrival, 2)
        starts[node] = round(start_time, 2)
        waits[node] = round(max(0.0, start_time - arrival), 2)
        current_time = start_time + service[node]
    arrivals["Depot_return"] = round(current_time + dist[best_tour[-2]][depot], 2)

    selected_arcs = [[best_tour[k], best_tour[k + 1]] for k in range(len(best_tour) - 1)]
    visit_order = {best_tour[k]: k for k in range(len(best_tour) - 1)}
    binding_nodes = []
    for node in customers:
        if node in starts:
            a_i, b_i = tw[node]
            if abs(starts[node] - a_i) <= 1e-6 or abs(starts[node] - b_i) <= 1e-6:
                binding_nodes.append(node)

    return {
        "status": "optimal",
        "objective": round(best_cost, 2),
        "objective_exact": round(best_cost, 2),
        "runtime_seconds": round(time.perf_counter() - start, 4),
        "tour": best_tour,
        "selected_arcs": selected_arcs,
        "service_start_times": starts,
        "arrival_times": arrivals,
        "waiting_times": waits,
        "visit_order": visit_order,
        "binding_time_window_nodes": binding_nodes,
        "solve_method": "exact_branch_and_bound_with_time_window_pruning"
    }


def main() -> None:
    base = Path(__file__).resolve().parent
    data = json.loads((base / "instance_data.json").read_text(encoding="utf-8"))
    sol = solve_exact_tsptw(data)
    if sol.get("status") != "optimal":
        sol = solve_with_fallback_branch_and_bound(data)
    (base / "solution_ref.json").write_text(json.dumps(sol, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
