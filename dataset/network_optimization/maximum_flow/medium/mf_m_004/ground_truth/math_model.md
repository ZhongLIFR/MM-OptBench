# Mathematical Model: Maximum Flow / Minimum Cut (s-t)

## Problem Overview
Given a directed network with nonnegative arc capacities, send as much flow as possible from a designated **source** node $s$ to a designated **sink** node $t$.  
This instance also provides the equivalent minimum-cut interpretation.

## Mathematical Formulation

### Sets and Indices
- $\mathcal{V}$: set of nodes
- $\mathcal{A}$: set of directed arcs
- $s$: source node
- $t$: sink node

### Decision Variables
- $f_{ij} \ge 0$: flow on arc $(i,j) \in \mathcal{A}$

### Parameters
- $u_{ij}$: capacity of arc $(i,j)$

### Objective (Maximum Flow)
\[
\max \sum_{(s,j)\in\mathcal{A}} f_{sj}
\]

### Constraints

**Flow conservation (for all $v \neq s,t$):**
\[
\sum_{(i,v)\in\mathcal{A}} f_{iv} - \sum_{(v,k)\in\mathcal{A}} f_{vk} = 0
\]

**Capacity bounds:**
\[
0 \le f_{ij} \le u_{ij}, \quad \forall (i,j)\in\mathcal{A}
\]

## Equivalent Minimum-Cut Formulation

Introduce binary variables $x_i \in \{0,1\}$ with
\[
x_s = 1, \quad x_t = 0.
\]

\[
\min \sum_{(i,j)\in\mathcal{A}} u_{ij} y_{ij}
\]

subject to
\[
y_{ij} \ge x_i - x_j, \quad y_{ij} \in \{0,1\}.
\]

## Reference Optimal Value

Verified optimal maximum flow value: **14.0**  
Verified minimum cut value: **14.0**

## One Verified Minimum Cut

$S = \{1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11\}$  
$T = \{12, 13\}$
