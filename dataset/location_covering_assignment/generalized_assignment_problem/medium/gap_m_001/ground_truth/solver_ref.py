#!/usr/bin/env python3
import json
import time
from pathlib import Path

SOLVER_POLICY = "prefer_gurobi_else_exact_fallback"


def ordered_assignments(tasks, assignments):
    return {task: assignments[task] for task in tasks}


def compute_agent_loads(agents, tasks, assignments, resource):
    loads = {agent: 0 for agent in agents}
    for task in tasks:
        agent = assignments[task]
        loads[agent] += resource[agent][task]
    return loads


def build_solution(agents, tasks, objective, assignments, resource, solver_used, solve_method, runtime_seconds, optimality_proof):
    objective = round(float(objective), 6)
    loads = compute_agent_loads(agents, tasks, assignments, resource)
    return {
        "status": "optimal",
        "objective_exact": objective,
        "objective_value": objective,
        "runtime_seconds": round(float(runtime_seconds), 6),
        "assignments": ordered_assignments(tasks, assignments),
        "agent_loads": loads,
        "solver_policy": SOLVER_POLICY,
        "solver_used": solver_used,
        "solve_method": solve_method,
        "optimality_proof": optimality_proof,
    }


def solve_with_gurobi(instance_data):
    import gurobipy as gp
    from gurobipy import GRB

    start = time.time()
    agents = instance_data["sets"]["agents"]
    tasks = instance_data["sets"]["tasks"]
    feasible_by_task = instance_data["task_feasible_agents"]
    cost = instance_data["cost_matrix"]
    resource = instance_data["resource_matrix"]
    capacity = instance_data["agent_capacities"]

    model = gp.Model("generalized_assignment_problem")
    x = {}
    for task in tasks:
        for agent in feasible_by_task[task]:
            x[agent, task] = model.addVar(vtype=GRB.BINARY, name=f"x_{agent}_{task}")

    model.setObjective(
        gp.quicksum(cost[agent][task] * x[agent, task] for (agent, task) in x),
        GRB.MINIMIZE,
    )

    for task in tasks:
        model.addConstr(
            gp.quicksum(x[agent, task] for agent in feasible_by_task[task]) == 1,
            name=f"assign_{task}",
        )

    for agent in agents:
        model.addConstr(
            gp.quicksum(resource[agent][task] * x[agent, task] for task in tasks if (agent, task) in x)
            <= capacity[agent],
            name=f"capacity_{agent}",
        )

    model.Params.OutputFlag = 0
    model.optimize()
    if model.Status != GRB.OPTIMAL:
        raise RuntimeError(f"Gurobi did not return an optimal solution. Status={model.Status}")

    assignments = {}
    for task in tasks:
        for agent in feasible_by_task[task]:
            if x[agent, task].X > 0.5:
                assignments[task] = agent
                break

    return build_solution(
        agents,
        tasks,
        model.ObjVal,
        assignments,
        resource,
        solver_used="gurobi",
        solve_method="gurobi_mip",
        runtime_seconds=time.time() - start,
        optimality_proof="gurobi_optimal_status",
    )


def solve_with_exact_search(instance_data):
    start = time.time()
    agents = instance_data["sets"]["agents"]
    tasks = instance_data["sets"]["tasks"]
    feasible_by_task = instance_data["task_feasible_agents"]
    cost = instance_data["cost_matrix"]
    resource = instance_data["resource_matrix"]
    capacity = instance_data["agent_capacities"]

    task_order = sorted(tasks, key=lambda task: (len(feasible_by_task[task]), task))
    suffix_lb = [0] * (len(task_order) + 1)
    for idx in range(len(task_order) - 1, -1, -1):
        task = task_order[idx]
        suffix_lb[idx] = suffix_lb[idx + 1] + min(cost[agent][task] for agent in feasible_by_task[task])

    best_objective = float("inf")
    best_assignments = None
    loads = {agent: 0 for agent in agents}
    partial = {}

    def dfs(index, objective):
        nonlocal best_objective, best_assignments

        if objective + suffix_lb[index] >= best_objective:
            return

        if index == len(task_order):
            best_objective = objective
            best_assignments = dict(partial)
            return

        task = task_order[index]
        options = sorted(feasible_by_task[task], key=lambda agent: (cost[agent][task], resource[agent][task], agent))
        for agent in options:
            usage = resource[agent][task]
            if loads[agent] + usage > capacity[agent]:
                continue
            loads[agent] += usage
            partial[task] = agent
            dfs(index + 1, objective + cost[agent][task])
            del partial[task]
            loads[agent] -= usage

    dfs(0, 0)
    if best_assignments is None:
        raise RuntimeError("Exact search did not find a feasible solution.")

    return build_solution(
        agents,
        tasks,
        best_objective,
        best_assignments,
        resource,
        solver_used="exact_branch_and_bound",
        solve_method="complete_depth_first_search",
        runtime_seconds=time.time() - start,
        optimality_proof="complete_depth_first_enumeration_with_pruning",
    )


def main():
    base = Path(__file__).resolve().parent
    instance_data = json.loads((base / "instance_data.json").read_text(encoding="utf-8"))
    try:
        solution = solve_with_gurobi(instance_data)
    except Exception:
        solution = solve_with_exact_search(instance_data)
    (base / "solution_ref.json").write_text(json.dumps(solution, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
