# Mathematical Model: Parallel Machine Scheduling

## Problem Overview

This instance is a single-period parallel machine scheduling problem with non-preemptive jobs.
Each job must be assigned to exactly one eligible machine. If two jobs are assigned to the same machine, they must be processed in sequence without overlap.

## Sets and Indices

- $J$: set of jobs
- $M$: set of machines
- $M_j$: eligible-machine set for job $j \in J$

For this instance:

- $J = {J1, J2, J3, J4, J5, J6, J7, J8, J9, J10, J11, J12, J13, J14, J15, J16, J17, J18}$
- $M = {M1, M2, M3, M4}$

## Parameters

- $p_{j,m}$: processing time of job $j$ on machine $m$ (defined for $m \in M_j$)
- $w_j$: job weight (used only for weighted-completion instances)
- $H$: a valid big-M horizon upper bound

## Decision Variables

- $x_{j,m} \in \{0,1\}$: 1 if job $j$ is assigned to machine $m$
- $S_j \ge 0$: start time of job $j$
- $C_j \ge 0$: completion time of job $j$
- $y_{i,j,m} \in \{0,1\}$ for $i<j$: ordering variable on machine $m$
- $C_{\max} \ge 0$: makespan variable

## Objective Function

\[
\min\; C_{\max}
\]

## Constraints

### 1. Assignment constraints

\[
\sum_{m \in M_j} x_{j,m} = 1 \qquad \forall j \in J
\]

### 2. Completion-time definition

\[
C_j = S_j + \sum_{m \in M_j} p_{j,m} x_{j,m} \qquad \forall j \in J
\]

### 3. Non-overlap constraints on each machine

For each pair of jobs $i<j$ and each machine $m \in M_i \cap M_j$:

\[
S_i + p_{i,m} \le S_j + H\,(3 - x_{i,m} - x_{j,m} - y_{i,j,m})
\]
\[
S_j + p_{j,m} \le S_i + H\,(2 - x_{i,m} - x_{j,m} + y_{i,j,m})
\]

### 4. Makespan constraints

\[
C_j \le C_{\max} \qquad \forall j \in J
\]

### 5. Variable domains

\[
S_j \ge 0,\; C_j \ge 0 \qquad \forall j \in J
\]
\[
x_{j,m} \in \{0,1\} \qquad \forall j \in J,\; m \in M_j
\]
\[
y_{i,j,m} \in \{0,1\} \qquad \forall i<j,\; m \in M_i \cap M_j
\]

## Complete Model

The executable reference solver implements the above formulation directly using a mixed-integer model.

## Instance-Specific Notes

This instance uses machine type `R` and objective `makespan`. The visual shows a matrix + duration-bar layout so that the instance remains readable as a single benchmark image. For R-type instances, the exact machine-dependent processing times are written directly inside eligible matrix cells.
