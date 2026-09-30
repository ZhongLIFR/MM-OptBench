# Mathematical Model: Set Packing Problem

## Problem Overview

This instance is a deterministic medium-level Set Packing problem.

A collection of candidate groups is given. Each candidate group has an associated integer value and contains a specified subset of items. The task is to select a subset of candidate groups with maximum total value, subject to the condition that no item appears in more than one selected group.

## Sets and Indices

- $U$: set of items
- $S$: set of candidate groups

For this instance:

- $U = \{A, B, C, D, E, F, G, H, I, J, K, L, M, N, O, P\}$
- $S = \{G1, G2, G3, G4, G5, G6, G7, G8, G9, G10, G11, G12, G13, G14, G15, G16, G17, G18, G19, G20, G21, G22\}$

## Parameters

- $a_{i,g} \in \{0,1\}$: equals 1 if item $i \in U$ belongs to candidate group $g \in S$, and 0 otherwise
- $w_g \ge 0$: value of candidate group $g$

For this instance, the candidate groups are defined as follows:

- G1: elements = {B, H, M}, value = 12
- G2: elements = {J, L, P}, value = 13
- G3: elements = {C, D, F}, value = 13
- G4: elements = {A, K, O}, value = 11
- G5: elements = {E, G, I, N}, value = 15
- G6: elements = {J, K, N}, value = 13
- G7: elements = {B, C, D, E, G, H, L, N}, value = 19
- G8: elements = {B, H, J, K, L, M, O}, value = 19
- G9: elements = {A, B, C, H, J, L, P}, value = 19
- G10: elements = {D, F, K, M, O, P}, value = 18
- G11: elements = {C, D, E, G, I, J, L, P}, value = 21
- G12: elements = {A, E, F, K, L, O}, value = 19
- G13: elements = {D, G, H, J}, value = 13
- G14: elements = {D, E, G, I, J, L, M, P}, value = 22
- G15: elements = {B, C, D, F, H, K, M, O}, value = 23
- G16: elements = {B, C, D, E, H, M, N}, value = 17
- G17: elements = {B, E, F, G, H, L, N}, value = 21
- G18: elements = {B, C, D, J, L}, value = 16
- G19: elements = {C, D, E, G, I, K, L, P}, value = 22
- G20: elements = {E, G, M, P}, value = 15
- G21: elements = {C, H, M, N, O}, value = 16
- G22: elements = {A, B, E, H, J, M, N, P}, value = 22

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

