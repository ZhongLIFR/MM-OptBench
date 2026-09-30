# Problem Overview

A single depot must replenish customer inventories over a finite horizon. In each period, one or more identical vehicles may be dispatched. Every dispatched vehicle starts at the depot, visits a subset of customers, and returns to the depot in the same period. Routing cost, vehicle-capacity usage, and inter-period inventory carry-over interact directly.

# Sets and Indices

- $T$: planning periods. For this instance, $T = ['t1', 't2', 't3', 't4', 't5', 't6', 't7', 't8', 't9']$.
- $C$: customers. For this instance, $C = ['C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9']$.
- $V$: vehicles. For this instance, $V = ['V1']$.
- $N$: nodes consisting of the depot and all customers.
- $0$: depot node.

# Parameters

- $d_{c,t}$: demand of customer $c$ in period $t$.
- $I_c^0$: initial inventory at customer $c$ before period $t_1$.
- $U_c$: maximum inventory capacity at customer $c$.
- $h_c$: unit holding cost charged on end-of-period inventory of customer $c$.
- $Q_v$: capacity of vehicle $v$ in every period.
- $f_v$: dispatch cost incurred when vehicle $v$ is used in a period.
- $a_{ij}$: routing cost of traveling directly from node $i$ to node $j$.
- $M_{c,t}$: delivery upper bound used to link delivery quantity and visit indicator.

# Decision Variables

- $x_{i,j,v,t} \in \{0,1\}$: equals 1 if vehicle $v$ uses directed arc $(i,j)$ in period $t$.
- $z_{c,v,t} \in \{0,1\}$: equals 1 if vehicle $v$ visits customer $c$ in period $t$.
- $q_{c,v,t} \ge 0$: quantity delivered by vehicle $v$ to customer $c$ in period $t$.
- $I_{c,t} \ge 0$: end-of-period inventory of customer $c$ after demand in period $t$ is satisfied.
- $y_{v,t} \in \{0,1\}$: equals 1 if vehicle $v$ is dispatched in period $t$.
- $u_{c,v,t} \ge 0$: route-order variable used in MTZ subtour elimination.

# Objective Function

Minimize total routing, holding, and dispatch cost:

$$
\min \sum_{t \in T} \sum_{v \in V} \sum_{i \in N} \sum_{j \in N, j \ne i} a_{ij} x_{i,j,v,t} + \sum_{t \in T} \sum_{c \in C} h_c I_{c,t} + \sum_{t \in T} \sum_{v \in V} f_v y_{v,t}
$$

# Constraints

Inventory balance for every customer and period:

$$
I_c^0 + \sum_{v \in V} q_{c,v,t_1} = d_{c,t_1} + I_{c,t_1} \quad \forall c \in C,
$$

$$
I_{c,t^-} + \sum_{v \in V} q_{c,v,t} = d_{c,t} + I_{c,t} \quad \forall c \in C,\ t \in T \setminus \{t_1\},
$$

Inventory capacity:

$$
I_{c,t} \le U_c \quad \forall c \in C,\ t \in T.
$$

Delivery only when visited:

$$
q_{c,v,t} \le M_{c,t} z_{c,v,t} \quad \forall c \in C,\ v \in V,\ t \in T.
$$

At most one vehicle may serve the same customer in the same period:

$$
\sum_{v \in V} z_{c,v,t} \le 1 \quad \forall c \in C,\ t \in T.
$$

Vehicle capacity:

$$
\sum_{c \in C} q_{c,v,t} \le Q_v y_{v,t} \quad \forall v \in V,\ t \in T.
$$

Single departure and single return for each used vehicle:

$$
\sum_{j \in C} x_{0,j,v,t} = y_{v,t} \quad \forall v \in V,\ t \in T,
$$

$$
\sum_{i \in C} x_{i,0,v,t} = y_{v,t} \quad \forall v \in V,\ t \in T.
$$

Visit-flow consistency for every vehicle and period:

$$
\sum_{i \in N \setminus \{c\}} x_{i,c,v,t} = z_{c,v,t} \quad \forall c \in C,\ v \in V,\ t \in T,
$$

$$
\sum_{j \in N \setminus \{c\}} x_{c,j,v,t} = z_{c,v,t} \quad \forall c \in C,\ v \in V,\ t \in T.
$$

Visits only when the vehicle is dispatched:

$$
z_{c,v,t} \le y_{v,t} \quad \forall c \in C,\ v \in V,\ t \in T.
$$

MTZ subtour elimination for each vehicle and period:

$$
u_{c,v,t} \ge z_{c,v,t}, \quad u_{c,v,t} \le |C| z_{c,v,t} \quad \forall c \in C,\ v \in V,\ t \in T,
$$

$$
u_{i,v,t} - u_{j,v,t} + |C| x_{i,j,v,t} \le |C|-1 + |C|(1-z_{i,v,t}) + |C|(1-z_{j,v,t})
\quad \forall i \ne j \in C,\ v \in V,\ t \in T.
$$

# Complete Model

The complete deterministic mixed-integer linear program is the objective above together with inventory balance, inventory capacity, delivery-visit linking, at-most-one-vehicle-per-customer-per-period, per-vehicle capacity, depot departure and return equalities, visit-flow conservation, dispatch-visit coupling, MTZ subtour elimination, and the binary / continuous variable domains.

# Instance-Specific Notes

- This instance has 9 periods, 9 customers, and 1 vehicles.
- Per-vehicle capacity is 14.
- Per-vehicle dispatch cost is 0.00.
- Demand regime: `mixed_route_aware_peaks`.
- Holding-cost regime: `moderate_mixed`.
- Vehicle-capacity regime: `moderate_slack`.
- Routing-layout regime: `upper_arc_with_long_tail`.
- Routing cost is induced by displayed coordinates using Euclidean distance rounded to two decimals.
- All instance-specific numerical values are stored in `ground_truth/instance_data.json` and mirrored in the textual specification and visuals.
