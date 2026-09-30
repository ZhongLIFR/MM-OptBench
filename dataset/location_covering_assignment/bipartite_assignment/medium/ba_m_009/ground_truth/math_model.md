# Mathematical Model: Bipartite Assignment / Matching

## Problem Overview

This instance is a single-period bipartite matching problem defined through a driver–route compatibility matrix.

Every route must be covered by exactly one feasible driver, while each driver can take at most one route. The instance is therefore an unbalanced minimum-cost matching model.

The objective is to minimize the total assignment cost over all feasible driver–route pairs.

## Sets and Indices

- $D$: set of drivers
- $R$: set of delivery routes

For this instance:

- $D = {D1, D2, D3, D4, D5, D6, D7, D8, D9, D10, D11, D12, D13, D14, D15, D16, D17, D18, D19, D20, D21, D22, D23, D24, D25, D26, D27}$
- $R = {R1, R2, R3, R4, R5, R6, R7, R8, R9, R10, R11, R12, R13, R14, R15, R16, R17, R18, R19, R20, R21, R22}$

## Parameters

- $c_{dr}$: assignment cost of assigning driver $d \in D$ to route $r \in R$
- $a_{dr} \in \{0,1\}$: compatibility indicator, where $a_{dr} = 1$ if driver $d$ can be assigned to route $r$

## Decision Variables

- $x_{dr} \in \{0,1\}$: equals 1 if driver $d$ is assigned to route $r$

## Objective Function

\[
\min \sum_{d \in D} \sum_{r \in R} c_{dr} x_{dr}
\]

## Constraints

### 1. Route coverage

Each route must receive exactly one driver:

\[
\sum_{d \in D} x_{dr} = 1
\qquad \forall r \in R
\]

### 2. Driver usage

Each driver can take at most one route:

\[
\sum_{r \in R} x_{dr} \le 1
\qquad \forall d \in D
\]

### 3. Compatibility feasibility

Assignments are only allowed on compatible driver–route pairs:

\[
x_{dr} \le a_{dr}
\qquad \forall d \in D,\; r \in R
\]

### 4. Variable domains

\[
x_{dr} \in \{0,1\}
\qquad \forall d \in D,\; r \in R
\]

## Complete Model

\[
\begin{aligned}
\min \quad
& \sum_{d \in D} \sum_{r \in R} c_{dr} x_{dr} \\
\text{s.t.} \quad
& \sum_{d \in D} x_{dr} = 1 && \forall r \in R, \\
& \sum_{r \in R} x_{dr} \le 1 && \forall d \in D, \\
& x_{dr} \le a_{dr} && \forall d \in D,\; r \in R, \\
& x_{dr} \in \{0,1\} && \forall d \in D,\; r \in R.
\end{aligned}
\]

## Instance-Specific Notes

This is an unbalanced matching instance in which all routes must be covered. Feasible assignments are determined by the compatibility structure encoded in `instance_data.json` and reflected in the instance table visual.
Entries shown as forbidden in the table visual correspond to pairs with $a_{dr}=0$ and therefore cannot be selected.
