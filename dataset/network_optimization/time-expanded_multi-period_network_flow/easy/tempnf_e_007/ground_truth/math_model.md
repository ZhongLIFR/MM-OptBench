# Mathematical Model: Single-Commodity Multi-Period Network Flow with Storage

## Problem Overview

Route a single commodity through a directed network over multiple time
periods. Arc capacities and arc costs may vary by period. Selected
storage-enabled nodes may hold end-of-period inventory and carry it into
the next period, subject to storage-capacity limits and holding costs.

## Sets and Indices

- $\mathcal{N}$: set of nodes, indexed by $i \in \mathcal{N}$
- $\mathcal{A}$: set of directed arcs, indexed by $(i,j) \in \mathcal{A}$
- $\mathcal{T}$: ordered set of periods, indexed by $t \in \mathcal{T}$
- $\mathcal{W} \subseteq \mathcal{N}$: set of storage-enabled nodes

## Parameters

- $b_{it}$: net balance at node $i$ in period $t$
  - $b_{it} > 0$ means net supply
  - $b_{it} < 0$ means net demand
- $u_{ijt}$: capacity of arc $(i,j)$ in period $t$
- $c_{ijt}$: unit routing cost on arc $(i,j)$ in period $t$
- $S_i$: storage capacity at storage-enabled node $i \in \mathcal{W}$
- $h_{it}$: holding cost for one unit of end-of-period inventory at
  storage-enabled node $i$ in period $t$
- $I_i^0$: initial inventory at storage-enabled node $i$

## Decision Variables

- $x_{ijt} \ge 0$: flow sent on arc $(i,j)$ in period $t$
- $I_{it} \ge 0$: end-of-period inventory at storage-enabled node
  $i \in \mathcal{W}$ in period $t$

## Objective Function

\[
\min \;
\sum_{(i,j)\in\mathcal{A}} \sum_{t\in\mathcal{T}} c_{ijt} x_{ijt}
+ \sum_{i\in\mathcal{W}} \sum_{t\in\mathcal{T}} h_{it} I_{it}.
\]

## Constraints

**Node-period balance for storage-enabled nodes**

For each $i \in \mathcal{W}$ and each period $t$:

\[
\sum_{j:(i,j)\in\mathcal{A}} x_{ijt}
- \sum_{j:(j,i)\in\mathcal{A}} x_{jit}
+ I_{it} - I_{i,t-1} = b_{it},
\]

with $I_{i,0} = I_i^0$.

**Node-period balance for non-storage nodes**

For each $i \in \mathcal{N} \setminus \mathcal{W}$ and each
period $t$:

\[
\sum_{j:(i,j)\in\mathcal{A}} x_{ijt}
- \sum_{j:(j,i)\in\mathcal{A}} x_{jit} = b_{it}.
\]

**Arc-capacity constraints**

\[
0 \le x_{ijt} \le u_{ijt},
\quad \forall (i,j)\in\mathcal{A}, \; \forall t\in\mathcal{T}.
\]

**Storage-capacity constraints**

\[
0 \le I_{it} \le S_i,
\quad \forall i\in\mathcal{W}, \; \forall t\in\mathcal{T}.
\]

## Complete Model

\[
\begin{aligned}
\min \quad
& \sum_{(i,j)\in\mathcal{A}} \sum_{t\in\mathcal{T}} c_{ijt} x_{ijt}
+ \sum_{i\in\mathcal{W}} \sum_{t\in\mathcal{T}} h_{it} I_{it} \\
\text{s.t.} \quad
& \sum_{j:(i,j)\in\mathcal{A}} x_{ijt}
- \sum_{j:(j,i)\in\mathcal{A}} x_{jit}
+ I_{it} - I_{i,t-1} = b_{it},
&& \forall i\in\mathcal{W}, \; \forall t\in\mathcal{T}, \\
& \sum_{j:(i,j)\in\mathcal{A}} x_{ijt}
- \sum_{j:(j,i)\in\mathcal{A}} x_{jit} = b_{it},
&& \forall i\in\mathcal{N}\setminus\mathcal{W}, \; \forall t\in\mathcal{T}, \\
& 0 \le x_{ijt} \le u_{ijt},
&& \forall (i,j)\in\mathcal{A}, \; \forall t\in\mathcal{T}, \\
& 0 \le I_{it} \le S_i,
&& \forall i\in\mathcal{W}, \; \forall t\in\mathcal{T}.
\end{aligned}
\]

## Instance-Specific Notes

- This easy-level instance uses one source node, one sink node, and one
  storage-enabled warehouse node.
- The public visual uses the exact arc-label order
  `[u1/c1|u2/c2|u3/c3|u4/c4]` in the period order `t1,t2,t3,t4`.
- Nodes omitted from the right-side role table have zero net balance in
  every period and no storage capability.
- All exact numeric coefficients, coordinates, and visual-layout data
  are also recorded in `instance_data.json`.
