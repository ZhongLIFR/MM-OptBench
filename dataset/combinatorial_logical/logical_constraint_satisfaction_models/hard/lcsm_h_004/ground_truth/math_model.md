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

- $V = \{x1, x2, x3, x4, x5, x6, x7, x8, x9, x10, x11, x12, x13, x14, x15, x16, x17, x18, x19, x20, x21, x22, x23, x24, x25, x26, x27, x28, x29, x30, x31\}$
- $C = \{C1, C2, C3, C4, C5, C6, C7, C8, C9, C10, C11, C12, C13, C14, C15, C16, C17, C18, C19, C20, C21, C22, C23, C24, C25, C26, C27, C28, C29, C30, C31, C32, C33, C34, C35, C36, C37, C38, C39, C40, C41, C42, C43, C44, C45, C46, C47, C48, C49, C50, C51, C52, C53, C54, C55, C56, C57, C58, C59, C60, C61, C62, C63\}$

## Parameters

- For each clause $c \in C$, let $L_c^+$ denote the variables appearing positively and let $L_c^-$ denote the variables appearing negatively.
- For each implication $(u,v) \in P$, the logical condition is $u \le v$.
- For each at-most-one group $g \in G$, at most one variable in that group may take value 1.
- For each cardinality constraint $k \in K$, at most $b_k$ variables in its designated subset may take value 1.

For this instance, the clauses are:

- $C1: (x11 \lor x16)$
- $C2: (\neg x4 \lor \neg x19)$
- $C3: (x16 \lor \neg x29)$
- $C4: (\neg x19 \lor \neg x28 \lor \neg x31)$
- $C5: (x17 \lor x18 \lor \neg x20)$
- $C6: (\neg x29 \lor \neg x31)$
- $C7: (\neg x7 \lor x24)$
- $C8: (\neg x17 \lor \neg x18 \lor \neg x21)$
- $C9: (\neg x17 \lor x18 \lor \neg x23)$
- $C10: (x28 \lor x31)$
- $C11: (\neg x29 \lor x31)$
- $C12: (\neg x3 \lor x11 \lor x16)$
- $C13: (x25 \lor \neg x27 \lor x31)$
- $C14: (\neg x18 \lor \neg x19 \lor \neg x23)$
- $C15: (x10 \lor \neg x12 \lor x15)$
- $C16: (x20 \lor x22 \lor \neg x23)$
- $C17: (x25 \lor x26 \lor \neg x27 \lor \neg x31)$
- $C18: (\neg x18 \lor x22)$
- $C19: (x20 \lor \neg x21)$
- $C20: (x5 \lor \neg x14)$
- $C21: (\neg x21 \lor \neg x23)$
- $C22: (\neg x9 \lor x11 \lor x13)$
- $C23: (\neg x17 \lor \neg x22)$
- $C24: (\neg x17 \lor x30)$
- $C25: (x2 \lor x23 \lor x24)$
- $C26: (x10 \lor x11 \lor \neg x12)$
- $C27: (x18 \lor x26)$
- $C28: (\neg x27 \lor x30 \lor \neg x31)$
- $C29: (\neg x20 \lor x21 \lor x24)$
- $C30: (\neg x17 \lor x19 \lor \neg x20)$
- $C31: (x4 \lor x12 \lor \neg x28)$
- $C32: (x26 \lor x27 \lor \neg x28)$
- $C33: (\neg x11 \lor x15)$
- $C34: (\neg x27 \lor x29)$
- $C35: (x10 \lor \neg x12 \lor \neg x15)$
- $C36: (x8 \lor \neg x29 \lor x30)$
- $C37: (x10 \lor \neg x19)$
- $C38: (x1 \lor x2)$
- $C39: (\neg x9 \lor \neg x11 \lor x15 \lor \neg x16)$
- $C40: (x9 \lor \neg x11 \lor x16)$
- $C41: (x10 \lor \neg x12 \lor \neg x13)$
- $C42: (\neg x25 \lor x29 \lor x31)$
- $C43: (x2 \lor x5 \lor \neg x6)$
- $C44: (x13 \lor \neg x26 \lor \neg x27)$
- $C45: (x21 \lor x23)$
- $C46: (x1 \lor \neg x6 \lor \neg x21)$
- $C47: (x5 \lor x16)$
- $C48: (\neg x26 \lor x28 \lor \neg x30)$
- $C49: (\neg x10 \lor x12 \lor \neg x15)$
- $C50: (\neg x7 \lor x21 \lor \neg x31)$
- $C51: (x20 \lor x21 \lor x22)$
- $C52: (x25 \lor \neg x27 \lor x28)$
- $C53: (x18 \lor \neg x20)$
- $C54: (x12 \lor \neg x13 \lor \neg x14)$
- $C55: (x11 \lor \neg x13)$
- $C56: (x25 \lor x31)$
- $C57: (x5 \lor \neg x6)$
- $C58: (x3 \lor x4)$
- $C59: (\neg x1 \lor x6 \lor \neg x7)$
- $C60: (x27 \lor x29 \lor x30)$
- $C61: (\neg x1 \lor \neg x8)$
- $C62: (\neg x13 \lor \neg x14 \lor x16)$
- $C63: (x17 \lor \neg x23 \lor \neg x24)$

Implication constraints:

- $x18 \le x1$
- $x1 \le x11$
- $x11 \le x15$
- $x15 \le x3$
- $x3 \le x30$
- $x30 \le x23$
- $x23 \le x6$
- $x6 \le x14$
- $x1 \le x5$

At-most-one groups:

- $\sum_{x \in \{x2, x4\}} x \le 1$ (A1)
- $\sum_{x \in \{x26, x28\}} x \le 1$ (A2)
- $\sum_{x \in \{x2, x7\}} x \le 1$ (A3)

Cardinality constraints:

- $\sum_{x \in \{x18, x19, x20\}} x \le 1$ (K1)
- $\sum_{x \in \{x18, x20, x22\}} x \le 2$ (K2)

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

