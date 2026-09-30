# Mathematical Model: Facility Location (CFL)

## Problem Overview

This instance is a single-period capacitated facility location problem with coverage-based assignment feasibility.

A subset of candidate facilities must be opened, and every customer must be assigned to exactly one opened facility that covers it. Each opened facility has a limited capacity. The objective minimizes the total facility opening cost and the demand-weighted assignment cost.

## Sets and Indices

- $F$: set of candidate facilities
- $C$: set of customers

For this instance:

- $F = {F1, F2, F3, F4}$
- $C = {C1, C2, C3, C4, C5, C6}$

## Parameters

- $f_f$: opening cost of facility $f \in F$
- $u_f$: capacity of facility $f \in F$
- $d_c$: demand of customer $c \in C$
- $r_f$: coverage radius of facility $f \in F$
- $c_{cf}$: assignment cost per unit demand from facility $f$ to customer $c$
- $a_{cf} \in \{0,1\}$: coverage feasibility indicator, where $a_{cf} = 1$ if customer $c$ is inside the coverage region of facility $f$

## Decision Variables

- $y_f \in \{0,1\}$: equals 1 if facility $f$ is opened
- $x_{cf} \in \{0,1\}$: equals 1 if customer $c$ is assigned to facility $f$

## Objective Function

\[
\min \sum_{f \in F} f_f y_f + \sum_{c \in C} \sum_{f \in F} d_c c_{cf} x_{cf}
\]

## Constraints

### 1. Customer assignment

Each customer must be assigned to exactly one facility:

\[
\sum_{f \in F} x_{cf} = 1
\qquad \forall c \in C
\]

### 2. Open-facility linking

A customer can only be assigned to a facility if that facility is opened:

\[
x_{cf} \le y_f
\qquad \forall c \in C,\; f \in F
\]

### 3. Coverage feasibility

Assignments are only allowed when the customer lies within the facility's coverage radius:

\[
x_{cf} \le a_{cf}
\qquad \forall c \in C,\; f \in F
\]

### 4. Facility capacities

Total assigned demand cannot exceed facility capacity:

\[
\sum_{c \in C} d_c x_{cf} \le u_f y_f
\qquad \forall f \in F
\]

### 5. Variable domains

\[
y_f \in \{0,1\}
\qquad \forall f \in F
\]

\[
x_{cf} \in \{0,1\}
\qquad \forall c \in C,\; f \in F
\]

## Complete Model

\[
\begin{aligned}
\min \quad
& \sum_{f \in F} f_f y_f + \sum_{c \in C} \sum_{f \in F} d_c c_{cf} x_{cf} \\
\text{s.t.} \quad
& \sum_{f \in F} x_{cf} = 1 && \forall c \in C, \\
& x_{cf} \le y_f && \forall c \in C,\; f \in F, \\
& x_{cf} \le a_{cf} && \forall c \in C,\; f \in F, \\
& \sum_{c \in C} d_c x_{cf} \le u_f y_f && \forall f \in F, \\
& y_f \in \{0,1\} && \forall f \in F, \\
& x_{cf} \in \{0,1\} && \forall c \in C,\; f \in F.
\end{aligned}
\]

## Instance-Specific Notes

This is a CFL instance, so facility capacities actively restrict assignments. Feasible assignments are determined by the coverage geometry encoded in `instance_data.json` and reflected in the instance visual.
