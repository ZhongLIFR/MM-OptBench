# Mathematical Model: Energy Dispatch and Unit Commitment

## Problem Overview

This instance is a deterministic single-zone energy dispatch and unit commitment problem.

A set of generating units must satisfy the electricity demand over a finite planning horizon. In each period, a generator may be either on or off. If it is on, its power output must lie between its minimum and maximum generation limits. Variable generation costs are linear in output, and a startup cost is incurred whenever a generator switches from off in the previous period to on in the current period.

The easy-level version considered here excludes ramping limits, minimum up/down constraints, transmission constraints, reserve requirements, and stochastic effects.

## Sets and Indices

- $G$: set of generating units
- $T$: set of time periods

For this instance:

- $G = {G1, G2, G3}$
- $T = {t1, t2, t3, t4}$

## Parameters

- $D_t$: system demand in period $t$
- $c_g$: marginal generation cost of generator $g$
- $f_g$: startup cost of generator $g$
- $P^{\min}_g$: minimum output of generator $g$ when it is on
- $P^{\max}_g$: maximum output of generator $g$ when it is on
- $u^0_g$: initial on/off status of generator $g$ before the first period

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

### 5. Variable domains

\[
p_{g,t} \ge 0, \qquad u_{g,t} \in \{0,1\}, \qquad v_{g,t} \in \{0,1\} \qquad \forall g \in G,\; t \in T
\]

## Complete Model

\[
\begin{aligned}
\min \quad & \sum_{g \in G} \sum_{t \in T} \left(c_g p_{g,t} + f_g v_{g,t}\right) \\
\text{s.t.} \quad
& \sum_{g \in G} p_{g,t} = D_t && \forall t \in T, \\
& p_{g,t} \ge P^{\min}_g u_{g,t} && \forall g \in G,\; t \in T, \\
& p_{g,t} \le P^{\max}_g u_{g,t} && \forall g \in G,\; t \in T, \\
& v_{g,t_1} \ge u_{g,t_1} - u^0_g && \forall g \in G, \\
& v_{g,t} \ge u_{g,t} - u_{g,t^-} && \forall g \in G,\; t \in T \setminus \{t_1\}, \\
& p_{g,t} \ge 0 && \forall g \in G,\; t \in T, \\
& u_{g,t} \in \{0,1\},\; v_{g,t} \in \{0,1\} && \forall g \in G,\; t \in T.
\end{aligned}
\]

## Instance-Specific Notes

This instance uses the official single-image visual format for easy-level energy dispatch and unit commitment. The figure contains a generator economics table, an exact demand timeline, and generator capacity ranges. All instance-specific numerical data needed to formulate the model are provided in the visual and recorded in `instance_data.json`.
