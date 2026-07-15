"""
Pydantic Response Models for the transfer-only optimization API.
Defines the output buckets for cycle resolution, surplus shipments, and unresolved transfer demands.
"""

from typing import List, Optional
from pydantic import BaseModel, Field

from .request_models import Transfer


class CycleMember(BaseModel):
    """Represents a single transfer inside a detected cycle."""
    employee_id: str = Field(description="ID of the employee")
    employee_name: str = Field(description="Name of the employee")
    from_location: str = Field(description="Origin location for the transfer")
    to_location: str = Field(description="Destination location for the transfer")


class CycleResolution(BaseModel):
    """Details a detected transfer cycle that avoids physical shipment."""
    cycle_id: str = Field(description="Unique identifier for the detected cycle")
    cycle_length: int = Field(description="Number of transfers in the cycle", ge=1)
    transfers: List[CycleMember] = Field(description="List of transfers that form the cycle")
    reason: str = Field(description="Reason the cycle was resolved without shipment")


class ShipmentResolution(BaseModel):
    """Represents an aggregated shipment required after cycle cancellation."""
    from_location: str = Field(description="Shipment origin location")
    to_location: str = Field(description="Shipment destination location")
    quantity: int = Field(description="Number of PCs to ship along this aggregated route", ge=1)


class OptimizeApiResponse(BaseModel):
    """Backend response model intended for n8n and lightweight clients."""
    status: str = Field(description="Optimization outcome identifier")
    two_way_swaps: List[CycleResolution] = Field(default_factory=list, description="Detected two-way swap cycles resolved without shipment")
    three_way_swaps: List[CycleResolution] = Field(default_factory=list, description="Detected three-way swap cycles resolved without shipment")
    surplus_transfers: List[ShipmentResolution] = Field(default_factory=list, description="Aggregated shipments required after cycle resolution")
    unresolved_transfers: List[Transfer] = Field(default_factory=list, description="Active transfers that still require shipment or review")
    total_shipments_saved: int = Field(default=0, description="Count of physical shipments avoided through cycle resolution")
    message: Optional[str] = Field(default=None, description="Optional human-readable explanation of the outcome")
