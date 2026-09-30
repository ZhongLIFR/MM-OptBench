# Mathematical Model: Job-Shop Scheduling

## Problem Overview

This instance is a single-period classical Job-Shop Scheduling problem.

A set of jobs must be processed on a set of machines. Each job consists of an ordered sequence of operations, and each operation requires a specific machine for a fixed processing duration. Operations of the same job must respect their precedence order. Each machine can process at most one operation at a time, and operations are non-preemptive.

The objective is to minimize the makespan, i.e., the completion time of the last finished operation.

## Sets and Indices

- $J$: set of jobs
- $M$: set of machines
- $O_j$: ordered set of operations of job $j \in J$

For this instance:

- $J = {J1, J2, J3, J4, J5, J6, J7, J8, J9, J10}$
- $M = {M1, M2, M3, M4, M5, M6, M7}$

Instance-specific ordered operations:

- $J1$: O1 on M1 with duration 6 $\rightarrow$ O2 on M4 with duration 16 $\rightarrow$ O3 on M2 with duration 5 $\rightarrow$ O4 on M5 with duration 6 $\rightarrow$ O5 on M3 with duration 4
- $J2$: O1 on M2 with duration 5 $\rightarrow$ O2 on M4 with duration 15 $\rightarrow$ O3 on M3 with duration 6 $\rightarrow$ O4 on M6 with duration 7 $\rightarrow$ O5 on M1 with duration 5
- $J3$: O1 on M3 with duration 7 $\rightarrow$ O2 on M4 with duration 16 $\rightarrow$ O3 on M5 with duration 5 $\rightarrow$ O4 on M1 with duration 6 $\rightarrow$ O5 on M2 with duration 4
- $J4$: O1 on M5 with duration 6 $\rightarrow$ O2 on M4 with duration 17 $\rightarrow$ O3 on M1 with duration 4 $\rightarrow$ O4 on M2 with duration 5 $\rightarrow$ O5 on M6 with duration 6
- $J5$: O1 on M6 with duration 5 $\rightarrow$ O2 on M4 with duration 14 $\rightarrow$ O3 on M2 with duration 6 $\rightarrow$ O4 on M3 with duration 5 $\rightarrow$ O5 on M5 with duration 7
- $J6$: O1 on M7 with duration 7 $\rightarrow$ O2 on M4 with duration 16 $\rightarrow$ O3 on M3 with duration 5 $\rightarrow$ O4 on M5 with duration 6 $\rightarrow$ O5 on M1 with duration 4
- $J7$: O1 on M1 with duration 6 $\rightarrow$ O2 on M4 with duration 15 $\rightarrow$ O3 on M5 with duration 4 $\rightarrow$ O4 on M6 with duration 7 $\rightarrow$ O5 on M2 with duration 5
- $J8$: O1 on M2 with duration 5 $\rightarrow$ O2 on M4 with duration 14 $\rightarrow$ O3 on M6 with duration 6 $\rightarrow$ O4 on M1 with duration 5 $\rightarrow$ O5 on M3 with duration 7
- $J9$: O1 on M3 with duration 7 $\rightarrow$ O2 on M4 with duration 16 $\rightarrow$ O3 on M1 with duration 5 $\rightarrow$ O4 on M5 with duration 6 $\rightarrow$ O5 on M7 with duration 4
- $J10$: O1 on M5 with duration 6 $\rightarrow$ O2 on M4 with duration 17 $\rightarrow$ O3 on M2 with duration 4 $\rightarrow$ O4 on M7 with duration 5 $\rightarrow$ O5 on M3 with duration 6

## Parameters

- $p_{j,k}$: processing time of the $k$-th operation of job $j$
- $m_{j,k}$: machine required by the $k$-th operation of job $j$
- $H$: a sufficiently large constant used in the disjunctive non-overlap constraints

## Decision Variables

- $s_{j,k} \ge 0$: start time of operation $(j,k)$
- $C_\max \ge 0$: makespan
- $y_{(j,k),(j',k')} \in \{0,1\}$: binary ordering variable for two distinct operations that require the same machine

## Objective Function

Minimize the makespan, i.e., the completion time of the last finished operation:

\[
\min\; C_\max
\]

where \(C_\max\) is constrained to be no smaller than the completion time of every operation.

## Constraints

### 1. Job precedence constraints

For every job $j \in J$ and consecutive operations $k, k+1 \in O_j$:

\[
s_{j,k+1} \ge s_{j,k} + p_{j,k}
\]

### 2. Machine non-overlap constraints

For any two distinct operations $(j,k)$ and $(j',k')$ that require the same machine, exactly one must be processed before the other:

\[
s_{j,k} + p_{j,k} \le s_{j',k'} + H\left(1 - y_{(j,k),(j',k')}\right)
\]

\[
s_{j',k'} + p_{j',k'} \le s_{j,k} + H\, y_{(j,k),(j',k')}
\]

### 3. Makespan definition

For every operation $(j,k)$:

\[
C_\max \ge s_{j,k} + p_{j,k}
\]

### 4. Variable domains

\[
s_{j,k} \ge 0 \qquad \forall j \in J,\; k \in O_j
\]

\[
C_\max \ge 0
\]

\[
y_{(j,k),(j',k')} \in \{0,1\}
\]

## Complete Model

\[
\begin{aligned}
\min \quad & C_\max \\
\text{s.t.} \quad
& s_{j,k+1} \ge s_{j,k} + p_{j,k} && \forall j \in J,\; k=1,\dots,|O_j|-1, \\
& s_{j,k} + p_{j,k} \le s_{j',k'} + H\left(1-y_{(j,k),(j',k')}\right) && \forall (j,k) \ne (j',k'):\; m_{j,k} = m_{j',k'}, \\
& s_{j',k'} + p_{j',k'} \le s_{j,k} + H\, y_{(j,k),(j',k')} && \forall (j,k) \ne (j',k'):\; m_{j,k} = m_{j',k'}, \\
& C_\max \ge s_{j,k} + p_{j,k} && \forall j \in J,\; k \in O_j, \\
& s_{j,k} \ge 0 && \forall j \in J,\; k \in O_j, \\
& C_\max \ge 0, \\
& y_{(j,k),(j',k')} \in \{0,1\} && \forall (j,k) \ne (j',k'):\; m_{j,k} = m_{j',k'}.
\end{aligned}
\]

## Instance-Specific Notes

This is a medium-level classical job-shop scheduling instance. Each job has a fixed machine order, operations are non-preemptive, and each machine can process at most one operation at a time. The required machine and processing time for every operation are specified in `instance_data.json` and reflected in the instance visual. The metadata additionally records the routing pattern, processing-time regime, and machine-load characteristics used to position the instance within the medium-level design space.
