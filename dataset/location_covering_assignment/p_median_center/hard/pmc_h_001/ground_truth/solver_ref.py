#!/usr/bin/env python3
import itertools
import json
import time
from pathlib import Path

SOLVER_POLICY = "prefer_gurobi_else_exact_fallback"


def load_data():
    base = Path(__file__).resolve().parent
    return json.loads((base / "instance_data.json").read_text(encoding="utf-8"))


def assignment_payload(data, assignments):
    payload = {}
    variant = data["variant_type"]
    for demand in data["sets"]["I"]:
        site = assignments[demand]
        distance = round(float(data["distance_matrix"][demand][site]), 2)
        entry = {
            "assigned_site": site,
            "distance": distance,
        }
        if variant == "p_median":
            weight = int(data["demand_weights"][demand])
            entry["weight"] = weight
            entry["weighted_distance"] = round(weight * distance, 2)
        payload[demand] = entry
    return payload


def build_solution(data, objective, open_sites, assignments, solver_used, solve_method, optimality_proof, runtime_seconds):
    objective = round(float(objective), 6)
    payload = assignment_payload(data, assignments)
    solution = {
        "instance_id": data["instance_id"],
        "status": "optimal",
        "objective_exact": objective,
        "objective_value": objective,
        "solver_policy": SOLVER_POLICY,
        "solver_used": solver_used,
        "solve_method": solve_method,
        "optimality_proof": optimality_proof,
        "runtime_seconds": round(float(runtime_seconds), 6),
        "open_sites": sorted(open_sites),
        "assignments": payload,
    }
    if data["variant_type"] == "p_median":
        total = round(sum(entry["weighted_distance"] for entry in payload.values()), 2)
        solution["total_weighted_assignment_distance"] = total
    else:
        max_dist = round(max(entry["distance"] for entry in payload.values()), 2)
        solution["max_assignment_distance"] = max_dist
    return solution


def evaluate_subset(data, open_sites):
    variant = data["variant_type"]
    assignments = {}
    if variant == "p_median":
        objective = 0.0
        for demand in data["sets"]["I"]:
            site = min(open_sites, key=lambda candidate: (float(data["distance_matrix"][demand][candidate]), candidate))
            distance = float(data["distance_matrix"][demand][site])
            assignments[demand] = site
            objective += int(data["demand_weights"][demand]) * distance
        return round(objective, 6), assignments
    demand_distances = []
    for demand in data["sets"]["I"]:
        site = min(open_sites, key=lambda candidate: (float(data["distance_matrix"][demand][candidate]), candidate))
        distance = float(data["distance_matrix"][demand][site])
        assignments[demand] = site
        demand_distances.append(distance)
    return round(max(demand_distances), 6), assignments


def solve_exact(data):
    candidates = data["sets"]["J"]
    p_value = int(data["p_value"])
    best = None
    for open_sites in itertools.combinations(candidates, p_value):
        objective, assignments = evaluate_subset(data, open_sites)
        candidate = (objective, tuple(open_sites), assignments)
        if best is None or candidate[:2] < best[:2]:
            best = candidate
    return best[0], list(best[1]), best[2]


def solve_with_gurobi(data):
    import gurobipy as gp
    from gurobipy import GRB

    demands = data["sets"]["I"]
    candidates = data["sets"]["J"]
    p_value = int(data["p_value"])
    distances = data["distance_matrix"]

    model = gp.Model("pmc_reference")
    model.Params.OutputFlag = 0

    y = model.addVars(candidates, vtype=GRB.BINARY, name="y")
    x = model.addVars(demands, candidates, vtype=GRB.BINARY, name="x")

    if data["variant_type"] == "p_median":
        weights = data["demand_weights"]
        model.setObjective(
            gp.quicksum(
                float(weights[demand]) * float(distances[demand][site]) * x[demand, site]
                for demand in demands
                for site in candidates
            ),
            GRB.MINIMIZE,
        )
    else:
        R = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="R")
        model.setObjective(R, GRB.MINIMIZE)

    for demand in demands:
        model.addConstr(gp.quicksum(x[demand, site] for site in candidates) == 1, name=f"assign_{demand}")

    model.addConstr(gp.quicksum(y[site] for site in candidates) == p_value, name="select_p")

    for demand in demands:
        for site in candidates:
            model.addConstr(x[demand, site] <= y[site], name=f"link_{demand}_{site}")

    if data["variant_type"] == "p_center":
        for demand in demands:
            model.addConstr(
                gp.quicksum(float(distances[demand][site]) * x[demand, site] for site in candidates) <= R,
                name=f"radius_{demand}",
            )

    model.optimize()
    if model.Status != GRB.OPTIMAL:
        raise RuntimeError(f"Gurobi did not reach optimality. Status={model.Status}")

    assignments = {}
    for demand in demands:
        chosen = max(candidates, key=lambda site: x[demand, site].X)
        assignments[demand] = chosen
    open_sites = [site for site in candidates if y[site].X > 0.5]
    return float(model.ObjVal), open_sites, assignments


def main():
    data = load_data()
    output_path = Path(__file__).resolve().parent / "solution_ref.json"
    start = time.perf_counter()
    try:
        objective, open_sites, assignments = solve_with_gurobi(data)
        runtime = time.perf_counter() - start
        solution = build_solution(
            data,
            objective,
            open_sites,
            assignments,
            solver_used="gurobi",
            solve_method="gurobi_mip",
            optimality_proof="gurobi_mip_optimal_status",
            runtime_seconds=runtime,
        )
    except Exception:
        objective, open_sites, assignments = solve_exact(data)
        runtime = time.perf_counter() - start
        solution = build_solution(
            data,
            objective,
            open_sites,
            assignments,
            solver_used="exact_enumeration",
            solve_method="subset_enumeration",
            optimality_proof="complete_enumeration_of_all_p_site_subsets",
            runtime_seconds=runtime,
        )

    output_path.write_text(json.dumps(solution, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
