# Mathematical Model: Graph Coloring Problem

## Problem Overview

This instance is a deterministic medium-level Graph Coloring decision problem on an undirected simple graph.

The task is to determine whether the graph admits a valid coloring using at most 4 colors. Each vertex must receive exactly one color, and adjacent vertices must receive different colors.

## Sets and Indices

- $V$: set of vertices
- $E$: set of undirected edges
- $K$: set of available colors

For this instance:

- $V = \{1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14\}$
- $K = \{1, 2, 3, 4\}$
- $E = \{(1,4), (1,5), (1,6), (1,9), (1,10), (1,14), (2,5), (2,7), (2,10), (2,12), (2,13), (2,14), (3,4), (3,5), (3,6), (3,7), (3,8), (3,9), (3,14), (4,6), (4,8), (4,10), (4,12), (5,7), (5,11), (5,13), (5,14), (6,7), (6,8), (6,14), (7,10), (8,10), (8,14), (9,12), (10,12), (10,13), (10,14), (11,13), (12,13), (12,14)\}$

## Parameters

- $(u,v) \in E$: undirected adjacency relation between vertices $u$ and $v$
- $K$: maximum number of available colors, fixed at 4

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

This instance uses the official medium-level adjacency-matrix visual format for Graph Coloring. All instance-specific data are fully recorded in `instance_data.json` and `canonical_specification.txt`, and are visually encoded in `visual_0.png` without revealing a valid final coloring assignment.
