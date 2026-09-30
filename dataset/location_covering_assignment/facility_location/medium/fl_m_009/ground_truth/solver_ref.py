#!/usr/bin/env python3
import itertools
import json
import os

SOLVER_POLICY = "prefer_gurobi_else_exact_fallback"

def ordered_assignments(data, assignments):
    return {c: assignments[c] for c in data["sets"]["C"]}

def build_result(data, open_set, assignments, solver_used, optimality_proof):
    assignments = ordered_assignments(data, assignments)
    opening_cost = sum(data["facility"][f]["open_cost"] for f in open_set)
    assignment_cost = 0.0
    for c, f in assignments.items():
        assignment_cost += data["assignment_cost_per_unit_demand"][c][f] * data["customer"][c]["demand"]
    objective = opening_cost + assignment_cost
    return {
        "objective_exact": round(objective, 6),
        "objective_value": round(objective, 6),
        "opening_cost": round(opening_cost, 6),
        "assignment_cost": round(assignment_cost, 6),
        "open_facilities": sorted(open_set),
        "assignments": assignments,
        "solver_policy": SOLVER_POLICY,
        "solver_used": solver_used,
        "optimality_proof": optimality_proof,
    }

def solve_with_gurobi(data):
    try:
        import gurobipy as gp
        from gurobipy import GRB
    except Exception:
        return None

    variant = data["variant_type"].upper()
    F = data["sets"]["F"]
    C = data["sets"]["C"]
    feasible = data["feasible_assignments"]

    model = gp.Model("facility_location_reference")
    model.Params.OutputFlag = 0

    y = model.addVars(F, vtype=GRB.BINARY, name="y")
    x = {(c, f): model.addVar(vtype=GRB.BINARY, name=f"x[{c},{f}]") for c in C for f in feasible[c]}

    model.setObjective(
        gp.quicksum(data["facility"][f]["open_cost"] * y[f] for f in F)
        + gp.quicksum(
            data["customer"][c]["demand"] * data["assignment_cost_per_unit_demand"][c][f] * x[c, f]
            for c in C for f in feasible[c]
        ),
        GRB.MINIMIZE,
    )

    for c in C:
        model.addConstr(gp.quicksum(x[c, f] for f in feasible[c]) == 1, name=f"assign[{c}]")

    for c in C:
        for f in feasible[c]:
            model.addConstr(x[c, f] <= y[f], name=f"open_link[{c},{f}]")

    if variant == "CFL":
        for f in F:
            model.addConstr(
                gp.quicksum(data["customer"][c]["demand"] * x[c, f] for c in C if f in feasible[c])
                <= data["facility"][f]["capacity"] * y[f],
                name=f"capacity[{f}]",
            )

    try:
        model.optimize()
    except Exception:
        return None

    if model.Status != GRB.OPTIMAL:
        return None

    assignments = {}
    for c in C:
        for f in feasible[c]:
            if x[c, f].X > 0.5:
                assignments[c] = f
                break

    open_set = {f for f in F if y[f].X > 0.5}
    return build_result(data, open_set, assignments, "gurobi", "gurobi_mip_optimal")

def evaluate_ufl(data, open_set):
    assignments = {}
    for c in data["sets"]["C"]:
        options = [f for f in data["feasible_assignments"][c] if f in open_set]
        if not options:
            return None
        assignments[c] = min(
            options,
            key=lambda f: data["assignment_cost_per_unit_demand"][c][f] * data["customer"][c]["demand"],
        )
    return build_result(data, open_set, assignments, "exact_enumeration", "exact_subset_enumeration")

def evaluate_cfl(data, open_set):
    choices = []
    for c in data["sets"]["C"]:
        options = [f for f in data["feasible_assignments"][c] if f in open_set]
        if not options:
            return None
        choices.append(options)

    best = None
    for combo in itertools.product(*choices):
        remaining = {f: data["facility"][f]["capacity"] for f in open_set}
        assignments = {}
        feasible_combo = True

        for idx, c in enumerate(data["sets"]["C"]):
            f = combo[idx]
            demand = data["customer"][c]["demand"]
            if remaining[f] < demand:
                feasible_combo = False
                break
            remaining[f] -= demand
            assignments[c] = f

        if feasible_combo:
            candidate = build_result(data, open_set, assignments, "exact_enumeration", "exact_subset_enumeration")
            if best is None or candidate["objective_exact"] < best["objective_exact"]:
                best = candidate

    return best

def solve_exact(data):
    variant = data["variant_type"].upper()
    F = data["sets"]["F"]
    best = None
    for r in range(1, len(F) + 1):
        for open_tuple in itertools.combinations(F, r):
            open_set = set(open_tuple)
            candidate = evaluate_ufl(data, open_set) if variant == "UFL" else evaluate_cfl(data, open_set)
            if candidate is not None and (best is None or candidate["objective_exact"] < best["objective_exact"]):
                best = candidate
    return best

def main():
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "instance_data.json"), "r", encoding="utf-8") as f:
        data = json.load(f)

    result = solve_with_gurobi(data)
    if result is None:
        result = solve_exact(data)

    output = (
        {"status": "optimal", **result}
        if result is not None
        else {"status": "infeasible", "solver_policy": SOLVER_POLICY, "solver_used": "none"}
    )
    with open(os.path.join(here, "solution_ref.json"), "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

if __name__ == "__main__":
    main()
