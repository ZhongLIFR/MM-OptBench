# Mathematical Model: Set Packing Problem

## Problem Overview

This instance is a deterministic medium-level Set Packing problem.

A collection of candidate groups is given. Each candidate group has an associated integer value and contains a specified subset of items. The task is to select a subset of candidate groups with maximum total value, subject to the condition that no item appears in more than one selected group.

## Sets and Indices

- $U$: set of items
- $S$: set of candidate groups

For this instance:

- $U = \{A, B, C, D, E, F, G, H, I, J, K, L, M, N, O\}$
- $S = \{G1, G2, G3, G4, G5, G6, G7, G8, G9, G10, G11, G12, G13, G14, G15, G16, G17, G18, G19, G20\}$

## Parameters

- $a_{i,g} \in \{0,1\}$: equals 1 if item $i \in U$ belongs to candidate group $g \in S$, and 0 otherwise
- $w_g \ge 0$: value of candidate group $g$

For this instance, the candidate groups are defined as follows:

- G1: elements = {C, D, H}, value = 12
- G2: elements = {B, G, K}, value = 13
- G3: elements = {A, M, N}, value = 12
- G4: elements = {E, L, O}, value = 11
- G5: elements = {F, I, J}, value = 10
- G6: elements = {F, H, M, N}, value = 11
- G7: elements = {A, D, F, J, N}, value = 13
- G8: elements = {B, D, G, H}, value = 14
- G9: elements = {F, I, M, O}, value = 15
- G10: elements = {B, H, I}, value = 13
- G11: elements = {A, D, H}, value = 9
- G12: elements = {A, I, K}, value = 12
- G13: elements = {C, I, K}, value = 13
- G14: elements = {A, B, I, J, M, N}, value = 16
- G15: elements = {C, D, E, H, L, O}, value = 19
- G16: elements = {E, F, I, L, O}, value = 16
- G17: elements = {B, H, L}, value = 9
- G18: elements = {D, F, H, J, O}, value = 14
- G19: elements = {B, D, G, H, K}, value = 13
- G20: elements = {E, K, N, O}, value = 14

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

