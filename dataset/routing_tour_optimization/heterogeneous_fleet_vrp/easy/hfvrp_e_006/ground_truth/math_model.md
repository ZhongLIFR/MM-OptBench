# Mathematical Model: Heterogeneous Fleet Vehicle Routing Problem

## Problem Overview

This instance is a deterministic single-depot Heterogeneous Fleet Vehicle Routing Problem (HFVRP).

A set of non-identical vehicles is available at a common depot. Each activated vehicle departs from the depot, serves a subset of customers, and returns to the depot. Every customer must be visited exactly once by exactly one activated vehicle. Each vehicle has its own capacity, fixed activation cost, and per-distance operating-cost multiplier. The routing graph is complete, and the base travel distance between nodes is induced by the plotted coordinates and then converted into vehicle-specific arc cost via the corresponding multiplier.

This instance uses an arc-based multi-vehicle routing model with activation variables and vehicle-specific MTZ-style load constraints. The formulation jointly decides which vehicles to activate and how to route them.

## Sets and Indices

- $N$: set of all nodes (depot plus customers)
- $C$: set of customers
- $K$: set of explicitly available vehicles
- $T$: set of vehicle categories
- $A$: set of directed arcs $(i,j)$ for all $i,j \in N$ with $i \ne j$
- $0$: designated depot node

For this instance:

- $N = \{Depot, C1, C2, C3, C4, C5, C6, C7, C8, C9, C10\}$
- $C = \{C1, C2, C3, C4, C5, C6, C7, C8, C9, C10\}$
- $K = \{SM1, SM2, SM3, LG1\}$
- $T = \{SM, LG\}$
- depot $= Depot$

## Parameters

- $\delta_{i,j}$: base distance from node $i$ to node $j$
- $d_i$: demand of customer $i$
- $Q_k$: capacity of vehicle $k$
- $f_k$: fixed activation cost of vehicle $k$
- $\alpha_k$: per-distance multiplier of vehicle $k$
- $c_{i,j,k} = \alpha_k \delta_{i,j}$: vehicle-specific travel cost on arc $(i,j)$

## Decision Variables

- $x_{i,j,k} \in \{0,1\}$: equals 1 if vehicle $k$ directly travels from node $i$ to node $j$
- $y_k \in \{0,1\}$: equals 1 if vehicle $k$ is activated
- $u_{i,k} \ge 0$: continuous vehicle-specific load/order helper variable for customer $i$ and vehicle $k$

## Objective Function

Minimize total fixed activation cost plus total variable routing cost:

\[
\min \; \sum_{k \in K} f_k y_k
+ \sum_{k \in K} \sum_{i \in N} \sum_{j \in N: j \ne i} c_{i,j,k} x_{i,j,k}
\]

## Constraints

### 1. Each customer is visited exactly once (outgoing form)

\[
\sum_{k \in K} \sum_{j \in N: j \ne i} x_{i,j,k} = 1 \qquad \forall i \in C
\]

### 2. Each customer is visited exactly once (incoming form)

\[
\sum_{k \in K} \sum_{j \in N: j \ne i} x_{j,i,k} = 1 \qquad \forall i \in C
\]

### 3. Flow conservation for each vehicle at each customer

\[
\sum_{j \in N: j \ne i} x_{i,j,k} = \sum_{j \in N: j \ne i} x_{j,i,k} \qquad \forall i \in C, \; \forall k \in K
\]

### 4. Depot departure equals activation

\[
\sum_{j \in N \setminus \{0\}} x_{0,j,k} = y_k \qquad \forall k \in K
\]

### 5. Depot return equals activation

\[
\sum_{i \in N \setminus \{0\}} x_{i,0,k} = y_k \qquad \forall k \in K
\]

### 6. Vehicle-capacity constraints

\[
\sum_{i \in C} d_i \left(\sum_{j \in N: j \ne i} x_{i,j,k}\right) \le Q_k y_k \qquad \forall k \in K
\]

### 7. Load-variable lower-linking constraints

\[
u_{i,k} \ge d_i \left(\sum_{h \in N: h \ne i} x_{h,i,k}\right)
\qquad \forall i \in C, \; \forall k \in K
\]

### 8. Load-variable upper-linking constraints

\[
u_{i,k} \le Q_k \left(\sum_{h \in N: h \ne i} x_{h,i,k}\right)
\qquad \forall i \in C, \; \forall k \in K
\]

### 9. Vehicle-specific MTZ-style capacity subtour elimination constraints

Define the service-indicator expression

\[
s_{j,k} = \sum_{h \in N: h \ne j} x_{h,j,k}.
\]

For every vehicle $k$ and every pair of distinct customers $i,j \in C$:

\[
u_{i,k} - u_{j,k} + Q_k x_{i,j,k} + Q_k s_{j,k} \le 2Q_k - d_j
\]

These constraints reduce to the usual MTZ/load-propagation form when vehicle $k$ serves customer $j$, while remaining non-binding when customer $j$ is assigned to a different vehicle.

### 10. Variable domains

\[
x_{i,j,k} \in \{0,1\} \qquad \forall (i,j) \in A, \; \forall k \in K
\]

\[
y_k \in \{0,1\} \qquad \forall k \in K
\]

\[
u_{i,k} \ge 0 \qquad \forall i \in C, \; \forall k \in K
\]

## Complete Model

\[
\begin{aligned}
\min \quad
& \sum_{k \in K} f_k y_k
+ \sum_{k \in K} \sum_{i \in N} \sum_{j \in N: j \ne i} c_{i,j,k} x_{i,j,k} \\
\text{s.t.} \quad
& \sum_{k \in K} \sum_{j \in N: j \ne i} x_{i,j,k} = 1 && \forall i \in C, \\
& \sum_{k \in K} \sum_{j \in N: j \ne i} x_{j,i,k} = 1 && \forall i \in C, \\
& \sum_{j \in N: j \ne i} x_{i,j,k} = \sum_{j \in N: j \ne i} x_{j,i,k} && \forall i \in C, \; \forall k \in K, \\
& \sum_{j \in N \setminus \{0\}} x_{0,j,k} = y_k && \forall k \in K, \\
& \sum_{i \in N \setminus \{0\}} x_{i,0,k} = y_k && \forall k \in K, \\
& \sum_{i \in C} d_i \left(\sum_{j \in N: j \ne i} x_{i,j,k}\right) \le Q_k y_k && \forall k \in K, \\
& u_{i,k} \ge d_i \left(\sum_{h \in N: h \ne i} x_{h,i,k}\right) && \forall i \in C, \; \forall k \in K, \\
& u_{i,k} \le Q_k \left(\sum_{h \in N: h \ne i} x_{h,i,k}\right) && \forall i \in C, \; \forall k \in K, \\
& u_{i,k} - u_{j,k} + Q_k x_{i,j,k} + Q_k \left(\sum_{h \in N: h \ne j} x_{h,j,k}\right) \le 2Q_k - d_j
&& \forall i,j \in C,\; i \ne j,\; \forall k \in K, \\
& x_{i,j,k} \in \{0,1\} && \forall (i,j) \in A, \; \forall k \in K, \\
& y_k \in \{0,1\} && \forall k \in K, \\
& u_{i,k} \ge 0 && \forall i \in C, \; \forall k \in K.
\end{aligned}
\]

## Instance-Specific Notes

This instance uses a single composite visual artifact. The left panel shows the depot and customer locations on a coordinate plane, and each customer is accompanied by a small on-map annotation giving its exact demand and coordinates; the depot annotation gives the depot coordinates. The upper-right table lists the available vehicle categories together with their counts, capacities, fixed activation costs, and distance multipliers. The lower-right text box states the base-distance and travel-cost rule. The visual therefore contains the full numerical instance data without revealing the selected routes or the optimal solution.
