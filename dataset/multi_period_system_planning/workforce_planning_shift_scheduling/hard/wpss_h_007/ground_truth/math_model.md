# Mathematical Model: Workforce Planning and Shift Scheduling

## Problem Overview

This instance is a deterministic hard-level workforce planning and shift scheduling problem.

A service unit must assign workers to Day, Evening, and Night shifts over a finite planning horizon. Every day-shift pair has a staffing requirement that must be covered. Each worker may work at most one shift per day and may only be assigned to shifts allowed by that worker's daily availability code. Each worker has a regular shift cap across the full horizon, and assignments above that cap incur worker-specific overtime cost.
Night exposure is limited by worker-specific Night-shift caps.
The model also limits worker-specific consecutive working days.
A simple rest rule forbids a Night assignment immediately followed by a Day assignment on the next day.

## Sets and Indices

- $W$: set of workers
- $T$: ordered set of planning days, written as $T = (t_1, t_2, \ldots, t_{|T|})$
- $S$: set of shifts, with $S = \{D, E, N\}$

For this instance:

- $|W| = 17$
- $|T| = 18$
- $S = \{D, E, N\}$

## Parameters

- $d_{t,s}$: required number of workers for day $t$ and shift $s$
- $c_{w,s}$: assignment cost of worker $w$ on shift $s$
- $A_{w,t,s} \in \{0,1\}$: availability indicator derived from the daily availability code
- $L_w$: regular shift cap for worker $w$ across the horizon
- $OT_w$: overtime cost per extra shift for worker $w$
- $N_w$: maximum number of Night assignments for worker $w$
- $R_w$: maximum number of consecutive working days for worker $w$

## Decision Variables

- $x_{w,t,s} \in \{0,1\}$: equals 1 if worker $w$ is assigned to shift $s$ on day $t$
- $o_w \ge 0$: overtime shifts used by worker $w$ beyond the regular cap

## Objective Function

Minimize total assignment cost and overtime cost:

\[
\min \; \sum_{w \in W} \sum_{t \in T} \sum_{s \in S} c_{w,s} x_{w,t,s}
+ \sum_{w \in W} OT_w \, o_w
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

### 4. Regular workload plus overtime constraints
\[
\sum_{t \in T} \sum_{s \in S} x_{w,t,s} \le L_w + o_w
\qquad \forall w \in W
\]

### 5. Night-shift limits
\[
\sum_{t \in T} x_{w,t,N} \le N_w
\qquad \forall w \in W
\]

### 6. Consecutive-working-day limits
\[
\sum_{\ell=j}^{j+R_w} \sum_{s \in S} x_{w,t_\ell,s} \le R_w
\qquad \forall w \in W,\; j = 1, \ldots, |T| - R_w
\]

### 7. Night-to-Day rest constraints
\[
x_{w,t_j,N} + x_{w,t_{j+1},D} \le 1
\qquad \forall w \in W,\; j = 1, \ldots, |T| - 1
\]

### 8. Variable domains
\[
x_{w,t,s} \in \{0,1\}
\qquad \forall w \in W,\; t \in T,\; s \in S
\]
\[
o_w \ge 0
\qquad \forall w \in W
\]

## Complete Model

\[
\begin{aligned}
\min \quad
& \sum_{w \in W} \sum_{t \in T} \sum_{s \in S} c_{w,s} x_{w,t,s}
+ \sum_{w \in W} OT_w \, o_w \\
\text{s.t.} \quad
& \sum_{w \in W} x_{w,t,s} \ge d_{t,s} && \forall t \in T,\; s \in S, \\
& \sum_{s \in S} x_{w,t,s} \le 1 && \forall w \in W,\; t \in T, \\
& x_{w,t,s} \le A_{w,t,s} && \forall w \in W,\; t \in T,\; s \in S, \\
& \sum_{t \in T} \sum_{s \in S} x_{w,t,s} \le L_w + o_w && \forall w \in W, \\
& \sum_{t \in T} x_{w,t,N} \le N_w && \forall w \in W, \\
& \sum_{\ell=j}^{j+R_w} \sum_{s \in S} x_{w,t_\ell,s} \le R_w && \forall w \in W,\; j = 1, \ldots, |T| - R_w, \\
& x_{w,t_j,N} + x_{w,t_{j+1},D} \le 1 && \forall w \in W,\; j = 1, \ldots, |T| - 1, \\
& x_{w,t,s} \in \{0,1\} && \forall w \in W,\; t \in T,\; s \in S, \\
& o_w \ge 0 && \forall w \in W.
\end{aligned}
\]

## Instance-Specific Notes

This instance uses four visual files designed to keep the hard-level worker-side information legible:

- `visual_0.png` contains the exact staffing-demand information.
- `visual_1.png` contains the exact worker-level cost and workload parameters.
- `visual_2.png` contains the exact availability codes for the first block of days: Mon1, Tue1, Wed1, Thu1, Fri1, Sat1, Sun1, Mon2, Tue2.
- `visual_3.png` contains the exact availability codes for the remaining days: Wed2, Thu2, Fri2, Sat2, Sun2, Mon3, Tue3, Wed3, Thu3.

The worker order is identical across both availability panels so that the reader can reconstruct the full horizon without ambiguity.
