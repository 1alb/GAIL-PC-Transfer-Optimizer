from typing import List

from app.models.request_models import OptimizeRequest, Transfer
from app.models.response_models import (
    CycleResolution,
    OptimizeApiResponse,
    ShipmentResolution,
)
from app.utils.logger import logger
from app.utils.solver import TransferResolutionSolver
from app.utils.transfer_cycle_preprocessor import preprocess_transfer_cycles_with_details


def _ensure_synthetic_employee_ids(transfers: List[Transfer]) -> None:
    for index, transfer in enumerate(transfers):
        if not transfer.employee_id:
            transfer.employee_id = f"unnamed-{index}"


def optimize_request(payload: OptimizeRequest) -> OptimizeApiResponse:
    """Coordinate cycle detection and OR-Tools flow-based transfer resolution."""
    _ensure_synthetic_employee_ids(payload.transfers)
    active_transfers, resolved_cycles, _ = preprocess_transfer_cycles_with_details(payload.transfers)
    logger.info(
        "Optimizer received %d transfers, %d transfers remain after cycle resolution.",
        len(payload.transfers),
        len(active_transfers),
    )

    solver = TransferResolutionSolver(active_transfers)
    shipments = solver.solve()

    two_way_swaps = [
        CycleResolution(**cycle)
        for cycle in resolved_cycles
        if cycle["cycle_length"] == 2
    ]
    three_way_swaps = [
        CycleResolution(**cycle)
        for cycle in resolved_cycles
        if cycle["cycle_length"] == 3
    ]

    return OptimizeApiResponse(
        status="OPTIMAL",
        two_way_swaps=two_way_swaps,
        three_way_swaps=three_way_swaps,
        surplus_transfers=shipments,
        unresolved_transfers=active_transfers,
        total_shipments_saved=sum(cycle["cycle_length"] for cycle in resolved_cycles),
        message=(
            f"Transfer resolution completed. {len(resolved_cycles)} cycles removed and "
            f"{len(shipments)} aggregated shipment routes generated."
        ),
    )
