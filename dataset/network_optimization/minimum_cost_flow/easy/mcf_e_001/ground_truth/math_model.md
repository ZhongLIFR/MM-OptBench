# Mathematical Model: Single-Commodity Minimum-Cost Flow

## Problem Overview
Given a directed network with node supplies/demands and arc capacities/costs, route flow to satisfy all demands while minimizing total transportation cost.

## Mathematical Formulation

### 1. Sets and Indices
- $\mathcal{N}$: set of nodes, indexed by $i \in \mathcal{N}$
- $\mathcal{A}$: set of directed arcs, $\mathcal{A} \subseteq \mathcal{N}\times\mathcal{N}$, indexed by $(i,j)\in\mathcal{A}$

### 2. Decision Variables
- $x_{ij} \ge 0$: amount of flow sent on arc $(i,j)\in\mathcal{A}$

### 3. Parameters
- $b_i$: supply/demand at node $i$ (positive for supply, negative for demand), $\sum_{i\in\mathcal{N}} b_i = 0$
- $u_{ij} > 0$: capacity of arc $(i,j)\in\mathcal{A}$
- $c_{ij} \ge 0$: unit cost of sending flow on arc $(i,j)\in\mathcal{A}$

### 4. Objective Function
\[
\min \;\; \sum_{(i,j)\in\mathcal{A}} c_{ij}\, x_{ij}.
\]

### 5. Constraints

**5.1 Flow Conservation**
\[
\sum_{j:(i,j)\in\mathcal{A}} x_{ij} - \sum_{j:(j,i)\in\mathcal{A}} x_{ji} = b_i,
\quad \forall i\in\mathcal{N}.
\]

**5.2 Capacity Constraints**
\[
0 \le x_{ij} \le u_{ij}, \quad \forall (i,j)\in\mathcal{A}.
\]

### 6. Complete Model
\[
\begin{aligned}
\min \quad & \sum_{(i,j)\in\mathcal{A}} c_{ij} x_{ij} \\
\text{s.t.}\quad
& \sum_{j:(i,j)\in\mathcal{A}} x_{ij} - \sum_{j:(j,i)\in\mathcal{A}} x_{ji} = b_i && \forall i\in\mathcal{N}, \\
& 0 \le x_{ij} \le u_{ij} && \forall (i,j)\in\mathcal{A}.
\end{aligned}
\]

## Instance-Specific Note
All numeric values are recorded in `instance_data.json`.
