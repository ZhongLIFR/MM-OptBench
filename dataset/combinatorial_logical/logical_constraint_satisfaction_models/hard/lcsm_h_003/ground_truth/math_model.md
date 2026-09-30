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

- $V = \{x1, x2, x3, x4, x5, x6, x7, x8, x9, x10, x11, x12, x13, x14, x15, x16, x17, x18, x19, x20, x21, x22, x23, x24, x25, x26, x27, x28, x29, x30\}$
- $C = \{C1, C2, C3, C4, C5, C6, C7, C8, C9, C10, C11, C12, C13, C14, C15, C16, C17, C18, C19, C20, C21, C22, C23, C24, C25, C26, C27, C28, C29, C30, C31, C32, C33, C34, C35, C36, C37, C38, C39, C40, C41, C42, C43, C44, C45, C46, C47, C48, C49, C50, C51, C52, C53, C54, C55, C56, C57, C58, C59, C60\}$

## Parameters

- For each clause $c \in C$, let $L_c^+$ denote the variables appearing positively and let $L_c^-$ denote the variables appearing negatively.
- For each implication $(u,v) \in P$, the logical condition is $u \le v$.
- For each at-most-one group $g \in G$, at most one variable in that group may take value 1.
- For each cardinality constraint $k \in K$, at most $b_k$ variables in its designated subset may take value 1.

For this instance, the clauses are:

- $C1: (x6 \lor x7)$
- $C2: (\neg x1 \lor \neg x20)$
- $C3: (\neg x10 \lor x17)$
- $C4: (\neg x22 \lor x23)$
- $C5: (\neg x25 \lor \neg x28 \lor \neg x29)$
- $C6: (x22 \lor \neg x23)$
- $C7: (\neg x10 \lor x14 \lor x24)$
- $C8: (x3 \lor x4 \lor \neg x8)$
- $C9: (\neg x24 \lor \neg x25)$
- $C10: (x12 \lor \neg x13 \lor x14)$
- $C11: (\neg x3 \lor x19)$
- $C12: (\neg x17 \lor x18 \lor x21)$
- $C13: (\neg x23 \lor x24)$
- $C14: (\neg x3 \lor x4)$
- $C15: (\neg x26 \lor x28 \lor \neg x29)$
- $C16: (x25 \lor \neg x27)$
- $C17: (x3 \lor \neg x5)$
- $C18: (\neg x24 \lor x27 \lor \neg x28)$
- $C19: (x25 \lor \neg x30)$
- $C20: (\neg x14 \lor \neg x29)$
- $C21: (x24 \lor x27)$
- $C22: (x5 \lor \neg x6 \lor \neg x8)$
- $C23: (\neg x1 \lor \neg x4)$
- $C24: (\neg x11 \lor \neg x14 \lor x15)$
- $C25: (\neg x6 \lor \neg x10)$
- $C26: (\neg x22 \lor \neg x23)$
- $C27: (x3 \lor x6 \lor \neg x7)$
- $C28: (x10 \lor \neg x11 \lor x12)$
- $C29: (x25 \lor \neg x26 \lor x30)$
- $C30: (\neg x17 \lor \neg x20 \lor x23)$
- $C31: (x25 \lor \neg x26)$
- $C32: (\neg x17 \lor x18 \lor x22)$
- $C33: (x19 \lor \neg x20 \lor x23)$
- $C34: (x11 \lor x12)$
- $C35: (x4 \lor \neg x6)$
- $C36: (\neg x3 \lor x6 \lor \neg x8)$
- $C37: (\neg x13 \lor x14)$
- $C38: (\neg x25 \lor x27 \lor x29)$
- $C39: (\neg x1 \lor x6 \lor \neg x16 \lor \neg x30)$
- $C40: (x24 \lor x29 \lor \neg x30)$
- $C41: (x25 \lor \neg x28)$
- $C42: (x12 \lor x21)$
- $C43: (\neg x8 \lor x23 \lor \neg x24)$
- $C44: (\neg x24 \lor x28)$
- $C45: (\neg x20 \lor \neg x23)$
- $C46: (x17 \lor \neg x20 \lor x21)$
- $C47: (\neg x3 \lor x14 \lor \neg x16)$
- $C48: (\neg x12 \lor x13 \lor x15)$
- $C49: (\neg x9 \lor x11 \lor x15)$
- $C50: (\neg x18 \lor x19 \lor \neg x20)$
- $C51: (x17 \lor \neg x18)$
- $C52: (\neg x4 \lor \neg x5 \lor x8)$
- $C53: (x17 \lor x20 \lor x23)$
- $C54: (x7 \lor \neg x17 \lor x18)$
- $C55: (x24 \lor x26)$
- $C56: (x10 \lor x11 \lor \neg x15)$
- $C57: (\neg x17 \lor x19)$
- $C58: (\neg x9 \lor x10 \lor \neg x13)$
- $C59: (\neg x10 \lor \neg x14 \lor x15)$
- $C60: (x14 \lor \neg x16)$

Implication constraints:

- $x7 \le x8$
- $x8 \le x19$
- $x19 \le x4$
- $x4 \le x28$
- $x28 \le x14$
- $x14 \le x17$
- $x17 \le x13$
- $x13 \le x2$

At-most-one groups:

- $\sum_{x \in \{x19, x20\}} x \le 1$ (A1)
- $\sum_{x \in \{x24, x26, x29\}} x \le 1$ (A2)
- $\sum_{x \in \{x18, x20, x22\}} x \le 1$ (A3)

Cardinality constraints:

- $\sum_{x \in \{x1, x2, x3, x4, x5\}} x \le 4$ (K1)
- $\sum_{x \in \{x17, x19, x20, x21, x23\}} x \le 2$ (K2)

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

