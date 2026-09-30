# Mathematical Model: Graph Coloring Problem

## Problem Overview

This instance is a deterministic medium-level Graph Coloring optimization problem on an undirected simple graph.

The task is to assign colors to all vertices so that adjacent vertices receive different colors while minimizing the number of used colors, with an upper bound of 12 available colors.

## Sets and Indices

- $V$: set of vertices
- $E$: set of undirected edges
- $K$: set of available colors

For this instance:

- $V = \{1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40\}$
- $K = \{1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12\}$
- $E = \{(1,2), (1,4), (1,5), (1,6), (1,8), (1,12), (1,13), (1,15), (1,16), (1,18), (1,19), (1,24), (1,25), (1,27), (1,31), (1,32), (1,33), (1,34), (1,37), (1,39), (2,4), (2,7), (2,10), (2,12), (2,13), (2,15), (2,18), (2,19), (2,21), (2,23), (2,25), (2,27), (2,32), (2,36), (2,37), (3,5), (3,6), (3,7), (3,9), (3,10), (3,12), (3,21), (3,22), (3,23), (3,25), (3,26), (3,27), (3,34), (3,36), (3,38), (4,5), (4,6), (4,8), (4,9), (4,12), (4,15), (4,18), (4,19), (4,20), (4,25), (4,27), (4,29), (4,31), (4,32), (4,35), (4,39), (5,6), (5,11), (5,19), (5,20), (5,21), (5,24), (5,25), (5,26), (5,33), (5,40), (6,11), (6,14), (6,19), (6,20), (6,22), (6,23), (6,25), (6,28), (6,29), (6,36), (6,37), (7,13), (7,14), (7,16), (7,25), (7,26), (7,34), (7,36), (7,37), (8,11), (8,15), (8,16), (8,20), (8,26), (8,29), (8,30), (8,39), (8,40), (9,12), (9,14), (9,19), (9,20), (9,22), (9,23), (9,27), (9,37), (10,13), (10,14), (10,19), (10,21), (10,22), (10,25), (10,28), (10,34), (11,16), (11,17), (11,18), (11,20), (11,24), (11,26), (11,29), (11,31), (11,33), (11,39), (12,13), (12,14), (12,15), (12,18), (12,19), (12,22), (12,23), (12,24), (12,25), (12,27), (12,32), (12,34), (12,37), (12,40), (13,14), (13,17), (13,19), (13,20), (13,22), (13,26), (13,28), (13,35), (13,37), (14,17), (14,20), (14,21), (14,22), (14,23), (14,24), (14,30), (14,36), (14,38), (15,18), (15,19), (15,20), (15,25), (15,26), (15,27), (15,28), (15,31), (15,32), (15,33), (15,36), (16,21), (16,30), (16,31), (16,33), (16,34), (16,37), (16,38), (16,40), (17,19), (17,22), (17,23), (17,25), (17,27), (17,36), (17,37), (18,19), (18,21), (18,25), (18,27), (18,28), (18,32), (18,33), (18,36), (18,38), (18,40), (19,21), (19,25), (19,27), (19,28), (19,32), (20,24), (20,30), (20,32), (20,33), (20,35), (20,39), (21,22), (21,23), (21,25), (21,29), (21,33), (21,34), (21,36), (21,37), (22,27), (22,28), (22,34), (22,35), (22,37), (23,29), (23,34), (23,37), (24,29), (24,31), (24,32), (24,33), (24,36), (24,40), (25,26), (25,27), (25,28), (25,32), (25,34), (25,35), (25,37), (26,30), (26,31), (26,32), (26,33), (26,39), (26,40), (27,28), (27,30), (27,31), (27,32), (27,34), (27,35), (27,37), (27,38), (28,31), (28,32), (28,35), (28,37), (28,39), (29,30), (29,32), (29,33), (29,34), (30,40), (31,38), (31,39), (32,39), (33,34), (33,35), (33,37), (33,38), (33,39), (35,39), (35,40), (36,38), (38,40)\}$

## Parameters

- $(u,v) \in E$: undirected adjacency relation between vertices $u$ and $v$
- $K_{\max}$: color upper bound, fixed at 12

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
