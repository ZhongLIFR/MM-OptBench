# Mathematical Model: Graph Coloring Problem

## Problem Overview

This instance is a deterministic medium-level weighted Graph Coloring optimization problem on an undirected simple graph.

The task is to assign colors to all vertices so that adjacent vertices receive different colors while minimizing the total cost of the used colors, with an upper bound of 7 available colors.

## Sets and Indices

- $V$: set of vertices
- $E$: set of undirected edges
- $K$: set of available colors

For this instance:

- $V = \{1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25\}$
- $K = \{1, 2, 3, 4, 5, 6, 7\}$
- $E = \{(1,2), (1,4), (1,6), (1,7), (1,13), (1,14), (1,18), (1,19), (1,21), (2,6), (2,10), (2,12), (2,17), (2,18), (2,19), (2,20), (2,21), (2,22), (3,6), (3,11), (3,12), (3,14), (3,16), (3,23), (3,24), (4,12), (4,13), (4,14), (4,16), (4,17), (4,18), (4,19), (5,7), (5,9), (5,12), (5,15), (5,20), (5,21), (6,8), (6,9), (6,10), (7,11), (7,12), (7,17), (7,18), (7,19), (7,20), (7,21), (7,22), (7,23), (7,25), (8,9), (8,16), (8,22), (9,12), (9,14), (9,15), (9,18), (9,23), (9,25), (10,11), (10,14), (10,16), (10,17), (10,22), (10,24), (11,15), (11,19), (11,24), (12,13), (12,15), (12,20), (13,14), (13,16), (13,18), (13,20), (13,24), (14,18), (14,22), (14,23), (15,20), (16,17), (16,18), (16,20), (18,20), (18,21), (19,21), (19,24), (20,21), (20,25), (21,23), (21,25), (22,25), (24,25)\}$

## Parameters

- $(u,v) \in E$: undirected adjacency relation between vertices $u$ and $v$
- $K_{\max}$: color upper bound, fixed at 7
- $w_k$: cost of using color $k$, with $w_1=6$, $w_2=2$, $w_3=5$, $w_4=1$, $w_5=4$, $w_6=2$, $w_7=3$

## Decision Variables

- $x_{v,k} \in \{0,1\}$: equals 1 if vertex $v$ is assigned color $k$, and 0 otherwise
- $y_k \in \{0,1\}$: equals 1 if color $k$ is used by at least one vertex, and 0 otherwise

## Objective Function

Minimize the total cost of the used colors:

\[
\min \; \sum_{k \in K} w_k y_k
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
\min \quad & \sum_{k \in K} w_k y_k \\
\text{s.t.} \quad
& \sum_{k \in K} x_{v,k} = 1 && \forall v \in V, \\
& x_{u,k} + x_{v,k} \le 1 && \forall (u,v) \in E,\; \forall k \in K, \\
& x_{v,k} \le y_k && \forall v \in V,\; \forall k \in K, \\
& x_{v,k} \in \{0,1\} && \forall v \in V,\; \forall k \in K, \\
& y_k \in \{0,1\} && \forall k \in K.
\end{aligned}
\]

## Instance-Specific Notes

This instance uses the official medium-level adjacency-matrix visual format for Graph Coloring. The figure includes a side legend listing the color-usage costs. All instance-specific data are fully recorded in `instance_data.json` and `canonical_specification.txt`, and are visually encoded in `visual_0.png` without revealing a valid final coloring assignment.
