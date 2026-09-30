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


def solve_with_gurobi(data: dict):
    if gp is None:
        return None

    nodes = data["sets"]["nodes"]
    depot = data["depot"]
    customers = data["sets"]["customers"]
    dist = data["travel_time_matrix"]
    service = data["service_times"]
    tw = data["time_windows"]
    big_m = data["meta_parameters"]["big_m"]

    try:
        model = gp.Model("tsptw_easy_ref")
        model.Params.OutputFlag = 0
        model.Params.TimeLimit = 60.0
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
            return None

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
            "solve_method": "gurobi_milp_exact",
        }
    except Exception:
        return None


def solve_exact_tsptw(data: dict) -> dict:
    nodes = data["sets"]["nodes"]
    depot = data["depot"]
    customers = data["sets"]["customers"]
    dist = data["travel_time_matrix"]
    service = data["service_times"]
    tw = data["time_windows"]

    gurobi_sol = solve_with_gurobi(data)
    if gurobi_sol is not None:
        return gurobi_sol

    start = time.perf_counter()
    n = len(customers)
    index = {customers[i]: i for i in range(n)}
    dp = [{} for _ in range(1 << n)]
    parent = [{} for _ in range(1 << n)]

    for j in customers:
        mask = 1 << index[j]
        travel = dist[depot][j]
        start_j = max(travel, tw[j][0])
        if start_j <= tw[j][1] + 1e-9:
            dp[mask][j] = (travel, start_j)
            parent[mask][j] = (None, None)

    for mask in range(1 << n):
        for j, (cost_so_far, service_start_j) in list(dp[mask].items()):
            depart_j = service_start_j + service[j]
            for k in customers:
                bit = 1 << index[k]
                if mask & bit:
                    continue
                arrival_k = depart_j + dist[j][k]
                start_k = max(arrival_k, tw[k][0])
                if start_k <= tw[k][1] + 1e-9:
                    new_mask = mask | bit
                    new_cost = cost_so_far + dist[j][k]
                    incumbent = dp[new_mask].get(k)
                    if incumbent is None or new_cost < incumbent[0] - 1e-9 or (
                        abs(new_cost - incumbent[0]) <= 1e-9 and start_k < incumbent[1] - 1e-9
                    ):
                        dp[new_mask][k] = (new_cost, start_k)
                        parent[new_mask][k] = (mask, j)

    full_mask = (1 << n) - 1
    best_end = None
    best_total = math.inf
    for j, (cost_so_far, service_start_j) in dp[full_mask].items():
        total_cost = cost_so_far + dist[j][depot]
        if total_cost < best_total - 1e-9:
            best_total = total_cost
            best_end = j

    if best_end is None:
        return {"status": "infeasible"}

    sequence = []
    mask = full_mask
    cur = best_end
    while cur is not None:
        sequence.append(cur)
        prev_mask, prev_node = parent[mask][cur]
        mask, cur = prev_mask, prev_node
    sequence.reverse()
    tour = [depot] + sequence + [depot]

    starts = {depot: 0.0}
    arrivals = {depot: 0.0}
    waits = {depot: 0.0}
    prev = depot
    current_time = 0.0
    for node in sequence:
        arr = current_time + dist[prev][node]
        st = max(arr, tw[node][0])
        arrivals[node] = round(arr, 2)
        starts[node] = round(st, 2)
        waits[node] = round(max(0.0, st - arr), 2)
        current_time = st + service[node]
        prev = node
    arrivals["Depot_return"] = round(current_time + dist[prev][depot], 2)

    selected_arcs = [[tour[k], tour[k + 1]] for k in range(len(tour) - 1)]
    visit_order = {tour[k]: k for k in range(len(tour) - 1)}
    binding_nodes = []
    for node in sequence:
        a_i, b_i = tw[node]
        if abs(starts[node] - a_i) <= 1e-6 or abs(starts[node] - b_i) <= 1e-6:
            binding_nodes.append(node)

    return {
        "status": "optimal",
        "objective": round(best_total, 2),
        "objective_exact": round(best_total, 2),
        "runtime_seconds": round(time.perf_counter() - start, 4),
        "tour": tour,
        "selected_arcs": selected_arcs,
        "service_start_times": starts,
        "arrival_times": arrivals,
        "waiting_times": waits,
        "visit_order": visit_order,
        "binding_time_window_nodes": binding_nodes,
        "solve_method": "exact_dynamic_programming_with_time_windows"
    }


def main() -> None:
    base = Path(__file__).resolve().parent
    data = json.loads((base / "instance_data.json").read_text(encoding="utf-8"))
    sol = solve_exact_tsptw(data)
    (base / "solution_ref.json").write_text(json.dumps(sol, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
