# Mathematical Model: Set Packing Problem

## Problem Overview

This instance is a deterministic medium-level Set Packing problem.

A collection of candidate groups is given. Each candidate group has an associated integer value and contains a specified subset of items. The task is to select a subset of candidate groups with maximum total value, subject to the condition that no item appears in more than one selected group.

## Sets and Indices

- $U$: set of items
- $S$: set of candidate groups

For this instance:

- $U = \{A, B, C, D, E, F, G, H, I, J, K, L, M, N, O, P\}$
- $S = \{G1, G2, G3, G4, G5, G6, G7, G8, G9, G10, G11, G12, G13, G14, G15, G16, G17, G18, G19, G20, G21\}$

## Parameters

- $a_{i,g} \in \{0,1\}$: equals 1 if item $i \in U$ belongs to candidate group $g \in S$, and 0 otherwise
- $w_g \ge 0$: value of candidate group $g$

For this instance, the candidate groups are defined as follows:

- G1: elements = {E, G, I}, value = 16
- G2: elements = {B, N, P}, value = 17
- G3: elements = {F, J, L}, value = 17
- G4: elements = {A, C, H}, value = 17
- G5: elements = {D, K, M, O}, value = 16
- G6: elements = {B, E, G, I, K, M, O}, value = 9
- G7: elements = {E, K, P}, value = 16
- G8: elements = {B, K, M, N, P}, value = 12
- G9: elements = {B, I, J}, value = 13
- G10: elements = {B, H, I}, value = 14
- G11: elements = {A, C, E, G, I}, value = 11
- G12: elements = {A, J, K}, value = 14
- G13: elements = {F, G, K, L}, value = 15
- G14: elements = {A, C, D, H, K, M, O}, value = 9
- G15: elements = {B, C, D, L, O, P}, value = 10
- G16: elements = {B, D, F, J, L, N, P}, value = 10
- G17: elements = {A, B, E, G, I, N, P}, value = 11
- G18: elements = {D, E, F, G, H, I, J}, value = 13
- G19: elements = {E, H, M}, value = 16
- G20: elements = {A, D, J, K, M}, value = 14
- G21: elements = {A, B, C, F, J}, value = 13

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

