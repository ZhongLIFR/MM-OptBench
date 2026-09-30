# Mathematical Model: Workforce Planning and Shift Scheduling

## Problem Overview

This instance is a deterministic easy-level workforce planning and shift scheduling problem.

A single service unit must assign workers to a small set of daily shifts over a short planning horizon. Every day-shift pair has a staffing requirement that must be covered. Each worker may work at most one shift per day and may only be assigned to shifts allowed by that worker's daily availability code. Each feasible assignment incurs a worker-specific and shift-specific cost.

The easy-level version considered here excludes overtime variables, fairness terms, rest-transition rules, consecutive-day limits, skill-substitution constraints, and stochastic effects.

## Sets and Indices

- $W$: set of workers
- $T$: set of planning days
- $S$: set of shifts

For this instance:

- $|W| = 8$
- $|T| = 8$
- $S = \{D, E, N\}$

## Parameters

- $d_{t,s}$: required number of workers for day $t$ and shift $s$
- $c_{w,s}$: assignment cost of worker $w$ on shift $s$
- $A_{w,t,s} \in \{0,1\}$: availability indicator equal to 1 if worker $w$ may work shift $s$ on day $t$

## Decision Variables

- $x_{w,t,s} \in \{0,1\}$: equals 1 if worker $w$ is assigned to shift $s$ on day $t$

## Objective Function

Minimize total assignment cost:

\[
\min \; \sum_{w \in W} \sum_{t \in T} \sum_{s \in S} c_{w,s} x_{w,t,s}
\]

## Constraints

### 1. Coverage constraints

\[
\sum_{w \in W} x_{w,t,s} \ge d_{t,s}
\qquad \forall t \in T,\; s \in S
\]

### 2. At-most-one-shift-per-day constraints

\[
\sum_{s \in S} x_{w,t,s} \le 1
\qquad \forall w \in W,\; t \in T
\]

### 3. Availability constraints

\[
x_{w,t,s} \le A_{w,t,s}
\qquad \forall w \in W,\; t \in T,\; s \in S
\]

### 4. Variable domains

\[
x_{w,t,s} \in \{0,1\}
\qquad \forall w \in W,\; t \in T,\; s \in S
\]

## Complete Model

\[
\begin{aligned}
\min \quad
& \sum_{w \in W} \sum_{t \in T} \sum_{s \in S} c_{w,s} x_{w,t,s} \\
\text{s.t.} \quad
& \sum_{w \in W} x_{w,t,s} \ge d_{t,s} && \forall t \in T,\; s \in S, \\
& \sum_{s \in S} x_{w,t,s} \le 1 && \forall w \in W,\; t \in T, \\
& x_{w,t,s} \le A_{w,t,s} && \forall w \in W,\; t \in T,\; s \in S, \\
& x_{w,t,s} \in \{0,1\} && \forall w \in W,\; t \in T,\; s \in S.
\end{aligned}
\]

## Instance-Specific Notes

This instance uses the official dual-visual format for easy-level workforce scheduling:

- `visual_0.png` contains the exact staffing-demand information.
- `visual_1.png` contains the exact worker-level shift costs and daily availability codes.

The visual design intentionally separates time-by-shift demand from worker-by-day availability so that all instance data remain readable at document scale while still requiring cross-panel reasoning to build the model.
