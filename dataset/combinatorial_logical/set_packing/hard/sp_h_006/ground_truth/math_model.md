# Mathematical Model: Set Packing Problem

## Problem Overview

This instance is a deterministic hard-level Set Packing problem.

A collection of candidate groups is given. Each candidate group has an associated integer value and contains a specified subset of items. The task is to select a subset of candidate groups with maximum total value, subject to the condition that no item appears in more than one selected group.

## Sets and Indices

- $U$: set of items
- $S$: set of candidate groups

For this instance:

- $U = \{A, B, C, D, E, F, G, H, I, J, K, L, M, N, O, P, Q, R, S, T, U, V, W\}$
- $S = \{G1, G2, G3, G4, G5, G6, G7, G8, G9, G10, G11, G12, G13, G14, G15, G16, G17, G18, G19, G20, G21, G22, G23, G24, G25, G26, G27, G28, G29\}$

## Parameters

- $a_{i,g} \in \{0,1\}$: equals 1 if item $i \in U$ belongs to candidate group $g \in S$, and 0 otherwise
- $w_g \ge 0$: value of candidate group $g$

For this instance, the candidate groups are defined as follows:

- G1: elements = {B, K, Q, V}, value = 20
- G2: elements = {C, D, T, W}, value = 20
- G3: elements = {A, F, H, L, N}, value = 19
- G4: elements = {I, M, P, S, U}, value = 22
- G5: elements = {E, G, J, O, R}, value = 21
- G6: elements = {A, C, G, J, K, O, P}, value = 26
- G7: elements = {E, F, J, K, M, W}, value = 17
- G8: elements = {F, K, R, S, W}, value = 22
- G9: elements = {C, E, H, K, T, U}, value = 21
- G10: elements = {F, G, H, K, L, O, Q, R, V}, value = 23
- G11: elements = {L, M, Q, T}, value = 21
- G12: elements = {A, C, D, E, F, H, L, O, W}, value = 30
- G13: elements = {A, B, E, F, G, O, Q}, value = 24
- G14: elements = {B, C, D, I, K, O, U, V}, value = 28
- G15: elements = {H, P, V, W}, value = 14
- G16: elements = {A, F, H, K, M, N, S, U, V}, value = 30
- G17: elements = {A, B, F, K, L, N, Q, T, V}, value = 29
- G18: elements = {F, M, V, W}, value = 21
- G19: elements = {C, I, R, U, W}, value = 19
- G20: elements = {A, M, P, Q}, value = 15
- G21: elements = {C, P, R, T, W}, value = 18
- G22: elements = {A, C, D, E, Q}, value = 17
- G23: elements = {B, F, I, J, K, V}, value = 19
- G24: elements = {C, D, E, R, U}, value = 17
- G25: elements = {C, K, M, Q, S, U, V, W}, value = 27
- G26: elements = {D, F, Q, T}, value = 19
- G27: elements = {A, F, K, P}, value = 19
- G28: elements = {A, D, H, J, M, N, T, U}, value = 25
- G29: elements = {D, H, S, V}, value = 13

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

