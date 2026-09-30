#!/usr/bin/env python3
import json
from pathlib import Path

SOLVER_POLICY = "prefer_gurobi_else_exact_fallback"
BIG = 10 ** 7


def ordered_assignments(drivers, assignments):
    return {d: assignments[d] for d in drivers if d in assignments}


def build_solution(drivers, objective, assignments, solver_used, optimality_proof):
    objective = round(float(objective), 6)
    return {
        "status": "optimal",
        "objective_exact": objective,
        "objective_value": objective,
        "assignments": ordered_assignments(drivers, assignments),
        "solver_policy": SOLVER_POLICY,
        "solver_used": solver_used,
        "optimality_proof": optimality_proof,
    }


def solve_with_linear_sum_assignment(instance_data):
    import numpy as np
    from scipy.optimize import linear_sum_assignment

    drivers = instance_data["sets"]["drivers"]
    routes = instance_data["sets"]["routes"]
    cost = instance_data["cost_matrix"]
    feasible = instance_data["feasible_assignments"]

    if instance_data["variant_type"] == "assignment":
        matrix = np.full((len(drivers), len(routes)), BIG, dtype=float)
        for i, d in enumerate(drivers):
            for j, r in enumerate(routes):
                if r in feasible[d]:
                    matrix[i, j] = cost[d][r]
        row_ind, col_ind = linear_sum_assignment(matrix)
        if np.any(matrix[row_ind, col_ind] >= BIG):
            raise RuntimeError("No feasible balanced assignment found.")
        assignments = {drivers[i]: routes[j] for i, j in zip(row_ind, col_ind)}
        objective = float(matrix[row_ind, col_ind].sum())
    else:
        required_side = instance_data["matching_requirement"]["required_side"]
        if required_side == "drivers":
            matrix = np.full((len(drivers), len(routes)), BIG, dtype=float)
            for i, d in enumerate(drivers):
                for j, r in enumerate(routes):
                    if r in feasible[d]:
                        matrix[i, j] = cost[d][r]
            row_ind, col_ind = linear_sum_assignment(matrix)
            if len(row_ind) != len(drivers) or np.any(matrix[row_ind, col_ind] >= BIG):
                raise RuntimeError("No feasible driver-covering matching found.")
            assignments = {drivers[i]: routes[j] for i, j in zip(row_ind, col_ind)}
            objective = float(matrix[row_ind, col_ind].sum())
        else:
            matrix = np.full((len(routes), len(drivers)), BIG, dtype=float)
            for j, r in enumerate(routes):
                for i, d in enumerate(drivers):
                    if r in feasible[d]:
                        matrix[j, i] = cost[d][r]
            row_ind, col_ind = linear_sum_assignment(matrix)
            if len(row_ind) != len(routes) or np.any(matrix[row_ind, col_ind] >= BIG):
                raise RuntimeError("No feasible route-covering matching found.")
            assignments = {drivers[i]: routes[j] for j, i in zip(row_ind, col_ind)}
            objective = float(matrix[row_ind, col_ind].sum())

    return build_solution(
        drivers,
        objective,
        assignments,
        solver_used="linear_sum_assignment",
        optimality_proof="exact_rectangular_linear_sum_assignment",
    )


def solve_with_gurobi(instance_data):
    import gurobipy as gp
    from gurobipy import GRB

    drivers = instance_data["sets"]["drivers"]
    routes = instance_data["sets"]["routes"]
    cost = instance_data["cost_matrix"]
    feasible = instance_data["feasible_assignments"]
    variant_type = instance_data["variant_type"]
    matching_requirement = instance_data.get("matching_requirement", {})

    model = gp.Model("bipartite_assignment_matching")
    x = {}
    for d in drivers:
        for r in feasible[d]:
            x[d, r] = model.addVar(vtype=GRB.BINARY, name=f"x_{d}_{r}")

    model.setObjective(gp.quicksum(cost[d][r] * x[d, r] for (d, r) in x), GRB.MINIMIZE)

    if variant_type == "assignment":
        for d in drivers:
            model.addConstr(gp.quicksum(x[d, r] for r in feasible[d]) == 1, name=f"driver_{d}")
        for r in routes:
            model.addConstr(gp.quicksum(x[d, r] for d in drivers if (d, r) in x) == 1, name=f"route_{r}")
    elif matching_requirement["required_side"] == "drivers":
        for d in drivers:
            model.addConstr(gp.quicksum(x[d, r] for r in feasible[d]) == 1, name=f"driver_{d}")
        for r in routes:
            model.addConstr(gp.quicksum(x[d, r] for d in drivers if (d, r) in x) <= 1, name=f"route_{r}")
    else:
        for r in routes:
            model.addConstr(gp.quicksum(x[d, r] for d in drivers if (d, r) in x) == 1, name=f"route_{r}")
        for d in drivers:
            model.addConstr(gp.quicksum(x[d, r] for r in feasible[d]) <= 1, name=f"driver_{d}")

    model.Params.OutputFlag = 0
    model.optimize()
    if model.Status != GRB.OPTIMAL:
        raise RuntimeError(f"Gurobi did not return an optimal solution. Status={model.Status}")

    assignments = {}
    for d in drivers:
        for r in feasible[d]:
            if x[d, r].X > 0.5:
                assignments[d] = r
                break

    return build_solution(
        drivers,
        model.ObjVal,
        assignments,
        solver_used="gurobi",
        optimality_proof="gurobi_optimal_status",
    )


def main():
    base = Path(__file__).resolve().parent
    instance_data = json.loads((base / "instance_data.json").read_text(encoding="utf-8"))
    try:
        solution = solve_with_gurobi(instance_data)
    except Exception:
        solution = solve_with_linear_sum_assignment(instance_data)
    (base / "solution_ref.json").write_text(json.dumps(solution, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
