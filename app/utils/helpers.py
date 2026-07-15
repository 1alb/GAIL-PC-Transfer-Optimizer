from collections import defaultdict
from typing import Dict, List, Tuple


def group_allocations_by_route(allocations: List[object]) -> Dict[Tuple[str, str], int]:
    """Aggregate allocations by source and destination plant names."""
    grouped: Dict[Tuple[str, str], int] = defaultdict(int)
    for allocation in allocations:
        grouped[(allocation.source_plant_name, allocation.destination_plant_name)] += 1
    return dict(sorted(grouped.items()))
