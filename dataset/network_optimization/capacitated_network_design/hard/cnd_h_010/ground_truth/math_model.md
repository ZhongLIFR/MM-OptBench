# Mathematical Model: Single-Commodity Capacitated Network Design

## Problem Overview

Choose which candidate directed arcs to install and how to route the
required shipment from the source node to the sink node. Installing an
arc incurs a fixed cost. Sending flow on an installed arc incurs a
variable cost per unit and may not exceed the arc capacity.

## Sets and Indices

- $\mathcal{N}$: set of nodes, indexed by $i \in \mathcal{N}$
- $\mathcal{A}$: set of candidate directed arcs, indexed by
  $(i,j) \in \mathcal{A}$
- $s$: source node
- $t$: sink node

## Parameters

- $D > 0$: required shipment amount from $s$ to $t$
- $u_{ij} > 0$: capacity of candidate arc $(i,j)$
- $f_{ij} \ge 0$: fixed installation cost of candidate arc $(i,j)$
- $c_{ij} \ge 0$: variable routing cost per unit on candidate arc
  $(i,j)$

## Decision Variables

- $y_{ij} \in \{0,1\}$: equals 1 if candidate arc $(i,j)$ is installed
- $x_{ij} \ge 0$: amount of flow routed on candidate arc $(i,j)$

## Objective Function

\[
\min \;\; \sum_{(i,j)\in\mathcal{A}} f_{ij} y_{ij}
      + \sum_{(i,j)\in\mathcal{A}} c_{ij} x_{ij}.
\]

## Constraints

**Flow conservation**

\[
\sum_{j:(i,j)\in\mathcal{A}} x_{ij} - \sum_{j:(j,i)\in\mathcal{A}} x_{ji}
=
\begin{cases}
D, & i = s, \\
-D, & i = t, \\
0, & \text{otherwise},
\end{cases}
\quad \forall i \in \mathcal{N}.
\]

**Capacity-linking constraints**

\[
0 \le x_{ij} \le u_{ij} y_{ij},
\quad \forall (i,j) \in \mathcal{A}.
\]

**Binary installation decisions**

\[
y_{ij} \in \{0,1\},
\quad \forall (i,j) \in \mathcal{A}.
\]

## Complete Model

\[
\begin{aligned}
\min \quad
& \sum_{(i,j)\in\mathcal{A}} f_{ij} y_{ij}
+ \sum_{(i,j)\in\mathcal{A}} c_{ij} x_{ij} \\
\text{s.t.} \quad
& \sum_{j:(i,j)\in\mathcal{A}} x_{ij} - \sum_{j:(j,i)\in\mathcal{A}} x_{ji}
=
\begin{cases}
D, & i = s, \\
-D, & i = t, \\
0, & \text{otherwise},
\end{cases}
&& \forall i\in\mathcal{N}, \\
& 0 \le x_{ij} \le u_{ij} y_{ij}
&& \forall (i,j)\in\mathcal{A}, \\
& y_{ij} \in \{0,1\}
&& \forall (i,j)\in\mathcal{A}.
\end{aligned}
\]

## Instance-Specific Notes

- In this instance, the source is node 1, the sink is node
  16, and the required shipment amount is 12 units.
- The single released visual uses the exact arc label order
  `[capacity, fixed_cost, variable_cost]`.
- All numeric values, coordinates, and visual-layout overrides are also
  recorded in `instance_data.json`.
