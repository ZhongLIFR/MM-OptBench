# Mathematical Model: Logical Constraint Satisfaction Problem

## Problem Overview

This instance is a deterministic easy-level logical constraint satisfaction problem.

A set of Boolean decision variables is given together with three types of logical restrictions: CNF clauses, simple implication constraints, and small at-most-one groups. The task is to find any binary assignment that satisfies all listed logical constraints. This is therefore a pure feasibility problem.

## Sets and Indices

- $V$: set of Boolean variables
- $C$: set of clause rows in the clause-variable matrix
- $G$: set of at-most-one groups
- $P$: set of implication constraints

For this instance:

- $V = \{x1, x2, x3, x4, x5, x6, x7, x8, x9, x10, x11, x12\}$
- $C = \{C1, C2, C3, C4, C5, C6, C7, C8, C9, C10, C11, C12, C13, C14, C15, C16, C17, C18, C19, C20\}$

## Parameters

- For each clause $c \in C$, let $L_c^+$ denote the variables appearing positively and let $L_c^-$ denote the variables appearing negatively.
- For each implication $(u,v) \in P$, the logical condition is $u \le v$.
- For each at-most-one group $g \in G$, at most one variable in that group may take value 1.

For this instance, the clauses are:

- $C1: (x2 \lor x11)$
- $C2: (\neg x6 \lor \neg x12)$
- $C3: (x1 \lor x4)$
- $C4: (\neg x1 \lor x12)$
- $C5: (x4 \lor x5 \lor x6)$
- $C6: (x7 \lor \neg x8 \lor x12)$
- $C7: (\neg x1 \lor x3)$
- $C8: (x1 \lor x10 \lor \neg x12)$
- $C9: (x2 \lor x6)$
- $C10: (x8 \lor \neg x10)$
- $C11: (x2 \lor \neg x3)$
- $C12: (\neg x7 \lor x11)$
- $C13: (x1 \lor x4 \lor \neg x5)$
- $C14: (x10 \lor \neg x11)$
- $C15: (\neg x8 \lor x10 \lor x11)$
- $C16: (\neg x8 \lor x10)$
- $C17: (x8 \lor \neg x9)$
- $C18: (\neg x2 \lor x3)$
- $C19: (x1 \lor \neg x2 \lor x4)$
- $C20: (x7 \lor \neg x9 \lor x11)$

Implication constraints:

- $x2 \le x11$
- $x7 \le x11$

At-most-one groups:

- $\sum_{x \in \{x1, x4\}} x \le 1$ (A1)

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

### 4. Binary domains

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
& x_i \in \{0,1\} && \forall i \in V.
\end{aligned}
\]

## Instance-Specific Notes

This instance uses the official easy-level clause-variable matrix visual format for logical constraint satisfaction. The matrix contains one row per clause and one column per Boolean variable, with '+' for positive literals, '−' for negative literals, and '.' for absent entries. Additional matrix rows labeled I* encode implication constraints, and rows labeled A* encode pairwise exclusions induced by at-most-one groups. All instance-specific structural data are fully recorded in `instance_data.json` and `canonical_specification.txt`, and are visually encoded in `visual_0.png` without revealing a satisfying assignment.

