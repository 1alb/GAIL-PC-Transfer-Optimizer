"""
Configuration Module for the PC Logistics Optimization API.
Handles environment variables, CORS settings, and default optimization parameters using Pydantic Settings.
"""

from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App General Config
    PROJECT_NAME: str = "PC Logistics Optimization API"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = False
    ENV: str = "development"

    # CORS Configuration
    # Accepts string-separated lists or JSON arrays of URLs
    BACKEND_CORS_ORIGINS: List[Union[AnyHttpUrl, str]] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://ai.studio",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Default Optimizer Settings
    DEFAULT_SOLVER_TIME_LIMIT_SECONDS: float = 60.0
    DEFAULT_SHIPPING_COST_PER_MILE: float = 1.50
    DEFAULT_CARBON_EMISSION_FACTOR_PER_MILE: float = 0.12  # kg CO2 per mile

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


settings = Settings()
