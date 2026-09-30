# Mathematical Model: Set Packing Problem

## Problem Overview

This instance is a deterministic hard-level Set Packing problem.

A collection of candidate groups is given. Each candidate group has an associated integer value and contains a specified subset of items. The task is to select a subset of candidate groups with maximum total value, subject to the condition that no item appears in more than one selected group.

## Sets and Indices

- $U$: set of items
- $S$: set of candidate groups

For this instance:

- $U = \{A, B, C, D, E, F, G, H, I, J, K, L, M, N, O, P, Q, R, S, T\}$
- $S = \{G1, G2, G3, G4, G5, G6, G7, G8, G9, G10, G11, G12, G13, G14, G15, G16, G17, G18, G19, G20, G21, G22, G23, G24, G25, G26\}$

## Parameters

- $a_{i,g} \in \{0,1\}$: equals 1 if item $i \in U$ belongs to candidate group $g \in S$, and 0 otherwise
- $w_g \ge 0$: value of candidate group $g$

For this instance, the candidate groups are defined as follows:

- G1: elements = {H, I, L, P, S}, value = 22
- G2: elements = {B, G, N, O, T}, value = 22
- G3: elements = {C, E, J, K, R}, value = 22
- G4: elements = {A, D, F, M, Q}, value = 18
- G5: elements = {C, E, H, J, L, N, R, T}, value = 18
- G6: elements = {A, B, C, G, J, K, L, N, S}, value = 16
- G7: elements = {C, E, F, I, M}, value = 22
- G8: elements = {C, E, I, J, K, M, S}, value = 17
- G9: elements = {A, B, D, E, G, L, P}, value = 18
- G10: elements = {C, H, I, K, M, Q, T}, value = 17
- G11: elements = {A, D, E, F, J, K, M, Q, S}, value = 12
- G12: elements = {C, H, K, M, P}, value = 16
- G13: elements = {A, D, E, J, K, L, P, Q}, value = 19
- G14: elements = {C, E, G, I, L, N}, value = 18
- G15: elements = {B, E, F, P}, value = 18
- G16: elements = {G, J, M, P, Q}, value = 22
- G17: elements = {H, Q, R, T}, value = 23
- G18: elements = {A, B, G, H, J, P, T}, value = 16
- G19: elements = {C, E, H, I, M, N, P, Q}, value = 19
- G20: elements = {C, G, H, J, N, R, S}, value = 16
- G21: elements = {D, I, O, R}, value = 22
- G22: elements = {F, H, J, Q}, value = 19
- G23: elements = {B, D, F, G, N, P, R}, value = 15
- G24: elements = {C, E, F, G, I, K, M, O, T}, value = 18
- G25: elements = {C, D, E, F, H, J, M, R}, value = 16
- G26: elements = {A, I, K, T}, value = 18

## Decision Variables

- $x_g \in \{0,1\}$: equals 1 if candidate group $g$ is selected, and 0 otherwise

## Objective Function

Maximize the total value of the selected groups:

\[
\max \; \sum_{g \in S} w_g x_g
\]

## Constraints

### 1. Item-packing constraints

For every item $i \in U$:

\[
\sum_{g \in S} a_{i,g} x_g \le 1
\]

### 2. Binary domains

\[
x_g \in \{0,1\} \qquad \forall g \in S
\]

## Complete Model

\[
\begin{aligned}
\max \quad & \sum_{g \in S} w_g x_g \\
\text{s.t.} \quad
& \sum_{g \in S} a_{i,g} x_g \le 1 && \forall i \in U, \\
& x_g \in \{0,1\} && \forall g \in S.
\end{aligned}
\]

## Instance-Specific Notes

This instance uses the official hard-level incidence-matrix visual format for Set Packing. The figure contains one row per candidate group, one column per item, filled cells for membership, and value bars with adjacent integers for group values. All instance-specific structural and numerical data are fully recorded in `instance_data.json` and `canonical_specification.txt`, and are visually encoded in `visual_0.png` without revealing which groups are selected in an optimal solution.

