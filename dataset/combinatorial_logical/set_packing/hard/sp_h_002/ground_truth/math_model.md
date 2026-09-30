# Mathematical Model: Set Packing Problem

## Problem Overview

This instance is a deterministic hard-level Set Packing problem.

A collection of candidate groups is given. Each candidate group has an associated integer value and contains a specified subset of items. The task is to select a subset of candidate groups with maximum total value, subject to the condition that no item appears in more than one selected group.

## Sets and Indices

- $U$: set of items
- $S$: set of candidate groups

For this instance:

- $U = \{A, B, C, D, E, F, G, H, I, J, K, L, M, N, O, P, Q, R, S\}$
- $S = \{G1, G2, G3, G4, G5, G6, G7, G8, G9, G10, G11, G12, G13, G14, G15, G16, G17, G18, G19, G20, G21, G22, G23, G24\}$

## Parameters

- $a_{i,g} \in \{0,1\}$: equals 1 if item $i \in U$ belongs to candidate group $g \in S$, and 0 otherwise
- $w_g \ge 0$: value of candidate group $g$

For this instance, the candidate groups are defined as follows:

- G1: elements = {C, O, Q, R}, value = 16
- G2: elements = {D, F, H, J, N}, value = 19
- G3: elements = {E, G, I, M, S}, value = 19
- G4: elements = {A, B, K, L, P}, value = 23
- G5: elements = {D, E, I, J, K, N, P}, value = 23
- G6: elements = {C, H, J, L, N, Q}, value = 17
- G7: elements = {A, B, H, J, N, P, R}, value = 23
- G8: elements = {A, E, G, N, P, S}, value = 20
- G9: elements = {A, B, C, F, H, L, R}, value = 19
- G10: elements = {A, B, D, F, H, K, O, Q}, value = 27
- G11: elements = {F, G, H, M, O, Q}, value = 19
- G12: elements = {E, G, K, L, M, P}, value = 23
- G13: elements = {A, D, F, G, H, K, S}, value = 20
- G14: elements = {B, E, L, N, Q}, value = 17
- G15: elements = {D, E, F, G, H, J, M, N, S}, value = 30
- G16: elements = {D, E, F, G, H, I, J, M, S}, value = 31
- G17: elements = {G, I, L, P}, value = 16
- G18: elements = {B, I, J, N, P}, value = 23
- G19: elements = {B, I, Q, S}, value = 17
- G20: elements = {E, H, K, L}, value = 14
- G21: elements = {A, C, F, H, O, S}, value = 24
- G22: elements = {B, D, E, G, I, J, L, R}, value = 25
- G23: elements = {C, E, F, I, N, Q, R}, value = 19
- G24: elements = {A, C, G, N, Q}, value = 18

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

