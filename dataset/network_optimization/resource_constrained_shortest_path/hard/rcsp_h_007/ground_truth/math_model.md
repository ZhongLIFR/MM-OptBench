# Mathematical Model: Dual-Resource Resource-Constrained Path Selection

## Problem Overview

Given a directed network with start node $s$ and destination node $t$, choose exactly one directed $s$-$t$ path of minimum total cost while satisfying upper bounds on total time and total budget.

## Sets and Indices

- $\mathcal{N}$: set of nodes, indexed by $i \in \mathcal{N}$
- $\mathcal{A}$: set of directed arcs, indexed by $(i,j) \in \mathcal{A}$
- $s$: start node
- $t$: destination node

## Parameters

- $c_{ij}$: cost of selecting arc $(i,j)$
- $r^{(1)}_{ij}$: time consumed by arc $(i,j)$
- $r^{(2)}_{ij}$: budget consumed by arc $(i,j)$
- $R_1$: upper bound on total time
- $R_2$: upper bound on total budget

## Decision Variables

- $x_{ij} \in \{0,1\}$: equals 1 if arc $(i,j)$ is selected in the route, and 0 otherwise

## Objective Function

\[
\min \;\; \sum_{(i,j)\in\mathcal{A}} c_{ij} x_{ij}
\]

## Constraints

**Flow conservation**

\[
\sum_{j:(i,j)\in\mathcal{A}} x_{ij} - \sum_{j:(j,i)\in\mathcal{A}} x_{ji} =
\begin{cases}
1 & \text{if } i=s, \\
-1 & \text{if } i=t, \\
0 & \text{otherwise,}
\end{cases}
\quad \forall i\in\mathcal{N}.
\]

**First resource bound**

\[
\sum_{(i,j)\in\mathcal{A}} r^{(1)}_{ij} x_{ij} \le R_1.
\]

**Second resource bound**

\[
\sum_{(i,j)\in\mathcal{A}} r^{(2)}_{ij} x_{ij} \le R_2.
\]

**Binary restrictions**

\[
x_{ij} \in \{0,1\}, \quad \forall (i,j)\in\mathcal{A}.
\]

## Complete Model

\[
\begin{aligned}
\min \quad & \sum_{(i,j)\in\mathcal{A}} c_{ij} x_{ij} \\
\text{s.t.} \quad
& \sum_{j:(i,j)\in\mathcal{A}} x_{ij} - \sum_{j:(j,i)\in\mathcal{A}} x_{ji} =
\begin{cases}
1 & \text{if } i=s, \\
-1 & \text{if } i=t, \\
0 & \text{otherwise,}
\end{cases}
&& \forall i\in\mathcal{N}, \\
& \sum_{(i,j)\in\mathcal{A}} r^{(1)}_{ij} x_{ij} \le R_1, \\
& \sum_{(i,j)\in\mathcal{A}} r^{(2)}_{ij} x_{ij} \le R_2, \\
& x_{ij} \in \{0,1\}
&& \forall (i,j)\in\mathcal{A}.
\end{aligned}
\]

## Instance-Specific Notes

- The displayed resource order in this instance is **[time, budget]**.
- All numeric coefficients, node coordinates, and visual layout data are stored in `instance_data.json`.
- Because all arc costs are positive, an optimal solution will not include an unnecessary directed cycle.
