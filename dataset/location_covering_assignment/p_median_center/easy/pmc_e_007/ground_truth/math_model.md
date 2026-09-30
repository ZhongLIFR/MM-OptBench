# Mathematical Model: p-Median / p-Center

## Problem Overview

This instance is a single-period discrete location-allocation problem.
A subset of candidate sites must be selected, and every demand point
must be assigned to exactly one selected site.

For this instance, the active variant is `p_center`.

## Sets and Indices

- `I`: set of demand points
- `J`: set of candidate sites

For this instance:

- `I = {D1, D2, D3, D4, D5, D6, D7}`
- `J = {F1, F2, F3, F4, F5, F6}`

## Parameters

- `p`: exact number of sites that must be selected
- `d_ij`: Euclidean distance from demand point `i in I` to candidate site `j in J`


For this instance, `p = 2`.

## Decision Variables

- `y_j in {0,1}`: equals 1 if candidate site `j` is selected
- `x_ij in {0,1}`: equals 1 if demand point `i` is assigned to candidate site `j`
- `R >= 0`: upper bound on the assignment distance experienced by any demand point

## Objective Function

\[
\min R
\]

## Constraints

### 1. Demand Assignment

Each demand point must be assigned to exactly one site:

\[
\sum_{j \in J} x_{ij} = 1
\qquad \forall i \in I
\]

### 2. Site Count

Exactly `p` candidate sites must be selected:

\[
\sum_{j \in J} y_j = p
\]

### 3. Linking Constraints

A demand point can only be assigned to a selected site:

\[
x_{ij} \le y_j
\qquad \forall i \in I,\; j \in J
\]

### 4. Radius Upper Bound

For every demand point, the chosen assignment distance must not exceed `R`:

\[
\sum_{j \in J} d_{ij} x_{ij} \le R
\qquad \forall i \in I
\]

### 5. Variable Domains

\[
y_j \in \{0,1\}
\qquad \forall j \in J
\]

\[
x_{ij} \in \{0,1\}
\qquad \forall i \in I,\; j \in J
\]

## Complete Model

\[
\begin{aligned}
\min \quad
& R \\
\text{s.t.} \quad
& \sum_{j \in J} x_{ij} = 1 && \forall i \in I, \\
& \sum_{j \in J} y_j = p, \\
& x_{ij} \le y_j && \forall i \in I,\; j \in J, \\
& \sum_{j \in J} d_{ij} x_{ij} \le R && \forall i \in I, \\
& y_j \in \{0,1\} && \forall j \in J, \\
& x_{ij} \in \{0,1\} && \forall i \in I,\; j \in J.
\end{aligned}
\]

## Instance-Specific Notes

This easy-level instance is a classical p-center problem. All candidate sites are feasible for every demand point, and the objective is driven by the worst served demand point.
All distances used by the reference implementation are the Euclidean
distances implied by the shown coordinates, rounded to 2 decimals.
