# Problem Overview

A single depot must replenish customer inventories over a finite horizon. In each period, at most one vehicle may be dispatched. If dispatched, it starts at the depot, visits a subset of customers, and returns to the depot in the same period. Deliveries interact with customer-level inventory balance and with routing cost.

# Sets and Indices

- $T$: planning periods. For this instance, $T = ['t1', 't2', 't3', 't4', 't5', 't6']$.
- $C$: customers. For this instance, $C = ['C1', 'C2', 'C3', 'C4', 'C5', 'C6']$.
- $N$: nodes consisting of the depot and all customers.
- $0$: depot node.

# Parameters

- $d_{c,t}$: demand of customer $c$ in period $t$.
- $I_c^0$: initial inventory at customer $c$ before period $t_1$.
- $U_c$: maximum inventory capacity at customer $c$.
- $h_c$: unit holding cost charged on end-of-period inventory of customer $c$.
- $Q$: vehicle capacity available in every period.
- $f$: fixed dispatch cost incurred when the vehicle is used in a period.
- $a_{ij}$: routing cost of traveling directly from node $i$ to node $j$.
- $M_{c,t}$: delivery upper bound used to link delivery quantity and visit indicator.

# Decision Variables

- $x_{i,j,t} \in \{0,1\}$: equals 1 if the route uses directed arc $(i,j)$ in period $t$.
- $z_{c,t} \in \{0,1\}$: equals 1 if customer $c$ is visited in period $t$.
- $q_{c,t} \ge 0$: quantity delivered to customer $c$ in period $t$.
- $I_{c,t} \ge 0$: end-of-period inventory of customer $c$ after demand in period $t$ is satisfied.
- $y_t \in \{0,1\}$: equals 1 if the vehicle is dispatched in period $t$.
- $u_{c,t} \ge 0$: route-order variable used in MTZ subtour elimination.

# Objective Function

Minimize total routing, holding, and dispatch cost:

$$
\min \sum_{t \in T} \sum_{i \in N} \sum_{j \in N, j \ne i} a_{ij} x_{i,j,t} + \sum_{t \in T} \sum_{c \in C} h_c I_{c,t} + \sum_{t \in T} f y_t
$$

# Constraints

Inventory balance for every customer and period:

$$
I_c^0 + q_{c,t_1} = d_{c,t_1} + I_{c,t_1} \quad \forall c \in C,
$$

$$
I_{c,t^-} + q_{c,t} = d_{c,t} + I_{c,t} \quad \forall c \in C,\ t \in T \setminus \{t_1\},
$$

Inventory capacity:

$$
I_{c,t} \le U_c \quad \forall c \in C,\ t \in T.
$$

Delivery only when visited:

$$
q_{c,t} \le M_{c,t} z_{c,t} \quad \forall c \in C,\ t \in T.
$$

Vehicle capacity:

$$
\sum_{c \in C} q_{c,t} \le Q y_t \quad \forall t \in T.
$$

Single departure and single return when the vehicle is used:

$$
\sum_{j \in C} x_{0,j,t} = y_t \quad \forall t \in T,
$$

$$
\sum_{i \in C} x_{i,0,t} = y_t \quad \forall t \in T.
$$

Visit-flow consistency:

$$
\sum_{i \in N \setminus \{c\}} x_{i,c,t} = z_{c,t} \quad \forall c \in C,\ t \in T,
$$

$$
\sum_{j \in N \setminus \{c\}} x_{c,j,t} = z_{c,t} \quad \forall c \in C,\ t \in T.
$$

Visits only when dispatched:

$$
z_{c,t} \le y_t \quad \forall c \in C,\ t \in T.
$$

MTZ subtour elimination for each period:

$$
u_{c,t} \ge z_{c,t}, \quad u_{c,t} \le |C| z_{c,t} \quad \forall c \in C,\ t \in T,
$$

$$
u_{i,t} - u_{j,t} + |C| x_{i,j,t} \le |C|-1 + |C|(1-z_{i,t}) + |C|(1-z_{j,t})
\quad \forall i \ne j \in C,\ t \in T.
$$

# Complete Model

The complete deterministic mixed-integer linear program is the objective above together with inventory balance, inventory capacity, delivery-visit linking, per-period vehicle capacity, depot departure and return equalities, visit-flow conservation, dispatch-visit coupling, MTZ subtour elimination, and the binary / continuous variable domains.

# Instance-Specific Notes

- This instance has 6 periods and 6 customers.
- Vehicle capacity is 11 units per period.
- Fixed dispatch cost is 0.00.
- Demand regime: `large_single_peak`.
- Holding-cost regime: `mixed_customer_specific`.
- Vehicle-capacity regime: `peak_binding`.
- Routing cost is induced by displayed coordinates using Euclidean distance rounded to two decimals.
- All instance-specific numerical values are stored in `ground_truth/instance_data.json` and are mirrored in the textual specification and visuals.
