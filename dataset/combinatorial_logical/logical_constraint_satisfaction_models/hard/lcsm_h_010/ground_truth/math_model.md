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

- $V = \{x1, x2, x3, x4, x5, x6, x7, x8, x9, x10, x11, x12, x13, x14, x15, x16, x17, x18, x19, x20, x21, x22, x23, x24, x25, x26, x27, x28, x29, x30, x31, x32, x33, x34, x35, x36, x37, x38\}$
- $C = \{C1, C2, C3, C4, C5, C6, C7, C8, C9, C10, C11, C12, C13, C14, C15, C16, C17, C18, C19, C20, C21, C22, C23, C24, C25, C26, C27, C28, C29, C30, C31, C32, C33, C34, C35, C36, C37, C38, C39, C40, C41, C42, C43, C44, C45, C46, C47, C48, C49, C50, C51, C52, C53, C54, C55, C56, C57, C58, C59, C60, C61, C62, C63, C64, C65, C66, C67, C68, C69, C70, C71, C72, C73, C74, C75\}$

## Parameters

- For each clause $c \in C$, let $L_c^+$ denote the variables appearing positively and let $L_c^-$ denote the variables appearing negatively.
- For each implication $(u,v) \in P$, the logical condition is $u \le v$.
- For each at-most-one group $g \in G$, at most one variable in that group may take value 1.
- For each cardinality constraint $k \in K$, at most $b_k$ variables in its designated subset may take value 1.

For this instance, the clauses are:

- $C1: (x19 \lor x30)$
- $C2: (\neg x16 \lor \neg x34)$
- $C3: (\neg x13 \lor x20)$
- $C4: (x33 \lor x34 \lor \neg x37)$
- $C5: (x6 \lor \neg x9 \lor \neg x37)$
- $C6: (x35 \lor x37 \lor x38)$
- $C7: (x3 \lor \neg x9)$
- $C8: (x27 \lor \neg x28 \lor x29)$
- $C9: (\neg x25 \lor x30 \lor \neg x31)$
- $C10: (\neg x6 \lor \neg x15)$
- $C11: (x12 \lor x15 \lor \neg x28)$
- $C12: (x4 \lor \neg x7 \lor \neg x8)$
- $C13: (\neg x21 \lor x27)$
- $C14: (\neg x11 \lor \neg x13)$
- $C15: (\neg x32 \lor \neg x33 \lor \neg x35)$
- $C16: (\neg x9 \lor x12 \lor \neg x13)$
- $C17: (x26 \lor \neg x27)$
- $C18: (x18 \lor x23 \lor x36)$
- $C19: (\neg x9 \lor x12 \lor x16)$
- $C20: (\neg x4 \lor x6 \lor \neg x8)$
- $C21: (\neg x17 \lor x19 \lor x20)$
- $C22: (x10 \lor \neg x12)$
- $C23: (\neg x32 \lor x34)$
- $C24: (x25 \lor x29 \lor x31)$
- $C25: (x17 \lor x19 \lor \neg x21)$
- $C26: (x26 \lor x27 \lor x31)$
- $C27: (\neg x11 \lor \neg x12)$
- $C28: (\neg x17 \lor x20 \lor \neg x37)$
- $C29: (\neg x35 \lor \neg x37 \lor x38)$
- $C30: (x3 \lor \neg x32)$
- $C31: (x3 \lor \neg x29 \lor \neg x36)$
- $C32: (x1 \lor x2 \lor x6)$
- $C33: (\neg x20 \lor \neg x23 \lor x24)$
- $C34: (x33 \lor \neg x36 \lor x37)$
- $C35: (x33 \lor \neg x34 \lor x35)$
- $C36: (\neg x2 \lor x6 \lor x7)$
- $C37: (\neg x19 \lor x23 \lor \neg x24)$
- $C38: (x4 \lor \neg x26 \lor \neg x34)$
- $C39: (x3 \lor \neg x12 \lor \neg x36)$
- $C40: (\neg x26 \lor x27)$
- $C41: (\neg x19 \lor x20 \lor x21)$
- $C42: (\neg x6 \lor x8)$
- $C43: (\neg x11 \lor x13 \lor \neg x16)$
- $C44: (x12 \lor \neg x16)$
- $C45: (\neg x2 \lor x6 \lor \neg x8)$
- $C46: (x9 \lor \neg x15 \lor \neg x16)$
- $C47: (\neg x19 \lor x21)$
- $C48: (x17 \lor x23)$
- $C49: (\neg x3 \lor x9 \lor x23)$
- $C50: (x11 \lor x12 \lor \neg x13)$
- $C51: (x24 \lor \neg x34)$
- $C52: (x26 \lor \neg x29 \lor \neg x30)$
- $C53: (\neg x32 \lor x35)$
- $C54: (\neg x1 \lor x3 \lor x5 \lor x6)$
- $C55: (x17 \lor x24)$
- $C56: (x34 \lor \neg x36 \lor \neg x38)$
- $C57: (\neg x33 \lor x37 \lor x38)$
- $C58: (\neg x15 \lor x33 \lor \neg x36)$
- $C59: (x1 \lor \neg x7 \lor x26)$
- $C60: (x30 \lor \neg x31)$
- $C61: (\neg x12 \lor x24 \lor \neg x37)$
- $C62: (\neg x1 \lor x25 \lor x33)$
- $C63: (\neg x9 \lor x11 \lor x12)$
- $C64: (x11 \lor x13)$
- $C65: (x27 \lor \neg x29 \lor \neg x31)$
- $C66: (x5 \lor x8)$
- $C67: (x2 \lor x4 \lor x5)$
- $C68: (x28 \lor \neg x29)$
- $C69: (\neg x32 \lor x34 \lor \neg x36)$
- $C70: (\neg x32 \lor x34 \lor \neg x35 \lor \neg x37)$
- $C71: (x29 \lor x31)$
- $C72: (\neg x12 \lor x16)$
- $C73: (\neg x3 \lor x4 \lor \neg x8)$
- $C74: (x26 \lor x29)$
- $C75: (x11 \lor \neg x21 \lor \neg x37)$

Implication constraints:

- $x15 \le x27$
- $x27 \le x38$
- $x38 \le x17$
- $x17 \le x26$
- $x26 \le x18$
- $x18 \le x33$
- $x33 \le x28$
- $x28 \le x30$
- $x30 \le x10$
- $x10 \le x25$
- $x25 \le x7$

At-most-one groups:

- $\sum_{x \in \{x3, x6\}} x \le 1$ (A1)
- $\sum_{x \in \{x17, x23\}} x \le 1$ (A2)
- $\sum_{x \in \{x32, x38\}} x \le 1$ (A3)
- $\sum_{x \in \{x20, x23, x24\}} x \le 1$ (A4)

Cardinality constraints:

- $\sum_{x \in \{x1, x2, x6\}} x \le 2$ (K1)
- $\sum_{x \in \{x9, x10, x12, x14, x15, x16\}} x \le 2$ (K2)

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

