# Mathematical Model: Graph Coloring Problem

## Problem Overview

This instance is a deterministic medium-level Graph Coloring decision problem on an undirected simple graph.

The task is to determine whether the graph admits a valid coloring using at most 7 colors. Each vertex must receive exactly one color, and adjacent vertices must receive different colors.

## Sets and Indices

- $V$: set of vertices
- $E$: set of undirected edges
- $K$: set of available colors

For this instance:

- $V = \{1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31\}$
- $K = \{1, 2, 3, 4, 5, 6, 7\}$
- $E = \{(1,2), (1,4), (1,8), (1,9), (1,11), (1,19), (1,23), (1,24), (1,29), (2,6), (2,10), (2,11), (2,14), (2,15), (2,18), (2,20), (2,23), (2,24), (3,4), (3,5), (3,8), (3,10), (3,11), (3,13), (3,18), (3,23), (3,24), (3,25), (4,6), (4,12), (4,23), (4,24), (4,27), (4,31), (5,7), (5,12), (5,13), (5,14), (5,15), (5,17), (5,20), (5,24), (5,26), (5,27), (5,29), (5,30), (5,31), (6,9), (6,10), (6,13), (6,18), (6,19), (6,20), (6,23), (6,24), (7,8), (7,10), (7,17), (7,20), (7,21), (7,22), (7,23), (7,27), (7,28), (7,31), (8,10), (8,13), (8,15), (8,16), (8,18), (8,21), (8,22), (9,15), (9,19), (9,28), (9,31), (10,12), (10,13), (10,17), (10,19), (10,25), (10,28), (10,29), (10,30), (10,31), (11,12), (11,13), (11,19), (11,27), (11,30), (11,31), (12,15), (12,16), (12,20), (12,22), (12,23), (12,24), (12,27), (12,28), (13,14), (13,15), (13,20), (13,22), (13,23), (13,24), (13,26), (13,29), (13,30), (14,15), (14,16), (14,17), (14,20), (14,24), (14,27), (14,29), (14,30), (15,20), (15,21), (15,24), (15,27), (15,28), (15,29), (15,30), (16,20), (16,26), (16,27), (17,26), (17,27), (17,28), (17,29), (18,20), (18,29), (18,30), (19,23), (19,24), (20,21), (20,24), (20,26), (20,28), (20,30), (21,22), (21,24), (21,25), (21,27), (21,29), (22,25), (22,26), (22,29), (23,25), (23,28), (23,31), (24,25), (24,28), (24,30), (25,27), (26,27), (26,28), (26,29), (27,31), (28,29), (28,30), (28,31)\}$

## Parameters

- $(u,v) \in E$: undirected adjacency relation between vertices $u$ and $v$
- $K$: maximum number of available colors, fixed at 7

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
