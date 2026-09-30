# Mathematical Model: Energy Dispatch and Unit Commitment

## Problem Overview

This instance is a deterministic single-zone medium-level energy dispatch and unit commitment problem.

A fleet of generating units must satisfy electricity demand across a finite planning horizon. In each period, a generator may be either on or off. If it is on, its power output must lie between its minimum and maximum generation limits. Variable generation costs are linear in output, and startup costs are incurred whenever a generator switches from off in the previous period to on in the current period. Shutdown costs may also be included. Compared with the easy-level formulation, this medium-level version additionally imposes ramping limits and minimum up/down time requirements.

## Sets and Indices

- $G$: set of generating units
- $T$: set of time periods

For this instance:

- $G = {G1, G2, G3, G4}$
- $T = {t1, t2, t3, t4, t5, t6, t7, t8, t9, t10}$

## Parameters

- $D_t$: system demand in period $t$
- $c_g$: marginal generation cost of generator $g$
- $f_g$: startup cost of generator $g$
- $s_g$: shutdown cost of generator $g$
- $P^{\min}_g$: minimum output of generator $g$ when it is on
- $P^{\max}_g$: maximum output of generator $g$ when it is on
- $RU_g$: ramp-up limit of generator $g$
- $RD_g$: ramp-down limit of generator $g$
- $UT_g$: minimum up-time of generator $g$
- $DT_g$: minimum down-time of generator $g$
- $u^0_g$: initial on/off status of generator $g$
- $p^0_g$: initial output of generator $g$

## Decision Variables

- $p_{g,t} \ge 0$: power output of generator $g$ in period $t$
- $u_{g,t} \in \{0,1\}$: commitment status of generator $g$ in period $t$
- $v_{g,t} \in \{0,1\}$: startup indicator
- $w_{g,t} \in \{0,1\}$: shutdown indicator

## Objective Function

Minimize total generation cost, startup cost, and shutdown cost:

\[
\min \; \sum_{g \in G} \sum_{t \in T} \left(c_g p_{g,t} + f_g v_{g,t} + s_g w_{g,t}\right)
\]

## Constraints

### 1. Demand balance constraints

\[
\sum_{g \in G} p_{g,t} = D_t \qquad \forall t \in T
\]

### 2. Generation lower-bound constraints

\[
p_{g,t} \ge P^{\min}_g u_{g,t} \qquad \forall g \in G,\; t \in T
\]

### 3. Generation upper-bound constraints

\[
p_{g,t} \le P^{\max}_g u_{g,t} \qquad \forall g \in G,\; t \in T
\]

### 4. Commitment transition constraints

For the first period:

\[
u_{g,t_1} - v_{g,t_1} + w_{g,t_1} = u^0_g \qquad \forall g \in G
\]

For every subsequent period:

\[
u_{g,t} - u_{g,t^-} - v_{g,t} + w_{g,t} = 0
\qquad \forall g \in G,\; t \in T \setminus \{t_1\}
\]

### 5. Ramp-up constraints

\[
p_{g,t} - p_{g,t^-} \le RU_g \qquad \forall g \in G,\; t \in T \setminus \{t_1\}
\]

### 6. Ramp-down constraints

\[
p_{g,t^-} - p_{g,t} \le RD_g \qquad \forall g \in G,\; t \in T \setminus \{t_1\}
\]

### 7. Minimum up-time constraints

Startup decisions require a generator to remain on for its minimum up-time window.

### 8. Minimum down-time constraints

Shutdown decisions require a generator to remain off for its minimum down-time window.

### 9. Variable domains

\[
p_{g,t} \ge 0, \qquad
u_{g,t}, v_{g,t}, w_{g,t} \in \{0,1\}
\qquad \forall g \in G,\; t \in T
\]

## Complete Model

\[
\begin{aligned}
\min \quad & \sum_{g \in G} \sum_{t \in T} (c_g p_{g,t} + f_g v_{g,t} + s_g w_{g,t}) \\
\text{s.t.} \quad
& \sum_{g \in G} p_{g,t} = D_t && \forall t \in T, \\
& P^{\min}_g u_{g,t} \le p_{g,t} \le P^{\max}_g u_{g,t} && \forall g,t, \\
& u_{g,t} - u_{g,t^-} - v_{g,t} + w_{g,t} = 0 && \forall g,t>t_1, \\
& p_{g,t} - p_{g,t^-} \le RU_g && \forall g,t>t_1, \\
& p_{g,t^-} - p_{g,t} \le RD_g && \forall g,t>t_1.
\end{aligned}
\]

## Instance-Specific Notes

This instance uses the official two-visual medium-level format for energy dispatch and unit commitment.
The first visual contains the generator economics table.
The second visual contains the exact demand timeline and generator capacity ranges.
All instance-specific numerical data required to formulate the optimization model are provided in the visual inputs and recorded in `instance_data.json`.
