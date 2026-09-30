# Mathematical Model: Graph Coloring Problem

## Problem Overview

This instance is a deterministic medium-level Graph Coloring decision problem on an undirected simple graph.

The task is to determine whether the graph admits a valid coloring using at most 6 colors. Each vertex must receive exactly one color, and adjacent vertices must receive different colors.

## Sets and Indices

- $V$: set of vertices
- $E$: set of undirected edges
- $K$: set of available colors

For this instance:

- $V = \{1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27\}$
- $K = \{1, 2, 3, 4, 5, 6\}$
- $E = \{(1,4), (1,5), (1,8), (1,10), (1,12), (1,13), (1,18), (1,20), (1,23), (1,24), (1,25), (1,26), (1,27), (2,7), (2,9), (2,12), (2,13), (2,15), (2,16), (2,18), (2,19), (2,20), (2,22), (2,23), (2,27), (3,4), (3,5), (3,6), (3,9), (3,10), (3,15), (3,17), (3,18), (3,19), (3,20), (4,5), (4,6), (4,11), (4,12), (4,13), (4,14), (4,16), (4,18), (4,19), (4,20), (4,24), (4,26), (4,27), (5,6), (5,7), (5,12), (5,13), (5,15), (5,18), (5,19), (5,20), (5,21), (5,24), (5,25), (5,27), (6,11), (6,13), (6,17), (6,19), (6,21), (6,22), (6,24), (6,27), (7,10), (7,11), (7,12), (7,15), (7,17), (7,18), (7,19), (7,20), (7,25), (7,26), (8,9), (8,11), (8,12), (8,15), (8,16), (8,17), (8,18), (8,20), (8,21), (8,23), (9,12), (9,13), (9,21), (9,22), (9,24), (10,11), (10,12), (10,13), (10,14), (10,15), (10,17), (10,22), (10,25), (11,13), (11,19), (11,21), (11,22), (11,25), (12,15), (12,17), (12,19), (12,20), (12,21), (12,22), (12,25), (13,14), (13,16), (13,17), (13,18), (13,20), (13,22), (13,26), (14,19), (14,21), (14,25), (14,27), (15,17), (15,18), (15,20), (15,24), (15,25), (15,27), (16,17), (16,18), (16,27), (17,20), (17,22), (17,23), (17,27), (18,19), (18,21), (18,22), (18,24), (18,25), (18,26), (18,27), (19,24), (19,26), (19,27), (20,21), (20,24), (20,25), (21,22), (21,24), (21,25), (21,26), (22,24), (22,25), (22,27), (24,25), (24,26), (24,27), (25,26), (25,27), (26,27)\}$

## Parameters

- $(u,v) \in E$: undirected adjacency relation between vertices $u$ and $v$
- $K$: maximum number of available colors, fixed at 6

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
