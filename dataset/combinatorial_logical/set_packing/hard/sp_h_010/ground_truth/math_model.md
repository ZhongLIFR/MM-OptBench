# Mathematical Model: Set Packing Problem

## Problem Overview

This instance is a deterministic hard-level Set Packing problem.

A collection of candidate groups is given. Each candidate group has an associated integer value and contains a specified subset of items. The task is to select a subset of candidate groups with maximum total value, subject to the condition that no item appears in more than one selected group.

## Sets and Indices

- $U$: set of items
- $S$: set of candidate groups

For this instance:

- $U = \{A, B, C, D, E, F, G, H, I, J, K, L, M, N, O, P, Q, R, S, T, U, V, W, X, Y, Z\}$
- $S = \{G1, G2, G3, G4, G5, G6, G7, G8, G9, G10, G11, G12, G13, G14, G15, G16, G17, G18, G19, G20, G21, G22, G23, G24, G25, G26, G27, G28, G29, G30, G31, G32, G33, G34\}$

## Parameters

- $a_{i,g} \in \{0,1\}$: equals 1 if item $i \in U$ belongs to candidate group $g \in S$, and 0 otherwise
- $w_g \ge 0$: value of candidate group $g$

For this instance, the candidate groups are defined as follows:

- G1: elements = {K, S, U, W, Y}, value = 23
- G2: elements = {J, N, P, Q, R}, value = 18
- G3: elements = {D, E, I, O, T}, value = 23
- G4: elements = {A, F, G, M, V}, value = 22
- G5: elements = {B, C, H, L, X, Z}, value = 20
- G6: elements = {C, E, L, M, R, Z}, value = 17
- G7: elements = {E, F, H, J, M, P, T, W, Z}, value = 25
- G8: elements = {B, G, I, J, M, R, U, Z}, value = 26
- G9: elements = {F, H, I, U, V, X}, value = 25
- G10: elements = {A, B, E, K, P, T}, value = 22
- G11: elements = {L, O, R, S, U}, value = 18
- G12: elements = {D, G, J, O, Q, R, W}, value = 20
- G13: elements = {F, J, K, N, O, V, Z}, value = 27
- G14: elements = {H, I, N, O, R, S, Z}, value = 19
- G15: elements = {G, J, K, Q, R, W, Z}, value = 23
- G16: elements = {C, G, K, O, T, X, Z}, value = 22
- G17: elements = {A, B, D, F, P, Q, U, Y}, value = 28
- G18: elements = {A, B, E, G, P, V}, value = 24
- G19: elements = {I, M, N, O, S}, value = 21
- G20: elements = {B, E, K, N, P, R, T, Y, Z}, value = 27
- G21: elements = {A, B, J, L, T, W}, value = 23
- G22: elements = {K, M, P, R, Y, Z}, value = 20
- G23: elements = {A, C, E, I, J, K, P, T}, value = 28
- G24: elements = {F, G, J, L, Q, S, Y}, value = 19
- G25: elements = {A, F, I, L, M, N, O, P}, value = 27
- G26: elements = {D, M, N, S}, value = 16
- G27: elements = {D, E, M, O, Q, R, U, W}, value = 24
- G28: elements = {A, D, E, J, K, M, N, V, Z}, value = 30
- G29: elements = {K, R, T, Z}, value = 17
- G30: elements = {G, I, P, U, Z}, value = 21
- G31: elements = {B, G, J, M, Q, U}, value = 25
- G32: elements = {B, E, M, Q, U}, value = 15
- G33: elements = {I, K, N, V}, value = 20
- G34: elements = {A, D, F, H, K, N, P, V, Y}, value = 27

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

