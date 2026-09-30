# Resource-Constrained Project Scheduling Reference Model

## Problem Overview

This instance is a deterministic single-project resource-constrained scheduling problem with renewable resources only. The goal is to schedule every real activity exactly once, respect the precedence network and the renewable resource capacities, and minimize the overall project makespan.

The reference ground truth uses a discrete time-indexed formulation over the finite horizon `H = 35`, which is the sum of the real-activity durations in this instance.

## Sets and Indices

- `V`: set of all activities including dummy `Start` and dummy `End`
- `I`: set of real activities, indexed by `i`
- `R`: set of renewable resources, indexed by `r`
- `T = {0, 1, ..., H}`: discrete time points, indexed by `t`
- `E`: set of precedence arcs `(i, j)`

## Parameters

- `p_i`: duration of activity `i`
- `d_{i,r}`: renewable resource demand of activity `i` on resource `r`
- `B_r`: capacity of renewable resource `r`
- `H`: finite scheduling horizon

Dummy activities satisfy `p_{Start} = p_{End} = 0` and zero resource demand.

## Decision Variables

- `x_{i,t} \in \{0,1\}`: equals 1 if real activity `i` starts at time `t`
- `C_{max} \ge 0`: project makespan

The start time of a real activity can be written as:

\[
S_i = \sum_{t=0}^{H-p_i} t\,x_{i,t}.
\]

## Objective Function

Minimize the project makespan:

\[
\min C_{max}.
\]

## Constraints

### 1. Unique Start Time

Each real activity starts exactly once:

\[
\sum_{t=0}^{H-p_i} x_{i,t} = 1
\qquad \forall i \in I.
\]

### 2. Precedence Constraints

For every precedence arc `(i,j)` between real activities:

\[
\sum_{t=0}^{H-p_j} t x_{j,t}
\ge
\sum_{t=0}^{H-p_i} t x_{i,t} + p_i.
\]

Arcs from `Start` reduce to nonnegativity, and arcs entering `End` are enforced through the makespan constraints.

### 3. Renewable Resource Constraints

At every integer time point `\tau` and for every renewable resource `r`, the total demand of all activities active at `\tau` cannot exceed the resource capacity:

\[
\sum_{i \in I}
\sum_{t=\max(0,\tau-p_i+1)}^{\min(\tau,H-p_i)}
d_{i,r} x_{i,t}
\le B_r
\qquad \forall r \in R,\ \forall \tau = 0,\dots,H-1.
\]

### 4. Makespan Definition

The makespan must dominate the finish time of every real activity:

\[
C_{max} \ge \sum_{t=0}^{H-p_i} (t+p_i)x_{i,t}
\qquad \forall i \in I.
\]

## Complete Model

\[
\begin{aligned}
\min \quad & C_{max} \\
\text{s.t.} \quad
& \sum_{t=0}^{H-p_i} x_{i,t} = 1 && \forall i \in I, \\
& \sum_{t=0}^{H-p_j} t x_{j,t}
  \ge
  \sum_{t=0}^{H-p_i} t x_{i,t} + p_i
  && \forall (i,j) \in E,\ i,j \in I, \\
& \sum_{i \in I}
  \sum_{t=\max(0,\tau-p_i+1)}^{\min(\tau,H-p_i)}
  d_{i,r} x_{i,t}
  \le B_r
  && \forall r \in R,\ \forall \tau = 0,\dots,H-1, \\
& C_{max} \ge \sum_{t=0}^{H-p_i} (t+p_i)x_{i,t}
  && \forall i \in I, \\
& x_{i,t} \in \{0,1\}
  && \forall i \in I,\ \forall t = 0,\dots,H-p_i, \\
& C_{max} \ge 0.
\end{aligned}
\]

## Instance-Specific Notes

- This medium-level instance contains `11` real activities plus dummy `Start` and `End`.
- The instance uses `2` renewable resource(s): R1, R2.
- The intended graph pattern is `three_source_bridge_network`.
- The intended capacity regime is `mixed`.
- The visual package is `dual_visual_precedence_network_plus_resource_matrix`.
