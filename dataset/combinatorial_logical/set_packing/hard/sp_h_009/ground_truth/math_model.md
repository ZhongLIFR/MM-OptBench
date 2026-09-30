# Mathematical Model: Set Packing Problem

## Problem Overview

This instance is a deterministic hard-level Set Packing problem.

A collection of candidate groups is given. Each candidate group has an associated integer value and contains a specified subset of items. The task is to select a subset of candidate groups with maximum total value, subject to the condition that no item appears in more than one selected group.

## Sets and Indices

- $U$: set of items
- $S$: set of candidate groups

For this instance:

- $U = \{A, B, C, D, E, F, G, H, I, J, K, L, M, N, O, P, Q, R, S, T, U, V, W, X, Y\}$
- $S = \{G1, G2, G3, G4, G5, G6, G7, G8, G9, G10, G11, G12, G13, G14, G15, G16, G17, G18, G19, G20, G21, G22, G23, G24, G25, G26, G27, G28, G29, G30, G31, G32\}$

## Parameters

- $a_{i,g} \in \{0,1\}$: equals 1 if item $i \in U$ belongs to candidate group $g \in S$, and 0 otherwise
- $w_g \ge 0$: value of candidate group $g$

For this instance, the candidate groups are defined as follows:

- G1: elements = {D, J, S, U, W}, value = 22
- G2: elements = {A, B, E, I, Q}, value = 23
- G3: elements = {H, K, M, O, T}, value = 21
- G4: elements = {L, N, P, V, Y}, value = 24
- G5: elements = {C, F, G, R, X}, value = 20
- G6: elements = {D, H, M, N, O, Q, R, T}, value = 30
- G7: elements = {B, R, T, W, Y}, value = 20
- G8: elements = {E, F, H, K, L, M, X}, value = 25
- G9: elements = {E, F, H, K, V, X}, value = 24
- G10: elements = {D, H, I, L, S}, value = 24
- G11: elements = {A, G, J, T, Y}, value = 19
- G12: elements = {A, D, F, J, N, P, Q, W, Y}, value = 35
- G13: elements = {E, O, U, V}, value = 21
- G14: elements = {A, E, I, K, N, P, Q, V, X}, value = 34
- G15: elements = {A, C, F, G, J, N, S, U}, value = 31
- G16: elements = {A, B, D, I, N, O, Q, U, V}, value = 34
- G17: elements = {B, D, H, K, N, Q, R, X, Y}, value = 32
- G18: elements = {C, D, K, Q, U, Y}, value = 25
- G19: elements = {E, J, O, V}, value = 19
- G20: elements = {D, M, Q, V}, value = 17
- G21: elements = {B, K, P, W}, value = 21
- G22: elements = {B, F, L, M, N, P, S, U, V}, value = 34
- G23: elements = {A, E, H, K, N, S, U, X}, value = 32
- G24: elements = {C, D, G, L, P, Q, T, X}, value = 29
- G25: elements = {E, I, L, M, O, Q, T, U, W}, value = 36
- G26: elements = {A, G, I, J, N, R, S, T, X}, value = 31
- G27: elements = {C, H, J, K, N, P, S, W}, value = 30
- G28: elements = {A, L, O, P, U, V, Y}, value = 25
- G29: elements = {B, D, F, H, M, O, S, X, Y}, value = 34
- G30: elements = {B, H, W, Y}, value = 21
- G31: elements = {D, I, K, V}, value = 21
- G32: elements = {C, E, G, J, M, O, S, U, Y}, value = 35

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

