#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import math
import time
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

def solve_with_gurobi(data: dict) -> dict:
    import gurobipy as gp
    from gurobipy import GRB

    nodes = data['sets']['nodes']
    customers = data['sets']['customers']
    vehicles = data['sets']['vehicles']
    depot = data['depot']
    demands = data['demands']
    vehicle_params = data['vehicle_parameters']
    cost_lookup = _vehicle_cost_lookup(data)

    m = gp.Model('easy_hfvrp')
    m.Params.OutputFlag = 0
    m.Params.TimeLimit = 120

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
        raise RuntimeError(f'Gurobi failed with status {m.Status}')

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

def solve_with_scipy(data: dict) -> dict:
    from scipy.optimize import Bounds, LinearConstraint, milp
    from scipy.sparse import coo_matrix

    nodes = data['sets']['nodes']
    customers = data['sets']['customers']
    vehicles = data['sets']['vehicles']
    depot = data['depot']
    demands = data['demands']
    vehicle_params = data['vehicle_parameters']
    cost_lookup = _vehicle_cost_lookup(data)

    y_index = {}
    x_index = {}
    u_index = {}
    idx = 0
    for vehicle_id in vehicles:
        y_index[vehicle_id] = idx
        idx += 1
    for vehicle_id in vehicles:
        for i in nodes:
            for j in nodes:
                if i != j:
                    x_index[(i, j, vehicle_id)] = idx
                    idx += 1
    for vehicle_id in vehicles:
        for i in customers:
            u_index[(i, vehicle_id)] = idx
            idx += 1
    n_var = idx

    c = [0.0] * n_var
    integrality = [0] * n_var
    lb = [0.0] * n_var
    ub = [1.0] * n_var

    for vehicle_id, col in y_index.items():
        c[col] = float(vehicle_params[vehicle_id]['fixed_activation_cost'])
        integrality[col] = 1
    for (i, j, vehicle_id), col in x_index.items():
        c[col] = float(cost_lookup[vehicle_id][i][j])
        integrality[col] = 1
    for (i, vehicle_id), col in u_index.items():
        ub[col] = float(vehicle_params[vehicle_id]['capacity'])

    rows = []
    lo = []
    hi = []

    def add_row(coeffs: dict, lhs: float, rhs: float) -> None:
        row_idx = len(lo)
        for col, val in coeffs.items():
            rows.append((row_idx, col, float(val)))
        lo.append(float(lhs))
        hi.append(float(rhs))

    for i in customers:
        add_row({x_index[(i, j, vehicle_id)]: 1.0 for vehicle_id in vehicles for j in nodes if j != i}, 1.0, 1.0)
        add_row({x_index[(j, i, vehicle_id)]: 1.0 for vehicle_id in vehicles for j in nodes if j != i}, 1.0, 1.0)

    for vehicle_id in vehicles:
        capacity = float(vehicle_params[vehicle_id]['capacity'])

        coeff = {x_index[(depot, j, vehicle_id)]: 1.0 for j in nodes if j != depot}
        coeff[y_index[vehicle_id]] = -1.0
        add_row(coeff, 0.0, 0.0)

        coeff = {x_index[(i, depot, vehicle_id)]: 1.0 for i in nodes if i != depot}
        coeff[y_index[vehicle_id]] = -1.0
        add_row(coeff, 0.0, 0.0)

        for h in customers:
            coeff = {x_index[(h, j, vehicle_id)]: 1.0 for j in nodes if j != h}
            for i in nodes:
                if i != h:
                    coeff[x_index[(i, h, vehicle_id)]] = coeff.get(x_index[(i, h, vehicle_id)], 0.0) - 1.0
            add_row(coeff, 0.0, 0.0)

        coeff = {x_index[(i, j, vehicle_id)]: float(demands[i]) for i in customers for j in nodes if j != i}
        coeff[y_index[vehicle_id]] = -capacity
        add_row(coeff, -math.inf, 0.0)

        for i in customers:
            incoming_i = {x_index[(h, i, vehicle_id)]: 1.0 for h in nodes if h != i}

            coeff = {u_index[(i, vehicle_id)]: 1.0}
            for col, val in incoming_i.items():
                coeff[col] = coeff.get(col, 0.0) - float(demands[i]) * val
            add_row(coeff, 0.0, math.inf)

            coeff = {u_index[(i, vehicle_id)]: 1.0}
            for col, val in incoming_i.items():
                coeff[col] = coeff.get(col, 0.0) - capacity * val
            add_row(coeff, -math.inf, 0.0)

        for i in customers:
            for j in customers:
                if i == j:
                    continue
                coeff = {
                    u_index[(i, vehicle_id)]: 1.0,
                    u_index[(j, vehicle_id)]: -1.0,
                    x_index[(i, j, vehicle_id)]: capacity,
                }
                for h in nodes:
                    if h != j:
                        arc = x_index[(h, j, vehicle_id)]
                        coeff[arc] = coeff.get(arc, 0.0) + capacity
                add_row(coeff, -math.inf, 2.0 * capacity - float(demands[j]))

    row, col, dat = zip(*rows) if rows else ([], [], [])
    A = coo_matrix((dat, (row, col)), shape=(len(lo), n_var))

    start = time.perf_counter()
    res = milp(
        c=c,
        integrality=integrality,
        bounds=Bounds(lb, ub),
        constraints=LinearConstraint(A, lo, hi),
        options={'time_limit': 120.0, 'presolve': True},
    )
    runtime = time.perf_counter() - start

    if not getattr(res, 'success', False):
        raise RuntimeError(
            f"SciPy MILP did not solve instance: status={getattr(res, 'status', None)}, "
            f"message={getattr(res, 'message', '')}"
        )

    x_selected = {key: (res.x[col] > 0.5) for key, col in x_index.items()}
    y_selected = {vehicle_id: (res.x[col] > 0.5) for vehicle_id, col in y_index.items()}
    route_data = _extract_routes(data, x_selected, y_selected)

    return {
        'status': 'optimal',
        'objective': round(float(res.fun), 4),
        'objective_exact': float(res.fun),
        'runtime_seconds': runtime,
        'solve_method': 'scipy_milp_mtz_hfvrp',
        **route_data,
    }

def solve_instance(data: dict) -> dict:
    try:
        return solve_with_gurobi(data)
    except Exception:
        return solve_with_scipy(data)

def main() -> None:
    base = Path(__file__).resolve().parent
    data = json.loads((base / 'instance_data.json').read_text(encoding='utf-8'))
    sol = solve_instance(data)
    (base / 'solution_ref.json').write_text(json.dumps(sol, indent=2), encoding='utf-8')

if __name__ == '__main__':
    main()
