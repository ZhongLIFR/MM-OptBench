# Mathematical Model: Vehicle Routing Problem

## Problem Overview

This instance is a deterministic single-depot Capacitated Vehicle Routing Problem (CVRP) with identical vehicles.

A fleet of vehicles departs from a common depot, serves all customers, and returns to the depot. Each customer must be visited exactly once by exactly one vehicle. Every route must respect the common vehicle-capacity limit. The graph is complete, and the travel cost between each ordered pair of distinct nodes is given by the instance-specific travel-cost matrix.

This instance uses an arc-based multi-vehicle routing model with MTZ-style load constraints to eliminate subtours and encode route feasibility under capacity limits.

## Sets and Indices

- $N$: set of all nodes (depot plus customers)
- $C$: set of customers
- $V$: set of available vehicles
- $A$: set of directed arcs $(i,j)$ for all $i,j \in N$ with $i \ne j$
- $0$: designated depot node

For this instance:

- $N = \{Depot, C1, C2, C3, C4, C5, C6, C7, C8, C9, C10, C11, C12\}$
- $C = \{C1, C2, C3, C4, C5, C6, C7, C8, C9, C10, C11, C12\}$
- $V = \{V1, V2, V3, V4\}$
- depot $= Depot$

## Parameters

- $c_{i,j}$: travel cost from node $i$ to node $j$
- $d_i$: demand of customer $i$
- $Q$: common capacity of each vehicle
- $m = |V|$: number of available vehicles

## Decision Variables

- $x_{i,j,v} \in \{0,1\}$: equals 1 if vehicle $v$ directly travels from node $i$ to node $j$
- $u_i$: continuous load/order helper variable for customer $i$, used in MTZ-style capacity subtour elimination

## Objective Function

Minimize total routing cost:

\[
\min \; \sum_{v \in V} \sum_{i \in N} \sum_{j \in N: j \ne i} c_{i,j} x_{i,j,v}
\]

## Constraints

### 1. Each customer is visited exactly once (outgoing form)

\[
\sum_{v \in V} \sum_{j \in N: j \ne i} x_{i,j,v} = 1 \qquad \forall i \in C
\]

### 2. Each customer is visited exactly once (incoming form)

\[
\sum_{v \in V} \sum_{j \in N: j \ne i} x_{j,i,v} = 1 \qquad \forall i \in C
\]

### 3. Flow conservation for each vehicle at each customer

\[
\sum_{j \in N: j \ne i} x_{i,j,v} = \sum_{j \in N: j \ne i} x_{j,i,v} \qquad \forall i \in C, \; \forall v \in V
\]

### 4. Depot departure/return consistency for each vehicle

\[
\sum_{j \in N \setminus \{0\}} x_{0,j,v} = \sum_{j \in N \setminus \{0\}} x_{j,0,v} \qquad \forall v \in V
\]

### 5. Each vehicle can be used for at most one route

\[
\sum_{j \in N \setminus \{0\}} x_{0,j,v} \le 1 \qquad \forall v \in V
\]

\[
\sum_{j \in N \setminus \{0\}} x_{j,0,v} \le 1 \qquad \forall v \in V
\]

### 6. Vehicle-capacity constraints

\[
\sum_{i \in C} d_i \left(\sum_{j \in N: j \ne i} x_{i,j,v}\right) \le Q \qquad \forall v \in V
\]

### 7. Load-variable lower-linking constraints

\[
u_i \ge d_i \left(\sum_{v \in V} \sum_{j \in N: j \ne i} x_{i,j,v}\right) \qquad \forall i \in C
\]

### 8. Load-variable upper-linking constraints

\[
u_i \le Q \left(\sum_{v \in V} \sum_{j \in N: j \ne i} x_{i,j,v}\right) \qquad \forall i \in C
\]

### 9. MTZ-style capacity subtour elimination constraints

For all distinct customers $i,j \in C$:

\[
u_i - u_j + Q \sum_{v \in V} x_{i,j,v} \le Q - d_j
\]

### 10. Variable domains

\[
x_{i,j,v} \in \{0,1\} \qquad \forall (i,j) \in A, \; \forall v \in V
\]

\[
u_i \ge 0 \qquad \forall i \in C
\]

## Complete Model

The complete model is the collection of the objective and constraints above, instantiated with the exact node set, customer set, fleet size, capacity level, and travel-cost matrix recorded for this instance.

## Instance-Specific Notes

This instance uses a single composite visual artifact. The left panel shows the depot, customers, exact node coordinates, and demand annotations on a coordinate plane. The right panel provides the fleet parameters and the complete travel-cost matrix. The visual therefore contains the full numerical problem specification without revealing the selected routes or the optimal solution.
