# Mathematical Model: Set Packing Problem

## Problem Overview

This instance is a deterministic medium-level Set Packing problem.

A collection of candidate groups is given. Each candidate group has an associated integer value and contains a specified subset of items. The task is to select a subset of candidate groups with maximum total value, subject to the condition that no item appears in more than one selected group.

## Sets and Indices

- $U$: set of items
- $S$: set of candidate groups

For this instance:

- $U = \{A, B, C, D, E, F, G, H, I, J, K, L, M, N, O, P, Q, R\}$
- $S = \{G1, G2, G3, G4, G5, G6, G7, G8, G9, G10, G11, G12, G13, G14, G15, G16, G17, G18, G19, G20, G21, G22, G23, G24\}$

## Parameters

- $a_{i,g} \in \{0,1\}$: equals 1 if item $i \in U$ belongs to candidate group $g \in S$, and 0 otherwise
- $w_g \ge 0$: value of candidate group $g$

For this instance, the candidate groups are defined as follows:

- G1: elements = {B, D, O}, value = 14
- G2: elements = {C, G, N}, value = 16
- G3: elements = {H, J, K, P}, value = 15
- G4: elements = {E, F, L, Q}, value = 16
- G5: elements = {A, I, M, R}, value = 13
- G6: elements = {G, P, Q}, value = 13
- G7: elements = {D, K, L, M, P, R}, value = 12
- G8: elements = {E, N, O}, value = 17
- G9: elements = {I, J, K, N, Q}, value = 12
- G10: elements = {A, E, F, H, K, M, P, R}, value = 8
- G11: elements = {C, J, Q, R}, value = 12
- G12: elements = {C, F, L, P}, value = 14
- G13: elements = {F, G, J, L, N, R}, value = 13
- G14: elements = {C, D, K}, value = 16
- G15: elements = {G, H, O}, value = 13
- G16: elements = {D, F, P}, value = 15
- G17: elements = {J, M, Q, R}, value = 12
- G18: elements = {A, B, H, Q}, value = 12
- G19: elements = {B, C, D, F, G, H, K, O}, value = 8
- G20: elements = {B, C, J, L, O, P}, value = 14
- G21: elements = {A, E, F, G, H, K, N}, value = 10
- G22: elements = {B, G, H}, value = 13
- G23: elements = {G, H, R}, value = 15
- G24: elements = {A, F, H, K, L, Q}, value = 13

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

This instance uses the official medium-level incidence-matrix visual format for Set Packing. The figure contains one row per candidate group, one column per item, filled cells for membership, and value bars with adjacent integers for group values. All instance-specific structural and numerical data are fully recorded in `instance_data.json` and `canonical_specification.txt`, and are visually encoded in `visual_0.png` without revealing which groups are selected in an optimal solution.

