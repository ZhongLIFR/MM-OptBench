# Mathematical Model: Traveling Salesman Problem

## Problem Overview

This instance is a deterministic Traveling Salesman Problem (TSP).

A salesman must visit every city exactly once and then return to the starting city. The graph is complete, and the travel cost between each ordered pair of distinct cities is given by the symmetric instance-specific cost matrix. A valid solution is a Hamiltonian cycle of minimum total travel cost.

This instance uses the standard arc-based TSP model with MTZ subtour elimination constraints.

## Sets and Indices

- $N$: set of cities
- $A$: set of directed arcs $(i,j)$ for all $i,j \in N$ with $i \ne j$
- $s$: designated reference city used to break tour symmetry in the MTZ formulation

For this instance:

- $N = {A, B, C, D, E, F, G, H, I, J, K, L, M, N, O, P, Q, R, S, T}$
- $s = A$

## Parameters

- $c_{i,j}$: travel cost from city $i$ to city $j$
- $n = |N|$: number of cities

## Decision Variables

- $x_{i,j} \in \{0,1\}$: equals 1 if the tour directly travels from city $i$ to city $j$
- $u_i$: visit order of city $i$ for MTZ subtour elimination, defined for $i \in N \setminus \{s\}$

## Objective Function

Minimize total travel cost:

\[
\min \; \sum_{i \in N} \sum_{j \in N: j \ne i} c_{i,j} x_{i,j}
\]

## Constraints

### 1. Outgoing-degree constraints

\[
\sum_{j \in N: j \ne i} x_{i,j} = 1 \qquad \forall i \in N
\]

### 2. Incoming-degree constraints

\[
\sum_{i \in N: i \ne j} x_{i,j} = 1 \qquad \forall j \in N
\]

### 3. MTZ subtour elimination constraints

For all distinct cities $i,j \in N \setminus \{s\}$:

\[
u_i - u_j + n x_{i,j} \le n - 1
\]

### 4. Order-variable bounds

\[
1 \le u_i \le n-1 \qquad \forall i \in N \setminus \{s\}
\]

### 5. Variable domains

\[
x_{i,j} \in \{0,1\} \qquad \forall (i,j) \in A
\]

## Complete Model

\[
\begin{aligned}
\min \quad & \sum_{i \in N} \sum_{j \in N: j \ne i} c_{i,j} x_{i,j} \\
\text{s.t.} \quad
& \sum_{j \in N: j \ne i} x_{i,j} = 1 && \forall i \in N, \\
& \sum_{i \in N: i \ne j} x_{i,j} = 1 && \forall j \in N, \\
& u_i - u_j + n x_{i,j} \le n-1 && \forall i,j \in N \setminus \{s\},\; i \ne j, \\
& 1 \le u_i \le n-1 && \forall i \in N \setminus \{s\}, \\
& x_{i,j} \in \{0,1\} && \forall (i,j) \in A.
\end{aligned}
\]

## Instance-Specific Notes

This instance uses the official hard-level Euclidean city-map visual format for TSP. The figure contains one labeled marker per city, with the exact coordinate pair printed next to each city and a cost-rule box stating how pairwise travel costs are derived from those coordinates. All instance-specific numerical data needed to solve the instance are provided in `instance_data.json` / `canonical_specification.txt`.
