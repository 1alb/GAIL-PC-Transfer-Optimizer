"""
Pydantic Request Models for the PC Logistics Optimization API.
Defines schemas for the n8n workflow payload and the internal optimizer models.
Adheres to Pydantic v2 best practices.
"""

from datetime import date
from enum import Enum
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class PCType(str, Enum):
    """Types of PCs available for allocation."""

    STANDARD = "STANDARD"
    POWER = "POWER"
    ELITE = "ELITE"


class PCStatus(str, Enum):
    """Current status of the PC hardware."""

    AVAILABLE = "AVAILABLE"
    ASSIGNED = "ASSIGNED"
    MAINTENANCE = "MAINTENANCE"


class PCSpecs(BaseModel):
    """Hardware specifications for a PC."""

    cpu: str = Field(description="CPU model (e.g., Apple M3, Intel i7)", examples=["Intel Core i7-13700"])
    ram_gb: int = Field(description="RAM size in GB", gt=0, examples=[16])
    gpu: Optional[str] = Field(None, description="GPU model if discrete, else None", examples=["NVIDIA RTX 4060"])
    storage_gb: int = Field(description="Storage size in GB", gt=0, examples=[512])


class PCItem(BaseModel):
    """Represents a single PC asset in the inventory."""

    pc_id: str = Field(description="Unique identifier for the PC asset", examples=["PC-10042"])
    serial_number: str = Field(description="Manufacturer serial number", examples=["SN-ABCD-12345"])
    pc_type: PCType = Field(description="Category of the PC (STANDARD, POWER, ELITE)", examples=[PCType.STANDARD])
    specs: PCSpecs = Field(description="Detailed specs of the system")
    status: PCStatus = Field(default=PCStatus.AVAILABLE, description="Status of the PC")


class PlantInventory(BaseModel):
    """Represents a location (Plant/Warehouse) and its PC inventory."""

    plant_id: str = Field(description="Unique identifier for the Plant/Warehouse", examples=["PLANT-CHI"])
    name: str = Field(description="Human-readable name of the facility", examples=["Chicago logistics hub"])
    latitude: float = Field(description="Latitude coordinate of the plant", ge=-90.0, le=90.0, examples=[41.8781])
    longitude: float = Field(description="Longitude coordinate of the plant", ge=-180.0, le=180.0, examples=[-87.6298])
    pcs: List[PCItem] = Field(default_factory=list, description="List of PC assets located at this plant")


class EmployeeTransfer(BaseModel):
    """Represents an employee transferring to another plant who needs a PC allocation."""

    transfer_id: str = Field(description="Unique identifier for the transfer order", examples=["TR-2026-001"])
    employee_id: str = Field(description="Unique ID of the employee", examples=["EMP-9981"])
    name: str = Field(description="Full name of the employee", examples=["Jane Doe"])
    department: str = Field(description="Employee's functional department", examples=["Data Science"])
    source_plant_id: str = Field(description="Plant ID where the employee is currently or was previously located", examples=["PLANT-NYC"])
    destination_plant_id: str = Field(description="Plant ID where the employee is transferring to", examples=["PLANT-CHI"])
    required_pc_type: PCType = Field(description="Required PC tier based on their role", examples=[PCType.POWER])
    transfer_date: date = Field(description="Effective date of the employee transfer", examples=["2026-08-01"])
    special_requirements: List[str] = Field(default_factory=list, description="Any specific custom hardware flags (e.g. 'high_gpu', 'dual_monitor')", examples=[["high_gpu"]])


class PolicyConstraints(BaseModel):
    """Business rules and limits parsed from policies for the optimizer."""

    max_shipping_distance_miles: float = Field(default=500.0, description="Max allowed distance in miles for transferring standard assets", gt=0.0)
    max_elite_shipping_distance_miles: float = Field(default=250.0, description="Max allowed distance in miles for shipping fragile ELITE high-value assets", gt=0.0)
    allow_cross_region_transfers: bool = Field(default=True, description="Whether to allow shipping across boundaries/states if needed")
    prioritize_local_allocation: bool = Field(default=True, description="True if local assets should be exhausted first, penalizing transfers")
    co2_emission_threshold_kg: Optional[float] = Field(None, description="Optional upper boundary on total CO2 emission of shipping", gt=0.0)
    restricted_routes: List[Dict[str, str]] = Field(default_factory=list, description="List of restricted shipping routes between plants/regions")
    priority_plants: List[str] = Field(default_factory=list, description="List of plant IDs with higher allocation priority")
    minimum_buffer_stock: Dict[str, int] = Field(default_factory=dict, description="Minimum inventory buffer stock levels required for each plant mapped by plant_id")


class AssetInput(BaseModel):
    """Single asset supplied by the n8n workflow for a plant."""

    asset_id: str = Field(description="Identifier for the PC asset", examples=["PC-10042"])
    asset_type: str = Field(description="Asset category or hardware tier", examples=["STANDARD"])
    model: str = Field(default="", description="Model name of the asset", examples=["ThinkPad T14"])
    serial_number: str = Field(default="", description="Serial number of the asset", examples=["SN-ABCD-12345"])
    assigned_to: str = Field(default="", description="Current assignee for the asset if any")
    employee_id: str = Field(default="", description="Employee identifier if the asset is already assigned")
    status: str = Field(default="Available", description="Asset status from the workflow payload")


class PlantInput(BaseModel):
    """Plant payload coming directly from the n8n workflow."""

    plant_name: str = Field(description="Plant or site name", examples=["New York"])
    latitude: float = Field(description="Latitude coordinate of the plant", ge=-90.0, le=90.0, examples=[40.7128])
    longitude: float = Field(description="Longitude coordinate of the plant", ge=-180.0, le=180.0, examples=[-74.0060])
    assets: List[AssetInput] = Field(default_factory=list, description="List of assets available at the plant")


class Transfer(BaseModel):
    """Represents an employee movement request for PC follow-the-person resolution."""

    employee_id: Optional[str] = Field(default=None, description="Unique identifier of the employee, or omitted when not available", examples=["EMP-9981"])
    employee_name: str = Field(description="Full name of the employee", examples=["Jane Doe"])
    from_location: str = Field(alias="source_plant", description="Location the employee is moving from", examples=["Delhi"])
    to_location: str = Field(alias="destination_plant", description="Location the employee is moving to", examples=["Kolkata"])
    from_coords: Optional[Dict[str, Any]] = Field(default=None, description="Optional source coordinates for geospatial matching")
    to_coords: Optional[Dict[str, Any]] = Field(default=None, description="Optional destination coordinates for geospatial matching")

    model_config = ConfigDict(populate_by_name=True)


class OptimizeRequest(BaseModel):
    """The complete payload for transfer-only optimization."""

    transfers: List[Transfer] = Field(
        ...,
        description="List of employee transfers for cycle and flow resolution",
    )

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("transfers")
    @classmethod
    def validate_non_empty_transfers(cls, v: List[Transfer]) -> List[Transfer]:
        if not v:
            raise ValueError("At least one transfer must be supplied.")

        for index, transfer in enumerate(v):
            if not transfer.employee_id:
                transfer.employee_id = f"unnamed-{index}"

        return v
