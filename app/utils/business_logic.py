"""
Business Logic Utilities for the PC Logistics Optimization Engine.
Provides reusable helper functions, validators, supply and demand calculations,
and distance matrix lookup utilities.
"""

import math
from typing import List, Dict, Any, Optional, Set, Tuple

from app.config import settings
from app.models.request_models import (
    PlantInventory,
    EmployeeTransfer,
    PCType,
    PolicyConstraints,
    PCStatus,
)


# =====================================================================
# 1. Coordinate & Distance Utilities
# =====================================================================

def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on the Earth in miles.
    Validates coordinate ranges prior to running mathematical formulas.
    
    Args:
        lat1: Latitude of first point in degrees (-90 to 90).
        lon1: Longitude of first point in degrees (-180 to 180).
        lat2: Latitude of second point in degrees (-90 to 90).
        lon2: Longitude of second point in degrees (-180 to 180).
        
    Returns:
        Great-circle distance in miles.
        
    Raises:
        ValueError: If any coordinate is out of bounds.
    """
    if not (-90.0 <= lat1 <= 90.0) or not (-90.0 <= lat2 <= 90.0):
        raise ValueError(f"Latitude must be between -90 and 90 degrees. Got lat1={lat1}, lat2={lat2}")
    if not (-180.0 <= lon1 <= 180.0) or not (-180.0 <= lon2 <= 180.0):
        raise ValueError(f"Longitude must be between -180 and 180 degrees. Got lon1={lon1}, lon2={lon2}")

    R = 3958.8  # Earth's radius in miles
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


class DistanceMatrix:
    """
    Computes and caches distances between plants to avoid repeated heavy mathematical calculations.
    Provides O(1) distance lookups after initialization.
    """

    def __init__(self, plants: List[PlantInventory]) -> None:
        """
        Initializes the distance matrix by caching locations.
        
        Args:
            plants: List of plants containing latitude and longitude.
        """
        self.locations: Dict[str, Tuple[float, float]] = {
            p.plant_id: (p.latitude, p.longitude) for p in plants
        }
        self._matrix: Dict[str, Dict[str, float]] = {}
        self._precompute_matrix()

    def _precompute_matrix(self) -> None:
        """Populates the cached distance matrix dict."""
        plant_ids = list(self.locations.keys())
        for pid1 in plant_ids:
            self._matrix[pid1] = {}
            lat1, lon1 = self.locations[pid1]
            for pid2 in plant_ids:
                if pid1 == pid2:
                    self._matrix[pid1][pid2] = 0.0
                else:
                    lat2, lon2 = self.locations[pid2]
                    self._matrix[pid1][pid2] = calculate_haversine_distance(lat1, lon1, lat2, lon2)

    def get_distance(self, plant_id1: str, plant_id2: str) -> float:
        """
        Retrieve distance between two plants. If not cached, computes dynamically if coordinates are known.
        
        Args:
            plant_id1: ID of first plant.
            plant_id2: ID of second plant.
            
        Returns:
            Distance in miles.
            
        Raises:
            KeyError: If either plant ID is unrecognized.
        """
        if plant_id1 in self._matrix and plant_id2 in self._matrix[plant_id1]:
            return self._matrix[plant_id1][plant_id2]
        
        if plant_id1 not in self.locations or plant_id2 not in self.locations:
            raise KeyError(f"One or both plant IDs ('{plant_id1}', '{plant_id2}') not registered in DistanceMatrix.")

        # If not precomputed but exists in coordinates, compute on-the-fly
        lat1, lon1 = self.locations[plant_id1]
        lat2, lon2 = self.locations[plant_id2]
        dist = calculate_haversine_distance(lat1, lon1, lat2, lon2)
        
        # Cache for subsequent runs
        if plant_id1 not in self._matrix:
            self._matrix[plant_id1] = {}
        self._matrix[plant_id1][plant_id2] = dist
        return dist

    def to_dict(self) -> Dict[str, Dict[str, float]]:
        """Returns the complete precomputed distance matrix dictionary representation."""
        return self._matrix


# =====================================================================
# 2. Input Integrity Validators
# =====================================================================

def validate_input_uniqueness(plants: List[PlantInventory], transfers: List[EmployeeTransfer]) -> None:
    """
    Enforces referential integrity and identifier uniqueness across the payload.
    
    Args:
        plants: List of plant inventories.
        transfers: List of employee transfer requests.
        
    Raises:
        ValueError: If duplicate plant_ids, pc_ids, or transfer_ids are found.
    """
    # 1. Validate unique Plant IDs
    plant_ids: Set[str] = set()
    for p in plants:
        if p.plant_id in plant_ids:
            raise ValueError(f"Payload contains duplicate Plant ID: '{p.plant_id}'")
        plant_ids.add(p.plant_id)

    # 2. Validate unique PC Asset IDs across all plants
    pc_ids: Set[str] = set()
    for p in plants:
        for pc in p.pcs:
            if pc.pc_id in pc_ids:
                raise ValueError(f"Payload contains duplicate PC ID: '{pc.pc_id}' across plant inventories.")
            pc_ids.add(pc.pc_id)

    # 3. Validate unique Transfer IDs
    transfer_ids: Set[str] = set()
    for t in transfers:
        if t.transfer_id in transfer_ids:
            raise ValueError(f"Payload contains duplicate Transfer ID: '{t.transfer_id}'")
        transfer_ids.add(t.transfer_id)


def validate_referential_integrity(plants: List[PlantInventory], transfers: List[EmployeeTransfer]) -> None:
    """
    Ensures every plant ID referenced by transfers exists in the plant list.
    
    Args:
        plants: List of plant inventories.
        transfers: List of transfer orders.
        
    Raises:
        ValueError: If a transfer references a missing source or destination plant ID.
    """
    known_plant_ids = {p.plant_id for p in plants}
    for t in transfers:
        if t.source_plant_id not in known_plant_ids:
            raise ValueError(
                f"Transfer order '{t.transfer_id}' references unknown source plant: '{t.source_plant_id}'"
            )
        if t.destination_plant_id not in known_plant_ids:
            raise ValueError(
                f"Transfer order '{t.transfer_id}' references unknown destination plant: '{t.destination_plant_id}'"
            )


# =====================================================================
# 3. Supply & Demand Balancing
# =====================================================================

def compute_supply_demand_balances(
    plants: List[PlantInventory],
    transfers: List[EmployeeTransfer]
) -> Dict[str, Dict[str, Any]]:
    """
    Analyzes supply of available hardware assets vs employee transfer demands.
    Calculates surplus/deficit per plant, broken down by PC Type.
    
    Args:
        plants: Plant inventory datasets.
        transfers: Employee transfer requests.
        
    Returns:
        A mapping of plant_id -> PC Type balance metadata.
        For example:
        {
            "PLANT-NYC": {
                "STANDARD": {"supply": 5, "demand": 2, "balance": 3},
                "POWER": {"supply": 1, "demand": 3, "balance": -2},
                "ELITE": {"supply": 0, "demand": 0, "balance": 0},
                "total": {"supply": 6, "demand": 5, "balance": 1}
            }
        }
    """
    balances: Dict[str, Dict[str, Any]] = {}
    
    # Initialize entries for each plant
    for p in plants:
        balances[p.plant_id] = {
            PCType.STANDARD: {"supply": 0, "demand": 0, "balance": 0},
            PCType.POWER: {"supply": 0, "demand": 0, "balance": 0},
            PCType.ELITE: {"supply": 0, "demand": 0, "balance": 0},
            "total": {"supply": 0, "demand": 0, "balance": 0}
        }
        
        # Tally supply of AVAILABLE laptops
        for pc in p.pcs:
            if pc.status == PCStatus.AVAILABLE:
                balances[p.plant_id][pc.pc_type]["supply"] += 1
                balances[p.plant_id]["total"]["supply"] += 1

    # Tally demand of transferring employees (destinations)
    for t in transfers:
        dest = t.destination_plant_id
        if dest in balances:
            pc_type = t.required_pc_type
            balances[dest][pc_type]["demand"] += 1
            balances[dest]["total"]["demand"] += 1

    # Compute balances (Supply - Demand)
    for pid, tiers in balances.items():
        for key in [PCType.STANDARD, PCType.POWER, PCType.ELITE, "total"]:
            tiers[key]["balance"] = tiers[key]["supply"] - tiers[key]["demand"]

    return balances


# =====================================================================
# 4. Configurable CO2 & Policy Validation
# =====================================================================


def calculate_transportation_emissions(distance: float) -> float:
    """
    Calculates carbon footprints using configured system carbon factors.
    
    Args:
        distance: Shipping distance in miles.
        
    Returns:
        CO2 emitted in kilograms, rounded to 2 decimal places.
    """
    co2 = distance * settings.DEFAULT_CARBON_EMISSION_FACTOR_PER_MILE
    return round(co2, 2)


def evaluate_transfer_policy(
    source_id: str,
    dest_id: str,
    distance: float,
    pc_type: PCType,
    policy: PolicyConstraints
) -> Dict[str, Any]:
    """
    Evaluates whether a potential transfer path violates any active logistics rules.
    Checks restricted routes, max allowed shipping bounds, and cross-region blocks.
    
    Args:
        source_id: Origin plant identifier.
        dest_id: Target plant identifier.
        distance: Distance between origin and target in miles.
        pc_type: PC Type category being shipped.
        policy: Configured policy boundaries.
        
    Returns:
        A dict reflecting safety parameters:
        {
            "allowed": bool,
            "reason": Optional[str],
            "cross_region_flag": bool
        }
    """
    # 1. Check direct route restriction list
    for route in policy.restricted_routes:
        from_node = route.get("from") or route.get("source") or route.get("source_plant_id")
        to_node = route.get("to") or route.get("destination") or route.get("destination_plant_id")
        if from_node == source_id and to_node == dest_id:
            return {
                "allowed": False,
                "reason": f"Path '{source_id} -> {dest_id}' is explicitly forbidden by policy restricted_routes.",
                "cross_region_flag": False
            }

    # 2. Check maximum physical shipping limits
    max_allowed = (
        policy.max_elite_shipping_distance_miles
        if pc_type == PCType.ELITE
        else policy.max_shipping_distance_miles
    )
    if distance > max_allowed:
        return {
            "allowed": False,
            "reason": f"Distance of {distance:.1f} miles exceeds maximum limit of {max_allowed} miles for {pc_type}.",
            "cross_region_flag": False
        }

    # 3. Check cross-region boundary constraints
    # (By definition, transfers > 150 miles constitute cross-region shipping)
    is_cross_region = distance > 150.0
    if is_cross_region and not policy.allow_cross_region_transfers:
        return {
            "allowed": False,
            "reason": "Cross-region transfer of assets (> 150.0 miles) is disabled by current policies.",
            "cross_region_flag": True
        }

    return {
        "allowed": True,
        "reason": None,
        "cross_region_flag": is_cross_region
    }
