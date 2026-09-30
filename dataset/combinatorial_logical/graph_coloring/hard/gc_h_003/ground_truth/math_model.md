# Mathematical Model: Graph Coloring Problem

## Problem Overview

This instance is a deterministic medium-level Graph Coloring optimization problem on an undirected simple graph.

The task is to assign colors to all vertices so that adjacent vertices receive different colors while minimizing the number of used colors, with an upper bound of 9 available colors.

## Sets and Indices

- $V$: set of vertices
- $E$: set of undirected edges
- $K$: set of available colors

For this instance:

- $V = \{1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30\}$
- $K = \{1, 2, 3, 4, 5, 6, 7, 8, 9\}$
- $E = \{(1,5), (1,6), (1,7), (1,9), (1,10), (1,11), (1,12), (1,13), (1,15), (1,19), (1,20), (1,21), (1,23), (1,24), (1,27), (1,28), (2,4), (2,7), (2,17), (2,20), (2,23), (2,25), (2,29), (3,4), (3,7), (3,12), (3,23), (3,30), (4,12), (4,13), (4,21), (4,25), (4,29), (4,30), (5,6), (5,8), (5,9), (5,11), (5,12), (5,14), (5,18), (5,20), (5,23), (5,26), (5,27), (5,28), (6,9), (6,11), (6,13), (6,16), (6,17), (6,20), (6,29), (7,9), (7,11), (7,12), (7,15), (7,21), (7,22), (7,27), (7,28), (7,29), (8,10), (8,13), (8,19), (8,20), (8,24), (8,27), (8,30), (9,10), (9,19), (9,22), (9,24), (9,26), (9,27), (10,11), (10,16), (10,19), (10,20), (10,22), (10,23), (10,24), (10,26), (10,30), (11,18), (11,19), (11,24), (11,26), (12,14), (12,17), (12,20), (12,21), (12,23), (12,27), (12,28), (12,29), (13,14), (13,20), (13,22), (13,27), (13,28), (14,15), (14,16), (14,21), (14,22), (14,25), (14,27), (14,28), (14,29), (14,30), (15,17), (15,23), (15,25), (16,18), (16,21), (16,23), (16,24), (16,25), (16,30), (17,21), (17,25), (17,29), (18,19), (18,22), (18,24), (18,25), (18,26), (18,28), (19,20), (19,22), (19,26), (19,27), (20,22), (20,23), (20,26), (20,27), (20,28), (21,23), (22,23), (22,24), (22,27), (23,27), (23,28), (23,29), (24,26), (24,27), (25,27), (25,30), (26,27), (27,28), (28,30)\}$

## Parameters

- $(u,v) \in E$: undirected adjacency relation between vertices $u$ and $v$
- $K_{\max}$: color upper bound, fixed at 9

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
