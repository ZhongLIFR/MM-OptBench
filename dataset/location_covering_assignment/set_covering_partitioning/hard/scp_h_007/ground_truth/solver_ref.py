#!/usr/bin/env python3
import json
import math
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


def lower_bound(data, uncovered_elements):
    if not uncovered_elements:
        return 0.0
    subset_sizes = [data["candidate_subsets"][subset_id]["cardinality"] for subset_id in data["sets"]["S"]]
    max_size = max(subset_sizes)
    min_cost = min(int(cost) for cost in data["subset_costs"].values())
    return float(math.ceil(len(uncovered_elements) / max_size) * min_cost)


def greedy_cover_upper_bound(data):
    uncovered = set(data["sets"]["E"])
    selected = []
    while uncovered:
        best_subset = None
        best_key = None
        for subset_id in data["sets"]["S"]:
            covered = set(data["candidate_subsets"][subset_id]["covered_elements"])
            gain = len(covered & uncovered)
            if gain == 0:
                continue
            key = (int(data["subset_costs"][subset_id]) / gain, int(data["subset_costs"][subset_id]), subset_id)
            if best_key is None or key < best_key:
                best_key = key
                best_subset = subset_id
        if best_subset is None:
            raise RuntimeError("Greedy cover could not find a feasible completion.")
        selected.append(best_subset)
        uncovered -= set(data["candidate_subsets"][best_subset]["covered_elements"])
    counts = coverage_counts(data, selected)
    if not is_feasible(data, counts):
        raise RuntimeError("Greedy cover produced an infeasible solution.")
    return selection_objective(data, selected), selected, counts


def greedy_partition_upper_bound(data):
    uncovered = set(data["sets"]["E"])
    selected = []
    while uncovered:
        pivot = min(
            uncovered,
            key=lambda element: (
                len([
                    subset_id
                    for subset_id in data["element_to_subsets"][element]
                    if set(data["candidate_subsets"][subset_id]["covered_elements"]).issubset(uncovered)
                ]),
                element,
            ),
        )
        candidates = []
        for subset_id in data["element_to_subsets"][pivot]:
            covered = set(data["candidate_subsets"][subset_id]["covered_elements"])
            if covered.issubset(uncovered):
                candidates.append(
                    (
                        int(data["subset_costs"][subset_id]) / len(covered),
                        int(data["subset_costs"][subset_id]),
                        subset_id,
                    )
                )
        if not candidates:
            raise RuntimeError("Greedy partition could not find a feasible completion.")
        _, _, chosen = min(candidates)
        selected.append(chosen)
        uncovered -= set(data["candidate_subsets"][chosen]["covered_elements"])
    counts = coverage_counts(data, selected)
    if not is_feasible(data, counts):
        raise RuntimeError("Greedy partition produced an infeasible solution.")
    return selection_objective(data, selected), selected, counts


def solve_exact_branch_and_bound_covering(data):
    subsets_by_element = data["element_to_subsets"]
    all_elements = set(data["sets"]["E"])
    best_objective, best_selected, best_counts = greedy_cover_upper_bound(data)

    def search(uncovered, selected, current_cost):
        nonlocal best_objective, best_selected, best_counts
        if current_cost >= best_objective:
            return
        if not uncovered:
            counts = coverage_counts(data, selected)
            if is_feasible(data, counts):
                best_objective = current_cost
                best_selected = list(selected)
                best_counts = counts
            return
        if current_cost + lower_bound(data, uncovered) >= best_objective:
            return
        pivot = min(uncovered, key=lambda element: (len(subsets_by_element[element]), element))
        candidates = []
        for subset_id in subsets_by_element[pivot]:
            covered = set(data["candidate_subsets"][subset_id]["covered_elements"])
            gain = len(covered & uncovered)
            if gain == 0:
                continue
            candidates.append(
                (
                    int(data["subset_costs"][subset_id]) / gain,
                    int(data["subset_costs"][subset_id]),
                    subset_id,
                )
            )
        for _, subset_cost, subset_id in sorted(candidates):
            covered = set(data["candidate_subsets"][subset_id]["covered_elements"])
            search(uncovered - covered, selected + [subset_id], current_cost + subset_cost)

    search(all_elements, [], 0.0)
    if best_selected is None:
        raise RuntimeError("No feasible covering solution exists.")
    return best_objective, best_selected, best_counts


def solve_exact_branch_and_bound_partitioning(data):
    subsets_by_element = data["element_to_subsets"]
    all_elements = set(data["sets"]["E"])
    best_objective, best_selected, best_counts = greedy_partition_upper_bound(data)

    def search(uncovered, selected, current_cost):
        nonlocal best_objective, best_selected, best_counts
        if current_cost >= best_objective:
            return
        if not uncovered:
            counts = coverage_counts(data, selected)
            if is_feasible(data, counts):
                best_objective = current_cost
                best_selected = list(selected)
                best_counts = counts
            return
        if current_cost + lower_bound(data, uncovered) >= best_objective:
            return
        pivot = min(
            uncovered,
            key=lambda element: (
                len([
                    subset_id
                    for subset_id in subsets_by_element[element]
                    if set(data["candidate_subsets"][subset_id]["covered_elements"]).issubset(uncovered)
                ]),
                element,
            ),
        )
        candidates = []
        for subset_id in subsets_by_element[pivot]:
            covered = set(data["candidate_subsets"][subset_id]["covered_elements"])
            if not covered.issubset(uncovered):
                continue
            candidates.append(
                (
                    int(data["subset_costs"][subset_id]) / len(covered),
                    int(data["subset_costs"][subset_id]),
                    subset_id,
                )
            )
        for _, subset_cost, subset_id in sorted(candidates):
            covered = set(data["candidate_subsets"][subset_id]["covered_elements"])
            search(uncovered - covered, selected + [subset_id], current_cost + subset_cost)

    search(all_elements, [], 0.0)
    if best_selected is None:
        raise RuntimeError("No feasible partitioning solution exists.")
    return best_objective, best_selected, best_counts


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
        if data["variant_type"] == "set_covering":
            objective, selected, counts = solve_exact_branch_and_bound_covering(data)
            solve_method = "exact_branch_and_bound_covering"
        else:
            objective, selected, counts = solve_exact_branch_and_bound_partitioning(data)
            solve_method = "exact_branch_and_bound_partitioning"
        runtime = time.perf_counter() - start
        solution = build_solution(
            data,
            objective,
            selected,
            counts,
            solver_used="branch_and_bound",
            solve_method=solve_method,
            optimality_proof="complete_branch_and_bound_search_with_pruning",
            runtime_seconds=runtime,
        )

    output_path.write_text(json.dumps(solution, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
