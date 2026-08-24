from ipaddress import ip_address
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SKYLINK_", env_file=".env", extra="ignore")

    mode: str = "demo"
    vehicle_host: str = "127.0.0.1"
    vehicle_port: int = 14542
    px4_link_port: int = 14540
    relay_port: int = 14541
    database_path: Path = Path("data/skylink.db")
    telemetry_hz: float = 5.0
    degraded_after_ms: int = 1_500
    lost_after_ms: int = 4_000

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, value: str) -> str:
        if value not in {"demo", "px4"}:
            raise ValueError("mode must be 'demo' or 'px4'")
        return value

    @field_validator("vehicle_host")
    @classmethod
    def require_loopback(cls, value: str) -> str:
        if not ip_address(value).is_loopback:
            raise ValueError("simulation mode only accepts loopback vehicle addresses")
        return value


settings = Settings()
