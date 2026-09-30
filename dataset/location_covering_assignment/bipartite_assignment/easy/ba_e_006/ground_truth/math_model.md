# Mathematical Model: Bipartite Assignment / Matching

## Problem Overview

This instance is a single-period bipartite assignment problem defined on a driver–route compatibility graph.

A set of drivers must be assigned to delivery routes subject to compatibility constraints. Each driver must be assigned to exactly one feasible route, and each route must receive exactly one driver.

The objective is to minimize the total assignment cost over all feasible driver–route pairs.

## Sets and Indices

- $D$: set of drivers
- $R$: set of delivery routes

For this instance:

- $D = {D1, D2, D3, D4, D5, D6, D7, D8, D9, D10}$
- $R = {R1, R2, R3, R4, R5, R6, R7, R8, R9, R10}$

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

### 1. Driver assignment

Each driver must be assigned to exactly one route:

\[
\sum_{r \in R} x_{dr} = 1
\qquad \forall d \in D
\]

### 2. Route coverage

Each route must receive exactly one driver:

\[
\sum_{d \in D} x_{dr} = 1
\qquad \forall r \in R
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
& \sum_{r \in R} x_{dr} = 1 && \forall d \in D, \\
& \sum_{d \in D} x_{dr} = 1 && \forall r \in R, \\
& x_{dr} \le a_{dr} && \forall d \in D,\; r \in R, \\
& x_{dr} \in \{0,1\} && \forall d \in D,\; r \in R.
\end{aligned}
\]

## Instance-Specific Notes

This is a balanced assignment instance, so both sides of the bipartite graph must be matched exactly once. Feasible assignments are determined by the compatibility structure encoded in `instance_data.json` and reflected in the instance visual.
Entries shown as forbidden in the visual cost matrix correspond to pairs with $a_{dr}=0$ and therefore cannot be selected.
