# Mathematical Model: Logical Constraint Satisfaction Problem

## Problem Overview

This instance is a deterministic hard-level logical constraint satisfaction problem.

A set of Boolean decision variables is given together with four types of logical restrictions: CNF clauses, simple implication constraints, at-most-one groups, and small cardinality constraints. The task is to find any binary assignment that satisfies all listed logical constraints. This is therefore a pure feasibility problem.

## Sets and Indices

- $V$: set of Boolean variables
- $C$: set of clause rows in the clause-variable matrix
- $G$: set of at-most-one groups
- $P$: set of implication constraints
- $K$: set of small cardinality constraints

For this instance:

- $V = \{x1, x2, x3, x4, x5, x6, x7, x8, x9, x10, x11, x12, x13, x14, x15, x16, x17, x18, x19, x20, x21, x22, x23, x24, x25, x26, x27, x28\}$
- $C = \{C1, C2, C3, C4, C5, C6, C7, C8, C9, C10, C11, C12, C13, C14, C15, C16, C17, C18, C19, C20, C21, C22, C23, C24, C25, C26, C27, C28, C29, C30, C31, C32, C33, C34, C35, C36, C37, C38, C39, C40, C41, C42, C43, C44, C45, C46, C47, C48, C49, C50, C51, C52, C53, C54, C55, C56, C57, C58\}$

## Parameters

- For each clause $c \in C$, let $L_c^+$ denote the variables appearing positively and let $L_c^-$ denote the variables appearing negatively.
- For each implication $(u,v) \in P$, the logical condition is $u \le v$.
- For each at-most-one group $g \in G$, at most one variable in that group may take value 1.
- For each cardinality constraint $k \in K$, at most $b_k$ variables in its designated subset may take value 1.

For this instance, the clauses are:

- $C1: (x14 \lor x27)$
- $C2: (\neg x6 \lor \neg x22)$
- $C3: (x1 \lor \neg x6)$
- $C4: (\neg x13 \lor \neg x18)$
- $C5: (\neg x6 \lor x8)$
- $C6: (x3 \lor \neg x5)$
- $C7: (\neg x3 \lor x4 \lor x5)$
- $C8: (\neg x3 \lor x7 \lor x9 \lor \neg x10)$
- $C9: (x1 \lor x10)$
- $C10: (x7 \lor x27)$
- $C11: (x7 \lor x9 \lor \neg x10)$
- $C12: (x3 \lor \neg x9)$
- $C13: (\neg x2 \lor x4)$
- $C14: (\neg x4 \lor x10 \lor x26)$
- $C15: (\neg x2 \lor x4 \lor x14)$
- $C16: (x4 \lor \neg x8)$
- $C17: (\neg x2 \lor x5 \lor x6)$
- $C18: (x20 \lor \neg x22)$
- $C19: (x21 \lor x23 \lor \neg x24)$
- $C20: (\neg x24 \lor x27)$
- $C21: (\neg x20 \lor x22)$
- $C22: (x11 \lor \neg x13 \lor x25)$
- $C23: (\neg x5 \lor \neg x9 \lor x10)$
- $C24: (x21 \lor x22 \lor \neg x25)$
- $C25: (x1 \lor x8)$
- $C26: (x4 \lor x10)$
- $C27: (x1 \lor x4 \lor x7)$
- $C28: (x1 \lor \neg x3)$
- $C29: (x10 \lor \neg x28)$
- $C30: (x2 \lor \neg x7 \lor x10)$
- $C31: (x22 \lor x27)$
- $C32: (x20 \lor x26 \lor \neg x27)$
- $C33: (x21 \lor x23 \lor \neg x26)$
- $C34: (\neg x13 \lor \neg x14)$
- $C35: (\neg x7 \lor \neg x14)$
- $C36: (x13 \lor \neg x14 \lor x16)$
- $C37: (x5 \lor \neg x9)$
- $C38: (\neg x23 \lor x24 \lor x28)$
- $C39: (x5 \lor x6 \lor x8)$
- $C40: (x1 \lor \neg x2 \lor \neg x9)$
- $C41: (\neg x4 \lor x5 \lor x8)$
- $C42: (\neg x27 \lor x28)$
- $C43: (\neg x8 \lor \neg x9 \lor \neg x10)$
- $C44: (x11 \lor \neg x13 \lor x18)$
- $C45: (\neg x11 \lor x18)$
- $C46: (x4 \lor \neg x6)$
- $C47: (x14 \lor \neg x15 \lor \neg x18)$
- $C48: (x14 \lor \neg x19)$
- $C49: (\neg x1 \lor x10 \lor \neg x24)$
- $C50: (\neg x5 \lor x24)$
- $C51: (\neg x1 \lor \neg x6 \lor \neg x8)$
- $C52: (\neg x20 \lor x23)$
- $C53: (x24 \lor x25 \lor \neg x28)$
- $C54: (x11 \lor x15)$
- $C55: (\neg x1 \lor x5 \lor x10)$
- $C56: (\neg x3 \lor x16)$
- $C57: (x11 \lor x13 \lor \neg x17)$
- $C58: (x1 \lor \neg x9)$

Implication constraints:

- $x9 \le x14$
- $x14 \le x5$
- $x5 \le x21$
- $x21 \le x24$
- $x24 \le x3$
- $x3 \le x16$
- $x16 \le x15$
- $x28 \le x23$

At-most-one groups:

- $\sum_{x \in \{x1, x8\}} x \le 1$ (A1)
- $\sum_{x \in \{x20, x27\}} x \le 1$ (A2)

Cardinality constraints:

- $\sum_{x \in \{x1, x2, x4, x6, x7, x9\}} x \le 3$ (K1)
- $\sum_{x \in \{x22, x23, x24, x26, x27, x28\}} x \le 5$ (K2)

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

