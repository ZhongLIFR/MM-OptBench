# Mathematical Model: Graph Coloring Problem

## Problem Overview

This instance is a deterministic medium-level Graph Coloring decision problem on an undirected simple graph.

The task is to determine whether the graph admits a valid coloring using at most 5 colors. Each vertex must receive exactly one color, and adjacent vertices must receive different colors.

## Sets and Indices

- $V$: set of vertices
- $E$: set of undirected edges
- $K$: set of available colors

For this instance:

- $V = \{1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24\}$
- $K = \{1, 2, 3, 4, 5\}$
- $E = \{(1,2), (1,5), (1,6), (1,14), (1,15), (1,17), (1,21), (1,23), (1,24), (2,5), (2,6), (2,10), (2,11), (2,13), (2,18), (2,19), (2,20), (2,24), (3,15), (3,17), (3,20), (3,22), (4,5), (4,10), (4,12), (4,13), (4,14), (4,19), (4,21), (4,23), (5,9), (5,10), (5,16), (5,17), (5,19), (5,20), (5,22), (6,10), (6,14), (6,17), (6,19), (6,22), (6,24), (7,8), (7,9), (7,14), (7,22), (8,9), (8,11), (8,14), (8,15), (8,16), (8,17), (8,22), (8,23), (8,24), (9,10), (9,12), (9,13), (9,18), (9,22), (10,14), (10,15), (10,16), (10,17), (10,19), (10,22), (11,14), (11,15), (11,16), (11,17), (11,21), (11,23), (12,13), (12,14), (12,15), (12,16), (12,21), (12,22), (12,23), (13,14), (13,17), (13,18), (13,21), (13,22), (13,23), (13,24), (14,15), (14,17), (14,18), (14,19), (14,20), (14,22), (15,16), (15,18), (15,19), (15,20), (15,21), (16,17), (16,20), (16,21), (17,18), (17,19), (17,23), (18,19), (18,21), (18,23), (18,24), (19,21), (20,22), (20,23), (20,24), (21,23), (22,23)\}$

## Parameters

- $(u,v) \in E$: undirected adjacency relation between vertices $u$ and $v$
- $K$: maximum number of available colors, fixed at 5

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
