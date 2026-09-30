# Mathematical Model: Parallel Machine Scheduling

## Problem Overview

This instance is a single-period parallel machine scheduling problem with non-preemptive jobs.
Each job must be assigned to exactly one eligible machine. The objective is to minimize the makespan, i.e., the maximum total processing load assigned to any machine.

## Sets and Indices

- $J$: set of jobs
- $M$: set of machines
- $M_j$: eligible-machine set for job $j \in J$

For this instance:

- $J = {J1, J2, J3, J4, J5, J6, J7, J8, J9, J10, J11, J12, J13, J14, J15, J16, J17, J18, J19, J20, J21, J22, J23, J24, J25, J26, J27, J28, J29, J30, J31, J32, J33, J34, J35, J36, J37, J38, J39, J40, J41, J42, J43, J44, J45, J46, J47, J48}$
- $M = {M1, M2, M3, M4, M5, M6, M7}$

## Parameters

- $p_{j,m}$: processing time of job $j$ on machine $m$ (defined for $m \in M_j$)
- $C_{\max}$: makespan variable

## Decision Variables

- $x_{j,m} \in \{0,1\}$: 1 if job $j$ is assigned to machine $m$
- $C_{\max} \ge 0$: maximum machine completion time

## Objective Function

\[
\min\; C_{\max}
\]

## Constraints

### 1. Assignment constraints

\[
\sum_{m \in M_j} x_{j,m} = 1 \qquad \forall j \in J
\]

### 2. Machine-load constraints

\[
\sum_{j \in J: m \in M_j} p_{j,m} x_{j,m} \le C_{\max} \qquad \forall m \in M
\]

### 3. Variable domains

\[
x_{j,m} \in \{0,1\} \qquad \forall j \in J,\; m \in M_j
\]
\[
C_{\max} \ge 0
\]

## Complete Model

The executable reference solver implements the above compact assignment-load mixed-integer formulation directly.

## Instance-Specific Notes

This instance uses machine type `Q` with a makespan objective. The visual shows a matrix + duration-bar layout so that the instance remains readable as a single benchmark image. For R-type instances, the exact machine-dependent processing times are written directly inside eligible matrix cells.
