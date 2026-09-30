# Mathematical Model: Traveling Salesman Problem with Time Windows

## Problem Overview

This instance is a deterministic single-vehicle Traveling Salesman Problem with Time Windows (TSPTW).

A single vehicle starts at the depot, visits every customer exactly once, and returns to the depot. Travel is allowed between every pair of distinct nodes. Each customer has a service time and a time window within which service must begin. The objective is to minimize total travel time.

## Sets and Indices

- $N$: set of all nodes, including the depot and all customers
- $C$: set of customers, i.e., $C = N \setminus \{Depot}$
- $A$: set of directed arcs $(i,j)$ for all $i,j \in N$ with $i \ne j$

For this instance:

- $N = {Depot, C1, C2, C3, C4, C5, C6, C7, C8, C9, C10, C11, C12, C13}$
- $C = {C1, C2, C3, C4, C5, C6, C7, C8, C9, C10, C11, C12, C13}$

## Parameters

- $c_{i,j}$: travel time from node $i$ to node $j$
- $s_i$: service time at node $i$
- $a_i$: earliest allowable service-start time at node $i$
- $b_i$: latest allowable service-start time at node $i$
- $M$: sufficiently large constant used in time-propagation constraints

For this instance, the recommended big-$M$ value is:

- $M = 2066.76$

## Decision Variables

- $x_{i,j} \in \{0,1\}$: equals 1 if the vehicle directly travels from node $i$ to node $j$
- $t_i \ge 0$: service-start time at node $i$

## Objective Function

Minimize total travel time:

\[
\min \; \sum_{i \in N} \sum_{j \in N: j \ne i} c_{i,j} x_{i,j}
\]

## Constraints

### 1. Outgoing-degree constraints

Exactly one outgoing arc must leave every node:

\[
\sum_{j \in N: j \ne i} x_{i,j} = 1 \qquad \forall i \in N
\]

### 2. Incoming-degree constraints

Exactly one incoming arc must enter every node:

\[
\sum_{i \in N: i \ne j} x_{i,j} = 1 \qquad \forall j \in N
\]

### 3. Time-propagation constraints

If arc $(i,j)$ is used, then service at node $j$ cannot begin before travel from $i$ to $j$ is completed after service at $i$:

\[
t_j \ge t_i + s_i + c_{i,j} - M(1 - x_{i,j})
\qquad \forall i,j \in N,\; i \ne j
\]

### 4. Time-window constraints

Service at each node must begin within its time window:

\[
a_i \le t_i \le b_i \qquad \forall i \in N
\]

### 5. Variable domains

\[
x_{i,j} \in \{0,1\} \qquad \forall (i,j) \in A
\]

\[
t_i \ge 0 \qquad \forall i \in N
\]

## Complete Model

\[
\begin{aligned}
\min \quad & \sum_{i \in N} \sum_{j \in N: j \ne i} c_{i,j} x_{i,j} \\
\text{s.t.} \quad
& \sum_{j \in N: j \ne i} x_{i,j} = 1 && \forall i \in N, \\
& \sum_{i \in N: i \ne j} x_{i,j} = 1 && \forall j \in N, \\
& t_j \ge t_i + s_i + c_{i,j} - M(1 - x_{i,j}) && \forall i,j \in N,\; i \ne j, \\
& a_i \le t_i \le b_i && \forall i \in N, \\
& x_{i,j} \in \{0,1\} && \forall (i,j) \in A, \\
& t_i \ge 0 && \forall i \in N.
\end{aligned}
\]

## Instance-Specific Notes

This instance uses the official medium-level TSPTW multimodal visual format. The figure contains one depot and one colored marker per customer on a Cartesian coordinate grid. Coordinates are printed next to each node, and each node also has a compact label showing its exact time window and service time. A cost-rule box states that travel times equal Euclidean distances between plotted coordinates rounded to 2 decimals. The complete graph edges are intentionally omitted to avoid clutter, but travel between every pair of distinct nodes is allowed. All instance-specific data needed to solve the instance are fully recorded in `canonical_specification.txt` and `instance_data.json`.
