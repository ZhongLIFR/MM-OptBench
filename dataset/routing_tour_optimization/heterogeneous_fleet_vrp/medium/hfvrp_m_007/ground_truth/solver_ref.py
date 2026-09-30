#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import math
import time
from functools import lru_cache
from pathlib import Path

def _vehicle_cost_lookup(data: dict) -> dict:
    lookup = {}
    vehicle_params = data['vehicle_parameters']
    cost_by_type = data['travel_cost_matrix_by_vehicle_type']
    for vehicle_id, params in vehicle_params.items():
        lookup[vehicle_id] = cost_by_type[params['type_id']]
    return lookup

def _extract_routes(data: dict, x_selected: dict, y_selected: dict) -> dict:
    nodes = data['sets']['nodes']
    customers = data['sets']['customers']
    vehicles = data['sets']['vehicles']
    depot = data['depot']
    demands = data['demands']
    base_dist = data['base_distance_matrix']
    vehicle_params = data['vehicle_parameters']
    cost_lookup = _vehicle_cost_lookup(data)

    routes = []
    route_vehicle_ids = []
    route_vehicle_types = []
    route_loads = []
    route_capacities = []
    route_base_distances = []
    route_variable_costs = []
    route_total_costs = []
    active_arcs = []

    for vehicle_id in vehicles:
        succ = {i: j for (i, j, k), flag in x_selected.items() if k == vehicle_id and flag}
        used = bool(y_selected.get(vehicle_id, False) or depot in succ)
        if not used:
            continue
        if depot not in succ:
            raise RuntimeError(f'Activated vehicle {vehicle_id} has no depot departure arc')

        route = [depot]
        seen = {depot}
        cur = depot
        load = 0
        base_total = 0.0
        variable_total = 0.0
        vehicle_type = vehicle_params[vehicle_id]['type_id']
        vehicle_cost = cost_lookup[vehicle_id]

        for _ in range(len(nodes) + 5):
            nxt = succ[cur]
            route.append(nxt)
            active_arcs.append([cur, nxt, vehicle_id])
            base_total += float(base_dist[cur][nxt])
            variable_total += float(vehicle_cost[cur][nxt])
            if nxt == depot:
                break
            if nxt in seen:
                raise RuntimeError(f'Cycle extraction failed for vehicle {vehicle_id}: repeated node {nxt}')
            seen.add(nxt)
            load += int(demands[nxt])
            cur = nxt

        if route[-1] != depot:
            raise RuntimeError(f'Route extraction failed for vehicle {vehicle_id}: did not return to depot')

        routes.append(route)
        route_vehicle_ids.append(vehicle_id)
        route_vehicle_types.append(vehicle_type)
        route_loads.append(load)
        route_capacities.append(int(vehicle_params[vehicle_id]['capacity']))
        route_base_distances.append(round(base_total, 2))
        route_variable_costs.append(round(variable_total, 4))
        route_total_costs.append(round(variable_total + float(vehicle_params[vehicle_id]['fixed_activation_cost']), 4))

    served = [cust for route in routes for cust in route if cust != depot]
    if sorted(served) != sorted(customers):
        raise RuntimeError('Extracted routes do not cover each customer exactly once')

    activated_vehicles = route_vehicle_ids[:]
    unused_vehicles = [vehicle_id for vehicle_id in vehicles if vehicle_id not in activated_vehicles]
    objective_from_routes = round(sum(route_total_costs), 4)
    capacity_binding_flag = any(
        abs(float(load) - float(cap)) <= 1e-9
        for load, cap in zip(route_loads, route_capacities)
    )

    return {
        'routes': routes,
        'route_vehicle_ids': route_vehicle_ids,
        'route_vehicle_types': route_vehicle_types,
        'route_loads': route_loads,
        'route_capacities': route_capacities,
        'route_base_distances': route_base_distances,
        'route_variable_costs': route_variable_costs,
        'route_total_costs': route_total_costs,
        'activated_vehicles': activated_vehicles,
        'unused_vehicles': unused_vehicles,
        'active_arcs': active_arcs,
        'num_routes_used': len(routes),
        'capacity_binding_flag': capacity_binding_flag,
        'objective_from_routes': objective_from_routes,
    }

def _assemble_solution_from_sequences(data: dict, assignments: list[tuple[str, list[str]]], runtime_seconds: float, solve_method: str, objective_exact: float) -> dict:
    depot = data['depot']
    demands = data['demands']
    base_dist = data['base_distance_matrix']
    vehicle_params = data['vehicle_parameters']
    cost_lookup = _vehicle_cost_lookup(data)

    routes = []
    route_vehicle_ids = []
    route_vehicle_types = []
    route_loads = []
    route_capacities = []
    route_base_distances = []
    route_variable_costs = []
    route_total_costs = []
    active_arcs = []

    for vehicle_id, customer_sequence in assignments:
        route = [depot] + customer_sequence + [depot]
        vehicle_type = vehicle_params[vehicle_id]['type_id']
        capacity = int(vehicle_params[vehicle_id]['capacity'])
        fixed_cost = float(vehicle_params[vehicle_id]['fixed_activation_cost'])
        variable_cost = sum(float(cost_lookup[vehicle_id][a][b]) for a, b in zip(route[:-1], route[1:]))
        base_cost = sum(float(base_dist[a][b]) for a, b in zip(route[:-1], route[1:]))
        load = sum(int(demands[c]) for c in customer_sequence)

        routes.append(route)
        route_vehicle_ids.append(vehicle_id)
        route_vehicle_types.append(vehicle_type)
        route_loads.append(load)
        route_capacities.append(capacity)
        route_base_distances.append(round(base_cost, 2))
        route_variable_costs.append(round(variable_cost, 4))
        route_total_costs.append(round(variable_cost + fixed_cost, 4))

        for a, b in zip(route[:-1], route[1:]):
            active_arcs.append([a, b, vehicle_id])

    objective = round(sum(route_total_costs), 4)
    capacity_binding_flag = any(abs(float(load) - float(cap)) <= 1e-9 for load, cap in zip(route_loads, route_capacities))

    return {
        'status': 'optimal',
        'objective': objective,
        'objective_exact': float(objective_exact),
        'runtime_seconds': runtime_seconds,
        'solve_method': solve_method,
        'routes': routes,
        'route_vehicle_ids': route_vehicle_ids,
        'route_vehicle_types': route_vehicle_types,
        'route_loads': route_loads,
        'route_capacities': route_capacities,
        'route_base_distances': route_base_distances,
        'route_variable_costs': route_variable_costs,
        'route_total_costs': route_total_costs,
        'activated_vehicles': route_vehicle_ids[:],
        'unused_vehicles': [vehicle_id for vehicle_id in data['sets']['vehicles'] if vehicle_id not in route_vehicle_ids],
        'active_arcs': active_arcs,
        'num_routes_used': len(routes),
        'capacity_binding_flag': capacity_binding_flag,
        'objective_from_routes': objective,
    }

def solve_with_gurobi(data: dict):
    try:
        import gurobipy as gp
        from gurobipy import GRB
    except Exception:
        return None

    try:
        nodes = data['sets']['nodes']
        customers = data['sets']['customers']
        vehicles = data['sets']['vehicles']
        depot = data['depot']
        demands = data['demands']
        vehicle_params = data['vehicle_parameters']
        cost_lookup = _vehicle_cost_lookup(data)

        m = gp.Model('medium_hfvrp')
        m.Params.OutputFlag = 0
        m.Params.TimeLimit = 15
        m.Params.MIPGap = 0.0

        y = {vehicle_id: m.addVar(vtype=GRB.BINARY, name=f'y[{vehicle_id}]') for vehicle_id in vehicles}
        x = {}
        u = {}
        for vehicle_id in vehicles:
            capacity = float(vehicle_params[vehicle_id]['capacity'])
            for i in customers:
                u[i, vehicle_id] = m.addVar(lb=0.0, ub=capacity, vtype=GRB.CONTINUOUS, name=f'u[{i},{vehicle_id}]')
            for i in nodes:
                for j in nodes:
                    if i != j:
                        x[i, j, vehicle_id] = m.addVar(vtype=GRB.BINARY, name=f'x[{i},{j},{vehicle_id}]')
        m.update()

        m.setObjective(
            gp.quicksum(float(vehicle_params[vehicle_id]['fixed_activation_cost']) * y[vehicle_id] for vehicle_id in vehicles)
            + gp.quicksum(
                float(cost_lookup[vehicle_id][i][j]) * x[i, j, vehicle_id]
                for vehicle_id in vehicles
                for i in nodes
                for j in nodes
                if i != j
            ),
            GRB.MINIMIZE,
        )

        for i in customers:
            m.addConstr(gp.quicksum(x[i, j, vehicle_id] for vehicle_id in vehicles for j in nodes if j != i) == 1)
            m.addConstr(gp.quicksum(x[j, i, vehicle_id] for vehicle_id in vehicles for j in nodes if j != i) == 1)

        for vehicle_id in vehicles:
            capacity = float(vehicle_params[vehicle_id]['capacity'])
            m.addConstr(gp.quicksum(x[depot, j, vehicle_id] for j in nodes if j != depot) == y[vehicle_id])
            m.addConstr(gp.quicksum(x[i, depot, vehicle_id] for i in nodes if i != depot) == y[vehicle_id])

            for h in customers:
                m.addConstr(
                    gp.quicksum(x[h, j, vehicle_id] for j in nodes if j != h)
                    == gp.quicksum(x[j, h, vehicle_id] for j in nodes if j != h)
                )

            m.addConstr(
                gp.quicksum(
                    float(demands[i]) * gp.quicksum(x[i, j, vehicle_id] for j in nodes if j != i)
                    for i in customers
                ) <= capacity * y[vehicle_id]
            )

            for i in customers:
                incoming_i = gp.quicksum(x[h, i, vehicle_id] for h in nodes if h != i)
                m.addConstr(u[i, vehicle_id] >= float(demands[i]) * incoming_i)
                m.addConstr(u[i, vehicle_id] <= capacity * incoming_i)

            for i in customers:
                for j in customers:
                    if i == j:
                        continue
                    incoming_j = gp.quicksum(x[h, j, vehicle_id] for h in nodes if h != j)
                    m.addConstr(
                        u[i, vehicle_id] - u[j, vehicle_id]
                        + capacity * x[i, j, vehicle_id]
                        + capacity * incoming_j
                        <= 2.0 * capacity - float(demands[j])
                    )

        start = time.perf_counter()
        m.optimize()
        runtime = time.perf_counter() - start

        if m.Status != GRB.OPTIMAL:
            return None

        x_selected = {(i, j, vehicle_id): (x[i, j, vehicle_id].X > 0.5) for (i, j, vehicle_id) in x}
        y_selected = {vehicle_id: (y[vehicle_id].X > 0.5) for vehicle_id in vehicles}
        route_data = _extract_routes(data, x_selected, y_selected)

        return {
            'status': 'optimal',
            'objective': round(float(m.ObjVal), 4),
            'objective_exact': float(m.ObjVal),
            'runtime_seconds': runtime,
            'solve_method': 'gurobi_mtz_hfvrp',
            **route_data,
        }
    except Exception:
        return None

def solve_exact_subset_dp(data: dict) -> dict:
    customers = list(data['sets']['customers'])
    depot = data['depot']
    vehicles = list(data['sets']['vehicles'])
    demands_map = data['demands']
    base_dist = data['base_distance_matrix']
    vehicle_params = data['vehicle_parameters']

    n = len(customers)
    if n > 18:
        raise RuntimeError(f'Exact subset-DP fallback only supports up to 18 customers; got {n}.')

    demands = [int(demands_map[c]) for c in customers]
    depot_cost = [float(base_dist[depot][c]) for c in customers]
    pair_cost = [[float(base_dist[customers[i]][customers[j]]) for j in range(n)] for i in range(n)]
    max_capacity = max(int(vehicle_params[v]['capacity']) for v in vehicles)

    all_masks = 1 << n
    demand_sum = [0] * all_masks
    for mask in range(1, all_masks):
        lsb = mask & -mask
        idx = lsb.bit_length() - 1
        demand_sum[mask] = demand_sum[mask ^ lsb] + demands[idx]

    feasible_masks = [mask for mask in range(1, all_masks) if demand_sum[mask] <= max_capacity]
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

    route_base_cost = {}
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
        route_base_cost[mask] = best
        route_last[mask] = best_last

    vehicle_masks_by_first = []
    vehicle_costs = []
    capacities = []
    for vehicle_id in vehicles:
        capacity = int(vehicle_params[vehicle_id]['capacity'])
        fixed_cost = float(vehicle_params[vehicle_id]['fixed_activation_cost'])
        multiplier = float(vehicle_params[vehicle_id]['distance_multiplier'])
        capacities.append(capacity)
        cost_map = {}
        masks_by_first = [[] for _ in range(n)]
        for mask in feasible_masks:
            if demand_sum[mask] > capacity:
                continue
            cost_map[mask] = fixed_cost + multiplier * route_base_cost[mask]
            rem = mask
            while rem:
                lsb = rem & -rem
                idx = lsb.bit_length() - 1
                masks_by_first[idx].append(mask)
                rem ^= lsb
        vehicle_costs.append(cost_map)
        vehicle_masks_by_first.append(masks_by_first)

    remaining_cap = [0] * (len(vehicles) + 1)
    for idx in range(len(vehicles) - 1, -1, -1):
        remaining_cap[idx] = remaining_cap[idx + 1] + capacities[idx]

    choices = {}

    @lru_cache(None)
    def cover(mask: int, idx: int) -> float:
        if mask == 0:
            return 0.0
        if idx == len(vehicles) or demand_sum[mask] > remaining_cap[idx]:
            return math.inf

        best = cover(mask, idx + 1)
        best_choice = ('skip', 0)
        first = (mask & -mask).bit_length() - 1
        for subset in vehicle_masks_by_first[idx][first]:
            if subset & mask != subset:
                continue
            cand = vehicle_costs[idx][subset] + cover(mask ^ subset, idx + 1)
            if cand < best:
                best = cand
                best_choice = ('use', subset)

        choices[(mask, idx)] = best_choice
        return best

    def reconstruct_customer_sequence(mask: int) -> list[str]:
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
        return [customers[idx] for idx in order]

    start = time.perf_counter()
    full_mask = all_masks - 1
    objective_exact = cover(full_mask, 0)
    runtime = time.perf_counter() - start
    if not math.isfinite(objective_exact):
        raise RuntimeError('Exact subset-DP fallback failed to find a feasible solution.')

    assignments = []
    mask = full_mask
    idx = 0
    while idx < len(vehicles) and mask:
        decision = choices.get((mask, idx), ('skip', 0))
        if decision[0] == 'use':
            subset = decision[1]
            assignments.append((vehicles[idx], reconstruct_customer_sequence(subset)))
            mask ^= subset
        idx += 1
    if mask != 0:
        raise RuntimeError('Failed to reconstruct the exact subset-DP solution.')

    return _assemble_solution_from_sequences(
        data=data,
        assignments=assignments,
        runtime_seconds=runtime,
        solve_method='exact_subset_dp_hfvrp',
        objective_exact=float(objective_exact),
    )

def solve_instance(data: dict) -> dict:
    sol = solve_with_gurobi(data)
    if sol is not None:
        return sol
    return solve_exact_subset_dp(data)

def main() -> None:
    base = Path(__file__).resolve().parent
    data = json.loads((base / 'instance_data.json').read_text(encoding='utf-8'))
    sol = solve_instance(data)
    (base / 'solution_ref.json').write_text(json.dumps(sol, indent=2), encoding='utf-8')

if __name__ == '__main__':
    main()
