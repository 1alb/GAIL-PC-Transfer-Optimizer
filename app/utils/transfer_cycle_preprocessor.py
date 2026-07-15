from typing import Any, Dict, List, Tuple

from app.models.request_models import Transfer


class ResolvedTransferInfo(dict):
    """A lightweight object that supports both dict-style and attribute-style access."""

    def __getattr__(self, item: str) -> Any:
        try:
            return self[item]
        except KeyError as exc:
            raise AttributeError(item) from exc


def preprocess_transfer_cycles(transfers: List[Transfer]) -> Tuple[List[Transfer], List[Dict[str, Any]]]:
    """Separate employee transfer cycles that do not require any PC movement from active transfers."""
    active_transfers, resolved_cycles, resolved_details = preprocess_transfer_cycles_with_details(transfers)
    return active_transfers, resolved_details


def _get_transfer_source(transfer: Any) -> str:
    return getattr(transfer, "from_location", None) or getattr(transfer, "source_plant_id", None) or getattr(transfer, "source_plant", "")


def _get_transfer_destination(transfer: Any) -> str:
    return getattr(transfer, "to_location", None) or getattr(transfer, "destination_plant_id", None) or getattr(transfer, "destination_plant", "")


def _get_transfer_name(transfer: Any) -> str:
    return getattr(transfer, "employee_name", None) or getattr(transfer, "name", "")


def preprocess_transfer_cycles_with_details(
    transfers: List[Transfer],
) -> Tuple[List[Transfer], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Separate cycles and also return grouped payloads for API responses."""
    if not transfers:
        return [], [], []

    adjacency: Dict[str, List[Transfer]] = {}
    all_nodes = set()
    self_loop_resolved: List[Dict[str, Any]] = []
    resolved_transfer_ids: set[str] = set()
    resolved_cycles: List[Dict[str, Any]] = []

    for transfer in transfers:
        source = _get_transfer_source(transfer)
        destination = _get_transfer_destination(transfer)
        if source == destination:
            resolved_transfer_ids.add(transfer.employee_id)
            self_loop_resolved.append(
                {
                    "cycle_id": f"self-{transfer.employee_id}",
                    "cycle_length": 1,
                    "transfers": [
                        {
                            "transfer_id": getattr(transfer, "transfer_id", transfer.employee_id),
                            "employee_id": transfer.employee_id,
                            "employee_name": _get_transfer_name(transfer),
                            "from_location": source,
                            "to_location": destination,
                        }
                    ],
                    "reason": "No shipment required for same-location transfer",
                }
            )
            continue

        adjacency.setdefault(source, [])
        adjacency.setdefault(destination, [])
        adjacency[source].append(transfer)
        all_nodes.add(source)
        all_nodes.add(destination)

    def inspect_cycle(cycle_transfer_ids: List[str], cycle_length: int) -> None:
        if len(cycle_transfer_ids) <= 1:
            return

        reason = "Mutual employee swap" if cycle_length == 2 else "Transfer cycle detected"
        cycle_transfers = []
        for transfer_id in cycle_transfer_ids:
            if transfer_id in resolved_transfer_ids:
                continue
            transfer = next(t for t in transfers if t.employee_id == transfer_id)
            resolved_transfer_ids.add(transfer_id)
            cycle_transfers.append(
                {
                    "transfer_id": getattr(transfer, "transfer_id", transfer.employee_id),
                    "employee_id": transfer.employee_id,
                    "employee_name": _get_transfer_name(transfer),
                    "from_location": _get_transfer_source(transfer),
                    "to_location": _get_transfer_destination(transfer),
                }
            )

        if cycle_transfers:
            resolved_cycles.append(
                {
                    "cycle_id": f"cycle-{'-'.join(cycle_transfer_ids)}",
                    "cycle_length": cycle_length,
                    "transfers": cycle_transfers,
                    "reason": reason,
                }
            )

    def dfs(node: str, path_nodes: List[str], path_edge_ids: List[str]) -> None:
        path_nodes.append(node)
        for transfer in adjacency.get(node, []):
            if transfer.employee_id in resolved_transfer_ids:
                continue

            destination = _get_transfer_destination(transfer)
            if destination in path_nodes:
                index = path_nodes.index(destination)
                cycle_edge_ids = path_edge_ids[index:] + [transfer.employee_id]
                cycle_length = len(cycle_edge_ids)
                inspect_cycle(cycle_edge_ids, cycle_length)
                continue

            path_edge_ids.append(transfer.employee_id)
            dfs(destination, path_nodes, path_edge_ids)
            path_edge_ids.pop()
        path_nodes.pop()

    for node in sorted(all_nodes):
        dfs(node, [], [])

    active_transfers = [transfer for transfer in transfers if transfer.employee_id not in resolved_transfer_ids]

    resolved_details: List[Dict[str, Any]] = []
    for cycle in resolved_cycles:
        for transfer_info in cycle["transfers"]:
            resolved_details.append(
                ResolvedTransferInfo(
                    {
                        "employee_id": transfer_info["employee_id"],
                        "employee_name": transfer_info["employee_name"],
                        "from_location": transfer_info["from_location"],
                        "to_location": transfer_info["to_location"],
                        "transfer_id": transfer_info.get("transfer_id", transfer_info["employee_id"]),
                        "reason": cycle["reason"],
                    }
                )
            )

    for resolved in self_loop_resolved:
        for transfer_info in resolved["transfers"]:
            resolved_details.append(
                ResolvedTransferInfo(
                    {
                        "employee_id": transfer_info["employee_id"],
                        "employee_name": transfer_info["employee_name"],
                        "from_location": transfer_info["from_location"],
                        "to_location": transfer_info["to_location"],
                        "transfer_id": transfer_info["employee_id"],
                        "reason": resolved["reason"],
                    }
                )
            )

    return active_transfers, resolved_cycles + self_loop_resolved, resolved_details
