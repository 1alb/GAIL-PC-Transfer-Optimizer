from typing import Any, Dict

from fastapi import APIRouter, HTTPException, status

from app.models.request_models import OptimizeRequest
from app.models.response_models import OptimizeApiResponse
from app.services.optimization_service import optimize_request
from app.utils.logger import logger

router = APIRouter()


@router.get("/health")
def health_check() -> Dict[str, Any]:
    """Return basic service health information."""
    return {
        "status": "healthy",
        "service": "PC Logistics Optimization API",
        "version": "1.0.0",
    }


@router.post("/optimize", response_model=OptimizeApiResponse, status_code=status.HTTP_200_OK, response_model_exclude_none=True)
def optimize(payload: OptimizeRequest) -> OptimizeApiResponse:
    """Validate and run the optimization workflow for n8n requests."""
    logger.info("Received optimization request for %d transfers.", len(payload.transfers))
    try:
        return optimize_request(payload)
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Validation error: {str(val_err)}") from val_err
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Optimization failed: {str(exc)}") from exc
