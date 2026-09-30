# Mathematical Model: Set Packing Problem

## Problem Overview

This instance is a deterministic hard-level Set Packing problem.

A collection of candidate groups is given. Each candidate group has an associated integer value and contains a specified subset of items. The task is to select a subset of candidate groups with maximum total value, subject to the condition that no item appears in more than one selected group.

## Sets and Indices

- $U$: set of items
- $S$: set of candidate groups

For this instance:

- $U = \{A, B, C, D, E, F, G, H, I, J, K, L, M, N, O, P, Q, R, S, T, U, V, W, X\}$
- $S = \{G1, G2, G3, G4, G5, G6, G7, G8, G9, G10, G11, G12, G13, G14, G15, G16, G17, G18, G19, G20, G21, G22, G23, G24, G25, G26, G27, G28, G29, G30\}$

## Parameters

- $a_{i,g} \in \{0,1\}$: equals 1 if item $i \in U$ belongs to candidate group $g \in S$, and 0 otherwise
- $w_g \ge 0$: value of candidate group $g$

For this instance, the candidate groups are defined as follows:

- G1: elements = {H, N, S, W}, value = 21
- G2: elements = {B, G, M, T, X}, value = 20
- G3: elements = {C, E, O, R, V}, value = 22
- G4: elements = {D, F, I, L, P}, value = 17
- G5: elements = {A, J, K, Q, U}, value = 20
- G6: elements = {B, C, J, K, M, R, S, T, V}, value = 16
- G7: elements = {F, K, L, M, Q, W}, value = 15
- G8: elements = {A, E, L, W}, value = 18
- G9: elements = {E, H, K, P, T, W}, value = 16
- G10: elements = {C, F, H, U}, value = 22
- G11: elements = {L, N, O, X}, value = 22
- G12: elements = {A, C, E, F, J, Q, S, W}, value = 13
- G13: elements = {A, B, C, D, H, L, N, P}, value = 13
- G14: elements = {I, V, W, X}, value = 19
- G15: elements = {B, E, H, I, O, Q, T, U, W}, value = 16
- G16: elements = {A, C, E, H, I, K, L, M}, value = 17
- G17: elements = {C, D, F, H, P, Q, R}, value = 19
- G18: elements = {B, I, R, W}, value = 23
- G19: elements = {A, J, L, M, N, Q, R, X}, value = 18
- G20: elements = {A, B, E, F, K, L, P, T, U}, value = 12
- G21: elements = {B, I, M, N, R, S, U, W}, value = 16
- G22: elements = {C, D, E, H, J, N, Q, X}, value = 14
- G23: elements = {D, E, F, H, I, J, M, U, W}, value = 14
- G24: elements = {N, P, R, T, X}, value = 22
- G25: elements = {E, F, H, J, K, M, U}, value = 14
- G26: elements = {A, F, G, I, K, O, S, X}, value = 18
- G27: elements = {A, G, H, I, K, M, S, X}, value = 17
- G28: elements = {K, N, O, T}, value = 18
- G29: elements = {C, F, G, H, L, M, N, P, T}, value = 15
- G30: elements = {B, E, F, K, S}, value = 18

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

