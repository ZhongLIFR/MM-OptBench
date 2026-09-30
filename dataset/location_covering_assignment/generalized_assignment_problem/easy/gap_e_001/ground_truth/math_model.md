# Mathematical Model: Generalized Assignment Problem

## Problem Overview

This instance is a single-period generalized assignment problem.

Each task must be assigned to exactly one feasible agent. Assigning task
$j$ to agent $i$ incurs assignment cost $c_{ij}$ and consumes
resource $a_{ij}$ from the limited capacity $b_i$ of agent $i$.

The objective is to minimize total assignment cost.

## Sets and Indices

- $I$: set of agents
- $J$: set of tasks

For this instance:

- $I = {A1, A2, A3, A4}$
- $J = {T1, T2, T3, T4, T5, T6}$

## Parameters

- $c_{ij}$: assignment cost if task $j \in J$ is assigned to agent $i \in I$
- $a_{ij}$: resource consumption if task $j \in J$ is assigned to agent $i \in I$
- $b_i$: capacity of agent $i \in I$
- $F_j \subseteq I$: set of feasible agents for task $j$

Forbidden task-agent pairs are shown explicitly as `—` in the visual
and are excluded from the variable set.

## Decision Variables

- $x_{ij} \in \{0,1\}$ for each feasible pair $(i,j)$, where
  $x_{ij} = 1$ if task $j$ is assigned to agent $i$

## Objective Function

\[
\min \sum_{j \in J} \sum_{i \in F_j} c_{ij} x_{ij}
\]

## Constraints

### 1. Exact task assignment

Every task must be assigned to exactly one feasible agent:

\[
\sum_{i \in F_j} x_{ij} = 1
\qquad \forall j \in J
\]

### 2. Agent capacity

The total resource consumption assigned to each agent may not exceed its
capacity:

\[
\sum_{j \in J: i \in F_j} a_{ij} x_{ij} \le b_i
\qquad \forall i \in I
\]

### 3. Variable domains

\[
x_{ij} \in \{0,1\}
\qquad \forall j \in J,\; \forall i \in F_j
\]

## Complete Model

\[
\begin{aligned}
\min \quad
& \sum_{j \in J} \sum_{i \in F_j} c_{ij} x_{ij} \\
\text{s.t.} \quad
& \sum_{i \in F_j} x_{ij} = 1 && \forall j \in J, \\
& \sum_{j \in J: i \in F_j} a_{ij} x_{ij} \le b_i && \forall i \in I, \\
& x_{ij} \in \{0,1\} && \forall j \in J,\; \forall i \in F_j.
\end{aligned}
\]

## Instance-Specific Notes

- The released easy-level instances use a single visual containing two
  coordinated exact tables.
- The upper table contains assignment costs and feasibility.
- The lower table contains resource consumption and aligned agent
  capacities.
- Identical row and column order is preserved across both tables.
