# Mathematical Model: Graph Coloring Problem

## Problem Overview

This instance is a deterministic medium-level weighted Graph Coloring optimization problem on an undirected simple graph.

The task is to assign colors to all vertices so that adjacent vertices receive different colors while minimizing the total cost of the used colors, with an upper bound of 8 available colors.

## Sets and Indices

- $V$: set of vertices
- $E$: set of undirected edges
- $K$: set of available colors

For this instance:

- $V = \{1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26\}$
- $K = \{1, 2, 3, 4, 5, 6, 7, 8\}$
- $E = \{(1,8), (1,9), (1,14), (1,17), (1,21), (1,23), (1,24), (2,5), (2,7), (2,8), (2,9), (2,12), (2,13), (2,14), (2,16), (2,20), (2,23), (2,24), (2,26), (3,5), (3,9), (3,10), (3,22), (4,10), (4,11), (4,13), (4,19), (4,21), (4,26), (5,11), (5,14), (5,16), (5,17), (5,19), (5,24), (5,25), (6,10), (6,11), (6,12), (6,24), (7,12), (7,14), (7,15), (7,20), (7,22), (8,10), (8,13), (8,14), (8,15), (8,17), (8,20), (8,25), (8,26), (9,10), (9,18), (9,25), (10,12), (10,25), (11,14), (11,16), (11,26), (12,13), (12,15), (12,16), (12,22), (12,26), (13,14), (13,17), (13,20), (13,23), (13,24), (13,26), (14,16), (14,19), (14,20), (14,26), (15,16), (15,19), (15,20), (16,19), (16,21), (16,22), (16,23), (17,18), (17,20), (17,21), (17,23), (17,24), (18,19), (19,23), (19,24), (19,25), (19,26), (20,21), (20,22), (20,25), (20,26), (21,22), (21,23), (21,24), (22,23), (25,26)\}$

## Parameters

- $(u,v) \in E$: undirected adjacency relation between vertices $u$ and $v$
- $K_{\max}$: color upper bound, fixed at 8
- $w_k$: cost of using color $k$, with $w_1=7$, $w_2=3$, $w_3=6$, $w_4=2$, $w_5=5$, $w_6=1$, $w_7=4$, $w_8=2$

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
