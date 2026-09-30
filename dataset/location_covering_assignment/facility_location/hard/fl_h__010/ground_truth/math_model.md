# Mathematical Model: Facility Location (CFL)

## Problem Overview

This is a single-period deterministic facility location instance.

## Sets and Indices

- $F$: set of candidate facilities
- $C$: set of customers

For this instance:

- $F = {F1, F2, F3, F4, F5, F6, F7, F8, F9}$
- $C = {C1, C2, C3, C4, C5, C6, C7, C8, C9, C10, C11, C12, C13, C14, C15, C16, C17, C18}$

## Parameters

- $f_f$: opening cost of facility $f \in F$
- $d_c$: demand of customer $c \in C$
- $c_{cf}$: assignment cost per unit demand from facility $f$ to customer $c$
- $a_{cf} \in \{0,1\}$: assignment-feasibility indicator
- $u_f$: facility capacity


## Decision Variables

- $y_f \in \{0,1\}$: 1 if facility $f$ is opened
- $x_{cf} \in \{0,1\}$: 1 if customer $c$ is assigned to facility $f$

## Objective Function

\[
\min \sum_{f \in F} f_f y_f + \sum_{c \in C}\sum_{f \in F} d_c c_{cf} x_{cf}
\]

## Constraints

### 1. Customer assignment

\[
\sum_{f \in F} x_{cf} = 1
\qquad \forall c \in C
\]

### 2. Open-facility linking

\[
x_{cf} \le y_f
\qquad \forall c \in C,\; f \in F
\]

### 3. Assignment feasibility

\[
x_{cf} \le a_{cf}
\qquad \forall c \in C,\; f \in F
\]

### 3A. Facility capacities

\[
\sum_{c \in C} d_c x_{cf} \le u_f y_f
\qquad \forall f \in F
\]



### 4. Variable domains

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
& \sum_{f \in F} f_f y_f + \sum_{c \in C}\sum_{f \in F} d_c c_{cf} x_{cf} \\
\text{s.t.} \quad
& \sum_{f \in F} x_{cf} = 1 && \forall c \in C, \\
& x_{cf} \le y_f && \forall c \in C,\; f \in F, \\
& x_{cf} \le a_{cf} && \forall c \in C,\; f \in F, \\
& \sum_{c \in C} d_c x_{cf} \le u_f y_f && \forall f \in F, \\
& y_f \in \{0,1\} && \forall f \in F, \\
& x_{cf} \in \{0,1\} && \forall c \in C,\; f \in F.
\end{aligned}
\]
