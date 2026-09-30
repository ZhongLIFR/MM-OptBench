# Mathematical Model: Lot-Sizing and Production Planning

## Problem Overview

This instance is a deterministic multi-period lot-sizing and production planning problem.

One or more products must be produced over a finite planning horizon. Production can be carried as inventory from one period to the next. Demand must be met on time without backlogging. Producing a product in a period incurs a linear variable production cost and, whenever production is positive, a fixed setup cost. Carrying end-of-period inventory incurs a holding cost.

This instance includes a shared period-capacity constraint.

## Sets and Indices

- $P$: set of products
- $T$: set of time periods

For this instance:

- $P = {P1, P2, P3}$
- $T = {t1, t2, t3, t4, t5, t6, t7, t8}$

## Parameters

- $d_{p,t}$: demand of product $p$ in period $t$
- $c_{p,t}$: unit production cost of product $p$ in period $t$
- $h_{p,t}$: unit holding cost for carrying one unit of product $p$ after period $t$
- $f_{p,t}$: fixed setup cost if product $p$ is produced in period $t$
- $C_t$: shared production capacity in period $t$
- $I^0_p$: initial inventory of product $p$
- $M_p$: setup-linking constant for product $p$

## Decision Variables

- $x_{p,t} \ge 0$: production quantity of product $p$ in period $t$
- $I_{p,t} \ge 0$: ending inventory of product $p$ after period $t$
- $y_{p,t} \in \{0,1\}$: setup indicator equal to 1 if product $p$ is produced in period $t$

## Objective Function

Minimize total production, holding, and setup cost:

\[
\min \; \sum_{p \in P} \sum_{t \in T} \left(c_{p,t} x_{p,t} + h_{p,t} I_{p,t} + f_{p,t} y_{p,t}\right)
\]

## Constraints

### 1. Inventory balance constraints

For the first period of each product:

\[
I^0_p + x_{p,t_1} = d_{p,t_1} + I_{p,t_1} \qquad \forall p \in P
\]

For every subsequent period:

\[
I_{p,t^-} + x_{p,t} = d_{p,t} + I_{p,t} \qquad \forall p \in P,\; t \in T \setminus \{t_1\}
\]

where $t^-$ denotes the period immediately preceding $t$.

### 2. Setup-linking constraints

\[
x_{p,t} \le M_p y_{p,t} \qquad \forall p \in P,\; t \in T
\]

### 3. Shared capacity constraints

\
\[
\sum_{p \in P} x_{p,t} \le C_t \qquad \forall t \in T
\]


### 4. Variable domains

\[
x_{p,t} \ge 0, \qquad I_{p,t} \ge 0, \qquad y_{p,t} \in \{0,1\} \qquad \forall p \in P,\; t \in T
\]

## Complete Model

\[
\begin{aligned}
\min \quad & \sum_{p \in P} \sum_{t \in T} \left(c_{p,t} x_{p,t} + h_{p,t} I_{p,t} + f_{p,t} y_{p,t}\right) \\
\text{s.t.} \quad
& I^0_p + x_{p,t_1} = d_{p,t_1} + I_{p,t_1} && \forall p \in P, \\
& I_{p,t^-} + x_{p,t} = d_{p,t} + I_{p,t} && \forall p \in P,\; t \in T \setminus \{t_1\}, \\
& x_{p,t} \le M_p y_{p,t} && \forall p \in P,\; t \in T,

\sum_{p \in P} x_{p,t} \le C_t && \forall t \in T, \\

& x_{p,t} \ge 0,\; I_{p,t} \ge 0 && \forall p \in P,\; t \in T, \\
& y_{p,t} \in \{0,1\} && \forall p \in P,\; t \in T.
\end{aligned}
\]

## Instance-Specific Notes

This instance uses the official single-image Timeline + Demand Grid visual format for easy-level lot-sizing. The figure contains a capacity timeline plus four aligned parameter blocks: exact demand values, unit production costs, unit holding costs, and fixed setup costs. All instance-specific numerical data needed to solve the instance are provided in the visual and recorded in `instance_data.json`.
