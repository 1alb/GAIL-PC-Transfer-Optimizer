"""
Transfer resolution solver for the simplified no-buffer-stock optimization flow.
Uses OR-Tools CP-SAT to reduce the active transfer graph into required shipments.
"""

from collections import defaultdict
from typing import Dict, List
from ortools.sat.python import cp_model

from app.models.request_models import Transfer
from app.models.response_models import ShipmentResolution


class TransferResolutionSolver:
    """Resolves a directed transfer graph into aggregated shipment requirements."""

    def __init__(self, transfers: List[Transfer]) -> None:
        self.transfers: List[Transfer] = [
            transfer for transfer in transfers if transfer.from_location != transfer.to_location
        ]

    def _compute_net_balances(self) -> Dict[str, int]:
        net_balance: Dict[str, int] = defaultdict(int)
        for transfer in self.transfers:
            net_balance[transfer.from_location] -= 1
            net_balance[transfer.to_location] += 1
        return net_balance

    def solve(self) -> List[ShipmentResolution]:
        if not self.transfers:
            return []

        net_balance = self._compute_net_balances()
        supplies = {node: -qty for node, qty in net_balance.items() if qty < 0}
        demands = {node: qty for node, qty in net_balance.items() if qty > 0}

        if not supplies or not demands:
            return []

        if sum(supplies.values()) != sum(demands.values()):
            raise ValueError("Invalid transfer graph: supply and demand are unbalanced.")

        supply_nodes = sorted(supplies)
        demand_nodes = sorted(demands)
        node_index: Dict[str, int] = {node: idx for idx, node in enumerate(sorted(set(supply_nodes + demand_nodes)))}

        model = cp_model.CpModel()
        flow_vars = {}
        for source in supply_nodes:
            for dest in demand_nodes:
                max_flow = min(supplies[source], demands[dest])
                flow_vars[(source, dest)] = model.NewIntVar(0, max_flow, f"flow_{source}_{dest}")

        for source in supply_nodes:
            model.Add(sum(flow_vars[(source, dest)] for dest in demand_nodes) == supplies[source])

        for dest in demand_nodes:
            model.Add(sum(flow_vars[(source, dest)] for source in supply_nodes) == demands[dest])

        obj_terms = []
        for source in supply_nodes:
            for dest in demand_nodes:
                source_idx = node_index[source]
                dest_idx = node_index[dest]
                cost = source_idx * 1000 + dest_idx
                obj_terms.append(cost * flow_vars[(source, dest)])

        model.Minimize(sum(obj_terms))

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 5.0
        status = solver.Solve(model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            raise ValueError("OR-Tools solver failed to compute an optimal shipment plan.")

        shipments: List[ShipmentResolution] = []
        for source in supply_nodes:
            for dest in demand_nodes:
                flow = solver.Value(flow_vars[(source, dest)])
                if flow > 0:
                    shipments.append(
                        ShipmentResolution(
                            from_location=source,
                            to_location=dest,
                            quantity=flow,
                        )
                    )

        return sorted(shipments, key=lambda item: (item.from_location, item.to_location))
