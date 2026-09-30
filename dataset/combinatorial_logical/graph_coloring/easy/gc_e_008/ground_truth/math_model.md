# Mathematical Model: Graph Coloring Problem

## Problem Overview

This instance is a deterministic easy-level Graph Coloring problem on an undirected simple graph.

The task is to assign one color to every vertex so that no pair of adjacent vertices receives the same color. This instance uses the feasibility version of the standard vertex-coloring model: the set of available colors is fixed in advance, and the goal is to determine a valid coloring using those colors.

## Sets and Indices

- $V$: set of vertices
- $E$: set of undirected edges
- $K$: set of available colors

For this instance:

- $V = \{1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14\}$
- $K = \{1, 2, 3, 4\}$
- $E = \{(1,2), (1,3), (1,4), (1,12), (1,14), (2,3), (2,4), (2,11), (2,12), (3,4), (3,6), (3,8), (3,12), (3,14), (4,5), (4,6), (4,11), (4,13), (5,8), (5,10), (5,11), (5,14), (6,8), (6,9), (6,11), (7,10), (7,12), (7,14), (8,9), (9,11), (9,12), (10,12), (10,13), (11,12), (11,13), (11,14)\}$

## Parameters

- $(u,v) \in E$: undirected adjacency relation between vertices $u$ and $v$
- $|K|$: number of available colors

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
x_{v,k} \in \{0,1\} \qquad \forall v \in V, \; \forall k \in K
\]

## Complete Model

\[
\begin{aligned}
\min \quad & 0 \\
\text{s.t.} \quad
& \sum_{k \in K} x_{v,k} = 1 && \forall v \in V, \\
& x_{u,k} + x_{v,k} \le 1 && \forall (u,v) \in E, \; \forall k \in K, \\
& x_{v,k} \in \{0,1\} && \forall v \in V, \; \forall k \in K.
\end{aligned}
\]

## Instance-Specific Notes

This instance uses the official easy-level adjacency-matrix visual format for Graph Coloring. The figure contains numeric vertex identifiers on both axes, black cells for adjacency, white cells for non-adjacency, and grey diagonal cells. All instance-specific numerical and structural data are fully recorded in `instance_data.json` and `canonical_specification.txt`, and are visually encoded in `visual_0.png` without revealing any valid coloring assignment.
