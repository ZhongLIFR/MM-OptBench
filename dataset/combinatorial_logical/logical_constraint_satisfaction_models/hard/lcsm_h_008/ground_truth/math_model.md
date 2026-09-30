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

- $V = \{x1, x2, x3, x4, x5, x6, x7, x8, x9, x10, x11, x12, x13, x14, x15, x16, x17, x18, x19, x20, x21, x22, x23, x24, x25, x26, x27, x28, x29, x30, x31, x32, x33, x34, x35\}$
- $C = \{C1, C2, C3, C4, C5, C6, C7, C8, C9, C10, C11, C12, C13, C14, C15, C16, C17, C18, C19, C20, C21, C22, C23, C24, C25, C26, C27, C28, C29, C30, C31, C32, C33, C34, C35, C36, C37, C38, C39, C40, C41, C42, C43, C44, C45, C46, C47, C48, C49, C50, C51, C52, C53, C54, C55, C56, C57, C58, C59, C60, C61, C62, C63, C64, C65, C66, C67, C68, C69, C70, C71\}$

## Parameters

- For each clause $c \in C$, let $L_c^+$ denote the variables appearing positively and let $L_c^-$ denote the variables appearing negatively.
- For each implication $(u,v) \in P$, the logical condition is $u \le v$.
- For each at-most-one group $g \in G$, at most one variable in that group may take value 1.
- For each cardinality constraint $k \in K$, at most $b_k$ variables in its designated subset may take value 1.

For this instance, the clauses are:

- $C1: (x21 \lor x27)$
- $C2: (\neg x3 \lor \neg x10)$
- $C3: (\neg x5 \lor x18)$
- $C4: (x14 \lor \neg x15)$
- $C5: (x12 \lor \neg x13 \lor \neg x14)$
- $C6: (\neg x22 \lor \neg x24)$
- $C7: (\neg x31 \lor x33 \lor x34 \lor \neg x35)$
- $C8: (\neg x23 \lor \neg x26 \lor \neg x27)$
- $C9: (x1 \lor x9 \lor \neg x22)$
- $C10: (x2 \lor x3 \lor \neg x4)$
- $C11: (x16 \lor x17 \lor x21)$
- $C12: (\neg x16 \lor \neg x19)$
- $C13: (x30 \lor \neg x32 \lor x33)$
- $C14: (\neg x3 \lor x5)$
- $C15: (\neg x9 \lor x10)$
- $C16: (x9 \lor \neg x13 \lor x14)$
- $C17: (\neg x30 \lor \neg x31 \lor x33)$
- $C18: (\neg x12 \lor x13)$
- $C19: (x1 \lor \neg x2 \lor x6)$
- $C20: (\neg x18 \lor \neg x19)$
- $C21: (x11 \lor \neg x13)$
- $C22: (x20 \lor \neg x28)$
- $C23: (x15 \lor \neg x16 \lor \neg x19)$
- $C24: (x3 \lor \neg x4 \lor x6)$
- $C25: (x11 \lor x13)$
- $C26: (\neg x34 \lor \neg x35)$
- $C27: (\neg x16 \lor \neg x30)$
- $C28: (\neg x5 \lor \neg x7)$
- $C29: (x6 \lor \neg x28)$
- $C30: (x4 \lor \neg x12 \lor x31)$
- $C31: (\neg x29 \lor x31 \lor x34)$
- $C32: (x29 \lor \neg x34)$
- $C33: (\neg x10 \lor x14 \lor x15)$
- $C34: (x25 \lor \neg x27 \lor \neg x28)$
- $C35: (x29 \lor \neg x32 \lor \neg x33)$
- $C36: (x29 \lor \neg x33 \lor \neg x35)$
- $C37: (\neg x15 \lor \neg x18)$
- $C38: (\neg x15 \lor x17 \lor \neg x18)$
- $C39: (\neg x29 \lor \neg x30)$
- $C40: (x5 \lor x7)$
- $C41: (x24 \lor \neg x27 \lor x28)$
- $C42: (x8 \lor x14)$
- $C43: (x8 \lor \neg x19 \lor \neg x23)$
- $C44: (\neg x15 \lor \neg x17 \lor x18)$
- $C45: (x9 \lor \neg x11 \lor \neg x13)$
- $C46: (x19 \lor \neg x29)$
- $C47: (x22 \lor x24 \lor \neg x28)$
- $C48: (\neg x2 \lor x4)$
- $C49: (\neg x10 \lor \neg x11 \lor \neg x14)$
- $C50: (\neg x8 \lor x13 \lor x14)$
- $C51: (\neg x25 \lor x28)$
- $C52: (x17 \lor \neg x19)$
- $C53: (x16 \lor \neg x19 \lor x29)$
- $C54: (\neg x16 \lor x17 \lor \neg x18)$
- $C55: (x15 \lor x18)$
- $C56: (x31 \lor \neg x34 \lor \neg x35)$
- $C57: (x15 \lor x17 \lor x26)$
- $C58: (\neg x22 \lor x23)$
- $C59: (\neg x30 \lor x31 \lor x35)$
- $C60: (\neg x23 \lor x26 \lor x27)$
- $C61: (x3 \lor \neg x27 \lor \neg x33)$
- $C62: (\neg x15 \lor x17)$
- $C63: (x30 \lor x31 \lor x34 \lor \neg x35)$
- $C64: (\neg x22 \lor \neg x32)$
- $C65: (x24 \lor \neg x25 \lor \neg x27 \lor x28)$
- $C66: (\neg x9 \lor x10 \lor \neg x13)$
- $C67: (\neg x22 \lor x23 \lor x25)$
- $C68: (\neg x1 \lor x3 \lor x6)$
- $C69: (x23 \lor \neg x24 \lor \neg x28)$
- $C70: (x10 \lor x11)$
- $C71: (\neg x2 \lor x6)$

Implication constraints:

- $x18 \le x26$
- $x26 \le x8$
- $x8 \le x27$
- $x27 \le x14$
- $x14 \le x7$
- $x7 \le x32$
- $x32 \le x24$
- $x24 \le x11$
- $x11 \le x35$
- $x35 \le x21$

At-most-one groups:

- $\sum_{x \in \{x8, x10\}} x \le 1$ (A1)
- $\sum_{x \in \{x9, x13\}} x \le 1$ (A2)
- $\sum_{x \in \{x9, x13, x14\}} x \le 1$ (A3)
- $\sum_{x \in \{x25, x26, x28\}} x \le 1$ (A4)

Cardinality constraints:

- $\sum_{x \in \{x22, x23, x24, x25, x26, x27\}} x \le 3$ (K1)
- $\sum_{x \in \{x29, x31, x32, x34, x35\}} x \le 2$ (K2)

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

