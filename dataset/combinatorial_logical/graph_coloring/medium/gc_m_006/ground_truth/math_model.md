# Mathematical Model: Graph Coloring Problem

## Problem Overview

This instance is a deterministic medium-level Graph Coloring optimization problem on an undirected simple graph.

The task is to assign colors to all vertices so that adjacent vertices receive different colors while minimizing the number of used colors, with an upper bound of 8 available colors.

## Sets and Indices

- $V$: set of vertices
- $E$: set of undirected edges
- $K$: set of available colors

For this instance:

- $V = \{1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22\}$
- $K = \{1, 2, 3, 4, 5, 6, 7, 8\}$
- $E = \{(1,2), (1,12), (1,13), (1,14), (1,16), (1,20), (1,21), (2,5), (2,13), (2,15), (2,17), (2,18), (2,19), (2,22), (3,4), (3,6), (3,9), (3,11), (3,12), (3,15), (3,17), (3,19), (3,20), (3,21), (4,6), (4,7), (4,9), (4,15), (4,17), (5,11), (5,15), (5,19), (5,20), (5,21), (6,9), (6,13), (6,14), (6,15), (6,17), (6,19), (6,20), (7,10), (7,11), (7,12), (7,13), (7,17), (8,10), (8,16), (8,18), (8,22), (9,10), (9,12), (9,15), (9,17), (9,20), (10,11), (10,13), (10,18), (10,19), (10,22), (11,12), (11,17), (11,22), (12,18), (12,19), (12,20), (12,21), (12,22), (13,21), (14,21), (15,17), (15,21), (16,18), (17,22), (18,20), (19,20)\}$

## Parameters

- $(u,v) \in E$: undirected adjacency relation between vertices $u$ and $v$
- $K_{\max}$: color upper bound, fixed at 8

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

This instance uses the official medium-level adjacency-matrix visual format for Graph Coloring. All instance-specific data are fully recorded in `instance_data.json` and `canonical_specification.txt`, and are visually encoded in `visual_0.png` without revealing a valid final coloring assignment.
