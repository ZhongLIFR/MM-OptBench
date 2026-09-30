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
TIME_LIMIT_SECONDS = 180.0


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
    distance = data["distance_matrix"]
    demands = data["demands"]
    holding_cost = data["holding_cost"]
    fixed_dispatch_cost = float(data["fixed_dispatch_cost"])

    dispatch_by_period = {t: int(round(float(y_solution[t]))) for t in periods}
    route_arcs_by_period = {}
    route_by_period = {}
    visited_customers_by_period = {}
    route_cost_by_period = {}
    holding_cost_by_period = {}
    dispatch_cost_by_period = {}
    load_by_period = {}

    for t in periods:
        arcs = sorted(
            [(i, j) for (i, j, tt), value in x_solution.items() if tt == t and int(round(float(value))) == 1],
            key=lambda item: (item[0], item[1]),
        )
        route_by_period[t] = reconstruct_route(arcs, customers) if dispatch_by_period[t] == 1 else []
        route_arcs_by_period[t] = (
            [[route_by_period[t][idx], route_by_period[t][idx + 1]] for idx in range(len(route_by_period[t]) - 1)]
            if dispatch_by_period[t] == 1
            else []
        )
        visited = [node for node in route_by_period[t] if node != DEPOT]
        visited_customers_by_period[t] = visited
        route_cost_by_period[t] = clean_float(sum(float(distance[i][j]) for i, j in arcs), 4)
        load_by_period[t] = clean_float(sum(float(q_solution[(c, t)]) for c in customers), 4)
        holding_cost_by_period[t] = clean_float(
            sum(float(holding_cost[c]) * float(inventory_solution[(c, t)]) for c in customers),
            4,
        )
        dispatch_cost_by_period[t] = clean_float(fixed_dispatch_cost * dispatch_by_period[t], 4)

    deliveries = {
        c: {t: clean_float(float(q_solution[(c, t)]), 4) for t in periods}
        for c in customers
    }
    ending_inventory = {
        c: {t: clean_float(float(inventory_solution[(c, t)]), 4) for t in periods}
        for c in customers
    }
    visit_indicator = {
        c: {t: int(round(float(z_solution[(c, t)]))) for t in periods}
        for c in customers
    }
    realized_total_demand = {
        t: int(sum(int(demands[c][t]) for c in customers))
        for t in periods
    }

    total_routing_cost = clean_float(sum(route_cost_by_period[t] for t in periods), 4)
    total_holding_cost = clean_float(sum(holding_cost_by_period[t] for t in periods), 4)
    total_dispatch_cost = clean_float(sum(dispatch_cost_by_period[t] for t in periods), 4)

    return {
        "status": "optimal",
        "objective": normalize_number(objective_value, 4),
        "objective_exact": float(objective_value),
        "runtime_seconds": runtime,
        "dispatch_by_period": dispatch_by_period,
        "dispatch_periods": [t for t in periods if dispatch_by_period[t] == 1],
        "route_by_period": route_by_period,
        "route_arcs_by_period": route_arcs_by_period,
        "visited_customers_by_period": visited_customers_by_period,
        "visit_indicator": visit_indicator,
        "deliveries": deliveries,
        "ending_inventory": ending_inventory,
        "aggregate_demand_by_period": realized_total_demand,
        "load_by_period": load_by_period,
        "route_cost_by_period": route_cost_by_period,
        "holding_cost_by_period": holding_cost_by_period,
        "dispatch_cost_by_period": dispatch_cost_by_period,
        "total_routing_cost": total_routing_cost,
        "total_holding_cost": total_holding_cost,
        "total_dispatch_cost": total_dispatch_cost,
        "capacity_binding_periods": [
            t for t in periods
            if dispatch_by_period[t] == 1 and abs(load_by_period[t] - float(data["vehicle_capacity"])) <= 1e-6
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
    distance = data["distance_matrix"]
    demands = data["demands"]
    initial_inventory = data["initial_inventory"]
    inventory_capacity = data["inventory_capacity"]
    holding_cost = data["holding_cost"]
    delivery_ub = data["delivery_upper_bound"]
    vehicle_capacity = float(data["vehicle_capacity"])
    fixed_dispatch_cost = float(data["fixed_dispatch_cost"])
    n_customers = len(customers)

    start = time.perf_counter()
    try:
        model = gp.Model("irp_easy")
        model.Params.OutputFlag = 0
        model.Params.TimeLimit = TIME_LIMIT_SECONDS
        model.Params.MIPGap = 0.0

        x = {
            (i, j, t): model.addVar(vtype=GRB.BINARY, name=f"x_{i}_{j}_{t}")
            for t in periods
            for i in nodes
            for j in nodes
            if i != j
        }
        z = {(c, t): model.addVar(vtype=GRB.BINARY, name=f"z_{c}_{t}") for c in customers for t in periods}
        q = {(c, t): model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"q_{c}_{t}") for c in customers for t in periods}
        inv = {(c, t): model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"I_{c}_{t}") for c in customers for t in periods}
        y = {t: model.addVar(vtype=GRB.BINARY, name=f"y_{t}") for t in periods}
        u = {(c, t): model.addVar(lb=0.0, ub=float(n_customers), vtype=GRB.CONTINUOUS, name=f"u_{c}_{t}") for c in customers for t in periods}

        model.setObjective(
            gp.quicksum(float(distance[i][j]) * x[i, j, t] for t in periods for i in nodes for j in nodes if i != j)
            + gp.quicksum(float(holding_cost[c]) * inv[c, t] for c in customers for t in periods)
            + gp.quicksum(fixed_dispatch_cost * y[t] for t in periods),
            GRB.MINIMIZE,
        )

        for c in customers:
            for idx, t in enumerate(periods):
                if idx == 0:
                    model.addConstr(
                        float(initial_inventory[c]) + q[c, t] == float(demands[c][t]) + inv[c, t],
                        name=f"balance_{c}_{t}",
                    )
                else:
                    prev = periods[idx - 1]
                    model.addConstr(
                        inv[c, prev] + q[c, t] == float(demands[c][t]) + inv[c, t],
                        name=f"balance_{c}_{t}",
                    )
                model.addConstr(inv[c, t] <= float(inventory_capacity[c]), name=f"capacity_{c}_{t}")
                model.addConstr(q[c, t] <= float(delivery_ub[c][t]) * z[c, t], name=f"deliver_link_{c}_{t}")
                model.addConstr(z[c, t] <= y[t], name=f"visit_dispatch_{c}_{t}")
                model.addConstr(u[c, t] >= z[c, t], name=f"u_lb_{c}_{t}")
                model.addConstr(u[c, t] <= float(n_customers) * z[c, t], name=f"u_ub_{c}_{t}")

        for t in periods:
            model.addConstr(
                gp.quicksum(q[c, t] for c in customers) <= vehicle_capacity * y[t],
                name=f"truck_capacity_{t}",
            )
            model.addConstr(
                gp.quicksum(x[DEPOT, j, t] for j in customers) == y[t],
                name=f"depot_depart_{t}",
            )
            model.addConstr(
                gp.quicksum(x[i, DEPOT, t] for i in customers) == y[t],
                name=f"depot_return_{t}",
            )
            for c in customers:
                model.addConstr(
                    gp.quicksum(x[i, c, t] for i in nodes if i != c) == z[c, t],
                    name=f"in_degree_{c}_{t}",
                )
                model.addConstr(
                    gp.quicksum(x[c, j, t] for j in nodes if j != c) == z[c, t],
                    name=f"out_degree_{c}_{t}",
                )
            for i in customers:
                for j in customers:
                    if i == j:
                        continue
                    model.addConstr(
                        u[i, t] - u[j, t] + float(n_customers) * x[i, j, t]
                        <= float(n_customers - 1)
                        + float(n_customers) * (1.0 - z[i, t])
                        + float(n_customers) * (1.0 - z[j, t]),
                        name=f"mtz_{i}_{j}_{t}",
                    )

        model.optimize()
        runtime = time.perf_counter() - start
        if model.Status != GRB.OPTIMAL:
            return None

        x_solution = {(i, j, t): int(round(float(var.X))) for (i, j, t), var in x.items()}
        z_solution = {(c, t): int(round(float(var.X))) for (c, t), var in z.items()}
        q_solution = {(c, t): clean_float(float(var.X), 6) for (c, t), var in q.items()}
        inventory_solution = {(c, t): clean_float(float(var.X), 6) for (c, t), var in inv.items()}
        y_solution = {t: int(round(float(var.X))) for t, var in y.items()}
        return package_solution(
            data,
            x_solution,
            z_solution,
            q_solution,
            inventory_solution,
            y_solution,
            runtime,
            float(model.ObjVal),
            "gurobi_milp_irp_easy",
        )
    except Exception:
        return None


def solve_with_scipy(data: dict) -> dict:
    periods = data["sets"]["periods"]
    customers = data["sets"]["customers"]
    nodes = data["sets"]["nodes"]
    distance = data["distance_matrix"]
    demands = data["demands"]
    initial_inventory = data["initial_inventory"]
    inventory_capacity = data["inventory_capacity"]
    holding_cost = data["holding_cost"]
    delivery_ub = data["delivery_upper_bound"]
    vehicle_capacity = float(data["vehicle_capacity"])
    fixed_dispatch_cost = float(data["fixed_dispatch_cost"])
    n_customers = len(customers)

    x_idx = {}
    z_idx = {}
    q_idx = {}
    inv_idx = {}
    y_idx = {}
    u_idx = {}
    idx = 0
    for t in periods:
        for i in nodes:
            for j in nodes:
                if i == j:
                    continue
                x_idx[(i, j, t)] = idx
                idx += 1
    for c in customers:
        for t in periods:
            z_idx[(c, t)] = idx
            idx += 1
    for c in customers:
        for t in periods:
            q_idx[(c, t)] = idx
            idx += 1
    for c in customers:
        for t in periods:
            inv_idx[(c, t)] = idx
            idx += 1
    for t in periods:
        y_idx[t] = idx
        idx += 1
    for c in customers:
        for t in periods:
            u_idx[(c, t)] = idx
            idx += 1

    n = idx
    c_vec = np.zeros(n, dtype=float)
    lb = np.zeros(n, dtype=float)
    ub = np.full(n, np.inf, dtype=float)
    integrality = np.zeros(n, dtype=int)

    for key, var_idx in x_idx.items():
        i, j, _ = key
        c_vec[var_idx] = float(distance[i][j])
        ub[var_idx] = 1.0
        integrality[var_idx] = 1
    for key, var_idx in z_idx.items():
        c_vec[var_idx] = 0.0
        ub[var_idx] = 1.0
        integrality[var_idx] = 1
    for (c_name, t), var_idx in q_idx.items():
        ub[var_idx] = float(delivery_ub[c_name][t])
    for (c_name, _), var_idx in inv_idx.items():
        c_vec[var_idx] = float(holding_cost[c_name])
        ub[var_idx] = float(inventory_capacity[c_name])
    for t, var_idx in y_idx.items():
        c_vec[var_idx] = fixed_dispatch_cost
        ub[var_idx] = 1.0
        integrality[var_idx] = 1
    for _, var_idx in u_idx.items():
        ub[var_idx] = float(n_customers)

    rows = []
    lower = []
    upper = []

    for c_name in customers:
        for idx_t, t in enumerate(periods):
            row = np.zeros(n, dtype=float)
            row[q_idx[(c_name, t)]] = 1.0
            row[inv_idx[(c_name, t)]] = -1.0
            rhs = float(demands[c_name][t])
            if idx_t == 0:
                rhs -= float(initial_inventory[c_name])
            else:
                prev = periods[idx_t - 1]
                row[inv_idx[(c_name, prev)]] = 1.0
            rows.append(row)
            lower.append(rhs)
            upper.append(rhs)

            row = np.zeros(n, dtype=float)
            row[inv_idx[(c_name, t)]] = 1.0
            rows.append(row)
            lower.append(-np.inf)
            upper.append(float(inventory_capacity[c_name]))

            row = np.zeros(n, dtype=float)
            row[q_idx[(c_name, t)]] = 1.0
            row[z_idx[(c_name, t)]] = -float(delivery_ub[c_name][t])
            rows.append(row)
            lower.append(-np.inf)
            upper.append(0.0)

            row = np.zeros(n, dtype=float)
            row[z_idx[(c_name, t)]] = 1.0
            row[y_idx[t]] = -1.0
            rows.append(row)
            lower.append(-np.inf)
            upper.append(0.0)

            row = np.zeros(n, dtype=float)
            row[z_idx[(c_name, t)]] = 1.0
            row[u_idx[(c_name, t)]] = -1.0
            rows.append(row)
            lower.append(-np.inf)
            upper.append(0.0)

            row = np.zeros(n, dtype=float)
            row[u_idx[(c_name, t)]] = 1.0
            row[z_idx[(c_name, t)]] = -float(n_customers)
            rows.append(row)
            lower.append(-np.inf)
            upper.append(0.0)

    for t in periods:
        row = np.zeros(n, dtype=float)
        for c_name in customers:
            row[q_idx[(c_name, t)]] = 1.0
        row[y_idx[t]] = -vehicle_capacity
        rows.append(row)
        lower.append(-np.inf)
        upper.append(0.0)

        row = np.zeros(n, dtype=float)
        for j in customers:
            row[x_idx[(DEPOT, j, t)]] = 1.0
        row[y_idx[t]] = -1.0
        rows.append(row)
        lower.append(0.0)
        upper.append(0.0)

        row = np.zeros(n, dtype=float)
        for i in customers:
            row[x_idx[(i, DEPOT, t)]] = 1.0
        row[y_idx[t]] = -1.0
        rows.append(row)
        lower.append(0.0)
        upper.append(0.0)

        for c_name in customers:
            row = np.zeros(n, dtype=float)
            for i in nodes:
                if i == c_name:
                    continue
                row[x_idx[(i, c_name, t)]] = 1.0
            row[z_idx[(c_name, t)]] = -1.0
            rows.append(row)
            lower.append(0.0)
            upper.append(0.0)

            row = np.zeros(n, dtype=float)
            for j in nodes:
                if j == c_name:
                    continue
                row[x_idx[(c_name, j, t)]] = 1.0
            row[z_idx[(c_name, t)]] = -1.0
            rows.append(row)
            lower.append(0.0)
            upper.append(0.0)

        for i in customers:
            for j in customers:
                if i == j:
                    continue
                row = np.zeros(n, dtype=float)
                row[u_idx[(i, t)]] = 1.0
                row[u_idx[(j, t)]] = -1.0
                row[x_idx[(i, j, t)]] = float(n_customers)
                row[z_idx[(i, t)]] = float(n_customers)
                row[z_idx[(j, t)]] = float(n_customers)
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
            "solve_method": "scipy_milp_irp_easy",
            "solver": infer_solver_label("scipy_milp_irp_easy"),
        }

    x_solution = {(i, j, t): int(round(float(res.x[var_idx]))) for (i, j, t), var_idx in x_idx.items()}
    z_solution = {(c_name, t): int(round(float(res.x[var_idx]))) for (c_name, t), var_idx in z_idx.items()}
    q_solution = {(c_name, t): clean_float(float(res.x[var_idx]), 6) for (c_name, t), var_idx in q_idx.items()}
    inventory_solution = {(c_name, t): clean_float(float(res.x[var_idx]), 6) for (c_name, t), var_idx in inv_idx.items()}
    y_solution = {t: int(round(float(res.x[var_idx]))) for t, var_idx in y_idx.items()}

    return package_solution(
        data,
        x_solution,
        z_solution,
        q_solution,
        inventory_solution,
        y_solution,
        runtime,
        float(res.fun),
        "scipy_milp_irp_easy",
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
