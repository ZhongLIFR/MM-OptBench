# Mathematical Model: Set Covering / Set Partitioning

## Problem Overview

This instance is a single-period binary subset-selection model.
A collection of candidate subsets is available, each with a fixed cost.
The model chooses a cost-minimizing selection of subsets subject to
element-incidence constraints.

For this instance, the active variant is `set_covering`.

## Sets and Indices

- `E`: set of elements
- `S`: set of candidate subsets

For this instance:

- `E = {E1, E2, E3, E4, E5, E6, E7, E8, E9}`
- `S = {S1, S2, S3, S4, S5, S6, S7, S8}`

## Parameters

- `c_s`: cost of candidate subset `s in S`
- `a_es in {0,1}`: incidence indicator, where `a_es = 1` if element `e in E`
  belongs to candidate subset `s in S`

## Decision Variables

- `x_s in {0,1}`: equals 1 if candidate subset `s` is selected

## Objective Function

\[
\min \sum_{s \in S} c_s x_s
\]

## Constraints

### 1. Element Coverage

Every element must be covered by at least one selected subset:

\[
\sum_{s \in S} a_{es} x_s \ge 1
\qquad \forall e \in E
\]

### 2. Variable Domains

\[
x_s \in \{0,1\}
\qquad \forall s \in S
\]

## Complete Model

\[
\begin{aligned}
\min \quad
& \sum_{s \in S} c_s x_s \\
\text{s.t.} \quad
& \sum_{s \in S} a_{es} x_s \ge 1 && \forall e \in E, \\
& x_s \in \{0,1\} && \forall s \in S.
\end{aligned}
\]

## Instance-Specific Notes

This easy-level instance uses the classical set covering semantics. The visual is a single exact incidence table, and the modeling task is driven by the trade-off between cheaper local subsets and more expensive but broader alternatives.
The reference implementation uses exactly the subset costs and
incidence data shown in the visual and recorded in `instance_data.json`.
