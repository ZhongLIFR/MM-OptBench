# Mathematical Model: p-Median / p-Center

## Problem Overview

This instance is a single-period discrete location-allocation problem.
A subset of candidate sites must be selected, and every demand point
must be assigned to exactly one selected site.

For this instance, the active variant is `p_median`.

## Sets and Indices

- `I`: set of demand points
- `J`: set of candidate sites

For this instance:

- `I = {D1, D2, D3, D4, D5, D6, D7, D8, D9, D10, D11, D12, D13, D14, D15, D16, D17, D18, D19, D20, D21, D22, D23, D24}`
- `J = {F1, F2, F3, F4, F5, F6, F7, F8, F9, F10, F11, F12, F13, F14}`

## Parameters

- `p`: exact number of sites that must be selected
- `d_ij`: Euclidean distance from demand point `i in I` to candidate site `j in J`
- `w_i`: demand weight of demand point `i in I`

For this instance, `p = 4`.

## Decision Variables

- `y_j in {0,1}`: equals 1 if candidate site `j` is selected
- `x_ij in {0,1}`: equals 1 if demand point `i` is assigned to candidate site `j`


## Objective Function

\[
\min \sum_{i \in I} \sum_{j \in J} w_i d_{ij} x_{ij}
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

### 4. Variable Domains

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
& \sum_{i \in I} \sum_{j \in J} w_i d_{ij} x_{ij} \\
\text{s.t.} \quad
& \sum_{j \in J} x_{ij} = 1 && \forall i \in I, \\
& \sum_{j \in J} y_j = p, \\
& x_{ij} \le y_j && \forall i \in I,\; j \in J, \\
& y_j \in \{0,1\} && \forall j \in J, \\
& x_{ij} \in \{0,1\} && \forall i \in I,\; j \in J.
\end{aligned}
\]

## Instance-Specific Notes

This hard-level instance is a classical weighted p-median problem. All candidate sites are feasible for every demand point, so the difficulty comes from the spatial geometry, the p-value, and the demand weights.
All distances used by the reference implementation are the Euclidean
distances implied by the shown coordinates, rounded to 2 decimals.
