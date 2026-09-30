# Mathematical Model: Graph Coloring Problem

## Problem Overview

This instance is a deterministic medium-level Graph Coloring optimization problem on an undirected simple graph.

The task is to assign colors to all vertices so that adjacent vertices receive different colors while minimizing the number of used colors, with an upper bound of 10 available colors.

## Sets and Indices

- $V$: set of vertices
- $E$: set of undirected edges
- $K$: set of available colors

For this instance:

- $V = \{1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33\}$
- $K = \{1, 2, 3, 4, 5, 6, 7, 8, 9, 10\}$
- $E = \{(1,2), (1,3), (1,14), (1,18), (1,19), (1,21), (1,26), (1,30), (2,3), (2,6), (2,7), (2,9), (2,12), (2,14), (2,18), (2,30), (3,8), (3,9), (3,12), (3,13), (3,14), (3,15), (3,20), (3,21), (3,23), (3,25), (3,32), (4,7), (4,15), (4,23), (4,28), (4,31), (4,32), (4,33), (5,6), (5,10), (5,12), (5,14), (5,15), (5,17), (5,20), (5,21), (5,22), (5,23), (5,25), (5,27), (6,20), (6,21), (7,8), (7,10), (7,11), (7,24), (7,28), (7,29), (7,30), (7,31), (8,12), (8,13), (8,16), (8,21), (8,22), (8,26), (8,28), (8,31), (8,32), (8,33), (9,10), (9,11), (9,12), (9,13), (9,15), (9,22), (9,26), (9,27), (9,28), (9,29), (9,31), (10,11), (10,13), (10,18), (10,28), (10,29), (10,30), (11,12), (11,14), (11,15), (11,16), (11,17), (11,20), (11,28), (11,32), (11,33), (12,14), (12,16), (12,17), (12,18), (12,19), (12,21), (12,22), (12,23), (12,24), (12,26), (12,30), (12,31), (12,32), (12,33), (13,24), (13,27), (13,29), (13,30), (13,31), (13,32), (13,33), (14,15), (14,16), (14,20), (14,21), (14,23), (14,25), (14,30), (15,25), (15,27), (15,29), (16,20), (16,21), (16,22), (16,24), (16,26), (16,27), (16,31), (16,32), (16,33), (17,18), (17,19), (17,22), (17,25), (17,26), (17,33), (18,21), (18,23), (18,25), (18,26), (19,21), (19,23), (19,30), (20,26), (20,30), (21,22), (21,25), (21,26), (21,30), (21,31), (21,33), (22,23), (22,25), (22,26), (22,30), (22,31), (22,33), (23,26), (23,30), (24,25), (24,26), (24,33), (25,26), (25,27), (26,31), (26,33), (27,28), (27,29), (27,33), (28,31), (29,30), (29,31), (31,32), (31,33)\}$

## Parameters

- $(u,v) \in E$: undirected adjacency relation between vertices $u$ and $v$
- $K_{\max}$: color upper bound, fixed at 10

## Decision Variables

- $x_{v,k} \in \{0,1\}$: equals 1 if vertex $v$ is assigned color $k$, and 0 otherwise
- $y_k \in \{0,1\}$: equals 1 if color $k$ is used by at least one vertex, and 0 otherwise

## Objective Function

Minimize the number of used colors:

\[
\min \; \sum_{k \in K} y_k
\]

## Constraints

### 1. Exactly one color per vertex

For every vertex $v \in V$:

\[
\sum_{k \in K} x_{v,k} = 1
\]

### 2. Adjacent vertices cannot share a color

For every edge $(u,v) \in E$ and every color $k \in K$:

\[
x_{u,k} + x_{v,k} \le 1
\]

### 3. Color-usage linking constraints

For every vertex $v \in V$ and every color $k \in K$:

\[
x_{v,k} \le y_k
\]

### 4. Binary domains

\[
x_{v,k} \in \{0,1\} \qquad \forall v \in V,\; \forall k \in K
\]

\[
y_k \in \{0,1\} \qquad \forall k \in K
\]

## Complete Model

\[
\begin{aligned}
\min \quad & \sum_{k \in K} y_k \\
\text{s.t.} \quad
& \sum_{k \in K} x_{v,k} = 1 && \forall v \in V, \\
& x_{u,k} + x_{v,k} \le 1 && \forall (u,v) \in E,\; \forall k \in K, \\
& x_{v,k} \le y_k && \forall v \in V,\; \forall k \in K, \\
& x_{v,k} \in \{0,1\} && \forall v \in V,\; \forall k \in K, \\
& y_k \in \{0,1\} && \forall k \in K.
\end{aligned}
\]

## Instance-Specific Notes

This instance uses the official hard-level adjacency-matrix visual format for Graph Coloring. All instance-specific data are fully recorded in `instance_data.json` and `canonical_specification.txt`, and are visually encoded in `visual_0.png` without revealing a valid final coloring assignment.
