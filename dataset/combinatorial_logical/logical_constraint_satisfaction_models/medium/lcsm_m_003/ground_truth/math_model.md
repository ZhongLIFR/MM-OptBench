# Mathematical Model: Logical Constraint Satisfaction Problem

## Problem Overview

This instance is a deterministic medium-level logical constraint satisfaction problem.

A set of Boolean decision variables is given together with four types of logical restrictions: CNF clauses, simple implication constraints, at-most-one groups, and small cardinality constraints. The task is to find any binary assignment that satisfies all listed logical constraints. This is therefore a pure feasibility problem.

## Sets and Indices

- $V$: set of Boolean variables
- $C$: set of clause rows in the clause-variable matrix
- $G$: set of at-most-one groups
- $P$: set of implication constraints
- $K$: set of small cardinality constraints

For this instance:

- $V = \{x1, x2, x3, x4, x5, x6, x7, x8, x9, x10, x11, x12, x13, x14, x15, x16, x17, x18, x19, x20\}$
- $C = \{C1, C2, C3, C4, C5, C6, C7, C8, C9, C10, C11, C12, C13, C14, C15, C16, C17, C18, C19, C20, C21, C22, C23, C24, C25, C26, C27, C28, C29, C30, C31, C32, C33, C34, C35, C36, C37, C38, C39, C40, C41, C42, C43, C44\}$

## Parameters

- For each clause $c \in C$, let $L_c^+$ denote the variables appearing positively and let $L_c^-$ denote the variables appearing negatively.
- For each implication $(u,v) \in P$, the logical condition is $u \le v$.
- For each at-most-one group $g \in G$, at most one variable in that group may take value 1.
- For each cardinality constraint $k \in K$, at most $b_k$ variables in its designated subset may take value 1.

For this instance, the clauses are:

- $C1: (x10 \lor x18)$
- $C2: (\neg x11 \lor \neg x13)$
- $C3: (\neg x13 \lor x15)$
- $C4: (\neg x4 \lor \neg x7 \lor \neg x13)$
- $C5: (x8 \lor x10 \lor x18)$
- $C6: (x1 \lor \neg x4 \lor \neg x17)$
- $C7: (x10 \lor \neg x17)$
- $C8: (x15 \lor x20)$
- $C9: (x19 \lor x20)$
- $C10: (\neg x1 \lor x5)$
- $C11: (x8 \lor \neg x11 \lor \neg x14)$
- $C12: (x8 \lor \neg x9 \lor x12 \lor x13)$
- $C13: (\neg x7 \lor \neg x15 \lor x19)$
- $C14: (\neg x15 \lor x19 \lor x20)$
- $C15: (x8 \lor \neg x11 \lor \neg x12)$
- $C16: (x4 \lor \neg x5 \lor \neg x6)$
- $C17: (\neg x2 \lor \neg x10 \lor x18)$
- $C18: (x18 \lor \neg x19)$
- $C19: (\neg x6 \lor x7)$
- $C20: (\neg x16 \lor x19 \lor x20)$
- $C21: (x8 \lor \neg x9 \lor x11)$
- $C22: (x16 \lor x18 \lor x19)$
- $C23: (x9 \lor \neg x10 \lor x12)$
- $C24: (x11 \lor x15)$
- $C25: (\neg x8 \lor x10)$
- $C26: (\neg x2 \lor \neg x5)$
- $C27: (\neg x3 \lor x12)$
- $C28: (x3 \lor x4 \lor \neg x7)$
- $C29: (x15 \lor x17)$
- $C30: (x16 \lor x18 \lor \neg x19)$
- $C31: (\neg x1 \lor x6)$
- $C32: (x8 \lor x12)$
- $C33: (\neg x17 \lor x18 \lor \neg x19)$
- $C34: (\neg x10 \lor \neg x11 \lor x14)$
- $C35: (\neg x2 \lor x4)$
- $C36: (\neg x17 \lor x20)$
- $C37: (\neg x16 \lor x20)$
- $C38: (\neg x2 \lor \neg x6 \lor \neg x7)$
- $C39: (\neg x1 \lor x2 \lor x3)$
- $C40: (x3 \lor \neg x6)$
- $C41: (x10 \lor \neg x12)$
- $C42: (\neg x13 \lor \neg x14)$
- $C43: (x4 \lor \neg x7)$
- $C44: (\neg x3 \lor x5 \lor x7)$

Implication constraints:

- $x7 \le x3$
- $x3 \le x6$
- $x6 \le x4$
- $x12 \le x7$

At-most-one groups:

- $\sum_{x \in \{x10, x13\}} x \le 1$ (A1)
- $\sum_{x \in \{x9, x13\}} x \le 1$ (A2)

Cardinality constraints:

- None

## Decision Variables

For each variable $x_i \in V$:

- $x_i \in \{0,1\}$

## Objective Function

This is a pure feasibility model. We therefore use a dummy constant objective:

\[
\min \; 0
\]

## Constraints

### 1. Clause satisfaction constraints

For each clause $c \in C$:

\[
\sum_{i \in L_c^+} x_i + \sum_{i \in L_c^-} (1 - x_i) \ge 1
\]

### 2. Implication constraints

For each implication $(u,v) \in P$:

\[
u \le v
\]

### 3. At-most-one constraints

For each at-most-one group $g \in G$ with variable subset $A_g \subseteq V$:

\[
\sum_{i \in A_g} x_i \le 1
\]

### 4. Cardinality constraints

For each cardinality constraint $k \in K$ with subset $S_k \subseteq V$ and upper bound $b_k$:

\[
\sum_{i \in S_k} x_i \le b_k
\]

### 5. Binary domains

\[
x_i \in \{0,1\} \qquad \forall i \in V
\]

## Complete Model

\[
\begin{aligned}
\min \quad & 0 \\
\text{s.t.} \quad
& \sum_{i \in L_c^+} x_i + \sum_{i \in L_c^-} (1 - x_i) \ge 1 && \forall c \in C, \\
& u \le v && \forall (u,v) \in P, \\
& \sum_{i \in A_g} x_i \le 1 && \forall g \in G, \\
& \sum_{i \in S_k} x_i \le b_k && \forall k \in K, \\
& x_i \in \{0,1\} && \forall i \in V.
\end{aligned}
\]

## Instance-Specific Notes

This instance uses the official medium-level clause-variable matrix visual format for logical constraint satisfaction. The matrix contains one column per Boolean variable. Rows labeled C* encode original clauses, rows labeled I* encode implication constraints, rows labeled A* encode pairwise exclusions derived from at-most-one groups, and rows labeled K* encode small cardinality constraints with the upper bound written directly in the row label. All instance-specific structural data are fully recorded in `instance_data.json` and `canonical_specification.txt`, and are visually encoded in `visual_0.png` without revealing a satisfying assignment.

