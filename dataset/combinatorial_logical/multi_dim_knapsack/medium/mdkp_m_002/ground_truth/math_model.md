# Mathematical Model: Multi-Dimensional Knapsack Problem

## Problem Overview

This instance is a deterministic 0--1 Multi-Dimensional Knapsack Problem (MDKP).

A set of candidate items is available for selection. Each item contributes an item-specific value if selected and consumes resource in each of several resource dimensions. A feasible solution selects a subset of items such that total consumption in every resource dimension does not exceed the corresponding capacity. The objective is to maximize the total value of the selected items.

## Sets and Indices

- $I$: set of items
- $R$: set of resource dimensions

For this instance:

- $I = \{1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28\}$
- $R = \{R1, R2, R3\}$

## Parameters

- $p_i$: value of item $i$
- $w_{i,r}$: resource consumption of item $i$ in dimension $r$
- $C_r$: capacity of resource dimension $r$

## Decision Variables

- $x_i \in \{0,1\}$: equals 1 if item $i$ is selected, and 0 otherwise

## Objective Function

Maximize the total value of selected items:

\[
\max \; \sum_{i \in I} p_i x_i
\]

## Constraints

### 1. Resource-capacity constraints

For every resource dimension $r \in R$:

\[
\sum_{i \in I} w_{i,r} x_i \le C_r
\]

### 2. Binary selection domains

\[
x_i \in \{0,1\} \qquad \forall i \in I
\]

## Complete Model

\[
\begin{aligned}
\max \quad & \sum_{i \in I} p_i x_i \\
\text{s.t.} \quad
& \sum_{i \in I} w_{i,r} x_i \le C_r && \forall r \in R, \\
& x_i \in \{0,1\} && \forall i \in I.
\end{aligned}
\]

## Instance-Specific Notes

This instance uses the official medium-level bar-based visual format for MDKP. The figure contains one row per item, numeric item identifiers, one displayed value per item, segmented per-resource usage bars, and separate resource-limit bars. All instance-specific numerical data needed to solve the instance are fully recorded in `instance_data.json` and `canonical_specification.txt`, and are visually encoded in `visual_0.png` without revealing the optimal subset.
