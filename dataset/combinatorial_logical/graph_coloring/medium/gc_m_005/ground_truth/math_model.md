# Mathematical Model: Graph Coloring Problem

## Problem Overview

This instance is a deterministic medium-level Graph Coloring optimization problem on an undirected simple graph.

The task is to assign colors to all vertices so that adjacent vertices receive different colors while minimizing the number of used colors, with an upper bound of 8 available colors.

## Sets and Indices

- $V$: set of vertices
- $E$: set of undirected edges
- $K$: set of available colors

For this instance:

- $V = \{1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20\}$
- $K = \{1, 2, 3, 4, 5, 6, 7, 8\}$
- $E = \{(1,6), (1,7), (1,8), (1,19), (2,8), (2,13), (2,14), (2,16), (2,18), (3,4), (3,5), (3,7), (3,8), (3,12), (3,15), (3,18), (3,20), (4,6), (4,7), (4,8), (4,9), (4,12), (4,15), (4,16), (4,18), (4,20), (5,7), (5,12), (5,14), (5,15), (5,20), (6,14), (6,18), (7,10), (7,12), (7,17), (7,20), (8,9), (8,11), (8,12), (8,17), (8,19), (8,20), (9,11), (9,15), (10,13), (10,15), (10,20), (11,14), (11,15), (11,18), (11,19), (12,13), (12,16), (12,20), (13,19), (14,15), (15,16), (15,19), (16,19), (17,20), (18,19)\}$

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
