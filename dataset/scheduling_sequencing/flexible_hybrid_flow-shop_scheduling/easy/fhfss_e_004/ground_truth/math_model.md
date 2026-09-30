# Mathematical Model: Flexible / Hybrid Flow-Shop Scheduling

## Problem Overview

This instance is a deterministic single-period Flexible / Hybrid Flow-Shop Scheduling problem.

Every job must pass through the same ordered set of stages. At each stage, the job must be assigned to exactly one machine from that stage. Machines within the same stage are identical with respect to processing duration, so the processing time depends only on the job and the stage. Jobs are non-preemptive, and each machine can process at most one job at a time.

The objective is to minimize the makespan.

## Sets and Indices

- $J$: set of jobs
- $S$: ordered set of stages
- $M_s$: set of machines available at stage $s \in S$

For this instance:

- $J = {J1, J2, J3, J4, J5, J6}$
- $S = {S1, S2, S3}$

Machine sets by stage:

- `S1`: `['S1M1', 'S1M2']`
- `S2`: `['S2M1']`
- `S3`: `['S3M1', 'S3M2']`

## Parameters

- $p_{j,s}$: processing time of job $j$ at stage $s$
- $H$: a sufficiently large valid horizon bound

Instance-specific processing times:

- `J1`: S1=4, S2=4, S3=5
- `J2`: S1=3, S2=6, S3=4
- `J3`: S1=5, S2=5, S3=3
- `J4`: S1=4, S2=7, S3=2
- `J5`: S1=6, S2=4, S3=4
- `J6`: S1=5, S2=6, S3=3

## Decision Variables

- $x_{j,s,m} \in \{0,1\}$: equals 1 if job $j$ is assigned to machine $m$ at stage $s$
- $start_{j,s} \ge 0$: start time of job $j$ at stage $s$
- $y_{j,k,s,m} \in \{0,1\}$ for $j < k$: binary ordering variable used when jobs $j$ and $k$ are both assigned to machine $m$ at stage $s$
- $C_\max \ge 0$: makespan

## Objective Function

Minimize the makespan:

\[
\min\; C_\max
\]

## Constraints

### 1. Assignment constraints

Every job chooses exactly one machine at every stage:

\[
\sum_{m \in M_s} x_{j,s,m} = 1
\qquad \forall j \in J,\; \forall s \in S.
\]

### 2. Stage precedence constraints

A job cannot start stage $s+1$ before completing stage $s$:

\[
start_{j,s+1} \ge start_{j,s} + p_{j,s}
\qquad \forall j \in J,\; \forall s \in S \setminus \{S3\}.
\]

### 3. Machine non-overlap constraints

For each stage $s$, machine $m \in M_s$, and each pair of distinct jobs $j < k$, if both jobs are assigned to machine $m$ at stage $s$, then one must finish before the other starts:

\[
start_{j,s} + p_{j,s} \le start_{k,s} + H\left(3 - x_{j,s,m} - x_{k,s,m} - y_{j,k,s,m}\right)
\]

\[
start_{k,s} + p_{k,s} \le start_{j,s} + H\left(2 - x_{j,s,m} - x_{k,s,m} + y_{j,k,s,m}\right)
\]

### 4. Makespan definition

The makespan must dominate every job completion time at the final stage:

\[
C_\max \ge start_{j,S3} + p_{j,S3}
\qquad \forall j \in J.
\]

### 5. Variable domains

\[
x_{j,s,m} \in \{0,1\}
\qquad \forall j \in J,\; \forall s \in S,\; \forall m \in M_s
\]

\[
y_{j,k,s,m} \in \{0,1\}
\qquad \forall j<k,\; \forall s \in S,\; \forall m \in M_s
\]

\[
start_{j,s} \ge 0
\qquad \forall j \in J,\; \forall s \in S
\]

\[
C_\max \ge 0
\]

## Complete Model

\[
\begin{aligned}
\min \quad & C_\max \\
\text{s.t.} \quad
& \sum_{m \in M_s} x_{j,s,m} = 1
&& \forall j \in J,\; \forall s \in S, \\
& start_{j,s+1} \ge start_{j,s} + p_{j,s}
&& \forall j \in J,\; \forall s \in S \setminus \{S3\}, \\
& start_{j,s} + p_{j,s} \le start_{k,s} + H\left(3 - x_{j,s,m} - x_{k,s,m} - y_{j,k,s,m}\right)
&& \forall j<k,\; \forall s \in S,\; \forall m \in M_s, \\
& start_{k,s} + p_{k,s} \le start_{j,s} + H\left(2 - x_{j,s,m} - x_{k,s,m} + y_{j,k,s,m}\right)
&& \forall j<k,\; \forall s \in S,\; \forall m \in M_s, \\
& C_\max \ge start_{j,S3} + p_{j,S3}
&& \forall j \in J, \\
& x_{j,s,m} \in \{0,1\}
&& \forall j \in J,\; \forall s \in S,\; \forall m \in M_s, \\
& y_{j,k,s,m} \in \{0,1\}
&& \forall j<k,\; \forall s \in S,\; \forall m \in M_s, \\
& start_{j,s} \ge 0
&& \forall j \in J,\; \forall s \in S, \\
& C_\max \ge 0.
\end{aligned}
\]

## Instance-Specific Notes

- All jobs share the same stage order.
- Machines within a stage are identical with respect to processing duration.
- The upper section of the visual encodes stage order and machine inventory.
- The lower section encodes the exact job-stage processing-time matrix.
