# Mathematical Model: Set Packing Problem

## Problem Overview

This instance is a deterministic medium-level Set Packing problem.

A collection of candidate groups is given. Each candidate group has an associated integer value and contains a specified subset of items. The task is to select a subset of candidate groups with maximum total value, subject to the condition that no item appears in more than one selected group.

## Sets and Indices

- $U$: set of items
- $S$: set of candidate groups

For this instance:

- $U = \{A, B, C, D, E, F, G, H, I, J, K, L, M, N\}$
- $S = \{G1, G2, G3, G4, G5, G6, G7, G8, G9, G10, G11, G12, G13, G14, G15, G16, G17, G18\}$

## Parameters

- $a_{i,g} \in \{0,1\}$: equals 1 if item $i \in U$ belongs to candidate group $g \in S$, and 0 otherwise
- $w_g \ge 0$: value of candidate group $g$

For this instance, the candidate groups are defined as follows:

- G1: elements = {A, E, K}, value = 13
- G2: elements = {B, D, M}, value = 10
- G3: elements = {C, F, H, I}, value = 13
- G4: elements = {G, J, L, N}, value = 12
- G5: elements = {B, C, F, I, M, N}, value = 17
- G6: elements = {C, E, K, M}, value = 13
- G7: elements = {A, B, D, E, K, M}, value = 17
- G8: elements = {B, G, I, N}, value = 15
- G9: elements = {D, I, M}, value = 12
- G10: elements = {F, H, J, K}, value = 13
- G11: elements = {A, D, N}, value = 9
- G12: elements = {B, D, G, J, L, M}, value = 16
- G13: elements = {A, B, E, F, I, K}, value = 19
- G14: elements = {F, G, M}, value = 9
- G15: elements = {E, F, M}, value = 12
- G16: elements = {A, C, L}, value = 9
- G17: elements = {A, B, D, I}, value = 11
- G18: elements = {A, B, D, E, L, M}, value = 15

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

