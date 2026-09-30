#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import math
import time
from functools import lru_cache
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

    try:
        customers = data["sets"]["customers"]
        vehicles = data["sets"]["vehicles"]
        nodes = data["sets"]["nodes"]
        depot = data["depot"]
        dist = data["distance_matrix"]
        demands = data["demands"]
        Q = float(data["vehicle_capacity"])
        fixed_cost = float(data.get("vehicle_fixed_cost", 0.0))

        m = gp.Model("hard_cvrp_ref")
        m.Params.OutputFlag = 0
        m.Params.TimeLimit = 60
        m.Params.MIPGap = 0.0

        x = {}
        y = {}
        for v in vehicles:
            y[v] = m.addVar(vtype=GRB.BINARY, name=f"y[{v}]")
            for i in nodes:
                for j in nodes:
                    if i != j:
                        x[i, j, v] = m.addVar(vtype=GRB.BINARY, name=f"x[{i},{j},{v}]")

        u = {i: m.addVar(lb=0.0, ub=Q, vtype=GRB.CONTINUOUS, name=f"u[{i}]") for i in customers}
        m.update()

        m.setObjective(
            gp.quicksum(float(dist[i][j]) * x[i, j, v]
                        for v in vehicles for i in nodes for j in nodes if i != j)
            + gp.quicksum(fixed_cost * y[v] for v in vehicles),
            GRB.MINIMIZE
        )

        for i in customers:
            m.addConstr(gp.quicksum(x[i, j, v] for v in vehicles for j in nodes if j != i) == 1)
            m.addConstr(gp.quicksum(x[j, i, v] for v in vehicles for j in nodes if j != i) == 1)

        for v in vehicles:
            dep_out = gp.quicksum(x[depot, j, v] for j in nodes if j != depot)
            dep_in = gp.quicksum(x[j, depot, v] for j in nodes if j != depot)
            m.addConstr(dep_out == dep_in)
            m.addConstr(dep_out <= 1)
            m.addConstr(dep_in <= 1)
            m.addConstr(dep_out <= y[v])

            for h in customers:
                m.addConstr(
                    gp.quicksum(x[h, j, v] for j in nodes if j != h)
                    == gp.quicksum(x[j, h, v] for j in nodes if j != h)
                )

            m.addConstr(
                gp.quicksum(
                    float(demands[i]) * gp.quicksum(x[i, j, v] for j in nodes if j != i)
                    for i in customers
                ) <= Q
            )

        for i in customers:
            served_i = gp.quicksum(x[i, j, v] for v in vehicles for j in nodes if j != i)
            m.addConstr(u[i] >= float(demands[i]) * served_i)
            m.addConstr(u[i] <= Q * served_i)

        for i in customers:
            for j in customers:
                if i == j:
                    continue
                m.addConstr(
                    u[i] - u[j] + Q * gp.quicksum(x[i, j, v] for v in vehicles)
                    <= Q - float(demands[j])
                )

        t0 = time.perf_counter()
        m.optimize()
        runtime = time.perf_counter() - t0
        if m.Status != GRB.OPTIMAL:
            return None

        x_selected = {(i, j, v): (x[i, j, v].X > 0.5) for (i, j, v) in x}
        routes, route_loads, route_costs, used_vehicles = [], [], [], []
        for v in vehicles:
            succ = {i: j for (i, j, vv), flag in x_selected.items() if vv == v and flag}
            if depot not in succ:
                continue
            route = [depot]
            seen = {depot}
            cur = depot
            load = 0
            cost = 0.0
            for _ in range(len(nodes) + 5):
                nxt = succ[cur]
                route.append(nxt)
                cost += float(dist[cur][nxt])
                if nxt == depot:
                    break
                if nxt in seen:
                    raise RuntimeError(f"Repeated node in extracted route for vehicle {v}: {nxt}")
                seen.add(nxt)
                load += int(demands[nxt])
                cur = nxt
            if route[-1] != depot:
                raise RuntimeError(f"Vehicle {v} route does not return to depot")
            routes.append(route)
            route_loads.append(load)
            route_costs.append(round(cost + fixed_cost, 4))
            used_vehicles.append(v)

        active_arcs = []
        for v, route in zip(used_vehicles, routes):
            for a, b in zip(route[:-1], route[1:]):
                active_arcs.append([a, b, v])

        return {
            "status": "optimal",
            "objective": round(float(m.ObjVal), 4),
            "objective_exact": float(m.ObjVal),
            "runtime_seconds": runtime,
            "routes": routes,
            "route_vehicle_ids": used_vehicles,
            "route_loads": route_loads,
            "route_costs": route_costs,
            "num_routes_used": len(routes),
            "active_arcs": active_arcs,
            "capacity_binding_flag": any(abs(float(load) - Q) <= 1e-9 for load in route_loads),
            "solve_method": "gurobi_mtz_cvrp",
        }
    except Exception:
        return None


def solve_exact_subset_dp(data: dict) -> dict:
    customers = list(data["sets"]["customers"])
    depot = data["depot"]
    vehicles = list(data["sets"]["vehicles"])
    dist = data["distance_matrix"]
    demands_map = data["demands"]
    capacity = int(data["vehicle_capacity"])
    fixed_cost = float(data.get("vehicle_fixed_cost", 0.0))

    n = len(customers)
    if n > 20:
        raise RuntimeError(f"Subset-DP reference solver only supports up to 20 customers; got {n}.")

    demands = [int(demands_map[c]) for c in customers]
    depot_cost = [float(dist[depot][c]) for c in customers]
    pair_cost = [
        [float(dist[customers[i]][customers[j]]) for j in range(n)]
        for i in range(n)
    ]

    all_masks = 1 << n
    demand_sum = [0] * all_masks
    for mask in range(1, all_masks):
        lsb = mask & -mask
        idx = lsb.bit_length() - 1
        demand_sum[mask] = demand_sum[mask ^ lsb] + demands[idx]

    feasible_masks = [mask for mask in range(1, all_masks) if demand_sum[mask] <= capacity]

    path_prev = {}

    @lru_cache(None)
    def path_cost(mask: int, last: int) -> float:
        bit = 1 << last
        if mask == bit:
            return depot_cost[last]

        prev_mask = mask ^ bit
        best = math.inf
        best_prev = -1
        rem = prev_mask
        while rem:
            lsb = rem & -rem
            prev = lsb.bit_length() - 1
            cand = path_cost(prev_mask, prev) + pair_cost[prev][last]
            if cand < best:
                best = cand
                best_prev = prev
            rem ^= lsb

        path_prev[(mask, last)] = best_prev
        return best

    route_var_cost = {}
    route_last = {}
    for mask in feasible_masks:
        rem = mask
        best = math.inf
        best_last = -1
        while rem:
            lsb = rem & -rem
            last = lsb.bit_length() - 1
            cand = path_cost(mask, last) + depot_cost[last]
            if cand < best:
                best = cand
                best_last = last
            rem ^= lsb
        route_var_cost[mask] = best
        route_last[mask] = best_last

    route_total_cost = {mask: cost + fixed_cost for mask, cost in route_var_cost.items()}

    masks_by_first = [[] for _ in range(n)]
    for mask in feasible_masks:
        rem = mask
        while rem:
            lsb = rem & -rem
            idx = lsb.bit_length() - 1
            masks_by_first[idx].append(mask)
            rem ^= lsb

    cover_choice = {}

    @lru_cache(None)
    def cover(mask: int, remaining_routes: int) -> float:
        if mask == 0:
            return 0.0
        if remaining_routes == 0 or demand_sum[mask] > remaining_routes * capacity:
            return math.inf

        first = (mask & -mask).bit_length() - 1
        best = math.inf
        best_subset = 0
        for subset in masks_by_first[first]:
            if subset & mask != subset:
                continue
            cand = route_total_cost[subset] + cover(mask ^ subset, remaining_routes - 1)
            if cand < best:
                best = cand
                best_subset = subset

        if best_subset:
            cover_choice[(mask, remaining_routes)] = best_subset
        return best

    def reconstruct_route(mask: int):
        last = route_last[mask]
        cur_mask = mask
        cur_last = last
        order = [cur_last]
        while cur_mask != (1 << cur_last):
            prev = path_prev[(cur_mask, cur_last)]
            cur_mask ^= 1 << cur_last
            cur_last = prev
            order.append(cur_last)
        order.reverse()
        route = [depot] + [customers[idx] for idx in order] + [depot]
        return route

    t0 = time.perf_counter()
    full_mask = all_masks - 1
    objective_exact = cover(full_mask, len(vehicles))
    runtime = time.perf_counter() - t0
    if not math.isfinite(objective_exact):
        raise RuntimeError("Exact subset-DP solver failed to find a feasible cover.")

    route_masks = []
    mask = full_mask
    remaining_routes = len(vehicles)
    while mask:
        subset = cover_choice[(mask, remaining_routes)]
        route_masks.append(subset)
        mask ^= subset
        remaining_routes -= 1

    routes = [reconstruct_route(mask) for mask in route_masks]
    route_loads = [demand_sum[mask] for mask in route_masks]
    route_costs = [round(route_total_cost[mask], 4) for mask in route_masks]
    used_vehicles = vehicles[: len(route_masks)]

    active_arcs = []
    for v, route in zip(used_vehicles, routes):
        for a, b in zip(route[:-1], route[1:]):
            active_arcs.append([a, b, v])

    return {
        "status": "optimal",
        "objective": round(float(objective_exact), 4),
        "objective_exact": float(objective_exact),
        "runtime_seconds": runtime,
        "routes": routes,
        "route_vehicle_ids": used_vehicles,
        "route_loads": route_loads,
        "route_costs": route_costs,
        "num_routes_used": len(routes),
        "active_arcs": active_arcs,
        "capacity_binding_flag": any(abs(float(load) - capacity) <= 1e-9 for load in route_loads),
        "solve_method": "exact_subset_dp_cvrp",
    }


def solve_instance(data: dict) -> dict:
    sol = solve_with_gurobi(data)
    if sol is not None:
        return sol
    return solve_exact_subset_dp(data)


def main() -> None:
    base = Path(__file__).resolve().parent
    data = json.loads((base / "instance_data.json").read_text(encoding="utf-8"))
    sol = solve_instance(data)
    (base / "solution_ref.json").write_text(json.dumps(sol, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
