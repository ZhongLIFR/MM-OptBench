# Mathematical Model: Parallel Machine Scheduling

## Problem Overview

This instance is a single-period Parallel Machine Scheduling problem.

A set of independent jobs must be assigned to parallel machines. Each job must be processed exactly once on one eligible machine. Machines process assigned jobs sequentially and non-preemptively. There are no precedence constraints, release dates, due dates, setup times, or machine calendars.

## Sets and Indices

- $J$: set of jobs
- $M$: set of machines
- $M_j$: eligible-machine set for job $j \in J$

For this instance:

- $J = {J1, J2, J3, J4, J5, J6, J7, J8, J9}$
- $M = {M1, M2, M3}$

## Parameters

- $p_j$: base processing time of job $j$
- $s_m$: speed factor of machine $m$
- $p_{j,m}$: effective processing time of job $j$ on machine $m$
- $w_j$: job weight (used only for weighted-completion instances)

## Decision Variables

- $x_{j,m} \in \{0,1\}$: 1 if job $j$ is assigned to machine $m$
- $C_j \ge 0$: completion time of job $j$

## Objective Function

Minimize the weighted total completion time:

\[
\min\; \sum_{j \in J} w_j C_j
\]

where $C_j$ is the completion time of job $j$ under the WSPT (Smith-rule) order induced on its assigned machine.

## Constraints

### 1. Assignment constraints

For every job $j \in J$:

\[
\sum_{m \in M_j} x_{j,m} = 1
\]

and

\[
x_{j,m} = 0 \qquad \forall j \in J,\; m \notin M_j
\]

### 2. Completion-time interpretation

For $P\|\|\sum w_j C_j$, once jobs are assigned to a machine, the executable reference solver sequences them in **WSPT order** on that machine, i.e., nondecreasing $p_{j,m}/w_j$. The completion time of each job is then determined by the cumulative assigned processing load preceding it in that order.

### 3. Variable domains

\[
C_j \ge 0 \qquad \forall j \in J
\]

\[
x_{j,m} \in \{0,1\} \qquad \forall j \in J,\; m \in M_j
\]

## Complete Model

\[
\begin{aligned}
\min \quad & \sum_{j \in J} w_j C_j \\
\text{s.t.} \quad
& \sum_{m \in M_j} x_{j,m} = 1 && \forall j \in J, \\
& x_{j,m} = 0 && \forall j \in J,\; m \notin M_j, \\
& C_j \ge 0 && \forall j \in J, \\
& x_{j,m} \in \{0,1\} && \forall j \in J,\; m \in M_j.
\end{aligned}
\]

## Instance-Specific Notes

This instance uses identical machines. The visual reports the job-machine eligibility matrix and the base job durations. For related-machine instances, effective processing times are derived from the machine speed factors and recorded in `instance_data.json`.
