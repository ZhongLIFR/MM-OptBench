# Mathematical Model: Graph Coloring Problem

## Problem Overview

This instance is a deterministic medium-level Graph Coloring decision problem with fixed assignments on an undirected simple graph.

The task is to determine whether the graph admits a valid coloring using at most 5 colors while satisfying the fixed pre-colored assignments shown in the instance data.

## Sets and Indices

- $V$: set of vertices
- $E$: set of undirected edges
- $K$: set of available colors

For this instance:

- $V = \{1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23\}$
- $K = \{1, 2, 3, 4, 5\}$
- $E = \{(1,5), (1,9), (1,10), (1,11), (1,12), (1,13), (1,17), (1,21), (1,23), (2,3), (2,4), (2,5), (2,7), (2,10), (2,11), (2,13), (2,15), (2,18), (2,20), (2,21), (3,10), (3,14), (3,17), (3,18), (3,20), (4,10), (4,12), (4,16), (4,18), (4,19), (4,20), (5,6), (5,7), (5,11), (5,13), (5,14), (5,15), (5,18), (5,19), (5,20), (5,22), (5,23), (6,8), (6,9), (6,12), (7,8), (7,10), (7,13), (7,16), (7,19), (7,22), (7,23), (8,11), (8,17), (8,20), (9,14), (9,15), (9,16), (9,20), (9,22), (11,13), (11,16), (11,18), (11,19), (11,20), (11,22), (12,14), (12,18), (12,20), (13,14), (13,17), (13,18), (14,21), (15,17), (15,22), (17,19), (17,21), (18,19), (18,21), (19,22), (22,23)\}$

## Parameters

- $(u,v) \in E$: undirected adjacency relation between vertices $u$ and $v$
- $K$: maximum number of available colors, fixed at 5
- Fixed assignments: vertex 1 -> color 3, vertex 5 -> color 1, vertex 6 -> color 1

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
For vertex 5:

\[
x_{5,1} = 1
\]
For vertex 6:

\[
x_{6,1} = 1
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
& x_{5,1} = 1 &&
& x_{6,1} = 1 &&
& x_{v,k} \in \{0,1\} && \forall v \in V,\; \forall k \in K.
\end{aligned}
\]

## Instance-Specific Notes

This instance uses the official medium-level adjacency-matrix visual format for Graph Coloring. The figure includes a side legend for the fixed pre-colored vertices. All instance-specific data are fully recorded in `instance_data.json` and `canonical_specification.txt`, and are visually encoded in `visual_0.png` without revealing a valid final coloring assignment.
