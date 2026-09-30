#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

try:
    import gurobipy as gp
    from gurobipy import GRB
except Exception:
    gp = None
    GRB = None


DEPOT = "Depot"
TIME_LIMIT_SECONDS = 240.0


def infer_solver_label(method: str | None) -> str | None:
    if not method:
        return None
    method_lower = method.lower()
    if "gurobi" in method_lower:
        return "Gurobi"
    if "scipy" in method_lower:
        return "SciPy"
    return method


def load_instance(base: Path) -> dict:
    return json.loads((base / "ground_truth" / "instance_data.json").read_text(encoding="utf-8"))


def normalize_number(value: float, decimals: int = 4):
    rounded = round(float(value))
    if abs(float(value) - rounded) <= 1e-9:
        return int(rounded)
    return float(round(float(value), decimals))


def clean_float(value: float, decimals: int = 6) -> float:
    return 0.0 if abs(float(value)) < 1e-9 else float(round(float(value), decimals))


def reconstruct_route(arcs: list[tuple[str, str]], customers: list[str]) -> list[str]:
    if not arcs:
        return []
    next_map = {}
    for i, j in arcs:
        next_map[i] = j
    route = [DEPOT]
    current = DEPOT
    for _ in range(len(customers) + 2):
        nxt = next_map.get(current)
        if nxt is None:
            break
        route.append(nxt)
        if nxt == DEPOT:
            return route
        current = nxt
    raise RuntimeError(f"Failed to reconstruct a depot-rooted route from arcs: {arcs}")


def package_solution(
    data: dict,
    x_solution: dict,
    z_solution: dict,
    q_solution: dict,
    inventory_solution: dict,
    y_solution: dict,
    runtime: float,
    objective_value: float,
    solve_method: str,
) -> dict:
    periods = data["sets"]["periods"]
    customers = data["sets"]["customers"]
    vehicles = data["sets"]["vehicles"]
    distance = data["distance_matrix"]
    demands = data["demands"]
    holding_cost = data["holding_cost"]
    dispatch_cost_by_vehicle = data["fixed_dispatch_cost_by_vehicle"]
    vehicle_capacity_by_vehicle = data["vehicle_capacity_by_vehicle"]

    dispatch_by_vehicle_period = {
        vehicle: {period: int(round(float(y_solution[(vehicle, period)]))) for period in periods}
        for vehicle in vehicles
    }
    route_by_vehicle_period = {vehicle: {} for vehicle in vehicles}
    route_arcs_by_vehicle_period = {vehicle: {} for vehicle in vehicles}
    visited_customers_by_vehicle_period = {vehicle: {} for vehicle in vehicles}
    route_cost_by_vehicle_period = {vehicle: {} for vehicle in vehicles}
    dispatch_cost_by_vehicle_period = {vehicle: {} for vehicle in vehicles}
    load_by_vehicle_period = {vehicle: {} for vehicle in vehicles}
    deliveries_by_vehicle_period = {
        vehicle: {
            period: {customer: clean_float(float(q_solution[(customer, vehicle, period)]), 4) for customer in customers}
            for period in periods
        }
        for vehicle in vehicles
    }

    for vehicle in vehicles:
        for period in periods:
            arcs = sorted(
                [
                    (i, j)
                    for (i, j, v, t), value in x_solution.items()
                    if v == vehicle and t == period and int(round(float(value))) == 1
                ],
                key=lambda item: (item[0], item[1]),
            )
            route = reconstruct_route(arcs, customers) if dispatch_by_vehicle_period[vehicle][period] == 1 else []
            route_by_vehicle_period[vehicle][period] = route
            route_arcs_by_vehicle_period[vehicle][period] = (
                [[route[idx], route[idx + 1]] for idx in range(len(route) - 1)]
                if route
                else []
            )
            visited_customers_by_vehicle_period[vehicle][period] = [node for node in route if node != DEPOT]
            route_cost_by_vehicle_period[vehicle][period] = clean_float(sum(float(distance[i][j]) for i, j in arcs), 4)
            dispatch_cost_by_vehicle_period[vehicle][period] = clean_float(
                float(dispatch_cost_by_vehicle[vehicle]) * dispatch_by_vehicle_period[vehicle][period],
                4,
            )
            load_by_vehicle_period[vehicle][period] = clean_float(
                sum(deliveries_by_vehicle_period[vehicle][period][customer] for customer in customers),
                4,
            )

    deliveries = {
        customer: {
            period: clean_float(sum(deliveries_by_vehicle_period[vehicle][period][customer] for vehicle in vehicles), 4)
            for period in periods
        }
        for customer in customers
    }
    ending_inventory = {
        customer: {period: clean_float(float(inventory_solution[(customer, period)]), 4) for period in periods}
        for customer in customers
    }
    visit_indicator = {
        customer: {
            period: {vehicle: int(round(float(z_solution[(customer, vehicle, period)]))) for vehicle in vehicles}
            for period in periods
        }
        for customer in customers
    }
    holding_cost_by_period = {
        period: clean_float(sum(float(holding_cost[c]) * float(inventory_solution[(c, period)]) for c in customers), 4)
        for period in periods
    }
    used_vehicles_by_period = {
        period: [vehicle for vehicle in vehicles if dispatch_by_vehicle_period[vehicle][period] == 1]
        for period in periods
    }
    dispatch_periods = [period for period in periods if used_vehicles_by_period[period]]
    route_cost_by_period = {
        period: clean_float(sum(route_cost_by_vehicle_period[vehicle][period] for vehicle in vehicles), 4)
        for period in periods
    }
    dispatch_cost_by_period = {
        period: clean_float(sum(dispatch_cost_by_vehicle_period[vehicle][period] for vehicle in vehicles), 4)
        for period in periods
    }
    realized_total_demand = {period: int(sum(int(demands[c][period]) for c in customers)) for period in periods}

    return {
        "status": "optimal",
        "objective": normalize_number(objective_value, 4),
        "objective_exact": float(objective_value),
        "runtime_seconds": runtime,
        "dispatch_by_vehicle_period": dispatch_by_vehicle_period,
        "dispatch_periods": dispatch_periods,
        "used_vehicles_by_period": used_vehicles_by_period,
        "route_by_vehicle_period": route_by_vehicle_period,
        "route_arcs_by_vehicle_period": route_arcs_by_vehicle_period,
        "visited_customers_by_vehicle_period": visited_customers_by_vehicle_period,
        "visit_indicator": visit_indicator,
        "deliveries_by_vehicle_period": deliveries_by_vehicle_period,
        "deliveries": deliveries,
        "ending_inventory": ending_inventory,
        "aggregate_demand_by_period": realized_total_demand,
        "load_by_vehicle_period": load_by_vehicle_period,
        "route_cost_by_vehicle_period": route_cost_by_vehicle_period,
        "route_cost_by_period": route_cost_by_period,
        "holding_cost_by_period": holding_cost_by_period,
        "dispatch_cost_by_vehicle_period": dispatch_cost_by_vehicle_period,
        "dispatch_cost_by_period": dispatch_cost_by_period,
        "total_routing_cost": clean_float(sum(route_cost_by_period.values()), 4),
        "total_holding_cost": clean_float(sum(holding_cost_by_period.values()), 4),
        "total_dispatch_cost": clean_float(sum(dispatch_cost_by_period.values()), 4),
        "capacity_binding_vehicle_periods": [
            f"{vehicle}:{period}"
            for vehicle in vehicles
            for period in periods
            if dispatch_by_vehicle_period[vehicle][period] == 1
            and abs(load_by_vehicle_period[vehicle][period] - float(vehicle_capacity_by_vehicle[vehicle])) <= 1e-6
        ],
        "solve_method": solve_method,
        "solver": infer_solver_label(solve_method),
    }


def solve_with_gurobi(data: dict) -> dict | None:
    if gp is None:
        return None
    periods = data["sets"]["periods"]
    customers = data["sets"]["customers"]
    nodes = data["sets"]["nodes"]
    vehicles = data["sets"]["vehicles"]
    distance = data["distance_matrix"]
    demands = data["demands"]
    initial_inventory = data["initial_inventory"]
    inventory_capacity = data["inventory_capacity"]
    holding_cost = data["holding_cost"]
    delivery_ub = data["delivery_upper_bound"]
    vehicle_capacity_by_vehicle = data["vehicle_capacity_by_vehicle"]
    dispatch_cost_by_vehicle = data["fixed_dispatch_cost_by_vehicle"]
    n_customers = len(customers)

    start = time.perf_counter()
    try:
        model = gp.Model("irp_medium")
        model.Params.OutputFlag = 0
        model.Params.TimeLimit = TIME_LIMIT_SECONDS
        model.Params.MIPGap = 0.0

        x = {
            (i, j, vehicle, period): model.addVar(vtype=GRB.BINARY, name=f"x_{i}_{j}_{vehicle}_{period}")
            for vehicle in vehicles
            for period in periods
            for i in nodes
            for j in nodes
            if i != j
        }
        z = {
            (customer, vehicle, period): model.addVar(vtype=GRB.BINARY, name=f"z_{customer}_{vehicle}_{period}")
            for customer in customers
            for vehicle in vehicles
            for period in periods
        }
        q = {
            (customer, vehicle, period): model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"q_{customer}_{vehicle}_{period}")
            for customer in customers
            for vehicle in vehicles
            for period in periods
        }
        inv = {
            (customer, period): model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"I_{customer}_{period}")
            for customer in customers
            for period in periods
        }
        y = {
            (vehicle, period): model.addVar(vtype=GRB.BINARY, name=f"y_{vehicle}_{period}")
            for vehicle in vehicles
            for period in periods
        }
        u = {
            (customer, vehicle, period): model.addVar(lb=0.0, ub=float(n_customers), vtype=GRB.CONTINUOUS, name=f"u_{customer}_{vehicle}_{period}")
            for customer in customers
            for vehicle in vehicles
            for period in periods
        }

        model.setObjective(
            gp.quicksum(
                float(distance[i][j]) * x[i, j, vehicle, period]
                for vehicle in vehicles
                for period in periods
                for i in nodes
                for j in nodes
                if i != j
            )
            + gp.quicksum(float(holding_cost[customer]) * inv[customer, period] for customer in customers for period in periods)
            + gp.quicksum(float(dispatch_cost_by_vehicle[vehicle]) * y[vehicle, period] for vehicle in vehicles for period in periods),
            GRB.MINIMIZE,
        )

        for customer in customers:
            for idx_t, period in enumerate(periods):
                delivered = gp.quicksum(q[customer, vehicle, period] for vehicle in vehicles)
                if idx_t == 0:
                    model.addConstr(
                        float(initial_inventory[customer]) + delivered == float(demands[customer][period]) + inv[customer, period],
                        name=f"balance_{customer}_{period}",
                    )
                else:
                    prev = periods[idx_t - 1]
                    model.addConstr(
                        inv[customer, prev] + delivered == float(demands[customer][period]) + inv[customer, period],
                        name=f"balance_{customer}_{period}",
                    )
                model.addConstr(inv[customer, period] <= float(inventory_capacity[customer]), name=f"cap_{customer}_{period}")
                model.addConstr(
                    gp.quicksum(z[customer, vehicle, period] for vehicle in vehicles) <= 1.0,
                    name=f"one_vehicle_{customer}_{period}",
                )
                for vehicle in vehicles:
                    model.addConstr(
                        q[customer, vehicle, period] <= float(delivery_ub[customer][period]) * z[customer, vehicle, period],
                        name=f"deliver_link_{customer}_{vehicle}_{period}",
                    )
                    model.addConstr(
                        z[customer, vehicle, period] <= y[vehicle, period],
                        name=f"visit_dispatch_{customer}_{vehicle}_{period}",
                    )
                    model.addConstr(u[customer, vehicle, period] >= z[customer, vehicle, period], name=f"u_lb_{customer}_{vehicle}_{period}")
                    model.addConstr(
                        u[customer, vehicle, period] <= float(n_customers) * z[customer, vehicle, period],
                        name=f"u_ub_{customer}_{vehicle}_{period}",
                    )

        for vehicle in vehicles:
            Q = float(vehicle_capacity_by_vehicle[vehicle])
            for period in periods:
                model.addConstr(
                    gp.quicksum(q[customer, vehicle, period] for customer in customers) <= Q * y[vehicle, period],
                    name=f"vehicle_capacity_{vehicle}_{period}",
                )
                model.addConstr(
                    gp.quicksum(x[DEPOT, customer, vehicle, period] for customer in customers) == y[vehicle, period],
                    name=f"depot_depart_{vehicle}_{period}",
                )
                model.addConstr(
                    gp.quicksum(x[customer, DEPOT, vehicle, period] for customer in customers) == y[vehicle, period],
                    name=f"depot_return_{vehicle}_{period}",
                )
                for customer in customers:
                    model.addConstr(
                        gp.quicksum(x[i, customer, vehicle, period] for i in nodes if i != customer) == z[customer, vehicle, period],
                        name=f"in_degree_{customer}_{vehicle}_{period}",
                    )
                    model.addConstr(
                        gp.quicksum(x[customer, j, vehicle, period] for j in nodes if j != customer) == z[customer, vehicle, period],
                        name=f"out_degree_{customer}_{vehicle}_{period}",
                    )
                for i in customers:
                    for j in customers:
                        if i == j:
                            continue
                        model.addConstr(
                            u[i, vehicle, period] - u[j, vehicle, period] + float(n_customers) * x[i, j, vehicle, period]
                            <= float(n_customers - 1)
                            + float(n_customers) * (1.0 - z[i, vehicle, period])
                            + float(n_customers) * (1.0 - z[j, vehicle, period]),
                            name=f"mtz_{i}_{j}_{vehicle}_{period}",
                        )

        model.optimize()
        runtime = time.perf_counter() - start
        if model.Status != GRB.OPTIMAL:
            return None

        x_solution = {(i, j, vehicle, period): int(round(float(var.X))) for (i, j, vehicle, period), var in x.items()}
        z_solution = {(customer, vehicle, period): int(round(float(var.X))) for (customer, vehicle, period), var in z.items()}
        q_solution = {(customer, vehicle, period): clean_float(float(var.X), 6) for (customer, vehicle, period), var in q.items()}
        inventory_solution = {(customer, period): clean_float(float(var.X), 6) for (customer, period), var in inv.items()}
        y_solution = {(vehicle, period): int(round(float(var.X))) for (vehicle, period), var in y.items()}

        return package_solution(
            data,
            x_solution,
            z_solution,
            q_solution,
            inventory_solution,
            y_solution,
            runtime,
            float(model.ObjVal),
            "gurobi_milp_irp_medium",
        )
    except Exception:
        return None


def solve_with_scipy(data: dict) -> dict:
    periods = data["sets"]["periods"]
    customers = data["sets"]["customers"]
    nodes = data["sets"]["nodes"]
    vehicles = data["sets"]["vehicles"]
    distance = data["distance_matrix"]
    demands = data["demands"]
    initial_inventory = data["initial_inventory"]
    inventory_capacity = data["inventory_capacity"]
    holding_cost = data["holding_cost"]
    delivery_ub = data["delivery_upper_bound"]
    vehicle_capacity_by_vehicle = data["vehicle_capacity_by_vehicle"]
    dispatch_cost_by_vehicle = data["fixed_dispatch_cost_by_vehicle"]
    n_customers = len(customers)

    x_idx = {}
    z_idx = {}
    q_idx = {}
    inv_idx = {}
    y_idx = {}
    u_idx = {}
    idx = 0
    for vehicle in vehicles:
        for period in periods:
            for i in nodes:
                for j in nodes:
                    if i == j:
                        continue
                    x_idx[(i, j, vehicle, period)] = idx
                    idx += 1
    for customer in customers:
        for vehicle in vehicles:
            for period in periods:
                z_idx[(customer, vehicle, period)] = idx
                idx += 1
    for customer in customers:
        for vehicle in vehicles:
            for period in periods:
                q_idx[(customer, vehicle, period)] = idx
                idx += 1
    for customer in customers:
        for period in periods:
            inv_idx[(customer, period)] = idx
            idx += 1
    for vehicle in vehicles:
        for period in periods:
            y_idx[(vehicle, period)] = idx
            idx += 1
    for customer in customers:
        for vehicle in vehicles:
            for period in periods:
                u_idx[(customer, vehicle, period)] = idx
                idx += 1

    n = idx
    c_vec = np.zeros(n, dtype=float)
    lb = np.zeros(n, dtype=float)
    ub = np.full(n, np.inf, dtype=float)
    integrality = np.zeros(n, dtype=int)

    for (i, j, vehicle, period), var_idx in x_idx.items():
        c_vec[var_idx] = float(distance[i][j])
        ub[var_idx] = 1.0
        integrality[var_idx] = 1
    for key, var_idx in z_idx.items():
        ub[var_idx] = 1.0
        integrality[var_idx] = 1
    for (customer, vehicle, period), var_idx in q_idx.items():
        ub[var_idx] = float(delivery_ub[customer][period])
    for (customer, period), var_idx in inv_idx.items():
        c_vec[var_idx] = float(holding_cost[customer])
        ub[var_idx] = float(inventory_capacity[customer])
    for (vehicle, period), var_idx in y_idx.items():
        c_vec[var_idx] = float(dispatch_cost_by_vehicle[vehicle])
        ub[var_idx] = 1.0
        integrality[var_idx] = 1
    for key, var_idx in u_idx.items():
        ub[var_idx] = float(n_customers)

    rows = []
    lower = []
    upper = []

    for customer in customers:
        for idx_t, period in enumerate(periods):
            row = np.zeros(n, dtype=float)
            for vehicle in vehicles:
                row[q_idx[(customer, vehicle, period)]] = 1.0
            row[inv_idx[(customer, period)]] = -1.0
            rhs = float(demands[customer][period])
            if idx_t == 0:
                rhs -= float(initial_inventory[customer])
            else:
                prev = periods[idx_t - 1]
                row[inv_idx[(customer, prev)]] = 1.0
            rows.append(row)
            lower.append(rhs)
            upper.append(rhs)

            row = np.zeros(n, dtype=float)
            row[inv_idx[(customer, period)]] = 1.0
            rows.append(row)
            lower.append(-np.inf)
            upper.append(float(inventory_capacity[customer]))

            row = np.zeros(n, dtype=float)
            for vehicle in vehicles:
                row[z_idx[(customer, vehicle, period)]] = 1.0
            rows.append(row)
            lower.append(-np.inf)
            upper.append(1.0)

            for vehicle in vehicles:
                row = np.zeros(n, dtype=float)
                row[q_idx[(customer, vehicle, period)]] = 1.0
                row[z_idx[(customer, vehicle, period)]] = -float(delivery_ub[customer][period])
                rows.append(row)
                lower.append(-np.inf)
                upper.append(0.0)

                row = np.zeros(n, dtype=float)
                row[z_idx[(customer, vehicle, period)]] = 1.0
                row[y_idx[(vehicle, period)]] = -1.0
                rows.append(row)
                lower.append(-np.inf)
                upper.append(0.0)

                row = np.zeros(n, dtype=float)
                row[z_idx[(customer, vehicle, period)]] = 1.0
                row[u_idx[(customer, vehicle, period)]] = -1.0
                rows.append(row)
                lower.append(-np.inf)
                upper.append(0.0)

                row = np.zeros(n, dtype=float)
                row[u_idx[(customer, vehicle, period)]] = 1.0
                row[z_idx[(customer, vehicle, period)]] = -float(n_customers)
                rows.append(row)
                lower.append(-np.inf)
                upper.append(0.0)

    for vehicle in vehicles:
        Q = float(vehicle_capacity_by_vehicle[vehicle])
        for period in periods:
            row = np.zeros(n, dtype=float)
            for customer in customers:
                row[q_idx[(customer, vehicle, period)]] = 1.0
            row[y_idx[(vehicle, period)]] = -Q
            rows.append(row)
            lower.append(-np.inf)
            upper.append(0.0)

            row = np.zeros(n, dtype=float)
            for customer in customers:
                row[x_idx[(DEPOT, customer, vehicle, period)]] = 1.0
            row[y_idx[(vehicle, period)]] = -1.0
            rows.append(row)
            lower.append(0.0)
            upper.append(0.0)

            row = np.zeros(n, dtype=float)
            for customer in customers:
                row[x_idx[(customer, DEPOT, vehicle, period)]] = 1.0
            row[y_idx[(vehicle, period)]] = -1.0
            rows.append(row)
            lower.append(0.0)
            upper.append(0.0)

            for customer in customers:
                row = np.zeros(n, dtype=float)
                for i in nodes:
                    if i == customer:
                        continue
                    row[x_idx[(i, customer, vehicle, period)]] = 1.0
                row[z_idx[(customer, vehicle, period)]] = -1.0
                rows.append(row)
                lower.append(0.0)
                upper.append(0.0)

                row = np.zeros(n, dtype=float)
                for j in nodes:
                    if j == customer:
                        continue
                    row[x_idx[(customer, j, vehicle, period)]] = 1.0
                row[z_idx[(customer, vehicle, period)]] = -1.0
                rows.append(row)
                lower.append(0.0)
                upper.append(0.0)

            for i in customers:
                for j in customers:
                    if i == j:
                        continue
                    row = np.zeros(n, dtype=float)
                    row[u_idx[(i, vehicle, period)]] = 1.0
                    row[u_idx[(j, vehicle, period)]] = -1.0
                    row[x_idx[(i, j, vehicle, period)]] = float(n_customers)
                    row[z_idx[(i, vehicle, period)]] = float(n_customers)
                    row[z_idx[(j, vehicle, period)]] = float(n_customers)
                    rows.append(row)
                    lower.append(-np.inf)
                    upper.append(float(3 * n_customers - 1))

    constraints = LinearConstraint(np.array(rows), np.array(lower), np.array(upper))
    bounds = Bounds(lb, ub)

    start = time.perf_counter()
    res = milp(c=c_vec, integrality=integrality, bounds=bounds, constraints=constraints)
    runtime = time.perf_counter() - start

    if res.status != 0 or res.x is None:
        return {
            "status": "infeasible_or_no_optimal_solution",
            "solver_status": int(res.status),
            "message": str(res.message),
            "runtime_seconds": runtime,
            "solve_method": "scipy_milp_irp_medium",
            "solver": infer_solver_label("scipy_milp_irp_medium"),
        }

    x_solution = {(i, j, vehicle, period): int(round(float(res.x[var_idx]))) for (i, j, vehicle, period), var_idx in x_idx.items()}
    z_solution = {(customer, vehicle, period): int(round(float(res.x[var_idx]))) for (customer, vehicle, period), var_idx in z_idx.items()}
    q_solution = {(customer, vehicle, period): clean_float(float(res.x[var_idx]), 6) for (customer, vehicle, period), var_idx in q_idx.items()}
    inventory_solution = {(customer, period): clean_float(float(res.x[var_idx]), 6) for (customer, period), var_idx in inv_idx.items()}
    y_solution = {(vehicle, period): int(round(float(res.x[var_idx]))) for (vehicle, period), var_idx in y_idx.items()}

    return package_solution(
        data,
        x_solution,
        z_solution,
        q_solution,
        inventory_solution,
        y_solution,
        runtime,
        float(res.fun),
        "scipy_milp_irp_medium",
    )


def solve_instance(base: Path) -> dict:
    data = load_instance(base)
    gurobi_solution = solve_with_gurobi(data)
    if gurobi_solution is not None:
        return gurobi_solution
    return solve_with_scipy(data)


def main() -> None:
    base = Path(__file__).resolve().parents[1]
    result = solve_instance(base)
    out_path = base / "ground_truth" / "solution_ref.json"
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
