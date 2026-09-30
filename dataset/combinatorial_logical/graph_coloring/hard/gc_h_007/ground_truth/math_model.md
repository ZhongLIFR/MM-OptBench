# Mathematical Model: Graph Coloring Problem

## Problem Overview

This instance is a deterministic medium-level Graph Coloring decision problem on an undirected simple graph.

The task is to determine whether the graph admits a valid coloring using at most 8 colors. Each vertex must receive exactly one color, and adjacent vertices must receive different colors.

## Sets and Indices

- $V$: set of vertices
- $E$: set of undirected edges
- $K$: set of available colors

For this instance:

- $V = \{1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34\}$
- $K = \{1, 2, 3, 4, 5, 6, 7, 8\}$
- $E = \{(1,2), (1,3), (1,4), (1,6), (1,7), (1,8), (1,9), (1,11), (1,12), (1,14), (1,16), (1,17), (1,19), (1,20), (1,21), (1,22), (1,31), (1,32), (2,4), (2,6), (2,8), (2,13), (2,14), (2,16), (2,17), (2,18), (2,19), (2,22), (2,23), (2,24), (2,25), (2,27), (2,30), (2,31), (3,8), (3,9), (3,10), (3,12), (3,15), (3,16), (3,17), (3,18), (3,20), (3,22), (3,23), (3,25), (3,27), (3,28), (3,29), (3,31), (3,32), (3,33), (4,9), (4,10), (4,12), (4,14), (4,15), (4,17), (4,18), (4,19), (4,20), (4,22), (4,26), (4,29), (4,34), (5,6), (5,10), (5,12), (5,15), (5,19), (5,20), (5,21), (5,23), (5,24), (5,29), (5,30), (5,32), (5,33), (5,34), (6,9), (6,10), (6,11), (6,12), (6,15), (6,16), (6,17), (6,19), (6,21), (6,22), (6,23), (6,24), (6,28), (6,31), (6,33), (7,9), (7,11), (7,14), (7,17), (7,24), (7,25), (7,28), (7,29), (7,31), (7,34), (8,10), (8,12), (8,13), (8,15), (8,17), (8,19), (8,20), (8,22), (8,25), (8,27), (8,28), (8,29), (9,11), (9,12), (9,16), (9,18), (9,19), (9,20), (9,26), (9,28), (10,11), (10,12), (10,14), (10,15), (10,16), (10,17), (10,18), (10,19), (10,27), (10,29), (10,32), (11,13), (11,14), (11,19), (11,20), (11,23), (11,24), (11,26), (11,27), (11,30), (11,33), (12,14), (12,21), (12,25), (12,26), (12,27), (12,28), (12,32), (13,18), (13,19), (13,21), (13,28), (13,29), (14,15), (14,16), (14,25), (14,26), (14,28), (14,29), (14,32), (14,34), (15,16), (15,17), (15,18), (15,19), (15,21), (15,22), (15,23), (15,24), (15,25), (15,30), (15,32), (16,17), (16,19), (16,20), (16,22), (16,29), (16,31), (16,34), (17,19), (17,20), (17,22), (17,23), (17,30), (17,31), (17,33), (18,20), (18,22), (18,27), (18,32), (19,22), (19,23), (19,24), (19,26), (19,28), (19,29), (19,31), (19,32), (20,22), (20,24), (20,27), (20,29), (20,30), (20,31), (20,32), (20,33), (20,34), (21,23), (21,25), (21,27), (21,30), (21,32), (22,24), (22,25), (22,26), (22,31), (22,32), (22,34), (23,28), (23,30), (23,32), (24,26), (24,28), (24,29), (24,30), (24,32), (24,33), (24,34), (25,27), (25,31), (26,27), (26,28), (26,30), (26,31), (27,30), (27,32), (27,33), (27,34), (28,31), (29,30), (29,32), (29,33), (29,34), (30,31), (30,32), (30,33), (30,34), (31,32), (31,33), (32,33), (32,34), (33,34)\}$

## Parameters

- $(u,v) \in E$: undirected adjacency relation between vertices $u$ and $v$
- $K$: maximum number of available colors, fixed at 8

## Decision Variables

- $x_{v,k} \in \{0,1\}$: equals 1 if vertex $v$ is assigned color $k$, and 0 otherwise

## Objective Function

This instance is modeled as a feasibility problem. A standard dummy objective is used:

\[
\min \; 0
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

### 3. Binary domains

\[
x_{v,k} \in \{0,1\} \qquad \forall v \in V,\; \forall k \in K
\]

## Complete Model

\[
\begin{aligned}
\min \quad & 0 \\
\text{s.t.} \quad
& \sum_{k \in K} x_{v,k} = 1 && \forall v \in V, \\
& x_{u,k} + x_{v,k} \le 1 && \forall (u,v) \in E,\; \forall k \in K,
& x_{v,k} \in \{0,1\} && \forall v \in V,\; \forall k \in K.
\end{aligned}
\]

## Instance-Specific Notes

This instance uses the official hard-level adjacency-matrix visual format for Graph Coloring. All instance-specific data are fully recorded in `instance_data.json` and `canonical_specification.txt`, and are visually encoded in `visual_0.png` without revealing a valid final coloring assignment.
