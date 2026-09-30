#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
import time


def normalize_numeric(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        rounded_int = round(value)
        if abs(value - rounded_int) <= 1e-6:
            return int(rounded_int)
        return round(value, 6)
    if isinstance(value, list):
        return [normalize_numeric(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize_numeric(val) for key, val in value.items()}
    return value


def solve_reference(data: dict, time_limit_seconds: float = 30.0) -> dict:
    try:
        import gurobipy as gp
        from gurobipy import GRB
    except Exception as exc:
        gp = None
        GRB = None

    jobs = data["sets"]["jobs"]
    stages = data["sets"]["stages"]
    machines_by_stage = data["sets"]["machines_by_stage"]
    p = data["processing_time"]
    horizon = sum(p[j][s] for j in jobs for s in stages)

    def build_solution_from_values(
        start_lookup: dict[tuple[str, str], float],
        assign_lookup: dict[tuple[str, str, str], float],
        objective_value: float,
        runtime_seconds: float,
        solve_method: str,
        solver_name: str,
    ) -> dict:
        machine_assignment: dict[str, dict[str, str]] = {j: {} for j in jobs}
        start_time: dict[str, dict[str, float]] = {j: {} for j in jobs}
        completion_time: dict[str, dict[str, float]] = {j: {} for j in jobs}
        machine_timelines: dict[str, dict[str, list[dict]]] = {
            s: {m: [] for m in machines_by_stage[s]}
            for s in stages
        }

        for j in jobs:
            for s in stages:
                chosen_machine = None
                for m in machines_by_stage[s]:
                    if assign_lookup[j, s, m] > 0.5:
                        chosen_machine = m
                        break
                if chosen_machine is None:
                    raise RuntimeError(f"No machine selected for {j}, {s}.")
                machine_assignment[j][s] = chosen_machine
                st = float(start_lookup[j, s])
                ft = st + float(p[j][s])
                start_time[j][s] = st
                completion_time[j][s] = ft
                machine_timelines[s][chosen_machine].append(
                    {
                        "job": j,
                        "start": st,
                        "finish": ft,
                        "duration": int(p[j][s]),
                    }
                )

        for s in stages:
            for m in machines_by_stage[s]:
                machine_timelines[s][m].sort(key=lambda rec: (rec["start"], rec["job"]))

        solution = {
            "status": "optimal",
            "objective": float(objective_value),
            "objective_exact": float(objective_value),
            "optimal_makespan": float(objective_value),
            "machine_assignment": machine_assignment,
            "start_time": start_time,
            "completion_time": completion_time,
            "machine_timelines": machine_timelines,
            "solve_method": solve_method,
            "solver": solver_name,
            "runtime_seconds": float(runtime_seconds),
        }
        return normalize_numeric(solution)

    def solve_with_scipy(time_limit: float) -> dict:
        import numpy as np
        from scipy.optimize import Bounds, LinearConstraint, milp
        from scipy.sparse import lil_matrix

        start_clock = time.perf_counter()

        start_idx: dict[tuple[str, str], int] = {}
        x_idx: dict[tuple[str, str, str], int] = {}
        y_idx: dict[tuple[str, str, str, str], int] = {}
        idx = 0

        for j in jobs:
            for s in stages:
                start_idx[j, s] = idx
                idx += 1
                for m in machines_by_stage[s]:
                    x_idx[j, s, m] = idx
                    idx += 1

        for s in stages:
            for m in machines_by_stage[s]:
                for pos_j, j in enumerate(jobs):
                    for k in jobs[pos_j + 1 :]:
                        y_idx[j, k, s, m] = idx
                        idx += 1

        cmax_idx = idx
        idx += 1
        n_vars = idx

        bounds_lb = np.zeros(n_vars, dtype=float)
        bounds_ub = np.full(n_vars, np.inf, dtype=float)
        integrality = np.zeros(n_vars, dtype=int)
        for (_, _, _), var_idx in x_idx.items():
            bounds_ub[var_idx] = 1.0
            integrality[var_idx] = 1
        for (_, _, _, _), var_idx in y_idx.items():
            bounds_ub[var_idx] = 1.0
            integrality[var_idx] = 1

        constraints = []

        for j in jobs:
            for s in stages:
                row = lil_matrix((1, n_vars), dtype=float)
                for m in machines_by_stage[s]:
                    row[0, x_idx[j, s, m]] = 1.0
                constraints.append(LinearConstraint(row.tocsr(), [1.0], [1.0]))

        for j in jobs:
            for pos_s, s in enumerate(stages[:-1]):
                next_s = stages[pos_s + 1]
                row = lil_matrix((1, n_vars), dtype=float)
                row[0, start_idx[j, next_s]] = 1.0
                row[0, start_idx[j, s]] = -1.0
                constraints.append(LinearConstraint(row.tocsr(), [float(p[j][s])], [np.inf]))

        for s in stages:
            for m in machines_by_stage[s]:
                for pos_j, j in enumerate(jobs):
                    for k in jobs[pos_j + 1 :]:
                        y_var = y_idx[j, k, s, m]

                        row_a = lil_matrix((1, n_vars), dtype=float)
                        row_a[0, start_idx[j, s]] = 1.0
                        row_a[0, start_idx[k, s]] = -1.0
                        row_a[0, x_idx[j, s, m]] = horizon
                        row_a[0, x_idx[k, s, m]] = horizon
                        row_a[0, y_var] = horizon
                        constraints.append(
                            LinearConstraint(
                                row_a.tocsr(),
                                [-np.inf],
                                [float(3 * horizon - p[j][s])],
                            )
                        )

                        row_b = lil_matrix((1, n_vars), dtype=float)
                        row_b[0, start_idx[k, s]] = 1.0
                        row_b[0, start_idx[j, s]] = -1.0
                        row_b[0, x_idx[j, s, m]] = horizon
                        row_b[0, x_idx[k, s, m]] = horizon
                        row_b[0, y_var] = -horizon
                        constraints.append(
                            LinearConstraint(
                                row_b.tocsr(),
                                [-np.inf],
                                [float(2 * horizon - p[k][s])],
                            )
                        )

        last_stage = stages[-1]
        for j in jobs:
            row = lil_matrix((1, n_vars), dtype=float)
            row[0, cmax_idx] = 1.0
            row[0, start_idx[j, last_stage]] = -1.0
            constraints.append(LinearConstraint(row.tocsr(), [float(p[j][last_stage])], [np.inf]))

        c = np.zeros(n_vars, dtype=float)
        c[cmax_idx] = 1.0

        result = milp(
            c=c,
            integrality=integrality,
            bounds=Bounds(bounds_lb, bounds_ub),
            constraints=constraints,
            options={"time_limit": float(time_limit), "mip_rel_gap": 0.0, "presolve": True},
        )
        wall_runtime = time.perf_counter() - start_clock
        if not result.success or result.x is None:
            raise RuntimeError(f"SciPy MILP did not prove optimality for {data['instance_id']}: status={result.status}")

        start_lookup = {(j, s): float(result.x[start_idx[j, s]]) for j in jobs for s in stages}
        assign_lookup = {(j, s, m): float(result.x[x_idx[j, s, m]]) for j in jobs for s in stages for m in machines_by_stage[s]}
        return build_solution_from_values(
            start_lookup=start_lookup,
            assign_lookup=assign_lookup,
            objective_value=float(result.fun),
            runtime_seconds=float(wall_runtime),
            solve_method="scipy_disjunctive_milp_fhfss",
            solver_name="SciPy",
        )

    if gp is None or GRB is None:
        return solve_with_scipy(max(120.0, 2 * time_limit_seconds))

    model = gp.Model(data["instance_id"])
    model.Params.OutputFlag = 0
    model.Params.TimeLimit = time_limit_seconds
    model.Params.MIPGap = 0.0

    x = {}
    start = {}
    y = {}

    for j in jobs:
        for s in stages:
            start[j, s] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"start[{j},{s}]")
            for m in machines_by_stage[s]:
                x[j, s, m] = model.addVar(vtype=GRB.BINARY, name=f"x[{j},{s},{m}]")

    for s in stages:
        for m in machines_by_stage[s]:
            for idx_j, j in enumerate(jobs):
                for k in jobs[idx_j + 1 :]:
                    y[j, k, s, m] = model.addVar(vtype=GRB.BINARY, name=f"y[{j},{k},{s},{m}]")

    cmax = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="C_max")
    model.setObjective(cmax, GRB.MINIMIZE)

    for j in jobs:
        for s in stages:
            model.addConstr(
                sum(x[j, s, m] for m in machines_by_stage[s]) == 1,
                name=f"assign[{j},{s}]",
            )

    for j in jobs:
        for idx_s, s in enumerate(stages[:-1]):
            next_s = stages[idx_s + 1]
            model.addConstr(
                start[j, next_s] >= start[j, s] + p[j][s],
                name=f"prec[{j},{s}]",
            )

    for s in stages:
        for m in machines_by_stage[s]:
            for idx_j, j in enumerate(jobs):
                for k in jobs[idx_j + 1 :]:
                    model.addConstr(
                        start[j, s] + p[j][s]
                        <= start[k, s] + horizon * (3 - x[j, s, m] - x[k, s, m] - y[j, k, s, m]),
                        name=f"noov_a[{j},{k},{s},{m}]",
                    )
                    model.addConstr(
                        start[k, s] + p[k][s]
                        <= start[j, s] + horizon * (2 - x[j, s, m] - x[k, s, m] + y[j, k, s, m]),
                        name=f"noov_b[{j},{k},{s},{m}]",
                    )

    last_stage = stages[-1]
    for j in jobs:
        model.addConstr(cmax >= start[j, last_stage] + p[j][last_stage], name=f"makespan[{j}]")

    wall_start = time.perf_counter()
    model.optimize()
    wall_runtime = time.perf_counter() - wall_start

    if model.Status == GRB.OPTIMAL:
        start_lookup = {(j, s): float(start[j, s].X) for j in jobs for s in stages}
        assign_lookup = {(j, s, m): float(x[j, s, m].X) for j in jobs for s in stages for m in machines_by_stage[s]}
        return build_solution_from_values(
            start_lookup=start_lookup,
            assign_lookup=assign_lookup,
            objective_value=float(model.ObjVal),
            runtime_seconds=float(max(model.Runtime, wall_runtime)),
            solve_method="gurobi_disjunctive_milp_fhfss",
            solver_name="Gurobi",
        )

    return solve_with_scipy(max(120.0, 2 * time_limit_seconds))


def main():
    gt_dir = Path(__file__).resolve().parent
    data = json.loads((gt_dir / "instance_data.json").read_text(encoding="utf-8"))
    solution = solve_reference(data, time_limit_seconds=30.0)
    (gt_dir / "solution_ref.json").write_text(json.dumps(solution, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
