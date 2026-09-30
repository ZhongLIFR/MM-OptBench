# Mathematical Model: Energy Dispatch and Unit Commitment

## Problem Overview

This instance is a deterministic single-zone hard-level energy dispatch and unit commitment problem.

A fleet of generating units must satisfy electricity demand across a finite planning horizon. In each period, a generator may be either on or off. If it is on, its power output must lie between its minimum and maximum generation limits. Variable generation costs are linear in output, and startup costs are incurred whenever a generator switches from off in the previous period to on in the current period. Compared with the easy-level and medium-level formulations, this hard-level version uses a longer horizon, a larger heterogeneous generator fleet, tighter capacity margins in stressed periods, and stronger temporal coupling through ramping limits and minimum up/down time requirements.

## Sets and Indices

- $G$: set of generating units
- $T$: set of time periods

For this instance:

- $G = {G1, G2, G3, G4, G5, G6}$
- $T = {t1, t2, t3, t4, t5, t6, t7, t8, t9, t10, t11, t12, t13, t14, t15, t16, t17, t18, t19, t20}$

## Parameters

- $D_t$: system demand in period $t$
- $c_g$: marginal generation cost of generator $g$
- $f_g$: startup cost of generator $g$
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
- $v_{g,t} \in \{0,1\}$: startup indicator equal to 1 if generator $g$ starts up in period $t$

## Objective Function

Minimize total generation cost plus total startup cost:

\[
\min \; \sum_{g \in G} \sum_{t \in T} \left(c_g p_{g,t} + f_g v_{g,t}\right)
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

### 4. Startup definition constraints

For the first period of each generator:

\[
v_{g,t_1} \ge u_{g,t_1} - u^0_g \qquad \forall g \in G
\]

For every subsequent period:

\[
v_{g,t} \ge u_{g,t} - u_{g,t^-} \qquad \forall g \in G,\; t \in T \setminus \{t_1\}
\]

where $t^-$ denotes the period immediately preceding $t$.

### 5. Ramp-up constraints

For the first period:

\[
p_{g,t_1} - p^0_g \le RU_g \qquad \forall g \in G
\]

For every subsequent period:

\[
p_{g,t} - p_{g,t^-} \le RU_g \qquad \forall g \in G,\; t \in T \setminus \{t_1\}
\]

### 6. Ramp-down constraints

For the first period:

\[
p^0_g - p_{g,t_1} \le RD_g \qquad \forall g \in G
\]

For every subsequent period:

\[
p_{g,t^-} - p_{g,t} \le RD_g \qquad \forall g \in G,\; t \in T \setminus \{t_1\}
\]

### 7. Minimum up-time constraints

Startup decisions require commitment persistence over the required up-time window:

\[
\sum_{\tau=t}^{t+UT_g-1} u_{g,\tau} \ge UT_g \, v_{g,t}
\qquad \forall g \in G,\; t \in T
\]

### 8. Minimum down-time constraints

Shutdown decisions implied by commitment decreases require off-status persistence over the required down-time window.

### 9. Variable domains

\[
p_{g,t} \ge 0, \qquad u_{g,t} \in \{0,1\}, \qquad v_{g,t} \in \{0,1\}
\qquad \forall g \in G,\; t \in T
\]

## Complete Model

\[
\begin{aligned}
\min \quad & \sum_{g \in G} \sum_{t \in T} \left(c_g p_{g,t} + f_g v_{g,t}\right) \\
\text{s.t.} \quad
& \sum_{g \in G} p_{g,t} = D_t && \forall t \in T, \\
& P^{\min}_g u_{g,t} \le p_{g,t} \le P^{\max}_g u_{g,t} && \forall g \in G,\; t \in T, \\
& v_{g,t_1} \ge u_{g,t_1} - u^0_g && \forall g \in G, \\
& v_{g,t} \ge u_{g,t} - u_{g,t^-} && \forall g \in G,\; t \in T \setminus \{t_1\}, \\
& p_{g,t_1} - p^0_g \le RU_g && \forall g \in G, \\
& p^0_g - p_{g,t_1} \le RD_g && \forall g \in G, \\
& p_{g,t} - p_{g,t^-} \le RU_g && \forall g \in G,\; t \in T \setminus \{t_1\}, \\
& p_{g,t^-} - p_{g,t} \le RD_g && \forall g \in G,\; t \in T \setminus \{t_1\}, \\
& \sum_{\tau=t}^{t+UT_g-1} u_{g,\tau} \ge UT_g \, v_{g,t} && \forall g \in G,\; t \in T, \\
& p_{g,t} \ge 0 && \forall g \in G,\; t \in T, \\
& u_{g,t} \in \{0,1\},\; v_{g,t} \in \{0,1\} && \forall g \in G,\; t \in T.
\end{aligned}
\]

## Instance-Specific Notes

This instance uses the official three-visual hard-level format for energy dispatch and unit commitment. The first visual contains the generator economics table. The second visual contains the exact demand timeline. The third visual contains the generator capacity ranges. The additional temporal parameters required for hard-level modeling, including ramp limits, minimum up/down times, and initial conditions, are provided in the textual task statement and recorded in `instance_data.json`.
