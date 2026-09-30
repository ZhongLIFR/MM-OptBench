#!/usr/bin/env python3
import json
import time
from pathlib import Path

SOLVER_POLICY = "prefer_gurobi_else_exact_fallback"


def load_data():
    base = Path(__file__).resolve().parent
    return json.loads((base / "instance_data.json").read_text(encoding="utf-8"))


def ordered_selection(data, selected_subsets):
    selected_lookup = set(selected_subsets)
    return [subset_id for subset_id in data["sets"]["S"] if subset_id in selected_lookup]


def coverage_counts(data, selected_subsets):
    counts = {element: 0 for element in data["sets"]["E"]}
    for subset_id in selected_subsets:
        for element in data["candidate_subsets"][subset_id]["covered_elements"]:
            counts[element] += 1
    return counts


def selection_objective(data, selected_subsets):
    return float(sum(int(data["subset_costs"][subset_id]) for subset_id in selected_subsets))


def is_feasible(data, counts):
    if data["variant_type"] == "set_covering":
        return all(value >= 1 for value in counts.values())
    return all(value == 1 for value in counts.values())


def build_solution(data, objective, selected_subsets, counts, solver_used, solve_method, optimality_proof, runtime_seconds):
    selected = ordered_selection(data, selected_subsets)
    objective = round(float(objective), 6)
    binding_elements = [element for element, value in counts.items() if value == 1]
    redundant_elements = [element for element, value in counts.items() if value > 1]
    return {
        "instance_id": data["instance_id"],
        "status": "optimal",
        "is_feasible": True,
        "objective_exact": objective,
        "objective_value": objective,
        "solver_policy": SOLVER_POLICY,
        "solver_used": solver_used,
        "solve_method": solve_method,
        "optimality_proof": optimality_proof,
        "runtime_seconds": round(float(runtime_seconds), 6),
        "selected_subsets": selected,
        "selected_subset_count": len(selected),
        "coverage_count_by_element": counts,
        "constraint_style": "cover_at_least_once" if data["variant_type"] == "set_covering" else "cover_exactly_once",
        "binding_elements": binding_elements,
        "redundantly_covered_elements": redundant_elements,
    }


def solve_exact(data):
    subsets = data["sets"]["S"]
    best = None
    for mask in range(1 << len(subsets)):
        selected = [subsets[idx] for idx in range(len(subsets)) if (mask >> idx) & 1]
        counts = coverage_counts(data, selected)
        if not is_feasible(data, counts):
            continue
        objective = selection_objective(data, selected)
        candidate = (objective, tuple(selected), counts)
        if best is None or candidate[:2] < best[:2]:
            best = candidate
    if best is None:
        raise RuntimeError("No feasible solution exists for this instance.")
    return best[0], list(best[1]), best[2]


def solve_with_gurobi(data):
    import gurobipy as gp
    from gurobipy import GRB

    elements = data["sets"]["E"]
    subsets = data["sets"]["S"]
    incidence = data["incidence_matrix"]
    subset_costs = data["subset_costs"]

    model = gp.Model("scp_reference")
    model.Params.OutputFlag = 0

    x = model.addVars(subsets, vtype=GRB.BINARY, name="x")

    for element in elements:
        expr = gp.quicksum(int(incidence[element][subset_id]) * x[subset_id] for subset_id in subsets)
        if data["variant_type"] == "set_covering":
            model.addConstr(expr >= 1, name=f"cover_{element}")
        else:
            model.addConstr(expr == 1, name=f"partition_{element}")

    model.setObjective(
        gp.quicksum(int(subset_costs[subset_id]) * x[subset_id] for subset_id in subsets),
        GRB.MINIMIZE,
    )
    model.optimize()

    if model.Status != GRB.OPTIMAL:
        raise RuntimeError(f"Gurobi did not reach optimality. Status={model.Status}")

    selected = [subset_id for subset_id in subsets if x[subset_id].X > 0.5]
    counts = coverage_counts(data, selected)
    return float(model.ObjVal), selected, counts


def main():
    data = load_data()
    output_path = Path(__file__).resolve().parent / "solution_ref.json"

    start = time.perf_counter()
    try:
        objective, selected, counts = solve_with_gurobi(data)
        runtime = time.perf_counter() - start
        solve_method = (
            "gurobi_binary_set_covering_mip"
            if data["variant_type"] == "set_covering"
            else "gurobi_binary_set_partitioning_mip"
        )
        solution = build_solution(
            data,
            objective,
            selected,
            counts,
            solver_used="gurobi",
            solve_method=solve_method,
            optimality_proof="gurobi_mip_optimal_status",
            runtime_seconds=runtime,
        )
    except Exception:
        objective, selected, counts = solve_exact(data)
        runtime = time.perf_counter() - start
        solution = build_solution(
            data,
            objective,
            selected,
            counts,
            solver_used="exact_enumeration",
            solve_method="complete_binary_subset_enumeration",
            optimality_proof="complete_enumeration_of_all_binary_subset_selections",
            runtime_seconds=runtime,
        )

    output_path.write_text(json.dumps(solution, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
