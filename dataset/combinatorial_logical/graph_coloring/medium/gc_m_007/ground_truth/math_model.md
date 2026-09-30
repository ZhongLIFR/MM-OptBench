# Mathematical Model: Graph Coloring Problem

## Problem Overview

This instance is a deterministic medium-level Graph Coloring decision problem with fixed assignments on an undirected simple graph.

The task is to determine whether the graph admits a valid coloring using at most 5 colors while satisfying the fixed pre-colored assignments shown in the instance data.

## Sets and Indices

- $V$: set of vertices
- $E$: set of undirected edges
- $K$: set of available colors

For this instance:

- $V = \{1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24\}$
- $K = \{1, 2, 3, 4, 5\}$
- $E = \{(1,7), (1,8), (1,10), (1,11), (1,12), (1,14), (1,18), (1,21), (1,23), (2,6), (2,11), (2,16), (2,17), (3,4), (3,5), (3,9), (3,11), (3,13), (3,14), (3,15), (3,21), (3,22), (4,6), (4,15), (4,16), (5,21), (5,24), (6,8), (6,9), (6,11), (6,15), (6,21), (6,22), (7,8), (7,10), (7,12), (7,15), (7,16), (7,23), (8,11), (8,14), (8,15), (8,16), (8,18), (8,19), (8,22), (9,16), (9,17), (9,23), (9,24), (10,14), (10,16), (10,17), (10,18), (10,19), (10,22), (11,12), (11,15), (11,20), (11,22), (11,23), (12,14), (12,16), (12,18), (13,15), (13,20), (14,19), (14,23), (14,24), (15,21), (15,22), (16,23), (17,21), (17,22), (18,22), (18,23), (19,20), (21,24), (22,24)\}$

## Parameters

- $(u,v) \in E$: undirected adjacency relation between vertices $u$ and $v$
- $K$: maximum number of available colors, fixed at 5
- Fixed assignments: vertex 1 -> color 3, vertex 3 -> color 1, vertex 4 -> color 2

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

### 4. Fixed assignments

For vertex 1:

\[
x_{1,3} = 1
\]
For vertex 3:

\[
x_{3,1} = 1
\]
For vertex 4:

\[
x_{4,2} = 1
\]

### 4. Binary domains

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
& x_{1,3} = 1 &&
& x_{3,1} = 1 &&
& x_{4,2} = 1 &&
& x_{v,k} \in \{0,1\} && \forall v \in V,\; \forall k \in K.
\end{aligned}
\]

## Instance-Specific Notes

This instance uses the official medium-level adjacency-matrix visual format for Graph Coloring. The figure includes a side legend for the fixed pre-colored vertices. All instance-specific data are fully recorded in `instance_data.json` and `canonical_specification.txt`, and are visually encoded in `visual_0.png` without revealing a valid final coloring assignment.
