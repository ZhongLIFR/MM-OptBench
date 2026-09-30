#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import math
import time
from pathlib import Path

def _extract_routes(nodes, customers, depot, vehicles, x_selected, dist, demands, Q):
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
        route_costs.append(round(cost, 4))
        used_vehicles.append(v)
    served = [c for r in routes for c in r if c != depot]
    if sorted(served) != sorted(customers):
        raise RuntimeError("Extracted routes do not cover each customer exactly once")
    active_arcs = []
    for v, route in zip(used_vehicles, routes):
        for a, b in zip(route[:-1], route[1:]):
            active_arcs.append([a, b, v])
    return routes, route_loads, route_costs, used_vehicles, active_arcs

def solve_with_gurobi(data: dict) -> dict:
    import gurobipy as gp
    from gurobipy import GRB

    nodes = data["sets"]["nodes"]
    customers = data["sets"]["customers"]
    vehicles = data["sets"]["vehicles"]
    depot = data["depot"]
    dist = data["distance_matrix"]
    demands = data["demands"]
    Q = float(data["vehicle_capacity"])

    m = gp.Model("easy_cvrp")
    m.Params.OutputFlag = 0
    m.Params.TimeLimit = 120

    x = {}
    for v in vehicles:
        for i in nodes:
            for j in nodes:
                if i != j:
                    x[i, j, v] = m.addVar(vtype=GRB.BINARY, name=f"x[{i},{j},{v}]")
    u = {i: m.addVar(lb=0.0, ub=Q, vtype=GRB.CONTINUOUS, name=f"u[{i}]") for i in customers}
    m.update()

    m.setObjective(
        gp.quicksum(float(dist[i][j]) * x[i, j, v]
                    for v in vehicles for i in nodes for j in nodes if i != j),
        GRB.MINIMIZE
    )

    for i in customers:
        m.addConstr(gp.quicksum(x[i, j, v] for v in vehicles for j in nodes if j != i) == 1)
        m.addConstr(gp.quicksum(x[j, i, v] for v in vehicles for j in nodes if j != i) == 1)

    for v in vehicles:
        m.addConstr(
            gp.quicksum(x[depot, j, v] for j in nodes if j != depot)
            == gp.quicksum(x[j, depot, v] for j in nodes if j != depot)
        )
        m.addConstr(gp.quicksum(x[depot, j, v] for j in nodes if j != depot) <= 1)
        m.addConstr(gp.quicksum(x[j, depot, v] for j in nodes if j != depot) <= 1)

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

    # aggregated MTZ
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
        raise RuntimeError(f"Gurobi failed with status {m.Status}")

    x_selected = {(i, j, v): (x[i, j, v].X > 0.5) for (i, j, v) in x}
    routes, route_loads, route_costs, used_vehicles, active_arcs = _extract_routes(
        nodes, customers, depot, vehicles, x_selected, dist, demands, Q
    )

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

def solve_with_scipy(data: dict) -> dict:
    from scipy.optimize import Bounds, LinearConstraint, milp
    from scipy.sparse import coo_matrix

    nodes = data["sets"]["nodes"]
    customers = data["sets"]["customers"]
    vehicles = data["sets"]["vehicles"]
    depot = data["depot"]
    dist = data["distance_matrix"]
    demands = data["demands"]
    Q = float(data["vehicle_capacity"])

    x_index, u_index, idx = {}, {}, 0
    for v in vehicles:
        for i in nodes:
            for j in nodes:
                if i != j:
                    x_index[(i, j, v)] = idx
                    idx += 1
    for i in customers:
        u_index[i] = idx
        idx += 1
    n_var = idx

    c = [0.0] * n_var
    for key, col in x_index.items():
        i, j, _ = key
        c[col] = float(dist[i][j])

    integrality = [1] * len(x_index) + [0] * len(u_index)
    lb = [0.0] * n_var
    ub = [1.0] * len(x_index) + [Q] * len(u_index)

    rows, lo, hi = [], [], []

    def add_row(coeffs, lhs, rhs):
        row_idx = len(lo)
        for col, val in coeffs.items():
            rows.append((row_idx, col, float(val)))
        lo.append(float(lhs))
        hi.append(float(rhs))

    for i in customers:
        add_row({x_index[(i, j, v)]: 1.0 for v in vehicles for j in nodes if j != i}, 1.0, 1.0)
        add_row({x_index[(j, i, v)]: 1.0 for v in vehicles for j in nodes if j != i}, 1.0, 1.0)

    for v in vehicles:
        coeff = {x_index[(depot, j, v)]: 1.0 for j in nodes if j != depot}
        for i in nodes:
            if i != depot:
                coeff[x_index[(i, depot, v)]] = coeff.get(x_index[(i, depot, v)], 0.0) - 1.0
        add_row(coeff, 0.0, 0.0)
        add_row({x_index[(depot, j, v)]: 1.0 for j in nodes if j != depot}, 0.0, 1.0)
        add_row({x_index[(i, depot, v)]: 1.0 for i in nodes if i != depot}, 0.0, 1.0)

        for h in customers:
            coeff = {x_index[(h, j, v)]: 1.0 for j in nodes if j != h}
            for i in nodes:
                if i != h:
                    coeff[x_index[(i, h, v)]] = coeff.get(x_index[(i, h, v)], 0.0) - 1.0
            add_row(coeff, 0.0, 0.0)

        add_row({x_index[(i, j, v)]: float(demands[i]) for i in customers for j in nodes if j != i}, 0.0, Q)

    for i in customers:
        visit = {x_index[(i, j, v)]: 1.0 for v in vehicles for j in nodes if j != i}
        coeff = {u_index[i]: 1.0}
        for col, val in visit.items():
            coeff[col] = coeff.get(col, 0.0) - float(demands[i]) * val
        add_row(coeff, 0.0, math.inf)

        coeff = {u_index[i]: 1.0}
        for col, val in visit.items():
            coeff[col] = coeff.get(col, 0.0) - Q * val
        add_row(coeff, -math.inf, 0.0)

    for i in customers:
        for j in customers:
            if i != j:
                coeff = {u_index[i]: 1.0, u_index[j]: -1.0}
                for v in vehicles:
                    coeff[x_index[(i, j, v)]] = coeff.get(x_index[(i, j, v)], 0.0) + Q
                add_row(coeff, -math.inf, Q - float(demands[j]))

    row, col, dat = zip(*rows) if rows else ([], [], [])
    A = coo_matrix((dat, (row, col)), shape=(len(lo), n_var))

    t0 = time.perf_counter()
    res = milp(
        c=c,
        integrality=integrality,
        bounds=Bounds(lb, ub),
        constraints=LinearConstraint(A, lo, hi),
        options={"time_limit": 120.0, "presolve": True},
    )
    runtime = time.perf_counter() - t0

    if not getattr(res, "success", False):
        raise RuntimeError(f"SciPy MILP failed: {getattr(res, 'message', '')}")

    x_selected = {key: (res.x[col] > 0.5) for key, col in x_index.items()}
    routes, route_loads, route_costs, used_vehicles, active_arcs = _extract_routes(
        nodes, customers, depot, vehicles, x_selected, dist, demands, Q
    )

    return {
        "status": "optimal",
        "objective": round(float(res.fun), 4),
        "objective_exact": float(res.fun),
        "runtime_seconds": runtime,
        "routes": routes,
        "route_vehicle_ids": used_vehicles,
        "route_loads": route_loads,
        "route_costs": route_costs,
        "num_routes_used": len(routes),
        "active_arcs": active_arcs,
        "capacity_binding_flag": any(abs(float(load) - Q) <= 1e-9 for load in route_loads),
        "solve_method": "scipy_milp_mtz_cvrp",
    }

def solve_instance(data: dict) -> dict:
    try:
        return solve_with_gurobi(data)
    except Exception:
        return solve_with_scipy(data)

def main() -> None:
    base = Path(__file__).resolve().parent
    data = json.loads((base / "instance_data.json").read_text(encoding="utf-8"))
    sol = solve_instance(data)
    (base / "solution_ref.json").write_text(json.dumps(sol, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()