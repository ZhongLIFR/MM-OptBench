#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE_PATH = os.path.join(HERE, "instance_data.json")
SOLUTION_PATH = os.path.join(HERE, "solution_ref.json")


def normalize_number(value: float):
    rounded = round(float(value))
    if abs(float(value) - rounded) <= 1e-8:
        return int(rounded)
    return float(round(float(value), 8))


with open(INSTANCE_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

nodes = [str(x) for x in data["sets"]["nodes"]]
periods = [str(t) for t in data["sets"]["periods"]]
storage_nodes = [str(x) for x in data["sets"]["storage_nodes"]]
arcs = data["arcs"]
arc_ids = [str(arc["id"]) for arc in arcs]
arc_tail = {str(arc["id"]): str(arc["from"]) for arc in arcs}
arc_head = {str(arc["id"]): str(arc["to"]) for arc in arcs}
cap = {
    (str(arc["id"]), str(t)): float(arc["capacity_by_period"][str(t)])
    for arc in arcs
    for t in periods
}
cost = {
    (str(arc["id"]), str(t)): float(arc["cost_by_period"][str(t)])
    for arc in arcs
    for t in periods
}
balance = {
    (str(node), str(t)): float(data["net_supply_by_node_period"][str(node)][str(t)])
    for node in nodes
    for t in periods
}
storage_capacity = {
    str(node): float(data["storage"][str(node)]["capacity"])
    for node in storage_nodes
}
holding_cost = {
    (str(node), str(t)): float(data["storage"][str(node)]["holding_cost_by_period"][str(t)])
    for node in storage_nodes
    for t in periods
}
initial_inventory = {
    str(node): float(data["storage"][str(node)]["initial_inventory"])
    for node in storage_nodes
}


def package_solution(
    objective_value: float,
    runtime_seconds: float,
    solve_method: str,
    solver_name: str,
    verification_method: str,
    fallback_used: bool,
    flows: dict[tuple[str, str], float],
    inventory: dict[tuple[str, str], float],
) -> dict[str, object]:
    routing_cost_total = sum(cost[(arc_id, t)] * flows[(arc_id, t)] for arc_id in arc_ids for t in periods)
    holding_cost_total = sum(
        holding_cost[(node, t)] * inventory[(node, t)]
        for node in storage_nodes
        for t in periods
    )

    flows_by_period = {
        t: {arc_id: normalize_number(flows[(arc_id, t)]) for arc_id in arc_ids}
        for t in periods
    }
    inventory_by_node = {
        node: {t: normalize_number(inventory[(node, t)]) for t in periods}
        for node in storage_nodes
    }
    nonzero_arc_periods = [
        f"{arc_id}@{t}"
        for t in periods
        for arc_id in arc_ids
        if flows[(arc_id, t)] > 1e-8
    ]
    binding_arc_periods = [
        f"{arc_id}@{t}"
        for t in periods
        for arc_id in arc_ids
        if abs(flows[(arc_id, t)] - cap[(arc_id, t)]) <= 1e-8 and cap[(arc_id, t)] > 0
    ]
    positive_inventory_periods = {
        node: [t for t in periods if inventory[(node, t)] > 1e-8]
        for node in storage_nodes
    }
    storage_binding_periods = {
        node: [t for t in periods if abs(inventory[(node, t)] - storage_capacity[node]) <= 1e-8]
        for node in storage_nodes
    }

    return {
        "status": "optimal",
        "objective_value": normalize_number(objective_value),
        "objective_exact": float(round(float(objective_value), 8)),
        "routing_cost_total": normalize_number(routing_cost_total),
        "holding_cost_total": normalize_number(holding_cost_total),
        "flows_by_period": flows_by_period,
        "inventory_by_node": inventory_by_node,
        "nonzero_arc_periods": nonzero_arc_periods,
        "binding_arc_periods": binding_arc_periods,
        "positive_inventory_periods": positive_inventory_periods,
        "storage_binding_periods": storage_binding_periods,
        "runtime_seconds": float(round(float(runtime_seconds), 8)),
        "solve_method": solve_method,
        "solver_used": solver_name,
        "solver": solver_name,
        "solver_policy": "gurobi_first_then_scipy_highs_exact_lp",
        "verification_method": verification_method,
        "fallback_used": bool(fallback_used),
    }


def solve_with_gurobi() -> dict[str, object] | None:
    try:
        import gurobipy as gp
        from gurobipy import GRB
    except Exception:
        return None

    start = time.perf_counter()
    try:
        model = gp.Model(str(data.get("instance_id", "tempnf_hard")))
        model.Params.OutputFlag = 0
        model.Params.TimeLimit = 60.0
        model.Params.MIPGap = 0.0

        x = {
            (arc_id, t): model.addVar(
                lb=0.0,
                ub=cap[(arc_id, t)],
                vtype=GRB.CONTINUOUS,
                name=f"x_{arc_id}_{t}",
            )
            for arc_id in arc_ids
            for t in periods
        }
        inv = {
            (node, t): model.addVar(
                lb=0.0,
                ub=storage_capacity[node],
                vtype=GRB.CONTINUOUS,
                name=f"I_{node}_{t}",
            )
            for node in storage_nodes
            for t in periods
        }

        model.setObjective(
            gp.quicksum(cost[(arc_id, t)] * x[(arc_id, t)] for arc_id in arc_ids for t in periods)
            + gp.quicksum(holding_cost[(node, t)] * inv[(node, t)] for node in storage_nodes for t in periods),
            GRB.MINIMIZE,
        )

        for t_idx, t in enumerate(periods):
            prev_t = periods[t_idx - 1] if t_idx > 0 else None
            for node in nodes:
                outflow = gp.quicksum(x[(arc_id, t)] for arc_id in arc_ids if arc_tail[arc_id] == node)
                inflow = gp.quicksum(x[(arc_id, t)] for arc_id in arc_ids if arc_head[arc_id] == node)
                if node in storage_nodes:
                    lhs = outflow - inflow + inv[(node, t)]
                    rhs = balance[(node, t)]
                    if prev_t is not None:
                        lhs -= inv[(node, prev_t)]
                    else:
                        rhs += initial_inventory[node]
                    model.addConstr(lhs == rhs, name=f"balance_{node}_{t}")
                else:
                    model.addConstr(outflow - inflow == balance[(node, t)], name=f"balance_{node}_{t}")

        model.optimize()
        runtime_seconds = time.perf_counter() - start
        if model.Status != GRB.OPTIMAL:
            return None

        flows = {(arc_id, t): float(x[(arc_id, t)].X) for arc_id in arc_ids for t in periods}
        inventory = {(node, t): float(inv[(node, t)].X) for node in storage_nodes for t in periods}
        return package_solution(
            float(model.ObjVal),
            runtime_seconds,
            "gurobi_lp_multi_period_network_flow",
            "Gurobi",
            "direct_gurobi_optimal_lp_solution",
            False,
            flows,
            inventory,
        )
    except Exception:
        return None


def solve_with_scipy() -> dict[str, object]:
    import numpy as np
    from scipy.optimize import linprog

    x_keys = [(arc_id, t) for arc_id in arc_ids for t in periods]
    inv_keys = [(node, t) for node in storage_nodes for t in periods]
    all_keys = x_keys + inv_keys
    idx = {key: pos for pos, key in enumerate(all_keys)}

    c = np.zeros(len(all_keys), dtype=float)
    bounds = []
    for key in x_keys:
        c[idx[key]] = cost[key]
        bounds.append((0.0, cap[key]))
    for key in inv_keys:
        c[idx[key]] = holding_cost[key]
        bounds.append((0.0, storage_capacity[key[0]]))

    A_eq = []
    b_eq = []
    for t_idx, t in enumerate(periods):
        prev_t = periods[t_idx - 1] if t_idx > 0 else None
        for node in nodes:
            row = np.zeros(len(all_keys), dtype=float)
            for arc_id in arc_ids:
                if arc_tail[arc_id] == node:
                    row[idx[(arc_id, t)]] += 1.0
                if arc_head[arc_id] == node:
                    row[idx[(arc_id, t)]] -= 1.0
            rhs = balance[(node, t)]
            if node in storage_nodes:
                row[idx[(node, t)]] += 1.0
                if prev_t is not None:
                    row[idx[(node, prev_t)]] -= 1.0
                else:
                    rhs += initial_inventory[node]
            A_eq.append(row)
            b_eq.append(rhs)

    start = time.perf_counter()
    result = linprog(
        c=c,
        A_eq=np.array(A_eq, dtype=float),
        b_eq=np.array(b_eq, dtype=float),
        bounds=bounds,
        method="highs",
    )
    runtime_seconds = time.perf_counter() - start
    if not result.success:
        raise RuntimeError(f"SciPy linprog failed: {result.message}")

    flows = {(arc_id, t): float(result.x[idx[(arc_id, t)]]) for arc_id in arc_ids for t in periods}
    inventory = {(node, t): float(result.x[idx[(node, t)]]) for node in storage_nodes for t in periods}
    return package_solution(
        float(result.fun),
        runtime_seconds,
        "scipy_highs_exact_lp_multi_period_network_flow",
        "SciPy",
        "scipy_highs_optimal_lp_solution",
        True,
        flows,
        inventory,
    )


def main() -> None:
    solution = solve_with_gurobi()
    if solution is None:
        solution = solve_with_scipy()
    with open(SOLUTION_PATH, "w", encoding="utf-8") as f:
        json.dump(solution, f, indent=2)
        f.write("\n")


if __name__ == "__main__":
    main()
